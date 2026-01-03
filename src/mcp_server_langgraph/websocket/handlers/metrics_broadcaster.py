"""
MetricsBroadcaster for Real-Time Session-Scoped Metrics Streaming.

Provides real-time streaming of Prometheus-like metrics to the DevTools Metrics tab.

Features:
- Session-scoped metric updates pushed via WebSocket
- Real-time visibility into http_requests_total, llm_tokens_total, etc.
- Sparkline data aggregation for visualization
- Trend calculation (up/down/stable)
- Metric type support (counter, gauge, histogram)

This broadcaster solves the gap where:
- Console logs stream in real-time via DevToolsBroadcaster
- Traces stream in real-time via TraceBroadcaster
- BUT metrics were polled from Mimir via API (not real-time)

Message Types (Server -> Client):
    - metric: Single metric update with value, sparkline, and trend
    - metrics_snapshot: Full snapshot of all current metrics

Usage:
    broadcaster = get_metrics_broadcaster()

    # Subscribe a client
    await broadcaster.subscribe(websocket, user_id="user-123", session_id="session-abc")

    # Broadcast a metric update (called from middleware/instrumentation)
    await broadcaster.broadcast_metric(
        name="http_requests_total",
        value=42,
        labels={"method": "GET", "path": "/api/chat"},
        session_id="session-abc",
    )

    # Unsubscribe
    await broadcaster.unsubscribe(websocket)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from fastapi import WebSocket as FastAPIWebSocket

logger = logging.getLogger(__name__)

# Default max points for sparkline data
DEFAULT_MAX_SPARKLINE_POINTS = 20


class MetricType(Enum):
    """Type of metric being broadcasted."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricValue:
    """Stores a metric value with metadata."""

    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    labels: dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.COUNTER
    histogram_buckets: dict[str, float] | None = None


@dataclass
class MetricHistory:
    """Stores historical values for a metric (for sparkline and trend)."""

    values: list[float] = field(default_factory=list)
    timestamps: list[datetime] = field(default_factory=list)
    max_points: int = DEFAULT_MAX_SPARKLINE_POINTS

    def add(self, value: float) -> None:
        """Add a value to the history."""
        self.values.append(value)
        self.timestamps.append(datetime.now(UTC))

        # Trim to max points
        if len(self.values) > self.max_points:
            self.values = self.values[-self.max_points :]
            self.timestamps = self.timestamps[-self.max_points :]

    def get_sparkline(self) -> list[float]:
        """Get values for sparkline visualization."""
        return list(self.values)

    def calculate_trend(self) -> str:
        """Calculate trend based on recent values.

        Returns:
            "up", "down", or "stable"
        """
        if len(self.values) < 2:
            return "stable"

        # Compare recent average to earlier average
        mid = len(self.values) // 2
        if mid == 0:
            mid = 1

        earlier_avg = sum(self.values[:mid]) / mid
        recent_avg = sum(self.values[mid:]) / (len(self.values) - mid)

        # Threshold for significant change (5%)
        threshold = 0.05 * abs(earlier_avg) if earlier_avg != 0 else 0.5

        diff = recent_avg - earlier_avg
        if diff > threshold:
            return "up"
        elif diff < -threshold:
            return "down"
        else:
            return "stable"

    def calculate_change_percent(self) -> float:
        """Calculate percentage change from earliest to latest value."""
        if len(self.values) < 2:
            return 0.0

        first = self.values[0]
        last = self.values[-1]

        if first == 0:
            return 100.0 if last > 0 else 0.0

        return ((last - first) / abs(first)) * 100


# =============================================================================
# Broadcaster Protocol
# =============================================================================


@runtime_checkable
class MetricsBroadcasterProtocol(Protocol):
    """Protocol defining the MetricsBroadcaster interface."""

    async def subscribe(
        self,
        websocket: FastAPIWebSocket,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> None:
        """Subscribe to metrics events."""
        ...

    async def unsubscribe(self, websocket: FastAPIWebSocket) -> None:
        """Unsubscribe from metrics events."""
        ...

    async def broadcast_metric(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
        session_id: str | None = None,
        metric_type: MetricType = MetricType.COUNTER,
        histogram_buckets: dict[str, float] | None = None,
    ) -> None:
        """Broadcast a metric update."""
        ...


# =============================================================================
# Broadcaster Implementation
# =============================================================================


class MetricsBroadcaster:
    """
    Broadcaster for real-time session-scoped metrics.

    Manages WebSocket subscriptions and broadcasts metric updates
    to connected DevTools clients.

    Features:
    - Session-scoped filtering (only receive metrics for your session)
    - Sparkline data aggregation
    - Trend calculation
    - Support for counter, gauge, histogram metrics
    """

    def __init__(self, max_sparkline_points: int = DEFAULT_MAX_SPARKLINE_POINTS) -> None:
        """Initialize the broadcaster.

        Args:
            max_sparkline_points: Maximum number of points to keep for sparkline.
        """
        # Map of websocket -> (user_id, session_id)
        self._subscribers: dict[Any, tuple[str | None, str | None]] = {}

        # Metric history for sparkline/trend (keyed by metric name)
        # For session-scoped: keyed by (metric_name, session_id)
        self._metric_history: dict[str, MetricHistory] = defaultdict(
            lambda: MetricHistory(max_points=max_sparkline_points)
        )

        # Current metric values (for snapshots)
        # Keyed by metric_name, then by session_id (or "global")
        self._current_values: dict[str, dict[str, MetricValue]] = defaultdict(dict)

        self._max_sparkline_points = max_sparkline_points

    @property
    def subscriber_count(self) -> int:
        """Get the number of active subscribers."""
        return len(self._subscribers)

    def get_session_id_for_subscriber(self, websocket: Any) -> str | None:
        """Get the session_id filter for a subscriber."""
        if websocket in self._subscribers:
            return self._subscribers[websocket][1]
        return None

    async def subscribe(
        self,
        websocket: Any,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> None:
        """Subscribe a WebSocket to metrics events.

        Args:
            websocket: The WebSocket connection
            user_id: Optional user ID for tracking
            session_id: Optional session ID for filtering
        """
        self._subscribers[websocket] = (user_id, session_id)
        logger.info(
            "Client subscribed to metrics events",
            extra={
                "user_id": user_id,
                "session_id": session_id,
                "subscriber_count": len(self._subscribers),
            },
        )

    async def unsubscribe(self, websocket: Any) -> None:
        """Unsubscribe a WebSocket from metrics events.

        Args:
            websocket: The WebSocket connection
        """
        if websocket in self._subscribers:
            user_id, session_id = self._subscribers.pop(websocket)
            logger.info(
                "Client unsubscribed from metrics events",
                extra={
                    "user_id": user_id,
                    "session_id": session_id,
                    "subscriber_count": len(self._subscribers),
                },
            )

    async def broadcast_metric(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
        session_id: str | None = None,
        metric_type: MetricType = MetricType.COUNTER,
        histogram_buckets: dict[str, float] | None = None,
    ) -> None:
        """Broadcast a metric update to subscribers.

        Args:
            name: Metric name (e.g., "http_requests_total")
            value: Current metric value
            labels: Optional metric labels
            session_id: Optional session ID for scoping
            metric_type: Type of metric (counter, gauge, histogram)
            histogram_buckets: Bucket values for histogram metrics
        """
        # Build history key
        history_key = f"{name}:{session_id}" if session_id else name

        # Update history
        history = self._metric_history[history_key]
        history.add(value)

        # Store current value
        scope_key = session_id or "global"
        self._current_values[name][scope_key] = MetricValue(
            value=value,
            labels=labels or {},
            metric_type=metric_type,
            histogram_buckets=histogram_buckets,
        )

        # Build message payload
        payload: dict[str, Any] = {
            "name": name,
            "value": value,
            "timestamp": datetime.now(UTC).isoformat(),
            "labels": labels or {},
            "metric_type": metric_type.value,
            "sparkline": history.get_sparkline(),
            "trend": history.calculate_trend(),
            "change": history.calculate_change_percent(),
        }

        if histogram_buckets:
            payload["histogram_buckets"] = histogram_buckets

        if session_id:
            payload["session_id"] = session_id

        message = {
            "type": "metric",
            "payload": payload,
        }

        # Broadcast to subscribers
        await self._broadcast(message, session_id=session_id)

    async def _broadcast(
        self,
        message: dict[str, Any],
        session_id: str | None = None,
    ) -> None:
        """Broadcast a message to subscribers.

        Args:
            message: The message to broadcast
            session_id: Optional session ID for filtering
        """
        failed_subscribers: list[Any] = []

        for websocket, (_, sub_session) in list(self._subscribers.items()):
            # Filter by session if specified
            if sub_session and session_id and sub_session != session_id:
                continue

            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(
                    "Failed to send metric to subscriber, removing",
                    extra={"error": str(e)},
                )
                failed_subscribers.append(websocket)

        # Remove failed subscribers
        for ws in failed_subscribers:
            self._subscribers.pop(ws, None)

    def get_metrics_snapshot(
        self,
        session_id: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Get a snapshot of current metric values.

        Args:
            session_id: Optional session ID to filter metrics

        Returns:
            Dict mapping metric names to their current values and metadata
        """
        result: dict[str, dict[str, Any]] = {}

        for metric_name, scope_values in self._current_values.items():
            # Get value for the requested session or global
            scope_key = session_id or "global"
            metric_value = scope_values.get(scope_key)

            if metric_value is None and session_id:
                # Fall back to global if no session-specific value
                metric_value = scope_values.get("global")

            if metric_value is not None:
                # Get history for sparkline/trend
                history_key = f"{metric_name}:{session_id}" if session_id else metric_name
                history = self._metric_history.get(history_key, MetricHistory())

                result[metric_name] = {
                    "value": metric_value.value,
                    "timestamp": metric_value.timestamp.isoformat(),
                    "labels": metric_value.labels,
                    "metric_type": metric_value.metric_type.value,
                    "sparkline": history.get_sparkline(),
                    "trend": history.calculate_trend(),
                    "change": history.calculate_change_percent(),
                }

                if metric_value.histogram_buckets:
                    result[metric_name]["histogram_buckets"] = metric_value.histogram_buckets

        return result


# =============================================================================
# Singleton Instance
# =============================================================================

_broadcaster: MetricsBroadcaster | None = None


def get_metrics_broadcaster() -> MetricsBroadcaster:
    """Get the application-wide MetricsBroadcaster instance.

    Returns:
        Singleton MetricsBroadcaster instance
    """
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = MetricsBroadcaster()
    return _broadcaster


def reset_metrics_broadcaster() -> None:
    """Reset the MetricsBroadcaster (for testing)."""
    global _broadcaster
    _broadcaster = None


# =============================================================================
# WebSocket Handler
# =============================================================================


class MetricsHandler:
    """
    WebSocket handler for real-time session-scoped metrics.

    Extends WebSocketBase to provide metrics streaming with the
    standardized infrastructure (auth, rate limiting, metrics, etc.).

    Usage:
        handler = MetricsHandler(
            config=WebSocketConfig(
                endpoint_name="metrics-session",
                require_auth=True,
                authz_resource_type="dashboard",
                authz_resource_id="devtools",
                authz_required_relation="viewer",
            ),
            broadcaster=get_metrics_broadcaster(),
        )
        await handler.run(websocket)
    """

    def __init__(
        self,
        config: Any,  # WebSocketConfig
        broadcaster: MetricsBroadcaster,
        metrics: Any = None,  # WebSocketMetrics
    ) -> None:
        """Initialize the metrics handler."""
        from mcp_server_langgraph.websocket.base import WebSocketBase

        # Create a wrapper that uses WebSocketBase
        self._config = config
        self._broadcaster = broadcaster
        self._metrics = metrics
        self._websocket: Any = None
        self._user_id: str | None = None
        self._session_id: str | None = None
        self._subscribed: bool = False

    async def run(self, websocket: Any) -> None:
        """Run the WebSocket handler."""
        from mcp_server_langgraph.websocket.base import WebSocketBase

        # Create inner handler that delegates to WebSocketBase
        handler = _MetricsInnerHandler(
            config=self._config,
            broadcaster=self._broadcaster,
            metrics=self._metrics,
        )
        await handler.run(websocket)


class _MetricsInnerHandler:
    """Inner handler implementing WebSocketBase pattern."""

    def __init__(
        self,
        config: Any,
        broadcaster: MetricsBroadcaster,
        metrics: Any = None,
    ) -> None:
        self._config = config
        self._broadcaster = broadcaster
        self._ws_metrics = metrics
        self._websocket: Any = None
        self._user_id: str | None = None
        self._session_id: str | None = None
        self._subscribed: bool = False

    async def run(self, websocket: Any) -> None:
        """Run the WebSocket handler loop."""
        import json

        from mcp_server_langgraph.auth.jwt_utils import decode_jwt_token

        self._websocket = websocket
        await websocket.accept()

        # Extract user from token
        token = websocket.query_params.get("token")
        if not token:
            token = websocket.headers.get("Authorization", "").replace("Bearer ", "")

        if token:
            try:
                payload = decode_jwt_token(token)
                if payload:
                    self._user_id = payload.get("sub") or payload.get("user_id")
            except Exception:
                pass

        # Subscribe to broadcaster
        await self._broadcaster.subscribe(
            websocket,
            user_id=self._user_id,
            session_id=self._session_id,
        )
        self._subscribed = True

        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)

                response = await self._handle_message(message)
                if response:
                    await websocket.send_json(response)

        except Exception:
            pass
        finally:
            if self._subscribed:
                await self._broadcaster.unsubscribe(websocket)

    async def _handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Handle incoming messages."""
        msg_type = message.get("type", "")

        if msg_type == "subscribe":
            # Update session filter
            payload = message.get("payload", {})
            self._session_id = payload.get("session_id")

            # Re-subscribe with session filter
            if self._subscribed:
                await self._broadcaster.unsubscribe(self._websocket)
            await self._broadcaster.subscribe(
                self._websocket,
                user_id=self._user_id,
                session_id=self._session_id,
            )
            self._subscribed = True

            return {
                "type": "subscribed",
                "payload": {"session_id": self._session_id},
            }

        elif msg_type == "unsubscribe":
            if self._subscribed:
                await self._broadcaster.unsubscribe(self._websocket)
                self._subscribed = False

            return {"type": "unsubscribed", "payload": {}}

        elif msg_type == "get_snapshot":
            payload = message.get("payload", {})
            session_id = payload.get("session_id", self._session_id)

            snapshot = self._broadcaster.get_metrics_snapshot(session_id=session_id)

            return {
                "type": "metrics_snapshot",
                "payload": {"metrics": snapshot, "session_id": session_id},
            }

        return None
