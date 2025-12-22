"""
Agent Request WebSocket Handler Tests.

TDD tests for the Agent Request (HITL) WebSocket using the standardized WebSocketBase.
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.websocket import (
    MessageEnvelope,
    WebSocketConfig,
)

pytestmark = [pytest.mark.unit, pytest.mark.websocket]


@pytest.fixture
def mock_websocket() -> MagicMock:
    """Create a mock WebSocket for testing."""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    ws.send_json = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_json = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.query_params = {}
    ws.headers = {}
    ws.client_state = MagicMock()
    return ws


@pytest.fixture
def mock_hitl_broadcaster() -> MagicMock:
    """Create a mock HITL broadcaster."""
    broadcaster = MagicMock()
    broadcaster.connect = AsyncMock()
    broadcaster.disconnect = MagicMock()
    broadcaster.broadcast = AsyncMock()
    broadcaster.send_to_session = AsyncMock()
    return broadcaster


@pytest.mark.xdist_group(name="agent_request_ws")
class TestAgentRequestHandler:
    """Test Agent Request WebSocket using WebSocketBase."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handler_extends_websocket_base(self) -> None:
        """
        GIVEN the AgentRequestHandler class
        WHEN checking its base classes
        THEN it should extend WebSocketBase.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase
        from mcp_server_langgraph.websocket.handlers.agent_request import (
            AgentRequestHandler,
        )

        assert issubclass(AgentRequestHandler, WebSocketBase)

    @pytest.mark.asyncio
    async def test_handles_subscribe_message(
        self, mock_websocket: MagicMock, mock_hitl_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN an active connection
        WHEN a subscribe message is received
        THEN subscription should be confirmed.
        """
        from mcp_server_langgraph.websocket.handlers.agent_request import (
            AgentRequestHandler,
        )

        handler = AgentRequestHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="agent-request"),
            broadcaster=mock_hitl_broadcaster,
            session_id="session-123",
        )
        handler._websocket = mock_websocket

        message = MessageEnvelope(
            type="subscribe",
            payload={"session_id": "session-123"},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "subscribed"

    @pytest.mark.asyncio
    async def test_handles_unsubscribe_message(
        self, mock_websocket: MagicMock, mock_hitl_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN an active subscription
        WHEN an unsubscribe message is received
        THEN unsubscription should be confirmed.
        """
        from mcp_server_langgraph.websocket.handlers.agent_request import (
            AgentRequestHandler,
        )

        handler = AgentRequestHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="agent-request"),
            broadcaster=mock_hitl_broadcaster,
            session_id="session-123",
        )
        handler._subscribed = True

        message = MessageEnvelope(
            type="unsubscribe",
            payload={},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"
        assert handler._subscribed is False

    @pytest.mark.asyncio
    async def test_returns_error_for_unknown_message(
        self, mock_websocket: MagicMock, mock_hitl_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN an active connection
        WHEN an unknown message type is received
        THEN an error response should be returned.
        """
        from mcp_server_langgraph.websocket.handlers.agent_request import (
            AgentRequestHandler,
        )

        handler = AgentRequestHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="agent-request"),
            broadcaster=mock_hitl_broadcaster,
            session_id="session-123",
        )

        message = MessageEnvelope(
            type="unknown_type",
            payload={},
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"

    @pytest.mark.asyncio
    async def test_push_approval_required(
        self, mock_websocket: MagicMock, mock_hitl_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN an active subscription
        WHEN push_approval_required is called
        THEN approval request should be sent to client.
        """
        from mcp_server_langgraph.websocket.handlers.agent_request import (
            AgentRequestHandler,
        )

        handler = AgentRequestHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="agent-request"),
            broadcaster=mock_hitl_broadcaster,
            session_id="session-123",
        )
        handler._websocket = mock_websocket
        handler._subscribed = True

        await handler.push_approval_required({
            "request_id": "req-001",
            "agent_name": "TestAgent",
            "confidence": 0.3,
            "proposed_action": "Execute tool",
        })

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "approval_required"
        assert call_args["payload"]["request_id"] == "req-001"

    @pytest.mark.asyncio
    async def test_push_clarification_required(
        self, mock_websocket: MagicMock, mock_hitl_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN an active subscription
        WHEN push_clarification_required is called
        THEN clarification request should be sent to client.
        """
        from mcp_server_langgraph.websocket.handlers.agent_request import (
            AgentRequestHandler,
        )

        handler = AgentRequestHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="agent-request"),
            broadcaster=mock_hitl_broadcaster,
            session_id="session-123",
        )
        handler._websocket = mock_websocket
        handler._subscribed = True

        await handler.push_clarification_required({
            "request_id": "req-002",
            "agent_name": "TestAgent",
            "question": "What database should I use?",
            "options": ["PostgreSQL", "MySQL", "SQLite"],
        })

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "clarification_required"
        assert call_args["payload"]["request_id"] == "req-002"

    @pytest.mark.asyncio
    async def test_push_not_sent_when_unsubscribed(
        self, mock_websocket: MagicMock, mock_hitl_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN a connection that is not subscribed
        WHEN push_approval_required is called
        THEN message should not be sent.
        """
        from mcp_server_langgraph.websocket.handlers.agent_request import (
            AgentRequestHandler,
        )

        handler = AgentRequestHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="agent-request"),
            broadcaster=mock_hitl_broadcaster,
            session_id="session-123",
        )
        handler._websocket = mock_websocket
        handler._subscribed = False

        await handler.push_approval_required({
            "request_id": "req-001",
            "agent_name": "TestAgent",
        })

        mock_websocket.send_json.assert_not_called()
