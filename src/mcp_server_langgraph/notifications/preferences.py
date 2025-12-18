"""
Notification Preferences System.

Manages user preferences for notification types.
Users can enable/disable specific notification types (info, success, warning, error).

Features:
- NotificationPreferences model with type-specific toggles
- InMemoryPreferencesRepository for development/testing
- Preference-aware filtering for notification broadcasts
- Default preferences (all enabled)

Usage:
    from mcp_server_langgraph.notifications.preferences import (
        NotificationPreferences,
        InMemoryPreferencesRepository,
        should_send_notification,
    )

    repo = InMemoryPreferencesRepository()

    # Save user preferences
    prefs = NotificationPreferences(
        user_id="user:alice",
        info_enabled=True,
        success_enabled=False,  # Disable success notifications
        warning_enabled=True,
        error_enabled=True,
    )
    await repo.save(prefs)

    # Check before sending
    if await should_send_notification(repo, "user:alice", "success"):
        # Send notification
        ...
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass  # Future TYPE_CHECKING-only imports

logger = logging.getLogger(__name__)


class NotificationPreferences(BaseModel):
    """
    User notification preferences.

    Controls which notification types a user receives.
    All types are enabled by default.

    Attributes:
        user_id: The user's unique identifier.
        info_enabled: Whether to receive info notifications.
        success_enabled: Whether to receive success notifications.
        warning_enabled: Whether to receive warning notifications.
        error_enabled: Whether to receive error notifications.
    """

    user_id: str = Field(..., description="User identifier")
    info_enabled: bool = Field(default=True, description="Receive info notifications")
    success_enabled: bool = Field(default=True, description="Receive success notifications")
    warning_enabled: bool = Field(default=True, description="Receive warning notifications")
    error_enabled: bool = Field(default=True, description="Receive error notifications")

    @classmethod
    def default(cls, user_id: str = "anonymous") -> NotificationPreferences:
        """
        Create default preferences with all types enabled.

        Args:
            user_id: The user ID for the preferences.

        Returns:
            NotificationPreferences with all types enabled.
        """
        return cls(
            user_id=user_id,
            info_enabled=True,
            success_enabled=True,
            warning_enabled=True,
            error_enabled=True,
        )

    def is_type_enabled(self, notification_type: str) -> bool:
        """
        Check if a notification type is enabled.

        Args:
            notification_type: The notification type to check.

        Returns:
            True if the type is enabled, True for unknown types (fail-open).
        """
        type_map = {
            "info": self.info_enabled,
            "success": self.success_enabled,
            "warning": self.warning_enabled,
            "error": self.error_enabled,
        }
        # Fail-open for unknown types (send by default)
        return type_map.get(notification_type, True)


class PreferencesRepository(ABC):
    """
    Abstract base class for notification preferences storage.

    Implementations can use different backends (in-memory, Redis, PostgreSQL, etc.).
    """

    @abstractmethod
    async def get(self, user_id: str) -> NotificationPreferences | None:
        """
        Get preferences for a user.

        Args:
            user_id: The user ID to look up.

        Returns:
            The user's preferences, or None if not found.
        """
        ...

    @abstractmethod
    async def save(self, preferences: NotificationPreferences) -> None:
        """
        Save user preferences.

        Args:
            preferences: The preferences to save.
        """
        ...

    @abstractmethod
    async def delete(self, user_id: str) -> None:
        """
        Delete preferences for a user.

        Args:
            user_id: The user ID to delete preferences for.
        """
        ...

    async def get_or_default(self, user_id: str) -> NotificationPreferences:
        """
        Get preferences for a user, or default if not found.

        Args:
            user_id: The user ID to look up.

        Returns:
            The user's preferences, or default preferences.
        """
        prefs = await self.get(user_id)
        if prefs is None:
            return NotificationPreferences.default(user_id=user_id)
        return prefs


class InMemoryPreferencesRepository(PreferencesRepository):
    """
    In-memory preferences repository for development and testing.

    Not suitable for production as data is not persisted.
    """

    def __init__(self) -> None:
        """Initialize the repository."""
        self._preferences: dict[str, NotificationPreferences] = {}

    async def get(self, user_id: str) -> NotificationPreferences | None:
        """Get preferences for a user."""
        return self._preferences.get(user_id)

    async def save(self, preferences: NotificationPreferences) -> None:
        """Save user preferences."""
        self._preferences[preferences.user_id] = preferences
        logger.debug(f"Saved notification preferences for user: {preferences.user_id}")

    async def delete(self, user_id: str) -> None:
        """Delete preferences for a user."""
        if user_id in self._preferences:
            del self._preferences[user_id]
            logger.debug(f"Deleted notification preferences for user: {user_id}")


class RedisPreferencesRepository(PreferencesRepository):
    """
    Redis-backed preferences repository for production use.

    Stores preferences as JSON strings in Redis with configurable key prefix.
    Provides graceful degradation on connection errors.

    Args:
        redis_client: Async Redis client instance.
        key_prefix: Prefix for Redis keys (default: "notification_preferences:").
    """

    def __init__(
        self,
        redis_client: Any,
        key_prefix: str = "notification_preferences:",
    ) -> None:
        """Initialize the Redis repository."""
        self._redis = redis_client
        self._key_prefix = key_prefix

    def _make_key(self, user_id: str) -> str:
        """Create Redis key for user preferences."""
        return f"{self._key_prefix}{user_id}"

    async def get(self, user_id: str) -> NotificationPreferences | None:
        """
        Get preferences for a user from Redis.

        Returns None if not found or on error (graceful degradation).
        """
        import json

        key = self._make_key(user_id)
        try:
            data = await self._redis.get(key)
            if data is None:
                return None

            # Parse JSON and validate
            parsed = json.loads(data)
            return NotificationPreferences.model_validate(parsed)
        except json.JSONDecodeError as e:
            logger.warning(f"Malformed JSON for preferences key {key}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to get preferences from Redis: {e}")
            return None

    async def save(self, preferences: NotificationPreferences) -> None:
        """
        Save user preferences to Redis.

        Logs warning on error but does not raise (graceful degradation).
        """
        import json

        key = self._make_key(preferences.user_id)
        try:
            data = json.dumps(preferences.model_dump())
            await self._redis.set(key, data)
            logger.debug(f"Saved notification preferences to Redis for user: {preferences.user_id}")
        except Exception as e:
            logger.warning(f"Failed to save preferences to Redis: {e}")

    async def delete(self, user_id: str) -> None:
        """
        Delete preferences for a user from Redis.

        Logs warning on error but does not raise (graceful degradation).
        """
        key = self._make_key(user_id)
        try:
            await self._redis.delete(key)
            logger.debug(f"Deleted notification preferences from Redis for user: {user_id}")
        except Exception as e:
            logger.warning(f"Failed to delete preferences from Redis: {e}")


async def should_send_notification(
    repository: PreferencesRepository,
    user_id: str,
    notification_type: str,
) -> bool:
    """
    Check if a notification should be sent based on user preferences.

    Args:
        repository: The preferences repository.
        user_id: The user to check preferences for.
        notification_type: The type of notification.

    Returns:
        True if the notification should be sent, False otherwise.
    """
    preferences = await repository.get_or_default(user_id)
    return preferences.is_type_enabled(notification_type)
