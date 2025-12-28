"""
MCP WebSocket OpenTelemetry Metrics.

This module provides OpenTelemetry-compatible metrics for MCP WebSocket
connections, including counters, gauges, and histograms for observability.

Migrated from: api.v1.mcp_websocket
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class OTelMCPMetrics:
    """
    OpenTelemetry-compatible metrics for MCP WebSocket.

    Provides counters, gauges, and histograms for observability.
    """

    def __init__(self) -> None:
        """Initialize OpenTelemetry metrics."""
        try:
            from opentelemetry.metrics import get_meter

            meter = get_meter("mcp_websocket")

            # Counters
            self._connections_total = meter.create_counter(
                "mcp_websocket_connections_total",
                description="Total number of MCP WebSocket connections",
            )
            self._messages_received = meter.create_counter(
                "mcp_websocket_messages_received_total",
                description="Total messages received",
            )
            self._messages_sent = meter.create_counter(
                "mcp_websocket_messages_sent_total",
                description="Total messages sent",
            )
            self._rate_limit_exceeded = meter.create_counter(
                "mcp_websocket_rate_limit_exceeded_total",
                description="Rate limit exceeded events",
            )

            # Histogram for latency
            self._message_latency = meter.create_histogram(
                "mcp_websocket_message_latency_ms",
                description="Message processing latency in milliseconds",
            )

            # Streaming metrics
            self._stream_chunks_total = meter.create_counter(
                "mcp_websocket_stream_chunks_total",
                description="Total streaming chunks sent",
            )
            self._stream_chunk_sizes = meter.create_histogram(
                "mcp_websocket_stream_chunk_size_bytes",
                description="Size of streaming chunks in bytes",
            )

            # Track active connections count
            self._active_connections = 0
            self._active_streams = 0
            self._total_chunks = 0
            self.active_connections_gauge = meter.create_observable_gauge(
                "mcp_websocket_active_connections",
                callbacks=[self._get_active_connections],
                description="Current number of active connections",
            )

            self._otel_available = True
        except ImportError:
            # OpenTelemetry not installed, use fallback
            self._otel_available = False
            self._active_connections = 0
            self._active_streams = 0
            self._total_chunks = 0
            self._stream_chunks_total: Any = None  # type: ignore[assignment,no-redef]
            self._stream_chunk_sizes: Any = None  # type: ignore[assignment,no-redef]
            self.active_connections_gauge: Any = None  # type: ignore[assignment,no-redef]
            logger.debug("OpenTelemetry not available, using fallback metrics")

    def _get_active_connections(self, options: Any) -> Any:
        """Callback for observable gauge."""
        if self._otel_available:
            from opentelemetry.metrics import Observation

            yield Observation(self._active_connections)

    def record_connection(self) -> None:
        """Record a new connection."""
        self._active_connections += 1
        if self._otel_available:
            self._connections_total.add(1)

    def record_disconnect(self) -> None:
        """Record a disconnection."""
        self._active_connections = max(0, self._active_connections - 1)

    def record_message_received(self, method: str = "", user_id: str = "") -> None:
        """Record a received message with attributes."""
        if self._otel_available:
            self._messages_received.add(1, {"method": method, "user_id": user_id})

    def record_message_sent(self, method: str = "", user_id: str = "") -> None:
        """Record a sent message with attributes."""
        if self._otel_available:
            self._messages_sent.add(1, {"method": method, "user_id": user_id})

    def record_rate_limit_exceeded(self, user_id: str = "") -> None:
        """Record rate limit exceeded event."""
        if self._otel_available:
            self._rate_limit_exceeded.add(1, {"user_id": user_id})

    def record_connection_rejected(self, user_id: str = "", reason: str = "") -> None:
        """Record connection rejected event."""
        if self._otel_available:
            # Use the existing connections counter with rejection attribute
            self._connections_total.add(1, {"user_id": user_id, "status": "rejected", "reason": reason})

    def record_message_size_exceeded(self, user_id: str = "") -> None:
        """Record message size exceeded event."""
        if self._otel_available:
            self._messages_received.add(1, {"user_id": user_id, "status": "rejected", "reason": "size_exceeded"})

    def record_message_latency(self, method: str = "", latency_ms: float = 0.0) -> None:
        """Record message processing latency."""
        if self._otel_available:
            self._message_latency.record(latency_ms, {"method": method})

    def record_stream_start(self, stream_id: str = "") -> None:
        """
        Record the start of a streaming operation.

        Args:
            stream_id: Unique identifier for the stream.
        """
        self._active_streams += 1

    def record_stream_chunk(self, stream_id: str = "", chunk_size: int = 0) -> None:
        """
        Record a chunk being sent in a stream.

        Args:
            stream_id: Unique identifier for the stream.
            chunk_size: Size of the chunk in bytes.
        """
        self._total_chunks += 1
        if self._otel_available:
            self._stream_chunks_total.add(1, {"stream_id": stream_id})
            self._stream_chunk_sizes.record(chunk_size, {"stream_id": stream_id})

    def record_stream_end(
        self,
        stream_id: str = "",
        chunks: int = 0,
        total_bytes: int = 0,
        duration_ms: float = 0.0,
    ) -> None:
        """
        Record the end of a streaming operation.

        Args:
            stream_id: Unique identifier for the stream.
            chunks: Total number of chunks sent.
            total_bytes: Total bytes sent.
            duration_ms: Total duration in milliseconds.
        """
        self._active_streams = max(0, self._active_streams - 1)


# Global OpenTelemetry metrics instance
otel_metrics = OTelMCPMetrics()


def get_otel_metrics() -> OTelMCPMetrics:
    """
    Get the global OTelMCPMetrics instance.

    Returns:
        The global OTelMCPMetrics instance.
    """
    return otel_metrics
