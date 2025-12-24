"""
SQLAlchemy models for Postgres-backed session storage.

These models support durable persistence of Agent Studio sessions for production use-cases
where chat history and session state must survive restarts.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class SessionBase(DeclarativeBase):
    """Base class for Session database models."""

    pass


class SessionModel(SessionBase):
    """
    SQLAlchemy model for session storage.

    Table: sessions (Agent Studio chat sessions)
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    config_model: Mapped[str] = mapped_column(String(100), nullable=False, default="gpt-4o-mini")
    config_temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    config_max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
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

    # Session status: 'active' (default) or 'archived'
    # Uses server_default to avoid table locks during migration
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
    )

    # Optional workflow ID this session is associated with
    workflow_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )

    # Full-text search vector (maintained by database trigger)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        nullable=True,
    )

    __table_args__ = (
        Index("ix_sessions_user_updated", "user_id", "updated_at"),
        Index("ix_sessions_user_created", "user_id", "created_at"),
        Index(
            "ix_sessions_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
        # Composite index for user + status filtering
        Index("ix_sessions_user_status", "user_id", "status"),
        # Composite index for user + workflow filtering
        Index("ix_sessions_user_workflow", "user_id", "workflow_id"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Session(id={self.id!r}, name={self.name!r}, status={self.status!r})>"


class MessageModel(SessionBase):
    """
    SQLAlchemy model for message storage.

    Table: messages (chat messages within Agent Studio sessions)

    Optimization Features:
    - Composite index on (session_id, order_index) for efficient message ordering
    - Composite index on (session_id, timestamp) for time-range queries
    - These indices enable efficient queries like:
      - Get all messages in a session ordered by order_index
      - Get messages in a session after a specific timestamp
    """

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    # Order index for maintaining message order
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Composite indices for optimized message queries
    __table_args__ = (
        # Composite index for message ordering within a session
        # SELECT * FROM messages WHERE session_id = ? ORDER BY order_index
        Index(
            "ix_messages_session_order",
            "session_id",
            "order_index",
        ),
        # Composite index for time-range message queries
        # SELECT * FROM messages WHERE session_id = ? AND timestamp > ? ORDER BY timestamp
        Index(
            "ix_messages_session_timestamp",
            "session_id",
            "timestamp",
        ),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Message(id={self.id!r}, session_id={self.session_id!r}, role={self.role!r})>"
