"""
RemediationFeedback Tests

TDD tests for the remediation feedback module used for AI model tuning.

Features:
- RejectionReason enum for structured feedback
- RemediationFeedback model for tracking approvals/rejections
- FeedbackStore protocol and in-memory implementation

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import gc
from datetime import UTC, datetime

import pytest

from mcp_server_langgraph.alerts.feedback import (
    InMemoryFeedbackStore,
    RejectionReason,
    RemediationFeedback,
)

pytestmark = pytest.mark.unit

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_feedback() -> RemediationFeedback:
    """Create a sample feedback entry."""
    return RemediationFeedback(
        feedback_id="fb-001",
        remediation_id="rem-001",
        alert_type="HighCPU",
        alert_labels={"service": "api-server", "pod": "api-123"},
        severity="critical",
        recommendation_id="rec-001",
        action="approved",
        reason=None,
        reason_detail=None,
        admin_user_id="admin-001",
        timestamp=datetime.now(UTC),
        execution_success=True,
        execution_time_seconds=15.5,
        admin_notes="Worked well",
    )


@pytest.fixture
def rejection_feedback() -> RemediationFeedback:
    """Create a sample rejection feedback entry."""
    return RemediationFeedback(
        feedback_id="fb-002",
        remediation_id="rem-002",
        alert_type="HighCPU",
        alert_labels={"service": "worker"},
        severity="critical",
        recommendation_id="rec-002",
        action="rejected",
        reason=RejectionReason.TOO_RISKY,
        reason_detail="Command requires sudo access",
        admin_user_id="admin-001",
        timestamp=datetime.now(UTC),
    )


@pytest.fixture
def feedback_store() -> InMemoryFeedbackStore:
    """Create an in-memory feedback store."""
    return InMemoryFeedbackStore()


# =============================================================================
# RejectionReason Enum Tests
# =============================================================================


@pytest.mark.xdist_group(name="alerts_feedback")
class TestRejectionReason:
    """Tests for RejectionReason enum."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_rejection_reason_values(self):
        """Should have all expected rejection reason values."""
        assert RejectionReason.TOO_RISKY.value == "too_risky"
        assert RejectionReason.INCORRECT_DIAGNOSIS.value == "incorrect_diagnosis"
        assert RejectionReason.WRONG_COMMAND.value == "wrong_command"
        assert RejectionReason.INCOMPLETE_STEPS.value == "incomplete_steps"
        assert RejectionReason.NOT_RELEVANT.value == "not_relevant"
        assert RejectionReason.PREFER_MANUAL.value == "prefer_manual"
        assert RejectionReason.OTHER.value == "other"

    def test_rejection_reason_count(self):
        """Should have exactly 7 rejection reasons."""
        assert len(RejectionReason) == 7


# =============================================================================
# RemediationFeedback Model Tests
# =============================================================================


@pytest.mark.xdist_group(name="alerts_feedback")
class TestRemediationFeedback:
    """Tests for RemediationFeedback model."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_approval_feedback(self, sample_feedback: RemediationFeedback):
        """Should create an approval feedback entry."""
        assert sample_feedback.feedback_id == "fb-001"
        assert sample_feedback.action == "approved"
        assert sample_feedback.reason is None
        assert sample_feedback.execution_success is True

    def test_create_rejection_feedback(self, rejection_feedback: RemediationFeedback):
        """Should create a rejection feedback entry."""
        assert rejection_feedback.action == "rejected"
        assert rejection_feedback.reason == RejectionReason.TOO_RISKY
        assert rejection_feedback.reason_detail == "Command requires sudo access"
        assert rejection_feedback.execution_success is None

    def test_feedback_has_timestamp(self, sample_feedback: RemediationFeedback):
        """Should have a timestamp."""
        assert sample_feedback.timestamp is not None
        assert sample_feedback.timestamp.tzinfo is not None

    def test_feedback_alert_labels(self, sample_feedback: RemediationFeedback):
        """Should store alert labels for pattern matching."""
        assert sample_feedback.alert_labels["service"] == "api-server"
        assert sample_feedback.alert_labels["pod"] == "api-123"


# =============================================================================
# InMemoryFeedbackStore Tests
# =============================================================================


@pytest.mark.xdist_group(name="alerts_feedback")
class TestInMemoryFeedbackStore:
    """Tests for in-memory feedback store implementation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_save_feedback(
        self,
        feedback_store: InMemoryFeedbackStore,
        sample_feedback: RemediationFeedback,
    ):
        """Should save feedback entry."""
        await feedback_store.save_feedback(sample_feedback)

        # Verify saved
        result = await feedback_store.get_recent_feedback(limit=10)
        assert len(result) == 1
        assert result[0].feedback_id == "fb-001"

    @pytest.mark.asyncio
    async def test_get_approved_examples(
        self,
        feedback_store: InMemoryFeedbackStore,
        sample_feedback: RemediationFeedback,
        rejection_feedback: RemediationFeedback,
    ):
        """Should return only approved examples for an alert type."""
        await feedback_store.save_feedback(sample_feedback)
        await feedback_store.save_feedback(rejection_feedback)

        # Get approved examples for HighCPU
        result = await feedback_store.get_approved_examples("HighCPU", limit=5)

        assert len(result) == 1
        assert result[0].action == "approved"
        assert result[0].feedback_id == "fb-001"

    @pytest.mark.asyncio
    async def test_get_approved_examples_with_limit(
        self,
        feedback_store: InMemoryFeedbackStore,
    ):
        """Should respect limit parameter."""
        # Create multiple approved feedback entries
        for i in range(10):
            fb = RemediationFeedback(
                feedback_id=f"fb-{i:03d}",
                remediation_id=f"rem-{i:03d}",
                alert_type="HighCPU",
                alert_labels={},
                severity="critical",
                recommendation_id=f"rec-{i:03d}",
                action="approved",
                reason=None,
                reason_detail=None,
                admin_user_id="admin-001",
                timestamp=datetime.now(UTC),
            )
            await feedback_store.save_feedback(fb)

        result = await feedback_store.get_approved_examples("HighCPU", limit=3)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_rejection_patterns(
        self,
        feedback_store: InMemoryFeedbackStore,
    ):
        """Should aggregate rejection reasons."""
        # Create multiple rejections with different reasons
        reasons = [
            RejectionReason.TOO_RISKY,
            RejectionReason.TOO_RISKY,
            RejectionReason.WRONG_COMMAND,
            RejectionReason.TOO_RISKY,
        ]

        for i, reason in enumerate(reasons):
            fb = RemediationFeedback(
                feedback_id=f"fb-{i:03d}",
                remediation_id=f"rem-{i:03d}",
                alert_type="HighCPU",
                alert_labels={},
                severity="critical",
                recommendation_id=f"rec-{i:03d}",
                action="rejected",
                reason=reason,
                reason_detail=None,
                admin_user_id="admin-001",
                timestamp=datetime.now(UTC),
            )
            await feedback_store.save_feedback(fb)

        result = await feedback_store.get_rejection_patterns("HighCPU")

        assert result[RejectionReason.TOO_RISKY] == 3
        assert result[RejectionReason.WRONG_COMMAND] == 1
        assert result.get(RejectionReason.INCORRECT_DIAGNOSIS, 0) == 0

    @pytest.mark.asyncio
    async def test_get_rejection_patterns_all_types(
        self,
        feedback_store: InMemoryFeedbackStore,
    ):
        """Should get rejection patterns across all alert types."""
        # Create rejections for different alert types
        for alert_type in ["HighCPU", "HighMemory"]:
            fb = RemediationFeedback(
                feedback_id=f"fb-{alert_type}",
                remediation_id=f"rem-{alert_type}",
                alert_type=alert_type,
                alert_labels={},
                severity="critical",
                recommendation_id=f"rec-{alert_type}",
                action="rejected",
                reason=RejectionReason.TOO_RISKY,
                reason_detail=None,
                admin_user_id="admin-001",
                timestamp=datetime.now(UTC),
            )
            await feedback_store.save_feedback(fb)

        # Get patterns for all types
        result = await feedback_store.get_rejection_patterns(None)

        assert result[RejectionReason.TOO_RISKY] == 2

    @pytest.mark.asyncio
    async def test_get_recent_feedback(
        self,
        feedback_store: InMemoryFeedbackStore,
        sample_feedback: RemediationFeedback,
        rejection_feedback: RemediationFeedback,
    ):
        """Should return recent feedback entries."""
        await feedback_store.save_feedback(sample_feedback)
        await feedback_store.save_feedback(rejection_feedback)

        result = await feedback_store.get_recent_feedback(limit=10)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_recent_feedback_with_limit(
        self,
        feedback_store: InMemoryFeedbackStore,
    ):
        """Should respect limit parameter for recent feedback."""
        for i in range(20):
            fb = RemediationFeedback(
                feedback_id=f"fb-{i:03d}",
                remediation_id=f"rem-{i:03d}",
                alert_type="HighCPU",
                alert_labels={},
                severity="critical",
                recommendation_id=f"rec-{i:03d}",
                action="approved",
                reason=None,
                reason_detail=None,
                admin_user_id="admin-001",
                timestamp=datetime.now(UTC),
            )
            await feedback_store.save_feedback(fb)

        result = await feedback_store.get_recent_feedback(limit=5)
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_update_execution_result(
        self,
        feedback_store: InMemoryFeedbackStore,
        sample_feedback: RemediationFeedback,
    ):
        """Should update execution result for a feedback entry."""
        # Save feedback without execution result
        sample_feedback.execution_success = None
        sample_feedback.execution_time_seconds = None
        await feedback_store.save_feedback(sample_feedback)

        # Update execution result
        await feedback_store.update_execution_result(
            remediation_id="rem-001",
            success=True,
            execution_time_seconds=25.0,
        )

        # Verify updated
        result = await feedback_store.get_recent_feedback(limit=10)
        assert result[0].execution_success is True
        assert result[0].execution_time_seconds == 25.0
