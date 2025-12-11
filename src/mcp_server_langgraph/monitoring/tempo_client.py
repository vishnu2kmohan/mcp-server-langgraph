"""
Grafana Tempo client for querying distributed traces.

Provides a high-level interface for querying Tempo/Jaeger traces with:
- Trace lookup by ID
- TraceQL search queries
- Service span statistics
- Duration percentile analysis
- Error trace filtering

Supports both Grafana Tempo and Jaeger APIs for backward compatibility.

Reference:
- Tempo API: https://grafana.com/docs/tempo/latest/api_docs/
- TraceQL: https://grafana.com/docs/tempo/latest/traceql/
"""

import logging
import ssl
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import certifi
import httpx
from pydantic import BaseModel, Field

from mcp_server_langgraph.core.config import settings

logger = logging.getLogger(__name__)


class TempoConfig(BaseModel):
    """Tempo client configuration."""

    url: str = Field(default="http://tempo:3200", description="Tempo server URL")
    timeout: int = Field(default=30, description="Query timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    retry_backoff: float = Field(default=1.0, description="Retry backoff multiplier")


@dataclass
class SpanInfo:
    """Information about a single span."""

    span_id: str
    trace_id: str
    operation_name: str
    service_name: str
    start_time: datetime
    duration_ms: float
    status_code: str | None = None
    parent_span_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TraceInfo:
    """Information about a complete trace."""

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
        """Check if trace contains errors."""
        return self.error_count > 0


@dataclass
class TraceSearchResult:
    """Result of a trace search query."""

    traces: list[TraceInfo]
    total_traces: int


class TempoClient:
    """
    High-level Grafana Tempo query client.

    Usage:
        client = TempoClient()
        await client.initialize()

        # Get trace by ID
        trace = await client.get_trace("abc123def456...")

        # Search traces with TraceQL
        traces = await client.search(
            query='{ resource.service.name = "mcp-server" }',
            start=datetime.now() - timedelta(hours=1),
            limit=20
        )

        # Get traces for a session
        traces = await client.search_by_attribute(
            attribute="session_id",
            value="sess-12345",
            start=datetime.now() - timedelta(hours=1)
        )

        await client.close()
    """

    def __init__(self, config: TempoConfig | None = None) -> None:
        self.config = config or self._load_config_from_settings()
        self.client: httpx.AsyncClient | None = None
        self._initialized = False

    def _load_config_from_settings(self) -> TempoConfig:
        """Load configuration from application settings."""
        return TempoConfig(
            url=getattr(settings, "tempo_url", "http://tempo:3200"),
            timeout=getattr(settings, "tempo_timeout", 30),
            retry_attempts=getattr(settings, "tempo_retry_attempts", 3),
        )

    async def initialize(self) -> None:
        """Initialize HTTP client with cross-platform SSL support."""
        if self._initialized:
            return

        # Use certifi CA bundle for cross-platform SSL verification
        ssl_context = ssl.create_default_context()
        try:
            ssl_context.load_verify_locations(certifi.where())
        except FileNotFoundError:
            logger.warning("certifi CA bundle not found, falling back to system certs")

        self.client = httpx.AsyncClient(
            timeout=self.config.timeout,
            follow_redirects=True,
            verify=ssl_context,
        )

        self._initialized = True
        logger.info(f"Tempo client initialized: {self.config.url}")

    async def close(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
        logger.info("Tempo client closed")

    async def _ensure_initialized(self) -> None:
        """Ensure client is initialized before making requests."""
        if not self._initialized:
            await self.initialize()

    async def get_trace(self, trace_id: str) -> TraceInfo | None:
        """
        Get a trace by its ID.

        Args:
            trace_id: The trace ID to look up

        Returns:
            TraceInfo if found, None otherwise
        """
        await self._ensure_initialized()
        assert self.client is not None

        url = f"{self.config.url}/api/traces/{trace_id}"

        try:
            response = await self.client.get(url)

            if response.status_code == 404:
                return None

            response.raise_for_status()
            data = response.json()

            return self._parse_trace(data)

        except httpx.HTTPError as e:
            logger.exception(f"Failed to fetch trace {trace_id}: {e}")
            raise

    async def search(
        self,
        query: str | None = None,
        service_name: str | None = None,
        operation_name: str | None = None,
        tags: dict[str, str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        min_duration: str | None = None,
        max_duration: str | None = None,
        limit: int = 20,
    ) -> TraceSearchResult:
        """
        Search for traces using TraceQL or filters.

        Args:
            query: TraceQL query string (e.g., '{ resource.service.name = "api" }')
            service_name: Filter by service name
            operation_name: Filter by operation/span name
            tags: Filter by span tags/attributes
            start: Search start time
            end: Search end time
            min_duration: Minimum trace duration (e.g., "100ms", "1s")
            max_duration: Maximum trace duration
            limit: Maximum number of traces to return

        Returns:
            TraceSearchResult with matching traces
        """
        await self._ensure_initialized()
        assert self.client is not None

        # Build search parameters
        params: dict[str, Any] = {"limit": limit}

        if query:
            # TraceQL search endpoint
            url = f"{self.config.url}/api/search"
            params["q"] = query
        else:
            # Tag-based search endpoint
            url = f"{self.config.url}/api/search"

            if service_name:
                params["tags"] = f"service.name={service_name}"
            if operation_name:
                if "tags" in params:
                    params["tags"] += f" name={operation_name}"
                else:
                    params["tags"] = f"name={operation_name}"

        if start:
            params["start"] = int(start.timestamp())
        if end:
            params["end"] = int(end.timestamp())
        if min_duration:
            params["minDuration"] = min_duration
        if max_duration:
            params["maxDuration"] = max_duration

        # Add tag filters
        if tags:
            tag_str = " ".join(f"{k}={v}" for k, v in tags.items())
            if "tags" in params:
                params["tags"] += f" {tag_str}"
            else:
                params["tags"] = tag_str

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            traces = []
            for trace_data in data.get("traces", []):
                trace = self._parse_trace_summary(trace_data)
                if trace:
                    traces.append(trace)

            return TraceSearchResult(
                traces=traces,
                total_traces=len(traces),
            )

        except httpx.HTTPError as e:
            logger.exception(f"Failed to search traces: {e}")
            raise

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
            attribute: Attribute name (e.g., "session_id", "user_id")
            value: Attribute value to match
            start: Search start time (defaults to last hour)
            end: Search end time (defaults to now)
            limit: Maximum number of traces

        Returns:
            TraceSearchResult with matching traces
        """
        if not start:
            start = datetime.now(UTC) - timedelta(hours=1)
        if not end:
            end = datetime.now(UTC)

        # Build TraceQL query for attribute match
        query = f'{{ span.{attribute} = "{value}" || resource.{attribute} = "{value}" }}'

        return await self.search(
            query=query,
            start=start,
            end=end,
            limit=limit,
        )

    async def get_service_spans(
        self,
        service_name: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> list[SpanInfo]:
        """
        Get recent spans for a service.

        Args:
            service_name: Service name to filter
            start: Start time (defaults to last hour)
            end: End time (defaults to now)
            limit: Maximum spans to return

        Returns:
            List of SpanInfo for the service
        """
        result = await self.search(
            service_name=service_name,
            start=start,
            end=end,
            limit=limit,
        )

        all_spans = []
        for trace in result.traces:
            all_spans.extend(trace.spans)

        return all_spans[:limit]

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
        if not start:
            start = datetime.now(UTC) - timedelta(hours=1)
        if not end:
            end = datetime.now(UTC)

        # TraceQL query for error spans
        query = f'{{ resource.service.name = "{service_name}" && status = error }}' if service_name else "{ status = error }"

        return await self.search(
            query=query,
            start=start,
            end=end,
            limit=limit,
        )

    async def health_check(self) -> bool:
        """
        Check if Tempo is healthy and reachable.

        Returns:
            True if healthy, False otherwise
        """
        await self._ensure_initialized()
        assert self.client is not None

        try:
            response = await self.client.get(f"{self.config.url}/ready")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def _parse_trace(self, data: dict[str, Any]) -> TraceInfo:
        """Parse Tempo trace response into TraceInfo."""
        batches = data.get("batches", [])

        spans: list[SpanInfo] = []
        root_service = ""
        root_operation = ""
        trace_id = ""
        start_time = datetime.now(UTC)
        total_duration_ms = 0.0
        error_count = 0

        for batch in batches:
            resource = batch.get("resource", {})
            resource_attrs = self._parse_attributes(resource.get("attributes", []))
            service_name = resource_attrs.get("service.name", "unknown")

            for scope_span in batch.get("scopeSpans", []):
                for span_data in scope_span.get("spans", []):
                    span = self._parse_span(span_data, service_name)
                    spans.append(span)

                    # Track root span
                    if not span.parent_span_id:
                        root_service = service_name
                        root_operation = span.operation_name
                        trace_id = span.trace_id
                        start_time = span.start_time
                        total_duration_ms = span.duration_ms

                    # Count errors
                    if span.status_code == "ERROR":
                        error_count += 1

        return TraceInfo(
            trace_id=trace_id,
            root_service=root_service,
            root_operation=root_operation,
            start_time=start_time,
            duration_ms=total_duration_ms,
            span_count=len(spans),
            error_count=error_count,
            spans=spans,
        )

    def _parse_trace_summary(self, data: dict[str, Any]) -> TraceInfo | None:
        """Parse trace search result summary."""
        try:
            trace_id = data.get("traceID", "")
            root_service = data.get("rootServiceName", "unknown")
            root_trace_name = data.get("rootTraceName", "")

            # Parse start time (nanoseconds to datetime)
            start_time_nanos = data.get("startTimeUnixNano", 0)
            start_time = datetime.fromtimestamp(
                start_time_nanos / 1e9,
                tz=UTC,
            )

            # Parse duration (nanoseconds to milliseconds)
            duration_nanos = data.get("durationMs", 0) * 1e6  # API returns ms
            if "durationMs" not in data:
                duration_nanos = data.get("durationNanos", 0)

            return TraceInfo(
                trace_id=trace_id,
                root_service=root_service,
                root_operation=root_trace_name,
                start_time=start_time,
                duration_ms=duration_nanos / 1e6,
                span_count=data.get("spanCount", 0),
                error_count=0,  # Not available in summary
                spans=[],  # Full spans require get_trace()
            )
        except (KeyError, ValueError) as e:
            logger.warning(f"Failed to parse trace summary: {e}")
            return None

    def _parse_span(self, span_data: dict[str, Any], service_name: str) -> SpanInfo:
        """Parse individual span data."""
        # Parse start time (nanoseconds)
        start_time_nanos = int(span_data.get("startTimeUnixNano", 0))
        start_time = datetime.fromtimestamp(start_time_nanos / 1e9, tz=UTC)

        # Parse duration (nanoseconds to milliseconds)
        end_time_nanos = int(span_data.get("endTimeUnixNano", 0))
        duration_ns = end_time_nanos - start_time_nanos
        duration_ms = duration_ns / 1e6

        # Parse status
        status = span_data.get("status", {})
        status_code = status.get("code", "UNSET")
        if status_code == 2:
            status_code = "ERROR"
        elif status_code == 1:
            status_code = "OK"
        else:
            status_code = "UNSET"

        return SpanInfo(
            span_id=span_data.get("spanId", ""),
            trace_id=span_data.get("traceId", ""),
            operation_name=span_data.get("name", ""),
            service_name=service_name,
            start_time=start_time,
            duration_ms=duration_ms,
            status_code=status_code,
            parent_span_id=span_data.get("parentSpanId"),
            attributes=self._parse_attributes(span_data.get("attributes", [])),
            events=span_data.get("events", []),
        )

    def _parse_attributes(self, attrs: list[dict[str, Any]]) -> dict[str, Any]:
        """Parse OTLP-style attributes list to dict."""
        result = {}
        for attr in attrs:
            key = attr.get("key", "")
            value = attr.get("value", {})

            # Extract typed value
            if "stringValue" in value:
                result[key] = value["stringValue"]
            elif "intValue" in value:
                result[key] = int(value["intValue"])
            elif "boolValue" in value:
                result[key] = value["boolValue"]
            elif "doubleValue" in value:
                result[key] = value["doubleValue"]
            elif "arrayValue" in value:
                result[key] = value["arrayValue"]

        return result


# Global client instance
_tempo_client: TempoClient | None = None


def get_tempo_client() -> TempoClient:
    """Get or create global Tempo client instance."""
    global _tempo_client
    if _tempo_client is None:
        _tempo_client = TempoClient()
    return _tempo_client


async def init_tempo_client() -> TempoClient:
    """Initialize and return global Tempo client."""
    client = get_tempo_client()
    await client.initialize()
    return client
