"""Tests for Response Model NaN/Inf Validators.

TDD: These tests verify that Pydantic field validators in response models
properly convert NaN/Inf values to safe defaults before JSON serialization.

This prevents JSON serialization failures when Prometheus histogram_quantile()
or other metrics calculations return NaN.
"""

from __future__ import annotations

import gc
import json
import math

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.api]


@pytest.mark.xdist_group(name="response_model_validators")
class TestCostResponseModelValidators:
    """Test validators for cost-related response models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_budget_status_response_nan_percent_used(self) -> None:
        """GIVEN NaN value for percent_used
        WHEN BudgetStatusResponse is created
        THEN percent_used is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.cost import BudgetStatusResponse

        response = BudgetStatusResponse(
            status="ok",
            percent_used=float("nan"),
            current_spend=100.0,
            remaining=900.0,
            monthly_limit=1000.0,
            entity_type="organization",
            entity_id="org-123",
            message="Test",
        )

        assert response.percent_used == 0.0
        assert math.isfinite(response.percent_used)

    def test_budget_status_response_inf_values(self) -> None:
        """GIVEN Infinity values for float fields
        WHEN BudgetStatusResponse is created
        THEN values are converted to 0.0
        """
        from mcp_server_langgraph.api.v1.cost import BudgetStatusResponse

        response = BudgetStatusResponse(
            status="exceeded",
            percent_used=float("inf"),
            current_spend=float("-inf"),
            remaining=float("inf"),
            monthly_limit=float("-inf"),
            entity_type="user",
            entity_id="user-456",
            message="Test",
        )

        assert response.percent_used == 0.0
        assert response.current_spend == 0.0
        assert response.remaining == 0.0
        assert response.monthly_limit == 0.0

    def test_budget_status_response_json_serializable(self) -> None:
        """GIVEN BudgetStatusResponse with NaN input
        WHEN serialized to JSON
        THEN no serialization error occurs
        """
        from mcp_server_langgraph.api.v1.cost import BudgetStatusResponse

        response = BudgetStatusResponse(
            status="warning",
            percent_used=float("nan"),
            current_spend=float("inf"),
            remaining=float("-inf"),
            monthly_limit=1000.0,
            entity_type="project",
            entity_id="proj-789",
            message="Test",
        )

        # Should not raise ValueError
        json_str = response.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["percent_used"] == 0.0
        assert parsed["current_spend"] == 0.0
        assert parsed["remaining"] == 0.0

    def test_anomaly_detection_response_nan_z_score(self) -> None:
        """GIVEN NaN value for z_score
        WHEN AnomalyDetectionResponse is created
        THEN z_score is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.cost import AnomalyDetectionResponse

        response = AnomalyDetectionResponse(
            is_anomaly=False,
            severity="none",
            z_score=float("nan"),
            mean=100.0,
            std_dev=10.0,
            message="No anomaly",
        )

        assert response.z_score == 0.0

    def test_anomaly_detection_response_all_nan(self) -> None:
        """GIVEN NaN values for all float fields
        WHEN AnomalyDetectionResponse is created
        THEN all values are converted to 0.0
        """
        from mcp_server_langgraph.api.v1.cost import AnomalyDetectionResponse

        response = AnomalyDetectionResponse(
            is_anomaly=True,
            severity="critical",
            z_score=float("nan"),
            mean=float("nan"),
            std_dev=float("nan"),
            message="Anomaly detected",
        )

        assert response.z_score == 0.0
        assert response.mean == 0.0
        assert response.std_dev == 0.0

    def test_anomaly_detection_response_json_serializable(self) -> None:
        """GIVEN AnomalyDetectionResponse with NaN inputs
        WHEN serialized to JSON
        THEN no serialization error occurs
        """
        from mcp_server_langgraph.api.v1.cost import AnomalyDetectionResponse

        response = AnomalyDetectionResponse(
            is_anomaly=True,
            severity="warning",
            z_score=float("inf"),
            mean=float("-inf"),
            std_dev=float("nan"),
            message="Test",
        )

        json_str = response.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["z_score"] == 0.0
        assert parsed["mean"] == 0.0
        assert parsed["std_dev"] == 0.0

    def test_forecast_response_nan_projected_total(self) -> None:
        """GIVEN NaN value for projected_total
        WHEN ForecastResponse is created
        THEN projected_total is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.cost import ForecastResponse

        response = ForecastResponse(
            projected_total=float("nan"),
            confidence_low=50.0,
            confidence_high=150.0,
            trend="stable",
            days_analyzed=7,
            message="Forecast",
        )

        assert response.projected_total == 0.0

    def test_forecast_response_all_nan(self) -> None:
        """GIVEN NaN values for all float fields
        WHEN ForecastResponse is created
        THEN all values are converted to 0.0
        """
        from mcp_server_langgraph.api.v1.cost import ForecastResponse

        response = ForecastResponse(
            projected_total=float("nan"),
            confidence_low=float("nan"),
            confidence_high=float("nan"),
            trend="increasing",
            days_analyzed=30,
            message="Forecast",
        )

        assert response.projected_total == 0.0
        assert response.confidence_low == 0.0
        assert response.confidence_high == 0.0

    def test_forecast_response_json_serializable(self) -> None:
        """GIVEN ForecastResponse with NaN inputs
        WHEN serialized to JSON
        THEN no serialization error occurs
        """
        from mcp_server_langgraph.api.v1.cost import ForecastResponse

        response = ForecastResponse(
            projected_total=float("inf"),
            confidence_low=float("-inf"),
            confidence_high=float("nan"),
            trend="decreasing",
            days_analyzed=14,
            message="Test",
        )

        json_str = response.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["projected_total"] == 0.0
        assert parsed["confidence_low"] == 0.0
        assert parsed["confidence_high"] == 0.0


@pytest.mark.xdist_group(name="response_model_validators")
class TestObservabilityResponseModelValidators:
    """Test validators for observability-related response models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_span_response_nan_duration(self) -> None:
        """GIVEN NaN value for duration_ms
        WHEN SpanResponse is created
        THEN duration_ms is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.observability import SpanResponse

        response = SpanResponse(
            span_id="span-123",
            name="test-span",
            start_time="2024-01-01T00:00:00Z",
            duration_ms=float("nan"),
        )

        assert response.duration_ms == 0.0

    def test_span_response_inf_duration(self) -> None:
        """GIVEN Infinity value for duration_ms
        WHEN SpanResponse is created
        THEN duration_ms is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.observability import SpanResponse

        response = SpanResponse(
            span_id="span-456",
            name="test-span",
            start_time="2024-01-01T00:00:00Z",
            duration_ms=float("inf"),
        )

        assert response.duration_ms == 0.0

    def test_span_response_none_duration_unchanged(self) -> None:
        """GIVEN None value for duration_ms
        WHEN SpanResponse is created
        THEN duration_ms remains None (optional field)
        """
        from mcp_server_langgraph.api.v1.observability import SpanResponse

        response = SpanResponse(
            span_id="span-789",
            name="test-span",
            start_time="2024-01-01T00:00:00Z",
            duration_ms=None,
        )

        assert response.duration_ms is None

    def test_trace_response_nan_duration(self) -> None:
        """GIVEN NaN value for duration_ms
        WHEN TraceResponse is created
        THEN duration_ms is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.observability import TraceResponse

        response = TraceResponse(
            trace_id="trace-123",
            name="test-trace",
            duration_ms=float("nan"),
        )

        assert response.duration_ms == 0.0

    def test_trace_list_item_nan_duration(self) -> None:
        """GIVEN NaN value for duration_ms
        WHEN TraceListItem is created
        THEN duration_ms is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.observability import TraceListItem

        item = TraceListItem(
            trace_id="trace-456",
            name="test-trace",
            duration_ms=float("nan"),
        )

        assert item.duration_ms == 0.0

    def test_metrics_response_nan_latencies(self) -> None:
        """GIVEN NaN values for latency fields
        WHEN MetricsResponse is created
        THEN latency values are converted to 0.0
        """
        from mcp_server_langgraph.api.v1.observability import MetricsResponse

        response = MetricsResponse(
            requests_total=100,
            errors_total=5,
            avg_latency_ms=float("nan"),
            p99_latency_ms=float("nan"),
            latency_p50=float("nan"),
            latency_p95=float("nan"),
            latency_p99=float("nan"),
        )

        assert response.avg_latency_ms == 0.0
        assert response.p99_latency_ms == 0.0
        assert response.latency_p50 == 0.0
        assert response.latency_p95 == 0.0
        assert response.latency_p99 == 0.0

    def test_metrics_response_json_serializable(self) -> None:
        """GIVEN MetricsResponse with NaN inputs
        WHEN serialized to JSON
        THEN no serialization error occurs
        """
        from mcp_server_langgraph.api.v1.observability import MetricsResponse

        response = MetricsResponse(
            requests_total=1000,
            errors_total=10,
            avg_latency_ms=float("inf"),
            p99_latency_ms=float("-inf"),
            latency_p50=float("nan"),
        )

        json_str = response.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["avg_latency_ms"] == 0.0
        assert parsed["p99_latency_ms"] == 0.0
        assert parsed["latency_p50"] == 0.0

    def test_session_metrics_response_nan_latencies(self) -> None:
        """GIVEN NaN values for latency fields
        WHEN SessionMetricsResponse is created
        THEN latency values are converted to 0.0
        """
        from mcp_server_langgraph.api.v1.observability import SessionMetricsResponse

        response = SessionMetricsResponse(
            total_requests=50,
            total_errors=2,
            avg_latency_ms=float("nan"),
            p95_latency_ms=float("inf"),
        )

        assert response.avg_latency_ms == 0.0
        assert response.p95_latency_ms == 0.0

    def test_workflow_metrics_response_nan_latencies(self) -> None:
        """GIVEN NaN values for latency fields
        WHEN WorkflowMetricsResponse is created
        THEN latency values are converted to 0.0
        """
        from mcp_server_langgraph.api.v1.observability import WorkflowMetricsResponse

        response = WorkflowMetricsResponse(
            total_executions=25,
            total_errors=1,
            avg_latency_ms=float("nan"),
            p95_latency_ms=float("-inf"),
        )

        assert response.avg_latency_ms == 0.0
        assert response.p95_latency_ms == 0.0

    def test_user_metrics_response_nan_latency(self) -> None:
        """GIVEN NaN value for avg_latency_ms
        WHEN UserMetricsResponse is created
        THEN avg_latency_ms is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.observability import UserMetricsResponse

        response = UserMetricsResponse(
            total_requests=100,
            total_sessions=10,
            total_errors=5,
            avg_latency_ms=float("nan"),
        )

        assert response.avg_latency_ms == 0.0

    def test_llm_streaming_metrics_response_nan_values(self) -> None:
        """GIVEN NaN values for streaming metrics
        WHEN LLMStreamingMetricsResponse is created
        THEN values are converted to 0.0
        """
        from mcp_server_langgraph.api.v1.observability import LLMStreamingMetricsResponse

        response = LLMStreamingMetricsResponse(
            ttfc_p50_seconds=float("nan"),
            ttfc_p95_seconds=float("inf"),
            ttfc_p99_seconds=float("-inf"),
            inter_chunk_latency_p50_seconds=float("nan"),
            inter_chunk_latency_p95_seconds=float("nan"),
            duration_avg_seconds=float("nan"),
            success_rate=float("nan"),
        )

        assert response.ttfc_p50_seconds == 0.0
        assert response.ttfc_p95_seconds == 0.0
        assert response.ttfc_p99_seconds == 0.0
        assert response.inter_chunk_latency_p50_seconds == 0.0
        assert response.inter_chunk_latency_p95_seconds == 0.0
        assert response.duration_avg_seconds == 0.0
        assert response.success_rate == 0.0


@pytest.mark.xdist_group(name="response_model_validators")
class TestWebSocketProtocolValidators:
    """Test validators for WebSocket protocol models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_budget_alert_payload_nan_percent_used(self) -> None:
        """GIVEN NaN value for percent_used
        WHEN BudgetAlertPayload is created
        THEN percent_used is converted to 0.0
        """
        from mcp_server_langgraph.websocket.protocols import (
            BudgetAlertPayload,
            BudgetAlertStatus,
            BudgetEntityType,
        )

        payload = BudgetAlertPayload(
            entity_type=BudgetEntityType.ORGANIZATION,
            entity_id="org-123",
            status=BudgetAlertStatus.WARNING,
            percent_used=float("nan"),
            current_spend="$500.00",
            remaining="$500.00",
            monthly_limit_usd="$1000.00",
        )

        assert payload.percent_used == 0.0

    def test_budget_alert_payload_inf_percent_used(self) -> None:
        """GIVEN Infinity value for percent_used
        WHEN BudgetAlertPayload is created
        THEN percent_used is converted to 0.0
        """
        from mcp_server_langgraph.websocket.protocols import (
            BudgetAlertPayload,
            BudgetAlertStatus,
            BudgetEntityType,
        )

        payload = BudgetAlertPayload(
            entity_type=BudgetEntityType.USER,
            entity_id="user-456",
            status=BudgetAlertStatus.EXCEEDED,
            percent_used=float("inf"),
            current_spend="$1500.00",
            remaining="-$500.00",
            monthly_limit_usd="$1000.00",
        )

        assert payload.percent_used == 0.0

    def test_suggestion_response_payload_nan_confidence(self) -> None:
        """GIVEN NaN value for confidence
        WHEN SuggestionResponsePayload is created
        THEN confidence is converted to 0.0
        """
        from mcp_server_langgraph.websocket.protocols import SuggestionResponsePayload

        payload = SuggestionResponsePayload(
            suggestion_id="sug-123",
            text="Test suggestion",
            confidence=float("nan"),
        )

        assert payload.confidence == 0.0

    def test_suggestion_response_payload_inf_confidence(self) -> None:
        """GIVEN Infinity value for confidence
        WHEN SuggestionResponsePayload is created
        THEN confidence is converted to 0.0
        """
        from mcp_server_langgraph.websocket.protocols import SuggestionResponsePayload

        payload = SuggestionResponsePayload(
            suggestion_id="sug-456",
            text="Another suggestion",
            confidence=float("inf"),
        )

        assert payload.confidence == 0.0

    def test_suggestion_response_payload_json_serializable(self) -> None:
        """GIVEN SuggestionResponsePayload with NaN confidence
        WHEN serialized to JSON
        THEN no serialization error occurs
        """
        from mcp_server_langgraph.websocket.protocols import SuggestionResponsePayload

        payload = SuggestionResponsePayload(
            suggestion_id="sug-789",
            text="Suggestion with NaN",
            confidence=float("nan"),
            reasoning="Test reasoning",
        )

        json_str = payload.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["confidence"] == 0.0


@pytest.mark.xdist_group(name="response_model_validators")
class TestCostSummaryResponseValidators:
    """Test validators for additional cost response models (Round 2)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_cost_summary_response_nan_total_cost(self) -> None:
        """GIVEN NaN value for total_cost
        WHEN CostSummaryResponse is created
        THEN total_cost is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.cost import CostSummaryResponse

        response = CostSummaryResponse(
            total_cost=float("nan"),
            prompt_tokens=100,
            completion_tokens=50,
        )

        assert response.total_cost == 0.0

    def test_cost_summary_response_inf_total_cost(self) -> None:
        """GIVEN Infinity value for total_cost
        WHEN CostSummaryResponse is created
        THEN total_cost is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.cost import CostSummaryResponse

        response = CostSummaryResponse(
            total_cost=float("inf"),
            prompt_tokens=100,
            completion_tokens=50,
        )

        assert response.total_cost == 0.0

    def test_model_cost_response_nan_cost(self) -> None:
        """GIVEN NaN value for cost
        WHEN ModelCostResponse is created
        THEN cost is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.cost import ModelCostResponse

        response = ModelCostResponse(
            model="gpt-4o",
            cost=float("nan"),
            requests=10,
        )

        assert response.cost == 0.0

    def test_daily_cost_response_nan_cost(self) -> None:
        """GIVEN NaN value for cost
        WHEN DailyCostResponse is created
        THEN cost is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.cost import DailyCostResponse

        response = DailyCostResponse(
            date="2024-01-01",
            cost=float("nan"),
        )

        assert response.cost == 0.0

    def test_cost_record_response_nan_estimated_cost(self) -> None:
        """GIVEN NaN value for estimated_cost_usd
        WHEN CostRecordResponse is created
        THEN estimated_cost_usd is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.cost import CostRecordResponse

        response = CostRecordResponse(
            timestamp="2024-01-01T00:00:00Z",
            user_id="user-123",
            session_id="session-456",
            model="gpt-4o",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=float("nan"),
        )

        assert response.estimated_cost_usd == 0.0

    def test_organization_cost_response_nan_total_cost(self) -> None:
        """GIVEN NaN value for total_cost
        WHEN OrganizationCostResponse is created
        THEN total_cost is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.cost import OrganizationCostResponse

        response = OrganizationCostResponse(
            organization_id="org-123",
            total_cost=float("nan"),
            total_tokens=1000,
            request_count=10,
        )

        assert response.total_cost == 0.0

    def test_project_cost_response_nan_total_cost(self) -> None:
        """GIVEN NaN value for total_cost
        WHEN ProjectCostResponse is created
        THEN total_cost is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.cost import ProjectCostResponse

        response = ProjectCostResponse(
            project_id="proj-123",
            total_cost=float("nan"),
            total_tokens=500,
            request_count=5,
        )

        assert response.total_cost == 0.0

    def test_team_cost_response_nan_total_cost(self) -> None:
        """GIVEN NaN value for total_cost
        WHEN TeamCostResponse is created
        THEN total_cost is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.cost import TeamCostResponse

        response = TeamCostResponse(
            team_id="team-123",
            total_cost=float("nan"),
            total_tokens=250,
            request_count=3,
        )

        assert response.total_cost == 0.0


@pytest.mark.xdist_group(name="response_model_validators")
class TestWorkflowResponseValidators:
    """Test validators for workflow response models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_node_position_nan_coordinates(self) -> None:
        """GIVEN NaN values for x and y coordinates
        WHEN NodePosition is created
        THEN coordinates are converted to 0.0
        """
        from mcp_server_langgraph.api.v1.workflows import NodePosition

        position = NodePosition(
            x=float("nan"),
            y=float("nan"),
        )

        assert position.x == 0.0
        assert position.y == 0.0

    def test_node_position_inf_coordinates(self) -> None:
        """GIVEN Infinity values for coordinates
        WHEN NodePosition is created
        THEN coordinates are converted to 0.0
        """
        from mcp_server_langgraph.api.v1.workflows import NodePosition

        position = NodePosition(
            x=float("inf"),
            y=float("-inf"),
        )

        assert position.x == 0.0
        assert position.y == 0.0

    def test_generate_workflow_response_nan_confidence(self) -> None:
        """GIVEN NaN value for confidence
        WHEN GenerateWorkflowResponse is created
        THEN confidence is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.workflows import (
            GenerateWorkflowResponse,
            WorkflowResponse,
        )

        response = GenerateWorkflowResponse(
            workflow=WorkflowResponse(id="wf-123", name="Test Workflow"),
            confidence=float("nan"),
        )

        assert response.confidence == 0.0

    def test_from_chat_response_nan_confidence(self) -> None:
        """GIVEN NaN value for confidence
        WHEN FromChatResponse is created
        THEN confidence is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.workflows import (
            FromChatResponse,
            PromptMetadata,
            WorkflowResponse,
        )

        response = FromChatResponse(
            workflow=WorkflowResponse(id="wf-456", name="Chat Workflow"),
            confidence=float("nan"),
            prompt_metadata=PromptMetadata(
                name="test",
                version="v1",
                hash="abc123",
                model="gpt-4o",
            ),
        )

        assert response.confidence == 0.0


@pytest.mark.xdist_group(name="response_model_validators")
class TestSurveyResponseValidators:
    """Test validators for survey response models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_sus_survey_response_nan_score(self) -> None:
        """GIVEN NaN value for sus_score
        WHEN SUSSurveyResponse is created
        THEN sus_score is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.surveys import SUSSurveyResponse

        response = SUSSurveyResponse(
            id="survey-123",
            sus_score=float("nan"),
        )

        assert response.sus_score == 0.0

    def test_sus_survey_response_inf_score(self) -> None:
        """GIVEN Infinity value for sus_score
        WHEN SUSSurveyResponse is created
        THEN sus_score is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.surveys import SUSSurveyResponse

        response = SUSSurveyResponse(
            id="survey-456",
            sus_score=float("inf"),
        )

        assert response.sus_score == 0.0


@pytest.mark.xdist_group(name="response_model_validators")
class TestAgentMetricsResponseValidators:
    """Test validators for agent metrics response models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestrator_metrics_nan_duration(self) -> None:
        """GIVEN NaN values for duration fields
        WHEN OrchestratorMetrics is created
        THEN duration values are converted to 0.0
        """
        from mcp_server_langgraph.api.v1.agents import OrchestratorMetrics

        metrics = OrchestratorMetrics(
            total_executions=100,
            successful_executions=95,
            failed_executions=5,
            avg_duration_ms=float("nan"),
            p50_duration_ms=float("nan"),
            p95_duration_ms=float("nan"),
            p99_duration_ms=float("nan"),
        )

        assert metrics.avg_duration_ms == 0.0
        assert metrics.p50_duration_ms == 0.0
        assert metrics.p95_duration_ms == 0.0
        assert metrics.p99_duration_ms == 0.0

    def test_hitl_metrics_nan_latency(self) -> None:
        """GIVEN NaN value for avg_response_latency_ms
        WHEN HITLMetrics is created
        THEN avg_response_latency_ms is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.agents import HITLMetrics

        metrics = HITLMetrics(
            total_requests=50,
            approved_count=40,
            rejected_count=5,
            pending_count=5,
            avg_response_latency_ms=float("nan"),
        )

        assert metrics.avg_response_latency_ms == 0.0

    def test_cost_metrics_nan_values(self) -> None:
        """GIVEN NaN values for cost fields
        WHEN CostMetrics is created
        THEN cost values are converted to 0.0
        """
        from mcp_server_langgraph.api.v1.agents import CostMetrics

        metrics = CostMetrics(
            total_cost_usd=float("nan"),
            total_tokens=1500,
            avg_cost_per_request_usd=float("nan"),
        )

        assert metrics.total_cost_usd == 0.0
        assert metrics.avg_cost_per_request_usd == 0.0


@pytest.mark.xdist_group(name="response_model_validators")
class TestAISuggestionResponseValidators:
    """Test validators for AI suggestion response models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_workflow_suggestion_nan_confidence(self) -> None:
        """GIVEN NaN value for confidence
        WHEN WorkflowSuggestion is created
        THEN confidence is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.ai import WorkflowSuggestion

        suggestion = WorkflowSuggestion(
            type="optimization",
            description="Test description",
            confidence=float("nan"),
        )

        assert suggestion.confidence == 0.0

    def test_artifact_suggestion_nan_confidence(self) -> None:
        """GIVEN NaN value for confidence
        WHEN ArtifactSuggestion is created
        THEN confidence is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.ai import ArtifactSuggestion

        suggestion = ArtifactSuggestion(
            id="sug-123",
            type="completion",
            content="Test artifact content",
            confidence=float("nan"),
        )

        assert suggestion.confidence == 0.0

    def test_chat_suggestion_nan_confidence(self) -> None:
        """GIVEN NaN value for confidence
        WHEN ChatSuggestion is created
        THEN confidence is converted to default (0.7)
        """
        from mcp_server_langgraph.api.v1.ai import ChatSuggestion

        suggestion = ChatSuggestion(
            text="Test suggestion",
            confidence=float("nan"),
        )

        # Default is 0.7 when NaN provided
        assert suggestion.confidence == 0.7

    def test_interpreted_action_nan_confidence(self) -> None:
        """GIVEN NaN value for confidence
        WHEN InterpretedAction is created
        THEN confidence is converted to default (0.8)
        """
        from mcp_server_langgraph.api.v1.ai import InterpretedAction

        action = InterpretedAction(
            action="test_action",
            intent="test_intent",
            parameters={},
            confidence=float("nan"),
        )

        # Default is 0.8 when NaN provided
        assert action.confidence == 0.8

    def test_interpret_command_response_nan_confidence(self) -> None:
        """GIVEN NaN value for confidence
        WHEN InterpretCommandResponse is created
        THEN confidence is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.ai import InterpretCommandResponse

        response = InterpretCommandResponse(
            action="navigate",
            intent="navigation",
            confidence=float("nan"),
            parameters={"target": "home"},
        )

        assert response.confidence == 0.0


@pytest.mark.xdist_group(name="response_model_validators")
class TestAIUXResponseValidators:
    """Test validators for AI UX response models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_disclosure_analyze_response_nan_confidence(self) -> None:
        """GIVEN NaN value for confidence
        WHEN DisclosureAnalyzeResponse is created
        THEN confidence is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.ai_ux import DisclosureAnalyzeResponse

        response = DisclosureAnalyzeResponse(
            current_level="beginner",
            recommended_level="intermediate",
            confidence=float("nan"),
        )

        assert response.confidence == 0.0

    def test_nudge_recommend_response_nan_confidence(self) -> None:
        """GIVEN NaN value for confidence
        WHEN NudgeRecommendResponse is created
        THEN confidence is converted to 0.5 (default)
        """
        from mcp_server_langgraph.api.v1.ai_ux import NudgeRecommendResponse

        response = NudgeRecommendResponse(
            should_show=True,
            confidence=float("nan"),
        )

        # Default is 0.5 when NaN provided
        assert response.confidence == 0.5

    def test_error_analyze_response_nan_confidence(self) -> None:
        """GIVEN NaN value for confidence
        WHEN ErrorAnalyzeResponse is created
        THEN confidence is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeResponse

        response = ErrorAnalyzeResponse(
            error_type="validation",
            auto_recoverable=False,
            confidence=float("nan"),
        )

        assert response.confidence == 0.0

    def test_onboarding_personalize_response_nan_confidence(self) -> None:
        """GIVEN NaN value for confidence
        WHEN OnboardingPersonalizeResponse is created
        THEN confidence is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.ai_ux import OnboardingPersonalizeResponse, OnboardingStep

        response = OnboardingPersonalizeResponse(
            detected_intent="explore",
            confidence=float("nan"),
            recommended_path=[OnboardingStep(step="welcome")],
        )

        assert response.confidence == 0.0

    def test_metrics_insights_response_nan_happiness_score(self) -> None:
        """GIVEN NaN value for happiness_score
        WHEN MetricsInsightsResponse is created
        THEN happiness_score is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.ai_ux import MetricsInsightsResponse, OverallHealth

        response = MetricsInsightsResponse(
            happiness_score=float("nan"),
            overall_health=OverallHealth.GOOD,
        )

        assert response.happiness_score == 0.0

    def test_composite_analysis_response_nan_confidence(self) -> None:
        """GIVEN NaN value for confidence
        WHEN CompositeAnalysisResponse is created
        THEN confidence is converted to 0.0
        """
        from mcp_server_langgraph.api.v1.ai_ux import CompositeAnalysisResponse

        response = CompositeAnalysisResponse(
            user_id="user-123",
            session_id="session-456",
            confidence=float("nan"),
        )

        assert response.confidence == 0.0
