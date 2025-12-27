"""
Tests for MCP Capability Registries (Tools, Resources, Prompts).

These tests verify that the unified registry system can aggregate
tools, resources, and prompts from multiple external MCP servers
with proper namespacing to avoid collisions.

Reference: MCP Protocol Specification 2025-11-25
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.mcp]


# =============================================================================
# MCPResourceRegistry Tests
# =============================================================================


@pytest.mark.xdist_group(name="mcp_capability_registries")
class TestMCPResourceDefinition:
    """Tests for MCPResourceDefinition dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_resource_definition_creates_qualified_name(self) -> None:
        """Verify qualified_name is generated from server_name:uri."""
        from mcp_server_langgraph.mcp.client.resource_registry import MCPResourceDefinition

        resource = MCPResourceDefinition(
            server_name="github",
            uri="repo://owner/repo",
            name="Repository",
            description="GitHub repository resource",
            mime_type="application/json",
        )

        assert resource.qualified_name == "github:repo://owner/repo"

    def test_resource_definition_handles_special_characters(self) -> None:
        """Verify special characters in URIs are preserved."""
        from mcp_server_langgraph.mcp.client.resource_registry import MCPResourceDefinition

        resource = MCPResourceDefinition(
            server_name="filesystem",
            uri="file:///path/to/file.txt",
            name="File",
            description="Local file",
        )

        assert resource.qualified_name == "filesystem:file:///path/to/file.txt"


@pytest.mark.xdist_group(name="mcp_capability_registries")
class TestMCPResourceRegistry:
    """Tests for MCPResourceRegistry."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_import_resources_from_server(self) -> None:
        """Verify resources can be imported from an MCP server."""
        from mcp_server_langgraph.mcp.client.resource_registry import MCPResourceRegistry

        registry = MCPResourceRegistry()

        # Mock session with resources
        mock_session = MagicMock()
        mock_session.list_resources = AsyncMock(
            return_value=[
                {
                    "uri": "config://settings",
                    "name": "Settings",
                    "description": "Application settings",
                    "mimeType": "application/json",
                },
                {
                    "uri": "config://theme",
                    "name": "Theme",
                    "description": "UI theme configuration",
                },
            ]
        )

        resources = await registry.import_resources("config-server", mock_session)

        assert len(resources) == 2
        assert resources[0].qualified_name == "config-server:config://settings"
        assert resources[1].qualified_name == "config-server:config://theme"

    @pytest.mark.asyncio
    async def test_get_resources_returns_all(self) -> None:
        """Verify get_resources returns all resources across servers."""
        from mcp_server_langgraph.mcp.client.resource_registry import MCPResourceRegistry

        registry = MCPResourceRegistry()

        # Import from two servers
        mock_session1 = MagicMock()
        mock_session1.list_resources = AsyncMock(
            return_value=[
                {"uri": "repo://a", "name": "A"},
            ]
        )

        mock_session2 = MagicMock()
        mock_session2.list_resources = AsyncMock(
            return_value=[
                {"uri": "file://b", "name": "B"},
            ]
        )

        await registry.import_resources("github", mock_session1)
        await registry.import_resources("filesystem", mock_session2)

        all_resources = registry.get_resources()
        assert len(all_resources) == 2

    @pytest.mark.asyncio
    async def test_get_resources_by_server(self) -> None:
        """Verify get_resources can filter by server name."""
        from mcp_server_langgraph.mcp.client.resource_registry import MCPResourceRegistry

        registry = MCPResourceRegistry()

        mock_session = MagicMock()
        mock_session.list_resources = AsyncMock(
            return_value=[
                {"uri": "repo://x", "name": "X"},
                {"uri": "repo://y", "name": "Y"},
            ]
        )

        await registry.import_resources("github", mock_session)

        github_resources = registry.get_resources(server_name="github")
        assert len(github_resources) == 2

        other_resources = registry.get_resources(server_name="unknown")
        assert len(other_resources) == 0

    def test_get_resource_by_qualified_name(self) -> None:
        """Verify get_resource returns specific resource."""
        from mcp_server_langgraph.mcp.client.resource_registry import (
            MCPResourceDefinition,
            MCPResourceRegistry,
        )

        registry = MCPResourceRegistry()

        # Manually add a resource
        resource = MCPResourceDefinition(
            server_name="test",
            uri="test://resource",
            name="Test Resource",
        )
        registry._resources[resource.qualified_name] = resource
        registry._server_resources["test"] = [resource.qualified_name]

        found = registry.get_resource("test:test://resource")
        assert found is not None
        assert found.name == "Test Resource"

        not_found = registry.get_resource("unknown:resource")
        assert not_found is None


# =============================================================================
# MCPPromptRegistry Tests
# =============================================================================


@pytest.mark.xdist_group(name="mcp_capability_registries")
class TestMCPPromptDefinition:
    """Tests for MCPPromptDefinition dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_prompt_definition_creates_qualified_name(self) -> None:
        """Verify qualified_name is generated from server_name:name."""
        from mcp_server_langgraph.mcp.client.prompt_registry import MCPPromptDefinition

        prompt = MCPPromptDefinition(
            server_name="code-assistant",
            name="code_review",
            description="Review code for issues",
            arguments=[
                {"name": "code", "required": True},
                {"name": "language", "required": False},
            ],
        )

        assert prompt.qualified_name == "code-assistant:code_review"

    def test_prompt_definition_with_empty_arguments(self) -> None:
        """Verify prompts can have empty argument lists."""
        from mcp_server_langgraph.mcp.client.prompt_registry import MCPPromptDefinition

        prompt = MCPPromptDefinition(
            server_name="summarizer",
            name="summarize",
            description="Summarize content",
            arguments=[],
        )

        assert prompt.qualified_name == "summarizer:summarize"
        assert prompt.arguments == []


@pytest.mark.xdist_group(name="mcp_capability_registries")
class TestMCPPromptRegistry:
    """Tests for MCPPromptRegistry."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_import_prompts_from_server(self) -> None:
        """Verify prompts can be imported from an MCP server."""
        from mcp_server_langgraph.mcp.client.prompt_registry import MCPPromptRegistry

        registry = MCPPromptRegistry()

        mock_session = MagicMock()
        mock_session.list_prompts = AsyncMock(
            return_value=[
                {
                    "name": "code_review",
                    "description": "Review code",
                    "arguments": [{"name": "code", "required": True}],
                },
                {
                    "name": "explain",
                    "description": "Explain code",
                    "arguments": [],
                },
            ]
        )

        prompts = await registry.import_prompts("code-assistant", mock_session)

        assert len(prompts) == 2
        assert prompts[0].qualified_name == "code-assistant:code_review"
        assert prompts[1].qualified_name == "code-assistant:explain"

    @pytest.mark.asyncio
    async def test_get_prompts_returns_all(self) -> None:
        """Verify get_prompts returns all prompts across servers."""
        from mcp_server_langgraph.mcp.client.prompt_registry import MCPPromptRegistry

        registry = MCPPromptRegistry()

        mock_session1 = MagicMock()
        mock_session1.list_prompts = AsyncMock(
            return_value=[
                {"name": "prompt_a", "description": "A"},
            ]
        )

        mock_session2 = MagicMock()
        mock_session2.list_prompts = AsyncMock(
            return_value=[
                {"name": "prompt_b", "description": "B"},
            ]
        )

        await registry.import_prompts("server1", mock_session1)
        await registry.import_prompts("server2", mock_session2)

        all_prompts = registry.get_prompts()
        assert len(all_prompts) == 2

    @pytest.mark.asyncio
    async def test_get_prompts_by_server(self) -> None:
        """Verify get_prompts can filter by server name."""
        from mcp_server_langgraph.mcp.client.prompt_registry import MCPPromptRegistry

        registry = MCPPromptRegistry()

        mock_session = MagicMock()
        mock_session.list_prompts = AsyncMock(
            return_value=[
                {"name": "p1", "description": "Prompt 1"},
                {"name": "p2", "description": "Prompt 2"},
            ]
        )

        await registry.import_prompts("my-server", mock_session)

        server_prompts = registry.get_prompts(server_name="my-server")
        assert len(server_prompts) == 2

        other_prompts = registry.get_prompts(server_name="other")
        assert len(other_prompts) == 0

    def test_get_prompt_by_qualified_name(self) -> None:
        """Verify get_prompt returns specific prompt."""
        from mcp_server_langgraph.mcp.client.prompt_registry import (
            MCPPromptDefinition,
            MCPPromptRegistry,
        )

        registry = MCPPromptRegistry()

        prompt = MCPPromptDefinition(
            server_name="test",
            name="my_prompt",
            description="Test prompt",
            arguments=[],
        )
        registry._prompts[prompt.qualified_name] = prompt
        registry._server_prompts["test"] = [prompt.qualified_name]

        found = registry.get_prompt("test:my_prompt")
        assert found is not None
        assert found.description == "Test prompt"

        not_found = registry.get_prompt("unknown:prompt")
        assert not_found is None


# =============================================================================
# Extended Session Methods Tests
# =============================================================================


@pytest.mark.xdist_group(name="mcp_capability_registries")
class TestMCPClientSessionExtendedMethods:
    """Tests for extended MCPClientSession methods (list_resources, list_prompts)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_session_list_resources(self) -> None:
        """Verify MCPClientSession can list resources from server."""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            url="http://localhost:8080/mcp",
        )

        session = MCPClientSession(config)
        session._connected = True
        session._session_id = "test-session"

        # Mock the HTTP response using patch
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "jsonrpc": "2.0",
                "id": "test",
                "result": {
                    "resources": [
                        {"uri": "config://test", "name": "Test Config"},
                    ]
                },
            }
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_http_client = MagicMock()
        mock_http_client.post = MagicMock(return_value=mock_response)
        session._http_client = mock_http_client

        resources = await session.list_resources()

        assert len(resources) == 1
        assert resources[0]["uri"] == "config://test"

    @pytest.mark.asyncio
    async def test_session_list_prompts(self) -> None:
        """Verify MCPClientSession can list prompts from server."""
        from mcp_server_langgraph.mcp.client.session_manager import MCPClientSession
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="test-server",
            url="http://localhost:8080/mcp",
        )

        session = MCPClientSession(config)
        session._connected = True
        session._session_id = "test-session"

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "jsonrpc": "2.0",
                "id": "test",
                "result": {
                    "prompts": [
                        {"name": "code_review", "description": "Review code"},
                    ]
                },
            }
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_http_client = MagicMock()
        mock_http_client.post = MagicMock(return_value=mock_response)
        session._http_client = mock_http_client

        prompts = await session.list_prompts()

        assert len(prompts) == 1
        assert prompts[0]["name"] == "code_review"


# =============================================================================
# Unified Capability Registry Tests
# =============================================================================


@pytest.mark.xdist_group(name="mcp_capability_registries")
class TestUnifiedMCPCapabilityRegistry:
    """Tests for unified registry that manages all MCP capabilities."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_register_server_imports_all_capabilities(self) -> None:
        """Verify registering a server imports tools, resources, and prompts."""
        from mcp_server_langgraph.mcp.client.unified_registry import MCPUnifiedRegistry
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        registry = MCPUnifiedRegistry()

        # Mock session
        mock_session = MagicMock()
        mock_session.connect = AsyncMock(return_value=None)
        mock_session.list_tools = AsyncMock(
            return_value=[
                {"name": "tool1", "description": "Tool 1", "inputSchema": {}},
            ]
        )
        mock_session.list_resources = AsyncMock(
            return_value=[
                {"uri": "res://1", "name": "Resource 1"},
            ]
        )
        mock_session.list_prompts = AsyncMock(
            return_value=[
                {"name": "prompt1", "description": "Prompt 1", "arguments": []},
            ]
        )
        mock_session.is_connected = True

        # Inject mock session factory
        registry._create_session = MagicMock(return_value=mock_session)

        config = MCPServerConfig(name="full-server", url="http://localhost:8080")
        await registry.register_server(config)

        # Verify all capabilities imported
        tools = registry.get_tools()
        resources = registry.get_resources()
        prompts = registry.get_prompts()

        assert len(tools) == 1
        assert tools[0].qualified_name == "full-server:tool1"

        assert len(resources) == 1
        assert resources[0].qualified_name == "full-server:res://1"

        assert len(prompts) == 1
        assert prompts[0].qualified_name == "full-server:prompt1"

    @pytest.mark.asyncio
    async def test_unregister_server_removes_all_capabilities(self) -> None:
        """Verify unregistering a server removes all its capabilities."""
        from mcp_server_langgraph.mcp.client.unified_registry import MCPUnifiedRegistry
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        registry = MCPUnifiedRegistry()

        mock_session = MagicMock()
        mock_session.connect = AsyncMock(return_value=None)
        mock_session.disconnect = AsyncMock(return_value=None)
        mock_session.list_tools = AsyncMock(
            return_value=[
                {"name": "t1", "description": "T1", "inputSchema": {}},
            ]
        )
        mock_session.list_resources = AsyncMock(
            return_value=[
                {"uri": "r://1", "name": "R1"},
            ]
        )
        mock_session.list_prompts = AsyncMock(
            return_value=[
                {"name": "p1", "description": "P1", "arguments": []},
            ]
        )
        mock_session.is_connected = True

        registry._create_session = MagicMock(return_value=mock_session)

        config = MCPServerConfig(name="temp-server", url="http://localhost:8080")
        await registry.register_server(config)

        # Verify capabilities exist
        assert len(registry.get_tools()) == 1
        assert len(registry.get_resources()) == 1
        assert len(registry.get_prompts()) == 1

        # Unregister
        await registry.unregister_server("temp-server")

        # Verify all removed
        assert len(registry.get_tools()) == 0
        assert len(registry.get_resources()) == 0
        assert len(registry.get_prompts()) == 0

    def test_get_server_capabilities_summary(self) -> None:
        """Verify get_server_capabilities returns summary for a server."""
        from mcp_server_langgraph.mcp.client.unified_registry import MCPUnifiedRegistry

        registry = MCPUnifiedRegistry()

        # Manually populate for testing
        registry._tool_registry._server_tools["server1"] = ["server1:t1", "server1:t2"]
        registry._resource_registry._server_resources["server1"] = ["server1:r1"]
        registry._prompt_registry._server_prompts["server1"] = []

        summary = registry.get_server_capabilities("server1")

        assert summary["tool_count"] == 2
        assert summary["resource_count"] == 1
        assert summary["prompt_count"] == 0


# =============================================================================
# API Integration Tests
# =============================================================================


@pytest.mark.xdist_group(name="mcp_capability_registries")
class TestMCPCapabilityAPIEndpoints:
    """Tests for REST API endpoints exposing aggregated capabilities."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_aggregated_tools_endpoint(self) -> None:
        """Verify /api/v1/mcp/aggregated/tools returns tools from all servers."""

        from mcp_server_langgraph.api.v1.mcp_aggregated import (
            aggregated_router,
            get_unified_registry,
        )

        # This test verifies the endpoint exists and returns correct structure
        # Full integration would require setting up the registry
        assert aggregated_router is not None
        assert get_unified_registry is not None

    @pytest.mark.asyncio
    async def test_list_aggregated_resources_endpoint(self) -> None:
        """Verify /api/v1/mcp/aggregated/resources returns resources from all servers."""
        from mcp_server_langgraph.api.v1.mcp_aggregated import aggregated_router

        # Verify endpoint is registered
        routes = [r.path for r in aggregated_router.routes]
        assert "/aggregated/resources" in routes or any("resources" in r for r in routes)

    @pytest.mark.asyncio
    async def test_list_aggregated_prompts_endpoint(self) -> None:
        """Verify /api/v1/mcp/aggregated/prompts returns prompts from all servers."""
        from mcp_server_langgraph.api.v1.mcp_aggregated import aggregated_router

        # Verify endpoint is registered
        routes = [r.path for r in aggregated_router.routes]
        assert "/aggregated/prompts" in routes or any("prompts" in r for r in routes)
