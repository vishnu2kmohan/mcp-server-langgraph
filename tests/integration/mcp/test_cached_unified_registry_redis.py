"""
Integration Tests for CachedUnifiedRegistry with Real Redis.

Tests validate the cache-aside pattern behavior with actual Redis connection:
- Cache hits and misses for tools/resources/prompts
- Cache population after fetching from registry
- Cache invalidation on server registration/unregistration
- TTL expiration behavior
- Graceful degradation on cache failures
- Pattern-based invalidation

Reference: MCP Protocol 2025-11-25 capability aggregation
"""

import asyncio
import gc
from typing import Any
from unittest.mock import MagicMock

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
    """Create a real CacheService with Redis for testing."""
    from mcp_server_langgraph.core.cache import CacheService

    cache = CacheService(
        redis_url=f"redis://localhost:{TEST_REDIS_PORT}",
        redis_db=14,  # Use DB 14 for MCP tests (isolated from other tests)
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


class MockToolDefinition:
    """Mock tool definition with proper attribute access."""

    def __init__(
        self,
        qualified_name: str,
        server_name: str,
        name: str,
        description: str,
        input_schema: dict[str, Any],
    ):
        self.qualified_name = qualified_name
        self.server_name = server_name
        self.name = name
        self.description = description
        self.input_schema = input_schema


class MockResourceDefinition:
    """Mock resource definition with proper attribute access."""

    def __init__(
        self,
        qualified_name: str,
        server_name: str,
        name: str,
        uri: str,
        description: str,
        mime_type: str,
    ):
        self.qualified_name = qualified_name
        self.server_name = server_name
        self.name = name
        self.uri = uri
        self.description = description
        self.mime_type = mime_type


class MockPromptDefinition:
    """Mock prompt definition with proper attribute access."""

    def __init__(
        self,
        qualified_name: str,
        server_name: str,
        name: str,
        description: str,
        arguments: list[dict[str, Any]],
    ):
        self.qualified_name = qualified_name
        self.server_name = server_name
        self.name = name
        self.description = description
        self.arguments = arguments


@pytest.fixture
def mock_registry():
    """Create a mock MCPUnifiedRegistry with sample data."""
    registry = MagicMock()

    # Sample tool definitions using proper objects (not MagicMock)
    sample_tools = [
        MockToolDefinition(
            qualified_name="test-server:search_files",
            server_name="test-server",
            name="search_files",
            description="Search for files",
            input_schema={"type": "object"},
        ),
        MockToolDefinition(
            qualified_name="test-server:read_file",
            server_name="test-server",
            name="read_file",
            description="Read a file",
            input_schema={"type": "object"},
        ),
    ]

    # Sample resource definitions
    sample_resources = [
        MockResourceDefinition(
            qualified_name="test-server:file:///test.md",
            server_name="test-server",
            name="test.md",
            uri="file:///test.md",
            description="Test file",
            mime_type="text/markdown",
        ),
    ]

    # Sample prompt definitions
    sample_prompts = [
        MockPromptDefinition(
            qualified_name="test-server:code_review",
            server_name="test-server",
            name="code_review",
            description="Review code",
            arguments=[{"name": "code", "type": "string"}],
        ),
    ]

    # Configure mock return values
    registry.get_tools = MagicMock(return_value=sample_tools)
    registry.get_resources = MagicMock(return_value=sample_resources)
    registry.get_prompts = MagicMock(return_value=sample_prompts)
    registry.get_server_names = MagicMock(return_value=["test-server"])
    registry.get_server_capabilities = MagicMock(return_value={"tool_count": 2, "resource_count": 1, "prompt_count": 1})

    return registry


@pytest.fixture
async def cached_registry(redis_cache_service, mock_registry):
    """Create a CachedUnifiedRegistry with real Redis and mock registry."""
    from mcp_server_langgraph.mcp.client.cached_unified_registry import (
        CachedUnifiedRegistry,
    )

    return CachedUnifiedRegistry(
        registry=mock_registry,
        cache=redis_cache_service,
        ttl=60,  # 60 seconds for tests
    )


@pytest.mark.skipif(
    not is_redis_available(),
    reason="Redis not available on test port",
)
@pytest.mark.xdist_group(name="integration_cached_unified_registry_redis")
class TestCachedUnifiedRegistryRedis:
    """Integration tests for CachedUnifiedRegistry with real Redis."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # =========================================================================
    # Cache Miss Tests - First Call Populates Cache
    # =========================================================================

    async def test_get_tools_cache_miss_fetches_from_registry(self, cached_registry, mock_registry):
        """
        GIVEN an empty cache
        WHEN get_tools is called
        THEN it should fetch from registry and return tools.
        """
        result = await cached_registry.get_tools()

        assert len(result) == 2
        assert result[0]["name"] == "search_files"
        mock_registry.get_tools.assert_called_once()

    async def test_get_tools_cache_miss_populates_redis(self, cached_registry, redis_cache_service, mock_registry):
        """
        GIVEN an empty cache
        WHEN get_tools is called
        THEN it should populate the Redis cache.
        """
        await cached_registry.get_tools()

        # Verify cache was populated
        cached = await redis_cache_service.aget("mcp:tools:all")
        assert cached is not None
        assert len(cached) == 2

    async def test_get_resources_cache_miss_fetches_from_registry(self, cached_registry, mock_registry):
        """
        GIVEN an empty cache
        WHEN get_resources is called
        THEN it should fetch from registry and return resources.
        """
        result = await cached_registry.get_resources()

        assert len(result) == 1
        assert result[0]["name"] == "test.md"
        mock_registry.get_resources.assert_called_once()

    async def test_get_prompts_cache_miss_fetches_from_registry(self, cached_registry, mock_registry):
        """
        GIVEN an empty cache
        WHEN get_prompts is called
        THEN it should fetch from registry and return prompts.
        """
        result = await cached_registry.get_prompts()

        assert len(result) == 1
        assert result[0]["name"] == "code_review"
        mock_registry.get_prompts.assert_called_once()

    async def test_get_server_names_cache_miss_fetches_from_registry(self, cached_registry, mock_registry):
        """
        GIVEN an empty cache
        WHEN get_server_names is called
        THEN it should fetch from registry and return server names.
        """
        result = await cached_registry.get_server_names()

        assert result == ["test-server"]
        mock_registry.get_server_names.assert_called_once()

    async def test_get_server_capabilities_cache_miss_fetches_from_registry(self, cached_registry, mock_registry):
        """
        GIVEN an empty cache
        WHEN get_server_capabilities is called
        THEN it should fetch from registry and return capabilities.
        """
        result = await cached_registry.get_server_capabilities("test-server")

        assert result["tool_count"] == 2
        assert result["resource_count"] == 1
        assert result["prompt_count"] == 1
        mock_registry.get_server_capabilities.assert_called_once_with("test-server")

    # =========================================================================
    # Cache Hit Tests - Second Call Uses Cache
    # =========================================================================

    async def test_get_tools_cache_hit_returns_cached_data(self, cached_registry, mock_registry):
        """
        GIVEN tools have been fetched once (cache populated)
        WHEN get_tools is called again
        THEN it should return cached data without hitting registry.
        """
        # First call - cache miss
        await cached_registry.get_tools()
        mock_registry.get_tools.reset_mock()

        # Second call - should hit cache
        result = await cached_registry.get_tools()

        assert len(result) == 2
        mock_registry.get_tools.assert_not_called()

    async def test_get_resources_cache_hit_returns_cached_data(self, cached_registry, mock_registry):
        """
        GIVEN resources have been fetched once (cache populated)
        WHEN get_resources is called again
        THEN it should return cached data without hitting registry.
        """
        # First call - cache miss
        await cached_registry.get_resources()
        mock_registry.get_resources.reset_mock()

        # Second call - should hit cache
        result = await cached_registry.get_resources()

        assert len(result) == 1
        mock_registry.get_resources.assert_not_called()

    async def test_get_prompts_cache_hit_returns_cached_data(self, cached_registry, mock_registry):
        """
        GIVEN prompts have been fetched once (cache populated)
        WHEN get_prompts is called again
        THEN it should return cached data without hitting registry.
        """
        # First call - cache miss
        await cached_registry.get_prompts()
        mock_registry.get_prompts.reset_mock()

        # Second call - should hit cache
        result = await cached_registry.get_prompts()

        assert len(result) == 1
        mock_registry.get_prompts.assert_not_called()

    async def test_get_server_names_cache_hit_returns_cached_data(self, cached_registry, mock_registry):
        """
        GIVEN server names have been fetched once (cache populated)
        WHEN get_server_names is called again
        THEN it should return cached data without hitting registry.
        """
        # First call - cache miss
        await cached_registry.get_server_names()
        mock_registry.get_server_names.reset_mock()

        # Second call - should hit cache
        result = await cached_registry.get_server_names()

        assert result == ["test-server"]
        mock_registry.get_server_names.assert_not_called()

    async def test_get_server_capabilities_cache_hit_returns_cached_data(self, cached_registry, mock_registry):
        """
        GIVEN server capabilities have been fetched once (cache populated)
        WHEN get_server_capabilities is called again
        THEN it should return cached data without hitting registry.
        """
        # First call - cache miss
        await cached_registry.get_server_capabilities("test-server")
        mock_registry.get_server_capabilities.reset_mock()

        # Second call - should hit cache
        result = await cached_registry.get_server_capabilities("test-server")

        assert result["tool_count"] == 2
        mock_registry.get_server_capabilities.assert_not_called()

    # =========================================================================
    # Server-Specific Filtering Tests
    # =========================================================================

    async def test_get_tools_with_server_filter_uses_separate_cache_key(self, cached_registry, mock_registry):
        """
        GIVEN tools for all servers have been cached
        WHEN get_tools is called with a server filter
        THEN it should use a different cache key and hit registry.
        """
        # First call without filter
        await cached_registry.get_tools()
        mock_registry.get_tools.reset_mock()

        # Call with server filter - should be a different cache key
        await cached_registry.get_tools(server_name="test-server")

        # Should have hit registry (different cache key)
        mock_registry.get_tools.assert_called_once_with("test-server")

    async def test_get_tools_same_server_filter_uses_cache(self, cached_registry, mock_registry):
        """
        GIVEN tools for a specific server have been cached
        WHEN get_tools is called with the same server filter
        THEN it should return cached data.
        """
        # First call with filter
        await cached_registry.get_tools(server_name="test-server")
        mock_registry.get_tools.reset_mock()

        # Second call with same filter - should hit cache
        result = await cached_registry.get_tools(server_name="test-server")

        assert len(result) == 2
        mock_registry.get_tools.assert_not_called()

    # =========================================================================
    # Cache Invalidation Tests
    # =========================================================================

    async def test_invalidate_server_clears_server_specific_cache(self, cached_registry, redis_cache_service, mock_registry):
        """
        GIVEN tools for a server have been cached
        WHEN invalidate_server is called
        THEN the cached data should be cleared.
        """
        # Populate cache
        await cached_registry.get_tools(server_name="test-server")

        # Verify cache was populated
        cached = await redis_cache_service.aget("mcp:tools:test-server")
        assert cached is not None

        # Invalidate
        await cached_registry.invalidate_server("test-server")

        # Cache should be cleared
        cached = await redis_cache_service.aget("mcp:tools:test-server")
        assert cached is None

    async def test_invalidate_server_also_clears_all_cache(self, cached_registry, redis_cache_service, mock_registry):
        """
        GIVEN "all" tools have been cached
        WHEN invalidate_server is called
        THEN the "all" cache should also be cleared.
        """
        # Populate "all" cache
        await cached_registry.get_tools()

        # Verify cache was populated
        cached = await redis_cache_service.aget("mcp:tools:all")
        assert cached is not None

        # Invalidate a server
        await cached_registry.invalidate_server("test-server")

        # "all" cache should be cleared (contains this server's data)
        cached = await redis_cache_service.aget("mcp:tools:all")
        assert cached is None

    async def test_invalidate_all_clears_all_mcp_cache(self, cached_registry, redis_cache_service, mock_registry):
        """
        GIVEN various MCP data has been cached
        WHEN invalidate_all is called
        THEN all MCP cache entries should be cleared.
        """
        # Populate multiple caches
        await cached_registry.get_tools()
        await cached_registry.get_resources()
        await cached_registry.get_prompts()
        await cached_registry.get_server_names()
        await cached_registry.get_server_capabilities("test-server")

        # Invalidate all
        await cached_registry.invalidate_all()

        # All caches should be cleared
        assert await redis_cache_service.aget("mcp:tools:all") is None
        assert await redis_cache_service.aget("mcp:resources:all") is None
        assert await redis_cache_service.aget("mcp:prompts:all") is None
        assert await redis_cache_service.aget("mcp:servers:all") is None
        assert await redis_cache_service.aget("mcp:server:test-server:capabilities") is None

    # =========================================================================
    # TTL Expiration Tests
    # =========================================================================

    async def test_cache_expires_after_ttl(self, mock_registry):
        """
        GIVEN data has been cached with a short TTL
        WHEN the TTL expires (both L1 and L2)
        THEN the next request should fetch from registry.
        """
        from mcp_server_langgraph.core.cache import CacheService
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        # Create cache service with short L1 TTL as well
        short_ttl_cache = CacheService(
            redis_url=f"redis://localhost:{TEST_REDIS_PORT}",
            redis_db=14,
            l1_ttl=1,  # 1 second L1 TTL
            l1_maxsize=100,
        )

        try:
            # Create registry with very short TTL for L2
            short_ttl_registry = CachedUnifiedRegistry(
                registry=mock_registry,
                cache=short_ttl_cache,
                ttl=1,  # 1 second L2 TTL
            )

            # First call - cache miss
            await short_ttl_registry.get_tools()
            mock_registry.get_tools.reset_mock()

            # Wait for both L1 and L2 TTLs to expire
            await asyncio.sleep(1.5)

            # Clear L1 cache to ensure we test L2 expiration
            short_ttl_cache.l1_cache.clear()

            # Second call - should be a cache miss (L2 expired)
            await short_ttl_registry.get_tools()

            # Registry should have been called again
            mock_registry.get_tools.assert_called_once()
        finally:
            # Cleanup
            try:
                if short_ttl_cache.redis is not None:
                    await short_ttl_cache.redis.flushdb()
            except Exception:
                pass

    # =========================================================================
    # Graceful Degradation Tests
    # =========================================================================

    async def test_cache_failure_falls_back_to_registry(self, mock_registry):
        """
        GIVEN cache operations fail
        WHEN get_tools is called
        THEN it should gracefully fall back to registry.
        """
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        # Create mock cache that fails
        failing_cache = MagicMock()
        failing_cache.aget = MagicMock(side_effect=Exception("Redis connection failed"))
        failing_cache.aset = MagicMock(side_effect=Exception("Redis connection failed"))

        # Make aget and aset async
        async def failing_aget(*args, **kwargs):
            raise Exception("Redis connection failed")

        async def failing_aset(*args, **kwargs):
            raise Exception("Redis connection failed")

        failing_cache.aget = failing_aget
        failing_cache.aset = failing_aset

        fallback_registry = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=failing_cache,
            ttl=60,
        )

        # Should not raise - should fall back to registry
        result = await fallback_registry.get_tools()

        assert len(result) == 2
        mock_registry.get_tools.assert_called_once()

    # =========================================================================
    # Data Serialization Tests
    # =========================================================================

    async def test_cached_data_preserves_structure(self, cached_registry, mock_registry):
        """
        GIVEN data has been serialized and cached
        WHEN data is retrieved from cache
        THEN the structure should be preserved correctly.
        """
        # First call - populates cache
        await cached_registry.get_tools()
        mock_registry.get_tools.reset_mock()

        # Second call - from cache
        result = await cached_registry.get_tools()

        # Verify structure is preserved
        tool = result[0]
        assert "qualified_name" in tool
        assert "server_name" in tool
        assert "name" in tool
        assert "description" in tool
        assert "input_schema" in tool
        assert tool["qualified_name"] == "test-server:search_files"

    async def test_cached_resources_preserves_structure(self, cached_registry, mock_registry):
        """
        GIVEN resources have been serialized and cached
        WHEN resources are retrieved from cache
        THEN the structure should be preserved correctly.
        """
        # First call - populates cache
        await cached_registry.get_resources()
        mock_registry.get_resources.reset_mock()

        # Second call - from cache
        result = await cached_registry.get_resources()

        # Verify structure is preserved
        resource = result[0]
        assert "qualified_name" in resource
        assert "server_name" in resource
        assert "name" in resource
        assert "uri" in resource
        assert "mime_type" in resource

    async def test_cached_prompts_preserves_structure(self, cached_registry, mock_registry):
        """
        GIVEN prompts have been serialized and cached
        WHEN prompts are retrieved from cache
        THEN the structure should be preserved correctly.
        """
        # First call - populates cache
        await cached_registry.get_prompts()
        mock_registry.get_prompts.reset_mock()

        # Second call - from cache
        result = await cached_registry.get_prompts()

        # Verify structure is preserved
        prompt = result[0]
        assert "qualified_name" in prompt
        assert "server_name" in prompt
        assert "name" in prompt
        assert "description" in prompt
        assert "arguments" in prompt

    # =========================================================================
    # Passthrough Method Tests
    # =========================================================================

    async def test_get_tool_passes_through_to_registry(self, cached_registry, mock_registry):
        """
        GIVEN a cached registry
        WHEN get_tool is called with a qualified name
        THEN it should pass through directly to the underlying registry.
        """
        mock_registry.get_tool = MagicMock(return_value={"name": "test_tool"})

        result = cached_registry.get_tool("test-server:test_tool")

        mock_registry.get_tool.assert_called_once_with("test-server:test_tool")
        assert result == {"name": "test_tool"}

    async def test_get_resource_passes_through_to_registry(self, cached_registry, mock_registry):
        """
        GIVEN a cached registry
        WHEN get_resource is called with a qualified name
        THEN it should pass through directly to the underlying registry.
        """
        mock_registry.get_resource = MagicMock(return_value={"name": "test_resource"})

        result = cached_registry.get_resource("test-server:test_resource")

        mock_registry.get_resource.assert_called_once_with("test-server:test_resource")
        assert result == {"name": "test_resource"}

    async def test_get_prompt_passes_through_to_registry(self, cached_registry, mock_registry):
        """
        GIVEN a cached registry
        WHEN get_prompt is called with a qualified name
        THEN it should pass through directly to the underlying registry.
        """
        mock_registry.get_prompt = MagicMock(return_value={"name": "test_prompt"})

        result = cached_registry.get_prompt("test-server:test_prompt")

        mock_registry.get_prompt.assert_called_once_with("test-server:test_prompt")
        assert result == {"name": "test_prompt"}

    # =========================================================================
    # L1 + L2 Tiered Cache Tests
    # =========================================================================

    async def test_l1_cache_is_populated_from_l2(self, cached_registry, redis_cache_service, mock_registry):
        """
        GIVEN data exists in L2 (Redis) but not in L1
        WHEN get_tools is called
        THEN data should be retrieved from L2 and populate L1.
        """
        # First call - populates both L1 and L2
        await cached_registry.get_tools()
        mock_registry.get_tools.reset_mock()

        # Clear L1 cache only
        redis_cache_service.l1_cache.clear()

        # Second call - should hit L2 and repopulate L1
        result = await cached_registry.get_tools()

        assert len(result) == 2
        mock_registry.get_tools.assert_not_called()

    async def test_l1_hit_does_not_query_l2(self, cached_registry, redis_cache_service, mock_registry):
        """
        GIVEN data exists in L1 cache
        WHEN get_tools is called
        THEN data should be retrieved from L1 without hitting L2.
        """
        # First call - populates L1 and L2
        await cached_registry.get_tools()

        # Second call should hit L1 directly
        result = await cached_registry.get_tools()

        assert len(result) == 2
        # Registry should only have been called once (first call)
        mock_registry.get_tools.assert_called_once()
