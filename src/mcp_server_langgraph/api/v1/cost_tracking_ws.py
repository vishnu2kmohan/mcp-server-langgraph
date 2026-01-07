"""
Cost Tracking WebSocket Endpoint.

Provides real-time cost tracking during LLM operations with
session-level and user-level budget monitoring.

URL: /api/v1/ws/usage/cost

Message Types (Client → Server):
- subscribe_session: Subscribe to cost updates for a session
- subscribe_user: Subscribe to user's budget status
- unsubscribe: Unsubscribe from updates

Message Types (Server → Client):
- session_total: Current session cost total
- user_budget: User's budget status and usage
- cost_event: Real-time cost event during LLM operation
- budget_warning: Alert when approaching budget limit
- unsubscribed: Confirmation of unsubscription
- error: Error message
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, WebSocket

from mcp_server_langgraph.websocket.base import WebSocketBase
from mcp_server_langgraph.websocket.services.cost_tracking import (
    CostTrackingServiceAdapter,
    get_websocket_cost_service,
)
from mcp_server_langgraph.websocket.types import AuthUser, MessageEnvelope, WebSocketConfig

logger = logging.getLogger(__name__)

# =============================================================================
# Router
# =============================================================================

router = APIRouter(tags=["websocket", "cost"])


# =============================================================================
# Handler
# =============================================================================


class CostTrackingWebSocketHandler(WebSocketBase):
    """
    WebSocket handler for real-time cost tracking.

    Provides session-level and user-level cost monitoring with
    budget alerts and real-time cost event streaming.
    """

    def __init__(self) -> None:
        """Initialize the handler with configuration."""
        config = WebSocketConfig(
            endpoint_name="cost-tracking",
            require_auth=True,
            heartbeat_interval=30,
            idle_timeout=1800,  # 30 minutes
            rate_limit_per_minute=120,  # 2 msg/sec for cost updates
        )
        super().__init__(config)

        # Subscription state
        self._subscribed_sessions: set[str] = set()
        self._subscribed_user_id: str | None = None

        # Initialize cost tracking service adapter (integrates with Redis + database)
        self._cost_service: CostTrackingServiceAdapter = get_websocket_cost_service()

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming WebSocket messages.

        Args:
            message: The incoming message envelope.

        Returns:
            Response message or None.
        """
        message_type = message.type

        if message_type == "subscribe_session":
            return await self._handle_subscribe_session(message)
        elif message_type == "subscribe_user":
            return await self._handle_subscribe_user(message)
        elif message_type == "unsubscribe":
            return await self._handle_unsubscribe(message)
        else:
            logger.warning(f"Unknown message type: {message_type}")
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "unknown_type",
                    "message": f"Unknown message type: {message_type}",
                },
                id=message.id,
            )

    async def _handle_subscribe_session(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle subscribe_session message."""
        session_id = message.payload.get("session_id") if message.payload else None

        if not session_id:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "missing_session_id",
                    "message": "session_id is required",
                },
                id=message.id,
            )

        self._subscribed_sessions.add(session_id)

        # Get session cost total (mock for now)
        total = await self._get_session_total(session_id)

        return MessageEnvelope(
            type="session_total",
            payload={
                "session_id": session_id,
                **total,
            },
            id=message.id,
        )

    async def _handle_subscribe_user(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle subscribe_user message."""
        user_id = message.payload.get("user_id") if message.payload else None

        if not user_id:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "missing_user_id",
                    "message": "user_id is required",
                },
                id=message.id,
            )

        self._subscribed_user_id = user_id

        # Get user budget (mock for now)
        budget = await self._get_user_budget(user_id)

        return MessageEnvelope(
            type="user_budget",
            payload={
                "user_id": user_id,
                **budget,
            },
            id=message.id,
        )

    async def _handle_unsubscribe(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle unsubscribe message."""
        session_id = message.payload.get("session_id") if message.payload else None

        if session_id and session_id in self._subscribed_sessions:
            self._subscribed_sessions.discard(session_id)

        return MessageEnvelope(
            type="unsubscribed",
            payload={"session_id": session_id},
            id=message.id,
        )

    async def _get_session_total(self, session_id: str) -> dict[str, Any]:
        """
        Get cost total for a session from the cost tracking service.

        Delegates to CostTrackingServiceAdapter which queries Redis cache
        and database for actual cost data when available.
        """
        session_cost = await self._cost_service.get_session_cost(session_id)
        return {
            "total_cost": str(Decimal(str(session_cost.get("total_cost", 0.0)))),
            "currency": "USD",
            "token_count": session_cost.get("token_count", 0),
            "request_count": 0,  # Would need request count tracking
            "last_updated": session_cost.get("updated_at", datetime.now(UTC).isoformat()),
        }

    async def _get_user_budget(self, user_id: str) -> dict[str, Any]:
        """
        Get budget status for a user from the cost tracking service.

        Delegates to CostTrackingServiceAdapter which queries the budget storage
        and calculates current usage from cost records.
        """
        user_budget = await self._cost_service.get_user_budget(user_id)
        return {
            "budget_limit": user_budget.get("budget_limit", 100.0),
            "current_usage": user_budget.get("current_usage", 0.0),
            "remaining": user_budget.get("remaining", 100.0),
            "currency": "USD",
            "period": "monthly",
            "period_start": datetime.now(UTC).replace(day=1).isoformat(),
            "warning_threshold": 0.8,  # Warn at 80% usage
        }

    async def on_connect(self, user: AuthUser) -> None:
        """Called when connection is established."""
        logger.info(
            "Cost tracking WebSocket connected",
            extra={"user_id": user.id},
        )

    async def on_disconnect(self) -> None:
        """Called when connection is closed."""
        self._subscribed_sessions.clear()
        self._subscribed_user_id = None
        logger.info(
            "Cost tracking WebSocket disconnected",
            extra={"user_id": self._user.id if self._user else "unknown"},
        )


# =============================================================================
# WebSocket Route
# =============================================================================


@router.websocket("")
async def cost_tracking_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time cost tracking.

    Provides session-level and user-level cost monitoring with
    budget alerts and real-time cost event streaming.
    """
    handler = CostTrackingWebSocketHandler()
    await handler.run(websocket)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "router",
    "CostTrackingWebSocketHandler",
]
