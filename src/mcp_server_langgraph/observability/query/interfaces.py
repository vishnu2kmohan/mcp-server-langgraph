"""
Abstract interfaces for observability query clients.

These interfaces define vendor-neutral contracts for querying telemetry data.
Applications code against these interfaces, allowing backend implementations
to be swapped without changing application code.

Supported implementations:
- Tracing: Tempo, Jaeger, AWS X-Ray, GCP Cloud Trace, Azure App Insights
- Logging: Loki, Elasticsearch, AWS CloudWatch, GCP Cloud Logging
- Metrics: Prometheus, Mimir, AWS CloudWatch, GCP Cloud Monitoring, Datadog

Example:
    from mcp_server_langgraph.observability.query import TracingQueryClient

    class MyService:
        def __init__(self, tracing: TracingQueryClient):
            self.tracing = tracing

        async def get_session_traces(self, session_id: str):
            return await self.tracing.search_by_attribute(
                attribute="session_id",
                value=session_id,
            )

NOTE: OpenTelemetry (OTEL) only defines export protocols (OTLP). There is NO
standard query API in OTEL. This module bridges that gap with abstractions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Protocol


# ==============================================================================
# Tracing Data Types
# ==============================================================================


class SpanStatusCode(str, Enum):
    """OpenTelemetry span status codes."""

    UNSET = "UNSET"
    OK = "OK"
    ERROR = "ERROR"


@dataclass
class SpanInfo:
    """
    Information about a single span.

    Follows OpenTelemetry semantic conventions for span attributes.
    """

    span_id: str
    trace_id: str
    operation_name: str
    service_name: str
    start_time: datetime
    duration_ms: float
    status_code: SpanStatusCode = SpanStatusCode.UNSET
    parent_span_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def is_root(self) -> bool:
        """Check if this is a root span (no parent)."""
        return self.parent_span_id is None

    @property
    def has_error(self) -> bool:
        """Check if span has error status."""
        return self.status_code == SpanStatusCode.ERROR


@dataclass
class TraceInfo:
    """
    Information about a complete distributed trace.

    A trace represents the full journey of a request through the system.
    """

    trace_id: str
    root_service: str
    root_operation: str
    start_time: datetime
    duration_ms: float
    span_count: int
    error_count: int = 0
    spans: list[SpanInfo] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Check if trace contains any errors."""
        return self.error_count > 0

    @property
    def services(self) -> list[str]:
        """Get list of unique services in this trace."""
        return list({span.service_name for span in self.spans})


@dataclass
class TraceSearchResult:
    """Result of a trace search query."""

    traces: list[TraceInfo]
    total_count: int
    next_cursor: str | None = None  # For pagination


# ==============================================================================
# Logging Data Types
# ==============================================================================


class LogLevel(str, Enum):
    """Standard log severity levels."""

    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    FATAL = "fatal"


@dataclass
class LogEntry:
    """
    A single log entry with metadata.

    Follows OpenTelemetry Logs semantic conventions.
    """

    timestamp: datetime
    level: LogLevel
    message: str
    service_name: str
    trace_id: str | None = None
    span_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def is_correlated(self) -> bool:
        """Check if log is correlated with a trace."""
        return self.trace_id is not None


@dataclass
class LogSearchResult:
    """Result of a log search query."""

    entries: list[LogEntry]
    total_count: int
    next_cursor: str | None = None


# ==============================================================================
# Metrics Data Types
# ==============================================================================


@dataclass
class MetricValue:
    """Single metric value with timestamp."""

    timestamp: datetime
    value: float

    @classmethod
    def now(cls, value: float) -> "MetricValue":
        """Create metric value with current timestamp."""
        return cls(timestamp=datetime.now(UTC), value=value)


@dataclass
class MetricSeries:
    """Time series of metric values with labels."""

    metric_name: str
    labels: dict[str, str]
    values: list[MetricValue]

    @property
    def latest_value(self) -> float | None:
        """Get most recent value."""
        return self.values[-1].value if self.values else None

    @property
    def average(self) -> float | None:
        """Calculate average across all values."""
        if not self.values:
            return None
        return sum(v.value for v in self.values) / len(self.values)


@dataclass
class MetricQueryResult:
    """Result of a metric query."""

    series: list[MetricSeries]
    warnings: list[str] = field(default_factory=list)


# ==============================================================================
# Abstract Query Clients
# ==============================================================================


class TracingQueryClient(ABC):
    """
    Abstract interface for querying distributed traces.

    Implementations:
    - TempoTracingClient (Grafana Tempo)
    - JaegerTracingClient (Jaeger)
    - XRayTracingClient (AWS X-Ray)
    - CloudTraceClient (GCP Cloud Trace)
    - AppInsightsTracingClient (Azure Application Insights)
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the client."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the client and release resources."""
        ...

    @abstractmethod
    async def get_trace(self, trace_id: str) -> TraceInfo | None:
        """
        Get a trace by its ID.

        Args:
            trace_id: The 32-character hex trace ID

        Returns:
            TraceInfo if found, None otherwise
        """
        ...

    @abstractmethod
    async def search_traces(
        self,
        service_name: str | None = None,
        operation_name: str | None = None,
        tags: dict[str, str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        min_duration_ms: float | None = None,
        max_duration_ms: float | None = None,
        limit: int = 20,
    ) -> TraceSearchResult:
        """
        Search for traces matching the given criteria.

        Args:
            service_name: Filter by service name
            operation_name: Filter by operation/span name
            tags: Filter by span tags/attributes
            start: Search start time (defaults to last hour)
            end: Search end time (defaults to now)
            min_duration_ms: Minimum trace duration in milliseconds
            max_duration_ms: Maximum trace duration in milliseconds
            limit: Maximum number of traces to return

        Returns:
            TraceSearchResult with matching traces
        """
        ...

    @abstractmethod
    async def search_by_attribute(
        self,
        attribute: str,
        value: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 20,
    ) -> TraceSearchResult:
        """
        Search traces by a specific attribute value.

        Useful for finding traces associated with a session, user, or request ID.

        Args:
            attribute: Attribute name (e.g., "session_id", "user_id", "request_id")
            value: Attribute value to match
            start: Search start time
            end: Search end time
            limit: Maximum traces to return

        Returns:
            TraceSearchResult with matching traces
        """
        ...

    @abstractmethod
    async def get_error_traces(
        self,
        service_name: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 20,
    ) -> TraceSearchResult:
        """
        Get traces that contain errors.

        Args:
            service_name: Optional service name filter
            start: Search start time
            end: Search end time
            limit: Maximum traces to return

        Returns:
            TraceSearchResult with error traces
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the tracing backend is healthy.

        Returns:
            True if healthy, False otherwise
        """
        ...


class LoggingQueryClient(ABC):
    """
    Abstract interface for querying logs.

    Implementations:
    - LokiLoggingClient (Grafana Loki)
    - ElasticsearchLoggingClient (Elasticsearch)
    - CloudWatchLogsClient (AWS CloudWatch Logs)
    - CloudLoggingClient (GCP Cloud Logging)
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the client."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the client and release resources."""
        ...

    @abstractmethod
    async def search_logs(
        self,
        query: str | None = None,
        service_name: str | None = None,
        level: LogLevel | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> LogSearchResult:
        """
        Search logs matching the given criteria.

        Args:
            query: Text search query or backend-specific query language
            service_name: Filter by service name
            level: Filter by log level (and above)
            start: Search start time
            end: Search end time
            limit: Maximum entries to return

        Returns:
            LogSearchResult with matching log entries
        """
        ...

    @abstractmethod
    async def get_logs_for_trace(
        self,
        trace_id: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> LogSearchResult:
        """
        Get logs correlated with a specific trace.

        Args:
            trace_id: The trace ID to find logs for
            start: Search start time
            end: Search end time

        Returns:
            LogSearchResult with correlated log entries
        """
        ...

    @abstractmethod
    async def get_logs_by_attribute(
        self,
        attribute: str,
        value: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> LogSearchResult:
        """
        Get logs matching a specific attribute value.

        Args:
            attribute: Attribute name (e.g., "session_id", "user_id")
            value: Attribute value to match
            start: Search start time
            end: Search end time
            limit: Maximum entries to return

        Returns:
            LogSearchResult with matching log entries
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the logging backend is healthy."""
        ...


class MetricsQueryClient(ABC):
    """
    Abstract interface for querying metrics.

    Implementations:
    - PrometheusMetricsClient (Prometheus/Mimir)
    - CloudWatchMetricsClient (AWS CloudWatch)
    - CloudMonitoringClient (GCP Cloud Monitoring)
    - DatadogMetricsClient (Datadog)
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the client."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the client and release resources."""
        ...

    @abstractmethod
    async def query_instant(
        self,
        query: str,
        time: datetime | None = None,
    ) -> MetricQueryResult:
        """
        Execute an instant query at a specific point in time.

        Args:
            query: Query string (PromQL, CloudWatch Expression, etc.)
            time: Evaluation time (defaults to now)

        Returns:
            MetricQueryResult with query results
        """
        ...

    @abstractmethod
    async def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        step: timedelta | None = None,
    ) -> MetricQueryResult:
        """
        Execute a range query over a time period.

        Args:
            query: Query string
            start: Range start time
            end: Range end time
            step: Step interval (resolution)

        Returns:
            MetricQueryResult with time series data
        """
        ...

    @abstractmethod
    async def get_service_metrics(
        self,
        service_name: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> dict[str, MetricSeries]:
        """
        Get standard metrics for a service.

        Returns request rate, error rate, latency percentiles, etc.

        Args:
            service_name: Service to get metrics for
            start: Time range start
            end: Time range end

        Returns:
            Dict mapping metric name to MetricSeries
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the metrics backend is healthy."""
        ...


# ==============================================================================
# Protocol for runtime type checking
# ==============================================================================


class ObservabilityClient(Protocol):
    """Protocol combining all observability query interfaces."""

    tracing: TracingQueryClient
    logging: LoggingQueryClient
    metrics: MetricsQueryClient

    async def initialize_all(self) -> None:
        """Initialize all clients."""
        ...

    async def close_all(self) -> None:
        """Close all clients."""
        ...

    async def health_check_all(self) -> dict[str, bool]:
        """Check health of all backends."""
        ...
