"""
Tests for CacheService close hooks.

Tests the close() and aclose() methods added to CacheService for proper
Redis client cleanup on application shutdown.

TDD Phase: RED - Tests written before implementation.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestCacheServiceClose:
    """Tests for CacheService close/aclose methods."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_cache_service_close_closes_sync_client(self):
        """close() should close the sync Redis client."""
        from mcp_server_langgraph.core.cache import CacheService

        # Create cache service with mock Redis
        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            mock_client = MagicMock()
            mock_redis_module.from_url.return_value = mock_client
            mock_client.ping.return_value = True

            cache = CacheService(redis_url="redis://localhost:6379")

            # Verify Redis client was created
            assert cache.redis is mock_client

            # Close the cache service
            cache.close()

            # Verify sync client was closed
            mock_client.close.assert_called_once()

            # Verify client reference is cleared
            assert cache.redis is None

    @pytest.mark.asyncio
    async def test_cache_service_aclose_closes_async_client(self):
        """aclose() should close the async Redis client."""
        from mcp_server_langgraph.core.cache import CacheService

        # Create cache service
        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            mock_sync_client = MagicMock()
            mock_redis_module.from_url.return_value = mock_sync_client
            mock_sync_client.ping.return_value = True

            cache = CacheService(redis_url="redis://localhost:6379")

            # Manually set async redis client (simulating lazy init)
            mock_async_client = AsyncMock(return_value=None)
            cache.async_redis = mock_async_client

            # Close async client
            await cache.aclose()

            # Verify async client was closed
            mock_async_client.close.assert_called_once()

            # Verify client reference is cleared
            assert cache.async_redis is None

    def test_close_after_close_is_safe(self):
        """Calling close() multiple times should be safe (idempotent)."""
        from mcp_server_langgraph.core.cache import CacheService

        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            mock_client = MagicMock()
            mock_redis_module.from_url.return_value = mock_client
            mock_client.ping.return_value = True

            cache = CacheService(redis_url="redis://localhost:6379")

            # Close multiple times - should not raise
            cache.close()
            cache.close()
            cache.close()

            # Close should only be called once (first time)
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose_after_aclose_is_safe(self):
        """Calling aclose() multiple times should be safe (idempotent)."""
        from mcp_server_langgraph.core.cache import CacheService

        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            mock_sync_client = MagicMock()
            mock_redis_module.from_url.return_value = mock_sync_client
            mock_sync_client.ping.return_value = True

            cache = CacheService(redis_url="redis://localhost:6379")

            # Manually set async redis client
            mock_async_client = AsyncMock(return_value=None)
            cache.async_redis = mock_async_client

            # Close multiple times - should not raise
            await cache.aclose()
            await cache.aclose()
            await cache.aclose()

            # Close should only be called once (first time)
            mock_async_client.close.assert_called_once()

    def test_close_when_redis_not_available(self):
        """close() should be safe when Redis was never available."""
        from mcp_server_langgraph.core.cache import CacheService

        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            # Simulate Redis unavailable during init
            mock_redis_module.from_url.side_effect = Exception("Connection refused")

            cache = CacheService(redis_url="redis://localhost:6379")

            # Verify Redis is None
            assert cache.redis is None
            assert cache.redis_available is False

            # close() should not raise
            cache.close()

    @pytest.mark.asyncio
    async def test_aclose_when_async_redis_not_initialized(self):
        """aclose() should be safe when async Redis was never initialized."""
        from mcp_server_langgraph.core.cache import CacheService

        with patch("mcp_server_langgraph.core.cache.redis") as mock_redis_module:
            # Allow sync Redis to succeed
            mock_sync_client = MagicMock()
            mock_redis_module.from_url.return_value = mock_sync_client
            mock_sync_client.ping.return_value = True

            cache = CacheService(redis_url="redis://localhost:6379")

            # Async redis is None (never initialized)
            assert cache.async_redis is None

            # aclose() should not raise
            await cache.aclose()
