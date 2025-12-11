"""
Pydantic models for Playground API requests and responses.

Provides type-safe request/response models for:
- Session management
- Chat messages
- Observability data (traces, logs, metrics, alerts)
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ==============================================================================
# Session Models
# ==============================================================================


class SessionConfig(BaseModel):
    """Configuration for a playground session."""

    model: str = Field(default="gpt-4o-mini", description="LLM model to use")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=1000, ge=1, le=128000, description="Max tokens per response")


class CreateSessionRequest(BaseModel):
    """Request to create a new playground session."""

    name: str = Field(..., min_length=1, max_length=100, description="Session name")
    config: SessionConfig | None = Field(default=None, description="Optional LLM configuration")


class CreateSessionResponse(BaseModel):
    """Response when creating a session."""

    session_id: str
    name: str
    created_at: datetime
    config: SessionConfig


class SessionMessage(BaseModel):
    """A message in a session."""

    message_id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionDetails(BaseModel):
    """Full session details including messages."""

    session_id: str
    name: str
    created_at: datetime
    updated_at: datetime
    messages: list[SessionMessage]
    config: SessionConfig


class SessionSummary(BaseModel):
    """Summary of a session for listing."""

    session_id: str
    name: str
    created_at: datetime
    message_count: int


class ListSessionsResponse(BaseModel):
    """Response when listing sessions."""

    sessions: list[SessionSummary]
    storage_backend: str | None = None  # "postgres", "redis", or "memory"


# ==============================================================================
# Chat Models
# ==============================================================================


class ChatRequest(BaseModel):
    """Request to send a chat message."""

    session_id: str
    message: str = Field(..., min_length=1, description="User message")


class ChatResponse(BaseModel):
    """Response with assistant reply."""

    response: str
    message_id: str
    timestamp: datetime
    usage: dict[str, Any] = Field(default_factory=dict)


# ==============================================================================
# Observability Models
# ==============================================================================


class SpanInfo(BaseModel):
    """Information about a trace span."""

    span_id: str
    trace_id: str
    name: str
    start_time: datetime
    end_time: datetime | None = None
    duration_ms: float | None = None
    status: str = "OK"
    attributes: dict[str, Any] = Field(default_factory=dict)
    children: list["SpanInfo"] = Field(default_factory=list)


class TraceInfo(BaseModel):
    """Information about a complete trace."""

    trace_id: str
    name: str
    start_time: datetime
    end_time: datetime | None = None
    duration_ms: float | None = None
    span_count: int
    status: str = "OK"


class TracesResponse(BaseModel):
    """Response with session traces."""

    traces: list[TraceInfo]
    total: int = 0


class TraceDetailsResponse(BaseModel):
    """Response with full trace span tree."""

    trace_id: str
    root_span: SpanInfo | None = None
    spans: list[SpanInfo] = Field(default_factory=list)


class LogLevel(str, Enum):
    """Log severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogEntry(BaseModel):
    """A structured log entry."""

    timestamp: datetime
    level: LogLevel
    message: str
    logger_name: str = ""
    trace_id: str | None = None
    span_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class LogsResponse(BaseModel):
    """Response with session logs."""

    logs: list[LogEntry]
    total: int = 0


class MetricValue(BaseModel):
    """A single metric data point."""

    timestamp: datetime
    value: float


class LLMMetrics(BaseModel):
    """LLM-specific metrics."""

    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    request_count: int = 0
    error_count: int = 0
    history: list[MetricValue] = Field(default_factory=list)


class ToolMetrics(BaseModel):
    """Tool execution metrics."""

    tool_calls: int = 0
    success_rate: float = 1.0
    avg_duration_ms: float = 0.0
    by_tool: dict[str, dict[str, Any]] = Field(default_factory=dict)


class MetricsSummary(BaseModel):
    """Summary of all metrics."""

    llm: LLMMetrics
    tools: ToolMetrics
    session_duration_ms: float = 0.0
    message_count: int = 0


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Alert(BaseModel):
    """An alert notification."""

    alert_id: str
    name: str
    message: str
    severity: AlertSeverity
    timestamp: datetime
    acknowledged: bool = False
    link: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class AlertsResponse(BaseModel):
    """Response with active alerts."""

    alerts: list[Alert]
    total: int = 0


# ==============================================================================
# WebSocket Models
# ==============================================================================


class WebSocketMessage(BaseModel):
    """Base WebSocket message."""

    type: str


class WebSocketConnected(WebSocketMessage):
    """Connection established message."""

    type: str = "connected"
    session_id: str


class WebSocketChunk(WebSocketMessage):
    """Streaming response chunk."""

    type: str = "chunk"
    content: str
    message_id: str


class WebSocketComplete(WebSocketMessage):
    """Response complete message."""

    type: str = "complete"
    message_id: str
    usage: dict[str, Any] = Field(default_factory=dict)


class WebSocketError(WebSocketMessage):
    """Error message."""

    type: str = "error"
    message: str
    code: str | None = None


class WebSocketToolCall(WebSocketMessage):
    """Tool call notification."""

    type: str = "tool_call"
    tool_name: str
    args: dict[str, Any]
    call_id: str


class WebSocketTraceEvent(WebSocketMessage):
    """Real-time trace event."""

    type: str = "trace"
    event: str  # "start", "end"
    trace_id: str
    span_name: str


class WebSocketLogEvent(WebSocketMessage):
    """Real-time log event."""

    type: str = "log"
    entry: LogEntry


class WebSocketMetricEvent(WebSocketMessage):
    """Real-time metric update."""

    type: str = "metric"
    name: str
    value: float
    timestamp: datetime


class WebSocketAlertEvent(WebSocketMessage):
    """Real-time alert notification."""

    type: str = "alert"
    alert: Alert


# ==============================================================================
# Health Models
# ==============================================================================


class HealthStatus(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str = "1.0.0"


class ReadinessStatus(BaseModel):
    """Readiness check response."""

    status: str
    checks: dict[str, str] = Field(default_factory=dict)
