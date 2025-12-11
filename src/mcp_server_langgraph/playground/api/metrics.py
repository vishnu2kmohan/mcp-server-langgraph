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
# Advanced metrics for comprehensive observability
_playground_llm_tokens_total: Any = None
_playground_tool_calls_total: Any = None
_playground_tool_duration: Any = None
_playground_traces_total: Any = None
_playground_spans_total: Any = None


def _init_metrics() -> bool:
    """Initialize Playground metrics lazily."""
    global _metrics_available  # noqa: PLW0603
    global _playground_sessions_total  # noqa: PLW0603
    global _playground_active_sessions  # noqa: PLW0603
    global _playground_chat_messages_total  # noqa: PLW0603
    global _playground_chat_latency  # noqa: PLW0603
    global _playground_websocket_connections  # noqa: PLW0603
    global _playground_llm_tokens_total  # noqa: PLW0603
    global _playground_tool_calls_total  # noqa: PLW0603
    global _playground_tool_duration  # noqa: PLW0603
    global _playground_traces_total  # noqa: PLW0603
    global _playground_spans_total  # noqa: PLW0603

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

        # Advanced metrics for LLM and tool usage
        _playground_llm_tokens_total = Counter(
            "playground_llm_tokens_total",
            "Total LLM tokens used",
            ["token_type"],  # prompt, completion
        )

        _playground_tool_calls_total = Counter(
            "playground_tool_calls_total",
            "Total tool calls made",
            ["tool_name", "status"],  # success, failure
        )

        _playground_tool_duration = Histogram(
            "playground_tool_duration_seconds",
            "Tool execution duration in seconds",
            ["tool_name"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )

        _playground_traces_total = Counter(
            "playground_traces_total",
            "Total traces created",
        )

        _playground_spans_total = Counter(
            "playground_spans_total",
            "Total spans created",
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


def record_llm_tokens(prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
    """
    Record LLM token usage.

    Args:
        prompt_tokens: Number of prompt tokens used
        completion_tokens: Number of completion tokens used
    """
    if not _metrics_available:
        return

    try:
        if _playground_llm_tokens_total:
            if prompt_tokens > 0:
                _playground_llm_tokens_total.labels(token_type="prompt").inc(prompt_tokens)  # noqa: S106
            if completion_tokens > 0:
                _playground_llm_tokens_total.labels(token_type="completion").inc(  # noqa: S106
                    completion_tokens
                )
    except Exception:
        pass


def record_tool_call(tool_name: str, duration: float, success: bool = True) -> None:
    """
    Record a tool call.

    Args:
        tool_name: Name of the tool called
        duration: Execution duration in seconds
        success: Whether the call succeeded
    """
    if not _metrics_available:
        return

    try:
        status = "success" if success else "failure"
        if _playground_tool_calls_total:
            _playground_tool_calls_total.labels(tool_name=tool_name, status=status).inc()
        if _playground_tool_duration:
            _playground_tool_duration.labels(tool_name=tool_name).observe(duration)
    except Exception:
        pass


def record_trace_created(span_count: int = 1) -> None:
    """
    Record trace and span creation.

    Args:
        span_count: Number of spans in the trace
    """
    if not _metrics_available:
        return

    try:
        if _playground_traces_total:
            _playground_traces_total.inc()
        if _playground_spans_total and span_count > 0:
            _playground_spans_total.inc(span_count)
    except Exception:
        pass
