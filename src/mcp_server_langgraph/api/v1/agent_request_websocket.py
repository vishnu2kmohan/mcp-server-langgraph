"""
Agent Request WebSocket API for Human-in-the-Loop (HITL).

Real-time WebSocket endpoint for HITL agent request notifications.

Message Types (Server → Client):
- approval_required: New approval request from agent
- clarification_required: Agent needs user input/clarification
- approval_updated: Status change (approved/rejected)
- execution_resumed: Agent resumed after decision

Message Types (Client → Server):
- ping: Keepalive ping
- clarification_response: User's response to clarification

Features:
- JWT authentication for WebSocket connections
- Role-based authorization (admin, hitl_reviewer)
- Session-scoped message filtering
- Ping/pong keepalive
- Feature flag integration
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws/agents/requests", tags=["agent-request-websocket"])


# -----------------------------------------------------------------------------
# Message Type Enum
# -----------------------------------------------------------------------------


class AgentRequestWSMessageType(StrEnum):
    """WebSocket message types for agent requests."""

    # Server → Client
    APPROVAL_REQUIRED = "approval_required"
    """New approval request from agent (low confidence)."""

    CLARIFICATION_REQUIRED = "clarification_required"
    """Agent needs user input/clarification."""

    APPROVAL_UPDATED = "approval_updated"
    """Status change notification (approved/rejected)."""

    EXECUTION_RESUMED = "execution_resumed"
    """Agent resumed execution after decision."""

    # Keepalive
    PONG = "pong"
    """Response to ping keepalive."""

    # Error
    ERROR = "error"
    """Error message."""


# -----------------------------------------------------------------------------
# Message Models
# -----------------------------------------------------------------------------


class ApprovalRequiredMessage(BaseModel):
    """Message for new approval request."""

    request_id: str = Field(description="Unique request identifier")
    session_id: str = Field(description="Session ID")
    task_id: str = Field(description="Task ID")
    agent_name: str = Field(description="Name of the agent")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    threshold: float = Field(ge=0.0, le=1.0, description="Threshold that triggered")
    proposed_action: str = Field(description="What the agent wants to do")
    trigger_reason: str = Field(description="Why approval is needed")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    requested_at: str = Field(description="ISO timestamp when requested")


class ClarificationRequiredMessage(BaseModel):
    """Message for clarification request."""

    request_id: str = Field(description="Unique request identifier")
    session_id: str = Field(description="Session ID")
    task_id: str = Field(description="Task ID")
    agent_name: str = Field(description="Name of the agent")
    clarification_type: str = Field(description="Type: text, choice, confirmation")
    question: str = Field(description="The question to ask")
    options: list[dict[str, Any]] = Field(
        default_factory=list, description="Options for choice type"
    )
    placeholder: str | None = Field(default=None, description="Placeholder for text input")
    required: bool = Field(default=True, description="Whether response is required")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    requested_at: str = Field(description="ISO timestamp when requested")


class ApprovalUpdatedMessage(BaseModel):
    """Message for approval status change."""

    request_id: str = Field(description="Request identifier")
    status: str = Field(description="New status: approved, rejected")
    decided_by: str = Field(description="Who made the decision")
    decided_at: str = Field(description="ISO timestamp of decision")
    reason: str | None = Field(default=None, description="Optional reason")


class ExecutionResumedMessage(BaseModel):
    """Message for agent execution resumption."""

    request_id: str = Field(description="Request identifier")
    task_id: str = Field(description="Task ID")
    agent_name: str = Field(description="Name of the agent")
    status: str = Field(description="Final status: approved, rejected")
    resumed_at: str = Field(description="ISO timestamp when resumed")


# -----------------------------------------------------------------------------
# WebSocket Connection Info
# -----------------------------------------------------------------------------


class WebSocketConnection:
    """Tracks a WebSocket connection with metadata."""

    def __init__(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: str,
    ) -> None:
        """Initialize connection info."""
        self.websocket = websocket
        self.session_id = session_id
        self.user_id = user_id
        self.connected_at = datetime.now(UTC)


# -----------------------------------------------------------------------------
# Broadcaster Service
# -----------------------------------------------------------------------------


class AgentRequestBroadcaster:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self) -> None:
        """Initialize broadcaster."""
        self._connections: dict[WebSocket, WebSocketConnection] = {}

    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: str,
    ) -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        self._connections[websocket] = WebSocketConnection(
            websocket=websocket,
            session_id=session_id,
            user_id=user_id,
        )
        logger.info(
            "WebSocket connected for agent requests",
            extra={"session_id": session_id, "user_id": user_id},
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self._connections:
            conn = self._connections.pop(websocket)
            logger.info(
                "WebSocket disconnected",
                extra={"session_id": conn.session_id, "user_id": conn.user_id},
            )

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast message to all connected clients."""
        disconnected: list[WebSocket] = []

        for websocket in list(self._connections.keys()):
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        # Clean up disconnected
        for ws in disconnected:
            self.disconnect(ws)

    async def send_to_session(self, session_id: str, message: dict[str, Any]) -> None:
        """Send message to all connections for a specific session."""
        disconnected: list[WebSocket] = []

        for websocket, conn in list(self._connections.items()):
            if conn.session_id == session_id:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append(websocket)

        for ws in disconnected:
            self.disconnect(ws)


# -----------------------------------------------------------------------------
# Global Broadcaster Instance
# -----------------------------------------------------------------------------

_broadcaster: AgentRequestBroadcaster | None = None


def get_broadcaster() -> AgentRequestBroadcaster:
    """Get the global broadcaster instance (singleton)."""
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = AgentRequestBroadcaster()
    return _broadcaster


# -----------------------------------------------------------------------------
# Authentication & Authorization
# -----------------------------------------------------------------------------


async def validate_websocket_token(token: str | None) -> dict[str, Any] | None:
    """
    Validate JWT token for WebSocket connection.

    Args:
        token: JWT token from query parameter or header

    Returns:
        User info dict if valid, None otherwise
    """
    if token is None:
        return None

    try:
        from mcp_server_langgraph.auth.middleware import get_auth_middleware

        auth_middleware = get_auth_middleware()
        result = await auth_middleware.verify_token(token)
        if result is None:
            return None  # type: ignore[unreachable]
        return result  # type: ignore[return-value]
    except Exception as e:
        logger.warning("WebSocket token validation failed", extra={"error": str(e)})
        return None


def check_reviewer_role(user_info: dict[str, Any]) -> bool:
    """
    Check if user has HITL reviewer role.

    Args:
        user_info: Decoded JWT claims

    Returns:
        True if user has admin or hitl_reviewer role
    """
    roles = user_info.get("realm_access", {}).get("roles", [])
    return "admin" in roles or "hitl_reviewer" in roles


# -----------------------------------------------------------------------------
# Feature Flag Integration
# -----------------------------------------------------------------------------


async def is_hitl_enabled() -> bool:
    """Check if HITL feature is enabled."""
    try:
        from mcp_server_langgraph.core.feature_flags import get_feature_flags

        flags = get_feature_flags()
        return flags.enable_agent_hitl
    except Exception:
        return True  # Default to enabled


async def check_hitl_enabled_for_ws(websocket: WebSocket) -> bool:
    """
    Check if HITL is enabled, close WebSocket if not.

    Returns:
        True if enabled, False if disabled (WebSocket closed)
    """
    if not await is_hitl_enabled():
        await websocket.close(code=4403, reason="HITL feature is disabled")
        return False
    return True


# -----------------------------------------------------------------------------
# Ping/Pong Keepalive
# -----------------------------------------------------------------------------


async def handle_ping(websocket: WebSocket) -> None:
    """Handle ping message with pong response."""
    await websocket.send_json({"type": AgentRequestWSMessageType.PONG})


# -----------------------------------------------------------------------------
# Broadcast Helper Functions
# -----------------------------------------------------------------------------


async def broadcast_approval_required(request: Any) -> None:
    """
    Broadcast approval_required message to all clients.

    Also sends push notification if enabled via feature flag.

    Args:
        request: AgentRequest object from agent_requests module
    """
    broadcaster = get_broadcaster()
    message = {
        "type": AgentRequestWSMessageType.APPROVAL_REQUIRED,
        "payload": {
            "request_id": request.request_id,
            "session_id": request.session_id,
            "task_id": request.task_id,
            "agent_name": request.agent_name,
            "confidence": request.confidence,
            "threshold": request.threshold,
            "proposed_action": request.proposed_action or "",
            "trigger_reason": request.trigger_reason or "low_confidence",
            "context": request.context or {},
            "requested_at": request.requested_at.isoformat()
            if hasattr(request.requested_at, "isoformat")
            else str(request.requested_at),
        },
    }
    await broadcaster.broadcast(message)
    logger.info(
        "Broadcast approval_required",
        extra={"request_id": request.request_id},
    )

    # Send push notification (async, non-blocking)
    user_id = request.context.get("user_id") if request.context else None
    await send_hitl_approval_notification(request, user_id=user_id)


async def broadcast_clarification_required(request: Any) -> None:
    """
    Broadcast clarification_required message to all clients.

    Args:
        request: AgentRequest object with clarification fields
    """
    broadcaster = get_broadcaster()
    message = {
        "type": AgentRequestWSMessageType.CLARIFICATION_REQUIRED,
        "payload": {
            "request_id": request.request_id,
            "session_id": request.session_id,
            "task_id": request.task_id,
            "agent_name": request.agent_name,
            "clarification_type": request.clarification_type or "text",
            "question": request.question or "",
            "options": request.options or [],
            "placeholder": request.placeholder,
            "required": True,
            "context": request.context or {},
            "requested_at": request.requested_at.isoformat()
            if hasattr(request.requested_at, "isoformat")
            else str(request.requested_at),
        },
    }
    await broadcaster.broadcast(message)
    logger.info(
        "Broadcast clarification_required",
        extra={"request_id": request.request_id},
    )


async def broadcast_approval_updated(
    request_id: str,
    status: str,
    decided_by: str,
    reason: str | None = None,
) -> None:
    """
    Broadcast approval_updated message to all clients.

    Args:
        request_id: Request identifier
        status: New status (approved, rejected)
        decided_by: Who made the decision
        reason: Optional reason for decision
    """
    broadcaster = get_broadcaster()
    message = {
        "type": AgentRequestWSMessageType.APPROVAL_UPDATED,
        "payload": {
            "request_id": request_id,
            "status": status,
            "decided_by": decided_by,
            "decided_at": datetime.now(UTC).isoformat(),
            "reason": reason,
        },
    }
    await broadcaster.broadcast(message)
    logger.info(
        "Broadcast approval_updated",
        extra={"request_id": request_id, "status": status},
    )


async def broadcast_execution_resumed(
    request_id: str,
    task_id: str,
    agent_name: str,
    status: str,
) -> None:
    """
    Broadcast execution_resumed message to all clients.

    Args:
        request_id: Request identifier
        task_id: Task identifier
        agent_name: Name of the agent
        status: Final status (approved, rejected)
    """
    broadcaster = get_broadcaster()
    message = {
        "type": AgentRequestWSMessageType.EXECUTION_RESUMED,
        "payload": {
            "request_id": request_id,
            "task_id": task_id,
            "agent_name": agent_name,
            "status": status,
            "resumed_at": datetime.now(UTC).isoformat(),
        },
    }
    await broadcaster.broadcast(message)
    logger.info(
        "Broadcast execution_resumed",
        extra={"request_id": request_id, "status": status},
    )


# -----------------------------------------------------------------------------
# WebSocket Endpoint
# -----------------------------------------------------------------------------


@router.websocket("")
async def agent_request_websocket(
    websocket: WebSocket,
    token: str | None = None,
    session_id: str | None = None,
) -> None:
    """
    WebSocket endpoint for agent request notifications.

    Query Parameters:
        token: JWT token for authentication
        session_id: Optional session ID to filter messages

    Message Flow:
        1. Client connects with token
        2. Server validates token and checks authorization
        3. Server sends approval_required/clarification_required messages
        4. Client responds via REST API
        5. Server sends approval_updated/execution_resumed messages
    """
    # Check feature flag
    if not await check_hitl_enabled_for_ws(websocket):
        return

    # Validate token
    user_info = await validate_websocket_token(token)
    if user_info is None:
        await websocket.close(code=4401, reason="Invalid or missing token")
        return

    # Check authorization
    if not check_reviewer_role(user_info):
        await websocket.close(code=4403, reason="Insufficient permissions")
        return

    # Connect
    broadcaster = get_broadcaster()
    user_id = user_info.get("sub", "unknown")
    effective_session_id = session_id or "global"

    await broadcaster.connect(websocket, session_id=effective_session_id, user_id=user_id)

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "ping":
                await handle_ping(websocket)
            else:
                # Unknown message type - send error
                await websocket.send_json(
                    {
                        "type": AgentRequestWSMessageType.ERROR,
                        "payload": {"message": f"Unknown message type: {msg_type}"},
                    }
                )

    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error", extra={"error": str(e)})
        broadcaster.disconnect(websocket)


# -----------------------------------------------------------------------------
# Push Notification Integration
# -----------------------------------------------------------------------------


def get_feature_flags() -> Any:
    """Get feature flags (lazy import to avoid circular dependencies)."""
    from mcp_server_langgraph.core.feature_flags import get_feature_flags as _get_flags

    return _get_flags()


def get_push_sender() -> Any:
    """Get push notification sender (lazy import)."""
    try:
        from mcp_server_langgraph.notifications.push_sender import (
            PushNotificationSender,
        )
        from mcp_server_langgraph.notifications.push_store import (
            InMemoryPushSubscriptionStore,
        )

        # Get VAPID keys from settings
        from mcp_server_langgraph.core.config import settings

        # Create a basic sender (in production, use proper store)
        store = InMemoryPushSubscriptionStore()
        sender = PushNotificationSender(
            vapid_private_key=getattr(settings, "vapid_private_key", ""),
            vapid_public_key=getattr(settings, "vapid_public_key", ""),
            vapid_claims={"sub": "mailto:admin@example.com"},
            subscription_store=store,
        )
        return sender
    except Exception as e:
        logger.warning(f"Failed to get push sender: {e}")
        return None


def create_approval_push_message(request: Any) -> Any:
    """
    Create a push notification message for an approval request.

    Args:
        request: AgentRequest object with approval details

    Returns:
        PushMessage object ready to send
    """
    from mcp_server_langgraph.notifications.push_sender import PushMessage

    confidence_pct = int(request.confidence * 100)

    return PushMessage(
        title=f"Agent needs approval ({confidence_pct}%)",
        body=request.proposed_action or f"Agent '{request.agent_name}' is waiting for your approval",
        icon="/icons/icon-192.png",
        badge="/icons/badge-72.png",
        tag=f"hitl-{request.request_id}",
        data={
            "request_id": request.request_id,
            "type": "approval",
            "session_id": request.session_id,
            "task_id": request.task_id,
            "agent_name": request.agent_name,
            "confidence": request.confidence,
        },
        actions=[
            {"action": "approve", "title": "Approve"},
            {"action": "reject", "title": "Reject"},
        ],
    )


def create_clarification_push_message(request: Any) -> Any:
    """
    Create a push notification message for a clarification request.

    Args:
        request: AgentRequest object with clarification details

    Returns:
        PushMessage object ready to send
    """
    from mcp_server_langgraph.notifications.push_sender import PushMessage

    return PushMessage(
        title=f"Agent has a question",
        body=request.question or f"Agent '{request.agent_name}' needs your input",
        icon="/icons/icon-192.png",
        badge="/icons/badge-72.png",
        tag=f"hitl-{request.request_id}",
        data={
            "request_id": request.request_id,
            "type": "clarification",
            "session_id": request.session_id,
            "task_id": request.task_id,
            "agent_name": request.agent_name,
            "clarification_type": getattr(request, "clarification_type", "text"),
        },
        actions=[
            {"action": "respond", "title": "Respond"},
            {"action": "dismiss", "title": "Dismiss"},
        ],
    )


async def send_hitl_approval_notification(
    request: Any,
    user_id: str | None = None,
) -> int:
    """
    Send a push notification for an HITL approval request.

    Args:
        request: AgentRequest object with approval details
        user_id: User ID to send notification to (optional)

    Returns:
        Number of notifications sent (0 if disabled or failed)
    """
    # Check feature flag
    flags = get_feature_flags()
    if not flags.enable_agent_hitl_push_notifications:
        logger.debug("HITL push notifications disabled via feature flag")
        return 0

    # Get push sender
    sender = get_push_sender()
    if sender is None:
        logger.debug("Push sender not available")
        return 0

    # Create message
    message = create_approval_push_message(request)

    # Send notification
    if user_id:
        count: int = await sender.send_to_user(user_id, message)
    else:
        # Fallback to broadcast if no user specified
        count = await sender.send_to_all(message)

    logger.info(
        "Sent HITL approval push notification",
        extra={
            "request_id": request.request_id,
            "user_id": user_id,
            "count": count,
        },
    )
    return int(count)


async def send_hitl_clarification_notification(
    request: Any,
    user_id: str | None = None,
) -> int:
    """
    Send a push notification for an HITL clarification request.

    Args:
        request: AgentRequest object with clarification details
        user_id: User ID to send notification to (optional)

    Returns:
        Number of notifications sent (0 if disabled or failed)
    """
    # Check feature flag
    flags = get_feature_flags()
    if not flags.enable_agent_hitl_push_notifications:
        logger.debug("HITL push notifications disabled via feature flag")
        return 0

    # Get push sender
    sender = get_push_sender()
    if sender is None:
        logger.debug("Push sender not available")
        return 0

    # Create message
    message = create_clarification_push_message(request)

    # Send notification
    if user_id:
        count: int = await sender.send_to_user(user_id, message)
    else:
        count = await sender.send_to_all(message)

    logger.info(
        "Sent HITL clarification push notification",
        extra={
            "request_id": request.request_id,
            "user_id": user_id,
            "count": count,
        },
    )
    return int(count)
