"""
User Preferences API Endpoints.

REST API for managing user preferences.

Endpoints:
- GET /preferences - Get current user's preferences
- PATCH /preferences - Update preferences (partial update)
- DELETE /preferences - Reset to defaults

Authentication:
- Uses Keycloak JWT authentication via get_current_user dependency
- User ID extracted from JWT claims

Storage:
- Preferences stored per-user
- In-memory by default, can be configured for Redis/DB persistence
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.middleware import get_current_user

logger = logging.getLogger(__name__)

# ==============================================================================
# Router
# ==============================================================================

user_preferences_router = APIRouter(
    prefix="/preferences",
    tags=["preferences"],
)

# ==============================================================================
# Constants & Defaults
# ==============================================================================

DEFAULT_USER_PREFERENCES: dict[str, Any] = {
    # General
    "theme": "system",
    "language": "en",
    "auto_scroll": True,
    # Accessibility
    "reduced_motion": False,
    "high_contrast": False,
    "screen_reader_mode": False,
    "font_size": "medium",
    # Model Defaults
    "default_model": None,
    "default_temperature": 0.7,
    "default_max_tokens": 4096,
    # Session
    "pinned_sessions": [],
    # Privacy
    "notifications_enabled": True,
    # Keyboard Shortcuts (custom overrides)
    "keyboard_shortcuts": {},
}

# ==============================================================================
# Models
# ==============================================================================


class UserPreferences(BaseModel):
    """User preferences model."""

    # General
    theme: Literal["light", "dark", "system"] = Field(default="system", description="UI theme")
    language: str = Field(default="en", description="UI language code")
    auto_scroll: bool = Field(default=True, description="Auto-scroll to new messages")

    # Accessibility
    reduced_motion: bool = Field(default=False, description="Reduce animations for accessibility")
    high_contrast: bool = Field(default=False, description="High contrast mode")
    screen_reader_mode: bool = Field(default=False, description="Screen reader optimizations")
    font_size: Literal["small", "medium", "large"] = Field(default="medium", description="UI font size")

    # Model Defaults
    default_model: str | None = Field(default=None, description="Default LLM model")
    default_temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Default temperature")
    default_max_tokens: int = Field(default=4096, gt=0, description="Default max tokens")

    # Session
    pinned_sessions: list[str] = Field(default_factory=list, description="Pinned session IDs")

    # Privacy
    notifications_enabled: bool = Field(default=True, description="Enable desktop notifications")

    # Keyboard Shortcuts
    keyboard_shortcuts: dict[str, str] = Field(default_factory=dict, description="Custom keyboard shortcut overrides")


class UserPreferencesUpdate(BaseModel):
    """Partial update model for user preferences."""

    # General
    theme: Literal["light", "dark", "system"] | None = None
    language: str | None = None
    auto_scroll: bool | None = None

    # Accessibility
    reduced_motion: bool | None = None
    high_contrast: bool | None = None
    screen_reader_mode: bool | None = None
    font_size: Literal["small", "medium", "large"] | None = None

    # Model Defaults
    default_model: str | None = None
    default_temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    default_max_tokens: int | None = Field(default=None, gt=0)

    # Session
    pinned_sessions: list[str] | None = None

    # Privacy
    notifications_enabled: bool | None = None

    # Keyboard Shortcuts
    keyboard_shortcuts: dict[str, str] | None = None


# ==============================================================================
# Storage
# ==============================================================================

# In-memory preferences store (user_id -> preferences dict)
_preferences_store: dict[str, dict[str, Any]] | None = None


def set_preferences_store(store: dict[str, dict[str, Any]] | None) -> None:
    """
    Set the preferences store.

    Used for dependency injection in tests.
    """
    global _preferences_store
    _preferences_store = store


def get_preferences_store() -> dict[str, dict[str, Any]]:
    """Get the preferences store."""
    global _preferences_store
    if _preferences_store is None:
        _preferences_store = {}
    return _preferences_store


# ==============================================================================
# Helper Functions
# ==============================================================================


def get_user_id(current_user: dict[str, Any]) -> str:
    """Extract user ID from authenticated user dict."""
    return current_user.get("user_id", "anonymous")


# ==============================================================================
# Type Aliases
# ==============================================================================

CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


# ==============================================================================
# Endpoints
# ==============================================================================


@user_preferences_router.get(
    "",
    response_model=UserPreferences,
    summary="Get user preferences",
    description="Get the current user's preferences. Returns defaults if not set.",
)
async def get_preferences(current_user: CurrentUser) -> UserPreferences:
    """Get current user's preferences."""
    user_id = get_user_id(current_user)
    store = get_preferences_store()

    # Get stored preferences or defaults
    stored = store.get(user_id, {})

    # Merge with defaults
    preferences_dict = {**DEFAULT_USER_PREFERENCES, **stored}

    return UserPreferences(**preferences_dict)


@user_preferences_router.patch(
    "",
    response_model=UserPreferences,
    summary="Update user preferences",
    description="Partially update the current user's preferences.",
)
async def update_preferences(
    current_user: CurrentUser,
    updates: UserPreferencesUpdate,
) -> UserPreferences:
    """Update current user's preferences."""
    user_id = get_user_id(current_user)
    store = get_preferences_store()

    # Get existing preferences
    existing = store.get(user_id, {**DEFAULT_USER_PREFERENCES})

    # Apply updates (only non-None values)
    update_dict = updates.model_dump(exclude_none=True)
    new_preferences = {**existing, **update_dict}

    # Store updated preferences
    store[user_id] = new_preferences

    logger.info(
        "Updated preferences for user",
        extra={"user_id": user_id, "updates": list(update_dict.keys())},
    )

    return UserPreferences(**new_preferences)


@user_preferences_router.delete(
    "",
    response_model=UserPreferences,
    summary="Reset user preferences",
    description="Reset the current user's preferences to defaults.",
)
async def reset_preferences(current_user: CurrentUser) -> UserPreferences:
    """Reset current user's preferences to defaults."""
    user_id = get_user_id(current_user)
    store = get_preferences_store()

    # Remove stored preferences
    if user_id in store:
        del store[user_id]

    logger.info("Reset preferences for user", extra={"user_id": user_id})

    return UserPreferences(**DEFAULT_USER_PREFERENCES)
