"""
TDD Tests for MCP Tool Proxy

These tests define the expected behavior for the MCPToolProxy system
that wraps external MCP tools as LangChain BaseTool.
Written FIRST before implementation (RED phase) per ADR-0082.
"""

import asyncio
import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest



pytestmark = pytest.mark.unit

@pytest.mark.xdist_group(name="mcp_tool_proxy")
class TestMCPToolProxy:
    """Test suite for MCPToolProxy class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_proxy_has_correct_metadata(self):
        """GIVEN an MCPToolDefinition
        WHEN MCPToolProxy is created
        THEN it has correct name, description, and metadata"""
        from mcp_server_langgraph.mcp.client.tool_proxy import MCPToolProxy
        from mcp_server_langgraph.mcp.client.tool_registry import MCPToolDefinition

        tool_def = MCPToolDefinition(
            server_name="playwright",
            name="screenshot",
            description="Take a screenshot of the current page",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to save screenshot"},
                },
                "required": ["path"],
            },
        )

        mock_executor = MagicMock()
        proxy = MCPToolProxy.from_definition(tool_def, mock_executor)

        # LangChain BaseTool properties
        assert proxy.name == "playwright_screenshot"  # qualified name with underscore
        assert "screenshot" in proxy.description.lower()
        assert proxy.mcp_server == "playwright"
        assert proxy.mcp_tool_name == "screenshot"

    @pytest.mark.unit
    def test_proxy_wraps_mcp_tool_as_langchain(self):
        """GIVEN an MCPToolDefinition
        WHEN MCPToolProxy is created
        THEN it can be used as a LangChain BaseTool"""
        from langchain_core.tools import BaseTool

        from mcp_server_langgraph.mcp.client.tool_proxy import MCPToolProxy
        from mcp_server_langgraph.mcp.client.tool_registry import MCPToolDefinition

        tool_def = MCPToolDefinition(
            server_name="github",
            name="create_pr",
            description="Create a pull request",
            input_schema={"type": "object", "properties": {}},
        )

        mock_executor = MagicMock()
        proxy = MCPToolProxy.from_definition(tool_def, mock_executor)

        assert isinstance(proxy, BaseTool)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_proxy_forwards_arguments_correctly(self):
        """GIVEN an MCPToolProxy
        WHEN _arun is called with arguments
        THEN arguments are forwarded to executor"""
        from mcp_server_langgraph.mcp.client.tool_proxy import MCPToolProxy
        from mcp_server_langgraph.mcp.client.tool_registry import MCPToolDefinition

        tool_def = MCPToolDefinition(
            server_name="playwright",
            name="navigate",
            description="Navigate to URL",
            input_schema={
                "type": "object",
                "properties": {"url": {"type": "string"}},
            },
        )

        mock_executor = AsyncMock()
        mock_executor.call_tool.return_value = "Navigation complete"

        proxy = MCPToolProxy.from_definition(tool_def, mock_executor)

        result = await proxy._arun(url="https://example.com")

        mock_executor.call_tool.assert_called_once_with(
            server="playwright",
            tool="navigate",
            arguments={"url": "https://example.com"},
        )
        assert result == "Navigation complete"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_proxy_handles_timeout(self):
        """GIVEN an MCPToolProxy
        WHEN executor times out
        THEN appropriate error is returned"""
        from mcp_server_langgraph.mcp.client.tool_proxy import MCPToolProxy
        from mcp_server_langgraph.mcp.client.tool_registry import MCPToolDefinition

        tool_def = MCPToolDefinition(
            server_name="slow-server",
            name="slow_tool",
            description="A slow tool",
            input_schema={"type": "object", "properties": {}},
        )

        mock_executor = AsyncMock()
        mock_executor.call_tool.side_effect = asyncio.TimeoutError("Operation timed out")

        proxy = MCPToolProxy.from_definition(tool_def, mock_executor)

        result = await proxy._arun()

        assert "timeout" in result.lower() or "error" in result.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_proxy_handles_server_errors(self):
        """GIVEN an MCPToolProxy
        WHEN executor raises an error
        THEN error is captured and returned as string"""
        from mcp_server_langgraph.mcp.client.tool_proxy import MCPToolProxy
        from mcp_server_langgraph.mcp.client.tool_registry import MCPToolDefinition

        tool_def = MCPToolDefinition(
            server_name="error-server",
            name="failing_tool",
            description="A tool that fails",
            input_schema={"type": "object", "properties": {}},
        )

        mock_executor = AsyncMock()
        mock_executor.call_tool.side_effect = ConnectionError("Server disconnected")

        proxy = MCPToolProxy.from_definition(tool_def, mock_executor)

        result = await proxy._arun()

        assert "error" in result.lower() or "disconnected" in result.lower()

    @pytest.mark.unit
    def test_proxy_generates_args_schema(self):
        """GIVEN an MCPToolDefinition with input_schema
        WHEN MCPToolProxy is created
        THEN args_schema is generated from input_schema"""
        from mcp_server_langgraph.mcp.client.tool_proxy import MCPToolProxy
        from mcp_server_langgraph.mcp.client.tool_registry import MCPToolDefinition

        tool_def = MCPToolDefinition(
            server_name="playwright",
            name="click",
            description="Click an element",
            input_schema={
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector",
                    },
                    "button": {
                        "type": "string",
                        "enum": ["left", "right", "middle"],
                        "description": "Mouse button",
                    },
                },
                "required": ["selector"],
            },
        )

        mock_executor = MagicMock()
        proxy = MCPToolProxy.from_definition(tool_def, mock_executor)

        # The proxy should have an args_schema
        assert proxy.args_schema is not None
        # Schema should be a Pydantic model or similar
        schema_fields = proxy.args_schema.model_fields
        assert "selector" in schema_fields

    @pytest.mark.unit
    def test_proxy_handles_empty_input_schema(self):
        """GIVEN an MCPToolDefinition with empty input_schema
        WHEN MCPToolProxy is created
        THEN it handles gracefully"""
        from mcp_server_langgraph.mcp.client.tool_proxy import MCPToolProxy
        from mcp_server_langgraph.mcp.client.tool_registry import MCPToolDefinition

        tool_def = MCPToolDefinition(
            server_name="simple",
            name="no_args_tool",
            description="A tool with no arguments",
            input_schema={},
        )

        mock_executor = MagicMock()
        proxy = MCPToolProxy.from_definition(tool_def, mock_executor)

        assert proxy is not None
        assert proxy.name == "simple_no_args_tool"


@pytest.mark.xdist_group(name="mcp_tool_proxy")
class TestMCPToolProxyFactory:
    """Test suite for MCPToolProxy factory methods."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_create_proxies_from_registry(self):
        """GIVEN an MCPToolRegistry with tools
        WHEN create_proxies_from_registry is called
        THEN proxies are created for all tools"""
        from mcp_server_langgraph.mcp.client.tool_proxy import create_proxies_from_registry
        from mcp_server_langgraph.mcp.client.tool_registry import (
            MCPToolDefinition,
            MCPToolRegistry,
        )

        registry = MCPToolRegistry()

        # Add some tools manually
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

        mock_executor = MagicMock()
        proxies = create_proxies_from_registry(registry, mock_executor)

        assert len(proxies) == 2
        proxy_names = [p.name for p in proxies]
        assert "playwright_screenshot" in proxy_names
        assert "github_create_pr" in proxy_names

    @pytest.mark.unit
    def test_create_proxies_for_specific_server(self):
        """GIVEN an MCPToolRegistry with tools from multiple servers
        WHEN create_proxies_from_registry is called with server_name
        THEN only proxies for that server are created"""
        from mcp_server_langgraph.mcp.client.tool_proxy import create_proxies_from_registry
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

        mock_executor = MagicMock()
        proxies = create_proxies_from_registry(
            registry, mock_executor, server_name="playwright"
        )

        assert len(proxies) == 2
        assert all("playwright" in p.name for p in proxies)


@pytest.mark.xdist_group(name="mcp_tool_proxy_integration")
class TestMCPToolProxyIntegration:
    """Integration tests for MCPToolProxy with agents."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_proxy_works_with_langchain_agent(self):
        """GIVEN MCPToolProxies
        WHEN used with a LangChain agent
        THEN tools are callable by the agent"""
        # Placeholder for agent integration test
        pass
