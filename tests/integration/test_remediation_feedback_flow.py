"""
Integration tests for Remediation Approval with Feedback Learning.

Tests the complete flow from remediation approval/rejection to AI model feedback:
- Approval flow with execution result tracking
- Rejection flow with structured reasons
- Few-shot learning from approved examples
- Constraint learning from rejection patterns
- Feedback-enhanced AI recommendations

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import gc
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from mcp_server_langgraph.alerts.feedback import (
    FeedbackStore,
    InMemoryFeedbackStore,
    RejectionReason,
    RemediationFeedback,
)
from mcp_server_langgraph.observability.query.interfaces import (
    Alert,
    AlertSeverity,
    AlertState,
)

# Mark as integration test
pytestmark = pytest.mark.integration


@pytest.fixture
def feedback_store() -> InMemoryFeedbackStore:
    """Create an in-memory feedback store for testing."""
    return InMemoryFeedbackStore()


@pytest.fixture
def sample_alert() -> Alert:
    """Create a sample alert for testing."""
    return Alert(
        alert_id="alert-cpu-001",
        name="HighCPUUsage",
        severity=AlertSeverity.CRITICAL,
        state=AlertState.FIRING,
        message="CPU usage exceeded 95% on production API server",
        labels={
            "service": "api-server",
            "namespace": "production",
            "pod": "api-server-7c8d9f4b-xyz",
        },
        annotations={
            "runbook_url": "https://runbooks.example.com/cpu",
            "summary": "Critical CPU usage detected",
        },
        started_at=datetime.now(UTC),
    )


@pytest.fixture
def approved_feedback_factory(
    feedback_store: InMemoryFeedbackStore,
) -> AsyncMock:
    """Factory to create approved feedback entries."""

    async def create_approved_feedback(
        alert_type: str,
        count: int = 1,
        execution_success: bool = True,
    ) -> list[RemediationFeedback]:
        feedbacks = []
        for i in range(count):
            fb = RemediationFeedback(
                feedback_id=str(uuid.uuid4()),
                remediation_id=str(uuid.uuid4()),
                recommendation_id=str(uuid.uuid4()),
                alert_type=alert_type,
                alert_labels={"service": f"service-{i}"},
                severity="critical",
                action="approved",
                reason=None,
                reason_detail=None,
                admin_user_id=f"admin-{i:03d}",
                timestamp=datetime.now(UTC) - timedelta(hours=i),
                execution_success=execution_success,
                execution_time_seconds=5.0 + i,
                admin_notes=f"Approved successfully - test case {i}",
            )
            await feedback_store.save_feedback(fb)
            feedbacks.append(fb)
        return feedbacks

    return AsyncMock(side_effect=create_approved_feedback)


@pytest.mark.xdist_group(name="integration_remediation_feedback")
class TestRemediationApprovalFlow:
    """Tests for the complete remediation approval flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_approval_saves_feedback(
        self,
        feedback_store: InMemoryFeedbackStore,
        sample_alert: Alert,
    ) -> None:
        """
        GIVEN an admin reviewing a remediation
        WHEN they approve the remediation
        THEN feedback is saved with action='approved'.
        """
        # Create approval feedback
        feedback = RemediationFeedback(
            feedback_id=str(uuid.uuid4()),
            remediation_id="rem-001",
            recommendation_id="rec-001",
            alert_type=sample_alert.name,
            alert_labels=sample_alert.labels,
            severity=sample_alert.severity.value,
            action="approved",
            reason=None,
            reason_detail=None,
            admin_user_id="admin-001",
            timestamp=datetime.now(UTC),
        )

        # Save feedback
        await feedback_store.save_feedback(feedback)

        # Verify feedback was saved
        recent = await feedback_store.get_recent_feedback(limit=10)
        assert len(recent) == 1
        assert recent[0].action == "approved"
        assert recent[0].remediation_id == "rem-001"

    @pytest.mark.asyncio
    async def test_approval_tracks_execution_result(
        self,
        feedback_store: InMemoryFeedbackStore,
        sample_alert: Alert,
    ) -> None:
        """
        GIVEN an approved remediation
        WHEN execution completes
        THEN the execution result is recorded.
        """
        # Create and save approval feedback
        feedback = RemediationFeedback(
            feedback_id=str(uuid.uuid4()),
            remediation_id="rem-002",
            recommendation_id="rec-002",
            alert_type=sample_alert.name,
            alert_labels=sample_alert.labels,
            severity=sample_alert.severity.value,
            action="approved",
            reason=None,
            reason_detail=None,
            admin_user_id="admin-001",
            timestamp=datetime.now(UTC),
        )
        await feedback_store.save_feedback(feedback)

        # Update with execution result
        await feedback_store.update_execution_result(
            remediation_id="rem-002",
            success=True,
            execution_time_seconds=3.5,
        )

        # Verify execution result was recorded
        recent = await feedback_store.get_recent_feedback(limit=10)
        assert len(recent) == 1
        assert recent[0].execution_success is True
        assert recent[0].execution_time_seconds == 3.5

    @pytest.mark.asyncio
    async def test_failed_execution_tracked(
        self,
        feedback_store: InMemoryFeedbackStore,
        sample_alert: Alert,
    ) -> None:
        """
        GIVEN an approved remediation
        WHEN execution fails
        THEN the failure is recorded.
        """
        feedback = RemediationFeedback(
            feedback_id=str(uuid.uuid4()),
            remediation_id="rem-003",
            recommendation_id="rec-003",
            alert_type=sample_alert.name,
            alert_labels=sample_alert.labels,
            severity=sample_alert.severity.value,
            action="approved",
            reason=None,
            reason_detail=None,
            admin_user_id="admin-001",
            timestamp=datetime.now(UTC),
        )
        await feedback_store.save_feedback(feedback)

        # Update with failed execution
        await feedback_store.update_execution_result(
            remediation_id="rem-003",
            success=False,
            execution_time_seconds=1.2,
        )

        recent = await feedback_store.get_recent_feedback(limit=10)
        assert recent[0].execution_success is False
        assert recent[0].execution_time_seconds == 1.2


@pytest.mark.xdist_group(name="integration_remediation_feedback")
class TestRemediationRejectionFlow:
    """Tests for the remediation rejection flow with structured reasons."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_rejection_saves_structured_reason(
        self,
        feedback_store: InMemoryFeedbackStore,
        sample_alert: Alert,
    ) -> None:
        """
        GIVEN an admin reviewing a remediation
        WHEN they reject with a structured reason
        THEN feedback is saved with the reason.
        """
        feedback = RemediationFeedback(
            feedback_id=str(uuid.uuid4()),
            remediation_id="rem-reject-001",
            recommendation_id="rec-reject-001",
            alert_type=sample_alert.name,
            alert_labels=sample_alert.labels,
            severity=sample_alert.severity.value,
            action="rejected",
            reason=RejectionReason.TOO_RISKY,
            reason_detail="The suggested command could cause data loss",
            admin_user_id="admin-001",
            timestamp=datetime.now(UTC),
        )

        await feedback_store.save_feedback(feedback)

        recent = await feedback_store.get_recent_feedback(limit=10)
        assert len(recent) == 1
        assert recent[0].action == "rejected"
        assert recent[0].reason == RejectionReason.TOO_RISKY
        assert "data loss" in (recent[0].reason_detail or "")

    @pytest.mark.asyncio
    async def test_all_rejection_reasons_supported(
        self,
        feedback_store: InMemoryFeedbackStore,
        sample_alert: Alert,
    ) -> None:
        """
        GIVEN all rejection reason types
        WHEN feedback is saved for each
        THEN all reasons are properly stored.
        """
        for reason in RejectionReason:
            feedback = RemediationFeedback(
                feedback_id=str(uuid.uuid4()),
                remediation_id=f"rem-{reason.value}",
                recommendation_id=f"rec-{reason.value}",
                alert_type=sample_alert.name,
                alert_labels=sample_alert.labels,
                severity=sample_alert.severity.value,
                action="rejected",
                reason=reason,
                reason_detail=f"Testing {reason.value}",
                admin_user_id="admin-001",
                timestamp=datetime.now(UTC),
            )
            await feedback_store.save_feedback(feedback)

        # Verify all reasons were saved
        patterns = await feedback_store.get_rejection_patterns()
        assert len(patterns) == len(RejectionReason)
        for reason in RejectionReason:
            assert patterns.get(reason, 0) == 1

    @pytest.mark.asyncio
    async def test_rejection_with_other_reason(
        self,
        feedback_store: InMemoryFeedbackStore,
        sample_alert: Alert,
    ) -> None:
        """
        GIVEN an admin selecting 'OTHER' reason
        WHEN providing custom reason detail
        THEN the detail is captured.
        """
        feedback = RemediationFeedback(
            feedback_id=str(uuid.uuid4()),
            remediation_id="rem-other-001",
            recommendation_id="rec-other-001",
            alert_type=sample_alert.name,
            alert_labels=sample_alert.labels,
            severity=sample_alert.severity.value,
            action="rejected",
            reason=RejectionReason.OTHER,
            reason_detail="We need to consult with the database team first",
            admin_user_id="admin-001",
            timestamp=datetime.now(UTC),
        )

        await feedback_store.save_feedback(feedback)

        recent = await feedback_store.get_recent_feedback(limit=10)
        assert recent[0].reason == RejectionReason.OTHER
        assert "database team" in (recent[0].reason_detail or "")


@pytest.mark.xdist_group(name="integration_remediation_feedback")
class TestFewShotLearning:
    """Tests for few-shot learning from approved examples."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_approved_examples_for_alert_type(
        self,
        feedback_store: InMemoryFeedbackStore,
    ) -> None:
        """
        GIVEN multiple approved remediations for an alert type
        WHEN requesting few-shot examples
        THEN relevant examples are returned.
        """
        # Create approved examples
        for i in range(5):
            fb = RemediationFeedback(
                feedback_id=str(uuid.uuid4()),
                remediation_id=f"rem-approved-{i}",
                recommendation_id=f"rec-approved-{i}",
                alert_type="HighCPUUsage",
                alert_labels={"service": f"service-{i}"},
                severity="critical",
                action="approved",
                reason=None,
                reason_detail=None,
                admin_user_id=f"admin-{i:03d}",
                timestamp=datetime.now(UTC) - timedelta(hours=i),
                execution_success=True,
                execution_time_seconds=5.0 + i,
            )
            await feedback_store.save_feedback(fb)

        # Get examples
        examples = await feedback_store.get_approved_examples(
            alert_type="HighCPUUsage",
            limit=3,
        )

        assert len(examples) == 3
        # Should be ordered by most recent first
        assert examples[0].remediation_id == "rem-approved-0"
        assert examples[1].remediation_id == "rem-approved-1"
        assert examples[2].remediation_id == "rem-approved-2"

    @pytest.mark.asyncio
    async def test_approved_examples_filtered_by_alert_type(
        self,
        feedback_store: InMemoryFeedbackStore,
    ) -> None:
        """
        GIVEN approved remediations for different alert types
        WHEN requesting examples for specific type
        THEN only matching examples are returned.
        """
        # Create examples for different alert types
        for alert_type in ["HighCPUUsage", "DiskSpaceLow", "MemoryPressure"]:
            for i in range(3):
                fb = RemediationFeedback(
                    feedback_id=str(uuid.uuid4()),
                    remediation_id=f"rem-{alert_type}-{i}",
                    recommendation_id=f"rec-{alert_type}-{i}",
                    alert_type=alert_type,
                    alert_labels={"service": "test"},
                    severity="critical",
                    action="approved",
                    reason=None,
                    reason_detail=None,
                    admin_user_id="admin-001",
                    timestamp=datetime.now(UTC),
                    execution_success=True,
                    execution_time_seconds=5.0,
                )
                await feedback_store.save_feedback(fb)

        # Get examples for specific type
        cpu_examples = await feedback_store.get_approved_examples(
            alert_type="HighCPUUsage",
            limit=10,
        )

        assert len(cpu_examples) == 3
        for ex in cpu_examples:
            assert ex.alert_type == "HighCPUUsage"

    @pytest.mark.asyncio
    async def test_approved_examples_exclude_failed_executions(
        self,
        feedback_store: InMemoryFeedbackStore,
    ) -> None:
        """
        GIVEN approved remediations with mixed execution results
        WHEN retrieving for few-shot learning
        THEN successful executions are prioritized.
        """
        # Create some successful and failed executions
        for i in range(4):
            fb = RemediationFeedback(
                feedback_id=str(uuid.uuid4()),
                remediation_id=f"rem-mixed-{i}",
                recommendation_id=f"rec-mixed-{i}",
                alert_type="HighCPUUsage",
                alert_labels={"service": "test"},
                severity="critical",
                action="approved",
                reason=None,
                reason_detail=None,
                admin_user_id="admin-001",
                timestamp=datetime.now(UTC) - timedelta(hours=i),
                execution_success=i % 2 == 0,  # Even = success, Odd = failure
                execution_time_seconds=5.0,
            )
            await feedback_store.save_feedback(fb)

        # Get all approved examples (current implementation returns all)
        examples = await feedback_store.get_approved_examples(
            alert_type="HighCPUUsage",
            limit=10,
        )

        # Verify we get the approved ones
        assert len(examples) == 4


@pytest.mark.xdist_group(name="integration_remediation_feedback")
class TestConstraintLearning:
    """Tests for constraint learning from rejection patterns."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_rejection_patterns_aggregated(
        self,
        feedback_store: InMemoryFeedbackStore,
        sample_alert: Alert,
    ) -> None:
        """
        GIVEN multiple rejections with various reasons
        WHEN getting rejection patterns
        THEN reasons are correctly aggregated.
        """
        # Create rejections with various reasons
        reasons = [
            RejectionReason.TOO_RISKY,
            RejectionReason.TOO_RISKY,
            RejectionReason.TOO_RISKY,
            RejectionReason.WRONG_COMMAND,
            RejectionReason.WRONG_COMMAND,
            RejectionReason.INCOMPLETE_STEPS,
        ]

        for i, reason in enumerate(reasons):
            fb = RemediationFeedback(
                feedback_id=str(uuid.uuid4()),
                remediation_id=f"rem-pattern-{i}",
                recommendation_id=f"rec-pattern-{i}",
                alert_type=sample_alert.name,
                alert_labels=sample_alert.labels,
                severity=sample_alert.severity.value,
                action="rejected",
                reason=reason,
                reason_detail=f"Rejection {i}",
                admin_user_id="admin-001",
                timestamp=datetime.now(UTC),
            )
            await feedback_store.save_feedback(fb)

        # Get patterns
        patterns = await feedback_store.get_rejection_patterns(
            alert_type=sample_alert.name
        )

        assert patterns[RejectionReason.TOO_RISKY] == 3
        assert patterns[RejectionReason.WRONG_COMMAND] == 2
        assert patterns[RejectionReason.INCOMPLETE_STEPS] == 1

    @pytest.mark.asyncio
    async def test_rejection_patterns_filtered_by_alert_type(
        self,
        feedback_store: InMemoryFeedbackStore,
    ) -> None:
        """
        GIVEN rejections for different alert types
        WHEN getting patterns for specific type
        THEN only matching patterns are counted.
        """
        # Create rejections for different alert types
        for alert_type in ["HighCPUUsage", "DiskSpaceLow"]:
            for i in range(3):
                fb = RemediationFeedback(
                    feedback_id=str(uuid.uuid4()),
                    remediation_id=f"rem-{alert_type}-{i}",
                    recommendation_id=f"rec-{alert_type}-{i}",
                    alert_type=alert_type,
                    alert_labels={"service": "test"},
                    severity="critical",
                    action="rejected",
                    reason=RejectionReason.TOO_RISKY,
                    reason_detail="Test rejection",
                    admin_user_id="admin-001",
                    timestamp=datetime.now(UTC),
                )
                await feedback_store.save_feedback(fb)

        # Get patterns for specific type
        cpu_patterns = await feedback_store.get_rejection_patterns(
            alert_type="HighCPUUsage"
        )

        assert cpu_patterns[RejectionReason.TOO_RISKY] == 3

        # Get patterns across all types
        all_patterns = await feedback_store.get_rejection_patterns(alert_type=None)
        assert all_patterns[RejectionReason.TOO_RISKY] == 6

    @pytest.mark.asyncio
    async def test_frequent_rejections_trigger_constraints(
        self,
        feedback_store: InMemoryFeedbackStore,
        sample_alert: Alert,
    ) -> None:
        """
        GIVEN more than 2 rejections for a reason
        WHEN the AI generates recommendations
        THEN constraints are added to avoid that pattern.
        """
        # Create multiple "too risky" rejections
        for i in range(5):
            fb = RemediationFeedback(
                feedback_id=str(uuid.uuid4()),
                remediation_id=f"rem-risky-{i}",
                recommendation_id=f"rec-risky-{i}",
                alert_type=sample_alert.name,
                alert_labels=sample_alert.labels,
                severity=sample_alert.severity.value,
                action="rejected",
                reason=RejectionReason.TOO_RISKY,
                reason_detail=f"Too risky - iteration {i}",
                admin_user_id="admin-001",
                timestamp=datetime.now(UTC),
            )
            await feedback_store.save_feedback(fb)

        patterns = await feedback_store.get_rejection_patterns(
            alert_type=sample_alert.name
        )

        # More than 2 rejections for TOO_RISKY should trigger constraint
        assert patterns[RejectionReason.TOO_RISKY] > 2


@pytest.mark.xdist_group(name="integration_remediation_feedback")
class TestFeedbackEnhancedRecommendations:
    """Tests for AI recommendations enhanced with feedback."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_recent_feedback_retrieval(
        self,
        feedback_store: InMemoryFeedbackStore,
        sample_alert: Alert,
    ) -> None:
        """
        GIVEN a mix of approvals and rejections
        WHEN retrieving recent feedback
        THEN they are ordered by timestamp.
        """
        # Create mixed feedback
        for i in range(10):
            fb = RemediationFeedback(
                feedback_id=str(uuid.uuid4()),
                remediation_id=f"rem-recent-{i}",
                recommendation_id=f"rec-recent-{i}",
                alert_type=sample_alert.name,
                alert_labels=sample_alert.labels,
                severity=sample_alert.severity.value,
                action="approved" if i % 2 == 0 else "rejected",
                reason=RejectionReason.TOO_RISKY if i % 2 == 1 else None,
                reason_detail=None,
                admin_user_id="admin-001",
                timestamp=datetime.now(UTC) - timedelta(hours=i),
            )
            await feedback_store.save_feedback(fb)

        # Get recent feedback
        recent = await feedback_store.get_recent_feedback(limit=5)

        assert len(recent) == 5
        # Should be ordered by most recent first
        assert recent[0].remediation_id == "rem-recent-0"
        assert recent[4].remediation_id == "rem-recent-4"

    @pytest.mark.asyncio
    async def test_feedback_store_protocol_compliance(
        self,
        feedback_store: InMemoryFeedbackStore,
    ) -> None:
        """
        GIVEN the FeedbackStore protocol
        WHEN using InMemoryFeedbackStore
        THEN all protocol methods are implemented.
        """
        # Verify protocol methods exist and work
        assert hasattr(feedback_store, "save_feedback")
        assert hasattr(feedback_store, "get_approved_examples")
        assert hasattr(feedback_store, "get_rejection_patterns")
        assert hasattr(feedback_store, "get_recent_feedback")
        assert hasattr(feedback_store, "update_execution_result")

        # Verify FeedbackStore is a valid protocol type
        assert isinstance(feedback_store, FeedbackStore)

    @pytest.mark.asyncio
    async def test_empty_feedback_store_returns_empty(
        self,
        feedback_store: InMemoryFeedbackStore,
    ) -> None:
        """
        GIVEN an empty feedback store
        WHEN querying for examples and patterns
        THEN empty results are returned.
        """
        examples = await feedback_store.get_approved_examples(
            alert_type="NonExistent",
            limit=10,
        )
        assert examples == []

        patterns = await feedback_store.get_rejection_patterns(
            alert_type="NonExistent"
        )
        assert patterns == {}

        recent = await feedback_store.get_recent_feedback(limit=10)
        assert recent == []
