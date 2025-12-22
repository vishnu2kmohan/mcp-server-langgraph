"""
TDD Tests for MCP Tool Registry

These tests define the expected behavior for the MCPToolRegistry system.
Written FIRST before implementation (RED phase) per ADR-0082.
"""

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.xdist_group(name="mcp_tool_registry")
class TestMCPToolDefinition:
    """Test suite for MCPToolDefinition dataclass."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_tool_definition_creates_qualified_name(self):
        """GIVEN server_name and tool name
        WHEN MCPToolDefinition is created
        THEN qualified_name is set to server_name:tool_name"""
        from mcp_server_langgraph.mcp.client.tool_registry import MCPToolDefinition

        tool = MCPToolDefinition(
            server_name="playwright",
            name="screenshot",
            description="Take a screenshot",
            input_schema={"type": "object", "properties": {}},
        )

        assert tool.qualified_name == "playwright:screenshot"

    @pytest.mark.unit
    def test_tool_definition_stores_all_fields(self):
        """GIVEN all parameters
        WHEN MCPToolDefinition is created
        THEN all fields are stored correctly"""
        from mcp_server_langgraph.mcp.client.tool_registry import MCPToolDefinition

        input_schema = {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        }

        tool = MCPToolDefinition(
            server_name="github",
            name="create_pr",
            description="Create a pull request",
            input_schema=input_schema,
        )

        assert tool.server_name == "github"
        assert tool.name == "create_pr"
        assert tool.description == "Create a pull request"
        assert tool.input_schema == input_schema


@pytest.mark.xdist_group(name="mcp_tool_registry")
class TestMCPServerConfig:
    """Test suite for MCPServerConfig dataclass."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_server_config_stdio_transport(self):
        """GIVEN command and args
        WHEN MCPServerConfig is created
        THEN stdio transport is configured"""
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="playwright",
            command="npx",
            args=["@playwright/mcp@latest"],
        )

        assert config.name == "playwright"
        assert config.command == "npx"
        assert config.args == ["@playwright/mcp@latest"]
        assert config.url is None

    @pytest.mark.unit
    def test_server_config_http_transport(self):
        """GIVEN url
        WHEN MCPServerConfig is created
        THEN http transport is configured"""
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="github",
            url="https://mcp.github.com/v1",
        )

        assert config.name == "github"
        assert config.url == "https://mcp.github.com/v1"
        assert config.command is None

    @pytest.mark.unit
    def test_server_config_defaults(self):
        """GIVEN minimal parameters
        WHEN MCPServerConfig is created
        THEN defaults are applied"""
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(name="test-server")

        assert config.timeout == 30.0
        assert config.tool_allowlist is None
        assert config.tool_blocklist is None
        assert config.env is None
        assert config.auth is None

    @pytest.mark.unit
    def test_server_config_with_allowlist(self):
        """GIVEN tool_allowlist
        WHEN MCPServerConfig is created
        THEN allowlist is stored"""
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="playwright",
            command="npx",
            args=["@playwright/mcp@latest"],
            tool_allowlist=["screenshot", "click", "navigate"],
        )

        assert config.tool_allowlist == ["screenshot", "click", "navigate"]

    @pytest.mark.unit
    def test_server_config_with_blocklist(self):
        """GIVEN tool_blocklist
        WHEN MCPServerConfig is created
        THEN blocklist is stored"""
        from mcp_server_langgraph.mcp.client.tool_registry import MCPServerConfig

        config = MCPServerConfig(
            name="filesystem",
            command="npx",
            args=["@modelcontextprotocol/server-filesystem"],
            tool_blocklist=["delete_file", "write_file"],
        )

        assert config.tool_blocklist == ["delete_file", "write_file"]


@pytest.mark.xdist_group(name="mcp_tool_registry")
class TestMCPToolRegistry:
    """Test suite for MCPToolRegistry class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_registry_initializes_empty(self):
        """GIVEN no parameters
        WHEN MCPToolRegistry is created
        THEN it has no registered servers or tools"""
        from mcp_server_langgraph.mcp.client.tool_registry import MCPToolRegistry

        registry = MCPToolRegistry()

        assert len(registry.get_tools()) == 0
        assert len(registry.get_server_names()) == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_register_server_imports_tools(self):
        """GIVEN an MCP server config
        WHEN register_server is called
        THEN tools from the server are imported"""
        from mcp_server_langgraph.mcp.client.tool_registry import (
            MCPServerConfig,
            MCPToolRegistry,
        )

        registry = MCPToolRegistry()

        # Mock the session creation and tool discovery
        mock_session = AsyncMock()
        mock_session.list_tools.return_value = [
            {
                "name": "screenshot",
                "description": "Take a screenshot",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "click",
                "description": "Click an element",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]
        mock_session.connect = AsyncMock()
        registry._create_session = MagicMock(return_value=mock_session)

        config = MCPServerConfig(
            name="playwright",
            command="npx",
            args=["@playwright/mcp@latest"],
        )

        tools = await registry.register_server(config)

        assert len(tools) == 2
        assert any(t.name == "screenshot" for t in tools)
        assert any(t.name == "click" for t in tools)
        assert all(t.server_name == "playwright" for t in tools)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unregister_server_removes_tools(self):
        """GIVEN a registered server
        WHEN unregister_server is called
        THEN the server's tools are removed"""
        from mcp_server_langgraph.mcp.client.tool_registry import (
            MCPServerConfig,
            MCPToolRegistry,
        )

        registry = MCPToolRegistry()

        # Mock setup
        mock_session = AsyncMock()
        mock_session.list_tools.return_value = [
            {
                "name": "screenshot",
                "description": "Take a screenshot",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]
        mock_session.connect = AsyncMock()
        mock_session.disconnect = AsyncMock()
        registry._create_session = MagicMock(return_value=mock_session)

        config = MCPServerConfig(name="playwright", command="npx", args=[])
        await registry.register_server(config)

        # Verify tools exist
        assert len(registry.get_tools()) == 1

        # Unregister
        await registry.unregister_server("playwright")

        assert len(registry.get_tools()) == 0
        assert "playwright" not in registry.get_server_names()
        mock_session.disconnect.assert_called_once()

    @pytest.mark.unit
    def test_get_tools_returns_all_tools(self):
        """GIVEN multiple registered servers
        WHEN get_tools is called without server_name
        THEN all tools from all servers are returned"""
        from mcp_server_langgraph.mcp.client.tool_registry import (
            MCPToolDefinition,
            MCPToolRegistry,
        )

        registry = MCPToolRegistry()

        # Manually add tools (simulate registered servers)
        registry._tools["playwright:screenshot"] = MCPToolDefinition(
            server_name="playwright",
            name="screenshot",
            description="Take a screenshot",
            input_schema={},
        )
        registry._tools["github:create_pr"] = MCPToolDefinition(
            server_name="github",
            name="create_pr",
            description="Create a PR",
            input_schema={},
        )

        tools = registry.get_tools()

        assert len(tools) == 2
        qualified_names = [t.qualified_name for t in tools]
        assert "playwright:screenshot" in qualified_names
        assert "github:create_pr" in qualified_names

    @pytest.mark.unit
    def test_get_tools_by_server_filters_correctly(self):
        """GIVEN multiple registered servers
        WHEN get_tools is called with server_name
        THEN only tools from that server are returned"""
        from mcp_server_langgraph.mcp.client.tool_registry import (
            MCPToolDefinition,
            MCPToolRegistry,
        )

        registry = MCPToolRegistry()

        # Add tools from multiple servers
        registry._tools["playwright:screenshot"] = MCPToolDefinition(
            server_name="playwright",
            name="screenshot",
            description="Take a screenshot",
            input_schema={},
        )
        registry._tools["playwright:click"] = MCPToolDefinition(
            server_name="playwright",
            name="click",
            description="Click element",
            input_schema={},
        )
        registry._tools["github:create_pr"] = MCPToolDefinition(
            server_name="github",
            name="create_pr",
            description="Create a PR",
            input_schema={},
        )
        registry._server_tools["playwright"] = [
            "playwright:screenshot",
            "playwright:click",
        ]
        registry._server_tools["github"] = ["github:create_pr"]

        playwright_tools = registry.get_tools(server_name="playwright")

        assert len(playwright_tools) == 2
        assert all(t.server_name == "playwright" for t in playwright_tools)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refresh_tools_updates_tool_list(self):
        """GIVEN a registered server that added new tools
        WHEN refresh_tools is called
        THEN the tool list is updated"""
        from mcp_server_langgraph.mcp.client.tool_registry import (
            MCPServerConfig,
            MCPToolRegistry,
        )

        registry = MCPToolRegistry()

        mock_session = AsyncMock()
        # Initial tool list
        mock_session.list_tools.return_value = [
            {
                "name": "screenshot",
                "description": "Take a screenshot",
                "inputSchema": {},
            },
        ]
        mock_session.connect = AsyncMock()
        registry._create_session = MagicMock(return_value=mock_session)

        config = MCPServerConfig(name="playwright", command="npx", args=[])
        await registry.register_server(config)

        # Server adds new tool
        mock_session.list_tools.return_value = [
            {"name": "screenshot", "description": "Take a screenshot", "inputSchema": {}},
            {"name": "navigate", "description": "Navigate to URL", "inputSchema": {}},
        ]

        new_tools = await registry.refresh_tools("playwright")

        assert len(new_tools) == 2
        assert any(t.name == "navigate" for t in new_tools)

    @pytest.mark.unit
    def test_duplicate_tool_names_use_qualified_names(self):
        """GIVEN two servers with same tool name
        WHEN both are registered
        THEN tools are distinguished by qualified names"""
        from mcp_server_langgraph.mcp.client.tool_registry import (
            MCPToolDefinition,
            MCPToolRegistry,
        )

        registry = MCPToolRegistry()

        # Both servers have a "read" tool
        registry._tools["filesystem:read"] = MCPToolDefinition(
            server_name="filesystem",
            name="read",
            description="Read from filesystem",
            input_schema={},
        )
        registry._tools["database:read"] = MCPToolDefinition(
            server_name="database",
            name="read",
            description="Read from database",
            input_schema={},
        )

        # Both should be accessible with distinct qualified names
        fs_tool = registry.get_tool("filesystem:read")
        db_tool = registry.get_tool("database:read")

        assert fs_tool is not None
        assert db_tool is not None
        assert fs_tool.description == "Read from filesystem"
        assert db_tool.description == "Read from database"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_tool_allowlist_filters_tools(self):
        """GIVEN a server config with tool_allowlist
        WHEN register_server is called
        THEN only allowed tools are imported"""
        from mcp_server_langgraph.mcp.client.tool_registry import (
            MCPServerConfig,
            MCPToolRegistry,
        )

        registry = MCPToolRegistry()

        mock_session = AsyncMock()
        mock_session.list_tools.return_value = [
            {"name": "screenshot", "description": "Take screenshot", "inputSchema": {}},
            {"name": "click", "description": "Click element", "inputSchema": {}},
            {"name": "delete", "description": "Delete element", "inputSchema": {}},
        ]
        mock_session.connect = AsyncMock()
        registry._create_session = MagicMock(return_value=mock_session)

        config = MCPServerConfig(
            name="playwright",
            command="npx",
            args=[],
            tool_allowlist=["screenshot", "click"],  # Only these allowed
        )

        tools = await registry.register_server(config)

        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "screenshot" in tool_names
        assert "click" in tool_names
        assert "delete" not in tool_names

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_tool_blocklist_hides_tools(self):
        """GIVEN a server config with tool_blocklist
        WHEN register_server is called
        THEN blocked tools are not imported"""
        from mcp_server_langgraph.mcp.client.tool_registry import (
            MCPServerConfig,
            MCPToolRegistry,
        )

        registry = MCPToolRegistry()

        mock_session = AsyncMock()
        mock_session.list_tools.return_value = [
            {"name": "read", "description": "Read file", "inputSchema": {}},
            {"name": "write", "description": "Write file", "inputSchema": {}},
            {"name": "delete", "description": "Delete file", "inputSchema": {}},
        ]
        mock_session.connect = AsyncMock()
        registry._create_session = MagicMock(return_value=mock_session)

        config = MCPServerConfig(
            name="filesystem",
            command="npx",
            args=[],
            tool_blocklist=["delete", "write"],  # Block dangerous operations
        )

        tools = await registry.register_server(config)

        assert len(tools) == 1
        assert tools[0].name == "read"

    @pytest.mark.unit
    def test_get_tool_returns_none_for_unknown(self):
        """GIVEN a registry
        WHEN get_tool is called with unknown name
        THEN None is returned"""
        from mcp_server_langgraph.mcp.client.tool_registry import MCPToolRegistry

        registry = MCPToolRegistry()

        result = registry.get_tool("unknown:tool")

        assert result is None

    @pytest.mark.unit
    def test_get_server_names_returns_registered_servers(self):
        """GIVEN registered servers
        WHEN get_server_names is called
        THEN all server names are returned"""
        from mcp_server_langgraph.mcp.client.tool_registry import MCPToolRegistry

        registry = MCPToolRegistry()
        registry._server_tools["playwright"] = []
        registry._server_tools["github"] = []

        names = registry.get_server_names()

        assert "playwright" in names
        assert "github" in names


@pytest.mark.xdist_group(name="mcp_tool_registry_integration")
class TestMCPToolRegistryIntegration:
    """Integration tests for MCPToolRegistry with hook system."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_registry_integrates_with_get_all_tools(self):
        """GIVEN a populated registry
        WHEN get_all_tools is called with the registry
        THEN external MCP tools are included"""
        # Placeholder for integration test with tools/__init__.py
        pass
