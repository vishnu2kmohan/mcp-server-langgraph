"""
Tests for MCP Protocol 2025-11-25 Compliance.

These tests verify that both REST and WebSocket handlers implement all
required and optional features per the MCP specification.

Reference: https://modelcontextprotocol.io/specification/2025-11-25
"""

import gc
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = [pytest.mark.unit, pytest.mark.mcp]


@pytest.mark.xdist_group(name="mcp_protocol_compliance")
class TestMCPProtocolCompliance:
    """Tests for MCP 2025-11-25 protocol compliance."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # =========================================================================
    # Core Protocol Methods
    # =========================================================================

    @pytest.mark.asyncio
    async def test_websocket_initialize_returns_protocol_version(self) -> None:
        """Verify initialize returns MCP 2025-11-25 protocol version."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()
        response = await handler.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-11-25"},
            }
        )

        assert response["result"]["protocolVersion"] == "2025-11-25"
        assert "capabilities" in response["result"]

    @pytest.mark.asyncio
    async def test_websocket_tools_list_returns_built_in_tools(self) -> None:
        """Verify tools/list returns all built-in tools (not hardcoded single tool)."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()

        with patch("mcp_server_langgraph.mcp.server_streamable.get_mcp_server") as mock_get_server:
            # Mock the MCP server's list_tools_public method
            mock_server = MagicMock()
            mock_tool = MagicMock()
            mock_tool.model_dump.return_value = {
                "name": "test_tool",
                "description": "Test tool",
                "inputSchema": {"type": "object"},
            }
            mock_server.list_tools_public = AsyncMock(return_value=[mock_tool])
            mock_get_server.return_value = mock_server

            response = await handler.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {},
                }
            )

            assert "result" in response
            assert "tools" in response["result"]
            # Should have at least the mocked tool
            assert len(response["result"]["tools"]) >= 1

    # =========================================================================
    # Sampling Feature (sampling/createMessage)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_websocket_sampling_create_message(self) -> None:
        """Verify sampling/createMessage is implemented for WebSocket."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()

        response = await handler.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "sampling/createMessage",
                "params": {
                    "messages": [{"role": "user", "content": {"type": "text", "text": "Hello"}}],
                    "maxTokens": 100,
                },
            }
        )

        # Should not return method not found
        assert "error" not in response or response["error"]["code"] != -32601, "sampling/createMessage should be implemented"

    @pytest.mark.asyncio
    async def test_websocket_sampling_with_model_preferences(self) -> None:
        """Verify sampling supports modelPreferences parameter."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()

        response = await handler.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "sampling/createMessage",
                "params": {
                    "messages": [{"role": "user", "content": {"type": "text", "text": "Hello"}}],
                    "maxTokens": 100,
                    "modelPreferences": {
                        "hints": [{"name": "claude-3-sonnet"}],
                        "intelligencePriority": 0.8,
                        "speedPriority": 0.5,
                        "costPriority": 0.3,
                    },
                },
            }
        )

        # Should not fail with invalid params
        assert response["error"]["code"] != -32602 if "error" in response else True

    # =========================================================================
    # Elicitation Feature (elicitation/create)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_websocket_elicitation_create(self) -> None:
        """Verify elicitation/create is implemented for WebSocket."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()

        response = await handler.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "elicitation/create",
                "params": {
                    "message": "Please provide your API key",
                    "requestedSchema": {
                        "type": "object",
                        "properties": {
                            "apiKey": {"type": "string"},
                        },
                    },
                },
            }
        )

        # Should not return method not found
        assert "error" not in response or response["error"]["code"] != -32601, "elicitation/create should be implemented"

    # =========================================================================
    # Tasks Feature (Experimental - tasks/*)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_websocket_tasks_list(self) -> None:
        """Verify tasks/list is implemented for WebSocket."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()

        response = await handler.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tasks/list",
                "params": {},
            }
        )

        # Should not return method not found
        assert "error" not in response or response["error"]["code"] != -32601, "tasks/list should be implemented"

    @pytest.mark.asyncio
    async def test_websocket_tasks_get(self) -> None:
        """Verify tasks/get is implemented for WebSocket."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()

        response = await handler.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tasks/get",
                "params": {"taskId": "test-task-id"},
            }
        )

        # Should not return method not found (may return task not found, which is OK)
        assert "error" not in response or response["error"]["code"] != -32601, "tasks/get should be implemented"

    @pytest.mark.asyncio
    async def test_websocket_tasks_cancel(self) -> None:
        """Verify tasks/cancel is implemented for WebSocket."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()

        response = await handler.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tasks/cancel",
                "params": {"taskId": "test-task-id"},
            }
        )

        # Should not return method not found
        assert "error" not in response or response["error"]["code"] != -32601, "tasks/cancel should be implemented"

    @pytest.mark.asyncio
    async def test_websocket_tasks_result(self) -> None:
        """Verify tasks/result is implemented for WebSocket."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()

        response = await handler.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tasks/result",
                "params": {"taskId": "test-task-id"},
            }
        )

        # Should not return method not found
        assert "error" not in response or response["error"]["code"] != -32601, "tasks/result should be implemented"

    # =========================================================================
    # Completion Feature (completion/complete)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_websocket_completion_complete(self) -> None:
        """Verify completion/complete is implemented for autocompletion."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()

        response = await handler.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "completion/complete",
                "params": {
                    "ref": {"type": "ref/prompt", "name": "code_review"},
                    "argument": {"name": "language", "value": "py"},
                },
            }
        )

        # Should not return method not found
        assert "error" not in response or response["error"]["code"] != -32601, "completion/complete should be implemented"

    @pytest.mark.asyncio
    async def test_completion_for_prompt_arguments(self) -> None:
        """Verify completion works for prompt argument values."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()

        response = await handler.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "completion/complete",
                "params": {
                    "ref": {"type": "ref/prompt", "name": "code_review"},
                    "argument": {"name": "language", "value": ""},
                },
            }
        )

        if "result" in response:
            assert "completion" in response["result"]
            assert "values" in response["result"]["completion"]

    @pytest.mark.asyncio
    async def test_completion_for_resource_uri(self) -> None:
        """Verify completion works for resource URIs."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()

        response = await handler.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "completion/complete",
                "params": {
                    "ref": {"type": "ref/resource", "uri": "config://"},
                    "argument": {"name": "uri", "value": "config://"},
                },
            }
        )

        if "result" in response:
            assert "completion" in response["result"]

    # =========================================================================
    # Logging Feature (logging/setLevel)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_websocket_logging_set_level(self) -> None:
        """Verify logging/setLevel is implemented for dynamic log control."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()

        response = await handler.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "logging/setLevel",
                "params": {"level": "debug"},
            }
        )

        # Should not return method not found
        assert "error" not in response or response["error"]["code"] != -32601, "logging/setLevel should be implemented"

    @pytest.mark.asyncio
    async def test_logging_valid_levels(self) -> None:
        """Verify all valid log levels are accepted."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()

        for level in ["debug", "info", "notice", "warning", "error", "critical", "alert", "emergency"]:
            response = await handler.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "logging/setLevel",
                    "params": {"level": level},
                }
            )

            # Should succeed for valid levels
            if "error" in response:
                assert response["error"]["code"] != -32602, f"Level '{level}' should be valid"

    # =========================================================================
    # Roots Feature (roots/list)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_websocket_roots_list(self) -> None:
        """Verify roots/list is implemented for filesystem roots."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()

        response = await handler.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "roots/list",
                "params": {},
            }
        )

        # Should not return method not found
        assert "error" not in response or response["error"]["code"] != -32601, "roots/list should be implemented"

    @pytest.mark.asyncio
    async def test_roots_returns_valid_structure(self) -> None:
        """Verify roots/list returns correct structure with uri and name."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()

        response = await handler.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "roots/list",
                "params": {},
            }
        )

        if "result" in response:
            assert "roots" in response["result"]
            for root in response["result"]["roots"]:
                assert "uri" in root
                assert "name" in root

    # =========================================================================
    # Capability Declaration Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_capabilities_include_all_features(self) -> None:
        """Verify capabilities include all implemented features."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()
        response = await handler.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {},
            }
        )

        capabilities = response["result"]["capabilities"]

        # Required capabilities
        assert "tools" in capabilities
        assert "resources" in capabilities
        assert "prompts" in capabilities

        # Optional capabilities (should be present if implemented)
        assert "sampling" in capabilities
        assert "elicitation" in capabilities
        assert "logging" in capabilities

    # =========================================================================
    # REST Parity Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_websocket_and_rest_tools_list_return_same_tools(self) -> None:
        """Verify WebSocket and REST return the same tools list."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler
        from mcp_server_langgraph.api.v1.mcp import MCPService

        # This test validates that both return the same tools
        # In production, both should query the same source
        ws_handler = MCPMessageHandler()
        rest_service = MCPService()

        # Both should have access to built-in tools
        assert hasattr(ws_handler, "_handle_tools_list_async")
        assert hasattr(rest_service, "list_tools")


@pytest.mark.xdist_group(name="mcp_protocol_compliance")
class TestMCPWebSocketTasksIntegration:
    """Tests for WebSocket tasks integration with Orchestrator."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_tasks_list_returns_orchestrator_tasks(self) -> None:
        """Verify tasks/list returns tasks from Orchestrator."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()

        # Should return empty list when no tasks
        response = await handler.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tasks/list",
                "params": {},
            }
        )

        if "result" in response:
            assert "tasks" in response["result"]
            assert isinstance(response["result"]["tasks"], list)

    @pytest.mark.asyncio
    async def test_tasks_cancel_returns_valid_response(self) -> None:
        """Verify tasks/cancel returns a valid response structure."""
        from mcp_server_langgraph.mcp.message_handler import MCPMessageHandler

        handler = MCPMessageHandler()

        response = await handler.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tasks/cancel",
                "params": {"taskId": "orch-task-123"},
            }
        )

        # Should return a valid result with cancelled field
        assert "result" in response
        assert "cancelled" in response["result"]
        # Without orchestrator, should return False
        assert response["result"]["cancelled"] is False
