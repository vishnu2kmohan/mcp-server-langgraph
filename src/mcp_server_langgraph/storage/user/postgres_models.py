"""
PostgreSQL models for user preferences.

Uses SQLAlchemy 2.0 declarative mapping with proper typing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class UserPreferencesBase(DeclarativeBase):
    """Base class for User Preferences database models."""

    pass


class UserPreferencesModel(UserPreferencesBase):
    """
    PostgreSQL model for user preferences storage.

    Table: user_preferences

    Stores user-specific preferences including:
    - Sub-persona selection
    - Feature flag overrides
    - UI/UX preferences

    Indices:
    - Primary key on user_id (unique per user)
    - Index on updated_at for cleanup queries
    """

    __tablename__ = "user_preferences"

    # Primary key - user_id is unique
    user_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        comment="User ID in OpenFGA format (user:username)",
    )

    # Sub-persona selection
    sub_persona: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Selected sub-persona variant (alice-builder, bob, etc.)",
    )

    # Feature flags as JSONB for flexible boolean storage
    feature_flags: Mapped[dict[str, bool]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="User-specific feature flag overrides",
    )

    # Additional preferences as JSONB
    preferences: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Additional UI/UX preferences (theme, layout, etc.)",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        comment="When preferences were first created",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="When preferences were last modified",
    )

    # Table-level configuration
    __table_args__ = (
        # Index for cleanup queries (find stale preferences)
        Index("ix_user_preferences_updated_at", "updated_at"),
        {"comment": "User preferences for persona and feature configuration"},
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<UserPreferencesModel(user_id={self.user_id!r}, sub_persona={self.sub_persona!r})>"
