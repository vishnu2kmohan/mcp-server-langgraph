"""
SQLAlchemy models for execution plans and plan templates.

This module defines database models for storing:
- ExecutionPlan: Pending or completed execution plans
- PlanTemplate: Reusable plan templates

All models use PostgreSQL persistence with pgvector for embeddings.

Phase 4: PostgreSQL Repositories (SQLAlchemy AsyncSession)
"""

from datetime import datetime, UTC
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mcp_server_langgraph.models.base import Base


class ExecutionPlanModel(Base):
    """
    SQLAlchemy model for execution_plans table.

    Maps to ExecutionPlan Pydantic model for persistence.

    Features:
    - Full plan lifecycle tracking (awaiting_approval → approved/rejected → executed/expired)
    - Risk-based approval requirements
    - Cost estimation and tracking
    - Embedding support for semantic search
    - GDPR user tracking (user_id, created_by)
    """

    __tablename__ = "execution_plans"

    # Primary key
    plan_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Foreign key to sessions
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Status and classification
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="awaiting_approval",
        index=True,
    )
    complexity: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Model configuration
    executor_model: Mapped[str] = mapped_column(String(255), nullable=False)
    critic_model: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Cost tracking
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    actual_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)

    # Content
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # v35.0: Uses JSONB (not ARRAY) to match SQL schema and preserve NULL semantics
    tools_needed: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    # Approval configuration
    force_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Orchestrator configuration
    suggested_orchestrator: Mapped[str] = mapped_column(String(20), nullable=False, default="standard")
    critique_rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    thinking_budget: Mapped[str] = mapped_column(String(20), nullable=False, default="none")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Approval/rejection tracking
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # User tracking (GDPR compliance)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # v35.0: Audit trail and capability tracking fields
    # NOTE: Uses JSONB to match Alembic migration c0d1e2f3g4h5 (not ARRAY)
    skills_needed: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    selected_tool_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    llm_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    kb_focus: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # v35.0 Phase 2e: Tool preference fields
    tool_preference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tool_selection_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Embedding status (Phase 7.25: Self-healing embedding service)
    embedding_status: Mapped[str | None] = mapped_column(String(20), nullable=True, default="pending")
    embedding_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    embedding_failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Note: description_embedding is vector(768) type, added via pgvector migration
    # SQLAlchemy doesn't have native vector type, so we handle this in raw SQL

    # Indexes
    __table_args__ = (Index("ix_execution_plans_session_status", "session_id", "status"),)

    def __repr__(self) -> str:
        return f"<ExecutionPlanModel(plan_id={self.plan_id}, status={self.status}, session_id={self.session_id})>"


class PlanTemplateModel(Base):
    """
    SQLAlchemy model for plan_templates table.

    Maps to PlanTemplate Pydantic model for persistence.

    Features:
    - Reusable plan configurations
    - Usage metrics tracking
    - Semantic search via embeddings
    - Ownership tracking
    """

    __tablename__ = "plan_templates"

    # Primary key
    template_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Template configuration
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    orchestrator: Mapped[str] = mapped_column(String(20), nullable=False, default="standard")
    thinking_budget: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    critique_rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    auto_approve: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Tags for search/filter
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True, default=[])

    # Ownership
    created_by: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Usage metrics
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
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

    # Embedding status (Phase 7.25: Self-healing embedding service)
    embedding_status: Mapped[str | None] = mapped_column(String(20), nullable=True, default="pending")
    embedding_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    embedding_failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Note: description_embedding is vector(768) type, added via pgvector migration

    # Indexes
    __table_args__ = (
        Index("ix_plan_templates_tags", "tags", postgresql_using="gin"),
        Index("ix_plan_templates_use_count", "use_count"),
    )

    def __repr__(self) -> str:
        return f"<PlanTemplateModel(template_id={self.template_id}, name={self.name}, created_by={self.created_by})>"
