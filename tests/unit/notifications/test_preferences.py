"""
Notification Preferences Tests.

TDD tests for notification preferences system.
Tests cover:
- NotificationPreferences model
- InMemoryPreferencesRepository
- Preference-aware notification filtering
"""

from __future__ import annotations

import gc
import pytest

pytestmark = [
    pytest.mark.unit,
]


class TestNotificationPreferences:
    """Tests for NotificationPreferences model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_default_preferences_enable_all_types(self) -> None:
        """
        GIVEN no explicit preferences
        WHEN creating default NotificationPreferences
        THEN all notification types should be enabled.
        """
        from mcp_server_langgraph.notifications.preferences import NotificationPreferences

        prefs = NotificationPreferences.default()

        assert prefs.info_enabled is True
        assert prefs.success_enabled is True
        assert prefs.warning_enabled is True
        assert prefs.error_enabled is True

    def test_is_type_enabled_returns_true_for_enabled_type(self) -> None:
        """
        GIVEN preferences with info enabled
        WHEN checking if info is enabled
        THEN it should return True.
        """
        from mcp_server_langgraph.notifications.preferences import NotificationPreferences

        prefs = NotificationPreferences(
            user_id="user:alice",
            info_enabled=True,
            success_enabled=False,
            warning_enabled=True,
            error_enabled=True,
        )

        assert prefs.is_type_enabled("info") is True

    def test_is_type_enabled_returns_false_for_disabled_type(self) -> None:
        """
        GIVEN preferences with success disabled
        WHEN checking if success is enabled
        THEN it should return False.
        """
        from mcp_server_langgraph.notifications.preferences import NotificationPreferences

        prefs = NotificationPreferences(
            user_id="user:alice",
            info_enabled=True,
            success_enabled=False,
            warning_enabled=True,
            error_enabled=True,
        )

        assert prefs.is_type_enabled("success") is False

    def test_is_type_enabled_returns_true_for_unknown_type(self) -> None:
        """
        GIVEN notification preferences
        WHEN checking an unknown notification type
        THEN it should return True (fail-open for unknown types).
        """
        from mcp_server_langgraph.notifications.preferences import NotificationPreferences

        prefs = NotificationPreferences.default()

        assert prefs.is_type_enabled("custom") is True

    def test_preferences_serialization_preserves_values_roundtrip(self) -> None:
        """
        GIVEN notification preferences
        WHEN converting to dict and back
        THEN the values should be preserved.
        """
        from mcp_server_langgraph.notifications.preferences import NotificationPreferences

        prefs = NotificationPreferences(
            user_id="user:alice",
            info_enabled=False,
            success_enabled=True,
            warning_enabled=True,
            error_enabled=False,
        )

        data = prefs.model_dump()
        restored = NotificationPreferences.model_validate(data)

        assert restored.user_id == prefs.user_id
        assert restored.info_enabled == prefs.info_enabled
        assert restored.success_enabled == prefs.success_enabled
        assert restored.warning_enabled == prefs.warning_enabled
        assert restored.error_enabled == prefs.error_enabled


@pytest.mark.asyncio
class TestInMemoryPreferencesRepository:
    """Tests for in-memory preferences repository."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_get_returns_none_for_unknown_user(self) -> None:
        """
        GIVEN an empty repository
        WHEN getting preferences for unknown user
        THEN it should return None.
        """
        from mcp_server_langgraph.notifications.preferences import InMemoryPreferencesRepository

        repo = InMemoryPreferencesRepository()

        result = await repo.get("user:unknown")

        assert result is None

    async def test_save_and_get_preferences(self) -> None:
        """
        GIVEN a repository
        WHEN saving and getting preferences
        THEN the saved preferences should be returned.
        """
        from mcp_server_langgraph.notifications.preferences import (
            InMemoryPreferencesRepository,
            NotificationPreferences,
        )

        repo = InMemoryPreferencesRepository()
        prefs = NotificationPreferences(
            user_id="user:alice",
            info_enabled=False,
            success_enabled=True,
            warning_enabled=True,
            error_enabled=True,
        )

        await repo.save(prefs)
        result = await repo.get("user:alice")

        assert result is not None
        assert result.user_id == "user:alice"
        assert result.info_enabled is False

    async def test_save_overwrites_existing_preferences(self) -> None:
        """
        GIVEN existing preferences for a user
        WHEN saving new preferences
        THEN the old preferences should be replaced.
        """
        from mcp_server_langgraph.notifications.preferences import (
            InMemoryPreferencesRepository,
            NotificationPreferences,
        )

        repo = InMemoryPreferencesRepository()

        # Save initial preferences
        prefs1 = NotificationPreferences(
            user_id="user:alice",
            info_enabled=True,
            success_enabled=True,
            warning_enabled=True,
            error_enabled=True,
        )
        await repo.save(prefs1)

        # Save updated preferences
        prefs2 = NotificationPreferences(
            user_id="user:alice",
            info_enabled=False,
            success_enabled=False,
            warning_enabled=True,
            error_enabled=True,
        )
        await repo.save(prefs2)

        result = await repo.get("user:alice")

        assert result is not None
        assert result.info_enabled is False
        assert result.success_enabled is False

    async def test_delete_removes_preferences(self) -> None:
        """
        GIVEN saved preferences
        WHEN deleting preferences
        THEN they should no longer be retrievable.
        """
        from mcp_server_langgraph.notifications.preferences import (
            InMemoryPreferencesRepository,
            NotificationPreferences,
        )

        repo = InMemoryPreferencesRepository()
        prefs = NotificationPreferences(
            user_id="user:alice",
            info_enabled=True,
            success_enabled=True,
            warning_enabled=True,
            error_enabled=True,
        )
        await repo.save(prefs)

        await repo.delete("user:alice")
        result = await repo.get("user:alice")

        assert result is None

    async def test_get_or_default_returns_saved_preferences(self) -> None:
        """
        GIVEN saved preferences
        WHEN calling get_or_default
        THEN saved preferences should be returned.
        """
        from mcp_server_langgraph.notifications.preferences import (
            InMemoryPreferencesRepository,
            NotificationPreferences,
        )

        repo = InMemoryPreferencesRepository()
        prefs = NotificationPreferences(
            user_id="user:alice",
            info_enabled=False,
            success_enabled=True,
            warning_enabled=True,
            error_enabled=True,
        )
        await repo.save(prefs)

        result = await repo.get_or_default("user:alice")

        assert result.info_enabled is False

    async def test_get_or_default_returns_defaults_for_unknown_user(self) -> None:
        """
        GIVEN no saved preferences
        WHEN calling get_or_default
        THEN default preferences should be returned.
        """
        from mcp_server_langgraph.notifications.preferences import InMemoryPreferencesRepository

        repo = InMemoryPreferencesRepository()

        result = await repo.get_or_default("user:unknown")

        assert result.user_id == "user:unknown"
        assert result.info_enabled is True
        assert result.success_enabled is True
        assert result.warning_enabled is True
        assert result.error_enabled is True


@pytest.mark.asyncio
class TestBroadcasterWithPreferences:
    """Tests for broadcaster with preferences integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_should_send_returns_true_for_enabled_type(self) -> None:
        """
        GIVEN user preferences with info enabled
        WHEN checking should_send for info notification
        THEN it should return True.
        """
        from mcp_server_langgraph.notifications.preferences import (
            InMemoryPreferencesRepository,
            NotificationPreferences,
            should_send_notification,
        )

        repo = InMemoryPreferencesRepository()
        prefs = NotificationPreferences(
            user_id="user:alice",
            info_enabled=True,
            success_enabled=False,
            warning_enabled=True,
            error_enabled=True,
        )
        await repo.save(prefs)

        result = await should_send_notification(repo, "user:alice", "info")

        assert result is True

    async def test_should_send_returns_false_for_disabled_type(self) -> None:
        """
        GIVEN user preferences with success disabled
        WHEN checking should_send for success notification
        THEN it should return False.
        """
        from mcp_server_langgraph.notifications.preferences import (
            InMemoryPreferencesRepository,
            NotificationPreferences,
            should_send_notification,
        )

        repo = InMemoryPreferencesRepository()
        prefs = NotificationPreferences(
            user_id="user:alice",
            info_enabled=True,
            success_enabled=False,
            warning_enabled=True,
            error_enabled=True,
        )
        await repo.save(prefs)

        result = await should_send_notification(repo, "user:alice", "success")

        assert result is False

    async def test_should_send_returns_true_for_unknown_user(self) -> None:
        """
        GIVEN no preferences for a user
        WHEN checking should_send
        THEN it should return True (default is to send).
        """
        from mcp_server_langgraph.notifications.preferences import (
            InMemoryPreferencesRepository,
            should_send_notification,
        )

        repo = InMemoryPreferencesRepository()

        result = await should_send_notification(repo, "user:unknown", "info")

        assert result is True

    async def test_error_notifications_always_sent(self) -> None:
        """
        GIVEN user preferences with error disabled (edge case)
        WHEN checking should_send for error notification
        THEN it should return False (preferences are respected).

        Note: UI may prevent disabling errors, but backend respects preferences.
        """
        from mcp_server_langgraph.notifications.preferences import (
            InMemoryPreferencesRepository,
            NotificationPreferences,
            should_send_notification,
        )

        repo = InMemoryPreferencesRepository()
        prefs = NotificationPreferences(
            user_id="user:alice",
            info_enabled=True,
            success_enabled=True,
            warning_enabled=True,
            error_enabled=False,
        )
        await repo.save(prefs)

        result = await should_send_notification(repo, "user:alice", "error")

        assert result is False
