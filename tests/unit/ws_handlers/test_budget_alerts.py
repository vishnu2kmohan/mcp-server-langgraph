"""
Budget Alerts WebSocket Handler Tests.

TDD tests for the Budget Alerts WebSocket using the standardized WebSocketBase.

Tests verify:
- Handler extends WebSocketBase correctly
- Method signatures match base class contract
- Subscription management works correctly
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.websocket import MessageEnvelope, WebSocketConfig

pytestmark = [pytest.mark.unit, pytest.mark.websocket]


@pytest.fixture
def mock_websocket() -> MagicMock:
    """Create a mock WebSocket for testing."""
    ws = MagicMock()
    ws.accept = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.close = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.send_json = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.send_text = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.receive_json = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.receive_text = AsyncMock(return_value=None)  # noqa: async-mock-config
    ws.query_params = {}
    ws.headers = {}
    ws.client_state = MagicMock()
    return ws


@pytest.fixture
def mock_broadcaster() -> MagicMock:
    """Create a mock budget alert broadcaster."""
    broadcaster = MagicMock()
    broadcaster.subscribe = AsyncMock(return_value=None)  # noqa: async-mock-config
    broadcaster.unsubscribe = AsyncMock(return_value=None)  # noqa: async-mock-config
    return broadcaster


@pytest.mark.xdist_group(name="budget_alerts_ws")
class TestBudgetAlertsHandlerConstruction:
    """Test BudgetAlertsHandler initialization and base class contract."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_extends_websocket_base(self) -> None:
        """
        GIVEN the BudgetAlertsHandler class
        WHEN checking its base classes
        THEN it should extend WebSocketBase.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase
        from mcp_server_langgraph.websocket.handlers.budget_alerts import (
            BudgetAlertsHandler,
        )

        handler = BudgetAlertsHandler(config=WebSocketConfig(endpoint_name="budget-alerts"))
        assert isinstance(handler, WebSocketBase)

    def test_handler_has_handle_message_method(self) -> None:
        """
        GIVEN the BudgetAlertsHandler class
        WHEN inspecting its methods
        THEN it should implement handle_message.
        """
        from mcp_server_langgraph.websocket.handlers.budget_alerts import (
            BudgetAlertsHandler,
        )

        handler = BudgetAlertsHandler(config=WebSocketConfig(endpoint_name="budget-alerts"))
        assert hasattr(handler, "handle_message")
        assert callable(handler.handle_message)


@pytest.mark.xdist_group(name="budget_alerts_ws")
class TestBudgetAlertsLifecycle:
    """Test Budget Alerts WebSocket lifecycle methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_connect_receives_auth_user(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a BudgetAlertsHandler
        WHEN on_connect is called
        THEN it should accept AuthUser.
        """
        from mcp_server_langgraph.websocket.handlers.budget_alerts import (
            BudgetAlertsHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser

        handler = BudgetAlertsHandler(config=WebSocketConfig(endpoint_name="budget-alerts"))
        handler._websocket = mock_websocket

        user = AuthUser(id="test-user", username="testuser")

        # Should not raise
        await handler.on_connect(user)

    @pytest.mark.asyncio
    async def test_on_disconnect_clears_subscriptions(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a BudgetAlertsHandler with subscriptions
        WHEN on_disconnect is called
        THEN it should clear subscriptions.
        """
        from mcp_server_langgraph.websocket.handlers.budget_alerts import (
            BudgetAlertsHandler,
        )
        from mcp_server_langgraph.websocket.types import AuthUser

        handler = BudgetAlertsHandler(config=WebSocketConfig(endpoint_name="budget-alerts"))
        handler._websocket = mock_websocket
        handler._user = AuthUser(id="test-user", username="testuser")
        handler.subscribed_entities = {"org:123", "project:456"}
        handler.subscribe_all = True

        await handler.on_disconnect()

        assert handler.subscribed_entities == set()
        assert handler.subscribe_all is False


@pytest.mark.xdist_group(name="budget_alerts_ws")
class TestBudgetAlertsMessageHandling:
    """Test Budget Alerts message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_subscribe_entities(self) -> None:
        """
        GIVEN a subscribe_entities message
        WHEN handle_message is called
        THEN it should subscribe to the specified entities.
        """
        from mcp_server_langgraph.websocket.handlers.budget_alerts import (
            BudgetAlertsHandler,
        )

        handler = BudgetAlertsHandler(config=WebSocketConfig(endpoint_name="budget-alerts"))

        message = MessageEnvelope(
            type="subscribe_entities",
            payload={"entity_ids": ["org:org-123", "project:proj-456"]},
            id="msg-1",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert isinstance(response, MessageEnvelope)
        assert response.type == "subscribed"
        assert "org:org-123" in handler.subscribed_entities
        assert "project:proj-456" in handler.subscribed_entities

    @pytest.mark.asyncio
    async def test_handle_subscribe_all(self) -> None:
        """
        GIVEN a subscribe_all message
        WHEN handle_message is called
        THEN it should set subscribe_all flag.
        """
        from mcp_server_langgraph.websocket.handlers.budget_alerts import (
            BudgetAlertsHandler,
        )

        handler = BudgetAlertsHandler(config=WebSocketConfig(endpoint_name="budget-alerts"))

        message = MessageEnvelope(
            type="subscribe_all",
            payload={},
            id="msg-2",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert isinstance(response, MessageEnvelope)
        assert response.type == "subscribed"
        assert handler.subscribe_all is True

    @pytest.mark.asyncio
    async def test_handle_unsubscribe(self) -> None:
        """
        GIVEN an unsubscribe message
        WHEN handle_message is called
        THEN it should clear subscriptions.
        """
        from mcp_server_langgraph.websocket.handlers.budget_alerts import (
            BudgetAlertsHandler,
        )

        handler = BudgetAlertsHandler(config=WebSocketConfig(endpoint_name="budget-alerts"))
        handler.subscribed_entities = {"org:123"}
        handler.subscribe_all = True

        message = MessageEnvelope(
            type="unsubscribe",
            payload={},
            id="msg-3",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert isinstance(response, MessageEnvelope)
        assert response.type == "unsubscribed"
        assert handler.subscribed_entities == set()
        assert handler.subscribe_all is False

    @pytest.mark.asyncio
    async def test_handle_unknown_type_returns_error(self) -> None:
        """
        GIVEN an unknown message type
        WHEN handle_message is called
        THEN it should return an error response.
        """
        from mcp_server_langgraph.websocket.handlers.budget_alerts import (
            BudgetAlertsHandler,
        )

        handler = BudgetAlertsHandler(config=WebSocketConfig(endpoint_name="budget-alerts"))

        message = MessageEnvelope(
            type="unknown_type",
            payload={},
            id="msg-4",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert isinstance(response, MessageEnvelope)
        assert response.type == "error"
