"""
Project SQLAlchemy Models

Implements the Unified Workspace Paradigm where:
    One Project = Session + Workflow + Connections

Uses modern SQLAlchemy 2.0+ async patterns with type annotations.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mcp_server_langgraph.models.base import Base


class ProjectModel(Base):
    """
    Core project entity - container for sessions, workflows, and connections.

    Implements the Unified Workspace Paradigm.
    """

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    organization_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    owner_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
    )
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

    # Full-text search vector (maintained by database trigger)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        nullable=True,
    )

    # Relationships
    workflows: Mapped[list["ProjectWorkflowModel"]] = relationship(
        "ProjectWorkflowModel",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    sessions: Mapped[list["ProjectSessionModel"]] = relationship(
        "ProjectSessionModel",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    connections: Mapped[list["ProjectConnectionModel"]] = relationship(
        "ProjectConnectionModel",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    members: Mapped[list["ProjectMemberModel"]] = relationship(
        "ProjectMemberModel",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_projects_owner_created", "owner_id", "created_at"),
        Index("ix_projects_org_status", "organization_id", "status"),
        Index("ix_projects_name_id", "name", "id"),
        Index(
            "ix_projects_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
    )


class ProjectWorkflowModel(Base):
    """Junction table linking projects to workflows."""

    __tablename__ = "project_workflows"

    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    workflow_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
    )
    workflow_name: Mapped[str] = mapped_column(String(255), nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    project: Mapped["ProjectModel"] = relationship(
        "ProjectModel",
        back_populates="workflows",
    )

    __table_args__ = (Index("ix_project_workflows_workflow", "workflow_id"),)


class ProjectSessionModel(Base):
    """Junction table linking projects to sessions."""

    __tablename__ = "project_sessions"

    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
    )
    session_name: Mapped[str] = mapped_column(String(255), nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    project: Mapped["ProjectModel"] = relationship(
        "ProjectModel",
        back_populates="sessions",
    )

    __table_args__ = (Index("ix_project_sessions_session", "session_id"),)


class ProjectConnectionModel(Base):
    """Connections (MCP servers, vector stores, API keys) linked to a project."""

    __tablename__ = "project_connections"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        nullable=False,
    )
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    connection_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # mcp_server, vector_store, api_key
    connection_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
    )
    config: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    project: Mapped["ProjectModel"] = relationship(
        "ProjectModel",
        back_populates="connections",
    )

    __table_args__ = (Index("ix_project_connections_type", "project_id", "connection_type"),)


class ProjectMemberModel(Base):
    """Project membership with roles."""

    __tablename__ = "project_members"

    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # owner, editor, viewer, executor
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    project: Mapped["ProjectModel"] = relationship(
        "ProjectModel",
        back_populates="members",
    )

    __table_args__ = (
        Index("ix_project_members_user", "user_id"),
        Index("ix_project_members_role", "project_id", "role"),
    )
