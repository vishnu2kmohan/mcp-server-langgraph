"""
Audit Log SQLAlchemy Models.

Provides SQLAlchemy ORM models for audit logging:
- AuditLogModel: Legacy model for connection operations
- UnifiedAuditLog: Unified model for regulatory compliance (GDPR, HIPAA, SOC2, FedRAMP, EU AI Act)

The UnifiedAuditLog model answers: WHO did WHAT, WHEN, and WHERE.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class AuditBase(DeclarativeBase):
    """Base class for audit-related models."""

    pass


class AuditLogModel(AuditBase):
    """SQLAlchemy model for audit log entries (legacy connection auditing)."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_audit_logs_resource", "resource_type", "resource_id"),
        Index("idx_audit_logs_actor", "actor_id"),
        Index("idx_audit_logs_event_type", "event_type"),
        Index("idx_audit_logs_timestamp", "timestamp"),
    )


class UnifiedAuditLog(AuditBase):
    """
    Unified audit log model for regulatory compliance.

    Supports GDPR, HIPAA, SOC 2, FedRAMP, and EU AI Act requirements.
    Answers: WHO did WHAT, WHEN, and WHERE with cryptographic integrity.

    Columns are organized by purpose:
    - Identification: log_id, timestamp
    - Classification: category, event_type, outcome
    - Actor (WHO): actor_id, actor_type, organization_id
    - Resource (WHAT): resource_type, resource_id, action
    - Context (WHERE): trace_id, span_id, session_id, ip_address, user_agent
    - Details: details (JSONB)
    - AI (EU AI Act): ai_operation (JSONB)
    - Integrity (FedRAMP AU-9): sequence_number, previous_hash, event_hash
    - Compliance: regulation_tags, retention_days
    """

    __tablename__ = "audit_logs"

    # Core identifiers
    log_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        name="log_id",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Event classification
    category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,  # Nullable for backward compatibility
    )
    event_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    outcome: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,  # success, failure, denied, error
    )

    # Actor information (WHO)
    actor_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    actor_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,  # user, service, system
    )
    organization_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Resource information (WHAT)
    resource_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    action: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Context (WHERE) - OpenTelemetry correlation
    trace_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    span_id: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    session_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Network context
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # Supports IPv6
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Additional details
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # AI operation details (EU AI Act Articles 12, 19, 72)
    ai_operation: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Integrity fields (FedRAMP AU-9 tamper-evidence)
    sequence_number: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    previous_hash: Mapped[str | None] = mapped_column(
        String(64),  # HMAC-SHA256 = 64 hex chars
        nullable=True,
    )
    event_hash: Mapped[str | None] = mapped_column(
        String(64),  # HMAC-SHA256 = 64 hex chars
        nullable=True,
    )

    # Compliance metadata
    regulation_tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(20)),
        nullable=True,
    )
    retention_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2555,  # 7 years default (DB level)
        insert_default=2555,  # Also insert default
    )

    def __init__(self, **kwargs: object) -> None:
        """Initialize with Python-level defaults."""
        # Set retention_days default if not provided
        if "retention_days" not in kwargs:
            kwargs["retention_days"] = 2555
        super().__init__(**kwargs)

    # Preserve backward compatibility with user_id column from GDPR migration
    user_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Preserve backward compatibility with metadata column from GDPR migration
    # Note: 'metadata' is reserved in SQLAlchemy, so we map to 'extra_metadata'
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",  # Column name in database
        JSONB,
        nullable=True,
    )

    __table_args__ = (
        # Existing indices from other migrations
        Index("idx_audit_logs_resource", "resource_type", "resource_id"),
        Index("idx_audit_logs_actor", "actor_id"),
        Index("idx_audit_logs_event_type", "event_type"),
        Index("idx_audit_logs_timestamp", "timestamp"),
        # New indices for unified audit facility
        Index("idx_audit_unified_category", "category"),
        Index("idx_audit_unified_outcome", "outcome"),
        Index("idx_audit_unified_org", "organization_id"),
        Index("idx_audit_unified_trace", "trace_id"),
        Index("idx_audit_unified_session", "session_id"),
        Index("idx_audit_unified_sequence", "sequence_number"),
        # Composite indices for compliance queries
        Index("idx_audit_unified_regulation", "regulation_tags"),
        Index("idx_audit_unified_category_time", "category", "timestamp"),
        Index("idx_audit_unified_org_time", "organization_id", "timestamp"),
        # Extend table instead of creating new (same tablename)
        {"extend_existing": True},
    )
