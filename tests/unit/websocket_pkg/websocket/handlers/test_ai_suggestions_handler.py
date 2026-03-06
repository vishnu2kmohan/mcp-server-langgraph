"""
Unit tests for AISuggestionsHandler.

TDD: These tests define expected behavior for the AI suggestions WebSocket handler.
The handler should:
- Track user ID on connect
- Log user ID on disconnect (even if on_connect was never called)
- Handle suggestion requests
"""

import gc
import logging
from unittest.mock import MagicMock

import pytest

from mcp_server_langgraph.websocket.types import (
    AuthUser,
    WebSocketConfig,
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

# Logger name for the AI suggestions handler
AI_SUGGESTIONS_LOGGER = "mcp_server_langgraph.websocket.handlers.ai_suggestions"


@pytest.fixture
def ai_suggestions_config():
    """Create a standard AI suggestions handler configuration."""
    return WebSocketConfig(
        endpoint_name="ai-suggestions",
        require_auth=True,
        authz_resource_type="ai",
        authz_resource_id="suggestions",
        authz_required_relation="user",
        rate_limit_per_minute=300,
        message_timeout=30,
    )


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    return AuthUser(
        id="user-123",
        username="testuser",
        email="test@example.com",
        roles=["developer"],
    )


class TestAISuggestionsHandler:
    """Tests for AISuggestionsHandler class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_initializes_with_config(self, ai_suggestions_config) -> None:
        """Test handler initialization with required dependencies."""
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )

        handler = AISuggestionsHandler(config=ai_suggestions_config)

        assert handler.user_id is None
        assert handler._session_context == {}

    @pytest.mark.asyncio
    async def test_on_connect_stores_user_id(self, ai_suggestions_config, mock_user) -> None:
        """Test that on_connect stores the user ID."""
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )

        handler = AISuggestionsHandler(config=ai_suggestions_config)
        handler._websocket = MagicMock()
        # Simulate base class run() which sets _user before calling on_connect
        handler._user = mock_user

        await handler.on_connect(mock_user)

        assert handler.user_id == "user-123"

    @pytest.mark.asyncio
    async def test_on_disconnect_logs_user_id_when_on_connect_was_called(
        self, ai_suggestions_config, mock_user, caplog
    ) -> None:
        """Test that on_disconnect logs the user ID after normal connection flow."""
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )

        handler = AISuggestionsHandler(config=ai_suggestions_config)
        handler._websocket = MagicMock()
        # Simulate base class run() which sets _user before calling on_connect
        handler._user = mock_user

        # Normal flow: on_connect is called first
        await handler.on_connect(mock_user)
        assert handler.user_id == "user-123"

        # Then disconnect - capture logs at INFO level
        with caplog.at_level(logging.INFO, logger=AI_SUGGESTIONS_LOGGER):
            await handler.on_disconnect()

        # Should log the user ID
        assert "user=user-123" in caplog.text

    @pytest.mark.asyncio
    async def test_on_disconnect_logs_user_from_base_class_when_on_connect_never_called(
        self, ai_suggestions_config, mock_user, caplog
    ) -> None:
        """
        Test that on_disconnect falls back to base class user when on_connect was never called.

        This tests the race condition scenario where:
        1. Client connects with valid token
        2. Token is verified successfully (base class sets self._user)
        3. Client disconnects BEFORE on_connect() is called
        4. on_disconnect() should still log the user ID from base class
        """
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )

        handler = AISuggestionsHandler(config=ai_suggestions_config)
        handler._websocket = MagicMock()

        # Simulate the race condition:
        # Base class has set self._user, but on_connect() was never called
        handler._user = mock_user  # Base class user is set
        # user_id property derives from _user, so it should be available
        assert handler.user_id == "user-123"

        # Disconnect happens - capture logs at INFO level
        with caplog.at_level(logging.INFO, logger=AI_SUGGESTIONS_LOGGER):
            await handler.on_disconnect()

        # Should log the user ID from base class, NOT "None"
        assert "user=user-123" in caplog.text
        assert "user=None" not in caplog.text

    @pytest.mark.asyncio
    async def test_on_disconnect_handles_completely_unauthenticated_case(self, ai_suggestions_config, caplog) -> None:
        """
        Test that on_disconnect handles the case where neither _user nor _user_id is set.

        This happens when authentication fails completely.
        """
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )

        handler = AISuggestionsHandler(config=ai_suggestions_config)
        handler._websocket = MagicMock()

        # Neither base class user nor handler user_id is set
        assert handler.user_id is None
        assert handler._user is None

        # Disconnect happens - should not crash - capture logs at INFO level
        with caplog.at_level(logging.INFO, logger=AI_SUGGESTIONS_LOGGER):
            await handler.on_disconnect()

        # Should log with None (acceptable in this edge case)
        assert "disconnected" in caplog.text


class TestAISuggestionsHandlerErrorResponses:
    """Tests for AISuggestionsHandler error response format (ADR-0093 protocol compliance)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_error_response_format(self, ai_suggestions_config) -> None:
        """
        Test that _create_error_response returns ADR-0093 compliant format.

        ADR-0093 specifies error responses MUST have:
        - type: "error"
        - payload: { code: str, message: str, retryable: bool }
        """
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )
        from mcp_server_langgraph.websocket.types import AISuggestionMessageType

        handler = AISuggestionsHandler(config=ai_suggestions_config)

        response = handler._create_error_response(
            code="test_code",
            message="Test error message",
            retryable=True,
        )

        # MUST have type="error"
        assert response.type == AISuggestionMessageType.ERROR

        # MUST have payload (NOT data!)
        assert response.payload is not None

        # Payload MUST contain all required fields
        assert response.payload["code"] == "test_code"
        assert response.payload["message"] == "Test error message"
        assert response.payload["retryable"] is True

    def test_error_response_with_retryable_false(self, ai_suggestions_config) -> None:
        """Test error response with retryable=False."""
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )

        handler = AISuggestionsHandler(config=ai_suggestions_config)

        response = handler._create_error_response(
            code="invalid_request",
            message="Request is invalid",
            retryable=False,
        )

        assert response.payload["retryable"] is False

    def test_error_response_serializes_correctly(self, ai_suggestions_config) -> None:
        """Test that error response serializes to correct JSON format for frontend."""
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )

        handler = AISuggestionsHandler(config=ai_suggestions_config)

        response = handler._create_error_response(
            code="internal_error",
            message="An internal error occurred",
            retryable=True,
        )

        # Serialize to dict (what gets sent over WebSocket)
        response_dict = response.to_dict()

        # Frontend expects this exact structure
        assert response_dict["type"] == "error"
        assert "payload" in response_dict
        assert response_dict["payload"]["code"] == "internal_error"
        assert response_dict["payload"]["message"] == "An internal error occurred"
        assert response_dict["payload"]["retryable"] is True

        # MUST NOT have "data" field (this was the bug)
        assert "data" not in response_dict

    @pytest.mark.asyncio
    async def test_handle_message_returns_error_on_exception(self, ai_suggestions_config, mock_user) -> None:
        """Test that handle_message returns proper error format on exception."""
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )
        from mcp_server_langgraph.websocket.types import (
            AISuggestionMessageType,
            MessageEnvelope,
        )

        handler = AISuggestionsHandler(config=ai_suggestions_config)
        handler._websocket = MagicMock()
        handler._user = mock_user
        # user_id is now a property on base class backed by self._user (already set above)

        # Create a message that will trigger an exception (missing required fields)
        bad_message = MessageEnvelope(
            type=AISuggestionMessageType.SUGGESTION_REQUEST,
            payload={"invalid": "payload"},  # Missing required fields
        )

        response = await handler.handle_message(bad_message)

        # Should return error response with correct format
        assert response is not None
        assert response.type == AISuggestionMessageType.ERROR
        assert response.payload is not None
        assert "code" in response.payload
        assert "message" in response.payload
        assert "retryable" in response.payload

    @pytest.mark.asyncio
    async def test_handle_invalid_request_returns_error(self, ai_suggestions_config, mock_user) -> None:
        """Test that invalid suggestion request returns proper error."""
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )
        from mcp_server_langgraph.websocket.types import (
            AISuggestionMessageType,
            MessageEnvelope,
        )

        handler = AISuggestionsHandler(config=ai_suggestions_config)
        handler._websocket = MagicMock()
        handler._user = mock_user
        # user_id is now a property on base class backed by self._user (already set above)

        # Create a suggestion request with missing session_id
        message = MessageEnvelope(
            type=AISuggestionMessageType.SUGGESTION_REQUEST,
            payload={
                "input_text": "Hello",
                "cursor_position": 5,
                # session_id is missing
            },
        )

        response = await handler.handle_message(message)

        # Should return error with "invalid_request" or "missing_session" code
        assert response is not None
        assert response.type == AISuggestionMessageType.ERROR
        assert response.payload["code"] in ["invalid_request", "missing_session"]
        assert response.payload["retryable"] is False
