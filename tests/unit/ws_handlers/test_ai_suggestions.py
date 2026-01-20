"""
AI Suggestions WebSocket Handler Tests.

TDD tests for the AI Suggestions WebSocket using the standardized WebSocketBase.

Tests verify:
- Handler extends WebSocketBase correctly
- Method signatures match base class contract
- Message handling dispatches correctly
- Suggestion request/accept/reject flows work
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.websocket import MessageEnvelope, WebSocketConfig

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


@pytest.mark.xdist_group(name="ai_suggestions_ws")
class TestAISuggestionsHandlerConstruction:
    """Test AISuggestionsHandler initialization and base class contract."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_extends_websocket_base(self) -> None:
        """
        GIVEN the AISuggestionsHandler class
        WHEN checking its base classes
        THEN it should extend WebSocketBase.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )

        handler = AISuggestionsHandler(
            config=WebSocketConfig(endpoint_name="ai-suggestions")
        )
        assert isinstance(handler, WebSocketBase)

    def test_handler_has_handle_message_method(self) -> None:
        """
        GIVEN the AISuggestionsHandler class
        WHEN inspecting its methods
        THEN it should implement handle_message.
        """
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )

        handler = AISuggestionsHandler(
            config=WebSocketConfig(endpoint_name="ai-suggestions")
        )
        assert hasattr(handler, "handle_message")
        assert callable(getattr(handler, "handle_message"))


@pytest.mark.xdist_group(name="ai_suggestions_ws")
class TestAISuggestionsLifecycle:
    """Test AI Suggestions WebSocket lifecycle methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_receives_auth_user(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN an AISuggestionsHandler
        WHEN on_connect is called
        THEN it should accept AuthUser and store user_id.
        """
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser

        handler = AISuggestionsHandler(
            config=WebSocketConfig(endpoint_name="ai-suggestions")
        )
        handler._websocket = mock_websocket

        user = AuthUser(id="test-user", username="testuser")
        await handler.on_connect(user)

        assert handler._user_id == "test-user"

    @pytest.mark.asyncio
    async def test_on_disconnect_clears_context(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN an AISuggestionsHandler with session context
        WHEN on_disconnect is called
        THEN it should clear the session context.
        """
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser

        handler = AISuggestionsHandler(
            config=WebSocketConfig(endpoint_name="ai-suggestions")
        )
        handler._websocket = mock_websocket
        handler._user = AuthUser(id="test-user", username="testuser")
        handler._session_context = {"session-1": "context"}

        await handler.on_disconnect()

        assert handler._session_context == {}


@pytest.mark.xdist_group(name="ai_suggestions_ws")
class TestAISuggestionsMessageHandling:
    """Test AI Suggestions message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_message_returns_none_for_unknown_type(self) -> None:
        """
        GIVEN an unknown message type
        WHEN handle_message is called
        THEN it should return None (no response).
        """
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )

        handler = AISuggestionsHandler(
            config=WebSocketConfig(endpoint_name="ai-suggestions")
        )

        message = MessageEnvelope(
            type="unknown_type",
            payload={},
            id="msg-1",
        )

        response = await handler.handle_message(message)
        assert response is None

    @pytest.mark.asyncio
    async def test_handle_suggestion_request_missing_session(self) -> None:
        """
        GIVEN a suggestion_request without session_id
        WHEN handle_message is called
        THEN it should return error with missing_session code.
        """
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )
        from mcp_server_langgraph.websocket.types import AISuggestionMessageType

        handler = AISuggestionsHandler(
            config=WebSocketConfig(endpoint_name="ai-suggestions")
        )

        # Request with empty payload triggers parsing, then missing session
        message = MessageEnvelope(
            type=AISuggestionMessageType.SUGGESTION_REQUEST,
            payload={"input_text": "test"},  # Missing session_id
            id="msg-2",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert isinstance(response, MessageEnvelope)
        assert response.type == "error"
        assert response.payload is not None
        # Could be invalid_request (parsing error) or missing_session
        assert response.payload.get("code") in ["invalid_request", "missing_session"]

    @pytest.mark.asyncio
    async def test_handle_suggestion_accept_returns_none(self) -> None:
        """
        GIVEN a suggestion_accept message
        WHEN handle_message is called
        THEN it should return None (feedback messages have no response).
        """
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )
        from mcp_server_langgraph.websocket.types import AISuggestionMessageType

        handler = AISuggestionsHandler(
            config=WebSocketConfig(endpoint_name="ai-suggestions")
        )
        handler._user_id = "test-user"

        message = MessageEnvelope(
            type=AISuggestionMessageType.SUGGESTION_ACCEPT,
            payload={"suggestion_id": "sugg-123"},
            id="msg-3",
        )

        response = await handler.handle_message(message)

        # Accept/reject messages are logged but return None
        assert response is None

    @pytest.mark.asyncio
    async def test_handle_suggestion_reject_returns_none(self) -> None:
        """
        GIVEN a suggestion_reject message
        WHEN handle_message is called
        THEN it should return None (feedback messages have no response).
        """
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )
        from mcp_server_langgraph.websocket.types import AISuggestionMessageType

        handler = AISuggestionsHandler(
            config=WebSocketConfig(endpoint_name="ai-suggestions")
        )
        handler._user_id = "test-user"

        message = MessageEnvelope(
            type=AISuggestionMessageType.SUGGESTION_REJECT,
            payload={"suggestion_id": "sugg-456", "reason": "not helpful"},
            id="msg-4",
        )

        response = await handler.handle_message(message)

        # Accept/reject messages are logged but return None
        assert response is None

    @pytest.mark.asyncio
    async def test_handle_context_update_returns_none(self) -> None:
        """
        GIVEN a context_update message
        WHEN handle_message is called
        THEN it should update context and return None.
        """
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )
        from mcp_server_langgraph.websocket.types import AISuggestionMessageType

        handler = AISuggestionsHandler(
            config=WebSocketConfig(endpoint_name="ai-suggestions")
        )
        handler._user_id = "test-user"

        message = MessageEnvelope(
            type=AISuggestionMessageType.CONTEXT_UPDATE,
            payload={"session_id": "sess-789", "context": "new context"},
            id="msg-5",
        )

        response = await handler.handle_message(message)

        # Context update is processed but returns None
        assert response is None
        # Verify context was stored
        assert handler._session_context.get("sess-789") == "new context"
