"""
User preferences Pydantic models.

These models represent the domain layer for user preferences,
separate from the SQLAlchemy database models.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class UserPreferences(BaseModel):
    """
    User preferences for persona and feature configuration.

    This model stores user-specific preferences including:
    - Sub-persona selection (alice-builder, alice-analyst, bob, etc.)
    - Feature flags for experimental features
    - UI preferences (theme, layout, etc.)

    Attributes:
        user_id: OpenFGA-compatible user ID (e.g., "user:alice")
        sub_persona: Selected sub-persona variant
        feature_flags: User-specific feature flag overrides
        preferences: Additional UI/UX preferences (theme, etc.)
        created_at: When preferences were first created
        updated_at: When preferences were last modified
    """

    user_id: str = Field(..., description="User ID in OpenFGA format (user:username)")
    sub_persona: str | None = Field(default=None, description="Selected sub-persona variant")
    feature_flags: dict[str, bool] = Field(
        default_factory=dict,
        description="User-specific feature flag overrides",
    )
    preferences: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional UI/UX preferences",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When preferences were first created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When preferences were last modified",
    )

    class Config:
        """Pydantic configuration."""

        from_attributes = True  # Enable ORM mode for SQLAlchemy conversion
