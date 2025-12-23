"""
RemediationApprovalQueue Unit Tests.

TDD tests for the remediation approval queue system.

Features tested:
- Queue remediation steps from AI recommendations
- List pending remediations
- Approve remediations
- Reject remediations
- Get remediation by ID
- Get history with pagination
- Approve/reject with feedback for AI learning
- Global queue singleton management

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import gc
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from mcp_server_langgraph.alerts.approval_queue import (
    RemediationApprovalQueue,
    RemediationRequest,
    get_approval_queue,
    set_approval_queue,
)
from mcp_server_langgraph.alerts.feedback import (
    InMemoryFeedbackStore,
    RejectionReason,
)
from mcp_server_langgraph.core.interrupts.approval import ApprovalStatus

pytestmark = [
    pytest.mark.unit,
    pytest.mark.alerts,
]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def queue() -> RemediationApprovalQueue:
    """Create a fresh approval queue for testing."""
    return RemediationApprovalQueue()


@pytest.fixture
def feedback_store() -> InMemoryFeedbackStore:
    """Create an in-memory feedback store for testing."""
    return InMemoryFeedbackStore()


@pytest.fixture
def sample_recommendation() -> MagicMock:
    """Create a sample AI recommendation with remediation steps."""
    recommendation = MagicMock()
    recommendation.recommendation_id = str(uuid.uuid4())
    recommendation.remediation_steps = [
        {
            "step_number": 1,
            "action": "identify",
            "description": "Identify top CPU-consuming processes",
            "command": "top -b -n 1 | head -20",
            "requires_approval": False,
            "risk_level": "low",
        },
        {
            "step_number": 2,
            "action": "scale",
            "description": "Scale up the deployment",
            "command": "kubectl scale deployment api-server --replicas=5",
            "requires_approval": True,
            "risk_level": "medium",
        },
        {
            "step_number": 3,
            "action": "restart",
            "description": "Restart the pod if scaling doesn't help",
            "command": "kubectl delete pod api-server-xyz",
            "requires_approval": True,
            "risk_level": "high",
        },
    ]
    return recommendation


@pytest.fixture(autouse=True)
def reset_global_queue() -> None:
    """Reset global queue before each test."""
    set_approval_queue(None)
    yield
    set_approval_queue(None)


# =============================================================================
# RemediationRequest Model Tests
# =============================================================================


@pytest.mark.xdist_group(name="alerts_approval_queue")
class TestRemediationRequest:
    """Tests for the RemediationRequest model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_remediation_request(self) -> None:
        """Should create a remediation request with all required fields."""
        request = RemediationRequest(
            remediation_id="rem-001",
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            step_number=1,
            action="scale",
            description="Scale up deployment",
            command="kubectl scale deployment --replicas=5",
            risk_level="medium",
            status=ApprovalStatus.PENDING,
            requested_at=datetime.now(UTC).isoformat(),
        )

        assert request.remediation_id == "rem-001"
        assert request.alert_id == "alert-001"
        assert request.alert_name == "HighCPU"
        assert request.status == ApprovalStatus.PENDING
        assert request.approved_by is None
        assert request.approved_at is None

    def test_remediation_request_defaults(self) -> None:
        """Should use default values for optional fields."""
        request = RemediationRequest(
            remediation_id="rem-001",
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            step_number=1,
            action="scale",
            description="Scale up deployment",
            requested_at=datetime.now(UTC).isoformat(),
        )

        assert request.risk_level == "medium"
        assert request.status == ApprovalStatus.PENDING
        assert request.command is None
        assert request.recommendation_id is None


# =============================================================================
# RemediationApprovalQueue Tests
# =============================================================================


@pytest.mark.xdist_group(name="alerts_approval_queue")
class TestRemediationApprovalQueueInit:
    """Tests for queue initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_queue_initialization(self) -> None:
        """Should initialize with empty remediations dict."""
        queue = RemediationApprovalQueue()
        assert queue._remediations == {}

    @pytest.mark.asyncio
    async def test_queue_thread_safety(self) -> None:
        """Should have a lock for thread safety."""
        queue = RemediationApprovalQueue()
        assert queue._lock is not None


@pytest.mark.xdist_group(name="alerts_approval_queue")
class TestQueueRemediation:
    """Tests for queueing remediations from AI recommendations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_queue_remediations_from_recommendation(
        self, queue: RemediationApprovalQueue, sample_recommendation: MagicMock
    ) -> None:
        """Should queue only steps that require approval."""
        result = await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            recommendation=sample_recommendation,
        )

        # Only steps 2 and 3 require approval
        assert len(result) == 2
        assert result[0].step_number == 2
        assert result[1].step_number == 3

    @pytest.mark.asyncio
    async def test_queue_remediation_assigns_unique_ids(
        self, queue: RemediationApprovalQueue, sample_recommendation: MagicMock
    ) -> None:
        """Should assign unique IDs to each remediation."""
        result = await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            recommendation=sample_recommendation,
        )

        ids = [r.remediation_id for r in result]
        assert len(ids) == len(set(ids))  # All unique

    @pytest.mark.asyncio
    async def test_queue_remediation_stores_alert_info(
        self, queue: RemediationApprovalQueue, sample_recommendation: MagicMock
    ) -> None:
        """Should store alert information in remediation request."""
        result = await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            recommendation=sample_recommendation,
        )

        for request in result:
            assert request.alert_id == "alert-001"
            assert request.alert_name == "HighCPU"
            assert request.severity == "critical"
            assert request.status == ApprovalStatus.PENDING

    @pytest.mark.asyncio
    async def test_queue_remediation_stores_step_details(
        self, queue: RemediationApprovalQueue, sample_recommendation: MagicMock
    ) -> None:
        """Should store step details from recommendation."""
        result = await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            recommendation=sample_recommendation,
        )

        # Check step 2 (scale)
        assert result[0].action == "scale"
        assert result[0].description == "Scale up the deployment"
        assert result[0].command == "kubectl scale deployment api-server --replicas=5"
        assert result[0].risk_level == "medium"

    @pytest.mark.asyncio
    async def test_queue_remediation_links_recommendation_id(
        self, queue: RemediationApprovalQueue, sample_recommendation: MagicMock
    ) -> None:
        """Should link recommendation ID for traceability."""
        result = await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            recommendation=sample_recommendation,
        )

        for request in result:
            assert request.recommendation_id == sample_recommendation.recommendation_id

    @pytest.mark.asyncio
    async def test_queue_remediation_empty_when_no_approval_needed(self, queue: RemediationApprovalQueue) -> None:
        """Should return empty list when no steps require approval."""
        recommendation = MagicMock()
        recommendation.recommendation_id = str(uuid.uuid4())
        recommendation.remediation_steps = [
            {
                "step_number": 1,
                "action": "identify",
                "description": "Safe diagnostic step",
                "command": "echo hello",
                "requires_approval": False,
                "risk_level": "low",
            },
        ]

        result = await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            recommendation=recommendation,
        )

        assert len(result) == 0


@pytest.mark.xdist_group(name="alerts_approval_queue")
class TestListPending:
    """Tests for listing pending remediations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_pending_empty(self, queue: RemediationApprovalQueue) -> None:
        """Should return empty list when no pending remediations."""
        result = await queue.list_pending()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_pending_returns_pending_only(
        self, queue: RemediationApprovalQueue, sample_recommendation: MagicMock
    ) -> None:
        """Should return only pending remediations."""
        # Queue some remediations
        queued = await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            recommendation=sample_recommendation,
        )

        # Approve one
        await queue.approve(queued[0].remediation_id, "admin@example.com")

        # List pending
        pending = await queue.list_pending()

        assert len(pending) == 1
        assert pending[0].remediation_id == queued[1].remediation_id
        assert pending[0].status == ApprovalStatus.PENDING


@pytest.mark.xdist_group(name="alerts_approval_queue")
class TestGetRemediation:
    """Tests for getting a specific remediation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_remediation_found(self, queue: RemediationApprovalQueue, sample_recommendation: MagicMock) -> None:
        """Should return remediation when found."""
        queued = await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            recommendation=sample_recommendation,
        )

        result = await queue.get_remediation(queued[0].remediation_id)
        assert result is not None
        assert result.remediation_id == queued[0].remediation_id

    @pytest.mark.asyncio
    async def test_get_remediation_not_found(self, queue: RemediationApprovalQueue) -> None:
        """Should return None when remediation not found."""
        result = await queue.get_remediation("nonexistent-id")
        assert result is None


@pytest.mark.xdist_group(name="alerts_approval_queue")
class TestApprove:
    """Tests for approving remediations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_approve_pending_remediation(
        self, queue: RemediationApprovalQueue, sample_recommendation: MagicMock
    ) -> None:
        """Should approve a pending remediation."""
        queued = await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            recommendation=sample_recommendation,
        )

        result = await queue.approve(queued[0].remediation_id, "admin@example.com")

        assert result.status == ApprovalStatus.APPROVED
        assert result.approved_by == "admin@example.com"
        assert result.approved_at is not None

    @pytest.mark.asyncio
    async def test_approve_not_found(self, queue: RemediationApprovalQueue) -> None:
        """Should raise KeyError when remediation not found."""
        with pytest.raises(KeyError, match="not found"):
            await queue.approve("nonexistent-id", "admin@example.com")

    @pytest.mark.asyncio
    async def test_approve_already_approved(self, queue: RemediationApprovalQueue, sample_recommendation: MagicMock) -> None:
        """Should raise ValueError when remediation already approved."""
        queued = await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            recommendation=sample_recommendation,
        )

        await queue.approve(queued[0].remediation_id, "admin@example.com")

        with pytest.raises(ValueError, match="not pending"):
            await queue.approve(queued[0].remediation_id, "admin@example.com")


@pytest.mark.xdist_group(name="alerts_approval_queue")
class TestReject:
    """Tests for rejecting remediations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_reject_pending_remediation(self, queue: RemediationApprovalQueue, sample_recommendation: MagicMock) -> None:
        """Should reject a pending remediation."""
        queued = await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            recommendation=sample_recommendation,
        )

        result = await queue.reject(
            queued[0].remediation_id,
            "admin@example.com",
            "Too risky for production",
        )

        assert result.status == ApprovalStatus.REJECTED
        assert result.approved_by == "admin@example.com"
        assert result.approved_at is not None
        assert result.reason == "Too risky for production"

    @pytest.mark.asyncio
    async def test_reject_without_reason(self, queue: RemediationApprovalQueue, sample_recommendation: MagicMock) -> None:
        """Should reject without requiring a reason."""
        queued = await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            recommendation=sample_recommendation,
        )

        result = await queue.reject(queued[0].remediation_id, "admin@example.com")

        assert result.status == ApprovalStatus.REJECTED
        assert result.reason is None

    @pytest.mark.asyncio
    async def test_reject_not_found(self, queue: RemediationApprovalQueue) -> None:
        """Should raise KeyError when remediation not found."""
        with pytest.raises(KeyError, match="not found"):
            await queue.reject("nonexistent-id", "admin@example.com")

    @pytest.mark.asyncio
    async def test_reject_already_rejected(self, queue: RemediationApprovalQueue, sample_recommendation: MagicMock) -> None:
        """Should raise ValueError when remediation already rejected."""
        queued = await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            recommendation=sample_recommendation,
        )

        await queue.reject(queued[0].remediation_id, "admin@example.com")

        with pytest.raises(ValueError, match="not pending"):
            await queue.reject(queued[0].remediation_id, "admin@example.com")


@pytest.mark.xdist_group(name="alerts_approval_queue")
class TestGetHistory:
    """Tests for getting remediation history."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_history_empty(self, queue: RemediationApprovalQueue) -> None:
        """Should return empty list when no completed remediations."""
        result = await queue.get_history()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_history_includes_approved_and_rejected(
        self, queue: RemediationApprovalQueue, sample_recommendation: MagicMock
    ) -> None:
        """Should include both approved and rejected remediations."""
        queued = await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            recommendation=sample_recommendation,
        )

        # Approve one, reject the other
        await queue.approve(queued[0].remediation_id, "admin@example.com")
        await queue.reject(queued[1].remediation_id, "admin@example.com", "Too risky")

        history = await queue.get_history()

        assert len(history) == 2
        statuses = {h.status for h in history}
        assert ApprovalStatus.APPROVED in statuses
        assert ApprovalStatus.REJECTED in statuses

    @pytest.mark.asyncio
    async def test_get_history_excludes_pending(
        self, queue: RemediationApprovalQueue, sample_recommendation: MagicMock
    ) -> None:
        """Should exclude pending remediations from history."""
        await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            recommendation=sample_recommendation,
        )

        history = await queue.get_history()

        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_get_history_respects_limit(self, queue: RemediationApprovalQueue) -> None:
        """Should respect limit parameter."""
        # Create many remediations
        for i in range(10):
            recommendation = MagicMock()
            recommendation.recommendation_id = str(uuid.uuid4())
            recommendation.remediation_steps = [
                {
                    "step_number": 1,
                    "action": f"action-{i}",
                    "description": f"Description {i}",
                    "requires_approval": True,
                }
            ]
            queued = await queue.queue_remediation(
                alert_id=f"alert-{i:03d}",
                alert_name="TestAlert",
                severity="warning",
                recommendation=recommendation,
            )
            await queue.approve(queued[0].remediation_id, "admin@example.com")

        history = await queue.get_history(limit=5)
        assert len(history) == 5

    @pytest.mark.asyncio
    async def test_get_history_respects_offset(self, queue: RemediationApprovalQueue) -> None:
        """Should respect offset parameter for pagination."""
        # Create many remediations
        for i in range(10):
            recommendation = MagicMock()
            recommendation.recommendation_id = str(uuid.uuid4())
            recommendation.remediation_steps = [
                {
                    "step_number": 1,
                    "action": f"action-{i}",
                    "description": f"Description {i}",
                    "requires_approval": True,
                }
            ]
            queued = await queue.queue_remediation(
                alert_id=f"alert-{i:03d}",
                alert_name="TestAlert",
                severity="warning",
                recommendation=recommendation,
            )
            await queue.approve(queued[0].remediation_id, "admin@example.com")

        full_history = await queue.get_history(limit=100)
        offset_history = await queue.get_history(limit=5, offset=3)

        assert len(offset_history) == 5
        # Verify offset worked (compare IDs)
        assert offset_history[0].remediation_id == full_history[3].remediation_id


@pytest.mark.xdist_group(name="alerts_approval_queue")
class TestApproveWithFeedback:
    """Tests for approving with feedback for AI learning."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_approve_with_feedback_saves_to_store(
        self,
        queue: RemediationApprovalQueue,
        sample_recommendation: MagicMock,
        feedback_store: InMemoryFeedbackStore,
    ) -> None:
        """Should save approval feedback to the store."""
        queued = await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            recommendation=sample_recommendation,
        )

        result = await queue.approve_with_feedback(
            queued[0].remediation_id,
            "admin@example.com",
            feedback_store,
        )

        assert result.status == ApprovalStatus.APPROVED

        # Verify feedback was saved
        recent = await feedback_store.get_recent_feedback(limit=10)
        assert len(recent) == 1
        assert recent[0].action == "approved"
        assert recent[0].remediation_id == queued[0].remediation_id
        assert recent[0].admin_user_id == "admin@example.com"

    @pytest.mark.asyncio
    async def test_approve_with_feedback_links_recommendation(
        self,
        queue: RemediationApprovalQueue,
        sample_recommendation: MagicMock,
        feedback_store: InMemoryFeedbackStore,
    ) -> None:
        """Should link the original recommendation ID in feedback."""
        queued = await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            recommendation=sample_recommendation,
        )

        await queue.approve_with_feedback(
            queued[0].remediation_id,
            "admin@example.com",
            feedback_store,
        )

        recent = await feedback_store.get_recent_feedback(limit=10)
        assert recent[0].recommendation_id == sample_recommendation.recommendation_id


@pytest.mark.xdist_group(name="alerts_approval_queue")
class TestRejectWithFeedback:
    """Tests for rejecting with structured feedback for AI learning."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_reject_with_feedback_saves_to_store(
        self,
        queue: RemediationApprovalQueue,
        sample_recommendation: MagicMock,
        feedback_store: InMemoryFeedbackStore,
    ) -> None:
        """Should save rejection feedback with structured reason."""
        queued = await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            recommendation=sample_recommendation,
        )

        result = await queue.reject_with_feedback(
            queued[0].remediation_id,
            "admin@example.com",
            RejectionReason.TOO_RISKY,
            feedback_store,
            reason_detail="Command could cause data loss",
        )

        assert result.status == ApprovalStatus.REJECTED

        # Verify feedback was saved
        recent = await feedback_store.get_recent_feedback(limit=10)
        assert len(recent) == 1
        assert recent[0].action == "rejected"
        assert recent[0].reason == RejectionReason.TOO_RISKY
        assert recent[0].reason_detail == "Command could cause data loss"

    @pytest.mark.asyncio
    async def test_reject_with_feedback_updates_rejection_patterns(
        self,
        queue: RemediationApprovalQueue,
        sample_recommendation: MagicMock,
        feedback_store: InMemoryFeedbackStore,
    ) -> None:
        """Should contribute to rejection patterns for constraint learning."""
        queued = await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            recommendation=sample_recommendation,
        )

        await queue.reject_with_feedback(
            queued[0].remediation_id,
            "admin@example.com",
            RejectionReason.WRONG_COMMAND,
            feedback_store,
        )

        patterns = await feedback_store.get_rejection_patterns(alert_type="HighCPU")
        assert patterns.get(RejectionReason.WRONG_COMMAND, 0) == 1

    @pytest.mark.asyncio
    async def test_reject_with_feedback_formats_reason_string(
        self,
        queue: RemediationApprovalQueue,
        sample_recommendation: MagicMock,
        feedback_store: InMemoryFeedbackStore,
    ) -> None:
        """Should format the reason string in the remediation request."""
        queued = await queue.queue_remediation(
            alert_id="alert-001",
            alert_name="HighCPU",
            severity="critical",
            recommendation=sample_recommendation,
        )

        result = await queue.reject_with_feedback(
            queued[0].remediation_id,
            "admin@example.com",
            RejectionReason.TOO_RISKY,
            feedback_store,
            reason_detail="Needs review",
        )

        # The reason field should contain formatted string
        assert "too_risky" in result.reason
        assert "Needs review" in result.reason


@pytest.mark.xdist_group(name="alerts_approval_queue")
class TestGlobalQueueManagement:
    """Tests for global queue singleton management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_approval_queue_creates_singleton(self) -> None:
        """Should create singleton on first call."""
        queue1 = get_approval_queue()
        queue2 = get_approval_queue()

        assert queue1 is queue2

    def test_set_approval_queue_replaces_singleton(self) -> None:
        """Should replace the singleton queue."""
        original = get_approval_queue()
        new_queue = RemediationApprovalQueue()

        set_approval_queue(new_queue)

        current = get_approval_queue()
        assert current is new_queue
        assert current is not original

    def test_set_approval_queue_to_none_resets(self) -> None:
        """Should reset to None for new creation."""
        original = get_approval_queue()

        set_approval_queue(None)

        new_queue = get_approval_queue()
        assert new_queue is not original
