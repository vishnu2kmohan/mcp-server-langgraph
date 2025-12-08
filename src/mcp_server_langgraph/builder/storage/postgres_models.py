"""
SQLAlchemy models for Postgres-backed workflow storage.

These models support durable persistence of workflows for production use-cases
where learning from prior chats and long-term storage is required.
"""

from datetime import datetime, UTC
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BuilderBase(DeclarativeBase):
    """Base class for Builder database models."""

    pass


class WorkflowModel(BuilderBase):
    """
    SQLAlchemy model for workflow storage.

    Table: builder_workflows
    """

    __tablename__ = "builder_workflows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    nodes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    edges: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
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

    def __repr__(self) -> str:
        """String representation."""
        return f"<Workflow(id={self.id!r}, name={self.name!r})>"
