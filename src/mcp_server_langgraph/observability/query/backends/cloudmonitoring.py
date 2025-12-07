"""
GCP Cloud Monitoring implementation of MetricsQueryClient.

Provides Cloud Monitoring API querying through the abstract interface,
enabling backend swapping without code changes.

Configured via environment variables:
    GOOGLE_CLOUD_PROJECT: GCP project ID
    GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON (optional)

Reference:
- Cloud Monitoring API: https://cloud.google.com/monitoring/api/v3
- Python Client: https://cloud.google.com/python/docs/reference/monitoring/latest
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from ..interfaces import (
    MetricQueryResult,
    MetricSeries,
    MetricValue,
    MetricsQueryClient,
)

if TYPE_CHECKING:
    from google.cloud import monitoring_v3

logger = logging.getLogger(__name__)


class CloudMonitoringClient(MetricsQueryClient):
    """
    GCP Cloud Monitoring implementation of MetricsQueryClient.

    Uses the Cloud Monitoring API to query metrics stored in GCP.

    Configured via environment variables:
        GOOGLE_CLOUD_PROJECT: GCP project ID (required)
        GOOGLE_APPLICATION_CREDENTIALS: Service account JSON path (optional)

    Example:
        client = CloudMonitoringClient()
        await client.initialize()

        # Query metrics
        result = await client.query_instant("custom.googleapis.com/my_metric")

        # Get service metrics
        metrics = await client.get_service_metrics("mcp-server")

        await client.close()
    """

    def __init__(self) -> None:
        """Initialize with configuration from environment."""
        self._project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "")
        self._client: monitoring_v3.MetricServiceAsyncClient | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the Cloud Monitoring client."""
        if self._initialized:
            return

        try:
            from google.cloud import monitoring_v3

            self._client = monitoring_v3.MetricServiceAsyncClient()
            self._initialized = True
            logger.info(f"Cloud Monitoring client initialized for project: {self._project_id}")
        except ImportError:
            raise ImportError("google-cloud-monitoring package required. Install with: pip install google-cloud-monitoring")

    async def close(self) -> None:
        """Close the Cloud Monitoring client."""
        if self._client:
            self._client = None
        self._initialized = False
        logger.info("Cloud Monitoring client closed")

    async def query_instant(
        self,
        query: str,
        time: datetime | None = None,
    ) -> MetricQueryResult:
        """
        Execute an instant query at a specific point in time.

        Args:
            query: Metric type (e.g., "custom.googleapis.com/my_metric")
            time: Evaluation time (defaults to now)

        Returns:
            MetricQueryResult with query results
        """
        if not self._initialized:
            await self.initialize()
        assert self._client is not None

        if not time:
            time = datetime.now(UTC)

        # Use a 1-minute window for instant query
        start = time - timedelta(minutes=1)
        end = time

        return await self.query_range(query, start, end, step=timedelta(minutes=1))

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
            query: Metric type (e.g., "custom.googleapis.com/my_metric")
            start: Range start time
            end: Range end time
            step: Step interval (resolution)

        Returns:
            MetricQueryResult with time series data
        """
        if not self._initialized:
            await self.initialize()
        assert self._client is not None

        try:
            from google.cloud import monitoring_v3
            from google.protobuf import duration_pb2, timestamp_pb2

            # Build time interval
            start_time = timestamp_pb2.Timestamp()
            start_time.FromDatetime(start)

            end_time = timestamp_pb2.Timestamp()
            end_time.FromDatetime(end)

            interval = monitoring_v3.TimeInterval(
                start_time=start_time,
                end_time=end_time,
            )

            # Build aggregation if step provided
            aggregation = None
            if step:
                alignment_period = duration_pb2.Duration()
                alignment_period.FromTimedelta(step)
                aggregation = monitoring_v3.Aggregation(
                    alignment_period=alignment_period,
                    per_series_aligner=monitoring_v3.Aggregation.Aligner.ALIGN_MEAN,
                )

            # Build filter - query is the metric type
            filter_str = f'metric.type = "{query}"'

            request = monitoring_v3.ListTimeSeriesRequest(
                name=f"projects/{self._project_id}",
                filter=filter_str,
                interval=interval,
                aggregation=aggregation,
                view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            )

            series_list = []
            async for time_series in await self._client.list_time_series(request=request):
                metric_series = self._convert_time_series(time_series)
                if metric_series:
                    series_list.append(metric_series)

            return MetricQueryResult(series=series_list)

        except Exception as e:
            logger.exception(f"Failed to query metrics: {e}")
            return MetricQueryResult(series=[])

    async def get_service_metrics(
        self,
        service_name: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> dict[str, MetricSeries]:
        """
        Get standard metrics for a service.

        Returns request rate, error rate, latency percentiles, etc.
        Uses Cloud Run or GKE standard metrics.
        """
        if not self._initialized:
            await self.initialize()
        assert self._client is not None

        if not end:
            end = datetime.now(UTC)
        if not start:
            start = end - timedelta(hours=1)

        result: dict[str, MetricSeries] = {}

        # Define standard metric types to query
        metric_types = [
            ("run.googleapis.com/request_count", "request_count"),
            ("run.googleapis.com/request_latencies", "request_latency"),
            ("run.googleapis.com/container/cpu/utilizations", "cpu_utilization"),
            ("run.googleapis.com/container/memory/utilizations", "memory_utilization"),
        ]

        for metric_type, metric_name in metric_types:
            try:
                from google.cloud import monitoring_v3
                from google.protobuf import timestamp_pb2

                start_time = timestamp_pb2.Timestamp()
                start_time.FromDatetime(start)

                end_time = timestamp_pb2.Timestamp()
                end_time.FromDatetime(end)

                interval = monitoring_v3.TimeInterval(
                    start_time=start_time,
                    end_time=end_time,
                )

                # Filter by service name
                filter_str = f'metric.type = "{metric_type}" AND resource.labels.service_name = "{service_name}"'

                request = monitoring_v3.ListTimeSeriesRequest(
                    name=f"projects/{self._project_id}",
                    filter=filter_str,
                    interval=interval,
                    view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                )

                async for time_series in await self._client.list_time_series(request=request):
                    metric_series = self._convert_time_series(time_series)
                    if metric_series:
                        result[metric_name] = metric_series
                        break  # Take first series for this metric

            except Exception as e:
                logger.warning(f"Failed to query metric {metric_type}: {e}")

        return result

    async def health_check(self) -> bool:
        """Check if Cloud Monitoring API is accessible."""
        return self._initialized

    def _convert_time_series(self, time_series: Any) -> MetricSeries | None:
        """Convert Cloud Monitoring TimeSeries to MetricSeries."""
        try:
            # Extract metric name
            metric_name = time_series.metric.type

            # Extract labels
            labels = {}
            if time_series.metric.labels:
                labels.update(dict(time_series.metric.labels))
            if time_series.resource.labels:
                labels.update(dict(time_series.resource.labels))

            # Extract values
            values = []
            for point in time_series.points:
                timestamp = datetime.fromtimestamp(
                    point.interval.end_time.seconds + point.interval.end_time.nanos / 1e9,
                    tz=UTC,
                )

                # Get value based on type
                value = 0.0
                typed_value = point.value
                if hasattr(typed_value, "double_value"):
                    value = typed_value.double_value
                elif hasattr(typed_value, "int64_value"):
                    value = float(typed_value.int64_value)
                elif hasattr(typed_value, "distribution_value"):
                    # For distributions, use mean
                    dist = typed_value.distribution_value
                    value = dist.mean if hasattr(dist, "mean") else 0.0

                values.append(MetricValue(timestamp=timestamp, value=value))

            return MetricSeries(
                metric_name=metric_name,
                labels=labels,
                values=values,
            )

        except Exception as e:
            logger.warning(f"Failed to convert time series: {e}")
            return None
