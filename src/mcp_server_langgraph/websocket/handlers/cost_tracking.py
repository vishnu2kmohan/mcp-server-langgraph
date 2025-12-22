"""
Cost Tracking WebSocket Handler.

Provides real-time cost tracking during LLM operations using WebSocketBase.

Features:
    - Real-time cost events as LLM operations occur
    - Session total cost tracking
    - User budget monitoring
    - Budget warning alerts

Message Types (Client -> Server):
    - subscribe_session: Subscribe to cost updates for a session
    - subscribe_user: Subscribe to user budget updates
    - unsubscribe: Unsubscribe from cost updates

Response Types (Server -> Client):
    - cost_event: Individual cost event (e.g., LLM call completed)
    - session_total: Current total cost for a session
    - user_budget: User budget status
    - budget_warning: Alert when approaching budget limit
    - unsubscribed: Confirmation of unsubscription
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
class CostServiceProtocol(Protocol):
    """Protocol defining the cost service interface."""

    async def get_session_cost(self, session_id: str) -> dict[str, Any]:
        """Get current cost for a session."""
        ...

    async def get_user_budget(self, user_id: str) -> dict[str, Any]:
        """Get budget status for a user."""
        ...


class CostTrackingHandler(WebSocketBase):
    """
    WebSocket handler for real-time cost tracking.

    Extends WebSocketBase to provide cost monitoring during LLM operations
    with the standardized infrastructure (auth, rate limiting, metrics, etc.).

    Usage:
        handler = CostTrackingHandler(
            config=WebSocketConfig(
                endpoint_name="cost-tracking",
                require_auth=True,
                authz_resource_type="cost",
                authz_resource_id="usage",
                authz_required_relation="viewer",
            ),
            cost_service=get_cost_service(),
        )
        await handler.run(websocket)
    """

    def __init__(
        self,
        config: WebSocketConfig,
        cost_service: CostServiceProtocol,
        metrics: WebSocketMetrics | None = None,
    ) -> None:
        """
        Initialize the cost tracking handler.

        Args:
            config: WebSocket configuration.
            cost_service: Cost tracking service.
            metrics: Optional metrics collector.
        """
        super().__init__(config=config, metrics=metrics)
        self._cost_service = cost_service
        self.subscribed_sessions: set[str] = set()
        self.subscribed_users: set[str] = set()

    async def on_connect(self, user: AuthUser) -> None:
        """
        Handle connection establishment.

        Args:
            user: The authenticated user.
        """
        logger.info(
            f"Cost tracking connected: user={user.id}",
            extra={"user_id": user.id},
        )

    async def on_disconnect(self) -> None:
        """Clean up subscriptions on disconnect."""
        self.subscribed_sessions.clear()
        self.subscribed_users.clear()

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming messages.

        Supports:
        - subscribe_session: Subscribe to session cost updates
        - subscribe_user: Subscribe to user budget updates
        - unsubscribe: Unsubscribe from updates

        Args:
            message: The incoming message envelope.

        Returns:
            Response message or None.
        """
        if message.type == "subscribe_session":
            return await self._handle_subscribe_session(message)
        elif message.type == "subscribe_user":
            return await self._handle_subscribe_user(message)
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

    async def _handle_subscribe_session(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle subscribe_session message."""
        payload = message.payload or {}
        session_id = payload.get("session_id")

        if not session_id:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "missing_session_id",
                    "message": "session_id is required for subscribe_session",
                },
                id=message.id,
            )

        try:
            session_cost = await self._cost_service.get_session_cost(session_id)
            self.subscribed_sessions.add(session_id)

            return MessageEnvelope(
                type="session_total",
                payload=session_cost,
                id=message.id,
            )

        except Exception as e:
            logger.warning(f"Error getting session cost for {session_id}: {e}")
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "session_cost_error",
                    "message": str(e),
                },
                id=message.id,
            )

    async def _handle_subscribe_user(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle subscribe_user message."""
        payload = message.payload or {}
        user_id = payload.get("user_id")

        if not user_id:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "missing_user_id",
                    "message": "user_id is required for subscribe_user",
                },
                id=message.id,
            )

        try:
            user_budget = await self._cost_service.get_user_budget(user_id)
            self.subscribed_users.add(user_id)

            return MessageEnvelope(
                type="user_budget",
                payload=user_budget,
                id=message.id,
            )

        except Exception as e:
            logger.warning(f"Error getting user budget for {user_id}: {e}")
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "user_budget_error",
                    "message": str(e),
                },
                id=message.id,
            )

    async def _handle_unsubscribe(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle unsubscribe message."""
        payload = message.payload or {}
        session_id = payload.get("session_id")
        user_id = payload.get("user_id")

        if session_id:
            self.subscribed_sessions.discard(session_id)
        if user_id:
            self.subscribed_users.discard(user_id)

        return MessageEnvelope(
            type="unsubscribed",
            payload={
                "session_id": session_id,
                "user_id": user_id,
            },
            id=message.id,
        )

    async def push_cost_event(self, session_id: str, cost_data: dict[str, Any]) -> None:
        """
        Push a cost event to the client if subscribed.

        Args:
            session_id: The session this cost event belongs to.
            cost_data: The cost event data.
        """
        if session_id not in self.subscribed_sessions:
            return

        if self._websocket:
            await self.send(
                MessageEnvelope(
                    type="cost_event",
                    payload={
                        "session_id": session_id,
                        **cost_data,
                    },
                )
            )

    async def push_budget_warning(self, user_id: str, warning_data: dict[str, Any]) -> None:
        """
        Push a budget warning to the client.

        Args:
            user_id: The user approaching their budget limit.
            warning_data: The warning data.
        """
        if user_id not in self.subscribed_users:
            return

        if self._websocket:
            await self.send(
                MessageEnvelope(
                    type="budget_warning",
                    payload={
                        "user_id": user_id,
                        **warning_data,
                    },
                )
            )
