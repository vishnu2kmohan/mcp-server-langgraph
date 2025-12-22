"""
SQLAlchemy models for Postgres-backed artifact storage.

These models support durable persistence of canvas artifacts for the Hybrid Canvas
feature, with full version history tracking.

Schema Design:
- artifacts: Main table storing current artifact state
- artifact_versions: Shadow table storing all versions for history/rollback
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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class ArtifactBase(DeclarativeBase):
    """Base class for Artifact database models."""

    pass


class ArtifactModel(ArtifactBase):
    """
    SQLAlchemy model for artifact storage.

    Table: artifacts (Canvas artifacts in Agent Studio)

    Features:
    - Version tracking with auto-increment
    - JSONB for flexible edit metadata
    - Full-text search via TSVECTOR
    - Composite indices for common query patterns
    """

    __tablename__ = "artifacts"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Foreign keys
    session_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Content fields
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="code")
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Untitled Artifact"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="code"
    )

    # Versioning
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Storage type for hybrid storage
    # 'inline' = content stored in PostgreSQL
    # 's3', 'gcs', 'azure' = content stored in cloud, this field stores the key
    storage_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="inline"
    )
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Metadata (JSONB for flexibility)
    edit_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

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

    # Full-text search vector (maintained by database trigger)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        nullable=True,
    )

    # Relationships
    versions: Mapped[list["ArtifactVersionModel"]] = relationship(
        "ArtifactVersionModel",
        back_populates="artifact",
        cascade="all, delete-orphan",
        order_by="ArtifactVersionModel.version",
    )

    __table_args__ = (
        # Composite indices for common queries
        Index("ix_artifacts_session_updated", "session_id", "updated_at"),
        Index("ix_artifacts_user_updated", "user_id", "updated_at"),
        Index("ix_artifacts_user_session", "user_id", "session_id"),
        # GIN index for full-text search
        Index(
            "ix_artifacts_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Artifact(id={self.id!r}, title={self.title!r}, version={self.version})>"

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "type": self.type,
            "title": self.title,
            "content": self.content,
            "content_type": self.content_type,
            "version": self.version,
            "storage_type": self.storage_type,
            "storage_key": self.storage_key,
            "edit_metadata": self.edit_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ArtifactVersionModel(ArtifactBase):
    """
    SQLAlchemy model for artifact version history.

    Table: artifact_versions (Version history for artifacts)

    This is a shadow table that stores every version of an artifact
    for history tracking and potential rollback.
    """

    __tablename__ = "artifact_versions"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Foreign key to parent artifact
    artifact_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Version info
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Content snapshot
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="code"
    )

    # Storage type for hybrid storage (same as ArtifactModel)
    storage_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="inline"
    )
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Who created this version
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)

    # When this version was created
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Version metadata (JSONB for flexibility)
    # Can store: edit_type, ai_confidence, diff_stats, etc.
    version_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )

    # Relationship back to parent artifact
    artifact: Mapped["ArtifactModel"] = relationship(
        "ArtifactModel",
        back_populates="versions",
    )

    __table_args__ = (
        # Unique constraint: one version number per artifact
        UniqueConstraint("artifact_id", "version", name="uq_artifact_version"),
        # Composite index for version lookups
        Index("ix_artifact_versions_artifact_version", "artifact_id", "version"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<ArtifactVersion(artifact_id={self.artifact_id!r}, version={self.version})>"

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "artifact_id": self.artifact_id,
            "version": self.version,
            "parent_version": self.parent_version,
            "content": self.content,
            "content_type": self.content_type,
            "storage_type": self.storage_type,
            "storage_key": self.storage_key,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.version_metadata,
        }
