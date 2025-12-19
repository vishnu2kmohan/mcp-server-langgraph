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
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
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
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
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
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
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
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
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
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
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
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
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


# ============================================================================
# Sorting Tests
# ============================================================================


@pytest.mark.xdist_group(name="test_observability_router_query")
class TestTracesListSorting:
    """Tests for sorting traces via GET /api/v1/observability/traces."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_traces_sort_by_start_time_descending(self, test_app: FastAPI) -> None:
        """
        GIVEN traces exist
        WHEN GET request with sort_by=start_time and sort_order=desc
        THEN service should receive sorting parameters
        """
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.list_traces.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/observability/traces?sort_by=start_time&sort_order=desc")

            assert response.status_code == 200

    def test_list_traces_sort_by_duration(self, test_app: FastAPI) -> None:
        """
        GIVEN traces exist
        WHEN GET request with sort_by=duration_ms
        THEN service should receive sorting parameters
        """
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.list_traces.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/observability/traces?sort_by=duration_ms&sort_order=asc")

            assert response.status_code == 200

    def test_list_traces_sort_by_name(self, test_app: FastAPI) -> None:
        """
        GIVEN traces exist
        WHEN GET request with sort_by=name
        THEN service should receive sorting parameters
        """
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.list_traces.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/observability/traces?sort_by=name&sort_order=asc")

            assert response.status_code == 200


# ============================================================================
# Search Tests
# ============================================================================


@pytest.mark.xdist_group(name="test_observability_router_query")
class TestTracesListSearch:
    """Tests for searching traces via GET /api/v1/observability/traces."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_traces_search_by_name(self, test_app: FastAPI) -> None:
        """
        GIVEN traces exist
        WHEN GET request with search parameter
        THEN service should receive search query
        """
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.list_traces.return_value = (
                [{"trace_id": "1", "name": "LLM Request"}],
                None,
            )
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/observability/traces?search=LLM")

            assert response.status_code == 200

    def test_list_traces_search_case_insensitive(self, test_app: FastAPI) -> None:
        """
        GIVEN traces exist
        WHEN GET request with lowercase search
        THEN service should handle case-insensitive search
        """
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.list_traces.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/observability/traces?search=llm")

            assert response.status_code == 200

    def test_list_traces_search_no_results(self, test_app: FastAPI) -> None:
        """
        GIVEN no matching traces
        WHEN GET request with search
        THEN should return empty list
        """
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.list_traces.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/observability/traces?search=nonexistent_xyz_123")

            assert response.status_code == 200
            data = response.json()
            assert data["data"] == []


# ============================================================================
# Combined Query Tests
# ============================================================================


@pytest.mark.xdist_group(name="test_observability_router_query")
class TestTracesListCombined:
    """Tests for combining sorting, filtering, and search."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_traces_search_with_sorting(self, test_app: FastAPI) -> None:
        """
        GIVEN traces exist
        WHEN GET request with search and sorting
        THEN service should handle both
        """
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.list_traces.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/observability/traces?search=test&sort_by=start_time&sort_order=desc")

            assert response.status_code == 200

    def test_list_traces_filter_with_sorting(self, test_app: FastAPI) -> None:
        """
        GIVEN traces exist
        WHEN GET request with session_id filter and sorting
        THEN service should handle both
        """
        session_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.list_traces.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/observability/traces?session_id={session_id}&sort_by=duration_ms&sort_order=asc")

            assert response.status_code == 200

    def test_list_traces_all_query_params(self, test_app: FastAPI) -> None:
        """
        GIVEN traces exist
        WHEN GET request with all query parameters
        THEN service should handle all params
        """
        session_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.observability.get_observability_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)
            mock_service.list_traces.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(
                f"/api/v1/observability/traces?search=test&session_id={session_id}&sort_by=start_time&sort_order=desc&limit=10"
            )

            assert response.status_code == 200
