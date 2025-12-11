"""
Playground service business metrics.

Prometheus metrics for Playground operations:
- playground_sessions_total: Session creation/deletion count
- playground_active_sessions: Current active session count
- playground_chat_messages_total: Chat message count
- playground_chat_latency_seconds: Chat response latency
- playground_websocket_connections: Active WebSocket connections

These metrics are scraped by Alloy and displayed in the Playground Grafana dashboard.
"""

from typing import Any

# Lazy-load prometheus_client to handle missing dependency
_metrics_available: bool | None = None
_playground_sessions_total: Any = None
_playground_active_sessions: Any = None
_playground_chat_messages_total: Any = None
_playground_chat_latency: Any = None
_playground_websocket_connections: Any = None


def _init_metrics() -> bool:
    """Initialize Playground metrics lazily."""
    global _metrics_available  # noqa: PLW0603
    global _playground_sessions_total  # noqa: PLW0603
    global _playground_active_sessions  # noqa: PLW0603
    global _playground_chat_messages_total  # noqa: PLW0603
    global _playground_chat_latency  # noqa: PLW0603
    global _playground_websocket_connections  # noqa: PLW0603

    if _metrics_available is not None:
        return _metrics_available

    try:
        from prometheus_client import Counter, Gauge, Histogram

        _playground_sessions_total = Counter(
            "playground_sessions_total",
            "Total number of session operations",
            ["operation"],  # created, deleted
        )

        _playground_active_sessions = Gauge(
            "playground_active_sessions",
            "Current number of active sessions",
        )

        _playground_chat_messages_total = Counter(
            "playground_chat_messages_total",
            "Total number of chat messages",
            ["role"],  # user, assistant
        )

        _playground_chat_latency = Histogram(
            "playground_chat_latency_seconds",
            "Chat response latency in seconds",
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
        )

        _playground_websocket_connections = Gauge(
            "playground_websocket_connections",
            "Current number of active WebSocket connections",
        )

        _metrics_available = True
        return True

    except ImportError:
        _metrics_available = False
        return False


# Initialize on module load
_init_metrics()


def record_session_created() -> None:
    """Record a session creation."""
    if not _metrics_available:
        return

    try:
        if _playground_sessions_total:
            _playground_sessions_total.labels(operation="created").inc()
        if _playground_active_sessions:
            _playground_active_sessions.inc()
    except Exception:
        pass


def record_session_deleted() -> None:
    """Record a session deletion."""
    if not _metrics_available:
        return

    try:
        if _playground_sessions_total:
            _playground_sessions_total.labels(operation="deleted").inc()
        if _playground_active_sessions:
            _playground_active_sessions.dec()
    except Exception:
        pass


def record_chat_message(role: str, latency: float | None = None) -> None:
    """
    Record a chat message.

    Args:
        role: "user" or "assistant"
        latency: Response latency in seconds (for assistant messages)
    """
    if not _metrics_available:
        return

    try:
        if _playground_chat_messages_total:
            _playground_chat_messages_total.labels(role=role).inc()
        if latency is not None and _playground_chat_latency:
            _playground_chat_latency.observe(latency)
    except Exception:
        pass


def websocket_connected() -> None:
    """Record a WebSocket connection."""
    if not _metrics_available:
        return

    try:
        if _playground_websocket_connections:
            _playground_websocket_connections.inc()
    except Exception:
        pass


def websocket_disconnected() -> None:
    """Record a WebSocket disconnection."""
    if not _metrics_available:
        return

    try:
        if _playground_websocket_connections:
            _playground_websocket_connections.dec()
    except Exception:
        pass


def set_active_sessions(count: int) -> None:
    """
    Set the current active session count.

    Args:
        count: Number of active sessions
    """
    if not _metrics_available:
        return

    try:
        if _playground_active_sessions:
            _playground_active_sessions.set(count)
    except Exception:
        pass
