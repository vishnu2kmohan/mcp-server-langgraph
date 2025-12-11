"""
Grafana Loki implementation of LoggingQueryClient.

Provides LogQL-based log querying through the abstract interface,
enabling backend swapping without code changes.

Reference:
- Loki API: https://grafana.com/docs/loki/latest/reference/api/
- LogQL: https://grafana.com/docs/loki/latest/query/
"""

import logging
import os
import ssl
from datetime import UTC, datetime, timedelta
from typing import Any

import certifi
import httpx

from ..interfaces import (
    LogEntry,
    LogLevel,
    LogSearchResult,
    LoggingQueryClient,
)

logger = logging.getLogger(__name__)


class LokiLoggingClient(LoggingQueryClient):
    """
    Grafana Loki implementation of LoggingQueryClient.

    Configured via environment variables:
        LOKI_URL: Loki server URL (default: http://loki:3100)
        LOKI_TIMEOUT: Query timeout in seconds (default: 30)

    Example:
        client = LokiLoggingClient()
        await client.initialize()

        # Search logs
        result = await client.search_logs(query="error", level=LogLevel.ERROR)

        # Get logs for a trace
        result = await client.get_logs_for_trace("trace-123")

        await client.close()
    """

    def __init__(self) -> None:
        """Initialize with configuration from environment."""
        self._url = os.getenv("LOKI_URL", "http://loki:3100")
        self._timeout = int(os.getenv("LOKI_TIMEOUT", "30"))
        self._client: httpx.AsyncClient | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the HTTP client."""
        if self._initialized:
            return

        # Use certifi CA bundle for cross-platform SSL verification
        ssl_context = ssl.create_default_context()
        try:
            ssl_context.load_verify_locations(certifi.where())
        except FileNotFoundError:
            logger.warning("certifi CA bundle not found, falling back to system certs")

        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            follow_redirects=True,
            verify=ssl_context,
        )

        self._initialized = True
        logger.info(f"Loki logging client initialized: {self._url}")

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._initialized = False
        logger.info("Loki logging client closed")

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

        Builds a LogQL query from the parameters.
        """
        if not self._initialized:
            await self.initialize()
        assert self._client is not None

        # Build LogQL query
        logql = self._build_logql(
            text_query=query,
            service_name=service_name,
            level=level,
        )

        # Set time range
        if not start:
            start = datetime.now(UTC) - timedelta(hours=1)
        if not end:
            end = datetime.now(UTC)

        params: dict[str, Any] = {
            "query": logql,
            "start": int(start.timestamp() * 1e9),  # nanoseconds
            "end": int(end.timestamp() * 1e9),
            "limit": limit,
            "direction": "backward",  # Most recent first
        }

        try:
            response = await self._client.get(
                f"{self._url}/loki/api/v1/query_range",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            entries = self._parse_query_result(data)
            return LogSearchResult(entries=entries, total_count=len(entries))

        except httpx.HTTPError as e:
            logger.exception(f"Loki query failed: {e}")
            raise

    async def get_logs_for_trace(
        self,
        trace_id: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> LogSearchResult:
        """
        Get logs correlated with a specific trace.

        Uses trace_id label or JSON field matching.
        """
        if not start:
            start = datetime.now(UTC) - timedelta(hours=1)
        if not end:
            end = datetime.now(UTC)

        # LogQL query for trace correlation
        # Try both label and JSON field matching
        logql = f'{{trace_id="{trace_id}"}} or {{}} | json | trace_id="{trace_id}"'

        return await self.search_logs(
            query=logql,
            start=start,
            end=end,
            limit=1000,  # Get all logs for the trace
        )

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
        """
        # Use JSON parsing to extract attribute
        logql = f'{{}} | json | {attribute}="{value}"'

        return await self.search_logs(
            query=logql,
            start=start,
            end=end,
            limit=limit,
        )

    async def health_check(self) -> bool:
        """Check if Loki is healthy and reachable."""
        if not self._initialized:
            await self.initialize()
        assert self._client is not None

        try:
            response = await self._client.get(f"{self._url}/ready")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def _build_logql(
        self,
        text_query: str | None = None,
        service_name: str | None = None,
        level: LogLevel | None = None,
    ) -> str:
        """Build a LogQL query from parameters."""
        # Start with stream selector
        labels = []
        if service_name:
            labels.append(f'service_name="{service_name}"')

        stream_selector = "{" + ", ".join(labels) + "}" if labels else "{}"

        # Build pipeline
        pipeline = []

        # Level filter (Loki levels: debug, info, warn, error, fatal)
        if level:
            level_value = level.value
            pipeline.append(f'|= `"level":"{level_value}"`')

        # Text search
        if text_query:
            # Check if it's already a LogQL query
            if text_query.startswith("{") or "|" in text_query:
                return text_query
            # Simple text filter
            pipeline.append(f"|~ `{text_query}`")

        if pipeline:
            return stream_selector + " " + " ".join(pipeline)
        return stream_selector

    def _parse_query_result(self, data: dict[str, Any]) -> list[LogEntry]:
        """Parse Loki query result into LogEntry list."""
        entries = []

        result_data = data.get("data", {})
        results = result_data.get("result", [])

        for stream in results:
            labels = stream.get("stream", {})
            service_name = labels.get("service_name", labels.get("job", "unknown"))

            for value in stream.get("values", []):
                timestamp_ns, message = value[0], value[1]

                # Parse timestamp (nanoseconds)
                timestamp = datetime.fromtimestamp(int(timestamp_ns) / 1e9, tz=UTC)

                # Try to extract level from message (JSON or text)
                level = self._extract_level(message)

                # Try to extract trace correlation
                trace_id, span_id = self._extract_trace_context(message, labels)

                # Try to extract attributes from JSON
                attributes = self._extract_attributes(message)

                entries.append(
                    LogEntry(
                        timestamp=timestamp,
                        level=level,
                        message=message,
                        service_name=service_name,
                        trace_id=trace_id,
                        span_id=span_id,
                        attributes=attributes,
                    )
                )

        return entries

    def _extract_level(self, message: str) -> LogLevel:
        """Extract log level from message."""
        import json

        try:
            data = json.loads(message)
            level_str = data.get("level", "info").lower()
            return LogLevel(level_str)
        except (json.JSONDecodeError, ValueError):
            pass

        # Try to match level patterns in text
        message_lower = message.lower()
        if "error" in message_lower or "fatal" in message_lower:
            return LogLevel.ERROR
        if "warn" in message_lower:
            return LogLevel.WARN
        if "debug" in message_lower:
            return LogLevel.DEBUG

        return LogLevel.INFO

    def _extract_trace_context(self, message: str, labels: dict[str, str]) -> tuple[str | None, str | None]:
        """Extract trace_id and span_id from message or labels."""
        import json

        trace_id = labels.get("trace_id")
        span_id = labels.get("span_id")

        if trace_id and span_id:
            return trace_id, span_id

        try:
            data = json.loads(message)
            trace_id = trace_id or data.get("trace_id")
            span_id = span_id or data.get("span_id")
        except json.JSONDecodeError:
            pass

        return trace_id, span_id

    def _extract_attributes(self, message: str) -> dict[str, Any]:
        """Extract attributes from JSON message."""
        import json

        try:
            data = json.loads(message)
            # Exclude standard fields
            excluded = {"timestamp", "level", "message", "msg", "trace_id", "span_id"}
            return {k: v for k, v in data.items() if k not in excluded}
        except json.JSONDecodeError:
            return {}
