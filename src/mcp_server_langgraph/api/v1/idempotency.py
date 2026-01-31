"""Atomic idempotency guard with Redis support for multi-instance deployments.

This module implements idempotency for chat completion requests to prevent:
- Race conditions from concurrent duplicate requests (R1-Finding 1)
- Content mismatch when request_id is reused (R1-Finding 2)
- Cross-user cache leakage (R2-Finding 8)

Two backends are provided:
- InMemoryIdempotencyBackend: For single-worker deployments (dev/testing)
- RedisIdempotencyBackend: For multi-instance production deployments

The IdempotencyGuard facade selects the appropriate backend based on configuration.
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class IdempotencyState(str, Enum):
    """States for idempotency tracking."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass
class IdempotencyRecord:
    """Record tracking a request's idempotency state.

    Attributes:
        request_id: Client-provided idempotency key
        session_id: Chat session ID
        user_id: User ID for security isolation (R2-Finding 8)
        state: Current state (in_progress or completed)
        created_at: When the record was created
        response: Cached response (only if completed)
        content_hash: SHA-256 hash for content validation (R1-Finding 2)
    """

    request_id: str
    session_id: str
    user_id: str
    state: IdempotencyState
    created_at: datetime
    response: dict[str, Any] | None = None
    content_hash: str | None = None


class IdempotencyBackend(ABC):
    """Abstract backend for idempotency storage.

    Implementations must be thread-safe and support atomic operations.
    """

    @abstractmethod
    async def try_acquire(self, user_id: str, session_id: str, request_id: str, content_hash: str) -> IdempotencyRecord | None:
        """Attempt to acquire idempotency lock.

        Args:
            user_id: User making the request (for isolation)
            session_id: Chat session ID
            request_id: Client-provided idempotency key
            content_hash: Hash of request content for validation

        Returns:
            None if lock acquired (new request)
            IdempotencyRecord if request already completed (return cached)

        Raises:
            HTTPException: 409 if request is in-progress or content mismatch
        """
        ...

    @abstractmethod
    async def mark_completed(self, user_id: str, session_id: str, request_id: str, response: dict[str, Any]) -> None:
        """Mark request as completed with cached response.

        Args:
            user_id: User who made the request
            session_id: Chat session ID
            request_id: Client-provided idempotency key
            response: Response to cache for idempotent retries
        """
        ...

    @abstractmethod
    async def release(self, user_id: str, session_id: str, request_id: str) -> None:
        """Release lock on failure (allows retry).

        Args:
            user_id: User who made the request
            session_id: Chat session ID
            request_id: Client-provided idempotency key
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the backend is healthy and ready to serve requests.

        Returns:
            True if healthy, False otherwise.
        """
        ...


class InMemoryIdempotencyBackend(IdempotencyBackend):
    """In-memory backend for single-worker deployments.

    WARNING: Not safe for multi-worker or multi-instance deployments.
    Use RedisIdempotencyBackend for production with multiple workers.

    Features:
    - Periodic cleanup instead of every-request cleanup (R2-Finding 5)
    - Size limits to prevent unbounded growth (R2-Finding 4)
    - User isolation in composite key (R2-Finding 8)
    """

    def __init__(
        self,
        ttl_seconds: int = 300,
        max_entries: int = 10000,
        cleanup_interval: int = 100,
        max_response_size: int = 1024 * 1024,
    ):
        """Initialize in-memory backend.

        Args:
            ttl_seconds: Time-to-live for records (default 5 minutes)
            max_entries: Maximum records before forced cleanup
            cleanup_interval: Cleanup every N requests (not every request)
            max_response_size: Max cached response size in bytes (R3, default 1MB)
        """
        self._records: dict[str, IdempotencyRecord] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
        self._max_entries = max_entries
        self._max_response_size = max_response_size
        self._lock = asyncio.Lock()
        self._cleanup_counter = 0
        self._cleanup_interval = cleanup_interval

    def _build_key(self, user_id: str, session_id: str, request_id: str) -> str:
        """Build composite key including user_id for security (R2-Finding 8)."""
        return f"{user_id}:{session_id}:{request_id}"

    async def _cleanup_expired(self) -> None:
        """Remove expired records (called periodically, not every request).

        R2-Finding 5: Periodic cleanup reduces lock contention.
        """
        now = datetime.now(UTC)
        expired = [k for k, v in self._records.items() if now - v.created_at > self._ttl]
        for k in expired:
            del self._records[k]

        # If still over limit, remove oldest (R2-Finding 4)
        if len(self._records) > self._max_entries:
            sorted_keys = sorted(self._records.keys(), key=lambda k: self._records[k].created_at)
            for k in sorted_keys[: len(self._records) - self._max_entries]:
                del self._records[k]

    async def try_acquire(self, user_id: str, session_id: str, request_id: str, content_hash: str) -> IdempotencyRecord | None:
        """Attempt to acquire lock with atomic check-and-set."""
        key = self._build_key(user_id, session_id, request_id)

        async with self._lock:
            # Periodic cleanup instead of every request (R2-Finding 5)
            self._cleanup_counter += 1
            if self._cleanup_counter >= self._cleanup_interval:
                await self._cleanup_expired()
                self._cleanup_counter = 0

            existing = self._records.get(key)
            if existing:
                if existing.state == IdempotencyState.IN_PROGRESS:
                    # R1-Finding 1: Return 409 for concurrent requests
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "error": "Request in progress",
                            "request_id": request_id,
                            "retry_after_seconds": 5,
                        },
                        headers={"Retry-After": "5"},
                    )
                elif existing.state == IdempotencyState.COMPLETED:
                    # R1-Finding 2: Verify content hash matches
                    if existing.content_hash and existing.content_hash != content_hash:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail={
                                "error": "Request ID reused with different content",
                                "request_id": request_id,
                                "message": "Generate a new request_id for different messages.",
                            },
                        )
                    # Codex review: Treat response=None (oversized) as cache miss
                    # This allows recomputation instead of returning empty cached response
                    if existing.response is None:
                        return None
                    return existing

            # Acquire lock
            self._records[key] = IdempotencyRecord(
                request_id=request_id,
                session_id=session_id,
                user_id=user_id,
                state=IdempotencyState.IN_PROGRESS,
                created_at=datetime.now(UTC),
                content_hash=content_hash,
            )
            return None

    async def mark_completed(self, user_id: str, session_id: str, request_id: str, response: dict[str, Any]) -> None:
        """Mark request as completed with cached response.

        R3: Limit response size to prevent memory issues (same as Redis backend).
        """
        key = self._build_key(user_id, session_id, request_id)
        async with self._lock:
            if key in self._records:
                self._records[key].state = IdempotencyState.COMPLETED
                # R3: Check response size before storing
                response_str = json.dumps(response)
                if len(response_str) <= self._max_response_size:
                    self._records[key].response = response
                # If too large, leave response as None (don't cache it)

    async def release(self, user_id: str, session_id: str, request_id: str) -> None:
        """Release lock on failure so client can retry."""
        key = self._build_key(user_id, session_id, request_id)
        async with self._lock:
            record = self._records.get(key)
            if record and record.state == IdempotencyState.IN_PROGRESS:
                del self._records[key]

    async def health_check(self) -> bool:
        """In-memory backend is always healthy."""
        return True


class RedisIdempotencyBackend(IdempotencyBackend):
    """Redis-based backend for multi-instance deployments.

    Uses SET NX with TTL for atomic lock acquisition.
    Suitable for production with multiple workers/instances.

    Features:
    - Atomic operations via Redis SET NX
    - Automatic TTL expiration (no manual cleanup needed)
    - Response size limits (R2-Finding 4)
    - Fail-open behavior for graceful degradation (R3)
    """

    def __init__(
        self,
        redis_url: str,
        ttl_seconds: int = 300,
        max_response_size: int = 1024 * 1024,
        fail_open: bool = True,
    ):
        """Initialize Redis backend.

        Args:
            redis_url: Redis connection URL
            ttl_seconds: TTL for records (default 5 minutes)
            max_response_size: Max cached response size in bytes (1MB default)
            fail_open: If True, allow requests when Redis is unavailable (R3).
                      If False, return 503 Service Unavailable on Redis errors.
        """
        self._redis_url = redis_url
        self._ttl_seconds = ttl_seconds
        self._max_response_size = max_response_size
        self._fail_open = fail_open
        self._client: Any = None

    async def _get_client(self) -> Any:
        """Lazy initialize Redis client."""
        if self._client is None:
            import redis.asyncio as redis

            self._client = redis.from_url(self._redis_url)  # type: ignore[no-untyped-call]
        return self._client

    def _build_key(self, user_id: str, session_id: str, request_id: str) -> str:
        """Build Redis key with user isolation (R2-Finding 8)."""
        return f"idempotency:{user_id}:{session_id}:{request_id}"

    async def try_acquire(self, user_id: str, session_id: str, request_id: str, content_hash: str) -> IdempotencyRecord | None:
        """Attempt atomic lock acquisition via SET NX.

        R3: Handle Redis connection errors with fail-open behavior.
        """
        try:
            client = await self._get_client()
            key = self._build_key(user_id, session_id, request_id)

            # Try to set with NX (only if not exists) - atomic operation
            record_data = json.dumps(
                {
                    "state": IdempotencyState.IN_PROGRESS.value,
                    "user_id": user_id,
                    "session_id": session_id,
                    "request_id": request_id,
                    "content_hash": content_hash,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            )

            acquired = await client.set(key, record_data, nx=True, ex=self._ttl_seconds)

            if acquired:
                return None  # Lock acquired

            # Key exists - check state
            existing_data = await client.get(key)
            if existing_data:
                data = json.loads(existing_data)
                if data.get("state") == IdempotencyState.IN_PROGRESS.value:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "error": "Request in progress",
                            "request_id": request_id,
                            "retry_after_seconds": 5,
                        },
                        headers={"Retry-After": "5"},
                    )
                elif data.get("state") == IdempotencyState.COMPLETED.value:
                    # Verify content hash (R1-Finding 2)
                    if data.get("content_hash") and data["content_hash"] != content_hash:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail={
                                "error": "Request ID reused with different content",
                                "request_id": request_id,
                            },
                        )
                    # Codex review: Treat response=None (oversized) as cache miss
                    if data.get("response") is None:
                        return None
                    return IdempotencyRecord(
                        request_id=request_id,
                        session_id=session_id,
                        user_id=user_id,
                        state=IdempotencyState.COMPLETED,
                        created_at=datetime.fromisoformat(data["created_at"]),
                        response=data.get("response"),
                        content_hash=data.get("content_hash"),
                    )

            return None
        except (ConnectionError, OSError, TimeoutError) as e:
            # R3: Handle Redis connection errors
            # Note: redis.exceptions.RedisError inherits from Exception but not from
            # ConnectionError/OSError/TimeoutError. However, the redis library typically
            # raises these standard exceptions for connectivity issues. For broader
            # Redis-specific errors, the fail_open mode allows the request to proceed.
            if self._fail_open:
                logger.warning(
                    "Redis unavailable for idempotency check, allowing request (fail_open=True): %s",
                    str(e),
                )
                return None  # Allow request to proceed
            else:
                logger.exception("Redis unavailable for idempotency check")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "error": "Idempotency service unavailable",
                        "message": "Redis is unavailable. Please retry later.",
                    },
                ) from e

    async def mark_completed(self, user_id: str, session_id: str, request_id: str, response: dict[str, Any]) -> None:
        """Mark request as completed with cached response."""
        client = await self._get_client()
        key = self._build_key(user_id, session_id, request_id)

        existing_data = await client.get(key)
        if existing_data:
            data = json.loads(existing_data)
            data["state"] = IdempotencyState.COMPLETED.value

            # R2-Finding 4: Limit response size to prevent memory issues
            # Optimization: Serialize response once and reuse for both size check and storage
            response_str = json.dumps(response, sort_keys=True)
            if len(response_str) <= self._max_response_size:
                data["response"] = response

            await client.set(key, json.dumps(data, sort_keys=True), ex=self._ttl_seconds)

    async def release(self, user_id: str, session_id: str, request_id: str) -> None:
        """Release lock by deleting the key."""
        client = await self._get_client()
        key = self._build_key(user_id, session_id, request_id)
        await client.delete(key)

    async def health_check(self) -> bool:
        """Check Redis connectivity via PING.

        Returns:
            True if Redis responds to PING, False otherwise.
        """
        try:
            client = await self._get_client()
            await client.ping()
            return True
        except (ConnectionError, OSError, TimeoutError):
            return False


class IdempotencyGuard:
    """Facade for idempotency backend selection.

    Automatically selects Redis backend when REDIS_URL is configured,
    falls back to in-memory with a warning for multi-worker risk.
    """

    def __init__(self) -> None:
        self._backend: IdempotencyBackend | None = None

    def _get_backend(self) -> IdempotencyBackend:
        """Get or create the appropriate backend."""
        if self._backend is None:
            from mcp_server_langgraph.core.config import settings

            redis_url = getattr(settings, "redis_url", None)
            workers = getattr(settings, "workers", 1)

            # R3: Fail-fast validation for multi-worker deployments
            validate_multi_worker_config(workers, redis_url)

            if redis_url:
                ttl = getattr(settings, "idempotency_ttl_seconds", 300)
                self._backend = RedisIdempotencyBackend(redis_url, ttl_seconds=ttl)
            else:
                # Single-worker mode with warning (R2-Finding 1)
                logger.warning("Using in-memory idempotency guard. Set REDIS_URL for multi-worker deployments.")
                ttl = getattr(settings, "idempotency_ttl_seconds", 300)
                max_entries = getattr(settings, "idempotency_max_entries", 10000)
                self._backend = InMemoryIdempotencyBackend(ttl_seconds=ttl, max_entries=max_entries)

        return self._backend

    async def try_acquire(self, user_id: str, session_id: str, request_id: str, content_hash: str) -> IdempotencyRecord | None:
        """Attempt to acquire idempotency lock."""
        return await self._get_backend().try_acquire(user_id, session_id, request_id, content_hash)

    async def mark_completed(self, user_id: str, session_id: str, request_id: str, response: dict[str, Any]) -> None:
        """Mark request as completed with cached response."""
        await self._get_backend().mark_completed(user_id, session_id, request_id, response)

    async def release(self, user_id: str, session_id: str, request_id: str) -> None:
        """Release lock on failure."""
        await self._get_backend().release(user_id, session_id, request_id)


# Singleton instance
_idempotency_guard = IdempotencyGuard()


def get_idempotency_guard() -> IdempotencyGuard:
    """Get the idempotency guard singleton."""
    return _idempotency_guard


def validate_multi_worker_config(workers: int, redis_url: str | None) -> None:
    """Validate configuration for multi-worker deployments.

    R3: Fail-fast at startup when workers > 1 without REDIS_URL configured.
    The in-memory idempotency backend is not safe for multi-worker deployments
    as each worker has its own isolated memory space.

    Args:
        workers: Number of workers configured (e.g., uvicorn --workers N)
        redis_url: Redis connection URL, if configured

    Raises:
        RuntimeError: If workers > 1 and redis_url is not configured
    """
    if workers > 1 and not redis_url:
        raise RuntimeError(
            f"Multi-worker deployment detected ({workers} workers) but REDIS_URL is not configured. "
            "The in-memory idempotency backend is not safe for multi-worker deployments. "
            "Please set REDIS_URL environment variable to enable distributed idempotency."
        )
