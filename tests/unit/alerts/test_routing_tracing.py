"""
Tests for OpenTelemetry tracing in alert routing.

Verifies that:
- Route operations create spans
- Async routing creates spans with subscription info
- Escalation checks create spans
- Errors are recorded in spans

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import gc
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@contextmanager
def mock_tracer(module_path: str):
    """Context manager to mock tracer.start_as_current_span for a module."""
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)
    mock_span.set_attribute = MagicMock()
    mock_span.record_exception = MagicMock()

    mock_tracer_obj = MagicMock()
    mock_tracer_obj.start_as_current_span = MagicMock(return_value=mock_span)

    with patch(f"{module_path}.tracer", mock_tracer_obj):
        yield mock_tracer_obj, mock_span


@pytest.mark.xdist_group(name="test_routing_tracing")
class TestRouterTracing:
    """Tests for tracing in AlertRouter."""

    @pytest.fixture(autouse=True)
    def _isolate_otel(self):
        """Reset circuit breakers and isolate OTEL state for xdist safety."""
        from mcp_server_langgraph.resilience.circuit_breaker import reset_all_circuit_breakers

        reset_all_circuit_breakers()
        return

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_route_creates_span(self) -> None:
        """
        GIVEN an AlertRouter with tracing enabled
        WHEN routing an alert
        THEN should create a span with routing attributes.
        """
        from mcp_server_langgraph.alerts.routing import Alert, AlertRouter

        with mock_tracer("mcp_server_langgraph.alerts.routing") as (mock_tracer_obj, mock_span):
            router = AlertRouter(default_tenant="default")

            alert = Alert(
                alert_id="alert-001",
                name="HighCPU",
                severity="critical",
                labels={"tenant": "acme-corp"},
                message="CPU usage high",
            )

            router.route(alert)

            # Verify span was created
            mock_tracer_obj.start_as_current_span.assert_called()
            call_args = mock_tracer_obj.start_as_current_span.call_args

            # Verify span name
            assert "route" in call_args[0][0].lower()

            # Verify span attributes
            attrs = call_args[1]["attributes"]
            assert attrs["routing.alert_id"] == "alert-001"
            assert attrs["routing.tenant_id"] == "acme-corp"

    @pytest.mark.asyncio
    async def test_route_async_creates_span(self) -> None:
        """
        GIVEN an AlertRouter with tracing and subscription store
        WHEN routing asynchronously
        THEN should create a span with subscription info.
        """
        from mcp_server_langgraph.alerts.routing import (
            Alert,
            AlertRouter,
            NotificationPreference,
            Subscription,
        )

        mock_store = AsyncMock(return_value=None)
        mock_store.get_subscriptions = AsyncMock(
            side_effect=lambda *a, **kw: [
                Subscription(
                    user_id="user-001",
                    tenant_id="acme-corp",
                    alert_types=["*"],
                    preference=NotificationPreference(channels=["email"]),
                ),
            ]
        )

        with mock_tracer("mcp_server_langgraph.alerts.routing") as (mock_tracer_obj, mock_span):
            router = AlertRouter(
                default_tenant="default",
                subscription_store=mock_store,
            )

            alert = Alert(
                alert_id="alert-002",
                name="HighCPU",
                severity="critical",
                labels={"tenant": "acme-corp"},
                message="CPU usage high",
            )

            await router.route_async(alert)

            # Verify span was created (route is called internally)
            mock_tracer_obj.start_as_current_span.assert_called()

            # Verify span attributes were set for subscriptions
            mock_span.set_attribute.assert_any_call("routing.subscribed_users", 1)

    def test_check_escalation_creates_span(self) -> None:
        """
        GIVEN an AlertRouter with escalation policies
        WHEN checking escalation
        THEN should create a span with escalation attributes.
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

        with mock_tracer("mcp_server_langgraph.alerts.routing") as (mock_tracer_obj, mock_span):
            router = AlertRouter(
                default_tenant="default",
                escalation_policies=[policy],
            )

            alert = Alert(
                alert_id="alert-003",
                name="HighCPU",
                severity="critical",
                labels={"tenant": "acme-corp"},
                message="CPU usage high",
                started_at=datetime.now(UTC) - timedelta(minutes=20),
            )

            router.check_escalation(alert)

            # Verify span was created
            mock_tracer_obj.start_as_current_span.assert_called()
            call_args = mock_tracer_obj.start_as_current_span.call_args

            # Verify span name contains escalation
            assert "escalation" in call_args[0][0].lower()

            # Verify span attributes
            attrs = call_args[1]["attributes"]
            assert attrs["escalation.alert_id"] == "alert-003"

    def test_route_filtered_records_in_span(self) -> None:
        """
        GIVEN a routing rule that filters alerts
        WHEN routing a filtered alert
        THEN should record filter reason in span.
        """
        from mcp_server_langgraph.alerts.routing import Alert, AlertRouter, RoutingRule

        rule = RoutingRule(
            tenant_id="acme-corp",
            severity_filter=["critical"],
        )

        with mock_tracer("mcp_server_langgraph.alerts.routing") as (mock_tracer_obj, mock_span):
            router = AlertRouter(default_tenant="default", rules=[rule])

            alert = Alert(
                alert_id="alert-004",
                name="HighCPU",
                severity="warning",  # Will be filtered
                labels={"tenant": "acme-corp"},
                message="CPU usage warning",
            )

            router.route(alert)

            # Verify filtered attribute was set
            mock_span.set_attribute.assert_any_call("routing.filtered", True)


@pytest.mark.xdist_group(name="test_routing_tracing")
class TestRoutingTracingErrorHandling:
    """Tests for error handling in routing tracing."""

    @pytest.fixture(autouse=True)
    def _isolate_otel(self):
        """Reset circuit breakers and isolate OTEL state for xdist safety."""
        from mcp_server_langgraph.resilience.circuit_breaker import reset_all_circuit_breakers

        reset_all_circuit_breakers()
        return

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_subscription_store_error_recorded_in_span(self) -> None:
        """
        GIVEN a subscription store that raises an error
        WHEN routing asynchronously
        THEN should record exception in span but still return result.
        """
        from mcp_server_langgraph.alerts.routing import Alert, AlertRouter

        mock_store = AsyncMock(return_value=None)
        mock_store.get_subscriptions.side_effect = RuntimeError("Store unavailable")

        with mock_tracer("mcp_server_langgraph.alerts.routing") as (mock_tracer_obj, mock_span):
            router = AlertRouter(
                default_tenant="default",
                subscription_store=mock_store,
            )

            alert = Alert(
                alert_id="alert-005",
                name="HighCPU",
                severity="critical",
                labels={"tenant": "acme-corp"},
                message="CPU usage high",
            )

            # Should not raise, but record error
            result = await router.route_async(alert)

            # Result should still be valid (graceful degradation)
            assert result.routed is True

            # Exception should be recorded
            mock_span.record_exception.assert_called()
