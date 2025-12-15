"""
Integration tests for Cost API endpoints.

Tests the full API path from HTTP request to response,
using the real FastAPI app with mocked storage backend.

Tests cover:
- GET /api/v1/cost/summary - Cost summary endpoint
- GET /api/v1/cost/by-model - Cost breakdown by model
- GET /api/v1/cost/history - Daily cost history
"""

import gc
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from mcp_server_langgraph.app import app
from mcp_server_langgraph.monitoring.cost_storage import (
    CostSummary,
    DailyCost,
    ModelCost,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_cost_storage():
    """Create a mock cost storage backend."""
    storage = MagicMock()
    storage.get_cost_summary = AsyncMock()  # async-mock-configured
    storage.get_cost_by_model = AsyncMock()  # async-mock-configured
    storage.get_cost_history = AsyncMock()  # async-mock-configured
    return storage


@pytest.fixture
def sample_cost_summary():
    """Sample CostSummary for testing."""
    return CostSummary(
        total_cost=Decimal("45.67"),
        total_prompt_tokens=10000,
        total_completion_tokens=5000,
        total_tokens=15000,
        request_count=100,
        period_start=datetime(2025, 1, 1, tzinfo=UTC),
        period_end=datetime(2025, 1, 31, tzinfo=UTC),
    )


@pytest.fixture
def sample_model_costs():
    """Sample list of ModelCost for testing."""
    return [
        ModelCost(
            model="gpt-4",
            provider="openai",
            total_cost=Decimal("30.00"),
            total_prompt_tokens=6000,
            total_completion_tokens=3000,
            request_count=50,
        ),
        ModelCost(
            model="claude-3-opus",
            provider="anthropic",
            total_cost=Decimal("15.67"),
            total_prompt_tokens=4000,
            total_completion_tokens=2000,
            request_count=50,
        ),
    ]


@pytest.fixture
def sample_daily_costs():
    """Sample list of DailyCost for testing."""
    return [
        DailyCost(
            date=datetime(2025, 1, 15, tzinfo=UTC),
            total_cost=Decimal("20.00"),
            total_tokens=5000,
            request_count=40,
        ),
        DailyCost(
            date=datetime(2025, 1, 16, tzinfo=UTC),
            total_cost=Decimal("25.67"),
            total_tokens=10000,
            request_count=60,
        ),
    ]


@pytest.mark.xdist_group(name="cost_api_integration")
class TestCostSummaryEndpoint:
    """Integration tests for GET /api/v1/cost/summary."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_cost_summary_returns_200(self, client, mock_cost_storage, sample_cost_summary):
        """GET /api/v1/cost/summary should return 200 with valid data."""
        mock_cost_storage.get_cost_summary.return_value = sample_cost_summary

        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            from mcp_server_langgraph.api.v1.cost import CostServiceImpl

            service = CostServiceImpl()
            service._storage = mock_cost_storage
            mock_get_service.return_value = service

            response = client.get("/api/v1/cost/summary")

        assert response.status_code == 200
        data = response.json()
        assert "total_cost" in data
        assert data["total_cost"] == 45.67

    def test_cost_summary_with_date_range(self, client, mock_cost_storage, sample_cost_summary):
        """GET /api/v1/cost/summary should accept date range parameters."""
        mock_cost_storage.get_cost_summary.return_value = sample_cost_summary

        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            from mcp_server_langgraph.api.v1.cost import CostServiceImpl

            service = CostServiceImpl()
            service._storage = mock_cost_storage
            mock_get_service.return_value = service

            response = client.get(
                "/api/v1/cost/summary",
                params={"start_date": "2025-01-01", "end_date": "2025-01-31"},
            )

        assert response.status_code == 200

    def test_cost_summary_includes_token_counts(self, client, mock_cost_storage, sample_cost_summary):
        """Response should include prompt and completion token counts."""
        mock_cost_storage.get_cost_summary.return_value = sample_cost_summary

        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            from mcp_server_langgraph.api.v1.cost import CostServiceImpl

            service = CostServiceImpl()
            service._storage = mock_cost_storage
            mock_get_service.return_value = service

            response = client.get("/api/v1/cost/summary")

        data = response.json()
        assert "prompt_tokens" in data
        assert "completion_tokens" in data
        assert data["prompt_tokens"] == 10000
        assert data["completion_tokens"] == 5000


@pytest.mark.xdist_group(name="cost_api_integration")
class TestCostByModelEndpoint:
    """Integration tests for GET /api/v1/cost/by-model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_cost_by_model_returns_200(self, client, mock_cost_storage, sample_model_costs):
        """GET /api/v1/cost/by-model should return 200 with list of models."""
        mock_cost_storage.get_cost_by_model.return_value = sample_model_costs

        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            from mcp_server_langgraph.api.v1.cost import CostServiceImpl

            service = CostServiceImpl()
            service._storage = mock_cost_storage
            mock_get_service.return_value = service

            response = client.get("/api/v1/cost/by-model")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_cost_by_model_includes_model_names(self, client, mock_cost_storage, sample_model_costs):
        """Response should include model names and costs."""
        mock_cost_storage.get_cost_by_model.return_value = sample_model_costs

        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            from mcp_server_langgraph.api.v1.cost import CostServiceImpl

            service = CostServiceImpl()
            service._storage = mock_cost_storage
            mock_get_service.return_value = service

            response = client.get("/api/v1/cost/by-model")

        data = response.json()
        models = [item["model"] for item in data]
        assert "gpt-4" in models
        assert "claude-3-opus" in models


@pytest.mark.xdist_group(name="cost_api_integration")
class TestCostHistoryEndpoint:
    """Integration tests for GET /api/v1/cost/history."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_cost_history_returns_200(self, client, mock_cost_storage, sample_daily_costs):
        """GET /api/v1/cost/history should return 200 with daily costs."""
        mock_cost_storage.get_cost_history.return_value = sample_daily_costs

        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            from mcp_server_langgraph.api.v1.cost import CostServiceImpl

            service = CostServiceImpl()
            service._storage = mock_cost_storage
            mock_get_service.return_value = service

            response = client.get("/api/v1/cost/history")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_cost_history_includes_dates(self, client, mock_cost_storage, sample_daily_costs):
        """Response should include dates for each day."""
        mock_cost_storage.get_cost_history.return_value = sample_daily_costs

        with patch("mcp_server_langgraph.api.v1.cost.get_cost_service") as mock_get_service:
            from mcp_server_langgraph.api.v1.cost import CostServiceImpl

            service = CostServiceImpl()
            service._storage = mock_cost_storage
            mock_get_service.return_value = service

            response = client.get("/api/v1/cost/history")

        data = response.json()
        for item in data:
            assert "date" in item
            assert "cost" in item
