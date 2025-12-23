"""
Tests for Multi-Tenant Alert Routing.

Verifies that:
- Alerts are routed to correct tenant based on labels
- Routing rules filter alerts appropriately
- Subscriptions are matched correctly
- Escalation policies work as expected
- Broadcast alerts reach multiple tenants

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_routing")
class TestAlertRouterBasicRouting:
    """Tests for basic tenant routing."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_route_alert_uses_tenant_label(self) -> None:
        """
        GIVEN an alert with a tenant label
        WHEN routing the alert
        THEN should route to the tenant from the label.
        """
        from mcp_server_langgraph.alerts.routing import Alert, AlertRouter

        router = AlertRouter(default_tenant="default")

        alert = Alert(
            alert_id="alert-001",
            name="HighCPU",
            severity="critical",
            labels={"tenant": "acme-corp"},
            message="CPU usage high",
        )

        result = router.route(alert)

        assert result.routed is True
        assert result.tenant_id == "acme-corp"
        assert "acme-corp" in result.target_tenants

    def test_route_alert_uses_default_tenant_when_no_label(self) -> None:
        """
        GIVEN an alert without a tenant label
        WHEN routing the alert
        THEN should route to the default tenant.
        """
        from mcp_server_langgraph.alerts.routing import Alert, AlertRouter

        router = AlertRouter(default_tenant="default-tenant")

        alert = Alert(
            alert_id="alert-002",
            name="HighMemory",
            severity="warning",
            labels={"service": "api"},
            message="Memory usage high",
        )

        result = router.route(alert)

        assert result.routed is True
        assert result.tenant_id == "default-tenant"
        assert "default-tenant" in result.target_tenants

    def test_route_broadcast_alert_to_multiple_tenants(self) -> None:
        """
        GIVEN an alert with broadcast=true and tenants list
        WHEN routing the alert
        THEN should route to all specified tenants.
        """
        from mcp_server_langgraph.alerts.routing import Alert, AlertRouter

        router = AlertRouter(default_tenant="default")

        alert = Alert(
            alert_id="alert-003",
            name="SystemOutage",
            severity="critical",
            labels={
                "tenant": "primary",
                "broadcast": "true",
                "tenants": "tenant-a, tenant-b, tenant-c",
            },
            message="System-wide outage",
        )

        result = router.route(alert)

        assert result.routed is True
        assert result.tenant_id == "primary"
        assert len(result.target_tenants) == 3
        assert "tenant-a" in result.target_tenants
        assert "tenant-b" in result.target_tenants
        assert "tenant-c" in result.target_tenants


@pytest.mark.xdist_group(name="test_routing")
class TestAlertRouterFilterRules:
    """Tests for routing rule filtering."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_filter_by_severity(self) -> None:
        """
        GIVEN a routing rule that only allows critical severity
        WHEN routing a warning alert
        THEN should filter out the alert.
        """
        from mcp_server_langgraph.alerts.routing import Alert, AlertRouter, RoutingRule

        rule = RoutingRule(
            tenant_id="acme-corp",
            severity_filter=["critical"],  # Only critical allowed
        )

        router = AlertRouter(default_tenant="default", rules=[rule])

        alert = Alert(
            alert_id="alert-004",
            name="HighCPU",
            severity="warning",  # Not in allowed list
            labels={"tenant": "acme-corp"},
            message="CPU usage high",
        )

        result = router.route(alert)

        assert result.routed is False
        assert result.filtered is True
        assert result.target_tenants == []

    def test_allow_matching_severity(self) -> None:
        """
        GIVEN a routing rule that only allows critical severity
        WHEN routing a critical alert
        THEN should allow the alert.
        """
        from mcp_server_langgraph.alerts.routing import Alert, AlertRouter, RoutingRule

        rule = RoutingRule(
            tenant_id="acme-corp",
            severity_filter=["critical"],
        )

        router = AlertRouter(default_tenant="default", rules=[rule])

        alert = Alert(
            alert_id="alert-005",
            name="HighCPU",
            severity="critical",
            labels={"tenant": "acme-corp"},
            message="CPU usage critical",
        )

        result = router.route(alert)

        assert result.routed is True
        assert result.filtered is False

    def test_filter_by_label_matcher(self) -> None:
        """
        GIVEN a routing rule requiring specific label
        WHEN routing an alert without the label
        THEN should filter out the alert.
        """
        from mcp_server_langgraph.alerts.routing import Alert, AlertRouter, RoutingRule

        rule = RoutingRule(
            tenant_id="acme-corp",
            label_matchers={"environment": "production"},
        )

        router = AlertRouter(default_tenant="default", rules=[rule])

        alert = Alert(
            alert_id="alert-006",
            name="HighCPU",
            severity="critical",
            labels={"tenant": "acme-corp", "environment": "staging"},
            message="CPU usage high",
        )

        result = router.route(alert)

        assert result.routed is False
        assert result.filtered is True


@pytest.mark.xdist_group(name="test_routing")
class TestAlertRouterSubscriptions:
    """Tests for subscription-based routing."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_route_async_includes_subscribed_users(self) -> None:
        """
        GIVEN an alert and users subscribed to its type
        WHEN routing asynchronously
        THEN should include subscribed user IDs.
        """
        from mcp_server_langgraph.alerts.routing import (
            Alert,
            AlertRouter,
            NotificationPreference,
            Subscription,
        )

        # Mock subscription store
        mock_store = AsyncMock()
        mock_store.get_subscriptions.return_value = [
            Subscription(
                user_id="user-001",
                tenant_id="acme-corp",
                alert_types=["HighCPU", "HighMemory"],
                preference=NotificationPreference(channels=["email", "push"]),
            ),
            Subscription(
                user_id="user-002",
                tenant_id="acme-corp",
                alert_types=["*"],  # Wildcard - all types
                preference=NotificationPreference(channels=["slack"]),
            ),
        ]

        router = AlertRouter(
            default_tenant="default",
            subscription_store=mock_store,
        )

        alert = Alert(
            alert_id="alert-007",
            name="HighCPU",
            severity="critical",
            labels={"tenant": "acme-corp"},
            message="CPU usage high",
        )

        result = await router.route_async(alert)

        assert result.routed is True
        assert "user-001" in result.subscribed_users
        assert "user-002" in result.subscribed_users
        assert result.notification_channels["user-001"] == ["email", "push"]
        assert result.notification_channels["user-002"] == ["slack"]

    @pytest.mark.asyncio
    async def test_route_async_filters_by_alert_type(self) -> None:
        """
        GIVEN users subscribed to specific alert types
        WHEN routing an alert not in their subscriptions
        THEN should not include those users.
        """
        from mcp_server_langgraph.alerts.routing import (
            Alert,
            AlertRouter,
            NotificationPreference,
            Subscription,
        )

        mock_store = AsyncMock()
        mock_store.get_subscriptions.return_value = [
            Subscription(
                user_id="user-001",
                tenant_id="acme-corp",
                alert_types=["HighMemory"],  # Not subscribed to HighCPU
                preference=NotificationPreference(channels=["email"]),
            ),
        ]

        router = AlertRouter(
            default_tenant="default",
            subscription_store=mock_store,
        )

        alert = Alert(
            alert_id="alert-008",
            name="HighCPU",
            severity="critical",
            labels={"tenant": "acme-corp"},
            message="CPU usage high",
        )

        result = await router.route_async(alert)

        assert result.routed is True
        assert "user-001" not in result.subscribed_users


@pytest.mark.xdist_group(name="test_routing")
class TestAlertRouterEscalation:
    """Tests for escalation policy."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_escalation_after_threshold(self) -> None:
        """
        GIVEN an alert older than escalation threshold
        WHEN checking escalation
        THEN should indicate escalation is needed.
        """
        from mcp_server_langgraph.alerts.routing import (
            Alert,
            AlertRouter,
            EscalationPolicy,
        )

        policy = EscalationPolicy(
            tenant_id="acme-corp",
            escalation_after_minutes=15,
            escalate_to=["oncall-team", "manager"],
        )

        router = AlertRouter(
            default_tenant="default",
            escalation_policies=[policy],
        )

        # Alert started 20 minutes ago
        alert = Alert(
            alert_id="alert-009",
            name="HighCPU",
            severity="critical",
            labels={"tenant": "acme-corp"},
            message="CPU usage high",
            started_at=datetime.now(UTC) - timedelta(minutes=20),
            acknowledged=False,
        )

        result = router.check_escalation(alert)

        assert result.should_escalate is True
        assert "oncall-team" in result.escalate_to
        assert "manager" in result.escalate_to

    def test_no_escalation_before_threshold(self) -> None:
        """
        GIVEN an alert newer than escalation threshold
        WHEN checking escalation
        THEN should not escalate.
        """
        from mcp_server_langgraph.alerts.routing import (
            Alert,
            AlertRouter,
            EscalationPolicy,
        )

        policy = EscalationPolicy(
            tenant_id="acme-corp",
            escalation_after_minutes=15,
            escalate_to=["oncall-team"],
        )

        router = AlertRouter(
            default_tenant="default",
            escalation_policies=[policy],
        )

        # Alert started 5 minutes ago
        alert = Alert(
            alert_id="alert-010",
            name="HighCPU",
            severity="critical",
            labels={"tenant": "acme-corp"},
            message="CPU usage high",
            started_at=datetime.now(UTC) - timedelta(minutes=5),
            acknowledged=False,
        )

        result = router.check_escalation(alert)

        assert result.should_escalate is False

    def test_no_escalation_when_acknowledged(self) -> None:
        """
        GIVEN an acknowledged alert older than threshold
        WHEN checking escalation
        THEN should not escalate.
        """
        from mcp_server_langgraph.alerts.routing import (
            Alert,
            AlertRouter,
            EscalationPolicy,
        )

        policy = EscalationPolicy(
            tenant_id="acme-corp",
            escalation_after_minutes=15,
            escalate_to=["oncall-team"],
        )

        router = AlertRouter(
            default_tenant="default",
            escalation_policies=[policy],
        )

        # Alert acknowledged even though older than threshold
        alert = Alert(
            alert_id="alert-011",
            name="HighCPU",
            severity="critical",
            labels={"tenant": "acme-corp"},
            message="CPU usage high",
            started_at=datetime.now(UTC) - timedelta(minutes=20),
            acknowledged=True,
        )

        result = router.check_escalation(alert)

        assert result.should_escalate is False


@pytest.mark.xdist_group(name="test_routing")
class TestMultiTenantIsolation:
    """Tests for multi-tenant isolation in alert flow."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_tenant_isolation_different_tenants_dont_see_each_other(self) -> None:
        """
        GIVEN alerts from different tenants
        WHEN routing each alert
        THEN each tenant only sees their own alerts.
        """
        from mcp_server_langgraph.alerts.routing import Alert, AlertRouter

        router = AlertRouter(default_tenant="default")

        alert_tenant_a = Alert(
            alert_id="alert-a1",
            name="HighCPU",
            severity="critical",
            labels={"tenant": "tenant-a"},
            message="CPU high on tenant A",
        )

        alert_tenant_b = Alert(
            alert_id="alert-b1",
            name="HighCPU",
            severity="critical",
            labels={"tenant": "tenant-b"},
            message="CPU high on tenant B",
        )

        result_a = router.route(alert_tenant_a)
        result_b = router.route(alert_tenant_b)

        # Each result only includes its own tenant
        assert result_a.tenant_id == "tenant-a"
        assert result_a.target_tenants == ["tenant-a"]
        assert "tenant-b" not in result_a.target_tenants

        assert result_b.tenant_id == "tenant-b"
        assert result_b.target_tenants == ["tenant-b"]
        assert "tenant-a" not in result_b.target_tenants

    def test_tenant_specific_rules_dont_affect_other_tenants(self) -> None:
        """
        GIVEN tenant-specific routing rules
        WHEN routing alerts from different tenants
        THEN rules only apply to their configured tenant.
        """
        from mcp_server_langgraph.alerts.routing import Alert, AlertRouter, RoutingRule

        # Rule that filters warning for tenant-a only
        rule = RoutingRule(
            tenant_id="tenant-a",
            severity_filter=["critical"],  # Only critical for tenant-a
        )

        router = AlertRouter(default_tenant="default", rules=[rule])

        # Warning alert for tenant-a (should be filtered)
        alert_a = Alert(
            alert_id="alert-a2",
            name="HighCPU",
            severity="warning",
            labels={"tenant": "tenant-a"},
            message="CPU warning on tenant A",
        )

        # Warning alert for tenant-b (no rule, should pass)
        alert_b = Alert(
            alert_id="alert-b2",
            name="HighCPU",
            severity="warning",
            labels={"tenant": "tenant-b"},
            message="CPU warning on tenant B",
        )

        result_a = router.route(alert_a)
        result_b = router.route(alert_b)

        # Tenant A warning is filtered
        assert result_a.routed is False
        assert result_a.filtered is True

        # Tenant B warning passes (no rule for tenant-b)
        assert result_b.routed is True
        assert result_b.filtered is False
