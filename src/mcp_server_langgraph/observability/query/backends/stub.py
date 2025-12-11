"""
Stub implementations for observability query clients.

These in-memory implementations are used for:
- Unit testing without external dependencies
- Development without running observability backends
- Integration testing when OBSERVABILITY_*_BACKEND=stub

The stub clients store data in memory and support basic query operations.
"""

import logging
from datetime import datetime, timedelta

from ..interfaces import (
    LogEntry,
    LogLevel,
    LogSearchResult,
    LoggingQueryClient,
    MetricQueryResult,
    MetricSeries,
    MetricsQueryClient,
    TraceInfo,
    TraceSearchResult,
    TracingQueryClient,
)

logger = logging.getLogger(__name__)


class StubTracingClient(TracingQueryClient):
    """
    In-memory stub implementation of TracingQueryClient.

    Stores traces in memory for testing purposes.
    """

    def __init__(self) -> None:
        self._traces: dict[str, TraceInfo] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the stub client."""
        self._initialized = True
        logger.info("Stub tracing client initialized")

    async def close(self) -> None:
        """Close the stub client."""
        self._traces.clear()
        logger.info("Stub tracing client closed")

    def add_trace(self, trace: TraceInfo) -> None:
        """Add a trace to the stub storage (for testing)."""
        self._traces[trace.trace_id] = trace

    async def get_trace(self, trace_id: str) -> TraceInfo | None:
        """Get a trace by ID."""
        return self._traces.get(trace_id)

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
        """Search traces with filtering."""
        results = []

        for trace in self._traces.values():
            # Filter by service
            if service_name and trace.root_service != service_name:
                continue

            # Filter by operation
            if operation_name and trace.root_operation != operation_name:
                continue

            # Filter by time range
            if start and trace.start_time < start:
                continue
            if end and trace.start_time > end:
                continue

            # Filter by duration
            if min_duration_ms and trace.duration_ms < min_duration_ms:
                continue
            if max_duration_ms and trace.duration_ms > max_duration_ms:
                continue

            results.append(trace)

        # Sort by start time descending and limit
        results.sort(key=lambda t: t.start_time, reverse=True)
        results = results[:limit]

        return TraceSearchResult(traces=results, total_count=len(results))

    async def search_by_attribute(
        self,
        attribute: str,
        value: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 20,
    ) -> TraceSearchResult:
        """Search traces by attribute value."""
        results = []

        for trace in self._traces.values():
            # Check time range
            if start and trace.start_time < start:
                continue
            if end and trace.start_time > end:
                continue

            # Check spans for attribute match
            for span in trace.spans:
                if span.attributes.get(attribute) == value:
                    results.append(trace)
                    break

        results = results[:limit]
        return TraceSearchResult(traces=results, total_count=len(results))

    async def get_error_traces(
        self,
        service_name: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 20,
    ) -> TraceSearchResult:
        """Get traces with errors."""
        results = []

        for trace in self._traces.values():
            if not trace.has_errors:
                continue

            if service_name and trace.root_service != service_name:
                continue

            if start and trace.start_time < start:
                continue
            if end and trace.start_time > end:
                continue

            results.append(trace)

        results = results[:limit]
        return TraceSearchResult(traces=results, total_count=len(results))

    async def health_check(self) -> bool:
        """Always return healthy for stub."""
        return self._initialized


class StubLoggingClient(LoggingQueryClient):
    """
    In-memory stub implementation of LoggingQueryClient.

    Stores logs in memory for testing purposes.
    """

    def __init__(self) -> None:
        self._logs: list[LogEntry] = []
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the stub client."""
        self._initialized = True
        logger.info("Stub logging client initialized")

    async def close(self) -> None:
        """Close the stub client."""
        self._logs.clear()
        logger.info("Stub logging client closed")

    def add_log(self, entry: LogEntry) -> None:
        """Add a log entry to stub storage (for testing)."""
        self._logs.append(entry)

    async def search_logs(
        self,
        query: str | None = None,
        service_name: str | None = None,
        level: LogLevel | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> LogSearchResult:
        """Search logs with filtering."""
        results = []
        level_order = list(LogLevel)

        for entry in self._logs:
            # Filter by service
            if service_name and entry.service_name != service_name:
                continue

            # Filter by level (include this level and above)
            if level:
                entry_idx = level_order.index(entry.level) if entry.level in level_order else -1
                filter_idx = level_order.index(level)
                if entry_idx < filter_idx:
                    continue

            # Filter by time range
            if start and entry.timestamp < start:
                continue
            if end and entry.timestamp > end:
                continue

            # Filter by text query
            if query and query.lower() not in entry.message.lower():
                continue

            results.append(entry)

        # Sort by timestamp descending and limit
        results.sort(key=lambda e: e.timestamp, reverse=True)
        results = results[:limit]

        return LogSearchResult(entries=results, total_count=len(results))

    async def get_logs_for_trace(
        self,
        trace_id: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> LogSearchResult:
        """Get logs correlated with a trace."""
        results = []

        for entry in self._logs:
            if entry.trace_id != trace_id:
                continue

            if start and entry.timestamp < start:
                continue
            if end and entry.timestamp > end:
                continue

            results.append(entry)

        results.sort(key=lambda e: e.timestamp)
        return LogSearchResult(entries=results, total_count=len(results))

    async def get_logs_by_attribute(
        self,
        attribute: str,
        value: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> LogSearchResult:
        """Get logs by attribute value."""
        results = []

        for entry in self._logs:
            if entry.attributes.get(attribute) != value:
                continue

            if start and entry.timestamp < start:
                continue
            if end and entry.timestamp > end:
                continue

            results.append(entry)

        results = results[:limit]
        return LogSearchResult(entries=results, total_count=len(results))

    async def health_check(self) -> bool:
        """Always return healthy for stub."""
        return self._initialized


class StubMetricsClient(MetricsQueryClient):
    """
    In-memory stub implementation of MetricsQueryClient.

    Stores metrics in memory for testing purposes.
    """

    def __init__(self) -> None:
        self._series: dict[str, MetricSeries] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the stub client."""
        self._initialized = True
        logger.info("Stub metrics client initialized")

    async def close(self) -> None:
        """Close the stub client."""
        self._series.clear()
        logger.info("Stub metrics client closed")

    def add_series(self, series: MetricSeries) -> None:
        """Add a metric series to stub storage (for testing)."""
        key = f"{series.metric_name}:{series.labels}"
        self._series[key] = series

    async def query_instant(
        self,
        query: str,
        time: datetime | None = None,
    ) -> MetricQueryResult:
        """Execute instant query (returns all matching series)."""
        # Simple matching: query is metric name prefix
        results = []
        for series in self._series.values():
            if query in series.metric_name:
                results.append(series)
        return MetricQueryResult(series=results)

    async def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        step: timedelta | None = None,
    ) -> MetricQueryResult:
        """Execute range query."""
        results = []
        for series in self._series.values():
            if query in series.metric_name:
                # Filter values within time range
                filtered_values = [v for v in series.values if start <= v.timestamp <= end]
                if filtered_values:
                    filtered_series = MetricSeries(
                        metric_name=series.metric_name,
                        labels=series.labels,
                        values=filtered_values,
                    )
                    results.append(filtered_series)
        return MetricQueryResult(series=results)

    async def get_service_metrics(
        self,
        service_name: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> dict[str, MetricSeries]:
        """Get standard metrics for a service."""
        results = {}
        for series in self._series.values():
            if series.labels.get("service") == service_name:
                results[series.metric_name] = series
        return results

    async def health_check(self) -> bool:
        """Always return healthy for stub."""
        return self._initialized
