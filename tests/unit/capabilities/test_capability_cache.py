"""Tests for CapabilityCache with Redis TTL caching.

TDD: These tests define the contract for TTL-based capability caching
to optimize STUDIO.md resolution performance.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestCapabilityCacheBasic:
    """Tests for CapabilityCache basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_capability_cache_exists(self) -> None:
        """Test CapabilityCache class exists."""
        from mcp_server_langgraph.capabilities.cache import CapabilityCache

        assert CapabilityCache is not None

    def test_capability_cache_accepts_default_ttl(self) -> None:
        """Test CapabilityCache accepts default_ttl parameter."""
        from mcp_server_langgraph.capabilities.cache import CapabilityCache

        cache = CapabilityCache(default_ttl=600)

        assert cache.default_ttl == 600

    def test_capability_cache_has_default_ttl(self) -> None:
        """Test CapabilityCache has sensible default TTL."""
        from mcp_server_langgraph.capabilities.cache import CapabilityCache

        cache = CapabilityCache()

        # Default 5 minutes = 300 seconds
        assert cache.default_ttl == 300

    def test_capability_cache_accepts_redis_client(self) -> None:
        """Test CapabilityCache accepts redis client parameter."""
        from mcp_server_langgraph.capabilities.cache import CapabilityCache

        mock_redis = MagicMock()
        cache = CapabilityCache(redis=mock_redis)

        assert cache.redis is mock_redis

    def test_capability_cache_works_without_redis(self) -> None:
        """Test CapabilityCache works without Redis (in-memory fallback)."""
        from mcp_server_langgraph.capabilities.cache import CapabilityCache

        cache = CapabilityCache()

        # Should not raise when Redis is None
        assert cache.redis is None


@pytest.mark.unit
class TestCapabilityCacheOperations:
    """Tests for CapabilityCache get/set operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing_key(self) -> None:
        """Test get returns None for cache miss."""
        from mcp_server_langgraph.capabilities.cache import CapabilityCache

        cache = CapabilityCache()
        result = await cache.get("nonexistent-key")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get_roundtrip(self) -> None:
        """Test set followed by get returns the value."""
        from mcp_server_langgraph.capabilities.cache import CapabilityCache

        cache = CapabilityCache()
        test_data = {"tools": ["tool-1", "tool-2"], "skills": ["skill-1"]}

        await cache.set("test-key", test_data)
        result = await cache.get("test-key")

        assert result == test_data

    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self) -> None:
        """Test set accepts custom TTL."""
        from mcp_server_langgraph.capabilities.cache import CapabilityCache

        cache = CapabilityCache()
        test_data = {"tools": ["tool-1"]}

        # Should not raise
        await cache.set("test-key", test_data, ttl=120)

    @pytest.mark.asyncio
    async def test_invalidate_removes_key(self) -> None:
        """Test invalidate removes a cached entry."""
        from mcp_server_langgraph.capabilities.cache import CapabilityCache

        cache = CapabilityCache()
        test_data = {"tools": ["tool-1"]}

        await cache.set("test-key", test_data)
        await cache.invalidate("test-key")
        result = await cache.get("test-key")

        assert result is None


@pytest.mark.unit
class TestCapabilityCacheScopeOperations:
    """Tests for CapabilityCache scope-based operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_for_scope_returns_cached_capabilities(self) -> None:
        """Test get_for_scope returns cached capabilities."""
        from mcp_server_langgraph.capabilities.cache import CapabilityCache
        from mcp_server_langgraph.core.scopes import CapabilityScope

        cache = CapabilityCache()
        test_data = {"tools": ["tool-1"], "skills": ["skill-1"]}

        await cache.set_for_scope(
            scope=CapabilityScope.PROJECT,
            scope_id="project-123",
            capabilities=test_data,
        )

        result = await cache.get_for_scope(
            scope=CapabilityScope.PROJECT,
            scope_id="project-123",
        )

        assert result == test_data

    @pytest.mark.asyncio
    async def test_invalidate_scope_removes_scope_entries(self) -> None:
        """Test invalidate_scope removes all entries for a scope."""
        from mcp_server_langgraph.capabilities.cache import CapabilityCache
        from mcp_server_langgraph.core.scopes import CapabilityScope

        cache = CapabilityCache()
        test_data = {"tools": ["tool-1"]}

        await cache.set_for_scope(
            scope=CapabilityScope.PROJECT,
            scope_id="project-123",
            capabilities=test_data,
        )

        await cache.invalidate_scope(CapabilityScope.PROJECT, "project-123")

        result = await cache.get_for_scope(
            scope=CapabilityScope.PROJECT,
            scope_id="project-123",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_scope_cache_key_format(self) -> None:
        """Test scope cache key uses correct format."""
        from mcp_server_langgraph.capabilities.cache import CapabilityCache
        from mcp_server_langgraph.core.scopes import CapabilityScope

        cache = CapabilityCache()

        key = cache.make_scope_key(CapabilityScope.PROJECT, "project-123")

        assert key == "capability:project:project-123"

    @pytest.mark.asyncio
    async def test_scope_cache_key_handles_none_scope_id(self) -> None:
        """Test scope cache key handles None scope_id."""
        from mcp_server_langgraph.capabilities.cache import CapabilityCache
        from mcp_server_langgraph.core.scopes import CapabilityScope

        cache = CapabilityCache()

        key = cache.make_scope_key(CapabilityScope.TASK, None)

        assert key == "capability:task:_default"


@pytest.mark.unit
class TestCapabilityCacheRedisIntegration:
    """Tests for CapabilityCache with Redis backend."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_uses_redis_when_available(self) -> None:
        """Test get uses Redis client when provided."""
        from mcp_server_langgraph.capabilities.cache import CapabilityCache

        mock_redis = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_redis.get.return_value = '{"tools": ["tool-1"]}'

        cache = CapabilityCache(redis=mock_redis)
        result = await cache.get("test-key")

        mock_redis.get.assert_called_once_with("test-key")
        assert result == {"tools": ["tool-1"]}

    @pytest.mark.asyncio
    async def test_set_uses_redis_with_ttl(self) -> None:
        """Test set uses Redis setex for TTL."""
        from mcp_server_langgraph.capabilities.cache import CapabilityCache

        mock_redis = AsyncMock(return_value=None)  # noqa: async-mock-config
        cache = CapabilityCache(redis=mock_redis, default_ttl=300)

        await cache.set("test-key", {"tools": ["tool-1"]})

        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args
        assert args[0][0] == "test-key"
        assert args[0][1] == 300  # TTL

    @pytest.mark.asyncio
    async def test_invalidate_uses_redis_delete(self) -> None:
        """Test invalidate uses Redis delete."""
        from mcp_server_langgraph.capabilities.cache import CapabilityCache

        mock_redis = AsyncMock(return_value=None)  # noqa: async-mock-config
        cache = CapabilityCache(redis=mock_redis)

        await cache.invalidate("test-key")

        mock_redis.delete.assert_called_once_with("test-key")

    @pytest.mark.asyncio
    async def test_handles_redis_errors_gracefully(self) -> None:
        """Test cache handles Redis errors without raising."""
        from mcp_server_langgraph.capabilities.cache import CapabilityCache

        mock_redis = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_redis.get.side_effect = Exception("Redis connection error")

        cache = CapabilityCache(redis=mock_redis)

        # Should not raise, returns None on error
        result = await cache.get("test-key")
        assert result is None
