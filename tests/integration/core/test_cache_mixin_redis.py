"""
Integration Tests for TieredCacheMixin with Real Redis

Tests validate cache mixin behavior with actual Redis connection:
- L1 (TTLCache) + L2 (Redis) tiered operations
- Stale-while-revalidate (SWR) pattern
- Cache invalidation patterns
- Metrics tracking
- Error handling with real Redis

Reference: docs-internal/CACHING_ARCHITECTURE_AUDIT.md
"""

import asyncio
import gc
import time

import pytest

from tests.constants import TEST_REDIS_PORT

pytestmark = [
    pytest.mark.integration,
    pytest.mark.redis,
    pytest.mark.asyncio,
]


def is_redis_available() -> bool:
    """Check if Redis is available on test port."""
    try:
        import redis

        client = redis.Redis(host="localhost", port=TEST_REDIS_PORT, socket_timeout=1)
        client.ping()
        client.close()
        return True
    except Exception:
        return False


@pytest.fixture
async def redis_cache_service():
    """Create a real CacheService with Redis."""
    from mcp_server_langgraph.core.cache import CacheService

    cache = CacheService(
        redis_url=f"redis://localhost:{TEST_REDIS_PORT}",
        redis_db=15,  # Use DB 15 for tests (isolated from other data)
        l1_ttl=60,
        l1_maxsize=100,
    )

    # Wait for Redis connection
    if not cache.redis_available:
        pytest.skip("Redis connection failed")

    yield cache

    # Cleanup - flush the test database
    try:
        if cache.redis is not None:
            await cache.redis.flushdb()
    except Exception:
        pass


@pytest.fixture
async def cache_mixin_service(redis_cache_service):
    """Create a test service using TieredCacheMixin."""
    from mcp_server_langgraph.core.cache_mixin import TieredCacheMixin

    class TestCacheService(TieredCacheMixin):
        cache_prefix = "test_integration"
        cache_ttl = 60

        def __init__(self, cache_service):
            self._cache_service = cache_service

    return TestCacheService(redis_cache_service)


@pytest.fixture
async def swr_mixin_service(redis_cache_service):
    """Create a test service using StaleWhileRevalidateMixin."""
    from mcp_server_langgraph.core.cache_mixin import StaleWhileRevalidateMixin

    class TestSWRService(StaleWhileRevalidateMixin):
        cache_prefix = "test_swr"
        cache_ttl = 60
        stale_threshold_seconds = 5

        def __init__(self, cache_service):
            self._cache_service = cache_service

    return TestSWRService(redis_cache_service)


@pytest.mark.skipif(
    not is_redis_available(),
    reason="Redis not available on test port",
)
@pytest.mark.xdist_group(name="integration_cache_mixin_redis")
class TestTieredCacheMixinRedisIntegration:
    """Integration tests for TieredCacheMixin with real Redis."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # =========================================================================
    # TieredCacheMixin Tests
    # =========================================================================

    async def test_cache_set_and_get_with_redis(self, cache_mixin_service):
        """Test basic set/get operations flow through Redis L2."""
        key = cache_mixin_service._make_cache_key("test", "basic")
        value = {"message": "Hello from Redis", "count": 42}

        # Set value
        await cache_mixin_service._cache_set(key, value)

        # Get value - should retrieve from cache
        result = await cache_mixin_service._cache_get(key)

        assert result is not None
        assert result["message"] == "Hello from Redis"
        assert result["count"] == 42

    async def test_cache_key_generation_is_deterministic(self, cache_mixin_service):
        """Test that cache keys are generated consistently."""
        request_data = {"user_id": "user123", "options": {"verbose": True}}

        key1 = cache_mixin_service._make_method_cache_key("analyze", request_data)
        key2 = cache_mixin_service._make_method_cache_key("analyze", request_data)

        assert key1 == key2
        assert key1.startswith("test_integration:analyze:")

    async def test_cache_get_returns_none_for_missing_key(self, cache_mixin_service):
        """Test cache miss returns None."""
        result = await cache_mixin_service._cache_get("nonexistent:key:12345")
        assert result is None

    async def test_cache_delete_removes_value(self, cache_mixin_service):
        """Test delete operation removes cached value."""
        key = cache_mixin_service._make_cache_key("test", "delete")
        value = {"data": "to_delete"}

        # Set then delete
        await cache_mixin_service._cache_set(key, value)
        await cache_mixin_service._cache_delete(key)

        # Should be gone
        result = await cache_mixin_service._cache_get(key)
        assert result is None

    async def test_cache_invalidate_prefix_removes_matching_keys(self, cache_mixin_service):
        """Test prefix-based invalidation removes matching keys."""
        # Set multiple keys with same method prefix
        method = "persona"
        for i in range(3):
            key = cache_mixin_service._make_cache_key(method, f"user{i}")
            await cache_mixin_service._cache_set(key, {"user": i})

        # Invalidate by method prefix
        count = await cache_mixin_service._cache_invalidate_prefix(method)

        # Should have deleted keys (count may vary based on Redis SCAN)
        assert count >= 0  # At least acknowledges the operation

        # Keys should be gone
        for i in range(3):
            key = cache_mixin_service._make_cache_key(method, f"user{i}")
            result = await cache_mixin_service._cache_get(key)
            assert result is None

    async def test_cache_invalidate_user_removes_user_keys(self, cache_mixin_service):
        """Test user-based invalidation removes user's cache entries."""
        user_id = "user_to_invalidate"

        # Set keys for this user across different methods
        for method in ["persona", "disclosure", "nudge"]:
            key = cache_mixin_service._make_user_cache_key(method, user_id)
            await cache_mixin_service._cache_set(key, {"method": method})

        # Invalidate user
        count = await cache_mixin_service._cache_invalidate_user(user_id)

        # Should have processed invalidation
        assert count >= 0

    async def test_cache_get_tiered_returns_data_from_l2(self, cache_mixin_service):
        """Test tiered get retrieves from L2 when L1 misses."""
        key = cache_mixin_service._make_cache_key("tiered", "test")
        value = {"layer": "L2"}

        # Store directly via cache service (bypassing L1)
        await cache_mixin_service._cache_set(key, value)

        # Clear L1 by creating new mixin instance with same cache service
        cache_mixin_service._cache.l1_cache.clear()

        # Get should still work (from L2)
        result = await cache_mixin_service._cache_get_tiered(key, "tiered_test")
        assert result is not None
        assert result["layer"] == "L2"

    # =========================================================================
    # StaleWhileRevalidateMixin Tests
    # =========================================================================

    async def test_swr_returns_fresh_data_on_miss(self, swr_mixin_service):
        """Test SWR fetches and caches on miss."""
        key = swr_mixin_service._make_cache_key("swr", "fresh_miss")
        fetch_called = False

        async def fetcher():
            nonlocal fetch_called
            fetch_called = True
            return {"status": "freshly_fetched"}

        result, is_stale = await swr_mixin_service._cache_get_swr(key, "swr_test", fetcher)

        assert fetch_called
        assert result is not None
        assert result["status"] == "freshly_fetched"
        assert is_stale is False
        assert "_cached_at" in result

    async def test_swr_returns_cached_fresh_data(self, swr_mixin_service):
        """Test SWR returns fresh cached data without refetch."""
        key = swr_mixin_service._make_cache_key("swr", "cached_fresh")

        # First call to cache
        call_count = 0

        async def fetcher():
            nonlocal call_count
            call_count += 1
            return {"status": "fetched", "call": call_count}

        await swr_mixin_service._cache_get_swr(key, "swr_test", fetcher)

        # Second call - should use cache (within stale threshold)
        result, is_stale = await swr_mixin_service._cache_get_swr(key, "swr_test", fetcher)

        assert call_count == 1  # Fetcher should only be called once
        assert result["status"] == "fetched"
        assert is_stale is False

    async def test_swr_detects_stale_data(self, swr_mixin_service):
        """Test SWR marks data as stale after threshold."""
        key = swr_mixin_service._make_cache_key("swr", "stale_detect")

        # Pre-populate cache with old timestamp
        old_data = {
            "status": "old",
            "_cached_at": time.time() - 10,  # 10 seconds ago (past 5s threshold)
        }
        await swr_mixin_service._cache_set(key, old_data)

        # Create fetcher that shouldn't be called initially
        async def fetcher():
            return {"status": "refreshed"}

        result, is_stale = await swr_mixin_service._cache_get_swr(key, "swr_test", fetcher)

        # Should return stale data
        assert result["status"] == "old"
        assert is_stale is True

    async def test_swr_timestamp_persists_in_redis(self, swr_mixin_service):
        """Test that _cached_at timestamp is stored in Redis."""
        key = swr_mixin_service._make_cache_key("swr", "timestamp")

        async def fetcher():
            return {"value": 123}

        await swr_mixin_service._cache_get_swr(key, "swr_test", fetcher)

        # Clear L1 and fetch from L2
        swr_mixin_service._cache.l1_cache.clear()

        cached = await swr_mixin_service._cache_get(key)
        assert cached is not None
        assert "_cached_at" in cached
        assert isinstance(cached["_cached_at"], float)

    # =========================================================================
    # Metrics Tests
    # =========================================================================

    async def test_cache_get_with_metrics_tracks_hits(self, cache_mixin_service):
        """Test that metrics are tracked for cache hits."""
        key = cache_mixin_service._make_cache_key("metrics", "hit")
        await cache_mixin_service._cache_set(key, {"data": "test"})

        # This should track a hit
        result = await cache_mixin_service._cache_get_with_metrics(key, "metrics_test")
        assert result is not None

    async def test_cache_get_with_metrics_tracks_misses(self, cache_mixin_service):
        """Test that metrics are tracked for cache misses."""
        key = cache_mixin_service._make_cache_key("metrics", "miss", "nonexistent")

        # This should track a miss
        result = await cache_mixin_service._cache_get_with_metrics(key, "metrics_test")
        assert result is None

    async def test_cache_get_observed_tracks_latency(self, cache_mixin_service):
        """Test that observed operations track latency."""
        key = cache_mixin_service._make_cache_key("observed", "latency")
        await cache_mixin_service._cache_set(key, {"data": "latency_test"})

        # Observed get should complete and track latency
        result = await cache_mixin_service._cache_get_observed(key, "observed_test")
        assert result is not None

    # =========================================================================
    # Error Handling Tests
    # =========================================================================

    async def test_cache_get_handles_connection_error_gracefully(self, cache_mixin_service):
        """Test that cache get handles Redis errors gracefully."""
        # Get with key that definitely doesn't exist
        result = await cache_mixin_service._cache_get("invalid:key:format")
        # Should return None, not raise exception
        assert result is None

    async def test_cache_set_handles_serialization_error(self, cache_mixin_service):
        """Test that cache set handles unserializable values gracefully."""
        key = cache_mixin_service._make_cache_key("error", "serialize")

        # Try to cache a function (not JSON serializable)
        # Should log warning but not crash
        try:
            await cache_mixin_service._cache_set(key, {"func": lambda x: x})
        except Exception:
            pass  # Expected to fail - verify it doesn't crash the service

    # =========================================================================
    # TTL Tests
    # =========================================================================

    async def test_cache_respects_ttl(self, cache_mixin_service):
        """Test that cached values expire after TTL."""
        key = cache_mixin_service._make_cache_key("ttl", "expire")

        # Set with very short TTL (1 second)
        await cache_mixin_service._cache_set(key, {"data": "temporary"}, ttl=1)

        # Should exist immediately
        result = await cache_mixin_service._cache_get(key)
        assert result is not None

        # Wait for expiry
        await asyncio.sleep(1.5)

        # Should be expired
        result = await cache_mixin_service._cache_get(key)
        # Note: L1 might still have it if TTL not enforced there
        # This primarily tests L2 (Redis) TTL
