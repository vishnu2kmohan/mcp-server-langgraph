"""
Comprehensive tests for multi-layer caching system.

Tests:
- L1 in-memory cache (TTLCache)
- L2 Redis distributed cache
- Cache stampede prevention with locks
- Cache decorator (@cached)
- Cache key generation and TTL logic
- Cache statistics and metrics
- Error handling and fallback behavior
"""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from mcp_server_langgraph.core.cache import (
    CACHE_TTLS,
    CacheLayer,
    CacheService,
    cache_invalidate,
    cached,
    create_anthropic_cached_message,
    generate_cache_key,
    get_cache,
)


@pytest.fixture
def cache_service_no_redis():
    """Cache service with L1 only (no Redis)"""
    with patch("mcp_server_langgraph.core.cache.redis.Redis") as mock_redis:
        mock_redis.side_effect = RedisConnectionError("Connection refused")
        cache = CacheService(l1_maxsize=100, l1_ttl=60)
        return cache


@pytest.fixture
def cache_service_with_mock_redis():
    """Cache service with mocked Redis"""
    with patch("mcp_server_langgraph.core.cache.redis.Redis") as mock_redis_class:
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.flushdb.return_value = True
        mock_redis.keys.return_value = []
        mock_redis_class.return_value = mock_redis

        cache = CacheService(l1_maxsize=100, l1_ttl=60, redis_db=2)
        cache.mock_redis = mock_redis  # Store for assertions
        return cache


@pytest.fixture(scope="module", autouse=True)
def init_test_observability():
    """Initialize observability for tests"""
    from mcp_server_langgraph.core.config import Settings
    from mcp_server_langgraph.observability.telemetry import init_observability, is_initialized

    if not is_initialized():
        test_settings = Settings(
            log_format="text",
            enable_file_logging=False,
            langsmith_tracing=False,
            observability_backend="opentelemetry",
        )
        init_observability(settings=test_settings, enable_file_logging=False)

    yield


class TestCacheServiceInitialization:
    """Test cache service initialization"""

    def test_init_with_defaults(self, cache_service_no_redis):
        """Test initialization with default parameters"""
        assert cache_service_no_redis.l1_maxsize == 100
        assert cache_service_no_redis.l1_ttl == 60
        assert cache_service_no_redis.redis_available is False
        assert len(cache_service_no_redis.l1_cache) == 0

    def test_init_with_redis_success(self, cache_service_with_mock_redis):
        """Test initialization with Redis available"""
        assert cache_service_with_mock_redis.redis_available is True
        assert cache_service_with_mock_redis.redis is not None
        cache_service_with_mock_redis.mock_redis.ping.assert_called_once()

    def test_init_statistics_reset(self, cache_service_no_redis):
        """Test that statistics are initialized to zero"""
        stats = cache_service_no_redis.stats
        assert stats["l1_hits"] == 0
        assert stats["l1_misses"] == 0
        assert stats["l2_hits"] == 0
        assert stats["l2_misses"] == 0
        assert stats["sets"] == 0
        assert stats["deletes"] == 0


class TestCacheL1Operations:
    """Test L1 (in-memory) cache operations"""

    def test_l1_set_and_get(self, cache_service_no_redis):
        """Test basic L1 set and get"""
        cache_service_no_redis.set("test:key", "value", level=CacheLayer.L1)
        result = cache_service_no_redis.get("test:key", level=CacheLayer.L1)
        assert result == "value"
        assert cache_service_no_redis.stats["l1_hits"] == 1
        assert cache_service_no_redis.stats["sets"] == 1

    def test_l1_cache_miss(self, cache_service_no_redis):
        """Test L1 cache miss"""
        result = cache_service_no_redis.get("nonexistent:key", level=CacheLayer.L1)
        assert result is None
        assert cache_service_no_redis.stats["l1_misses"] == 1

    def test_l1_cache_complex_objects(self, cache_service_no_redis):
        """Test L1 caching of complex objects"""
        test_data = {"user": "alice", "permissions": ["read", "write"], "nested": {"key": "value"}}
        cache_service_no_redis.set("complex:key", test_data, level=CacheLayer.L1)
        result = cache_service_no_redis.get("complex:key", level=CacheLayer.L1)
        assert result == test_data
        assert isinstance(result, dict)

    def test_l1_ttl_expiration(self, cache_service_no_redis):
        """Test L1 TTL expiration"""
        # Create cache with very short TTL
        cache_short_ttl = CacheService(l1_maxsize=100, l1_ttl=1)
        cache_short_ttl.set("expiring:key", "value", level=CacheLayer.L1)

        # Should exist immediately
        assert cache_short_ttl.get("expiring:key", level=CacheLayer.L1) == "value"

        # Wait for expiration (1s TTL + small buffer)
        time.sleep(1.05)

        # Should be expired
        result = cache_short_ttl.get("expiring:key", level=CacheLayer.L1)
        assert result is None

    def test_l1_max_size_eviction(self):
        """Test L1 cache evicts old entries when full"""
        cache_small = CacheService(l1_maxsize=3, l1_ttl=60)

        # Fill cache to capacity
        cache_small.set("key1", "value1", level=CacheLayer.L1)
        cache_small.set("key2", "value2", level=CacheLayer.L1)
        cache_small.set("key3", "value3", level=CacheLayer.L1)

        assert len(cache_small.l1_cache) == 3

        # Add one more (should evict oldest)
        cache_small.set("key4", "value4", level=CacheLayer.L1)

        # Cache should still be at max size
        assert len(cache_small.l1_cache) <= 3


class TestCacheL2Operations:
    """Test L2 (Redis) cache operations"""

    def test_l2_set_and_get(self, cache_service_with_mock_redis):
        """Test L2 set and get with Redis"""
        import pickle

        test_value = {"data": "test"}

        # Set value (will be in L1 immediately due to level=L2)
        cache_service_with_mock_redis.set("test:key", test_value, ttl=300, level=CacheLayer.L2)

        # Should have called Redis setex
        cache_service_with_mock_redis.mock_redis.setex.assert_called()

        # First get will hit L1 (since L2 writes also write to L1)
        result = cache_service_with_mock_redis.get("test:key", level=CacheLayer.L2)
        assert result == test_value
        assert cache_service_with_mock_redis.stats["l1_hits"] == 1

        # Clear L1 to test L2 retrieval
        cache_service_with_mock_redis.l1_cache.clear()

        # Mock Redis to return pickled value for L2 hit
        cache_service_with_mock_redis.mock_redis.get.return_value = pickle.dumps(test_value)

        result = cache_service_with_mock_redis.get("test:key", level=CacheLayer.L2)
        assert result == test_value
        assert cache_service_with_mock_redis.stats["l2_hits"] == 1

    def test_l2_fallback_to_l1_on_redis_failure(self, cache_service_with_mock_redis):
        """Test that L2 failures fall back gracefully"""
        cache_service_with_mock_redis.mock_redis.get.side_effect = RedisConnectionError("Connection lost")

        # Set in L1 only
        cache_service_with_mock_redis.set("test:key", "value", level=CacheLayer.L2)

        # Get should fall back to L1 even though L2 fails
        result = cache_service_with_mock_redis.get("test:key", level=CacheLayer.L1)
        assert result == "value"

    def test_l2_cache_promotion(self, cache_service_with_mock_redis):
        """Test L2 → L1 promotion on cache hit"""
        import pickle

        test_value = "promoted_value"
        cache_service_with_mock_redis.mock_redis.get.return_value = pickle.dumps(test_value)

        # Get from L2 (should promote to L1)
        result = cache_service_with_mock_redis.get("promote:key", level=CacheLayer.L2)

        assert result == test_value
        # Should now be in L1
        assert "promote:key" in cache_service_with_mock_redis.l1_cache


class TestCacheDelete:
    """Test cache deletion"""

    def test_delete_from_l1(self, cache_service_no_redis):
        """Test delete removes from L1"""
        cache_service_no_redis.set("delete:key", "value", level=CacheLayer.L1)
        assert cache_service_no_redis.get("delete:key") is not None

        cache_service_no_redis.delete("delete:key")

        assert cache_service_no_redis.get("delete:key") is None
        assert cache_service_no_redis.stats["deletes"] == 1

    def test_delete_from_l2(self, cache_service_with_mock_redis):
        """Test delete removes from both L1 and L2"""
        cache_service_with_mock_redis.set("delete:key", "value", level=CacheLayer.L2)
        cache_service_with_mock_redis.delete("delete:key")

        # Should have called Redis delete
        cache_service_with_mock_redis.mock_redis.delete.assert_called_with("delete:key")
        assert cache_service_with_mock_redis.stats["deletes"] == 1


class TestCacheClear:
    """Test cache clearing"""

    def test_clear_all_l1(self, cache_service_no_redis):
        """Test clearing all L1 cache"""
        cache_service_no_redis.set("key1", "value1", level=CacheLayer.L1)
        cache_service_no_redis.set("key2", "value2", level=CacheLayer.L1)

        cache_service_no_redis.clear()

        assert len(cache_service_no_redis.l1_cache) == 0
        assert cache_service_no_redis.get("key1") is None
        assert cache_service_no_redis.get("key2") is None

    def test_clear_with_pattern(self, cache_service_with_mock_redis):
        """Test clearing with pattern (L2 only)"""
        cache_service_with_mock_redis.mock_redis.keys.return_value = [b"user:123:profile", b"user:123:settings"]

        cache_service_with_mock_redis.clear(pattern="user:123:*")

        # Should have queried for matching keys
        cache_service_with_mock_redis.mock_redis.keys.assert_called_with("user:123:*")
        # Should have deleted them
        cache_service_with_mock_redis.mock_redis.delete.assert_called()

    def test_clear_all_l2(self, cache_service_with_mock_redis):
        """Test clearing all L2 cache"""
        cache_service_with_mock_redis.clear()

        # Should have flushed entire Redis DB
        cache_service_with_mock_redis.mock_redis.flushdb.assert_called_once()


class TestCacheStampedePrevention:
    """Test cache stampede prevention with locks"""

    @pytest.mark.asyncio
    async def test_get_with_lock_cache_hit(self, cache_service_no_redis):
        """Test get_with_lock returns cached value without calling fetcher"""
        fetcher = AsyncMock(return_value="fetched_value")

        # Pre-populate cache
        cache_service_no_redis.set("locked:key", "cached_value")

        result = await cache_service_no_redis.get_with_lock("locked:key", fetcher)

        assert result == "cached_value"
        # Fetcher should not have been called
        fetcher.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_with_lock_cache_miss(self, cache_service_no_redis):
        """Test get_with_lock calls fetcher on cache miss"""
        fetcher = AsyncMock(return_value="fetched_value")

        result = await cache_service_no_redis.get_with_lock("locked:key", fetcher, ttl=300)

        assert result == "fetched_value"
        fetcher.assert_called_once()

        # Should be cached now
        assert cache_service_no_redis.get("locked:key") == "fetched_value"

    @pytest.mark.asyncio
    async def test_get_with_lock_prevents_stampede(self, cache_service_no_redis):
        """Test that concurrent requests don't cause stampede"""
        call_count = 0

        async def expensive_fetcher():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Simulate slow operation
            return f"result_{call_count}"

        # Launch 10 concurrent requests
        tasks = [cache_service_no_redis.get_with_lock("stampede:key", expensive_fetcher) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # Fetcher should only be called once (first request)
        assert call_count == 1

        # All requests should get the same result
        assert all(result == "result_1" for result in results)

    @pytest.mark.asyncio
    async def test_get_with_lock_sync_fetcher(self, cache_service_no_redis):
        """Test get_with_lock with synchronous fetcher"""

        def sync_fetcher():
            return "sync_result"

        result = await cache_service_no_redis.get_with_lock("sync:key", sync_fetcher)

        assert result == "sync_result"
        assert cache_service_no_redis.get("sync:key") == "sync_result"


class TestCacheTTLLogic:
    """Test TTL determination from cache keys"""

    def test_ttl_from_key_prefix_auth(self, cache_service_no_redis):
        """Test TTL determination for auth keys"""
        ttl = cache_service_no_redis._get_ttl_from_key("auth_permission:user:resource")
        assert ttl == CACHE_TTLS["auth_permission"]  # 300 seconds

    def test_ttl_from_key_prefix_user(self, cache_service_no_redis):
        """Test TTL determination for user profile keys"""
        ttl = cache_service_no_redis._get_ttl_from_key("user_profile:alice")
        assert ttl == CACHE_TTLS["user_profile"]  # 900 seconds

    def test_ttl_default_for_unknown_prefix(self, cache_service_no_redis):
        """Test default TTL for unknown key prefix"""
        ttl = cache_service_no_redis._get_ttl_from_key("unknown:key:type")
        assert ttl == 300  # Default 5 minutes

    def test_ttl_for_key_without_prefix(self, cache_service_no_redis):
        """Test TTL for key without colon separator"""
        ttl = cache_service_no_redis._get_ttl_from_key("simplekey")
        assert ttl == 300


class TestCacheStatistics:
    """Test cache statistics tracking"""

    def test_statistics_initial_state(self, cache_service_no_redis):
        """Test statistics in initial state"""
        stats = cache_service_no_redis.get_statistics()

        assert stats["l1"]["hits"] == 0
        assert stats["l1"]["misses"] == 0
        assert stats["l1"]["hit_rate"] == 0.0
        assert stats["l1"]["size"] == 0
        assert stats["l1"]["max_size"] == 100

        assert stats["l2"]["available"] is False

    def test_statistics_after_operations(self, cache_service_no_redis):
        """Test statistics after cache operations"""
        # Generate some hits and misses
        cache_service_no_redis.set("key1", "value1")
        cache_service_no_redis.get("key1")  # Hit (L1 hit)
        cache_service_no_redis.get("key1")  # Hit (L1 hit)
        cache_service_no_redis.get("nonexistent")  # Miss (L1 miss + L2 miss)

        stats = cache_service_no_redis.get_statistics()

        assert stats["l1"]["hits"] == 2
        # L1 misses = 1 (nonexistent key)
        # L2 misses = 1 (nonexistent key, since redis_available=False)
        assert stats["l1"]["misses"] == 1
        assert stats["l1"]["hit_rate"] == 2 / 3  # 2 hits / 3 total L1 operations
        assert stats["total"]["sets"] == 1

    def test_statistics_l2_metrics(self, cache_service_with_mock_redis):
        """Test L2 statistics when Redis is available"""
        stats = cache_service_with_mock_redis.get_statistics()
        assert stats["l2"]["available"] is True


class TestCachedDecorator:
    """Test @cached decorator"""

    @pytest.mark.asyncio
    async def test_cached_decorator_async_function(self, cache_service_no_redis):
        """Test @cached decorator with async function"""
        call_count = 0

        @cached(key_prefix="test", ttl=60)
        async def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return x * 2

        # First call - should execute
        result1 = await expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call with same args - should use cache
        result2 = await expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented

        # Different args - should execute
        result3 = await expensive_function(10)
        assert result3 == 20
        assert call_count == 2

    def test_cached_decorator_sync_function(self):
        """Test @cached decorator with synchronous function"""
        call_count = 0

        @cached(key_prefix="test_sync", ttl=60)
        def expensive_sync_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 3

        # First call
        result1 = expensive_sync_function(7)
        assert result1 == 21
        assert call_count == 1

        # Second call - cached
        result2 = expensive_sync_function(7)
        assert result2 == 21
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_cached_decorator_with_kwargs(self):
        """Test @cached decorator with keyword arguments"""
        call_count = 0

        @cached(key_prefix="test_kwargs", ttl=60)
        async def func_with_kwargs(a: int, b: int = 0) -> int:
            nonlocal call_count
            call_count += 1
            return a + b

        # Different kwarg values should cache separately
        result1 = await func_with_kwargs(1, b=2)
        result2 = await func_with_kwargs(1, b=3)

        assert result1 == 3
        assert result2 == 4
        assert call_count == 2  # Different kwargs = different cache keys

    @pytest.mark.asyncio
    async def test_cached_decorator_long_key_hashing(self):
        """Test that long cache keys are hashed"""

        @cached(key_prefix="very_long_prefix", ttl=60)
        async def func_with_many_args(*args):
            return sum(args)

        # Generate long key with many arguments
        many_args = tuple(range(100))
        result = await func_with_many_args(*many_args)

        assert result == sum(range(100))


class TestCacheKeyGeneration:
    """Test cache key generation helper"""

    def test_generate_cache_key_basic(self):
        """Test basic cache key generation"""
        key = generate_cache_key("user_123", "profile", prefix="user", version="v1")
        assert key == "user:user_123:profile:v1"

    def test_generate_cache_key_no_prefix(self):
        """Test cache key generation without prefix"""
        key = generate_cache_key("part1", "part2", version="v2")
        assert key == "part1:part2:v2"

    def test_generate_cache_key_long_key_hashing(self):
        """Test that long keys are hashed"""
        long_parts = ["x" * 100 for _ in range(10)]
        key = generate_cache_key(*long_parts, prefix="test", version="v1")

        # Should be hashed (includes hash in key)
        assert "hash" in key
        assert len(key) < 100  # Much shorter than original


class TestCacheInvalidate:
    """Test cache invalidation helper"""

    def test_cache_invalidate_pattern(self, cache_service_with_mock_redis):
        """Test cache_invalidate with pattern"""
        with patch("mcp_server_langgraph.core.cache.get_cache", return_value=cache_service_with_mock_redis):
            cache_service_with_mock_redis.mock_redis.keys.return_value = [b"user:123:key1"]

            cache_invalidate("user:123:*")

            cache_service_with_mock_redis.mock_redis.keys.assert_called_with("user:123:*")


class TestAnthropicPromptCaching:
    """Test Anthropic-specific prompt caching (L3)"""

    def test_create_anthropic_cached_message(self):
        """Test Anthropic prompt caching message structure"""
        system_prompt = "You are a helpful assistant."
        messages = [{"role": "user", "content": "Hello"}]

        result = create_anthropic_cached_message(system_prompt, messages)

        assert result["model"] == "claude-3-5-sonnet-20241022"
        assert len(result["system"]) == 1
        assert result["system"][0]["type"] == "text"
        assert result["system"][0]["text"] == system_prompt
        assert result["system"][0]["cache_control"]["type"] == "ephemeral"
        assert result["messages"] == messages


class TestCacheErrorHandling:
    """Test error handling and resilience"""

    def test_redis_connection_failure_doesnt_crash(self):
        """Test that Redis connection failure doesn't crash initialization"""
        with patch("mcp_server_langgraph.core.cache.redis.Redis") as mock_redis:
            mock_redis.side_effect = Exception("Connection failed")

            # Should not raise, just disable Redis
            cache = CacheService()
            assert cache.redis_available is False
            assert cache.redis is None

    def test_l2_get_failure_returns_none(self, cache_service_with_mock_redis):
        """Test that L2 get failures return None gracefully"""
        cache_service_with_mock_redis.mock_redis.get.side_effect = Exception("Redis error")

        result = cache_service_with_mock_redis.get("error:key", level=CacheLayer.L2)

        # Should return None, not crash
        assert result is None

    def test_l2_set_failure_doesnt_crash(self, cache_service_with_mock_redis):
        """Test that L2 set failures don't crash"""
        cache_service_with_mock_redis.mock_redis.setex.side_effect = Exception("Redis error")

        # Should not raise
        cache_service_with_mock_redis.set("error:key", "value", level=CacheLayer.L2)

        # L1 should still work
        assert "error:key" in cache_service_with_mock_redis.l1_cache


class TestCacheGlobalInstance:
    """Test global cache singleton"""

    def test_get_cache_returns_singleton(self):
        """Test get_cache returns same instance"""
        cache1 = get_cache()
        cache2 = get_cache()

        assert cache1 is cache2

    def test_get_cache_creates_instance(self):
        """Test get_cache creates CacheService instance"""
        cache = get_cache()
        assert isinstance(cache, CacheService)


class TestCacheLayers:
    """Test cache layer constants"""

    def test_cache_layer_values(self):
        """Test CacheLayer enum values"""
        assert CacheLayer.L1 == "l1"
        assert CacheLayer.L2 == "l2"
        assert CacheLayer.L3 == "l3"


class TestCacheTTLConstants:
    """Test cache TTL configuration"""

    def test_cache_ttls_defined(self):
        """Test all expected cache TTLs are defined"""
        assert "auth_permission" in CACHE_TTLS
        assert "user_profile" in CACHE_TTLS
        assert "llm_response" in CACHE_TTLS
        assert "embedding" in CACHE_TTLS
        assert "prometheus_query" in CACHE_TTLS

    def test_cache_ttls_reasonable_values(self):
        """Test TTL values are reasonable"""
        # Auth should be relatively short (5 min)
        assert CACHE_TTLS["auth_permission"] == 300

        # Embeddings can be long (24 hours)
        assert CACHE_TTLS["embedding"] == 86400

        # Prometheus queries should be short (1 min)
        assert CACHE_TTLS["prometheus_query"] == 60
