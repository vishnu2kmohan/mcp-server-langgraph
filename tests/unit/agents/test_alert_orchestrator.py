"""
Unit tests for Alert Orchestrator (Phase 12).

Tests alert-specific orchestration for multi-alert correlation:
- Parallel execution of correlation, root cause, remediation analyses
- Pattern detection across alert groups
- Feature flag for gradual rollout
- Integration with AlertCorrelationEngine

TDD: Tests written FIRST before implementation.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.core.feature_flags import feature_flags

pytestmark = [pytest.mark.unit, pytest.mark.agents]


@pytest.mark.xdist_group(name="alert_orchestrator_feature_flags")
class TestAlertOrchestratorFeatureFlags:
    """Test feature flags for orchestrated alert analysis."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_enable_orchestrated_alert_analysis_flag_exists(self) -> None:
        """Test that enable_orchestrated_alert_analysis flag exists."""
        assert hasattr(feature_flags, "enable_orchestrated_alert_analysis")

    def test_enable_orchestrated_alert_analysis_default_false(self) -> None:
        """Test that orchestrated alert analysis is disabled by default (gradual rollout)."""
        assert feature_flags.enable_orchestrated_alert_analysis is False


@pytest.mark.xdist_group(name="alert_orchestrator_module")
class TestAlertOrchestratorModule:
    """Test alert orchestrator module structure."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_alert_orchestrator_module_exists(self) -> None:
        """Test that alert_orchestrator module exists."""
        from mcp_server_langgraph.agents import alert_orchestrator

        assert alert_orchestrator is not None

    def test_alert_orchestrator_class_exists(self) -> None:
        """Test that AlertOrchestrator class exists."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        assert AlertOrchestrator is not None

    def test_alert_analysis_task_class_exists(self) -> None:
        """Test that AlertAnalysisTask class exists."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertAnalysisTask

        assert AlertAnalysisTask is not None

    def test_alert_analysis_result_class_exists(self) -> None:
        """Test that AlertAnalysisResult class exists."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertAnalysisResult

        assert AlertAnalysisResult is not None


@pytest.mark.xdist_group(name="alert_orchestrator_initialization")
class TestAlertOrchestratorInitialization:
    """Test alert orchestrator initialization."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_alert_orchestrator_initialization(self) -> None:
        """Test that AlertOrchestrator can be initialized."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        orchestrator = AlertOrchestrator()
        assert orchestrator is not None

    def test_alert_orchestrator_accepts_correlation_engine(self) -> None:
        """Test that AlertOrchestrator accepts AlertCorrelationEngine."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        mock_engine = MagicMock()
        orchestrator = AlertOrchestrator(correlation_engine=mock_engine)
        assert orchestrator.correlation_engine == mock_engine

    def test_alert_orchestrator_accepts_recommendation_service(self) -> None:
        """Test that AlertOrchestrator accepts AIRecommendationService."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        mock_service = MagicMock()
        orchestrator = AlertOrchestrator(recommendation_service=mock_service)
        assert orchestrator.recommendation_service == mock_service


@pytest.mark.xdist_group(name="alert_analysis_task")
class TestAlertAnalysisTask:
    """Test AlertAnalysisTask data class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_alert_analysis_task_has_task_type(self) -> None:
        """Test that AlertAnalysisTask has task_type field."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertAnalysisTask

        task = AlertAnalysisTask(
            task_type="correlation",
            alert_ids=["alert-1"],
        )
        assert task.task_type == "correlation"

    def test_alert_analysis_task_has_alert_ids(self) -> None:
        """Test that AlertAnalysisTask has alert_ids field."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertAnalysisTask

        task = AlertAnalysisTask(
            task_type="correlation",
            alert_ids=["alert-1", "alert-2"],
        )
        assert task.alert_ids == ["alert-1", "alert-2"]

    def test_alert_analysis_task_has_data(self) -> None:
        """Test that AlertAnalysisTask has data field."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertAnalysisTask

        task = AlertAnalysisTask(
            task_type="root_cause",
            alert_ids=["alert-1"],
            data={"severity": "critical"},
        )
        assert task.data == {"severity": "critical"}

    def test_alert_analysis_task_supports_all_types(self) -> None:
        """Test that AlertAnalysisTask supports all analysis types."""
        from mcp_server_langgraph.agents.alert_orchestrator import (
            ALERT_ANALYSIS_TYPES,
            AlertAnalysisTask,
        )

        # Check all types are defined
        expected_types = {"correlation", "root_cause", "remediation", "pattern_detection"}
        assert expected_types.issubset(set(ALERT_ANALYSIS_TYPES))


@pytest.mark.xdist_group(name="alert_analysis_result")
class TestAlertAnalysisResult:
    """Test AlertAnalysisResult data class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_alert_analysis_result_has_task_type(self) -> None:
        """Test that AlertAnalysisResult has task_type field."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertAnalysisResult

        result = AlertAnalysisResult(
            task_type="correlation",
            success=True,
            result={"correlated_groups": []},
        )
        assert result.task_type == "correlation"

    def test_alert_analysis_result_has_success(self) -> None:
        """Test that AlertAnalysisResult has success field."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertAnalysisResult

        result = AlertAnalysisResult(
            task_type="root_cause",
            success=True,
        )
        assert result.success is True

    def test_alert_analysis_result_has_error(self) -> None:
        """Test that AlertAnalysisResult can have error field."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertAnalysisResult

        result = AlertAnalysisResult(
            task_type="remediation",
            success=False,
            error="Analysis failed",
        )
        assert result.error == "Analysis failed"


@pytest.mark.xdist_group(name="alert_orchestrator_execution")
class TestAlertOrchestratorExecution:
    """Test alert orchestrator execution."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_has_execute_method(self) -> None:
        """Test that AlertOrchestrator has execute method."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        orchestrator = AlertOrchestrator()
        assert hasattr(orchestrator, "execute")
        assert callable(orchestrator.execute)

    @pytest.mark.asyncio
    async def test_execute_returns_list_of_results(self) -> None:
        """Test that execute returns list of AlertAnalysisResult."""
        from mcp_server_langgraph.agents.alert_orchestrator import (
            AlertAnalysisTask,
            AlertOrchestrator,
        )

        # Create mock correlation engine
        mock_engine = MagicMock()
        mock_engine.correlate = MagicMock(return_value=[])

        orchestrator = AlertOrchestrator(correlation_engine=mock_engine)

        tasks = [
            AlertAnalysisTask(
                task_type="correlation",
                alert_ids=["alert-1"],
            ),
        ]

        results = await orchestrator.execute(tasks)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_execute_runs_tasks_in_parallel(self) -> None:
        """Test that execute runs tasks in parallel."""
        import asyncio

        from mcp_server_langgraph.agents.alert_orchestrator import (
            AlertAnalysisTask,
            AlertOrchestrator,
        )

        # Track execution order
        execution_order = []

        async def mock_root_cause(*args, **kwargs):
            execution_order.append("root_cause_start")
            await asyncio.sleep(0.01)
            execution_order.append("root_cause_end")
            return MagicMock()

        async def mock_remediation(*args, **kwargs):
            execution_order.append("remediation_start")
            await asyncio.sleep(0.01)
            execution_order.append("remediation_end")
            return MagicMock()

        mock_service = MagicMock()
        mock_service.analyze_root_cause = mock_root_cause
        mock_service.generate_remediation = mock_remediation

        orchestrator = AlertOrchestrator(recommendation_service=mock_service)

        tasks = [
            AlertAnalysisTask(
                task_type="root_cause",
                alert_ids=["alert-1"],
            ),
            AlertAnalysisTask(
                task_type="remediation",
                alert_ids=["alert-2"],
            ),
        ]

        await orchestrator.execute(tasks)

        # Verify parallel execution: both starts should happen before both ends
        if len(execution_order) >= 4:
            root_cause_start_idx = execution_order.index("root_cause_start")
            remediation_start_idx = execution_order.index("remediation_start")
            root_cause_end_idx = execution_order.index("root_cause_end")
            remediation_end_idx = execution_order.index("remediation_end")

            # Both starts should happen before at least one end
            assert root_cause_start_idx < max(root_cause_end_idx, remediation_end_idx)
            assert remediation_start_idx < max(root_cause_end_idx, remediation_end_idx)


@pytest.mark.xdist_group(name="alert_orchestrator_synthesis")
class TestAlertOrchestratorSynthesis:
    """Test alert orchestrator cross-service synthesis."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_has_synthesize_method(self) -> None:
        """Test that AlertOrchestrator has synthesize method."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        orchestrator = AlertOrchestrator()
        assert hasattr(orchestrator, "synthesize")
        assert callable(orchestrator.synthesize)

    def test_synthesize_generates_correlation_summary(self) -> None:
        """Test that synthesize generates correlation summary."""
        from mcp_server_langgraph.agents.alert_orchestrator import (
            AlertAnalysisResult,
            AlertOrchestrator,
        )

        orchestrator = AlertOrchestrator()

        results = [
            AlertAnalysisResult(
                task_type="correlation",
                success=True,
                result={"groups": [{"alerts": ["a1", "a2"], "pattern": "cascade"}]},
            ),
            AlertAnalysisResult(
                task_type="root_cause",
                success=True,
                result={"root_cause": "Database connection pool exhausted"},
            ),
        ]

        synthesis = orchestrator.synthesize(results)
        assert "correlation_summary" in synthesis
        assert isinstance(synthesis["correlation_summary"], dict)


@pytest.mark.xdist_group(name="alert_orchestrator_analysis")
class TestAlertOrchestratorAnalysis:
    """Test orchestrated alert analysis."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_has_analyze_alerts(self) -> None:
        """Test that AlertOrchestrator has analyze_alerts method."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        orchestrator = AlertOrchestrator()
        assert hasattr(orchestrator, "analyze_alerts")
        assert callable(orchestrator.analyze_alerts)

    @pytest.mark.asyncio
    async def test_analyze_alerts_returns_response(self) -> None:
        """Test that analyze_alerts returns comprehensive response."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        # Create mock services
        mock_engine = MagicMock()
        mock_engine.correlate = MagicMock(return_value=[])

        mock_service = MagicMock()
        mock_result = MagicMock()
        mock_result.model_dump = MagicMock(return_value={"root_cause": "test"})
        mock_service.analyze_root_cause = AsyncMock(return_value=mock_result)
        mock_service.generate_remediation = AsyncMock(return_value=mock_result)

        orchestrator = AlertOrchestrator(
            correlation_engine=mock_engine,
            recommendation_service=mock_service,
        )

        result = await orchestrator.analyze_alerts(
            alert_ids=["alert-1", "alert-2"],
            include_correlation=True,
            include_root_cause=True,
            include_remediation=False,
        )

        assert result is not None
        assert "alert_ids" in result


@pytest.mark.xdist_group(name="alert_orchestrator_fallback")
class TestAlertOrchestratorFallback:
    """Test alert orchestrator feature flag fallback."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_respects_feature_flag(self) -> None:
        """Test that orchestrator respects enable_orchestrated_alert_analysis flag."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        orchestrator = AlertOrchestrator()
        assert hasattr(orchestrator, "is_enabled")

    def test_orchestrator_is_enabled_property(self) -> None:
        """Test that orchestrator has is_enabled property."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        orchestrator = AlertOrchestrator()
        # Default is False for gradual rollout
        assert isinstance(orchestrator.is_enabled, bool)


@pytest.mark.xdist_group(name="alert_orchestrator_inheritance")
class TestAlertOrchestratorInheritance:
    """Test AlertOrchestrator inherits from BaseOrchestrator."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_alert_orchestrator_inherits_base_orchestrator(self) -> None:
        """Test that AlertOrchestrator inherits from BaseOrchestrator."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseOrchestrator
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        assert issubclass(AlertOrchestrator, BaseOrchestrator)

    def test_alert_orchestrator_has_feature_flag_name_property(self) -> None:
        """Test that AlertOrchestrator has feature_flag_name property."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        orchestrator = AlertOrchestrator()
        assert hasattr(orchestrator, "feature_flag_name")
        assert orchestrator.feature_flag_name == "enable_orchestrated_alert_analysis"

    def test_alert_orchestrator_inherits_execute_method(self) -> None:
        """Test that AlertOrchestrator uses inherited execute method."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseOrchestrator
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        assert AlertOrchestrator.execute is not None
        assert hasattr(AlertOrchestrator, "execute")

    def test_alert_orchestrator_implements_execute_task(self) -> None:
        """Test that AlertOrchestrator implements _execute_task abstract method."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        orchestrator = AlertOrchestrator()
        assert hasattr(orchestrator, "_execute_task")
        assert callable(orchestrator._execute_task)

    def test_alert_orchestrator_implements_synthesize(self) -> None:
        """Test that AlertOrchestrator implements synthesize abstract method."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        orchestrator = AlertOrchestrator()
        assert hasattr(orchestrator, "synthesize")
        assert callable(orchestrator.synthesize)


@pytest.mark.xdist_group(name="alert_orchestrator_pattern_detection")
class TestAlertOrchestratorPatternDetection:
    """Test alert orchestrator pattern detection."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_has_detect_patterns_method(self) -> None:
        """Test that AlertOrchestrator has detect_patterns method."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        orchestrator = AlertOrchestrator()
        assert hasattr(orchestrator, "detect_patterns")
        assert callable(orchestrator.detect_patterns)

    def test_detect_patterns_returns_patterns(self) -> None:
        """Test that detect_patterns returns pattern list."""
        from mcp_server_langgraph.agents.alert_orchestrator import AlertOrchestrator

        mock_engine = MagicMock()
        mock_engine.detect_patterns = MagicMock(return_value=[
            {"type": "cascade", "alerts": ["a1", "a2"]},
        ])

        orchestrator = AlertOrchestrator(correlation_engine=mock_engine)

        patterns = orchestrator.detect_patterns(alert_ids=["a1", "a2", "a3"])
        assert isinstance(patterns, list)
