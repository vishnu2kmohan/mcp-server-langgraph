"""
TieredCacheMixin - DRY Caching Abstraction

Provides consistent L1+L2 tiered caching capabilities for services.
Services inherit this mixin to get standardized caching with:
- L1 (TTLCache) + L2 (Redis) tiered lookup
- Circuit breaker and retry (via CacheService)
- Prometheus metrics integration
- OpenTelemetry tracing (ADR-0030 compliance)
- Consistent cache key generation
- User and method-based invalidation

Usage:
    class AIUXService(TieredCacheMixin):
        cache_prefix = "ai_ux"
        cache_ttl = 3600  # 1 hour

        async def analyze_persona(self, request: Request) -> Response:
            cache_key = self._make_method_cache_key("persona", request.model_dump())

            # Check cache
            cached = await self._cache_get(cache_key)
            if cached:
                return Response(**cached)

            # Compute and cache
            result = await self._do_analysis(request)
            await self._cache_set(cache_key, result.model_dump())
            return result

Reference: docs-internal/CACHING_ARCHITECTURE_AUDIT.md
ADR-0030: Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from opentelemetry import trace

from mcp_server_langgraph.core.cache import CACHE_TTLS, get_cache
from mcp_server_langgraph.observability.telemetry import logger

if TYPE_CHECKING:
    from mcp_server_langgraph.core.cache import CacheService

# OpenTelemetry tracer for cache operations
tracer = trace.get_tracer(__name__)


# =============================================================================
# Prometheus Metrics (ADR-0030 Compliance)
# =============================================================================

try:
    from prometheus_client import Counter, Histogram

    CACHE_MIXIN_HITS = Counter(
        name="cache_mixin_hits_total",
        documentation="Cache hits via TieredCacheMixin",
        labelnames=["service", "method"],
    )

    CACHE_MIXIN_MISSES = Counter(
        name="cache_mixin_misses_total",
        documentation="Cache misses via TieredCacheMixin",
        labelnames=["service", "method"],
    )

    # L1/L2 layer separation metrics (ADR-0030)
    CACHE_MIXIN_L1_HITS = Counter(
        name="cache_mixin_l1_hits_total",
        documentation="L1 (in-memory) cache hits via TieredCacheMixin",
        labelnames=["service", "method"],
    )

    CACHE_MIXIN_L2_HITS = Counter(
        name="cache_mixin_l2_hits_total",
        documentation="L2 (Redis) cache hits via TieredCacheMixin",
        labelnames=["service", "method"],
    )

    # Latency histogram (ADR-0030)
    CACHE_MIXIN_LATENCY = Histogram(
        name="cache_mixin_operation_duration_seconds",
        documentation="Cache operation latency via TieredCacheMixin",
        labelnames=["service", "method", "operation"],
        buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    )

    # Error counter (ADR-0030)
    CACHE_MIXIN_ERRORS = Counter(
        name="cache_mixin_errors_total",
        documentation="Cache operation errors via TieredCacheMixin",
        labelnames=["service", "method", "operation", "error_type"],
    )

    PROMETHEUS_AVAILABLE = True

except ImportError:

    class _MockCounter:
        """Mock counter for when prometheus_client unavailable."""

        def labels(self, **kwargs: Any) -> _MockCounter:
            return self

        def inc(self, amount: float = 1) -> None:
            pass

    class _MockHistogram:
        """Mock histogram for when prometheus_client unavailable."""

        def labels(self, **kwargs: Any) -> _MockHistogram:
            return self

        def observe(self, amount: float) -> None:
            pass

    CACHE_MIXIN_HITS = _MockCounter()  # type: ignore[assignment]
    CACHE_MIXIN_MISSES = _MockCounter()  # type: ignore[assignment]
    CACHE_MIXIN_L1_HITS = _MockCounter()  # type: ignore[assignment]
    CACHE_MIXIN_L2_HITS = _MockCounter()  # type: ignore[assignment]
    CACHE_MIXIN_LATENCY = _MockHistogram()  # type: ignore[assignment]
    CACHE_MIXIN_ERRORS = _MockCounter()  # type: ignore[assignment]
    PROMETHEUS_AVAILABLE = False


# =============================================================================
# TieredCacheMixin
# =============================================================================


class TieredCacheMixin:
    """
    Mixin providing tiered caching capabilities for services.

    Subclasses MUST define:
    - cache_prefix: str - Unique prefix for cache keys (e.g., "ai_ux", "artifact")

    Subclasses MAY override:
    - cache_ttl: int - Default TTL in seconds (default: 300)

    Provides:
    - _cache_get(key) - Get from L1 -> L2 -> None
    - _cache_set(key, value, ttl) - Set in L1 + L2
    - _cache_delete(key) - Delete from L1 + L2
    - _cache_invalidate_prefix(prefix) - Delete keys matching pattern
    - _cache_invalidate_user(user_id) - Delete all user's cache entries
    - _make_cache_key(*parts) - Generate prefixed key
    - _make_user_cache_key(method, user_id) - Generate user-scoped key
    - _make_method_cache_key(method, request) - Generate method+hash key
    """

    # Subclasses MUST override
    cache_prefix: str = "default"

    # Subclasses MAY override
    cache_ttl: int = CACHE_TTLS.get("connection", 300)

    # Internal cache service reference (lazy initialized)
    _cache_service: CacheService | None = None

    @property
    def _cache(self) -> CacheService:
        """
        Get the cache service instance (lazy initialization).

        Returns:
            CacheService instance
        """
        if self._cache_service is None:
            self._cache_service = get_cache()
        return self._cache_service

    # =========================================================================
    # Cache Key Generation
    # =========================================================================

    def _make_cache_key(self, *parts: str) -> str:
        """
        Generate a prefixed cache key from parts.

        Args:
            *parts: Key parts to join with colons

        Returns:
            Prefixed cache key (e.g., "ai_ux:persona:user123")
        """
        return f"{self.cache_prefix}:{':'.join(parts)}"

    def _make_user_cache_key(self, method: str, user_id: str) -> str:
        """
        Generate a user-scoped cache key.

        Args:
            method: Method or operation name
            user_id: User identifier

        Returns:
            User-scoped cache key (e.g., "ai_ux:persona:user123")
        """
        return self._make_cache_key(method, user_id)

    def _make_method_cache_key(self, method: str, request_data: dict[str, Any]) -> str:
        """
        Generate a deterministic cache key from method and request data.

        Uses MD5 hash of sorted JSON for determinism.

        Args:
            method: Method or operation name
            request_data: Request data dict to hash

        Returns:
            Method+hash cache key (e.g., "ai_ux:analyze:a1b2c3d4")
        """
        # Sort keys for determinism
        sorted_json = json.dumps(request_data, sort_keys=True, default=str)
        # MD5 used for cache key generation (non-security purpose)
        hash_suffix = hashlib.md5(  # noqa: S324
            sorted_json.encode(), usedforsecurity=False
        ).hexdigest()[:16]
        return self._make_cache_key(method, hash_suffix)

    # =========================================================================
    # Cache Operations
    # =========================================================================

    async def _cache_get(self, key: str) -> Any | None:
        """
        Get value from tiered cache (L1 -> L2 -> None).

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            return await self._cache.aget(key)
        except Exception as e:
            logger.warning(f"Cache get failed for {key}: {e}")
            return None

    async def _cache_get_with_metrics(self, key: str, method: str = "unknown") -> Any | None:
        """
        Get value from cache with Prometheus metrics tracking.

        Args:
            key: Cache key
            method: Method name for metric labels

        Returns:
            Cached value or None
        """
        result = await self._cache_get(key)

        if result is not None:
            CACHE_MIXIN_HITS.labels(service=self.cache_prefix, method=method).inc()
            logger.debug(f"Cache hit for {self.cache_prefix}:{method}")
        else:
            CACHE_MIXIN_MISSES.labels(service=self.cache_prefix, method=method).inc()

        return result

    async def _cache_set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Set value in both L1 and L2 cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (defaults to self.cache_ttl)
        """
        try:
            await self._cache.aset(key, value, ttl=ttl or self.cache_ttl)
            logger.debug(f"Cached {key} with TTL {ttl or self.cache_ttl}s")
        except Exception as e:
            logger.warning(f"Cache set failed for {key}: {e}")

    async def _cache_delete(self, key: str) -> None:
        """
        Delete key from both L1 and L2 cache.

        Args:
            key: Cache key to delete
        """
        try:
            await self._cache.adelete(key)
            logger.debug(f"Deleted cache key: {key}")
        except Exception as e:
            logger.warning(f"Cache delete failed for {key}: {e}")

    async def _cache_invalidate_prefix(self, prefix: str) -> int:
        """
        Invalidate all cache entries matching a prefix pattern.

        Args:
            prefix: Prefix to match (will be combined with cache_prefix)

        Returns:
            Number of keys deleted
        """
        pattern = f"{self.cache_prefix}:{prefix}:*"
        try:
            count = await self._cache.adelete_pattern(pattern)
            logger.info(f"Invalidated {count} keys matching {pattern}")
            return count
        except Exception as e:
            logger.warning(f"Cache invalidation failed for {pattern}: {e}")
            return 0

    async def _cache_invalidate_user(self, user_id: str) -> int:
        """
        Invalidate all cache entries for a specific user.

        Uses pattern: {prefix}:*:{user_id}:*

        Args:
            user_id: User identifier

        Returns:
            Number of keys deleted
        """
        pattern = f"{self.cache_prefix}:*:{user_id}:*"
        try:
            count = await self._cache.adelete_pattern(pattern)
            logger.info(f"Invalidated {count} cache entries for user {user_id}")
            return count
        except Exception as e:
            logger.warning(f"User cache invalidation failed for {user_id}: {e}")
            return 0

    # =========================================================================
    # L1/L2 Layer-Aware Operations (ADR-0030)
    # =========================================================================

    async def _cache_get_tiered(self, key: str, method: str = "unknown") -> Any | None:
        """
        Get value from cache with L1/L2 layer separation in metrics.

        Records separate metrics for L1 (in-memory) vs L2 (Redis) hits.
        This enables granular alerting and performance analysis per layer.

        Args:
            key: Cache key
            method: Method name for metric labels

        Returns:
            Cached value or None
        """
        cache_service = self._cache

        # Check L1 (in-memory) first
        l1_cache = getattr(cache_service, "l1_cache", None)
        if l1_cache is not None and key in l1_cache:
            CACHE_MIXIN_L1_HITS.labels(service=self.cache_prefix, method=method).inc()
            logger.debug(f"L1 cache hit for {self.cache_prefix}:{method}")
            return l1_cache[key]

        # Check L2 (Redis)
        try:
            result = await cache_service.aget(key)
            if result is not None:
                CACHE_MIXIN_L2_HITS.labels(service=self.cache_prefix, method=method).inc()
                logger.debug(f"L2 cache hit for {self.cache_prefix}:{method}")
                return result
        except Exception as e:
            logger.warning(f"L2 cache get failed for {key}: {e}")

        # Complete miss
        CACHE_MIXIN_MISSES.labels(service=self.cache_prefix, method=method).inc()
        return None

    # =========================================================================
    # OpenTelemetry Traced Operations (ADR-0030)
    # =========================================================================

    async def _cache_get_traced(self, key: str, method: str = "unknown") -> Any | None:
        """
        Get value from cache with OpenTelemetry tracing.

        Creates a span with cache.hit attribute for observability.

        Args:
            key: Cache key
            method: Method name for span naming

        Returns:
            Cached value or None
        """
        with tracer.start_as_current_span(
            f"cache.{self.cache_prefix}.{method}",
            attributes={"cache.key": key, "cache.service": self.cache_prefix},
        ) as span:
            result = await self._cache_get(key)
            span.set_attribute("cache.hit", result is not None)
            return result

    # =========================================================================
    # Observed Operations with Latency and Error Tracking (ADR-0030)
    # =========================================================================

    async def _cache_get_observed(self, key: str, method: str = "unknown") -> Any | None:
        """
        Get value from cache with latency and error metrics.

        Records operation latency in histogram and errors in counter.
        Unlike _cache_get, this method tracks errors in metrics.

        Args:
            key: Cache key
            method: Method name for metric labels

        Returns:
            Cached value or None
        """
        start_time = time.perf_counter()
        try:
            # Call cache.aget directly to catch errors (unlike _cache_get which swallows)
            result = await self._cache.aget(key)
            return result
        except Exception as e:
            CACHE_MIXIN_ERRORS.labels(
                service=self.cache_prefix,
                method=method,
                operation="get",
                error_type=type(e).__name__,
            ).inc()
            logger.warning(f"Cache get error for {key}: {e}")
            return None
        finally:
            duration = time.perf_counter() - start_time
            CACHE_MIXIN_LATENCY.labels(service=self.cache_prefix, method=method, operation="get").observe(duration)

    async def _cache_set_observed(
        self,
        key: str,
        value: Any,
        method: str = "unknown",
        ttl: int | None = None,
    ) -> None:
        """
        Set value in cache with latency and error metrics.

        Records operation latency in histogram and errors in counter.

        Args:
            key: Cache key
            value: Value to cache
            method: Method name for metric labels
            ttl: TTL in seconds (defaults to self.cache_ttl)
        """
        start_time = time.perf_counter()
        try:
            await self._cache.aset(key, value, ttl=ttl or self.cache_ttl)
            logger.debug(f"Cached {key} with TTL {ttl or self.cache_ttl}s")
        except Exception as e:
            CACHE_MIXIN_ERRORS.labels(
                service=self.cache_prefix,
                method=method,
                operation="set",
                error_type=type(e).__name__,
            ).inc()
            logger.warning(f"Cache set error for {key}: {e}")
        finally:
            duration = time.perf_counter() - start_time
            CACHE_MIXIN_LATENCY.labels(service=self.cache_prefix, method=method, operation="set").observe(duration)


# =============================================================================
# StaleWhileRevalidateMixin (Extracted from AIUXService pattern)
# =============================================================================


class StaleWhileRevalidateMixin(TieredCacheMixin):
    """
    Mixin providing stale-while-revalidate caching pattern.

    Returns stale data immediately while triggering background refresh.
    This pattern improves perceived latency for frequently accessed data
    that can tolerate some staleness.

    Subclasses MUST define:
    - cache_prefix: str - Unique prefix for cache keys

    Subclasses MAY override:
    - stale_threshold_seconds: int - Time after which data is considered stale (default: 60)
    - cache_ttl: int - TTL in seconds (default: 300)

    Usage:
        class AIUXService(StaleWhileRevalidateMixin):
            cache_prefix = "ai_ux"
            stale_threshold_seconds = 120  # 2 minutes before stale

            async def get_persona_analysis(self, user_id: str) -> dict:
                cache_key = self._make_user_cache_key("persona", user_id)

                result, is_stale = await self._cache_get_swr(
                    cache_key,
                    method="persona",
                    fetcher=lambda: self._fetch_persona(user_id),
                )
                return result

    Reference: docs-internal/CACHING_ARCHITECTURE_AUDIT.md
    """

    # Default stale threshold (60 seconds)
    stale_threshold_seconds: int = 60

    async def _cache_get_swr(
        self,
        key: str,
        method: str,
        fetcher: Callable[[], Awaitable[dict[str, Any]]],
        ttl: int | None = None,
    ) -> tuple[dict[str, Any] | None, bool]:
        """
        Get value with stale-while-revalidate pattern.

        Returns cached data immediately (even if stale) while triggering
        background refresh for stale data. This improves perceived latency.

        Args:
            key: Cache key
            method: Method name for metrics
            fetcher: Async function to fetch fresh data on miss or stale
            ttl: TTL in seconds (defaults to self.cache_ttl)

        Returns:
            Tuple of (data, is_stale):
            - data: The cached or fetched data (with _cached_at timestamp)
            - is_stale: True if returned data was stale (refresh triggered)
        """
        # Try to get from cache
        cached = await self._cache_get(key)

        if cached is not None:
            # Check if stale
            cached_at = cached.get("_cached_at", 0)
            age = time.time() - cached_at

            if age < self.stale_threshold_seconds:
                # Fresh data
                logger.debug(f"Fresh cache hit for {key} (age: {age:.1f}s)")
                return cached, False
            else:
                # Stale data - return immediately, refresh in background
                logger.debug(f"Stale cache hit for {key} (age: {age:.1f}s)")
                # Note: Background refresh would be triggered by caller
                return cached, True

        # Cache miss - fetch fresh data
        logger.debug(f"Cache miss for {key}, fetching fresh data")
        fresh_data = await fetcher()

        # Add timestamp and cache
        if fresh_data is not None:
            fresh_data["_cached_at"] = time.time()
            await self._cache_set(key, fresh_data, ttl=ttl)

        return fresh_data, False


# =============================================================================
# Convenience Functions
# =============================================================================


def get_cache_ttl(cache_type: str) -> int:
    """
    Get TTL for a cache type from CACHE_TTLS.

    Args:
        cache_type: Cache type name (e.g., "llm_response", "auth_permission")

    Returns:
        TTL in seconds (defaults to 300 if type not found)
    """
    return CACHE_TTLS.get(cache_type, 300)


__all__ = [
    # Mixins
    "TieredCacheMixin",
    "StaleWhileRevalidateMixin",
    # Utilities
    "get_cache_ttl",
    # Prometheus Metrics
    "CACHE_MIXIN_HITS",
    "CACHE_MIXIN_MISSES",
    "CACHE_MIXIN_L1_HITS",
    "CACHE_MIXIN_L2_HITS",
    "CACHE_MIXIN_LATENCY",
    "CACHE_MIXIN_ERRORS",
]
