"""
Trace Broadcaster for real-time trace streaming.

Manages WebSocket subscriptions for trace/span streaming.
Integrates with OpenTelemetry to receive and broadcast trace updates.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from starlette.websockets import WebSocket

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


@dataclass
class Subscription:
    """Represents a WebSocket subscription with optional filter."""

    websocket: WebSocket
    filter_: TraceFilter | None = None


class TraceBroadcaster:
    """
    Broadcaster for real-time trace streaming.

    Manages WebSocket subscriptions and broadcasts trace spans
    to connected clients based on their filters.

    Example:
        broadcaster = TraceBroadcaster()

        # Subscribe a client
        await broadcaster.subscribe(websocket, TraceFilter(service_name="my-service"))

        # Broadcast a new span
        await broadcaster.broadcast_span({
            "trace_id": "abc123",
            "span_id": "def456",
            "service_name": "my-service",
            "operation_name": "http.request",
            "duration_ms": 150.5,
            "status": "OK",
        })

        # Unsubscribe
        await broadcaster.unsubscribe(websocket)
    """

    def __init__(self) -> None:
        """Initialize the trace broadcaster."""
        self._subscriptions: dict[WebSocket, TraceFilter | None] = {}
        self._lock = asyncio.Lock()
        # In-memory buffer for recent traces (for get_recent_traces)
        self._recent_traces: list[dict[str, Any]] = []
        self._max_recent_traces = 100

    async def subscribe(
        self,
        websocket: WebSocket,
        filter_: TraceFilter | None = None,
    ) -> None:
        """
        Subscribe a WebSocket to trace events.

        Args:
            websocket: The WebSocket connection to subscribe.
            filter_: Optional filter criteria for traces.
        """
        async with self._lock:
            self._subscriptions[websocket] = filter_
            logger.info(f"WebSocket subscribed to traces (total: {len(self._subscriptions)})")

    async def unsubscribe(self, websocket: WebSocket) -> None:
        """
        Unsubscribe a WebSocket from trace events.

        Args:
            websocket: The WebSocket connection to unsubscribe.
        """
        async with self._lock:
            if websocket in self._subscriptions:
                del self._subscriptions[websocket]
                logger.info(f"WebSocket unsubscribed from traces (total: {len(self._subscriptions)})")

    async def get_recent_traces(
        self,
        filter_: TraceFilter | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get recent traces matching the filter.

        Args:
            filter_: Optional filter criteria.
            limit: Maximum number of traces to return.

        Returns:
            List of recent trace spans.
        """
        async with self._lock:
            traces = self._recent_traces.copy()

        # Apply filter
        if filter_:
            traces = [t for t in traces if self._matches_filter(t, filter_)]

        # Apply limit
        return traces[:limit]

    async def broadcast_span(self, span: dict[str, Any]) -> None:
        """
        Broadcast a trace span to all matching subscribers.

        Args:
            span: The span data to broadcast.
        """
        # Add to recent traces buffer
        async with self._lock:
            self._recent_traces.insert(0, span)
            if len(self._recent_traces) > self._max_recent_traces:
                self._recent_traces = self._recent_traces[: self._max_recent_traces]
            subscriptions = list(self._subscriptions.items())

        # Broadcast to matching subscribers
        for websocket, filter_ in subscriptions:
            if filter_ is None or self._matches_filter(span, filter_):
                try:
                    await websocket.send_json(
                        {
                            "type": "trace_span",
                            "payload": span,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to send trace span to subscriber: {e}")

    def _matches_filter(self, span: dict[str, Any], filter_: TraceFilter) -> bool:
        """
        Check if a span matches the filter criteria.

        Args:
            span: The span data to check.
            filter_: The filter criteria.

        Returns:
            True if the span matches all filter criteria.
        """
        if filter_.service_name and span.get("service_name") != filter_.service_name:
            return False
        # Payloads use "name" (TraceSpanPayload) but some sources may use "operation_name"
        span_name = span.get("name") or span.get("operation_name")
        if filter_.operation_name and span_name != filter_.operation_name:
            return False
        if filter_.trace_id and span.get("trace_id") != filter_.trace_id:
            return False
        if filter_.min_duration_ms and span.get("duration_ms", 0) < filter_.min_duration_ms:
            return False
        if filter_.status and span.get("status") != filter_.status:
            return False
        # Check session_id filter (supports all three attribute variants)
        if filter_.session_id:
            attrs = span.get("attributes", {}) or {}
            span_session_id = (
                attrs.get("session.id")
                or attrs.get("session_id")
                or attrs.get("sessionId")
                or span.get("session_id")  # Direct field fallback
            )
            if span_session_id != filter_.session_id:
                return False
        return True

    def queue_broadcast(self, span: dict[str, Any]) -> None:
        """
        Synchronously add a span to the recent traces buffer.

        This is a non-blocking method that can be called from any context,
        including from OTEL span processors that run outside of async contexts.
        Does not broadcast to WebSocket subscribers - use broadcast_span() for that.

        Args:
            span: The span data to add to the buffer.
        """
        # Direct append without async lock - thread-safe for single writes
        # The list operations are atomic in CPython
        self._recent_traces.insert(0, span)
        if len(self._recent_traces) > self._max_recent_traces:
            self._recent_traces = self._recent_traces[: self._max_recent_traces]

    @property
    def subscriber_count(self) -> int:
        """Get the number of active subscribers."""
        return len(self._subscriptions)
