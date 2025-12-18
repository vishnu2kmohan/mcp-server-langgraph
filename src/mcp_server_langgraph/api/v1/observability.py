"""
Observability Router

Provides trace, metrics, logs, and alerts access under /api/v1/observability/*.

This consolidates observability functionality into a unified API.
Backend selection is configurable via environment variables:
    - OBSERVABILITY_TRACING_BACKEND: tempo|jaeger|xray|cloudtrace|appinsights
    - OBSERVABILITY_LOGGING_BACKEND: loki|elasticsearch|cloudwatch|cloudlogging
    - OBSERVABILITY_METRICS_BACKEND: prometheus|mimir|cloudwatch|cloudmonitoring|datadog
    - OBSERVABILITY_ALERTING_BACKEND: grafana|cloudmonitoring|cloudwatch|azuremonitor

Usage:
    GET /api/v1/observability/traces - List traces
    GET /api/v1/observability/traces/{id} - Get a specific trace
    GET /api/v1/observability/metrics - Get metrics summary
    GET /api/v1/observability/logs - List logs
    GET /api/v1/observability/alerts - List alerts
    GET /api/v1/observability/alerts/{id} - Get a specific alert
    GET /api/v1/observability/alerts/rules - List alerting rules
"""

import logging
from typing import TYPE_CHECKING, Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.api.pagination import (
    CursorPaginatedResponse,
    CursorPaginationMetadata,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mcp_server_langgraph.observability.query.interfaces import (
        AlertingQueryClient,
        LoggingQueryClient,
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


class LogEntryResponse(BaseModel):
    """Response model for a log entry."""

    timestamp: str = Field(description="Log timestamp")
    level: str = Field(description="Log level (debug, info, warn, error, fatal)")
    message: str = Field(description="Log message")
    service_name: str = Field(description="Service name")
    trace_id: str | None = Field(default=None, description="Correlated trace ID")
    span_id: str | None = Field(default=None, description="Correlated span ID")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Additional attributes")


class AlertResponse(BaseModel):
    """Response model for an alert."""

    alert_id: str = Field(description="Alert ID/fingerprint")
    name: str = Field(description="Alert name")
    severity: str = Field(description="Severity level (info, warning, error, critical)")
    state: str = Field(description="Alert state (pending, firing, resolved, silenced)")
    message: str = Field(description="Alert message/summary")
    labels: dict[str, str] = Field(default_factory=dict, description="Alert labels")
    annotations: dict[str, str] = Field(default_factory=dict, description="Alert annotations")
    started_at: str | None = Field(default=None, description="Alert start timestamp")
    ended_at: str | None = Field(default=None, description="Alert end timestamp")
    generator_url: str | None = Field(default=None, description="Link to view in monitoring system")


class AlertRuleResponse(BaseModel):
    """Response model for an alerting rule."""

    rule_id: str = Field(description="Rule ID")
    name: str = Field(description="Rule name")
    expression: str = Field(description="Query expression (PromQL, LogQL, etc.)")
    severity: str = Field(description="Default severity level")
    labels: dict[str, str] = Field(default_factory=dict, description="Rule labels")
    annotations: dict[str, str] = Field(default_factory=dict, description="Rule annotations")
    evaluation_interval_seconds: int = Field(description="Evaluation interval in seconds")
    for_duration_seconds: int | None = Field(default=None, description="For duration in seconds")
    enabled: bool = Field(description="Whether rule is enabled")


class SessionMetricsResponse(BaseModel):
    """Response model for session-level aggregated metrics."""

    total_requests: int = Field(description="Total requests in this session")
    total_errors: int = Field(description="Total errors in this session")
    avg_latency_ms: float = Field(description="Average latency in milliseconds")
    p95_latency_ms: float = Field(description="95th percentile latency in milliseconds")


class WorkflowMetricsResponse(BaseModel):
    """Response model for workflow-level aggregated metrics."""

    total_executions: int = Field(description="Total workflow executions")
    total_errors: int = Field(description="Total errors in workflow executions")
    avg_latency_ms: float = Field(description="Average execution latency in milliseconds")
    p95_latency_ms: float = Field(description="95th percentile latency in milliseconds")


class UserMetricsResponse(BaseModel):
    """Response model for user-level aggregated metrics."""

    total_requests: int = Field(description="Total requests by this user")
    total_sessions: int = Field(description="Total unique sessions by this user")
    total_errors: int = Field(description="Total errors for this user")
    avg_latency_ms: float = Field(description="Average latency in milliseconds")


# Service Interface


class ObservabilityService:
    """Interface for observability operations. Implemented by monitoring layer."""

    async def list_traces(
        self,
        cursor: str | None = None,
        limit: int = 20,
        session_id: str | None = None,
        user_id: str | None = None,
        workflow_id: str | None = None,
        project_id: str | None = None,
        organization_id: str | None = None,
        search: str | None = None,
        sort_by: str | None = "start_time",
        sort_order: str | None = "desc",
    ) -> tuple[list[dict[str, Any]], str | None]:
        """List traces with pagination, filtering, search, and sorting.

        Args:
            cursor: Pagination cursor (trace ID to start after)
            limit: Maximum number of traces to return
            session_id: Filter by session ID
            user_id: Filter by user ID
            workflow_id: Filter by workflow ID
            project_id: Filter by project ID
            organization_id: Filter by organization ID (multi-tenant)
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

    async def list_logs(
        self,
        cursor: str | None = None,
        limit: int = 100,
        level: str | None = None,
        search: str | None = None,
        trace_id: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        workflow_id: str | None = None,
        project_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """List logs with pagination and filtering.

        Args:
            cursor: Pagination cursor
            limit: Maximum number of entries to return
            level: Filter by log level (debug, info, warn, error, fatal)
            search: Search in log message
            trace_id: Filter by trace ID
            session_id: Filter by session ID
            user_id: Filter by user ID
            workflow_id: Filter by workflow ID
            project_id: Filter by project ID

        Returns (log_entries, next_cursor).
        """
        raise NotImplementedError

    async def list_alerts(
        self,
        state: str | None = None,
        severity: str | None = None,
        service_name: str | None = None,
        workflow_id: str | None = None,
        project_id: str | None = None,
        limit: int = 100,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """List alerts with filtering.

        Args:
            state: Filter by alert state (pending, firing, resolved, silenced)
            severity: Filter by severity level (info, warning, error, critical)
            service_name: Filter by service name
            workflow_id: Filter by workflow ID
            project_id: Filter by project ID
            limit: Maximum number of alerts to return

        Returns (alerts, next_cursor).
        """
        raise NotImplementedError

    async def get_metrics_by_session(self, session_id: str) -> dict[str, Any]:
        """Get aggregated metrics for a specific session (computed from traces).

        Args:
            session_id: Session ID to get metrics for

        Returns dict with total_requests, total_errors, avg_latency_ms, p95_latency_ms.
        """
        raise NotImplementedError

    async def get_metrics_by_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Get aggregated metrics for a specific workflow.

        Args:
            workflow_id: Workflow ID to get metrics for

        Returns dict with total_executions, total_errors, avg_latency_ms, p95_latency_ms.
        """
        raise NotImplementedError

    async def get_metrics_by_user(self, user_id: str) -> dict[str, Any]:
        """Get aggregated metrics for a specific user.

        Args:
            user_id: User ID to get metrics for

        Returns dict with total_requests, total_sessions, total_errors, avg_latency_ms.
        """
        raise NotImplementedError

    async def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        """Get an alert by ID. Returns None if not found."""
        raise NotImplementedError

    async def list_alert_rules(
        self,
        enabled_only: bool = True,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List configured alerting rules."""
        raise NotImplementedError


class ObservabilityServiceImpl(ObservabilityService):
    """
    Implementation of ObservabilityService that wraps TracingQueryClient, MetricsQueryClient,
    LoggingQueryClient, and AlertingQueryClient.

    Connects the API layer to the observability query layer.
    Handles conversion from TraceInfo/SpanInfo/Alert dataclasses to dict format.
    """

    def __init__(
        self,
        tracing: "TracingQueryClient | None" = None,
        metrics: "MetricsQueryClient | None" = None,
        logging: "LoggingQueryClient | None" = None,
        alerting: "AlertingQueryClient | None" = None,
    ) -> None:
        """
        Initialize with query clients.

        Args:
            tracing: TracingQueryClient instance. If None, uses factory default.
            metrics: MetricsQueryClient instance. If None, uses factory default.
            logging: LoggingQueryClient instance. If None, uses factory default.
            alerting: AlertingQueryClient instance. If None, uses factory default.
        """
        self._tracing = tracing
        self._metrics = metrics
        self._logging = logging
        self._alerting = alerting

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

    @property
    def logging(self) -> "LoggingQueryClient":
        """Get the logging client, lazily initializing if needed."""
        if self._logging is None:
            from mcp_server_langgraph.observability.query.factory import (
                get_logging_client,
            )

            self._logging = get_logging_client()
        return self._logging

    @property
    def alerting(self) -> "AlertingQueryClient":
        """Get the alerting client, lazily initializing if needed."""
        if self._alerting is None:
            from mcp_server_langgraph.observability.query.factory import (
                get_alerting_client,
            )

            self._alerting = get_alerting_client()
        return self._alerting

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
        user_id: str | None = None,
        workflow_id: str | None = None,
        project_id: str | None = None,
        organization_id: str | None = None,
        search: str | None = None,
        sort_by: str | None = "start_time",
        sort_order: str | None = "desc",
    ) -> tuple[list[dict[str, Any]], str | None]:
        """
        List traces with pagination, filtering, search, and sorting.

        Delegates to tracing.search_traces() or tracing.search_by_attribute()
        when entity filters are provided.

        Returns (traces, next_cursor).
        """
        # Build tags dict from entity filters for attribute-based search
        tags: dict[str, str] = {}
        if session_id:
            tags["session_id"] = session_id
        if user_id:
            tags["user_id"] = user_id
        if workflow_id:
            tags["workflow_id"] = workflow_id
        if project_id:
            tags["project_id"] = project_id
        if organization_id:
            tags["organization_id"] = organization_id

        if tags:
            # Use attribute search for entity filtering
            # Pick the first attribute for search_by_attribute
            attr_name, attr_value = next(iter(tags.items()))
            result = await self.tracing.search_by_attribute(
                attribute=attr_name,
                value=attr_value,
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
        except Exception as e:
            logger.debug("Operation failed: %s", e)

        try:
            # Query errors_total
            errors_result = await self.metrics.query_instant("errors_total")
            if errors_result.series:
                val = errors_result.series[0].latest_value
                if val is not None:
                    errors_total = int(val)
        except Exception as e:
            logger.debug("Operation failed: %s", e)

        return {
            "requests_total": requests_total,
            "errors_total": errors_total,
            "latency_p50": latency_p50,
            "latency_p95": latency_p95,
            "latency_p99": latency_p99,
        }

    def _log_entry_to_dict(self, entry: Any) -> dict[str, Any]:
        """Convert LogEntry dataclass to dict matching LogEntryResponse format."""
        return {
            "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
            "level": entry.level.value if hasattr(entry.level, "value") else str(entry.level),
            "message": entry.message,
            "service_name": entry.service_name,
            "trace_id": entry.trace_id,
            "span_id": entry.span_id,
            "attributes": entry.attributes if hasattr(entry, "attributes") else {},
        }

    async def list_logs(
        self,
        cursor: str | None = None,
        limit: int = 100,
        level: str | None = None,
        search: str | None = None,
        trace_id: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        workflow_id: str | None = None,
        project_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """
        List logs with pagination and filtering.

        Delegates to logging.search_logs() or logging.get_logs_for_trace()
        when trace_id is provided.

        Returns (log_entries, next_cursor).
        """
        from mcp_server_langgraph.observability.query.interfaces import LogLevel

        # Convert level string to LogLevel enum if provided
        log_level = None
        if level:
            try:
                log_level = LogLevel(level.lower())
            except ValueError:
                pass  # Invalid level, ignore filter

        if trace_id:
            # Get logs correlated with a specific trace
            result = await self.logging.get_logs_for_trace(trace_id=trace_id)
        elif session_id:
            # Get logs by session_id attribute
            result = await self.logging.get_logs_by_attribute(
                attribute="session_id",
                value=session_id,
                limit=limit,
            )
        elif user_id:
            # Get logs by user_id attribute
            result = await self.logging.get_logs_by_attribute(
                attribute="user_id",
                value=user_id,
                limit=limit,
            )
        elif workflow_id:
            # Get logs by workflow_id attribute
            result = await self.logging.get_logs_by_attribute(
                attribute="workflow_id",
                value=workflow_id,
                limit=limit,
            )
        elif project_id:
            # Get logs by project_id attribute
            result = await self.logging.get_logs_by_attribute(
                attribute="project_id",
                value=project_id,
                limit=limit,
            )
        else:
            # General search
            result = await self.logging.search_logs(
                query=search,
                level=log_level,
                limit=limit,
            )

        # Convert LogEntry objects to dicts
        entries = [self._log_entry_to_dict(e) for e in result.entries]

        return entries, result.next_cursor

    def _alert_to_dict(self, alert: Any) -> dict[str, Any]:
        """Convert Alert dataclass to dict matching AlertResponse format."""
        return {
            "alert_id": alert.alert_id,
            "name": alert.name,
            "severity": alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
            "state": alert.state.value if hasattr(alert.state, "value") else str(alert.state),
            "message": alert.message,
            "labels": alert.labels,
            "annotations": alert.annotations,
            "started_at": alert.started_at.isoformat() if alert.started_at else None,
            "ended_at": alert.ended_at.isoformat() if alert.ended_at else None,
            "generator_url": alert.generator_url,
        }

    def _alert_rule_to_dict(self, rule: Any) -> dict[str, Any]:
        """Convert AlertRule dataclass to dict matching AlertRuleResponse format."""
        return {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "expression": rule.expression,
            "severity": rule.severity.value if hasattr(rule.severity, "value") else str(rule.severity),
            "labels": rule.labels,
            "annotations": rule.annotations,
            "evaluation_interval_seconds": int(rule.evaluation_interval.total_seconds()),
            "for_duration_seconds": int(rule.for_duration.total_seconds()) if rule.for_duration else None,
            "enabled": rule.enabled,
        }

    async def list_alerts(
        self,
        state: str | None = None,
        severity: str | None = None,
        service_name: str | None = None,
        workflow_id: str | None = None,
        project_id: str | None = None,
        limit: int = 100,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """
        List alerts with filtering.

        Delegates to alerting.list_alerts() or alerting.get_alerts_for_service().

        Returns (alerts, next_cursor).
        """
        from mcp_server_langgraph.observability.query.interfaces import AlertSeverity, AlertState

        # Convert string state/severity to enums
        alert_state = None
        if state:
            try:
                alert_state = AlertState(state.lower())
            except ValueError:
                pass

        alert_severity = None
        if severity:
            try:
                alert_severity = AlertSeverity(severity.lower())
            except ValueError:
                pass

        # Build labels dict for entity filtering
        labels: dict[str, str] = {}
        if workflow_id:
            labels["workflow_id"] = workflow_id
        if project_id:
            labels["project_id"] = project_id

        if service_name:
            result = await self.alerting.get_alerts_for_service(
                service_name=service_name,
                limit=limit,
            )
        else:
            result = await self.alerting.list_alerts(
                state=alert_state,
                severity=alert_severity,
                labels=labels if labels else None,
                limit=limit,
            )

        # Convert Alert objects to dicts
        alerts = [self._alert_to_dict(a) for a in result.alerts]

        return alerts, result.next_cursor

    async def get_metrics_by_session(self, session_id: str) -> dict[str, Any]:
        """
        Get aggregated metrics for a specific session (computed from traces).

        Uses Tempo TraceQL to find all traces for this session,
        then aggregates span durations to compute metrics.
        """
        result = await self.tracing.search_by_attribute(
            attribute="session_id",
            value=session_id,
            limit=1000,
        )

        traces = result.traces
        if not traces:
            return {
                "total_requests": 0,
                "total_errors": 0,
                "avg_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
            }

        durations = [t.duration_ms for t in traces if t.duration_ms is not None]
        error_count = sum(1 for t in traces if t.has_errors)

        # Calculate percentile
        p95_latency = 0.0
        if durations:
            sorted_durations = sorted(durations)
            p95_idx = int(len(sorted_durations) * 0.95)
            p95_latency = sorted_durations[min(p95_idx, len(sorted_durations) - 1)]

        return {
            "total_requests": len(traces),
            "total_errors": error_count,
            "avg_latency_ms": sum(durations) / len(durations) if durations else 0.0,
            "p95_latency_ms": p95_latency,
        }

    async def get_metrics_by_workflow(self, workflow_id: str) -> dict[str, Any]:
        """
        Get aggregated metrics for a specific workflow.

        Uses Tempo TraceQL to find all traces for this workflow.
        """
        result = await self.tracing.search_by_attribute(
            attribute="workflow_id",
            value=workflow_id,
            limit=1000,
        )

        traces = result.traces
        if not traces:
            return {
                "total_executions": 0,
                "total_errors": 0,
                "avg_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
            }

        durations = [t.duration_ms for t in traces if t.duration_ms is not None]
        error_count = sum(1 for t in traces if t.has_errors)

        # Calculate percentile
        p95_latency = 0.0
        if durations:
            sorted_durations = sorted(durations)
            p95_idx = int(len(sorted_durations) * 0.95)
            p95_latency = sorted_durations[min(p95_idx, len(sorted_durations) - 1)]

        return {
            "total_executions": len(traces),
            "total_errors": error_count,
            "avg_latency_ms": sum(durations) / len(durations) if durations else 0.0,
            "p95_latency_ms": p95_latency,
        }

    async def get_metrics_by_user(self, user_id: str) -> dict[str, Any]:
        """
        Get aggregated metrics for a specific user.

        Uses Tempo TraceQL to find all traces for this user.
        """
        result = await self.tracing.search_by_attribute(
            attribute="user_id",
            value=user_id,
            limit=1000,
        )

        traces = result.traces
        if not traces:
            return {
                "total_requests": 0,
                "total_sessions": 0,
                "total_errors": 0,
                "avg_latency_ms": 0.0,
            }

        durations = [t.duration_ms for t in traces if t.duration_ms is not None]
        error_count = sum(1 for t in traces if t.has_errors)

        # Count unique sessions from trace attributes
        unique_sessions: set[str] = set()
        for t in traces:
            for span in t.spans:
                if hasattr(span, "attributes") and "session_id" in span.attributes:
                    unique_sessions.add(span.attributes["session_id"])

        return {
            "total_requests": len(traces),
            "total_sessions": len(unique_sessions),
            "total_errors": error_count,
            "avg_latency_ms": sum(durations) / len(durations) if durations else 0.0,
        }

    async def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        """
        Get an alert by ID.

        Returns None if not found.
        """
        alert = await self.alerting.get_alert(alert_id)

        if alert is None:
            return None

        return self._alert_to_dict(alert)

    async def list_alert_rules(
        self,
        enabled_only: bool = True,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        List configured alerting rules.

        Returns list of rule dicts.
        """
        rules = await self.alerting.list_alert_rules(
            enabled_only=enabled_only,
            limit=limit,
        )

        return [self._alert_rule_to_dict(r) for r in rules]


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
    user_id: str | None = Query(default=None, description="Filter by user ID"),
    workflow_id: str | None = Query(default=None, description="Filter by workflow ID"),
    project_id: str | None = Query(default=None, description="Filter by project ID"),
    organization_id: str | None = Query(default=None, description="Filter by organization ID (multi-tenant)"),
    search: str | None = Query(default=None, min_length=1, max_length=500, description="Search in trace name"),
    sort_by: Literal["name", "start_time", "duration_ms"] = Query(default="start_time", description="Field to sort by"),
    sort_order: Literal["asc", "desc"] = Query(default="desc", description="Sort order"),
) -> CursorPaginatedResponse[dict[str, Any]]:
    """
    List traces with cursor-based pagination.

    Supports:
    - Pagination: cursor, limit
    - Filtering: session_id, user_id, workflow_id, project_id, organization_id
    - Search: search (searches trace name)
    - Sorting: sort_by, sort_order

    Filter by entity IDs to get traces for a specific session, user, workflow, project, or organization.
    """
    service = get_observability_service()
    traces, next_cursor = await service.list_traces(
        cursor=cursor,
        limit=limit,
        session_id=session_id,
        user_id=user_id,
        workflow_id=workflow_id,
        project_id=project_id,
        organization_id=organization_id,
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


@observability_router.get("/observability/logs")
async def list_logs(
    cursor: str | None = Query(default=None, description="Pagination cursor"),
    limit: int = Query(default=100, ge=1, le=1000, description="Items per page"),
    level: Literal["debug", "info", "warn", "error", "fatal"] | None = Query(default=None, description="Filter by log level"),
    search: str | None = Query(default=None, min_length=1, max_length=500, description="Search in log message"),
    trace_id: str | None = Query(default=None, description="Filter by correlated trace ID"),
    session_id: str | None = Query(default=None, description="Filter by session ID"),
    user_id: str | None = Query(default=None, description="Filter by user ID"),
    workflow_id: str | None = Query(default=None, description="Filter by workflow ID"),
    project_id: str | None = Query(default=None, description="Filter by project ID"),
) -> CursorPaginatedResponse[dict[str, Any]]:
    """
    List logs with cursor-based pagination.

    Supports:
    - Pagination: cursor, limit
    - Filtering: level, trace_id, session_id, user_id, workflow_id, project_id
    - Search: search (searches log message)

    Use trace_id to get logs correlated with a specific distributed trace.
    Use session_id, user_id, workflow_id, or project_id to filter by entity.
    """
    service = get_observability_service()
    entries, next_cursor = await service.list_logs(
        cursor=cursor,
        limit=limit,
        level=level,
        search=search,
        trace_id=trace_id,
        session_id=session_id,
        user_id=user_id,
        workflow_id=workflow_id,
        project_id=project_id,
    )

    # Build pagination metadata
    has_next = next_cursor is not None
    pagination = CursorPaginationMetadata(
        next_cursor=next_cursor,
        prev_cursor=None,
        has_next=has_next,
        has_prev=cursor is not None,
        count=len(entries),
    )

    return CursorPaginatedResponse(data=entries, pagination=pagination)


@observability_router.get("/observability/alerts")
async def list_alerts(
    state: Literal["pending", "firing", "resolved", "silenced"] | None = Query(
        default=None, description="Filter by alert state"
    ),
    severity: Literal["info", "warning", "error", "critical"] | None = Query(
        default=None, description="Filter by severity level"
    ),
    service_name: str | None = Query(default=None, description="Filter by service name"),
    workflow_id: str | None = Query(default=None, description="Filter by workflow ID"),
    project_id: str | None = Query(default=None, description="Filter by project ID"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum alerts to return"),
) -> CursorPaginatedResponse[dict[str, Any]]:
    """
    List alerts with filtering.

    Supports:
    - Filtering: state, severity, service_name, workflow_id, project_id
    - Limit: max number of alerts to return

    Use service_name to get alerts for a specific service.
    Use workflow_id or project_id to filter by entity.
    """
    service = get_observability_service()
    alerts, next_cursor = await service.list_alerts(
        state=state,
        severity=severity,
        service_name=service_name,
        workflow_id=workflow_id,
        project_id=project_id,
        limit=limit,
    )

    # Build pagination metadata
    has_next = next_cursor is not None
    pagination = CursorPaginationMetadata(
        next_cursor=next_cursor,
        prev_cursor=None,
        has_next=has_next,
        has_prev=False,
        count=len(alerts),
    )

    return CursorPaginatedResponse(data=alerts, pagination=pagination)


@observability_router.get("/observability/alerts/rules")
async def list_alert_rules(
    enabled_only: bool = Query(default=True, description="Only return enabled rules"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum rules to return"),
) -> list[AlertRuleResponse]:
    """
    List configured alerting rules.

    Returns the alerting rules configured in the monitoring system.
    """
    service = get_observability_service()
    rules = await service.list_alert_rules(
        enabled_only=enabled_only,
        limit=limit,
    )

    return [AlertRuleResponse(**r) for r in rules]


@observability_router.get("/observability/alerts/{alert_id}")
async def get_alert(alert_id: str) -> AlertResponse:
    """
    Get a specific alert by ID.

    Returns the alert details including labels, annotations, and timing.
    """
    service = get_observability_service()
    alert = await service.get_alert(alert_id)

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    return AlertResponse(**alert)


# ==============================================================================
# Metrics By Entity Endpoints (Trace-Based Aggregation)
# ==============================================================================


@observability_router.get("/observability/metrics/by-session/{session_id}")
async def get_metrics_by_session(session_id: str) -> SessionMetricsResponse:
    """
    Get aggregated metrics for a specific session.

    Computes metrics from traces associated with this session:
    - total_requests: Total number of traces/requests in the session
    - total_errors: Number of traces with errors
    - avg_latency_ms: Average trace duration in milliseconds
    - p95_latency_ms: 95th percentile trace duration

    This endpoint uses Tempo TraceQL to aggregate spans by session_id attribute.
    """
    service = get_observability_service()
    metrics = await service.get_metrics_by_session(session_id)
    return SessionMetricsResponse(**metrics)


@observability_router.get("/observability/metrics/by-workflow/{workflow_id}")
async def get_metrics_by_workflow(workflow_id: str) -> WorkflowMetricsResponse:
    """
    Get aggregated metrics for a specific workflow.

    Computes metrics from traces associated with this workflow:
    - total_executions: Total number of workflow executions
    - total_errors: Number of executions with errors
    - avg_latency_ms: Average execution latency in milliseconds
    - p95_latency_ms: 95th percentile execution latency

    This endpoint uses Tempo TraceQL to aggregate spans by workflow_id attribute.
    """
    service = get_observability_service()
    metrics = await service.get_metrics_by_workflow(workflow_id)
    return WorkflowMetricsResponse(**metrics)


@observability_router.get("/observability/metrics/by-user/{user_id}")
async def get_metrics_by_user(user_id: str) -> UserMetricsResponse:
    """
    Get aggregated metrics for a specific user.

    Computes metrics from traces associated with this user:
    - total_requests: Total number of traces/requests by this user
    - total_sessions: Number of unique sessions by this user
    - total_errors: Number of traces with errors
    - avg_latency_ms: Average trace duration in milliseconds

    This endpoint uses Tempo TraceQL to aggregate spans by user_id attribute.
    """
    service = get_observability_service()
    metrics = await service.get_metrics_by_user(user_id)
    return UserMetricsResponse(**metrics)
