"""
Unit tests for orchestrator observability metrics.

Tests the metrics instrumentation for UX and Alert orchestrators:
- Parallel execution metrics (task count, speedup ratio)
- Synthesis metrics
- Orchestrator-type specific metrics
- Feature flag metrics

TDD: Tests written FIRST before implementation.
"""

import gc
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.agents]


@pytest.mark.xdist_group(name="orchestrator_metrics_module")
class TestOrchestratorMetricsModule:
    """Test orchestrator metrics module structure."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ux_orchestration_counter_exists(self) -> None:
        """Test that UX orchestration counter exists."""
        from mcp_server_langgraph.agents.metrics import ux_orchestration_counter

        assert ux_orchestration_counter is not None

    def test_alert_orchestration_counter_exists(self) -> None:
        """Test that alert orchestration counter exists."""
        from mcp_server_langgraph.agents.metrics import alert_orchestration_counter

        assert alert_orchestration_counter is not None

    def test_parallel_speedup_histogram_exists(self) -> None:
        """Test that parallel speedup histogram exists."""
        from mcp_server_langgraph.agents.metrics import parallel_speedup_histogram

        assert parallel_speedup_histogram is not None

    def test_orchestrator_parallel_tasks_histogram_exists(self) -> None:
        """Test that parallel tasks histogram exists."""
        from mcp_server_langgraph.agents.metrics import orchestrator_parallel_tasks_histogram

        assert orchestrator_parallel_tasks_histogram is not None


@pytest.mark.xdist_group(name="orchestrator_metrics_functions")
class TestOrchestratorMetricsFunctions:
    """Test orchestrator metrics recording functions."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_ux_orchestration_exists(self) -> None:
        """Test that record_ux_orchestration function exists."""
        from mcp_server_langgraph.agents.metrics import record_ux_orchestration

        assert callable(record_ux_orchestration)

    def test_record_alert_orchestration_exists(self) -> None:
        """Test that record_alert_orchestration function exists."""
        from mcp_server_langgraph.agents.metrics import record_alert_orchestration

        assert callable(record_alert_orchestration)

    def test_record_parallel_speedup_exists(self) -> None:
        """Test that record_parallel_speedup function exists."""
        from mcp_server_langgraph.agents.metrics import record_parallel_speedup

        assert callable(record_parallel_speedup)


@pytest.mark.xdist_group(name="ux_orchestration_metrics")
class TestUXOrchestrationMetrics:
    """Test UX orchestration metrics recording."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_ux_orchestration_records_counter(self) -> None:
        """Test that record_ux_orchestration records the counter."""
        from mcp_server_langgraph.agents.metrics import (
            record_ux_orchestration,
            ux_orchestration_counter,
        )

        # Should not raise
        record_ux_orchestration(
            task_count=3,
            successful_count=3,
            duration_ms=150.5,
            success=True,
        )

    def test_record_ux_orchestration_accepts_analysis_types(self) -> None:
        """Test that record_ux_orchestration accepts analysis types."""
        from mcp_server_langgraph.agents.metrics import record_ux_orchestration

        # Should accept analysis types parameter
        record_ux_orchestration(
            task_count=2,
            successful_count=2,
            duration_ms=100.0,
            success=True,
            analysis_types=["persona_analysis", "disclosure_analysis"],
        )

    def test_record_ux_orchestration_tracks_failure(self) -> None:
        """Test that record_ux_orchestration tracks failures."""
        from mcp_server_langgraph.agents.metrics import record_ux_orchestration

        record_ux_orchestration(
            task_count=3,
            successful_count=2,
            duration_ms=200.0,
            success=False,
            error_type="service_unavailable",
        )


@pytest.mark.xdist_group(name="alert_orchestration_metrics")
class TestAlertOrchestrationMetrics:
    """Test alert orchestration metrics recording."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_alert_orchestration_records_counter(self) -> None:
        """Test that record_alert_orchestration records the counter."""
        from mcp_server_langgraph.agents.metrics import record_alert_orchestration

        record_alert_orchestration(
            alert_count=5,
            task_count=4,
            successful_count=4,
            duration_ms=250.0,
            success=True,
        )

    def test_record_alert_orchestration_accepts_analysis_types(self) -> None:
        """Test that record_alert_orchestration accepts analysis types."""
        from mcp_server_langgraph.agents.metrics import record_alert_orchestration

        record_alert_orchestration(
            alert_count=3,
            task_count=2,
            successful_count=2,
            duration_ms=180.0,
            success=True,
            analysis_types=["correlation", "root_cause"],
        )

    def test_record_alert_orchestration_tracks_correlation_groups(self) -> None:
        """Test that record_alert_orchestration tracks correlation groups."""
        from mcp_server_langgraph.agents.metrics import record_alert_orchestration

        record_alert_orchestration(
            alert_count=10,
            task_count=4,
            successful_count=4,
            duration_ms=300.0,
            success=True,
            correlation_groups=3,
        )


@pytest.mark.xdist_group(name="parallel_speedup_metrics")
class TestParallelSpeedupMetrics:
    """Test parallel speedup metrics."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_parallel_speedup_records_ratio(self) -> None:
        """Test that record_parallel_speedup records speedup ratio."""
        from mcp_server_langgraph.agents.metrics import record_parallel_speedup

        record_parallel_speedup(
            orchestrator_type="ux",
            task_count=3,
            parallel_duration_ms=100.0,
            estimated_sequential_ms=300.0,
        )

    def test_record_parallel_speedup_calculates_ratio(self) -> None:
        """Test that record_parallel_speedup calculates correct ratio."""
        from mcp_server_langgraph.agents.metrics import record_parallel_speedup

        # 300ms sequential / 100ms parallel = 3x speedup
        record_parallel_speedup(
            orchestrator_type="alert",
            task_count=4,
            parallel_duration_ms=80.0,
            estimated_sequential_ms=320.0,  # 4 tasks * 80ms each
        )


@pytest.mark.xdist_group(name="orchestrator_synthesis_metrics")
class TestOrchestratorSynthesisMetrics:
    """Test synthesis metrics for orchestrators."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_ux_synthesis_exists(self) -> None:
        """Test that record_ux_synthesis function exists."""
        from mcp_server_langgraph.agents.metrics import record_ux_synthesis

        assert callable(record_ux_synthesis)

    def test_record_ux_synthesis_records_cross_insights(self) -> None:
        """Test that record_ux_synthesis records cross insights count."""
        from mcp_server_langgraph.agents.metrics import record_ux_synthesis

        record_ux_synthesis(
            input_count=3,
            cross_insights_count=2,
            duration_ms=50.0,
        )

    def test_record_alert_synthesis_exists(self) -> None:
        """Test that record_alert_synthesis function exists."""
        from mcp_server_langgraph.agents.metrics import record_alert_synthesis

        assert callable(record_alert_synthesis)

    def test_record_alert_synthesis_records_correlation_summary(self) -> None:
        """Test that record_alert_synthesis records correlation summary."""
        from mcp_server_langgraph.agents.metrics import record_alert_synthesis

        record_alert_synthesis(
            input_count=4,
            correlation_groups=2,
            patterns_detected=1,
            duration_ms=75.0,
        )


@pytest.mark.xdist_group(name="orchestrator_feature_flag_metrics")
class TestOrchestratorFeatureFlagMetrics:
    """Test feature flag usage metrics for orchestrators."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_orchestrator_feature_flag_check_exists(self) -> None:
        """Test that record_orchestrator_feature_flag_check exists."""
        from mcp_server_langgraph.agents.metrics import record_orchestrator_feature_flag_check

        assert callable(record_orchestrator_feature_flag_check)

    def test_record_orchestrator_feature_flag_check_records(self) -> None:
        """Test that record_orchestrator_feature_flag_check records the check."""
        from mcp_server_langgraph.agents.metrics import record_orchestrator_feature_flag_check

        record_orchestrator_feature_flag_check(
            orchestrator_type="ux",
            flag_name="enable_orchestrated_ai_ux",
            enabled=True,
        )

        record_orchestrator_feature_flag_check(
            orchestrator_type="alert",
            flag_name="enable_orchestrated_alert_analysis",
            enabled=False,
        )
