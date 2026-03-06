"""
Cost Budget Alerts Unit Tests

Tests for budget management and cost alerting.
TDD: Tests written FIRST (RED phase).

The budget alert system should:
1. Define budgets per organization/project/team/user
2. Track spend against budgets
3. Alert when approaching or exceeding thresholds
4. Support configurable thresholds (warning at 80%, critical at 100%)
"""

import gc
from decimal import Decimal

import pytest

from mcp_server_langgraph.core.numeric import safe_average

pytestmark = [pytest.mark.unit]


class TestBudgetDefinition:
    """Tests for budget definition and configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_budget_model_exists(self) -> None:
        """
        GIVEN the budget module
        WHEN importing Budget
        THEN it should be available
        """
        from mcp_server_langgraph.monitoring.cost_budget import Budget

        assert Budget is not None

    def test_budget_has_required_fields(self) -> None:
        """
        GIVEN a Budget instance
        WHEN created with required parameters
        THEN it should have all required fields
        """
        from mcp_server_langgraph.monitoring.cost_budget import Budget

        budget = Budget(
            entity_type="organization",
            entity_id="org:acme",
            monthly_limit_usd=Decimal("1000.00"),
        )

        assert budget.entity_type == "organization"
        assert budget.entity_id == "org:acme"
        assert budget.monthly_limit_usd == Decimal("1000.00")

    def test_budget_supports_all_entity_types(self) -> None:
        """
        GIVEN the Budget model
        WHEN creating budgets for different entity types
        THEN all types should be supported
        """
        from mcp_server_langgraph.monitoring.cost_budget import Budget

        # Organization budget
        org_budget = Budget(
            entity_type="organization",
            entity_id="org:acme",
            monthly_limit_usd=Decimal("10000.00"),
        )
        assert org_budget.entity_type == "organization"

        # Project budget
        project_budget = Budget(
            entity_type="project",
            entity_id="project:backend",
            monthly_limit_usd=Decimal("5000.00"),
        )
        assert project_budget.entity_type == "project"

        # Team budget
        team_budget = Budget(
            entity_type="team",
            entity_id="team:platform",
            monthly_limit_usd=Decimal("2000.00"),
        )
        assert team_budget.entity_type == "team"

        # User budget
        user_budget = Budget(
            entity_type="user",
            entity_id="user:john",
            monthly_limit_usd=Decimal("500.00"),
        )
        assert user_budget.entity_type == "user"

    def test_budget_has_configurable_thresholds(self) -> None:
        """
        GIVEN a Budget instance
        WHEN created with custom thresholds
        THEN it should use those thresholds
        """
        from mcp_server_langgraph.monitoring.cost_budget import Budget

        budget = Budget(
            entity_type="user",
            entity_id="user:test",
            monthly_limit_usd=Decimal("100.00"),
            warning_threshold=0.75,  # Warn at 75%
            critical_threshold=0.95,  # Critical at 95%
        )

        assert budget.warning_threshold == 0.75
        assert budget.critical_threshold == 0.95


class TestBudgetChecker:
    """Tests for budget checking logic."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_check_budget_returns_status(self) -> None:
        """
        GIVEN a budget and current spend
        WHEN checking budget status
        THEN it should return appropriate status
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            Budget,
            BudgetChecker,
        )

        budget = Budget(
            entity_type="user",
            entity_id="user:test",
            monthly_limit_usd=Decimal("100.00"),
        )

        checker = BudgetChecker()

        # Under budget (50%)
        status = await checker.check(budget, current_spend=Decimal("50.00"))
        assert status.status == "ok"
        assert status.percent_used == 50.0

    @pytest.mark.asyncio
    async def test_check_budget_warning_threshold(self) -> None:
        """
        GIVEN a budget at 85% usage
        WHEN checking budget status
        THEN it should return warning status
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            Budget,
            BudgetChecker,
        )

        budget = Budget(
            entity_type="user",
            entity_id="user:test",
            monthly_limit_usd=Decimal("100.00"),
            warning_threshold=0.80,
        )

        checker = BudgetChecker()
        status = await checker.check(budget, current_spend=Decimal("85.00"))

        assert status.status == "warning"
        assert status.percent_used == 85.0

    @pytest.mark.asyncio
    async def test_check_budget_critical_threshold(self) -> None:
        """
        GIVEN a budget at 100% usage
        WHEN checking budget status
        THEN it should return critical status
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            Budget,
            BudgetChecker,
        )

        budget = Budget(
            entity_type="user",
            entity_id="user:test",
            monthly_limit_usd=Decimal("100.00"),
        )

        checker = BudgetChecker()
        status = await checker.check(budget, current_spend=Decimal("100.00"))

        assert status.status == "critical"
        assert status.percent_used == 100.0

    @pytest.mark.asyncio
    async def test_check_budget_exceeded(self) -> None:
        """
        GIVEN a budget at 120% usage
        WHEN checking budget status
        THEN it should return exceeded status
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            Budget,
            BudgetChecker,
        )

        budget = Budget(
            entity_type="user",
            entity_id="user:test",
            monthly_limit_usd=Decimal("100.00"),
        )

        checker = BudgetChecker()
        status = await checker.check(budget, current_spend=Decimal("120.00"))

        assert status.status == "exceeded"
        assert status.percent_used == 120.0


class TestCostAnomalyDetection:
    """Tests for cost anomaly detection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_anomaly_detector_exists(self) -> None:
        """
        GIVEN the cost budget module
        WHEN importing CostAnomalyDetector
        THEN it should be available
        """
        from mcp_server_langgraph.monitoring.cost_budget import CostAnomalyDetector

        assert CostAnomalyDetector is not None

    @pytest.mark.asyncio
    async def test_detect_anomaly_normal_usage(self) -> None:
        """
        GIVEN historical usage data with consistent spend
        WHEN current spend is within normal range
        THEN it should not detect an anomaly
        """
        from mcp_server_langgraph.monitoring.cost_budget import CostAnomalyDetector

        # Historical daily costs (roughly $10/day)
        history = [
            Decimal("9.50"),
            Decimal("10.20"),
            Decimal("10.00"),
            Decimal("9.80"),
            Decimal("10.50"),
        ]

        detector = CostAnomalyDetector()
        result = await detector.detect(
            current_value=Decimal("10.30"),
            historical_values=history,
        )

        assert result.is_anomaly is False

    @pytest.mark.asyncio
    async def test_detect_anomaly_spike(self) -> None:
        """
        GIVEN historical usage data with consistent spend
        WHEN current spend is 3x the average
        THEN it should detect an anomaly
        """
        from mcp_server_langgraph.monitoring.cost_budget import CostAnomalyDetector

        # Historical daily costs (roughly $10/day)
        history = [
            Decimal("9.50"),
            Decimal("10.20"),
            Decimal("10.00"),
            Decimal("9.80"),
            Decimal("10.50"),
        ]

        detector = CostAnomalyDetector()
        result = await detector.detect(
            current_value=Decimal("35.00"),  # 3.5x normal
            historical_values=history,
        )

        assert result.is_anomaly is True
        assert result.severity in ("warning", "critical")

    @pytest.mark.asyncio
    async def test_detect_anomaly_insufficient_history(self) -> None:
        """
        GIVEN less than min_history_size historical values
        WHEN detecting anomalies
        THEN it should return no anomaly with appropriate message
        """
        from mcp_server_langgraph.monitoring.cost_budget import CostAnomalyDetector

        # Only 2 historical values (default min is 3)
        history = [Decimal("10.00"), Decimal("10.50")]

        detector = CostAnomalyDetector()
        result = await detector.detect(
            current_value=Decimal("100.00"),  # Way above normal
            historical_values=history,
        )

        assert result.is_anomaly is False
        assert result.severity == "none"
        assert "Insufficient history" in result.message

    @pytest.mark.asyncio
    async def test_detect_anomaly_zero_std_dev_matching_value(self) -> None:
        """
        GIVEN all historical values are identical
        WHEN current value matches the historical mean
        THEN it should not detect an anomaly
        """
        from mcp_server_langgraph.monitoring.cost_budget import CostAnomalyDetector

        # All identical values
        history = [Decimal("10.00"), Decimal("10.00"), Decimal("10.00")]

        detector = CostAnomalyDetector()
        result = await detector.detect(
            current_value=Decimal("10.00"),
            historical_values=history,
        )

        assert result.is_anomaly is False
        assert result.severity == "none"
        assert result.std_dev == Decimal("0")

    @pytest.mark.asyncio
    async def test_detect_anomaly_zero_std_dev_different_value(self) -> None:
        """
        GIVEN all historical values are identical
        WHEN current value differs from the historical mean
        THEN it should detect a warning anomaly
        """
        from mcp_server_langgraph.monitoring.cost_budget import CostAnomalyDetector

        # All identical values
        history = [Decimal("10.00"), Decimal("10.00"), Decimal("10.00")]

        detector = CostAnomalyDetector()
        result = await detector.detect(
            current_value=Decimal("11.00"),  # Any deviation
            historical_values=history,
        )

        assert result.is_anomaly is True
        assert result.severity == "warning"
        assert result.std_dev == Decimal("0")

    @pytest.mark.asyncio
    async def test_detect_anomaly_negative_spike(self) -> None:
        """
        GIVEN historical usage with consistent spend
        WHEN current spend is significantly LOWER (negative z-score)
        THEN it should still detect as anomaly
        """
        from mcp_server_langgraph.monitoring.cost_budget import CostAnomalyDetector

        # Historical daily costs (roughly $10/day)
        history = [
            Decimal("9.50"),
            Decimal("10.20"),
            Decimal("10.00"),
            Decimal("9.80"),
            Decimal("10.50"),
        ]

        detector = CostAnomalyDetector()
        result = await detector.detect(
            current_value=Decimal("0.50"),  # Way below normal
            historical_values=history,
        )

        assert result.is_anomaly is True
        assert result.z_score < 0  # Negative z-score

    @pytest.mark.asyncio
    async def test_detect_anomaly_warning_threshold(self) -> None:
        """
        GIVEN historical data with known statistics
        WHEN current value is just above warning threshold (z=2)
        THEN it should detect warning but not critical
        """
        from mcp_server_langgraph.monitoring.cost_budget import CostAnomalyDetector

        # Values designed to have mean=10, std=1
        history = [Decimal("9.00"), Decimal("10.00"), Decimal("11.00")]

        detector = CostAnomalyDetector()

        # z-score of ~2.1 should be warning
        result = await detector.detect(
            current_value=Decimal("12.10"),
            historical_values=history,
        )

        assert result.is_anomaly is True
        assert result.severity == "warning"

    @pytest.mark.asyncio
    async def test_detect_anomaly_critical_threshold(self) -> None:
        """
        GIVEN historical data with known statistics
        WHEN current value is above critical threshold (z=3)
        THEN it should detect critical anomaly
        """
        from mcp_server_langgraph.monitoring.cost_budget import CostAnomalyDetector

        # Values designed to have mean=10, std=1
        history = [Decimal("9.00"), Decimal("10.00"), Decimal("11.00")]

        detector = CostAnomalyDetector()

        # z-score of ~3.1 should be critical
        result = await detector.detect(
            current_value=Decimal("13.10"),
            historical_values=history,
        )

        assert result.is_anomaly is True
        assert result.severity == "critical"

    @pytest.mark.asyncio
    async def test_detect_anomaly_custom_thresholds(self) -> None:
        """
        GIVEN detector with custom warning/critical thresholds
        WHEN analyzing value that exceeds custom threshold
        THEN it should use custom thresholds for detection
        """
        from mcp_server_langgraph.monitoring.cost_budget import CostAnomalyDetector

        history = [Decimal("10.00"), Decimal("10.00"), Decimal("10.00"), Decimal("10.00")]

        # Lower thresholds for more sensitive detection
        detector = CostAnomalyDetector(warning_z_score=1.0, critical_z_score=2.0)

        # Different value should now be anomaly with lower threshold
        result = await detector.detect(
            current_value=Decimal("10.50"),  # Small deviation
            historical_values=history,
        )

        # With std_dev=0, any deviation is anomalous
        assert result.is_anomaly is True

    @pytest.mark.asyncio
    async def test_detect_anomaly_empty_history(self) -> None:
        """
        GIVEN empty historical values list
        WHEN detecting anomalies
        THEN it should return no anomaly with appropriate message
        """
        from mcp_server_langgraph.monitoring.cost_budget import CostAnomalyDetector

        detector = CostAnomalyDetector()
        result = await detector.detect(
            current_value=Decimal("100.00"),
            historical_values=[],
        )

        assert result.is_anomaly is False
        assert result.severity == "none"
        assert "Insufficient history" in result.message

    @pytest.mark.asyncio
    async def test_detect_anomaly_just_below_warning(self) -> None:
        """
        GIVEN value just below the warning threshold
        WHEN detecting anomalies
        THEN it should not detect an anomaly
        """
        from mcp_server_langgraph.monitoring.cost_budget import CostAnomalyDetector

        # Values with mean=10, std=1
        history = [Decimal("9.00"), Decimal("10.00"), Decimal("11.00")]

        detector = CostAnomalyDetector()

        # z-score of ~1.9 should not be anomaly
        result = await detector.detect(
            current_value=Decimal("11.90"),
            historical_values=history,
        )

        assert result.is_anomaly is False
        assert result.severity == "none"


class TestCostForecasting:
    """Tests for cost forecasting based on usage trends."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_forecaster_import_when_module_loaded_is_available(self) -> None:
        """
        GIVEN the cost budget module
        WHEN importing CostForecaster
        THEN it should be available
        """
        from mcp_server_langgraph.monitoring.cost_budget import CostForecaster

        assert CostForecaster is not None

    @pytest.mark.asyncio
    async def test_forecast_end_of_month(self) -> None:
        """
        GIVEN historical daily spend data
        WHEN forecasting end of month
        THEN it should project based on trend
        """
        from mcp_server_langgraph.monitoring.cost_budget import CostForecaster

        # 10 days of spend at ~$10/day
        daily_spend = [Decimal("10.00")] * 10

        forecaster = CostForecaster()
        forecast = await forecaster.forecast_month_end(
            daily_values=daily_spend,
            days_in_month=30,
        )

        # Should project ~$300 for the month (30 days * $10/day)
        assert forecast.projected_total >= Decimal("290.00")
        assert forecast.projected_total <= Decimal("310.00")

    @pytest.mark.asyncio
    async def test_forecast_with_increasing_trend(self) -> None:
        """
        GIVEN spend data with increasing trend
        WHEN forecasting end of month
        THEN it should account for the trend
        """
        from mcp_server_langgraph.monitoring.cost_budget import CostForecaster

        # Increasing spend: $5, $6, $7, $8, $9, $10
        daily_spend = [Decimal(str(i)) for i in range(5, 11)]

        forecaster = CostForecaster()
        forecast = await forecaster.forecast_month_end(
            daily_values=daily_spend,
            days_in_month=30,
        )

        # With increasing trend, projection should be higher than simple average
        simple_avg = safe_average(daily_spend) * 30
        assert forecast.projected_total >= simple_avg

    @pytest.mark.asyncio
    async def test_forecast_empty_daily_values(self) -> None:
        """
        GIVEN no daily spend data
        WHEN forecasting end of month
        THEN it should return zero projection with appropriate message
        """
        from mcp_server_langgraph.monitoring.cost_budget import CostForecaster

        forecaster = CostForecaster()
        forecast = await forecaster.forecast_month_end(
            daily_values=[],
            days_in_month=30,
        )

        assert forecast.projected_total == Decimal("0")
        assert forecast.days_analyzed == 0
        assert "No data" in forecast.message

    @pytest.mark.asyncio
    async def test_forecast_single_day_data(self) -> None:
        """
        GIVEN only one day of data
        WHEN forecasting end of month
        THEN it should project using that day's value
        """
        from mcp_server_langgraph.monitoring.cost_budget import CostForecaster

        daily_spend = [Decimal("10.00")]

        forecaster = CostForecaster()
        forecast = await forecaster.forecast_month_end(
            daily_values=daily_spend,
            days_in_month=30,
        )

        # With one day at $10, projecting 30 days = ~$300
        assert forecast.projected_total >= Decimal("290.00")
        assert forecast.projected_total <= Decimal("310.00")
        assert forecast.days_analyzed == 1
        assert forecast.trend == "stable"

    @pytest.mark.asyncio
    async def test_forecast_month_complete(self) -> None:
        """
        GIVEN data for entire month
        WHEN forecasting end of month
        THEN it should return actual total with month complete message
        """
        from mcp_server_langgraph.monitoring.cost_budget import CostForecaster

        # 30 days of spend at $10/day = $300 total
        daily_spend = [Decimal("10.00")] * 30

        forecaster = CostForecaster()
        forecast = await forecaster.forecast_month_end(
            daily_values=daily_spend,
            days_in_month=30,
        )

        # Month is complete, total should be actual sum
        assert forecast.projected_total == Decimal("300.00")
        assert forecast.days_analyzed == 30
        assert "complete" in forecast.message.lower()

    @pytest.mark.asyncio
    async def test_forecast_with_decreasing_trend(self) -> None:
        """
        GIVEN spend data with decreasing trend
        WHEN forecasting end of month
        THEN it should indicate decreasing trend
        """
        from mcp_server_langgraph.monitoring.cost_budget import CostForecaster

        # Decreasing spend: $20, $18, $16, $14, $12, $10
        daily_spend = [Decimal(str(i)) for i in range(20, 8, -2)]

        forecaster = CostForecaster()
        forecast = await forecaster.forecast_month_end(
            daily_values=daily_spend,
            days_in_month=30,
        )

        assert forecast.trend == "decreasing"


class TestBudgetValidation:
    """Tests for Budget validation in __post_init__."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_budget_rejects_warning_gte_critical_threshold(self) -> None:
        """
        GIVEN warning_threshold >= critical_threshold
        WHEN creating a Budget
        THEN it should raise ValueError
        """
        from mcp_server_langgraph.monitoring.cost_budget import Budget

        with pytest.raises(ValueError, match="warning_threshold must be less than critical_threshold"):
            Budget(
                entity_type="user",
                entity_id="user:test",
                monthly_limit_usd=Decimal("100.00"),
                warning_threshold=0.90,  # Equal or greater than critical
                critical_threshold=0.90,
            )

    def test_budget_rejects_warning_greater_than_critical(self) -> None:
        """
        GIVEN warning_threshold > critical_threshold
        WHEN creating a Budget
        THEN it should raise ValueError
        """
        from mcp_server_langgraph.monitoring.cost_budget import Budget

        with pytest.raises(ValueError, match="warning_threshold must be less than critical_threshold"):
            Budget(
                entity_type="user",
                entity_id="user:test",
                monthly_limit_usd=Decimal("100.00"),
                warning_threshold=0.95,  # Greater than critical
                critical_threshold=0.80,
            )

    def test_budget_rejects_zero_monthly_limit(self) -> None:
        """
        GIVEN monthly_limit_usd = 0
        WHEN creating a Budget
        THEN it should raise ValueError
        """
        from mcp_server_langgraph.monitoring.cost_budget import Budget

        with pytest.raises(ValueError, match="monthly_limit_usd must be positive"):
            Budget(
                entity_type="user",
                entity_id="user:test",
                monthly_limit_usd=Decimal("0.00"),
            )

    def test_budget_rejects_negative_monthly_limit(self) -> None:
        """
        GIVEN monthly_limit_usd < 0
        WHEN creating a Budget
        THEN it should raise ValueError
        """
        from mcp_server_langgraph.monitoring.cost_budget import Budget

        with pytest.raises(ValueError, match="monthly_limit_usd must be positive"):
            Budget(
                entity_type="user",
                entity_id="user:test",
                monthly_limit_usd=Decimal("-100.00"),
            )


class TestBudgetCheckerAll:
    """Tests for BudgetChecker.check_all method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_check_all_returns_list_of_statuses(self) -> None:
        """
        GIVEN multiple budgets and spend data
        WHEN calling check_all
        THEN it should return status for each budget
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            Budget,
            BudgetChecker,
        )

        budgets = [
            Budget(
                entity_type="user",
                entity_id="user:alice",
                monthly_limit_usd=Decimal("100.00"),
            ),
            Budget(
                entity_type="user",
                entity_id="user:bob",
                monthly_limit_usd=Decimal("200.00"),
            ),
        ]

        spend_by_entity = {
            "user:alice": Decimal("50.00"),  # 50% - ok
            "user:bob": Decimal("180.00"),  # 90% - warning
        }

        checker = BudgetChecker()
        results = await checker.check_all(budgets, spend_by_entity)

        assert len(results) == 2
        assert results[0].status == "ok"
        assert results[0].budget.entity_id == "user:alice"
        assert results[1].status == "warning"
        assert results[1].budget.entity_id == "user:bob"

    @pytest.mark.asyncio
    async def test_check_all_handles_missing_spend_data(self) -> None:
        """
        GIVEN a budget with no spend data
        WHEN calling check_all
        THEN it should default to zero spend
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            Budget,
            BudgetChecker,
        )

        budgets = [
            Budget(
                entity_type="user",
                entity_id="user:new",
                monthly_limit_usd=Decimal("100.00"),
            ),
        ]

        spend_by_entity = {}  # No spend data

        checker = BudgetChecker()
        results = await checker.check_all(budgets, spend_by_entity)

        assert len(results) == 1
        assert results[0].current_spend == Decimal("0")
        assert results[0].status == "ok"


class TestBudgetStatusMessage:
    """Tests for BudgetStatus.message property."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_message_ok_status(self) -> None:
        """
        GIVEN a budget status with 'ok' status
        WHEN accessing message
        THEN it should indicate budget is on track
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            Budget,
            BudgetStatus,
        )

        budget = Budget(
            entity_type="user",
            entity_id="user:test",
            monthly_limit_usd=Decimal("100.00"),
        )
        status = BudgetStatus(
            budget=budget,
            current_spend=Decimal("50.00"),
            percent_used=50.0,
            status="ok",
            remaining=Decimal("50.00"),
        )

        assert "on track" in status.message.lower()
        assert "50.0%" in status.message

    def test_message_warning_status(self) -> None:
        """
        GIVEN a budget status with 'warning' status
        WHEN accessing message
        THEN it should indicate budget warning
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            Budget,
            BudgetStatus,
        )

        budget = Budget(
            entity_type="user",
            entity_id="user:test",
            monthly_limit_usd=Decimal("100.00"),
        )
        status = BudgetStatus(
            budget=budget,
            current_spend=Decimal("85.00"),
            percent_used=85.0,
            status="warning",
            remaining=Decimal("15.00"),
        )

        assert "warning" in status.message.lower()
        assert "85.0%" in status.message

    def test_message_critical_status(self) -> None:
        """
        GIVEN a budget status with 'critical' status
        WHEN accessing message
        THEN it should indicate budget critical
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            Budget,
            BudgetStatus,
        )

        budget = Budget(
            entity_type="user",
            entity_id="user:test",
            monthly_limit_usd=Decimal("100.00"),
        )
        status = BudgetStatus(
            budget=budget,
            current_spend=Decimal("100.00"),
            percent_used=100.0,
            status="critical",
            remaining=Decimal("0.00"),
        )

        assert "critical" in status.message.lower()
        assert "100.0%" in status.message

    def test_message_exceeded_status(self) -> None:
        """
        GIVEN a budget status with 'exceeded' status
        WHEN accessing message
        THEN it should indicate budget exceeded with overspend amount
        """
        from mcp_server_langgraph.monitoring.cost_budget import (
            Budget,
            BudgetStatus,
        )

        budget = Budget(
            entity_type="user",
            entity_id="user:test",
            monthly_limit_usd=Decimal("100.00"),
        )
        status = BudgetStatus(
            budget=budget,
            current_spend=Decimal("120.00"),
            percent_used=120.0,
            status="exceeded",
            remaining=Decimal("-20.00"),
        )

        assert "exceeded" in status.message.lower()
        assert "120.0%" in status.message
        assert "over budget" in status.message.lower()


class TestBudgetSingletonAccessors:
    """Tests for singleton accessor functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_budget_checker_returns_singleton(self) -> None:
        """
        GIVEN get_budget_checker function
        WHEN called multiple times
        THEN it should return the same instance
        """
        from mcp_server_langgraph.monitoring.cost_budget import get_budget_checker

        checker1 = get_budget_checker()
        checker2 = get_budget_checker()

        assert checker1 is checker2

    def test_get_anomaly_detector_returns_singleton(self) -> None:
        """
        GIVEN get_anomaly_detector function
        WHEN called multiple times
        THEN it should return the same instance
        """
        from mcp_server_langgraph.monitoring.cost_budget import get_anomaly_detector

        detector1 = get_anomaly_detector()
        detector2 = get_anomaly_detector()

        assert detector1 is detector2

    def test_get_forecaster_returns_singleton(self) -> None:
        """
        GIVEN get_forecaster function
        WHEN called multiple times
        THEN it should return the same instance
        """
        from mcp_server_langgraph.monitoring.cost_budget import get_forecaster

        forecaster1 = get_forecaster()
        forecaster2 = get_forecaster()

        assert forecaster1 is forecaster2
