"""
Audit Event WebSocket Streaming Endpoint.

Provides real-time streaming of audit events for compliance monitoring
and security operations center (SOC) integration.

Features:
- Real-time audit event streaming
- Filter by category, regulation, actor
- Authentication required
- Admin/compliance_officer role required

Usage:
    Connect to: wss://host/api/v1/audit/stream
    Send filter: {"categories": ["security"], "regulations": ["HIPAA"]}
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from starlette.websockets import WebSocketState

from mcp_server_langgraph.audit.broadcast import (
    AuditEventBroadcaster,
    AuditEventFilter,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["audit"])

# Global broadcaster instance
_broadcaster: AuditEventBroadcaster | None = None


def get_audit_event_broadcaster() -> AuditEventBroadcaster:
    """Get the audit event broadcaster instance."""
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = AuditEventBroadcaster()
    return _broadcaster


def set_audit_event_broadcaster(broadcaster: AuditEventBroadcaster | None) -> None:
    """Set the audit event broadcaster instance (for app initialization)."""
    global _broadcaster
    _broadcaster = broadcaster


async def validate_websocket_auth(websocket: WebSocket) -> dict[str, Any] | None:
    """
    Validate WebSocket authentication using JWT token.

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

    try:
        from mcp_server_langgraph.auth.jwt_utils import decode_jwt_token

        # Validate JWT token and extract user claims
        payload = decode_jwt_token(token)
        if not payload:
            logger.warning("Invalid JWT token for WebSocket connection")
            return None

        return {
            "user_id": payload.get("sub") or payload.get("user_id") or "unknown",
            "roles": payload.get("roles", []),
            "email": payload.get("email"),
            "preferred_username": payload.get("preferred_username"),
        }
    except Exception as e:
        logger.warning(f"Failed to validate WebSocket auth token: {e}")
        return None


def has_audit_access(user: dict[str, Any]) -> bool:
    """
    Check if user has access to audit streams.

    Args:
        user: User dict with roles.

    Returns:
        True if user has admin or compliance_officer role.
    """
    roles = user.get("roles", [])
    return "admin" in roles or "compliance_officer" in roles


@router.websocket("/stream")
async def audit_event_stream(
    websocket: WebSocket,
    broadcaster: AuditEventBroadcaster = Depends(get_audit_event_broadcaster),
) -> None:
    """
    WebSocket endpoint for real-time audit event streaming.

    Connect to this endpoint to receive audit events in real-time.
    Authentication is required via query param or header token.

    Send a JSON message to set filters:
    {
        "categories": ["authentication", "security"],
        "regulations": ["HIPAA", "FedRAMP"],
        "actors": ["user:alice"],
        "event_types": ["login_success", "login_failure"]
    }

    Receive audit events as JSON:
    {
        "event_id": "evt-001",
        "timestamp": "2025-01-15T10:30:00Z",
        "category": "authentication",
        "event_type": "login_success",
        ...
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

    # Check authorization
    if not has_audit_access(user):
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Admin or compliance officer role required",
        )
        return

    logger.info(f"Audit stream connected: user={user.get('user_id')}")

    # Default filter (all events)
    filter_ = AuditEventFilter()

    # Subscribe to events
    await broadcaster.subscribe(websocket, filter_)

    try:
        while True:
            # Wait for filter updates from client
            try:
                data = await websocket.receive_json()

                # Update filter based on received data
                filter_ = AuditEventFilter(
                    categories=data.get("categories"),
                    regulations=data.get("regulations"),
                    actors=data.get("actors"),
                    event_types=data.get("event_types"),
                )

                # Re-subscribe with new filter
                await broadcaster.unsubscribe(websocket)
                await broadcaster.subscribe(websocket, filter_)

                # Acknowledge filter update
                await websocket.send_json(
                    {
                        "type": "filter_updated",
                        "filter": {
                            "categories": filter_.categories,
                            "regulations": filter_.regulations,
                            "actors": filter_.actors,
                            "event_types": filter_.event_types,
                        },
                    }
                )

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning(f"Error processing WebSocket message: {e}")
                # Continue listening for more messages

    finally:
        await broadcaster.unsubscribe(websocket)
        logger.info(f"Audit stream disconnected: user={user.get('user_id')}")

        # Close connection if still open
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()
