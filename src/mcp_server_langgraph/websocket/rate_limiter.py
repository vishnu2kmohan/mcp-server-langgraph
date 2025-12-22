"""
WebSocket Rate Limiting.

Provides rate limiting for WebSocket connections and messages
to prevent abuse and ensure fair resource usage.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RateLimitInfo:
    """
    Rate limit information for error responses.

    Provides clients with information about rate limits when they
    exceed their quota, following standard rate limiting headers pattern.

    Attributes:
        limit: Maximum messages allowed per window (per minute).
        remaining: Number of messages remaining in the current window.
        retry_after: Seconds until the rate limit window resets.
    """

    limit: int
    remaining: int
    retry_after: int

    def to_dict(self) -> dict[str, int]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with limit, remaining, and retry_after fields.
        """
        return {
            "limit": self.limit,
            "remaining": self.remaining,
            "retry_after": self.retry_after,
        }


def _utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(UTC)


class MessageRateLimiter:
    """
    Rate limiter for WebSocket messages using sliding window.

    Tracks message count within a time window and blocks messages
    when the limit is exceeded.

    Usage:
        limiter = MessageRateLimiter(max_messages=100, window_seconds=60)
        if limiter.check_and_increment():
            # Process message
        else:
            # Rate limit exceeded
    """

    def __init__(self, max_messages: int, window_seconds: int) -> None:
        """
        Initialize the rate limiter.

        Args:
            max_messages: Maximum messages allowed in the window.
            window_seconds: Duration of the rate limit window in seconds.
        """
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self._message_count = 0
        self._window_start = _utc_now()

    def check_and_increment(self) -> bool:
        """
        Check if a message is allowed and increment the counter.

        Resets the window if it has expired.

        Returns:
            True if message is allowed, False if rate limit exceeded.
        """
        now = _utc_now()
        elapsed = (now - self._window_start).total_seconds()

        # Reset window if expired
        if elapsed >= self.window_seconds:
            self._window_start = now
            self._message_count = 0

        # Check if under limit
        if self._message_count >= self.max_messages:
            return False

        # Allow and increment
        self._message_count += 1
        return True

    def get_remaining(self) -> int:
        """
        Get the remaining message quota.

        Returns:
            Number of messages remaining in the current window.
        """
        now = _utc_now()
        elapsed = (now - self._window_start).total_seconds()

        # Window expired, full quota available
        if elapsed >= self.window_seconds:
            return self.max_messages

        return max(0, self.max_messages - self._message_count)

    def get_retry_after(self) -> int:
        """
        Get the time until the rate limit window resets.

        Returns:
            Seconds until the window resets (0 if window has expired).
        """
        now = _utc_now()
        elapsed = (now - self._window_start).total_seconds()

        # Window expired, no wait needed
        if elapsed >= self.window_seconds:
            return 0

        return max(0, int(self.window_seconds - elapsed))

    def reset(self) -> None:
        """Reset the rate limiter."""
        self._message_count = 0
        self._window_start = _utc_now()


class UserRateLimiter:
    """
    Manages rate limiting on a per-user basis across all their connections.

    This ensures a user can't bypass rate limits by opening multiple connections.

    Usage:
        limiter = UserRateLimiter(max_messages=100, window_seconds=60)
        if limiter.check_and_increment("user-123"):
            # Process message
        else:
            # Rate limit exceeded for this user
    """

    def __init__(self, max_messages: int, window_seconds: int) -> None:
        """
        Initialize the per-user rate limiter.

        Args:
            max_messages: Maximum messages allowed per user in the window.
            window_seconds: Duration of the rate limit window in seconds.
        """
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self._user_limiters: dict[str, MessageRateLimiter] = {}

    def check_and_increment(self, user_id: str) -> bool:
        """
        Check if a user's message is allowed and increment their counter.

        Args:
            user_id: User identifier.

        Returns:
            True if message is allowed, False if rate limit exceeded.
        """
        if user_id not in self._user_limiters:
            self._user_limiters[user_id] = MessageRateLimiter(
                max_messages=self.max_messages,
                window_seconds=self.window_seconds,
            )

        return self._user_limiters[user_id].check_and_increment()

    def get_remaining(self, user_id: str) -> int:
        """
        Get the remaining quota for a user.

        Args:
            user_id: User identifier.

        Returns:
            Remaining messages for this user.
        """
        if user_id not in self._user_limiters:
            return self.max_messages

        return self._user_limiters[user_id].get_remaining()

    def get_retry_after(self, user_id: str) -> int:
        """
        Get the time until the user's rate limit window resets.

        Args:
            user_id: User identifier.

        Returns:
            Seconds until the window resets (0 if no limiter exists).
        """
        if user_id not in self._user_limiters:
            return 0

        return self._user_limiters[user_id].get_retry_after()

    def get_user_count(self) -> int:
        """Get the number of users being tracked."""
        return len(self._user_limiters)

    def cleanup_expired(self) -> None:
        """
        Remove rate limiters for users whose windows have expired.

        This prevents memory growth from inactive users.
        """
        now = _utc_now()
        expired_users = []

        for user_id, limiter in self._user_limiters.items():
            elapsed = (now - limiter._window_start).total_seconds()
            if elapsed >= self.window_seconds:
                expired_users.append(user_id)

        for user_id in expired_users:
            del self._user_limiters[user_id]


class ConnectionRateLimiter:
    """
    Rate limiter for concurrent WebSocket connections.

    Tracks the number of active connections and prevents new connections
    when the limit is reached.

    Usage:
        limiter = ConnectionRateLimiter(max_connections=1000)
        if limiter.check_connection():
            # Accept connection
            try:
                # Handle connection
            finally:
                limiter.release_connection()
        else:
            # Reject connection
    """

    def __init__(self, max_connections: int) -> None:
        """
        Initialize the connection rate limiter.

        Args:
            max_connections: Maximum concurrent connections allowed.
        """
        self.max_connections = max_connections
        self._active_connections = 0

    def check_connection(self) -> bool:
        """
        Check if a new connection is allowed.

        Returns:
            True if connection is allowed, False if limit reached.
        """
        if self._active_connections >= self.max_connections:
            return False

        self._active_connections += 1
        return True

    def release_connection(self) -> None:
        """Release a connection slot."""
        self._active_connections = max(0, self._active_connections - 1)

    @property
    def active_connections(self) -> int:
        """Get the number of active connections."""
        return self._active_connections


class WebSocketRateLimiter:
    """
    Combined rate limiter for WebSocket endpoints.

    Provides both global and per-user rate limiting with
    configurable limits and cleanup.

    Usage:
        limiter = WebSocketRateLimiter(messages_per_minute=600)

        if limiter.check_message(user_id="user-123"):
            # Process message
        else:
            # Rate limit exceeded
    """

    def __init__(
        self,
        messages_per_minute: int = 600,
        max_users: int = 10000,
        cleanup_interval: int = 300,
    ) -> None:
        """
        Initialize the WebSocket rate limiter.

        Args:
            messages_per_minute: Maximum messages per user per minute.
            max_users: Maximum number of users to track.
            cleanup_interval: Seconds between expired user cleanup.
        """
        self.messages_per_minute = messages_per_minute
        self.max_users = max_users
        self.cleanup_interval = cleanup_interval

        # Per-user limiter
        self._user_limiter = UserRateLimiter(
            max_messages=messages_per_minute,
            window_seconds=60,
        )

        # Global limiter for anonymous/no-user-id messages
        self._global_limiter = MessageRateLimiter(
            max_messages=messages_per_minute,
            window_seconds=60,
        )

        self._last_cleanup = _utc_now()

    def check_message(self, user_id: str | None = None) -> bool:
        """
        Check if a message is allowed.

        Args:
            user_id: Optional user identifier. If None, uses global limit.

        Returns:
            True if message is allowed, False if rate limit exceeded.
        """
        self._maybe_cleanup()

        if user_id:
            return self._user_limiter.check_and_increment(user_id)
        else:
            return self._global_limiter.check_and_increment()

    def get_remaining_quota(self, user_id: str | None = None) -> int:
        """
        Get remaining message quota.

        Args:
            user_id: Optional user identifier.

        Returns:
            Remaining messages in the current window.
        """
        if user_id:
            return self._user_limiter.get_remaining(user_id)
        else:
            return self._global_limiter.get_remaining()

    def get_stats(self) -> dict[str, Any]:
        """
        Get rate limiter statistics.

        Returns:
            Dictionary with rate limiter statistics.
        """
        return {
            "messages_per_minute": self.messages_per_minute,
            "active_users": self._user_limiter.get_user_count(),
            "global_remaining": self._global_limiter.get_remaining(),
        }

    def get_rate_limit_info(self, user_id: str | None = None) -> RateLimitInfo:
        """
        Get rate limit info for error responses.

        Provides structured information about rate limits that can be
        included in error responses to help clients implement backoff.

        Args:
            user_id: Optional user identifier.

        Returns:
            RateLimitInfo with limit, remaining, and retry_after fields.
        """
        if user_id:
            remaining = self._user_limiter.get_remaining(user_id)
            retry_after = self._user_limiter.get_retry_after(user_id)
        else:
            remaining = self._global_limiter.get_remaining()
            retry_after = self._global_limiter.get_retry_after()

        return RateLimitInfo(
            limit=self.messages_per_minute,
            remaining=remaining,
            retry_after=retry_after,
        )

    def _maybe_cleanup(self) -> None:
        """Run cleanup if interval has elapsed."""
        now = _utc_now()
        elapsed = (now - self._last_cleanup).total_seconds()

        if elapsed >= self.cleanup_interval:
            self._user_limiter.cleanup_expired()
            self._last_cleanup = now


# =============================================================================
# Redis-backed Rate Limiters for Distributed Deployments
# =============================================================================


class RedisUserRateLimiter:
    """
    Redis-backed per-user rate limiter for distributed deployments.

    Uses Redis INCR with expiration for atomic rate limiting that works
    across multiple server instances.

    Usage:
        import redis.asyncio as redis
        client = redis.from_url("redis://localhost:6379/3")
        limiter = RedisUserRateLimiter(
            redis_client=client,
            max_messages=100,
            window_seconds=60,
        )

        if await limiter.check_and_increment("user-123"):
            # Process message
        else:
            # Rate limit exceeded
    """

    def __init__(
        self,
        redis_client: Any,
        max_messages: int,
        window_seconds: int,
        key_prefix: str = "ratelimit:ws:user:",
        fail_open: bool = True,
    ) -> None:
        """
        Initialize the Redis-backed per-user rate limiter.

        Args:
            redis_client: Redis async client instance.
            max_messages: Maximum messages allowed per user in the window.
            window_seconds: Duration of the rate limit window in seconds.
            key_prefix: Prefix for Redis keys.
            fail_open: If True, allow requests when Redis is unavailable.
        """
        self._redis = redis_client
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix
        self.fail_open = fail_open

    def _get_key(self, user_id: str) -> str:
        """Get the Redis key for a user."""
        return f"{self.key_prefix}{user_id}"

    async def check_and_increment(self, user_id: str) -> bool:
        """
        Check if a user's message is allowed and increment their counter.

        Uses Redis INCR for atomic increment, with EXPIRE to set TTL
        on first access.

        Args:
            user_id: User identifier.

        Returns:
            True if message is allowed, False if rate limit exceeded.
        """
        key = self._get_key(user_id)

        try:
            # Atomic increment
            count: int = await self._redis.incr(key)

            # Set expiry on first increment (NX = only if not exists)
            if count == 1:
                await self._redis.expire(key, self.window_seconds)
            else:
                # Also try to set expire with NX in case it wasn't set
                await self._redis.expire(key, self.window_seconds, nx=True)

            # Check limit
            return bool(count <= self.max_messages)

        except Exception as e:
            logger.warning(
                f"Redis rate limit check failed for {user_id}: {e}",
                extra={"user_id": user_id, "error": str(e)},
            )
            # Fail-open or fail-closed based on configuration
            return self.fail_open

    async def get_remaining(self, user_id: str) -> int:
        """
        Get the remaining quota for a user.

        Args:
            user_id: User identifier.

        Returns:
            Remaining messages for this user.
        """
        key = self._get_key(user_id)

        try:
            count_bytes = await self._redis.get(key)
            if count_bytes is None:
                return self.max_messages

            count = int(count_bytes)
            return max(0, self.max_messages - count)

        except Exception as e:
            logger.warning(
                f"Redis get remaining failed for {user_id}: {e}",
                extra={"user_id": user_id, "error": str(e)},
            )
            # Return max on error (optimistic)
            return self.max_messages

    async def get_retry_after(self, user_id: str) -> int:
        """
        Get the time until the user's rate limit window resets.

        Uses Redis TTL to get the remaining time on the key.

        Args:
            user_id: User identifier.

        Returns:
            Seconds until the window resets (0 if no key or error).
        """
        key = self._get_key(user_id)

        try:
            ttl: int = await self._redis.ttl(key)
            # TTL returns -1 if key has no expire, -2 if key doesn't exist
            if ttl < 0:
                return 0
            return int(ttl)

        except Exception as e:
            logger.warning(
                f"Redis get TTL failed for {user_id}: {e}",
                extra={"user_id": user_id, "error": str(e)},
            )
            # Return 0 on error (conservative)
            return 0


class RedisWebSocketRateLimiter:
    """
    Redis-backed WebSocket rate limiter for distributed deployments.

    Provides rate limiting that is shared across multiple server instances,
    ensuring consistent enforcement in Kubernetes or other distributed setups.

    Usage:
        limiter = RedisWebSocketRateLimiter(
            redis_url="redis://localhost:6379/3",
            messages_per_minute=600,
        )

        if await limiter.check_message("user-123"):
            # Process message
        else:
            # Rate limit exceeded
    """

    def __init__(
        self,
        redis_url: str,
        messages_per_minute: int = 600,
        key_prefix: str = "ratelimit:ws:user:",
        fail_open: bool = True,
    ) -> None:
        """
        Initialize the Redis WebSocket rate limiter.

        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379/3).
            messages_per_minute: Maximum messages per user per minute.
            key_prefix: Prefix for Redis keys.
            fail_open: If True, allow requests when Redis is unavailable.
        """
        self.redis_url = redis_url
        self.messages_per_minute = messages_per_minute
        self.key_prefix = key_prefix
        self.fail_open = fail_open

        # Lazy-initialized Redis client
        self._redis_client: Any = None
        self._user_limiter: RedisUserRateLimiter | None = None

    async def _ensure_connected(self) -> None:
        """Ensure Redis client is connected (lazy initialization)."""
        if self._redis_client is None:
            try:
                import redis.asyncio as aioredis

                self._redis_client = aioredis.from_url(  # type: ignore[no-untyped-call]
                    self.redis_url,
                    decode_responses=False,
                )
                self._user_limiter = RedisUserRateLimiter(
                    redis_client=self._redis_client,
                    max_messages=self.messages_per_minute,
                    window_seconds=60,
                    key_prefix=self.key_prefix,
                    fail_open=self.fail_open,
                )
            except Exception as e:
                logger.exception(f"Failed to connect to Redis: {e}")
                raise

    async def check_message(self, user_id: str | None = None) -> bool:
        """
        Check if a message is allowed.

        Args:
            user_id: User identifier. Required for Redis-based limiting.

        Returns:
            True if message is allowed, False if rate limit exceeded.
        """
        if user_id is None:
            # For anonymous users, use a fixed key
            user_id = "__anonymous__"

        await self._ensure_connected()

        if self._user_limiter is None:
            return self.fail_open

        return await self._user_limiter.check_and_increment(user_id)

    async def get_remaining_quota(self, user_id: str | None = None) -> int:
        """
        Get remaining message quota.

        Args:
            user_id: User identifier.

        Returns:
            Remaining messages in the current window.
        """
        if user_id is None:
            user_id = "__anonymous__"

        await self._ensure_connected()

        if self._user_limiter is None:
            return self.messages_per_minute

        return await self._user_limiter.get_remaining(user_id)

    async def get_stats(self, user_id: str | None = None) -> dict[str, Any]:
        """
        Get rate limiter statistics for a user.

        Args:
            user_id: User identifier.

        Returns:
            Dictionary with rate limiter statistics.
        """
        if user_id is None:
            user_id = "__anonymous__"

        remaining = await self.get_remaining_quota(user_id)

        return {
            "remaining": remaining,
            "limit": self.messages_per_minute,
            "used": self.messages_per_minute - remaining,
            "user_id": user_id,
        }

    async def get_rate_limit_info(self, user_id: str | None = None) -> RateLimitInfo:
        """
        Get rate limit info for error responses.

        Provides structured information about rate limits that can be
        included in error responses to help clients implement backoff.

        Args:
            user_id: Optional user identifier.

        Returns:
            RateLimitInfo with limit, remaining, and retry_after fields.
        """
        if user_id is None:
            user_id = "__anonymous__"

        await self._ensure_connected()

        remaining = self.messages_per_minute  # Default if not connected
        retry_after = 0

        if self._user_limiter is not None:
            remaining = await self._user_limiter.get_remaining(user_id)
            retry_after = await self._user_limiter.get_retry_after(user_id)

        return RateLimitInfo(
            limit=self.messages_per_minute,
            remaining=remaining,
            retry_after=retry_after,
        )

    async def health_check(self) -> dict[str, Any]:
        """
        Check Redis connection health.

        Performs a PING command to verify connectivity to Redis.

        Returns:
            Dictionary with health status:
                - healthy: bool - True if Redis is responding
                - component: str - "redis_rate_limiter"
                - error: str - Present only if unhealthy
        """
        if self._redis_client is None:
            return {
                "healthy": False,
                "component": "redis_rate_limiter",
                "error": "Redis not connected",
            }

        try:
            await self._redis_client.ping()
            return {
                "healthy": True,
                "component": "redis_rate_limiter",
            }
        except Exception as e:
            return {
                "healthy": False,
                "component": "redis_rate_limiter",
                "error": str(e),
            }

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._redis_client is not None:
            await self._redis_client.close()
            self._redis_client = None
            self._user_limiter = None


# =============================================================================
# Factory Functions
# =============================================================================


def create_redis_rate_limiter(
    messages_per_minute: int = 600,
    key_prefix: str = "ratelimit:ws:user:",
    fail_open: bool = True,
) -> RedisWebSocketRateLimiter:
    """
    Create a Redis-backed WebSocket rate limiter from application settings.

    Args:
        messages_per_minute: Maximum messages per user per minute.
        key_prefix: Prefix for Redis keys.
        fail_open: If True, allow requests when Redis is unavailable.

    Returns:
        RedisWebSocketRateLimiter instance.
    """
    from mcp_server_langgraph.core.config import settings

    redis_url = f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_rate_limit_db}"

    return RedisWebSocketRateLimiter(
        redis_url=redis_url,
        messages_per_minute=messages_per_minute,
        key_prefix=key_prefix,
        fail_open=fail_open,
    )


def get_websocket_rate_limiter(
    messages_per_minute: int = 600,
) -> WebSocketRateLimiter | RedisWebSocketRateLimiter:
    """
    Get the appropriate WebSocket rate limiter based on feature flags.

    Returns in-memory limiter if distributed rate limiting is disabled,
    otherwise returns Redis-backed limiter.

    Args:
        messages_per_minute: Maximum messages per user per minute.

    Returns:
        WebSocketRateLimiter or RedisWebSocketRateLimiter.
    """
    try:
        from mcp_server_langgraph.core.feature_flags import get_feature_flags

        ff = get_feature_flags()
        # Use the existing enable_distributed_rate_limiting flag
        if getattr(ff, "enable_distributed_rate_limiting", False):
            return create_redis_rate_limiter(messages_per_minute=messages_per_minute)
    except Exception as e:
        logger.warning(f"Failed to check feature flags: {e}")

    # Default to in-memory limiter
    return WebSocketRateLimiter(messages_per_minute=messages_per_minute)
