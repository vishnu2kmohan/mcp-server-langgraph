"""
SQLAlchemy models for cost tracking persistence.

This module defines database models for storing LLM token usage and cost metrics
with PostgreSQL persistence and automatic retention policies.
"""

from datetime import datetime, UTC
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()


class TokenUsageRecord(Base):  # type: ignore[misc,valid-type]
    """
    Persistent storage for LLM token usage and cost data.

    This model stores detailed token usage metrics for cost tracking,
    budgeting, and analytics with automatic retention policies.

    Indexes:
        - timestamp: For time-range queries and retention cleanup
        - user_id: For per-user cost analysis
        - session_id: For per-session cost tracking
        - model: For per-model cost analysis
        - composite (user_id, timestamp): For efficient user cost queries

    Retention:
        Records are automatically purged after CONTEXT_RETENTION_DAYS (default: 90)
        via background cleanup job.
    """

    __tablename__ = "token_usage_records"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="When the LLM call was made (UTC)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        doc="When the record was created (UTC)",
    )

    # Identifiers
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="User identifier",
    )
    session_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Session identifier",
    )

    # Model information
    model: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Model name (e.g., claude-3-5-sonnet-20241022)",
    )
    provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Provider name (e.g., anthropic, openai, google)",
    )

    # Token counts
    prompt_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Number of input tokens",
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Number of output tokens",
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Total tokens (prompt + completion)",
    )

    # Cost (stored as Decimal for precision)
    estimated_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=6),
        nullable=False,
        doc="Estimated cost in USD (6 decimal places for sub-cent precision)",
    )

    # Optional categorization
    feature: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Feature name (e.g., 'chat', 'summarization', 'context_compaction')",
    )

    # Metadata (stored as JSON)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",  # Column name in DB
        JSON,
        nullable=True,
        doc="Additional metadata (JSON)",
    )

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_user_timestamp", "user_id", "timestamp"),
        Index("ix_provider_model", "provider", "model"),
        Index("ix_timestamp_desc", "timestamp", postgresql_ops={"timestamp": "DESC"}),
    )

    def __repr__(self) -> str:
        return (
            f"<TokenUsageRecord(id={self.id}, "
            f"user_id={self.user_id}, "
            f"model={self.model}, "
            f"tokens={self.total_tokens}, "
            f"cost=${self.estimated_cost_usd})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "created_at": self.created_at.isoformat(),
            "user_id": self.user_id,
            "session_id": self.session_id,
            "model": self.model,
            "provider": self.provider,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": str(self.estimated_cost_usd),
            "feature": self.feature,
            "metadata": self.metadata_,
        }
