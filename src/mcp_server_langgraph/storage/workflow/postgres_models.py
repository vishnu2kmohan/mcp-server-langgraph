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

from sqlalchemy import JSON, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class WorkflowBase(DeclarativeBase):
    """Base class for Workflow database models."""

    pass


class WorkflowModel(WorkflowBase):
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
