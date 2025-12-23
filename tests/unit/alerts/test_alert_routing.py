"""
Multi-Tenant Alert Routing Tests.

TDD tests for routing alerts to appropriate tenants based on labels,
subscriptions, and routing rules.

Features:
- Route alerts by tenant ID
- Filter by severity and labels
- Support subscription-based routing
- Handle alert escalation paths

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="alert_routing")
class TestAlertRouter:
    """Tests for multi-tenant alert routing."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_route_alert_by_tenant_label(self) -> None:
        """Test routing alert to correct tenant based on tenant label."""
        from mcp_server_langgraph.alerts.routing import (
            AlertRouter,
            Alert,
            RoutingResult,
        )

        router = AlertRouter()
        alert = Alert(
            alert_id="alert-001",
            name="HighCPU",
            severity="critical",
            labels={"tenant": "acme-corp", "service": "api"},
            message="CPU usage above 90%",
        )

        result = router.route(alert)

        assert isinstance(result, RoutingResult)
        assert result.tenant_id == "acme-corp"
        assert result.routed is True

    def test_route_alert_with_no_tenant_uses_default(self) -> None:
        """Test routing alert without tenant label to default tenant."""
        from mcp_server_langgraph.alerts.routing import (
            AlertRouter,
            Alert,
        )

        router = AlertRouter(default_tenant="system")
        alert = Alert(
            alert_id="alert-002",
            name="DiskFull",
            severity="warning",
            labels={"service": "storage"},
            message="Disk usage above 80%",
        )

        result = router.route(alert)

        assert result.tenant_id == "system"
        assert result.routed is True

    def test_route_alert_to_multiple_tenants(self) -> None:
        """Test routing alert to multiple tenants via broadcast label."""
        from mcp_server_langgraph.alerts.routing import (
            AlertRouter,
            Alert,
        )

        router = AlertRouter()
        alert = Alert(
            alert_id="alert-003",
            name="MaintenanceWindow",
            severity="info",
            labels={"broadcast": "true", "tenants": "acme-corp,globex,initech"},
            message="Scheduled maintenance in 1 hour",
        )

        result = router.route(alert)

        assert result.routed is True
        assert len(result.target_tenants) == 3
        assert "acme-corp" in result.target_tenants
        assert "globex" in result.target_tenants


@pytest.mark.unit
@pytest.mark.xdist_group(name="alert_routing")
class TestRoutingRules:
    """Tests for alert routing rules."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_apply_severity_filter_rule(self) -> None:
        """Test filtering alerts by severity."""
        from mcp_server_langgraph.alerts.routing import (
            AlertRouter,
            Alert,
            RoutingRule,
        )

        # Rule: Only route critical and warning to this tenant
        rule = RoutingRule(
            tenant_id="ops-team",
            severity_filter=["critical", "warning"],
        )

        router = AlertRouter(rules=[rule])

        # Critical alert should route
        critical_alert = Alert(
            alert_id="alert-004",
            name="ServiceDown",
            severity="critical",
            labels={"tenant": "ops-team"},
            message="Service unreachable",
        )
        result = router.route(critical_alert)
        assert result.routed is True

        # Info alert should NOT route to ops-team
        info_alert = Alert(
            alert_id="alert-005",
            name="DeploymentComplete",
            severity="info",
            labels={"tenant": "ops-team"},
            message="Deployment successful",
        )
        result = router.route(info_alert)
        assert result.filtered is True

    def test_apply_label_matcher_rule(self) -> None:
        """Test filtering alerts by label patterns."""
        from mcp_server_langgraph.alerts.routing import (
            AlertRouter,
            Alert,
            RoutingRule,
        )

        # Rule: Only route alerts from production environment
        rule = RoutingRule(
            tenant_id="sre-team",
            label_matchers={"environment": "production"},
        )

        router = AlertRouter(rules=[rule])

        # Production alert should route
        prod_alert = Alert(
            alert_id="alert-006",
            name="HighLatency",
            severity="warning",
            labels={"tenant": "sre-team", "environment": "production"},
            message="P99 latency above 500ms",
        )
        result = router.route(prod_alert)
        assert result.routed is True

        # Staging alert should be filtered
        staging_alert = Alert(
            alert_id="alert-007",
            name="HighLatency",
            severity="warning",
            labels={"tenant": "sre-team", "environment": "staging"},
            message="P99 latency above 500ms",
        )
        result = router.route(staging_alert)
        assert result.filtered is True


@pytest.mark.unit
@pytest.mark.xdist_group(name="alert_routing")
class TestSubscriptionRouting:
    """Tests for subscription-based alert routing."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_route_to_subscribed_users(self) -> None:
        """Test routing alerts to users subscribed to alert type."""
        from mcp_server_langgraph.alerts.routing import (
            AlertRouter,
            Alert,
            Subscription,
        )

        subscriptions = [
            Subscription(
                user_id="user-001",
                tenant_id="acme-corp",
                alert_types=["HighCPU", "HighMemory"],
            ),
            Subscription(
                user_id="user-002",
                tenant_id="acme-corp",
                alert_types=["HighCPU"],
            ),
        ]

        mock_store = AsyncMock()
        mock_store.get_subscriptions = AsyncMock(return_value=subscriptions)

        router = AlertRouter(subscription_store=mock_store)
        alert = Alert(
            alert_id="alert-008",
            name="HighCPU",
            severity="warning",
            labels={"tenant": "acme-corp"},
            message="CPU above 80%",
        )

        result = await router.route_async(alert)

        assert len(result.subscribed_users) == 2
        assert "user-001" in result.subscribed_users
        assert "user-002" in result.subscribed_users

    @pytest.mark.asyncio
    async def test_route_respects_user_preferences(self) -> None:
        """Test routing respects user notification preferences."""
        from mcp_server_langgraph.alerts.routing import (
            AlertRouter,
            Alert,
            Subscription,
            NotificationPreference,
        )

        subscriptions = [
            Subscription(
                user_id="user-003",
                tenant_id="acme-corp",
                alert_types=["*"],  # All alerts
                preference=NotificationPreference(
                    channels=["email", "push"],
                    quiet_hours_start=22,  # 10 PM
                    quiet_hours_end=7,  # 7 AM
                ),
            ),
        ]

        mock_store = AsyncMock()
        mock_store.get_subscriptions = AsyncMock(return_value=subscriptions)

        router = AlertRouter(subscription_store=mock_store)
        alert = Alert(
            alert_id="alert-009",
            name="HighMemory",
            severity="warning",
            labels={"tenant": "acme-corp"},
            message="Memory above 85%",
        )

        result = await router.route_async(alert)

        assert len(result.subscribed_users) == 1
        assert result.notification_channels == {"user-003": ["email", "push"]}


@pytest.mark.unit
@pytest.mark.xdist_group(name="alert_routing")
class TestEscalationRouting:
    """Tests for alert escalation routing."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_escalate_unacknowledged_alert(self) -> None:
        """Test escalation of unacknowledged critical alerts."""
        from mcp_server_langgraph.alerts.routing import (
            AlertRouter,
            Alert,
            EscalationPolicy,
        )

        policy = EscalationPolicy(
            tenant_id="acme-corp",
            escalation_after_minutes=15,
            escalate_to=["manager-001", "on-call-team"],
        )

        router = AlertRouter(escalation_policies=[policy])
        alert = Alert(
            alert_id="alert-010",
            name="ServiceDown",
            severity="critical",
            labels={"tenant": "acme-corp"},
            message="Critical service unreachable",
            started_at=datetime.now(UTC) - timedelta(minutes=20),
            acknowledged=False,
        )

        result = router.check_escalation(alert)

        assert result.should_escalate is True
        assert "manager-001" in result.escalate_to
        assert "on-call-team" in result.escalate_to

    def test_no_escalation_for_acknowledged_alert(self) -> None:
        """Test no escalation for acknowledged alerts."""
        from mcp_server_langgraph.alerts.routing import (
            AlertRouter,
            Alert,
            EscalationPolicy,
        )

        policy = EscalationPolicy(
            tenant_id="acme-corp",
            escalation_after_minutes=15,
            escalate_to=["manager-001"],
        )

        router = AlertRouter(escalation_policies=[policy])
        alert = Alert(
            alert_id="alert-011",
            name="ServiceDown",
            severity="critical",
            labels={"tenant": "acme-corp"},
            message="Service unreachable",
            started_at=datetime.now(UTC) - timedelta(minutes=20),
            acknowledged=True,
        )

        result = router.check_escalation(alert)

        assert result.should_escalate is False


@pytest.mark.unit
@pytest.mark.xdist_group(name="alert_routing")
class TestRoutingModels:
    """Tests for routing data models."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_alert_model(self) -> None:
        """Test Alert model creation."""
        from mcp_server_langgraph.alerts.routing import Alert

        alert = Alert(
            alert_id="alert-012",
            name="TestAlert",
            severity="warning",
            labels={"env": "test"},
            message="Test message",
        )

        assert alert.alert_id == "alert-012"
        assert alert.name == "TestAlert"
        assert alert.severity == "warning"
        assert alert.labels["env"] == "test"

    def test_routing_result_model(self) -> None:
        """Test RoutingResult model."""
        from mcp_server_langgraph.alerts.routing import RoutingResult

        result = RoutingResult(
            tenant_id="test-tenant",
            routed=True,
            target_tenants=["test-tenant"],
            subscribed_users=["user-001"],
        )

        assert result.tenant_id == "test-tenant"
        assert result.routed is True
        assert len(result.target_tenants) == 1

    def test_subscription_model(self) -> None:
        """Test Subscription model."""
        from mcp_server_langgraph.alerts.routing import Subscription

        sub = Subscription(
            user_id="user-001",
            tenant_id="acme-corp",
            alert_types=["HighCPU", "HighMemory"],
        )

        assert sub.user_id == "user-001"
        assert "HighCPU" in sub.alert_types

    def test_routing_rule_model(self) -> None:
        """Test RoutingRule model."""
        from mcp_server_langgraph.alerts.routing import RoutingRule

        rule = RoutingRule(
            tenant_id="ops-team",
            severity_filter=["critical"],
            label_matchers={"env": "prod"},
        )

        assert rule.tenant_id == "ops-team"
        assert "critical" in rule.severity_filter
        assert rule.label_matchers["env"] == "prod"

    def test_escalation_policy_model(self) -> None:
        """Test EscalationPolicy model."""
        from mcp_server_langgraph.alerts.routing import EscalationPolicy

        policy = EscalationPolicy(
            tenant_id="acme-corp",
            escalation_after_minutes=30,
            escalate_to=["manager", "on-call"],
        )

        assert policy.tenant_id == "acme-corp"
        assert policy.escalation_after_minutes == 30
        assert len(policy.escalate_to) == 2
