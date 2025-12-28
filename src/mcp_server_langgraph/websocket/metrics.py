"""
WebSocket Metrics Collection.

Provides standardized metrics collection for all WebSocket endpoints
with OpenTelemetry integration and fallback support.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_meter(name: str) -> Any:
    """
    Get an OpenTelemetry meter.

    Args:
        name: The meter name.

    Returns:
        OpenTelemetry Meter instance.

    Raises:
        ImportError: If OpenTelemetry is not available.
    """
    from opentelemetry.metrics import get_meter as otel_get_meter

    return otel_get_meter(name)


class WebSocketMetrics:
    """
    Metrics collection for WebSocket endpoints.

    Collects connection counts, message rates, errors, and latencies.
    Integrates with OpenTelemetry when available, falls back to in-memory
    counters otherwise.

    Usage:
        metrics = WebSocketMetrics(endpoint_name="notifications")
        metrics.record_connection()
        metrics.record_message_received(message_type="ping")
        metrics.record_disconnect()
    """

    def __init__(
        self,
        endpoint_name: str,
        enable_otel: bool = False,
    ) -> None:
        """
        Initialize WebSocket metrics.

        Args:
            endpoint_name: Name of the WebSocket endpoint for metric labels.
            enable_otel: Whether to enable OpenTelemetry integration.
        """
        self.endpoint_name = endpoint_name
        self._active_connections = 0
        self._total_connections = 0
        self._messages_received = 0
        self._messages_sent = 0
        self._errors = 0
        self._rate_limit_exceeded = 0
        self._connections_rejected = 0
        self._token_expirations = 0
        self._latencies: list[float] = []
        self._otel_available = False
        self._otel_meter: Any = None

        if enable_otel:
            self._init_otel()

    def _init_otel(self) -> None:
        """Initialize OpenTelemetry metrics if available."""
        try:
            self._otel_meter = get_meter(f"websocket_{self.endpoint_name}")

            # Create counters
            self._otel_connections_total = self._otel_meter.create_counter(
                f"websocket_{self.endpoint_name}_connections_total",
                description=f"Total connections to {self.endpoint_name}",
            )
            self._otel_messages_received = self._otel_meter.create_counter(
                f"websocket_{self.endpoint_name}_messages_received_total",
                description="Total messages received",
            )
            self._otel_messages_sent = self._otel_meter.create_counter(
                f"websocket_{self.endpoint_name}_messages_sent_total",
                description="Total messages sent",
            )
            self._otel_errors = self._otel_meter.create_counter(
                f"websocket_{self.endpoint_name}_errors_total",
                description="Total errors",
            )
            self._otel_rate_limit_exceeded = self._otel_meter.create_counter(
                f"websocket_{self.endpoint_name}_rate_limit_exceeded_total",
                description="Rate limit exceeded events",
            )
            self._otel_connections_rejected = self._otel_meter.create_counter(
                f"websocket_{self.endpoint_name}_connections_rejected_total",
                description="Rejected connections",
            )
            self._otel_token_expirations = self._otel_meter.create_counter(
                f"websocket_{self.endpoint_name}_token_expirations_total",
                description="Token expirations (close code 4010)",
            )

            # Create histogram for latency
            self._otel_latency = self._otel_meter.create_histogram(
                f"websocket_{self.endpoint_name}_latency_ms",
                description="Message processing latency in milliseconds",
            )

            # Create observable gauge for active connections
            self._otel_active_gauge = self._otel_meter.create_observable_gauge(
                f"websocket_{self.endpoint_name}_active_connections",
                callbacks=[self._get_active_connections_callback],
                description="Current number of active connections",
            )

            self._otel_available = True
            logger.debug(f"OTel metrics initialized for {self.endpoint_name}")

        except ImportError:
            logger.debug(f"OpenTelemetry not available for {self.endpoint_name}, using fallback metrics")

    def _get_active_connections_callback(self, options: Any) -> Any:
        """Callback for observable gauge."""
        if self._otel_available:
            from opentelemetry.metrics import Observation

            yield Observation(self._active_connections)

    @property
    def active_connections(self) -> int:
        """Get current number of active connections."""
        return self._active_connections

    @property
    def total_connections(self) -> int:
        """Get total number of connections ever made."""
        return self._total_connections

    @property
    def messages_received(self) -> int:
        """Get total messages received."""
        return self._messages_received

    @property
    def messages_sent(self) -> int:
        """Get total messages sent."""
        return self._messages_sent

    @property
    def errors(self) -> int:
        """Get total errors."""
        return self._errors

    @property
    def rate_limit_exceeded(self) -> int:
        """Get total rate limit exceeded events."""
        return self._rate_limit_exceeded

    @property
    def connections_rejected(self) -> int:
        """Get total rejected connections."""
        return self._connections_rejected

    @property
    def token_expirations(self) -> int:
        """Get total token expiration events (close code 4010)."""
        return self._token_expirations

    @property
    def average_latency(self) -> float:
        """Get average message latency in milliseconds."""
        if not self._latencies:
            return 0.0
        return sum(self._latencies) / len(self._latencies)

    def record_connection(self, user_id: str = "") -> None:
        """
        Record a new connection.

        Args:
            user_id: Optional user ID for attribution.
        """
        self._active_connections += 1
        self._total_connections += 1

        if self._otel_available:
            self._otel_connections_total.add(1, {"endpoint": self.endpoint_name, "user_id": user_id})

    def record_disconnect(self) -> None:
        """Record a disconnection."""
        self._active_connections = max(0, self._active_connections - 1)

    def record_message_received(self, message_type: str = "", user_id: str = "") -> None:
        """
        Record a received message.

        Args:
            message_type: Type of message received.
            user_id: Optional user ID for attribution.
        """
        self._messages_received += 1

        if self._otel_available:
            self._otel_messages_received.add(
                1,
                {
                    "endpoint": self.endpoint_name,
                    "type": message_type,
                    "user_id": user_id,
                },
            )

    def record_message_sent(self, message_type: str = "", user_id: str = "") -> None:
        """
        Record a sent message.

        Args:
            message_type: Type of message sent.
            user_id: Optional user ID for attribution.
        """
        self._messages_sent += 1

        if self._otel_available:
            self._otel_messages_sent.add(
                1,
                {
                    "endpoint": self.endpoint_name,
                    "type": message_type,
                    "user_id": user_id,
                },
            )

    def record_error(self, error_type: str = "", user_id: str = "") -> None:
        """
        Record an error.

        Args:
            error_type: Type of error.
            user_id: Optional user ID for attribution.
        """
        self._errors += 1

        if self._otel_available:
            self._otel_errors.add(
                1,
                {
                    "endpoint": self.endpoint_name,
                    "error_type": error_type,
                    "user_id": user_id,
                },
            )

    def record_rate_limit_exceeded(self, user_id: str = "") -> None:
        """
        Record a rate limit exceeded event.

        Args:
            user_id: User ID that exceeded the limit.
        """
        self._rate_limit_exceeded += 1

        if self._otel_available:
            self._otel_rate_limit_exceeded.add(1, {"endpoint": self.endpoint_name, "user_id": user_id})

    def record_connection_rejected(self, reason: str = "", user_id: str = "") -> None:
        """
        Record a rejected connection.

        Args:
            reason: Reason for rejection.
            user_id: Optional user ID.
        """
        self._connections_rejected += 1

        if self._otel_available:
            self._otel_connections_rejected.add(
                1,
                {
                    "endpoint": self.endpoint_name,
                    "reason": reason,
                    "user_id": user_id,
                },
            )

    def record_token_expired(self, user_id: str = "") -> None:
        """
        Record a token expiration event (close code 4010).

        This is tracked when a WebSocket connection is closed due to
        JWT token expiration during an active connection.

        Args:
            user_id: Optional user ID whose token expired.
        """
        self._token_expirations += 1

        if self._otel_available:
            self._otel_token_expirations.add(
                1,
                {
                    "endpoint": self.endpoint_name,
                    "user_id": user_id,
                },
            )

    def record_latency(self, latency_ms: float, message_type: str = "") -> None:
        """
        Record message processing latency.

        Args:
            latency_ms: Latency in milliseconds.
            message_type: Type of message processed.
        """
        self._latencies.append(latency_ms)

        # Keep only last 1000 latencies to avoid memory growth
        if len(self._latencies) > 1000:
            self._latencies = self._latencies[-1000:]

        if self._otel_available:
            self._otel_latency.record(
                latency_ms,
                {"endpoint": self.endpoint_name, "type": message_type},
            )

    def record_message_latency(self, message_type: str = "", latency_seconds: float = 0.0) -> None:
        """
        Record message processing latency from seconds.

        Convenience method that accepts latency in seconds and converts to
        milliseconds internally.

        Args:
            message_type: Type of message processed.
            latency_seconds: Latency in seconds.
        """
        self.record_latency(latency_seconds * 1000, message_type)

    def get_stats(self) -> dict[str, Any]:
        """
        Get all metrics as a dictionary.

        Returns:
            Dictionary with all current metrics.
        """
        return {
            "endpoint_name": self.endpoint_name,
            "active_connections": self._active_connections,
            "total_connections": self._total_connections,
            "messages_received": self._messages_received,
            "messages_sent": self._messages_sent,
            "errors": self._errors,
            "rate_limit_exceeded": self._rate_limit_exceeded,
            "connections_rejected": self._connections_rejected,
            "token_expirations": self._token_expirations,
            "average_latency_ms": self.average_latency,
        }

    def reset(self) -> None:
        """Reset all metrics to zero. Useful for testing."""
        self._active_connections = 0
        self._total_connections = 0
        self._messages_received = 0
        self._messages_sent = 0
        self._errors = 0
        self._rate_limit_exceeded = 0
        self._connections_rejected = 0
        self._token_expirations = 0
        self._latencies = []
