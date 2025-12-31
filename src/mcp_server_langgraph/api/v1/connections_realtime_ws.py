"""
Connections Realtime WebSocket Endpoint.

Provides real-time connection status updates replacing polling-based
ConnectionsPage updates with efficient push-based updates.

URL: /api/v1/ws/connections/realtime

Message Types (Client → Server):
- subscribe: Subscribe to specific connection updates
- unsubscribe: Unsubscribe from connection updates
- subscribe_all: Subscribe to all connection updates
- request_health_check: Trigger health check for a connection
- refresh: Request current connection list

Message Types (Server → Client):
- connection_list: List of all connections
- connection_status: Single connection status (after subscribe)
- connection_updated: Connection was updated
- subscribed_all: Subscription to all confirmed
- unsubscribed: Unsubscription confirmed
- health_check_result: Result of health check
- error: Error message
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, WebSocket

from mcp_server_langgraph.websocket.base import WebSocketBase
from mcp_server_langgraph.websocket.types import AuthUser, MessageEnvelope, WebSocketConfig

if TYPE_CHECKING:
    from mcp_server_langgraph.websocket.services.connections import ConnectionsServiceAdapter

logger = logging.getLogger(__name__)

# =============================================================================
# Router
# =============================================================================

router = APIRouter(tags=["websocket", "connections"])


# =============================================================================
# Handler
# =============================================================================


class ConnectionsRealtimeWebSocketHandler(WebSocketBase):
    """
    WebSocket handler for real-time connection status updates.

    Replaces polling-based ConnectionsPage updates with efficient
    push-based updates using the WebSocketBase infrastructure.
    """

    def __init__(self, connections_service: ConnectionsServiceAdapter | None = None) -> None:
        """Initialize the handler with configuration.

        Args:
            connections_service: Optional connections service adapter.
                If not provided, will be lazy-initialized.
        """
        config = WebSocketConfig(
            endpoint_name="connections-realtime",
            require_auth=True,
            heartbeat_interval=30,
            idle_timeout=1800,  # 30 minutes
            rate_limit_per_minute=120,  # 2 msg/sec reasonable for status updates
        )
        super().__init__(config)

        # Subscription state
        self._subscribed_connections: set[str] = set()
        self._subscribed_all: bool = False

        # Service adapter for connection data
        self._connections_service: ConnectionsServiceAdapter | None = connections_service

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming WebSocket messages.

        Args:
            message: The incoming message envelope.

        Returns:
            Response message or None.
        """
        message_type = message.type

        if message_type == "subscribe":
            return await self._handle_subscribe(message)
        elif message_type == "unsubscribe":
            return await self._handle_unsubscribe(message)
        elif message_type == "subscribe_all":
            return await self._handle_subscribe_all(message)
        elif message_type == "request_health_check":
            return await self._handle_health_check(message)
        elif message_type == "refresh":
            return await self._handle_refresh(message)
        else:
            logger.warning(f"Unknown message type: {message_type}")
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "unknown_type",
                    "message": f"Unknown message type: {message_type}",
                },
                id=message.id,
            )

    async def _handle_subscribe(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle subscribe message for a specific connection."""
        connection_id = message.payload.get("connection_id") if message.payload else None

        if not connection_id:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "missing_connection_id",
                    "message": "connection_id is required",
                },
                id=message.id,
            )

        self._subscribed_connections.add(connection_id)

        # Get connection status (mock for now, will integrate with real service)
        connection = await self._get_connection_status(connection_id)

        return MessageEnvelope(
            type="connection_status",
            payload={"connection": connection},
            id=message.id,
        )

    async def _handle_unsubscribe(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle unsubscribe message."""
        connection_id = message.payload.get("connection_id") if message.payload else None

        if connection_id and connection_id in self._subscribed_connections:
            self._subscribed_connections.discard(connection_id)

        return MessageEnvelope(
            type="unsubscribed",
            payload={"connection_id": connection_id},
            id=message.id,
        )

    async def _handle_subscribe_all(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle subscribe_all message."""
        self._subscribed_all = True

        return MessageEnvelope(
            type="subscribed_all",
            payload={"subscribed": True},
            id=message.id,
        )

    async def _handle_health_check(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle health check request for a connection."""
        connection_id = message.payload.get("connection_id") if message.payload else None

        if not connection_id:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "missing_connection_id",
                    "message": "connection_id is required",
                },
                id=message.id,
            )

        # Perform health check (mock for now)
        result = await self._perform_health_check(connection_id)

        return MessageEnvelope(
            type="health_check_result",
            payload=result,
            id=message.id,
        )

    async def _handle_refresh(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle refresh message - returns current connection list."""
        connections = await self._get_all_connections()

        return MessageEnvelope(
            type="connection_list",
            payload={"connections": connections},
            id=message.id,
        )

    async def _get_connection_status(self, connection_id: str) -> dict[str, Any]:
        """
        Get status for a specific connection.

        Uses ConnectionsServiceAdapter when available, falls back to stub data.
        """
        if self._connections_service is not None:
            connection = await self._connections_service.get_connection(connection_id)
            if connection is not None:
                return connection

        # Fallback when service unavailable or connection not found
        return {
            "id": connection_id,
            "name": f"Connection {connection_id}",
            "status": "unknown",
            "type": "mcp",
            "last_seen": datetime.now(UTC).isoformat(),
        }

    async def _get_all_connections(self) -> list[dict[str, Any]]:
        """
        Get all connections.

        Uses ConnectionsServiceAdapter when available, falls back to empty list.
        """
        if self._connections_service is not None:
            try:
                return await self._connections_service.list_connections()
            except Exception as e:
                logger.warning(f"Failed to list connections: {e}")
                return []

        # Fallback when service unavailable
        return []

    async def _perform_health_check(self, connection_id: str) -> dict[str, Any]:
        """
        Perform health check for a connection.

        Uses ConnectionsServiceAdapter when available, falls back to stub data.
        """
        if self._connections_service is not None:
            health = await self._connections_service.get_connection_health(connection_id)
            if health:
                health["checked_at"] = datetime.now(UTC).isoformat()
                return health

        # Fallback when service unavailable
        return {
            "connection_id": connection_id,
            "healthy": True,
            "latency_ms": 42,
            "checked_at": datetime.now(UTC).isoformat(),
        }

    async def on_connect(self, user: AuthUser) -> None:
        """Called when connection is established."""
        logger.info(
            "Connections realtime WebSocket connected",
            extra={"user_id": user.id},
        )

    async def on_disconnect(self) -> None:
        """Called when connection is closed."""
        self._subscribed_connections.clear()
        self._subscribed_all = False
        logger.info(
            "Connections realtime WebSocket disconnected",
            extra={"user_id": self._user.id if self._user else "unknown"},
        )


# =============================================================================
# WebSocket Route
# =============================================================================

# Global handler instance for broadcasting
_handler_instances: dict[str, ConnectionsRealtimeWebSocketHandler] = {}


@router.websocket("")
async def connections_realtime_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time connection status updates.

    Replaces polling-based ConnectionsPage updates with efficient
    push-based updates.
    """
    handler = ConnectionsRealtimeWebSocketHandler()
    await handler.run(websocket)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "router",
    "ConnectionsRealtimeWebSocketHandler",
]
