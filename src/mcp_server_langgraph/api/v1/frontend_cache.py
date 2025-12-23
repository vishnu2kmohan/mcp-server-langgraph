"""
Frontend Cache API

Provides Redis L2 caching endpoints for the frontend useTieredCache hook.
Enables cross-tab cache sharing and persistence beyond sessionStorage limits.

Endpoints:
- GET /cache/{key} - Get cached value (user-scoped)
- PUT /cache/{key} - Set cached value with TTL
- DELETE /cache/{key} - Delete cached value
- DELETE /cache/prefix/{prefix} - Invalidate all keys matching prefix

Security:
- All keys are user-scoped to prevent cross-user data leakage
- Authentication required for all endpoints
- Maximum TTL enforced (1 hour)
- Maximum value size enforced (100KB)

Reference: docs-internal/CACHING_ARCHITECTURE_AUDIT.md - "Redis L2 Backend for Frontend"
"""

import json
import sys
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.dependencies import get_current_user
from mcp_server_langgraph.core.cache import CacheService, get_cache
from mcp_server_langgraph.observability.telemetry import logger


# =============================================================================
# Prometheus Metrics
# =============================================================================

try:
    from prometheus_client import Counter, Histogram

    # Cache operation counters
    frontend_cache_get_total = Counter(
        name="frontend_cache_get_total",
        documentation="Total frontend cache GET requests",
    )

    frontend_cache_hit_total = Counter(
        name="frontend_cache_hit_total",
        documentation="Total frontend cache hits",
    )

    frontend_cache_miss_total = Counter(
        name="frontend_cache_miss_total",
        documentation="Total frontend cache misses",
    )

    frontend_cache_set_total = Counter(
        name="frontend_cache_set_total",
        documentation="Total frontend cache SET requests",
    )

    frontend_cache_delete_total = Counter(
        name="frontend_cache_delete_total",
        documentation="Total frontend cache DELETE requests",
    )

    # Latency histogram
    frontend_cache_latency_seconds = Histogram(
        name="frontend_cache_latency_seconds",
        documentation="Frontend cache operation latency in seconds",
        labelnames=["operation"],
        buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    )

    PROMETHEUS_AVAILABLE = True

except ImportError:
    # Fallback to mock metrics if prometheus_client not available
    import warnings

    warnings.warn(
        "prometheus_client not available. Frontend cache metrics will be disabled.",
        stacklevel=2,
    )

    class _MockCounter:
        """Mock counter for when prometheus_client is unavailable."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._value = _MockValue()

        def inc(self, amount: float = 1) -> None:
            self._value._val += amount

    class _MockValue:
        """Mock value holder."""

        def __init__(self) -> None:
            self._val: float = 0.0

        def get(self) -> float:
            return self._val

    class _MockHistogram:
        """Mock histogram for when prometheus_client is unavailable."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._count = _MockValue()
            self._sum = 0.0

        def labels(self, **kwargs: Any) -> "_MockHistogram":
            return self

        def observe(self, value: float) -> None:
            self._count._val += 1
            self._sum += value

    frontend_cache_get_total = _MockCounter()  # type: ignore[assignment]
    frontend_cache_hit_total = _MockCounter()  # type: ignore[assignment]
    frontend_cache_miss_total = _MockCounter()  # type: ignore[assignment]
    frontend_cache_set_total = _MockCounter()  # type: ignore[assignment]
    frontend_cache_delete_total = _MockCounter()  # type: ignore[assignment]
    frontend_cache_latency_seconds = _MockHistogram()  # type: ignore[assignment]
    PROMETHEUS_AVAILABLE = False

# =============================================================================
# Constants
# =============================================================================

# Cache key prefix for frontend-sourced cache entries
FRONTEND_CACHE_PREFIX = "frontend"

# Default TTL for frontend cache entries (5 minutes)
DEFAULT_TTL_SECONDS = 300

# Maximum TTL allowed (1 hour) - prevents indefinite cache entries
MAX_TTL_SECONDS = 3600

# Maximum value size in bytes (100KB) - prevents memory exhaustion
MAX_VALUE_SIZE_BYTES = 100 * 1024


# =============================================================================
# Request/Response Models
# =============================================================================


class CacheSetRequest(BaseModel):
    """Request body for setting a cached value."""

    value: Any = Field(..., description="Value to cache (must be JSON-serializable)")
    ttl_seconds: int | None = Field(
        default=None,
        description=f"TTL in seconds (default: {DEFAULT_TTL_SECONDS}, max: {MAX_TTL_SECONDS})",
        ge=1,
        # Note: No max validation here - we cap at MAX_TTL_SECONDS in the handler
        # This allows clients to request longer TTLs but they get capped server-side
    )


class CacheResponse(BaseModel):
    """Response for cache operations."""

    key: str = Field(..., description="Cache key (without user prefix)")
    hit: bool | None = Field(default=None, description="Whether cache hit occurred (GET only)")
    value: Any | None = Field(default=None, description="Cached value (GET only)")
    success: bool | None = Field(default=None, description="Whether operation succeeded (PUT/DELETE)")


class CacheInvalidateResponse(BaseModel):
    """Response for prefix invalidation."""

    prefix: str = Field(..., description="Prefix that was invalidated")
    deleted_count: int = Field(..., description="Number of keys deleted")


# =============================================================================
# Router
# =============================================================================

frontend_cache_router = APIRouter(prefix="/cache", tags=["frontend-cache"])


# =============================================================================
# Helper Functions
# =============================================================================


def _make_user_cache_key(user_id: str, key: str) -> str:
    """
    Generate user-scoped cache key.

    Args:
        user_id: Authenticated user's ID
        key: Original cache key from frontend

    Returns:
        User-scoped cache key: "frontend:{user_id}:{key}"
    """
    return f"{FRONTEND_CACHE_PREFIX}:{user_id}:{key}"


def _validate_value_size(value: Any) -> None:
    """
    Validate that value size is within limits.

    Args:
        value: Value to validate

    Raises:
        HTTPException: If value exceeds size limit
    """
    try:
        serialized = json.dumps(value)
        size = sys.getsizeof(serialized)
        if size > MAX_VALUE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"Value size ({size} bytes) exceeds maximum ({MAX_VALUE_SIZE_BYTES} bytes)",
            )
    except (TypeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Value must be JSON-serializable: {e}",
        ) from e


# =============================================================================
# Endpoints
# =============================================================================


@frontend_cache_router.get("/{key:path}", response_model=CacheResponse)
async def get_cached_value(
    key: str,
    cache: CacheService = Depends(get_cache),
    user: dict[str, Any] = Depends(get_current_user),
) -> CacheResponse:
    """
    Get cached value for frontend (user-scoped).

    The cache key is automatically prefixed with the user ID to ensure
    isolation between users.

    Args:
        key: Cache key (will be prefixed with user ID)
        cache: CacheService dependency
        user: Authenticated user

    Returns:
        CacheResponse with hit status and value if found
    """
    start_time = time.perf_counter()
    user_id = user.get("user_id", user.get("sub", "anonymous"))
    full_key = _make_user_cache_key(user_id, key)

    # Increment GET counter
    frontend_cache_get_total.inc()

    try:
        value = await cache.aget(full_key)
        hit = value is not None

        # Increment hit/miss counters
        if hit:
            frontend_cache_hit_total.inc()
        else:
            frontend_cache_miss_total.inc()

        # Record latency
        duration = time.perf_counter() - start_time
        frontend_cache_latency_seconds.labels(operation="get").observe(duration)

        logger.debug(
            "Frontend cache GET",
            extra={
                "cache_key": key,
                "user_id": user_id,
                "hit": hit,
                "duration_ms": duration * 1000,
            },
        )

        return CacheResponse(key=key, hit=hit, value=value)

    except Exception as e:
        # Record latency even on error
        duration = time.perf_counter() - start_time
        frontend_cache_latency_seconds.labels(operation="get").observe(duration)

        # Increment miss counter on error
        frontend_cache_miss_total.inc()

        logger.warning(
            "Frontend cache GET failed",
            extra={
                "cache_key": key,
                "user_id": user_id,
                "error": str(e),
                "duration_ms": duration * 1000,
            },
        )
        # Return miss on error (graceful degradation)
        return CacheResponse(key=key, hit=False, value=None)


@frontend_cache_router.put("/{key:path}", response_model=CacheResponse)
async def set_cached_value(
    key: str,
    request: CacheSetRequest,
    cache: CacheService = Depends(get_cache),
    user: dict[str, Any] = Depends(get_current_user),
) -> CacheResponse:
    """
    Set cached value for frontend (user-scoped).

    The cache key is automatically prefixed with the user ID to ensure
    isolation between users. TTL is enforced with a maximum of 1 hour.

    Args:
        key: Cache key (will be prefixed with user ID)
        request: Cache set request with value and optional TTL
        cache: CacheService dependency
        user: Authenticated user

    Returns:
        CacheResponse with success status

    Raises:
        HTTPException 413: If value exceeds size limit
        HTTPException 400: If value is not JSON-serializable
    """
    start_time = time.perf_counter()
    user_id = user.get("user_id", user.get("sub", "anonymous"))
    full_key = _make_user_cache_key(user_id, key)

    # Validate value size
    _validate_value_size(request.value)

    # Determine TTL (with max enforcement)
    ttl = request.ttl_seconds if request.ttl_seconds is not None else DEFAULT_TTL_SECONDS
    ttl = min(ttl, MAX_TTL_SECONDS)

    # Increment SET counter
    frontend_cache_set_total.inc()

    try:
        await cache.aset(full_key, request.value, ttl=ttl)

        # Record latency
        duration = time.perf_counter() - start_time
        frontend_cache_latency_seconds.labels(operation="set").observe(duration)

        logger.debug(
            "Frontend cache SET",
            extra={
                "cache_key": key,
                "user_id": user_id,
                "ttl_seconds": ttl,
                "duration_ms": duration * 1000,
            },
        )

        return CacheResponse(key=key, success=True)

    except Exception as e:
        # Record latency even on error
        duration = time.perf_counter() - start_time
        frontend_cache_latency_seconds.labels(operation="set").observe(duration)

        logger.warning(
            "Frontend cache SET failed",
            extra={
                "cache_key": key,
                "user_id": user_id,
                "error": str(e),
                "duration_ms": duration * 1000,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set cache value: {e}",
        ) from e


@frontend_cache_router.delete("/prefix/{prefix:path}", response_model=CacheInvalidateResponse)
async def invalidate_prefix(
    prefix: str,
    cache: CacheService = Depends(get_cache),
    user: dict[str, Any] = Depends(get_current_user),
) -> CacheInvalidateResponse:
    """
    Invalidate all keys matching prefix.

    Uses SCAN-based pattern deletion for efficiency.

    Note: This route must be defined BEFORE /{key:path} to ensure proper matching.

    Args:
        prefix: Key prefix to invalidate
        cache: CacheService dependency
        user: Authenticated user

    Returns:
        CacheInvalidateResponse with deleted count
    """
    user_id = user.get("user_id", user.get("sub", "anonymous"))
    pattern = f"{FRONTEND_CACHE_PREFIX}:{user_id}:{prefix}:*"

    try:
        count = await cache.adelete_pattern(pattern)

        logger.debug(
            "Frontend cache prefix invalidation",
            extra={
                "prefix": prefix,
                "user_id": user_id,
                "deleted_count": count,
            },
        )

        return CacheInvalidateResponse(prefix=prefix, deleted_count=count)

    except Exception as e:
        logger.warning(
            "Frontend cache prefix invalidation failed",
            extra={
                "prefix": prefix,
                "user_id": user_id,
                "error": str(e),
            },
        )
        # Return 0 on error (graceful degradation)
        return CacheInvalidateResponse(prefix=prefix, deleted_count=0)


@frontend_cache_router.delete("/{key:path}", response_model=CacheResponse)
async def delete_cached_value(
    key: str,
    cache: CacheService = Depends(get_cache),
    user: dict[str, Any] = Depends(get_current_user),
) -> CacheResponse:
    """
    Delete cached value for frontend.

    Args:
        key: Cache key (will be prefixed with user ID)
        cache: CacheService dependency
        user: Authenticated user

    Returns:
        CacheResponse with success status
    """
    start_time = time.perf_counter()
    user_id = user.get("user_id", user.get("sub", "anonymous"))
    full_key = _make_user_cache_key(user_id, key)

    # Increment DELETE counter
    frontend_cache_delete_total.inc()

    try:
        await cache.adelete(full_key)

        # Record latency
        duration = time.perf_counter() - start_time
        frontend_cache_latency_seconds.labels(operation="delete").observe(duration)

        logger.debug(
            "Frontend cache DELETE",
            extra={
                "cache_key": key,
                "user_id": user_id,
                "duration_ms": duration * 1000,
            },
        )

        return CacheResponse(key=key, success=True)

    except Exception as e:
        # Record latency even on error
        duration = time.perf_counter() - start_time
        frontend_cache_latency_seconds.labels(operation="delete").observe(duration)

        logger.warning(
            "Frontend cache DELETE failed",
            extra={
                "cache_key": key,
                "user_id": user_id,
                "error": str(e),
                "duration_ms": duration * 1000,
            },
        )
        # Return success even on error (idempotent delete)
        return CacheResponse(key=key, success=True)
