"""
Agent Request WebSocket API - DEPRECATED Compatibility Shim.

This module is DEPRECATED as of v3.0. Use the new locations instead:

- Message types and broadcaster: mcp_server_langgraph.hitl
- Registry functions: mcp_server_langgraph.websocket.registry
- WebSocket handler: mcp_server_langgraph.websocket.handlers.agent_request

This file exists only for backward compatibility with existing tests.
It will be removed in v4.0.
"""

from __future__ import annotations

import logging
import warnings
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter

from mcp_server_langgraph.core.feature_flags import (
    get_feature_flags as _core_get_feature_flags,
)

# Re-export from new locations
from mcp_server_langgraph.hitl.broadcast import (
    AgentRequestBroadcaster,
    AgentRequestWSMessageType,
    ApprovalRequiredMessage,
    ApprovalUpdatedMessage,
    ClarificationRequiredMessage,
    ExecutionResumedMessage,
    WebSocketConnection,
)
from mcp_server_langgraph.websocket.registry import (
    get_agent_request_broadcaster,
    set_agent_request_broadcaster,
)

if TYPE_CHECKING:
    from fastapi import WebSocket

    from mcp_server_langgraph.api.v1.agent_requests import AgentRequest
    from mcp_server_langgraph.notifications.push_sender import (
        PushMessage,
        PushNotificationSender,
    )

logger = logging.getLogger(__name__)

# Issue deprecation warning on import
warnings.warn(
    "mcp_server_langgraph.api.v1.agent_request_websocket is deprecated. "
    "Use mcp_server_langgraph.hitl and mcp_server_langgraph.websocket instead.",
    DeprecationWarning,
    stacklevel=2,
)

# =============================================================================
# Legacy Router (stub for tests)
# =============================================================================

router = APIRouter(prefix="/ws/agents/requests", tags=["agent-request-websocket-legacy"])


# =============================================================================
# Backward-compatible aliases
# =============================================================================


def get_broadcaster() -> AgentRequestBroadcaster:
    """
    Get the global agent request broadcaster.

    DEPRECATED: Use websocket.registry.get_agent_request_broadcaster() instead.
    """
    return get_agent_request_broadcaster()


def set_broadcaster(broadcaster: AgentRequestBroadcaster | None) -> None:
    """
    Set the global agent request broadcaster.

    DEPRECATED: Use websocket.registry.set_agent_request_broadcaster() instead.
    """
    set_agent_request_broadcaster(broadcaster)


# =============================================================================
# Feature Flag Helpers
# =============================================================================


def is_hitl_enabled() -> bool:
    """
    Check if HITL feature is enabled.

    DEPRECATED: Check feature flags directly.
    """
    try:
        from mcp_server_langgraph.core.feature_flags import is_enabled

        return is_enabled("hitl_approvals")
    except Exception:
        return False


def check_hitl_enabled_for_ws() -> bool:
    """
    Check if HITL is enabled for WebSocket connections.

    DEPRECATED: Use is_hitl_enabled() instead.
    """
    return is_hitl_enabled()


def check_reviewer_role(user_info: list[str] | dict[str, Any]) -> bool:
    """
    Check if user has HITL reviewer role.

    Args:
        user_info: Either a list of user roles, or a JWT payload dict
                   with realm_access.roles nested structure.

    Returns:
        True if user has admin or hitl_reviewer role.
    """
    required_roles = {"admin", "hitl_reviewer", "hitl_approver"}

    # Handle dict (JWT payload) vs list (direct roles)
    if isinstance(user_info, dict):
        # Extract roles from Keycloak JWT structure
        realm_access = user_info.get("realm_access", {})
        roles = realm_access.get("roles", [])
    else:
        roles = user_info

    return bool(set(roles) & required_roles)


# =============================================================================
# Token Validation
# =============================================================================


async def validate_websocket_token(token: str | None) -> dict[str, Any] | None:
    """
    Validate JWT token for WebSocket connection.

    DEPRECATED: Use websocket.base.WebSocketBase authentication.

    Args:
        token: JWT token string.

    Returns:
        User payload if valid, None otherwise.
    """
    if not token:
        return None

    try:
        from mcp_server_langgraph.auth.middleware import get_auth_middleware

        auth = get_auth_middleware()
        result = await auth.verify_token(token)

        # Handle both dict and VerificationResult return types
        # Note: mypy sees dict branch as unreachable but it's needed for test mocks
        if isinstance(result, dict):  # type: ignore[unreachable]
            # Direct dict return from mocked auth
            return result  # type: ignore[unreachable]
        elif hasattr(result, "valid") and hasattr(result, "payload"):
            # VerificationResult object
            if result.valid and result.payload:
                return result.payload
        return None
    except Exception:
        logger.exception("Token validation failed")
        return None


# =============================================================================
# Ping/Pong Handler
# =============================================================================


async def handle_ping(websocket: WebSocket, correlation_id: str | None = None) -> None:
    """
    Handle ping message by sending pong response.

    DEPRECATED: Ping/pong is handled by WebSocketBase.

    Args:
        websocket: WebSocket connection.
        correlation_id: Optional correlation ID for the response.
    """
    pong_message = {
        "type": AgentRequestWSMessageType.PONG.value,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if correlation_id:
        pong_message["correlation_id"] = correlation_id
    await websocket.send_json(pong_message)


# =============================================================================
# Broadcast Helpers
# =============================================================================


async def broadcast_approval_required(message: Any) -> None:
    """
    Broadcast approval required message to all clients and send push notification.

    DEPRECATED: Use broadcaster.broadcast() directly.

    Args:
        message: ApprovalRequiredMessage or AgentRequest object.
    """
    broadcaster = get_broadcaster()

    # Convert message to dict (handles both Pydantic models)
    payload = (
        message.model_dump() if hasattr(message, "model_dump") else (dict(message) if hasattr(message, "__iter__") else {})
    )

    await broadcaster.broadcast(
        {
            "type": AgentRequestWSMessageType.APPROVAL_REQUIRED.value,
            "payload": payload,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )

    # Also send push notification if user_id is available in context
    user_id: str | None = None
    if hasattr(message, "context") and isinstance(message.context, dict):
        user_id = message.context.get("user_id")

    if user_id:
        await send_hitl_approval_notification(message, user_id)


async def broadcast_clarification_required(message: Any) -> None:
    """
    Broadcast clarification required message to all clients and send push notification.

    DEPRECATED: Use broadcaster.broadcast() directly.

    Args:
        message: ClarificationRequiredMessage or AgentRequest object.
    """
    broadcaster = get_broadcaster()

    payload = (
        message.model_dump() if hasattr(message, "model_dump") else (dict(message) if hasattr(message, "__iter__") else {})
    )

    await broadcaster.broadcast(
        {
            "type": AgentRequestWSMessageType.CLARIFICATION_REQUIRED.value,
            "payload": payload,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )

    # Also send push notification if user_id is available in context
    user_id: str | None = None
    if hasattr(message, "context") and isinstance(message.context, dict):
        user_id = message.context.get("user_id")

    if user_id:
        await send_hitl_clarification_notification(message, user_id)


async def broadcast_approval_updated(message: Any) -> None:
    """
    Broadcast approval updated message to all clients and send push notification.

    DEPRECATED: Use broadcaster.broadcast() directly.

    Args:
        message: ApprovalUpdatedMessage or dict.
    """
    broadcaster = get_broadcaster()

    payload = (
        message.model_dump() if hasattr(message, "model_dump") else (dict(message) if hasattr(message, "__iter__") else {})
    )

    await broadcaster.broadcast(
        {
            "type": AgentRequestWSMessageType.APPROVAL_UPDATED.value,
            "payload": payload,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )

    # Also send push notification if user_id is available in context
    user_id: str | None = None
    if hasattr(message, "context") and isinstance(message.context, dict):
        user_id = message.context.get("user_id")

    if user_id:
        await send_hitl_approval_updated_notification(message, user_id)


async def broadcast_execution_resumed(message: Any) -> None:
    """
    Broadcast execution resumed message to all clients and send push notification.

    DEPRECATED: Use broadcaster.broadcast() directly.

    Args:
        message: ExecutionResumedMessage or dict.
    """
    broadcaster = get_broadcaster()

    payload = (
        message.model_dump() if hasattr(message, "model_dump") else (dict(message) if hasattr(message, "__iter__") else {})
    )

    await broadcaster.broadcast(
        {
            "type": AgentRequestWSMessageType.EXECUTION_RESUMED.value,
            "payload": payload,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )

    # Also send push notification if user_id is available in context
    user_id: str | None = None
    if hasattr(message, "context") and isinstance(message.context, dict):
        user_id = message.context.get("user_id")

    if user_id:
        await send_hitl_execution_resumed_notification(message, user_id)


# =============================================================================
# Push Notification Helpers
# =============================================================================


# Global push sender instance (lazy loaded)
_push_sender: PushNotificationSender | None = None


def get_push_sender() -> PushNotificationSender | None:
    """
    Get the global push notification sender.

    Returns:
        PushNotificationSender instance if configured, None otherwise.
    """
    global _push_sender
    return _push_sender


def set_push_sender(sender: PushNotificationSender | None) -> None:
    """
    Set the global push notification sender.

    Args:
        sender: PushNotificationSender instance or None.
    """
    global _push_sender
    _push_sender = sender


def get_feature_flags() -> Any:
    """
    Get feature flag service instance.

    Returns:
        FeatureFlagService instance.
    """
    return _core_get_feature_flags()


def create_approval_push_message(request: AgentRequest) -> PushMessage:
    """
    Create a push notification message for an approval request.

    Args:
        request: The agent approval request.

    Returns:
        PushMessage formatted for approval notifications.
    """
    from mcp_server_langgraph.notifications.push_sender import PushMessage

    confidence_pct = int(request.confidence * 100) if request.confidence else 0

    return PushMessage(
        title=f"Agent needs approval ({confidence_pct}%)",
        body=request.proposed_action or "Review required",
        tag=f"hitl-{request.request_id}",
        data={
            "request_id": request.request_id,
            "type": "approval",
            "session_id": request.session_id,
            "task_id": request.task_id,
        },
        actions=[
            {"action": "approve", "title": "Approve"},
            {"action": "reject", "title": "Reject"},
        ],
    )


def create_clarification_push_message(request: AgentRequest) -> PushMessage:
    """
    Create a push notification message for a clarification request.

    Args:
        request: The agent clarification request.

    Returns:
        PushMessage formatted for clarification notifications.
    """
    from mcp_server_langgraph.notifications.push_sender import PushMessage

    return PushMessage(
        title="Agent has a question",
        body=request.question or "Input needed",
        tag=f"hitl-{request.request_id}",
        data={
            "request_id": request.request_id,
            "type": "clarification",
            "session_id": request.session_id,
            "task_id": request.task_id,
        },
    )


def create_approval_updated_push_message(message: Any) -> PushMessage:
    """
    Create a push notification message for an approval update.

    Args:
        message: The approval update message (ApprovalUpdatedMessage or similar).

    Returns:
        PushMessage formatted for approval update notifications.
    """
    from mcp_server_langgraph.notifications.push_sender import PushMessage

    status = getattr(message, "status", "updated")
    if status == "approved":
        title = "Request approved"
        body = "Your agent request has been approved"
    elif status == "rejected":
        title = "Request rejected"
        body = "Your agent request has been rejected"
    else:
        title = "Request updated"
        body = f"Your agent request status: {status}"

    return PushMessage(
        title=title,
        body=body,
        tag=f"hitl-{message.request_id}",
        data={
            "request_id": message.request_id,
            "type": "approval_updated",
            "session_id": getattr(message, "session_id", None),
            "status": status,
        },
    )


def create_execution_resumed_push_message(message: Any) -> PushMessage:
    """
    Create a push notification message for execution resumed.

    Args:
        message: The execution resumed message.

    Returns:
        PushMessage formatted for execution resumed notifications.
    """
    from mcp_server_langgraph.notifications.push_sender import PushMessage

    return PushMessage(
        title="Agent execution resumed",
        body="Your approved task is now continuing",
        tag=f"hitl-{message.request_id}",
        data={
            "request_id": message.request_id,
            "type": "execution_resumed",
            "session_id": getattr(message, "session_id", None),
            "task_id": getattr(message, "task_id", None),
        },
    )


async def send_hitl_approval_notification(
    request: AgentRequest,
    user_id: str,
) -> None:
    """
    Send a push notification for an HITL approval request.

    Only sends if push notifications are enabled via feature flags.

    Args:
        request: The agent approval request.
        user_id: The user ID to notify.
    """
    try:
        flags = get_feature_flags()
        if not flags.enable_agent_hitl_push_notifications:
            logger.debug("HITL push notifications disabled")
            return

        sender = get_push_sender()
        if sender is None:
            logger.debug("Push sender not configured")
            return

        message = create_approval_push_message(request)
        await sender.send_to_user(user_id, message)
        logger.info(f"Sent HITL approval push notification to user {user_id}")

    except Exception as e:
        logger.warning(f"Failed to send HITL approval push notification: {e}")


async def send_hitl_clarification_notification(
    request: AgentRequest,
    user_id: str,
) -> None:
    """
    Send a push notification for an HITL clarification request.

    Only sends if push notifications are enabled via feature flags.

    Args:
        request: The agent clarification request.
        user_id: The user ID to notify.
    """
    try:
        flags = get_feature_flags()
        if not flags.enable_agent_hitl_push_notifications:
            logger.debug("HITL push notifications disabled")
            return

        sender = get_push_sender()
        if sender is None:
            logger.debug("Push sender not configured")
            return

        message = create_clarification_push_message(request)
        await sender.send_to_user(user_id, message)
        logger.info(f"Sent HITL clarification push notification to user {user_id}")

    except Exception as e:
        logger.warning(f"Failed to send HITL clarification push notification: {e}")


async def send_hitl_approval_updated_notification(
    message: Any,
    user_id: str,
) -> None:
    """
    Send a push notification for an HITL approval update.

    Only sends if push notifications are enabled via feature flags.

    Args:
        message: The approval update message.
        user_id: The user ID to notify.
    """
    try:
        flags = get_feature_flags()
        if not flags.enable_agent_hitl_push_notifications:
            logger.debug("HITL push notifications disabled")
            return

        sender = get_push_sender()
        if sender is None:
            logger.debug("Push sender not configured")
            return

        push_message = create_approval_updated_push_message(message)
        await sender.send_to_user(user_id, push_message)
        logger.info(f"Sent HITL approval update push notification to user {user_id}")

    except Exception as e:
        logger.warning(f"Failed to send HITL approval update push notification: {e}")


async def send_hitl_execution_resumed_notification(
    message: Any,
    user_id: str,
) -> None:
    """
    Send a push notification for HITL execution resumed.

    Only sends if push notifications are enabled via feature flags.

    Args:
        message: The execution resumed message.
        user_id: The user ID to notify.
    """
    try:
        flags = get_feature_flags()
        if not flags.enable_agent_hitl_push_notifications:
            logger.debug("HITL push notifications disabled")
            return

        sender = get_push_sender()
        if sender is None:
            logger.debug("Push sender not configured")
            return

        push_message = create_execution_resumed_push_message(message)
        await sender.send_to_user(user_id, push_message)
        logger.info(f"Sent HITL execution resumed push notification to user {user_id}")

    except Exception as e:
        logger.warning(f"Failed to send HITL execution resumed push notification: {e}")


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Message types
    "AgentRequestWSMessageType",
    "ApprovalRequiredMessage",
    "ApprovalUpdatedMessage",
    "ClarificationRequiredMessage",
    "ExecutionResumedMessage",
    # Broadcaster
    "AgentRequestBroadcaster",
    "WebSocketConnection",
    "get_broadcaster",
    "set_broadcaster",
    # Feature flags
    "is_hitl_enabled",
    "check_hitl_enabled_for_ws",
    "check_reviewer_role",
    "get_feature_flags",
    # Token validation
    "validate_websocket_token",
    # Ping/pong
    "handle_ping",
    # Broadcast helpers
    "broadcast_approval_required",
    "broadcast_approval_updated",
    "broadcast_clarification_required",
    "broadcast_execution_resumed",
    # Push notification helpers
    "get_push_sender",
    "set_push_sender",
    "create_approval_push_message",
    "create_clarification_push_message",
    "create_approval_updated_push_message",
    "create_execution_resumed_push_message",
    "send_hitl_approval_notification",
    "send_hitl_clarification_notification",
    "send_hitl_approval_updated_notification",
    "send_hitl_execution_resumed_notification",
    # Router
    "router",
]
