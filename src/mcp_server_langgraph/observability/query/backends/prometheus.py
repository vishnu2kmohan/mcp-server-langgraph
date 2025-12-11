"""
Prometheus/Mimir implementation of MetricsQueryClient.

Wraps the existing PrometheusClient to implement the abstract MetricsQueryClient
interface for vendor-neutral metrics querying. Works with both Prometheus and
Grafana Mimir (100% PromQL compatible).

Configured via environment variables:
    PROMETHEUS_URL: Prometheus/Mimir server URL
    MIMIR_URL: Alternative for Mimir (takes precedence)

Reference:
- PromQL: https://prometheus.io/docs/prometheus/latest/querying/basics/
- Mimir API: https://grafana.com/docs/mimir/latest/references/http-api/
"""

import logging
import os
from datetime import datetime, timedelta

from mcp_server_langgraph.monitoring.prometheus_client import (
    MetricValue as PromMetricValue,
    PrometheusClient,
    PrometheusConfig,
    QueryResult,
)

from ..interfaces import (
    MetricQueryResult,
    MetricSeries,
    MetricValue,
    MetricsQueryClient,
)

logger = logging.getLogger(__name__)


def _convert_metric_value(prom_value: PromMetricValue) -> MetricValue:
    """Convert Prometheus MetricValue to interface MetricValue."""
    return MetricValue(
        timestamp=prom_value.timestamp,
        value=prom_value.value,
    )


def _convert_query_result(result: QueryResult) -> MetricSeries:
    """Convert Prometheus QueryResult to interface MetricSeries."""
    # Extract metric name from labels
    metric_name = result.metric.get("__name__", "unknown")

    # Convert labels (exclude __name__)
    labels = {k: v for k, v in result.metric.items() if k != "__name__"}

    return MetricSeries(
        metric_name=metric_name,
        labels=labels,
        values=[_convert_metric_value(v) for v in result.values],
    )


class PrometheusMetricsClient(MetricsQueryClient):
    """
    Prometheus/Mimir implementation of MetricsQueryClient.

    Wraps the existing PrometheusClient to provide the abstract interface.
    Works with both Prometheus and Grafana Mimir.

    Configured via environment variables:
        PROMETHEUS_URL: Prometheus server URL (default: http://prometheus:9090)
        MIMIR_URL: Mimir server URL (takes precedence if set)

    Example:
        client = PrometheusMetricsClient()
        await client.initialize()

        # Query metrics
        result = await client.query_instant("http_requests_total")

        # Get service metrics
        metrics = await client.get_service_metrics("mcp-server")

        await client.close()
    """

    def __init__(self) -> None:
        """Initialize with configuration from environment."""
        # Mimir URL takes precedence
        mimir_url = os.getenv("MIMIR_URL")
        prometheus_url = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")

        # Use Mimir if available (Prometheus-compatible endpoint), otherwise Prometheus
        url = f"{mimir_url}/prometheus" if mimir_url else prometheus_url

        timeout = int(os.getenv("PROMETHEUS_TIMEOUT", "30"))

        config = PrometheusConfig(url=url, timeout=timeout)
        self._client = PrometheusClient(config=config)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the Prometheus client."""
        await self._client.initialize()
        self._initialized = True
        logger.info("Prometheus/Mimir metrics client initialized")

    async def close(self) -> None:
        """Close the Prometheus client."""
        await self._client.close()
        self._initialized = False
        logger.info("Prometheus/Mimir metrics client closed")

    async def query_instant(
        self,
        query: str,
        time: datetime | None = None,
    ) -> MetricQueryResult:
        """
        Execute an instant query at a specific point in time.

        Args:
            query: PromQL query string
            time: Evaluation time (defaults to now)

        Returns:
            MetricQueryResult with query results
        """
        results = await self._client.query(query, time=time)

        series = [_convert_query_result(r) for r in results]
        return MetricQueryResult(series=series)

    async def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        step: timedelta | None = None,
    ) -> MetricQueryResult:
        """
        Execute a range query over a time period.

        Args:
            query: PromQL query string
            start: Range start time
            end: Range end time
            step: Step interval (resolution), defaults to 1 minute

        Returns:
            MetricQueryResult with time series data
        """
        # Convert step to string format
        if step is None:
            step_str = "1m"
        else:
            total_seconds = int(step.total_seconds())
            if total_seconds >= 3600:
                step_str = f"{total_seconds // 3600}h"
            elif total_seconds >= 60:
                step_str = f"{total_seconds // 60}m"
            else:
                step_str = f"{total_seconds}s"

        results = await self._client.query_range(
            promql=query,
            start=start,
            end=end,
            step=step_str,
        )

        series = [_convert_query_result(r) for r in results]
        return MetricQueryResult(series=series)

    async def get_service_metrics(
        self,
        service_name: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> dict[str, MetricSeries]:
        """
        Get standard metrics for a service.

        Returns request rate, error rate, latency percentiles, etc.
        """
        # Use the existing SLA metrics method
        sla_metrics = await self._client.get_sla_metrics(
            service=service_name,
            timerange="1h",  # Default to last hour
        )

        result: dict[str, MetricSeries] = {}

        # Convert SLA metrics to MetricSeries
        now = start or end or datetime.now()

        # Uptime
        result["uptime_percentage"] = MetricSeries(
            metric_name="uptime_percentage",
            labels={"service": service_name},
            values=[
                MetricValue(
                    timestamp=now,
                    value=sla_metrics["uptime_percentage"],
                )
            ],
        )

        # Error rate
        result["error_rate_percentage"] = MetricSeries(
            metric_name="error_rate_percentage",
            labels={"service": service_name},
            values=[
                MetricValue(
                    timestamp=now,
                    value=sla_metrics["error_rate_percentage"],
                )
            ],
        )

        # Response time percentiles
        response_times = sla_metrics.get("response_times", {})
        for percentile, value in response_times.items():
            result[f"response_time_{percentile}"] = MetricSeries(
                metric_name=f"response_time_{percentile}",
                labels={"service": service_name},
                values=[MetricValue(timestamp=now, value=value)],
            )

        return result

    async def health_check(self) -> bool:
        """Check if Prometheus/Mimir is healthy."""
        if not self._initialized:
            await self.initialize()

        try:
            # Simple query to verify connectivity
            await self._client.query("up")
            return True
        except Exception:
            return False


# Alias for Mimir (same implementation, different name)
MimirMetricsClient = PrometheusMetricsClient
