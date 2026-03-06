"""
Unit tests for Agent Request (HITL) WebSocket Handler.

Tests the AgentRequestHandler class for Human-in-the-Loop notifications.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="websocket_agent_request_handler"),
]

RATE_LIMITER_PATCH = "mcp_server_langgraph.websocket.rate_limiter.get_websocket_rate_limiter"


class TestAgentRequestHandlerInit:
    """Tests for AgentRequestHandler initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_init_stores_broadcaster(self) -> None:
        """GIVEN broadcaster WHEN creating handler THEN stores broadcaster."""
        from mcp_server_langgraph.websocket.handlers.agent_request import AgentRequestHandler
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="agent-request")
        mock_broadcaster = MagicMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AgentRequestHandler(config=config, broadcaster=mock_broadcaster)

        assert handler._broadcaster is mock_broadcaster
        assert handler._session_id == "global"
        assert handler._subscribed is False

    def test_init_with_session_id(self) -> None:
        """GIVEN session_id WHEN creating handler THEN stores session_id."""
        from mcp_server_langgraph.websocket.handlers.agent_request import AgentRequestHandler
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="agent-request")
        mock_broadcaster = MagicMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AgentRequestHandler(config=config, broadcaster=mock_broadcaster, session_id="sess-123")

        assert handler._session_id == "sess-123"


class TestAgentRequestHandlerLifecycle:
    """Tests for AgentRequestHandler lifecycle hooks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_registers(self) -> None:
        """GIVEN user WHEN on_connect called THEN connects to broadcaster."""
        from mcp_server_langgraph.websocket.handlers.agent_request import AgentRequestHandler
        from mcp_server_langgraph.websocket.types import AuthUser, WebSocketConfig

        config = WebSocketConfig(endpoint_name="agent-request")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AgentRequestHandler(config=config, broadcaster=mock_broadcaster, session_id="sess-123")

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        user = AuthUser(id="user-123", username="testuser")
        handler._user = user  # Base class sets this before calling on_connect

        await handler.on_connect(user)

        assert handler.user_id == "user-123"
        # accept=False because WebSocketBase already accepted the connection
        mock_broadcaster.connect.assert_called_once_with(mock_ws, "sess-123", "user-123", accept=False)

    @pytest.mark.asyncio
    async def test_on_disconnect_unregisters(self) -> None:
        """GIVEN connected WHEN on_disconnect called THEN disconnects."""
        from mcp_server_langgraph.websocket.handlers.agent_request import AgentRequestHandler
        from mcp_server_langgraph.websocket.types import AuthUser, WebSocketConfig

        config = WebSocketConfig(endpoint_name="agent-request")
        mock_broadcaster = MagicMock()

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AgentRequestHandler(config=config, broadcaster=mock_broadcaster)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler._subscribed = True
        handler._user = AuthUser(id="user-123", username="user-123")

        await handler.on_disconnect()

        mock_broadcaster.disconnect.assert_called_once_with(mock_ws)
        assert handler._subscribed is False


class TestAgentRequestHandlerMessages:
    """Tests for AgentRequestHandler message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_subscribe(self) -> None:
        """GIVEN subscribe message WHEN handle_message called THEN subscribes."""
        from mcp_server_langgraph.websocket.handlers.agent_request import AgentRequestHandler
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="agent-request")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AgentRequestHandler(config=config, broadcaster=mock_broadcaster)

        message = MessageEnvelope(type="subscribe", id="msg-1")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "subscribed"
        assert handler._subscribed is True

    @pytest.mark.asyncio
    async def test_handle_subscribe_with_session_id(self) -> None:
        """GIVEN subscribe with session_id WHEN handle_message called THEN uses session_id."""
        from mcp_server_langgraph.websocket.handlers.agent_request import AgentRequestHandler
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="agent-request")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AgentRequestHandler(config=config, broadcaster=mock_broadcaster)

        message = MessageEnvelope(type="subscribe", id="msg-1", payload={"session_id": "new-session"})
        response = await handler.handle_message(message)

        assert response is not None
        assert response.payload["session_id"] == "new-session"
        assert handler._session_id == "new-session"

    @pytest.mark.asyncio
    async def test_handle_unsubscribe(self) -> None:
        """GIVEN subscribed WHEN unsubscribe message THEN unsubscribes."""
        from mcp_server_langgraph.websocket.handlers.agent_request import AgentRequestHandler
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="agent-request")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AgentRequestHandler(config=config, broadcaster=mock_broadcaster)

        handler._subscribed = True

        message = MessageEnvelope(type="unsubscribe", id="msg-2")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"
        assert handler._subscribed is False

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self) -> None:
        """GIVEN unknown message type WHEN handle_message called THEN returns error."""
        from mcp_server_langgraph.websocket.handlers.agent_request import AgentRequestHandler
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

        config = WebSocketConfig(endpoint_name="agent-request")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AgentRequestHandler(config=config, broadcaster=mock_broadcaster)

        message = MessageEnvelope(type="invalid", id="msg-3")
        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "unknown_message_type"


class TestAgentRequestHandlerPush:
    """Tests for AgentRequestHandler push functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_push_approval_required_when_subscribed(self) -> None:
        """GIVEN subscribed WHEN push_approval_required THEN sends."""
        from mcp_server_langgraph.websocket.handlers.agent_request import AgentRequestHandler
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="agent-request")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AgentRequestHandler(config=config, broadcaster=mock_broadcaster)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler._subscribed = True

        request = {"id": "req-1", "action": "deploy", "confidence": 0.3}
        await handler.push_approval_required(request)

        mock_ws.send_json.assert_called_once()
        sent_data = mock_ws.send_json.call_args[0][0]
        assert sent_data["type"] == "approval_required"
        assert sent_data["payload"] == request

    @pytest.mark.asyncio
    async def test_push_approval_required_when_not_subscribed(self) -> None:
        """GIVEN not subscribed WHEN push_approval_required THEN does not send."""
        from mcp_server_langgraph.websocket.handlers.agent_request import AgentRequestHandler
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="agent-request")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AgentRequestHandler(config=config, broadcaster=mock_broadcaster)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler._subscribed = False

        await handler.push_approval_required({"id": "req-1"})

        mock_ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_clarification_required(self) -> None:
        """GIVEN subscribed WHEN push_clarification_required THEN sends."""
        from mcp_server_langgraph.websocket.handlers.agent_request import AgentRequestHandler
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="agent-request")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AgentRequestHandler(config=config, broadcaster=mock_broadcaster)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler._subscribed = True

        request = {"id": "req-2", "question": "Which environment?"}
        await handler.push_clarification_required(request)

        mock_ws.send_json.assert_called_once()
        sent_data = mock_ws.send_json.call_args[0][0]
        assert sent_data["type"] == "clarification_required"

    @pytest.mark.asyncio
    async def test_push_approval_updated(self) -> None:
        """GIVEN subscribed WHEN push_approval_updated THEN sends."""
        from mcp_server_langgraph.websocket.handlers.agent_request import AgentRequestHandler
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="agent-request")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AgentRequestHandler(config=config, broadcaster=mock_broadcaster)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler._subscribed = True

        await handler.push_approval_updated(
            request_id="req-1",
            status="approved",
            decided_by="admin",
            reason="Looks good",
        )

        mock_ws.send_json.assert_called_once()
        sent_data = mock_ws.send_json.call_args[0][0]
        assert sent_data["type"] == "approval_updated"
        assert sent_data["payload"]["status"] == "approved"
        assert sent_data["payload"]["reason"] == "Looks good"

    @pytest.mark.asyncio
    async def test_push_execution_resumed(self) -> None:
        """GIVEN subscribed WHEN push_execution_resumed THEN sends."""
        from mcp_server_langgraph.websocket.handlers.agent_request import AgentRequestHandler
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(endpoint_name="agent-request")
        mock_broadcaster = AsyncMock(return_value=None)  # noqa: async-mock-config

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = AgentRequestHandler(config=config, broadcaster=mock_broadcaster)

        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_ws
        handler._subscribed = True

        await handler.push_execution_resumed(
            request_id="req-1",
            task_id="task-1",
            agent_name="deployment-agent",
            status="approved",
        )

        mock_ws.send_json.assert_called_once()
        sent_data = mock_ws.send_json.call_args[0][0]
        assert sent_data["type"] == "execution_resumed"
        assert sent_data["payload"]["agent_name"] == "deployment-agent"
