"""
Trace WebSocket Handler.

Provides real-time trace/span streaming using the standardized WebSocketBase class.

Features:
    - Real-time trace span streaming
    - Filter by service_name, operation_name, trace_id, duration, status
    - Clear filters to receive all traces
    - Query recent traces

Message Types (Client -> Server):
    - subscribe: Subscribe to trace events
    - unsubscribe: Unsubscribe from trace events
    - set_filter: Set trace filter criteria
    - clear_filter: Clear all filters (receive all traces)
    - get_recent: Get recent traces matching current filter

Response Types (Server -> Client):
    - subscribed: Successfully subscribed to traces
    - unsubscribed: Successfully unsubscribed from traces
    - filter_updated: Filter has been updated
    - filter_cleared: Filter has been cleared
    - recent_traces: Recent trace data
    - trace_span: Real-time trace span update
    - error: Error message
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from mcp_server_langgraph.websocket.base import WebSocketBase
from mcp_server_langgraph.websocket.mixins import BroadcasterMixin
from mcp_server_langgraph.websocket.types import (
    AuthUser,
    MessageEnvelope,
    WebSocketConfig,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.websocket.metrics import WebSocketMetrics

logger = logging.getLogger(__name__)


@dataclass
class TraceFilter:
    """Filter criteria for trace spans."""

    service_name: str | None = None
    operation_name: str | None = None
    trace_id: str | None = None
    min_duration_ms: float | None = None
    status: str | None = None  # "OK", "ERROR", "UNSET"
    session_id: str | None = None  # Filter by session.id for DevTools


@runtime_checkable
class TraceBroadcasterProtocol(Protocol):
    """Protocol defining the trace broadcaster interface."""

    async def subscribe(self, websocket: Any, filter_: TraceFilter | None = None) -> None:
        """Subscribe to trace events with optional filter."""
        ...

    async def unsubscribe(self, websocket: Any) -> None:
        """Unsubscribe from trace events."""
        ...

    async def get_recent_traces(
        self,
        filter_: TraceFilter | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get recent traces matching the filter."""
        ...


class TraceHandler(WebSocketBase, BroadcasterMixin):
    """
    WebSocket handler for real-time trace/span streaming.

    Extends WebSocketBase to provide trace streaming with the
    standardized infrastructure (auth, rate limiting, metrics, etc.).

    Usage:
        handler = TraceHandler(
            config=WebSocketConfig(
                endpoint_name="traces",
                require_auth=True,
                authz_resource_type="traces",
                authz_resource_id="trace-stream",
                authz_required_relation="viewer",
            ),
            broadcaster=get_trace_broadcaster(),
        )
        await handler.run(websocket)
    """

    def __init__(
        self,
        config: WebSocketConfig,
        broadcaster: TraceBroadcasterProtocol,
        metrics: WebSocketMetrics | None = None,
    ) -> None:
        """
        Initialize the trace handler.

        Args:
            config: WebSocket configuration.
            broadcaster: Trace broadcaster for managing subscriptions.
            metrics: Optional metrics collector.
        """
        super().__init__(config=config, metrics=metrics)
        self._broadcaster = broadcaster
        self._current_filter: TraceFilter = TraceFilter()
        # Note: _subscribed is managed by BroadcasterMixin
        self._session_id: str | None = None

    async def on_connect(self, user: AuthUser) -> None:
        """
        Handle successful connection.

        Uses session_id from base class (extracted from query params in run())
        for session-scoped trace filtering. Subscribes to trace events.

        Args:
            user: The authenticated user.
        """
        # Use session_id from base class if available (populated in run()).
        # Fallback to direct query_params extraction for tests that bypass run().
        if self.session_id:
            self._session_id = self.session_id
        elif self._websocket:
            query_params = getattr(self._websocket, "query_params", {}) or {}
            self._session_id = query_params.get("session_id")

        if self._websocket:
            # Use BroadcasterMixin's subscribe() with filter_ kwarg
            await self.subscribe(filter_=self._current_filter)

        logger.info(
            f"Trace stream connected: user={user.id}",
            extra={"user_id": user.id, "session_id": self.session_id},
        )

    async def on_disconnect(self) -> None:
        """
        Handle disconnection.

        Unsubscribes from trace broadcaster.
        """
        # Use BroadcasterMixin's unsubscribe() for cleanup
        await self.unsubscribe()
        logger.info(f"Trace stream disconnected: user={self.user_id}")

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """
        Handle incoming messages.

        Args:
            message: The incoming message envelope.

        Returns:
            Response message envelope, or None if no response needed.
        """
        if message.type == "subscribe":
            return await self._handle_subscribe(message)
        elif message.type == "unsubscribe":
            return await self._handle_unsubscribe(message)
        elif message.type == "set_filter":
            return await self._handle_set_filter(message)
        elif message.type == "clear_filter":
            return await self._handle_clear_filter(message)
        elif message.type == "get_recent":
            return await self._handle_get_recent(message)
        else:
            return self.create_unknown_message_error(message.type, message.id)

    async def _handle_subscribe(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle subscribe message."""
        if self._websocket and not self._subscribed:
            # Use BroadcasterMixin's subscribe() with filter_ kwarg
            await self.subscribe(filter_=self._current_filter)
            logger.info(f"User {self.user_id} subscribed to traces")

        return self.create_subscribed_response(
            correlation_id=message.id,
            message="Successfully subscribed to traces",
        )

    async def _handle_unsubscribe(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle unsubscribe message."""
        if self._websocket and self._subscribed:
            # Use BroadcasterMixin's unsubscribe()
            await self.unsubscribe()
            logger.info(f"User {self.user_id} unsubscribed from traces")

        return self.create_unsubscribed_response(
            correlation_id=message.id,
            message="Successfully unsubscribed from traces",
        )

    async def _handle_set_filter(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle set_filter message."""
        payload = message.payload or {}

        new_filter = TraceFilter(
            service_name=payload.get("service_name"),
            operation_name=payload.get("operation_name"),
            trace_id=payload.get("trace_id"),
            min_duration_ms=payload.get("min_duration_ms"),
            status=payload.get("status"),
            session_id=payload.get("session_id"),
        )

        # Resubscribe with new filter using BroadcasterMixin methods
        if self._websocket and self._subscribed:
            await self.unsubscribe()
            await self.subscribe(filter_=new_filter)

        self._current_filter = new_filter
        logger.info(f"User {self.user_id} updated trace filter: {new_filter}")

        return MessageEnvelope(
            type="filter_updated",
            payload={
                "filter": {
                    "service_name": new_filter.service_name,
                    "operation_name": new_filter.operation_name,
                    "trace_id": new_filter.trace_id,
                    "min_duration_ms": new_filter.min_duration_ms,
                    "status": new_filter.status,
                    "session_id": new_filter.session_id,
                }
            },
            id=message.id,
        )

    async def _handle_clear_filter(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle clear_filter message."""
        new_filter = TraceFilter()

        # Resubscribe with empty filter using BroadcasterMixin methods
        if self._websocket and self._subscribed:
            await self.unsubscribe()
            await self.subscribe(filter_=new_filter)

        self._current_filter = new_filter
        logger.info(f"User {self.user_id} cleared trace filter")

        return MessageEnvelope(
            type="filter_cleared",
            payload={"message": "Filter cleared, receiving all traces"},
            id=message.id,
        )

    async def _handle_get_recent(self, message: MessageEnvelope) -> MessageEnvelope:
        """Handle get_recent message."""
        payload = message.payload or {}
        limit = payload.get("limit", 50)

        # Get recent traces matching current filter
        traces = await self._broadcaster.get_recent_traces(
            filter_=self._current_filter,
            limit=limit,
        )

        return MessageEnvelope(
            type="recent_traces",
            payload={"traces": traces, "count": len(traces)},
            id=message.id,
        )
