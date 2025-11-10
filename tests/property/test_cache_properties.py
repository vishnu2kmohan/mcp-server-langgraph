"""
Property-based tests for cache module using Hypothesis.

Tests cache invariants and edge cases:
- Cache get/set roundtrip preservation
- TTL expiration behavior
- Key generation consistency
- Multi-layer cache promotion/demotion
- Concurrent access safety
"""

import asyncio
import gc
import time
from unittest.mock import Mock, patch

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from mcp_server_langgraph.core.cache import CACHE_TTLS, CacheLayer, CacheService, cached, generate_cache_key

pytestmark = [pytest.mark.unit, pytest.mark.property]


@pytest.mark.xdist_group(name="property_cache_properties_tests")
class TestCacheValuePreservation:
    """Test that cache preserves values correctly"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @given(value=st.integers())
    @settings(max_examples=50, deadline=2000)
    def test_integer_values_preserved(self, value):
        """Property: Integer values are preserved through cache"""
        cache = CacheService(l1_maxsize=100, l1_ttl=60)
        cache.set(f"int:{value}", value)
        retrieved = cache.get(f"int:{value}")
        assert retrieved == value

    @given(value=st.text(min_size=0, max_size=1000))
    @settings(max_examples=50, deadline=2000)
    def test_string_values_preserved(self, value):
        """Property: String values are preserved through cache"""
        cache = CacheService(l1_maxsize=100, l1_ttl=60)
        cache.set(f"str:{hash(value)}", value)
        retrieved = cache.get(f"str:{hash(value)}")
        assert retrieved == value

    @given(value=st.lists(st.integers(), min_size=0, max_size=50))
    @settings(max_examples=30, deadline=2000)
    def test_list_values_preserved(self, value):
        """Property: List values are preserved through cache"""
        cache = CacheService(l1_maxsize=100, l1_ttl=60)
        cache.set(f"list:{len(value)}", value)
        retrieved = cache.get(f"list:{len(value)}")
        assert retrieved == value

    @given(value=st.dictionaries(st.text(min_size=1, max_size=10), st.integers(), min_size=0, max_size=20))
    @settings(max_examples=30, deadline=2000)
    def test_dict_values_preserved(self, value):
        """Property: Dict values are preserved through cache"""
        cache = CacheService(l1_maxsize=100, l1_ttl=60)
        cache.set(f"dict:{len(value)}", value)
        retrieved = cache.get(f"dict:{len(value)}")
        assert retrieved == value

    @given(value=st.booleans())
    @settings(max_examples=20, deadline=1000)
    def test_boolean_values_preserved(self, value):
        """Property: Boolean values are preserved through cache"""
        cache = CacheService(l1_maxsize=100, l1_ttl=60)
        cache.set(f"bool:{value}", value)
        retrieved = cache.get(f"bool:{value}")
        assert retrieved == value


@pytest.mark.xdist_group(name="property_cache_properties_tests")
class TestCacheKeyNormalization:
    """Test cache key generation properties"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @given(parts=st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=5))
    @settings(max_examples=30, deadline=2000)
    def test_key_generation_deterministic(self, parts):
        """Property: Same parts always generate same key"""
        key1 = generate_cache_key(*parts, prefix="test", version="v1")
        key2 = generate_cache_key(*parts, prefix="test", version="v1")
        assert key1 == key2

    @given(
        prefix1=st.text(min_size=1, max_size=10),
        prefix2=st.text(min_size=1, max_size=10),
        part=st.text(min_size=1, max_size=10),
    )
    @settings(max_examples=30, deadline=2000)
    def test_different_prefixes_different_keys(self, prefix1, prefix2, part):
        """Property: Different prefixes generate different keys"""
        assume(prefix1 != prefix2)

        key1 = generate_cache_key(part, prefix=prefix1, version="v1")
        key2 = generate_cache_key(part, prefix=prefix2, version="v1")

        assert key1 != key2

    @given(
        version1=st.text(min_size=1, max_size=5),
        version2=st.text(min_size=1, max_size=5),
        part=st.text(min_size=1, max_size=10),
    )
    @settings(max_examples=30, deadline=2000)
    def test_different_versions_different_keys(self, version1, version2, part):
        """Property: Different versions generate different keys"""
        assume(version1 != version2)

        key1 = generate_cache_key(part, prefix="test", version=version1)
        key2 = generate_cache_key(part, prefix="test", version=version2)

        assert key1 != key2

    @given(parts=st.lists(st.text(min_size=50, max_size=100), min_size=5, max_size=10))
    @settings(max_examples=15, deadline=2000)
    def test_long_keys_are_hashed(self, parts):
        """Property: Long keys are hashed to prevent issues"""
        key = generate_cache_key(*parts, prefix="test", version="v1")

        # Property: Long inputs result in hashed key
        # If original would be > 200 chars, key should contain 'hash'
        original_length = sum(len(p) for p in parts) + len(parts) * 2  # Rough estimate
        if original_length > 200:
            assert "hash" in key
            assert len(key) < 100  # Hashed key should be much shorter


@pytest.mark.xdist_group(name="property_cache_properties_tests")
class TestCacheTTLProperties:
    """Test TTL-related properties"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @given(cache_type=st.sampled_from(list(CACHE_TTLS.keys())))
    @settings(max_examples=10, deadline=1000)
    def test_ttl_lookup_consistent(self, cache_type):
        """Property: TTL lookup is consistent for valid cache types"""
        cache = CacheService(l1_maxsize=100, l1_ttl=60)

        key = f"{cache_type}:test:key"
        ttl = cache._get_ttl_from_key(key)

        # Should return the configured TTL for this cache type
        assert ttl == CACHE_TTLS[cache_type]

    @given(unknown_type=st.text(min_size=1, max_size=20))
    @settings(max_examples=20, deadline=2000)
    def test_unknown_cache_type_has_default_ttl(self, unknown_type):
        """Property: Unknown cache types get default TTL"""
        assume(unknown_type not in CACHE_TTLS)

        cache = CacheService(l1_maxsize=100, l1_ttl=60)
        key = f"{unknown_type}:test:key"
        ttl = cache._get_ttl_from_key(key)

        # Should return default TTL (300 seconds)
        assert ttl == 300


@pytest.mark.xdist_group(name="property_cache_properties_tests")
class TestCacheStatisticsProperties:
    """Test cache statistics invariants"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @given(num_operations=st.integers(min_value=1, max_value=50))
    @settings(max_examples=20, deadline=3000)
    def test_statistics_counts_accumulate(self, num_operations):
        """Property: Statistics counts accumulate correctly"""
        cache = CacheService(l1_maxsize=100, l1_ttl=60)

        for i in range(num_operations):
            cache.set(f"key:{i}", f"value:{i}")

        stats = cache.get_statistics()

        # Property: Set count matches operations
        assert stats["total"]["sets"] == num_operations

    @given(num_hits=st.integers(min_value=1, max_value=20))
    @settings(max_examples=15, deadline=2000)
    def test_hit_rate_calculation_correct(self, num_hits):
        """Property: Hit rate is correctly calculated"""
        cache = CacheService(l1_maxsize=100, l1_ttl=60)

        # Set a value
        cache.set("test:key", "value")

        # Generate hits
        for _ in range(num_hits):
            cache.get("test:key")

        # Generate one miss
        cache.get("nonexistent")

        stats = cache.get_statistics()

        # Property: Hit rate = hits / (hits + misses)
        expected_hit_rate = num_hits / (num_hits + 1)
        assert abs(stats["l1"]["hit_rate"] - expected_hit_rate) < 0.01

    @given(num_deletes=st.integers(min_value=1, max_value=30))
    @settings(max_examples=15, deadline=2000)
    def test_delete_statistics_accurate(self, num_deletes):
        """Property: Delete statistics are accurate"""
        cache = CacheService(l1_maxsize=100, l1_ttl=60)

        # Create and delete keys
        for i in range(num_deletes):
            cache.set(f"delete:key:{i}", f"value:{i}")
            cache.delete(f"delete:key:{i}")

        stats = cache.get_statistics()

        # Property: Delete count matches operations
        assert stats["total"]["deletes"] == num_deletes


@pytest.mark.xdist_group(name="property_cache_properties_tests")
class TestCacheConcurrencySafety:
    """Test cache behavior under concurrent access"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @given(num_concurrent=st.integers(min_value=2, max_value=10))
    @settings(max_examples=10, deadline=5000)
    @pytest.mark.asyncio
    async def test_concurrent_sets_dont_lose_data(self, num_concurrent):
        """Property: Concurrent sets don't lose data"""
        cache = CacheService(l1_maxsize=200, l1_ttl=60)

        async def set_value(i):
            cache.set(f"concurrent:key:{i}", f"value:{i}")

        # Concurrent sets
        await asyncio.gather(*[set_value(i) for i in range(num_concurrent)])

        # Property: All values should be retrievable
        for i in range(num_concurrent):
            retrieved = cache.get(f"concurrent:key:{i}")
            assert retrieved == f"value:{i}"

    @given(num_readers=st.integers(min_value=2, max_value=10))
    @settings(max_examples=10, deadline=3000)
    @pytest.mark.asyncio
    async def test_concurrent_reads_consistent(self, num_readers):
        """Property: Concurrent reads return consistent value"""
        cache = CacheService(l1_maxsize=100, l1_ttl=60)
        cache.set("shared:key", "shared_value")

        async def read_value():
            return cache.get("shared:key")

        # Concurrent reads
        results = await asyncio.gather(*[read_value() for _ in range(num_readers)])

        # Property: All reads return same value
        assert all(result == "shared_value" for result in results)


@pytest.mark.xdist_group(name="property_cache_properties_tests")
class TestCacheDecoratorProperties:
    """Test @cached decorator properties"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @given(
        x=st.integers(min_value=1, max_value=100),
        y=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=30, deadline=2000)
    @pytest.mark.asyncio
    async def test_cached_decorator_memoization(self, x, y):
        """Property: @cached decorator correctly memoizes results (avoiding falsy values)"""
        # Use unique key prefix to avoid cache pollution between test runs
        import random

        from mcp_server_langgraph.core.cache import get_cache

        # Clear the global cache before test to ensure clean slate
        cache = get_cache()
        cache.clear()

        unique_prefix = f"memo_test_{random.randint(1000000, 9999999)}"
        call_count = [0]

        @cached(key_prefix=unique_prefix, ttl=60)
        async def expensive_operation(a: int, b: int) -> int:
            call_count[0] += 1
            # Return a dict to ensure truthy value (avoids walrus operator issue with 0)
            return {"result": a + b, "calls": call_count[0]}

        # First call
        result1 = await expensive_operation(x, y)
        assert call_count[0] == 1
        assert result1["result"] == x + y

        # Second call with same args
        result2 = await expensive_operation(x, y)

        # Property: Results should be equal
        assert result1 == result2
        # Property: Second call should use cache (call_count stays at 1)
        assert call_count[0] == 1

    @given(values=st.lists(st.integers(), min_size=1, max_size=10, unique=True))
    @settings(max_examples=20, deadline=3000)
    @pytest.mark.asyncio
    async def test_cached_decorator_different_args_cached_separately(self, values):
        """Property: Different arguments are cached independently"""

        @cached(key_prefix="separate_test", ttl=60)
        async def identity(x: int) -> int:
            return x

        # Call with each value
        for value in values:
            result = await identity(value)
            assert result == value

        # Verify each is cached
        for value in values:
            result = await identity(value)
            assert result == value


@pytest.mark.xdist_group(name="property_cache_properties_tests")
class TestCacheEdgeCases:
    """Test cache edge cases and boundary conditions"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @given(st.just(None))
    @settings(max_examples=5, deadline=1000)
    def test_cache_handles_none_value(self, value):
        """Property: Cache can store and retrieve None without crashing"""
        cache = CacheService(l1_maxsize=100, l1_ttl=60)
        cache.set("none:key", value)

        # Property: get() should not crash when retrieving None
        # Note: get() returns None for both cache miss and cached None
        # This is a design limitation - we can't distinguish them
        result = cache.get("none:key")

        # Assert: Operation completed without exception and returned None
        assert result is None, f"Cache should handle None values gracefully, got: {result}"

    @given(value=st.floats(allow_nan=False, allow_infinity=False))
    @settings(max_examples=30, deadline=2000)
    def test_cache_handles_float_values(self, value):
        """Property: Cache correctly handles float values"""
        cache = CacheService(l1_maxsize=100, l1_ttl=60)
        cache.set(f"float:{value}", value)
        retrieved = cache.get(f"float:{value}")
        assert retrieved == value

    @given(size=st.integers(min_value=1, max_value=10))
    @settings(max_examples=15, deadline=2000)
    def test_cache_respects_max_size(self, size):
        """Property: Cache never exceeds maxsize"""
        cache = CacheService(l1_maxsize=size, l1_ttl=60)

        # Try to overfill cache
        for i in range(size * 2):
            cache.set(f"overflow:key:{i}", f"value:{i}")

        # Property: Cache size should never exceed maxsize
        assert len(cache.l1_cache) <= size


@pytest.mark.xdist_group(name="property_cache_properties_tests")
class TestCacheTTLBehavior:
    """Test TTL-related properties"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @given(ttl_seconds=st.floats(min_value=0.1, max_value=0.3))
    @settings(max_examples=10, deadline=2000)
    def test_cache_expires_after_ttl(self, ttl_seconds):
        """Property: Cached values expire after TTL"""
        # Performance optimization: Use 0.1-0.3s TTL instead of 1-3s
        # This reduces test time from ~35s to ~3.5s (10x speedup)
        # while validating the same TTL expiration behavior
        cache = CacheService(l1_maxsize=100, l1_ttl=ttl_seconds)
        cache.set("expiring:key", "value")

        # Should exist immediately
        assert cache.get("expiring:key") == "value"

        # Wait for expiration (add buffer) - reduced from 0.5s to 0.05s
        time.sleep(ttl_seconds + 0.05)

        # 🔴 RED → 🟢 GREEN: Assert TTL expiration behavior
        # Property: Cached values must expire after TTL
        result = cache.get("expiring:key")
        assert result is None, (
            f"Cache value should expire after {ttl_seconds}s TTL, but got: {result}\n"
            f"This indicates cachetools TTL is not working as expected."
        )

    @given(cache_type=st.sampled_from(list(CACHE_TTLS.keys())))
    @settings(max_examples=10, deadline=1000)
    def test_ttl_from_key_prefix_consistent(self, cache_type):
        """Property: TTL determination is consistent for cache types"""
        cache = CacheService(l1_maxsize=100, l1_ttl=60)

        key1 = f"{cache_type}:key1"
        key2 = f"{cache_type}:key2"

        ttl1 = cache._get_ttl_from_key(key1)
        ttl2 = cache._get_ttl_from_key(key2)

        # Property: Same cache type → same TTL
        assert ttl1 == ttl2
        assert ttl1 == CACHE_TTLS[cache_type]


@pytest.mark.xdist_group(name="property_cache_properties_tests")
class TestCacheStatisticsInvariants:
    """Test cache statistics invariants"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @given(
        num_sets=st.integers(min_value=0, max_value=20),
        num_gets=st.integers(min_value=0, max_value=20),
    )
    @settings(max_examples=20, deadline=2000)
    def test_statistics_never_negative(self, num_sets, num_gets):
        """Property: Cache statistics are never negative"""
        cache = CacheService(l1_maxsize=100, l1_ttl=60)

        # Perform operations
        for i in range(num_sets):
            cache.set(f"stats:key:{i}", f"value:{i}")

        for i in range(num_gets):
            cache.get(f"stats:key:{i % max(num_sets, 1)}")

        stats = cache.get_statistics()

        # Property: All statistics >= 0
        assert stats["l1"]["hits"] >= 0
        assert stats["l1"]["misses"] >= 0
        assert stats["l2"]["hits"] >= 0
        assert stats["l2"]["misses"] >= 0
        assert stats["total"]["sets"] >= 0
        assert stats["total"]["deletes"] >= 0

    @given(operations=st.lists(st.sampled_from(["set", "get", "delete"]), min_size=1, max_size=30))
    @settings(max_examples=15, deadline=2000)
    def test_hit_rate_between_zero_and_one(self, operations):
        """Property: Hit rate is always between 0 and 1"""
        cache = CacheService(l1_maxsize=100, l1_ttl=60)

        # Perform random operations
        for op in operations:
            if op == "set":
                cache.set("rate:key", "value")
            elif op == "get":
                cache.get("rate:key")
            elif op == "delete":
                cache.delete("rate:key")

        stats = cache.get_statistics()

        # Property: Hit rate is valid percentage
        assert 0.0 <= stats["l1"]["hit_rate"] <= 1.0
        assert 0.0 <= stats["l2"]["hit_rate"] <= 1.0


@pytest.mark.xdist_group(name="property_cache_properties_tests")
class TestCacheStampedePrevention:
    """Test cache stampede prevention properties"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @given(num_concurrent=st.integers(min_value=2, max_value=8))
    @settings(max_examples=10, deadline=5000)
    @pytest.mark.asyncio
    async def test_stampede_prevention_calls_fetcher_once(self, num_concurrent):
        """Property: get_with_lock calls fetcher only once for concurrent requests"""
        cache = CacheService(l1_maxsize=100, l1_ttl=60)
        call_count = [0]

        async def expensive_fetcher():
            call_count[0] += 1
            await asyncio.sleep(0.05)
            return "fetched_value"

        # Launch concurrent requests
        tasks = [cache.get_with_lock("stampede:key", expensive_fetcher) for _ in range(num_concurrent)]
        results = await asyncio.gather(*tasks)

        # Property: Fetcher called exactly once
        assert call_count[0] == 1
        # Property: All requests get same result
        assert all(result == "fetched_value" for result in results)


@pytest.mark.xdist_group(name="property_cache_properties_tests")
class TestCacheDeleteProperties:
    """Test cache deletion properties"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @given(num_keys=st.integers(min_value=1, max_value=30))
    @settings(max_examples=15, deadline=2000)
    def test_delete_removes_keys(self, num_keys):
        """Property: Deleted keys are no longer retrievable"""
        cache = CacheService(l1_maxsize=100, l1_ttl=60)

        # Set keys
        keys = [f"delete:key:{i}" for i in range(num_keys)]
        for key in keys:
            cache.set(key, f"value:{key}")

        # Delete keys
        for key in keys:
            cache.delete(key)

        # Property: Deleted keys return None
        for key in keys:
            assert cache.get(key) is None

    @given(num_keys=st.integers(min_value=1, max_value=20))
    @settings(max_examples=15, deadline=2000)
    def test_clear_removes_all_keys(self, num_keys):
        """Property: clear() removes all keys"""
        cache = CacheService(l1_maxsize=100, l1_ttl=60)

        # Set keys
        for i in range(num_keys):
            cache.set(f"clear:key:{i}", f"value:{i}")

        # Clear cache
        cache.clear()

        # Property: All keys should be gone
        assert len(cache.l1_cache) == 0

        # Verify by attempting to get
        for i in range(num_keys):
            assert cache.get(f"clear:key:{i}") is None


@pytest.mark.xdist_group(name="property_cache_properties_tests")
class TestCacheLevelIsolation:
    """Test cache level isolation properties"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @given(value=st.text(min_size=1, max_size=50))
    @settings(max_examples=15, deadline=2000)
    def test_l1_only_doesnt_affect_l2(self, value):
        """Property: L1-only operations don't interact with L2"""
        with patch("mcp_server_langgraph.core.cache.redis.Redis") as mock_redis_class:
            mock_redis = Mock()
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            mock_redis_class.return_value = mock_redis

            cache = CacheService(l1_maxsize=100, l1_ttl=60)

            # Set L1 only
            cache.set("l1:key", value, level=CacheLayer.L1)

            # L2 (Redis) should not be called
            mock_redis.setex.assert_not_called()

    @given(value=st.integers())
    @settings(max_examples=15, deadline=2000)
    def test_l2_writes_also_write_to_l1(self, value):
        """Property: L2 writes are promoted to L1"""
        with patch("mcp_server_langgraph.core.cache.redis.Redis") as mock_redis_class:
            mock_redis = Mock()
            mock_redis.ping.return_value = True
            mock_redis.setex.return_value = True
            mock_redis_class.return_value = mock_redis

            cache = CacheService(l1_maxsize=100, l1_ttl=60)

            # Set L2 (should also set L1)
            cache.set("l2:key", value, level=CacheLayer.L2)

            # Property: Should be in L1
            assert "l2:key" in cache.l1_cache
            assert cache.l1_cache["l2:key"] == value
