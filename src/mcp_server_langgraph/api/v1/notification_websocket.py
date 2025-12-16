"""
Notification WebSocket Streaming Endpoint.

Provides real-time streaming of notifications to connected clients.

Features:
- Real-time notification streaming
- User-specific notifications
- Authentication required
- Graceful connection lifecycle management

Usage:
    Connect to: wss://host/ws/notifications

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
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from starlette.websockets import WebSocketState

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
    Validate WebSocket authentication.

    Args:
        websocket: The WebSocket connection.

    Returns:
        User dict if authenticated, None otherwise.
    """
    # Check for token in query params or headers
    token = websocket.query_params.get("token")
    if not token:
        token = websocket.headers.get("Authorization", "").replace("Bearer ", "")

    if not token:
        return None

    # TODO: Implement actual token validation
    # For now, return a mock user for testing
    return {
        "user_id": "test-user",
        "username": "testuser",
        "roles": ["user"],
    }


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
