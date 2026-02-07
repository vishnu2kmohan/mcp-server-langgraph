"""
Alert Database Models.

SQLAlchemy models for persistent alert storage.

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from datetime import datetime, UTC
from typing import Any

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from mcp_server_langgraph.models.base import Base


class AlertRecord(Base):
    """
    Persistent storage for infrastructure alerts from Alertmanager.

    This model stores alerts received from Alertmanager for:
    - AI recommendation lookup
    - Alert history queries
    - Audit trail purposes

    Indexes:
        - alert_id: For quick lookup by alert fingerprint
        - severity: For severity-based filtering
        - state: For state-based filtering
        - started_at: For time-range queries
        - composite (severity, state): For filtered queries

    Retention:
        Records are retained for 30 days by default.
    """

    __tablename__ = "alert_records"

    # Primary key (internal)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Alert identifier (from Alertmanager fingerprint)
    alert_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        doc="Alert fingerprint from Alertmanager",
    )

    # Alert metadata
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Alert name (e.g., HighCPU, DiskFull)",
    )
    severity: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Alert severity (critical, warning, info, error)",
    )
    state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Alert state (pending, firing, resolved, silenced)",
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        doc="Alert description message",
    )

    # Labels and annotations as JSON
    labels: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        doc="Alert labels from Alertmanager",
    )
    annotations: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        doc="Alert annotations from Alertmanager",
    )

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        doc="When the alert started firing (UTC)",
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the alert resolved (UTC, null if still firing)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        doc="When the record was created (UTC)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        doc="When the record was last updated (UTC)",
    )

    # Generator URL (link to monitoring system)
    generator_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="URL to view alert in monitoring system",
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("ix_alerts_severity_state", "severity", "state"),
        Index("ix_alerts_started_at_state", "started_at", "state"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<AlertRecord(alert_id={self.alert_id}, name={self.name}, severity={self.severity})>"
