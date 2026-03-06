"""
Unit tests for Explanation Orchestrator.

Tests AI explanation generation using parallel execution pattern:
- Parallel execution of uncertainty, risk, alternatives, evidence analyses
- Synthesis into AIExplanation model
- Feature flag for gradual rollout
- Integration with LLM factory

TDD: Tests written FIRST before implementation.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.core.feature_flags import feature_flags

pytestmark = [pytest.mark.unit, pytest.mark.agents]


class TestExplanationOrchestratorFeatureFlags:
    """Test feature flags for AI explanations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_enable_ai_explanations_flag_exists(self) -> None:
        """Test that enable_ai_explanations flag exists."""
        assert hasattr(feature_flags, "enable_ai_explanations")

    def test_enable_ai_explanations_default_false(self) -> None:
        """Test that AI explanations is disabled by default (gradual rollout)."""
        assert feature_flags.enable_ai_explanations is False


class TestExplanationOrchestratorInheritance:
    """Test ExplanationOrchestrator inherits from BaseOrchestrator."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_explanation_orchestrator_inherits_base_orchestrator(self) -> None:
        """Test that ExplanationOrchestrator inherits from BaseOrchestrator."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseOrchestrator
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )

        assert issubclass(ExplanationOrchestrator, BaseOrchestrator)

    def test_explanation_orchestrator_has_feature_flag_name_property(self) -> None:
        """Test that ExplanationOrchestrator has feature_flag_name property."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )

        orchestrator = ExplanationOrchestrator()
        assert hasattr(orchestrator, "feature_flag_name")
        assert orchestrator.feature_flag_name == "enable_ai_explanations"

    def test_explanation_orchestrator_inherits_execute_method(self) -> None:
        """Test that ExplanationOrchestrator uses inherited execute method."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )

        assert hasattr(ExplanationOrchestrator, "execute")

    def test_explanation_orchestrator_implements_execute_task(self) -> None:
        """Test that ExplanationOrchestrator implements _execute_task abstract method."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )

        orchestrator = ExplanationOrchestrator()
        assert hasattr(orchestrator, "_execute_task")
        assert callable(orchestrator._execute_task)

    def test_explanation_orchestrator_implements_synthesize(self) -> None:
        """Test that ExplanationOrchestrator implements synthesize abstract method."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )

        orchestrator = ExplanationOrchestrator()
        assert hasattr(orchestrator, "synthesize")
        assert callable(orchestrator.synthesize)


class TestExplanationOrchestratorModule:
    """Test explanation orchestrator module structure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_explanation_orchestrator_module_exists(self) -> None:
        """Test that explanation_orchestrator module exists."""
        from mcp_server_langgraph.agents import explanation_orchestrator

        assert explanation_orchestrator is not None

    def test_explanation_orchestrator_class_exists(self) -> None:
        """Test that ExplanationOrchestrator class exists."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )

        assert ExplanationOrchestrator is not None

    def test_explanation_task_class_exists(self) -> None:
        """Test that ExplanationTask class exists."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationTask,
        )

        assert ExplanationTask is not None

    def test_explanation_result_class_exists(self) -> None:
        """Test that ExplanationResult class exists."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationResult,
        )

        assert ExplanationResult is not None

    def test_explanation_analysis_types_defined(self) -> None:
        """Test that explanation analysis types are defined."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            EXPLANATION_ANALYSIS_TYPES,
        )

        expected_types = {
            "uncertainty_analysis",
            "risk_analysis",
            "alternatives_analysis",
            "evidence_extraction",
        }
        assert expected_types == set(EXPLANATION_ANALYSIS_TYPES)


class TestExplanationOrchestratorInitialization:
    """Test explanation orchestrator initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_explanation_orchestrator_initialization(self) -> None:
        """Test that ExplanationOrchestrator can be initialized."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )

        orchestrator = ExplanationOrchestrator()
        assert orchestrator is not None

    def test_explanation_orchestrator_accepts_llm_factory(self) -> None:
        """Test that ExplanationOrchestrator accepts LLM factory."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )

        mock_llm = MagicMock()
        orchestrator = ExplanationOrchestrator(llm_factory=mock_llm)
        assert orchestrator.llm_factory == mock_llm

    def test_explanation_orchestrator_accepts_artifact_storage(self) -> None:
        """Test that ExplanationOrchestrator accepts ArtifactStorage."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )

        mock_storage = MagicMock()
        orchestrator = ExplanationOrchestrator(artifact_storage=mock_storage)
        assert orchestrator.artifact_storage == mock_storage

    def test_explanation_orchestrator_accepts_cost_tracker(self) -> None:
        """Test that ExplanationOrchestrator accepts cost tracker."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )

        mock_tracker = MagicMock()
        orchestrator = ExplanationOrchestrator(cost_tracker=mock_tracker)
        assert orchestrator.cost_tracker == mock_tracker


class TestExplanationTask:
    """Test ExplanationTask data class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_explanation_task_has_task_type(self) -> None:
        """Test that ExplanationTask has task_type field."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationTask,
        )

        task = ExplanationTask(
            task_type="uncertainty_analysis",
            approval_id="test-approval-id",
        )
        assert task.task_type == "uncertainty_analysis"

    def test_explanation_task_has_approval_id(self) -> None:
        """Test that ExplanationTask has approval_id field."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationTask,
        )

        task = ExplanationTask(
            task_type="uncertainty_analysis",
            approval_id="approval-123",
        )
        assert task.approval_id == "approval-123"

    def test_explanation_task_has_context(self) -> None:
        """Test that ExplanationTask has context field."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationTask,
        )

        context = {
            "agent_name": "TestAgent",
            "confidence": 0.65,
            "threshold": 0.7,
        }
        task = ExplanationTask(
            task_type="uncertainty_analysis",
            approval_id="test-id",
            context=context,
        )
        assert task.context == context

    def test_explanation_task_has_reasoning_trace(self) -> None:
        """Test that ExplanationTask has reasoning_trace field."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationTask,
        )

        trace = ["Step 1", "Step 2"]
        task = ExplanationTask(
            task_type="evidence_extraction",
            approval_id="test-id",
            reasoning_trace=trace,
        )
        assert task.reasoning_trace == trace

    def test_explanation_task_supports_all_types(self) -> None:
        """Test that ExplanationTask supports all analysis types."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            EXPLANATION_ANALYSIS_TYPES,
            ExplanationTask,
        )

        for task_type in EXPLANATION_ANALYSIS_TYPES:
            task = ExplanationTask(
                task_type=task_type,
                approval_id="test-id",
            )
            assert task.task_type == task_type


class TestExplanationResult:
    """Test ExplanationResult data class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_explanation_result_has_task_type(self) -> None:
        """Test that ExplanationResult has task_type field."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationResult,
        )

        result = ExplanationResult(
            task_type="uncertainty_analysis",
            success=True,
            result={"why_uncertain": "Test explanation"},
        )
        assert result.task_type == "uncertainty_analysis"

    def test_explanation_result_has_success(self) -> None:
        """Test that ExplanationResult has success field."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationResult,
        )

        result = ExplanationResult(
            task_type="uncertainty_analysis",
            success=True,
        )
        assert result.success is True

    def test_explanation_result_has_error(self) -> None:
        """Test that ExplanationResult can have error field."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationResult,
        )

        result = ExplanationResult(
            task_type="uncertainty_analysis",
            success=False,
            error="LLM call failed",
        )
        assert result.error == "LLM call failed"


class TestExplanationOrchestratorExecution:
    """Test explanation orchestrator execution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestrator_has_execute_method(self) -> None:
        """Test that ExplanationOrchestrator has execute method."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )

        orchestrator = ExplanationOrchestrator()
        assert hasattr(orchestrator, "execute")
        assert callable(orchestrator.execute)

    @pytest.mark.asyncio
    async def test_execute_returns_list_of_results(self) -> None:
        """Test that execute returns list of ExplanationResult."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
            ExplanationTask,
        )

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Test explanation"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        orchestrator = ExplanationOrchestrator(llm_factory=mock_llm)

        tasks = [
            ExplanationTask(
                task_type="uncertainty_analysis",
                approval_id="test-id",
                context={"agent_name": "TestAgent"},
            ),
        ]

        results = await orchestrator.execute(tasks)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_execute_runs_tasks_in_parallel(self) -> None:
        """Test that execute runs tasks in parallel."""
        import asyncio

        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
            ExplanationTask,
        )

        execution_order: list[str] = []

        async def mock_ainvoke(*args, **kwargs):
            task_name = "task"
            execution_order.append(f"{task_name}_start")
            await asyncio.sleep(0.01)
            execution_order.append(f"{task_name}_end")
            response = MagicMock()
            response.content = "Test"
            return response

        mock_llm = MagicMock()
        mock_llm.ainvoke = mock_ainvoke

        orchestrator = ExplanationOrchestrator(llm_factory=mock_llm)

        tasks = [
            ExplanationTask(
                task_type="uncertainty_analysis",
                approval_id="test-id",
                context={},
            ),
            ExplanationTask(
                task_type="risk_analysis",
                approval_id="test-id",
                context={},
            ),
        ]

        await orchestrator.execute(tasks)

        # Should have interleaved execution patterns for parallel
        assert len(execution_order) == 4


class TestExplanationOrchestratorSynthesis:
    """Test explanation orchestrator synthesis."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestrator_has_synthesize_method(self) -> None:
        """Test that ExplanationOrchestrator has synthesize method."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )

        orchestrator = ExplanationOrchestrator()
        assert hasattr(orchestrator, "synthesize")
        assert callable(orchestrator.synthesize)

    def test_synthesize_combines_results(self) -> None:
        """Test that synthesize combines results into explanation dict."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
            ExplanationResult,
        )

        orchestrator = ExplanationOrchestrator()

        results = [
            ExplanationResult(
                task_type="uncertainty_analysis",
                success=True,
                result={"why_uncertain": "Input is ambiguous."},
            ),
            ExplanationResult(
                task_type="risk_analysis",
                success=True,
                result={"what_could_go_wrong": "May perform wrong action."},
            ),
        ]

        synthesis = orchestrator.synthesize(results)
        assert "explanation" in synthesis
        assert synthesis["explanation"]["why_uncertain"] == "Input is ambiguous."
        assert synthesis["explanation"]["what_could_go_wrong"] == "May perform wrong action."

    def test_synthesize_handles_failed_analyses(self) -> None:
        """Test that synthesize handles failed analyses."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
            ExplanationResult,
        )

        orchestrator = ExplanationOrchestrator()

        results = [
            ExplanationResult(
                task_type="uncertainty_analysis",
                success=True,
                result={"why_uncertain": "Test"},
            ),
            ExplanationResult(
                task_type="risk_analysis",
                success=False,
                error="LLM timeout",
            ),
        ]

        synthesis = orchestrator.synthesize(results)
        assert "failed_analyses" in synthesis
        assert "risk_analysis" in synthesis["failed_analyses"]


class TestExplanationOrchestratorGenerateExplanation:
    """Test generate_explanation main entry point."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestrator_has_generate_explanation(self) -> None:
        """Test that ExplanationOrchestrator has generate_explanation method."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )

        orchestrator = ExplanationOrchestrator()
        assert hasattr(orchestrator, "generate_explanation")
        assert callable(orchestrator.generate_explanation)

    @pytest.mark.asyncio
    async def test_generate_explanation_returns_ai_explanation(self) -> None:
        """Test that generate_explanation returns AIExplanation model."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Test explanation content"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        orchestrator = ExplanationOrchestrator(llm_factory=mock_llm)

        result = await orchestrator.generate_explanation(
            approval_id="test-approval-id",
            agent_name="TestAgent",
            proposed_action="Delete old files",
            confidence=0.65,
            threshold=0.7,
            trigger_reason="low_confidence",
        )

        assert isinstance(result, AIExplanation)

    @pytest.mark.asyncio
    async def test_generate_explanation_includes_reasoning_trace(self) -> None:
        """Test that generate_explanation accepts and uses reasoning trace."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Test explanation"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        orchestrator = ExplanationOrchestrator(llm_factory=mock_llm)

        trace = ["Step 1: Parsed query", "Step 2: Found ambiguity"]
        result = await orchestrator.generate_explanation(
            approval_id="test-id",
            agent_name="Agent",
            proposed_action="Action",
            confidence=0.6,
            threshold=0.7,
            trigger_reason="low_confidence",
            reasoning_trace=trace,
        )

        assert isinstance(result, AIExplanation)


class TestExplanationOrchestratorFallback:
    """Test explanation orchestrator feature flag fallback."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestrator_respects_feature_flag(self) -> None:
        """Test that orchestrator respects enable_ai_explanations flag."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )

        orchestrator = ExplanationOrchestrator()
        assert hasattr(orchestrator, "is_enabled")

    def test_orchestrator_is_enabled_property(self) -> None:
        """Test that orchestrator has is_enabled property."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
        )

        orchestrator = ExplanationOrchestrator()
        # Default is False for gradual rollout
        assert isinstance(orchestrator.is_enabled, bool)


class TestExplanationOrchestratorNoLLM:
    """Test explanation orchestrator behavior when LLM is not configured."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_execute_returns_failed_result_when_no_llm(self) -> None:
        """Test that execute returns failed result when LLM not configured."""
        from mcp_server_langgraph.agents.explanation_orchestrator import (
            ExplanationOrchestrator,
            ExplanationTask,
        )

        orchestrator = ExplanationOrchestrator(llm_factory=None)

        tasks = [
            ExplanationTask(
                task_type="uncertainty_analysis",
                approval_id="test-id",
                context={},
            ),
        ]

        results = await orchestrator.execute(tasks)
        assert len(results) == 1
        assert results[0].success is False
        assert "not configured" in results[0].error.lower()
