"""
Tests for audit metrics (Prometheus).

TDD RED phase: These tests define expected behavior for audit metrics.

The metrics system should:
- Track audit_events_total by category, event_type, outcome
- Track audit_events_latency_seconds
- Track audit_integrity_verified_total
- Track audit_integrity_failures_total
- Track audit_chain_length
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_metrics")
class TestAuditMetricsCounters:
    """Tests for audit event counters."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_event_counter_increments(self) -> None:
        """GIVEN audit event WHEN processed THEN counter increments."""
        from mcp_server_langgraph.audit.metrics import AuditMetrics
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

        metrics = AuditMetrics()

        event = UnifiedAuditEvent(
            category=AuditEventCategory.AUTHENTICATION,
            event_type=AuditEventType.LOGIN_SUCCESS,
            actor=AuditActor(actor_id="user:alice", actor_type="user"),
            resource_type="session",
            resource_id="sess-001",
            action="Login",
            outcome="success",
            context=AuditContext(request_id="req-1"),
        )

        metrics.record_event(event)

        # Verify counter was incremented
        count = metrics.get_event_count(
            category="authentication",
            event_type="login.success",
            outcome="success",
        )
        assert count >= 1

    def test_event_counter_labels(self) -> None:
        """GIVEN event with labels WHEN counted THEN labels are correct."""
        from mcp_server_langgraph.audit.metrics import AuditMetrics
        from mcp_server_langgraph.audit.models import (
            AuditActor,
            AuditContext,
            AuditEventCategory,
            AuditEventType,
            UnifiedAuditEvent,
        )

        metrics = AuditMetrics()

        # Record events with different labels
        for outcome in ["success", "failure"]:
            event = UnifiedAuditEvent(
                category=AuditEventCategory.DATA_ACCESS,
                event_type=AuditEventType.DATA_READ,
                actor=AuditActor(actor_id="user:test", actor_type="user"),
                resource_type="document",
                resource_id="doc-001",
                action="Read",
                outcome=outcome,
                context=AuditContext(request_id="req-1"),
            )
            metrics.record_event(event)

        success_count = metrics.get_event_count(
            category="data_access",
            event_type="data.read",
            outcome="success",
        )
        failure_count = metrics.get_event_count(
            category="data_access",
            event_type="data.read",
            outcome="failure",
        )

        assert success_count >= 1
        assert failure_count >= 1


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_metrics")
class TestAuditMetricsHistograms:
    """Tests for audit latency histograms."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_latency_histogram_records(self) -> None:
        """GIVEN event processing WHEN timed THEN latency recorded."""
        from mcp_server_langgraph.audit.metrics import AuditMetrics

        metrics = AuditMetrics()

        # Record a latency observation
        metrics.record_event_latency(
            category="authentication",
            latency_seconds=0.05,
        )

        # Verify histogram has observations
        observations = metrics.get_latency_observations("authentication")
        assert observations >= 1


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_metrics")
class TestAuditMetricsIntegrity:
    """Tests for integrity-related metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_integrity_verified_counter(self) -> None:
        """GIVEN integrity check WHEN passed THEN counter increments."""
        from mcp_server_langgraph.audit.metrics import AuditMetrics

        metrics = AuditMetrics()

        metrics.record_integrity_verification(success=True, events_verified=100)

        verified = metrics.get_integrity_verified_count()
        assert verified >= 1

    def test_integrity_failure_counter(self) -> None:
        """GIVEN integrity check WHEN failed THEN failure counter increments."""
        from mcp_server_langgraph.audit.metrics import AuditMetrics

        metrics = AuditMetrics()

        metrics.record_integrity_verification(success=False, events_verified=100)

        failures = metrics.get_integrity_failure_count()
        assert failures >= 1

    def test_chain_length_gauge(self) -> None:
        """GIVEN hash chain WHEN updated THEN gauge reflects length."""
        from mcp_server_langgraph.audit.metrics import AuditMetrics

        metrics = AuditMetrics()

        metrics.set_chain_length(1500)

        length = metrics.get_chain_length()
        assert length == 1500


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_metrics")
class TestAuditMetricsExport:
    """Tests for Prometheus metrics export."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_metrics_export_returns_prometheus_format(self) -> None:
        """GIVEN metrics WHEN exported THEN Prometheus format returned."""
        from mcp_server_langgraph.audit.metrics import AuditMetrics

        metrics = AuditMetrics()

        # Record some events
        metrics.record_integrity_verification(success=True, events_verified=50)

        # Get Prometheus format
        output = metrics.export_prometheus_format()

        assert "audit_" in output
        assert "# HELP" in output or "# TYPE" in output or output.strip() != ""

    def test_metrics_registry_contains_all_expected_metrics(self) -> None:
        """GIVEN metrics WHEN checking registry THEN all metrics registered."""
        from mcp_server_langgraph.audit.metrics import AuditMetrics

        metrics = AuditMetrics()

        registered = metrics.get_registered_metrics()

        # Check that expected metrics are registered
        expected_metrics = [
            "audit_events_total",
            "audit_events_latency_seconds",
            "audit_integrity_verified_total",
            "audit_integrity_failures_total",
            "audit_chain_length",
        ]

        for metric_name in expected_metrics:
            assert metric_name in registered
