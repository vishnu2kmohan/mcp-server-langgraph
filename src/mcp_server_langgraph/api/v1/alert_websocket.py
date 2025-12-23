"""
Alert WebSocket Streaming Endpoint.

Provides real-time streaming of infrastructure alerts to Admin users.

Features:
- Real-time alert streaming for Admin persona
- JWT authentication required (query param or header)
- Admin role authorization enforced
- Severity filtering (critical/warning only)
- Graceful connection lifecycle management
- Ping/pong keepalive support

Usage:
    Connect to: wss://host/ws/alerts?token=<jwt>
    Or with header: Authorization: Bearer <jwt>

Message Format:
    Receive alerts as JSON:
    {
        "type": "alert",
        "payload": {
            "alert_id": "string",
            "name": "string",
            "severity": "critical" | "warning",
            "state": "pending" | "firing" | "resolved" | "silenced",
            "message": "string",
            "labels": { ... },
            "annotations": { ... },
            "started_at": "ISO8601 timestamp",
            "ended_at": "ISO8601 timestamp" | null,
            "duration_ms": number | null,
            "generator_url": "string" | null
        }
    }

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from starlette.websockets import WebSocketState

from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster
from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload
from mcp_server_langgraph.auth.middleware import get_auth_middleware

logger = logging.getLogger(__name__)

alert_websocket_router = APIRouter(tags=["alerts"])

# Global broadcaster instance
_broadcaster: AlertBroadcaster | None = None

# Admin roles that are allowed to receive alerts
ADMIN_ROLES = {"admin", "platform_admin", "system_admin"}


def get_alert_broadcaster() -> AlertBroadcaster:
    """Get the alert broadcaster instance."""
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = AlertBroadcaster()
    return _broadcaster


def set_alert_broadcaster(broadcaster: AlertBroadcaster | None) -> None:
    """Set the alert broadcaster instance (for app initialization or testing)."""
    global _broadcaster
    _broadcaster = broadcaster


def is_admin_user(user: dict[str, Any]) -> bool:
    """
    Check if user has admin role.

    Args:
        user: User data dictionary with 'roles' key.

    Returns:
        True if user has any admin role, False otherwise.
    """
    roles = user.get("roles", [])
    return bool(set(roles) & ADMIN_ROLES)


async def validate_alert_websocket_auth(websocket: WebSocket) -> dict[str, Any] | None:
    """
    Validate WebSocket authentication using JWT.

    Extracts JWT token from query params or Authorization header,
    validates using AuthMiddleware, and returns user data.

    Token sources (in order of precedence):
    1. Query parameter: ?token=<jwt>
    2. Authorization header: Bearer <jwt>

    Args:
        websocket: The WebSocket connection.

    Returns:
        User dict if authenticated, None otherwise.
        User dict contains: user_id, username, roles, email, etc.
    """
    # Check for token in query params (takes precedence for WebSocket)
    token = websocket.query_params.get("token")

    # Fallback to Authorization header
    if not token:
        auth_header = websocket.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix

    if not token:
        logger.debug("Alert WebSocket auth failed: no token provided")
        return None

    try:
        # Use AuthMiddleware for token validation (DI pattern preferred)
        auth_middleware = getattr(websocket.app.state, "auth_middleware", None)
        if auth_middleware is None:
            # Fallback to global for backward compatibility
            auth_middleware = get_auth_middleware()
        result = await auth_middleware.verify_token(token)

        if not result.valid or not result.payload:
            logger.warning(
                "Alert WebSocket auth failed: token verification failed",
                extra={"error": result.error},
            )
            return None

        # Extract user information from JWT payload
        user_data = extract_user_from_jwt_payload(result.payload)

        logger.debug(
            "Alert WebSocket auth success",
            extra={"user_id": user_data.get("user_id")},
        )

        return user_data

    except Exception as e:
        logger.warning(f"Alert WebSocket auth error: {e}", exc_info=True)
        return None


async def handle_client_message(websocket: WebSocket, data: dict[str, Any]) -> dict[str, Any] | None:
    """
    Handle messages from the client.

    Currently supports:
    - ping: Returns pong for keepalive

    Args:
        websocket: The WebSocket connection.
        data: The received JSON data.

    Returns:
        Response to send back, or None if no response needed.
    """
    message_type = data.get("type")

    if message_type == "ping":
        return {"type": "pong"}

    return None


@alert_websocket_router.websocket("/alerts")
async def alert_stream(
    websocket: WebSocket,
    broadcaster: AlertBroadcaster = Depends(get_alert_broadcaster),
) -> None:
    """
    WebSocket endpoint for real-time alert streaming to Admin users.

    Connect to this endpoint to receive infrastructure alerts in real-time.
    Authentication and admin authorization are required.

    Alerts are filtered to critical and warning severity only.
    Info-level alerts are not streamed.

    Alerts are sent in the format:
    {
        "type": "alert",
        "payload": {
            "alert_id": "string",
            "name": "string",
            "severity": "critical" | "warning",
            "state": "firing" | "resolved" | etc,
            "message": "string",
            "labels": { ... },
            "annotations": { ... },
            "started_at": "ISO8601",
            "ended_at": "ISO8601" | null,
            "duration_ms": number | null
        }
    }
    """
    # Accept the connection first to be able to send close messages
    await websocket.accept()

    # Validate authentication
    user = await validate_alert_websocket_auth(websocket)
    if not user:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication required",
        )
        return

    # Validate admin authorization
    if not is_admin_user(user):
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Admin role required",
        )
        return

    user_id = user.get("user_id")
    logger.info(f"Alert stream connected: user={user_id}")

    # Subscribe to alerts
    await broadcaster.subscribe(websocket, user_id=user_id)  # type: ignore[arg-type]

    try:
        while True:
            # Keep connection alive, wait for messages from client
            try:
                # Client can send ping/pong or other messages
                data = await websocket.receive_json()

                # Handle client message
                response = await handle_client_message(websocket, data)
                if response:
                    await websocket.send_json(response)

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning(f"Error processing alert WebSocket message: {e}")
                # Continue listening for more messages

    finally:
        await broadcaster.unsubscribe(websocket)
        logger.info(f"Alert stream disconnected: user={user_id}")

        # Close connection if still open
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()
