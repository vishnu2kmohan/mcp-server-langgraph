"""
Unit tests for MCP WebSocket Handler.

Tests the MCPWebSocketHandler class for MCP protocol handling.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.websocket.types import MessageEnvelope

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="websocket_mcp_handler"),
]

RATE_LIMITER_PATCH = "mcp_server_langgraph.websocket.rate_limiter.get_websocket_rate_limiter"


class TestMCPWebSocketHandlerInit:
    """Tests for MCPWebSocketHandler initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_default_config(self) -> None:
        """GIVEN no config WHEN creating handler THEN uses default config."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        assert handler.config.endpoint_name == "mcp"
        assert handler.config.require_auth is False
        assert handler.config.rate_limit_per_minute == 600
        assert handler.config.heartbeat_interval == 30
        assert handler.config.idle_timeout == 1800
        assert handler.session_id is not None

    def test_init_with_config(self) -> None:
        """GIVEN config WHEN creating handler THEN uses config."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(
            endpoint_name="custom-mcp",
            require_auth=True,
            rate_limit_per_minute=300,
        )

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler(config=config)

        assert handler.config.endpoint_name == "custom-mcp"
        assert handler.config.require_auth is True
        assert handler.config.rate_limit_per_minute == 300

    def test_init_with_session_id(self) -> None:
        """GIVEN session_id WHEN creating handler THEN uses session_id."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler(session_id="custom-session-123")

        assert handler.session_id == "custom-session-123"

    def test_init_generates_uuid_session_id(self) -> None:
        """GIVEN no session_id WHEN creating handler THEN generates UUID."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler
        import uuid

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        # Verify it's a valid UUID
        try:
            uuid.UUID(handler.session_id)
            valid_uuid = True
        except ValueError:
            valid_uuid = False

        assert valid_uuid


class TestMCPWebSocketHandlerLifecycle:
    """Tests for MCPWebSocketHandler lifecycle hooks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_authenticated(self) -> None:
        """GIVEN authenticated user WHEN on_connect called THEN creates AuthenticatedMCPHandler."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler
        from mcp_server_langgraph.websocket.types import AuthUser

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        user = AuthUser(id="user-123", username="testuser")
        # Mock the roles attribute
        user.roles = ["admin", "viewer"]
        # Set _user as run() does before calling on_connect
        handler._user = user

        with patch("mcp_server_langgraph.mcp.message_handler.AuthenticatedMCPHandler") as mock_auth_handler:
            await handler.on_connect(user)

        assert handler.user_id == "user-123"
        assert handler._roles == ["admin", "viewer"]
        mock_auth_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_connect_anonymous(self) -> None:
        """GIVEN no user WHEN on_connect called THEN creates MCPMessageHandler."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        with patch("mcp_server_langgraph.mcp.message_handler.AuthenticatedMCPHandler") as mock_handler:
            await handler.on_connect(None)

        mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_disconnect(self) -> None:
        """GIVEN connected WHEN on_disconnect called THEN clears state."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        handler._mcp_handler = MagicMock()
        from mcp_server_langgraph.websocket.types import AuthUser

        handler._user = AuthUser(id="user-123", username="testuser", email="test@example.com", roles=["developer"])

        await handler.on_disconnect()

        assert handler._disconnected is True
        assert handler._mcp_handler is None


class TestMCPWebSocketHandlerMessages:
    """Tests for MCPWebSocketHandler message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_message_valid_jsonrpc(self) -> None:
        """GIVEN valid JSON-RPC message WHEN handle_message called THEN routes to handler."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        mock_mcp_handler = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_mcp_handler.handle.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"tools": []},
        }
        handler._mcp_handler = mock_mcp_handler

        jsonrpc_message = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        message = MessageEnvelope(type="mcp_request", payload=jsonrpc_message, id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.payload["jsonrpc"] == "2.0"
        assert "result" in response.payload
        mock_mcp_handler.handle.assert_called_once_with(jsonrpc_message)

    @pytest.mark.asyncio
    async def test_handle_message_invalid_jsonrpc_version(self) -> None:
        """GIVEN invalid JSON-RPC version WHEN handle_message called THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        jsonrpc_message = {"jsonrpc": "1.0", "id": 1, "method": "test"}
        message = MessageEnvelope(type="mcp_request", payload=jsonrpc_message, id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert "error" in response.payload
        assert response.payload["error"]["code"] == -32600  # INVALID_REQUEST

    @pytest.mark.asyncio
    async def test_handle_message_missing_method(self) -> None:
        """GIVEN message without method WHEN handle_message called THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        jsonrpc_message = {"jsonrpc": "2.0", "id": 1}
        message = MessageEnvelope(type="mcp_request", payload=jsonrpc_message, id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert "error" in response.payload
        assert response.payload["error"]["code"] == -32600

    @pytest.mark.asyncio
    async def test_handle_message_response_message(self) -> None:
        """GIVEN response message WHEN handle_message called THEN routes to handler."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        mock_mcp_handler = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_mcp_handler.handle.return_value = None
        handler._mcp_handler = mock_mcp_handler

        # Response message (has result, not method)
        jsonrpc_message = {"jsonrpc": "2.0", "id": 1, "result": {"success": True}}
        message = MessageEnvelope(type="mcp_request", payload=jsonrpc_message, id="msg-1")
        await handler.handle_message(message)

        mock_mcp_handler.handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_error_response(self) -> None:
        """GIVEN error response message WHEN handle_message called THEN routes to handler."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        mock_mcp_handler = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_mcp_handler.handle.return_value = None
        handler._mcp_handler = mock_mcp_handler

        # Error response message
        jsonrpc_message = {"jsonrpc": "2.0", "id": 1, "error": {"code": -1, "message": "Error"}}
        message = MessageEnvelope(type="mcp_request", payload=jsonrpc_message, id="msg-1")
        await handler.handle_message(message)

        mock_mcp_handler.handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_creates_handler_if_none(self) -> None:
        """GIVEN no handler WHEN handle_message called THEN creates handler."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        handler._mcp_handler = None

        with patch("mcp_server_langgraph.mcp.message_handler.MCPMessageHandler") as mock_handler_class:
            mock_instance = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_instance.handle.return_value = {"jsonrpc": "2.0", "id": 1, "result": {}}
            mock_handler_class.return_value = mock_instance

            jsonrpc_message = {"jsonrpc": "2.0", "id": 1, "method": "test"}
            message = MessageEnvelope(type="mcp_request", payload=jsonrpc_message, id="msg-1")
            await handler.handle_message(message)

            mock_handler_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_exception(self) -> None:
        """GIVEN handler exception WHEN handle_message called THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        mock_mcp_handler = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_mcp_handler.handle.side_effect = Exception("Internal error")
        handler._mcp_handler = mock_mcp_handler

        jsonrpc_message = {"jsonrpc": "2.0", "id": 1, "method": "test"}
        message = MessageEnvelope(type="mcp_request", payload=jsonrpc_message, id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert "error" in response.payload
        assert response.payload["error"]["code"] == -32603  # INTERNAL_ERROR


class TestMCPWebSocketHandlerValidation:
    """Tests for MCPWebSocketHandler JSON-RPC validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validate_jsonrpc_valid(self) -> None:
        """GIVEN valid message WHEN _validate_jsonrpc called THEN returns None."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        message = {"jsonrpc": "2.0", "id": 1, "method": "test"}
        result = handler._validate_jsonrpc(message)

        assert result is None

    def test_validate_jsonrpc_invalid_version(self) -> None:
        """GIVEN invalid version WHEN _validate_jsonrpc called THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        message = {"jsonrpc": "1.0", "id": 1, "method": "test"}
        result = handler._validate_jsonrpc(message)

        assert result is not None
        assert result["error"]["code"] == -32600

    def test_validate_jsonrpc_missing_version(self) -> None:
        """GIVEN missing version WHEN _validate_jsonrpc called THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        message = {"id": 1, "method": "test"}
        result = handler._validate_jsonrpc(message)

        assert result is not None
        assert result["error"]["code"] == -32600

    def test_validate_jsonrpc_missing_method(self) -> None:
        """GIVEN missing method WHEN _validate_jsonrpc called THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        message = {"jsonrpc": "2.0", "id": 1}
        result = handler._validate_jsonrpc(message)

        assert result is not None
        assert result["error"]["code"] == -32600

    def test_validate_jsonrpc_with_result(self) -> None:
        """GIVEN message with result WHEN _validate_jsonrpc called THEN returns None."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        message = {"jsonrpc": "2.0", "id": 1, "result": {}}
        result = handler._validate_jsonrpc(message)

        assert result is None

    def test_validate_jsonrpc_with_error(self) -> None:
        """GIVEN message with error WHEN _validate_jsonrpc called THEN returns None."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        message = {"jsonrpc": "2.0", "id": 1, "error": {"code": -1, "message": "Error"}}
        result = handler._validate_jsonrpc(message)

        assert result is None


class TestMCPWebSocketHandlerError:
    """Tests for MCPWebSocketHandler error response generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_error_response_returns_formatted_jsonrpc_error(self) -> None:
        """GIVEN error params WHEN _error_response called THEN returns formatted error."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        result = handler._error_response(123, -32600, "Invalid request")

        assert result["jsonrpc"] == "2.0"
        assert result["id"] == 123
        assert result["error"]["code"] == -32600
        assert result["error"]["message"] == "Invalid request"

    def test_error_response_null_id(self) -> None:
        """GIVEN null id WHEN _error_response called THEN returns error with null id."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        result = handler._error_response(None, -32700, "Parse error")

        assert result["id"] is None
        assert result["error"]["code"] == -32700


class TestMCPWebSocketHandlerNotification:
    """Tests for MCPWebSocketHandler notification sending."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_send_notification(self) -> None:
        """GIVEN websocket WHEN _send_notification called THEN sends."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws

        notification = {"jsonrpc": "2.0", "method": "progress", "params": {"progress": 50}}
        await handler._send_notification(notification)

        mock_ws.send_json.assert_called_once_with(notification)

    @pytest.mark.asyncio
    async def test_send_notification_no_websocket(self) -> None:
        """GIVEN no websocket WHEN _send_notification called THEN does not send."""
        from mcp_server_langgraph.websocket.handlers.mcp import MCPWebSocketHandler

        with patch(RATE_LIMITER_PATCH, side_effect=lambda *a, **kw: MagicMock()):
            handler = MCPWebSocketHandler()

        # No websocket
        notification = {"jsonrpc": "2.0", "method": "progress"}
        await handler._send_notification(notification)
        # Should not raise
