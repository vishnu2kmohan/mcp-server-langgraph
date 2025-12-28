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
        doc="Model name (e.g., claude-sonnet-4-5-20250929)",
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

    # Organizational hierarchy for multi-tenant cost attribution
    organization_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Organization ID for multi-tenant cost attribution (e.g., 'organization:acme')",
    )
    project_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Project ID for project-level cost breakdown (e.g., 'project:backend')",
    )
    team_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Team/group ID for team-level cost attribution (e.g., 'team:platform')",
    )

    # Custom cost allocation tags for flexible cost attribution
    allocation_tags: Mapped[dict[str, str] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Custom key-value tags for cost allocation (e.g., {'environment': 'production', 'campaign': 'launch-2025'})",
    )

    # Composite indexes for common queries
    __table_args__ = (
        # Existing indexes
        Index("ix_user_timestamp", "user_id", "timestamp"),
        Index("ix_provider_model", "provider", "model"),
        Index("ix_timestamp_desc", "timestamp", postgresql_ops={"timestamp": "DESC"}),
        # Organizational cost query indexes
        Index("ix_org_timestamp", "organization_id", "timestamp"),
        Index("ix_project_timestamp", "project_id", "timestamp"),
        Index("ix_team_user_timestamp", "team_id", "user_id", "timestamp"),
        Index("ix_org_project_team", "organization_id", "project_id", "team_id"),
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
            # Organizational hierarchy
            "organization_id": self.organization_id,
            "project_id": self.project_id,
            "team_id": self.team_id,
            # Custom allocation tags
            "allocation_tags": self.allocation_tags,
        }


class BudgetRecord(Base):  # type: ignore[misc,valid-type]
    """
    Persistent storage for budget configurations.

    Stores budget limits for organizations, projects, teams, and users
    to enable cost control and alerting.

    Entity Types:
        - organization: Company-wide budget limits
        - project: Per-project budget limits
        - team: Team-level budget limits
        - user: Individual user budget limits

    The entity_type + entity_id combination is unique (one budget per entity).
    """

    __tablename__ = "budget_records"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Entity identification (unique constraint on type + id)
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Entity type: organization, project, team, user",
    )
    entity_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Entity identifier (e.g., 'organization:acme', 'user:alice')",
    )

    # Budget configuration
    monthly_limit_usd: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        doc="Monthly budget limit in USD",
    )
    warning_threshold: Mapped[float] = mapped_column(
        Numeric(precision=3, scale=2),
        nullable=False,
        insert_default=0.80,
        default=0.80,
        doc="Warning threshold as percentage (0.80 = 80%)",
    )
    critical_threshold: Mapped[float] = mapped_column(
        Numeric(precision=3, scale=2),
        nullable=False,
        insert_default=1.0,
        default=1.0,
        doc="Critical threshold as percentage (1.0 = 100%)",
    )

    # Metadata
    name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Human-readable budget name",
    )
    description: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        doc="Budget description",
    )
    enabled: Mapped[bool] = mapped_column(
        default=True,
        doc="Whether budget monitoring is enabled",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        doc="When the budget was created (UTC)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        doc="When the budget was last updated (UTC)",
    )

    # Indexes
    __table_args__ = (
        # Unique constraint: one budget per entity
        Index("ix_budget_entity_type_id", "entity_type", "entity_id", unique=True),
        # For filtering by entity type
        Index("ix_budget_entity_type", "entity_type"),
        # For filtering enabled budgets
        Index("ix_budget_enabled", "enabled"),
    )

    def __repr__(self) -> str:
        return f"<BudgetRecord(id={self.id}, entity={self.entity_id}, limit=${self.monthly_limit_usd})>"

    def to_dict(self) -> dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "monthly_limit_usd": str(self.monthly_limit_usd),
            "warning_threshold": float(self.warning_threshold),
            "critical_threshold": float(self.critical_threshold),
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
