"""
Integration tests for LGTM Python Client APIs.

These tests validate that the Python client implementations (LokiLoggingClient,
TempoTracingClient, PrometheusMetricsClient) work correctly with real LGTM services.

Unlike test_lgtm_stack.py which tests infrastructure health via HTTP endpoints,
these tests validate the actual Python client APIs used by the application.

Tests require `make test-infra-full-up` to be running.

TDD Rationale:
--------------
The E2E test failures revealed that while infrastructure health tests exist,
there were no tests validating that our Python client APIs actually work.
This creates a gap where infrastructure could be healthy but client code broken.

Test Categories:
----------------
1. LokiLoggingClient: Log search, trace correlation, health check
2. TempoTracingClient: Trace search, trace retrieval, health check
3. PrometheusMetricsClient: Instant queries, range queries, health check

Markers:
--------
- @pytest.mark.integration: Integration test category
- @pytest.mark.observability: Observability-specific tests
- @pytest.mark.lgtm: LGTM stack specific tests

References:
-----------
- ADR-0067: Grafana LGTM Stack
- src/mcp_server_langgraph/observability/query/backends/
"""

import gc
import os
import socket
from datetime import UTC, datetime, timedelta

import pytest

from tests.constants import (
    TEST_LOKI_PORT,
    TEST_MIMIR_PORT,
    TEST_TEMPO_PORT,
)

# Module-level marker
pytestmark = [
    pytest.mark.integration,
    pytest.mark.observability,
    pytest.mark.xdist_group(name="lgtm_client_integration"),
]


def get_worker_prefix() -> str:
    """Get worker-specific prefix for test isolation in parallel execution."""
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "main")
    return f"test_{worker_id}"


# PYTEST-XDIST FIX: LGTM infrastructure tests are flaky in parallel execution
# because infrastructure availability checks may pass but actual operations
# fail due to timing issues with container startup/readiness.
_XDIST_LGTM_INFRASTRUCTURE_UNSTABLE = os.getenv("PYTEST_XDIST_WORKER") is not None


def teardown_module() -> None:
    """Force GC to prevent mock accumulation in xdist workers."""
    gc.collect()


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is in use (service is accessible)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        try:
            sock.connect((host, port))
            return True
        except (TimeoutError, ConnectionRefusedError, OSError):
            return False


def loki_available() -> bool:
    """Check if Loki is available AND healthy for testing.

    Verifies Loki is actually running by checking a Loki-specific endpoint.
    """
    import httpx

    if not is_port_in_use(TEST_LOKI_PORT):
        return False

    try:
        # Check Loki-specific endpoint, not just /ready which any service might respond to
        response = httpx.get(
            f"http://localhost:{TEST_LOKI_PORT}/loki/api/v1/labels",
            timeout=2.0,
        )
        # Loki returns 200 for this endpoint even if no labels exist
        return response.status_code == 200
    except Exception:
        return False


def tempo_available() -> bool:
    """Check if Tempo is available AND healthy for testing.

    Verifies Tempo is actually running by checking a Tempo-specific endpoint.
    """
    import httpx

    if not is_port_in_use(TEST_TEMPO_PORT):
        return False

    try:
        # Check Tempo-specific endpoint
        # The /api/search endpoint should return 200 even with no params
        response = httpx.get(
            f"http://localhost:{TEST_TEMPO_PORT}/api/search",
            timeout=2.0,
        )
        # Tempo returns 200 or 400 for this endpoint
        return response.status_code in [200, 400]
    except Exception:
        return False


def mimir_available() -> bool:
    """Check if Mimir is available AND healthy for testing.

    Verifies Mimir is actually running by checking a Mimir-specific endpoint.
    """
    import httpx

    if not is_port_in_use(TEST_MIMIR_PORT):
        return False

    try:
        # Check Mimir/Prometheus-specific endpoint
        response = httpx.get(
            f"http://localhost:{TEST_MIMIR_PORT}/api/v1/status/buildinfo",
            timeout=2.0,
        )
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture(autouse=True)
def teardown_gc():
    """Force GC after each test to prevent memory accumulation."""
    yield
    gc.collect()


# ==============================================================================
# Loki Logging Client Tests
# ==============================================================================


@pytest.mark.xdist_group(name="loki_client")
class TestLokiLoggingClient:
    """
    Integration tests for LokiLoggingClient.

    Tests the Python client API for querying logs from Grafana Loki.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not loki_available(), reason="Loki not available")
    @pytest.mark.xfail(
        _XDIST_LGTM_INFRASTRUCTURE_UNSTABLE,
        reason="Loki infrastructure timing issues in xdist parallel execution",
        strict=False,
    )
    async def test_loki_client_health_check(self) -> None:
        """
        GIVEN LokiLoggingClient configured with test environment
        WHEN health_check() is called
        THEN it returns True indicating Loki is healthy.
        """
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        # Override URL to use test port
        client = LokiLoggingClient()
        client._url = f"http://localhost:{TEST_LOKI_PORT}"

        try:
            await client.initialize()
            is_healthy = await client.health_check()
            assert is_healthy is True
        finally:
            await client.close()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not loki_available(), reason="Loki not available")
    async def test_loki_client_search_logs_empty_query(self) -> None:
        """
        GIVEN LokiLoggingClient configured with test environment
        WHEN search_logs() is called with minimal filters
        THEN it returns a LogSearchResult (may be empty but no error).

        Note: Loki requires at least one valid stream selector or line filter.
        An empty query '{}' returns 400 Bad Request. We use a service_name
        filter to ensure the query is valid.
        """
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        client = LokiLoggingClient()
        client._url = f"http://localhost:{TEST_LOKI_PORT}"

        try:
            await client.initialize()

            # Use a service_name filter to ensure valid LogQL query
            # (empty query '{}' returns 400 Bad Request from Loki)
            result = await client.search_logs(
                service_name="mcp-server-langgraph",  # Valid stream selector
                start=datetime.now(UTC) - timedelta(hours=1),
                end=datetime.now(UTC),
                limit=10,
            )

            # Should return a valid result structure (may have 0 entries)
            assert result is not None
            assert hasattr(result, "entries")
            assert hasattr(result, "total_count")
            assert isinstance(result.entries, list)
        finally:
            await client.close()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not loki_available(), reason="Loki not available")
    async def test_loki_client_search_logs_with_level_filter(self) -> None:
        """
        GIVEN LokiLoggingClient configured with test environment
        WHEN search_logs() is called with level filter
        THEN it returns filtered results without error.

        Note: Loki requires at least one stream selector, so we include
        service_name to ensure the query is valid.
        """
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )
        from mcp_server_langgraph.observability.query.interfaces import LogLevel

        client = LokiLoggingClient()
        client._url = f"http://localhost:{TEST_LOKI_PORT}"

        try:
            await client.initialize()

            result = await client.search_logs(
                service_name="mcp-server-langgraph",  # Required stream selector
                level=LogLevel.ERROR,
                start=datetime.now(UTC) - timedelta(hours=1),
                end=datetime.now(UTC),
                limit=10,
            )

            assert result is not None
            assert isinstance(result.entries, list)
        finally:
            await client.close()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not loki_available(), reason="Loki not available")
    async def test_loki_client_get_logs_for_trace(self) -> None:
        """
        GIVEN LokiLoggingClient configured with test environment
        WHEN get_logs_for_trace() is called with a trace ID
        THEN it returns correlated logs (may be empty for nonexistent trace).
        """
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        client = LokiLoggingClient()
        client._url = f"http://localhost:{TEST_LOKI_PORT}"
        prefix = get_worker_prefix()

        try:
            await client.initialize()

            # Query for a fake trace ID (should return empty, not error)
            result = await client.get_logs_for_trace(
                trace_id=f"{prefix}_nonexistent_trace_id_12345",
                start=datetime.now(UTC) - timedelta(hours=1),
                end=datetime.now(UTC),
            )

            assert result is not None
            assert isinstance(result.entries, list)
        finally:
            await client.close()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not loki_available(), reason="Loki not available")
    async def test_loki_client_get_logs_by_attribute(self) -> None:
        """
        GIVEN LokiLoggingClient configured with test environment
        WHEN get_logs_by_attribute() is called
        THEN it returns matching logs (may be empty).
        """
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        client = LokiLoggingClient()
        client._url = f"http://localhost:{TEST_LOKI_PORT}"

        try:
            await client.initialize()

            result = await client.get_logs_by_attribute(
                attribute="service_name",
                value="mcp-server-langgraph",
                start=datetime.now(UTC) - timedelta(hours=1),
                end=datetime.now(UTC),
                limit=10,
            )

            assert result is not None
            assert isinstance(result.entries, list)
        finally:
            await client.close()


# ==============================================================================
# Tempo Tracing Client Tests
# ==============================================================================


@pytest.mark.xdist_group(name="tempo_client")
class TestTempoTracingClient:
    """
    Integration tests for TempoTracingClient.

    Tests the Python client API for querying traces from Grafana Tempo.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not tempo_available(), reason="Tempo not available")
    async def test_tempo_client_health_check(self, monkeypatch) -> None:
        """
        GIVEN TempoTracingClient configured with test environment
        WHEN health_check() is called
        THEN it returns True indicating Tempo is healthy.
        """
        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        # Set environment variable for the client (monkeypatch auto-cleans up)
        monkeypatch.setenv("TEMPO_URL", f"http://localhost:{TEST_TEMPO_PORT}")

        try:
            client = TempoTracingClient()
            await client.initialize()
            is_healthy = await client.health_check()
            assert is_healthy is True
        finally:
            await client.close()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not tempo_available(), reason="Tempo not available")
    async def test_tempo_client_search_traces_empty(self, monkeypatch) -> None:
        """
        GIVEN TempoTracingClient configured with test environment
        WHEN search_traces() is called with no filters
        THEN it returns a TraceSearchResult (may be empty but no error).
        """
        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        monkeypatch.setenv("TEMPO_URL", f"http://localhost:{TEST_TEMPO_PORT}")

        try:
            client = TempoTracingClient()
            await client.initialize()

            result = await client.search_traces(
                start=datetime.now(UTC) - timedelta(hours=1),
                end=datetime.now(UTC),
                limit=10,
            )

            assert result is not None
            assert hasattr(result, "traces")
            assert hasattr(result, "total_count")
            assert isinstance(result.traces, list)
        finally:
            await client.close()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not tempo_available(), reason="Tempo not available")
    async def test_tempo_client_get_nonexistent_trace(self, monkeypatch) -> None:
        """
        GIVEN TempoTracingClient configured with test environment
        WHEN get_trace() is called with nonexistent trace ID
        THEN it returns None (not an error).

        Note: Trace IDs must be valid hexadecimal (16 or 32 chars).
        Using a valid format that doesn't exist in the system.
        """
        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        monkeypatch.setenv("TEMPO_URL", f"http://localhost:{TEST_TEMPO_PORT}")
        # Use worker ID to generate a unique but valid hex trace ID
        worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
        # Extract numeric part and pad to create valid 32-char hex trace ID
        worker_num = "".join(c for c in worker_id if c.isdigit()) or "0"
        # Create a valid 32-character hexadecimal trace ID (nonexistent)
        trace_id = f"deadbeef{worker_num.zfill(8)}cafebabe00000000"

        try:
            client = TempoTracingClient()
            await client.initialize()

            # Query for nonexistent but valid format trace ID
            result = await client.get_trace(trace_id)

            # Should return None for nonexistent trace
            assert result is None
        finally:
            await client.close()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not tempo_available(), reason="Tempo not available")
    async def test_tempo_client_search_by_service_name(self, monkeypatch) -> None:
        """
        GIVEN TempoTracingClient configured with test environment
        WHEN search_traces() is called with service_name filter
        THEN it returns filtered results (may be empty).
        """
        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        monkeypatch.setenv("TEMPO_URL", f"http://localhost:{TEST_TEMPO_PORT}")

        try:
            client = TempoTracingClient()
            await client.initialize()

            result = await client.search_traces(
                service_name="mcp-server-langgraph",
                start=datetime.now(UTC) - timedelta(hours=1),
                end=datetime.now(UTC),
                limit=10,
            )

            assert result is not None
            assert isinstance(result.traces, list)
        finally:
            await client.close()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not tempo_available(), reason="Tempo not available")
    async def test_tempo_client_get_error_traces(self, monkeypatch) -> None:
        """
        GIVEN TempoTracingClient configured with test environment
        WHEN get_error_traces() is called
        THEN it returns error traces (may be empty).
        """
        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        monkeypatch.setenv("TEMPO_URL", f"http://localhost:{TEST_TEMPO_PORT}")

        try:
            client = TempoTracingClient()
            await client.initialize()

            result = await client.get_error_traces(
                start=datetime.now(UTC) - timedelta(hours=1),
                end=datetime.now(UTC),
                limit=10,
            )

            assert result is not None
            assert isinstance(result.traces, list)
        finally:
            await client.close()


# ==============================================================================
# Prometheus/Mimir Metrics Client Tests
# ==============================================================================


@pytest.mark.xdist_group(name="mimir_client")
class TestPrometheusMetricsClient:
    """
    Integration tests for PrometheusMetricsClient.

    Tests the Python client API for querying metrics from Grafana Mimir.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not mimir_available(), reason="Mimir not available")
    async def test_mimir_client_health_check(self, monkeypatch) -> None:
        """
        GIVEN PrometheusMetricsClient configured with test environment
        WHEN health_check() is called
        THEN it returns True indicating Mimir is healthy.
        """
        from mcp_server_langgraph.observability.query.backends.prometheus import (
            PrometheusMetricsClient,
        )

        monkeypatch.setenv("MIMIR_URL", f"http://localhost:{TEST_MIMIR_PORT}")

        try:
            client = PrometheusMetricsClient()
            await client.initialize()
            is_healthy = await client.health_check()
            assert is_healthy is True
        finally:
            await client.close()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not mimir_available(), reason="Mimir not available")
    async def test_mimir_client_query_instant(self, monkeypatch) -> None:
        """
        GIVEN PrometheusMetricsClient configured with test environment
        WHEN query_instant() is called with 'up' query
        THEN it returns a MetricQueryResult.
        """
        from mcp_server_langgraph.observability.query.backends.prometheus import (
            PrometheusMetricsClient,
        )

        monkeypatch.setenv("MIMIR_URL", f"http://localhost:{TEST_MIMIR_PORT}")

        try:
            client = PrometheusMetricsClient()
            await client.initialize()

            result = await client.query_instant("up")

            assert result is not None
            assert hasattr(result, "series")
            assert isinstance(result.series, list)
        finally:
            await client.close()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not mimir_available(), reason="Mimir not available")
    async def test_mimir_client_query_range(self, monkeypatch) -> None:
        """
        GIVEN PrometheusMetricsClient configured with test environment
        WHEN query_range() is called
        THEN it returns a MetricQueryResult with time series data.
        """
        from mcp_server_langgraph.observability.query.backends.prometheus import (
            PrometheusMetricsClient,
        )

        monkeypatch.setenv("MIMIR_URL", f"http://localhost:{TEST_MIMIR_PORT}")

        try:
            client = PrometheusMetricsClient()
            await client.initialize()

            result = await client.query_range(
                query="up",
                start=datetime.now(UTC) - timedelta(minutes=15),
                end=datetime.now(UTC),
                step=timedelta(minutes=1),
            )

            assert result is not None
            assert hasattr(result, "series")
            assert isinstance(result.series, list)
        finally:
            await client.close()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not mimir_available(), reason="Mimir not available")
    async def test_mimir_client_invalid_query_returns_empty(self, monkeypatch) -> None:
        """
        GIVEN PrometheusMetricsClient configured with test environment
        WHEN query_instant() is called with invalid PromQL
        THEN it returns an empty MetricQueryResult (client catches errors internally).
        """
        from mcp_server_langgraph.observability.query.backends.prometheus import (
            PrometheusMetricsClient,
        )

        monkeypatch.setenv("MIMIR_URL", f"http://localhost:{TEST_MIMIR_PORT}")

        try:
            client = PrometheusMetricsClient()
            await client.initialize()

            # Invalid PromQL — client catches the error and returns empty result
            result = await client.query_instant("invalid{{{query")
            assert result.series == []
        finally:
            await client.close()


# ==============================================================================
# Client Lifecycle Tests
# ==============================================================================


@pytest.mark.xdist_group(name="lgtm_lifecycle")
class TestLGTMClientLifecycle:
    """
    Tests for client lifecycle management (initialize, close).
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not loki_available(), reason="Loki not available")
    async def test_loki_client_double_initialize_is_idempotent(self) -> None:
        """
        GIVEN LokiLoggingClient
        WHEN initialize() is called twice
        THEN second call is a no-op (idempotent).
        """
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        client = LokiLoggingClient()
        client._url = f"http://localhost:{TEST_LOKI_PORT}"

        try:
            await client.initialize()
            assert client._initialized is True

            # Second initialize should be idempotent
            await client.initialize()
            assert client._initialized is True
        finally:
            await client.close()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not loki_available(), reason="Loki not available")
    async def test_loki_client_close_cleans_up(self) -> None:
        """
        GIVEN initialized LokiLoggingClient
        WHEN close() is called
        THEN client is properly cleaned up.
        """
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        client = LokiLoggingClient()
        client._url = f"http://localhost:{TEST_LOKI_PORT}"

        await client.initialize()
        assert client._initialized is True
        assert client._client is not None

        await client.close()
        assert client._initialized is False
        assert client._client is None

    @pytest.mark.asyncio
    @pytest.mark.skipif(not tempo_available(), reason="Tempo not available")
    async def test_tempo_client_context_manager_pattern(self, monkeypatch) -> None:
        """
        GIVEN TempoTracingClient
        WHEN used with async context manager pattern
        THEN resources are properly managed.
        """
        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        monkeypatch.setenv("TEMPO_URL", f"http://localhost:{TEST_TEMPO_PORT}")

        client = TempoTracingClient()
        await client.initialize()

        # Perform operation
        is_healthy = await client.health_check()
        assert is_healthy is True

        await client.close()
        assert client._initialized is False


# ==============================================================================
# Error Handling Tests
# ==============================================================================


@pytest.mark.xdist_group(name="lgtm_errors")
class TestLGTMClientErrorHandling:
    """
    Tests for client error handling with unreachable services.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_loki_client_unreachable_service(self) -> None:
        """
        GIVEN LokiLoggingClient configured with unreachable URL
        WHEN health_check() is called
        THEN it returns False (not raises exception).
        """
        from mcp_server_langgraph.observability.query.backends.loki import (
            LokiLoggingClient,
        )

        client = LokiLoggingClient()
        # Use port that's definitely not in use
        client._url = "http://localhost:65535"

        try:
            await client.initialize()
            is_healthy = await client.health_check()
            assert is_healthy is False
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_tempo_client_unreachable_service(self, monkeypatch) -> None:
        """
        GIVEN TempoTracingClient configured with unreachable URL
        WHEN health_check() is called
        THEN it returns False (not raises exception).
        """
        from mcp_server_langgraph.observability.query.backends.tempo import (
            TempoTracingClient,
        )

        monkeypatch.setenv("TEMPO_URL", "http://localhost:65535")

        try:
            client = TempoTracingClient()
            await client.initialize()
            is_healthy = await client.health_check()
            assert is_healthy is False
        finally:
            await client.close()
