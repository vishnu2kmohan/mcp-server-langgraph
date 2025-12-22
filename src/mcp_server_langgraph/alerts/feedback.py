"""
Remediation Feedback Module

Models and storage for tracking remediation approval/rejection feedback.
Used for AI model tuning with few-shot learning and constraint learning.

Features:
- RejectionReason enum for structured feedback
- RemediationFeedback dataclass for tracking approvals/rejections
- FeedbackStore protocol for persistence abstraction
- InMemoryFeedbackStore for testing

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from sqlalchemy import JSON, DateTime, Float, String, Text, Boolean, select
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

Base = declarative_base()


# =============================================================================
# Enums
# =============================================================================


class RejectionReason(str, Enum):
    """Structured rejection reasons for AI learning.

    These categories help the AI learn from human feedback:
    - TOO_RISKY: Avoid high-risk commands
    - INCORRECT_DIAGNOSIS: Focus on accurate root cause analysis
    - WRONG_COMMAND: Double-check command syntax
    - INCOMPLETE_STEPS: Provide complete step-by-step instructions
    - NOT_RELEVANT: Ensure remediation matches alert context
    - PREFER_MANUAL: Some situations need human judgment
    - OTHER: Free-form reason for edge cases
    """

    TOO_RISKY = "too_risky"
    INCORRECT_DIAGNOSIS = "incorrect_diagnosis"
    WRONG_COMMAND = "wrong_command"
    INCOMPLETE_STEPS = "incomplete_steps"
    NOT_RELEVANT = "not_relevant"
    PREFER_MANUAL = "prefer_manual"
    OTHER = "other"


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class RemediationFeedback:
    """Feedback on a remediation recommendation.

    Tracks both approvals and rejections with structured reasons,
    enabling the AI to learn from human feedback over time.
    """

    # Identification
    feedback_id: str
    remediation_id: str
    recommendation_id: str

    # Alert context for pattern matching
    alert_type: str
    alert_labels: dict[str, str]
    severity: str

    # Feedback data
    action: str  # "approved" | "rejected"
    reason: RejectionReason | None
    reason_detail: str | None
    admin_user_id: str
    timestamp: datetime

    # Post-execution feedback (for approved remediations)
    execution_success: bool | None = None
    execution_time_seconds: float | None = None
    admin_notes: str | None = None


# =============================================================================
# Storage Protocol
# =============================================================================


@runtime_checkable
class FeedbackStore(Protocol):
    """Protocol for feedback persistence.

    Implementations can use PostgreSQL, Redis, or any other storage backend.
    """

    async def save_feedback(self, feedback: RemediationFeedback) -> None:
        """Save a feedback entry."""
        ...

    async def get_approved_examples(
        self,
        alert_type: str,
        limit: int = 5,
    ) -> list[RemediationFeedback]:
        """Get approved examples for few-shot learning.

        Returns successful remediations for the given alert type,
        ordered by most recent first.
        """
        ...

    async def get_rejection_patterns(
        self,
        alert_type: str | None = None,
    ) -> dict[RejectionReason, int]:
        """Get rejection reason counts for constraint learning.

        If alert_type is None, returns patterns across all alert types.
        """
        ...

    async def get_recent_feedback(
        self,
        limit: int = 100,
    ) -> list[RemediationFeedback]:
        """Get recent feedback entries.

        Returns feedback ordered by timestamp (most recent first).
        """
        ...

    async def update_execution_result(
        self,
        remediation_id: str,
        success: bool,
        execution_time_seconds: float,
    ) -> None:
        """Update the execution result for a feedback entry.

        Called after a remediation is executed to record the outcome.
        """
        ...


# =============================================================================
# In-Memory Implementation (for testing)
# =============================================================================


class InMemoryFeedbackStore:
    """In-memory feedback store for testing.

    Production code should use PostgresFeedbackStore instead.
    """

    def __init__(self) -> None:
        """Initialize empty feedback store."""
        self._feedback: list[RemediationFeedback] = []

    async def save_feedback(self, feedback: RemediationFeedback) -> None:
        """Save feedback entry to memory."""
        self._feedback.append(feedback)

    async def get_approved_examples(
        self,
        alert_type: str,
        limit: int = 5,
    ) -> list[RemediationFeedback]:
        """Get approved examples for the given alert type."""
        approved = [
            fb
            for fb in self._feedback
            if fb.action == "approved" and fb.alert_type == alert_type
        ]

        # Sort by timestamp (most recent first) and limit
        approved.sort(key=lambda fb: fb.timestamp, reverse=True)
        return approved[:limit]

    async def get_rejection_patterns(
        self,
        alert_type: str | None = None,
    ) -> dict[RejectionReason, int]:
        """Get rejection reason counts."""
        counts: dict[RejectionReason, int] = defaultdict(int)

        for fb in self._feedback:
            if fb.action != "rejected" or fb.reason is None:
                continue

            if alert_type is None or fb.alert_type == alert_type:
                counts[fb.reason] += 1

        return dict(counts)

    async def get_recent_feedback(
        self,
        limit: int = 100,
    ) -> list[RemediationFeedback]:
        """Get recent feedback entries."""
        # Sort by timestamp (most recent first)
        sorted_feedback = sorted(
            self._feedback,
            key=lambda fb: fb.timestamp,
            reverse=True,
        )
        return sorted_feedback[:limit]

    async def update_execution_result(
        self,
        remediation_id: str,
        success: bool,
        execution_time_seconds: float,
    ) -> None:
        """Update execution result for a feedback entry."""
        for fb in self._feedback:
            if fb.remediation_id == remediation_id:
                fb.execution_success = success
                fb.execution_time_seconds = execution_time_seconds
                break


# =============================================================================
# SQLAlchemy Model
# =============================================================================


class FeedbackRecord(Base):  # type: ignore[misc,valid-type]
    """
    SQLAlchemy model for remediation feedback records.

    Corresponds to the remediation_feedback table in PostgreSQL.
    """

    __tablename__ = "remediation_feedback"

    feedback_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    remediation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    recommendation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    alert_labels: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    reason_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    execution_success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    execution_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# =============================================================================
# PostgreSQL Implementation
# =============================================================================


class PostgresFeedbackStore(FeedbackStore):
    """
    PostgreSQL-backed feedback store.

    Production-ready implementation using SQLAlchemy async sessions.
    """

    def __init__(
        self, session_maker: async_sessionmaker[AsyncSession]
    ) -> None:
        """
        Initialize the PostgreSQL feedback store.

        Args:
            session_maker: SQLAlchemy async session factory.
        """
        self._session_maker = session_maker

    def _record_to_feedback(self, record: FeedbackRecord) -> RemediationFeedback:
        """
        Convert a database record to a RemediationFeedback dataclass.

        Args:
            record: The database record.

        Returns:
            A RemediationFeedback instance.
        """
        reason = None
        if record.reason:
            try:
                reason = RejectionReason(record.reason)
            except ValueError:
                pass  # Invalid reason value, leave as None

        return RemediationFeedback(
            feedback_id=record.feedback_id,
            remediation_id=record.remediation_id,
            recommendation_id=record.recommendation_id,
            alert_type=record.alert_type,
            alert_labels=record.alert_labels or {},
            severity=record.severity,
            action=record.action,
            reason=reason,
            reason_detail=record.reason_detail,
            admin_user_id=record.admin_user_id,
            timestamp=record.timestamp,
            execution_success=record.execution_success,
            execution_time_seconds=record.execution_time_seconds,
            admin_notes=record.admin_notes,
        )

    async def save_feedback(self, feedback: RemediationFeedback) -> None:
        """Save feedback entry to the database."""
        async with self._session_maker() as session:
            record = FeedbackRecord(
                feedback_id=feedback.feedback_id,
                remediation_id=feedback.remediation_id,
                recommendation_id=feedback.recommendation_id,
                alert_type=feedback.alert_type,
                alert_labels=feedback.alert_labels,
                severity=feedback.severity,
                action=feedback.action,
                reason=feedback.reason.value if feedback.reason else None,
                reason_detail=feedback.reason_detail,
                admin_user_id=feedback.admin_user_id,
                timestamp=feedback.timestamp,
                execution_success=feedback.execution_success,
                execution_time_seconds=feedback.execution_time_seconds,
                admin_notes=feedback.admin_notes,
            )
            session.add(record)
            await session.commit()

    async def get_approved_examples(
        self,
        alert_type: str,
        limit: int = 5,
    ) -> list[RemediationFeedback]:
        """Get approved examples for few-shot learning."""
        async with self._session_maker() as session:
            stmt = (
                select(FeedbackRecord)
                .where(FeedbackRecord.action == "approved")
                .where(FeedbackRecord.alert_type == alert_type)
                .order_by(FeedbackRecord.timestamp.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            records = result.scalars().all()
            return [self._record_to_feedback(r) for r in records]

    async def get_rejection_patterns(
        self,
        alert_type: str | None = None,
    ) -> dict[RejectionReason, int]:
        """Get rejection reason counts for constraint learning."""
        async with self._session_maker() as session:
            stmt = select(FeedbackRecord).where(
                FeedbackRecord.action == "rejected",
                FeedbackRecord.reason.isnot(None),
            )
            if alert_type:
                stmt = stmt.where(FeedbackRecord.alert_type == alert_type)

            result = await session.execute(stmt)
            records = result.scalars().all()

            counts: dict[RejectionReason, int] = defaultdict(int)
            for record in records:
                if record.reason:
                    try:
                        reason = RejectionReason(record.reason)
                        counts[reason] += 1
                    except ValueError:
                        pass  # Skip invalid reason values

            return dict(counts)

    async def get_recent_feedback(
        self,
        limit: int = 100,
    ) -> list[RemediationFeedback]:
        """Get recent feedback entries."""
        async with self._session_maker() as session:
            stmt = (
                select(FeedbackRecord)
                .order_by(FeedbackRecord.timestamp.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            records = result.scalars().all()
            return [self._record_to_feedback(r) for r in records]

    async def update_execution_result(
        self,
        remediation_id: str,
        success: bool,
        execution_time_seconds: float,
    ) -> None:
        """Update the execution result for a feedback entry."""
        async with self._session_maker() as session:
            stmt = select(FeedbackRecord).where(
                FeedbackRecord.remediation_id == remediation_id
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if record:
                record.execution_success = success
                record.execution_time_seconds = execution_time_seconds
                await session.commit()
