"""
Tests for HITL (Human-in-the-Loop) metrics.

Tests verify OpenTelemetry metric recording for HITL operations:
- Request tracking (approval, clarification)
- Decision recording (approved, rejected, timeout)
- Response latency measurement
- Confidence distribution tracking
- Pending request gauges

TDD: RED phase - tests written FIRST before implementation.
"""

from __future__ import annotations

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.hitl, pytest.mark.multi_agent]


@pytest.mark.unit
class TestHITLMetricsRecording:
    """Test suite for HITL metrics recording functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_hitl_request_exists(self) -> None:
        """GIVEN the metrics module
        WHEN importing record_hitl_request
        THEN the function should exist.
        """
        from mcp_server_langgraph.agents.metrics import record_hitl_request

        assert callable(record_hitl_request)

    def test_record_hitl_request_with_approval_type(self) -> None:
        """GIVEN an HITL approval request
        WHEN recording the request
        THEN it should record without error.
        """
        from mcp_server_langgraph.agents.metrics import record_hitl_request

        # Should not raise
        record_hitl_request(
            request_type="approval",
            agent_name="Research Assistant",
            confidence=0.65,
            trigger_reason="low_confidence",
        )

    def test_record_hitl_request_with_clarification_type(self) -> None:
        """GIVEN an HITL clarification request
        WHEN recording the request
        THEN it should record without error.
        """
        from mcp_server_langgraph.agents.metrics import record_hitl_request

        record_hitl_request(
            request_type="clarification",
            agent_name="Data Analyst",
            confidence=0.8,
            trigger_reason="ambiguous_input",
        )

    def test_record_hitl_request_with_various_triggers(self) -> None:
        """GIVEN various trigger reasons
        WHEN recording HITL requests
        THEN all should be recorded successfully.
        """
        from mcp_server_langgraph.agents.metrics import record_hitl_request

        trigger_reasons = [
            "low_confidence",
            "destructive_action",
            "external_api",
            "high_cost",
            "policy_required",
        ]

        for reason in trigger_reasons:
            record_hitl_request(
                request_type="approval",
                agent_name="Test Agent",
                confidence=0.5,
                trigger_reason=reason,
            )


@pytest.mark.unit
class TestHITLDecisionMetrics:
    """Test suite for HITL decision recording."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_hitl_decision_exists(self) -> None:
        """GIVEN the metrics module
        WHEN importing record_hitl_decision
        THEN the function should exist.
        """
        from mcp_server_langgraph.agents.metrics import record_hitl_decision

        assert callable(record_hitl_decision)

    def test_record_hitl_decision_approved(self) -> None:
        """GIVEN an approved HITL decision
        WHEN recording the decision
        THEN it should record without error.
        """
        from mcp_server_langgraph.agents.metrics import record_hitl_decision

        record_hitl_decision(
            request_type="approval",
            agent_name="Research Assistant",
            decision="approved",
            latency_seconds=30.5,
        )

    def test_record_hitl_decision_rejected(self) -> None:
        """GIVEN a rejected HITL decision
        WHEN recording the decision
        THEN it should record without error.
        """
        from mcp_server_langgraph.agents.metrics import record_hitl_decision

        record_hitl_decision(
            request_type="approval",
            agent_name="Data Analyst",
            decision="rejected",
            latency_seconds=15.0,
        )

    def test_record_hitl_decision_timeout(self) -> None:
        """GIVEN a timed-out HITL decision
        WHEN recording the decision
        THEN it should record without error.
        """
        from mcp_server_langgraph.agents.metrics import record_hitl_decision

        record_hitl_decision(
            request_type="clarification",
            agent_name="Code Reviewer",
            decision="timeout",
            latency_seconds=3600.0,  # 1 hour timeout
        )

    def test_record_hitl_decision_with_fast_response(self) -> None:
        """GIVEN a very fast HITL decision (< 1 second)
        WHEN recording the decision
        THEN it should record without error.
        """
        from mcp_server_langgraph.agents.metrics import record_hitl_decision

        record_hitl_decision(
            request_type="approval",
            agent_name="Quick Agent",
            decision="approved",
            latency_seconds=0.5,
        )


@pytest.mark.unit
class TestHITLPendingMetrics:
    """Test suite for HITL pending request tracking."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_increment_hitl_pending_exists(self) -> None:
        """GIVEN the metrics module
        WHEN importing increment_hitl_pending
        THEN the function should exist.
        """
        from mcp_server_langgraph.agents.metrics import increment_hitl_pending

        assert callable(increment_hitl_pending)

    def test_decrement_hitl_pending_exists(self) -> None:
        """GIVEN the metrics module
        WHEN importing decrement_hitl_pending
        THEN the function should exist.
        """
        from mcp_server_langgraph.agents.metrics import decrement_hitl_pending

        assert callable(decrement_hitl_pending)

    def test_increment_hitl_pending_for_approval(self) -> None:
        """GIVEN an approval request type
        WHEN incrementing pending count
        THEN it should record without error.
        """
        from mcp_server_langgraph.agents.metrics import increment_hitl_pending

        increment_hitl_pending(request_type="approval")

    def test_decrement_hitl_pending_for_clarification(self) -> None:
        """GIVEN a clarification request type
        WHEN decrementing pending count
        THEN it should record without error.
        """
        from mcp_server_langgraph.agents.metrics import decrement_hitl_pending

        decrement_hitl_pending(request_type="clarification")


@pytest.mark.unit
class TestHITLMetricsCounters:
    """Test suite for HITL metric counter definitions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_hitl_request_counter_exists(self) -> None:
        """GIVEN the metrics module
        WHEN checking for HITL request counter
        THEN it should be defined.
        """
        from mcp_server_langgraph.agents.metrics import hitl_request_counter

        assert hitl_request_counter is not None

    def test_hitl_decision_counter_exists(self) -> None:
        """GIVEN the metrics module
        WHEN checking for HITL decision counter
        THEN it should be defined.
        """
        from mcp_server_langgraph.agents.metrics import hitl_decision_counter

        assert hitl_decision_counter is not None

    def test_hitl_response_latency_histogram_exists(self) -> None:
        """GIVEN the metrics module
        WHEN checking for HITL response latency histogram
        THEN it should be defined.
        """
        from mcp_server_langgraph.agents.metrics import hitl_response_latency_histogram

        assert hitl_response_latency_histogram is not None

    def test_hitl_confidence_histogram_exists(self) -> None:
        """GIVEN the metrics module
        WHEN checking for HITL confidence histogram
        THEN it should be defined.
        """
        from mcp_server_langgraph.agents.metrics import hitl_confidence_histogram

        assert hitl_confidence_histogram is not None

    def test_hitl_pending_gauge_exists(self) -> None:
        """GIVEN the metrics module
        WHEN checking for HITL pending gauge
        THEN it should be defined.
        """
        from mcp_server_langgraph.agents.metrics import hitl_pending_gauge

        assert hitl_pending_gauge is not None


@pytest.mark.unit
class TestHITLTracing:
    """Test suite for HITL trace span helpers."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_hitl_request_span_exists(self) -> None:
        """GIVEN the metrics module
        WHEN importing hitl_request_span
        THEN the function should exist.
        """
        from mcp_server_langgraph.agents.metrics import hitl_request_span

        assert callable(hitl_request_span)

    def test_hitl_request_span_context_manager(self) -> None:
        """GIVEN hitl_request_span
        WHEN used as context manager
        THEN it should yield a span object.
        """
        from mcp_server_langgraph.agents.metrics import hitl_request_span

        with hitl_request_span(
            request_type="approval",
            request_id="req-001",
            agent_name="Test Agent",
            confidence=0.65,
            trigger_reason="low_confidence",
        ) as span:
            assert span is not None
            # Span should have set_attributes method
            assert hasattr(span, "set_attributes")

    def test_add_hitl_decision_to_span_exists(self) -> None:
        """GIVEN the metrics module
        WHEN importing add_hitl_decision_to_span
        THEN the function should exist.
        """
        from mcp_server_langgraph.agents.metrics import add_hitl_decision_to_span

        assert callable(add_hitl_decision_to_span)

    def test_add_hitl_decision_to_span_approved(self) -> None:
        """GIVEN an active HITL span
        WHEN adding an approved decision
        THEN it should not raise.
        """
        from mcp_server_langgraph.agents.metrics import (
            add_hitl_decision_to_span,
            hitl_request_span,
        )

        with hitl_request_span(
            request_type="approval",
            request_id="req-002",
            agent_name="Test Agent",
            confidence=0.65,
            trigger_reason="low_confidence",
        ) as span:
            add_hitl_decision_to_span(span, "approved", 30.5)

    def test_add_hitl_decision_to_span_with_reason(self) -> None:
        """GIVEN an active HITL span
        WHEN adding a rejected decision with reason
        THEN it should not raise.
        """
        from mcp_server_langgraph.agents.metrics import (
            add_hitl_decision_to_span,
            hitl_request_span,
        )

        with hitl_request_span(
            request_type="approval",
            request_id="req-003",
            agent_name="Test Agent",
            confidence=0.5,
            trigger_reason="destructive_action",
        ) as span:
            add_hitl_decision_to_span(span, "rejected", 15.0, reason="Not authorized")

    def test_create_hitl_span_exists(self) -> None:
        """GIVEN the metrics module
        WHEN importing create_hitl_span
        THEN the function should exist.
        """
        from mcp_server_langgraph.agents.metrics import create_hitl_span

        assert callable(create_hitl_span)

    def test_create_hitl_span_returns_span(self) -> None:
        """GIVEN create_hitl_span
        WHEN called
        THEN it should return a span object.
        """
        from mcp_server_langgraph.agents.metrics import create_hitl_span

        span = create_hitl_span(
            request_type="clarification",
            request_id="req-004",
            agent_name="Data Analyst",
            confidence=0.8,
            trigger_reason="ambiguous_input",
        )
        try:
            assert span is not None
            assert hasattr(span, "set_attributes")
            assert hasattr(span, "end")
        finally:
            span.end()

    def test_hitl_tracer_exists(self) -> None:
        """GIVEN the metrics module
        WHEN importing hitl_tracer
        THEN it should be defined.
        """
        from mcp_server_langgraph.agents.metrics import hitl_tracer

        assert hitl_tracer is not None


@pytest.mark.unit
class TestAgentTaskMetrics:
    """Test suite for agent task metrics (used for HITL intervention rate calculation).

    The `agent_task_total` metric is referenced in HITL alert rules to calculate
    intervention rate: (HITL requests / total tasks).
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_task_counter_exists(self) -> None:
        """GIVEN the metrics module
        WHEN checking for agent task counter
        THEN it should be defined.
        """
        from mcp_server_langgraph.agents.metrics import agent_task_counter

        assert agent_task_counter is not None

    def test_record_agent_task_exists(self) -> None:
        """GIVEN the metrics module
        WHEN importing record_agent_task
        THEN the function should exist.
        """
        from mcp_server_langgraph.agents.metrics import record_agent_task

        assert callable(record_agent_task)

    def test_record_agent_task_successful(self) -> None:
        """GIVEN a successful agent task
        WHEN recording the task
        THEN it should record without error.
        """
        from mcp_server_langgraph.agents.metrics import record_agent_task

        record_agent_task(
            agent_name="Research Assistant",
            task_type="analysis",
            success=True,
        )

    def test_record_agent_task_failed(self) -> None:
        """GIVEN a failed agent task
        WHEN recording the task
        THEN it should record without error.
        """
        from mcp_server_langgraph.agents.metrics import record_agent_task

        record_agent_task(
            agent_name="Data Analyst",
            task_type="export",
            success=False,
            error_type="validation_error",
        )

    def test_record_agent_task_with_duration(self) -> None:
        """GIVEN a task with duration
        WHEN recording the task
        THEN it should record the duration without error.
        """
        from mcp_server_langgraph.agents.metrics import record_agent_task

        record_agent_task(
            agent_name="Code Reviewer",
            task_type="review",
            success=True,
            duration_ms=2500.0,
        )

    def test_record_agent_task_various_types(self) -> None:
        """GIVEN various task types
        WHEN recording agent tasks
        THEN all should be recorded successfully.
        """
        from mcp_server_langgraph.agents.metrics import record_agent_task

        task_types = [
            "analysis",
            "export",
            "review",
            "synthesis",
            "query",
        ]

        for task_type in task_types:
            record_agent_task(
                agent_name="Test Agent",
                task_type=task_type,
                success=True,
            )

    def test_agent_task_duration_histogram_exists(self) -> None:
        """GIVEN the metrics module
        WHEN checking for agent task duration histogram
        THEN it should be defined.
        """
        from mcp_server_langgraph.agents.metrics import agent_task_duration_histogram

        assert agent_task_duration_histogram is not None
