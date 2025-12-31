"""
TDD Tests for MCP WebSocket Handler.

Tests the MCPWebSocketHandler class that extends WebSocketBase
to provide standardized infrastructure for the MCP WebSocket endpoint.

Following TDD RED-GREEN-REFACTOR cycle:
- RED: Write failing tests that define expected behavior
- GREEN: Implement minimal code to make tests pass
- REFACTOR: Improve code quality while keeping tests green
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.websocket.types import MessageEnvelope

# Mark all tests in this module
pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.mcp,
    pytest.mark.xdist_group(name="mcp_websocket_handler"),
]


def make_mcp_message(payload: dict[str, Any], msg_id: str = "test-req") -> MessageEnvelope:
    """Create a MessageEnvelope wrapping an MCP/JSON-RPC payload."""
    return MessageEnvelope(type="mcp_request", payload=payload, id=msg_id)


class TestMCPWebSocketHandlerConstruction:
    """Test MCPWebSocketHandler initialization and configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_extends_websocket_base(self) -> None:
        """MCPWebSocketHandler should extend WebSocketBase."""
        from mcp_server_langgraph.websocket.base import WebSocketBase
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()
        assert isinstance(handler, WebSocketBase)

    def test_handler_has_mcp_endpoint_name(self) -> None:
        """Handler should have 'mcp' as endpoint name."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()
        assert handler.config.endpoint_name == "mcp"

    def test_handler_uses_correct_rate_limit(self) -> None:
        """Handler should use 600 messages per minute (10/sec) rate limit."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()
        assert handler.config.rate_limit_per_minute == 600

    def test_handler_configures_message_timeout(self) -> None:
        """Handler should have 30 second message timeout."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()
        assert handler.config.message_timeout == 30

    def test_handler_accepts_custom_config(self) -> None:
        """Handler should accept custom WebSocketConfig."""
        from mcp_server_langgraph.websocket import WebSocketConfig
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        custom_config = WebSocketConfig(
            endpoint_name="custom-mcp",
            require_auth=True,
            rate_limit_per_minute=300,
        )
        handler = MCPWebSocketHandler(config=custom_config)
        assert handler.config.endpoint_name == "custom-mcp"
        assert handler.config.rate_limit_per_minute == 300


@pytest.mark.xdist_group(name="mcp_websocket_handler")
class TestMCPMessageHandling:
    """Test MCP protocol message handling via WebSocketBase."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_message_routes_to_mcp_handler(self) -> None:
        """Messages should be routed to internal MCP message handler."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()

        # Mock the internal MCP handler
        mock_mcp_handler = AsyncMock()  # noqa: async-mock-config - configured below
        mock_mcp_handler.handle = AsyncMock(return_value={"jsonrpc": "2.0", "id": 1, "result": {"initialized": True}})
        handler._mcp_handler = mock_mcp_handler

        # Create a MessageEnvelope with the JSON-RPC message as payload
        json_rpc_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-11-25"},
        }
        message = make_mcp_message(json_rpc_payload, msg_id="req-1")

        response = await handler.handle_message(message)

        mock_mcp_handler.handle.assert_called_once_with(json_rpc_payload)
        # Response is a MessageEnvelope - check its payload
        assert response is not None
        assert response.type == "mcp_response"
        assert response.payload is not None
        assert response.payload["jsonrpc"] == "2.0"
        assert response.payload["id"] == 1
        assert "result" in response.payload

    @pytest.mark.asyncio
    async def test_handle_tools_list_returns_tools(self) -> None:
        """tools/list should return available tools."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()

        payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        message = make_mcp_message(payload)

        response = await handler.handle_message(message)

        assert response is not None
        assert response.payload is not None
        assert response.payload["jsonrpc"] == "2.0"
        assert response.payload["id"] == 1
        assert "result" in response.payload
        assert "tools" in response.payload["result"]

    @pytest.mark.asyncio
    async def test_handle_resources_list_returns_resources(self) -> None:
        """resources/list should return available resources."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()

        payload = {"jsonrpc": "2.0", "id": 1, "method": "resources/list", "params": {}}
        message = make_mcp_message(payload)

        response = await handler.handle_message(message)

        assert response is not None
        assert response.payload is not None
        assert response.payload["jsonrpc"] == "2.0"
        assert response.payload["id"] == 1
        assert "result" in response.payload
        assert "resources" in response.payload["result"]

    @pytest.mark.asyncio
    async def test_handle_prompts_list_returns_prompts(self) -> None:
        """prompts/list should return available prompts."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()

        payload = {"jsonrpc": "2.0", "id": 1, "method": "prompts/list", "params": {}}
        message = make_mcp_message(payload)

        response = await handler.handle_message(message)

        assert response is not None
        assert response.payload is not None
        assert response.payload["jsonrpc"] == "2.0"
        assert response.payload["id"] == 1
        assert "result" in response.payload
        assert "prompts" in response.payload["result"]

    @pytest.mark.asyncio
    async def test_handle_unknown_method_returns_error(self) -> None:
        """Unknown methods should return method_not_found error."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()

        payload = {"jsonrpc": "2.0", "id": 1, "method": "unknown/method", "params": {}}
        message = make_mcp_message(payload)

        response = await handler.handle_message(message)

        assert response is not None
        assert response.payload is not None
        assert response.payload["jsonrpc"] == "2.0"
        assert response.payload["id"] == 1
        assert "error" in response.payload
        assert response.payload["error"]["code"] == -32601  # METHOD_NOT_FOUND


class TestMCPPingPong:
    """Test ping/pong handling for MCP WebSocket."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_ping_handled_by_base_class(self) -> None:
        """Ping messages should be handled by WebSocketBase."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()

        # Ping is handled at the base class level before handle_message
        # The handle_message should not receive ping messages
        # Create an invalid MCP message (no jsonrpc field)
        payload = {"type": "ping"}
        message = make_mcp_message(payload)

        # This should not be a valid MCP message
        response = await handler.handle_message(message)

        # Should return parse error since it's not valid JSON-RPC
        assert response is not None
        assert response.payload is not None
        assert "error" in response.payload


@pytest.mark.xdist_group(name="mcp_websocket_handler")
class TestMCPAuthenticationContext:
    """Test authenticated MCP handler creation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_creates_authenticated_handler(self) -> None:
        """on_connect should create AuthenticatedMCPHandler for auth users."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler
        from mcp_server_langgraph.websocket import WebSocketConfig

        config = WebSocketConfig(
            endpoint_name="mcp",
            require_auth=True,
        )
        handler = MCPWebSocketHandler(config=config)

        # Mock user object
        mock_user = MagicMock()
        mock_user.id = "test-user"
        mock_user.roles = ["admin", "mcp:use"]

        await handler.on_connect(mock_user)

        # The handler should have created an authenticated MCP handler
        assert handler._mcp_handler is not None
        assert handler._user_id == "test-user"

    @pytest.mark.asyncio
    async def test_on_connect_anonymous_creates_base_handler(self) -> None:
        """on_connect without user should create base MCPMessageHandler."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler
        from mcp_server_langgraph.websocket import WebSocketConfig

        config = WebSocketConfig(
            endpoint_name="mcp",
            require_auth=False,
        )
        handler = MCPWebSocketHandler(config=config)

        await handler.on_connect(None)

        # Should have a base MCP handler, not authenticated
        assert handler._mcp_handler is not None


class TestMCPSessionManagement:
    """Test session ID handling for MCP WebSocket."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_accepts_session_id(self) -> None:
        """Handler should accept explicit session ID."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler(session_id="custom-session-123")
        assert handler.session_id == "custom-session-123"

    def test_handler_generates_session_id_when_not_provided(self) -> None:
        """Handler should generate session ID when not provided."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()
        assert handler.session_id is not None
        assert len(handler.session_id) > 0


@pytest.mark.xdist_group(name="mcp_websocket_handler")
class TestMCPStreamingSupport:
    """Test streaming tool call support."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_streaming_tool_call_with_meta_streaming_flag(self) -> None:
        """Tool calls with _meta.streaming should use streaming handler."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()
        handler._websocket = AsyncMock()  # noqa: async-mock-config - mock websocket for notifications

        # Mock user to enable authenticated features
        mock_user = MagicMock()
        mock_user.id = "test-user"
        mock_user.roles = []
        await handler.on_connect(mock_user)

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "test_tool",
                "arguments": {},
                "_meta": {"streaming": True},
            },
        }
        message = make_mcp_message(payload)

        # Should handle streaming tool call (actual behavior depends on implementation)
        response = await handler.handle_message(message)
        assert response is not None
        assert response.payload is not None
        assert response.payload["jsonrpc"] == "2.0"

    @pytest.mark.asyncio
    async def test_non_streaming_tool_call(self) -> None:
        """Tool calls without streaming flag should execute normally."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "test_tool", "arguments": {}},
        }
        message = make_mcp_message(payload)

        response = await handler.handle_message(message)

        assert response is not None
        assert response.payload is not None
        assert response.payload["jsonrpc"] == "2.0"
        assert response.payload["id"] == 1


class TestMCPMetricsIntegration:
    """Test metrics recording for MCP WebSocket."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_message_handling_succeeds_with_metrics(self) -> None:
        """Messages should be handled successfully (metrics integration optional)."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()

        payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        message = make_mcp_message(payload)

        response = await handler.handle_message(message)

        # Message should be handled successfully
        assert response is not None
        assert response.payload is not None
        assert response.payload["jsonrpc"] == "2.0"
        assert response.payload["id"] == 1
        assert "result" in response.payload
        # Metrics recording happens at a higher level (in ws_router)


class TestMCPRateLimiting:
    """Test per-user rate limiting for MCP WebSocket."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_rate_limit_configured_from_config(self) -> None:
        """Rate limit should be configured from WebSocketConfig."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler
        from mcp_server_langgraph.websocket import WebSocketConfig

        config = WebSocketConfig(
            endpoint_name="mcp",
            rate_limit_per_minute=100,
        )
        handler = MCPWebSocketHandler(config=config)

        assert handler.config.rate_limit_per_minute == 100


@pytest.mark.xdist_group(name="mcp_websocket_handler")
class TestMCPErrorHandling:
    """Test error handling for MCP protocol messages."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_invalid_json_rpc_returns_parse_error(self) -> None:
        """Invalid JSON-RPC should return parse error."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()

        # Missing jsonrpc version
        payload = {"id": 1, "method": "test"}
        message = make_mcp_message(payload)

        response = await handler.handle_message(message)

        assert response is not None
        assert response.payload is not None
        assert "error" in response.payload
        assert response.payload["error"]["code"] == -32600  # INVALID_REQUEST

    @pytest.mark.asyncio
    async def test_missing_method_returns_invalid_request(self) -> None:
        """Missing method field should return invalid request error."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()

        payload = {"jsonrpc": "2.0", "id": 1, "params": {}}
        message = make_mcp_message(payload)

        response = await handler.handle_message(message)

        assert response is not None
        assert response.payload is not None
        assert "error" in response.payload
        assert response.payload["error"]["code"] == -32600  # INVALID_REQUEST

    @pytest.mark.asyncio
    async def test_exception_in_handler_returns_internal_error(self) -> None:
        """Exceptions in message handling should return internal error."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()

        # Mock internal handler to raise exception
        mock_mcp_handler = AsyncMock()  # noqa: async-mock-config - configured below
        mock_mcp_handler.handle = AsyncMock(side_effect=Exception("Internal failure"))
        handler._mcp_handler = mock_mcp_handler

        payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        message = make_mcp_message(payload)

        response = await handler.handle_message(message)

        assert response is not None
        assert response.payload is not None
        assert "error" in response.payload
        assert response.payload["error"]["code"] == -32603  # INTERNAL_ERROR


class TestMCPWebSocketHandlerProtocol:
    """Test MCP 2025-11-25 protocol compliance."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_initialize_returns_capabilities(self) -> None:
        """initialize method should return server capabilities."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }
        message = make_mcp_message(payload)

        response = await handler.handle_message(message)

        assert response is not None
        assert response.payload is not None
        assert response.payload["jsonrpc"] == "2.0"
        assert response.payload["id"] == 1
        assert "result" in response.payload
        result = response.payload["result"]
        assert "protocolVersion" in result
        assert "capabilities" in result
        assert "serverInfo" in result

    @pytest.mark.asyncio
    async def test_response_includes_jsonrpc_version(self) -> None:
        """All responses should include jsonrpc version 2.0."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()

        payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        message = make_mcp_message(payload)

        response = await handler.handle_message(message)

        assert response is not None
        assert response.payload is not None
        assert response.payload["jsonrpc"] == "2.0"

    @pytest.mark.asyncio
    async def test_notification_handling_does_not_crash(self) -> None:
        """Notifications should be handled without crashing."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()

        # Notification - no id field
        # Note: The base MCPMessageHandler may not recognize all notifications
        payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        message = make_mcp_message(payload)

        # Should not raise an exception
        response = await handler.handle_message(message)

        # Response should be valid JSON-RPC (either success or error)
        # The key is that handling doesn't crash
        assert response is not None
        assert response.payload is not None
        assert response.payload["jsonrpc"] == "2.0"


@pytest.mark.xdist_group(name="mcp_websocket_handler")
class TestMCPWebSocketHandlerLifecycle:
    """Test WebSocketBase lifecycle integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_disconnect_cleans_up(self) -> None:
        """on_disconnect should clean up MCP handler resources."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        handler = MCPWebSocketHandler()

        # Set up some state
        mock_user = MagicMock()
        mock_user.id = "test-user"
        mock_user.roles = []
        await handler.on_connect(mock_user)

        # Disconnect
        await handler.on_disconnect()

        # Handler should be cleaned up
        # Implementation may vary - check key cleanup happened
        assert handler._mcp_handler is None or hasattr(handler, "_disconnected")
