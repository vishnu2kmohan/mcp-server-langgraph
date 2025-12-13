"""
Observability Router Unit Tests

Tests for /api/v1/observability endpoints per TDD methodology.
Tests written FIRST before implementation (RED phase).

The observability endpoint provides trace and metrics access.
"""

import gc
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


@pytest.fixture
def test_app() -> FastAPI:
    """Create a test app with the observability router."""
    from mcp_server_langgraph.api.v1.observability import observability_router

    app = FastAPI()
    app.include_router(observability_router, prefix="/api/v1")
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)


@pytest.mark.xdist_group(name="test_observability_router")
class TestTracesListEndpoint:
    """Tests for GET /api/v1/observability/traces endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_traces_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a request to /api/v1/observability/traces
        WHEN GET request is made
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_traces.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/observability/traces")

            assert response.status_code == 200

    def test_list_traces_returns_array(self, test_app: FastAPI) -> None:
        """
        GIVEN traces exist
        WHEN GET request is made
        THEN response should contain array of traces
        """
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_traces.return_value = (
                [{"trace_id": "abc123", "name": "Test Trace"}],
                None,
            )
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/observability/traces")
            data = response.json()

            assert "data" in data
            assert isinstance(data["data"], list)


@pytest.mark.xdist_group(name="test_observability_router")
class TestTraceGetEndpoint:
    """Tests for GET /api/v1/observability/traces/{id} endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_trace_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a trace exists
        WHEN GET request is made with trace ID
        THEN response should be 200 OK
        """
        trace_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_trace.return_value = {
                "trace_id": trace_id,
                "name": "Test Trace",
                "spans": [],
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/observability/traces/{trace_id}")

            assert response.status_code == 200

    def test_get_trace_not_found_returns_404(self, test_app: FastAPI) -> None:
        """
        GIVEN a trace does not exist
        WHEN GET request is made
        THEN response should be 404 Not Found
        """
        trace_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_trace.return_value = None
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/observability/traces/{trace_id}")

            assert response.status_code == 404


@pytest.mark.xdist_group(name="test_observability_router")
class TestMetricsEndpoint:
    """Tests for GET /api/v1/observability/metrics endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_metrics_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a request to /api/v1/observability/metrics
        WHEN GET request is made
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_metrics.return_value = {
                "requests_total": 1000,
                "errors_total": 10,
                "latency_p50": 0.1,
                "latency_p99": 0.5,
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/observability/metrics")

            assert response.status_code == 200

    def test_get_metrics_returns_data(self, test_app: FastAPI) -> None:
        """
        GIVEN metrics exist
        WHEN GET request is made
        THEN response should contain metrics data
        """
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_metrics.return_value = {
                "requests_total": 1000,
                "errors_total": 10,
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/observability/metrics")
            data = response.json()

            assert "requests_total" in data
            assert "errors_total" in data
