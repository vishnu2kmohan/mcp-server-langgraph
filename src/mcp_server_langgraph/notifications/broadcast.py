"""
Notification Broadcasting for Real-Time Updates.

Provides real-time streaming of notifications to connected WebSocket clients.

Features:
- Subscribe/unsubscribe pattern for WebSocket connections
- User-specific notifications support
- Broadcast to all or specific users
- Graceful handling of disconnected clients
- Thread-safe subscriber management

Message Format:
    {
        "type": "notification",
        "payload": {
            "type": "info" | "success" | "warning" | "error",
            "title": "string",
            "message": "string",
            "action": { "label": "string", "url": "string" }  // optional
        }
    }
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Protocol

if TYPE_CHECKING:
    from mcp_server_langgraph.notifications.preferences import PreferencesRepository

logger = logging.getLogger(__name__)

# Valid notification types
NotificationType = Literal["info", "success", "warning", "error"]
VALID_NOTIFICATION_TYPES = {"info", "success", "warning", "error"}


class WebSocketConnection(Protocol):
    """Protocol for WebSocket connections."""

    async def send_json(self, data: dict[str, Any]) -> None:
        """Send JSON data to the WebSocket."""
        ...


@dataclass
class Subscriber:
    """A WebSocket subscriber with optional user ID."""

    connection: WebSocketConnection
    user_id: str | None = None


class NotificationBroadcaster:
    """
    Broadcasts notifications to subscribed WebSocket connections.

    Provides real-time notification streaming for:
    - System-wide notifications (broadcast to all)
    - User-specific notifications (broadcast to specific user)
    - Session/workflow events
    - Tier limit warnings
    """

    def __init__(self) -> None:
        """Initialize the broadcaster."""
        self._subscribers: list[Subscriber] = []
        self._lock = asyncio.Lock()

    @property
    def subscriber_count(self) -> int:
        """Get the number of active subscribers."""
        return len(self._subscribers)

    def get_subscriber_count_for_user(self, user_id: str) -> int:
        """
        Get the number of active subscribers for a specific user.

        Args:
            user_id: The user ID to check.

        Returns:
            Number of connections for the user.
        """
        return sum(1 for s in self._subscribers if s.user_id == user_id)

    async def subscribe(
        self,
        connection: WebSocketConnection,
        user_id: str | None = None,
    ) -> None:
        """
        Subscribe a WebSocket connection to notifications.

        Args:
            connection: The WebSocket connection to subscribe.
            user_id: Optional user ID for user-specific notifications.
        """
        async with self._lock:
            subscriber = Subscriber(
                connection=connection,
                user_id=user_id,
            )
            self._subscribers.append(subscriber)
            logger.info(f"Notification subscriber added. User: {user_id or 'anonymous'}. Total: {self.subscriber_count}")

    async def unsubscribe(self, connection: WebSocketConnection) -> None:
        """
        Unsubscribe a WebSocket connection.

        Args:
            connection: The WebSocket connection to unsubscribe.
        """
        async with self._lock:
            self._subscribers = [s for s in self._subscribers if s.connection != connection]
            logger.info(f"Notification subscriber removed. Total: {self.subscriber_count}")

    def _create_notification_message(
        self,
        notification_type: str,
        title: str,
        message: str,
        action: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a notification message in the expected format.

        Args:
            notification_type: Type of notification (info, success, warning, error).
            title: Notification title.
            message: Notification message.
            action: Optional action with label and url.

        Returns:
            Formatted notification message.

        Raises:
            ValueError: If notification_type is invalid.
        """
        if notification_type not in VALID_NOTIFICATION_TYPES:
            raise ValueError(f"Invalid notification type: {notification_type}. Must be one of: {VALID_NOTIFICATION_TYPES}")

        payload: dict[str, Any] = {
            "type": notification_type,
            "title": title,
            "message": message,
        }

        if action:
            payload["action"] = action

        return {
            "type": "notification",
            "payload": payload,
        }

    async def broadcast(
        self,
        notification_type: str,
        title: str,
        message: str,
        action: dict[str, str] | None = None,
    ) -> None:
        """
        Broadcast a notification to all subscribers.

        Args:
            notification_type: Type of notification (info, success, warning, error).
            title: Notification title.
            message: Notification message.
            action: Optional action with label and url.

        Raises:
            ValueError: If notification_type is invalid.
        """
        notification_message = self._create_notification_message(
            notification_type=notification_type,
            title=title,
            message=message,
            action=action,
        )

        if not self._subscribers:
            return

        failed_connections: list[WebSocketConnection] = []

        async with self._lock:
            for subscriber in self._subscribers:
                try:
                    await subscriber.connection.send_json(notification_message)
                except Exception as e:
                    logger.warning(f"Failed to send notification to subscriber: {e}")
                    failed_connections.append(subscriber.connection)

            # Remove failed connections
            if failed_connections:
                self._subscribers = [s for s in self._subscribers if s.connection not in failed_connections]
                logger.info(f"Removed {len(failed_connections)} failed subscribers. Remaining: {self.subscriber_count}")

    async def broadcast_to_user(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        action: dict[str, str] | None = None,
    ) -> None:
        """
        Broadcast a notification to a specific user's connections.

        Args:
            user_id: The user ID to send notification to.
            notification_type: Type of notification (info, success, warning, error).
            title: Notification title.
            message: Notification message.
            action: Optional action with label and url.

        Raises:
            ValueError: If notification_type is invalid.
        """
        notification_message = self._create_notification_message(
            notification_type=notification_type,
            title=title,
            message=message,
            action=action,
        )

        if not self._subscribers:
            return

        failed_connections: list[WebSocketConnection] = []

        async with self._lock:
            user_subscribers = [s for s in self._subscribers if s.user_id == user_id]

            for subscriber in user_subscribers:
                try:
                    await subscriber.connection.send_json(notification_message)
                except Exception as e:
                    logger.warning(f"Failed to send notification to user {user_id}: {e}")
                    failed_connections.append(subscriber.connection)

            # Remove failed connections
            if failed_connections:
                self._subscribers = [s for s in self._subscribers if s.connection not in failed_connections]
                logger.info(f"Removed {len(failed_connections)} failed subscribers. Remaining: {self.subscriber_count}")

    async def broadcast_to_user_with_preferences(
        self,
        repository: "PreferencesRepository",
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        action: dict[str, str] | None = None,
    ) -> None:
        """
        Broadcast a notification to a user, respecting their preferences.

        Checks the user's notification preferences before sending.
        If the notification type is disabled, the notification is not sent.

        Args:
            repository: Preferences repository for looking up user preferences.
            user_id: The user ID to send notification to.
            notification_type: Type of notification (info, success, warning, error).
            title: Notification title.
            message: Notification message.
            action: Optional action with label and url.

        Raises:
            ValueError: If notification_type is invalid.
        """
        from mcp_server_langgraph.notifications.preferences import should_send_notification

        # Check user preferences before sending
        if not await should_send_notification(repository, user_id, notification_type):
            logger.debug(f"Notification type '{notification_type}' disabled for user {user_id}, skipping")
            return

        # Send the notification using the existing method
        await self.broadcast_to_user(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            action=action,
        )

    async def notify_user(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        action: dict[str, str] | None = None,
    ) -> None:
        """
        Send a notification to a user, respecting their preferences.

        This is the preferred method for sending user notifications.
        It automatically retrieves the user's preferences from the global
        preferences repository and filters accordingly.

        Args:
            user_id: The user ID to send notification to.
            notification_type: Type of notification (info, success, warning, error).
            title: Notification title.
            message: Notification message.
            action: Optional action with label and url.

        Raises:
            ValueError: If notification_type is invalid.
        """
        from mcp_server_langgraph.api.v1.notification_preferences import get_preferences_repository

        repository = get_preferences_repository()
        await self.broadcast_to_user_with_preferences(
            repository=repository,
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            action=action,
        )
