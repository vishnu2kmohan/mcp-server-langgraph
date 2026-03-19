"""
PostgreSQL ORM Models for Agentic Memory

Tables:
- notes: Structured notes with FTS support
- phase_checkpoints: Phase completion checkpoints
- compliance_reports: SOC 2 compliance report storage

All models use the unified DeclarativeBase from models/base.py.
"""

from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from mcp_server_langgraph.models.base import Base


class NoteModel(Base):
    """SQLAlchemy model for notes table."""

    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="general")
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, key="metadata_json")
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    slug: Mapped[str | None] = mapped_column(String(500), nullable=True)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)

    __table_args__ = (
        Index("ix_notes_user_created", "user_id", "created_at"),
        Index("ix_notes_session_id", "session_id"),
        Index("ix_notes_category", "category"),
        Index("ix_notes_tags", "tags", postgresql_using="gin"),
        Index("ix_notes_search_vector", "search_vector", postgresql_using="gin"),
    )


class PhaseCheckpointModel(Base):
    """SQLAlchemy model for phase_checkpoints table.

    Named phase_checkpoints to avoid collision with LangGraph's
    conversation checkpoint concept.
    """

    __tablename__ = "phase_checkpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    phase: Mapped[str] = mapped_column(String(100), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    artifacts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, key="metadata_json")
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_phase_checkpoints_user_created", "user_id", "created_at", postgresql_ops={"created_at": "DESC"}),
        Index("ix_phase_checkpoints_phase", "phase"),
        Index("ix_phase_checkpoints_created_desc", "created_at", postgresql_ops={"created_at": "DESC"}),
    )


class ComplianceReportModel(Base):
    """SQLAlchemy model for compliance_reports table."""

    __tablename__ = "compliance_reports"

    report_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    report_type: Mapped[str] = mapped_column(String(20), nullable=False)
    generated_at: Mapped[str] = mapped_column(String(50), nullable=False)
    period_start: Mapped[str] = mapped_column(String(50), nullable=False)
    period_end: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_items: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    compliance_score: Mapped[float] = mapped_column(Float, nullable=False)
    passed_controls: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_controls: Mapped[int] = mapped_column(Integer, nullable=False)
    partial_controls: Mapped[int] = mapped_column(Integer, nullable=False)
    total_controls: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_compliance_reports_type_generated", "report_type", "generated_at", postgresql_ops={"generated_at": "DESC"}),
        Index("ix_compliance_reports_generated_desc", "generated_at", postgresql_ops={"generated_at": "DESC"}),
    )
