"""
Notification WebSocket Streaming Endpoint.

.. deprecated:: 3.0
    This module is deprecated. Use the new standardized WebSocket infrastructure:

    - Handler: :mod:`mcp_server_langgraph.websocket.handlers.notifications`
    - Base class: :mod:`mcp_server_langgraph.websocket.base.WebSocketBase`
    - New URL: ``/api/v1/ws/notifications``

    This module will be removed in v4.0.

Provides real-time streaming of notifications to connected clients.

Features:
- Real-time notification streaming
- User-specific notifications
- JWT authentication required (query param or header)
- Graceful connection lifecycle management

Usage:
    Connect to: wss://host/api/v1/ws/notifications?token=<jwt>
    Or with header: Authorization: Bearer <jwt>

Message Format:
    Receive notifications as JSON:
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

import logging
import warnings

warnings.warn(
    "mcp_server_langgraph.api.v1.notification_websocket is deprecated. "
    "Use mcp_server_langgraph.websocket.handlers.notifications instead. "
    "This module will be removed in v4.0.",
    DeprecationWarning,
    stacklevel=2,
)
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from starlette.websockets import WebSocketState

from mcp_server_langgraph.auth.jwt_utils import extract_user_from_jwt_payload
from mcp_server_langgraph.auth.middleware import get_auth_middleware
from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

logger = logging.getLogger(__name__)

router = APIRouter(tags=["notifications"])

# Global broadcaster instance
_broadcaster: NotificationBroadcaster | None = None


def get_notification_broadcaster() -> NotificationBroadcaster:
    """Get the notification broadcaster instance."""
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = NotificationBroadcaster()
    return _broadcaster


def set_notification_broadcaster(broadcaster: NotificationBroadcaster | None) -> None:
    """Set the notification broadcaster instance (for app initialization or testing)."""
    global _broadcaster
    _broadcaster = broadcaster


async def validate_websocket_auth(websocket: WebSocket) -> dict[str, Any] | None:
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
        logger.debug("WebSocket auth failed: no token provided")
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
                "WebSocket auth failed: token verification failed",
                extra={"error": result.error},
            )
            return None

        # Extract user information from JWT payload
        user_data = extract_user_from_jwt_payload(result.payload)

        logger.debug(
            "WebSocket auth success",
            extra={"user_id": user_data.get("user_id")},
        )

        return user_data

    except Exception as e:
        logger.warning(f"WebSocket auth error: {e}", exc_info=True)
        return None


@router.websocket("/notifications")
async def notification_stream(
    websocket: WebSocket,
    broadcaster: NotificationBroadcaster = Depends(get_notification_broadcaster),
) -> None:
    """
    WebSocket endpoint for real-time notification streaming.

    Connect to this endpoint to receive notifications in real-time.
    Authentication is required via query param or header token.

    Notifications are sent in the format:
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
    # Accept the connection first to be able to send close messages
    await websocket.accept()

    # Validate authentication
    user = await validate_websocket_auth(websocket)
    if not user:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication required",
        )
        return

    user_id = user.get("user_id")
    logger.info(f"Notification stream connected: user={user_id}")

    # Subscribe to notifications
    await broadcaster.subscribe(websocket, user_id=user_id)

    try:
        while True:
            # Keep connection alive, wait for messages from client
            try:
                # Client can send ping/pong or other messages
                data = await websocket.receive_json()

                # Handle ping from client
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning(f"Error processing WebSocket message: {e}")
                # Continue listening for more messages

    finally:
        await broadcaster.unsubscribe(websocket)
        logger.info(f"Notification stream disconnected: user={user_id}")

        # Close connection if still open
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()
