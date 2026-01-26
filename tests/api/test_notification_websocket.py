"""
Tests for NotificationBroadcaster.

Tests for the core notification broadcasting functionality used by
real-time notification streaming via WebSocket.

The NotificationBroadcaster should:
- Manage WebSocket subscriptions for multiple clients
- Broadcast notifications in format: { type: "notification", payload: { type, title, message } }
- Support targeted notifications to specific users
- Handle disconnected subscribers gracefully

Note: Tests for the WebSocket endpoint itself are in tests/unit/websocket_pkg/handlers/test_notification_handler.py
"""

import gc
from unittest.mock import AsyncMock

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.api]


@pytest.mark.api
@pytest.mark.xdist_group(name="notification_broadcaster")
class TestNotificationBroadcaster:
    """Tests for NotificationBroadcaster."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcaster_add_subscriber(self) -> None:
        """
        GIVEN a broadcaster
        WHEN adding a subscriber
        THEN subscriber is registered.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()
        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config

        await broadcaster.subscribe(mock_ws)

        assert broadcaster.subscriber_count == 1

    @pytest.mark.asyncio
    async def test_broadcaster_remove_subscriber(self) -> None:
        """
        GIVEN a broadcaster with subscriber
        WHEN removing subscriber
        THEN subscriber is unregistered.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()
        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config

        await broadcaster.subscribe(mock_ws)
        await broadcaster.unsubscribe(mock_ws)

        assert broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_broadcaster_broadcast_notification(self) -> None:
        """
        GIVEN subscribers
        WHEN broadcasting notification
        THEN all subscribers receive notification in correct format.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()
        mock_ws1 = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_ws2 = AsyncMock(return_value=None)  # noqa: async-mock-config

        await broadcaster.subscribe(mock_ws1)
        await broadcaster.subscribe(mock_ws2)

        # Broadcast a notification
        await broadcaster.broadcast(
            notification_type="success",
            title="Session Created",
            message="Your session has been created successfully.",
        )

        # Verify both subscribers received the notification in correct format
        expected_message = {
            "type": "notification",
            "payload": {
                "type": "success",
                "title": "Session Created",
                "message": "Your session has been created successfully.",
            },
        }
        mock_ws1.send_json.assert_called_once_with(expected_message)
        mock_ws2.send_json.assert_called_once_with(expected_message)

    @pytest.mark.asyncio
    async def test_broadcaster_broadcast_with_action(self) -> None:
        """
        GIVEN subscribers
        WHEN broadcasting notification with action
        THEN all subscribers receive notification with action.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()
        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config

        await broadcaster.subscribe(mock_ws)

        # Broadcast a notification with action
        await broadcaster.broadcast(
            notification_type="info",
            title="New Workflow Shared",
            message="Alice shared a workflow with you.",
            action={"label": "View Workflow", "url": "/workflows/123"},
        )

        # Verify notification includes action
        expected_message = {
            "type": "notification",
            "payload": {
                "type": "info",
                "title": "New Workflow Shared",
                "message": "Alice shared a workflow with you.",
                "action": {"label": "View Workflow", "url": "/workflows/123"},
            },
        }
        mock_ws.send_json.assert_called_once_with(expected_message)

    @pytest.mark.asyncio
    async def test_broadcaster_handles_disconnected_subscriber(self) -> None:
        """
        GIVEN a subscriber that disconnects
        WHEN broadcasting
        THEN handles error gracefully and removes subscriber.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()
        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_ws.send_json.side_effect = Exception("Connection closed")

        await broadcaster.subscribe(mock_ws)

        # Should not raise
        await broadcaster.broadcast(
            notification_type="info",
            title="Test",
            message="Test message",
        )

        # Subscriber should be removed after failed send
        assert broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_broadcaster_broadcast_to_specific_user(self) -> None:
        """
        GIVEN multiple subscribers for different users
        WHEN broadcasting to specific user
        THEN only that user's subscribers receive notification.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()
        mock_ws_user1 = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_ws_user2 = AsyncMock(return_value=None)  # noqa: async-mock-config

        await broadcaster.subscribe(mock_ws_user1, user_id="user-001")
        await broadcaster.subscribe(mock_ws_user2, user_id="user-002")

        # Broadcast to specific user
        await broadcaster.broadcast_to_user(
            user_id="user-001",
            notification_type="warning",
            title="Tier Limit Approaching",
            message="You've used 4/5 sessions.",
        )

        # Only user-001 should receive the notification
        assert mock_ws_user1.send_json.called
        assert not mock_ws_user2.send_json.called


@pytest.mark.api
@pytest.mark.xdist_group(name="notification_broadcaster")
class TestNotificationTypes:
    """Tests for notification type validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "notification_type",
        ["info", "success", "warning", "error"],
    )
    async def test_valid_notification_types(self, notification_type: str) -> None:
        """
        GIVEN a valid notification type
        WHEN broadcasting
        THEN notification is sent with correct type.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()
        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config

        await broadcaster.subscribe(mock_ws)

        await broadcaster.broadcast(
            notification_type=notification_type,
            title="Test",
            message="Test message",
        )

        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["payload"]["type"] == notification_type

    @pytest.mark.asyncio
    async def test_invalid_notification_type_raises(self) -> None:
        """
        GIVEN an invalid notification type
        WHEN broadcasting
        THEN raises ValueError.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()
        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config

        await broadcaster.subscribe(mock_ws)

        with pytest.raises(ValueError, match="Invalid notification type"):
            await broadcaster.broadcast(
                notification_type="invalid_type",
                title="Test",
                message="Test message",
            )


@pytest.mark.api
@pytest.mark.xdist_group(name="notification_broadcaster")
class TestNotificationWebSocketLifecycle:
    """Tests for WebSocket connection lifecycle with broadcaster."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_subscribe_on_connect(self) -> None:
        """
        GIVEN notification broadcaster
        WHEN client connects
        THEN client is subscribed to broadcaster.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()

        # Simulate connection with configured mock
        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_ws.send_json.return_value = None
        await broadcaster.subscribe(mock_ws, user_id="user-001")

        assert broadcaster.subscriber_count == 1

    @pytest.mark.asyncio
    async def test_unsubscribe_on_disconnect(self) -> None:
        """
        GIVEN connected client
        WHEN client disconnects
        THEN client is unsubscribed from broadcaster.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()
        mock_ws = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_ws.send_json.return_value = None

        await broadcaster.subscribe(mock_ws, user_id="user-001")
        await broadcaster.unsubscribe(mock_ws)

        assert broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_get_subscriber_count_by_user(self) -> None:
        """
        GIVEN multiple connections from same user
        WHEN checking subscriber count for user
        THEN returns correct count.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()
        mock_ws1 = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_ws1.send_json.return_value = None
        mock_ws2 = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_ws2.send_json.return_value = None
        mock_ws3 = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_ws3.send_json.return_value = None

        # User 1 has 2 connections, User 2 has 1
        await broadcaster.subscribe(mock_ws1, user_id="user-001")
        await broadcaster.subscribe(mock_ws2, user_id="user-001")
        await broadcaster.subscribe(mock_ws3, user_id="user-002")

        assert broadcaster.get_subscriber_count_for_user("user-001") == 2
        assert broadcaster.get_subscriber_count_for_user("user-002") == 1
        assert broadcaster.get_subscriber_count_for_user("user-003") == 0
