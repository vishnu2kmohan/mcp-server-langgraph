"""
Budget Alert Broadcaster Unit Tests

TDD tests for real-time budget alerts via WebSocket.
Tests written FIRST (RED phase).

The BudgetAlertBroadcaster should:
1. Subscribe/unsubscribe WebSocket connections per user
2. Broadcast budget status changes to subscribed users
3. Support entity-based filtering (org, project, team, user)
4. Integrate with BudgetChecker for status determination
5. Send push notifications for critical budget alerts
"""

import gc
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.monitoring]


@pytest.mark.xdist_group(name="test_budget_broadcaster_core")
class TestBudgetAlertBroadcasterCore:
    """Core tests for BudgetAlertBroadcaster."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_broadcaster_import_when_module_loaded_is_available(self) -> None:
        """
        GIVEN the cost budget module
        WHEN importing BudgetAlertBroadcaster
        THEN it should be available
        """
        from mcp_server_langgraph.monitoring.cost_budget import BudgetAlertBroadcaster

        assert BudgetAlertBroadcaster is not None

    def test_broadcaster_initializes_empty(self) -> None:
        """
        GIVEN a new BudgetAlertBroadcaster
        WHEN created
        THEN it should have zero subscribers
        """
        from mcp_server_langgraph.monitoring.cost_budget import BudgetAlertBroadcaster

        broadcaster = BudgetAlertBroadcaster()
        assert broadcaster.subscriber_count == 0


@pytest.mark.xdist_group(name="test_budget_broadcaster_subscribe")
class TestBudgetAlertBroadcasterSubscription:
    """Tests for subscription management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_subscribe_adds_connection(self) -> None:
        """
        GIVEN a BudgetAlertBroadcaster
        WHEN a WebSocket connection subscribes
        THEN subscriber count should increase
        """
        from mcp_server_langgraph.monitoring.cost_budget import BudgetAlertBroadcaster

        broadcaster = BudgetAlertBroadcaster()

        # Mock WebSocket connection
        mock_connection = MagicMock()
        mock_connection.send_json = AsyncMock()  # noqa: async-mock-config

        await broadcaster.subscribe(
            connection=mock_connection,
            user_id="user:alice",
        )

        assert broadcaster.subscriber_count == 1

    @pytest.mark.asyncio
    async def test_subscribe_with_entity_filter(self) -> None:
        """
        GIVEN a BudgetAlertBroadcaster
        WHEN subscribing with entity filters
        THEN subscription should be recorded with filters
        """
        from mcp_server_langgraph.monitoring.cost_budget import BudgetAlertBroadcaster

        broadcaster = BudgetAlertBroadcaster()

        mock_connection = MagicMock()
        mock_connection.send_json = AsyncMock()  # noqa: async-mock-config

        await broadcaster.subscribe(
            connection=mock_connection,
            user_id="user:alice",
            entity_filters=["organization:acme", "project:backend"],
        )

        assert broadcaster.subscriber_count == 1
        # Verify subscriber has filters
        assert broadcaster.get_subscriber_filters("user:alice") == [
            "organization:acme",
            "project:backend",
        ]

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_connection(self) -> None:
        """
        GIVEN a BudgetAlertBroadcaster with a subscriber
        WHEN the connection unsubscribes
        THEN subscriber count should decrease
        """
        from mcp_server_langgraph.monitoring.cost_budget import BudgetAlertBroadcaster

        broadcaster = BudgetAlertBroadcaster()

        mock_connection = MagicMock()
        mock_connection.send_json = AsyncMock()  # noqa: async-mock-config

        await broadcaster.subscribe(
            connection=mock_connection,
            user_id="user:alice",
        )
        assert broadcaster.subscriber_count == 1

        await broadcaster.unsubscribe(mock_connection)
        assert broadcaster.subscriber_count == 0


@pytest.mark.xdist_group(name="test_budget_broadcaster_broadcast")
class TestBudgetAlertBroadcasterBroadcast:
    """Tests for broadcasting budget alerts."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcast_budget_status_sends_to_all(self) -> None:
        """
        GIVEN a BudgetAlertBroadcaster with subscribers
        WHEN broadcasting a budget status
        THEN all subscribers should receive the message
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            Budget,
            BudgetAlertBroadcaster,
            BudgetStatus,
        )

        broadcaster = BudgetAlertBroadcaster()

        # Add two subscribers
        mock_conn1 = MagicMock()
        mock_conn1.send_json = AsyncMock()  # noqa: async-mock-config
        mock_conn2 = MagicMock()
        mock_conn2.send_json = AsyncMock()  # noqa: async-mock-config

        await broadcaster.subscribe(mock_conn1, "user:alice")
        await broadcaster.subscribe(mock_conn2, "user:bob")

        # Create budget status
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

        await broadcaster.broadcast_budget_status(status)

        # Both subscribers should receive the message
        mock_conn1.send_json.assert_called_once()
        mock_conn2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_message_format(self) -> None:
        """
        GIVEN a BudgetAlertBroadcaster with a subscriber
        WHEN broadcasting a budget status
        THEN message should have correct format
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            Budget,
            BudgetAlertBroadcaster,
            BudgetStatus,
        )

        broadcaster = BudgetAlertBroadcaster()

        mock_connection = MagicMock()
        mock_connection.send_json = AsyncMock()  # noqa: async-mock-config

        await broadcaster.subscribe(mock_connection, "user:alice")

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

        await broadcaster.broadcast_budget_status(status)

        # Verify message format
        call_args = mock_connection.send_json.call_args[0][0]
        assert call_args["type"] == "budget_alert"
        assert "payload" in call_args
        assert call_args["payload"]["entity_id"] == "organization:acme"
        assert call_args["payload"]["status"] == "warning"
        assert call_args["payload"]["percent_used"] == 85.0

    @pytest.mark.asyncio
    async def test_broadcast_respects_entity_filter(self) -> None:
        """
        GIVEN subscribers with entity filters
        WHEN broadcasting a budget status
        THEN only filtered subscribers should receive it
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            Budget,
            BudgetAlertBroadcaster,
            BudgetStatus,
        )

        broadcaster = BudgetAlertBroadcaster()

        # Subscriber watching organization:acme
        mock_conn1 = MagicMock()
        mock_conn1.send_json = AsyncMock()  # noqa: async-mock-config
        await broadcaster.subscribe(
            mock_conn1,
            "user:alice",
            entity_filters=["organization:acme"],
        )

        # Subscriber watching organization:other
        mock_conn2 = MagicMock()
        mock_conn2.send_json = AsyncMock()  # noqa: async-mock-config
        await broadcaster.subscribe(
            mock_conn2,
            "user:bob",
            entity_filters=["organization:other"],
        )

        # Broadcast status for organization:acme
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

        await broadcaster.broadcast_budget_status(status)

        # Only alice should receive (watching organization:acme)
        mock_conn1.send_json.assert_called_once()
        mock_conn2.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_all_filter_receives_everything(self) -> None:
        """
        GIVEN a subscriber with no entity filter (watching all)
        WHEN broadcasting any budget status
        THEN they should receive it
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            Budget,
            BudgetAlertBroadcaster,
            BudgetStatus,
        )

        broadcaster = BudgetAlertBroadcaster()

        # Subscriber watching all (no filter)
        mock_connection = MagicMock()
        mock_connection.send_json = AsyncMock()  # noqa: async-mock-config
        await broadcaster.subscribe(mock_connection, "user:admin")

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

        await broadcaster.broadcast_budget_status(status)

        # Admin with no filter should receive
        mock_connection.send_json.assert_called_once()


@pytest.mark.xdist_group(name="test_budget_broadcaster_push")
class TestBudgetAlertBroadcasterPushNotification:
    """Tests for push notification integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_critical_status_sends_push_notification(self) -> None:
        """
        GIVEN a BudgetAlertBroadcaster with push sender configured
        WHEN broadcasting a critical budget status
        THEN it should send a push notification
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            Budget,
            BudgetAlertBroadcaster,
            BudgetStatus,
        )

        mock_push_sender = MagicMock()
        mock_push_sender.send_budget_alert = AsyncMock(return_value=1)

        broadcaster = BudgetAlertBroadcaster(push_sender=mock_push_sender)

        budget = Budget(
            entity_type="organization",
            entity_id="organization:acme",
            monthly_limit_usd=Decimal("1000.00"),
        )
        status = BudgetStatus(
            budget=budget,
            current_spend=Decimal("1000.00"),
            percent_used=100.0,
            status="critical",
            remaining=Decimal("0.00"),
        )

        await broadcaster.broadcast_budget_status(status)

        # Push notification should be sent for critical status
        mock_push_sender.send_budget_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_exceeded_status_sends_push_notification(self) -> None:
        """
        GIVEN a BudgetAlertBroadcaster with push sender configured
        WHEN broadcasting an exceeded budget status
        THEN it should send a push notification
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            Budget,
            BudgetAlertBroadcaster,
            BudgetStatus,
        )

        mock_push_sender = MagicMock()
        mock_push_sender.send_budget_alert = AsyncMock(return_value=1)

        broadcaster = BudgetAlertBroadcaster(push_sender=mock_push_sender)

        budget = Budget(
            entity_type="organization",
            entity_id="organization:acme",
            monthly_limit_usd=Decimal("1000.00"),
        )
        status = BudgetStatus(
            budget=budget,
            current_spend=Decimal("1200.00"),
            percent_used=120.0,
            status="exceeded",
            remaining=Decimal("-200.00"),
        )

        await broadcaster.broadcast_budget_status(status)

        mock_push_sender.send_budget_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_warning_status_no_push_notification(self) -> None:
        """
        GIVEN a BudgetAlertBroadcaster with push sender configured
        WHEN broadcasting a warning budget status
        THEN it should NOT send a push notification
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            Budget,
            BudgetAlertBroadcaster,
            BudgetStatus,
        )

        mock_push_sender = MagicMock()
        mock_push_sender.send_budget_alert = AsyncMock(return_value=1)

        broadcaster = BudgetAlertBroadcaster(push_sender=mock_push_sender)

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

        await broadcaster.broadcast_budget_status(status)

        # No push for warning - only WebSocket
        mock_push_sender.send_budget_alert.assert_not_called()


@pytest.mark.xdist_group(name="test_budget_broadcaster_graceful")
class TestBudgetAlertBroadcasterGraceful:
    """Tests for graceful error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_failed_connection_removed(self) -> None:
        """
        GIVEN a subscriber with a failed connection
        WHEN broadcasting
        THEN the failed connection should be removed
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            Budget,
            BudgetAlertBroadcaster,
            BudgetStatus,
        )

        broadcaster = BudgetAlertBroadcaster()

        # Good connection
        mock_conn1 = MagicMock()
        mock_conn1.send_json = AsyncMock()  # noqa: async-mock-config
        await broadcaster.subscribe(mock_conn1, "user:alice")

        # Bad connection (will raise exception)
        mock_conn2 = MagicMock()
        mock_conn2.send_json = AsyncMock(side_effect=Exception("Connection closed"))
        await broadcaster.subscribe(mock_conn2, "user:bob")

        assert broadcaster.subscriber_count == 2

        budget = Budget(
            entity_type="organization",
            entity_id="organization:acme",
            monthly_limit_usd=Decimal("1000.00"),
        )
        status = BudgetStatus(
            budget=budget,
            current_spend=Decimal("500.00"),
            percent_used=50.0,
            status="ok",
            remaining=Decimal("500.00"),
        )

        await broadcaster.broadcast_budget_status(status)

        # Failed connection should be removed
        assert broadcaster.subscriber_count == 1


@pytest.mark.xdist_group(name="test_budget_broadcaster_singleton")
class TestBudgetAlertBroadcasterSingleton:
    """Tests for singleton accessor."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_budget_alert_broadcaster_exists(self) -> None:
        """
        GIVEN the cost budget module
        WHEN importing get_budget_alert_broadcaster
        THEN it should be available
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            get_budget_alert_broadcaster,
        )

        assert get_budget_alert_broadcaster is not None

    def test_get_budget_alert_broadcaster_returns_singleton(self) -> None:
        """
        GIVEN get_budget_alert_broadcaster
        WHEN called multiple times
        THEN it should return the same instance
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            get_budget_alert_broadcaster,
        )

        broadcaster1 = get_budget_alert_broadcaster()
        broadcaster2 = get_budget_alert_broadcaster()

        assert broadcaster1 is broadcaster2
