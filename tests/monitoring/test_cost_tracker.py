"""
Tests for Cost Tracking System

Comprehensive test suite for LLM cost monitoring following TDD principles.

Tests cover:
- Token usage recording
- Cost calculation
- Cost aggregation by dimensions
- Budget monitoring
- Alert triggering
- API endpoints
- Edge cases
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def sample_token_usage():
    """Sample token usage data for testing."""
    return {
        "timestamp": datetime.now(timezone.utc),
        "user_id": "user123",
        "session_id": "session456",
        "model": "claude-3-5-sonnet-20241022",
        "provider": "anthropic",
        "prompt_tokens": 1000,
        "completion_tokens": 500,
        "estimated_cost_usd": Decimal("0.0105"),  # (1000/1000)*0.003 + (500/1000)*0.015
        "feature": "chat",
        "metadata": {},
    }


@pytest.fixture
def sample_budget():
    """Sample budget for testing."""
    return {
        "id": "budget_001",
        "name": "Development Team Monthly Budget",
        "limit_usd": Decimal("1000.00"),
        "period": "monthly",
        "start_date": datetime.now(timezone.utc).replace(day=1),
        "alert_thresholds": [Decimal("0.75"), Decimal("0.90")],
    }


# ==============================================================================
# Test Cost Calculation
# ==============================================================================


@pytest.mark.unit
def test_calculate_cost_for_anthropic_sonnet():
    """Test cost calculation for Anthropic Claude 3.5 Sonnet."""
    # Arrange
    from mcp_server_langgraph.monitoring.pricing import calculate_cost

    # Act
    cost = calculate_cost(
        model="claude-3-5-sonnet-20241022",
        provider="anthropic",
        prompt_tokens=1000,
        completion_tokens=500,
    )

    # Assert
    # Input: 1000 tokens * $0.003/1K = $0.003
    # Output: 500 tokens * $0.015/1K = $0.0075
    # Total: $0.0105
    assert cost == Decimal("0.0105")


@pytest.mark.unit
def test_calculate_cost_for_anthropic_haiku():
    """Test cost calculation for Anthropic Claude 3.5 Haiku (cheaper model)."""
    from mcp_server_langgraph.monitoring.pricing import calculate_cost

    cost = calculate_cost(
        model="claude-3-5-haiku-20241022",
        provider="anthropic",
        prompt_tokens=1000,
        completion_tokens=500,
    )

    # Input: 1000 * $0.0008/1K = $0.0008
    # Output: 500 * $0.004/1K = $0.002
    # Total: $0.0028
    assert cost == Decimal("0.0028")


@pytest.mark.unit
def test_calculate_cost_for_openai_gpt4_turbo():
    """Test cost calculation for OpenAI GPT-4 Turbo."""
    from mcp_server_langgraph.monitoring.pricing import calculate_cost

    cost = calculate_cost(
        model="gpt-4-turbo",
        provider="openai",
        prompt_tokens=1000,
        completion_tokens=500,
    )

    # Input: 1000 * $0.01/1K = $0.01
    # Output: 500 * $0.03/1K = $0.015
    # Total: $0.025
    assert cost == Decimal("0.025")


@pytest.mark.unit
def test_calculate_cost_for_google_gemini_flash():
    """Test cost calculation for Google Gemini 2.5 Flash (free tier)."""
    from mcp_server_langgraph.monitoring.pricing import calculate_cost

    cost = calculate_cost(
        model="gemini-2.5-flash-preview-001",
        provider="google",
        prompt_tokens=10000,  # Higher volume for free tier
        completion_tokens=5000,
    )

    # Input: 10000 * $0.000075/1K = $0.00075
    # Output: 5000 * $0.0003/1K = $0.0015
    # Total: $0.00225
    assert cost == Decimal("0.00225")


@pytest.mark.unit
def test_calculate_cost_with_zero_tokens_returns_zero():
    """Test cost calculation with zero tokens."""
    from mcp_server_langgraph.monitoring.pricing import calculate_cost

    cost = calculate_cost(
        model="claude-3-5-sonnet-20241022",
        provider="anthropic",
        prompt_tokens=0,
        completion_tokens=0,
    )

    assert cost == Decimal("0")


@pytest.mark.unit
def test_calculate_cost_with_unknown_model_raises_key_error():
    """Test cost calculation with unknown model raises KeyError."""
    from mcp_server_langgraph.monitoring.pricing import calculate_cost

    with pytest.raises(KeyError):
        calculate_cost(
            model="unknown-model",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
        )


# ==============================================================================
# Test CostMetricsCollector
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cost_metrics_collector_records_usage(sample_token_usage):
    """Test CostMetricsCollector records token usage."""
    from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

    # Arrange
    collector = CostMetricsCollector()

    # Act
    await collector.record_usage(**sample_token_usage)

    # Assert
    # Verify record was saved (implementation-dependent)
    assert collector.total_records > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cost_metrics_collector_calculates_cost_automatically():
    """Test collector automatically calculates cost if not provided."""
    from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

    collector = CostMetricsCollector()

    # Act - record without explicit cost
    await collector.record_usage(
        timestamp=datetime.now(timezone.utc),
        user_id="user123",
        session_id="session456",
        model="claude-3-5-sonnet-20241022",
        provider="anthropic",
        prompt_tokens=1000,
        completion_tokens=500,
        # estimated_cost_usd not provided
    )

    # Assert - cost should be calculated
    latest_record = await collector.get_latest_record()
    assert latest_record.estimated_cost_usd == Decimal("0.0105")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cost_metrics_collector_increments_prometheus_counters():
    """Test collector updates Prometheus metrics."""
    from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

    collector = CostMetricsCollector()

    with patch("mcp_server_langgraph.monitoring.cost_tracker.llm_token_usage") as mock_counter:
        await collector.record_usage(
            timestamp=datetime.now(timezone.utc),
            user_id="user123",
            session_id="session456",
            model="claude-3-5-sonnet-20241022",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
        )

        # Assert Prometheus counter was incremented
        assert mock_counter.labels.called


# ==============================================================================
# Test CostAggregator
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cost_aggregator_sums_by_model():
    """Test CostAggregator aggregates costs by model."""
    from mcp_server_langgraph.monitoring.cost_tracker import CostAggregator

    aggregator = CostAggregator()

    # Arrange - mock data
    records = [
        {"model": "claude-3-5-sonnet-20241022", "cost": Decimal("0.01")},
        {"model": "claude-3-5-sonnet-20241022", "cost": Decimal("0.02")},
        {"model": "gpt-4-turbo", "cost": Decimal("0.03")},
    ]

    # Act
    summary = await aggregator.aggregate_by_model(records)

    # Assert
    assert summary["claude-3-5-sonnet-20241022"] == Decimal("0.03")
    assert summary["gpt-4-turbo"] == Decimal("0.03")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cost_aggregator_sums_by_user():
    """Test CostAggregator aggregates costs by user."""
    from mcp_server_langgraph.monitoring.cost_tracker import CostAggregator

    aggregator = CostAggregator()

    records = [
        {"user_id": "user1", "cost": Decimal("0.01")},
        {"user_id": "user1", "cost": Decimal("0.02")},
        {"user_id": "user2", "cost": Decimal("0.03")},
    ]

    summary = await aggregator.aggregate_by_user(records)

    assert summary["user1"] == Decimal("0.03")
    assert summary["user2"] == Decimal("0.03")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cost_aggregator_sums_by_feature():
    """Test CostAggregator aggregates costs by feature."""
    from mcp_server_langgraph.monitoring.cost_tracker import CostAggregator

    aggregator = CostAggregator()

    records = [
        {"feature": "chat", "cost": Decimal("0.01")},
        {"feature": "chat", "cost": Decimal("0.02")},
        {"feature": "tool_execution", "cost": Decimal("0.05")},
    ]

    summary = await aggregator.aggregate_by_feature(records)

    assert summary["chat"] == Decimal("0.03")
    assert summary["tool_execution"] == Decimal("0.05")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cost_aggregator_calculates_total_cost():
    """Test CostAggregator calculates total cost."""
    from mcp_server_langgraph.monitoring.cost_tracker import CostAggregator

    aggregator = CostAggregator()

    records = [
        {"cost": Decimal("0.01")},
        {"cost": Decimal("0.02")},
        {"cost": Decimal("0.03")},
    ]

    total = await aggregator.calculate_total(records)

    assert total == Decimal("0.06")


# ==============================================================================
# Test BudgetMonitor
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_budget_monitor_detects_75_percent_utilization(sample_budget):
    """Test BudgetMonitor sends warning at 75% budget utilization."""
    from mcp_server_langgraph.monitoring.budget_monitor import BudgetMonitor, BudgetPeriod

    monitor = BudgetMonitor()

    # Create budget first
    await monitor.create_budget(
        id=sample_budget["id"],
        name=sample_budget["name"],
        limit_usd=sample_budget["limit_usd"],
        period=BudgetPeriod.MONTHLY,
        start_date=sample_budget["start_date"],
        alert_thresholds=sample_budget["alert_thresholds"],
    )

    # Mock current spend at 75%
    with patch.object(monitor, "get_period_spend", return_value=Decimal("750.00")):
        with patch.object(monitor, "send_alert") as mock_alert:
            await monitor.check_budget(sample_budget["id"])

            # Assert warning alert sent
            mock_alert.assert_called_once()
            call_args = mock_alert.call_args[1]
            assert call_args["level"] == "warning"
            assert "75" in call_args["message"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_budget_monitor_detects_90_percent_utilization(sample_budget):
    """Test BudgetMonitor sends critical alert at 90% budget utilization."""
    from mcp_server_langgraph.monitoring.budget_monitor import BudgetMonitor, BudgetPeriod

    monitor = BudgetMonitor()

    # Create budget first
    await monitor.create_budget(
        id=sample_budget["id"],
        name=sample_budget["name"],
        limit_usd=sample_budget["limit_usd"],
        period=BudgetPeriod.MONTHLY,
        start_date=sample_budget["start_date"],
        alert_thresholds=sample_budget["alert_thresholds"],
    )

    with patch.object(monitor, "get_period_spend", return_value=Decimal("900.00")):
        with patch.object(monitor, "send_alert") as mock_alert:
            await monitor.check_budget(sample_budget["id"])

            mock_alert.assert_called_once()
            call_args = mock_alert.call_args[1]
            assert call_args["level"] == "critical"
            assert "90" in call_args["message"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_budget_monitor_no_alert_below_threshold(sample_budget):
    """Test BudgetMonitor does not alert below 75% utilization."""
    from mcp_server_langgraph.monitoring.budget_monitor import BudgetMonitor, BudgetPeriod

    monitor = BudgetMonitor()

    # Create budget first
    await monitor.create_budget(
        id=sample_budget["id"],
        name=sample_budget["name"],
        limit_usd=sample_budget["limit_usd"],
        period=BudgetPeriod.MONTHLY,
        start_date=sample_budget["start_date"],
        alert_thresholds=sample_budget["alert_thresholds"],
    )

    with patch.object(monitor, "get_period_spend", return_value=Decimal("500.00")):  # 50%
        with patch.object(monitor, "send_alert") as mock_alert:
            await monitor.check_budget(sample_budget["id"])

            mock_alert.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_budget_monitor_handles_budget_exceeded():
    """Test BudgetMonitor handles budget being exceeded."""
    from datetime import datetime, timezone

    from mcp_server_langgraph.monitoring.budget_monitor import BudgetMonitor, BudgetPeriod

    monitor = BudgetMonitor()

    # Create budget first
    await monitor.create_budget(
        id="budget_001",
        name="Test Budget",
        limit_usd=Decimal("1000.00"),
        period=BudgetPeriod.MONTHLY,
        start_date=datetime.now(timezone.utc).replace(day=1),
        alert_thresholds=[Decimal("0.75"), Decimal("0.90")],
    )

    with patch.object(monitor, "get_period_spend", return_value=Decimal("1500.00")):  # 150%
        with patch.object(monitor, "send_alert") as mock_alert:
            await monitor.check_budget("budget_001")

            # Should send critical alert for exceeded budget
            assert mock_alert.called


# ==============================================================================
# Test Cost API Endpoints
# ==============================================================================


@pytest.fixture
def cost_api_client():
    """FastAPI test client for cost API."""
    from mcp_server_langgraph.monitoring.cost_api import app

    return TestClient(app)


@pytest.mark.xfail(
    strict=True,
    reason="Cost API endpoints not implemented yet. "
    "When cost tracking API is implemented, this test will XPASS and fail CI.",
)
@pytest.mark.unit
def test_get_cost_summary_returns_aggregated_data(cost_api_client):
    """Test GET /api/cost/summary returns aggregated cost data."""
    # Mock data
    with patch("mcp_server_langgraph.monitoring.cost_api.get_cost_summary") as mock_summary:
        mock_summary.return_value = {
            "period_start": datetime.now(timezone.utc),
            "period_end": datetime.now(timezone.utc),
            "total_cost_usd": Decimal("123.45"),
            "total_tokens": 100000,
            "request_count": 500,
            "by_model": {"claude-3-5-sonnet-20241022": Decimal("100.00")},
            "by_user": {"user1": Decimal("50.00")},
        }

        response = cost_api_client.get("/api/cost/summary?period=month")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_cost_usd"] == "123.45"
        assert data["request_count"] == 500


@pytest.mark.skip(reason="Cost API endpoints not implemented yet")
@pytest.mark.unit
def test_get_cost_usage_filters_by_user(cost_api_client):
    """Test GET /api/cost/usage filters by user_id."""
    with patch("mcp_server_langgraph.monitoring.cost_api.get_usage_records") as mock_records:
        mock_records.return_value = [{"user_id": "user123", "cost": "0.01"}]

        response = cost_api_client.get("/api/cost/usage?user_id=user123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) > 0
        assert data[0]["user_id"] == "user123"


@pytest.mark.skip(reason="Cost API endpoints not implemented yet")
@pytest.mark.unit
def test_create_budget_creates_new_budget(cost_api_client):
    """Test POST /api/cost/budget creates new budget."""
    budget_data = {
        "name": "Q4 Budget",
        "limit_usd": "5000.00",
        "period": "quarterly",
        "alert_thresholds": ["0.75", "0.90"],
    }

    with patch("mcp_server_langgraph.monitoring.cost_api.create_budget") as mock_create:
        mock_create.return_value = {"id": "budget_new", **budget_data}

        response = cost_api_client.post("/api/cost/budget", json=budget_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Q4 Budget"
        assert data["limit_usd"] == "5000.00"


@pytest.mark.skip(reason="Cost API get_trends function not implemented yet")
@pytest.mark.unit
def test_get_cost_trends_returns_time_series_data(cost_api_client):
    """Test GET /api/cost/trends returns time-series data."""
    with patch("mcp_server_langgraph.monitoring.cost_api.get_trends") as mock_trends:
        mock_trends.return_value = {
            "metric": "total_cost",
            "period": "7d",
            "data_points": [
                {"timestamp": "2025-11-01T00:00:00Z", "value": "10.50"},
                {"timestamp": "2025-11-02T00:00:00Z", "value": "12.30"},
            ],
        }

        response = cost_api_client.get("/api/cost/trends?metric=total_cost&period=7d")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["metric"] == "total_cost"
        assert len(data["data_points"]) == 2


@pytest.mark.skip(reason="Cost API export_costs function not implemented yet")
@pytest.mark.unit
def test_export_cost_data_as_csv(cost_api_client):
    """Test GET /api/cost/export?format=csv exports CSV."""
    with patch("mcp_server_langgraph.monitoring.cost_api.export_costs") as mock_export:
        mock_export.return_value = "timestamp,user_id,cost\n2025-11-01,user1,0.01\n"

        response = cost_api_client.get("/api/cost/export?format=csv")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/csv"
        assert "timestamp,user_id,cost" in response.text


# ==============================================================================
# Integration Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_end_to_end_cost_tracking_flow():
    """Test complete flow: record usage → aggregate → check budget."""
    from mcp_server_langgraph.monitoring.budget_monitor import BudgetMonitor
    from mcp_server_langgraph.monitoring.cost_tracker import CostAggregator, CostMetricsCollector

    # Step 1: Record usage
    collector = CostMetricsCollector()
    await collector.record_usage(
        timestamp=datetime.now(timezone.utc),
        user_id="user123",
        session_id="session456",
        model="claude-3-5-sonnet-20241022",
        provider="anthropic",
        prompt_tokens=10000,
        completion_tokens=5000,
    )

    # Step 2: Aggregate costs
    aggregator = CostAggregator()
    records = await collector.get_records(period="day")
    # Convert TokenUsage objects to dicts for aggregator
    record_dicts = [{"cost": r.estimated_cost_usd} for r in records]
    total_cost = await aggregator.calculate_total(record_dicts)

    # Step 3: Check budget
    monitor = BudgetMonitor()
    with patch.object(monitor, "get_period_spend", return_value=total_cost):
        # Should not alert for small spend
        with patch.object(monitor, "send_alert") as mock_alert:
            await monitor.check_budget("budget_001")

            # Depends on total cost vs budget
            # For this test, assume low spend
            assert mock_alert.call_count == 0


# ==============================================================================
# Edge Cases
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cost_tracker_handles_concurrent_writes():
    """Test CostMetricsCollector handles concurrent usage recording."""
    import asyncio

    from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

    collector = CostMetricsCollector()

    # Record multiple usages concurrently
    tasks = [
        collector.record_usage(
            timestamp=datetime.now(timezone.utc),
            user_id=f"user{i}",
            session_id=f"session{i}",
            model="claude-3-5-sonnet-20241022",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
        )
        for i in range(10)
    ]

    await asyncio.gather(*tasks)

    # All records should be saved
    assert collector.total_records == 10


@pytest.mark.unit
def test_pricing_table_has_all_supported_models():
    """Test pricing table includes all supported models."""
    from mcp_server_langgraph.monitoring.pricing import PRICING_TABLE

    # Verify all providers present
    assert "anthropic" in PRICING_TABLE
    assert "openai" in PRICING_TABLE
    assert "google" in PRICING_TABLE

    # Verify key models present
    assert "claude-3-5-sonnet-20241022" in PRICING_TABLE["anthropic"]
    assert "gpt-4-turbo" in PRICING_TABLE["openai"]
    assert "gemini-2.5-flash-preview-001" in PRICING_TABLE["google"]
