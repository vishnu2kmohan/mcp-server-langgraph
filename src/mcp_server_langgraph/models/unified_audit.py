"""
Unified Audit SQLAlchemy Model.

Provides the SQLAlchemy ORM model for the unified audit logging facility.
This model supports all regulatory compliance requirements:
- GDPR, HIPAA, SOC 2, FedRAMP, EU AI Act

Maps to the partitioned audit_logs_partitioned table.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mcp_server_langgraph.models.base import Base


class UnifiedAuditModel(Base):
    """
    SQLAlchemy model for unified audit events.

    Answers: WHO did WHAT, WHEN, and WHERE with cryptographic integrity.

    Maps to the partitioned audit table for efficient retention management
    via DROP PARTITION (O(1) cleanup).
    """

    __tablename__ = "audit_logs_partitioned"

    # Core identifiers
    event_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        name="event_id",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        primary_key=True,  # Required for partitioning by timestamp
        default=lambda: datetime.now(UTC),
    )

    # Event classification
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    outcome: Mapped[str] = mapped_column(
        String(20),
        nullable=False,  # success, failure, denied, error
    )

    # Actor information (WHO) - flattened from AuditActor
    actor_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    actor_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,  # user, service, system
    )
    username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    organization_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    roles: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(100)),
        nullable=True,
    )

    # Resource information (WHAT)
    resource_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    resource_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Context (WHERE) - flattened from AuditContext
    request_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
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
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # Supports IPv6
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    http_method: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
    http_path: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )
    http_status: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Additional details (JSONB)
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # AI operation details (EU AI Act)
    ai_operation: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Integrity fields (FedRAMP AU-9)
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
        default=2555,  # 7 years default
    )

    __table_args__ = (
        # Performance indices
        Index("idx_unified_audit_actor", "actor_id"),
        Index("idx_unified_audit_category", "category"),
        Index("idx_unified_audit_event_type", "event_type"),
        Index("idx_unified_audit_org", "organization_id"),
        Index("idx_unified_audit_resource", "resource_type", "resource_id"),
        Index("idx_unified_audit_sequence", "sequence_number"),
        Index("idx_unified_audit_trace", "trace_id"),
        # Compliance query indices
        Index("idx_unified_audit_regulation", "regulation_tags"),
        Index("idx_unified_audit_category_time", "category", "timestamp"),
        Index("idx_unified_audit_org_time", "organization_id", "timestamp"),
        # PostgreSQL table options
        {
            "postgresql_partition_by": "RANGE (timestamp)",
        },
    )
