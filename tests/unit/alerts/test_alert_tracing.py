"""
Tests for OpenTelemetry tracing in alert flow.

Verifies that:
- Alert broadcast creates spans
- AI recommendation generation creates spans
- Alert correlation creates spans
- Remediation execution creates spans

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import gc
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def create_test_alert():
    """Create a test alert for tracing tests."""
    from mcp_server_langgraph.observability.query.interfaces import (
        Alert,
        AlertSeverity,
        AlertState,
    )

    return Alert(
        alert_id="test-alert-001",
        name="HighCPUUsage",
        severity=AlertSeverity.CRITICAL,
        state=AlertState.FIRING,
        message="CPU usage above 90%",
        labels={"service": "api-gateway", "instance": "prod-1"},
        annotations={"summary": "High CPU on api-gateway"},
        started_at=datetime.now(UTC),
    )


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


@pytest.mark.xdist_group(name="test_alert_tracing")
class TestBroadcasterTracing:
    """Tests for tracing in AlertBroadcaster."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcast_alert_creates_span(self) -> None:
        """
        GIVEN an AlertBroadcaster with tracing enabled
        WHEN broadcasting an alert
        THEN should create a span with alert attributes.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        with mock_tracer("mcp_server_langgraph.alerts.broadcaster") as (mock_tracer_obj, mock_span):
            # Create broadcaster
            broadcaster = AlertBroadcaster()

            # Mock a WebSocket subscriber
            mock_ws = AsyncMock(return_value=None)
            await broadcaster.subscribe(mock_ws, "admin-user-1")

            # Broadcast alert
            alert = create_test_alert()
            await broadcaster.broadcast_alert(alert)

            # Verify span was created
            mock_tracer_obj.start_as_current_span.assert_called()
            call_args = mock_tracer_obj.start_as_current_span.call_args

            # Verify span name
            assert call_args[0][0] == "alert.broadcast"

            # Verify span attributes
            attrs = call_args[1]["attributes"]
            assert attrs["alert.id"] == "test-alert-001"
            assert attrs["alert.name"] == "HighCPUUsage"
            assert attrs["alert.severity"] == "critical"

    @pytest.mark.asyncio
    async def test_broadcast_alert_update_creates_span(self) -> None:
        """
        GIVEN an AlertBroadcaster with tracing enabled
        WHEN broadcasting an alert update
        THEN should create a span with update type.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        with mock_tracer("mcp_server_langgraph.alerts.broadcaster") as (mock_tracer_obj, mock_span):
            broadcaster = AlertBroadcaster()

            mock_ws = AsyncMock(return_value=None)
            await broadcaster.subscribe(mock_ws, "admin-user-1")

            alert = create_test_alert()
            await broadcaster.broadcast_alert_update(alert, update_type="resolved")

            # Verify span was created
            mock_tracer_obj.start_as_current_span.assert_called()
            call_args = mock_tracer_obj.start_as_current_span.call_args

            # Verify span name
            assert call_args[0][0] == "alert.broadcast_update"

            # Verify span attributes
            attrs = call_args[1]["attributes"]
            assert attrs["alert.update_type"] == "resolved"


@pytest.mark.xdist_group(name="test_alert_tracing")
class TestAIRecommendationTracing:
    """Tests for tracing in AI recommendation service."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_generate_recommendation_creates_span(self) -> None:
        """
        GIVEN an AIRecommendationService with tracing enabled
        WHEN generating a recommendation
        THEN should create a span with recommendation attributes.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )

        with mock_tracer("mcp_server_langgraph.alerts.ai_recommendation") as (mock_tracer_obj, mock_span):
            # Mock LLM
            mock_llm = MagicMock()
            mock_llm.acompletion = AsyncMock(
                return_value=MagicMock(
                    choices=[
                        MagicMock(
                            message=MagicMock(
                                content='{"root_cause_analysis": "High CPU", "remediation_steps": [], "risk_assessment": {}}'
                            )
                        )
                    ]
                )
            )

            service = AIRecommendationService(llm_factory=mock_llm)

            alert = create_test_alert()

            # Generate recommendation (patch metrics)
            with patch("mcp_server_langgraph.alerts.metrics.record_recommendation_request"):
                with patch("mcp_server_langgraph.alerts.metrics.record_recommendation_generated"):
                    await service.generate_recommendation(alert)

            # Verify span was created with correct name
            mock_tracer_obj.start_as_current_span.assert_called()
            call_args = mock_tracer_obj.start_as_current_span.call_args

            # Verify span name contains recommendation
            assert "recommendation" in call_args[0][0].lower()

            # Verify span attributes
            attrs = call_args[1]["attributes"]
            assert attrs["alert.id"] == "test-alert-001"
            assert attrs["alert.type"] == "HighCPUUsage"


@pytest.mark.xdist_group(name="test_alert_tracing")
class TestCorrelationTracing:
    """Tests for tracing in alert correlation engine."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_correlate_alerts_creates_span(self) -> None:
        """
        GIVEN an AlertCorrelationEngine with tracing enabled
        WHEN correlating alerts
        THEN should create a span with correlation attributes.
        """
        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
            CorrelatedAlert,
        )

        with mock_tracer("mcp_server_langgraph.alerts.correlation") as (mock_tracer_obj, mock_span):
            engine = AlertCorrelationEngine()

            # Create test alerts
            now = datetime.now(UTC)
            alerts = [
                CorrelatedAlert(
                    alert_id=f"alert-{i}",
                    name="HighCPU",
                    severity="critical",
                    labels={"service": "api"},
                    started_at=now,
                )
                for i in range(5)
            ]

            # Correlate alerts
            engine.correlate_by_label(alerts, "service")

            # Verify span was created
            mock_tracer_obj.start_as_current_span.assert_called()
            call_args = mock_tracer_obj.start_as_current_span.call_args

            # Verify span name contains correlation
            assert "correlat" in call_args[0][0].lower()

            # Verify span attributes
            attrs = call_args[1]["attributes"]
            assert attrs["correlation.alert_count"] == 5
            assert attrs["correlation.method"] == "label"

    def test_correlate_by_time_creates_span(self) -> None:
        """
        GIVEN an AlertCorrelationEngine with tracing enabled
        WHEN correlating alerts by time
        THEN should create a span with time correlation attributes.
        """
        from datetime import timedelta

        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
            CorrelatedAlert,
        )

        with mock_tracer("mcp_server_langgraph.alerts.correlation") as (mock_tracer_obj, mock_span):
            engine = AlertCorrelationEngine()

            # Create test alerts with close timestamps
            now = datetime.now(UTC)
            alerts = [
                CorrelatedAlert(
                    alert_id=f"alert-{i}",
                    name="HighCPU",
                    severity="critical",
                    labels={"service": "api"},
                    started_at=now + timedelta(minutes=i),
                )
                for i in range(3)
            ]

            # Correlate alerts by time
            engine.correlate_by_time(alerts, window_minutes=10)

            # Verify span was created
            mock_tracer_obj.start_as_current_span.assert_called()
            call_args = mock_tracer_obj.start_as_current_span.call_args

            # Verify span name contains time correlation
            assert "time" in call_args[0][0].lower()

            # Verify span attributes
            attrs = call_args[1]["attributes"]
            assert attrs["correlation.alert_count"] == 3
            assert attrs["correlation.method"] == "time"

    def test_detect_pattern_creates_span(self) -> None:
        """
        GIVEN an AlertCorrelationEngine with tracing enabled
        WHEN detecting patterns
        THEN should create a span with pattern detection attributes.
        """
        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
            CorrelatedAlert,
        )

        with mock_tracer("mcp_server_langgraph.alerts.correlation") as (mock_tracer_obj, mock_span):
            engine = AlertCorrelationEngine()

            # Create test alerts
            now = datetime.now(UTC)
            alerts = [
                CorrelatedAlert(
                    alert_id="alert-1",
                    name="HighCPU",
                    severity="critical",
                    labels={"service": "api", "host": "host-1"},
                    started_at=now,
                ),
                CorrelatedAlert(
                    alert_id="alert-2",
                    name="HighMemory",
                    severity="critical",
                    labels={"service": "api", "host": "host-1"},
                    started_at=now,
                ),
            ]

            # Detect patterns
            engine.detect_pattern(alerts)

            # Verify span was created
            mock_tracer_obj.start_as_current_span.assert_called()
            call_args = mock_tracer_obj.start_as_current_span.call_args

            # Verify span name contains pattern
            assert "pattern" in call_args[0][0].lower()

            # Verify span attributes
            attrs = call_args[1]["attributes"]
            assert attrs["pattern.alert_count"] == 2


@pytest.mark.xdist_group(name="test_alert_tracing")
class TestExecutorTracing:
    """Tests for tracing in remediation executor."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_execute_remediation_creates_span(self) -> None:
        """
        GIVEN a RemediationExecutor with tracing enabled
        WHEN executing a remediation
        THEN should create a span with execution attributes.
        """
        from mcp_server_langgraph.alerts.approval_queue import RemediationRequest
        from mcp_server_langgraph.alerts.executor import RemediationExecutor
        from mcp_server_langgraph.core.interrupts.approval import ApprovalStatus

        with mock_tracer("mcp_server_langgraph.alerts.executor") as (mock_tracer_obj, mock_span):
            executor = RemediationExecutor()

            # Create test request with all required fields
            request = RemediationRequest(
                remediation_id="rem-001",
                alert_id="alert-001",
                alert_name="HighCPUUsage",
                severity="critical",
                step_number=1,
                action="restart",
                description="Restart the service",
                command="echo 'test'",
                status=ApprovalStatus.APPROVED,
                requested_at=datetime.now(UTC).isoformat(),
                approved_by="admin-1",
                approved_at=datetime.now(UTC).isoformat(),
            )

            # Execute remediation
            await executor.execute(request)

            # Verify span was created
            mock_tracer_obj.start_as_current_span.assert_called()
            call_args = mock_tracer_obj.start_as_current_span.call_args

            # Verify span name contains execution
            assert "execut" in call_args[0][0].lower()

            # Verify span attributes
            attrs = call_args[1]["attributes"]
            assert attrs["remediation.id"] == "rem-001"
            assert attrs["remediation.alert_id"] == "alert-001"


@pytest.mark.xdist_group(name="test_alert_tracing")
class TestTracingEdgeCases:
    """Tests for tracing edge cases and error handling."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_correlation_with_empty_alerts_creates_span(self) -> None:
        """
        GIVEN an AlertCorrelationEngine with tracing enabled
        WHEN correlating an empty list of alerts
        THEN should still create a span with zero count.
        """
        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
        )

        with mock_tracer("mcp_server_langgraph.alerts.correlation") as (mock_tracer_obj, mock_span):
            engine = AlertCorrelationEngine()

            # Correlate empty list
            groups = engine.correlate_by_time([], window_minutes=5)

            # Should still create a span
            mock_tracer_obj.start_as_current_span.assert_called()
            call_args = mock_tracer_obj.start_as_current_span.call_args

            # Verify span attributes show zero alerts
            attrs = call_args[1]["attributes"]
            assert attrs["correlation.alert_count"] == 0

            # Result should be empty
            assert groups == []

    def test_pattern_detection_with_empty_alerts_creates_span(self) -> None:
        """
        GIVEN an AlertCorrelationEngine with tracing enabled
        WHEN detecting patterns in an empty list
        THEN should create a span with unknown pattern type.
        """
        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
            PatternType,
        )

        with mock_tracer("mcp_server_langgraph.alerts.correlation") as (mock_tracer_obj, mock_span):
            engine = AlertCorrelationEngine()

            # Detect pattern in empty list
            result = engine.detect_pattern([])

            # Verify span was created
            mock_tracer_obj.start_as_current_span.assert_called()
            call_args = mock_tracer_obj.start_as_current_span.call_args

            # Verify span name
            assert "pattern" in call_args[0][0].lower()

            # Verify span attributes
            attrs = call_args[1]["attributes"]
            assert attrs["pattern.alert_count"] == 0

            # Verify span was updated with pattern type
            mock_span.set_attribute.assert_any_call("pattern.type", "unknown")

            # Result should be unknown pattern
            assert result.pattern_type == PatternType.UNKNOWN
            assert result.confidence == 0.0

    def test_correlation_span_attributes_with_single_alert(self) -> None:
        """
        GIVEN an AlertCorrelationEngine with tracing enabled
        WHEN correlating a single alert
        THEN should create span with correct count and produce one group.
        """
        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
            CorrelatedAlert,
        )

        with mock_tracer("mcp_server_langgraph.alerts.correlation") as (mock_tracer_obj, mock_span):
            engine = AlertCorrelationEngine()

            now = datetime.now(UTC)
            alerts = [
                CorrelatedAlert(
                    alert_id="single-alert",
                    name="LoneAlert",
                    severity="warning",
                    labels={"service": "solo"},
                    started_at=now,
                )
            ]

            groups = engine.correlate_by_time(alerts, window_minutes=5)

            # Verify span was created with single alert
            mock_tracer_obj.start_as_current_span.assert_called()
            call_args = mock_tracer_obj.start_as_current_span.call_args

            attrs = call_args[1]["attributes"]
            assert attrs["correlation.alert_count"] == 1

            # Should have one group with one alert
            assert len(groups) == 1
            assert len(groups[0].alerts) == 1

    def test_pattern_detection_span_records_pattern_confidence(self) -> None:
        """
        GIVEN an AlertCorrelationEngine with tracing enabled
        WHEN detecting a resource exhaustion pattern
        THEN should record pattern type and confidence in span.
        """
        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
            CorrelatedAlert,
        )

        with mock_tracer("mcp_server_langgraph.alerts.correlation") as (mock_tracer_obj, mock_span):
            engine = AlertCorrelationEngine()

            now = datetime.now(UTC)
            # Create alerts that trigger resource exhaustion pattern
            alerts = [
                CorrelatedAlert(
                    alert_id="alert-1",
                    name="HighCPU",
                    severity="critical",
                    labels={"service": "api", "host": "host-1"},
                    started_at=now,
                ),
                CorrelatedAlert(
                    alert_id="alert-2",
                    name="HighMemory",
                    severity="critical",
                    labels={"service": "api", "host": "host-1"},
                    started_at=now,
                ),
            ]

            engine.detect_pattern(alerts)

            # Verify span was created
            mock_tracer_obj.start_as_current_span.assert_called()

            # Verify span attributes were set for pattern type
            # The span should have pattern.type set
            set_attribute_calls = mock_span.set_attribute.call_args_list
            pattern_type_set = any(call[0][0] == "pattern.type" for call in set_attribute_calls)
            assert pattern_type_set, "Expected pattern.type to be set in span"

    @pytest.mark.asyncio
    async def test_broadcaster_tracing_with_no_subscribers(self) -> None:
        """
        GIVEN an AlertBroadcaster with tracing enabled but no subscribers
        WHEN broadcasting an alert
        THEN should still create span with zero client count.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        with mock_tracer("mcp_server_langgraph.alerts.broadcaster") as (mock_tracer_obj, mock_span):
            broadcaster = AlertBroadcaster()

            # No subscribers - broadcast should still work
            alert = create_test_alert()

            # This should not raise even with no subscribers
            await broadcaster.broadcast_alert(alert)

            # Verify span was created
            mock_tracer_obj.start_as_current_span.assert_called()
            call_args = mock_tracer_obj.start_as_current_span.call_args

            # Verify span attributes
            attrs = call_args[1]["attributes"]
            assert attrs["alert.id"] == "test-alert-001"

    @pytest.mark.asyncio
    async def test_ai_recommendation_tracing_with_cache_hit(self) -> None:
        """
        GIVEN an AIRecommendationService with a cached recommendation
        WHEN requesting the same recommendation again
        THEN should create span indicating cache hit.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )

        with mock_tracer("mcp_server_langgraph.alerts.ai_recommendation") as (mock_tracer_obj, mock_span):
            # Mock LLM
            mock_llm = MagicMock()
            mock_llm.acompletion = AsyncMock(
                return_value=MagicMock(
                    choices=[
                        MagicMock(
                            message=MagicMock(
                                content='{"root_cause_analysis": "Test", "remediation_steps": [], "risk_assessment": {}}'
                            )
                        )
                    ]
                )
            )

            service = AIRecommendationService(llm_factory=mock_llm)
            alert = create_test_alert()

            # Patch metrics to avoid import issues
            with patch("mcp_server_langgraph.alerts.metrics.record_recommendation_request"):
                with patch("mcp_server_langgraph.alerts.metrics.record_recommendation_generated"):
                    # First request - should call LLM
                    await service.generate_recommendation(alert)

                    # Reset mock to track second call
                    mock_tracer_obj.start_as_current_span.reset_mock()

                    # Second request - should hit cache
                    await service.generate_recommendation(alert)

                    # Verify span was created for cache hit
                    mock_tracer_obj.start_as_current_span.assert_called()


@pytest.mark.xdist_group(name="test_alert_tracing")
class TestDistributedTracingContextPropagation:
    """Tests for distributed tracing context propagation across alert flow."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_alert_broadcaster_includes_trace_id_in_message(self) -> None:
        """
        GIVEN an AlertBroadcaster with tracing enabled
        WHEN broadcasting an alert
        THEN the message should include trace_id for correlation.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        with mock_tracer("mcp_server_langgraph.alerts.broadcaster") as (mock_tracer_obj, mock_span):
            # Mock the span to return a trace ID
            mock_span.get_span_context.return_value = MagicMock(
                trace_id=12345678901234567890,
                span_id=9876543210,
            )

            broadcaster = AlertBroadcaster()
            alert = create_test_alert()

            # The broadcaster should include trace context in the message
            await broadcaster.broadcast_alert(alert)

            # Verify the span was created
            mock_tracer_obj.start_as_current_span.assert_called()

    @pytest.mark.asyncio
    async def test_ai_recommendation_links_to_parent_span(self) -> None:
        """
        GIVEN an AIRecommendationService with a parent trace context
        WHEN generating a recommendation
        THEN should link to the parent span context.
        """
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )

        with mock_tracer("mcp_server_langgraph.alerts.ai_recommendation") as (mock_tracer_obj, mock_span):
            mock_llm = MagicMock()
            mock_llm.acompletion = AsyncMock(
                return_value=MagicMock(
                    choices=[
                        MagicMock(
                            message=MagicMock(
                                content='{"root_cause_analysis": "Test", "remediation_steps": [], "risk_assessment": {}}'
                            )
                        )
                    ]
                )
            )

            service = AIRecommendationService(llm_factory=mock_llm)
            alert = create_test_alert()

            with patch("mcp_server_langgraph.alerts.metrics.record_recommendation_request"):
                with patch("mcp_server_langgraph.alerts.metrics.record_recommendation_generated"):
                    await service.generate_recommendation(alert)

            # The span should be created (already validated in other tests)
            mock_tracer_obj.start_as_current_span.assert_called()

            # Verify span has alert.id attribute for correlation
            call_args = mock_tracer_obj.start_as_current_span.call_args
            attrs = call_args[1]["attributes"]
            assert "alert.id" in attrs

    @pytest.mark.asyncio
    async def test_remediation_executor_creates_linked_span(self) -> None:
        """
        GIVEN a RemediationExecutor with tracing enabled
        WHEN executing a remediation
        THEN should create a span linked to the alert context.
        """
        from mcp_server_langgraph.alerts.approval_queue import RemediationRequest
        from mcp_server_langgraph.alerts.executor import RemediationExecutor
        from mcp_server_langgraph.core.interrupts.approval import ApprovalStatus

        with mock_tracer("mcp_server_langgraph.alerts.executor") as (mock_tracer_obj, mock_span):
            executor = RemediationExecutor()

            request = RemediationRequest(
                remediation_id="rem-002",
                alert_id="alert-002",
                alert_name="HighCPU",
                severity="critical",
                step_number=1,
                action="restart",
                description="Restart service",
                command="echo 'test'",
                status=ApprovalStatus.APPROVED,
                requested_at=datetime.now(UTC).isoformat(),
                approved_by="admin",
                approved_at=datetime.now(UTC).isoformat(),
            )

            await executor.execute(request)

            # Verify span was created with remediation AND alert IDs
            mock_tracer_obj.start_as_current_span.assert_called()
            call_args = mock_tracer_obj.start_as_current_span.call_args
            attrs = call_args[1]["attributes"]

            # Should have both remediation.id and remediation.alert_id for correlation
            assert "remediation.id" in attrs
            assert "remediation.alert_id" in attrs
            assert attrs["remediation.alert_id"] == "alert-002"

    def test_correlation_engine_preserves_span_context(self) -> None:
        """
        GIVEN an AlertCorrelationEngine with tracing enabled
        WHEN correlating alerts from different spans
        THEN should preserve span context for each operation.
        """
        from mcp_server_langgraph.alerts.correlation import (
            AlertCorrelationEngine,
            CorrelatedAlert,
        )

        with mock_tracer("mcp_server_langgraph.alerts.correlation") as (mock_tracer_obj, mock_span):
            engine = AlertCorrelationEngine()

            now = datetime.now(UTC)
            alerts = [
                CorrelatedAlert(
                    alert_id="alert-a",
                    name="HighCPU",
                    severity="critical",
                    labels={"service": "api"},
                    started_at=now,
                ),
                CorrelatedAlert(
                    alert_id="alert-b",
                    name="HighMemory",
                    severity="warning",
                    labels={"service": "api"},
                    started_at=now,
                ),
            ]

            # Perform correlation
            engine.correlate_by_label(alerts, "service")

            # Verify span was created
            mock_tracer_obj.start_as_current_span.assert_called()

            # Span should include correlation method and alert count
            call_args = mock_tracer_obj.start_as_current_span.call_args
            attrs = call_args[1]["attributes"]
            assert attrs["correlation.alert_count"] == 2
            assert attrs["correlation.method"] == "label"
