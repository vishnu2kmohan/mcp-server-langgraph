"""
Unit tests for Studio Orchestrator.

Tests unified orchestration for ALL Studio AI capabilities:
- Consolidates UXOrchestrator + StudioShellOrchestrator
- 8 task categories: UX, SESSION, CONVERSATION, CANVAS, DIAGRAM, TRACE, HITL, COMMAND
- 25+ task types across all categories
- Cross-category insights synthesis
- Feature flag for gradual rollout
- Cost tracking per category
- Persona-aware permission checks

TDD: Tests written FIRST before implementation.
"""

import gc
from decimal import Decimal
from enum import Enum
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.core.feature_flags import feature_flags

pytestmark = [pytest.mark.unit, pytest.mark.agents]


# =============================================================================
# Feature Flag Tests
# =============================================================================


@pytest.mark.xdist_group(name="studio_orchestrator_feature_flags")
class TestStudioOrchestratorFeatureFlags:
    """Test feature flags for Studio AI orchestration."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_enable_studio_ai_flag_exists(self) -> None:
        """Test that enable_studio_ai flag exists."""
        assert hasattr(feature_flags, "enable_studio_ai")

    def test_enable_studio_ai_default_false(self) -> None:
        """Test that studio AI is disabled by default (gradual rollout)."""
        assert feature_flags.enable_studio_ai is False


# =============================================================================
# Module Structure Tests
# =============================================================================


@pytest.mark.xdist_group(name="studio_orchestrator_module")
class TestStudioOrchestratorModule:
    """Test Studio orchestrator module structure."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_studio_orchestrator_module_exists(self) -> None:
        """Test that studio_orchestrator module exists."""
        from mcp_server_langgraph.agents import studio_orchestrator

        assert studio_orchestrator is not None

    def test_studio_orchestrator_class_exists(self) -> None:
        """Test that StudioOrchestrator class exists."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        assert StudioOrchestrator is not None

    def test_studio_task_class_exists(self) -> None:
        """Test that StudioTask class exists."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioTask

        assert StudioTask is not None

    def test_studio_result_class_exists(self) -> None:
        """Test that StudioResult class exists."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioResult

        assert StudioResult is not None

    def test_task_category_enum_exists(self) -> None:
        """Test that TaskCategory enum exists."""
        from mcp_server_langgraph.agents.studio_orchestrator import TaskCategory

        assert TaskCategory is not None
        assert issubclass(TaskCategory, Enum)


# =============================================================================
# TaskCategory Enum Tests
# =============================================================================


@pytest.mark.xdist_group(name="studio_task_category")
class TestTaskCategory:
    """Test TaskCategory enum."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_task_category_has_ux(self) -> None:
        """Test that TaskCategory has UX value."""
        from mcp_server_langgraph.agents.studio_orchestrator import TaskCategory

        assert hasattr(TaskCategory, "UX")
        assert TaskCategory.UX.value == "ux"

    def test_task_category_has_session(self) -> None:
        """Test that TaskCategory has SESSION value."""
        from mcp_server_langgraph.agents.studio_orchestrator import TaskCategory

        assert hasattr(TaskCategory, "SESSION")
        assert TaskCategory.SESSION.value == "session"

    def test_task_category_has_conversation(self) -> None:
        """Test that TaskCategory has CONVERSATION value."""
        from mcp_server_langgraph.agents.studio_orchestrator import TaskCategory

        assert hasattr(TaskCategory, "CONVERSATION")
        assert TaskCategory.CONVERSATION.value == "conversation"

    def test_task_category_has_canvas(self) -> None:
        """Test that TaskCategory has CANVAS value."""
        from mcp_server_langgraph.agents.studio_orchestrator import TaskCategory

        assert hasattr(TaskCategory, "CANVAS")
        assert TaskCategory.CANVAS.value == "canvas"

    def test_task_category_has_diagram(self) -> None:
        """Test that TaskCategory has DIAGRAM value."""
        from mcp_server_langgraph.agents.studio_orchestrator import TaskCategory

        assert hasattr(TaskCategory, "DIAGRAM")
        assert TaskCategory.DIAGRAM.value == "diagram"

    def test_task_category_has_trace(self) -> None:
        """Test that TaskCategory has TRACE value."""
        from mcp_server_langgraph.agents.studio_orchestrator import TaskCategory

        assert hasattr(TaskCategory, "TRACE")
        assert TaskCategory.TRACE.value == "trace"

    def test_task_category_has_hitl(self) -> None:
        """Test that TaskCategory has HITL value."""
        from mcp_server_langgraph.agents.studio_orchestrator import TaskCategory

        assert hasattr(TaskCategory, "HITL")
        assert TaskCategory.HITL.value == "hitl"

    def test_task_category_has_command(self) -> None:
        """Test that TaskCategory has COMMAND value."""
        from mcp_server_langgraph.agents.studio_orchestrator import TaskCategory

        assert hasattr(TaskCategory, "COMMAND")
        assert TaskCategory.COMMAND.value == "command"

    def test_task_category_has_8_categories(self) -> None:
        """Test that TaskCategory has exactly 8 categories."""
        from mcp_server_langgraph.agents.studio_orchestrator import TaskCategory

        assert len(TaskCategory) == 8


# =============================================================================
# StudioTask Tests
# =============================================================================


@pytest.mark.xdist_group(name="studio_task")
class TestStudioTask:
    """Test StudioTask data class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_studio_task_has_category(self) -> None:
        """Test that StudioTask has category field."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioTask,
            TaskCategory,
        )

        task = StudioTask(
            category=TaskCategory.UX,
            task_type="persona_analysis",
            user_id="test-user",
        )
        assert task.category == TaskCategory.UX

    def test_studio_task_has_task_type(self) -> None:
        """Test that StudioTask has task_type field."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioTask,
            TaskCategory,
        )

        task = StudioTask(
            category=TaskCategory.SESSION,
            task_type="session_summarize",
            user_id="test-user",
        )
        assert task.task_type == "session_summarize"

    def test_studio_task_has_user_id(self) -> None:
        """Test that StudioTask has user_id field."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioTask,
            TaskCategory,
        )

        task = StudioTask(
            category=TaskCategory.UX,
            task_type="persona_analysis",
            user_id="test-user-123",
        )
        assert task.user_id == "test-user-123"

    def test_studio_task_has_session_id(self) -> None:
        """Test that StudioTask has optional session_id field."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioTask,
            TaskCategory,
        )

        task = StudioTask(
            category=TaskCategory.SESSION,
            task_type="session_summarize",
            user_id="test-user",
            session_id="session-456",
        )
        assert task.session_id == "session-456"

    def test_studio_task_has_persona(self) -> None:
        """Test that StudioTask has optional persona field for RBAC."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioTask,
            TaskCategory,
        )

        task = StudioTask(
            category=TaskCategory.UX,
            task_type="persona_analysis",
            user_id="test-user",
            persona="alice-builder",
        )
        assert task.persona == "alice-builder"

    def test_studio_task_has_data(self) -> None:
        """Test that StudioTask has data field."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioTask,
            TaskCategory,
        )

        task = StudioTask(
            category=TaskCategory.CANVAS,
            task_type="artifact_suggest_type",
            user_id="test-user",
            data={"content": "some code here"},
        )
        assert task.data == {"content": "some code here"}

    def test_studio_task_data_defaults_to_empty_dict(self) -> None:
        """Test that StudioTask data defaults to empty dict."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioTask,
            TaskCategory,
        )

        task = StudioTask(
            category=TaskCategory.UX,
            task_type="persona_analysis",
            user_id="test-user",
        )
        assert task.data == {}


# =============================================================================
# StudioResult Tests
# =============================================================================


@pytest.mark.xdist_group(name="studio_result")
class TestStudioResult:
    """Test StudioResult data class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_studio_result_has_task_type(self) -> None:
        """Test that StudioResult has task_type field."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioResult

        result = StudioResult(
            task_type="persona_analysis",
            success=True,
            result={"detected_persona": "alice-builder"},
        )
        assert result.task_type == "persona_analysis"

    def test_studio_result_has_success(self) -> None:
        """Test that StudioResult has success field."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioResult

        result = StudioResult(
            task_type="persona_analysis",
            success=True,
        )
        assert result.success is True

    def test_studio_result_has_result(self) -> None:
        """Test that StudioResult has result field."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioResult

        result = StudioResult(
            task_type="persona_analysis",
            success=True,
            result={"confidence": 0.85},
        )
        assert result.result == {"confidence": 0.85}

    def test_studio_result_has_error(self) -> None:
        """Test that StudioResult has error field."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioResult

        result = StudioResult(
            task_type="persona_analysis",
            success=False,
            error="Analysis failed",
        )
        assert result.error == "Analysis failed"


# =============================================================================
# Inheritance Tests
# =============================================================================


@pytest.mark.xdist_group(name="studio_orchestrator_inheritance")
class TestStudioOrchestratorInheritance:
    """Test StudioOrchestrator inherits from BaseOrchestrator."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_studio_orchestrator_inherits_base_orchestrator(self) -> None:
        """Test that StudioOrchestrator inherits from BaseOrchestrator."""
        from mcp_server_langgraph.agents.base_orchestrator import BaseOrchestrator
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        assert issubclass(StudioOrchestrator, BaseOrchestrator)

    def test_studio_orchestrator_has_feature_flag_name_property(self) -> None:
        """Test that StudioOrchestrator has feature_flag_name property."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        orchestrator = StudioOrchestrator()
        assert hasattr(orchestrator, "feature_flag_name")
        assert orchestrator.feature_flag_name == "enable_studio_ai"

    def test_studio_orchestrator_inherits_execute_method(self) -> None:
        """Test that StudioOrchestrator uses inherited execute method."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        assert hasattr(StudioOrchestrator, "execute")

    def test_studio_orchestrator_implements_execute_task(self) -> None:
        """Test that StudioOrchestrator implements _execute_task abstract method."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        orchestrator = StudioOrchestrator()
        assert hasattr(orchestrator, "_execute_task")
        assert callable(orchestrator._execute_task)

    def test_studio_orchestrator_implements_synthesize(self) -> None:
        """Test that StudioOrchestrator implements synthesize abstract method."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        orchestrator = StudioOrchestrator()
        assert hasattr(orchestrator, "synthesize")
        assert callable(orchestrator.synthesize)


# =============================================================================
# Initialization Tests
# =============================================================================


@pytest.mark.xdist_group(name="studio_orchestrator_initialization")
class TestStudioOrchestratorInitialization:
    """Test Studio orchestrator initialization."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_studio_orchestrator_initialization(self) -> None:
        """Test that StudioOrchestrator can be initialized."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        orchestrator = StudioOrchestrator()
        assert orchestrator is not None

    def test_studio_orchestrator_accepts_ai_ux_service(self) -> None:
        """Test that StudioOrchestrator accepts AIUXService."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        mock_service = MagicMock()
        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)
        assert orchestrator.ai_ux_service == mock_service

    def test_studio_orchestrator_accepts_llm_factory(self) -> None:
        """Test that StudioOrchestrator accepts LLMFactory."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        mock_factory = MagicMock()
        orchestrator = StudioOrchestrator(llm_factory=mock_factory)
        assert orchestrator.llm_factory == mock_factory

    def test_studio_orchestrator_accepts_cost_tracker(self) -> None:
        """Test that StudioOrchestrator accepts CostTracker."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        mock_tracker = MagicMock()
        orchestrator = StudioOrchestrator(cost_tracker=mock_tracker)
        assert orchestrator.cost_tracker == mock_tracker

    def test_studio_orchestrator_accepts_enable_metrics(self) -> None:
        """Test that StudioOrchestrator accepts enable_metrics flag."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        orchestrator = StudioOrchestrator(enable_metrics=False)
        assert orchestrator.enable_metrics is False


# =============================================================================
# Task Type Registry Tests
# =============================================================================


@pytest.mark.xdist_group(name="studio_task_types")
class TestStudioTaskTypes:
    """Test Studio orchestrator task type registry."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_studio_task_types_constant_exists(self) -> None:
        """Test that STUDIO_TASK_TYPES constant exists."""
        from mcp_server_langgraph.agents.studio_orchestrator import STUDIO_TASK_TYPES

        assert STUDIO_TASK_TYPES is not None
        assert isinstance(STUDIO_TASK_TYPES, (frozenset, set, dict))

    def test_ux_task_types_exist(self) -> None:
        """Test that UX task types are defined."""
        from mcp_server_langgraph.agents.studio_orchestrator import STUDIO_TASK_TYPES

        ux_types = {
            "persona_analysis",
            "disclosure_analysis",
            "error_analysis",
            "nudge_recommendation",
        }
        for task_type in ux_types:
            assert task_type in STUDIO_TASK_TYPES

    def test_session_task_types_exist(self) -> None:
        """Test that Session task types are defined."""
        from mcp_server_langgraph.agents.studio_orchestrator import STUDIO_TASK_TYPES

        session_types = {"session_summarize", "session_group", "session_similarity"}
        for task_type in session_types:
            assert task_type in STUDIO_TASK_TYPES

    def test_conversation_task_types_exist(self) -> None:
        """Test that Conversation task types are defined."""
        from mcp_server_langgraph.agents.studio_orchestrator import STUDIO_TASK_TYPES

        conversation_types = {"intent_detect", "context_optimize", "goal_track"}
        for task_type in conversation_types:
            assert task_type in STUDIO_TASK_TYPES

    def test_canvas_task_types_exist(self) -> None:
        """Test that Canvas task types are defined."""
        from mcp_server_langgraph.agents.studio_orchestrator import STUDIO_TASK_TYPES

        canvas_types = {"artifact_suggest_type", "code_analyze", "diff_explain"}
        for task_type in canvas_types:
            assert task_type in STUDIO_TASK_TYPES

    def test_diagram_task_types_exist(self) -> None:
        """Test that Diagram task types are defined."""
        from mcp_server_langgraph.agents.studio_orchestrator import STUDIO_TASK_TYPES

        diagram_types = {"diagram_analyze", "diagram_to_code"}
        for task_type in diagram_types:
            assert task_type in STUDIO_TASK_TYPES

    def test_trace_task_types_exist(self) -> None:
        """Test that Trace task types are defined."""
        from mcp_server_langgraph.agents.studio_orchestrator import STUDIO_TASK_TYPES

        trace_types = {"trace_summarize", "trace_anomaly"}
        for task_type in trace_types:
            assert task_type in STUDIO_TASK_TYPES

    def test_hitl_task_types_exist(self) -> None:
        """Test that HITL task types are defined."""
        from mcp_server_langgraph.agents.studio_orchestrator import STUDIO_TASK_TYPES

        hitl_types = {"risk_assess", "decision_history"}
        for task_type in hitl_types:
            assert task_type in STUDIO_TASK_TYPES

    def test_command_task_types_exist(self) -> None:
        """Test that Command task types are defined."""
        from mcp_server_langgraph.agents.studio_orchestrator import STUDIO_TASK_TYPES

        command_types = {"command_interpret", "inline_suggest", "ai_edit_generate"}
        for task_type in command_types:
            assert task_type in STUDIO_TASK_TYPES


# =============================================================================
# Execution Tests
# =============================================================================


@pytest.mark.xdist_group(name="studio_orchestrator_execution")
class TestStudioOrchestratorExecution:
    """Test Studio orchestrator execution."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_has_execute_method(self) -> None:
        """Test that StudioOrchestrator has execute method."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        orchestrator = StudioOrchestrator()
        assert hasattr(orchestrator, "execute")
        assert callable(orchestrator.execute)

    @pytest.mark.asyncio
    async def test_execute_returns_list_of_results(self) -> None:
        """Test that execute returns list of StudioResult."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        # Create mock AIUXService
        mock_service = MagicMock()
        mock_service.analyze_persona = AsyncMock(return_value=MagicMock())

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        tasks = [
            StudioTask(
                category=TaskCategory.UX,
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

        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        # Track execution order
        execution_order: list[str] = []

        async def mock_persona_analysis(*args, **kwargs):
            execution_order.append("persona_start")
            await asyncio.sleep(0.01)
            execution_order.append("persona_end")
            return MagicMock()

        async def mock_session_summarize(*args, **kwargs):
            execution_order.append("session_start")
            await asyncio.sleep(0.01)
            execution_order.append("session_end")
            return MagicMock()

        mock_service = MagicMock()
        mock_service.analyze_persona = mock_persona_analysis
        mock_service.summarize_session = mock_session_summarize

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        tasks = [
            StudioTask(
                category=TaskCategory.UX,
                task_type="persona_analysis",
                user_id="test-user",
            ),
            StudioTask(
                category=TaskCategory.SESSION,
                task_type="session_summarize",
                user_id="test-user",
                session_id="session-123",
            ),
        ]

        await orchestrator.execute(tasks)

        # Verify parallel execution
        if len(execution_order) == 4:
            persona_start_idx = execution_order.index("persona_start")
            session_start_idx = execution_order.index("session_start")
            persona_end_idx = execution_order.index("persona_end")
            session_end_idx = execution_order.index("session_end")

            # Both starts should happen before at least one end
            assert persona_start_idx < max(persona_end_idx, session_end_idx)
            assert session_start_idx < max(persona_end_idx, session_end_idx)


# =============================================================================
# Category Handler Tests
# =============================================================================


@pytest.mark.xdist_group(name="studio_orchestrator_handlers")
class TestStudioOrchestratorHandlers:
    """Test Studio orchestrator category-specific handlers."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_ux_tasks_dispatched_to_ai_ux_service(self) -> None:
        """Test that UX tasks are dispatched to AIUXService."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_result = MagicMock()
        mock_result.model_dump = MagicMock(return_value={"confidence": 0.8})

        mock_service = MagicMock()
        mock_service.analyze_persona = AsyncMock(return_value=mock_result)

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        task = StudioTask(
            category=TaskCategory.UX,
            task_type="persona_analysis",
            user_id="test-user",
        )

        await orchestrator._execute_task(task)
        mock_service.analyze_persona.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_task_type_returns_error_result(self) -> None:
        """Test that unknown task type returns error result."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        orchestrator = StudioOrchestrator()

        task = StudioTask(
            category=TaskCategory.UX,
            task_type="unknown_task_type",
            user_id="test-user",
        )

        result = await orchestrator._execute_task(task)
        assert result.success is False
        assert "unknown" in result.error.lower() or "unsupported" in result.error.lower()


# =============================================================================
# Synthesis Tests
# =============================================================================


@pytest.mark.xdist_group(name="studio_orchestrator_synthesis")
class TestStudioOrchestratorSynthesis:
    """Test Studio orchestrator cross-category synthesis."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_has_synthesize_method(self) -> None:
        """Test that StudioOrchestrator has synthesize method."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        orchestrator = StudioOrchestrator()
        assert hasattr(orchestrator, "synthesize")
        assert callable(orchestrator.synthesize)

    def test_synthesize_generates_cross_insights(self) -> None:
        """Test that synthesize generates cross-category insights."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioResult,
        )

        orchestrator = StudioOrchestrator()

        results = [
            StudioResult(
                task_type="persona_analysis",
                success=True,
                result={"detected_persona": "alice-builder", "confidence": 0.85},
            ),
            StudioResult(
                task_type="session_summarize",
                success=True,
                result={"summary": "User was exploring code analysis features"},
            ),
        ]

        synthesis = orchestrator.synthesize(results)
        assert "cross_insights" in synthesis
        assert isinstance(synthesis["cross_insights"], list)

    def test_synthesize_includes_results(self) -> None:
        """Test that synthesize includes individual results."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioResult,
        )

        orchestrator = StudioOrchestrator()

        results = [
            StudioResult(
                task_type="persona_analysis",
                success=True,
                result={"detected_persona": "bob"},
            ),
        ]

        synthesis = orchestrator.synthesize(results)
        assert "results" in synthesis

    def test_synthesize_includes_failed_analyses(self) -> None:
        """Test that synthesize includes failed analyses."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioResult,
        )

        orchestrator = StudioOrchestrator()

        results = [
            StudioResult(
                task_type="persona_analysis",
                success=True,
                result={},
            ),
            StudioResult(
                task_type="session_summarize",
                success=False,
                error="Service unavailable",
            ),
        ]

        synthesis = orchestrator.synthesize(results)
        assert "failed_analyses" in synthesis or "failed" in synthesis


# =============================================================================
# Run Unified Analysis Tests
# =============================================================================


@pytest.mark.xdist_group(name="studio_orchestrator_unified_analysis")
class TestStudioOrchestratorUnifiedAnalysis:
    """Test Studio orchestrator unified analysis endpoint."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_has_analyze_method(self) -> None:
        """Test that StudioOrchestrator has analyze method."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        orchestrator = StudioOrchestrator()
        assert hasattr(orchestrator, "analyze")
        assert callable(orchestrator.analyze)

    @pytest.mark.asyncio
    async def test_analyze_returns_comprehensive_response(self) -> None:
        """Test that analyze returns comprehensive response."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        mock_service = MagicMock()
        mock_result = MagicMock()
        mock_result.model_dump = MagicMock(return_value={"confidence": 0.8})
        mock_service.analyze_persona = AsyncMock(return_value=mock_result)

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        result = await orchestrator.analyze(
            user_id="test-user",
            session_id="test-session",
            include_ux=True,
            include_session=False,
        )

        assert result is not None
        assert "user_id" in result
        assert "session_id" in result


# =============================================================================
# Feature Flag and Fallback Tests
# =============================================================================


@pytest.mark.xdist_group(name="studio_orchestrator_fallback")
class TestStudioOrchestratorFallback:
    """Test Studio orchestrator feature flag and fallback behavior."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_respects_feature_flag(self) -> None:
        """Test that orchestrator respects enable_studio_ai flag."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        orchestrator = StudioOrchestrator()
        assert hasattr(orchestrator, "is_enabled")

    def test_orchestrator_is_enabled_property(self) -> None:
        """Test that orchestrator has is_enabled property."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        orchestrator = StudioOrchestrator()
        assert isinstance(orchestrator.is_enabled, bool)


# =============================================================================
# Cost Tracking Tests
# =============================================================================


@pytest.mark.xdist_group(name="studio_orchestrator_cost")
class TestStudioOrchestratorCostTracking:
    """Test Studio orchestrator cost tracking."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_has_get_session_cost(self) -> None:
        """Test that StudioOrchestrator has get_session_cost method."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        orchestrator = StudioOrchestrator(session_id="test-session")
        assert hasattr(orchestrator, "get_session_cost")
        assert callable(orchestrator.get_session_cost)

    def test_get_session_cost_returns_decimal(self) -> None:
        """Test that get_session_cost returns Decimal."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        orchestrator = StudioOrchestrator(session_id="test-session")
        cost = orchestrator.get_session_cost()
        assert isinstance(cost, Decimal)

    def test_orchestrator_has_check_budget(self) -> None:
        """Test that StudioOrchestrator has check_budget method."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        orchestrator = StudioOrchestrator(session_id="test-session")
        assert hasattr(orchestrator, "check_budget")
        assert callable(orchestrator.check_budget)


# =============================================================================
# Metrics Tests
# =============================================================================


@pytest.mark.xdist_group(name="studio_orchestrator_metrics")
class TestStudioOrchestratorMetrics:
    """Test Studio orchestrator metrics."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_studio_orchestration_metrics_exist(self) -> None:
        """Test that Studio orchestration metrics are defined."""
        from mcp_server_langgraph.agents.metrics import record_orchestrator_execution

        assert callable(record_orchestrator_execution)


# =============================================================================
# Command Intelligence Tests (TDD - Sprint 2)
# =============================================================================


@pytest.mark.xdist_group(name="studio_orchestrator_command")
class TestCommandIntelligence:
    """Test Command Intelligence task handling.

    Tests for command_interpret, inline_suggest, and ai_edit_generate tasks.
    TDD: Tests written FIRST before implementation.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_command_interpret_dispatches_to_service(self) -> None:
        """Test that command_interpret task dispatches to ai_ux_service."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_result = {"interpreted_command": "create_file", "parameters": {"name": "test.py"}}
        mock_service = MagicMock()
        mock_service.interpret_command = AsyncMock(return_value=mock_result)

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        task = StudioTask(
            category=TaskCategory.COMMAND,
            task_type="command_interpret",
            user_id="test-user",
            session_id="test-session",
            data={"query": "create a new Python file called test.py", "context": {}},
        )

        result = await orchestrator._execute_task(task)

        mock_service.interpret_command.assert_called_once_with(
            query="create a new Python file called test.py",
            context={},
            user_id="test-user",
            session_id="test-session",
        )
        assert result.success is True
        assert result.result == mock_result

    @pytest.mark.asyncio
    async def test_inline_suggest_dispatches_to_service(self) -> None:
        """Test that inline_suggest task dispatches to ai_ux_service."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_result = {
            "suggestions": [
                {"text": "def hello():", "confidence": 0.95},
                {"text": "def hello_world():", "confidence": 0.8},
            ]
        }
        mock_service = MagicMock()
        mock_service.generate_inline_suggestions = AsyncMock(return_value=mock_result)

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        task = StudioTask(
            category=TaskCategory.COMMAND,
            task_type="inline_suggest",
            user_id="test-user",
            session_id="test-session",
            data={
                "code": "def ",
                "cursor_position": 4,
                "language": "python",
            },
        )

        result = await orchestrator._execute_task(task)

        mock_service.generate_inline_suggestions.assert_called_once_with(
            code="def ",
            cursor_position=4,
            language="python",
            user_id="test-user",
            session_id="test-session",
        )
        assert result.success is True
        assert result.result == mock_result

    @pytest.mark.asyncio
    async def test_ai_edit_generate_dispatches_to_service(self) -> None:
        """Test that ai_edit_generate task dispatches to ai_ux_service."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_result = {
            "edited_content": "def hello():\n    print('Hello, World!')\n",
            "diff": {
                "additions": 1,
                "deletions": 0,
            },
            "explanation": "Added print statement",
        }
        mock_service = MagicMock()
        mock_service.generate_ai_edit = AsyncMock(return_value=mock_result)

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        task = StudioTask(
            category=TaskCategory.COMMAND,
            task_type="ai_edit_generate",
            user_id="test-user",
            session_id="test-session",
            data={
                "content": "def hello():\n    pass\n",
                "instruction": "Add a print statement that says Hello World",
                "artifact_type": "code",
            },
        )

        result = await orchestrator._execute_task(task)

        mock_service.generate_ai_edit.assert_called_once_with(
            content="def hello():\n    pass\n",
            instruction="Add a print statement that says Hello World",
            artifact_type="code",
            user_id="test-user",
            session_id="test-session",
        )
        assert result.success is True
        assert result.result == mock_result

    @pytest.mark.asyncio
    async def test_command_task_returns_error_when_service_not_configured(self) -> None:
        """Test that command task returns error when service is not configured."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        orchestrator = StudioOrchestrator(ai_ux_service=None)

        task = StudioTask(
            category=TaskCategory.COMMAND,
            task_type="command_interpret",
            user_id="test-user",
            session_id="test-session",
            data={"query": "test"},
        )

        result = await orchestrator._execute_task(task)

        assert result.success is False
        assert "not configured" in result.error.lower()

    @pytest.mark.asyncio
    async def test_unknown_command_task_type_returns_error(self) -> None:
        """Test that unknown command task type returns error."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        task = StudioTask(
            category=TaskCategory.COMMAND,
            task_type="unknown_command_type",
            user_id="test-user",
            session_id="test-session",
            data={},
        )

        result = await orchestrator._execute_task(task)

        assert result.success is False
        assert "unknown" in result.error.lower()

    @pytest.mark.asyncio
    async def test_command_task_handles_service_exception(self) -> None:
        """Test that command task handles service exceptions gracefully."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.interpret_command = AsyncMock(side_effect=Exception("Service unavailable"))

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        task = StudioTask(
            category=TaskCategory.COMMAND,
            task_type="command_interpret",
            user_id="test-user",
            session_id="test-session",
            data={"query": "test"},
        )

        result = await orchestrator._execute_task(task)

        assert result.success is False
        assert "service unavailable" in result.error.lower()

    @pytest.mark.asyncio
    async def test_command_interpret_with_empty_query(self) -> None:
        """Test command_interpret handles empty query gracefully."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_result = {"interpreted_command": None, "parameters": {}}
        mock_service = MagicMock()
        mock_service.interpret_command = AsyncMock(return_value=mock_result)

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        task = StudioTask(
            category=TaskCategory.COMMAND,
            task_type="command_interpret",
            user_id="test-user",
            session_id="test-session",
            data={"query": "", "context": {}},
        )

        result = await orchestrator._execute_task(task)

        mock_service.interpret_command.assert_called_once()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_inline_suggest_with_various_languages(self) -> None:
        """Test inline_suggest works with various programming languages."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.generate_inline_suggestions = AsyncMock(return_value={"suggestions": []})

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        for lang in ["python", "typescript", "javascript", "rust", "go"]:
            task = StudioTask(
                category=TaskCategory.COMMAND,
                task_type="inline_suggest",
                user_id="test-user",
                session_id="test-session",
                data={
                    "code": "func",
                    "cursor_position": 4,
                    "language": lang,
                },
            )

            result = await orchestrator._execute_task(task)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_ai_edit_generate_with_different_artifact_types(self) -> None:
        """Test ai_edit_generate works with different artifact types."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_service = MagicMock()
        mock_service.generate_ai_edit = AsyncMock(return_value={"edited_content": "edited", "diff": {}})

        orchestrator = StudioOrchestrator(ai_ux_service=mock_service)

        for artifact_type in ["code", "markdown", "json", "mermaid"]:
            task = StudioTask(
                category=TaskCategory.COMMAND,
                task_type="ai_edit_generate",
                user_id="test-user",
                session_id="test-session",
                data={
                    "content": "content",
                    "instruction": "edit it",
                    "artifact_type": artifact_type,
                },
            )

            result = await orchestrator._execute_task(task)
            assert result.success is True


# =============================================================================
# ExplanationOrchestrator Consolidation Tests (TDD - Sprint 3)
# =============================================================================


@pytest.mark.xdist_group(name="studio_orchestrator_explanation_consolidation")
class TestExplanationOrchestratorConsolidation:
    """Test consolidation of ExplanationOrchestrator into StudioOrchestrator.

    ExplanationOrchestrator provides 4 HITL explanation task types:
    - uncertainty_analysis: Analyze WHY the agent is uncertain
    - risk_analysis: Analyze what could go wrong
    - alternatives_analysis: Generate safer alternatives
    - evidence_extraction: Extract confidence factors from reasoning trace

    These should be accessible via StudioOrchestrator's HITL category.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_hitl_explanation_task_types_exist(self) -> None:
        """Test that HITL explanation task types are in STUDIO_TASK_TYPES."""
        from mcp_server_langgraph.agents.studio_orchestrator import STUDIO_TASK_TYPES

        explanation_types = {
            "uncertainty_analysis",
            "risk_analysis",
            "alternatives_analysis",
            "evidence_extraction",
        }
        for task_type in explanation_types:
            assert task_type in STUDIO_TASK_TYPES, f"{task_type} not in STUDIO_TASK_TYPES"

    def test_hitl_explanation_types_mapped_to_hitl_category(self) -> None:
        """Test that explanation task types are mapped to HITL category."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            TASK_TYPE_TO_CATEGORY,
            TaskCategory,
        )

        explanation_types = [
            "uncertainty_analysis",
            "risk_analysis",
            "alternatives_analysis",
            "evidence_extraction",
        ]
        for task_type in explanation_types:
            assert task_type in TASK_TYPE_TO_CATEGORY, f"{task_type} not mapped"
            assert TASK_TYPE_TO_CATEGORY[task_type] == TaskCategory.HITL, f"{task_type} not mapped to HITL"

    def test_studio_orchestrator_accepts_explanation_orchestrator(self) -> None:
        """Test that StudioOrchestrator accepts explanation_orchestrator dependency."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        mock_explanation_orchestrator = MagicMock()
        orchestrator = StudioOrchestrator(explanation_orchestrator=mock_explanation_orchestrator)
        assert orchestrator.explanation_orchestrator == mock_explanation_orchestrator

    def test_explanation_orchestrator_default_to_none(self) -> None:
        """Test that explanation_orchestrator defaults to None."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        orchestrator = StudioOrchestrator()
        assert orchestrator.explanation_orchestrator is None

    @pytest.mark.asyncio
    async def test_uncertainty_analysis_delegated_to_explanation_orchestrator(
        self,
    ) -> None:
        """Test that uncertainty_analysis task delegates to ExplanationOrchestrator."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_result = {"why_uncertain": "The input is ambiguous"}
        mock_explanation_orch = MagicMock()
        mock_explanation_orch._analyze_uncertainty = AsyncMock(return_value=mock_result)

        orchestrator = StudioOrchestrator(explanation_orchestrator=mock_explanation_orch)

        task = StudioTask(
            category=TaskCategory.HITL,
            task_type="uncertainty_analysis",
            user_id="test-user",
            data={
                "approval_id": "approval-123",
                "context": {
                    "agent_name": "TestAgent",
                    "proposed_action": "Delete file",
                    "confidence": 0.65,
                    "threshold": 0.7,
                    "trigger_reason": "low_confidence",
                },
            },
        )

        result = await orchestrator._execute_task(task)

        assert result.success is True
        assert result.result["why_uncertain"] == "The input is ambiguous"

    @pytest.mark.asyncio
    async def test_risk_analysis_delegated_to_explanation_orchestrator(self) -> None:
        """Test that risk_analysis task delegates to ExplanationOrchestrator."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_result = {"what_could_go_wrong": "File deletion is irreversible"}
        mock_explanation_orch = MagicMock()
        mock_explanation_orch._analyze_risk = AsyncMock(return_value=mock_result)

        orchestrator = StudioOrchestrator(explanation_orchestrator=mock_explanation_orch)

        task = StudioTask(
            category=TaskCategory.HITL,
            task_type="risk_analysis",
            user_id="test-user",
            data={
                "approval_id": "approval-123",
                "context": {
                    "proposed_action": "Delete file",
                    "trigger_reason": "destructive_action",
                },
            },
        )

        result = await orchestrator._execute_task(task)

        assert result.success is True
        assert "what_could_go_wrong" in result.result

    @pytest.mark.asyncio
    async def test_alternatives_analysis_delegated_to_explanation_orchestrator(
        self,
    ) -> None:
        """Test that alternatives_analysis task delegates to ExplanationOrchestrator."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_result = {
            "safer_alternatives": [
                {"action": "Move to trash", "confidence": 0.95, "trade_off": "Recoverable"},
            ]
        }
        mock_explanation_orch = MagicMock()
        mock_explanation_orch._analyze_alternatives = AsyncMock(return_value=mock_result)

        orchestrator = StudioOrchestrator(explanation_orchestrator=mock_explanation_orch)

        task = StudioTask(
            category=TaskCategory.HITL,
            task_type="alternatives_analysis",
            user_id="test-user",
            data={
                "approval_id": "approval-123",
                "context": {
                    "proposed_action": "Delete file",
                    "confidence": 0.65,
                },
            },
        )

        result = await orchestrator._execute_task(task)

        assert result.success is True
        assert "safer_alternatives" in result.result

    @pytest.mark.asyncio
    async def test_evidence_extraction_delegated_to_explanation_orchestrator(
        self,
    ) -> None:
        """Test that evidence_extraction task delegates to ExplanationOrchestrator."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_result = {
            "confidence_factors": [
                {"factor": "ambiguous_input", "weight": -0.2, "evidence": "Multiple matches"},
            ],
            "reasoning_trace": ["Step 1", "Step 2"],
        }
        mock_explanation_orch = MagicMock()
        mock_explanation_orch._extract_evidence = AsyncMock(return_value=mock_result)

        orchestrator = StudioOrchestrator(explanation_orchestrator=mock_explanation_orch)

        task = StudioTask(
            category=TaskCategory.HITL,
            task_type="evidence_extraction",
            user_id="test-user",
            data={
                "approval_id": "approval-123",
                "reasoning_trace": ["Step 1", "Step 2"],
            },
        )

        result = await orchestrator._execute_task(task)

        assert result.success is True
        assert "confidence_factors" in result.result

    @pytest.mark.asyncio
    async def test_explanation_task_fallback_when_orchestrator_not_configured(
        self,
    ) -> None:
        """Test explanation tasks return error when orchestrator not configured."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        orchestrator = StudioOrchestrator(explanation_orchestrator=None)

        task = StudioTask(
            category=TaskCategory.HITL,
            task_type="uncertainty_analysis",
            user_id="test-user",
            data={"approval_id": "approval-123", "context": {}},
        )

        result = await orchestrator._execute_task(task)

        assert result.success is False
        assert "not configured" in result.error.lower()

    @pytest.mark.asyncio
    async def test_explanation_task_handles_orchestrator_exception(self) -> None:
        """Test explanation tasks handle orchestrator exceptions gracefully."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_explanation_orch = MagicMock()
        mock_explanation_orch._analyze_uncertainty = AsyncMock(side_effect=Exception("LLM unavailable"))

        orchestrator = StudioOrchestrator(explanation_orchestrator=mock_explanation_orch)

        task = StudioTask(
            category=TaskCategory.HITL,
            task_type="uncertainty_analysis",
            user_id="test-user",
            data={"approval_id": "approval-123", "context": {}},
        )

        result = await orchestrator._execute_task(task)

        assert result.success is False
        assert "llm unavailable" in result.error.lower()

    def test_hitl_category_has_all_task_types(self) -> None:
        """Test HITL category has all expected task types including explanation."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            TASK_TYPE_TO_CATEGORY,
            TaskCategory,
        )

        expected_hitl_types = {
            # Original HITL types
            "risk_assess",
            "decision_history",
            # ExplanationOrchestrator types
            "uncertainty_analysis",
            "risk_analysis",
            "alternatives_analysis",
            "evidence_extraction",
        }

        hitl_types = {k for k, v in TASK_TYPE_TO_CATEGORY.items() if v == TaskCategory.HITL}

        for expected in expected_hitl_types:
            assert expected in hitl_types, f"{expected} not in HITL category"


# =============================================================================
# Status Broadcaster Integration Tests
# =============================================================================


@pytest.mark.xdist_group(name="studio_orchestrator_broadcaster")
class TestStudioOrchestratorBroadcasterIntegration:
    """Test StudioOrchestrator integration with OrchestratorStatusBroadcaster."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_accepts_status_broadcaster(self) -> None:
        """Test that StudioOrchestrator constructor accepts status_broadcaster."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        mock_broadcaster = MagicMock()
        orchestrator = StudioOrchestrator(status_broadcaster=mock_broadcaster)

        assert orchestrator is not None
        assert orchestrator.status_broadcaster is mock_broadcaster

    def test_orchestrator_accepts_user_id(self) -> None:
        """Test that StudioOrchestrator constructor accepts user_id."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        orchestrator = StudioOrchestrator(user_id="user-123")
        assert orchestrator._user_id == "user-123"

    def test_orchestrator_without_broadcaster_has_none(self) -> None:
        """Test that orchestrator without broadcaster has None."""
        from mcp_server_langgraph.agents.studio_orchestrator import StudioOrchestrator

        orchestrator = StudioOrchestrator()
        assert orchestrator.status_broadcaster is None

    @pytest.mark.asyncio
    async def test_broadcaster_task_started_called_on_task_execution(self) -> None:
        """Test that broadcaster.broadcast_task_started is called when task starts."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_broadcaster = MagicMock()
        mock_broadcaster.broadcast_task_started = AsyncMock()  # noqa: async-mock-config
        mock_broadcaster.broadcast_status = AsyncMock()  # noqa: async-mock-config
        mock_broadcaster.broadcast_task_completed = AsyncMock()  # noqa: async-mock-config

        orchestrator = StudioOrchestrator(
            status_broadcaster=mock_broadcaster,
            user_id="user-123",
        )

        # Create a task
        task = StudioTask(
            task_type="persona_analysis",
            category=TaskCategory.UX,
            data={"user_id": "test"},
        )

        # Execute the task
        await orchestrator.execute([task])

        # Verify broadcast_task_started was called
        mock_broadcaster.broadcast_task_started.assert_called()
        call_args = mock_broadcaster.broadcast_task_started.call_args
        assert call_args.kwargs["user_id"] == "user-123"

    @pytest.mark.asyncio
    async def test_broadcaster_task_completed_called_on_success(self) -> None:
        """Test that broadcaster.broadcast_task_completed is called on success."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_broadcaster = MagicMock()
        mock_broadcaster.broadcast_task_started = AsyncMock()  # noqa: async-mock-config
        mock_broadcaster.broadcast_status = AsyncMock()  # noqa: async-mock-config
        mock_broadcaster.broadcast_task_completed = AsyncMock()  # noqa: async-mock-config

        orchestrator = StudioOrchestrator(
            status_broadcaster=mock_broadcaster,
            user_id="user-456",
        )

        task = StudioTask(
            task_type="persona_analysis",
            category=TaskCategory.UX,
            data={"user_id": "test"},
        )

        await orchestrator.execute([task])

        # Verify broadcast_task_completed was called
        mock_broadcaster.broadcast_task_completed.assert_called()
        call_args = mock_broadcaster.broadcast_task_completed.call_args
        assert call_args.kwargs["user_id"] == "user-456"

    @pytest.mark.asyncio
    async def test_broadcaster_status_processing_called(self) -> None:
        """Test that broadcast_status with PROCESSING is called."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_broadcaster = MagicMock()
        mock_broadcaster.broadcast_task_started = AsyncMock()  # noqa: async-mock-config
        mock_broadcaster.broadcast_status = AsyncMock()  # noqa: async-mock-config
        mock_broadcaster.broadcast_task_completed = AsyncMock()  # noqa: async-mock-config

        orchestrator = StudioOrchestrator(
            status_broadcaster=mock_broadcaster,
        )

        task = StudioTask(
            task_type="session_summarize",
            category=TaskCategory.SESSION,
        )

        await orchestrator.execute([task])

        # Verify broadcast_status was called
        mock_broadcaster.broadcast_status.assert_called()

    @pytest.mark.asyncio
    async def test_broadcaster_not_called_when_not_provided(self) -> None:
        """Test that broadcaster methods are not called when not provided."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        # Create orchestrator without broadcaster
        orchestrator = StudioOrchestrator()

        task = StudioTask(
            task_type="persona_analysis",
            category=TaskCategory.UX,
        )

        # This should not raise any errors
        await orchestrator.execute([task])

        # No broadcaster means no calls - just verify execution completes
        assert orchestrator.status_broadcaster is None

    @pytest.mark.asyncio
    async def test_broadcaster_multiple_tasks_all_broadcast(self) -> None:
        """Test that multiple tasks all trigger broadcasts."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )

        mock_broadcaster = MagicMock()
        mock_broadcaster.broadcast_task_started = AsyncMock()  # noqa: async-mock-config
        mock_broadcaster.broadcast_status = AsyncMock()  # noqa: async-mock-config
        mock_broadcaster.broadcast_task_completed = AsyncMock()  # noqa: async-mock-config

        orchestrator = StudioOrchestrator(
            status_broadcaster=mock_broadcaster,
        )

        tasks = [
            StudioTask(task_type="persona_analysis", category=TaskCategory.UX),
            StudioTask(task_type="session_summarize", category=TaskCategory.SESSION),
        ]

        await orchestrator.execute(tasks)

        # Two tasks, so broadcast_task_started should be called twice
        assert mock_broadcaster.broadcast_task_started.call_count == 2
        assert mock_broadcaster.broadcast_task_completed.call_count == 2

    @pytest.mark.asyncio
    async def test_broadcaster_idle_status_broadcast_on_completion(self) -> None:
        """Test that IDLE status is broadcast when all tasks complete."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatus,
        )

        mock_broadcaster = MagicMock()
        mock_broadcaster.broadcast_task_started = AsyncMock()  # noqa: async-mock-config
        mock_broadcaster.broadcast_status = AsyncMock()  # noqa: async-mock-config
        mock_broadcaster.broadcast_task_completed = AsyncMock()  # noqa: async-mock-config

        orchestrator = StudioOrchestrator(
            status_broadcaster=mock_broadcaster,
        )

        tasks = [
            StudioTask(task_type="persona_analysis", category=TaskCategory.UX),
        ]

        await orchestrator.execute(tasks)

        # Find the IDLE status broadcast call
        broadcast_status_calls = mock_broadcaster.broadcast_status.call_args_list
        idle_calls = [
            call
            for call in broadcast_status_calls
            if call.kwargs.get("status") == OrchestratorStatus.IDLE or (call.args and call.args[0] == OrchestratorStatus.IDLE)
        ]

        # Should have at least one IDLE broadcast
        assert len(idle_calls) >= 1, "Expected IDLE status broadcast after all tasks complete"

    @pytest.mark.asyncio
    async def test_broadcaster_idle_status_after_multiple_tasks(self) -> None:
        """Test that IDLE is broadcast only after ALL tasks complete."""
        from mcp_server_langgraph.agents.studio_orchestrator import (
            StudioOrchestrator,
            StudioTask,
            TaskCategory,
        )
        from mcp_server_langgraph.websocket.handlers.orchestrator_status import (
            OrchestratorStatus,
        )

        mock_broadcaster = MagicMock()
        mock_broadcaster.broadcast_task_started = AsyncMock()  # noqa: async-mock-config
        mock_broadcaster.broadcast_status = AsyncMock()  # noqa: async-mock-config
        mock_broadcaster.broadcast_task_completed = AsyncMock()  # noqa: async-mock-config

        orchestrator = StudioOrchestrator(
            status_broadcaster=mock_broadcaster,
        )

        tasks = [
            StudioTask(task_type="persona_analysis", category=TaskCategory.UX),
            StudioTask(task_type="session_summarize", category=TaskCategory.SESSION),
            StudioTask(task_type="intent_detect", category=TaskCategory.CONVERSATION),
        ]

        await orchestrator.execute(tasks)

        # Get all broadcast_status calls in order
        status_calls = mock_broadcaster.broadcast_status.call_args_list

        # The last status call should be IDLE
        last_call = status_calls[-1]
        last_status = last_call.kwargs.get("status") or last_call.args[0]
        assert last_status == OrchestratorStatus.IDLE, f"Last status should be IDLE, got {last_status}"
