"""
Audit WebSocket Handler.

Provides real-time audit event streaming using the standardized WebSocketBase class.

Features:
    - Real-time audit event streaming
    - Filter by category, regulation, actor, event type
    - Admin/compliance officer access (enforced via OpenFGA)

Message Types (Client -> Server):
    - set_filter: Set event filter criteria
    - clear_filter: Clear all filters (receive all events)

Response Types (Server -> Client):
    - filter_updated: Filter has been updated
    - audit_event: Real-time audit event
    - error: Error message
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
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


@dataclass
class AuditFilter:
    """Filter criteria for audit events."""

    categories: list[str] | None = None
    regulations: list[str] | None = None
    actors: list[str] | None = None
    event_types: list[str] | None = None


@runtime_checkable
class AuditBroadcasterProtocol(Protocol):
    """Protocol defining the audit broadcaster interface."""

    async def subscribe(self, websocket: Any, filter_: Any = None) -> None:
        """Subscribe to audit events."""
        ...

    async def unsubscribe(self, websocket: Any) -> None:
        """Unsubscribe from audit events."""
        ...


class AuditHandler(WebSocketBase):
    """
    WebSocket handler for real-time audit event streaming.

    Extends WebSocketBase to provide audit streaming with the
    standardized infrastructure (auth, rate limiting, metrics, etc.).

    Usage:
        handler = AuditHandler(
            config=WebSocketConfig(
                endpoint_name="audit",
                require_auth=True,
                authz_resource_type="logs",
                authz_resource_id="audit",
                authz_required_relation="viewer",
            ),
            broadcaster=get_audit_event_broadcaster(),
        )
        await handler.run(websocket)
    """

    def __init__(
        self,
        config: WebSocketConfig,
        broadcaster: AuditBroadcasterProtocol,
        metrics: WebSocketMetrics | None = None,
    ) -> None:
        """
        Initialize the audit handler.

        Args:
            config: WebSocket configuration.
            broadcaster: Audit event broadcaster for managing subscriptions.
            metrics: Optional metrics collector.
        """
        super().__init__(config=config, metrics=metrics)
        self._broadcaster = broadcaster
        self._current_filter: AuditFilter = AuditFilter()

    async def on_connect(self, user: AuthUser) -> None:
        """
        Handle connection establishment.

        Args:
            user: The authenticated user.
        """
        # Subscribe to all events initially (no filter)
        if self._websocket:
            await self._broadcaster.subscribe(self._websocket, self._current_filter)
        logger.info(
            f"Audit stream connected: user={user.id}",
            extra={"user_id": user.id},
        )

    async def on_disconnect(self) -> None:
        """Clean up on disconnect."""
        if self._websocket:
            await self._broadcaster.unsubscribe(self._websocket)
        logger.info(
            f"Audit stream disconnected: user={self.user_id}",
            extra={"user_id": self.user_id},
        )

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming messages.

        Supports:
        - set_filter: Set event filter criteria
        - clear_filter: Clear all filters

        Args:
            message: The incoming message envelope.

        Returns:
            Response message or None.
        """
        if message.type == "set_filter":
            return await self._handle_set_filter(message)
        elif message.type == "clear_filter":
            return await self._handle_clear_filter(message)
        else:
            return MessageEnvelope(
                type="error",
                payload={
                    "code": "unknown_message_type",
                    "message": f"Unknown message type: {message.type}",
                },
                id=message.id,
            )

    async def _handle_set_filter(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle set_filter message."""
        payload = message.payload or {}

        # Create new filter from payload
        new_filter = AuditFilter(
            categories=payload.get("categories"),
            regulations=payload.get("regulations"),
            actors=payload.get("actors"),
            event_types=payload.get("event_types"),
        )

        # Re-subscribe with new filter
        if self._websocket:
            await self._broadcaster.unsubscribe(self._websocket)
            await self._broadcaster.subscribe(self._websocket, new_filter)

        self._current_filter = new_filter

        return MessageEnvelope(
            type="filter_updated",
            payload={
                "filter": {
                    "categories": new_filter.categories,
                    "regulations": new_filter.regulations,
                    "actors": new_filter.actors,
                    "event_types": new_filter.event_types,
                }
            },
            id=message.id,
        )

    async def _handle_clear_filter(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle clear_filter message."""
        # Clear filter (receive all events)
        new_filter = AuditFilter()

        # Re-subscribe with empty filter
        if self._websocket:
            await self._broadcaster.unsubscribe(self._websocket)
            await self._broadcaster.subscribe(self._websocket, new_filter)

        self._current_filter = new_filter

        return MessageEnvelope(
            type="filter_updated",
            payload={
                "filter": {
                    "categories": None,
                    "regulations": None,
                    "actors": None,
                    "event_types": None,
                }
            },
            id=message.id,
        )

    async def push_audit_event(self, event: dict[str, Any]) -> None:
        """
        Push an audit event to the client.

        Args:
            event: The audit event data to send.
        """
        if self._websocket:
            await self._websocket.send_json(
                {
                    "type": "audit_event",
                    "payload": event,
                }
            )
