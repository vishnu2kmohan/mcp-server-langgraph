"""
Notification Preferences API Endpoints.

REST API for managing user notification preferences.

Endpoints:
- GET /notifications/preferences - Get current user's preferences
- PUT /notifications/preferences - Update preferences
- POST /notifications/preferences/reset - Reset to defaults

Authentication:
- Uses Keycloak JWT authentication via get_current_user dependency
- User ID extracted from JWT claims
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.middleware import get_current_user
from mcp_server_langgraph.notifications.preferences import (
    InMemoryPreferencesRepository,
    NotificationPreferences,
    PreferencesRepository,
)

logger = logging.getLogger(__name__)

notification_preferences_router = APIRouter(
    prefix="/notifications/preferences",
    tags=["notifications", "preferences"],
)

# Type alias for authenticated user dependency
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]

# Global preferences repository (set via dependency injection)
_preferences_repository: PreferencesRepository | None = None


def set_preferences_repository(repository: PreferencesRepository | None) -> None:
    """
    Set the global preferences repository.

    Used for dependency injection in production and testing.

    Args:
        repository: The preferences repository to use.
    """
    global _preferences_repository
    _preferences_repository = repository


def get_preferences_repository() -> PreferencesRepository:
    """
    Get the preferences repository.

    Returns:
        The configured preferences repository.
    """
    if _preferences_repository is None:
        logger.warning("No preferences repository configured, using in-memory fallback")
        return InMemoryPreferencesRepository()
    return _preferences_repository


def get_current_user_id(current_user: dict[str, Any]) -> str:
    """
    Extract user ID from authenticated user dict.

    The get_current_user dependency returns a dict with 'user_id' already
    in "user:username" format from JWT claims.

    Args:
        current_user: User dict from get_current_user dependency.

    Returns:
        The user's ID in "user:username" format.
    """
    user_id = current_user.get("user_id", current_user.get("sub", "anonymous"))
    return str(user_id) if user_id else "anonymous"


class PreferencesResponse(BaseModel):
    """Response model for notification preferences."""

    user_id: str = Field(..., description="User identifier")
    info_enabled: bool = Field(..., description="Receive info notifications")
    success_enabled: bool = Field(..., description="Receive success notifications")
    warning_enabled: bool = Field(..., description="Receive warning notifications")
    error_enabled: bool = Field(..., description="Receive error notifications")


class PreferencesUpdateRequest(BaseModel):
    """Request model for updating preferences."""

    info_enabled: bool | None = Field(None, description="Receive info notifications")
    success_enabled: bool | None = Field(None, description="Receive success notifications")
    warning_enabled: bool | None = Field(None, description="Receive warning notifications")
    error_enabled: bool | None = Field(None, description="Receive error notifications")


@notification_preferences_router.get(
    "",
    response_model=PreferencesResponse,
    summary="Get notification preferences",
    description="Get the current user's notification preferences.",
)
async def get_preferences(current_user: CurrentUser) -> PreferencesResponse:
    """
    Get the current user's notification preferences.

    Returns default preferences if none are saved.
    """
    user_id = get_current_user_id(current_user)
    repo = get_preferences_repository()

    prefs = await repo.get_or_default(user_id)

    return PreferencesResponse(
        user_id=prefs.user_id,
        info_enabled=prefs.info_enabled,
        success_enabled=prefs.success_enabled,
        warning_enabled=prefs.warning_enabled,
        error_enabled=prefs.error_enabled,
    )


@notification_preferences_router.put(
    "",
    response_model=PreferencesResponse,
    summary="Update notification preferences",
    description="Update the current user's notification preferences.",
)
async def update_preferences(
    request: PreferencesUpdateRequest,
    current_user: CurrentUser,
) -> PreferencesResponse:
    """
    Update the current user's notification preferences.

    Supports partial updates - only provided fields are changed.
    """
    user_id = get_current_user_id(current_user)
    repo = get_preferences_repository()

    # Get existing preferences or defaults
    existing = await repo.get_or_default(user_id)

    # Merge with updates (partial update)
    updated = NotificationPreferences(
        user_id=user_id,
        info_enabled=request.info_enabled if request.info_enabled is not None else existing.info_enabled,
        success_enabled=request.success_enabled if request.success_enabled is not None else existing.success_enabled,
        warning_enabled=request.warning_enabled if request.warning_enabled is not None else existing.warning_enabled,
        error_enabled=request.error_enabled if request.error_enabled is not None else existing.error_enabled,
    )

    # Save updated preferences
    await repo.save(updated)

    logger.info(f"Updated notification preferences for user: {user_id}")

    return PreferencesResponse(
        user_id=updated.user_id,
        info_enabled=updated.info_enabled,
        success_enabled=updated.success_enabled,
        warning_enabled=updated.warning_enabled,
        error_enabled=updated.error_enabled,
    )


@notification_preferences_router.post(
    "/reset",
    response_model=PreferencesResponse,
    summary="Reset notification preferences",
    description="Reset the current user's notification preferences to defaults.",
)
async def reset_preferences(current_user: CurrentUser) -> PreferencesResponse:
    """
    Reset the current user's notification preferences to defaults.

    Deletes any custom preferences and returns default values.
    """
    user_id = get_current_user_id(current_user)
    repo = get_preferences_repository()

    # Delete existing preferences
    await repo.delete(user_id)

    # Return defaults
    defaults = NotificationPreferences.default(user_id=user_id)

    logger.info(f"Reset notification preferences for user: {user_id}")

    return PreferencesResponse(
        user_id=defaults.user_id,
        info_enabled=defaults.info_enabled,
        success_enabled=defaults.success_enabled,
        warning_enabled=defaults.warning_enabled,
        error_enabled=defaults.error_enabled,
    )
