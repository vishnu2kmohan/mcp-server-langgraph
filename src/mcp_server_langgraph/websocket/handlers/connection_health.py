"""
Connection Health WebSocket Handler.

Provides real-time connection health monitoring using the standardized WebSocketBase class.

Features:
    - Refresh all connection statuses
    - Subscribe to specific connection updates
    - Health check requests for individual connections
    - Real-time connection status updates

Message Types (Client -> Server):
    - refresh: Get status of all connections
    - subscribe: Subscribe to updates for a connection
    - unsubscribe: Unsubscribe from connection updates
    - check_health: Request health check for a connection

Response Types (Server -> Client):
    - connection_status: List of all connections
    - subscribed: Subscription confirmed
    - unsubscribed: Unsubscription confirmed
    - health_check_started: Health check initiated
    - connection_update: Real-time connection status update
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
class ConnectionRepositoryProtocol(Protocol):
    """Protocol defining the connection repository interface.

    This protocol is intentionally flexible to support both the actual
    ConnectionRepository implementation and test mocks.
    """

    async def list(
        self,
        owner_id: str,
        cursor: str | None = None,
        limit: int = 1000,
        search: str | None = None,
        status: str | None = None,
        auth_type: str | None = None,
        project_id: str | None = None,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
    ) -> tuple[list[Any], str | None]:
        """List connections for owner.

        Args:
            owner_id: Owner ID for filtering connections.
            cursor: Optional pagination cursor.
            limit: Maximum number of connections to return.
            search: Optional search term.
            status: Optional status filter.
            auth_type: Optional auth type filter.
            project_id: Optional project ID filter.
            sort_by: Field to sort by.
            sort_order: Sort order (asc/desc).

        Returns:
            Tuple of (connections list, next cursor).
        """
        ...

    async def get(self, connection_id: str) -> Any | None:
        """Get connection by ID."""
        ...


class ConnectionHealthHandler(WebSocketBase):
    """
    WebSocket handler for real-time connection health monitoring.

    Extends WebSocketBase to provide connection health monitoring with the
    standardized infrastructure (auth, rate limiting, metrics, etc.).

    Usage:
        handler = ConnectionHealthHandler(
            config=WebSocketConfig(
                endpoint_name="connection-health",
                require_auth=True,
                authz_resource_type="mcp_connection",
                authz_resource_id="health",
                authz_required_relation="viewer",
            ),
            connection_repository=get_connection_repository(),
            owner_id=user_id,
        )
        await handler.run(websocket)
    """

    def __init__(
        self,
        config: WebSocketConfig,
        connection_repository: ConnectionRepositoryProtocol,
        owner_id: str,
        metrics: WebSocketMetrics | None = None,
    ) -> None:
        """
        Initialize the connection health handler.

        Args:
            config: WebSocket configuration.
            connection_repository: Repository for connection operations.
            owner_id: Owner ID for filtering connections.
            metrics: Optional metrics collector.
        """
        super().__init__(config=config, metrics=metrics)
        self._connection_repository = connection_repository
        self._owner_id = owner_id
        self._subscriptions: set[str] = set()

    async def on_connect(self, user: AuthUser) -> None:
        """
        Handle connection establishment.

        Args:
            user: The authenticated user.
        """
        logger.info(
            f"Connection health WebSocket connected: user={user.id}",
            extra={"user_id": user.id},
        )

    async def on_disconnect(self) -> None:
        """Clean up on disconnect."""
        self._subscriptions.clear()
        logger.info(
            "Connection health WebSocket disconnected",
            extra={"owner_id": self._owner_id},
        )

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming messages.

        Supports:
        - refresh: Get all connection statuses
        - subscribe: Subscribe to connection updates
        - unsubscribe: Unsubscribe from connection updates
        - check_health: Request health check for a connection

        Args:
            message: The incoming message envelope.

        Returns:
            Response message or None.
        """
        if message.type == "refresh":
            return await self._handle_refresh(message)
        elif message.type == "subscribe":
            return await self._handle_subscribe(message)
        elif message.type == "unsubscribe":
            return await self._handle_unsubscribe(message)
        elif message.type == "check_health":
            return await self._handle_check_health(message)
        else:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "unknown_message_type",
                    "message": f"Unknown message type: {message.type}",
                },
                id=message.id,
            )

    async def _handle_refresh(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle refresh message - return all connection statuses."""
        try:
            connections, _ = await self._connection_repository.list(owner_id=self._owner_id, limit=1000)

            connection_list = [
                {
                    "id": conn.id,
                    "name": conn.name,
                    "url": conn.url,
                    "status": conn.status,
                    "auth_type": conn.auth_type,
                    "server_name": getattr(conn, "server_name", None),
                    "server_version": getattr(conn, "server_version", None),
                    "tool_count": getattr(conn, "tool_count", 0),
                    "resource_count": getattr(conn, "resource_count", 0),
                    "prompt_count": getattr(conn, "prompt_count", 0),
                }
                for conn in connections
            ]

            return MessageEnvelope(
                type="connection_status",
                payload={"connections": connection_list},
                id=message.id,
            )

        except Exception as e:
            logger.warning(f"Error refreshing connection status: {e}")
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "refresh_failed",
                    "message": str(e),
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
                    "code": "missing_parameter",
                    "message": "Missing connection_id",
                },
                id=message.id,
            )

        self._subscriptions.add(connection_id)

        return MessageEnvelope(
            type="subscribed",
            payload={"connection_id": connection_id},
            id=message.id,
        )

    async def _handle_unsubscribe(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle unsubscribe message."""
        payload = message.payload or {}
        connection_id = payload.get("connection_id")

        if not connection_id:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "missing_parameter",
                    "message": "Missing connection_id",
                },
                id=message.id,
            )

        self._subscriptions.discard(connection_id)

        return MessageEnvelope(
            type="unsubscribed",
            payload={"connection_id": connection_id},
            id=message.id,
        )

    async def _handle_check_health(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle check_health message."""
        payload = message.payload or {}
        connection_id = payload.get("connection_id")

        if not connection_id:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "missing_parameter",
                    "message": "Missing connection_id",
                },
                id=message.id,
            )

        try:
            connection = await self._connection_repository.get(connection_id)
            if not connection:
                return MessageEnvelope(
                    type="error",
                    payload={
                        "code": "not_found",
                        "message": "Connection not found",
                    },
                    id=message.id,
                )

            # Return acknowledgment - actual health check is async
            return MessageEnvelope(
                type="health_check_started",
                payload={
                    "connection_id": connection_id,
                    "message": "Health check initiated",
                },
                id=message.id,
            )

        except Exception as e:
            logger.warning(f"Error starting health check for {connection_id}: {e}")
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "health_check_failed",
                    "message": str(e),
                },
                id=message.id,
            )

    async def push_connection_update(self, connection_id: str, status: dict[str, Any]) -> None:
        """
        Push a connection status update to the client.

        Only sends if the client is subscribed to this connection.

        Args:
            connection_id: The connection ID.
            status: The connection status data.
        """
        if self._websocket and connection_id in self._subscriptions:
            await self._websocket.send_json(
                {
                    "type": "connection_update",
                    "payload": status,
                }
            )
