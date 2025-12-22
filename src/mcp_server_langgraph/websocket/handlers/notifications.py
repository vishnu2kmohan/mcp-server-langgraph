"""
Notification WebSocket Handler.

Provides real-time notification streaming using the standardized WebSocketBase class.

Features:
    - User-specific notifications
    - Integration with NotificationBroadcaster
    - Authentication required
    - Graceful connection lifecycle management

Message Format (Server -> Client):
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

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from mcp_server_langgraph.websocket.base import WebSocketBase
from mcp_server_langgraph.websocket.types import (
    AuthUser,
    MessageEnvelope,
    WebSocketConfig,
)

if TYPE_CHECKING:
    from fastapi import WebSocket as FastAPIWebSocket

    from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

logger = logging.getLogger(__name__)


@runtime_checkable
class BroadcasterProtocol(Protocol):
    """Protocol defining the broadcaster interface needed by this handler."""

    async def subscribe(self, websocket: FastAPIWebSocket, user_id: str | None = None) -> None:
        """Subscribe a WebSocket to notifications."""
        ...

    async def unsubscribe(self, websocket: FastAPIWebSocket) -> None:
        """Unsubscribe a WebSocket from notifications."""
        ...


class NotificationWebSocketHandler(WebSocketBase):
    """
    WebSocket handler for real-time notification streaming.

    Extends WebSocketBase to provide notification streaming with the
    standardized infrastructure (auth, rate limiting, metrics, etc.).

    This handler is largely passive - it receives notifications from the
    broadcaster and forwards them to the connected client. The client
    can only send ping messages.

    Usage:
        handler = NotificationWebSocketHandler(
            config=WebSocketConfig(
                endpoint_name="notifications",
                require_auth=True,
                authz_resource_type="chat",
                authz_resource_id="notifications",
                authz_required_relation="viewer",
            ),
            broadcaster=get_notification_broadcaster(),
        )
        await handler.run(websocket)
    """

    def __init__(
        self,
        config: WebSocketConfig,
        broadcaster: BroadcasterProtocol,
        metrics: WebSocketMetrics | None = None,
    ) -> None:
        """
        Initialize the notification handler.

        Args:
            config: WebSocket configuration.
            broadcaster: Notification broadcaster instance.
            metrics: Optional metrics collector.
        """
        super().__init__(config=config, metrics=metrics)
        self._broadcaster = broadcaster
        self._user_id: str | None = None

    async def on_connect(self, user: AuthUser) -> None:
        """
        Handle connection establishment.

        Subscribes the client to the notification broadcaster.

        Args:
            user: The authenticated user.
        """
        self._user_id = user.id

        if self._websocket:
            await self._broadcaster.subscribe(self._websocket, user_id=self._user_id)
            logger.info(
                f"Notification stream connected: user={self._user_id}",
                extra={"user_id": self._user_id},
            )

    async def on_disconnect(self) -> None:
        """
        Handle connection teardown.

        Unsubscribes the client from the notification broadcaster.
        """
        if self._websocket:
            await self._broadcaster.unsubscribe(self._websocket)
            logger.info(
                f"Notification stream disconnected: user={self._user_id}",
                extra={"user_id": self._user_id},
            )

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming messages.

        The notification WebSocket is largely passive - it mostly receives
        notifications from the server. Client messages are typically just
        acknowledgments or keep-alives that don't require responses beyond
        the ping/pong handled by the base class.

        Args:
            message: The incoming message envelope.

        Returns:
            None - no response needed for notification client messages.
        """
        # Notification WebSocket is passive - no custom message handling needed
        # Ping/pong is handled by the base class
        logger.debug(
            f"Received message type: {message.type}",
            extra={"message_type": message.type, "user_id": self._user_id},
        )
        return None
