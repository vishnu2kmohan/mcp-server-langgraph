"""
Factory for creating observability query clients.

Supports configuration-based backend selection via environment variables,
allowing applications to use cloud-managed equivalents without code changes.

Environment Variables:
    OBSERVABILITY_TRACING_BACKEND: tempo|jaeger|xray|cloudtrace|appinsights
    OBSERVABILITY_LOGGING_BACKEND: loki|elasticsearch|cloudwatch|cloudlogging
    OBSERVABILITY_METRICS_BACKEND: prometheus|mimir|cloudwatch|cloudmonitoring|datadog

    # Backend-specific URLs
    TEMPO_URL: http://tempo:3200 (default)
    JAEGER_URL: http://jaeger:16686 (default)
    LOKI_URL: http://loki:3100 (default)
    PROMETHEUS_URL: http://prometheus:9090 (default)
    MIMIR_URL: http://mimir:9009 (default)

Cloud Provider Configuration:
    # AWS X-Ray
    AWS_REGION: us-east-1
    AWS_XRAY_DAEMON_ADDRESS: 127.0.0.1:2000

    # GCP Cloud Trace
    GOOGLE_CLOUD_PROJECT: my-project
    GOOGLE_APPLICATION_CREDENTIALS: /path/to/credentials.json

    # Azure Application Insights
    APPLICATIONINSIGHTS_CONNECTION_STRING: InstrumentationKey=...

Example:
    # Development with Grafana stack
    export OBSERVABILITY_TRACING_BACKEND=tempo
    export TEMPO_URL=http://localhost:3200

    # Production with GCP
    export OBSERVABILITY_TRACING_BACKEND=cloudtrace
    export GOOGLE_CLOUD_PROJECT=my-prod-project
"""

import logging
import os
from enum import Enum
from typing import TypeVar

from .interfaces import (
    LoggingQueryClient,
    MetricsQueryClient,
    TracingQueryClient,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TracingBackend(str, Enum):
    """Supported tracing backends."""

    TEMPO = "tempo"
    JAEGER = "jaeger"
    XRAY = "xray"  # AWS X-Ray
    CLOUDTRACE = "cloudtrace"  # GCP Cloud Trace
    APPINSIGHTS = "appinsights"  # Azure Application Insights
    STUB = "stub"  # In-memory stub for testing


class LoggingBackend(str, Enum):
    """Supported logging backends."""

    LOKI = "loki"
    ELASTICSEARCH = "elasticsearch"
    CLOUDWATCH = "cloudwatch"  # AWS CloudWatch Logs
    CLOUDLOGGING = "cloudlogging"  # GCP Cloud Logging
    STUB = "stub"  # In-memory stub for testing


class MetricsBackend(str, Enum):
    """Supported metrics backends."""

    PROMETHEUS = "prometheus"
    MIMIR = "mimir"
    CLOUDWATCH = "cloudwatch"  # AWS CloudWatch Metrics
    CLOUDMONITORING = "cloudmonitoring"  # GCP Cloud Monitoring
    DATADOG = "datadog"
    STUB = "stub"  # In-memory stub for testing


# Global client instances
_tracing_client: TracingQueryClient | None = None
_logging_client: LoggingQueryClient | None = None
_metrics_client: MetricsQueryClient | None = None


def _get_tracing_backend() -> TracingBackend:
    """Determine tracing backend from environment."""
    backend = os.getenv("OBSERVABILITY_TRACING_BACKEND", "tempo").lower()
    try:
        return TracingBackend(backend)
    except ValueError:
        logger.warning(f"Unknown tracing backend '{backend}', falling back to tempo")
        return TracingBackend.TEMPO


def _get_logging_backend() -> LoggingBackend:
    """Determine logging backend from environment."""
    backend = os.getenv("OBSERVABILITY_LOGGING_BACKEND", "loki").lower()
    try:
        return LoggingBackend(backend)
    except ValueError:
        logger.warning(f"Unknown logging backend '{backend}', falling back to loki")
        return LoggingBackend.LOKI


def _get_metrics_backend() -> MetricsBackend:
    """Determine metrics backend from environment."""
    backend = os.getenv("OBSERVABILITY_METRICS_BACKEND", "prometheus").lower()
    try:
        return MetricsBackend(backend)
    except ValueError:
        logger.warning(f"Unknown metrics backend '{backend}', falling back to prometheus")
        return MetricsBackend.PROMETHEUS


def _create_tracing_client(backend: TracingBackend) -> TracingQueryClient:
    """Create tracing client for the specified backend."""
    if backend == TracingBackend.TEMPO:
        from .backends.tempo import TempoTracingClient

        return TempoTracingClient()

    elif backend == TracingBackend.JAEGER:
        # TODO: Implement Jaeger backend
        raise NotImplementedError(
            "Jaeger tracing backend not yet implemented. Use OBSERVABILITY_TRACING_BACKEND=tempo or stub instead."
        )

    elif backend == TracingBackend.XRAY:
        # TODO: Implement AWS X-Ray backend
        raise NotImplementedError(
            "AWS X-Ray tracing backend not yet implemented. Use OBSERVABILITY_TRACING_BACKEND=tempo or stub instead."
        )

    elif backend == TracingBackend.CLOUDTRACE:
        from .backends.cloudtrace import CloudTraceClient

        return CloudTraceClient()

    elif backend == TracingBackend.APPINSIGHTS:
        # TODO: Implement Azure Application Insights backend
        raise NotImplementedError(
            "Azure Application Insights backend not yet implemented. Use OBSERVABILITY_TRACING_BACKEND=tempo or stub instead."
        )

    elif backend == TracingBackend.STUB:
        from .backends.stub import StubTracingClient

        return StubTracingClient()

    else:
        raise ValueError(f"Unsupported tracing backend: {backend}")


def _create_logging_client(backend: LoggingBackend) -> LoggingQueryClient:
    """Create logging client for the specified backend."""
    if backend == LoggingBackend.LOKI:
        from .backends.loki import LokiLoggingClient

        return LokiLoggingClient()

    elif backend == LoggingBackend.ELASTICSEARCH:
        # TODO: Implement Elasticsearch backend
        raise NotImplementedError(
            "Elasticsearch logging backend not yet implemented. Use OBSERVABILITY_LOGGING_BACKEND=loki or stub instead."
        )

    elif backend == LoggingBackend.CLOUDWATCH:
        # TODO: Implement AWS CloudWatch Logs backend
        raise NotImplementedError(
            "AWS CloudWatch Logs backend not yet implemented. Use OBSERVABILITY_LOGGING_BACKEND=loki or stub instead."
        )

    elif backend == LoggingBackend.CLOUDLOGGING:
        from .backends.cloudlogging import CloudLoggingClient

        return CloudLoggingClient()

    elif backend == LoggingBackend.STUB:
        from .backends.stub import StubLoggingClient

        return StubLoggingClient()

    else:
        raise ValueError(f"Unsupported logging backend: {backend}")


def _create_metrics_client(backend: MetricsBackend) -> MetricsQueryClient:
    """Create metrics client for the specified backend."""
    if backend == MetricsBackend.PROMETHEUS:
        from .backends.prometheus import PrometheusMetricsClient

        return PrometheusMetricsClient()

    elif backend == MetricsBackend.MIMIR:
        # Mimir uses the same client as Prometheus (100% PromQL compatible)
        from .backends.prometheus import PrometheusMetricsClient

        return PrometheusMetricsClient()

    elif backend == MetricsBackend.CLOUDWATCH:
        # TODO: Implement AWS CloudWatch Metrics backend
        raise NotImplementedError(
            "AWS CloudWatch Metrics backend not yet implemented. Use OBSERVABILITY_METRICS_BACKEND=prometheus or stub instead."
        )

    elif backend == MetricsBackend.CLOUDMONITORING:
        from .backends.cloudmonitoring import CloudMonitoringClient

        return CloudMonitoringClient()

    elif backend == MetricsBackend.DATADOG:
        # TODO: Implement Datadog Metrics backend
        raise NotImplementedError(
            "Datadog Metrics backend not yet implemented. Use OBSERVABILITY_METRICS_BACKEND=prometheus or stub instead."
        )

    elif backend == MetricsBackend.STUB:
        from .backends.stub import StubMetricsClient

        return StubMetricsClient()

    else:
        raise ValueError(f"Unsupported metrics backend: {backend}")


def get_tracing_client() -> TracingQueryClient:
    """
    Get or create the global tracing query client.

    Returns client based on OBSERVABILITY_TRACING_BACKEND environment variable.
    """
    global _tracing_client
    if _tracing_client is None:
        backend = _get_tracing_backend()
        logger.info(f"Creating tracing client for backend: {backend.value}")
        _tracing_client = _create_tracing_client(backend)
    return _tracing_client


def get_logging_client() -> LoggingQueryClient:
    """
    Get or create the global logging query client.

    Returns client based on OBSERVABILITY_LOGGING_BACKEND environment variable.
    """
    global _logging_client
    if _logging_client is None:
        backend = _get_logging_backend()
        logger.info(f"Creating logging client for backend: {backend.value}")
        _logging_client = _create_logging_client(backend)
    return _logging_client


def get_metrics_client() -> MetricsQueryClient:
    """
    Get or create the global metrics query client.

    Returns client based on OBSERVABILITY_METRICS_BACKEND environment variable.
    """
    global _metrics_client
    if _metrics_client is None:
        backend = _get_metrics_backend()
        logger.info(f"Creating metrics client for backend: {backend.value}")
        _metrics_client = _create_metrics_client(backend)
    return _metrics_client


async def init_query_clients() -> None:
    """
    Initialize all query clients based on environment configuration.

    Call this during application startup.
    """
    tracing = get_tracing_client()
    logging_client = get_logging_client()
    metrics = get_metrics_client()

    await tracing.initialize()
    await logging_client.initialize()
    await metrics.initialize()

    logger.info("All observability query clients initialized")


async def close_query_clients() -> None:
    """
    Close all query clients and release resources.

    Call this during application shutdown.
    """
    global _tracing_client, _logging_client, _metrics_client

    if _tracing_client:
        await _tracing_client.close()
        _tracing_client = None

    if _logging_client:
        await _logging_client.close()
        _logging_client = None

    if _metrics_client:
        await _metrics_client.close()
        _metrics_client = None

    logger.info("All observability query clients closed")


async def health_check_all() -> dict[str, bool]:
    """
    Check health of all observability backends.

    Returns:
        Dict mapping backend type to health status
    """
    results = {}

    try:
        tracing = get_tracing_client()
        results["tracing"] = await tracing.health_check()
    except Exception as e:
        logger.exception(f"Tracing health check failed: {e}")
        results["tracing"] = False

    try:
        logging_client = get_logging_client()
        results["logging"] = await logging_client.health_check()
    except Exception as e:
        logger.exception(f"Logging health check failed: {e}")
        results["logging"] = False

    try:
        metrics = get_metrics_client()
        results["metrics"] = await metrics.health_check()
    except Exception as e:
        logger.exception(f"Metrics health check failed: {e}")
        results["metrics"] = False

    return results
