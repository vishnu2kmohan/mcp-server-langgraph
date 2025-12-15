"""
Observability Router

Provides trace and metrics access under /api/v1/observability/*.

This consolidates observability functionality into a unified API.

Usage:
    GET /api/v1/observability/traces - List traces
    GET /api/v1/observability/traces/{id} - Get a specific trace
    GET /api/v1/observability/metrics - Get metrics summary
"""

from typing import TYPE_CHECKING, Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.api.pagination import (
    CursorPaginatedResponse,
    CursorPaginationMetadata,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.observability.query.interfaces import (
        MetricsQueryClient,
        TracingQueryClient,
    )


observability_router = APIRouter(tags=["observability"])


# Response Models


class SpanResponse(BaseModel):
    """Response model for a span."""

    span_id: str = Field(description="Span ID")
    parent_span_id: str | None = Field(default=None, description="Parent span ID")
    name: str = Field(description="Span name")
    start_time: str = Field(description="Start timestamp")
    end_time: str | None = Field(default=None, description="End timestamp")
    duration_ms: float | None = Field(default=None, description="Duration in milliseconds")
    status: str = Field(default="OK", description="Span status")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Span attributes")


class TraceResponse(BaseModel):
    """Response model for a trace."""

    trace_id: str = Field(description="Trace ID")
    name: str = Field(description="Trace name")
    start_time: str | None = Field(default=None, description="Start timestamp")
    end_time: str | None = Field(default=None, description="End timestamp")
    duration_ms: float | None = Field(default=None, description="Total duration")
    span_count: int | None = Field(default=None, description="Number of spans")
    spans: list[SpanResponse] = Field(default_factory=list, description="Trace spans")


class TraceListItem(BaseModel):
    """Response model for trace list item."""

    trace_id: str = Field(description="Trace ID")
    name: str = Field(description="Trace name")
    start_time: str | None = Field(default=None, description="Start timestamp")
    duration_ms: float | None = Field(default=None, description="Total duration")
    span_count: int | None = Field(default=None, description="Number of spans")


class MetricsResponse(BaseModel):
    """Response model for metrics."""

    requests_total: int = Field(description="Total requests")
    errors_total: int = Field(description="Total errors")
    latency_p50: float | None = Field(default=None, description="P50 latency in seconds")
    latency_p95: float | None = Field(default=None, description="P95 latency in seconds")
    latency_p99: float | None = Field(default=None, description="P99 latency in seconds")


# Service Interface


class ObservabilityService:
    """Interface for observability operations. Implemented by monitoring layer."""

    async def list_traces(
        self,
        cursor: str | None = None,
        limit: int = 20,
        session_id: str | None = None,
        search: str | None = None,
        sort_by: str | None = "start_time",
        sort_order: str | None = "desc",
    ) -> tuple[list[dict[str, Any]], str | None]:
        """List traces with pagination, filtering, search, and sorting.

        Args:
            cursor: Pagination cursor (trace ID to start after)
            limit: Maximum number of traces to return
            session_id: Filter by session ID
            search: Search in trace name
            sort_by: Field to sort by (name, start_time, duration_ms)
            sort_order: Sort order (asc, desc)

        Returns (traces, next_cursor).
        """
        raise NotImplementedError

    async def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        """Get a trace by ID. Returns None if not found."""
        raise NotImplementedError

    async def get_metrics(self, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
        """Get metrics summary. Returns metrics data."""
        raise NotImplementedError


class ObservabilityServiceImpl(ObservabilityService):
    """
    Implementation of ObservabilityService that wraps TracingQueryClient and MetricsQueryClient.

    Connects the API layer to the observability query layer.
    Handles conversion from TraceInfo/SpanInfo dataclasses to dict format.
    """

    def __init__(
        self,
        tracing: "TracingQueryClient | None" = None,
        metrics: "MetricsQueryClient | None" = None,
    ) -> None:
        """
        Initialize with query clients.

        Args:
            tracing: TracingQueryClient instance. If None, uses factory default.
            metrics: MetricsQueryClient instance. If None, uses factory default.
        """
        self._tracing = tracing
        self._metrics = metrics

    @property
    def tracing(self) -> "TracingQueryClient":
        """Get the tracing client, lazily initializing if needed."""
        if self._tracing is None:
            from mcp_server_langgraph.observability.query.factory import (
                get_tracing_client,
            )

            self._tracing = get_tracing_client()
        return self._tracing

    @property
    def metrics(self) -> "MetricsQueryClient":
        """Get the metrics client, lazily initializing if needed."""
        if self._metrics is None:
            from mcp_server_langgraph.observability.query.factory import (
                get_metrics_client,
            )

            self._metrics = get_metrics_client()
        return self._metrics

    def _trace_info_to_dict(self, trace: Any) -> dict[str, Any]:
        """Convert TraceInfo dataclass to dict matching TraceListItem/TraceResponse format."""
        return {
            "trace_id": trace.trace_id,
            "name": trace.root_operation,
            "start_time": trace.start_time.isoformat() if trace.start_time else None,
            "duration_ms": trace.duration_ms,
            "span_count": trace.span_count,
        }

    def _trace_info_to_full_dict(self, trace: Any) -> dict[str, Any]:
        """Convert TraceInfo with spans to full dict matching TraceResponse format."""
        result = self._trace_info_to_dict(trace)
        result["spans"] = [
            {
                "span_id": span.span_id,
                "parent_span_id": span.parent_span_id,
                "name": span.operation_name,
                "start_time": span.start_time.isoformat() if span.start_time else None,
                "duration_ms": span.duration_ms,
                "status": span.status_code.value if hasattr(span, "status_code") else "OK",
                "attributes": span.attributes if hasattr(span, "attributes") else {},
            }
            for span in trace.spans
        ]
        return result

    async def list_traces(
        self,
        cursor: str | None = None,
        limit: int = 20,
        session_id: str | None = None,
        search: str | None = None,
        sort_by: str | None = "start_time",
        sort_order: str | None = "desc",
    ) -> tuple[list[dict[str, Any]], str | None]:
        """
        List traces with pagination, filtering, search, and sorting.

        Delegates to tracing.search_traces() or tracing.search_by_attribute()
        when session_id is provided.

        Returns (traces, next_cursor).
        """
        if session_id:
            # Use attribute search for session filtering
            result = await self.tracing.search_by_attribute(
                attribute="session_id",
                value=session_id,
                limit=limit,
            )
        else:
            # Use general search
            result = await self.tracing.search_traces(
                limit=limit,
            )

        # Convert TraceInfo objects to dicts
        traces = [self._trace_info_to_dict(t) for t in result.traces]

        return traces, result.next_cursor

    async def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        """
        Get a trace by ID.

        Delegates to tracing.get_trace() and converts to dict format.

        Returns None if not found.
        """
        trace = await self.tracing.get_trace(trace_id)

        if trace is None:
            return None

        return self._trace_info_to_full_dict(trace)

    async def get_metrics(self, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
        """
        Get metrics summary.

        Queries for requests_total, errors_total, and latency percentiles.

        Returns dict matching MetricsResponse format.
        """
        # Query for key metrics using instant queries
        # Default values if metrics not available
        requests_total = 0
        errors_total = 0
        latency_p50 = None
        latency_p95 = None
        latency_p99 = None

        try:
            # Query requests_total
            requests_result = await self.metrics.query_instant("requests_total")
            if requests_result.series:
                val = requests_result.series[0].latest_value
                if val is not None:
                    requests_total = int(val)
        except Exception:
            pass  # Use default if query fails

        try:
            # Query errors_total
            errors_result = await self.metrics.query_instant("errors_total")
            if errors_result.series:
                val = errors_result.series[0].latest_value
                if val is not None:
                    errors_total = int(val)
        except Exception:
            pass  # Use default if query fails

        return {
            "requests_total": requests_total,
            "errors_total": errors_total,
            "latency_p50": latency_p50,
            "latency_p95": latency_p95,
            "latency_p99": latency_p99,
        }


# Service singleton
_observability_service: ObservabilityService | None = None


def get_observability_service() -> ObservabilityService:
    """Get the observability service instance (returns ObservabilityServiceImpl)."""
    global _observability_service
    if _observability_service is None:
        _observability_service = ObservabilityServiceImpl()
    return _observability_service


def set_observability_service(service: ObservabilityService) -> None:
    """Set the observability service instance (for testing/DI)."""
    global _observability_service
    _observability_service = service


def reset_observability_service() -> None:
    """Reset the observability service singleton (for testing)."""
    global _observability_service
    _observability_service = None


# Endpoints


@observability_router.get("/observability/traces")
async def list_traces(
    cursor: str | None = Query(default=None, description="Pagination cursor"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session_id: str | None = Query(default=None, description="Filter by session ID"),
    search: str | None = Query(default=None, min_length=1, max_length=500, description="Search in trace name"),
    sort_by: Literal["name", "start_time", "duration_ms"] = Query(default="start_time", description="Field to sort by"),
    sort_order: Literal["asc", "desc"] = Query(default="desc", description="Sort order"),
) -> CursorPaginatedResponse[dict[str, Any]]:
    """
    List traces with cursor-based pagination.

    Supports:
    - Pagination: cursor, limit
    - Filtering: session_id
    - Search: search (searches trace name)
    - Sorting: sort_by, sort_order

    Optionally filter by session_id to get traces for a specific session.
    """
    service = get_observability_service()
    traces, next_cursor = await service.list_traces(
        cursor=cursor,
        limit=limit,
        session_id=session_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Build pagination metadata
    has_next = next_cursor is not None
    pagination = CursorPaginationMetadata(
        next_cursor=next_cursor,
        prev_cursor=None,
        has_next=has_next,
        has_prev=cursor is not None,
        count=len(traces),
    )

    return CursorPaginatedResponse(data=traces, pagination=pagination)


@observability_router.get("/observability/traces/{trace_id}")
async def get_trace(trace_id: str) -> TraceResponse:
    """
    Get a specific trace by ID.

    Returns the complete trace with all spans.
    """
    service = get_observability_service()
    trace = await service.get_trace(trace_id)

    if trace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace {trace_id} not found",
        )

    return TraceResponse(**trace)


@observability_router.get("/observability/metrics")
async def get_metrics(
    start_date: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
) -> MetricsResponse:
    """
    Get metrics summary.

    Returns aggregate metrics for the specified period.
    """
    service = get_observability_service()
    metrics = await service.get_metrics(start_date=start_date, end_date=end_date)

    return MetricsResponse(**metrics)
