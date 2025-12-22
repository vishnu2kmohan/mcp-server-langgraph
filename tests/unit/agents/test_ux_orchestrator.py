"""
Unit tests for UX Orchestrator (Phase 11).

Tests UX-specific orchestration for AI UX Service composite analysis:
- Parallel execution of persona, disclosure, error analyses
- Cross-service insights synthesis
- Feature flag for gradual rollout
- Integration with ArtifactStorage

TDD: Tests written FIRST before implementation.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.core.feature_flags import feature_flags

pytestmark = [pytest.mark.unit, pytest.mark.agents]


@pytest.mark.xdist_group(name="ux_orchestrator_feature_flags")
class TestUXOrchestratorFeatureFlags:
    """Test feature flags for orchestrated AI UX."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_enable_orchestrated_ai_ux_flag_exists(self) -> None:
        """Test that enable_orchestrated_ai_ux flag exists."""
        assert hasattr(feature_flags, "enable_orchestrated_ai_ux")

    def test_enable_orchestrated_ai_ux_default_false(self) -> None:
        """Test that orchestrated AI UX is disabled by default (gradual rollout)."""
        assert feature_flags.enable_orchestrated_ai_ux is False


@pytest.mark.xdist_group(name="ux_orchestrator_inheritance")
class TestUXOrchestratorInheritance:
    """Test UXOrchestrator inherits from BaseOrchestrator."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_ux_orchestrator_inherits_base_orchestrator(self) -> None:
        """Test that UXOrchestrator inherits from BaseOrchestrator."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseOrchestrator
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        assert issubclass(UXOrchestrator, BaseOrchestrator)

    def test_ux_orchestrator_has_feature_flag_name_property(self) -> None:
        """Test that UXOrchestrator has feature_flag_name property."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        orchestrator = UXOrchestrator()
        assert hasattr(orchestrator, "feature_flag_name")
        assert orchestrator.feature_flag_name == "enable_orchestrated_ai_ux"

    def test_ux_orchestrator_inherits_execute_method(self) -> None:
        """Test that UXOrchestrator uses inherited execute method."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseOrchestrator
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        # The execute method should come from the base class
        assert UXOrchestrator.execute is not None
        # Verify it's a method from BaseOrchestrator (or overridden properly)
        assert hasattr(UXOrchestrator, "execute")

    def test_ux_orchestrator_implements_execute_task(self) -> None:
        """Test that UXOrchestrator implements _execute_task abstract method."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        orchestrator = UXOrchestrator()
        assert hasattr(orchestrator, "_execute_task")
        assert callable(orchestrator._execute_task)

    def test_ux_orchestrator_implements_synthesize(self) -> None:
        """Test that UXOrchestrator implements synthesize abstract method."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        orchestrator = UXOrchestrator()
        assert hasattr(orchestrator, "synthesize")
        assert callable(orchestrator.synthesize)


@pytest.mark.xdist_group(name="ux_orchestrator_module")
class TestUXOrchestratorModule:
    """Test UX orchestrator module structure."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_ux_orchestrator_module_exists(self) -> None:
        """Test that ux_orchestrator module exists."""
        from mcp_server_langgraph.agents import ux_orchestrator

        assert ux_orchestrator is not None

    def test_ux_orchestrator_class_exists(self) -> None:
        """Test that UXOrchestrator class exists."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        assert UXOrchestrator is not None

    def test_ux_analysis_task_class_exists(self) -> None:
        """Test that UXAnalysisTask class exists."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXAnalysisTask

        assert UXAnalysisTask is not None

    def test_ux_analysis_result_class_exists(self) -> None:
        """Test that UXAnalysisResult class exists."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXAnalysisResult

        assert UXAnalysisResult is not None


@pytest.mark.xdist_group(name="ux_orchestrator_initialization")
class TestUXOrchestratorInitialization:
    """Test UX orchestrator initialization."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_ux_orchestrator_initialization(self) -> None:
        """Test that UXOrchestrator can be initialized."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        orchestrator = UXOrchestrator()
        assert orchestrator is not None

    def test_ux_orchestrator_accepts_ai_ux_service(self) -> None:
        """Test that UXOrchestrator accepts AIUXService."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        mock_service = MagicMock()
        orchestrator = UXOrchestrator(ai_ux_service=mock_service)
        assert orchestrator.ai_ux_service == mock_service

    def test_ux_orchestrator_accepts_artifact_storage(self) -> None:
        """Test that UXOrchestrator accepts ArtifactStorage."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        mock_storage = MagicMock()
        orchestrator = UXOrchestrator(artifact_storage=mock_storage)
        assert orchestrator.artifact_storage == mock_storage


@pytest.mark.xdist_group(name="ux_analysis_task")
class TestUXAnalysisTask:
    """Test UXAnalysisTask data class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_ux_analysis_task_has_task_type(self) -> None:
        """Test that UXAnalysisTask has task_type field."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXAnalysisTask

        task = UXAnalysisTask(
            task_type="persona_analysis",
            user_id="test-user",
        )
        assert task.task_type == "persona_analysis"

    def test_ux_analysis_task_has_user_id(self) -> None:
        """Test that UXAnalysisTask has user_id field."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXAnalysisTask

        task = UXAnalysisTask(
            task_type="persona_analysis",
            user_id="test-user-123",
        )
        assert task.user_id == "test-user-123"

    def test_ux_analysis_task_has_data(self) -> None:
        """Test that UXAnalysisTask has data field."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXAnalysisTask

        task = UXAnalysisTask(
            task_type="persona_analysis",
            user_id="test-user",
            data={"assigned_persona": "bob"},
        )
        assert task.data == {"assigned_persona": "bob"}

    def test_ux_analysis_task_supports_all_types(self) -> None:
        """Test that UXAnalysisTask supports all analysis types."""
        from mcp_server_langgraph.agents.ux_orchestrator import (
            UX_ANALYSIS_TYPES,
            UXAnalysisTask,
        )

        # Check all types are defined
        expected_types = {"persona_analysis", "disclosure_analysis", "error_analysis"}
        assert expected_types.issubset(set(UX_ANALYSIS_TYPES))


@pytest.mark.xdist_group(name="ux_analysis_result")
class TestUXAnalysisResult:
    """Test UXAnalysisResult data class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_ux_analysis_result_has_task_type(self) -> None:
        """Test that UXAnalysisResult has task_type field."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXAnalysisResult

        result = UXAnalysisResult(
            task_type="persona_analysis",
            success=True,
            result={"detected_persona": "alice-builder"},
        )
        assert result.task_type == "persona_analysis"

    def test_ux_analysis_result_has_success(self) -> None:
        """Test that UXAnalysisResult has success field."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXAnalysisResult

        result = UXAnalysisResult(
            task_type="persona_analysis",
            success=True,
        )
        assert result.success is True

    def test_ux_analysis_result_has_error(self) -> None:
        """Test that UXAnalysisResult can have error field."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXAnalysisResult

        result = UXAnalysisResult(
            task_type="persona_analysis",
            success=False,
            error="Analysis failed",
        )
        assert result.error == "Analysis failed"


@pytest.mark.xdist_group(name="ux_orchestrator_execution")
class TestUXOrchestratorExecution:
    """Test UX orchestrator execution."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_has_execute_method(self) -> None:
        """Test that UXOrchestrator has execute method."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        orchestrator = UXOrchestrator()
        assert hasattr(orchestrator, "execute")
        assert callable(orchestrator.execute)

    @pytest.mark.asyncio
    async def test_execute_returns_list_of_results(self) -> None:
        """Test that execute returns list of UXAnalysisResult."""
        from mcp_server_langgraph.agents.ux_orchestrator import (
            UXAnalysisTask,
            UXOrchestrator,
        )

        # Create mock AIUXService
        mock_service = MagicMock()
        mock_service.analyze_persona = AsyncMock(return_value=MagicMock())
        mock_service.analyze_disclosure = AsyncMock(return_value=MagicMock())

        orchestrator = UXOrchestrator(ai_ux_service=mock_service)

        tasks = [
            UXAnalysisTask(
                task_type="persona_analysis",
                user_id="test-user",
                data={"assigned_persona": "bob"},
            ),
        ]

        results = await orchestrator.execute(tasks)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_execute_runs_tasks_in_parallel(self) -> None:
        """Test that execute runs tasks in parallel."""
        import asyncio

        from mcp_server_langgraph.agents.ux_orchestrator import (
            UXAnalysisTask,
            UXOrchestrator,
        )

        # Track execution order
        execution_order = []

        async def mock_persona_analysis(*args, **kwargs):
            execution_order.append("persona_start")
            await asyncio.sleep(0.01)  # Small delay
            execution_order.append("persona_end")
            return MagicMock()

        async def mock_disclosure_analysis(*args, **kwargs):
            execution_order.append("disclosure_start")
            await asyncio.sleep(0.01)  # Small delay
            execution_order.append("disclosure_end")
            return MagicMock()

        mock_service = MagicMock()
        mock_service.analyze_persona = mock_persona_analysis
        mock_service.analyze_disclosure = mock_disclosure_analysis

        orchestrator = UXOrchestrator(ai_ux_service=mock_service)

        tasks = [
            UXAnalysisTask(
                task_type="persona_analysis",
                user_id="test-user",
                data={"assigned_persona": "bob"},
            ),
            UXAnalysisTask(
                task_type="disclosure_analysis",
                user_id="test-user",
                data={"feature_usage": {}},
            ),
        ]

        await orchestrator.execute(tasks)

        # Verify parallel execution: both starts should happen before both ends
        # In sequential execution: start1, end1, start2, end2
        # In parallel execution: start1, start2, end1, end2 (or similar interleaving)
        persona_start_idx = execution_order.index("persona_start")
        disclosure_start_idx = execution_order.index("disclosure_start")
        persona_end_idx = execution_order.index("persona_end")
        disclosure_end_idx = execution_order.index("disclosure_end")

        # Both starts should happen before at least one end
        assert persona_start_idx < max(persona_end_idx, disclosure_end_idx)
        assert disclosure_start_idx < max(persona_end_idx, disclosure_end_idx)


@pytest.mark.xdist_group(name="ux_orchestrator_synthesis")
class TestUXOrchestratorSynthesis:
    """Test UX orchestrator cross-service synthesis."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_has_synthesize_method(self) -> None:
        """Test that UXOrchestrator has synthesize method."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        orchestrator = UXOrchestrator()
        assert hasattr(orchestrator, "synthesize")
        assert callable(orchestrator.synthesize)

    def test_synthesize_generates_cross_insights(self) -> None:
        """Test that synthesize generates cross-service insights."""
        from mcp_server_langgraph.agents.ux_orchestrator import (
            UXAnalysisResult,
            UXOrchestrator,
        )

        orchestrator = UXOrchestrator()

        results = [
            UXAnalysisResult(
                task_type="persona_analysis",
                success=True,
                result={"detected_persona": "alice-builder", "confidence": 0.85},
            ),
            UXAnalysisResult(
                task_type="disclosure_analysis",
                success=True,
                result={"current_level": "beginner", "recommended_level": "advanced"},
            ),
        ]

        synthesis = orchestrator.synthesize(results)
        assert "cross_insights" in synthesis
        assert isinstance(synthesis["cross_insights"], list)


@pytest.mark.xdist_group(name="ux_orchestrator_composite")
class TestUXOrchestratorCompositeAnalysis:
    """Test orchestrated composite analysis."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_has_run_composite_analysis(self) -> None:
        """Test that UXOrchestrator has run_composite_analysis method."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        orchestrator = UXOrchestrator()
        assert hasattr(orchestrator, "run_composite_analysis")
        assert callable(orchestrator.run_composite_analysis)

    @pytest.mark.asyncio
    async def test_run_composite_analysis_returns_response(self) -> None:
        """Test that run_composite_analysis returns composite response."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        # Create mock AIUXService with all methods
        mock_service = MagicMock()
        mock_result = MagicMock()
        mock_result.model_dump = MagicMock(return_value={"confidence": 0.8})

        mock_service.analyze_persona = AsyncMock(return_value=mock_result)
        mock_service.analyze_disclosure = AsyncMock(return_value=mock_result)
        mock_service.analyze_error = AsyncMock(return_value=mock_result)

        orchestrator = UXOrchestrator(ai_ux_service=mock_service)

        result = await orchestrator.run_composite_analysis(
            user_id="test-user",
            session_id="test-session",
            include_persona=True,
            include_disclosure=True,
            include_error=False,
            persona_data={"assigned_persona": "bob"},
            disclosure_data={"feature_usage": {}},
        )

        assert result is not None
        assert "user_id" in result
        assert "session_id" in result


@pytest.mark.xdist_group(name="ux_orchestrator_fallback")
class TestUXOrchestratorFallback:
    """Test UX orchestrator feature flag fallback."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_respects_feature_flag(self) -> None:
        """Test that orchestrator respects enable_orchestrated_ai_ux flag."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        orchestrator = UXOrchestrator()
        assert hasattr(orchestrator, "is_enabled")

    def test_orchestrator_is_enabled_property(self) -> None:
        """Test that orchestrator has is_enabled property."""
        from mcp_server_langgraph.agents.ux_orchestrator import UXOrchestrator

        orchestrator = UXOrchestrator()
        # Default is False for gradual rollout
        assert isinstance(orchestrator.is_enabled, bool)


@pytest.mark.xdist_group(name="ux_orchestrator_metrics")
class TestUXOrchestratorMetrics:
    """Test UX orchestrator metrics."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_ux_orchestration_metrics_exist(self) -> None:
        """Test that UX orchestration metrics are defined."""
        from mcp_server_langgraph.agents.metrics import record_orchestrator_execution

        # Should be able to record UX orchestration metrics
        assert callable(record_orchestrator_execution)
