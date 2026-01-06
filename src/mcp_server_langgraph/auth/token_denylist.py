"""Token denylist for immediate JWT revocation on logout.

Per OWASP Session Management Cheat Sheet:
"When an explicit session termination event occurs, a digest or hash of any
associated JWTs should be submitted to a denylist on the API."

This module provides both in-memory and Redis-backed implementations:
- InMemoryTokenDenylist: For development/testing (data lost on restart)
- RedisTokenDenylist: For production (persistent, supports clustering)

Usage:
    # On logout, add token to denylist
    await denylist.add(token_jti, token_expires_at)

    # During token verification, check denylist
    if await denylist.is_denied(token_jti):
        raise jwt.InvalidTokenError("Token has been revoked")
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from mcp_server_langgraph.observability.telemetry import logger

if TYPE_CHECKING:
    import redis.asyncio


class TokenDenylist(ABC):
    """Abstract base class for token denylist implementations."""

    @abstractmethod
    async def add(self, jti: str, expires_at: datetime) -> None:
        """
        Add a token JTI to the denylist.

        Args:
            jti: JWT ID (unique token identifier from 'jti' claim)
            expires_at: Token expiration timestamp (for auto-cleanup)
        """

    @abstractmethod
    async def is_denied(self, jti: str) -> bool:
        """
        Check if a token JTI is in the denylist.

        Args:
            jti: JWT ID to check

        Returns:
            True if token is denied, False otherwise
        """

    @abstractmethod
    async def remove(self, jti: str) -> None:
        """
        Remove a token JTI from the denylist.

        Args:
            jti: JWT ID to remove
        """

    @abstractmethod
    async def aclose(self) -> None:
        """
        Close any underlying connections (idempotent).

        Safe to call multiple times. Should be called during shutdown.
        """


class InMemoryTokenDenylist(TokenDenylist):
    """
    In-memory token denylist for development and testing.

    WARNING: Not suitable for production use:
    - Data lost on restart
    - No clustering support
    - Memory grows unbounded without cleanup
    """

    def __init__(self) -> None:
        """Initialize in-memory denylist."""
        # Maps JTI -> expiration timestamp
        self._denied_tokens: dict[str, datetime] = {}
        logger.info("Initialized InMemoryTokenDenylist")

    async def add(self, jti: str, expires_at: datetime) -> None:
        """Add token to denylist until its expiration."""
        # Don't add already expired tokens
        now = datetime.now(UTC)
        if expires_at <= now:
            logger.debug(f"Token {jti[:8]}... already expired, not adding to denylist")
            return

        self._denied_tokens[jti] = expires_at
        logger.info(f"Token {jti[:8]}... added to denylist until {expires_at.isoformat()}")

    async def is_denied(self, jti: str) -> bool:
        """Check if token is denied."""
        if jti not in self._denied_tokens:
            return False

        expires_at = self._denied_tokens[jti]
        now = datetime.now(UTC)

        # Auto-cleanup expired entries
        if expires_at <= now:
            del self._denied_tokens[jti]
            logger.debug(f"Token {jti[:8]}... removed from denylist (expired)")
            return False

        return True

    async def remove(self, jti: str) -> None:
        """Remove token from denylist."""
        if jti in self._denied_tokens:
            del self._denied_tokens[jti]
            logger.debug(f"Token {jti[:8]}... removed from denylist")

    async def aclose(self) -> None:
        """No-op for in-memory implementation (idempotent)."""
        pass


class RedisTokenDenylist(TokenDenylist):
    """
    Redis-backed token denylist for production use.

    Features:
    - Persistent storage survives restarts
    - Automatic TTL-based expiration (Redis handles cleanup)
    - Clustering support via Redis Cluster
    - O(1) lookup performance
    """

    def __init__(
        self,
        redis_client: redis.asyncio.Redis,
        key_prefix: str = "token_denylist:",
    ) -> None:
        """
        Initialize Redis-backed denylist.

        Args:
            redis_client: Async Redis client instance
            key_prefix: Prefix for all denylist keys (default: "token_denylist:")
        """
        self.redis = redis_client
        self.key_prefix = key_prefix
        logger.info(f"Initialized RedisTokenDenylist with prefix '{key_prefix}'")

    async def add(self, jti: str, expires_at: datetime) -> None:
        """Add token to denylist with TTL matching token expiration."""
        now = datetime.now(UTC)

        # Don't add already expired tokens
        if expires_at <= now:
            logger.debug(f"Token {jti[:8]}... already expired, not adding to denylist")
            return

        # Calculate TTL in seconds
        ttl = max(0, int((expires_at - now).total_seconds()))

        key = f"{self.key_prefix}{jti}"
        await self.redis.setex(key, ttl, "revoked")

        logger.info(f"Token {jti[:8]}... added to Redis denylist (TTL: {ttl}s)")

    async def is_denied(self, jti: str) -> bool:
        """Check if token is denied."""
        key = f"{self.key_prefix}{jti}"
        result = await self.redis.exists(key)
        return bool(result and int(result) > 0)

    async def remove(self, jti: str) -> None:
        """Remove token from denylist."""
        key = f"{self.key_prefix}{jti}"
        await self.redis.delete(key)
        logger.debug(f"Token {jti[:8]}... removed from Redis denylist")

    async def aclose(self) -> None:
        """
        Close the Redis client (idempotent).

        Safe to call multiple times. After calling, Redis operations will fail.
        This should be called during application shutdown to prevent connection leaks.
        """
        if self.redis is not None:
            try:
                await self.redis.aclose()
            except Exception as e:
                logger.warning(f"Error closing RedisTokenDenylist Redis client: {e}")
            finally:
                self.redis = None  # type: ignore[assignment]


def create_token_denylist(
    backend: str = "memory",
    redis_client: redis.asyncio.Redis | None = None,
    key_prefix: str = "token_denylist:",
) -> TokenDenylist:
    """
    Factory function to create a token denylist instance.

    Args:
        backend: Backend type ("memory" or "redis")
        redis_client: Redis client (required for "redis" backend)
        key_prefix: Redis key prefix (only used for "redis" backend)

    Returns:
        TokenDenylist instance

    Raises:
        ValueError: If backend is invalid or redis_client missing for redis backend
    """
    if backend == "memory":
        return InMemoryTokenDenylist()
    elif backend == "redis":
        if redis_client is None:
            msg = "redis_client is required for Redis backend"
            raise ValueError(msg)
        return RedisTokenDenylist(redis_client, key_prefix)
    else:
        msg = f"Unsupported backend: {backend}. Use 'memory' or 'redis'."
        raise ValueError(msg)
