"""
E2E Integration Test: WebSocket Notification Data Flow

Tests the complete notification data flow:
    Producer (API) → NotificationBroadcaster → WebSocket Handler → Client

This test verifies that notifications are properly broadcast to subscribers,
catching wiring issues where notifications are created but not delivered.

Following memory safety patterns for pytest-xdist (see CLAUDE.md).
"""

import gc
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.notifications,
    pytest.mark.websocket,
    pytest.mark.asyncio,
    pytest.mark.xdist_group(name="websocket_notification_flow_e2e"),
]


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def unique_user_id() -> str:
    """Generate unique user ID for test isolation."""
    return f"user-{uuid4().hex[:8]}"


@pytest.fixture
def unique_notification_id() -> str:
    """Generate unique notification ID for test isolation."""
    return f"notif-{uuid4().hex[:8]}"


@pytest.fixture
def mock_websocket_connection():
    """Create a mock WebSocket connection."""
    connection = MagicMock()
    connection.send_json = AsyncMock()
    connection.close = AsyncMock()
    connection.accept = AsyncMock()
    return connection


@pytest.fixture
def create_notification_broadcaster():
    """Factory for creating test notification broadcasters."""
    from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

    def _create() -> NotificationBroadcaster:
        return NotificationBroadcaster()

    return _create


@pytest.fixture
def create_notification_preferences():
    """Factory for creating test notification preferences."""
    from mcp_server_langgraph.notifications.preferences import NotificationPreferences

    def _create(
        user_id: str,
        info_enabled: bool = True,
        success_enabled: bool = True,
        warning_enabled: bool = True,
        error_enabled: bool = True,
    ) -> NotificationPreferences:
        return NotificationPreferences(
            user_id=user_id,
            info_enabled=info_enabled,
            success_enabled=success_enabled,
            warning_enabled=warning_enabled,
            error_enabled=error_enabled,
        )

    return _create


# ============================================================================
# E2E WebSocket Notification Flow Tests
# ============================================================================


class TestNotificationBroadcasterFlow:
    """
    E2E tests for notification broadcaster core operations.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_subscribe_adds_connection(
        self,
        unique_user_id,
        mock_websocket_connection,
        create_notification_broadcaster,
    ):
        """
        E2E: Verify subscribe adds WebSocket to subscribers.

        GIVEN: A NotificationBroadcaster
        WHEN: A connection subscribes
        THEN: The subscriber count increases
        """
        broadcaster = create_notification_broadcaster()

        assert broadcaster.subscriber_count == 0

        await broadcaster.subscribe(
            connection=mock_websocket_connection,
            user_id=unique_user_id,
        )

        assert broadcaster.subscriber_count == 1

    async def test_unsubscribe_removes_connection(
        self,
        unique_user_id,
        mock_websocket_connection,
        create_notification_broadcaster,
    ):
        """
        E2E: Verify unsubscribe removes WebSocket from subscribers.

        GIVEN: A broadcaster with a subscriber
        WHEN: The connection unsubscribes
        THEN: The subscriber count decreases
        """
        broadcaster = create_notification_broadcaster()

        await broadcaster.subscribe(
            connection=mock_websocket_connection,
            user_id=unique_user_id,
        )
        assert broadcaster.subscriber_count == 1

        await broadcaster.unsubscribe(mock_websocket_connection)
        assert broadcaster.subscriber_count == 0

    async def test_broadcast_sends_to_all_subscribers(
        self,
        create_notification_broadcaster,
    ):
        """
        E2E: Verify broadcast sends to all subscribers.

        GIVEN: Multiple subscribed connections
        WHEN: A notification is broadcast
        THEN: All connections receive the message
        """
        broadcaster = create_notification_broadcaster()

        # Create multiple mock connections
        connections = [MagicMock() for i in range(3)]
        for i, conn in enumerate(connections):
            conn.send_json = AsyncMock()
            await broadcaster.subscribe(connection=conn, user_id=f"user-{i}")

        # Broadcast notification
        await broadcaster.broadcast(
            notification_type="info",
            title="System Update",
            message="The system will restart in 5 minutes",
        )

        # Verify all connections received the message
        for conn in connections:
            conn.send_json.assert_called_once()
            call_args = conn.send_json.call_args[0][0]
            assert call_args["type"] == "notification"
            assert call_args["payload"]["title"] == "System Update"


class TestNotificationTargetedDelivery:
    """
    E2E tests for targeted notification delivery.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_broadcast_to_user_targets_specific_user(
        self,
        unique_user_id,
        mock_websocket_connection,
        create_notification_broadcaster,
    ):
        """
        E2E: Verify broadcast_to_user only sends to target user.

        GIVEN: Multiple users subscribed
        WHEN: Notification is sent to specific user
        THEN: Only that user receives the message
        """
        broadcaster = create_notification_broadcaster()

        # Subscribe target user
        await broadcaster.subscribe(
            connection=mock_websocket_connection,
            user_id=unique_user_id,
        )

        # Subscribe other user
        other_connection = MagicMock()
        other_connection.send_json = AsyncMock()
        await broadcaster.subscribe(
            connection=other_connection,
            user_id="other-user",
        )

        # Send to target user only
        await broadcaster.broadcast_to_user(
            user_id=unique_user_id,
            notification_type="success",
            title="Personal Message",
            message="This is just for you",
        )

        # Target user received message
        mock_websocket_connection.send_json.assert_called_once()

        # Other user did NOT receive message
        other_connection.send_json.assert_not_called()

    async def test_broadcast_with_action(
        self,
        unique_user_id,
        mock_websocket_connection,
        create_notification_broadcaster,
    ):
        """
        E2E: Verify notification with action is properly formatted.

        GIVEN: A subscribed connection
        WHEN: Notification with action is sent
        THEN: The action is included in the payload
        """
        broadcaster = create_notification_broadcaster()

        await broadcaster.subscribe(
            connection=mock_websocket_connection,
            user_id=unique_user_id,
        )

        await broadcaster.broadcast_to_user(
            user_id=unique_user_id,
            notification_type="info",
            title="Workflow Shared",
            message="Alice shared a workflow with you",
            action={"label": "View Workflow", "url": "/workflows/123"},
        )

        call_args = mock_websocket_connection.send_json.call_args[0][0]
        assert call_args["payload"]["action"]["label"] == "View Workflow"
        assert call_args["payload"]["action"]["url"] == "/workflows/123"


class TestNotificationPreferencesFlow:
    """
    E2E tests for notification preferences filtering.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_preferences_filter_disabled_types(
        self,
        unique_user_id,
        create_notification_preferences,
    ):
        """
        E2E: Verify preferences filter disabled notification types.

        GIVEN: Preferences with info disabled
        WHEN: Checking if info should be sent
        THEN: Returns False
        """
        from mcp_server_langgraph.notifications.preferences import (
            should_send_notification,
            InMemoryPreferencesRepository,
        )

        prefs = create_notification_preferences(
            user_id=unique_user_id,
            info_enabled=False,
        )

        repository = InMemoryPreferencesRepository()
        await repository.save(prefs)

        # Info should NOT be sent
        should_send = await should_send_notification(
            repository=repository,
            user_id=unique_user_id,
            notification_type="info",
        )
        assert should_send is False

        # Warning should still be sent
        should_send = await should_send_notification(
            repository=repository,
            user_id=unique_user_id,
            notification_type="warning",
        )
        assert should_send is True

    async def test_broadcast_respects_preferences(
        self,
        unique_user_id,
        mock_websocket_connection,
        create_notification_broadcaster,
        create_notification_preferences,
    ):
        """
        E2E: Verify broadcast_with_preferences respects user settings.

        GIVEN: User with info notifications disabled
        WHEN: Info notification is sent with preferences
        THEN: User does NOT receive the notification
        """
        from mcp_server_langgraph.notifications.preferences import (
            InMemoryPreferencesRepository,
        )

        broadcaster = create_notification_broadcaster()
        repository = InMemoryPreferencesRepository()

        # Subscribe user
        await broadcaster.subscribe(
            connection=mock_websocket_connection,
            user_id=unique_user_id,
        )

        # Save preferences with info disabled
        prefs = create_notification_preferences(
            user_id=unique_user_id,
            info_enabled=False,
        )
        await repository.save(prefs)

        # Try to send info notification
        await broadcaster.broadcast_to_user_with_preferences(
            repository=repository,
            user_id=unique_user_id,
            notification_type="info",
            title="Info Message",
            message="This should be filtered",
        )

        # User should NOT receive message (filtered by preferences)
        mock_websocket_connection.send_json.assert_not_called()

    async def test_error_notifications_always_delivered(
        self,
        unique_user_id,
        mock_websocket_connection,
        create_notification_broadcaster,
        create_notification_preferences,
    ):
        """
        E2E: Verify error notifications are delivered even with restrictions.

        GIVEN: User with error notifications enabled
        WHEN: Error notification is sent
        THEN: User receives the notification
        """
        from mcp_server_langgraph.notifications.preferences import (
            InMemoryPreferencesRepository,
        )

        broadcaster = create_notification_broadcaster()
        repository = InMemoryPreferencesRepository()

        await broadcaster.subscribe(
            connection=mock_websocket_connection,
            user_id=unique_user_id,
        )

        # Preferences with only errors enabled
        prefs = create_notification_preferences(
            user_id=unique_user_id,
            info_enabled=False,
            success_enabled=False,
            warning_enabled=False,
            error_enabled=True,
        )
        await repository.save(prefs)

        # Send error notification
        await broadcaster.broadcast_to_user_with_preferences(
            repository=repository,
            user_id=unique_user_id,
            notification_type="error",
            title="Critical Error",
            message="Something went wrong",
        )

        # User SHOULD receive error
        mock_websocket_connection.send_json.assert_called_once()
        call_args = mock_websocket_connection.send_json.call_args[0][0]
        assert call_args["payload"]["type"] == "error"


class TestNotificationMessageFormat:
    """
    E2E tests for notification message format.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_notification_message_structure(
        self,
        unique_user_id,
        mock_websocket_connection,
        create_notification_broadcaster,
    ):
        """
        E2E: Verify notification message has correct structure.

        GIVEN: A subscribed connection
        WHEN: Notification is sent
        THEN: Message has type and payload fields
        """
        broadcaster = create_notification_broadcaster()

        await broadcaster.subscribe(
            connection=mock_websocket_connection,
            user_id=unique_user_id,
        )

        await broadcaster.broadcast(
            notification_type="warning",
            title="Warning Title",
            message="Warning message content",
        )

        call_args = mock_websocket_connection.send_json.call_args[0][0]

        # Verify structure
        assert "type" in call_args
        assert call_args["type"] == "notification"
        assert "payload" in call_args

        payload = call_args["payload"]
        assert payload["type"] == "warning"
        assert payload["title"] == "Warning Title"
        assert payload["message"] == "Warning message content"

    async def test_notification_types_validated(
        self,
        unique_user_id,
        mock_websocket_connection,
        create_notification_broadcaster,
    ):
        """
        E2E: Verify all notification types are valid.

        GIVEN: Valid notification types
        WHEN: Each type is sent
        THEN: All are accepted without error
        """
        broadcaster = create_notification_broadcaster()

        await broadcaster.subscribe(
            connection=mock_websocket_connection,
            user_id=unique_user_id,
        )

        valid_types = ["info", "success", "warning", "error"]

        for notification_type in valid_types:
            mock_websocket_connection.send_json.reset_mock()

            await broadcaster.broadcast(
                notification_type=notification_type,
                title=f"{notification_type.title()} Message",
                message=f"This is a {notification_type} notification",
            )

            mock_websocket_connection.send_json.assert_called_once()


class TestNotificationConnectionLifecycle:
    """
    E2E tests for WebSocket connection lifecycle.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_failed_send_removes_connection(
        self,
        unique_user_id,
        create_notification_broadcaster,
    ):
        """
        E2E: Verify failed sends remove dead connections.

        GIVEN: A connection that fails to receive
        WHEN: Broadcast is attempted
        THEN: The dead connection is removed
        """
        broadcaster = create_notification_broadcaster()

        # Create connection that fails
        failing_connection = MagicMock()
        failing_connection.send_json = AsyncMock(
            side_effect=ConnectionError("Connection closed")
        )

        await broadcaster.subscribe(
            connection=failing_connection,
            user_id=unique_user_id,
        )

        assert broadcaster.subscriber_count == 1

        # Broadcast (should fail)
        await broadcaster.broadcast(
            notification_type="info",
            title="Test",
            message="Test message",
        )

        # Connection should be removed
        assert broadcaster.subscriber_count == 0

    async def test_multiple_connections_same_user(
        self,
        unique_user_id,
        create_notification_broadcaster,
    ):
        """
        E2E: Verify user can have multiple connections.

        GIVEN: Same user with multiple devices/tabs
        WHEN: Notification is sent to user
        THEN: All connections receive the message
        """
        broadcaster = create_notification_broadcaster()

        # Create multiple connections for same user
        connections = [MagicMock() for _ in range(3)]
        for conn in connections:
            conn.send_json = AsyncMock()
            await broadcaster.subscribe(
                connection=conn,
                user_id=unique_user_id,
            )

        assert broadcaster.subscriber_count == 3

        # Send to user
        await broadcaster.broadcast_to_user(
            user_id=unique_user_id,
            notification_type="info",
            title="Multi-device",
            message="Should arrive on all devices",
        )

        # All connections received
        for conn in connections:
            conn.send_json.assert_called_once()


class TestPreferencesRepository:
    """
    E2E tests for preferences repository operations.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_in_memory_repository_crud(
        self,
        unique_user_id,
        create_notification_preferences,
    ):
        """
        E2E: Verify InMemoryPreferencesRepository CRUD operations.

        GIVEN: An in-memory preferences repository
        WHEN: Preferences are saved, retrieved, deleted
        THEN: All operations work correctly
        """
        from mcp_server_langgraph.notifications.preferences import (
            InMemoryPreferencesRepository,
        )

        repository = InMemoryPreferencesRepository()

        # Create
        prefs = create_notification_preferences(
            user_id=unique_user_id,
            warning_enabled=False,
        )
        await repository.save(prefs)

        # Read
        retrieved = await repository.get(unique_user_id)
        assert retrieved is not None
        assert retrieved.user_id == unique_user_id
        assert retrieved.warning_enabled is False

        # Delete
        await repository.delete(unique_user_id)
        deleted = await repository.get(unique_user_id)
        assert deleted is None

    async def test_get_or_default_returns_defaults(
        self,
        unique_user_id,
    ):
        """
        E2E: Verify get_or_default returns defaults for new user.

        GIVEN: A user with no saved preferences
        WHEN: get_or_default is called
        THEN: Default preferences are returned (all enabled)
        """
        from mcp_server_langgraph.notifications.preferences import (
            InMemoryPreferencesRepository,
        )

        repository = InMemoryPreferencesRepository()

        prefs = await repository.get_or_default(unique_user_id)

        assert prefs.user_id == unique_user_id
        assert prefs.info_enabled is True
        assert prefs.success_enabled is True
        assert prefs.warning_enabled is True
        assert prefs.error_enabled is True
