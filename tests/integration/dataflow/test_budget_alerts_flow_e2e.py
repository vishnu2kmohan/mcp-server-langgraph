"""
E2E Integration Test: Budget Alerts Data Flow

Tests the complete budget alerts data flow:
    Cost Recording → BudgetChecker.check() → BudgetAlertBroadcaster → WebSocket

This test verifies that budget alerts are properly triggered and broadcast
when budget thresholds are exceeded.

Following memory safety patterns for pytest-xdist (see CLAUDE.md).
"""

import gc
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.budget,
    pytest.mark.asyncio,
    pytest.mark.xdist_group(name="budget_alerts_flow_e2e"),
]


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def unique_user_id() -> str:
    """Generate unique user ID for test isolation."""
    return f"user-{uuid4().hex[:8]}"


@pytest.fixture
def unique_org_id() -> str:
    """Generate unique organization ID for test isolation."""
    return f"org-{uuid4().hex[:8]}"


@pytest.fixture
def unique_project_id() -> str:
    """Generate unique project ID for test isolation."""
    return f"project-{uuid4().hex[:8]}"


@pytest.fixture
def create_test_budget():
    """Factory for creating test budget configurations."""
    from mcp_server_langgraph.monitoring.cost_budget import Budget

    def _create(
        entity_id: str,
        entity_type: str = "organization",
        monthly_limit_usd: Decimal = Decimal("100.00"),
        warning_threshold: float = 0.80,
        critical_threshold: float = 1.00,
    ) -> Budget:
        return Budget(
            entity_id=entity_id,
            entity_type=entity_type,
            monthly_limit_usd=monthly_limit_usd,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
        )

    return _create


@pytest.fixture
def mock_websocket_connection():
    """Create a mock WebSocket connection."""
    connection = MagicMock()
    connection.send_json = AsyncMock(return_value=None)
    connection.close = AsyncMock(return_value=None)
    return connection


# ============================================================================
# E2E Budget Alerts Data Flow Tests
# ============================================================================


class TestBudgetCheckerFlow:
    """
    E2E tests for budget checking logic.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_budget_check_ok_status(
        self,
        unique_org_id,
        create_test_budget,
    ):
        """
        E2E: Verify budget check returns 'ok' status when under threshold.

        GIVEN: A budget with $100 limit
        WHEN: Current spend is $50 (50%)
        THEN: Status is 'ok'
        """
        from mcp_server_langgraph.monitoring.cost_budget import BudgetChecker

        checker = BudgetChecker()
        budget = create_test_budget(
            entity_id=unique_org_id,
            monthly_limit_usd=Decimal("100.00"),
            warning_threshold=0.80,
        )

        status = await checker.check(budget, Decimal("50.00"))

        assert status.status == "ok"
        assert status.percent_used == 50.0
        assert status.remaining == Decimal("50.00")

    async def test_budget_check_warning_status(
        self,
        unique_org_id,
        create_test_budget,
    ):
        """
        E2E: Verify budget check returns 'warning' status at 80%.

        GIVEN: A budget with $100 limit and 80% warning threshold
        WHEN: Current spend is $85 (85%)
        THEN: Status is 'warning'
        """
        from mcp_server_langgraph.monitoring.cost_budget import BudgetChecker

        checker = BudgetChecker()
        budget = create_test_budget(
            entity_id=unique_org_id,
            monthly_limit_usd=Decimal("100.00"),
            warning_threshold=0.80,
        )

        status = await checker.check(budget, Decimal("85.00"))

        assert status.status == "warning"
        assert status.percent_used == 85.0
        assert status.remaining == Decimal("15.00")

    async def test_budget_check_critical_status(
        self,
        unique_org_id,
        create_test_budget,
    ):
        """
        E2E: Verify budget check returns 'critical' status at 100%.

        GIVEN: A budget with $100 limit and 100% critical threshold
        WHEN: Current spend is $100 (100%)
        THEN: Status is 'critical'
        """
        from mcp_server_langgraph.monitoring.cost_budget import BudgetChecker

        checker = BudgetChecker()
        budget = create_test_budget(
            entity_id=unique_org_id,
            monthly_limit_usd=Decimal("100.00"),
            critical_threshold=1.00,
        )

        status = await checker.check(budget, Decimal("100.00"))

        assert status.status == "critical"
        assert status.percent_used == 100.0
        assert status.remaining == Decimal("0.00")

    async def test_budget_check_exceeded_status(
        self,
        unique_org_id,
        create_test_budget,
    ):
        """
        E2E: Verify budget check returns 'exceeded' status over 100%.

        GIVEN: A budget with $100 limit
        WHEN: Current spend is $120 (120%)
        THEN: Status is 'exceeded'
        """
        from mcp_server_langgraph.monitoring.cost_budget import BudgetChecker

        checker = BudgetChecker()
        budget = create_test_budget(
            entity_id=unique_org_id,
            monthly_limit_usd=Decimal("100.00"),
        )

        status = await checker.check(budget, Decimal("120.00"))

        assert status.status == "exceeded"
        assert status.percent_used == 120.0
        assert status.remaining == Decimal("-20.00")


class TestBudgetAlertBroadcasterFlow:
    """
    E2E tests for budget alert broadcasting to WebSocket subscribers.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_broadcaster_sends_to_subscribers(
        self,
        unique_user_id,
        unique_org_id,
        create_test_budget,
        mock_websocket_connection,
    ):
        """
        E2E: Verify broadcaster sends alerts to subscribed WebSocket.

        GIVEN: A subscriber registered with the broadcaster
        WHEN: A budget status is broadcast
        THEN: The subscriber receives the alert message
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            BudgetAlertBroadcaster,
            BudgetChecker,
        )

        broadcaster = BudgetAlertBroadcaster()
        checker = BudgetChecker()

        # Subscribe the connection
        await broadcaster.subscribe(
            connection=mock_websocket_connection,
            user_id=unique_user_id,
        )

        assert broadcaster.subscriber_count == 1

        # Create a warning budget status
        budget = create_test_budget(
            entity_id=unique_org_id,
            monthly_limit_usd=Decimal("100.00"),
        )
        status = await checker.check(budget, Decimal("85.00"))

        # Broadcast the status
        await broadcaster.broadcast_budget_status(status)

        # Verify message was sent
        mock_websocket_connection.send_json.assert_called_once()
        call_args = mock_websocket_connection.send_json.call_args[0][0]

        assert call_args["type"] == "budget_alert"
        assert call_args["payload"]["entity_id"] == unique_org_id
        assert call_args["payload"]["status"] == "warning"

    async def test_broadcaster_filters_by_entity(
        self,
        unique_user_id,
        unique_org_id,
        create_test_budget,
        mock_websocket_connection,
    ):
        """
        E2E: Verify broadcaster filters alerts by entity.

        GIVEN: A subscriber filtering for specific entity
        WHEN: Alerts for other entities are broadcast
        THEN: The subscriber does not receive those alerts
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            BudgetAlertBroadcaster,
            BudgetChecker,
        )

        broadcaster = BudgetAlertBroadcaster()
        checker = BudgetChecker()

        # Subscribe with filter for our org only
        await broadcaster.subscribe(
            connection=mock_websocket_connection,
            user_id=unique_user_id,
            entity_filters=[unique_org_id],
        )

        # Create budget status for different org
        other_budget = create_test_budget(
            entity_id="other-org-123",
            monthly_limit_usd=Decimal("100.00"),
        )
        other_status = await checker.check(other_budget, Decimal("90.00"))

        # Broadcast - should be filtered
        await broadcaster.broadcast_budget_status(other_status)

        # Verify message was NOT sent (filtered out)
        mock_websocket_connection.send_json.assert_not_called()

    async def test_broadcaster_receives_matching_entity(
        self,
        unique_user_id,
        unique_org_id,
        create_test_budget,
        mock_websocket_connection,
    ):
        """
        E2E: Verify subscriber receives alerts for filtered entity.

        GIVEN: A subscriber filtering for specific entity
        WHEN: Alert for that entity is broadcast
        THEN: The subscriber receives the alert
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            BudgetAlertBroadcaster,
            BudgetChecker,
        )

        broadcaster = BudgetAlertBroadcaster()
        checker = BudgetChecker()

        # Subscribe with filter for our org
        await broadcaster.subscribe(
            connection=mock_websocket_connection,
            user_id=unique_user_id,
            entity_filters=[unique_org_id],
        )

        # Create budget status for our org
        budget = create_test_budget(
            entity_id=unique_org_id,
            monthly_limit_usd=Decimal("100.00"),
        )
        status = await checker.check(budget, Decimal("105.00"))

        # Broadcast
        await broadcaster.broadcast_budget_status(status)

        # Verify message WAS sent
        mock_websocket_connection.send_json.assert_called_once()
        call_args = mock_websocket_connection.send_json.call_args[0][0]
        assert call_args["payload"]["status"] == "exceeded"

    async def test_broadcaster_unsubscribe(
        self,
        unique_user_id,
        unique_org_id,
        create_test_budget,
        mock_websocket_connection,
    ):
        """
        E2E: Verify unsubscribe removes subscriber.

        GIVEN: A subscribed WebSocket connection
        WHEN: The connection is unsubscribed
        THEN: The subscriber count decreases
        """
        from mcp_server_langgraph.monitoring.cost_budget import BudgetAlertBroadcaster

        broadcaster = BudgetAlertBroadcaster()

        # Subscribe
        await broadcaster.subscribe(
            connection=mock_websocket_connection,
            user_id=unique_user_id,
        )
        assert broadcaster.subscriber_count == 1

        # Unsubscribe
        await broadcaster.unsubscribe(mock_websocket_connection)
        assert broadcaster.subscriber_count == 0


class TestBudgetCheckAllFlow:
    """
    E2E tests for checking multiple budgets.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_check_all_budgets(
        self,
        create_test_budget,
    ):
        """
        E2E: Verify check_all processes multiple budgets.

        GIVEN: Multiple budgets for different entities
        WHEN: check_all is called with spend data
        THEN: All budgets are checked and status returned
        """
        from mcp_server_langgraph.monitoring.cost_budget import BudgetChecker

        checker = BudgetChecker()

        # Create multiple budgets
        budgets = [
            create_test_budget(
                entity_id="org-1",
                monthly_limit_usd=Decimal("100.00"),
            ),
            create_test_budget(
                entity_id="org-2",
                monthly_limit_usd=Decimal("200.00"),
            ),
            create_test_budget(
                entity_id="org-3",
                monthly_limit_usd=Decimal("50.00"),
            ),
        ]

        # Spend data
        spend_by_entity = {
            "org-1": Decimal("50.00"),  # 50% - ok
            "org-2": Decimal("180.00"),  # 90% - warning
            "org-3": Decimal("60.00"),  # 120% - exceeded
        }

        # Check all
        statuses = await checker.check_all(budgets, spend_by_entity)

        assert len(statuses) == 3
        assert statuses[0].status == "ok"
        assert statuses[1].status == "warning"
        assert statuses[2].status == "exceeded"


class TestBudgetMessageFormat:
    """
    E2E tests for budget alert message format.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_budget_status_to_message(
        self,
        unique_org_id,
        create_test_budget,
    ):
        """
        E2E: Verify budget status is converted to correct message format.

        GIVEN: A budget status
        WHEN: Converting to WebSocket message
        THEN: The message has correct format and fields
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            BudgetChecker,
            budget_status_to_message,
        )

        checker = BudgetChecker()
        budget = create_test_budget(
            entity_id=unique_org_id,
            entity_type="organization",
            monthly_limit_usd=Decimal("100.00"),
        )

        status = await checker.check(budget, Decimal("85.00"))
        message = budget_status_to_message(status)

        assert message["type"] == "budget_alert"
        assert "payload" in message

        payload = message["payload"]
        assert payload["entity_type"] == "organization"
        assert payload["entity_id"] == unique_org_id
        assert payload["status"] == "warning"
        assert payload["percent_used"] == 85.0
        assert payload["current_spend"] == "85.00"
        assert payload["remaining"] == "15.00"
        assert payload["monthly_limit_usd"] == "100.00"
        assert "message" in payload
