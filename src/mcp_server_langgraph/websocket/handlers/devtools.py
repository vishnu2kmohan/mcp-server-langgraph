"""
DevTools WebSocket Handler.

Provides real-time console logs and network events for the DevTools panel.

Features:
    - Subscribe to console log events
    - Subscribe to network request events
    - Real-time updates as events occur
    - Context filtering by session/workflow ID

Message Types (Client -> Server):
    - subscribe: Subscribe to console/network events
    - unsubscribe: Unsubscribe from events
    - clear: Clear current entries

Response Types (Server -> Client):
    - subscribed: Successfully subscribed to events
    - unsubscribed: Successfully unsubscribed from events
    - console: Console log entry
    - network: Network request start
    - network_update: Network request completion/update
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

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


# =============================================================================
# Broadcaster Protocol
# =============================================================================


@runtime_checkable
class DevToolsBroadcasterProtocol(Protocol):
    """Protocol defining the DevTools broadcaster interface."""

    async def subscribe(
        self,
        websocket: FastAPIWebSocket,
        user_id: str | None = None,
        context_entity_id: str | None = None,
    ) -> None:
        """Subscribe to DevTools events."""
        ...

    async def unsubscribe(self, websocket: FastAPIWebSocket) -> None:
        """Unsubscribe from DevTools events."""
        ...


# =============================================================================
# Broadcaster Implementation
# =============================================================================


class DevToolsBroadcaster:
    """
    Broadcaster for DevTools console and network events.

    Manages WebSocket subscriptions and broadcasts DevTools events
    to all connected clients.

    Usage:
        broadcaster = DevToolsBroadcaster()

        # Subscribe a client
        await broadcaster.subscribe(websocket, user_id="user-123")

        # Broadcast a console event
        await broadcaster.broadcast_console({
            "level": "info",
            "message": "Test message",
            "timestamp": 1234567890,
            "source": "system",
        })

        # Unsubscribe
        await broadcaster.unsubscribe(websocket)
    """

    def __init__(self) -> None:
        """Initialize the broadcaster."""
        # Map of websocket -> (user_id, context_entity_id)
        self._subscribers: dict[Any, tuple[str | None, str | None]] = {}

    async def subscribe(
        self,
        websocket: Any,
        user_id: str | None = None,
        context_entity_id: str | None = None,
    ) -> None:
        """Subscribe a WebSocket to DevTools events.

        Args:
            websocket: The WebSocket connection
            user_id: Optional user ID for tracking
            context_entity_id: Optional session/workflow ID for filtering
        """
        self._subscribers[websocket] = (user_id, context_entity_id)
        logger.info(
            "Client subscribed to DevTools events",
            extra={
                "user_id": user_id,
                "context_entity_id": context_entity_id,
                "subscriber_count": len(self._subscribers),
            },
        )

    async def unsubscribe(self, websocket: Any) -> None:
        """Unsubscribe a WebSocket from DevTools events.

        Args:
            websocket: The WebSocket connection
        """
        if websocket in self._subscribers:
            user_id, _ = self._subscribers.pop(websocket)
            logger.info(
                "Client unsubscribed from DevTools events",
                extra={"user_id": user_id, "subscriber_count": len(self._subscribers)},
            )

    async def _broadcast(
        self,
        message: dict[str, Any],
        context_entity_id: str | None = None,
    ) -> None:
        """Broadcast a message to subscribers.

        Args:
            message: The message to broadcast
            context_entity_id: Optional context ID for filtering
        """
        failed_subscribers: list[Any] = []

        for websocket, (_, sub_context) in list(self._subscribers.items()):
            # Filter by context if specified
            if sub_context and context_entity_id and sub_context != context_entity_id:
                continue

            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(
                    "Failed to send to subscriber, removing",
                    extra={"error": str(e)},
                )
                failed_subscribers.append(websocket)

        # Remove failed subscribers
        for ws in failed_subscribers:
            self._subscribers.pop(ws, None)

    async def broadcast_console(
        self,
        entry: dict[str, Any],
        context_entity_id: str | None = None,
    ) -> None:
        """Broadcast a console log entry.

        Args:
            entry: Console entry dict with level, message, timestamp, source, etc.
            context_entity_id: Optional session/workflow ID for filtering
        """
        await self._broadcast(
            {
                "type": "console",
                "payload": entry,
            },
            context_entity_id=context_entity_id,
        )

    async def broadcast_network(
        self,
        entry: dict[str, Any],
        context_entity_id: str | None = None,
    ) -> None:
        """Broadcast a network request start event.

        Args:
            entry: Network entry dict with id, method, url, startTime, etc.
            context_entity_id: Optional session/workflow ID for filtering
        """
        await self._broadcast(
            {
                "type": "network",
                "payload": entry,
            },
            context_entity_id=context_entity_id,
        )

    async def broadcast_network_update(
        self,
        update: dict[str, Any],
        context_entity_id: str | None = None,
    ) -> None:
        """Broadcast a network request update/completion.

        Args:
            update: Update dict with id, status, statusCode, duration, etc.
            context_entity_id: Optional session/workflow ID for filtering
        """
        await self._broadcast(
            {
                "type": "network_update",
                "payload": update,
            },
            context_entity_id=context_entity_id,
        )


# =============================================================================
# WebSocket Handler
# =============================================================================


class DevToolsHandler(WebSocketBase):
    """
    WebSocket handler for real-time DevTools console and network events.

    Extends WebSocketBase to provide DevTools event streaming with the
    standardized infrastructure (auth, rate limiting, metrics, etc.).

    Usage:
        handler = DevToolsHandler(
            config=WebSocketConfig(
                endpoint_name="devtools",
                require_auth=True,
                authz_resource_type="dashboard",
                authz_resource_id="devtools",
                authz_required_relation="viewer",
            ),
            broadcaster=get_devtools_broadcaster(),
        )
        await handler.run(websocket)
    """

    def __init__(
        self,
        config: WebSocketConfig,
        broadcaster: DevToolsBroadcasterProtocol,
        metrics: WebSocketMetrics | None = None,
    ) -> None:
        """
        Initialize the DevTools handler.

        Args:
            config: WebSocket configuration.
            broadcaster: Broadcaster for managing subscriptions.
            metrics: Optional metrics collector.
        """
        super().__init__(config=config, metrics=metrics)
        self._broadcaster = broadcaster
        self._subscribed: bool = False
        self._user_id: str | None = None
        self._context_entity_id: str | None = None

    async def on_connect(self, user: AuthUser) -> None:
        """
        Handle connection establishment.

        Subscribes the client to the DevTools broadcaster.

        Args:
            user: The authenticated user.
        """
        self._user_id = user.id

        if self._websocket:
            await self._broadcaster.subscribe(
                self._websocket,
                user_id=self._user_id,
                context_entity_id=self._context_entity_id,
            )
            self._subscribed = True
            logger.info(
                f"DevTools stream connected: user={self._user_id}",
                extra={"user_id": self._user_id},
            )

    async def on_disconnect(self) -> None:
        """
        Handle connection teardown.

        Unsubscribes the client from the DevTools broadcaster.
        """
        if self._websocket and self._subscribed:
            await self._broadcaster.unsubscribe(self._websocket)
            logger.info(
                f"DevTools stream disconnected: user={self._user_id}",
                extra={"user_id": self._user_id},
            )

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming messages.

        Supports subscribe, unsubscribe, and context messages.

        Args:
            message: The incoming message envelope.

        Returns:
            Response envelope or None.
        """
        logger.debug(
            f"Received message type: {message.type}",
            extra={"message_type": message.type, "user_id": self._user_id},
        )

        if message.type == "subscribe":
            # Extract context entity ID from payload if provided
            if message.payload and isinstance(message.payload, dict):
                self._context_entity_id = message.payload.get("contextEntityId")

            if self._websocket and not self._subscribed:
                await self._broadcaster.subscribe(
                    self._websocket,
                    user_id=self._user_id,
                    context_entity_id=self._context_entity_id,
                )
                self._subscribed = True

            return MessageEnvelope(
                type="subscribed",
                id=message.id,
                payload={"status": "subscribed", "contextEntityId": self._context_entity_id},
            )

        elif message.type == "unsubscribe":
            if self._websocket and self._subscribed:
                await self._broadcaster.unsubscribe(self._websocket)
                self._subscribed = False

            return MessageEnvelope(
                type="unsubscribed",
                id=message.id,
                payload={"status": "unsubscribed"},
            )

        elif message.type == "set_context":
            # Update context filter
            if message.payload and isinstance(message.payload, dict):
                self._context_entity_id = message.payload.get("contextEntityId")

                # Re-subscribe with new context
                if self._websocket and self._subscribed:
                    await self._broadcaster.unsubscribe(self._websocket)
                    await self._broadcaster.subscribe(
                        self._websocket,
                        user_id=self._user_id,
                        context_entity_id=self._context_entity_id,
                    )

            return MessageEnvelope(
                type="context_updated",
                id=message.id,
                payload={"contextEntityId": self._context_entity_id},
            )

        # Ping/pong is handled by the base class
        return None


# =============================================================================
# Singleton Instance
# =============================================================================

_broadcaster: DevToolsBroadcaster | None = None


def get_devtools_broadcaster() -> DevToolsBroadcaster:
    """Get the application-wide DevTools broadcaster instance.

    Returns:
        Singleton DevToolsBroadcaster instance
    """
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = DevToolsBroadcaster()
    return _broadcaster


def reset_devtools_broadcaster() -> None:
    """Reset the DevTools broadcaster (for testing)."""
    global _broadcaster
    _broadcaster = None
