"""
Connections Realtime WebSocket Handler.

Provides real-time connection status updates using the standardized WebSocketBase class.

Features:
    - Real-time connection status updates
    - Subscribe to specific connections or all connections
    - On-demand health check requests
    - Replaces polling-based ConnectionsPage updates

Message Types (Client -> Server):
    - subscribe: Subscribe to a specific connection (requires connection_id)
    - subscribe_all: Subscribe to all connection updates
    - unsubscribe: Unsubscribe from a connection (requires connection_id)
    - request_health_check: Request health check for a connection

Response Types (Server -> Client):
    - connection_list: Initial list of all connections
    - connection_status: Current status of a subscribed connection
    - connection_updated: Real-time connection status change (pushed)
    - subscribed_all: Confirmation of subscribe_all
    - unsubscribed: Confirmation of unsubscription
    - health_check_result: Result of a health check request
    - error: Error message
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
    from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

logger = logging.getLogger(__name__)


@runtime_checkable
class ConnectionServiceProtocol(Protocol):
    """Protocol defining the connection service interface needed by this handler."""

    async def list_connections(self) -> list[dict[str, Any]]:
        """List all connections."""
        ...

    async def get_connection(self, connection_id: str) -> dict[str, Any] | None:
        """Get a specific connection by ID."""
        ...

    async def get_connection_health(self, connection_id: str) -> dict[str, Any]:
        """Get health status for a connection."""
        ...


class ConnectionsRealtimeHandler(WebSocketBase):
    """
    WebSocket handler for real-time connection status updates.

    Extends WebSocketBase to provide real-time connection monitoring
    with the standardized infrastructure (auth, rate limiting, metrics, etc.).

    This handler replaces the polling-based approach used in ConnectionsPage
    with efficient push-based updates.

    Usage:
        handler = ConnectionsRealtimeHandler(
            config=WebSocketConfig(
                endpoint_name="connections-realtime",
                require_auth=True,
                authz_resource_type="mcp_connection",
                authz_resource_id="*",
                authz_required_relation="viewer",
            ),
            connection_service=get_connection_service(),
        )
        await handler.run(websocket)
    """

    def __init__(
        self,
        config: WebSocketConfig,
        connection_service: ConnectionServiceProtocol,
        metrics: WebSocketMetrics | None = None,
    ) -> None:
        """
        Initialize the connections realtime handler.

        Args:
            config: WebSocket configuration.
            connection_service: Connection service for connection operations.
            metrics: Optional metrics collector.
        """
        super().__init__(config=config, metrics=metrics)
        self._connection_service = connection_service
        self.subscriptions: set[str] = set()
        self.subscribe_all: bool = False

    async def on_connect(self, user: AuthUser) -> None:
        """
        Handle connection establishment.

        Sends the initial connection list to the client.

        Args:
            user: The authenticated user.
        """
        # Send initial connection list
        connections = await self._connection_service.list_connections()

        if self._websocket:
            await self._websocket.send_json(
                {
                    "type": "connection_list",
                    "connections": connections,
                }
            )

    async def on_disconnect(self) -> None:
        """Clean up subscriptions on disconnect."""
        self.subscriptions.clear()
        self.subscribe_all = False

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming messages.

        Supports:
        - subscribe: Subscribe to specific connection updates
        - subscribe_all: Subscribe to all connection updates
        - unsubscribe: Unsubscribe from connection updates
        - request_health_check: Request health check for a connection

        Args:
            message: The incoming message envelope.

        Returns:
            Response message or None.
        """
        if message.type == "subscribe":
            return await self._handle_subscribe(message)
        elif message.type == "subscribe_all":
            return await self._handle_subscribe_all(message)
        elif message.type == "unsubscribe":
            return await self._handle_unsubscribe(message)
        elif message.type == "request_health_check":
            return await self._handle_health_check(message)
        else:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "unknown_message_type",
                    "message": f"Unknown message type: {message.type}",
                },
                id=message.id,
            )

    async def _handle_subscribe(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle subscribe message."""
        payload = message.payload or {}
        connection_id = payload.get("connection_id")

        if not connection_id:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "missing_connection_id",
                    "message": "connection_id is required for subscribe",
                },
                id=message.id,
            )

        try:
            connection = await self._connection_service.get_connection(connection_id)
            if connection is None:
                return MessageEnvelope(
                    type="error",
                    payload={
                        "code": "connection_not_found",
                        "message": f"Connection {connection_id} not found",
                    },
                    id=message.id,
                )

            self.subscriptions.add(connection_id)
            return MessageEnvelope(
                type="connection_status",
                payload={"connection": connection},
                id=message.id,
            )

        except Exception as e:
            logger.warning(f"Error subscribing to connection {connection_id}: {e}")
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "subscribe_error",
                    "message": str(e),
                },
                id=message.id,
            )

    async def _handle_subscribe_all(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle subscribe_all message."""
        self.subscribe_all = True
        return MessageEnvelope(
            type="subscribed_all",
            payload={"subscribed": True},
            id=message.id,
        )

    async def _handle_unsubscribe(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle unsubscribe message."""
        payload = message.payload or {}
        connection_id = payload.get("connection_id")

        if connection_id:
            self.subscriptions.discard(connection_id)

        return MessageEnvelope(
            type="unsubscribed",
            payload={"connection_id": connection_id},
            id=message.id,
        )

    async def _handle_health_check(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle health check request."""
        payload = message.payload or {}
        connection_id = payload.get("connection_id")

        if not connection_id:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "missing_connection_id",
                    "message": "connection_id is required for health check",
                },
                id=message.id,
            )

        try:
            health = await self._connection_service.get_connection_health(connection_id)
            return MessageEnvelope(
                type="health_check_result",
                payload=health,
                id=message.id,
            )

        except Exception as e:
            logger.warning(f"Error checking health for connection {connection_id}: {e}")
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "health_check_error",
                    "message": str(e),
                },
                id=message.id,
            )

    async def push_connection_update(self, connection: dict[str, Any]) -> None:
        """
        Push a connection update to the client if subscribed.

        Args:
            connection: The updated connection data.
        """
        connection_id = connection.get("id")
        if not connection_id:
            return

        # Check if client is subscribed to this connection or all connections
        if not self.subscribe_all and connection_id not in self.subscriptions:
            return

        if self._websocket:
            await self.send(
                MessageEnvelope(
                    type="connection_updated",
                    payload={"connection": connection},
                )
            )
