"""
Connection Health WebSocket Endpoint

.. deprecated:: 3.0
    This module is deprecated. Use the new standardized WebSocket infrastructure:

    - Handler: :mod:`mcp_server_langgraph.websocket.handlers.connection_health`
    - Base class: :mod:`mcp_server_langgraph.websocket.base.WebSocketBase`
    - New URL: ``/api/v1/ws/connections/health``

    This module will be removed in v4.0.

Real-time connection health monitoring via WebSocket.
Provides:
- Initial status of all connections on connect
- Heartbeat/ping-pong mechanism
- Health check requests for individual connections
- Subscription to specific connection updates
- REST endpoint for health summary

MCP Spec: 2025-03-26 compatible
"""

import json
import warnings

warnings.warn(
    "mcp_server_langgraph.api.v1.connection_health_ws is deprecated. "
    "Use mcp_server_langgraph.websocket.handlers.connection_health instead. "
    "This module will be removed in v4.0.",
    DeprecationWarning,
    stacklevel=2,
)
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from mcp_server_langgraph.auth.middleware import get_current_user
from mcp_server_langgraph.repositories.connections import ConnectionRepository
from mcp_server_langgraph.core.dependencies import get_connection_repository

logger = logging.getLogger(__name__)

connection_health_router = APIRouter(tags=["connection-health"])


# ============================================================================
# Response Models
# ============================================================================


class ConnectionHealthStatus(BaseModel):
    """Health status for a single connection."""

    id: str
    name: str
    url: str
    status: str
    auth_type: str
    server_name: str | None = None
    server_version: str | None = None
    tool_count: int = 0
    resource_count: int = 0
    prompt_count: int = 0
    last_error: str | None = None
    last_checked: datetime | None = None


class HealthSummary(BaseModel):
    """Aggregated health summary for all connections."""

    total: int
    connected: int
    disconnected: int
    connecting: int
    error: int
    auth_required: int
    last_check: datetime


# ============================================================================
# WebSocket Connection Manager
# ============================================================================


class HealthWebSocketManager:
    """Manages WebSocket connections for health monitoring."""

    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}
        self.subscriptions: dict[str, set[str]] = {}  # client_id -> set of connection_ids

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Register a WebSocket connection (assumes already accepted by handler)."""
        self.active_connections[client_id] = websocket
        self.subscriptions[client_id] = set()
        logger.info(f"Health WebSocket connected: {client_id}")

    def disconnect(self, client_id: str) -> None:
        """Remove a disconnected client."""
        self.active_connections.pop(client_id, None)
        self.subscriptions.pop(client_id, None)
        logger.info(f"Health WebSocket disconnected: {client_id}")

    def subscribe(self, client_id: str, connection_id: str) -> None:
        """Subscribe a client to updates for a specific connection."""
        if client_id in self.subscriptions:
            self.subscriptions[client_id].add(connection_id)

    def unsubscribe(self, client_id: str, connection_id: str) -> None:
        """Unsubscribe a client from a specific connection."""
        if client_id in self.subscriptions:
            self.subscriptions[client_id].discard(connection_id)

    async def send_to_client(self, client_id: str, message: dict[str, Any]) -> None:
        """Send a message to a specific client."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to client {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(client_id)

        for client_id in disconnected:
            self.disconnect(client_id)

    async def broadcast_connection_update(self, connection_id: str, status: dict[str, Any]) -> None:
        """Broadcast update for a specific connection to subscribed clients."""
        message = {"type": "connection_update", "connection": status}

        for client_id, subscribed in self.subscriptions.items():
            if connection_id in subscribed:
                await self.send_to_client(client_id, message)


# Global manager instance
health_ws_manager = HealthWebSocketManager()


# ============================================================================
# Helper Functions
# ============================================================================


async def validate_websocket_auth(websocket: WebSocket) -> dict[str, Any] | None:
    """
    Validate WebSocket authentication using JWT token.

    Args:
        websocket: The WebSocket connection.

    Returns:
        User dict if authenticated, None otherwise.
    """
    token = websocket.query_params.get("token")
    if not token:
        token = websocket.headers.get("Authorization", "").replace("Bearer ", "")

    if not token:
        return None

    try:
        from mcp_server_langgraph.auth.jwt_utils import decode_jwt_token

        payload = decode_jwt_token(token)
        if not payload:
            logger.warning("Invalid JWT token for WebSocket connection")
            return None

        return {
            "user_id": payload.get("sub") or payload.get("user_id") or "unknown",
            "roles": payload.get("roles", []),
            "email": payload.get("email"),
        }
    except Exception as e:
        logger.warning(f"Failed to validate WebSocket auth token: {e}")
        return None


async def get_all_connection_statuses(
    repo: ConnectionRepository,
    owner_id: str,
) -> list[dict[str, Any]]:
    """Get health status for all connections belonging to owner."""
    connections, _ = await repo.list(owner_id=owner_id, limit=1000)

    return [
        {
            "id": conn.id,
            "name": conn.name,
            "url": conn.url,
            "status": conn.status,
            "auth_type": conn.auth_type,
            "server_name": conn.server_name,
            "tool_count": conn.tool_count,
            "resource_count": conn.resource_count,
            "prompt_count": conn.prompt_count,
        }
        for conn in connections
    ]


async def handle_message(
    message: dict[str, Any],
    client_id: str,
    repo: ConnectionRepository,
    owner_id: str,
) -> dict[str, Any]:
    """Handle incoming WebSocket message."""
    msg_type = message.get("type", "")

    if msg_type == "ping":
        return {"type": "pong", "timestamp": datetime.now(UTC).isoformat()}

    elif msg_type == "refresh":
        connections = await get_all_connection_statuses(repo, owner_id)
        return {"type": "connection_status", "connections": connections}

    elif msg_type == "subscribe":
        connection_id = message.get("connection_id")
        if connection_id:
            health_ws_manager.subscribe(client_id, connection_id)
            return {"type": "subscribed", "connection_id": connection_id}
        return {"type": "error", "message": "Missing connection_id"}

    elif msg_type == "unsubscribe":
        connection_id = message.get("connection_id")
        if connection_id:
            health_ws_manager.unsubscribe(client_id, connection_id)
            return {"type": "unsubscribed", "connection_id": connection_id}
        return {"type": "error", "message": "Missing connection_id"}

    elif msg_type == "check_health":
        connection_id = message.get("connection_id")
        if not connection_id:
            return {"type": "error", "message": "Missing connection_id"}

        connection = await repo.get(connection_id)
        if not connection:
            return {"type": "error", "message": "Connection not found"}

        # Return acknowledgment - actual health check would be async
        return {
            "type": "health_check_started",
            "connection_id": connection_id,
            "message": "Health check initiated",
        }

    else:
        return {"type": "error", "message": f"Unknown message type: {msg_type}"}


# ============================================================================
# WebSocket Endpoint
# ============================================================================


@connection_health_router.websocket("/connections/health/ws")
async def connection_health_websocket(
    websocket: WebSocket,
    repo: ConnectionRepository = Depends(get_connection_repository),
) -> None:
    """
    WebSocket endpoint for real-time connection health monitoring.

    Authentication:
    - Token via query param: ws://host/connections/health/ws?token=JWT
    - Token via header: Authorization: Bearer JWT

    Message types:
    - ping: Heartbeat check, responds with pong
    - refresh: Request fresh status for all connections
    - subscribe: Subscribe to updates for a specific connection
    - unsubscribe: Unsubscribe from a specific connection
    - check_health: Trigger health check for a specific connection

    Server messages:
    - connection_status: Full status of all connections
    - connection_update: Update for a specific connection
    - health_check_started: Acknowledgment of health check request
    - health_check_result: Result of health check
    - pong: Response to ping
    - error: Error message
    """
    # Accept WebSocket first to allow sending error messages
    await websocket.accept()

    # Authenticate the connection
    user = await validate_websocket_auth(websocket)
    if not user:
        await websocket.send_json({"type": "error", "message": "Authentication required"})
        await websocket.close(code=4001)
        return

    owner_id = user["user_id"]
    client_id = str(id(websocket))

    await health_ws_manager.connect(websocket, client_id)

    try:
        # Send initial connection status
        connections = await get_all_connection_statuses(repo, owner_id)
        await websocket.send_json({"type": "connection_status", "connections": connections})

        # Message loop
        while True:
            try:
                raw_message = await websocket.receive_text()

                try:
                    message = json.loads(raw_message)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                    continue

                response = await handle_message(message, client_id, repo, owner_id)
                await websocket.send_json(response)

            except WebSocketDisconnect:
                break

    finally:
        health_ws_manager.disconnect(client_id)


# ============================================================================
# REST Endpoint for Health Summary
# ============================================================================


@connection_health_router.get(
    "/connections/health/summary",
)
async def get_health_summary(
    repo: ConnectionRepository = Depends(get_connection_repository),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> HealthSummary:
    """
    Get aggregated health summary for connections belonging to current user.

    Returns counts by status and timestamp of last check.
    """
    user_id = current_user.get("sub", current_user.get("user_id", "anonymous"))
    connections, _ = await repo.list(owner_id=user_id, limit=1000)

    status_counts = {
        "connected": 0,
        "disconnected": 0,
        "connecting": 0,
        "error": 0,
        "auth_required": 0,
    }

    for conn in connections:
        if conn.status in status_counts:
            status_counts[conn.status] += 1

    return HealthSummary(
        total=len(connections),
        connected=status_counts["connected"],
        disconnected=status_counts["disconnected"],
        connecting=status_counts["connecting"],
        error=status_counts["error"],
        auth_required=status_counts["auth_required"],
        last_check=datetime.now(UTC),
    )


# Re-export for dependency override in tests
__all__ = [
    "connection_health_router",
    "get_connection_repository",
    "health_ws_manager",
    "HealthWebSocketManager",
    "HealthSummary",
    "ConnectionHealthStatus",
]
