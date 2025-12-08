"""
SQLAlchemy models for Postgres-backed session storage.

These models support durable persistence of playground sessions for production use-cases
where chat history and session state must survive restarts.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class PlaygroundBase(DeclarativeBase):
    """Base class for Playground database models."""

    pass


class SessionModel(PlaygroundBase):
    """
    SQLAlchemy model for session storage.

    Table: playground_sessions
    """

    __tablename__ = "playground_sessions"

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

    def __repr__(self) -> str:
        """String representation."""
        return f"<Session(id={self.id!r}, name={self.name!r})>"


class MessageModel(PlaygroundBase):
    """
    SQLAlchemy model for message storage.

    Table: playground_messages
    """

    __tablename__ = "playground_messages"

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

    def __repr__(self) -> str:
        """String representation."""
        return f"<Message(id={self.id!r}, session_id={self.session_id!r}, role={self.role!r})>"
