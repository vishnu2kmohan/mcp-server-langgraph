"""
Budget Alerts WebSocket Handler.

Provides real-time budget alerts streaming via WebSocket using WebSocketBase.

Features:
    - Real-time budget status changes (warning, critical, exceeded)
    - Entity-based subscription (org/project/team/user)
    - Subscribe all option for admins
    - Integration with BudgetAlertBroadcaster

Message Types (Client -> Server):
    - subscribe_entities: Subscribe to specific entity budget alerts
    - subscribe_all: Subscribe to all budget alerts (admin)
    - unsubscribe: Unsubscribe from budget alerts

Response Types (Server -> Client):
    - subscribed: Confirmation of subscription
    - unsubscribed: Confirmation of unsubscription
    - budget_alert: Budget status change event
    - error: Error message
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from mcp_server_langgraph.websocket.base import WebSocketBase
from mcp_server_langgraph.websocket.types import (
    AuthUser,
    MessageEnvelope,
    WebSocketConfig,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.monitoring.cost_budget import (
        BudgetAlertBroadcaster,
        BudgetStatus,
    )
    from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

logger = logging.getLogger(__name__)


def budget_status_to_envelope(status: BudgetStatus) -> dict[str, Any]:
    """
    Convert a BudgetStatus to WebSocket message payload.

    Args:
        status: The BudgetStatus to convert.

    Returns:
        Dictionary payload for WebSocket message.
    """
    return {
        "entity_type": status.budget.entity_type,
        "entity_id": status.budget.entity_id,
        "status": status.status,
        "percent_used": status.percent_used,
        "current_spend": str(status.current_spend),
        "remaining": str(status.remaining),
        "monthly_limit_usd": str(status.budget.monthly_limit_usd),
        "message": status.message,
    }


class BudgetAlertsHandler(WebSocketBase):
    """
    WebSocket handler for real-time budget alerts.

    Extends WebSocketBase to provide budget monitoring with the
    standardized infrastructure (auth, rate limiting, metrics, etc.).

    Usage:
        handler = BudgetAlertsHandler(
            config=WebSocketConfig(
                endpoint_name="budget-alerts",
                require_auth=True,
                authz_resource_type="budget",
                authz_resource_id="alerts",
                authz_required_relation="viewer",
            ),
        )
        await handler.run(websocket)
    """

    def __init__(
        self,
        config: WebSocketConfig,
        broadcaster: BudgetAlertBroadcaster | None = None,
        metrics: WebSocketMetrics | None = None,
    ) -> None:
        """
        Initialize the budget alerts handler.

        Args:
            config: WebSocket configuration.
            broadcaster: Optional budget alert broadcaster for receiving alerts.
            metrics: Optional metrics collector.
        """
        super().__init__(config=config, metrics=metrics)
        self.subscribed_entities: set[str] = set()
        self.subscribe_all: bool = False
        self._broadcaster = broadcaster

    async def on_connect(self, user: AuthUser) -> None:
        """
        Handle connection establishment.

        Args:
            user: The authenticated user.
        """
        logger.info(
            f"Budget alerts connected: user={user.id}",
            extra={"user_id": user.id},
        )

    async def on_disconnect(self) -> None:
        """Clean up subscriptions on disconnect."""
        self.subscribed_entities.clear()
        self.subscribe_all = False

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming messages.

        Supports:
        - subscribe_entities: Subscribe to specific entity budget alerts
        - subscribe_all: Subscribe to all budget alerts
        - unsubscribe: Unsubscribe from alerts

        Args:
            message: The incoming message envelope.

        Returns:
            Response message or None.
        """
        if message.type == "subscribe_entities":
            return await self._handle_subscribe_entities(message)
        elif message.type == "subscribe_all":
            return await self._handle_subscribe_all(message)
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

    async def _handle_subscribe_entities(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle subscribe_entities message."""
        payload = message.payload or {}
        entity_ids = payload.get("entity_ids", [])

        if not entity_ids:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "missing_entity_ids",
                    "message": "entity_ids is required for subscribe_entities",
                },
                id=message.id,
            )

        for entity_id in entity_ids:
            self.subscribed_entities.add(entity_id)

        logger.info(
            f"Budget alerts subscribed to entities: {entity_ids}",
            extra={"entity_ids": entity_ids},
        )

        return MessageEnvelope(
            type="subscribed",
            payload={
                "entity_ids": list(self.subscribed_entities),
                "subscribe_all": self.subscribe_all,
            },
            id=message.id,
        )

    async def _handle_subscribe_all(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle subscribe_all message."""
        self.subscribe_all = True

        logger.info("Budget alerts subscribed to all")

        return MessageEnvelope(
            type="subscribed",
            payload={
                "entity_ids": list(self.subscribed_entities),
                "subscribe_all": True,
            },
            id=message.id,
        )

    async def _handle_unsubscribe(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle unsubscribe message."""
        self.subscribed_entities.clear()
        self.subscribe_all = False

        logger.info("Budget alerts unsubscribed")

        return MessageEnvelope(
            type="unsubscribed",
            payload={},
            id=message.id,
        )

    async def push_budget_alert(self, status: BudgetStatus) -> None:
        """
        Push a budget alert to the client if subscribed.

        Args:
            status: The BudgetStatus to push.
        """
        entity_id = status.budget.entity_id

        # Check if subscribed
        if not self.subscribe_all:
            if entity_id not in self.subscribed_entities:
                return

        if self._websocket:
            await self.send(
                MessageEnvelope(
                    type="budget_alert",
                    payload=budget_status_to_envelope(status),
                )
            )
