"""
Broadcaster Preferences Integration Tests.

TDD tests for NotificationBroadcaster with preferences filtering.
Tests verify that:
- Broadcaster respects user notification preferences
- Disabled notification types are not sent to users
- System-wide broadcasts bypass preferences (optional)
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.asyncio,
]


class MockWebSocket:
    """Mock WebSocket connection for testing."""

    def __init__(self) -> None:
        self.sent_messages: list[dict[str, Any]] = []
        self.send_json = AsyncMock(side_effect=self._track_message)

    async def _track_message(self, data: dict[str, Any]) -> None:
        self.sent_messages.append(data)


class TestBroadcasterWithPreferencesIntegration:
    """Tests for broadcaster integration with preferences."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_broadcast_to_user_respects_disabled_preference(self) -> None:
        """
        GIVEN a user with info notifications disabled
        WHEN broadcasting an info notification to that user
        THEN the notification should not be sent.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster
        from mcp_server_langgraph.notifications.preferences import (
            InMemoryPreferencesRepository,
            NotificationPreferences,
        )

        # Setup
        broadcaster = NotificationBroadcaster()
        repo = InMemoryPreferencesRepository()

        # Disable info notifications for alice
        prefs = NotificationPreferences(
            user_id="user:alice",
            info_enabled=False,
            success_enabled=True,
            warning_enabled=True,
            error_enabled=True,
        )
        await repo.save(prefs)

        # Subscribe alice
        ws = MockWebSocket()
        await broadcaster.subscribe(ws, user_id="user:alice")

        # Broadcast info notification
        await broadcaster.broadcast_to_user_with_preferences(
            repository=repo,
            user_id="user:alice",
            notification_type="info",
            title="Test",
            message="This should not be sent",
        )

        # Verify notification was NOT sent
        assert len(ws.sent_messages) == 0

    async def test_broadcast_to_user_sends_enabled_notification(self) -> None:
        """
        GIVEN a user with success notifications enabled
        WHEN broadcasting a success notification to that user
        THEN the notification should be sent.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster
        from mcp_server_langgraph.notifications.preferences import (
            InMemoryPreferencesRepository,
            NotificationPreferences,
        )

        # Setup
        broadcaster = NotificationBroadcaster()
        repo = InMemoryPreferencesRepository()

        # Enable success notifications for alice
        prefs = NotificationPreferences(
            user_id="user:alice",
            info_enabled=False,
            success_enabled=True,
            warning_enabled=True,
            error_enabled=True,
        )
        await repo.save(prefs)

        # Subscribe alice
        ws = MockWebSocket()
        await broadcaster.subscribe(ws, user_id="user:alice")

        # Broadcast success notification
        await broadcaster.broadcast_to_user_with_preferences(
            repository=repo,
            user_id="user:alice",
            notification_type="success",
            title="Great!",
            message="This should be sent",
        )

        # Verify notification was sent
        assert len(ws.sent_messages) == 1
        assert ws.sent_messages[0]["payload"]["type"] == "success"
        assert ws.sent_messages[0]["payload"]["title"] == "Great!"

    async def test_broadcast_to_user_uses_defaults_for_new_user(self) -> None:
        """
        GIVEN a user with no saved preferences
        WHEN broadcasting a notification to that user
        THEN the notification should be sent (defaults are all enabled).
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster
        from mcp_server_langgraph.notifications.preferences import InMemoryPreferencesRepository

        # Setup
        broadcaster = NotificationBroadcaster()
        repo = InMemoryPreferencesRepository()
        # No preferences saved for alice

        # Subscribe alice
        ws = MockWebSocket()
        await broadcaster.subscribe(ws, user_id="user:alice")

        # Broadcast info notification
        await broadcaster.broadcast_to_user_with_preferences(
            repository=repo,
            user_id="user:alice",
            notification_type="info",
            title="Default",
            message="Should be sent with default preferences",
        )

        # Verify notification was sent (defaults enable all)
        assert len(ws.sent_messages) == 1

    async def test_broadcast_all_ignores_preferences(self) -> None:
        """
        GIVEN users with various preferences
        WHEN using broadcast() (system-wide)
        THEN all subscribers receive the notification regardless of preferences.

        Note: System-wide broadcasts (like maintenance notices) bypass user preferences.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        # Setup
        broadcaster = NotificationBroadcaster()

        # Subscribe alice with info disabled
        alice_ws = MockWebSocket()
        await broadcaster.subscribe(alice_ws, user_id="user:alice")

        # Broadcast system-wide (uses original broadcast method, no preferences)
        await broadcaster.broadcast(
            notification_type="info",
            title="System Notice",
            message="Maintenance in 5 minutes",
        )

        # Verify alice still received it (system broadcast bypasses preferences)
        assert len(alice_ws.sent_messages) == 1
        assert alice_ws.sent_messages[0]["payload"]["title"] == "System Notice"

    async def test_broadcast_to_multiple_users_filters_per_user(self) -> None:
        """
        GIVEN multiple users with different preferences
        WHEN broadcasting to each
        THEN only users with enabled preferences receive notifications.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster
        from mcp_server_langgraph.notifications.preferences import (
            InMemoryPreferencesRepository,
            NotificationPreferences,
        )

        # Setup
        broadcaster = NotificationBroadcaster()
        repo = InMemoryPreferencesRepository()

        # Alice has info disabled
        await repo.save(
            NotificationPreferences(
                user_id="user:alice",
                info_enabled=False,
                success_enabled=True,
                warning_enabled=True,
                error_enabled=True,
            )
        )

        # Bob has info enabled
        await repo.save(
            NotificationPreferences(
                user_id="user:bob",
                info_enabled=True,
                success_enabled=True,
                warning_enabled=True,
                error_enabled=True,
            )
        )

        # Subscribe both
        alice_ws = MockWebSocket()
        bob_ws = MockWebSocket()
        await broadcaster.subscribe(alice_ws, user_id="user:alice")
        await broadcaster.subscribe(bob_ws, user_id="user:bob")

        # Broadcast to alice (should not receive)
        await broadcaster.broadcast_to_user_with_preferences(
            repository=repo,
            user_id="user:alice",
            notification_type="info",
            title="For Alice",
            message="Alice has info disabled",
        )

        # Broadcast to bob (should receive)
        await broadcaster.broadcast_to_user_with_preferences(
            repository=repo,
            user_id="user:bob",
            notification_type="info",
            title="For Bob",
            message="Bob has info enabled",
        )

        # Verify
        assert len(alice_ws.sent_messages) == 0
        assert len(bob_ws.sent_messages) == 1
        assert bob_ws.sent_messages[0]["payload"]["title"] == "For Bob"


class TestNotifyUserConvenienceMethod:
    """Tests for the notify_user() convenience method."""

    def teardown_method(self) -> None:
        """Force GC and reset global preferences repository."""
        from mcp_server_langgraph.api.v1.notification_preferences import set_preferences_repository

        set_preferences_repository(None)
        gc.collect()

    async def test_notify_user_uses_global_preferences_repository(self) -> None:
        """
        GIVEN a global preferences repository configured
        WHEN calling notify_user()
        THEN it should use the global repository for preference checks.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster
        from mcp_server_langgraph.notifications.preferences import (
            InMemoryPreferencesRepository,
            NotificationPreferences,
        )
        from mcp_server_langgraph.api.v1.notification_preferences import set_preferences_repository

        # Setup global repository with alice's preferences
        repo = InMemoryPreferencesRepository()
        prefs = NotificationPreferences(
            user_id="user:alice",
            info_enabled=False,  # Disable info
            success_enabled=True,
            warning_enabled=True,
            error_enabled=True,
        )
        await repo.save(prefs)
        set_preferences_repository(repo)

        # Setup broadcaster
        broadcaster = NotificationBroadcaster()
        ws = MockWebSocket()
        await broadcaster.subscribe(ws, user_id="user:alice")

        # Use notify_user (should respect preferences)
        await broadcaster.notify_user(
            user_id="user:alice",
            notification_type="info",
            title="Test Info",
            message="Should not be sent (info disabled)",
        )

        # Verify notification was NOT sent (info disabled)
        assert len(ws.sent_messages) == 0

    async def test_notify_user_sends_enabled_notification_type(self) -> None:
        """
        GIVEN a global preferences repository with success enabled
        WHEN calling notify_user() with success type
        THEN the notification should be sent.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster
        from mcp_server_langgraph.notifications.preferences import (
            InMemoryPreferencesRepository,
            NotificationPreferences,
        )
        from mcp_server_langgraph.api.v1.notification_preferences import set_preferences_repository

        # Setup global repository
        repo = InMemoryPreferencesRepository()
        prefs = NotificationPreferences(
            user_id="user:alice",
            info_enabled=False,
            success_enabled=True,  # Enable success
            warning_enabled=True,
            error_enabled=True,
        )
        await repo.save(prefs)
        set_preferences_repository(repo)

        # Setup broadcaster
        broadcaster = NotificationBroadcaster()
        ws = MockWebSocket()
        await broadcaster.subscribe(ws, user_id="user:alice")

        # Use notify_user with success type
        await broadcaster.notify_user(
            user_id="user:alice",
            notification_type="success",
            title="Success!",
            message="This should be sent",
        )

        # Verify notification was sent
        assert len(ws.sent_messages) == 1
        assert ws.sent_messages[0]["payload"]["type"] == "success"
        assert ws.sent_messages[0]["payload"]["title"] == "Success!"

    async def test_notify_user_works_with_default_preferences(self) -> None:
        """
        GIVEN no preferences saved for user
        WHEN calling notify_user()
        THEN notification should be sent (defaults enable all).
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster
        from mcp_server_langgraph.notifications.preferences import InMemoryPreferencesRepository
        from mcp_server_langgraph.api.v1.notification_preferences import set_preferences_repository

        # Setup global repository with no preferences for alice
        repo = InMemoryPreferencesRepository()
        set_preferences_repository(repo)

        # Setup broadcaster
        broadcaster = NotificationBroadcaster()
        ws = MockWebSocket()
        await broadcaster.subscribe(ws, user_id="user:alice")

        # Use notify_user
        await broadcaster.notify_user(
            user_id="user:alice",
            notification_type="info",
            title="Default Test",
            message="Should be sent with default preferences",
        )

        # Verify notification was sent (defaults enable all)
        assert len(ws.sent_messages) == 1
