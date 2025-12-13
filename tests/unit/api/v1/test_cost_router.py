"""
Cost Router Unit Tests

Tests for /api/v1/cost endpoints per TDD methodology.
Tests written FIRST before implementation (RED phase).

The cost endpoint provides cost tracking and analysis.
"""

import gc
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


@pytest.fixture
def test_app() -> FastAPI:
    """Create a test app with the cost router."""
    from mcp_server_langgraph.api.v1.cost import cost_router

    app = FastAPI()
    app.include_router(cost_router, prefix="/api/v1")
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)


@pytest.mark.xdist_group(name="test_cost_router")
class TestCostSummaryEndpoint:
    """Tests for GET /api/v1/cost/summary endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_summary_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a request to /api/v1/cost/summary
        WHEN GET request is made
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_summary.return_value = {
                "total_cost": 125.50,
                "prompt_tokens": 50000,
                "completion_tokens": 25000,
                "period_start": "2025-01-01T00:00:00Z",
                "period_end": "2025-01-31T23:59:59Z",
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/summary")

            assert response.status_code == 200

    def test_get_summary_returns_cost_data(self, test_app: FastAPI) -> None:
        """
        GIVEN cost data exists
        WHEN GET request is made
        THEN response should contain cost summary
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_summary.return_value = {
                "total_cost": 125.50,
                "prompt_tokens": 50000,
                "completion_tokens": 25000,
            }
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/summary")
            data = response.json()

            assert "total_cost" in data
            assert "prompt_tokens" in data
            assert "completion_tokens" in data


@pytest.mark.xdist_group(name="test_cost_router")
class TestCostByModelEndpoint:
    """Tests for GET /api/v1/cost/by-model endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_by_model_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a request to /api/v1/cost/by-model
        WHEN GET request is made
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_by_model.return_value = [
                {"model": "gpt-4", "cost": 100.00, "requests": 500},
                {"model": "gpt-3.5-turbo", "cost": 25.50, "requests": 1000},
            ]
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/by-model")

            assert response.status_code == 200

    def test_get_by_model_returns_breakdown(self, test_app: FastAPI) -> None:
        """
        GIVEN cost data exists
        WHEN GET request is made
        THEN response should contain per-model breakdown
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_by_model.return_value = [
                {"model": "gpt-4", "cost": 100.00, "requests": 500},
            ]
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/by-model")
            data = response.json()

            assert isinstance(data, list)
            assert len(data) > 0
            assert "model" in data[0]
            assert "cost" in data[0]


@pytest.mark.xdist_group(name="test_cost_router")
class TestCostHistoryEndpoint:
    """Tests for GET /api/v1/cost/history endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_history_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a request to /api/v1/cost/history
        WHEN GET request is made with date range
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_history.return_value = [
                {"date": "2025-01-01", "cost": 10.00},
                {"date": "2025-01-02", "cost": 15.00},
            ]
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/history?start_date=2025-01-01&end_date=2025-01-31")

            assert response.status_code == 200

    def test_get_history_returns_time_series(self, test_app: FastAPI) -> None:
        """
        GIVEN cost data exists for date range
        WHEN GET request is made
        THEN response should contain time series data
        """
        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_history.return_value = [
                {"date": "2025-01-01", "cost": 10.00},
            ]
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/cost/history")
            data = response.json()

            assert isinstance(data, list)
