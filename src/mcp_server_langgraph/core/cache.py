"""
Multi-layer caching system for MCP server.

Provides:
- L1: In-memory LRU cache (< 10ms, per-instance)
- L2: Redis distributed cache (< 50ms, shared)
- L3: Provider-native caching (Anthropic, Gemini prompt caching)

Features:
- Automatic TTL and eviction
- Cache stampede prevention
- Metrics and observability
- Tiered cache promotion/demotion

See ADR-0028 for design rationale.
"""

import asyncio
import functools
import hashlib
import pickle
from typing import Any, Callable, Dict, Optional, ParamSpec, TypeVar, cast

import redis
from cachetools import TTLCache

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.observability.telemetry import logger, tracer

P = ParamSpec("P")
T = TypeVar("T")

# Cache TTL configurations (seconds)
CACHE_TTLS = {
    "auth_permission": 300,  # 5 minutes - permissions don't change frequently
    "user_profile": 900,  # 15 minutes - profiles update infrequently
    "llm_response": 3600,  # 1 hour - deterministic responses
    "embedding": 86400,  # 24 hours - embeddings are deterministic
    "prometheus_query": 60,  # 1 minute - metrics change frequently
    "knowledge_base": 1800,  # 30 minutes - search index updates periodically
    "feature_flag": 60,  # 1 minute - fast rollout needed
}


class CacheLayer:
    """Enum for cache layers"""

    L1 = "l1"  # In-memory LRU
    L2 = "l2"  # Redis distributed
    L3 = "l3"  # Provider-native


class CacheService:
    """
    Unified caching service with L1 + L2 layers.

    Usage:
        cache = CacheService()

        # Set value
        cache.set("user:profile:123", user_data, ttl=900)

        # Get value (tries L1 → L2 → None)
        user_data = cache.get("user:profile:123")

        # Delete value
        cache.delete("user:profile:123")

        # Clear all caches
        cache.clear()
    """

    def __init__(
        self,
        l1_maxsize: int = 1000,
        l1_ttl: int = 60,
        redis_url: Optional[str] = None,
        redis_db: int = 2,
    ):
        """
        Initialize cache service.

        Args:
            l1_maxsize: Max entries in L1 cache
            l1_ttl: Default TTL for L1 cache in seconds
            redis_url: Redis connection URL
            redis_db: Redis database number (default: 2 for cache)
        """
        # L1: In-memory cache (per-instance)
        self.l1_cache = TTLCache(maxsize=l1_maxsize, ttl=l1_ttl)
        self.l1_maxsize = l1_maxsize
        self.l1_ttl = l1_ttl

        # L2: Redis cache (shared across instances)
        redis_host = getattr(settings, "redis_host", "localhost")
        redis_port = getattr(settings, "redis_port", 6379)

        try:
            self.redis = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=False,  # Keep binary for pickle
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            # Test connection
            self.redis.ping()
            self.redis_available = True
            logger.info(
                "Redis cache initialized",
                extra={"host": redis_host, "port": redis_port, "db": redis_db},
            )
        except Exception as e:
            logger.warning(
                f"Redis cache unavailable, L2 cache disabled: {e}",
                extra={"host": redis_host, "port": redis_port},
            )
            self.redis = None  # type: ignore[assignment]
            self.redis_available = False

        # Cache stampede prevention locks
        self._refresh_locks: Dict[str, asyncio.Lock] = {}

        # Statistics
        self.stats = {
            "l1_hits": 0,
            "l1_misses": 0,
            "l2_hits": 0,
            "l2_misses": 0,
            "sets": 0,
            "deletes": 0,
        }

    def get(self, key: str, level: str = CacheLayer.L2) -> Optional[Any]:
        """
        Get value from cache (L1 → L2 → None).

        Args:
            key: Cache key
            level: Cache level to search (l1 or l2)

        Returns:
            Cached value or None if not found
        """
        # Try L1 first
        if level in (CacheLayer.L1, CacheLayer.L2) and key in self.l1_cache:
            self.stats["l1_hits"] += 1
            logger.debug(f"L1 cache hit: {key}")

            # Emit metric
            self._emit_cache_hit_metric(CacheLayer.L1, key)

            return self.l1_cache[key]

        self.stats["l1_misses"] += 1

        # Try L2 if enabled
        if level == CacheLayer.L2 and self.redis_available:
            try:
                data = self.redis.get(key)
                if data:
                    value = pickle.loads(cast(bytes, data))  # nosec B301 - Internal cache data only, not user-provided

                    # Promote to L1
                    self.l1_cache[key] = value

                    self.stats["l2_hits"] += 1
                    logger.debug(f"L2 cache hit: {key}")

                    # Emit metric
                    self._emit_cache_hit_metric(CacheLayer.L2, key)

                    return value
            except Exception as e:
                logger.warning(f"L2 cache get failed: {e}", extra={"key": key})

        self.stats["l2_misses"] += 1

        # Emit cache miss metric
        self._emit_cache_miss_metric(level, key)

        return None

    def set(  # type: ignore[no-untyped-def]
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        level: str = CacheLayer.L2,
    ):
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (default: from cache type)
            level: Cache level (l1, l2)
        """
        # Use default TTL for cache type
        if ttl is None:
            ttl = self._get_ttl_from_key(key)

        # Set in L1
        if level in (CacheLayer.L1, CacheLayer.L2):
            self.l1_cache[key] = value

        # Set in L2
        if level == CacheLayer.L2 and self.redis_available:
            try:
                self.redis.setex(key, ttl, pickle.dumps(value))
                logger.debug(f"L2 cache set: {key} (TTL: {ttl}s)")
            except Exception as e:
                logger.warning(f"L2 cache set failed: {e}", extra={"key": key})

        self.stats["sets"] += 1

        # Emit metric
        self._emit_cache_set_metric(level, key)

    def delete(self, key: str) -> None:
        """
        Delete from all cache levels.

        Args:
            key: Cache key to delete
        """
        # Delete from L1
        self.l1_cache.pop(key, None)

        # Delete from L2
        if self.redis_available:
            try:
                self.redis.delete(key)
            except Exception as e:
                logger.warning(f"L2 cache delete failed: {e}")

        self.stats["deletes"] += 1

    def clear(self, pattern: Optional[str] = None) -> None:
        """
        Clear cache (all or by pattern).

        Args:
            pattern: Redis key pattern (e.g., "user:*") or None for all
        """
        # Clear L1
        self.l1_cache.clear()

        # Clear L2
        if self.redis_available:
            try:
                if pattern:
                    keys = self.redis.keys(pattern)
                    if keys:
                        self.redis.delete(*keys)  # type: ignore[misc]
                        logger.info(f"Cleared L2 cache by pattern: {pattern} ({len(cast(list[Any], keys))} keys)")
                else:
                    self.redis.flushdb()
                    logger.info("Cleared all L2 cache")
            except Exception as e:
                logger.warning(f"L2 cache clear failed: {e}")

    async def get_with_lock(
        self,
        key: str,
        fetcher: Callable,  # type: ignore[type-arg]
        ttl: Optional[int] = None,
    ) -> Any:
        """
        Get from cache or fetch with lock (prevents cache stampede).

        Args:
            key: Cache key
            fetcher: Async function to fetch data if cache miss
            ttl: Time-to-live in seconds

        Returns:
            Cached or fetched value
        """
        # Try cache first
        if cached := self.get(key):
            return cached

        # Acquire lock for this key
        if key not in self._refresh_locks:
            self._refresh_locks[key] = asyncio.Lock()

        async with self._refresh_locks[key]:
            # Double-check cache (another request may have filled it)
            if cached := self.get(key):
                return cached

            # Fetch and cache
            value = await fetcher() if asyncio.iscoroutinefunction(fetcher) else fetcher()
            self.set(key, value, ttl)

            return value

    def _get_ttl_from_key(self, key: str) -> int:
        """
        Determine TTL from cache key prefix.

        Args:
            key: Cache key (format: "type:...")

        Returns:
            TTL in seconds
        """
        # Extract cache type from key prefix
        cache_type = key.split(":")[0] if ":" in key else "default"

        return CACHE_TTLS.get(cache_type, 300)  # Default 5 minutes

    def _emit_cache_hit_metric(self, layer: str, key: str) -> None:
        """Emit cache hit metric"""
        try:
            from mcp_server_langgraph.observability.telemetry import config

            cache_type = key.split(":")[0] if ":" in key else "unknown"

            # Create metric if doesn't exist
            if not hasattr(config, "cache_hits_counter"):
                config.cache_hits_counter = config.meter.create_counter(
                    name="cache.hits",
                    description="Total cache hits",
                    unit="1",
                )

            config.cache_hits_counter.add(
                1,
                attributes={"layer": layer, "cache_type": cache_type},
            )
        except Exception:
            pass  # Don't let metrics failure break caching

    def _emit_cache_miss_metric(self, layer: str, key: str) -> None:
        """Emit cache miss metric"""
        try:
            from mcp_server_langgraph.observability.telemetry import config

            cache_type = key.split(":")[0] if ":" in key else "unknown"

            if not hasattr(config, "cache_misses_counter"):
                config.cache_misses_counter = config.meter.create_counter(
                    name="cache.misses",
                    description="Total cache misses",
                    unit="1",
                )

            config.cache_misses_counter.add(
                1,
                attributes={"layer": layer, "cache_type": cache_type},
            )
        except Exception:
            pass

    def _emit_cache_set_metric(self, layer: str, key: str) -> None:
        """Emit cache set metric"""
        try:
            from mcp_server_langgraph.observability.telemetry import config

            cache_type = key.split(":")[0] if ":" in key else "unknown"

            if not hasattr(config, "cache_sets_counter"):
                config.cache_sets_counter = config.meter.create_counter(
                    name="cache.sets",
                    description="Total cache sets",
                    unit="1",
                )

            config.cache_sets_counter.add(
                1,
                attributes={"layer": layer, "cache_type": cache_type},
            )
        except Exception:
            pass

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        hit_rate_l1 = (
            self.stats["l1_hits"] / (self.stats["l1_hits"] + self.stats["l1_misses"])
            if (self.stats["l1_hits"] + self.stats["l1_misses"]) > 0
            else 0.0
        )

        hit_rate_l2 = (
            self.stats["l2_hits"] / (self.stats["l2_hits"] + self.stats["l2_misses"])
            if (self.stats["l2_hits"] + self.stats["l2_misses"]) > 0
            else 0.0
        )

        return {
            "l1": {
                "hits": self.stats["l1_hits"],
                "misses": self.stats["l1_misses"],
                "hit_rate": hit_rate_l1,
                "size": len(self.l1_cache),
                "max_size": self.l1_maxsize,
            },
            "l2": {
                "hits": self.stats["l2_hits"],
                "misses": self.stats["l2_misses"],
                "hit_rate": hit_rate_l2,
                "available": self.redis_available,
            },
            "total": {
                "sets": self.stats["sets"],
                "deletes": self.stats["deletes"],
            },
        }


# Global cache instance
_cache_service: Optional[CacheService] = None


def get_cache() -> CacheService:
    """Get global cache service (singleton)"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService(
            l1_maxsize=getattr(settings, "l1_cache_size", 1000),
            l1_ttl=getattr(settings, "l1_cache_ttl", 60),
            redis_db=getattr(settings, "redis_cache_db", 2),
        )
    return _cache_service


def cached(
    key_prefix: str,
    ttl: Optional[int] = None,
    level: str = CacheLayer.L2,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for caching async function results.

    Args:
        key_prefix: Prefix for cache key
        ttl: Time-to-live in seconds (default: auto from key_prefix)
        level: Cache level (l1 or l2)

    Usage:
        @cached(key_prefix="user:profile", ttl=900)
        async def get_user_profile(user_id: str) -> dict[str, Any]:
            return await db.get_user(user_id)

        # Auto TTL from key prefix
        @cached(key_prefix="auth_permission")  # Uses 300s TTL
        async def check_permission(user: str, resource: str) -> bool:
            return await openfga.check(user, resource)
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            """Async wrapper with caching"""
            cache = get_cache()

            # Generate cache key
            key_parts = [key_prefix]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            key = ":".join(key_parts)

            # Hash if too long
            if len(key) > 200:
                key_hash = hashlib.md5(key.encode(), usedforsecurity=False).hexdigest()  # nosec B324
                key = f"{key_prefix}:hash:{key_hash}"

            with tracer.start_as_current_span(
                f"cache.{key_prefix}",
                attributes={"cache.key": key, "cache.level": level},
            ) as span:
                # Try cache
                if cached_value := cache.get(key, level=level):
                    span.set_attribute("cache.hit", True)
                    return cached_value  # type: ignore[no-any-return]

                span.set_attribute("cache.hit", False)

                # Cache miss: call function
                result = await func(*args, **kwargs)  # type: ignore[misc]

                # Store in cache
                cache.set(key, result, ttl=ttl, level=level)

                return result  # type: ignore[no-any-return]

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            """Sync wrapper with caching"""
            cache = get_cache()

            # Generate cache key
            key_parts = [key_prefix]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            key = ":".join(key_parts)

            if len(key) > 200:
                key_hash = hashlib.md5(key.encode(), usedforsecurity=False).hexdigest()  # nosec B324
                key = f"{key_prefix}:hash:{key_hash}"

            # Try cache
            if cached_value := cache.get(key, level=level):
                return cached_value  # type: ignore[no-any-return]

            # Cache miss: call function
            result = func(*args, **kwargs)

            # Store in cache
            cache.set(key, result, ttl=ttl, level=level)

            return result

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]  # Complex decorator typing
        else:
            return sync_wrapper

    return decorator


def cache_invalidate(key_pattern: str) -> None:
    """
    Invalidate cache entries matching pattern.

    Args:
        key_pattern: Pattern to match (e.g., "user:123:*" for all user 123 caches)

    Usage:
        # Invalidate all caches for a user
        cache_invalidate("user:123:*")

        # Invalidate all auth caches
        cache_invalidate("auth:*")
    """
    cache = get_cache()
    cache.clear(pattern=key_pattern)
    logger.info(f"Cache invalidated: {key_pattern}")


# Anthropic-specific prompt caching (L3)
def create_anthropic_cached_message(system_prompt: str, messages: list) -> dict[str, Any]:  # type: ignore[type-arg]
    """
    Create Anthropic message with prompt caching.

    Args:
        system_prompt: System prompt to cache
        messages: List of messages

    Returns:
        Message dict with cache_control
    """
    return {
        "model": "claude-3-5-sonnet-20241022",
        "system": [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},  # Cache this!
            }
        ],
        "messages": messages,
    }


# Helper function for cache key generation
def generate_cache_key(*parts: Any, prefix: str = "", version: str = "v1") -> str:
    """
    Generate standardized cache key.

    Args:
        *parts: Key components
        prefix: Key prefix (cache type)
        version: Cache version (for invalidation)

    Returns:
        Cache key string

    Usage:
        key = generate_cache_key("user_123", "profile", prefix="user", version="v1")
        # Returns: "user:user_123:profile:v1"
    """
    key_parts = [prefix] if prefix else []
    key_parts.extend(str(part) for part in parts)
    key_parts.append(version)

    key = ":".join(key_parts)

    # Hash if too long
    if len(key) > 200:
        key_hash = hashlib.md5(key.encode(), usedforsecurity=False).hexdigest()  # nosec B324
        key = f"{prefix}:hash:{key_hash}:{version}"

    return key
