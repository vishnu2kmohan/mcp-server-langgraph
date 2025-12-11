"""
Observability Query Abstraction Layer.

Provides vendor-neutral interfaces for querying telemetry data that has been
exported via OTLP and stored in various backends.

Architecture:
    Applications → OTLP Export → [Tempo/Jaeger/etc] → Query Interface → Applications

IMPORTANT: OTLP (OpenTelemetry Protocol) is PUSH-only for exporting telemetry.
This module provides the QUERY side - reading persisted data back.

The abstraction allows swapping backends without changing application code:
    - TracingQueryClient: Query traces (Tempo, Jaeger, Datadog, etc.)
    - LoggingQueryClient: Query logs (Loki, Elasticsearch, CloudWatch, etc.)
    - MetricsQueryClient: Query metrics (Prometheus, Mimir, Datadog, etc.)

Usage:
    from mcp_server_langgraph.observability.query import get_tracing_client

    # Application code uses abstract interface
    client = get_tracing_client()  # Returns appropriate implementation
    traces = await client.search_traces(service="mcp-server", limit=10)

    # Backend can be configured via environment variables:
    # OBSERVABILITY_TRACING_BACKEND=tempo|jaeger|datadog
    # OBSERVABILITY_LOGGING_BACKEND=loki|elasticsearch|cloudwatch
    # OBSERVABILITY_METRICS_BACKEND=prometheus|mimir|datadog
"""

from .interfaces import (
    LogEntry,
    LoggingQueryClient,
    MetricsQueryClient,
    MetricValue,
    SpanInfo,
    TraceInfo,
    TracingQueryClient,
)
from .factory import (
    get_tracing_client,
    get_logging_client,
    get_metrics_client,
    init_query_clients,
    close_query_clients,
)

__all__ = [
    # Interfaces
    "TracingQueryClient",
    "LoggingQueryClient",
    "MetricsQueryClient",
    # Data classes
    "TraceInfo",
    "SpanInfo",
    "LogEntry",
    "MetricValue",
    # Factory functions
    "get_tracing_client",
    "get_logging_client",
    "get_metrics_client",
    "init_query_clients",
    "close_query_clients",
]
