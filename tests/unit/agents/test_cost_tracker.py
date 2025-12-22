"""
Tests for Token & Cost Budget Tracking.

Phase 5 of the Multi-Agent Orchestrator Enhancement Plan.

TDD: Write tests FIRST, then implementation.

Tests cover:
1. CostRecord model
2. BudgetStatus enum
3. CostAlert model
4. CostTracker class with per-orchestration and session limits
5. Feature flags for cost tracking
"""

from __future__ import annotations

import gc
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="cost_models")
class TestCostModels:
    """Test cost tracking data models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_cost_record_exists(self) -> None:
        """CostRecord model should exist."""
        from mcp_server_langgraph.agents.cost_models import CostRecord

        assert CostRecord is not None

    def test_cost_record_has_required_fields(self) -> None:
        """CostRecord should have model, tokens, and cost fields."""
        from mcp_server_langgraph.agents.cost_models import CostRecord

        record = CostRecord(
            model="claude-opus-4-5-20251101",
            input_tokens=1000,
            output_tokens=500,
            input_cost=Decimal("0.005"),
            output_cost=Decimal("0.0125"),
            total_cost=Decimal("0.0175"),
        )

        assert record.model == "claude-opus-4-5-20251101"
        assert record.input_tokens == 1000
        assert record.output_tokens == 500
        assert record.input_cost == Decimal("0.005")
        assert record.output_cost == Decimal("0.0125")
        assert record.total_cost == Decimal("0.0175")

    def test_cost_record_optional_task_id(self) -> None:
        """CostRecord should optionally include task_id."""
        from mcp_server_langgraph.agents.cost_models import CostRecord

        record = CostRecord(
            model="claude-opus-4-5-20251101",
            input_tokens=1000,
            output_tokens=500,
            input_cost=Decimal("0.005"),
            output_cost=Decimal("0.0125"),
            total_cost=Decimal("0.0175"),
            task_id="task-123",
        )

        assert record.task_id == "task-123"

    def test_budget_status_enum_exists(self) -> None:
        """BudgetStatus enum should exist with correct values."""
        from mcp_server_langgraph.agents.cost_models import BudgetStatus

        assert BudgetStatus.OK is not None
        assert BudgetStatus.WARNING is not None
        assert BudgetStatus.CRITICAL is not None
        assert BudgetStatus.EXCEEDED is not None

    def test_budget_status_values(self) -> None:
        """BudgetStatus should have string values."""
        from mcp_server_langgraph.agents.cost_models import BudgetStatus

        assert BudgetStatus.OK.value == "ok"
        assert BudgetStatus.WARNING.value == "warning"
        assert BudgetStatus.CRITICAL.value == "critical"
        assert BudgetStatus.EXCEEDED.value == "exceeded"

    def test_cost_alert_exists(self) -> None:
        """CostAlert model should exist."""
        from mcp_server_langgraph.agents.cost_models import CostAlert

        assert CostAlert is not None

    def test_cost_alert_has_required_fields(self) -> None:
        """CostAlert should have status, threshold, and usage info."""
        from mcp_server_langgraph.agents.cost_models import BudgetStatus, CostAlert

        alert = CostAlert(
            status=BudgetStatus.WARNING,
            threshold_percentage=0.75,
            current_cost=Decimal("3.75"),
            limit=Decimal("5.00"),
            session_id="session-123",
        )

        assert alert.status == BudgetStatus.WARNING
        assert alert.threshold_percentage == 0.75
        assert alert.current_cost == Decimal("3.75")
        assert alert.limit == Decimal("5.00")
        assert alert.session_id == "session-123"


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="cost_feature_flags")
class TestCostFeatureFlags:
    """Test feature flags for cost tracking."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_enable_cost_tracking_flag_exists(self) -> None:
        """Feature flags should include enable_cost_tracking."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert hasattr(ff, "enable_cost_tracking")

    def test_enable_cost_tracking_default_true(self) -> None:
        """enable_cost_tracking should default to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert ff.enable_cost_tracking is True

    def test_orchestration_cost_limit_flag_exists(self) -> None:
        """Feature flags should include orchestration_cost_limit."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert hasattr(ff, "orchestration_cost_limit")

    def test_orchestration_cost_limit_default(self) -> None:
        """orchestration_cost_limit should default to 0.50."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert ff.orchestration_cost_limit == 0.50

    def test_session_cost_limit_flag_exists(self) -> None:
        """Feature flags should include session_cost_limit."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert hasattr(ff, "session_cost_limit")

    def test_session_cost_limit_default(self) -> None:
        """session_cost_limit should default to 5.00."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert ff.session_cost_limit == 5.00

    def test_cost_alert_thresholds_flag_exists(self) -> None:
        """Feature flags should include cost_alert_thresholds."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert hasattr(ff, "cost_alert_thresholds")

    def test_cost_alert_thresholds_default(self) -> None:
        """cost_alert_thresholds should default to [0.5, 0.75, 0.9]."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        ff = FeatureFlags()
        assert ff.cost_alert_thresholds == [0.5, 0.75, 0.9]


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="cost_tracker_basic")
class TestCostTrackerBasic:
    """Test CostTracker basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_cost_tracker_exists(self) -> None:
        """CostTracker class should exist."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        assert CostTracker is not None

    def test_cost_tracker_initialization(self) -> None:
        """CostTracker should initialize with configurable limits."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        tracker = CostTracker(
            per_orchestration_limit=0.50,
            session_limit=5.00,
            alert_thresholds=[0.5, 0.75, 0.9],
        )

        assert tracker.per_orchestration_limit == Decimal("0.50")
        assert tracker.session_limit == Decimal("5.00")
        assert tracker.alert_thresholds == [0.5, 0.75, 0.9]

    def test_cost_tracker_default_initialization(self) -> None:
        """CostTracker should use feature flag defaults."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        tracker = CostTracker()

        # Should use feature flag defaults
        assert tracker.per_orchestration_limit == Decimal("0.50")
        assert tracker.session_limit == Decimal("5.00")
        assert tracker.alert_thresholds == [0.5, 0.75, 0.9]

    def test_cost_tracker_has_model_registry(self) -> None:
        """CostTracker should use ModelRegistry for pricing."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        tracker = CostTracker()
        assert tracker.model_registry is not None


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="cost_tracker_tracking")
class TestCostTrackerTracking:
    """Test CostTracker usage tracking."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_track_usage_returns_cost_record(self) -> None:
        """track_usage should return a CostRecord."""
        from mcp_server_langgraph.agents.cost_models import CostRecord
        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        tracker = CostTracker()
        record = tracker.track_usage(
            model="claude-opus-4-5-20251101",
            input_tokens=1000,
            output_tokens=500,
        )

        assert isinstance(record, CostRecord)
        assert record.model == "claude-opus-4-5-20251101"
        assert record.input_tokens == 1000
        assert record.output_tokens == 500

    def test_track_usage_calculates_cost_from_registry(self) -> None:
        """track_usage should calculate cost using ModelRegistry pricing."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        tracker = CostTracker()
        record = tracker.track_usage(
            model="claude-opus-4-5-20251101",
            input_tokens=1_000_000,  # 1M tokens
            output_tokens=1_000_000,  # 1M tokens
        )

        # Opus pricing: $5.00/1M input, $25.00/1M output
        assert record.input_cost == Decimal("5.00")
        assert record.output_cost == Decimal("25.00")
        assert record.total_cost == Decimal("30.00")

    def test_track_usage_with_task_id(self) -> None:
        """track_usage should accept optional task_id."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        tracker = CostTracker()
        record = tracker.track_usage(
            model="claude-opus-4-5-20251101",
            input_tokens=1000,
            output_tokens=500,
            task_id="task-123",
        )

        assert record.task_id == "task-123"

    def test_track_usage_with_session_id(self) -> None:
        """track_usage should accept optional session_id for accumulation."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        tracker = CostTracker()
        record = tracker.track_usage(
            model="claude-opus-4-5-20251101",
            input_tokens=1000,
            output_tokens=500,
            session_id="session-abc",
        )

        assert record is not None
        # Session cost should be tracked
        assert tracker.get_session_cost("session-abc") > Decimal("0")

    def test_track_usage_accumulates_session_cost(self) -> None:
        """Multiple track_usage calls should accumulate session cost."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        tracker = CostTracker()
        session_id = "session-accumulate"

        # First call
        tracker.track_usage(
            model="claude-opus-4-5-20251101",
            input_tokens=100_000,
            output_tokens=50_000,
            session_id=session_id,
        )
        cost_after_first = tracker.get_session_cost(session_id)

        # Second call
        tracker.track_usage(
            model="claude-opus-4-5-20251101",
            input_tokens=100_000,
            output_tokens=50_000,
            session_id=session_id,
        )
        cost_after_second = tracker.get_session_cost(session_id)

        assert cost_after_second == cost_after_first * 2

    def test_track_usage_unknown_model_uses_fallback(self) -> None:
        """Unknown model should use fallback pricing."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        tracker = CostTracker()
        record = tracker.track_usage(
            model="unknown-model-xyz",
            input_tokens=1000,
            output_tokens=500,
        )

        # Should still return a record with some cost
        assert record.total_cost >= Decimal("0")


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="cost_tracker_budget")
class TestCostTrackerBudget:
    """Test CostTracker budget checking."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_check_budget_returns_ok_when_under_limit(self) -> None:
        """check_budget should return OK when under all thresholds."""
        from mcp_server_langgraph.agents.cost_models import BudgetStatus
        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        tracker = CostTracker(session_limit=10.00)
        session_id = "session-ok"

        # Track small usage (under 50% threshold)
        tracker.track_usage(
            model="claude-haiku-4-5-20251001",
            input_tokens=1000,
            output_tokens=500,
            session_id=session_id,
        )

        status = tracker.check_budget(session_id)
        assert status.status == BudgetStatus.OK

    def test_check_budget_returns_warning_at_50_percent(self) -> None:
        """check_budget should return WARNING at 50% threshold."""
        from mcp_server_langgraph.agents.cost_models import BudgetStatus
        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        # Set up tracker with known limit
        tracker = CostTracker(session_limit=1.00, alert_thresholds=[0.5, 0.75, 0.9])
        session_id = "session-warning"

        # Manually set session cost to 55% of limit
        tracker._session_costs[session_id] = Decimal("0.55")

        status = tracker.check_budget(session_id)
        assert status.status == BudgetStatus.WARNING
        assert status.threshold_percentage == 0.5

    def test_check_budget_returns_critical_at_90_percent(self) -> None:
        """check_budget should return CRITICAL at 90% threshold."""
        from mcp_server_langgraph.agents.cost_models import BudgetStatus
        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        tracker = CostTracker(session_limit=1.00, alert_thresholds=[0.5, 0.75, 0.9])
        session_id = "session-critical"

        # Manually set session cost to 92% of limit
        tracker._session_costs[session_id] = Decimal("0.92")

        status = tracker.check_budget(session_id)
        assert status.status == BudgetStatus.CRITICAL
        assert status.threshold_percentage == 0.9

    def test_check_budget_returns_exceeded_at_100_percent(self) -> None:
        """check_budget should return EXCEEDED at 100%+ threshold."""
        from mcp_server_langgraph.agents.cost_models import BudgetStatus
        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        tracker = CostTracker(session_limit=1.00)
        session_id = "session-exceeded"

        # Manually set session cost to 105% of limit
        tracker._session_costs[session_id] = Decimal("1.05")

        status = tracker.check_budget(session_id)
        assert status.status == BudgetStatus.EXCEEDED

    def test_check_budget_unknown_session_returns_ok(self) -> None:
        """check_budget with unknown session should return OK."""
        from mcp_server_langgraph.agents.cost_models import BudgetStatus
        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        tracker = CostTracker()
        status = tracker.check_budget("unknown-session")

        assert status.status == BudgetStatus.OK
        assert status.current_cost == Decimal("0")

    def test_check_orchestration_budget(self) -> None:
        """check_orchestration_budget should check per-orchestration limit."""
        from mcp_server_langgraph.agents.cost_models import BudgetStatus
        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        tracker = CostTracker(per_orchestration_limit=0.10)

        # Check with cost under limit
        status = tracker.check_orchestration_budget(Decimal("0.05"))
        assert status.status == BudgetStatus.OK

        # Check with cost over limit
        status = tracker.check_orchestration_budget(Decimal("0.15"))
        assert status.status == BudgetStatus.EXCEEDED


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="cost_tracker_reset")
class TestCostTrackerReset:
    """Test CostTracker reset functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_reset_session_clears_cost(self) -> None:
        """reset_session should clear session cost to zero."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        tracker = CostTracker()
        session_id = "session-reset"

        # Track some usage
        tracker.track_usage(
            model="claude-opus-4-5-20251101",
            input_tokens=100_000,
            output_tokens=50_000,
            session_id=session_id,
        )

        assert tracker.get_session_cost(session_id) > Decimal("0")

        # Reset
        tracker.reset_session(session_id)

        assert tracker.get_session_cost(session_id) == Decimal("0")

    def test_reset_all_sessions(self) -> None:
        """reset_all should clear all session costs."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        tracker = CostTracker()

        # Track usage in multiple sessions
        tracker.track_usage(
            model="claude-opus-4-5-20251101",
            input_tokens=100_000,
            output_tokens=50_000,
            session_id="session-1",
        )
        tracker.track_usage(
            model="claude-opus-4-5-20251101",
            input_tokens=100_000,
            output_tokens=50_000,
            session_id="session-2",
        )

        # Reset all
        tracker.reset_all()

        assert tracker.get_session_cost("session-1") == Decimal("0")
        assert tracker.get_session_cost("session-2") == Decimal("0")


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="cost_tracker_metrics")
class TestCostTrackerMetrics:
    """Test CostTracker Prometheus metrics integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_track_usage_records_prometheus_metric(self) -> None:
        """track_usage should record cost in Prometheus counter."""
        from unittest.mock import patch

        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        with patch(
            "mcp_server_langgraph.agents.cost_tracker.record_cost_usage"
        ) as mock_record:
            tracker = CostTracker()
            tracker.track_usage(
                model="claude-opus-4-5-20251101",
                input_tokens=1000,
                output_tokens=500,
                session_id="session-metrics",
            )

            mock_record.assert_called_once()
            call_args = mock_record.call_args
            assert call_args.kwargs["model"] == "claude-opus-4-5-20251101"
            assert call_args.kwargs["input_tokens"] == 1000
            assert call_args.kwargs["output_tokens"] == 500
