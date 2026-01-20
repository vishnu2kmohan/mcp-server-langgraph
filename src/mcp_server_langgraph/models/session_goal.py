"""
Session Goal SQLAlchemy Model.

Provides SQLAlchemy ORM model for session goal tracking:
- SessionGoal: Tracks user goals within sessions

Reference: docs-internal/frontend/PENDING-BACKEND-APIS.md
Migration: alembic/versions/z6a7b8c9d0e1_add_session_goals_table.py
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import BigInteger, CheckConstraint, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class SessionGoalBase(DeclarativeBase):
    """Base class for session goal models."""

    pass


class SessionGoal(SessionGoalBase):
    """
    Session goal model for tracking user goals.

    Supports:
    - Goal setting with timestamp
    - Achievement status (true, false, partial)
    - Optional feedback on completion

    Maps to: session_goals table
    """

    __tablename__ = "session_goals"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        name="id",
    )

    # Session reference
    session_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # User reference
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # Goal content
    goal: Mapped[str] = mapped_column(
        Text(),
        nullable=False,
    )

    # Achievement status: 'true', 'false', 'partial'
    achieved: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    # Optional feedback when completing
    feedback: Mapped[str | None] = mapped_column(
        Text(),
        nullable=True,
    )

    # Timestamps (stored as Unix milliseconds for frontend compatibility)
    set_at: Mapped[int] = mapped_column(
        BigInteger(),
        nullable=False,
    )

    completed_at: Mapped[int | None] = mapped_column(
        BigInteger(),
        nullable=True,
    )

    # Database timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        CheckConstraint(
            "achieved IN ('true', 'false', 'partial')",
            name="ck_session_goals_achieved_values",
        ),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"SessionGoal(id={self.id!r}, session_id={self.session_id!r}, "
            f"goal={self.goal[:30]!r}..., achieved={self.achieved!r})"
        )
