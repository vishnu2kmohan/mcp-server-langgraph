"""
GCP Cloud Trace implementation of TracingQueryClient.

Provides Cloud Trace API querying through the abstract interface,
enabling backend swapping without code changes.

Configured via environment variables:
    GOOGLE_CLOUD_PROJECT: GCP project ID
    GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON (optional)

Reference:
- Cloud Trace API: https://cloud.google.com/trace/docs/reference
- Python Client: https://cloud.google.com/python/docs/reference/cloudtrace/latest
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from ..interfaces import (
    SpanInfo,
    SpanStatusCode,
    TraceInfo,
    TraceSearchResult,
    TracingQueryClient,
)

if TYPE_CHECKING:
    from google.cloud import trace_v1

logger = logging.getLogger(__name__)


class CloudTraceClient(TracingQueryClient):
    """
    GCP Cloud Trace implementation of TracingQueryClient.

    Uses the Cloud Trace API to query distributed traces stored in GCP.

    Configured via environment variables:
        GOOGLE_CLOUD_PROJECT: GCP project ID (required)
        GOOGLE_APPLICATION_CREDENTIALS: Service account JSON path (optional)

    Example:
        client = CloudTraceClient()
        await client.initialize()

        # Search traces
        result = await client.search_traces(service_name="mcp-server", limit=10)

        # Get trace by ID
        trace = await client.get_trace("abc123def456...")

        await client.close()
    """

    def __init__(self) -> None:
        """Initialize with configuration from environment."""
        self._project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "")
        self._client: trace_v1.TraceServiceAsyncClient | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the Cloud Trace client."""
        if self._initialized:
            return

        try:
            from google.cloud import trace_v1

            self._client = trace_v1.TraceServiceAsyncClient()
            self._initialized = True
            logger.info(f"Cloud Trace client initialized for project: {self._project_id}")
        except ImportError:
            raise ImportError("google-cloud-trace package required. Install with: pip install google-cloud-trace")

    async def close(self) -> None:
        """Close the Cloud Trace client."""
        if self._client:
            # GCP clients don't have explicit close, but we reset state
            self._client = None
        self._initialized = False
        logger.info("Cloud Trace client closed")

    async def get_trace(self, trace_id: str) -> TraceInfo | None:
        """
        Get a trace by its ID.

        Args:
            trace_id: The 32-character hex trace ID

        Returns:
            TraceInfo if found, None otherwise
        """
        if not self._initialized:
            await self.initialize()
        assert self._client is not None

        try:
            from google.cloud import trace_v1

            request = trace_v1.GetTraceRequest(
                project_id=self._project_id,
                trace_id=trace_id,
            )

            trace = await self._client.get_trace(request=request)
            return self._convert_trace(trace, trace_id)

        except Exception as e:
            logger.exception(f"Failed to get trace {trace_id}: {e}")
            return None

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

        Uses Cloud Trace filter syntax.
        """
        if not self._initialized:
            await self.initialize()
        assert self._client is not None

        # Build filter string
        filters = []

        if service_name:
            filters.append(f"+label:service_name:{service_name}")

        if operation_name:
            filters.append(f'+span:"{operation_name}"')

        if tags:
            for key, value in tags.items():
                filters.append(f"+label:{key}:{value}")

        if min_duration_ms:
            # Cloud Trace uses nanoseconds
            min_duration_ns = int(min_duration_ms * 1_000_000)
            filters.append(f"duration>={min_duration_ns}ns")

        if max_duration_ms:
            max_duration_ns = int(max_duration_ms * 1_000_000)
            filters.append(f"duration<={max_duration_ns}ns")

        filter_str = " ".join(filters) if filters else ""

        # Default time range
        if not end:
            end = datetime.now(UTC)
        if not start:
            start = end - timedelta(hours=1)

        try:
            from google.cloud import trace_v1
            from google.protobuf import timestamp_pb2

            start_time = timestamp_pb2.Timestamp()
            start_time.FromDatetime(start)

            end_time = timestamp_pb2.Timestamp()
            end_time.FromDatetime(end)

            request = trace_v1.ListTracesRequest(
                project_id=self._project_id,
                start_time=start_time,
                end_time=end_time,
                filter=filter_str if filter_str else None,
                page_size=limit,
            )

            traces = []
            async for trace in await self._client.list_traces(request=request):
                trace_info = self._convert_trace(trace, trace.trace_id)
                if trace_info:
                    traces.append(trace_info)
                if len(traces) >= limit:
                    break

            return TraceSearchResult(traces=traces, total_count=len(traces))

        except Exception as e:
            logger.exception(f"Failed to search traces: {e}")
            return TraceSearchResult(traces=[], total_count=0)

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

        Uses Cloud Trace label filtering.
        """
        return await self.search_traces(
            tags={attribute: value},
            start=start,
            end=end,
            limit=limit,
        )

    async def get_error_traces(
        self,
        service_name: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 20,
    ) -> TraceSearchResult:
        """
        Get traces that contain errors.

        Uses Cloud Trace status filtering.
        """
        if not self._initialized:
            await self.initialize()
        assert self._client is not None

        # Build filter for error traces
        filters = ["+status:ERROR"]

        if service_name:
            filters.append(f"+label:service_name:{service_name}")

        filter_str = " ".join(filters)

        # Default time range
        if not end:
            end = datetime.now(UTC)
        if not start:
            start = end - timedelta(hours=1)

        try:
            from google.cloud import trace_v1
            from google.protobuf import timestamp_pb2

            start_time = timestamp_pb2.Timestamp()
            start_time.FromDatetime(start)

            end_time = timestamp_pb2.Timestamp()
            end_time.FromDatetime(end)

            request = trace_v1.ListTracesRequest(
                project_id=self._project_id,
                start_time=start_time,
                end_time=end_time,
                filter=filter_str,
                page_size=limit,
            )

            traces = []
            async for trace in await self._client.list_traces(request=request):
                trace_info = self._convert_trace(trace, trace.trace_id)
                if trace_info:
                    traces.append(trace_info)
                if len(traces) >= limit:
                    break

            return TraceSearchResult(traces=traces, total_count=len(traces))

        except Exception as e:
            logger.exception(f"Failed to get error traces: {e}")
            return TraceSearchResult(traces=[], total_count=0)

    async def health_check(self) -> bool:
        """Check if Cloud Trace API is accessible."""
        return self._initialized

    def _convert_trace(self, trace: Any, trace_id: str) -> TraceInfo | None:
        """Convert Cloud Trace response to TraceInfo."""
        try:
            spans = []
            root_service = "unknown"
            root_operation = ""
            start_time = datetime.now(UTC)
            total_duration_ns = 0
            error_count = 0

            for span in trace.spans:
                span_info = self._convert_span(span, trace_id)
                spans.append(span_info)

                # Track root span
                if not span.parent_span_id:
                    root_operation = span_info.operation_name
                    start_time = span_info.start_time
                    total_duration_ns = int(span_info.duration_ms * 1_000_000)

                    # Extract service name from labels
                    if hasattr(span, "labels") and span.labels:
                        root_service = span.labels.get("service_name", "unknown")

                # Count errors
                if span_info.status_code == SpanStatusCode.ERROR:
                    error_count += 1

            return TraceInfo(
                trace_id=trace_id,
                root_service=root_service,
                root_operation=root_operation,
                start_time=start_time,
                duration_ms=total_duration_ns / 1_000_000,
                span_count=len(spans),
                error_count=error_count,
                spans=spans,
            )

        except Exception as e:
            logger.warning(f"Failed to convert trace {trace_id}: {e}")
            return None

    def _convert_span(self, span: Any, trace_id: str) -> SpanInfo:
        """Convert Cloud Trace span to SpanInfo."""
        # Parse timestamps
        start_time = datetime.fromtimestamp(
            span.start_time.seconds + span.start_time.nanos / 1e9,
            tz=UTC,
        )
        end_time = datetime.fromtimestamp(
            span.end_time.seconds + span.end_time.nanos / 1e9,
            tz=UTC,
        )
        duration_ms = (end_time - start_time).total_seconds() * 1000

        # Map status code
        status_code = SpanStatusCode.UNSET
        if hasattr(span, "status") and span.status:
            if span.status.code == 2:  # ERROR
                status_code = SpanStatusCode.ERROR
            elif span.status.code == 1:  # OK
                status_code = SpanStatusCode.OK

        # Extract attributes
        attributes = {}
        if hasattr(span, "attributes") and span.attributes:
            for key, value in span.attributes.attribute_map.items():
                if hasattr(value, "string_value"):
                    attributes[key] = value.string_value.value
                elif hasattr(value, "int_value"):
                    attributes[key] = value.int_value
                elif hasattr(value, "bool_value"):
                    attributes[key] = value.bool_value

        # Extract service name
        service_name = "unknown"
        if hasattr(span, "labels") and span.labels:
            service_name = span.labels.get("service_name", "unknown")

        return SpanInfo(
            span_id=span.span_id,
            trace_id=trace_id,
            operation_name=span.display_name.value if hasattr(span.display_name, "value") else str(span.display_name),
            service_name=service_name,
            start_time=start_time,
            duration_ms=duration_ms,
            status_code=status_code,
            parent_span_id=span.parent_span_id if span.parent_span_id else None,
            attributes=attributes,
            events=[],
        )
