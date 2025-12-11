"""
Grafana Tempo implementation of TracingQueryClient.

Wraps the existing TempoClient from monitoring/tempo_client.py to implement
the abstract TracingQueryClient interface for vendor-neutral trace querying.

This allows applications to query Tempo traces through the abstract interface,
enabling backend swapping without code changes.

Reference:
- Tempo API: https://grafana.com/docs/tempo/latest/api_docs/
- TraceQL: https://grafana.com/docs/tempo/latest/traceql/
"""

import logging
import os
from datetime import datetime

from mcp_server_langgraph.monitoring.tempo_client import (
    SpanInfo as TempoSpanInfo,
    TempoClient,
    TempoConfig,
    TraceInfo as TempoTraceInfo,
)

from ..interfaces import (
    SpanInfo,
    SpanStatusCode,
    TraceInfo,
    TraceSearchResult,
    TracingQueryClient,
)

logger = logging.getLogger(__name__)


def _convert_span(tempo_span: TempoSpanInfo) -> SpanInfo:
    """Convert Tempo SpanInfo to interface SpanInfo."""
    # Map status code
    status_code = SpanStatusCode.UNSET
    if tempo_span.status_code == "ERROR":
        status_code = SpanStatusCode.ERROR
    elif tempo_span.status_code == "OK":
        status_code = SpanStatusCode.OK

    return SpanInfo(
        span_id=tempo_span.span_id,
        trace_id=tempo_span.trace_id,
        operation_name=tempo_span.operation_name,
        service_name=tempo_span.service_name,
        start_time=tempo_span.start_time,
        duration_ms=tempo_span.duration_ms,
        status_code=status_code,
        parent_span_id=tempo_span.parent_span_id,
        attributes=tempo_span.attributes,
        events=tempo_span.events,
    )


def _convert_trace(tempo_trace: TempoTraceInfo) -> TraceInfo:
    """Convert Tempo TraceInfo to interface TraceInfo."""
    return TraceInfo(
        trace_id=tempo_trace.trace_id,
        root_service=tempo_trace.root_service,
        root_operation=tempo_trace.root_operation,
        start_time=tempo_trace.start_time,
        duration_ms=tempo_trace.duration_ms,
        span_count=tempo_trace.span_count,
        error_count=tempo_trace.error_count,
        spans=[_convert_span(s) for s in tempo_trace.spans],
    )


class TempoTracingClient(TracingQueryClient):
    """
    Grafana Tempo implementation of TracingQueryClient.

    Wraps the existing TempoClient to provide the abstract interface.
    Configured via environment variables:
        TEMPO_URL: Tempo server URL (default: http://tempo:3200)

    Example:
        client = TempoTracingClient()
        await client.initialize()

        # Search traces
        result = await client.search_traces(service_name="mcp-server", limit=10)

        # Get trace by ID
        trace = await client.get_trace("abc123def456...")

        await client.close()
    """

    def __init__(self) -> None:
        """Initialize with configuration from environment."""
        tempo_url = os.getenv("TEMPO_URL", "http://tempo:3200")
        timeout = int(os.getenv("TEMPO_TIMEOUT", "30"))

        config = TempoConfig(url=tempo_url, timeout=timeout)
        self._client = TempoClient(config=config)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the Tempo client."""
        await self._client.initialize()
        self._initialized = True
        logger.info("Tempo tracing client initialized")

    async def close(self) -> None:
        """Close the Tempo client."""
        await self._client.close()
        self._initialized = False
        logger.info("Tempo tracing client closed")

    async def get_trace(self, trace_id: str) -> TraceInfo | None:
        """
        Get a trace by its ID.

        Args:
            trace_id: The 32-character hex trace ID

        Returns:
            TraceInfo if found, None otherwise
        """
        tempo_trace = await self._client.get_trace(trace_id)
        if tempo_trace is None:
            return None
        return _convert_trace(tempo_trace)

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

        Uses Tempo's TraceQL search capabilities.
        """
        # Convert duration to Tempo format (e.g., "100ms", "1s")
        min_duration = None
        max_duration = None
        if min_duration_ms is not None:
            min_duration = f"{min_duration_ms}ms"
        if max_duration_ms is not None:
            max_duration = f"{max_duration_ms}ms"

        result = await self._client.search(
            service_name=service_name,
            operation_name=operation_name,
            tags=tags,
            start=start,
            end=end,
            min_duration=min_duration,
            max_duration=max_duration,
            limit=limit,
        )

        traces = [_convert_trace(t) for t in result.traces]
        return TraceSearchResult(traces=traces, total_count=result.total_traces)

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
        """
        result = await self._client.search_by_attribute(
            attribute=attribute,
            value=value,
            start=start,
            end=end,
            limit=limit,
        )

        traces = [_convert_trace(t) for t in result.traces]
        return TraceSearchResult(traces=traces, total_count=result.total_traces)

    async def get_error_traces(
        self,
        service_name: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 20,
    ) -> TraceSearchResult:
        """
        Get traces that contain errors.
        """
        result = await self._client.get_error_traces(
            service_name=service_name,
            start=start,
            end=end,
            limit=limit,
        )

        traces = [_convert_trace(t) for t in result.traces]
        return TraceSearchResult(traces=traces, total_count=result.total_traces)

    async def health_check(self) -> bool:
        """
        Check if Tempo is healthy and reachable.
        """
        return await self._client.health_check()
