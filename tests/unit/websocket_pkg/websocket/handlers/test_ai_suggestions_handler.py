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


@pytest.mark.xdist_group(name="ai_suggestions_handler")
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

        assert handler._user_id is None
        assert handler._session_context == {}

    @pytest.mark.asyncio
    async def test_on_connect_stores_user_id(self, ai_suggestions_config, mock_user) -> None:
        """Test that on_connect stores the user ID."""
        from mcp_server_langgraph.websocket.handlers.ai_suggestions import (
            AISuggestionsHandler,
        )

        handler = AISuggestionsHandler(config=ai_suggestions_config)
        handler._websocket = MagicMock()

        await handler.on_connect(mock_user)

        assert handler._user_id == "user-123"

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

        # Normal flow: on_connect is called first
        await handler.on_connect(mock_user)
        assert handler._user_id == "user-123"

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
        # handler._user_id is still None (on_connect never called)
        assert handler._user_id is None

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
        assert handler._user_id is None
        assert handler._user is None

        # Disconnect happens - should not crash - capture logs at INFO level
        with caplog.at_level(logging.INFO, logger=AI_SUGGESTIONS_LOGGER):
            await handler.on_disconnect()

        # Should log with None (acceptable in this edge case)
        assert "disconnected" in caplog.text
