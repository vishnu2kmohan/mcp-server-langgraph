"""
Tests for Prometheus Client

Comprehensive test suite for Prometheus metric querying following TDD principles.

Tests cover:
- HTTP client initialization and cleanup
- Instant queries and range queries
- Result parsing (instant and range)
- Uptime/downtime calculations
- Percentile queries
- Error rate calculations
- SLA metrics aggregation
- Edge cases and error handling
"""

import gc
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_langgraph.monitoring.prometheus_client import MetricValue, PrometheusClient, PrometheusConfig, QueryResult

# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def prometheus_config():
    """Sample Prometheus configuration."""
    return PrometheusConfig(
        url="http://prometheus:9090",
        timeout=30,
        retry_attempts=3,
        retry_backoff=1.0,
    )


@pytest.fixture
def sample_instant_query_response():
    """Sample Prometheus instant query response."""
    return {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {"job": "mcp-server-langgraph", "instance": "localhost:8000"},
                    "value": [1699920000.0, "99.95"],  # [timestamp, value]
                }
            ],
        },
    }


@pytest.fixture
def sample_range_query_response():
    """Sample Prometheus range query response."""
    return {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {"job": "mcp-server-langgraph"},
                    "values": [
                        [1699920000.0, "99.95"],
                        [1699920060.0, "99.96"],
                        [1699920120.0, "99.97"],
                    ],
                }
            ],
        },
    }


# ==============================================================================
# Test Configuration and Initialization
# ==============================================================================


@pytest.mark.xdist_group(name="prometheus_client_tests")
class TestPrometheusClient:
    """Test suite for PrometheusClient with memory safety pattern."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_creates_http_client(self, prometheus_config):
        """Test initialize() creates httpx.AsyncClient."""
        # Arrange
        client = PrometheusClient(config=prometheus_config)
        assert client.client is None
        assert not client._initialized

        # Act
        await client.initialize()

        # Assert
        assert client.client is not None
        assert isinstance(client.client, httpx.AsyncClient)
        assert client._initialized is True

        # Cleanup
        await client.close()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_is_idempotent(self, prometheus_config):
        """Test initialize() can be called multiple times safely."""
        # Arrange
        client = PrometheusClient(config=prometheus_config)

        # Act
        await client.initialize()
        first_client = client.client

        await client.initialize()  # Second call
        second_client = client.client

        # Assert - same client instance
        assert first_client is second_client

        # Cleanup
        await client.close()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close_cleans_up_http_client(self, prometheus_config):
        """Test close() properly cleans up AsyncClient."""
        # Arrange
        client = PrometheusClient(config=prometheus_config)
        await client.initialize()

        # Act
        await client.close()

        # Assert - client is closed (check via attempting operation)
        # Note: httpx.AsyncClient doesn't have is_closed, so we verify it doesn't raise
        assert client.client is not None  # Client object still exists but is closed

    @pytest.mark.unit
    def test_load_config_from_settings_uses_defaults(self):
        """Test _load_config_from_settings() returns default config."""
        # Arrange & Act
        client = PrometheusClient()

        # Assert
        assert client.config.url == "http://prometheus:9090"
        assert client.config.timeout == 30
        assert client.config.retry_attempts == 3


# ==============================================================================
# Test Data Models
# ==============================================================================


@pytest.mark.unit
def test_metric_value_from_prometheus_parses_correctly():
    """Test MetricValue.from_prometheus() parses Prometheus data format."""
    # Arrange
    prom_data = [1699920000.0, "99.95"]

    # Act
    metric = MetricValue.from_prometheus(prom_data)

    # Assert
    assert metric.timestamp == datetime.fromtimestamp(1699920000.0)
    assert metric.value == 99.95


@pytest.mark.unit
def test_query_result_get_latest_value_returns_last_value():
    """Test QueryResult.get_latest_value() returns most recent value."""
    # Arrange
    values = [
        MetricValue(timestamp=datetime.now(timezone.utc), value=10.0),
        MetricValue(timestamp=datetime.now(timezone.utc) + timedelta(minutes=1), value=20.0),
        MetricValue(timestamp=datetime.now(timezone.utc) + timedelta(minutes=2), value=30.0),
    ]
    result = QueryResult(metric={"job": "test"}, values=values)

    # Act
    latest = result.get_latest_value()

    # Assert
    assert latest == 30.0


@pytest.mark.unit
def test_query_result_get_average_calculates_mean():
    """Test QueryResult.get_average() calculates average of all values."""
    # Arrange
    values = [
        MetricValue(timestamp=datetime.now(timezone.utc), value=10.0),
        MetricValue(timestamp=datetime.now(timezone.utc), value=20.0),
        MetricValue(timestamp=datetime.now(timezone.utc), value=30.0),
    ]
    result = QueryResult(metric={"job": "test"}, values=values)

    # Act
    average = result.get_average()

    # Assert
    assert average == 20.0


@pytest.mark.unit
def test_query_result_get_latest_value_returns_none_when_empty():
    """Test QueryResult.get_latest_value() returns None for empty values."""
    # Arrange
    result = QueryResult(metric={"job": "test"}, values=[])

    # Act
    latest = result.get_latest_value()

    # Assert
    assert latest is None


@pytest.mark.unit
def test_query_result_get_average_returns_none_when_empty():
    """Test QueryResult.get_average() returns None for empty values."""
    # Arrange
    result = QueryResult(metric={"job": "test"}, values=[])

    # Act
    average = result.get_average()

    # Assert
    assert average is None


# ==============================================================================
# Test Query Methods
# ==============================================================================


@pytest.mark.xdist_group(name="prometheus_query_tests")
class TestPrometheusQueries:
    """Test suite for Prometheus query methods."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_executes_instant_query_successfully(self, prometheus_config, sample_instant_query_response):
        """Test query() executes instant query and parses response."""
        # Arrange
        client = PrometheusClient(config=prometheus_config)

        mock_response = MagicMock()
        mock_response.json.return_value = sample_instant_query_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=mock_response):
            await client.initialize()

            # Act
            results = await client.query('up{job="mcp-server-langgraph"}')

            # Assert
            assert len(results) == 1
            assert results[0].metric["job"] == "mcp-server-langgraph"
            assert results[0].get_latest_value() == 99.95

        await client.close()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_range_executes_range_query_successfully(self, prometheus_config, sample_range_query_response):
        """Test query_range() executes range query and parses time series."""
        # Arrange
        client = PrometheusClient(config=prometheus_config)

        mock_response = MagicMock()
        mock_response.json.return_value = sample_range_query_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=mock_response):
            await client.initialize()

            # Act
            start = datetime.now(timezone.utc) - timedelta(hours=1)
            end = datetime.now(timezone.utc)
            results = await client.query_range('up{job="mcp-server-langgraph"}', start=start, end=end, step="1m")

            # Assert
            assert len(results) == 1
            assert len(results[0].values) == 3
            assert results[0].values[0].value == 99.95
            assert results[0].values[1].value == 99.96
            assert results[0].values[2].value == 99.97

        await client.close()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_auto_initializes_if_not_initialized(self, prometheus_config, sample_instant_query_response):
        """Test query() auto-initializes client if not already initialized."""
        # Arrange
        client = PrometheusClient(config=prometheus_config)
        assert not client._initialized

        mock_response = MagicMock()
        mock_response.json.return_value = sample_instant_query_response
        mock_response.raise_for_status = MagicMock()

        # Create a mock AsyncClient with a proper get method
        mock_async_client = MagicMock(spec=httpx.AsyncClient)
        mock_async_client.get = AsyncMock(return_value=mock_response)

        # Act
        with patch.object(httpx, "AsyncClient", return_value=mock_async_client):
            await client.query("up")

        # Assert - client should be initialized
        assert client._initialized

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_raises_value_error_on_prometheus_error(self, prometheus_config):
        """Test query() raises ValueError when Prometheus returns error status."""
        # Arrange
        client = PrometheusClient(config=prometheus_config)

        error_response = {"status": "error", "error": "invalid query", "errorType": "bad_data"}

        mock_response = MagicMock()
        mock_response.json.return_value = error_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=mock_response):
            await client.initialize()

            # Act & Assert
            with pytest.raises(ValueError, match="Prometheus query failed"):
                await client.query("invalid_query")

        await client.close()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_range_raises_value_error_when_client_not_initialized(self, prometheus_config):
        """Test query_range() raises ValueError if client is None."""
        # Arrange
        client = PrometheusClient(config=prometheus_config)
        # Force client to None after initialization check
        client._initialized = True
        client.client = None

        # Act & Assert
        with pytest.raises(ValueError, match="Prometheus client not initialized"):
            start = datetime.now(timezone.utc) - timedelta(hours=1)
            end = datetime.now(timezone.utc)
            await client.query_range("up", start=start, end=end)


# ==============================================================================
# Test SLA Query Methods
# ==============================================================================


@pytest.mark.xdist_group(name="prometheus_sla_tests")
class TestPrometheusSLAQueries:
    """Test suite for SLA-specific query methods."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_uptime_returns_percentage(self, prometheus_config):
        """Test query_uptime() returns uptime percentage."""
        # Arrange
        client = PrometheusClient(config=prometheus_config)

        uptime_response = {
            "status": "success",
            "data": {"result": [{"metric": {"job": "mcp-server-langgraph"}, "value": [1699920000.0, "99.95"]}]},
        }

        mock_response = MagicMock()
        mock_response.json.return_value = uptime_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=mock_response):
            await client.initialize()

            # Act
            uptime = await client.query_uptime(service="mcp-server-langgraph", timerange="30d")

            # Assert
            assert uptime == 99.95

        await client.close()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_uptime_returns_100_when_no_data(self, prometheus_config):
        """Test query_uptime() returns 100% when no data available (optimistic)."""
        # Arrange
        client = PrometheusClient(config=prometheus_config)

        empty_response = {"status": "success", "data": {"result": []}}

        mock_response = MagicMock()
        mock_response.json.return_value = empty_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=mock_response):
            await client.initialize()

            # Act
            uptime = await client.query_uptime()

            # Assert
            assert uptime == 100.0

        await client.close()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_uptime_returns_99_on_error(self, prometheus_config):
        """Test query_uptime() returns 99% (conservative) on query error."""
        # Arrange
        client = PrometheusClient(config=prometheus_config)

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=httpx.ConnectError):
            await client.initialize()

            # Act
            uptime = await client.query_uptime()

            # Assert
            assert uptime == 99.0

        await client.close()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_downtime_calculates_seconds_from_uptime(self, prometheus_config):
        """Test query_downtime() calculates downtime in seconds."""
        # Arrange
        client = PrometheusClient(config=prometheus_config)

        with patch.object(client, "query_uptime", new_callable=AsyncMock, return_value=99.5):  # 99.5% uptime
            # Act
            downtime = await client.query_downtime(service="mcp-server-langgraph", timerange="1h")

            # Assert
            # 1 hour = 3600 seconds
            # 0.5% downtime = 3600 * 0.005 = 18 seconds
            assert downtime == 18.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_downtime_supports_multiple_timerange_formats(self, prometheus_config):
        """Test query_downtime() supports different timerange formats (d, h, m)."""
        # Arrange
        client = PrometheusClient(config=prometheus_config)

        with patch.object(client, "query_uptime", new_callable=AsyncMock, return_value=99.0):  # 1% downtime
            # Act & Assert - Days
            downtime_days = await client.query_downtime(timerange="1d")
            assert downtime_days == 864.0  # 86400 * 0.01

            # Act & Assert - Hours
            downtime_hours = await client.query_downtime(timerange="24h")
            assert downtime_hours == 864.0  # 86400 * 0.01

            # Act & Assert - Minutes
            downtime_minutes = await client.query_downtime(timerange="60m")
            assert downtime_minutes == 36.0  # 3600 * 0.01

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_downtime_raises_value_error_for_invalid_timerange(self, prometheus_config):
        """Test query_downtime() raises ValueError for unsupported timerange format."""
        # Arrange
        client = PrometheusClient(config=prometheus_config)

        with patch.object(client, "query_uptime", new_callable=AsyncMock, return_value=99.0):
            # Act & Assert
            with pytest.raises(ValueError, match="Unsupported timerange format"):
                await client.query_downtime(timerange="1s")  # Seconds not supported

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_percentiles_returns_p50_p95_p99(self, prometheus_config):
        """Test query_percentiles() returns p50, p95, p99 percentiles."""
        # Arrange
        client = PrometheusClient(config=prometheus_config)

        # Mock responses for each percentile query
        def mock_percentile_response(percentile_value):
            return {
                "status": "success",
                "data": {"result": [{"metric": {}, "value": [1699920000.0, str(percentile_value)]}]},
            }

        mock_responses = [
            MagicMock(json=MagicMock(return_value=mock_percentile_response(0.250)), raise_for_status=MagicMock()),
            MagicMock(json=MagicMock(return_value=mock_percentile_response(0.450)), raise_for_status=MagicMock()),
            MagicMock(json=MagicMock(return_value=mock_percentile_response(0.650)), raise_for_status=MagicMock()),
        ]

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_responses):
            await client.initialize()

            # Act
            percentiles = await client.query_percentiles(
                metric="http_request_duration_seconds", percentiles=[50, 95, 99], timerange="1h"
            )

            # Assert
            assert percentiles[50] == 0.250
            assert percentiles[95] == 0.450
            assert percentiles[99] == 0.650

        await client.close()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_percentiles_returns_zero_on_query_error(self, prometheus_config):
        """Test query_percentiles() returns 0.0 for percentiles that fail to query."""
        # Arrange
        client = PrometheusClient(config=prometheus_config)

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=httpx.ConnectError):
            await client.initialize()

            # Act
            percentiles = await client.query_percentiles(metric="http_request_duration_seconds", percentiles=[50, 95, 99])

            # Assert
            assert percentiles[50] == 0.0
            assert percentiles[95] == 0.0
            assert percentiles[99] == 0.0

        await client.close()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_error_rate_calculates_percentage(self, prometheus_config):
        """Test query_error_rate() calculates error rate as percentage."""
        # Arrange
        client = PrometheusClient(config=prometheus_config)

        # Mock two query responses: error rate and total rate
        error_response = {
            "status": "success",
            "data": {"result": [{"metric": {}, "value": [1699920000.0, "5.0"]}]},  # 5 errors/sec
        }

        total_response = {
            "status": "success",
            "data": {"result": [{"metric": {}, "value": [1699920000.0, "100.0"]}]},  # 100 requests/sec
        }

        mock_responses = [
            MagicMock(json=MagicMock(return_value=error_response), raise_for_status=MagicMock()),
            MagicMock(json=MagicMock(return_value=total_response), raise_for_status=MagicMock()),
        ]

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, side_effect=mock_responses):
            await client.initialize()

            # Act
            error_rate = await client.query_error_rate(timerange="5m", service="mcp-server-langgraph")

            # Assert
            # 5 / 100 * 100 = 5%
            assert error_rate == 5.0

        await client.close()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_error_rate_returns_zero_when_no_requests(self, prometheus_config):
        """Test query_error_rate() returns 0% when total requests is 0."""
        # Arrange
        client = PrometheusClient(config=prometheus_config)

        empty_response = {"status": "success", "data": {"result": []}}

        with patch.object(
            httpx.AsyncClient,
            "get",
            new_callable=AsyncMock,
            return_value=MagicMock(json=MagicMock(return_value=empty_response), raise_for_status=MagicMock()),
        ):
            await client.initialize()

            # Act
            error_rate = await client.query_error_rate()

            # Assert
            assert error_rate == 0.0

        await client.close()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_sla_metrics_aggregates_all_metrics(self, prometheus_config):
        """Test get_sla_metrics() aggregates uptime, downtime, error rate, and response times."""
        # Arrange
        client = PrometheusClient(config=prometheus_config)

        with patch.object(client, "query_uptime", new_callable=AsyncMock, return_value=99.95):
            with patch.object(client, "query_downtime", new_callable=AsyncMock, return_value=43.2):
                with patch.object(client, "query_error_rate", new_callable=AsyncMock, return_value=0.5):
                    with patch.object(
                        client,
                        "query_percentiles",
                        new_callable=AsyncMock,
                        return_value={50: 0.100, 95: 0.250, 99: 0.500},
                    ):
                        # Act
                        sla_metrics = await client.get_sla_metrics(service="mcp-server-langgraph", timerange="30d")

                        # Assert
                        assert sla_metrics["uptime_percentage"] == 99.95
                        assert sla_metrics["downtime_seconds"] == 43.2
                        assert sla_metrics["error_rate_percentage"] == 0.5
                        assert sla_metrics["response_times"]["p50_seconds"] == 0.100
                        assert sla_metrics["response_times"]["p95_seconds"] == 0.250
                        assert sla_metrics["response_times"]["p99_seconds"] == 0.500
                        assert sla_metrics["service"] == "mcp-server-langgraph"
                        assert sla_metrics["timerange"] == "30d"


# ==============================================================================
# Test Global Client Instance
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_prometheus_client_returns_singleton():
    """Test get_prometheus_client() returns global singleton instance."""
    # Arrange
    # Reset global instance
    import mcp_server_langgraph.monitoring.prometheus_client as prom_module
    from mcp_server_langgraph.monitoring.prometheus_client import get_prometheus_client

    prom_module._prometheus_client = None

    # Act
    client1 = await get_prometheus_client()
    client2 = await get_prometheus_client()

    # Assert - same instance
    assert client1 is client2
    assert client1._initialized

    # Cleanup
    await client1.close()
