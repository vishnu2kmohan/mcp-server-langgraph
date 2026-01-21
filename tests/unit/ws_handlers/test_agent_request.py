"""
Agent Request WebSocket Handler Tests.

TDD tests for the Agent Request (HITL) WebSocket using the standardized WebSocketBase.
"""

from __future__ import annotations

import gc
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
    ws.accept = AsyncMock()  # noqa: async-mock-config
    ws.close = AsyncMock()  # noqa: async-mock-config
    ws.send_json = AsyncMock()  # noqa: async-mock-config
    ws.send_text = AsyncMock()  # noqa: async-mock-config
    ws.receive_json = AsyncMock()  # noqa: async-mock-config
    ws.receive_text = AsyncMock()  # noqa: async-mock-config
    ws.query_params = {}
    ws.headers = {}
    ws.client_state = MagicMock()
    return ws


@pytest.fixture
def mock_hitl_broadcaster() -> MagicMock:
    """Create a mock HITL broadcaster."""
    broadcaster = MagicMock()
    broadcaster.connect = AsyncMock()  # noqa: async-mock-config
    broadcaster.disconnect = MagicMock()
    broadcaster.broadcast = AsyncMock()  # noqa: async-mock-config
    broadcaster.send_to_session = AsyncMock()  # noqa: async-mock-config
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
    async def test_handles_subscribe_message(self, mock_websocket: MagicMock, mock_hitl_broadcaster: MagicMock) -> None:
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
    async def test_handles_unsubscribe_message(self, mock_websocket: MagicMock, mock_hitl_broadcaster: MagicMock) -> None:
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
    async def test_push_approval_required(self, mock_websocket: MagicMock, mock_hitl_broadcaster: MagicMock) -> None:
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

        await handler.push_approval_required(
            {
                "request_id": "req-001",
                "agent_name": "TestAgent",
                "confidence": 0.3,
                "proposed_action": "Execute tool",
            }
        )

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "approval_required"
        assert call_args["payload"]["request_id"] == "req-001"

    @pytest.mark.asyncio
    async def test_push_clarification_required(self, mock_websocket: MagicMock, mock_hitl_broadcaster: MagicMock) -> None:
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

        await handler.push_clarification_required(
            {
                "request_id": "req-002",
                "agent_name": "TestAgent",
                "question": "What database should I use?",
                "options": ["PostgreSQL", "MySQL", "SQLite"],
            }
        )

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "clarification_required"
        assert call_args["payload"]["request_id"] == "req-002"

    @pytest.mark.asyncio
    async def test_push_not_sent_when_unsubscribed(self, mock_websocket: MagicMock, mock_hitl_broadcaster: MagicMock) -> None:
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

        await handler.push_approval_required(
            {
                "request_id": "req-001",
                "agent_name": "TestAgent",
            }
        )

        mock_websocket.send_json.assert_not_called()


@pytest.mark.xdist_group(name="agent_request_ws")
class TestAgentRequestSessionIdFromQueryParams:
    """Test session_id extraction from WebSocket query parameters.

    These tests verify that AgentRequestHandler properly extracts session_id
    from URL query parameters during on_connect, instead of defaulting to "global".

    This is critical for session-scoped HITL notifications where the frontend
    connects with ?session_id=<session_id> in the URL.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_extracts_session_id_from_query_params(
        self, mock_hitl_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN a WebSocket connection with session_id in query params
        WHEN on_connect is called
        THEN the handler should extract and use the session_id (not "global").
        """
        from mcp_server_langgraph.websocket.handlers.agent_request import (
            AgentRequestHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser

        # Create websocket with session_id in query params
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.send_json = AsyncMock()
        ws.query_params = {"v": "1.0.0", "session_id": "session-from-url"}
        ws.headers = {}

        handler = AgentRequestHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="agent-request"),
            broadcaster=mock_hitl_broadcaster,
            # No session_id passed to constructor
        )
        handler._websocket = ws

        user = AuthUser(id="test-user", username="testuser")
        await handler.on_connect(user)

        # Verify session_id was extracted from query params (not "global")
        assert handler._session_id == "session-from-url"

    @pytest.mark.asyncio
    async def test_on_connect_passes_session_id_to_broadcaster(
        self, mock_hitl_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN a WebSocket connection with session_id in query params
        WHEN on_connect calls broadcaster.connect
        THEN the session_id from query params should be passed to broadcaster.
        """
        from mcp_server_langgraph.websocket.handlers.agent_request import (
            AgentRequestHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser

        # Create websocket with session_id in query params
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.send_json = AsyncMock()
        ws.query_params = {"v": "1.0.0", "session_id": "session-xyz-789"}
        ws.headers = {}

        handler = AgentRequestHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="agent-request"),
            broadcaster=mock_hitl_broadcaster,
        )
        handler._websocket = ws

        user = AuthUser(id="test-user", username="testuser")
        await handler.on_connect(user)

        # Verify broadcaster.connect was called with the session_id from URL
        mock_hitl_broadcaster.connect.assert_called_once()
        call_args = mock_hitl_broadcaster.connect.call_args
        # broadcaster.connect(websocket, session_id, user_id, accept=False)
        assert call_args[0][1] == "session-xyz-789"  # session_id is second positional arg

    @pytest.mark.asyncio
    async def test_constructor_session_id_takes_precedence(
        self, mock_hitl_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN a handler with session_id from constructor and query params
        WHEN on_connect is called
        THEN constructor session_id should take precedence over query params.
        """
        from mcp_server_langgraph.websocket.handlers.agent_request import (
            AgentRequestHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser

        # Create websocket with session_id in query params
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.send_json = AsyncMock()
        ws.query_params = {"v": "1.0.0", "session_id": "session-from-url"}
        ws.headers = {}

        handler = AgentRequestHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="agent-request"),
            broadcaster=mock_hitl_broadcaster,
            session_id="session-from-constructor",  # Explicit constructor value
        )
        handler._websocket = ws

        user = AuthUser(id="test-user", username="testuser")
        await handler.on_connect(user)

        # Constructor value should take precedence
        assert handler._session_id == "session-from-constructor"

    @pytest.mark.asyncio
    async def test_defaults_to_global_when_no_session_id_anywhere(
        self, mock_websocket: MagicMock, mock_hitl_broadcaster: MagicMock
    ) -> None:
        """
        GIVEN a handler without session_id in constructor or query params
        WHEN on_connect is called
        THEN it should still default to "global" for backward compatibility.
        """
        from mcp_server_langgraph.websocket.handlers.agent_request import (
            AgentRequestHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser

        # mock_websocket has query_params = {} (no session_id)
        handler = AgentRequestHandler(
            config=WebSocketConfig(require_auth=False, endpoint_name="agent-request"),
            broadcaster=mock_hitl_broadcaster,
            # No session_id
        )
        handler._websocket = mock_websocket

        user = AuthUser(id="test-user", username="testuser")
        await handler.on_connect(user)

        # Should default to "global" when no session_id anywhere
        assert handler._session_id == "global"
