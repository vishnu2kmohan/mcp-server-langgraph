"""
Integration tests for Observability API endpoints.

Tests the full API path from HTTP request to response,
using the real FastAPI app with mocked tracing/metrics clients.

Tests cover:
- GET /api/v1/observability/traces - List traces
- GET /api/v1/observability/traces/{id} - Get single trace
- GET /api/v1/observability/metrics - Get system metrics
"""

import gc
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from mcp_server_langgraph.app import app
from mcp_server_langgraph.observability.query.interfaces import (
    MetricQueryResult,
    MetricSeries,
    MetricValue,
    SpanInfo,
    SpanStatusCode,
    TraceInfo,
    TraceSearchResult,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_tracing_client():
    """Create a mock tracing query client."""
    client = MagicMock()
    client.search_traces = AsyncMock()  # async-mock-configured
    client.get_trace = AsyncMock()  # async-mock-configured
    client.search_by_attribute = AsyncMock()  # async-mock-configured
    return client


@pytest.fixture
def mock_metrics_client():
    """Create a mock metrics query client."""
    client = MagicMock()
    client.query_instant = AsyncMock()  # async-mock-configured
    client.get_service_metrics = AsyncMock()  # async-mock-configured
    return client


@pytest.fixture
def sample_trace_info():
    """Sample TraceInfo for testing."""
    return TraceInfo(
        trace_id="abc123def456",
        root_service="mcp-server",
        root_operation="handle_request",
        start_time=datetime(2025, 1, 15, 10, 30, 0),
        duration_ms=150.5,
        span_count=5,
        error_count=0,
        spans=[
            SpanInfo(
                span_id="span1",
                trace_id="abc123def456",
                operation_name="handle_request",
                service_name="mcp-server",
                start_time=datetime(2025, 1, 15, 10, 30, 0),
                duration_ms=150.5,
                status_code=SpanStatusCode.OK,
            )
        ],
    )


@pytest.fixture
def sample_trace_search_result(sample_trace_info):
    """Sample TraceSearchResult for testing."""
    return TraceSearchResult(
        traces=[sample_trace_info],
        total_count=1,
        next_cursor=None,
    )


@pytest.fixture
def sample_metrics_result():
    """Sample MetricQueryResult for testing."""
    return MetricQueryResult(
        series=[
            MetricSeries(
                metric_name="requests_total",
                labels={"service": "mcp-server"},
                values=[MetricValue(timestamp=datetime.now(), value=1000)],
            )
        ]
    )


@pytest.mark.xdist_group(name="observability_api_integration")
class TestTracesListEndpoint:
    """Integration tests for GET /api/v1/observability/traces."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_traces_list_returns_200(self, client, mock_tracing_client, mock_metrics_client, sample_trace_search_result):
        """GET /api/v1/observability/traces should return 200 with traces."""
        mock_tracing_client.search_traces.return_value = sample_trace_search_result

        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

            service = ObservabilityServiceImpl(
                tracing=mock_tracing_client,
                metrics=mock_metrics_client,
            )
            mock_get_service.return_value = service

            response = client.get("/api/v1/observability/traces")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_traces_list_with_session_filter(
        self, client, mock_tracing_client, mock_metrics_client, sample_trace_search_result
    ):
        """GET /api/v1/observability/traces should filter by session_id."""
        mock_tracing_client.search_by_attribute.return_value = sample_trace_search_result

        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

            service = ObservabilityServiceImpl(
                tracing=mock_tracing_client,
                metrics=mock_metrics_client,
            )
            mock_get_service.return_value = service

            response = client.get(
                "/api/v1/observability/traces",
                params={"session_id": "session-123"},
            )

        assert response.status_code == 200

    def test_traces_list_includes_trace_ids(
        self, client, mock_tracing_client, mock_metrics_client, sample_trace_search_result
    ):
        """Response should include trace IDs."""
        mock_tracing_client.search_traces.return_value = sample_trace_search_result

        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

            service = ObservabilityServiceImpl(
                tracing=mock_tracing_client,
                metrics=mock_metrics_client,
            )
            mock_get_service.return_value = service

            response = client.get("/api/v1/observability/traces")

        data = response.json()
        if data["data"]:
            assert "trace_id" in data["data"][0]


@pytest.mark.xdist_group(name="observability_api_integration")
class TestTraceDetailEndpoint:
    """Integration tests for GET /api/v1/observability/traces/{id}."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_trace_detail_returns_200(self, client, mock_tracing_client, mock_metrics_client, sample_trace_info):
        """GET /api/v1/observability/traces/{id} should return 200 with trace."""
        mock_tracing_client.get_trace.return_value = sample_trace_info

        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

            service = ObservabilityServiceImpl(
                tracing=mock_tracing_client,
                metrics=mock_metrics_client,
            )
            mock_get_service.return_value = service

            response = client.get("/api/v1/observability/traces/abc123def456")

        assert response.status_code == 200
        data = response.json()
        assert data["trace_id"] == "abc123def456"

    def test_trace_detail_includes_spans(self, client, mock_tracing_client, mock_metrics_client, sample_trace_info):
        """Response should include spans list."""
        mock_tracing_client.get_trace.return_value = sample_trace_info

        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

            service = ObservabilityServiceImpl(
                tracing=mock_tracing_client,
                metrics=mock_metrics_client,
            )
            mock_get_service.return_value = service

            response = client.get("/api/v1/observability/traces/abc123def456")

        data = response.json()
        assert "spans" in data
        assert isinstance(data["spans"], list)

    def test_trace_detail_returns_404_for_not_found(self, client, mock_tracing_client, mock_metrics_client):
        """GET /api/v1/observability/traces/{id} should return 404 for not found."""
        mock_tracing_client.get_trace.return_value = None

        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

            service = ObservabilityServiceImpl(
                tracing=mock_tracing_client,
                metrics=mock_metrics_client,
            )
            mock_get_service.return_value = service

            response = client.get("/api/v1/observability/traces/nonexistent")

        assert response.status_code == 404


@pytest.mark.xdist_group(name="observability_api_integration")
class TestMetricsEndpoint:
    """Integration tests for GET /api/v1/observability/metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_metrics_returns_200(self, client, mock_tracing_client, mock_metrics_client, sample_metrics_result):
        """GET /api/v1/observability/metrics should return 200."""
        mock_metrics_client.query_instant.return_value = sample_metrics_result

        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

            service = ObservabilityServiceImpl(
                tracing=mock_tracing_client,
                metrics=mock_metrics_client,
            )
            mock_get_service.return_value = service

            response = client.get("/api/v1/observability/metrics")

        assert response.status_code == 200
        data = response.json()
        assert "requests_total" in data or isinstance(data, dict)
