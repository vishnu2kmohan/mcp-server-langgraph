"""
Agent Request (HITL) WebSocket Handler.

Provides real-time Human-in-the-Loop (HITL) notifications using WebSocketBase.

Features:
    - Approval request notifications (low confidence triggers)
    - Clarification request notifications (agent needs input)
    - Status update notifications
    - Session-scoped message filtering

Message Types (Client -> Server):
    - subscribe: Subscribe to HITL notifications
    - unsubscribe: Unsubscribe from notifications

Response Types (Server -> Client):
    - subscribed: Subscription confirmed
    - unsubscribed: Unsubscription confirmed
    - approval_required: New approval request from agent
    - clarification_required: Agent needs user input
    - approval_updated: Status change notification
    - execution_resumed: Agent resumed execution
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
class HITLBroadcasterProtocol(Protocol):
    """Protocol defining the HITL broadcaster interface."""

    async def connect(self, websocket: Any, session_id: str, user_id: str, accept: bool = True) -> None:
        """Connect and register a WebSocket."""
        ...

    def disconnect(self, websocket: Any) -> None:
        """Disconnect and unregister a WebSocket."""
        ...

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast message to all connections."""
        ...

    async def send_to_session(self, session_id: str, message: dict[str, Any]) -> None:
        """Send message to a specific session."""
        ...


class AgentRequestHandler(WebSocketBase):
    """
    WebSocket handler for Human-in-the-Loop (HITL) agent request notifications.

    Extends WebSocketBase to provide HITL notifications with the
    standardized infrastructure (auth, rate limiting, metrics, etc.).

    Usage:
        handler = AgentRequestHandler(
            config=WebSocketConfig(
                endpoint_name="agent-request",
                require_auth=True,
                authz_resource_type="workflow",
                authz_resource_id="hitl",
                authz_required_relation="editor",
            ),
            broadcaster=get_broadcaster(),
            session_id=session_id,
        )
        await handler.run(websocket)
    """

    def __init__(
        self,
        config: WebSocketConfig,
        broadcaster: HITLBroadcasterProtocol,
        session_id: str | None = None,
        metrics: WebSocketMetrics | None = None,
    ) -> None:
        """
        Initialize the agent request handler.

        Args:
            config: WebSocket configuration.
            broadcaster: HITL broadcaster for managing subscriptions.
            session_id: Optional session ID for filtering messages.
            metrics: Optional metrics collector.
        """
        super().__init__(config=config, metrics=metrics)
        self._broadcaster = broadcaster
        self._session_id = session_id or "global"
        self._subscribed: bool = False

    async def on_connect(self, user: AuthUser) -> None:
        """
        Handle connection establishment.

        Uses session_id from base class (extracted from query params in run())
        if not provided via constructor, enabling session-scoped HITL notifications.

        Args:
            user: The authenticated user.
        """
        # Extract session_id from query params if still using default "global"
        # Note: We check query_params directly since this handler may set
        # its own _session_id in __init__ which shadows the base class property.
        if self._session_id == "global" and self._websocket:
            query_params = getattr(self._websocket, "query_params", {}) or {}
            url_session_id = query_params.get("session_id")
            if url_session_id:
                self._session_id = url_session_id

        if self._websocket:
            # Pass accept=False because WebSocketBase already accepted the connection
            await self._broadcaster.connect(self._websocket, self._session_id, user.id, accept=False)
        logger.info(
            f"Agent request WebSocket connected: user={user.id}, session={self._session_id}",
            extra={"user_id": user.id, "session_id": self._session_id},
        )

    async def on_disconnect(self) -> None:
        """Clean up on disconnect."""
        if self._websocket:
            self._broadcaster.disconnect(self._websocket)
        self._subscribed = False
        logger.info(
            f"Agent request WebSocket disconnected: user={self.user_id}",
            extra={"user_id": self.user_id, "session_id": self._session_id},
        )

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming messages.

        Supports:
        - subscribe: Subscribe to HITL notifications
        - unsubscribe: Unsubscribe from notifications

        Args:
            message: The incoming message envelope.

        Returns:
            Response message or None.
        """
        if message.type == "subscribe":
            return await self._handle_subscribe(message)
        elif message.type == "unsubscribe":
            return await self._handle_unsubscribe(message)
        else:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "unknown_message_type",
                    "message": f"Unknown message type: {message.type}",
                },
                id=message.id,
            )

    async def _handle_subscribe(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle subscribe message."""
        payload = message.payload or {}
        # Allow client to specify a different session ID
        session_id = payload.get("session_id", self._session_id)

        self._session_id = session_id
        self._subscribed = True

        return self.create_subscribed_response(
            correlation_id=message.id,
            message="Successfully subscribed to HITL notifications",
            extra_payload={"session_id": session_id},
        )

    async def _handle_unsubscribe(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle unsubscribe message."""
        self._subscribed = False

        return self.create_unsubscribed_response(
            correlation_id=message.id,
            message="Successfully unsubscribed from HITL notifications",
        )

    async def push_approval_required(self, request: dict[str, Any]) -> None:
        """
        Push an approval request to the client.

        Only sends if the client is subscribed.

        Args:
            request: The approval request data.
        """
        await self.send_if_subscribed(
            {
                "type": "approval_required",
                "payload": request,
            }
        )

    async def push_clarification_required(self, request: dict[str, Any]) -> None:
        """
        Push a clarification request to the client.

        Only sends if the client is subscribed.

        Args:
            request: The clarification request data.
        """
        await self.send_if_subscribed(
            {
                "type": "clarification_required",
                "payload": request,
            }
        )

    async def push_approval_updated(self, request_id: str, status: str, decided_by: str, reason: str | None = None) -> None:
        """
        Push an approval status update to the client.

        Only sends if the client is subscribed.

        Args:
            request_id: Request identifier.
            status: New status (approved, rejected).
            decided_by: Who made the decision.
            reason: Optional reason for decision.
        """
        await self.send_if_subscribed(
            {
                "type": "approval_updated",
                "payload": {
                    "request_id": request_id,
                    "status": status,
                    "decided_by": decided_by,
                    "reason": reason,
                },
            }
        )

    async def push_execution_resumed(self, request_id: str, task_id: str, agent_name: str, status: str) -> None:
        """
        Push an execution resumed notification to the client.

        Only sends if the client is subscribed.

        Args:
            request_id: Request identifier.
            task_id: Task identifier.
            agent_name: Name of the agent.
            status: Final status (approved, rejected).
        """
        await self.send_if_subscribed(
            {
                "type": "execution_resumed",
                "payload": {
                    "request_id": request_id,
                    "task_id": task_id,
                    "agent_name": agent_name,
                    "status": status,
                },
            }
        )
