"""
Unit tests for GCP observability query backends.

Tests GCP Cloud Trace, Cloud Logging, and Cloud Monitoring backends.
These use mocking since GCP libraries require actual credentials.

Follows TDD: These tests are written FIRST before implementation (RED phase).
Follows xdist memory safety patterns per MEMORY_SAFETY_GUIDELINES.md.
"""

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Module-level marker for pytest
pytestmark = pytest.mark.unit


def _create_mock_trace_v1() -> MagicMock:
    """Create a mock google.cloud.trace_v1 module."""
    mock_trace = MagicMock()
    mock_trace.TraceServiceAsyncClient = MagicMock
    mock_trace.GetTraceRequest = MagicMock
    mock_trace.ListTracesRequest = MagicMock
    return mock_trace


def _create_mock_logging_v2() -> MagicMock:
    """Create a mock google.cloud.logging_v2 module."""
    mock_logging = MagicMock()
    mock_logging.LoggingServiceV2AsyncClient = MagicMock
    mock_logging.ListLogEntriesRequest = MagicMock
    return mock_logging


def _create_mock_monitoring_v3() -> MagicMock:
    """Create a mock google.cloud.monitoring_v3 module."""
    mock_monitoring = MagicMock()
    mock_monitoring.MetricServiceAsyncClient = MagicMock
    mock_monitoring.TimeInterval = MagicMock
    mock_monitoring.Aggregation = MagicMock()
    mock_monitoring.Aggregation.Aligner = MagicMock()
    mock_monitoring.Aggregation.Aligner.ALIGN_MEAN = 1
    mock_monitoring.ListTimeSeriesRequest = MagicMock
    mock_monitoring.ListTimeSeriesRequest.TimeSeriesView = MagicMock()
    mock_monitoring.ListTimeSeriesRequest.TimeSeriesView.FULL = 1
    return mock_monitoring


def _create_mock_timestamp_pb2() -> MagicMock:
    """Create a mock google.protobuf.timestamp_pb2 module."""
    mock_timestamp = MagicMock()
    mock_timestamp.Timestamp = MagicMock
    return mock_timestamp


def _create_mock_duration_pb2() -> MagicMock:
    """Create a mock google.protobuf.duration_pb2 module."""
    mock_duration = MagicMock()
    mock_duration.Duration = MagicMock
    return mock_duration


@pytest.mark.xdist_group(name="gcp_observability")
class TestCloudTraceClient:
    """Tests for GCP Cloud Trace backend implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_initialize_creates_client(self) -> None:
        """GIVEN CloudTraceClient WHEN initialize() THEN client is created."""
        mock_trace = _create_mock_trace_v1()

        with patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}):
            with patch.dict("sys.modules", {"google.cloud.trace_v1": mock_trace}):
                # Import after patching
                from mcp_server_langgraph.observability.query.backends.cloudtrace import (
                    CloudTraceClient,
                )

                client = CloudTraceClient()
                await client.initialize()

                assert client._initialized is True

    @pytest.mark.asyncio
    async def test_get_trace_returns_trace_info(self) -> None:
        """GIVEN a trace ID WHEN get_trace() THEN returns TraceInfo."""
        mock_trace = _create_mock_trace_v1()
        mock_timestamp = _create_mock_timestamp_pb2()

        # Setup mock response
        mock_client_instance = MagicMock()

        mock_span = MagicMock()
        mock_span.span_id = "span123"
        mock_span.name = "projects/test-project/traces/trace123/spans/span123"
        mock_span.display_name = MagicMock(value="test-operation")
        mock_span.start_time = MagicMock(seconds=int(datetime.now(UTC).timestamp()), nanos=0)
        mock_span.end_time = MagicMock(seconds=int(datetime.now(UTC).timestamp()) + 1, nanos=0)
        mock_span.parent_span_id = ""
        mock_span.status = MagicMock(code=0)
        mock_span.attributes = MagicMock(attribute_map={})
        mock_span.labels = {}

        mock_trace_response = MagicMock()
        mock_trace_response.spans = [mock_span]

        # Set up client to return AsyncMock for async method
        mock_client_instance.get_trace = AsyncMock(return_value=mock_trace_response)

        # CRITICAL: Make TraceServiceAsyncClient() return our mock instance
        mock_trace.TraceServiceAsyncClient = MagicMock(return_value=mock_client_instance)

        with patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}):
            with patch.dict(
                "sys.modules",
                {
                    "google.cloud.trace_v1": mock_trace,
                    "google.protobuf.timestamp_pb2": mock_timestamp,
                },
            ):
                from mcp_server_langgraph.observability.query.backends.cloudtrace import (
                    CloudTraceClient,
                )

                client = CloudTraceClient()
                await client.initialize()

                result = await client.get_trace("trace123")

                assert result is not None
                assert result.trace_id == "trace123"

    @pytest.mark.asyncio
    async def test_health_check_returns_true_when_initialized(self) -> None:
        """GIVEN initialized client WHEN health_check THEN returns True."""
        mock_trace = _create_mock_trace_v1()

        with patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}):
            with patch.dict("sys.modules", {"google.cloud.trace_v1": mock_trace}):
                from mcp_server_langgraph.observability.query.backends.cloudtrace import (
                    CloudTraceClient,
                )

                client = CloudTraceClient()
                await client.initialize()

                result = await client.health_check()

                assert result is True

    @pytest.mark.asyncio
    async def test_close_resets_state(self) -> None:
        """GIVEN initialized client WHEN close() THEN state is reset."""
        mock_trace = _create_mock_trace_v1()

        with patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}):
            with patch.dict("sys.modules", {"google.cloud.trace_v1": mock_trace}):
                from mcp_server_langgraph.observability.query.backends.cloudtrace import (
                    CloudTraceClient,
                )

                client = CloudTraceClient()
                await client.initialize()
                assert client._initialized is True

                await client.close()
                assert client._initialized is False
                assert client._client is None


@pytest.mark.xdist_group(name="gcp_observability")
class TestCloudLoggingClient:
    """Tests for GCP Cloud Logging backend implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_initialize_creates_client(self) -> None:
        """GIVEN CloudLoggingClient WHEN initialize() THEN client is created."""
        mock_logging = _create_mock_logging_v2()

        with patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}):
            with patch.dict("sys.modules", {"google.cloud.logging_v2": mock_logging}):
                from mcp_server_langgraph.observability.query.backends.cloudlogging import (
                    CloudLoggingClient,
                )

                client = CloudLoggingClient()
                await client.initialize()

                assert client._initialized is True

    @pytest.mark.asyncio
    async def test_search_logs_returns_log_entries(self) -> None:
        """GIVEN logs exist WHEN search_logs() THEN returns LogSearchResult."""
        mock_logging = _create_mock_logging_v2()
        mock_client_instance = MagicMock()
        mock_logging.LoggingServiceV2AsyncClient.return_value = mock_client_instance

        # Empty response for simplicity
        async def mock_list_entries(*args, **kwargs):
            return []

        mock_client_instance.list_log_entries = AsyncMock(return_value=[])

        with patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}):
            with patch.dict("sys.modules", {"google.cloud.logging_v2": mock_logging}):
                from mcp_server_langgraph.observability.query.backends.cloudlogging import (
                    CloudLoggingClient,
                )

                client = CloudLoggingClient()
                await client.initialize()

                result = await client.search_logs(query="test")

                assert result.total_count >= 0

    @pytest.mark.asyncio
    async def test_health_check_returns_true_when_initialized(self) -> None:
        """GIVEN initialized client WHEN health_check THEN returns True."""
        mock_logging = _create_mock_logging_v2()

        with patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}):
            with patch.dict("sys.modules", {"google.cloud.logging_v2": mock_logging}):
                from mcp_server_langgraph.observability.query.backends.cloudlogging import (
                    CloudLoggingClient,
                )

                client = CloudLoggingClient()
                await client.initialize()

                result = await client.health_check()

                assert result is True

    @pytest.mark.asyncio
    async def test_close_resets_state(self) -> None:
        """GIVEN initialized client WHEN close() THEN state is reset."""
        mock_logging = _create_mock_logging_v2()

        with patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}):
            with patch.dict("sys.modules", {"google.cloud.logging_v2": mock_logging}):
                from mcp_server_langgraph.observability.query.backends.cloudlogging import (
                    CloudLoggingClient,
                )

                client = CloudLoggingClient()
                await client.initialize()
                assert client._initialized is True

                await client.close()
                assert client._initialized is False
                assert client._client is None


@pytest.mark.xdist_group(name="gcp_observability")
class TestCloudMonitoringClient:
    """Tests for GCP Cloud Monitoring backend implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_initialize_creates_client(self) -> None:
        """GIVEN CloudMonitoringClient WHEN initialize() THEN client is created."""
        mock_monitoring = _create_mock_monitoring_v3()

        with patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}):
            with patch.dict("sys.modules", {"google.cloud.monitoring_v3": mock_monitoring}):
                from mcp_server_langgraph.observability.query.backends.cloudmonitoring import (
                    CloudMonitoringClient,
                )

                client = CloudMonitoringClient()
                await client.initialize()

                assert client._initialized is True

    @pytest.mark.asyncio
    async def test_query_instant_returns_metric_result(self) -> None:
        """GIVEN metric exists WHEN query_instant() THEN returns MetricQueryResult."""
        mock_monitoring = _create_mock_monitoring_v3()
        mock_timestamp = _create_mock_timestamp_pb2()
        mock_duration = _create_mock_duration_pb2()

        mock_client_instance = MagicMock()
        mock_monitoring.MetricServiceAsyncClient.return_value = mock_client_instance

        # Empty response
        async def mock_list_time_series(*args, **kwargs):
            return []

        mock_client_instance.list_time_series = AsyncMock(return_value=[])

        with patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}):
            with patch.dict(
                "sys.modules",
                {
                    "google.cloud.monitoring_v3": mock_monitoring,
                    "google.protobuf.timestamp_pb2": mock_timestamp,
                    "google.protobuf.duration_pb2": mock_duration,
                },
            ):
                from mcp_server_langgraph.observability.query.backends.cloudmonitoring import (
                    CloudMonitoringClient,
                )

                client = CloudMonitoringClient()
                await client.initialize()

                result = await client.query_instant("custom.googleapis.com/test_metric")

                assert result.series == []

    @pytest.mark.asyncio
    async def test_health_check_returns_true_when_initialized(self) -> None:
        """GIVEN initialized client WHEN health_check THEN returns True."""
        mock_monitoring = _create_mock_monitoring_v3()

        with patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}):
            with patch.dict("sys.modules", {"google.cloud.monitoring_v3": mock_monitoring}):
                from mcp_server_langgraph.observability.query.backends.cloudmonitoring import (
                    CloudMonitoringClient,
                )

                client = CloudMonitoringClient()
                await client.initialize()

                result = await client.health_check()

                assert result is True

    @pytest.mark.asyncio
    async def test_close_resets_state(self) -> None:
        """GIVEN initialized client WHEN close() THEN state is reset."""
        mock_monitoring = _create_mock_monitoring_v3()

        with patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}):
            with patch.dict("sys.modules", {"google.cloud.monitoring_v3": mock_monitoring}):
                from mcp_server_langgraph.observability.query.backends.cloudmonitoring import (
                    CloudMonitoringClient,
                )

                client = CloudMonitoringClient()
                await client.initialize()
                assert client._initialized is True

                await client.close()
                assert client._initialized is False
                assert client._client is None
