"""
Budget Alerts WebSocket Handler Unit Tests

TDD tests for real-time budget alerts streaming via WebSocket.
Tests written FIRST (RED phase).

The BudgetAlertsHandler should:
1. Extend WebSocketBase with standardized infrastructure
2. Support subscribe/unsubscribe for budget alerts
3. Filter alerts by entity (org/project/team/user)
4. Integrate with BudgetAlertBroadcaster for push events
5. Provide current budget status on connect
"""

import gc
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.websocket]


@pytest.mark.xdist_group(name="test_budget_alerts_handler_core")
class TestBudgetAlertsHandlerCore:
    """Core tests for BudgetAlertsHandler."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_import_when_module_loaded_is_available(self) -> None:
        """
        GIVEN the websocket handlers module
        WHEN importing BudgetAlertsHandler
        THEN it should be available
        """
        from mcp_server_langgraph.websocket.handlers.budget_alerts import (
            BudgetAlertsHandler,
        )

        assert BudgetAlertsHandler is not None

    def test_handler_extends_websocket_base(self) -> None:
        """
        GIVEN BudgetAlertsHandler
        WHEN checking inheritance
        THEN it should extend WebSocketBase
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase
        from mcp_server_langgraph.websocket.handlers.budget_alerts import (
            BudgetAlertsHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(
            endpoint_name="budget-alerts",
            require_auth=True,
        )
        handler = BudgetAlertsHandler(config=config)

        assert isinstance(handler, WebSocketBase)


@pytest.mark.xdist_group(name="test_budget_alerts_handler_subscribe")
class TestBudgetAlertsHandlerSubscription:
    """Tests for subscription management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_subscribe_entities(self) -> None:
        """
        GIVEN a BudgetAlertsHandler
        WHEN handling subscribe_entities message
        THEN it should subscribe to the specified entities
        """
        from mcp_server_langgraph.websocket.handlers.budget_alerts import (
            BudgetAlertsHandler,
        )
        from mcp_server_langgraph.websocket.types import (
            MessageEnvelope,
            WebSocketConfig,
        )

        config = WebSocketConfig(
            endpoint_name="budget-alerts",
            require_auth=True,
        )
        handler = BudgetAlertsHandler(config=config)

        message = MessageEnvelope(
            type="subscribe_entities",
            payload={
                "entity_ids": ["organization:acme", "project:backend"],
            },
            id="msg-123",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "subscribed"
        assert response.id == "msg-123"
        assert "organization:acme" in handler.subscribed_entities
        assert "project:backend" in handler.subscribed_entities

    @pytest.mark.asyncio
    async def test_handle_subscribe_all(self) -> None:
        """
        GIVEN a BudgetAlertsHandler
        WHEN handling subscribe_all message
        THEN it should subscribe to all budget alerts
        """
        from mcp_server_langgraph.websocket.handlers.budget_alerts import (
            BudgetAlertsHandler,
        )
        from mcp_server_langgraph.websocket.types import (
            MessageEnvelope,
            WebSocketConfig,
        )

        config = WebSocketConfig(
            endpoint_name="budget-alerts",
            require_auth=True,
        )
        handler = BudgetAlertsHandler(config=config)

        message = MessageEnvelope(
            type="subscribe_all",
            payload={},
            id="msg-456",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "subscribed"
        assert handler.subscribe_all is True

    @pytest.mark.asyncio
    async def test_handle_unsubscribe(self) -> None:
        """
        GIVEN a BudgetAlertsHandler with subscriptions
        WHEN handling unsubscribe message
        THEN it should clear subscriptions
        """
        from mcp_server_langgraph.websocket.handlers.budget_alerts import (
            BudgetAlertsHandler,
        )
        from mcp_server_langgraph.websocket.types import (
            MessageEnvelope,
            WebSocketConfig,
        )

        config = WebSocketConfig(
            endpoint_name="budget-alerts",
            require_auth=True,
        )
        handler = BudgetAlertsHandler(config=config)

        # First subscribe
        handler.subscribed_entities.add("organization:acme")
        handler.subscribe_all = True

        # Then unsubscribe
        message = MessageEnvelope(
            type="unsubscribe",
            payload={},
            id="msg-789",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "unsubscribed"
        assert len(handler.subscribed_entities) == 0
        assert handler.subscribe_all is False


@pytest.mark.xdist_group(name="test_budget_alerts_handler_push")
class TestBudgetAlertsHandlerPush:
    """Tests for push event handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_push_budget_alert_to_subscriber(self) -> None:
        """
        GIVEN a subscribed BudgetAlertsHandler
        WHEN pushing a budget alert for a subscribed entity
        THEN it should send the alert
        """
        from mcp_server_langgraph.monitoring.cost_budget import Budget, BudgetStatus
        from mcp_server_langgraph.websocket.handlers.budget_alerts import (
            BudgetAlertsHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(
            endpoint_name="budget-alerts",
            require_auth=True,
        )
        handler = BudgetAlertsHandler(config=config)
        handler.subscribed_entities.add("organization:acme")

        # Mock websocket
        mock_websocket = MagicMock()
        mock_websocket.send_json = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_websocket

        budget = Budget(
            entity_type="organization",
            entity_id="organization:acme",
            monthly_limit_usd=Decimal("1000.00"),
        )
        status = BudgetStatus(
            budget=budget,
            current_spend=Decimal("850.00"),
            percent_used=85.0,
            status="warning",
            remaining=Decimal("150.00"),
        )

        await handler.push_budget_alert(status)

        mock_websocket.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_budget_alert_filtered_out(self) -> None:
        """
        GIVEN a subscribed BudgetAlertsHandler
        WHEN pushing a budget alert for a non-subscribed entity
        THEN it should NOT send the alert
        """
        from mcp_server_langgraph.monitoring.cost_budget import Budget, BudgetStatus
        from mcp_server_langgraph.websocket.handlers.budget_alerts import (
            BudgetAlertsHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(
            endpoint_name="budget-alerts",
            require_auth=True,
        )
        handler = BudgetAlertsHandler(config=config)
        handler.subscribed_entities.add("organization:acme")

        # Mock websocket
        mock_websocket = MagicMock()
        mock_websocket.send_json = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_websocket

        # Alert for different org
        budget = Budget(
            entity_type="organization",
            entity_id="organization:other",
            monthly_limit_usd=Decimal("1000.00"),
        )
        status = BudgetStatus(
            budget=budget,
            current_spend=Decimal("850.00"),
            percent_used=85.0,
            status="warning",
            remaining=Decimal("150.00"),
        )

        await handler.push_budget_alert(status)

        mock_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_budget_alert_subscribe_all(self) -> None:
        """
        GIVEN a handler with subscribe_all=True
        WHEN pushing any budget alert
        THEN it should send the alert
        """
        from mcp_server_langgraph.monitoring.cost_budget import Budget, BudgetStatus
        from mcp_server_langgraph.websocket.handlers.budget_alerts import (
            BudgetAlertsHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(
            endpoint_name="budget-alerts",
            require_auth=True,
        )
        handler = BudgetAlertsHandler(config=config)
        handler.subscribe_all = True

        # Mock websocket
        mock_websocket = MagicMock()
        mock_websocket.send_json = AsyncMock(return_value=None)  # noqa: async-mock-config
        handler._websocket = mock_websocket

        budget = Budget(
            entity_type="project",
            entity_id="project:random",
            monthly_limit_usd=Decimal("500.00"),
        )
        status = BudgetStatus(
            budget=budget,
            current_spend=Decimal("400.00"),
            percent_used=80.0,
            status="warning",
            remaining=Decimal("100.00"),
        )

        await handler.push_budget_alert(status)

        mock_websocket.send_json.assert_called_once()


@pytest.mark.xdist_group(name="test_budget_alerts_handler_lifecycle")
class TestBudgetAlertsHandlerLifecycle:
    """Tests for connection lifecycle."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_on_disconnect_clears_subscriptions(self) -> None:
        """
        GIVEN a handler with subscriptions
        WHEN on_disconnect is called
        THEN it should clear all subscriptions
        """
        from mcp_server_langgraph.websocket.handlers.budget_alerts import (
            BudgetAlertsHandler,
        )
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(
            endpoint_name="budget-alerts",
            require_auth=True,
        )
        handler = BudgetAlertsHandler(config=config)
        handler.subscribed_entities.add("organization:acme")
        handler.subscribe_all = True

        await handler.on_disconnect()

        assert len(handler.subscribed_entities) == 0
        assert handler.subscribe_all is False

    @pytest.mark.asyncio
    async def test_unknown_message_type_returns_error(self) -> None:
        """
        GIVEN a BudgetAlertsHandler
        WHEN handling an unknown message type
        THEN it should return an error response
        """
        from mcp_server_langgraph.websocket.handlers.budget_alerts import (
            BudgetAlertsHandler,
        )
        from mcp_server_langgraph.websocket.types import (
            MessageEnvelope,
            WebSocketConfig,
        )

        config = WebSocketConfig(
            endpoint_name="budget-alerts",
            require_auth=True,
        )
        handler = BudgetAlertsHandler(config=config)

        message = MessageEnvelope(
            type="unknown_type",
            payload={},
            id="msg-000",
        )

        response = await handler.handle_message(message)

        assert response is not None
        assert response.type == "error"
        assert "unknown_message_type" in response.payload.get("code", "")
