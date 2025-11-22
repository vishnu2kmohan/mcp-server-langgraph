"""
Tests for Cost API Endpoints

Comprehensive test suite for FastAPI cost monitoring endpoints following TDD principles.

Tests cover:
- GET /api/cost/summary - Aggregated cost summary
- GET /api/cost/usage - Detailed usage records
- GET /api/cost/budget/{id} - Budget status
- POST /api/cost/budget - Create budget
- GET /api/cost/trends - Time-series trends
- GET /api/cost/export - CSV/JSON export
- Edge cases and error handling
"""

import gc
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from mcp_server_langgraph.monitoring.budget_monitor import BudgetPeriod, BudgetStatus
from mcp_server_langgraph.monitoring.cost_api import app
from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage

pytestmark = pytest.mark.unit

# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def cost_api_client():
    """FastAPI test client for cost API."""
    return TestClient(app)


@pytest.fixture
def sample_token_usage_records():
    """Sample token usage records for testing."""
    return [
        TokenUsage(
            timestamp=datetime.now(timezone.utc),
            user_id="user1",
            session_id="session1",
            model="claude-3-5-sonnet-20241022",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
            estimated_cost_usd=Decimal("0.0105"),
            feature="chat",
        ),
        TokenUsage(
            timestamp=datetime.now(timezone.utc),
            user_id="user2",
            session_id="session2",
            model="gpt-4-turbo",
            provider="openai",
            prompt_tokens=2000,
            completion_tokens=1000,
            total_tokens=3000,
            estimated_cost_usd=Decimal("0.050"),
            feature="tool_execution",
        ),
    ]


# ==============================================================================
# Test Root Endpoint
# ==============================================================================


@pytest.mark.unit
def test_root_returns_api_information(cost_api_client):
    """Test GET / returns API information."""
    # Act
    response = cost_api_client.get("/")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Cost Monitoring API"
    assert data["version"] == "1.0.0"
    assert "features" in data


@pytest.mark.unit
def test_health_check_returns_healthy(cost_api_client):
    """Test GET /health returns healthy status."""
    # Act
    response = cost_api_client.get("/health")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "cost-monitoring-api"


# ==============================================================================
# Test Cost Summary Endpoint
# ==============================================================================


@pytest.mark.xdist_group(name="cost_api_summary_tests")
class TestCostSummaryEndpoint:
    """Test suite for GET /api/cost/summary endpoint."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_get_cost_summary_returns_aggregated_data(self, cost_api_client, sample_token_usage_records):
        """Test GET /api/cost/summary returns aggregated cost data."""
        # Arrange - Mock cost collector
        with patch("mcp_server_langgraph.monitoring.cost_api.get_cost_collector") as mock_get_collector:
            mock_collector = MagicMock()
            mock_collector.get_records = AsyncMock(return_value=sample_token_usage_records)
            mock_get_collector.return_value = mock_collector

            # Act
            response = cost_api_client.get("/api/cost/summary?period=month")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "total_cost_usd" in data
            assert "total_tokens" in data
            assert "request_count" in data
            assert "by_model" in data
            assert "by_user" in data

    @pytest.mark.unit
    def test_get_cost_summary_aggregates_by_model(self, cost_api_client, sample_token_usage_records):
        """Test GET /api/cost/summary aggregates costs by model."""
        # Arrange
        with patch("mcp_server_langgraph.monitoring.cost_api.get_cost_collector") as mock_get_collector:
            mock_collector = MagicMock()
            mock_collector.get_records = AsyncMock(return_value=sample_token_usage_records)
            mock_get_collector.return_value = mock_collector

            # Act
            response = cost_api_client.get("/api/cost/summary?period=month&group_by=model")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "claude-3-5-sonnet-20241022" in data["by_model"]
            assert "gpt-4-turbo" in data["by_model"]

    @pytest.mark.unit
    def test_get_cost_summary_supports_different_periods(self, cost_api_client):
        """Test GET /api/cost/summary supports day, week, month periods."""
        # Arrange
        with patch("mcp_server_langgraph.monitoring.cost_api.get_cost_collector") as mock_get_collector:
            mock_collector = MagicMock()
            mock_collector.get_records = AsyncMock(return_value=[])
            mock_get_collector.return_value = mock_collector

            # Act & Assert - Day
            response = cost_api_client.get("/api/cost/summary?period=day")
            assert response.status_code == status.HTTP_200_OK

            # Act & Assert - Week
            response = cost_api_client.get("/api/cost/summary?period=week")
            assert response.status_code == status.HTTP_200_OK

            # Act & Assert - Month
            response = cost_api_client.get("/api/cost/summary?period=month")
            assert response.status_code == status.HTTP_200_OK


# ==============================================================================
# Test Usage Records Endpoint
# ==============================================================================


@pytest.mark.xdist_group(name="cost_api_usage_tests")
class TestUsageRecordsEndpoint:
    """Test suite for GET /api/cost/usage endpoint."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_get_usage_records_returns_detailed_records(self, cost_api_client, sample_token_usage_records):
        """Test GET /api/cost/usage returns detailed usage records."""
        # Arrange
        with patch("mcp_server_langgraph.monitoring.cost_api.get_cost_collector") as mock_get_collector:
            mock_collector = MagicMock()
            mock_collector.get_records = AsyncMock(return_value=sample_token_usage_records)
            mock_get_collector.return_value = mock_collector

            # Act
            response = cost_api_client.get("/api/cost/usage")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 2
            assert data[0]["user_id"] in ["user1", "user2"]
            assert "estimated_cost_usd" in data[0]

    @pytest.mark.unit
    def test_get_usage_records_filters_by_user_id(self, cost_api_client, sample_token_usage_records):
        """Test GET /api/cost/usage filters by user_id."""
        # Arrange
        user1_records = [r for r in sample_token_usage_records if r.user_id == "user1"]

        with patch("mcp_server_langgraph.monitoring.cost_api.get_cost_collector") as mock_get_collector:
            mock_collector = MagicMock()
            mock_collector.get_records = AsyncMock(return_value=user1_records)
            mock_get_collector.return_value = mock_collector

            # Act
            response = cost_api_client.get("/api/cost/usage?user_id=user1")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert all(record["user_id"] == "user1" for record in data)

    @pytest.mark.unit
    def test_get_usage_records_filters_by_model(self, cost_api_client, sample_token_usage_records):
        """Test GET /api/cost/usage filters by model."""
        # Arrange
        sonnet_records = [r for r in sample_token_usage_records if r.model == "claude-3-5-sonnet-20241022"]

        with patch("mcp_server_langgraph.monitoring.cost_api.get_cost_collector") as mock_get_collector:
            mock_collector = MagicMock()
            mock_collector.get_records = AsyncMock(return_value=sonnet_records)
            mock_get_collector.return_value = mock_collector

            # Act
            response = cost_api_client.get("/api/cost/usage?model=claude-3-5-sonnet-20241022")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert all(record["model"] == "claude-3-5-sonnet-20241022" for record in data)

    @pytest.mark.unit
    def test_get_usage_records_respects_limit_parameter(self, cost_api_client, sample_token_usage_records):
        """Test GET /api/cost/usage respects limit parameter."""
        # Arrange
        with patch("mcp_server_langgraph.monitoring.cost_api.get_cost_collector") as mock_get_collector:
            mock_collector = MagicMock()
            mock_collector.get_records = AsyncMock(return_value=sample_token_usage_records)
            mock_get_collector.return_value = mock_collector

            # Act
            response = cost_api_client.get("/api/cost/usage?limit=1")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) <= 1


# ==============================================================================
# Test Budget Endpoints
# ==============================================================================


@pytest.mark.xdist_group(name="cost_api_budget_tests")
class TestBudgetEndpoints:
    """Test suite for budget-related endpoints."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_create_budget_creates_new_budget(self, cost_api_client):
        """Test POST /api/cost/budget creates new budget."""
        # Arrange
        budget_data = {
            "id": "test_budget",
            "name": "Test Budget",
            "limit_usd": "1000.00",
            "period": "monthly",
            "alert_thresholds": ["0.75", "0.90"],
        }

        with patch("mcp_server_langgraph.monitoring.cost_api.get_budget_monitor") as mock_get_monitor:
            mock_monitor = MagicMock()
            mock_budget = MagicMock()
            mock_budget.id = "test_budget"
            mock_budget.name = "Test Budget"
            mock_budget.limit_usd = Decimal("1000.00")
            mock_budget.period = BudgetPeriod.MONTHLY
            mock_budget.start_date = datetime.now(timezone.utc)
            mock_budget.end_date = None
            mock_budget.alert_thresholds = [Decimal("0.75"), Decimal("0.90")]
            mock_budget.enabled = True
            mock_budget.metadata = {}

            mock_monitor.create_budget = AsyncMock(return_value=mock_budget)
            mock_get_monitor.return_value = mock_monitor

            # Act
            response = cost_api_client.post("/api/cost/budget", json=budget_data)

            # Assert
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["id"] == "test_budget"
            assert data["name"] == "Test Budget"

    @pytest.mark.unit
    def test_get_budget_status_returns_budget_details(self, cost_api_client):
        """Test GET /api/cost/budget/{id} returns budget status."""
        # Arrange
        mock_status = BudgetStatus(
            budget_id="test_budget",
            budget_name="Test Budget",
            limit_usd=Decimal("1000.00"),
            spent_usd=Decimal("750.00"),
            remaining_usd=Decimal("250.00"),
            utilization=Decimal("0.75"),
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc),
            is_exceeded=False,
            days_remaining=15,
            projected_end_of_period_spend=Decimal("900.00"),
        )

        with patch("mcp_server_langgraph.monitoring.cost_api.get_budget_monitor") as mock_get_monitor:
            mock_monitor = MagicMock()
            mock_monitor.get_budget_status = AsyncMock(return_value=mock_status)
            mock_get_monitor.return_value = mock_monitor

            # Act
            response = cost_api_client.get("/api/cost/budget/test_budget")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["budget_id"] == "test_budget"
            assert data["spent_usd"] == "750.00"
            assert data["utilization"] == "0.75"

    @pytest.mark.unit
    def test_get_budget_status_returns_404_for_nonexistent_budget(self, cost_api_client):
        """Test GET /api/cost/budget/{id} returns 404 for non-existent budget."""
        # Arrange
        with patch("mcp_server_langgraph.monitoring.cost_api.get_budget_monitor") as mock_get_monitor:
            mock_monitor = MagicMock()
            mock_monitor.get_budget_status = AsyncMock(return_value=None)
            mock_get_monitor.return_value = mock_monitor

            # Act
            response = cost_api_client.get("/api/cost/budget/nonexistent")

            # Assert
            assert response.status_code == status.HTTP_404_NOT_FOUND


# ==============================================================================
# Test Trends Endpoint
# ==============================================================================


@pytest.mark.xdist_group(name="cost_api_trends_tests")
class TestTrendsEndpoint:
    """Test suite for GET /api/cost/trends endpoint."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_get_cost_trends_returns_time_series_data(self, cost_api_client):
        """Test GET /api/cost/trends returns time-series data."""
        # Arrange
        with patch("mcp_server_langgraph.monitoring.cost_api.get_cost_collector") as mock_get_collector:
            mock_collector = MagicMock()
            mock_collector.get_records = AsyncMock(return_value=[])
            mock_get_collector.return_value = mock_collector

            # Act
            response = cost_api_client.get("/api/cost/trends?metric=total_cost&period=7d")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["metric"] == "total_cost"
            assert data["period"] == "7d"
            assert "data_points" in data
            assert isinstance(data["data_points"], list)

    @pytest.mark.unit
    def test_get_cost_trends_supports_different_metrics(self, cost_api_client):
        """Test GET /api/cost/trends supports total_cost and token_usage metrics."""
        # Arrange
        with patch("mcp_server_langgraph.monitoring.cost_api.get_cost_collector") as mock_get_collector:
            mock_collector = MagicMock()
            mock_collector.get_records = AsyncMock(return_value=[])
            mock_get_collector.return_value = mock_collector

            # Act & Assert - Total cost
            response = cost_api_client.get("/api/cost/trends?metric=total_cost&period=7d")
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["metric"] == "total_cost"

            # Act & Assert - Token usage
            response = cost_api_client.get("/api/cost/trends?metric=token_usage&period=7d")
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["metric"] == "token_usage"

    @pytest.mark.unit
    def test_get_cost_trends_supports_different_periods(self, cost_api_client):
        """Test GET /api/cost/trends supports 7d, 30d, 90d periods."""
        # Arrange
        with patch("mcp_server_langgraph.monitoring.cost_api.get_cost_collector") as mock_get_collector:
            mock_collector = MagicMock()
            mock_collector.get_records = AsyncMock(return_value=[])
            mock_get_collector.return_value = mock_collector

            # Act & Assert - 7 days
            response = cost_api_client.get("/api/cost/trends?period=7d")
            assert response.status_code == status.HTTP_200_OK
            assert len(response.json()["data_points"]) == 7

            # Act & Assert - 30 days
            response = cost_api_client.get("/api/cost/trends?period=30d")
            assert response.status_code == status.HTTP_200_OK
            assert len(response.json()["data_points"]) == 30


# ==============================================================================
# Test Export Endpoint
# ==============================================================================


@pytest.mark.xdist_group(name="cost_api_export_tests")
class TestExportEndpoint:
    """Test suite for GET /api/cost/export endpoint."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_export_cost_data_as_csv(self, cost_api_client, sample_token_usage_records):
        """Test GET /api/cost/export?format=csv exports CSV."""
        # Arrange
        with patch("mcp_server_langgraph.monitoring.cost_api.get_cost_collector") as mock_get_collector:
            mock_collector = MagicMock()
            mock_collector.get_records = AsyncMock(return_value=sample_token_usage_records)
            mock_get_collector.return_value = mock_collector

            # Act
            response = cost_api_client.get("/api/cost/export?format=csv&period=month")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"] == "text/csv; charset=utf-8"
            assert "attachment" in response.headers["content-disposition"]
            assert "cost_export_month.csv" in response.headers["content-disposition"]
            # Verify CSV structure
            assert "timestamp,user_id,session_id,model,provider" in response.text
            assert "user1" in response.text or "user2" in response.text

    @pytest.mark.unit
    def test_export_cost_data_as_json(self, cost_api_client, sample_token_usage_records):
        """Test GET /api/cost/export?format=json exports JSON."""
        # Arrange
        with patch("mcp_server_langgraph.monitoring.cost_api.get_cost_collector") as mock_get_collector:
            mock_collector = MagicMock()
            mock_collector.get_records = AsyncMock(return_value=sample_token_usage_records)
            mock_get_collector.return_value = mock_collector

            # Act
            response = cost_api_client.get("/api/cost/export?format=json&period=month")

            # Assert
            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"] == "application/json"
            assert "attachment" in response.headers["content-disposition"]
            assert "cost_export_month.json" in response.headers["content-disposition"]
            # Verify JSON structure
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2

    @pytest.mark.unit
    def test_export_cost_data_returns_400_for_unsupported_format(self, cost_api_client):
        """Test GET /api/cost/export returns 400 for unsupported format."""
        # Arrange
        with patch("mcp_server_langgraph.monitoring.cost_api.get_cost_collector") as mock_get_collector:
            mock_collector = MagicMock()
            mock_collector.get_records = AsyncMock(return_value=[])
            mock_get_collector.return_value = mock_collector

            # Act
            response = cost_api_client.get("/api/cost/export?format=xml")

            # Assert
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Unsupported format" in response.json()["detail"]
