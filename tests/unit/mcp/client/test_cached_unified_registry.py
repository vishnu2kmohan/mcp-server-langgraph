"""
Tests for Redis Cached MCP Unified Registry Service.

TDD RED Phase: These tests define the expected behavior of CachedUnifiedRegistry.

The cache layer wraps MCPUnifiedRegistry and provides:
- Cache-aside pattern for listing tools/resources/prompts
- Cache invalidation on server registration/unregistration
- TTL-based expiration (30 minutes default)
- Per-server and global cache keys

Reference: MCP Protocol 2025-11-25 capability aggregation
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.mcp]

# Test constants
CACHE_TTL = 1800  # 30 minutes for MCP capabilities
TEST_SERVER_NAME = "test-server"
TEST_QUALIFIED_TOOL_NAME = "test-server:read_file"
TEST_QUALIFIED_RESOURCE_NAME = "test-server:file://readme.md"
TEST_QUALIFIED_PROMPT_NAME = "test-server:code_review"


def create_mock_tool(
    name: str = "read_file",
    server_name: str = TEST_SERVER_NAME,
    description: str = "Read a file from the filesystem",
) -> MagicMock:
    """Create a mock tool definition."""
    tool = MagicMock()
    tool.name = name
    tool.server_name = server_name
    tool.qualified_name = f"{server_name}:{name}"
    tool.description = description
    tool.input_schema = {"type": "object", "properties": {"path": {"type": "string"}}}
    return tool


def create_mock_resource(
    uri: str = "file://readme.md",
    server_name: str = TEST_SERVER_NAME,
    name: str = "readme.md",
) -> MagicMock:
    """Create a mock resource definition."""
    resource = MagicMock()
    resource.uri = uri
    resource.server_name = server_name
    resource.name = name
    resource.qualified_name = f"{server_name}:{uri}"
    resource.description = "README file"
    resource.mime_type = "text/markdown"
    return resource


def create_mock_prompt(
    name: str = "code_review",
    server_name: str = TEST_SERVER_NAME,
) -> MagicMock:
    """Create a mock prompt definition."""
    prompt = MagicMock()
    prompt.name = name
    prompt.server_name = server_name
    prompt.qualified_name = f"{server_name}:{name}"
    prompt.description = "Review code for issues"
    prompt.arguments = [
        {"name": "code", "required": True, "description": "Code to review"},
    ]
    return prompt


def create_serializable_tool_dict(
    name: str = "read_file",
    server_name: str = TEST_SERVER_NAME,
) -> dict[str, Any]:
    """Create a serializable tool dict for cache storage."""
    return {
        "name": name,
        "server_name": server_name,
        "qualified_name": f"{server_name}:{name}",
        "description": "Read a file from the filesystem",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}},
    }


def create_serializable_resource_dict(
    uri: str = "file://readme.md",
    server_name: str = TEST_SERVER_NAME,
    name: str = "readme.md",
) -> dict[str, Any]:
    """Create a serializable resource dict for cache storage."""
    return {
        "uri": uri,
        "server_name": server_name,
        "name": name,
        "qualified_name": f"{server_name}:{uri}",
        "description": "README file",
        "mime_type": "text/markdown",
    }


def create_serializable_prompt_dict(
    name: str = "code_review",
    server_name: str = TEST_SERVER_NAME,
) -> dict[str, Any]:
    """Create a serializable prompt dict for cache storage."""
    return {
        "name": name,
        "server_name": server_name,
        "qualified_name": f"{server_name}:{name}",
        "description": "Review code for issues",
        "arguments": [
            {"name": "code", "required": True, "description": "Code to review"},
        ],
    }


# =============================================================================
# Tests for Cache-Aside Read Pattern
# =============================================================================


@pytest.mark.xdist_group(name="test_cached_unified_registry")
@pytest.mark.unit
class TestCachedUnifiedRegistryGetTools:
    """Tests for get_tools cache-aside pattern."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_tools_returns_cached_on_hit(self) -> None:
        """Test that get_tools returns cached tools without hitting registry."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_cache = MagicMock()

        # Cache hit - return serialized tools
        cached_tools = [create_serializable_tool_dict()]
        mock_cache.aget = AsyncMock(return_value=cached_tools)

        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        result = await service.get_tools()

        # Assert
        assert len(result) == 1
        assert result[0]["qualified_name"] == TEST_QUALIFIED_TOOL_NAME
        # Registry should NOT be called on cache hit
        mock_registry.get_tools.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_tools_fetches_from_registry_on_cache_miss(self) -> None:
        """Test that get_tools fetches from registry on cache miss."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_cache = MagicMock()

        # Cache miss
        mock_cache.aget = AsyncMock(return_value=None)
        mock_cache.aset = AsyncMock(return_value=None)

        # Registry has tools
        mock_registry.get_tools.return_value = [create_mock_tool()]

        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        result = await service.get_tools()

        # Assert
        assert len(result) == 1
        # Registry should be called
        mock_registry.get_tools.assert_called_once_with(None)
        # Cache should be populated
        mock_cache.aset.assert_awaited()

    @pytest.mark.asyncio
    async def test_get_tools_with_server_filter_uses_separate_cache_key(self) -> None:
        """Test that get_tools with server filter uses different cache key."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_cache = MagicMock()

        # Cache miss
        mock_cache.aget = AsyncMock(return_value=None)
        mock_cache.aset = AsyncMock(return_value=None)

        # Registry has tools
        mock_registry.get_tools.return_value = [create_mock_tool()]

        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        await service.get_tools(server_name=TEST_SERVER_NAME)

        # Assert - cache key should include server name
        cache_get_call = mock_cache.aget.call_args
        assert TEST_SERVER_NAME in cache_get_call[0][0]

    @pytest.mark.asyncio
    async def test_get_tools_gracefully_handles_cache_failure(self) -> None:
        """Test that get_tools falls back to registry on cache failure."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_cache = MagicMock()

        # Cache raises exception
        mock_cache.aget = AsyncMock(side_effect=Exception("Redis connection failed"))
        mock_cache.aset = AsyncMock(return_value=None)

        # Registry has tools
        mock_registry.get_tools.return_value = [create_mock_tool()]

        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act - should not raise, should fall back to registry
        result = await service.get_tools()

        # Assert
        assert len(result) == 1
        mock_registry.get_tools.assert_called_once()


@pytest.mark.xdist_group(name="test_cached_unified_registry")
@pytest.mark.unit
class TestCachedUnifiedRegistryGetResources:
    """Tests for get_resources cache-aside pattern."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_resources_returns_cached_on_hit(self) -> None:
        """Test that get_resources returns cached resources without hitting registry."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_cache = MagicMock()

        # Cache hit
        cached_resources = [create_serializable_resource_dict()]
        mock_cache.aget = AsyncMock(return_value=cached_resources)

        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        result = await service.get_resources()

        # Assert
        assert len(result) == 1
        assert result[0]["qualified_name"] == TEST_QUALIFIED_RESOURCE_NAME
        mock_registry.get_resources.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_resources_fetches_from_registry_on_cache_miss(self) -> None:
        """Test that get_resources fetches from registry on cache miss."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_cache = MagicMock()

        # Cache miss
        mock_cache.aget = AsyncMock(return_value=None)
        mock_cache.aset = AsyncMock(return_value=None)

        # Registry has resources
        mock_registry.get_resources.return_value = [create_mock_resource()]

        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        result = await service.get_resources()

        # Assert
        assert len(result) == 1
        mock_registry.get_resources.assert_called_once_with(None)
        mock_cache.aset.assert_awaited()


@pytest.mark.xdist_group(name="test_cached_unified_registry")
@pytest.mark.unit
class TestCachedUnifiedRegistryGetPrompts:
    """Tests for get_prompts cache-aside pattern."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_prompts_returns_cached_on_hit(self) -> None:
        """Test that get_prompts returns cached prompts without hitting registry."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_cache = MagicMock()

        # Cache hit
        cached_prompts = [create_serializable_prompt_dict()]
        mock_cache.aget = AsyncMock(return_value=cached_prompts)

        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        result = await service.get_prompts()

        # Assert
        assert len(result) == 1
        assert result[0]["qualified_name"] == TEST_QUALIFIED_PROMPT_NAME
        mock_registry.get_prompts.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_prompts_fetches_from_registry_on_cache_miss(self) -> None:
        """Test that get_prompts fetches from registry on cache miss."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_cache = MagicMock()

        # Cache miss
        mock_cache.aget = AsyncMock(return_value=None)
        mock_cache.aset = AsyncMock(return_value=None)

        # Registry has prompts
        mock_registry.get_prompts.return_value = [create_mock_prompt()]

        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        result = await service.get_prompts()

        # Assert
        assert len(result) == 1
        mock_registry.get_prompts.assert_called_once_with(None)
        mock_cache.aset.assert_awaited()


# =============================================================================
# Tests for Cache Invalidation
# =============================================================================


@pytest.mark.xdist_group(name="test_cached_unified_registry")
@pytest.mark.unit
class TestCachedUnifiedRegistryInvalidation:
    """Tests for cache invalidation on registry changes."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_invalidate_server_clears_server_cache_keys(self) -> None:
        """Test that invalidate_server clears all cache keys for that server."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_cache = MagicMock()
        mock_cache.adelete_pattern = AsyncMock(return_value=3)

        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        await service.invalidate_server(TEST_SERVER_NAME)

        # Assert - should delete pattern matching server
        mock_cache.adelete_pattern.assert_awaited()
        pattern = mock_cache.adelete_pattern.call_args[0][0]
        assert TEST_SERVER_NAME in pattern or "mcp:" in pattern

    @pytest.mark.asyncio
    async def test_invalidate_all_clears_all_mcp_cache_keys(self) -> None:
        """Test that invalidate_all clears all MCP cache keys."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_cache = MagicMock()
        mock_cache.adelete_pattern = AsyncMock(return_value=10)

        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        await service.invalidate_all()

        # Assert - should delete all mcp:* keys
        mock_cache.adelete_pattern.assert_awaited()
        pattern = mock_cache.adelete_pattern.call_args[0][0]
        assert pattern.startswith("mcp:")

    @pytest.mark.asyncio
    async def test_register_server_invalidates_cache(self) -> None:
        """Test that register_server invalidates relevant cache."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_registry.register_server = AsyncMock(return_value={"tool_count": 1, "resource_count": 0, "prompt_count": 0})
        mock_cache = MagicMock()
        mock_cache.adelete_pattern = AsyncMock(return_value=0)

        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        mock_config = MagicMock()
        mock_config.name = TEST_SERVER_NAME
        await service.register_server(mock_config)

        # Assert - should invalidate cache
        mock_cache.adelete_pattern.assert_awaited()
        mock_registry.register_server.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unregister_server_invalidates_cache(self) -> None:
        """Test that unregister_server invalidates relevant cache."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_registry.unregister_server = AsyncMock(return_value=None)
        mock_cache = MagicMock()
        mock_cache.adelete_pattern = AsyncMock(return_value=3)

        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        await service.unregister_server(TEST_SERVER_NAME)

        # Assert - should invalidate cache for that server
        mock_cache.adelete_pattern.assert_awaited()
        mock_registry.unregister_server.assert_awaited_once_with(TEST_SERVER_NAME)


# =============================================================================
# Tests for Server List Caching
# =============================================================================


@pytest.mark.xdist_group(name="test_cached_unified_registry")
@pytest.mark.unit
class TestCachedUnifiedRegistryServerList:
    """Tests for get_server_names and get_server_capabilities caching."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_server_names_returns_cached_on_hit(self) -> None:
        """Test that get_server_names returns cached list on hit."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_cache = MagicMock()

        # Cache hit
        cached_servers = [TEST_SERVER_NAME, "another-server"]
        mock_cache.aget = AsyncMock(return_value=cached_servers)

        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        result = await service.get_server_names()

        # Assert
        assert len(result) == 2
        assert TEST_SERVER_NAME in result
        mock_registry.get_server_names.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_server_capabilities_returns_cached_on_hit(self) -> None:
        """Test that get_server_capabilities returns cached data on hit."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_cache = MagicMock()

        # Cache hit
        cached_capabilities = {
            "tool_count": 5,
            "resource_count": 3,
            "prompt_count": 2,
        }
        mock_cache.aget = AsyncMock(return_value=cached_capabilities)

        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act
        result = await service.get_server_capabilities(TEST_SERVER_NAME)

        # Assert
        assert result["tool_count"] == 5
        assert result["resource_count"] == 3
        assert result["prompt_count"] == 2
        mock_registry.get_server_capabilities.assert_not_called()


# =============================================================================
# Tests for Cache Key Generation
# =============================================================================


@pytest.mark.xdist_group(name="test_cached_unified_registry")
@pytest.mark.unit
class TestCacheKeyGeneration:
    """Tests for cache key generation patterns."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_generate_tools_cache_key_all(self) -> None:
        """Test cache key for all tools."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            generate_tools_cache_key,
        )

        key = generate_tools_cache_key(None)
        assert key == "mcp:tools:all"

    def test_generate_tools_cache_key_server_filtered(self) -> None:
        """Test cache key for server-filtered tools."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            generate_tools_cache_key,
        )

        key = generate_tools_cache_key(TEST_SERVER_NAME)
        assert key == f"mcp:tools:{TEST_SERVER_NAME}"

    def test_generate_resources_cache_key_all(self) -> None:
        """Test cache key for all resources."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            generate_resources_cache_key,
        )

        key = generate_resources_cache_key(None)
        assert key == "mcp:resources:all"

    def test_generate_prompts_cache_key_all(self) -> None:
        """Test cache key for all prompts."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            generate_prompts_cache_key,
        )

        key = generate_prompts_cache_key(None)
        assert key == "mcp:prompts:all"

    def test_generate_server_list_cache_key(self) -> None:
        """Test cache key for server list."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            generate_server_list_cache_key,
        )

        key = generate_server_list_cache_key()
        assert key == "mcp:servers:all"

    def test_generate_server_capabilities_cache_key(self) -> None:
        """Test cache key for server capabilities."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            generate_server_capabilities_cache_key,
        )

        key = generate_server_capabilities_cache_key(TEST_SERVER_NAME)
        assert key == f"mcp:server:{TEST_SERVER_NAME}:capabilities"


# =============================================================================
# Tests for Broadcaster Integration
# =============================================================================


@pytest.mark.xdist_group(name="test_cached_unified_registry")
@pytest.mark.unit
class TestCachedUnifiedRegistryBroadcasterIntegration:
    """Tests for broadcaster integration with registry events.

    When servers are registered/unregistered, the broadcaster should be
    notified to push real-time updates to WebSocket clients.

    Reference: MCP Protocol 2025-11-25 capability aggregation
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_register_server_broadcasts_server_registered_event(self) -> None:
        """Test that register_server broadcasts server_registered event."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_registry.register_server = AsyncMock(return_value={"tool_count": 5, "resource_count": 3, "prompt_count": 2})
        mock_cache = MagicMock()
        mock_cache.adelete_pattern = AsyncMock(return_value=0)

        mock_broadcaster = MagicMock()
        mock_broadcaster.broadcast_server_registered = AsyncMock(return_value=None)

        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
            broadcaster=mock_broadcaster,
        )

        # Act
        mock_config = MagicMock()
        mock_config.name = TEST_SERVER_NAME
        await service.register_server(mock_config)

        # Assert - broadcaster should be called with server registration event
        mock_broadcaster.broadcast_server_registered.assert_awaited_once_with(
            server_name=TEST_SERVER_NAME,
            tool_count=5,
            resource_count=3,
            prompt_count=2,
        )

    @pytest.mark.asyncio
    async def test_unregister_server_broadcasts_server_unregistered_event(self) -> None:
        """Test that unregister_server broadcasts server_unregistered event."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_registry.unregister_server = AsyncMock(return_value=None)
        mock_cache = MagicMock()
        mock_cache.adelete_pattern = AsyncMock(return_value=3)

        mock_broadcaster = MagicMock()
        mock_broadcaster.broadcast_server_unregistered = AsyncMock(return_value=None)

        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
            broadcaster=mock_broadcaster,
        )

        # Act
        await service.unregister_server(TEST_SERVER_NAME)

        # Assert - broadcaster should be called with server unregistration event
        mock_broadcaster.broadcast_server_unregistered.assert_awaited_once_with(
            server_name=TEST_SERVER_NAME,
        )

    @pytest.mark.asyncio
    async def test_refresh_all_broadcasts_capability_changed_events(self) -> None:
        """Test that refresh_all broadcasts capability changed events."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_registry.refresh_all = AsyncMock(return_value={"tool_count": 10, "resource_count": 5, "prompt_count": 3})
        mock_cache = MagicMock()
        mock_cache.adelete_pattern = AsyncMock(return_value=3)

        mock_broadcaster = MagicMock()
        mock_broadcaster.broadcast_tools_changed = AsyncMock(return_value=None)
        mock_broadcaster.broadcast_resources_changed = AsyncMock(return_value=None)
        mock_broadcaster.broadcast_prompts_changed = AsyncMock(return_value=None)

        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
            broadcaster=mock_broadcaster,
        )

        # Act
        await service.refresh_all(TEST_SERVER_NAME)

        # Assert - all capability changed events should be broadcast
        mock_broadcaster.broadcast_tools_changed.assert_awaited_once_with(
            server_name=TEST_SERVER_NAME,
            count=10,
        )
        mock_broadcaster.broadcast_resources_changed.assert_awaited_once_with(
            server_name=TEST_SERVER_NAME,
            count=5,
        )
        mock_broadcaster.broadcast_prompts_changed.assert_awaited_once_with(
            server_name=TEST_SERVER_NAME,
            count=3,
        )

    @pytest.mark.asyncio
    async def test_no_broadcaster_does_not_raise(self) -> None:
        """Test that operations work without a broadcaster configured."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_registry.register_server = AsyncMock(return_value={"tool_count": 1, "resource_count": 0, "prompt_count": 0})
        mock_cache = MagicMock()
        mock_cache.adelete_pattern = AsyncMock(return_value=0)

        # No broadcaster configured
        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Act - should not raise
        mock_config = MagicMock()
        mock_config.name = TEST_SERVER_NAME
        result = await service.register_server(mock_config)

        # Assert
        assert result["tool_count"] == 1


@pytest.mark.xdist_group(name="cached_registry_broadcaster")
class TestCachedUnifiedRegistrySetBroadcaster:
    """Tests for the set_broadcaster() method.

    Tests the ability to set a broadcaster after construction,
    enabling runtime wiring during application startup.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        import gc

        gc.collect()

    @pytest.mark.asyncio
    async def test_set_broadcaster_enables_broadcasting(self) -> None:
        """Test that set_broadcaster enables broadcasting for subsequent operations."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_registry.register_server = AsyncMock(return_value={"tool_count": 5, "resource_count": 2, "prompt_count": 1})
        mock_cache = MagicMock()
        mock_cache.adelete_pattern = AsyncMock(return_value=0)

        # Create without broadcaster
        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
        )

        # Add broadcaster after construction
        mock_broadcaster = MagicMock()
        mock_broadcaster.broadcast_server_registered = AsyncMock(return_value=None)
        service.set_broadcaster(mock_broadcaster)

        # Act
        mock_config = MagicMock()
        mock_config.name = TEST_SERVER_NAME
        await service.register_server(mock_config)

        # Assert - broadcaster should have been called
        mock_broadcaster.broadcast_server_registered.assert_awaited_once_with(
            server_name=TEST_SERVER_NAME,
            tool_count=5,
            resource_count=2,
            prompt_count=1,
        )

    @pytest.mark.asyncio
    async def test_set_broadcaster_replaces_existing_broadcaster(self) -> None:
        """Test that set_broadcaster replaces an existing broadcaster."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_registry.register_server = AsyncMock(return_value={"tool_count": 3, "resource_count": 1, "prompt_count": 0})
        mock_cache = MagicMock()
        mock_cache.adelete_pattern = AsyncMock(return_value=0)

        # Create with initial broadcaster
        old_broadcaster = MagicMock()
        old_broadcaster.broadcast_server_registered = AsyncMock(return_value=None)
        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
            broadcaster=old_broadcaster,
        )

        # Replace with new broadcaster
        new_broadcaster = MagicMock()
        new_broadcaster.broadcast_server_registered = AsyncMock(return_value=None)
        service.set_broadcaster(new_broadcaster)

        # Act
        mock_config = MagicMock()
        mock_config.name = TEST_SERVER_NAME
        await service.register_server(mock_config)

        # Assert - new broadcaster called, old not called
        new_broadcaster.broadcast_server_registered.assert_awaited_once()
        old_broadcaster.broadcast_server_registered.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_set_broadcaster_to_none_disables_broadcasting(self) -> None:
        """Test that set_broadcaster(None) disables broadcasting."""
        from mcp_server_langgraph.mcp.client.cached_unified_registry import (
            CachedUnifiedRegistry,
        )

        mock_registry = MagicMock()
        mock_registry.register_server = AsyncMock(return_value={"tool_count": 1, "resource_count": 0, "prompt_count": 0})
        mock_cache = MagicMock()
        mock_cache.adelete_pattern = AsyncMock(return_value=0)

        # Create with broadcaster
        mock_broadcaster = MagicMock()
        mock_broadcaster.broadcast_server_registered = AsyncMock(return_value=None)
        service = CachedUnifiedRegistry(
            registry=mock_registry,
            cache=mock_cache,
            ttl=CACHE_TTL,
            broadcaster=mock_broadcaster,
        )

        # Disable broadcaster
        service.set_broadcaster(None)

        # Act - should not raise
        mock_config = MagicMock()
        mock_config.name = TEST_SERVER_NAME
        result = await service.register_server(mock_config)

        # Assert - broadcaster not called, operation succeeded
        mock_broadcaster.broadcast_server_registered.assert_not_awaited()
        assert result["tool_count"] == 1
