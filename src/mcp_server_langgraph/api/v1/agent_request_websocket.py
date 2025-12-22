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
        from mcp_server_langgraph.core.feature_flags import get_feature_flag_service

        ff = get_feature_flag_service()
        return ff.is_enabled("hitl_approvals")
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
        if isinstance(result, dict):
            # Direct dict return from mocked auth
            return result
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
    Broadcast approval required message to all clients.

    DEPRECATED: Use broadcaster.broadcast() directly.

    Args:
        message: ApprovalRequiredMessage or AgentRequest object.
    """
    broadcaster = get_broadcaster()

    # Convert message to dict (handles both Pydantic models)
    payload = (
        message.model_dump()
        if hasattr(message, "model_dump")
        else (dict(message) if hasattr(message, "__iter__") else {})
    )

    await broadcaster.broadcast(
        {
            "type": AgentRequestWSMessageType.APPROVAL_REQUIRED.value,
            "payload": payload,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


async def broadcast_clarification_required(message: Any) -> None:
    """
    Broadcast clarification required message to all clients.

    DEPRECATED: Use broadcaster.broadcast() directly.

    Args:
        message: ClarificationRequiredMessage or AgentRequest object.
    """
    broadcaster = get_broadcaster()

    payload = (
        message.model_dump()
        if hasattr(message, "model_dump")
        else (dict(message) if hasattr(message, "__iter__") else {})
    )

    await broadcaster.broadcast(
        {
            "type": AgentRequestWSMessageType.CLARIFICATION_REQUIRED.value,
            "payload": payload,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


async def broadcast_approval_updated(message: Any) -> None:
    """
    Broadcast approval updated message to all clients.

    DEPRECATED: Use broadcaster.broadcast() directly.

    Args:
        message: ApprovalUpdatedMessage or dict.
    """
    broadcaster = get_broadcaster()

    payload = (
        message.model_dump()
        if hasattr(message, "model_dump")
        else (dict(message) if hasattr(message, "__iter__") else {})
    )

    await broadcaster.broadcast(
        {
            "type": AgentRequestWSMessageType.APPROVAL_UPDATED.value,
            "payload": payload,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


async def broadcast_execution_resumed(message: Any) -> None:
    """
    Broadcast execution resumed message to all clients.

    DEPRECATED: Use broadcaster.broadcast() directly.

    Args:
        message: ExecutionResumedMessage or dict.
    """
    broadcaster = get_broadcaster()

    payload = (
        message.model_dump()
        if hasattr(message, "model_dump")
        else (dict(message) if hasattr(message, "__iter__") else {})
    )

    await broadcaster.broadcast(
        {
            "type": AgentRequestWSMessageType.EXECUTION_RESUMED.value,
            "payload": payload,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


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
    # Token validation
    "validate_websocket_token",
    # Ping/pong
    "handle_ping",
    # Broadcast helpers
    "broadcast_approval_required",
    "broadcast_approval_updated",
    "broadcast_clarification_required",
    "broadcast_execution_resumed",
    # Router
    "router",
]
