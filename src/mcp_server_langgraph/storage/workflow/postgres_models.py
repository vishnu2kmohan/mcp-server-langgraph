"""
SQLAlchemy models for Postgres-backed workflow storage.

These models support durable persistence of workflows for production use-cases
where learning from prior chats and long-term storage is required.

Optimized for:
1. Full-Text Search (FTS) using PostgreSQL tsvector with GIN index
2. Cursor-based pagination with composite indices (sort_column + id)
3. Efficient filtering via composite indices (user_id + updated_at)
4. Stable sorting with unique tiebreaker (id column)
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mcp_server_langgraph.models.base import Base


class WorkflowModel(Base):
    """
    SQLAlchemy model for workflow storage.

    Table: workflows (Agent Studio workflow definitions)

    Optimization Features:
    - search_vector: TSVECTOR column for PostgreSQL Full-Text Search
    - status: Workflow status for filtering (active, archived, draft)
    - Composite indices for efficient pagination and filtering
    - GIN index on search_vector for fast FTS queries

    The search_vector is populated via database trigger (see migration)
    with weighted fields: name (A) > description (B)
    """

    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # Title: Human-friendly display name (defaults to name if not set)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    nodes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    edges: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Status column for filtering workflows
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
        index=True,
    )

    # Full-Text Search vector (populated by trigger)
    # Weighted: name (A) > description (B)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)

    # Sharing fields
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    share_link: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)

    # Versioning fields (added for chat-to-workflow feature)
    head_version_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("workflow_versions.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)

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

    # Composite indices for optimized queries
    __table_args__ = (
        # GIN index for Full-Text Search on search_vector
        Index(
            "ix_workflows_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
        # Composite index for cursor-based pagination by updated_at
        # ORDER BY updated_at DESC, id DESC
        Index(
            "ix_workflows_updated_at_id",
            "updated_at",
            "id",
        ),
        # Composite index for cursor-based pagination by name
        # ORDER BY name ASC, id ASC
        Index(
            "ix_workflows_name_id",
            "name",
            "id",
        ),
        # Composite index for filtered queries by user + updated_at
        # WHERE user_id = ? ORDER BY updated_at DESC
        Index(
            "ix_workflows_user_updated",
            "user_id",
            "updated_at",
        ),
        # Composite index for filtered queries by user + created_at
        # WHERE user_id = ? ORDER BY created_at DESC
        Index(
            "ix_workflows_user_created",
            "user_id",
            "created_at",
        ),
        # Composite index for status + updated_at filtering
        # WHERE status = ? ORDER BY updated_at DESC
        Index(
            "ix_workflows_status_updated",
            "status",
            "updated_at",
        ),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Workflow(id={self.id!r}, name={self.name!r}, status={self.status!r})>"


class WorkflowShareModel(Base):
    """
    SQLAlchemy model for workflow sharing permissions.

    Table: workflow_shares (user-to-workflow permissions)

    Stores sharing relationships between workflows and users with
    permission levels: view, edit, execute.
    """

    __tablename__ = "workflow_shares"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    permission: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)

    # Composite indices for efficient queries
    __table_args__ = (
        # Unique constraint on workflow_id + user_id
        Index(
            "ix_workflow_shares_workflow_user",
            "workflow_id",
            "user_id",
            unique=True,
        ),
        # Composite index for permission-based queries
        Index(
            "ix_workflow_shares_user_permission",
            "user_id",
            "permission",
        ),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<WorkflowShare(workflow_id={self.workflow_id!r}, user_id={self.user_id!r}, permission={self.permission!r})>"


class WorkflowVersionModel(Base):
    """
    SQLAlchemy model for workflow version history.

    Table: workflow_versions (append-only revision history)

    Enables:
    - Durable workflows with draft/publish lifecycle
    - Version diffing and rollback
    - Prompt-level telemetry linkage for optimization
    - Audit trail of all workflow changes

    References:
    - Plan: Chat-to-Workflow Feature (validated by 4 independent reviews)
    - ADR-0089: Prompt Architecture Centralization
    """

    __tablename__ = "workflow_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Snapshot of workflow state at this version
    graph_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    commit_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Audit fields
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Telemetry linkage for prompt optimization (per review consensus)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationship to workflow
    workflow: Mapped["WorkflowModel"] = relationship(
        "WorkflowModel",
        foreign_keys=[workflow_id],
        backref="versions",
    )

    # Table constraints and indices
    __table_args__ = (
        # Unique constraint: one version number per workflow
        Index(
            "ix_workflow_versions_workflow_version",
            "workflow_id",
            "version_number",
            unique=True,
        ),
        # Index for ordering by creation time
        Index(
            "ix_workflow_versions_created_at",
            "workflow_id",
            "created_at",
        ),
        # Index for prompt telemetry queries
        Index(
            "ix_workflow_versions_prompt_version",
            "prompt_version",
            postgresql_where="prompt_version IS NOT NULL",
        ),
        # Ensure version numbers are positive
        CheckConstraint(
            "version_number > 0",
            name="workflow_versions_version_positive",
        ),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<WorkflowVersion(workflow_id={self.workflow_id!r}, version={self.version_number}, created_at={self.created_at!r})>"
