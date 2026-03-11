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

import gc
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ==============================================================================
# Helper Functions
# ==============================================================================


def _create_mock_cost_collector() -> MagicMock:
    """Create a mock cost collector for testing BudgetMonitor without database."""
    mock = MagicMock()  # noqa: async-mock-config (methods configured below)
    mock.get_cost_summary = AsyncMock(return_value={"total_cost_usd": Decimal("0.00")})
    return mock


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def sample_token_usage():
    """Sample token usage data for testing."""
    return {
        "timestamp": datetime.now(UTC),
        "user_id": "user123",
        "session_id": "session456",
        "model": "claude-sonnet-4-5-20250929",
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
        "start_date": datetime.now(UTC).replace(day=1),
        "alert_thresholds": [Decimal("0.75"), Decimal("0.90")],
    }


@pytest.fixture
def reset_singletons(monkeypatch):
    """Reset cost storage singleton before/after tests."""
    from mcp_server_langgraph.monitoring.cost_storage_factory import (
        reset_cost_storage_backend,
    )
    from mcp_server_langgraph.monitoring.cost_tracker import _reset_cost_collector

    # Use memory backend for unit tests (monkeypatch auto-restores on teardown)
    monkeypatch.setenv("COST_STORAGE_BACKEND", "memory")

    reset_cost_storage_backend()
    _reset_cost_collector()

    yield

    reset_cost_storage_backend()
    _reset_cost_collector()


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
        model="claude-sonnet-4-5-20250929",
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
    """Test cost calculation for Anthropic Claude 4.5 Haiku (cost-effective model)."""
    from mcp_server_langgraph.monitoring.pricing import calculate_cost

    cost = calculate_cost(
        model="claude-haiku-4-5-20251001",
        provider="anthropic",
        prompt_tokens=1000,
        completion_tokens=500,
    )

    # Input: 1000 * $0.001/1K = $0.001
    # Output: 500 * $0.005/1K = $0.0025
    # Total: $0.0035
    assert cost == Decimal("0.0035")


@pytest.mark.unit
def test_calculate_cost_for_openai_gpt5():
    """Test cost calculation for OpenAI GPT-5.1."""
    from mcp_server_langgraph.monitoring.pricing import calculate_cost

    cost = calculate_cost(
        model="gpt-5.1",
        provider="openai",
        prompt_tokens=1000,
        completion_tokens=500,
    )

    # Input: 1000 * $0.00125/1K = $0.00125
    # Output: 500 * $0.01/1K = $0.005
    # Total: $0.00625
    assert cost == Decimal("0.00625")


@pytest.mark.unit
def test_calculate_cost_for_google_gemini_flash():
    """Test cost calculation for Google Gemini 2.5 Flash."""
    from mcp_server_langgraph.monitoring.pricing import calculate_cost

    cost = calculate_cost(
        model="gemini-2.5-flash",
        provider="google",
        prompt_tokens=10000,
        completion_tokens=5000,
    )

    # Input: 10000 * $0.0003/1K = $0.003
    # Output: 5000 * $0.0025/1K = $0.0125
    # Total: $0.0155
    assert cost == Decimal("0.0155")


@pytest.mark.unit
def test_calculate_cost_with_zero_tokens_returns_zero():
    """Test cost calculation with zero tokens."""
    from mcp_server_langgraph.monitoring.pricing import calculate_cost

    cost = calculate_cost(
        model="claude-sonnet-4-5-20250929",
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
async def test_cost_metrics_collector_records_usage(sample_token_usage, reset_singletons):
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
async def test_cost_metrics_collector_calculates_cost_automatically(reset_singletons):
    """Test collector automatically calculates cost if not provided."""
    from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

    collector = CostMetricsCollector()

    # Act - record without explicit cost
    await collector.record_usage(
        timestamp=datetime.now(UTC),
        user_id="user123",
        session_id="session456",
        model="claude-sonnet-4-5-20250929",
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
async def test_cost_metrics_collector_increments_prometheus_counters(reset_singletons):
    """Test collector updates Prometheus metrics."""
    from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

    collector = CostMetricsCollector()

    with patch("mcp_server_langgraph.monitoring.cost_tracker.llm_token_usage") as mock_counter:
        await collector.record_usage(
            timestamp=datetime.now(UTC),
            user_id="user123",
            session_id="session456",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
        )

        # Assert Prometheus counter was incremented
        assert mock_counter.labels.called


# ==============================================================================
# Test CostAggregator
# ==============================================================================


@pytest.mark.xdist_group(name="cost_tracker_aggregator")
class TestAggregateByField:
    """Tests for generic _aggregate_by_field method (TDD: RED phase)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def aggregator(self):
        from mcp_server_langgraph.monitoring.cost_tracker import CostAggregator

        return CostAggregator()

    @pytest.fixture
    def sample_records(self):
        return [
            {"model": "gpt-4", "user_id": "user1", "feature": "chat", "cost": Decimal("0.10")},
            {"model": "gpt-4", "user_id": "user2", "feature": "chat", "cost": Decimal("0.20")},
            {"model": "claude-3", "user_id": "user1", "feature": "summarize", "cost": Decimal("0.15")},
        ]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_aggregate_by_field_model(self, aggregator, sample_records):
        """Should aggregate by model field correctly."""
        result = await aggregator._aggregate_by_field(sample_records, "model")
        assert result == {"gpt-4": Decimal("0.30"), "claude-3": Decimal("0.15")}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_aggregate_by_field_user_id(self, aggregator, sample_records):
        """Should aggregate by user_id field correctly."""
        result = await aggregator._aggregate_by_field(sample_records, "user_id")
        assert result == {"user1": Decimal("0.25"), "user2": Decimal("0.20")}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_aggregate_by_field_feature(self, aggregator, sample_records):
        """Should aggregate by feature field correctly."""
        result = await aggregator._aggregate_by_field(sample_records, "feature")
        assert result == {"chat": Decimal("0.30"), "summarize": Decimal("0.15")}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_aggregate_by_field_missing_field_uses_unknown(self, aggregator):
        """Should use 'unknown' for missing fields."""
        records = [
            {"model": "gpt-4", "cost": Decimal("0.10")},  # No user_id
            {"model": "gpt-4", "user_id": "user1", "cost": Decimal("0.20")},
        ]
        result = await aggregator._aggregate_by_field(records, "user_id")
        assert result == {"unknown": Decimal("0.10"), "user1": Decimal("0.20")}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_aggregate_by_field_empty_records(self, aggregator):
        """Should return empty dict for empty records."""
        result = await aggregator._aggregate_by_field([], "model")
        assert result == {}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_aggregate_by_field_handles_string_cost(self, aggregator):
        """Should handle string cost values."""
        records = [
            {"model": "gpt-4", "cost": "0.10"},  # String, not Decimal
            {"model": "gpt-4", "cost": "0.20"},
        ]
        result = await aggregator._aggregate_by_field(records, "model")
        assert result == {"gpt-4": Decimal("0.30")}


@pytest.mark.xdist_group(name="cost_tracker_aggregator")
class TestExistingAggregationMethods:
    """Tests that existing public methods still work after refactoring."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def aggregator(self):
        from mcp_server_langgraph.monitoring.cost_tracker import CostAggregator

        return CostAggregator()

    @pytest.fixture
    def sample_records(self):
        return [
            {"model": "gpt-4", "user_id": "user1", "feature": "chat", "cost": Decimal("0.10")},
            {"model": "gpt-4", "user_id": "user2", "feature": "chat", "cost": Decimal("0.20")},
        ]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_aggregate_by_model_uses_generic(self, aggregator, sample_records):
        """aggregate_by_model should delegate to _aggregate_by_field."""
        result = await aggregator.aggregate_by_model(sample_records)
        assert "gpt-4" in result
        assert result["gpt-4"] == Decimal("0.30")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_aggregate_by_user_uses_generic(self, aggregator, sample_records):
        """aggregate_by_user should delegate to _aggregate_by_field."""
        result = await aggregator.aggregate_by_user(sample_records)
        assert "user1" in result
        assert result["user1"] == Decimal("0.10")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_aggregate_by_feature_uses_generic(self, aggregator, sample_records):
        """aggregate_by_feature should delegate to _aggregate_by_field."""
        result = await aggregator.aggregate_by_feature(sample_records)
        assert "chat" in result
        assert result["chat"] == Decimal("0.30")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cost_aggregator_sums_by_model():
    """Test CostAggregator aggregates costs by model."""
    from mcp_server_langgraph.monitoring.cost_tracker import CostAggregator

    aggregator = CostAggregator()

    # Arrange - mock data
    records = [
        {"model": "claude-sonnet-4-5-20250929", "cost": Decimal("0.01")},
        {"model": "claude-sonnet-4-5-20250929", "cost": Decimal("0.02")},
        {"model": "gpt-5.1", "cost": Decimal("0.03")},
    ]

    # Act
    summary = await aggregator.aggregate_by_model(records)

    # Assert
    assert summary["claude-sonnet-4-5-20250929"] == Decimal("0.03")
    assert summary["gpt-5.1"] == Decimal("0.03")


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


@pytest.mark.xdist_group(name="cost_tracker_budget_tests")
class TestBudgetMonitor:
    """Test suite for BudgetMonitor with memory safety pattern."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_budget_monitor_detects_75_percent_utilization(self, sample_budget):
        """Test BudgetMonitor sends warning at 75% budget utilization."""
        from mcp_server_langgraph.monitoring.budget_monitor import BudgetMonitor, BudgetPeriod

        monitor = BudgetMonitor(cost_collector=_create_mock_cost_collector())

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
        with patch.object(monitor, "get_period_spend", new_callable=AsyncMock, return_value=Decimal("750.00")):
            with patch.object(monitor, "send_alert", new_callable=AsyncMock) as mock_alert:
                await monitor.check_budget(sample_budget["id"])

                # Assert warning alert sent
                mock_alert.assert_called_once()
                call_args = mock_alert.call_args[1]
                assert call_args["level"] == "warning"
                assert "75" in call_args["message"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_budget_monitor_detects_90_percent_utilization(self, sample_budget):
        """Test BudgetMonitor sends critical alert at 90% budget utilization."""
        from mcp_server_langgraph.monitoring.budget_monitor import BudgetMonitor, BudgetPeriod

        monitor = BudgetMonitor(cost_collector=_create_mock_cost_collector())

        # Create budget first
        await monitor.create_budget(
            id=sample_budget["id"],
            name=sample_budget["name"],
            limit_usd=sample_budget["limit_usd"],
            period=BudgetPeriod.MONTHLY,
            start_date=sample_budget["start_date"],
            alert_thresholds=sample_budget["alert_thresholds"],
        )

        with patch.object(monitor, "get_period_spend", new_callable=AsyncMock, return_value=Decimal("900.00")):
            with patch.object(monitor, "send_alert", new_callable=AsyncMock) as mock_alert:
                await monitor.check_budget(sample_budget["id"])

                mock_alert.assert_called_once()
                call_args = mock_alert.call_args[1]
                assert call_args["level"] == "critical"
                assert "90" in call_args["message"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_budget_monitor_no_alert_below_threshold(self, sample_budget):
        """Test BudgetMonitor does not alert below 75% utilization."""
        from mcp_server_langgraph.monitoring.budget_monitor import BudgetMonitor, BudgetPeriod

        monitor = BudgetMonitor(cost_collector=_create_mock_cost_collector())

        # Create budget first
        await monitor.create_budget(
            id=sample_budget["id"],
            name=sample_budget["name"],
            limit_usd=sample_budget["limit_usd"],
            period=BudgetPeriod.MONTHLY,
            start_date=sample_budget["start_date"],
            alert_thresholds=sample_budget["alert_thresholds"],
        )

        with patch.object(monitor, "get_period_spend", new_callable=AsyncMock, return_value=Decimal("500.00")):  # 50%
            with patch.object(monitor, "send_alert", new_callable=AsyncMock) as mock_alert:
                await monitor.check_budget(sample_budget["id"])

                mock_alert.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_budget_monitor_handles_budget_exceeded(self):
        """Test BudgetMonitor handles budget being exceeded."""
        from datetime import datetime

        from mcp_server_langgraph.monitoring.budget_monitor import BudgetMonitor, BudgetPeriod

        monitor = BudgetMonitor(cost_collector=_create_mock_cost_collector())

        # Create budget first
        await monitor.create_budget(
            id="budget_001",
            name="Test Budget",
            limit_usd=Decimal("1000.00"),
            period=BudgetPeriod.MONTHLY,
            start_date=datetime.now(UTC).replace(day=1),
            alert_thresholds=[Decimal("0.75"), Decimal("0.90")],
        )

        with patch.object(monitor, "get_period_spend", new_callable=AsyncMock, return_value=Decimal("1500.00")):  # 150%
            with patch.object(monitor, "send_alert", new_callable=AsyncMock) as mock_alert:
                await monitor.check_budget("budget_001")

                # Should send critical alert for exceeded budget
                assert mock_alert.called


# ==============================================================================
# Integration Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_end_to_end_cost_tracking_flow(reset_singletons):
    """Test complete flow: record usage → aggregate → check budget."""
    from mcp_server_langgraph.monitoring.budget_monitor import BudgetMonitor
    from mcp_server_langgraph.monitoring.cost_tracker import CostAggregator, CostMetricsCollector

    # Step 1: Record usage
    collector = CostMetricsCollector()
    await collector.record_usage(
        timestamp=datetime.now(UTC),
        user_id="user123",
        session_id="session456",
        model="claude-sonnet-4-5-20250929",
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
    with patch.object(monitor, "get_period_spend", new_callable=AsyncMock, return_value=total_cost):
        # Should not alert for small spend
        with patch.object(monitor, "send_alert", new_callable=AsyncMock) as mock_alert:
            await monitor.check_budget("budget_001")

            # Depends on total cost vs budget
            # For this test, assume low spend
            assert mock_alert.call_count == 0


# ==============================================================================
# Edge Cases
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cost_tracker_handles_concurrent_writes(reset_singletons):
    """Test CostMetricsCollector handles concurrent usage recording."""
    import asyncio

    from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

    collector = CostMetricsCollector()

    # Record multiple usages concurrently
    tasks = [
        collector.record_usage(
            timestamp=datetime.now(UTC),
            user_id=f"user{i}",
            session_id=f"session{i}",
            model="claude-sonnet-4-5-20250929",
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
    assert "claude-sonnet-4-5-20250929" in PRICING_TABLE["anthropic"]
    assert "gpt-5.1" in PRICING_TABLE["openai"]
    assert "gemini-2.5-flash" in PRICING_TABLE["google"]


# ==============================================================================
# Additional Coverage Tests for TokenUsage
# ==============================================================================


@pytest.mark.xdist_group(name="cost_tracker_token_usage")
class TestTokenUsageModel:
    """Tests for TokenUsage pydantic model to improve coverage."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_token_usage_auto_calculates_total_tokens(self):
        """Test TokenUsage auto-calculates total_tokens if not provided."""
        from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage

        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user123",
            session_id="session456",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("0.01"),
        )

        assert usage.total_tokens == 1500

    @pytest.mark.unit
    def test_token_usage_serialize_decimal(self):
        """Test TokenUsage serializes Decimal to string."""
        from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage

        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user123",
            session_id="session456",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("0.012345"),
        )

        # model_dump with mode='json' triggers serializers
        data = usage.model_dump(mode="json")
        assert data["estimated_cost_usd"] == "0.012345"
        assert isinstance(data["estimated_cost_usd"], str)

    @pytest.mark.unit
    def test_token_usage_serialize_timestamp(self):
        """Test TokenUsage serializes datetime to ISO format."""
        from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage

        ts = datetime(2025, 1, 15, 12, 30, 45, tzinfo=UTC)
        usage = TokenUsage(
            timestamp=ts,
            user_id="user123",
            session_id="session456",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("0.01"),
        )

        data = usage.model_dump(mode="json")
        assert "2025-01-15" in data["timestamp"]
        assert isinstance(data["timestamp"], str)


# ==============================================================================
# Additional Coverage Tests for CostMetricsCollector
# ==============================================================================


@pytest.mark.xdist_group(name="cost_tracker_collector_extended")
class TestCostMetricsCollectorExtended:
    """Extended tests for CostMetricsCollector to improve coverage."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collector_get_records_filters_by_user(self, reset_singletons):
        """Test get_records filters by user_id."""
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        collector = CostMetricsCollector()

        # Record usage for two different users
        await collector.record_usage(
            timestamp=datetime.now(UTC),
            user_id="user1",
            session_id="session1",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
        )
        await collector.record_usage(
            timestamp=datetime.now(UTC),
            user_id="user2",
            session_id="session2",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
        )

        # Filter by user1
        records = await collector.get_records(user_id="user1")
        assert len(records) == 1
        assert records[0].user_id == "user1"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collector_get_records_filters_by_model(self, reset_singletons):
        """Test get_records filters by model."""
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        collector = CostMetricsCollector()

        await collector.record_usage(
            timestamp=datetime.now(UTC),
            user_id="user1",
            session_id="session1",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
        )
        await collector.record_usage(
            timestamp=datetime.now(UTC),
            user_id="user1",
            session_id="session2",
            model="gpt-5.1",
            provider="openai",
            prompt_tokens=1000,
            completion_tokens=500,
        )

        records = await collector.get_records(model="gpt-5.1")
        assert len(records) == 1
        assert records[0].model == "gpt-5.1"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collector_get_total_cost_with_user_filter(self, reset_singletons):
        """Test get_total_cost filters by user."""
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        collector = CostMetricsCollector()

        await collector.record_usage(
            timestamp=datetime.now(UTC),
            user_id="user1",
            session_id="session1",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("0.01"),
        )
        await collector.record_usage(
            timestamp=datetime.now(UTC),
            user_id="user2",
            session_id="session2",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("0.02"),
        )

        total = await collector.get_total_cost(user_id="user1")
        assert total == Decimal("0.01")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collector_get_latest_record_returns_none_when_empty(self, reset_singletons):
        """Test get_latest_record returns None for empty collector."""
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        collector = CostMetricsCollector()
        result = await collector.get_latest_record()
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collector_cleanup_old_records_in_memory(self, reset_singletons):
        """Test cleanup_old_records removes old in-memory records."""
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        collector = CostMetricsCollector(retention_days=1)

        # Record old and new usage
        old_timestamp = datetime.now(UTC) - timedelta(days=5)
        new_timestamp = datetime.now(UTC)

        await collector.record_usage(
            timestamp=old_timestamp,
            user_id="user1",
            session_id="session1",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
        )
        await collector.record_usage(
            timestamp=new_timestamp,
            user_id="user2",
            session_id="session2",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
        )

        assert collector.total_records == 2

        deleted = await collector.cleanup_old_records()

        assert deleted == 1
        assert collector.total_records == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collector_record_usage_with_feature_and_metadata(self, reset_singletons):
        """Test record_usage stores feature and metadata correctly."""
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        collector = CostMetricsCollector()

        await collector.record_usage(
            timestamp=datetime.now(UTC),
            user_id="user1",
            session_id="session1",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            feature="chat",
            metadata={"request_id": "req123"},
        )

        record = await collector.get_latest_record()
        assert record.feature == "chat"
        assert record.metadata == {"request_id": "req123"}


# ==============================================================================
# Test Singleton Pattern
# ==============================================================================


@pytest.mark.unit
def test_get_cost_collector_returns_singleton(reset_singletons):
    """Test get_cost_collector returns the same instance."""
    from mcp_server_langgraph.monitoring.cost_tracker import get_cost_collector

    collector1 = get_cost_collector()
    collector2 = get_cost_collector()

    assert collector1 is collector2


# ==============================================================================
# Test Time Period Filtering
# ==============================================================================


@pytest.mark.xdist_group(name="cost_tracker_time")
class TestTimePeriodFiltering:
    """Tests for time period filtering in cost records."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_filter_by_day_returns_last_24_hours(self, reset_singletons) -> None:
        """
        GIVEN records from different time periods
        WHEN get_records is called with period="day"
        THEN only records from the last 24 hours are returned
        """
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        collector = CostMetricsCollector()

        # Create records from different times
        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1, hours=1)  # Just over 24 hours ago
        last_hour = now - timedelta(hours=1)

        await collector.record_usage(
            timestamp=yesterday,
            user_id="user1",
            session_id="sess1",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=100,
            completion_tokens=50,
        )

        await collector.record_usage(
            timestamp=last_hour,
            user_id="user1",
            session_id="sess2",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=200,
            completion_tokens=100,
        )

        # Filter by day
        records = await collector.get_records(period="day")

        # Only the record from last_hour should be returned
        assert len(records) == 1
        assert records[0].session_id == "sess2"

    @pytest.mark.asyncio
    async def test_filter_by_week_returns_last_7_days(self, reset_singletons) -> None:
        """
        GIVEN records from different time periods
        WHEN get_records is called with period="week"
        THEN only records from the last 7 days are returned
        """
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        collector = CostMetricsCollector()

        now = datetime.now(UTC)
        eight_days_ago = now - timedelta(days=8)
        three_days_ago = now - timedelta(days=3)

        await collector.record_usage(
            timestamp=eight_days_ago,
            user_id="user1",
            session_id="old_session",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=100,
            completion_tokens=50,
        )

        await collector.record_usage(
            timestamp=three_days_ago,
            user_id="user1",
            session_id="recent_session",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=200,
            completion_tokens=100,
        )

        records = await collector.get_records(period="week")

        assert len(records) == 1
        assert records[0].session_id == "recent_session"

    @pytest.mark.asyncio
    async def test_filter_by_month_returns_last_30_days(self, reset_singletons) -> None:
        """
        GIVEN records from different time periods
        WHEN get_records is called with period="month"
        THEN only records from the last 30 days are returned
        """
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        collector = CostMetricsCollector()

        now = datetime.now(UTC)
        forty_days_ago = now - timedelta(days=40)
        ten_days_ago = now - timedelta(days=10)

        await collector.record_usage(
            timestamp=forty_days_ago,
            user_id="user1",
            session_id="very_old",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=100,
            completion_tokens=50,
        )

        await collector.record_usage(
            timestamp=ten_days_ago,
            user_id="user1",
            session_id="within_month",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=200,
            completion_tokens=100,
        )

        records = await collector.get_records(period="month")

        assert len(records) == 1
        assert records[0].session_id == "within_month"


# ==============================================================================
# Test Distributed Tracing for Cost Attribution
# ==============================================================================


@pytest.mark.xdist_group(name="cost_tracker_distributed_tracing")
class TestDistributedTracingCostAttribution:
    """Tests for distributed tracing fields in TokenUsage for cost attribution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_token_usage_includes_trace_id_field(self) -> None:
        """TokenUsage should include optional trace_id field for OpenTelemetry correlation."""
        from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage

        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user123",
            session_id="session456",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("0.01"),
            trace_id="abc123def456789012345678901234",
        )

        assert usage.trace_id == "abc123def456789012345678901234"

    @pytest.mark.unit
    def test_token_usage_trace_id_defaults_to_none(self) -> None:
        """TokenUsage trace_id should default to None when not provided."""
        from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage

        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user123",
            session_id="session456",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("0.01"),
        )

        assert usage.trace_id is None

    @pytest.mark.unit
    def test_token_usage_includes_span_id_field(self) -> None:
        """TokenUsage should include optional span_id field."""
        from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage

        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user123",
            session_id="session456",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("0.01"),
            span_id="0123456789abcdef",
        )

        assert usage.span_id == "0123456789abcdef"

    @pytest.mark.unit
    def test_token_usage_includes_workflow_id_field(self) -> None:
        """TokenUsage should include optional workflow_id for workflow cost attribution."""
        from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage

        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user123",
            session_id="session456",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("0.01"),
            workflow_id="workflow-abc-123",
        )

        assert usage.workflow_id == "workflow-abc-123"

    @pytest.mark.unit
    def test_token_usage_includes_orchestrator_id_field(self) -> None:
        """TokenUsage should include optional orchestrator_id for agent cost attribution."""
        from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage

        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user123",
            session_id="session456",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("0.01"),
            orchestrator_id="orchestrator-main-001",
        )

        assert usage.orchestrator_id == "orchestrator-main-001"

    @pytest.mark.unit
    def test_token_usage_includes_request_id_field(self) -> None:
        """TokenUsage should include optional request_id for request tracking."""
        from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage

        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user123",
            session_id="session456",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("0.01"),
            request_id="req-uuid-1234",
        )

        assert usage.request_id == "req-uuid-1234"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collector_record_usage_accepts_trace_context(self, reset_singletons) -> None:
        """CostMetricsCollector.record_usage should accept distributed tracing fields."""
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        collector = CostMetricsCollector()

        usage = await collector.record_usage(
            timestamp=datetime.now(UTC),
            user_id="user123",
            session_id="session456",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            trace_id="trace-abc123",
            span_id="span-def456",
            workflow_id="workflow-789",
            orchestrator_id="orch-001",
            request_id="req-xyz",
        )

        assert usage.trace_id == "trace-abc123"
        assert usage.span_id == "span-def456"
        assert usage.workflow_id == "workflow-789"
        assert usage.orchestrator_id == "orch-001"
        assert usage.request_id == "req-xyz"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collector_record_usage_defaults_trace_fields_to_none(self, reset_singletons) -> None:
        """CostMetricsCollector.record_usage should default trace fields to None."""
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        collector = CostMetricsCollector()

        usage = await collector.record_usage(
            timestamp=datetime.now(UTC),
            user_id="user123",
            session_id="session456",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
        )

        assert usage.trace_id is None
        assert usage.span_id is None
        assert usage.workflow_id is None
        assert usage.orchestrator_id is None
        assert usage.request_id is None

    @pytest.mark.unit
    def test_token_usage_serializes_trace_fields_in_json(self) -> None:
        """TokenUsage should include trace fields when serialized to JSON."""
        from mcp_server_langgraph.monitoring.cost_tracker import TokenUsage

        usage = TokenUsage(
            timestamp=datetime.now(UTC),
            user_id="user123",
            session_id="session456",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=Decimal("0.01"),
            trace_id="trace-123",
            workflow_id="workflow-456",
        )

        data = usage.model_dump(mode="json")

        assert data["trace_id"] == "trace-123"
        assert data["workflow_id"] == "workflow-456"
        assert data["span_id"] is None  # Default should be None
        assert data["orchestrator_id"] is None
        assert data["request_id"] is None
