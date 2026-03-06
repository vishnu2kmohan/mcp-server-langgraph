"""
TDD Tests for MCP Executor

These tests define the expected behavior for the MCPExecutor system
that routes tool calls to external MCP servers.
Written FIRST before implementation (RED phase) per ADR-0082.
"""

import asyncio
import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


pytestmark = pytest.mark.unit


class TestMCPExecutor:
    """Test suite for MCPExecutor class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_executor_routes_to_correct_server(self):
        """GIVEN an MCPExecutor with multiple servers
        WHEN call_tool is invoked
        THEN it routes to the correct server"""
        from mcp_server_langgraph.mcp.client.executor import MCPExecutor
        from mcp_server_langgraph.mcp.client.tool_registry import (
            MCPServerConfig,
            MCPToolRegistry,
        )

        registry = MCPToolRegistry()

        # Create mock session that will be returned by _create_session
        mock_session = AsyncMock(return_value=None)
        mock_session.is_connected = True
        mock_session.list_tools.return_value = [
            {"name": "screenshot", "description": "Take screenshot", "inputSchema": {}},
        ]
        mock_session.call_tool.return_value = {"success": True, "image": "base64..."}

        # Patch the _create_session method to return our mock
        with patch.object(registry, "_create_session", return_value=mock_session):
            await registry.register_server(MCPServerConfig(name="playwright", command="npx", args=["playwright"]))

        executor = MCPExecutor(registry)

        result = await executor.call_tool(
            server="playwright",
            tool="screenshot",
            arguments={"url": "https://example.com"},
        )

        mock_session.call_tool.assert_called_once_with("screenshot", {"url": "https://example.com"})
        assert result["success"] is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_executor_raises_for_unknown_server(self):
        """GIVEN an MCPExecutor
        WHEN call_tool is invoked with unknown server
        THEN it raises KeyError"""
        from mcp_server_langgraph.mcp.client.executor import MCPExecutor
        from mcp_server_langgraph.mcp.client.tool_registry import MCPToolRegistry

        registry = MCPToolRegistry()
        executor = MCPExecutor(registry)

        with pytest.raises(KeyError, match="not registered"):
            await executor.call_tool(
                server="nonexistent",
                tool="some_tool",
                arguments={},
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_executor_respects_timeout(self):
        """GIVEN an MCPExecutor
        WHEN call_tool times out
        THEN asyncio.TimeoutError is raised"""
        from mcp_server_langgraph.mcp.client.executor import MCPExecutor
        from mcp_server_langgraph.mcp.client.tool_registry import (
            MCPServerConfig,
            MCPToolRegistry,
        )

        registry = MCPToolRegistry()

        # Create mock that takes too long
        mock_session = AsyncMock(return_value=None)
        mock_session.is_connected = True
        mock_session.list_tools.return_value = [
            {"name": "slow_tool", "description": "Slow", "inputSchema": {}},
        ]

        async def slow_call(name, args):
            await asyncio.sleep(10)  # noqa: sleep-duration - Testing MCP timeout
            return {"result": "done"}

        mock_session.call_tool.side_effect = slow_call

        with patch.object(registry, "_create_session", return_value=mock_session):
            await registry.register_server(MCPServerConfig(name="slow", command="slow", timeout=0.1))

        executor = MCPExecutor(registry)

        with pytest.raises(asyncio.TimeoutError):
            await executor.call_tool(
                server="slow",
                tool="slow_tool",
                arguments={},
                timeout=0.1,
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_executor_batch_call_parallel(self):
        """GIVEN an MCPExecutor
        WHEN batch_call is invoked
        THEN calls are executed in parallel"""
        from mcp_server_langgraph.mcp.client.executor import MCPExecutor, MCPToolCall
        from mcp_server_langgraph.mcp.client.tool_registry import (
            MCPServerConfig,
            MCPToolRegistry,
        )

        registry = MCPToolRegistry()

        # Track call order
        call_order: list[str] = []

        mock_session = AsyncMock(return_value=None)
        mock_session.is_connected = True
        mock_session.list_tools.return_value = [
            {"name": "tool_a", "description": "A", "inputSchema": {}},
            {"name": "tool_b", "description": "B", "inputSchema": {}},
        ]

        async def tracked_call(name, args):
            call_order.append(f"start_{name}")
            await asyncio.sleep(0.1)
            call_order.append(f"end_{name}")
            return {"tool": name}

        mock_session.call_tool.side_effect = tracked_call

        with patch.object(registry, "_create_session", return_value=mock_session):
            await registry.register_server(MCPServerConfig(name="server", command="cmd"))

        executor = MCPExecutor(registry)

        calls = [
            MCPToolCall(server="server", tool="tool_a", arguments={}),
            MCPToolCall(server="server", tool="tool_b", arguments={}),
        ]

        results = await executor.batch_call(calls)

        assert len(results) == 2
        # Both should start before either ends (parallel execution)
        assert "start_tool_a" in call_order[:2]
        assert "start_tool_b" in call_order[:2]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_executor_batch_call_handles_partial_failure(self):
        """GIVEN an MCPExecutor
        WHEN batch_call has some failures
        THEN successful results are returned with errors"""
        from mcp_server_langgraph.mcp.client.executor import MCPExecutor, MCPToolCall
        from mcp_server_langgraph.mcp.client.tool_registry import (
            MCPServerConfig,
            MCPToolRegistry,
        )

        registry = MCPToolRegistry()

        mock_session = AsyncMock(return_value=None)
        mock_session.is_connected = True
        mock_session.list_tools.return_value = [
            {"name": "good_tool", "description": "Works", "inputSchema": {}},
            {"name": "bad_tool", "description": "Fails", "inputSchema": {}},
        ]

        async def mixed_call(name, args):
            if name == "bad_tool":
                raise ConnectionError("Server disconnected")
            return {"success": True}

        mock_session.call_tool.side_effect = mixed_call

        with patch.object(registry, "_create_session", return_value=mock_session):
            await registry.register_server(MCPServerConfig(name="server", command="cmd"))

        executor = MCPExecutor(registry)

        calls = [
            MCPToolCall(server="server", tool="good_tool", arguments={}),
            MCPToolCall(server="server", tool="bad_tool", arguments={}),
        ]

        results = await executor.batch_call(calls)

        assert len(results) == 2
        # First should succeed
        assert results[0].success is True
        assert results[0].result == {"success": True}
        # Second should fail
        assert results[1].success is False
        assert "disconnected" in results[1].error.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_executor_reconnects_on_disconnection(self):
        """GIVEN an MCPExecutor with disconnected server
        WHEN call_tool is invoked
        THEN it attempts to reconnect"""
        from mcp_server_langgraph.mcp.client.executor import MCPExecutor
        from mcp_server_langgraph.mcp.client.tool_registry import (
            MCPServerConfig,
            MCPToolRegistry,
        )

        registry = MCPToolRegistry()

        # Session that starts disconnected
        mock_session = AsyncMock(return_value=None)
        mock_session.list_tools.return_value = [
            {"name": "tool", "description": "Tool", "inputSchema": {}},
        ]
        mock_session.call_tool.return_value = {"result": "ok"}

        # Track connection state
        connected = False

        @property
        def is_connected_prop():
            return connected

        type(mock_session).is_connected = property(lambda self: connected)

        async def connect():
            nonlocal connected
            connected = True

        mock_session.connect = connect

        with patch.object(registry, "_create_session", return_value=mock_session):
            await registry.register_server(MCPServerConfig(name="server", command="cmd"))

        # Manually disconnect
        connected = False

        executor = MCPExecutor(registry)

        # Should reconnect automatically
        result = await executor.call_tool(
            server="server",
            tool="tool",
            arguments={},
        )

        assert result["result"] == "ok"

    @pytest.mark.unit
    def test_executor_initialization_configures_params(self):
        """GIVEN registry and optional auth provider
        WHEN MCPExecutor is created
        THEN it stores references correctly"""
        from mcp_server_langgraph.mcp.client.executor import MCPExecutor
        from mcp_server_langgraph.mcp.client.tool_registry import MCPToolRegistry

        registry = MCPToolRegistry()
        mock_auth = MagicMock()

        executor = MCPExecutor(registry, auth_provider=mock_auth)

        assert executor.registry is registry
        assert executor.auth_provider is mock_auth

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_executor_result_model(self):
        """GIVEN an MCPToolResult
        WHEN accessed
        THEN it has expected attributes"""
        from mcp_server_langgraph.mcp.client.executor import MCPToolResult

        # Success result
        success_result = MCPToolResult(
            server="playwright",
            tool="screenshot",
            success=True,
            result={"image": "base64..."},
            error=None,
            duration_ms=150.5,
        )

        assert success_result.success is True
        assert success_result.result["image"] == "base64..."
        assert success_result.error is None
        assert success_result.duration_ms == 150.5

        # Failure result
        failure_result = MCPToolResult(
            server="playwright",
            tool="screenshot",
            success=False,
            result=None,
            error="Connection timeout",
            duration_ms=5000.0,
        )

        assert failure_result.success is False
        assert failure_result.result is None
        assert "timeout" in failure_result.error.lower()

    @pytest.mark.unit
    def test_tool_call_model(self):
        """GIVEN an MCPToolCall
        WHEN accessed
        THEN it has expected attributes"""
        from mcp_server_langgraph.mcp.client.executor import MCPToolCall

        call = MCPToolCall(
            server="github",
            tool="create_pr",
            arguments={"title": "Fix bug", "body": "Details..."},
        )

        assert call.server == "github"
        assert call.tool == "create_pr"
        assert call.arguments["title"] == "Fix bug"
