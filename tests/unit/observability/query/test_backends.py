"""
Unit tests for observability query backends.

Tests the backend implementations for TracingQueryClient, LoggingQueryClient,
and MetricsQueryClient that wrap underlying clients (Tempo, Loki, Prometheus/Mimir).

Follows TDD: These tests are written FIRST before implementation (RED phase).
"""

import gc
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from mcp_server_langgraph.observability.query.backends.stub import (
    StubLoggingClient,
    StubMetricsClient,
    StubTracingClient,
)
from mcp_server_langgraph.observability.query.interfaces import (
    LogEntry,
    LogLevel,
    MetricSeries,
    MetricValue,
    TraceInfo,
)

# Module-level marker for pytest
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="observability_query")
class TestStubTracingClient:
    """Tests for StubTracingClient implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_initialize_sets_initialized_flag(self) -> None:
        """GIVEN a new StubTracingClient WHEN initialize() is called THEN _initialized is True."""
        # GIVEN
        client = StubTracingClient()

        # WHEN
        await client.initialize()

        # THEN
        assert client._initialized is True

    @pytest.mark.asyncio
    async def test_close_clears_traces(self) -> None:
        """GIVEN a client with traces WHEN close() is called THEN traces are cleared."""
        # GIVEN
        client = StubTracingClient()
        await client.initialize()
        trace = TraceInfo(
            trace_id="abc123",
            root_service="test-service",
            root_operation="test-op",
            start_time=datetime.now(UTC),
            duration_ms=100.0,
            span_count=1,
        )
        client.add_trace(trace)

        # WHEN
        await client.close()

        # THEN
        assert len(client._traces) == 0

    @pytest.mark.asyncio
    async def test_get_trace_returns_trace_by_id(self) -> None:
        """GIVEN a client with a trace WHEN get_trace() with matching ID THEN returns trace."""
        # GIVEN
        client = StubTracingClient()
        await client.initialize()
        trace = TraceInfo(
            trace_id="trace-123",
            root_service="mcp-server",
            root_operation="POST /api/chat",
            start_time=datetime.now(UTC),
            duration_ms=250.5,
            span_count=5,
            error_count=0,
        )
        client.add_trace(trace)

        # WHEN
        result = await client.get_trace("trace-123")

        # THEN
        assert result is not None
        assert result.trace_id == "trace-123"
        assert result.root_service == "mcp-server"

    @pytest.mark.asyncio
    async def test_get_trace_returns_none_for_missing_id(self) -> None:
        """GIVEN a client WHEN get_trace() with non-existent ID THEN returns None."""
        # GIVEN
        client = StubTracingClient()
        await client.initialize()

        # WHEN
        result = await client.get_trace("nonexistent")

        # THEN
        assert result is None

    @pytest.mark.asyncio
    async def test_search_traces_filters_by_service(self) -> None:
        """GIVEN traces from multiple services WHEN search by service THEN returns matching."""
        # GIVEN
        client = StubTracingClient()
        await client.initialize()

        now = datetime.now(UTC)
        trace1 = TraceInfo(
            trace_id="t1",
            root_service="mcp-server",
            root_operation="op1",
            start_time=now,
            duration_ms=100.0,
            span_count=1,
        )
        trace2 = TraceInfo(
            trace_id="t2",
            root_service="other-service",
            root_operation="op2",
            start_time=now,
            duration_ms=200.0,
            span_count=2,
        )
        client.add_trace(trace1)
        client.add_trace(trace2)

        # WHEN
        result = await client.search_traces(service_name="mcp-server")

        # THEN
        assert result.total_count == 1
        assert result.traces[0].trace_id == "t1"

    @pytest.mark.asyncio
    async def test_search_traces_filters_by_duration(self) -> None:
        """GIVEN traces with different durations WHEN filter by duration THEN returns matching."""
        # GIVEN
        client = StubTracingClient()
        await client.initialize()

        now = datetime.now(UTC)
        fast_trace = TraceInfo(
            trace_id="fast",
            root_service="svc",
            root_operation="op",
            start_time=now,
            duration_ms=50.0,
            span_count=1,
        )
        slow_trace = TraceInfo(
            trace_id="slow",
            root_service="svc",
            root_operation="op",
            start_time=now,
            duration_ms=500.0,
            span_count=1,
        )
        client.add_trace(fast_trace)
        client.add_trace(slow_trace)

        # WHEN
        result = await client.search_traces(min_duration_ms=100.0)

        # THEN
        assert result.total_count == 1
        assert result.traces[0].trace_id == "slow"

    @pytest.mark.asyncio
    async def test_get_error_traces_returns_only_errors(self) -> None:
        """GIVEN traces with and without errors WHEN get_error_traces THEN returns only errors."""
        # GIVEN
        client = StubTracingClient()
        await client.initialize()

        now = datetime.now(UTC)
        ok_trace = TraceInfo(
            trace_id="ok",
            root_service="svc",
            root_operation="op",
            start_time=now,
            duration_ms=100.0,
            span_count=1,
            error_count=0,
        )
        error_trace = TraceInfo(
            trace_id="error",
            root_service="svc",
            root_operation="op",
            start_time=now,
            duration_ms=100.0,
            span_count=1,
            error_count=1,
        )
        client.add_trace(ok_trace)
        client.add_trace(error_trace)

        # WHEN
        result = await client.get_error_traces()

        # THEN
        assert result.total_count == 1
        assert result.traces[0].trace_id == "error"

    @pytest.mark.asyncio
    async def test_health_check_returns_true_when_initialized(self) -> None:
        """GIVEN initialized client WHEN health_check THEN returns True."""
        # GIVEN
        client = StubTracingClient()
        await client.initialize()

        # WHEN
        result = await client.health_check()

        # THEN
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_returns_false_when_not_initialized(self) -> None:
        """GIVEN non-initialized client WHEN health_check THEN returns False."""
        # GIVEN
        client = StubTracingClient()

        # WHEN
        result = await client.health_check()

        # THEN
        assert result is False


@pytest.mark.xdist_group(name="observability_query")
class TestStubLoggingClient:
    """Tests for StubLoggingClient implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_logs_filters_by_level(self) -> None:
        """GIVEN logs at different levels WHEN search by level THEN returns matching and above."""
        # GIVEN
        client = StubLoggingClient()
        await client.initialize()

        now = datetime.now(UTC)
        debug_log = LogEntry(
            timestamp=now,
            level=LogLevel.DEBUG,
            message="Debug message",
            service_name="svc",
        )
        error_log = LogEntry(
            timestamp=now,
            level=LogLevel.ERROR,
            message="Error message",
            service_name="svc",
        )
        client.add_log(debug_log)
        client.add_log(error_log)

        # WHEN
        result = await client.search_logs(level=LogLevel.ERROR)

        # THEN
        assert result.total_count == 1
        assert result.entries[0].level == LogLevel.ERROR

    @pytest.mark.asyncio
    async def test_get_logs_for_trace_returns_correlated_logs(self) -> None:
        """GIVEN logs with trace correlation WHEN get_logs_for_trace THEN returns correlated."""
        # GIVEN
        client = StubLoggingClient()
        await client.initialize()

        now = datetime.now(UTC)
        log1 = LogEntry(
            timestamp=now,
            level=LogLevel.INFO,
            message="Log 1",
            service_name="svc",
            trace_id="trace-abc",
        )
        log2 = LogEntry(
            timestamp=now,
            level=LogLevel.INFO,
            message="Log 2",
            service_name="svc",
            trace_id="trace-xyz",
        )
        client.add_log(log1)
        client.add_log(log2)

        # WHEN
        result = await client.get_logs_for_trace("trace-abc")

        # THEN
        assert result.total_count == 1
        assert result.entries[0].trace_id == "trace-abc"

    @pytest.mark.asyncio
    async def test_search_logs_text_search(self) -> None:
        """GIVEN logs with different messages WHEN search by text THEN returns matching."""
        # GIVEN
        client = StubLoggingClient()
        await client.initialize()

        now = datetime.now(UTC)
        client.add_log(
            LogEntry(
                timestamp=now,
                level=LogLevel.INFO,
                message="User authentication successful",
                service_name="svc",
            )
        )
        client.add_log(
            LogEntry(
                timestamp=now,
                level=LogLevel.INFO,
                message="Database connection established",
                service_name="svc",
            )
        )

        # WHEN
        result = await client.search_logs(query="authentication")

        # THEN
        assert result.total_count == 1
        assert "authentication" in result.entries[0].message.lower()


@pytest.mark.xdist_group(name="observability_query")
class TestStubMetricsClient:
    """Tests for StubMetricsClient implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_query_instant_matches_by_name(self) -> None:
        """GIVEN metric series WHEN query_instant with name THEN returns matching."""
        # GIVEN
        client = StubMetricsClient()
        await client.initialize()

        now = datetime.now(UTC)
        series = MetricSeries(
            metric_name="http_requests_total",
            labels={"service": "mcp-server"},
            values=[MetricValue(timestamp=now, value=100.0)],
        )
        client.add_series(series)

        # WHEN
        result = await client.query_instant("http_requests")

        # THEN
        assert len(result.series) == 1
        assert result.series[0].metric_name == "http_requests_total"

    @pytest.mark.asyncio
    async def test_query_range_filters_by_time(self) -> None:
        """GIVEN metric values over time WHEN query_range THEN returns values in range."""
        # GIVEN
        client = StubMetricsClient()
        await client.initialize()

        now = datetime.now(UTC)
        old_value = MetricValue(timestamp=now - timedelta(hours=2), value=50.0)
        recent_value = MetricValue(timestamp=now - timedelta(minutes=30), value=100.0)

        series = MetricSeries(
            metric_name="cpu_usage",
            labels={"service": "mcp-server"},
            values=[old_value, recent_value],
        )
        client.add_series(series)

        # WHEN
        result = await client.query_range(
            query="cpu_usage",
            start=now - timedelta(hours=1),
            end=now,
        )

        # THEN
        assert len(result.series) == 1
        assert len(result.series[0].values) == 1
        assert result.series[0].values[0].value == 100.0

    @pytest.mark.asyncio
    async def test_get_service_metrics_filters_by_label(self) -> None:
        """GIVEN metrics for multiple services WHEN get_service_metrics THEN returns for service."""
        # GIVEN
        client = StubMetricsClient()
        await client.initialize()

        now = datetime.now(UTC)
        client.add_series(
            MetricSeries(
                metric_name="request_count",
                labels={"service": "mcp-server"},
                values=[MetricValue(timestamp=now, value=100.0)],
            )
        )
        client.add_series(
            MetricSeries(
                metric_name="request_count",
                labels={"service": "other-service"},
                values=[MetricValue(timestamp=now, value=200.0)],
            )
        )

        # WHEN
        result = await client.get_service_metrics("mcp-server")

        # THEN
        assert "request_count" in result
        assert result["request_count"].labels["service"] == "mcp-server"


@pytest.mark.xdist_group(name="observability_query")
class TestFactoryFunctions:
    """Tests for factory functions and environment-based configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_tracing_client_returns_stub_backend(self) -> None:
        """GIVEN OBSERVABILITY_TRACING_BACKEND=stub WHEN get_tracing_client THEN returns stub."""
        from mcp_server_langgraph.observability.query.factory import (
            _create_tracing_client,
            TracingBackend,
        )

        # WHEN
        client = _create_tracing_client(TracingBackend.STUB)

        # THEN
        assert isinstance(client, StubTracingClient)

    @pytest.mark.asyncio
    async def test_get_logging_client_returns_stub_backend(self) -> None:
        """GIVEN OBSERVABILITY_LOGGING_BACKEND=stub WHEN get_logging_client THEN returns stub."""
        from mcp_server_langgraph.observability.query.factory import (
            _create_logging_client,
            LoggingBackend,
        )

        # WHEN
        client = _create_logging_client(LoggingBackend.STUB)

        # THEN
        assert isinstance(client, StubLoggingClient)

    @pytest.mark.asyncio
    async def test_get_metrics_client_returns_stub_backend(self) -> None:
        """GIVEN OBSERVABILITY_METRICS_BACKEND=stub WHEN get_metrics_client THEN returns stub."""
        from mcp_server_langgraph.observability.query.factory import (
            _create_metrics_client,
            MetricsBackend,
        )

        # WHEN
        client = _create_metrics_client(MetricsBackend.STUB)

        # THEN
        assert isinstance(client, StubMetricsClient)

    @pytest.mark.asyncio
    async def test_init_and_close_query_clients(self) -> None:
        """GIVEN stub backends WHEN init_query_clients/close_query_clients THEN lifecycle works."""
        import os

        from mcp_server_langgraph.observability.query.factory import (
            close_query_clients,
            init_query_clients,
        )

        # GIVEN - stub backends configured
        with patch.dict(
            os.environ,
            {
                "OBSERVABILITY_TRACING_BACKEND": "stub",
                "OBSERVABILITY_LOGGING_BACKEND": "stub",
                "OBSERVABILITY_METRICS_BACKEND": "stub",
            },
        ):
            # Reset global clients
            import mcp_server_langgraph.observability.query.factory as factory

            factory._tracing_client = None
            factory._logging_client = None
            factory._metrics_client = None

            # WHEN
            await init_query_clients()

            # THEN - clients are initialized
            assert factory._tracing_client is not None
            assert factory._logging_client is not None
            assert factory._metrics_client is not None

            # WHEN - close
            await close_query_clients()

            # THEN - clients are None
            assert factory._tracing_client is None
            assert factory._logging_client is None
            assert factory._metrics_client is None
