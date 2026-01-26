"""
Unit tests for LGTM stack backend implementations.

Tests the Tempo (tracing), Loki (logging), and Prometheus/Mimir (metrics)
backend implementations of the abstract query client interfaces.

Follows TDD: These tests are written FIRST before implementation (RED phase).

Reference:
    ADR-0026: Observability Query Backend Abstraction
"""

import gc
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_langgraph.observability.query.interfaces import (
    LogLevel,
    SpanStatusCode,
)


# Module-level markers
pytestmark = [pytest.mark.unit, pytest.mark.observability]


# =============================================================================
# Tempo Tracing Client Tests
# =============================================================================


@pytest.mark.xdist_group(name="lgtm_tempo")
class TestTempoTracingClient:
    """Tests for TempoTracingClient implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_initialize_creates_tempo_client(self) -> None:
        """GIVEN a new TempoTracingClient WHEN initialize() is called THEN _initialized is True."""
        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"TEMPO_URL": "http://localhost:3200"}):
            client = TempoTracingClient()

            # Mock the underlying TempoClient
            client._client = MagicMock()
            client._client.initialize = AsyncMock(return_value=None)  # noqa: async-mock-config

            # WHEN
            await client.initialize()

            # THEN
            assert client._initialized is True
            client._client.initialize.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_releases_resources(self) -> None:
        """GIVEN an initialized client WHEN close() is called THEN resources are released."""
        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"TEMPO_URL": "http://localhost:3200"}):
            client = TempoTracingClient()
            client._client = MagicMock()
            client._client.initialize = AsyncMock(return_value=None)  # noqa: async-mock-config
            client._client.close = AsyncMock(return_value=None)  # noqa: async-mock-config

            await client.initialize()

            # WHEN
            await client.close()

            # THEN
            assert client._initialized is False
            client._client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_trace_converts_tempo_trace_to_interface(self) -> None:
        """GIVEN a trace exists in Tempo WHEN get_trace() is called THEN returns converted TraceInfo."""
        from mcp_server_langgraph.monitoring.tempo_client import (
            SpanInfo as TempoSpanInfo,
            TraceInfo as TempoTraceInfo,
        )
        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"TEMPO_URL": "http://localhost:3200"}):
            client = TempoTracingClient()
            client._initialized = True

            now = datetime.now(UTC)
            tempo_trace = TempoTraceInfo(
                trace_id="abc123def456",
                root_service="mcp-server",
                root_operation="POST /api/chat",
                start_time=now,
                duration_ms=250.5,
                span_count=5,
                error_count=0,
                spans=[
                    TempoSpanInfo(
                        span_id="span-1",
                        trace_id="abc123def456",
                        operation_name="POST /api/chat",
                        service_name="mcp-server",
                        start_time=now,
                        duration_ms=250.5,
                        status_code="OK",
                        parent_span_id=None,
                        attributes={"http.method": "POST"},
                        events=[],
                    )
                ],
            )

            client._client = MagicMock()
            client._client.get_trace = AsyncMock(return_value=tempo_trace)

            # WHEN
            result = await client.get_trace("abc123def456")

            # THEN
            assert result is not None
            assert result.trace_id == "abc123def456"
            assert result.root_service == "mcp-server"
            assert result.root_operation == "POST /api/chat"
            assert result.duration_ms == 250.5
            assert len(result.spans) == 1
            assert result.spans[0].status_code == SpanStatusCode.OK

    @pytest.mark.asyncio
    async def test_get_trace_returns_none_for_missing_trace(self) -> None:
        """GIVEN trace doesn't exist WHEN get_trace() is called THEN returns None."""
        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"TEMPO_URL": "http://localhost:3200"}):
            client = TempoTracingClient()
            client._initialized = True
            client._client = MagicMock()
            client._client.get_trace = AsyncMock(return_value=None)

            # WHEN
            result = await client.get_trace("nonexistent")

            # THEN
            assert result is None

    @pytest.mark.asyncio
    async def test_search_traces_passes_filters_to_tempo(self) -> None:
        """GIVEN search criteria WHEN search_traces() is called THEN passes filters to Tempo."""
        from mcp_server_langgraph.monitoring.tempo_client import TraceSearchResult
        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"TEMPO_URL": "http://localhost:3200"}):
            client = TempoTracingClient()
            client._initialized = True
            client._client = MagicMock()
            client._client.search = AsyncMock(return_value=TraceSearchResult(traces=[], total_traces=0))

            now = datetime.now(UTC)
            start = now - timedelta(hours=1)

            # WHEN
            await client.search_traces(
                service_name="mcp-server",
                operation_name="POST /api/chat",
                start=start,
                end=now,
                min_duration_ms=100.0,
                limit=20,
            )

            # THEN
            client._client.search.assert_awaited_once()
            call_args = client._client.search.call_args
            assert call_args.kwargs["service_name"] == "mcp-server"
            assert call_args.kwargs["operation_name"] == "POST /api/chat"
            assert call_args.kwargs["min_duration"] == "100.0ms"
            assert call_args.kwargs["limit"] == 20

    @pytest.mark.asyncio
    async def test_get_error_traces_returns_traces_with_errors(self) -> None:
        """GIVEN traces with errors WHEN get_error_traces() is called THEN returns error traces."""
        from mcp_server_langgraph.monitoring.tempo_client import (
            TraceSearchResult,
            TraceInfo as TempoTraceInfo,
        )
        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"TEMPO_URL": "http://localhost:3200"}):
            client = TempoTracingClient()
            client._initialized = True

            now = datetime.now(UTC)
            error_trace = TempoTraceInfo(
                trace_id="error-trace",
                root_service="mcp-server",
                root_operation="POST /api/chat",
                start_time=now,
                duration_ms=500.0,
                span_count=3,
                error_count=1,
                spans=[],
            )

            client._client = MagicMock()
            client._client.get_error_traces = AsyncMock(return_value=TraceSearchResult(traces=[error_trace], total_traces=1))

            # WHEN
            result = await client.get_error_traces(service_name="mcp-server")

            # THEN
            assert result.total_count == 1
            assert result.traces[0].error_count == 1

    @pytest.mark.asyncio
    async def test_health_check_returns_tempo_health(self) -> None:
        """GIVEN Tempo is healthy WHEN health_check() is called THEN returns True."""
        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"TEMPO_URL": "http://localhost:3200"}):
            client = TempoTracingClient()
            client._initialized = True
            client._client = MagicMock()
            client._client.health_check = AsyncMock(return_value=True)

            # WHEN
            result = await client.health_check()

            # THEN
            assert result is True


# =============================================================================
# Loki Logging Client Tests
# =============================================================================


@pytest.mark.xdist_group(name="lgtm_loki")
class TestLokiLoggingClient:
    """Tests for LokiLoggingClient implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_initialize_creates_http_client(self) -> None:
        """GIVEN a new LokiLoggingClient WHEN initialize() is called THEN HTTP client is created."""
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"LOKI_URL": "http://localhost:3100"}):
            client = LokiLoggingClient()

            # WHEN
            await client.initialize()

            # THEN
            assert client._initialized is True
            assert client._client is not None

            # Cleanup
            await client.close()

    @pytest.mark.asyncio
    async def test_close_releases_http_client(self) -> None:
        """GIVEN an initialized client WHEN close() is called THEN HTTP client is released."""
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"LOKI_URL": "http://localhost:3100"}):
            client = LokiLoggingClient()
            await client.initialize()

            # WHEN
            await client.close()

            # THEN
            assert client._initialized is False
            assert client._client is None

    @pytest.mark.asyncio
    async def test_build_logql_with_service_filter(self) -> None:
        """GIVEN service_name parameter WHEN _build_logql() is called THEN includes service label."""
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"LOKI_URL": "http://localhost:3100"}):
            client = LokiLoggingClient()

            # WHEN
            logql = client._build_logql(service_name="mcp-server")

            # THEN
            assert 'service_name="mcp-server"' in logql

    @pytest.mark.asyncio
    async def test_build_logql_with_level_filter(self) -> None:
        """GIVEN level parameter WHEN _build_logql() is called THEN includes level filter."""
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"LOKI_URL": "http://localhost:3100"}):
            client = LokiLoggingClient()

            # WHEN
            logql = client._build_logql(level=LogLevel.ERROR)

            # THEN
            assert '"level":"error"' in logql

    @pytest.mark.asyncio
    async def test_build_logql_with_text_query(self) -> None:
        """GIVEN text_query parameter WHEN _build_logql() is called THEN includes text filter."""
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"LOKI_URL": "http://localhost:3100"}):
            client = LokiLoggingClient()

            # WHEN
            logql = client._build_logql(text_query="authentication failed")

            # THEN
            assert "authentication failed" in logql
            assert "|~" in logql

    @pytest.mark.asyncio
    async def test_build_logql_with_raw_logql_passes_through(self) -> None:
        """GIVEN raw LogQL query WHEN _build_logql() is called THEN returns query as-is."""
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"LOKI_URL": "http://localhost:3100"}):
            client = LokiLoggingClient()
            raw_logql = '{job="mcp-server"} |= "error"'

            # WHEN
            result = client._build_logql(text_query=raw_logql)

            # THEN
            assert result == raw_logql

    @pytest.mark.asyncio
    async def test_parse_query_result_extracts_log_entries(self) -> None:
        """GIVEN Loki query result WHEN _parse_query_result() is called THEN returns LogEntry list."""
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"LOKI_URL": "http://localhost:3100"}):
            client = LokiLoggingClient()

            loki_response = {
                "data": {
                    "result": [
                        {
                            "stream": {
                                "service_name": "mcp-server",
                                "job": "mcp-server",
                            },
                            "values": [
                                [
                                    "1702742400000000000",  # timestamp in nanoseconds
                                    '{"level":"error","message":"Connection failed","trace_id":"abc123"}',
                                ]
                            ],
                        }
                    ]
                }
            }

            # WHEN
            entries = client._parse_query_result(loki_response)

            # THEN
            assert len(entries) == 1
            assert entries[0].level == LogLevel.ERROR
            assert entries[0].service_name == "mcp-server"
            assert entries[0].trace_id == "abc123"

    @pytest.mark.asyncio
    async def test_extract_level_from_json_message(self) -> None:
        """GIVEN JSON log message with level WHEN _extract_level() is called THEN returns level."""
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"LOKI_URL": "http://localhost:3100"}):
            client = LokiLoggingClient()

            # WHEN
            level = client._extract_level('{"level":"warning","message":"test"}')

            # THEN
            assert level == LogLevel.WARN

    @pytest.mark.asyncio
    async def test_extract_level_from_text_message(self) -> None:
        """GIVEN plain text message with level keyword WHEN _extract_level() THEN returns level."""
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"LOKI_URL": "http://localhost:3100"}):
            client = LokiLoggingClient()

            # WHEN
            level = client._extract_level("ERROR: Something went wrong")

            # THEN
            assert level == LogLevel.ERROR

    @pytest.mark.asyncio
    async def test_search_logs_calls_loki_api(self) -> None:
        """GIVEN search parameters WHEN search_logs() is called THEN calls Loki API."""
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"LOKI_URL": "http://localhost:3100"}):
            client = LokiLoggingClient()

            # Mock HTTP client
            mock_response = MagicMock(spec=httpx.Response)
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {"data": {"result": []}}

            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_client.get = AsyncMock(return_value=mock_response)

            client._client = mock_client
            client._initialized = True

            # Mock circuit breaker
            with patch("mcp_server_langgraph.observability.query.backends.loki.get_circuit_breaker") as mock_breaker:
                mock_breaker.return_value.current_state = "closed"
                mock_breaker.return_value.state.on_success = MagicMock()

                # WHEN
                result = await client.search_logs(
                    service_name="mcp-server",
                    level=LogLevel.ERROR,
                    limit=50,
                )

                # THEN
                mock_client.get.assert_awaited_once()
                call_args = mock_client.get.call_args
                assert "/loki/api/v1/query_range" in str(call_args)
                assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_get_logs_for_trace_uses_trace_id_label(self) -> None:
        """GIVEN trace_id WHEN get_logs_for_trace() is called THEN queries by trace_id label."""
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"LOKI_URL": "http://localhost:3100"}):
            client = LokiLoggingClient()
            client._initialized = True

            # Mock search_logs to capture the query
            client.search_logs = AsyncMock(return_value=None)  # type: ignore[method-assign]  # noqa: async-mock-config

            # WHEN
            await client.get_logs_for_trace("trace-abc123")

            # THEN
            call_args = client.search_logs.call_args
            query = call_args.kwargs.get("query", "")
            assert 'trace_id="trace-abc123"' in query

    @pytest.mark.asyncio
    async def test_health_check_returns_true_when_ready(self) -> None:
        """GIVEN Loki is ready WHEN health_check() is called THEN returns True."""
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"LOKI_URL": "http://localhost:3100"}):
            client = LokiLoggingClient()

            mock_response = MagicMock(spec=httpx.Response)
            mock_response.status_code = 200

            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_client.get = AsyncMock(return_value=mock_response)

            client._client = mock_client
            client._initialized = True

            # WHEN
            result = await client.health_check()

            # THEN
            assert result is True


# =============================================================================
# Prometheus/Mimir Metrics Client Tests
# =============================================================================


@pytest.mark.xdist_group(name="lgtm_prometheus")
class TestPrometheusMetricsClient:
    """Tests for PrometheusMetricsClient implementation (also used by Mimir)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_initialize_calls_underlying_client(self) -> None:
        """GIVEN a new client WHEN initialize() is called THEN underlying client is initialized."""
        from mcp_server_langgraph.observability.query.backends.prometheus import (
            PrometheusMetricsClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"PROMETHEUS_URL": "http://localhost:9090"}):
            client = PrometheusMetricsClient()

            # Mock the underlying PrometheusClient
            client._client = MagicMock()
            client._client.initialize = AsyncMock(return_value=None)  # noqa: async-mock-config
            client._client.close = AsyncMock(return_value=None)  # noqa: async-mock-config

            # WHEN
            await client.initialize()

            # THEN
            assert client._initialized is True
            client._client.initialize.assert_awaited_once()

            # Cleanup
            await client.close()

    @pytest.mark.asyncio
    async def test_close_calls_underlying_client(self) -> None:
        """GIVEN an initialized client WHEN close() is called THEN underlying client is closed."""
        from mcp_server_langgraph.observability.query.backends.prometheus import (
            PrometheusMetricsClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"PROMETHEUS_URL": "http://localhost:9090"}):
            client = PrometheusMetricsClient()
            client._client = MagicMock()
            client._client.initialize = AsyncMock(return_value=None)  # noqa: async-mock-config
            client._client.close = AsyncMock(return_value=None)  # noqa: async-mock-config

            await client.initialize()

            # WHEN
            await client.close()

            # THEN
            assert client._initialized is False
            client._client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_query_instant_calls_underlying_query(self) -> None:
        """GIVEN a PromQL query WHEN query_instant() is called THEN calls underlying query."""
        from mcp_server_langgraph.monitoring.prometheus_client import (
            MetricValue as PromMetricValue,
            QueryResult,
        )
        from mcp_server_langgraph.observability.query.backends.prometheus import (
            PrometheusMetricsClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"PROMETHEUS_URL": "http://localhost:9090"}):
            client = PrometheusMetricsClient()
            client._initialized = True

            # Mock underlying client query result
            now = datetime.now(UTC)
            mock_result = [
                QueryResult(
                    metric={"__name__": "http_requests_total", "job": "mcp-server"},
                    values=[PromMetricValue(timestamp=now, value=100.0)],
                )
            ]
            client._client = MagicMock()
            client._client.query = AsyncMock(return_value=mock_result)

            # WHEN
            result = await client.query_instant("http_requests_total")

            # THEN
            client._client.query.assert_awaited_once()
            assert len(result.series) == 1
            assert result.series[0].metric_name == "http_requests_total"
            assert result.series[0].values[0].value == 100.0

    @pytest.mark.asyncio
    async def test_query_range_calls_underlying_query_range(self) -> None:
        """GIVEN time range WHEN query_range() is called THEN calls underlying query_range."""
        from mcp_server_langgraph.monitoring.prometheus_client import (
            MetricValue as PromMetricValue,
            QueryResult,
        )
        from mcp_server_langgraph.observability.query.backends.prometheus import (
            PrometheusMetricsClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"PROMETHEUS_URL": "http://localhost:9090"}):
            client = PrometheusMetricsClient()
            client._initialized = True

            now = datetime.now(UTC)
            start = now - timedelta(hours=1)

            # Mock underlying client
            mock_result = [
                QueryResult(
                    metric={"__name__": "http_requests_total", "job": "mcp-server"},
                    values=[
                        PromMetricValue(timestamp=start, value=100.0),
                        PromMetricValue(timestamp=now, value=200.0),
                    ],
                )
            ]
            client._client = MagicMock()
            client._client.query_range = AsyncMock(return_value=mock_result)

            # WHEN
            result = await client.query_range(
                query="rate(http_requests_total[5m])",
                start=start,
                end=now,
            )

            # THEN
            client._client.query_range.assert_awaited_once()
            assert len(result.series) == 1
            assert len(result.series[0].values) == 2

    @pytest.mark.asyncio
    async def test_get_service_metrics_returns_sla_metrics(self) -> None:
        """GIVEN service name WHEN get_service_metrics() is called THEN returns SLA metrics."""
        from mcp_server_langgraph.observability.query.backends.prometheus import (
            PrometheusMetricsClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"PROMETHEUS_URL": "http://localhost:9090"}):
            client = PrometheusMetricsClient()
            client._initialized = True

            # Mock SLA metrics response
            mock_sla_metrics = {
                "uptime_percentage": 99.9,
                "error_rate_percentage": 0.1,
                "response_times": {"p50": 50.0, "p95": 150.0, "p99": 250.0},
            }
            client._client = MagicMock()
            client._client.get_sla_metrics = AsyncMock(return_value=mock_sla_metrics)

            # WHEN
            result = await client.get_service_metrics("mcp-server")

            # THEN
            assert "uptime_percentage" in result
            assert "error_rate_percentage" in result
            assert result["uptime_percentage"].values[0].value == 99.9

    @pytest.mark.asyncio
    async def test_health_check_returns_true_when_query_succeeds(self) -> None:
        """GIVEN Prometheus is healthy WHEN health_check() is called THEN returns True."""
        from mcp_server_langgraph.observability.query.backends.prometheus import (
            PrometheusMetricsClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"PROMETHEUS_URL": "http://localhost:9090"}):
            client = PrometheusMetricsClient()
            client._initialized = True
            client._client = MagicMock()
            client._client.query = AsyncMock(return_value=[])  # Empty result but no error

            # WHEN
            result = await client.health_check()

            # THEN
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_error(self) -> None:
        """GIVEN Prometheus query fails WHEN health_check() is called THEN returns False."""
        from mcp_server_langgraph.observability.query.backends.prometheus import (
            PrometheusMetricsClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"PROMETHEUS_URL": "http://localhost:9090"}):
            client = PrometheusMetricsClient()
            client._initialized = True
            client._client = MagicMock()
            client._client.query = AsyncMock(side_effect=Exception("Connection failed"))

            # WHEN
            result = await client.health_check()

            # THEN
            assert result is False

    @pytest.mark.asyncio
    async def test_convert_query_result_extracts_metric_name(self) -> None:
        """GIVEN QueryResult with __name__ WHEN converted THEN extracts metric name."""
        from mcp_server_langgraph.monitoring.prometheus_client import (
            MetricValue as PromMetricValue,
            QueryResult,
        )
        from mcp_server_langgraph.observability.query.backends.prometheus import (
            _convert_query_result,
        )

        # GIVEN
        now = datetime.now(UTC)
        query_result = QueryResult(
            metric={"__name__": "cpu_usage", "instance": "localhost:9090"},
            values=[PromMetricValue(timestamp=now, value=75.5)],
        )

        # WHEN
        series = _convert_query_result(query_result)

        # THEN
        assert series.metric_name == "cpu_usage"
        assert series.labels == {"instance": "localhost:9090"}
        assert len(series.values) == 1
        assert series.values[0].value == 75.5


# =============================================================================
# Grafana Alerting Client Tests
# =============================================================================


@pytest.mark.xdist_group(name="lgtm_grafana")
class TestGrafanaAlertingClient:
    """Tests for GrafanaAlertingClient implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_initialize_creates_http_client(self) -> None:
        """GIVEN a new client WHEN initialize() is called THEN HTTP client is created."""
        from mcp_server_langgraph.observability.query.backends.grafana import (
            GrafanaAlertingClient,
        )

        # GIVEN
        with patch.dict(
            "os.environ",
            {
                "GRAFANA_URL": "http://localhost:3000",
                "GRAFANA_API_KEY": "test-key",
            },
        ):
            client = GrafanaAlertingClient()

            # WHEN
            await client.initialize()

            # THEN
            assert client._client is not None

            # Cleanup
            await client.close()

    @pytest.mark.asyncio
    async def test_list_alerts_calls_grafana_api(self) -> None:
        """GIVEN alerting state filter WHEN list_alerts() is called THEN calls Grafana API."""
        from mcp_server_langgraph.observability.query.backends.grafana import (
            GrafanaAlertingClient,
        )
        from mcp_server_langgraph.observability.query.interfaces import AlertState

        # GIVEN
        with patch.dict(
            "os.environ",
            {
                "GRAFANA_URL": "http://localhost:3000",
                "GRAFANA_API_KEY": "test-key",
            },
        ):
            client = GrafanaAlertingClient()

            mock_response = MagicMock(spec=httpx.Response)
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = []

            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_client.get = AsyncMock(return_value=mock_response)

            client._client = mock_client

            # WHEN
            result = await client.list_alerts(state=AlertState.FIRING)

            # THEN
            mock_client.get.assert_awaited()
            assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_health_check_returns_true_when_healthy(self) -> None:
        """GIVEN Grafana is healthy WHEN health_check() is called THEN returns True."""
        from mcp_server_langgraph.observability.query.backends.grafana import (
            GrafanaAlertingClient,
        )

        # GIVEN
        with patch.dict(
            "os.environ",
            {
                "GRAFANA_URL": "http://localhost:3000",
                "GRAFANA_API_KEY": "test-key",
            },
        ):
            client = GrafanaAlertingClient()

            mock_response = MagicMock(spec=httpx.Response)
            mock_response.status_code = 200

            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_client.get = AsyncMock(return_value=mock_response)

            client._client = mock_client

            # WHEN
            result = await client.health_check()

            # THEN
            assert result is True


# =============================================================================
# Error Handling and Resilience Tests
# =============================================================================


@pytest.mark.xdist_group(name="lgtm_tempo_errors")
class TestTempoTracingClientErrorHandling:
    """Tests for Tempo client error handling and resilience.

    NOTE: These tests document EXPECTED error handling behavior.
    They are marked xfail until proper error handling is implemented
    in the backend classes.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_trace_handles_connection_error(self) -> None:
        """GIVEN Tempo is unreachable WHEN get_trace() is called THEN returns None."""
        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"TEMPO_URL": "http://localhost:3200"}):
            client = TempoTracingClient()
            client._initialized = True
            client._client = MagicMock()
            client._client.get_trace = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

            # WHEN
            result = await client.get_trace("test-trace-id")

            # THEN
            assert result is None

    @pytest.mark.asyncio
    async def test_search_traces_handles_timeout(self) -> None:
        """GIVEN request times out WHEN search_traces() is called THEN returns empty result."""
        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"TEMPO_URL": "http://localhost:3200"}):
            client = TempoTracingClient()
            client._initialized = True
            client._client = MagicMock()
            client._client.search = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))

            # WHEN
            result = await client.search_traces(service_name="mcp-server")

            # THEN
            assert result.total_count == 0
            assert result.traces == []

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_connection_error(self) -> None:
        """GIVEN Tempo is unreachable WHEN health_check() is called THEN returns False."""
        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"TEMPO_URL": "http://localhost:3200"}):
            client = TempoTracingClient()
            client._initialized = True
            client._client = MagicMock()
            client._client.health_check = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

            # WHEN
            result = await client.health_check()

            # THEN
            assert result is False

    @pytest.mark.asyncio
    async def test_get_trace_handles_invalid_trace_format(self) -> None:
        """GIVEN Tempo returns malformed data WHEN get_trace() is called THEN returns None."""
        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"TEMPO_URL": "http://localhost:3200"}):
            client = TempoTracingClient()
            client._initialized = True
            client._client = MagicMock()
            # Return malformed data that causes conversion error
            client._client.get_trace = AsyncMock(side_effect=ValueError("Invalid data"))

            # WHEN
            result = await client.get_trace("malformed-trace")

            # THEN
            assert result is None


@pytest.mark.xdist_group(name="lgtm_loki_errors")
class TestLokiLoggingClientErrorHandling:
    """Tests for Loki client error handling and resilience.

    NOTE: These tests document EXPECTED error handling behavior.
    They are marked xfail until proper error handling is implemented.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_logs_handles_connection_error(self) -> None:
        """GIVEN Loki is unreachable WHEN search_logs() is called THEN returns empty result."""
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"LOKI_URL": "http://localhost:3100"}):
            client = LokiLoggingClient()
            client._initialized = True

            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            client._client = mock_client

            # Mock circuit breaker
            with patch("mcp_server_langgraph.observability.query.backends.loki.get_circuit_breaker") as mock_breaker:
                mock_breaker.return_value.current_state = "closed"
                mock_breaker.return_value.state.on_failure = MagicMock()

                # WHEN
                result = await client.search_logs(service_name="mcp-server")

                # THEN
                assert result.total_count == 0
                assert result.entries == []

    @pytest.mark.asyncio
    async def test_search_logs_handles_timeout(self) -> None:
        """GIVEN request times out WHEN search_logs() is called THEN returns empty result."""
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"LOKI_URL": "http://localhost:3100"}):
            client = LokiLoggingClient()
            client._initialized = True

            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))
            client._client = mock_client

            with patch("mcp_server_langgraph.observability.query.backends.loki.get_circuit_breaker") as mock_breaker:
                mock_breaker.return_value.current_state = "closed"
                mock_breaker.return_value.state.on_failure = MagicMock()

                # WHEN
                result = await client.search_logs(service_name="mcp-server")

                # THEN
                assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_timeout(self) -> None:
        """GIVEN Loki times out WHEN health_check() is called THEN returns False."""
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"LOKI_URL": "http://localhost:3100"}):
            client = LokiLoggingClient()
            client._initialized = True

            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Health check timed out"))
            client._client = mock_client

            # WHEN
            result = await client.health_check()

            # THEN
            assert result is False

    @pytest.mark.asyncio
    async def test_parse_query_result_handles_malformed_json(self) -> None:
        """GIVEN Loki returns non-JSON log line WHEN parsed THEN handles gracefully."""
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"LOKI_URL": "http://localhost:3100"}):
            client = LokiLoggingClient()

            # Non-JSON log line (plain text)
            loki_response = {
                "data": {
                    "result": [
                        {
                            "stream": {"service_name": "mcp-server"},
                            "values": [
                                [
                                    "1702742400000000000",
                                    "Plain text log message without JSON",
                                ]
                            ],
                        }
                    ]
                }
            }

            # WHEN
            entries = client._parse_query_result(loki_response)

            # THEN - should not crash, returns entry with raw message
            assert len(entries) == 1
            assert "Plain text log message" in entries[0].message

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self) -> None:
        """GIVEN multiple failures WHEN circuit breaker is checked THEN state is open."""
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"LOKI_URL": "http://localhost:3100"}):
            client = LokiLoggingClient()
            client._initialized = True

            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            client._client = mock_client

            with patch("mcp_server_langgraph.observability.query.backends.loki.get_circuit_breaker") as mock_breaker:
                mock_breaker.return_value.current_state = "open"
                mock_breaker.return_value.is_circuit_open = True

                # WHEN - circuit is open, should short-circuit
                result = await client.search_logs(service_name="mcp-server")

                # THEN
                assert result.total_count == 0


@pytest.mark.xdist_group(name="lgtm_prometheus_errors")
class TestPrometheusMetricsClientErrorHandling:
    """Tests for Prometheus client error handling and resilience.

    NOTE: These tests document EXPECTED error handling behavior.
    They are marked xfail until proper error handling is implemented.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_query_instant_handles_connection_error(self) -> None:
        """GIVEN Prometheus is unreachable WHEN query_instant() is called THEN returns empty."""
        from mcp_server_langgraph.observability.query.backends.prometheus import (
            PrometheusMetricsClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"PROMETHEUS_URL": "http://localhost:9090"}):
            client = PrometheusMetricsClient()
            client._initialized = True
            client._client = MagicMock()
            client._client.query = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

            # WHEN
            result = await client.query_instant("up")

            # THEN
            assert result.series == []

    @pytest.mark.asyncio
    async def test_query_range_handles_timeout(self) -> None:
        """GIVEN request times out WHEN query_range() is called THEN returns empty result."""
        from mcp_server_langgraph.observability.query.backends.prometheus import (
            PrometheusMetricsClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"PROMETHEUS_URL": "http://localhost:9090"}):
            client = PrometheusMetricsClient()
            client._initialized = True

            now = datetime.now(UTC)
            start = now - timedelta(hours=1)

            client._client = MagicMock()
            client._client.query_range = AsyncMock(side_effect=httpx.TimeoutException("Query timed out"))

            # WHEN
            result = await client.query_range(
                query="rate(http_requests_total[5m])",
                start=start,
                end=now,
            )

            # THEN
            assert result.series == []

    @pytest.mark.asyncio
    async def test_query_handles_promql_syntax_error(self) -> None:
        """GIVEN invalid PromQL WHEN query_instant() is called THEN returns empty result."""
        from mcp_server_langgraph.observability.query.backends.prometheus import (
            PrometheusMetricsClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"PROMETHEUS_URL": "http://localhost:9090"}):
            client = PrometheusMetricsClient()
            client._initialized = True
            client._client = MagicMock()
            client._client.query = AsyncMock(side_effect=ValueError("parse error: unexpected token"))

            # WHEN
            result = await client.query_instant("invalid{{query")

            # THEN
            assert result.series == []

    @pytest.mark.asyncio
    async def test_get_service_metrics_handles_partial_failure(self) -> None:
        """GIVEN some metrics fail WHEN get_service_metrics() is called THEN returns partial."""
        from mcp_server_langgraph.observability.query.backends.prometheus import (
            PrometheusMetricsClient,
        )

        # GIVEN
        with patch.dict("os.environ", {"PROMETHEUS_URL": "http://localhost:9090"}):
            client = PrometheusMetricsClient()
            client._initialized = True
            client._client = MagicMock()
            # Return partial data - some metrics fail
            client._client.get_sla_metrics = AsyncMock(side_effect=Exception("Partial failure"))

            # WHEN
            result = await client.get_service_metrics("mcp-server")

            # THEN - should return empty dict on failure
            assert result == {}


@pytest.mark.xdist_group(name="lgtm_grafana_errors")
class TestGrafanaAlertingClientErrorHandling:
    """Tests for Grafana client error handling and resilience.

    NOTE: These tests document EXPECTED error handling behavior.
    They are marked xfail until proper error handling is implemented.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_alerts_handles_auth_failure(self) -> None:
        """GIVEN API key is invalid WHEN list_alerts() is called THEN returns empty."""
        from mcp_server_langgraph.observability.query.backends.grafana import (
            GrafanaAlertingClient,
        )
        from mcp_server_langgraph.observability.query.interfaces import AlertState

        # GIVEN
        with patch.dict(
            "os.environ",
            {
                "GRAFANA_URL": "http://localhost:3000",
                "GRAFANA_API_KEY": "invalid-key",
            },
        ):
            client = GrafanaAlertingClient()

            mock_response = MagicMock(spec=httpx.Response)
            mock_response.status_code = 401
            mock_response.raise_for_status = MagicMock(
                side_effect=httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=mock_response)
            )

            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_client.get = AsyncMock(return_value=mock_response)
            client._client = mock_client

            # WHEN
            result = await client.list_alerts(state=AlertState.FIRING)

            # THEN
            assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_list_alerts_handles_connection_error(self) -> None:
        """GIVEN Grafana is unreachable WHEN list_alerts() is called THEN returns empty."""
        from mcp_server_langgraph.observability.query.backends.grafana import (
            GrafanaAlertingClient,
        )
        from mcp_server_langgraph.observability.query.interfaces import AlertState

        # GIVEN
        with patch.dict(
            "os.environ",
            {
                "GRAFANA_URL": "http://localhost:3000",
                "GRAFANA_API_KEY": "test-key",
            },
        ):
            client = GrafanaAlertingClient()

            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            client._client = mock_client

            # WHEN
            result = await client.list_alerts(state=AlertState.FIRING)

            # THEN
            assert result.total_count == 0
            assert result.alerts == []

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_forbidden(self) -> None:
        """GIVEN insufficient permissions WHEN health_check() is called THEN returns False."""
        from mcp_server_langgraph.observability.query.backends.grafana import (
            GrafanaAlertingClient,
        )

        # GIVEN
        with patch.dict(
            "os.environ",
            {
                "GRAFANA_URL": "http://localhost:3000",
                "GRAFANA_API_KEY": "test-key",
            },
        ):
            client = GrafanaAlertingClient()

            mock_response = MagicMock(spec=httpx.Response)
            mock_response.status_code = 403

            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_client.get = AsyncMock(return_value=mock_response)
            client._client = mock_client

            # WHEN
            result = await client.health_check()

            # THEN
            assert result is False

    @pytest.mark.asyncio
    async def test_list_alerts_handles_malformed_response(self) -> None:
        """GIVEN Grafana returns invalid JSON WHEN list_alerts() is called THEN returns empty."""
        from mcp_server_langgraph.observability.query.backends.grafana import (
            GrafanaAlertingClient,
        )
        from mcp_server_langgraph.observability.query.interfaces import AlertState

        # GIVEN
        with patch.dict(
            "os.environ",
            {
                "GRAFANA_URL": "http://localhost:3000",
                "GRAFANA_API_KEY": "test-key",
            },
        ):
            client = GrafanaAlertingClient()

            mock_response = MagicMock(spec=httpx.Response)
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json = MagicMock(side_effect=ValueError("Invalid JSON"))

            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_client.get = AsyncMock(return_value=mock_response)
            client._client = mock_client

            # WHEN
            result = await client.list_alerts(state=AlertState.FIRING)

            # THEN
            assert result.total_count == 0
