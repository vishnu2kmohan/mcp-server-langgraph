"""
PostgresFeedbackStore Unit Tests.

TDD tests for the PostgreSQL-backed remediation feedback store.

Features tested:
- Save and retrieve feedback
- Get approved examples for few-shot learning
- Get rejection patterns for constraint learning
- Get recent feedback
- Update execution results

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import gc
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.alerts.feedback import (
    FeedbackStore,
    RejectionReason,
    RemediationFeedback,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.alerts,
]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_feedback() -> RemediationFeedback:
    """Create a sample feedback entry."""
    return RemediationFeedback(
        feedback_id=str(uuid.uuid4()),
        remediation_id=str(uuid.uuid4()),
        recommendation_id=str(uuid.uuid4()),
        alert_type="HighCPU",
        alert_labels={"service": "api-server", "namespace": "production"},
        severity="critical",
        action="approved",
        reason=None,
        reason_detail=None,
        admin_user_id="admin-001",
        timestamp=datetime.now(UTC),
    )


@pytest.fixture
def sample_rejected_feedback() -> RemediationFeedback:
    """Create a sample rejected feedback entry."""
    return RemediationFeedback(
        feedback_id=str(uuid.uuid4()),
        remediation_id=str(uuid.uuid4()),
        recommendation_id=str(uuid.uuid4()),
        alert_type="HighCPU",
        alert_labels={"service": "api-server"},
        severity="critical",
        action="rejected",
        reason=RejectionReason.TOO_RISKY,
        reason_detail="Command could cause data loss",
        admin_user_id="admin-001",
        timestamp=datetime.now(UTC),
    )


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock async session."""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    # session.add() is synchronous, not async - use MagicMock to prevent warnings
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_session_maker(mock_session: AsyncMock) -> MagicMock:
    """Create a mock session maker."""
    session_maker = MagicMock()
    session_maker.return_value = mock_session
    return session_maker


# =============================================================================
# PostgresFeedbackStore Class Existence Tests
# =============================================================================


@pytest.mark.xdist_group(name="postgres_feedback_store")
class TestPostgresFeedbackStoreExists:
    """Tests for PostgresFeedbackStore class existence."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_postgres_feedback_store_class_exists(self) -> None:
        """
        GIVEN the feedback module
        WHEN importing PostgresFeedbackStore
        THEN should export the class.
        """
        from mcp_server_langgraph.alerts.feedback import (
            PostgresFeedbackStore,
        )

        assert PostgresFeedbackStore is not None

    def test_postgres_feedback_store_implements_protocol(
        self, mock_session_maker: MagicMock
    ) -> None:
        """
        GIVEN a PostgresFeedbackStore instance
        WHEN checking protocol implementation
        THEN should implement FeedbackStore protocol.
        """
        from mcp_server_langgraph.alerts.feedback import (
            PostgresFeedbackStore,
        )

        store = PostgresFeedbackStore(mock_session_maker)
        assert isinstance(store, FeedbackStore)


# =============================================================================
# PostgresFeedbackStore CRUD Tests
# =============================================================================


@pytest.mark.xdist_group(name="postgres_feedback_store")
class TestPostgresFeedbackStoreCRUD:
    """Tests for CRUD operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_save_feedback(
        self,
        mock_session_maker: MagicMock,
        mock_session: AsyncMock,
        sample_feedback: RemediationFeedback,
    ) -> None:
        """
        GIVEN a PostgresFeedbackStore
        WHEN saving feedback
        THEN should execute insert statement.
        """
        from mcp_server_langgraph.alerts.feedback import (
            PostgresFeedbackStore,
        )

        store = PostgresFeedbackStore(mock_session_maker)
        await store.save_feedback(sample_feedback)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_approved_examples(
        self,
        mock_session_maker: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """
        GIVEN a PostgresFeedbackStore with approved feedback
        WHEN getting approved examples for an alert type
        THEN should return list of approved feedback.
        """
        from mcp_server_langgraph.alerts.feedback import (
            FeedbackRecord,
            PostgresFeedbackStore,
        )

        # Create mock records
        mock_record = MagicMock(spec=FeedbackRecord)
        mock_record.feedback_id = str(uuid.uuid4())
        mock_record.remediation_id = str(uuid.uuid4())
        mock_record.recommendation_id = str(uuid.uuid4())
        mock_record.alert_type = "HighCPU"
        mock_record.alert_labels = {"service": "api-server"}
        mock_record.severity = "critical"
        mock_record.action = "approved"
        mock_record.reason = None
        mock_record.reason_detail = None
        mock_record.admin_user_id = "admin-001"
        mock_record.timestamp = datetime.now(UTC)
        mock_record.execution_success = True
        mock_record.execution_time_seconds = 2.5
        mock_record.admin_notes = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_record]
        mock_session.execute.return_value = mock_result

        store = PostgresFeedbackStore(mock_session_maker)
        examples = await store.get_approved_examples("HighCPU", limit=5)

        assert len(examples) == 1
        assert examples[0].action == "approved"
        assert examples[0].alert_type == "HighCPU"

    @pytest.mark.asyncio
    async def test_get_rejection_patterns(
        self,
        mock_session_maker: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """
        GIVEN a PostgresFeedbackStore with rejected feedback
        WHEN getting rejection patterns
        THEN should return dict of reason counts.
        """
        from mcp_server_langgraph.alerts.feedback import (
            FeedbackRecord,
            PostgresFeedbackStore,
        )

        # Create mock records with rejection reasons
        mock_records = []
        for reason in [RejectionReason.TOO_RISKY, RejectionReason.TOO_RISKY, RejectionReason.WRONG_COMMAND]:
            mock_record = MagicMock(spec=FeedbackRecord)
            mock_record.reason = reason.value
            mock_records.append(mock_record)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_records
        mock_session.execute.return_value = mock_result

        store = PostgresFeedbackStore(mock_session_maker)
        patterns = await store.get_rejection_patterns()

        assert patterns[RejectionReason.TOO_RISKY] == 2
        assert patterns[RejectionReason.WRONG_COMMAND] == 1

    @pytest.mark.asyncio
    async def test_get_recent_feedback(
        self,
        mock_session_maker: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """
        GIVEN a PostgresFeedbackStore with multiple feedback entries
        WHEN getting recent feedback
        THEN should return list ordered by timestamp.
        """
        from mcp_server_langgraph.alerts.feedback import (
            FeedbackRecord,
            PostgresFeedbackStore,
        )

        # Create mock records
        records = []
        for i in range(3):
            mock_record = MagicMock(spec=FeedbackRecord)
            mock_record.feedback_id = str(uuid.uuid4())
            mock_record.remediation_id = str(uuid.uuid4())
            mock_record.recommendation_id = str(uuid.uuid4())
            mock_record.alert_type = f"Alert{i}"
            mock_record.alert_labels = {}
            mock_record.severity = "warning"
            mock_record.action = "approved"
            mock_record.reason = None
            mock_record.reason_detail = None
            mock_record.admin_user_id = "admin"
            mock_record.timestamp = datetime.now(UTC) - timedelta(hours=i)
            mock_record.execution_success = None
            mock_record.execution_time_seconds = None
            mock_record.admin_notes = None
            records.append(mock_record)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = records
        mock_session.execute.return_value = mock_result

        store = PostgresFeedbackStore(mock_session_maker)
        feedback = await store.get_recent_feedback(limit=10)

        assert len(feedback) == 3

    @pytest.mark.asyncio
    async def test_update_execution_result(
        self,
        mock_session_maker: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """
        GIVEN a PostgresFeedbackStore
        WHEN updating execution result
        THEN should update the record.
        """
        from mcp_server_langgraph.alerts.feedback import (
            FeedbackRecord,
            PostgresFeedbackStore,
        )

        # Mock existing record
        mock_record = MagicMock(spec=FeedbackRecord)
        mock_record.remediation_id = "rem-001"
        mock_record.execution_success = None
        mock_record.execution_time_seconds = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_record
        mock_session.execute.return_value = mock_result

        store = PostgresFeedbackStore(mock_session_maker)
        await store.update_execution_result(
            remediation_id="rem-001",
            success=True,
            execution_time_seconds=5.2,
        )

        assert mock_record.execution_success is True
        assert mock_record.execution_time_seconds == 5.2
        mock_session.commit.assert_called_once()


# =============================================================================
# PostgresFeedbackStore Edge Cases
# =============================================================================


@pytest.mark.xdist_group(name="postgres_feedback_store")
class TestPostgresFeedbackStoreEdgeCases:
    """Tests for edge cases and error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_approved_examples_empty(
        self,
        mock_session_maker: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """
        GIVEN a PostgresFeedbackStore with no approved feedback
        WHEN getting approved examples
        THEN should return empty list.
        """
        from mcp_server_langgraph.alerts.feedback import (
            PostgresFeedbackStore,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        store = PostgresFeedbackStore(mock_session_maker)
        examples = await store.get_approved_examples("NonExistentAlert")

        assert examples == []

    @pytest.mark.asyncio
    async def test_get_rejection_patterns_by_alert_type(
        self,
        mock_session_maker: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """
        GIVEN a PostgresFeedbackStore
        WHEN getting rejection patterns for a specific alert type
        THEN should filter by alert type.
        """
        from mcp_server_langgraph.alerts.feedback import (
            FeedbackRecord,
            PostgresFeedbackStore,
        )

        mock_record = MagicMock(spec=FeedbackRecord)
        mock_record.reason = RejectionReason.INCOMPLETE_STEPS.value

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_record]
        mock_session.execute.return_value = mock_result

        store = PostgresFeedbackStore(mock_session_maker)
        patterns = await store.get_rejection_patterns(alert_type="HighCPU")

        assert RejectionReason.INCOMPLETE_STEPS in patterns

    @pytest.mark.asyncio
    async def test_update_execution_result_not_found(
        self,
        mock_session_maker: MagicMock,
        mock_session: AsyncMock,
    ) -> None:
        """
        GIVEN a PostgresFeedbackStore
        WHEN updating execution result for non-existent remediation
        THEN should handle gracefully.
        """
        from mcp_server_langgraph.alerts.feedback import (
            PostgresFeedbackStore,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        store = PostgresFeedbackStore(mock_session_maker)

        # Should not raise
        await store.update_execution_result(
            remediation_id="nonexistent",
            success=True,
            execution_time_seconds=1.0,
        )

    @pytest.mark.asyncio
    async def test_save_rejected_feedback(
        self,
        mock_session_maker: MagicMock,
        mock_session: AsyncMock,
        sample_rejected_feedback: RemediationFeedback,
    ) -> None:
        """
        GIVEN a PostgresFeedbackStore
        WHEN saving rejected feedback with reason
        THEN should persist the rejection reason.
        """
        from mcp_server_langgraph.alerts.feedback import (
            PostgresFeedbackStore,
        )

        store = PostgresFeedbackStore(mock_session_maker)
        await store.save_feedback(sample_rejected_feedback)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
