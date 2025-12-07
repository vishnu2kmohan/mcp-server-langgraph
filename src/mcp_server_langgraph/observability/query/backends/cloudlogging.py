"""
GCP Cloud Logging implementation of LoggingQueryClient.

Provides Cloud Logging API querying through the abstract interface,
enabling backend swapping without code changes.

Configured via environment variables:
    GOOGLE_CLOUD_PROJECT: GCP project ID
    GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON (optional)

Reference:
- Cloud Logging API: https://cloud.google.com/logging/docs/reference/v2/rest
- Python Client: https://cloud.google.com/python/docs/reference/logging/latest
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from ..interfaces import (
    LogEntry,
    LogLevel,
    LogSearchResult,
    LoggingQueryClient,
)

if TYPE_CHECKING:
    from google.cloud import logging_v2

logger = logging.getLogger(__name__)


# Map GCP severity to our LogLevel
_SEVERITY_MAP = {
    0: LogLevel.DEBUG,  # DEFAULT
    100: LogLevel.DEBUG,  # DEBUG
    200: LogLevel.INFO,  # INFO
    300: LogLevel.INFO,  # NOTICE
    400: LogLevel.WARN,  # WARNING
    500: LogLevel.ERROR,  # ERROR
    600: LogLevel.ERROR,  # CRITICAL
    700: LogLevel.FATAL,  # ALERT
    800: LogLevel.FATAL,  # EMERGENCY
}


class CloudLoggingClient(LoggingQueryClient):
    """
    GCP Cloud Logging implementation of LoggingQueryClient.

    Uses the Cloud Logging API to query logs stored in GCP.

    Configured via environment variables:
        GOOGLE_CLOUD_PROJECT: GCP project ID (required)
        GOOGLE_APPLICATION_CREDENTIALS: Service account JSON path (optional)

    Example:
        client = CloudLoggingClient()
        await client.initialize()

        # Search logs
        result = await client.search_logs(query="error", level=LogLevel.ERROR)

        # Get logs for a trace
        result = await client.get_logs_for_trace("trace-123")

        await client.close()
    """

    def __init__(self) -> None:
        """Initialize with configuration from environment."""
        self._project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "")
        self._client: logging_v2.LoggingServiceV2AsyncClient | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the Cloud Logging client."""
        if self._initialized:
            return

        try:
            from google.cloud import logging_v2

            self._client = logging_v2.LoggingServiceV2AsyncClient()
            self._initialized = True
            logger.info(f"Cloud Logging client initialized for project: {self._project_id}")
        except ImportError:
            raise ImportError("google-cloud-logging package required. Install with: pip install google-cloud-logging")

    async def close(self) -> None:
        """Close the Cloud Logging client."""
        if self._client:
            self._client = None
        self._initialized = False
        logger.info("Cloud Logging client closed")

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

        Builds a Cloud Logging filter from the parameters.
        """
        if not self._initialized:
            await self.initialize()
        assert self._client is not None

        # Build filter string
        filter_parts = []

        # Time range
        if not end:
            end = datetime.now(UTC)
        if not start:
            start = end - timedelta(hours=1)

        filter_parts.append(f'timestamp>="{start.isoformat()}"')
        filter_parts.append(f'timestamp<="{end.isoformat()}"')

        # Service name filter
        if service_name:
            filter_parts.append(f'resource.labels.service_name="{service_name}"')

        # Level filter
        if level:
            severity = self._level_to_severity(level)
            filter_parts.append(f"severity>={severity}")

        # Text search
        if query:
            # Check if it's already a Cloud Logging filter
            if "=" in query or ":" in query:
                filter_parts.append(query)
            else:
                filter_parts.append(f'textPayload:"{query}"')

        filter_str = " AND ".join(filter_parts)

        try:
            from google.cloud import logging_v2

            request = logging_v2.ListLogEntriesRequest(
                resource_names=[f"projects/{self._project_id}"],
                filter=filter_str,
                order_by="timestamp desc",
                page_size=limit,
            )

            entries = []
            async for entry in await self._client.list_log_entries(request=request):
                log_entry = self._convert_entry(entry)
                if log_entry:
                    entries.append(log_entry)
                if len(entries) >= limit:
                    break

            return LogSearchResult(entries=entries, total_count=len(entries))

        except Exception as e:
            logger.exception(f"Failed to search logs: {e}")
            return LogSearchResult(entries=[], total_count=0)

    async def get_logs_for_trace(
        self,
        trace_id: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> LogSearchResult:
        """
        Get logs correlated with a specific trace.

        Uses the trace field for correlation.
        """
        if not self._initialized:
            await self.initialize()
        assert self._client is not None

        # Build filter for trace correlation
        filter_parts = []

        # Time range
        if not end:
            end = datetime.now(UTC)
        if not start:
            start = end - timedelta(hours=1)

        filter_parts.append(f'timestamp>="{start.isoformat()}"')
        filter_parts.append(f'timestamp<="{end.isoformat()}"')

        # Trace filter (Cloud Logging uses projects/PROJECT_ID/traces/TRACE_ID format)
        filter_parts.append(f'trace="projects/{self._project_id}/traces/{trace_id}" OR labels.trace_id="{trace_id}"')

        filter_str = " AND ".join(filter_parts)

        try:
            from google.cloud import logging_v2

            request = logging_v2.ListLogEntriesRequest(
                resource_names=[f"projects/{self._project_id}"],
                filter=filter_str,
                order_by="timestamp asc",  # Chronological order for traces
                page_size=1000,
            )

            entries = []
            async for entry in await self._client.list_log_entries(request=request):
                log_entry = self._convert_entry(entry)
                if log_entry:
                    entries.append(log_entry)

            return LogSearchResult(entries=entries, total_count=len(entries))

        except Exception as e:
            logger.exception(f"Failed to get logs for trace {trace_id}: {e}")
            return LogSearchResult(entries=[], total_count=0)

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

        Uses Cloud Logging label filtering.
        """
        # Use labels filter
        query = f'labels.{attribute}="{value}"'
        return await self.search_logs(
            query=query,
            start=start,
            end=end,
            limit=limit,
        )

    async def health_check(self) -> bool:
        """Check if Cloud Logging API is accessible."""
        return self._initialized

    def _level_to_severity(self, level: LogLevel) -> int:
        """Convert LogLevel to GCP severity number."""
        severity_map = {
            LogLevel.TRACE: 100,  # DEBUG
            LogLevel.DEBUG: 100,  # DEBUG
            LogLevel.INFO: 200,  # INFO
            LogLevel.WARN: 400,  # WARNING
            LogLevel.ERROR: 500,  # ERROR
            LogLevel.FATAL: 700,  # ALERT
        }
        return severity_map.get(level, 200)

    def _severity_to_level(self, severity: int) -> LogLevel:
        """Convert GCP severity to LogLevel."""
        # Find the closest match
        for sev, level in sorted(_SEVERITY_MAP.items(), reverse=True):
            if severity >= sev:
                return level
        return LogLevel.DEBUG

    def _convert_entry(self, entry: Any) -> LogEntry | None:
        """Convert Cloud Logging entry to LogEntry."""
        try:
            # Parse timestamp
            timestamp = datetime.fromtimestamp(
                entry.timestamp.seconds + entry.timestamp.nanos / 1e9,
                tz=UTC,
            )

            # Get severity/level
            level = self._severity_to_level(entry.severity)

            # Get message
            if hasattr(entry, "text_payload") and entry.text_payload:
                message = entry.text_payload
            elif hasattr(entry, "json_payload") and entry.json_payload:
                import json

                message = json.dumps(dict(entry.json_payload))
            else:
                message = str(entry)

            # Get service name
            service_name: str = "unknown"
            if hasattr(entry, "resource") and entry.resource:
                if hasattr(entry.resource, "labels"):
                    labels = dict(entry.resource.labels)
                    service_name = str(
                        labels.get("service_name", labels.get("container_name", labels.get("module_id", "unknown")))
                    )

            # Get trace context
            trace_id = None
            span_id = None

            if hasattr(entry, "trace") and entry.trace:
                # Extract trace ID from projects/PROJECT_ID/traces/TRACE_ID
                parts = entry.trace.split("/")
                if len(parts) >= 4:
                    trace_id = parts[-1]

            if hasattr(entry, "span_id") and entry.span_id:
                span_id = entry.span_id

            # Get attributes from labels
            attributes = {}
            if hasattr(entry, "labels") and entry.labels:
                attributes = dict(entry.labels)

            return LogEntry(
                timestamp=timestamp,
                level=level,
                message=message,
                service_name=service_name,
                trace_id=trace_id,
                span_id=span_id,
                attributes=attributes,
            )

        except Exception as e:
            logger.warning(f"Failed to convert log entry: {e}")
            return None
