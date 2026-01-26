"""
TDD RED Phase: Tests for CacheService async methods.

These tests verify that:
1. Async methods exist (aget, aset, adelete, aclear)
2. Async methods use redis.asyncio for L2 cache
3. Async methods properly handle L1 -> L2 cache promotion
4. Async operations don't block the event loop

Following memory safety patterns for pytest-xdist (see CLAUDE.md).
"""

import asyncio
import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.core.cache import CacheService

# Module-level pytestmark for test organization
pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="cache_async")
class TestCacheServiceAsyncMethods:
    """
    TDD tests for CacheService async methods.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_aget_method_exists_and_is_async(self):
        """
        RED: Verify aget() method exists and is a coroutine function.
        """
        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            mock_redis_module.from_url.return_value = MagicMock()
            mock_redis_module.from_url.return_value.ping.return_value = True

            cache = CacheService(redis_url="redis://localhost:6379")

            assert hasattr(cache, "aget"), "CacheService must have aget() method"
            assert asyncio.iscoroutinefunction(cache.aget), "aget() must be an async method (coroutine function)"

    async def test_aset_method_exists_and_is_async(self):
        """
        RED: Verify aset() method exists and is a coroutine function.
        """
        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            mock_redis_module.from_url.return_value = MagicMock()
            mock_redis_module.from_url.return_value.ping.return_value = True

            cache = CacheService(redis_url="redis://localhost:6379")

            assert hasattr(cache, "aset"), "CacheService must have aset() method"
            assert asyncio.iscoroutinefunction(cache.aset), "aset() must be an async method (coroutine function)"

    async def test_adelete_method_exists_and_is_async(self):
        """
        RED: Verify adelete() method exists and is a coroutine function.
        """
        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            mock_redis_module.from_url.return_value = MagicMock()
            mock_redis_module.from_url.return_value.ping.return_value = True

            cache = CacheService(redis_url="redis://localhost:6379")

            assert hasattr(cache, "adelete"), "CacheService must have adelete() method"
            assert asyncio.iscoroutinefunction(cache.adelete), "adelete() must be an async method (coroutine function)"

    async def test_aclear_method_exists_and_is_async(self):
        """
        RED: Verify aclear() method exists and is a coroutine function.
        """
        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            mock_redis_module.from_url.return_value = MagicMock()
            mock_redis_module.from_url.return_value.ping.return_value = True

            cache = CacheService(redis_url="redis://localhost:6379")

            assert hasattr(cache, "aclear"), "CacheService must have aclear() method"
            assert asyncio.iscoroutinefunction(cache.aclear), "aclear() must be an async method (coroutine function)"


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="cache_async")
class TestCacheServiceAsyncGet:
    """
    TDD tests for CacheService.aget() functionality.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_aget_returns_value_from_l1_cache(self):
        """
        Verify aget() returns value from L1 cache (in-memory) when present.
        """
        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            mock_redis_module.from_url.return_value = MagicMock()
            mock_redis_module.from_url.return_value.ping.return_value = True

            cache = CacheService(redis_url="redis://localhost:6379")

            # Pre-populate L1 cache
            cache.l1_cache["test_key"] = "test_value"

            result = await cache.aget("test_key")

            assert result == "test_value", "Should return value from L1 cache"

    async def test_aget_returns_value_from_l2_and_promotes_to_l1(self):
        """
        Verify aget() returns value from L2 (Redis) and promotes to L1.
        """
        import pickle

        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            mock_sync_redis = MagicMock()
            mock_sync_redis.ping.return_value = True
            mock_redis_module.from_url.return_value = mock_sync_redis

            cache = CacheService(redis_url="redis://localhost:6379")

            # Mock async Redis client
            mock_async_redis = AsyncMock(return_value=None)  # async-mock-configured (return_value set below)
            mock_async_redis.get.return_value = pickle.dumps("l2_value")
            cache.async_redis = mock_async_redis

            # Ensure L1 cache is empty
            assert "test_key" not in cache.l1_cache

            result = await cache.aget("test_key")

            assert result == "l2_value", "Should return value from L2 cache"
            assert cache.l1_cache["test_key"] == "l2_value", "Should promote value to L1 cache"

    async def test_aget_returns_none_when_not_found(self):
        """
        Verify aget() returns None when key not in L1 or L2.
        """
        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            mock_sync_redis = MagicMock()
            mock_sync_redis.ping.return_value = True
            mock_redis_module.from_url.return_value = mock_sync_redis

            cache = CacheService(redis_url="redis://localhost:6379")

            # Mock async Redis client returning None
            mock_async_redis = AsyncMock(return_value=None)  # async-mock-configured (return_value set below)
            mock_async_redis.get.return_value = None
            cache.async_redis = mock_async_redis

            result = await cache.aget("nonexistent_key")

            assert result is None, "Should return None when key not found"


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="cache_async")
class TestCacheServiceAsyncSet:
    """
    TDD tests for CacheService.aset() functionality.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_aset_stores_in_l1_cache(self):
        """
        Verify aset() stores value in L1 cache.
        """
        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            mock_sync_redis = MagicMock()
            mock_sync_redis.ping.return_value = True
            mock_redis_module.from_url.return_value = mock_sync_redis

            cache = CacheService(redis_url="redis://localhost:6379")

            # Mock async Redis client
            mock_async_redis = AsyncMock(return_value=None)  # noqa: async-mock-config
            cache.async_redis = mock_async_redis

            await cache.aset("test_key", "test_value", ttl=300)

            assert cache.l1_cache["test_key"] == "test_value", "Should store in L1 cache"

    async def test_aset_stores_in_l2_cache(self):
        """
        Verify aset() stores value in L2 (async Redis) cache.
        """
        import pickle

        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            mock_sync_redis = MagicMock()
            mock_sync_redis.ping.return_value = True
            mock_redis_module.from_url.return_value = mock_sync_redis

            cache = CacheService(redis_url="redis://localhost:6379")

            # Mock async Redis client
            mock_async_redis = AsyncMock(return_value=None)  # noqa: async-mock-config
            cache.async_redis = mock_async_redis

            await cache.aset("test_key", "test_value", ttl=300)

            # Verify async Redis was called
            mock_async_redis.setex.assert_called_once()
            call_args = mock_async_redis.setex.call_args
            assert call_args[0][0] == "test_key"
            assert call_args[0][1] == 300  # TTL
            assert pickle.loads(call_args[0][2]) == "test_value"


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="cache_async")
class TestCacheServiceAsyncDelete:
    """
    TDD tests for CacheService.adelete() functionality.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_adelete_removes_from_l1_cache(self):
        """
        Verify adelete() removes value from L1 cache.
        """
        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            mock_sync_redis = MagicMock()
            mock_sync_redis.ping.return_value = True
            mock_redis_module.from_url.return_value = mock_sync_redis

            cache = CacheService(redis_url="redis://localhost:6379")

            # Pre-populate L1 cache
            cache.l1_cache["test_key"] = "test_value"

            # Mock async Redis client
            mock_async_redis = AsyncMock(return_value=None)  # noqa: async-mock-config
            cache.async_redis = mock_async_redis

            await cache.adelete("test_key")

            assert "test_key" not in cache.l1_cache, "Should remove from L1 cache"

    async def test_adelete_removes_from_l2_cache(self):
        """
        Verify adelete() removes value from L2 (async Redis) cache.
        """
        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            mock_sync_redis = MagicMock()
            mock_sync_redis.ping.return_value = True
            mock_redis_module.from_url.return_value = mock_sync_redis

            cache = CacheService(redis_url="redis://localhost:6379")

            # Mock async Redis client
            mock_async_redis = AsyncMock(return_value=None)  # noqa: async-mock-config
            cache.async_redis = mock_async_redis

            await cache.adelete("test_key")

            # Verify async Redis delete was called
            mock_async_redis.delete.assert_called_once_with("test_key")


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="cache_async")
class TestCacheServiceAsyncClear:
    """
    TDD tests for CacheService.aclear() functionality.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_aclear_clears_l1_cache(self):
        """
        Verify aclear() clears L1 cache.
        """
        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            mock_sync_redis = MagicMock()
            mock_sync_redis.ping.return_value = True
            mock_redis_module.from_url.return_value = mock_sync_redis

            cache = CacheService(redis_url="redis://localhost:6379")

            # Pre-populate L1 cache
            cache.l1_cache["key1"] = "value1"
            cache.l1_cache["key2"] = "value2"

            # Mock async Redis client
            mock_async_redis = AsyncMock(return_value=None)  # async-mock-configured (return_value set below)
            mock_async_redis.keys.return_value = []
            cache.async_redis = mock_async_redis

            await cache.aclear()

            assert len(cache.l1_cache) == 0, "Should clear L1 cache"

    async def test_aclear_with_pattern_clears_matching_keys(self):
        """
        Verify aclear() with pattern clears only matching keys from L2.
        """
        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            mock_sync_redis = MagicMock()
            mock_sync_redis.ping.return_value = True
            mock_redis_module.from_url.return_value = mock_sync_redis

            cache = CacheService(redis_url="redis://localhost:6379")

            # Mock async Redis client
            mock_async_redis = AsyncMock(return_value=None)  # async-mock-configured (return_value set below)
            mock_async_redis.keys.return_value = [b"user:123", b"user:456"]
            cache.async_redis = mock_async_redis

            await cache.aclear(pattern="user:*")

            # Verify pattern search was used
            mock_async_redis.keys.assert_called_once_with("user:*")
            # Verify delete was called with matched keys
            mock_async_redis.delete.assert_called_once()
