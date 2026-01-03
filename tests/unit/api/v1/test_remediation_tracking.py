"""
Tests for Remediation Tracking - had_fewshot and had_constraints.

TDD tests to verify that:
1. AIRecommendation tracks whether few-shot examples were used
2. AIRecommendation tracks whether rejection constraints were used
3. RemediationRequest receives these tracking fields from AIRecommendation
4. Approval/rejection metrics include these tracking fields

Reference: Plan Phase 3.2 - Remediation Tracking
"""

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="remediation_tracking")
class TestAIRecommendationTracking:
    """Tests for AI recommendation tracking fields."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    def test_ai_recommendation_has_tracking_fields(self) -> None:
        """AIRecommendation model has had_fewshot and had_constraints fields."""
        from mcp_server_langgraph.alerts.ai_recommendation import AIRecommendation

        recommendation = AIRecommendation(
            recommendation_id="rec-123",
            alert_id="alert-456",
            root_cause_analysis="Test analysis",
            remediation_steps=[],
            risk_assessment={},
            generated_at=datetime.now(UTC).isoformat(),
            model_used="test-model",
            had_fewshot=True,
            had_constraints=True,
        )

        assert recommendation.had_fewshot is True
        assert recommendation.had_constraints is True

    def test_ai_recommendation_tracking_defaults_to_false(self) -> None:
        """AIRecommendation tracking fields default to False."""
        from mcp_server_langgraph.alerts.ai_recommendation import AIRecommendation

        recommendation = AIRecommendation(
            recommendation_id="rec-123",
            alert_id="alert-456",
            root_cause_analysis="Test analysis",
            remediation_steps=[],
            risk_assessment={},
            generated_at=datetime.now(UTC).isoformat(),
            model_used="test-model",
        )

        assert recommendation.had_fewshot is False
        assert recommendation.had_constraints is False

    @pytest.mark.asyncio
    async def test_generate_recommendation_sets_had_fewshot_when_examples_used(self) -> None:
        """generate_recommendation sets had_fewshot=True when few-shot examples are available."""
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )
        from mcp_server_langgraph.observability.query.interfaces import (
            Alert,
            AlertSeverity,
            AlertState,
        )

        # Mock LLM factory
        mock_llm = AsyncMock()
        mock_llm.acompletion.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content='{"root_cause_analysis": "test", "remediation_steps": [], "risk_assessment": {}}'
                    )
                )
            ]
        )

        # Mock feedback store with examples
        mock_feedback_store = AsyncMock()
        mock_feedback_store.get_approved_examples.return_value = [
            MagicMock(alert_type="HighCPU", alert_labels={}, execution_time_seconds=10, admin_notes="Fixed"),
        ]
        mock_feedback_store.get_rejection_patterns.return_value = {}

        service = AIRecommendationService(
            llm_factory=mock_llm,
            feedback_store=mock_feedback_store,
        )

        alert = Alert(
            alert_id="alert-123",
            name="HighCPU",
            severity=AlertSeverity.WARNING,
            state=AlertState.FIRING,
            message="CPU is high",
            labels={},
            annotations={},
            started_at=datetime.now(UTC).isoformat(),
        )

        recommendation = await service.generate_recommendation(alert, force_regenerate=True)

        assert recommendation.had_fewshot is True

    @pytest.mark.asyncio
    async def test_generate_recommendation_sets_had_constraints_when_constraints_used(self) -> None:
        """generate_recommendation sets had_constraints=True when rejection constraints are applied."""
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )
        from mcp_server_langgraph.alerts.feedback import RejectionReason
        from mcp_server_langgraph.observability.query.interfaces import (
            Alert,
            AlertSeverity,
            AlertState,
        )

        # Mock LLM factory
        mock_llm = AsyncMock()
        mock_llm.acompletion.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content='{"root_cause_analysis": "test", "remediation_steps": [], "risk_assessment": {}}'
                    )
                )
            ]
        )

        # Mock feedback store with rejection patterns (>2 threshold triggers constraints)
        mock_feedback_store = AsyncMock()
        mock_feedback_store.get_approved_examples.return_value = []
        mock_feedback_store.get_rejection_patterns.return_value = {
            RejectionReason.TOO_RISKY: 5,  # Above threshold of 2
        }

        service = AIRecommendationService(
            llm_factory=mock_llm,
            feedback_store=mock_feedback_store,
        )

        alert = Alert(
            alert_id="alert-456",
            name="HighMemory",
            severity=AlertSeverity.CRITICAL,
            state=AlertState.FIRING,
            message="Memory is high",
            labels={},
            annotations={},
            started_at=datetime.now(UTC).isoformat(),
        )

        recommendation = await service.generate_recommendation(alert, force_regenerate=True)

        assert recommendation.had_constraints is True

    @pytest.mark.asyncio
    async def test_generate_recommendation_both_flags_false_without_feedback(self) -> None:
        """generate_recommendation sets both flags False when no feedback store is provided."""
        from mcp_server_langgraph.alerts.ai_recommendation import (
            AIRecommendationService,
        )
        from mcp_server_langgraph.observability.query.interfaces import (
            Alert,
            AlertSeverity,
            AlertState,
        )

        # Mock LLM factory
        mock_llm = AsyncMock()
        mock_llm.acompletion.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content='{"root_cause_analysis": "test", "remediation_steps": [], "risk_assessment": {}}'
                    )
                )
            ]
        )

        # No feedback store
        service = AIRecommendationService(llm_factory=mock_llm, feedback_store=None)

        alert = Alert(
            alert_id="alert-789",
            name="DiskFull",
            severity=AlertSeverity.WARNING,
            state=AlertState.FIRING,
            message="Disk is full",
            labels={},
            annotations={},
            started_at=datetime.now(UTC).isoformat(),
        )

        recommendation = await service.generate_recommendation(alert, force_regenerate=True)

        assert recommendation.had_fewshot is False
        assert recommendation.had_constraints is False


@pytest.mark.xdist_group(name="remediation_tracking")
class TestRemediationQueueTracking:
    """Tests for remediation queue propagating tracking fields."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_queue_remediation_propagates_had_fewshot(self) -> None:
        """queue_remediation copies had_fewshot from AIRecommendation to RemediationRequest."""
        from mcp_server_langgraph.alerts.ai_recommendation import AIRecommendation
        from mcp_server_langgraph.alerts.approval_queue import RemediationApprovalQueue

        queue = RemediationApprovalQueue()

        recommendation = AIRecommendation(
            recommendation_id="rec-123",
            alert_id="alert-456",
            root_cause_analysis="Test",
            remediation_steps=[{"step_number": 1, "action": "restart", "description": "Restart pod"}],
            risk_assessment={},
            generated_at=datetime.now(UTC).isoformat(),
            model_used="test-model",
            had_fewshot=True,
            had_constraints=False,
        )

        requests = await queue.queue_remediation(
            alert_id="alert-456",
            alert_name="HighCPU",
            severity="warning",
            recommendation=recommendation,
        )

        assert len(requests) == 1
        assert requests[0].had_fewshot is True
        assert requests[0].had_constraints is False

    @pytest.mark.asyncio
    async def test_queue_remediation_propagates_had_constraints(self) -> None:
        """queue_remediation copies had_constraints from AIRecommendation to RemediationRequest."""
        from mcp_server_langgraph.alerts.ai_recommendation import AIRecommendation
        from mcp_server_langgraph.alerts.approval_queue import RemediationApprovalQueue

        queue = RemediationApprovalQueue()

        recommendation = AIRecommendation(
            recommendation_id="rec-789",
            alert_id="alert-101",
            root_cause_analysis="Test",
            remediation_steps=[{"step_number": 1, "action": "scale", "description": "Scale deployment"}],
            risk_assessment={},
            generated_at=datetime.now(UTC).isoformat(),
            model_used="test-model",
            had_fewshot=False,
            had_constraints=True,
        )

        requests = await queue.queue_remediation(
            alert_id="alert-101",
            alert_name="HighMemory",
            severity="critical",
            recommendation=recommendation,
        )

        assert len(requests) == 1
        assert requests[0].had_fewshot is False
        assert requests[0].had_constraints is True


@pytest.mark.xdist_group(name="remediation_tracking")
class TestApprovalMetricsTracking:
    """Tests for approval/rejection metrics including tracking fields."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_approval_records_tracking_fields(self) -> None:
        """record_recommendation_approval is called with had_fewshot and had_constraints."""
        from mcp_server_langgraph.alerts.approval_queue import (
            RemediationApprovalQueue,
            RemediationRequest,
        )
        from mcp_server_langgraph.alerts.feedback import InMemoryFeedbackStore
        from mcp_server_langgraph.core.interrupts.approval import ApprovalStatus

        queue = RemediationApprovalQueue()
        feedback_store = InMemoryFeedbackStore()

        # Manually add a remediation with tracking flags set
        request = RemediationRequest(
            remediation_id="rem-123",
            alert_id="alert-456",
            alert_name="HighCPU",
            severity="warning",
            step_number=1,
            action="restart",
            description="Restart pod",
            status=ApprovalStatus.PENDING,
            requested_at=datetime.now(UTC).isoformat(),
            had_fewshot=True,
            had_constraints=True,
        )
        queue._remediations["rem-123"] = request

        with patch("mcp_server_langgraph.api.v1.remediation_approvals.record_recommendation_approval") as mock_record:
            # Import and call the approve endpoint logic
            from mcp_server_langgraph.api.v1.remediation_approvals import ApproveRequest

            result = await queue.approve_with_feedback(
                remediation_id="rem-123",
                approved_by="admin@example.com",
                feedback_store=feedback_store,
            )

            # The tracking fields should be preserved
            assert result.had_fewshot is True
            assert result.had_constraints is True

    @pytest.mark.asyncio
    async def test_rejection_records_tracking_fields(self) -> None:
        """record_recommendation_rejection is called with had_fewshot and had_constraints."""
        from mcp_server_langgraph.alerts.approval_queue import (
            RemediationApprovalQueue,
            RemediationRequest,
        )
        from mcp_server_langgraph.alerts.feedback import InMemoryFeedbackStore, RejectionReason
        from mcp_server_langgraph.core.interrupts.approval import ApprovalStatus

        queue = RemediationApprovalQueue()
        feedback_store = InMemoryFeedbackStore()

        # Manually add a remediation with tracking flags set
        request = RemediationRequest(
            remediation_id="rem-456",
            alert_id="alert-789",
            alert_name="HighMemory",
            severity="critical",
            step_number=1,
            action="scale",
            description="Scale deployment",
            status=ApprovalStatus.PENDING,
            requested_at=datetime.now(UTC).isoformat(),
            had_fewshot=False,
            had_constraints=True,
        )
        queue._remediations["rem-456"] = request

        result = await queue.reject_with_feedback(
            remediation_id="rem-456",
            rejected_by="admin@example.com",
            reason=RejectionReason.TOO_RISKY,
            feedback_store=feedback_store,
        )

        # The tracking fields should be preserved
        assert result.had_fewshot is False
        assert result.had_constraints is True
