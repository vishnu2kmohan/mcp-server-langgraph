"""
Observability Router

Provides trace and metrics access under /api/v1/observability/*.

This consolidates observability functionality into a unified API.

Usage:
    GET /api/v1/observability/traces - List traces
    GET /api/v1/observability/traces/{id} - Get a specific trace
    GET /api/v1/observability/metrics - Get metrics summary
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.api.pagination import (
    CursorPaginatedResponse,
    CursorPaginationMetadata,
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
        self, cursor: str | None = None, limit: int = 20, session_id: str | None = None
    ) -> tuple[list[dict[str, Any]], str | None]:
        """List traces with pagination. Returns (traces, next_cursor)."""
        raise NotImplementedError

    async def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        """Get a trace by ID. Returns None if not found."""
        raise NotImplementedError

    async def get_metrics(self, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
        """Get metrics summary. Returns metrics data."""
        raise NotImplementedError


# Service singleton
_observability_service: ObservabilityService | None = None


def get_observability_service() -> ObservabilityService:
    """Get the observability service instance."""
    global _observability_service
    if _observability_service is None:
        _observability_service = ObservabilityService()
    return _observability_service


def set_observability_service(service: ObservabilityService) -> None:
    """Set the observability service instance (for testing/DI)."""
    global _observability_service
    _observability_service = service


# Endpoints


@observability_router.get("/observability/traces")
async def list_traces(
    cursor: str | None = Query(default=None, description="Pagination cursor"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session_id: str | None = Query(default=None, description="Filter by session ID"),
) -> CursorPaginatedResponse[dict[str, Any]]:
    """
    List traces with cursor-based pagination.

    Optionally filter by session_id to get traces for a specific session.
    """
    service = get_observability_service()
    traces, next_cursor = await service.list_traces(cursor=cursor, limit=limit, session_id=session_id)

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
