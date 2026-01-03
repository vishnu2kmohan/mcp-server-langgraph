"""
BroadcastingSpanProcessor - Connects OpenTelemetry to TraceBroadcaster.

This processor captures completed OTEL spans and broadcasts them to the
TraceBroadcaster for real-time WebSocket streaming to the DevTools panel.

Architecture:
    OTEL Spans → BroadcastingSpanProcessor → TraceBroadcaster → WebSocket → DevTools

This enables real-time trace visibility in the frontend without polling.

Usage:
    from mcp_server_langgraph.observability.broadcasting_span_processor import (
        BroadcastingSpanProcessor,
    )
    from mcp_server_langgraph.observability.trace_broadcaster import TraceBroadcaster

    broadcaster = TraceBroadcaster()
    processor = BroadcastingSpanProcessor(broadcaster=broadcaster)

    # Add to TracerProvider
    tracer_provider.add_span_processor(processor)
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor

if TYPE_CHECKING:
    from mcp_server_langgraph.observability.trace_broadcaster import TraceBroadcaster

logger = logging.getLogger(__name__)


def span_to_broadcast_dict(span: ReadableSpan) -> dict[str, Any]:
    """
    Convert an OpenTelemetry span to a dictionary for broadcasting.

    Args:
        span: The completed OTEL span.

    Returns:
        Dictionary with span data suitable for WebSocket broadcast.
    """
    # Get trace and span IDs as hex strings
    span_context = span.get_span_context()  # type: ignore[no-untyped-call]
    trace_id = format(span_context.trace_id, "032x")
    span_id = format(span_context.span_id, "016x")

    # Get parent span ID if exists
    parent_span_id = None
    if span.parent is not None:
        parent_span_id = format(span.parent.span_id, "016x")

    # Calculate duration in milliseconds
    duration_ns = (span.end_time - span.start_time) if span.end_time and span.start_time else 0
    duration_ms = duration_ns / 1_000_000  # nanoseconds to milliseconds

    # Get service name from resource attributes
    service_name = "unknown"
    if span.resource and span.resource.attributes:
        service_name = str(span.resource.attributes.get("service.name", "unknown"))

    # Get status
    status = "UNSET"
    if span.status:
        status = span.status.status_code.name

    # Convert attributes to dict (handle BoundedAttributes)
    attributes: dict[str, Any] = {}
    if span.attributes:
        for key, value in span.attributes.items():
            attributes[key] = value

    return {
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "name": span.name,
        "service_name": service_name,
        "start_time": span.start_time,
        "end_time": span.end_time,
        "duration_ms": duration_ms,
        "status": status,
        "attributes": attributes,
    }


class BroadcastingSpanProcessor(SpanProcessor):
    """
    SpanProcessor that broadcasts completed spans to TraceBroadcaster.

    This processor is added to the TracerProvider alongside the OTLP exporter.
    When spans complete, it converts them to dicts and queues them for
    broadcast to WebSocket subscribers.

    Thread-safe and non-blocking: uses asyncio to schedule broadcasts.
    """

    def __init__(self, broadcaster: TraceBroadcaster) -> None:
        """
        Initialize the broadcasting span processor.

        Args:
            broadcaster: The TraceBroadcaster to send spans to.
        """
        self._broadcaster = broadcaster
        self._loop: asyncio.AbstractEventLoop | None = None
        logger.info("BroadcastingSpanProcessor initialized")

    def on_start(
        self,
        span: ReadableSpan,
        parent_context: Context | None = None,
    ) -> None:
        """
        Called when a span is started.

        We only broadcast completed spans, so this is a no-op.
        """
        pass

    def on_end(self, span: ReadableSpan) -> None:
        """
        Called when a span ends.

        Converts the span to a dict and queues it for broadcast.

        IMPORTANT: This is called synchronously from OTEL internals.
        We ALWAYS use the synchronous queue_broadcast method to ensure
        spans are captured immediately, regardless of async context.
        """
        try:
            span_data = span_to_broadcast_dict(span)

            # ALWAYS use synchronous queue to capture spans immediately
            # This adds to the recent_traces buffer synchronously
            self._broadcaster.queue_broadcast(span_data)

            # Then try to schedule async broadcast to WebSocket subscribers
            self._schedule_websocket_broadcast(span_data)

        except Exception as e:
            # Never let broadcasting errors affect the application
            logger.debug(f"Failed to broadcast span: {e}")

    def _schedule_websocket_broadcast(self, span_data: dict[str, Any]) -> None:
        """
        Schedule async broadcast to WebSocket subscribers.

        This is best-effort - if there's no running loop or subscribers,
        it silently skips. The span is already in recent_traces buffer.
        """
        try:
            loop = asyncio.get_running_loop()
            # Schedule async broadcast to WebSocket subscribers
            loop.create_task(self._broadcaster.broadcast_span(span_data))
        except RuntimeError:
            # No running event loop - that's fine, span is already queued
            pass

    def queue_broadcast(self, span_data: dict[str, Any]) -> None:
        """
        Queue a span for broadcast to WebSocket subscribers.

        Delegates to the broadcaster's queue_broadcast method.
        """
        self._broadcaster.queue_broadcast(span_data)

    def shutdown(self) -> None:
        """
        Shutdown the processor.

        Called when the TracerProvider is shut down.
        """
        logger.info("BroadcastingSpanProcessor shutdown")

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """
        Force flush any pending broadcasts.

        Since we broadcast immediately, there's nothing to flush.

        Returns:
            True (always succeeds).
        """
        return True
