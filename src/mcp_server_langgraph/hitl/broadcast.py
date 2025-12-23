"""
HITL Agent Request Broadcasting.

Provides WebSocket broadcasting infrastructure for Human-in-the-Loop
agent request notifications.

Message Types (Server -> Client):
- approval_required: New approval request from agent
- clarification_required: Agent needs user input/clarification
- approval_updated: Status change (approved/rejected)
- execution_resumed: Agent resumed after decision
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)


# =============================================================================
# Message Type Enum
# =============================================================================


class AgentRequestWSMessageType(StrEnum):
    """WebSocket message types for agent requests."""

    # Server -> Client
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


# =============================================================================
# Message Models
# =============================================================================


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
    options: list[dict[str, Any]] = Field(default_factory=list, description="Options for choice type")
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


# =============================================================================
# WebSocket Connection Info
# =============================================================================


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


# =============================================================================
# Broadcaster Service
# =============================================================================


class AgentRequestBroadcaster:
    """Manages WebSocket connections and message broadcasting for HITL requests."""

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

    @property
    def connection_count(self) -> int:
        """Get current number of active connections."""
        return len(self._connections)

    def get_connections_for_session(self, session_id: str) -> list[WebSocketConnection]:
        """Get all connections for a specific session."""
        return [conn for conn in self._connections.values() if conn.session_id == session_id]


__all__ = [
    "AgentRequestBroadcaster",
    "AgentRequestWSMessageType",
    "ApprovalRequiredMessage",
    "ApprovalUpdatedMessage",
    "ClarificationRequiredMessage",
    "ExecutionResumedMessage",
    "WebSocketConnection",
]
