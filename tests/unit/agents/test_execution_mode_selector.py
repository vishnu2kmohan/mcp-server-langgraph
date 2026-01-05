"""Tests for ExecutionModeSelector.

TDD: These tests define the contract for execution mode selection based on
task characteristics, complexity, and tool/skill requirements.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="execution_selector_basic")
class TestExecutionModeSelectorBasic:
    """Tests for ExecutionModeSelector basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_execution_mode_selector_exists(self) -> None:
        """Test that ExecutionModeSelector class exists."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector

        assert ExecutionModeSelector is not None

    def test_execution_mode_selector_has_select_method(self) -> None:
        """Test ExecutionModeSelector has select method."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector

        selector = ExecutionModeSelector()
        assert hasattr(selector, "select")
        assert callable(selector.select)

    def test_select_returns_execution_mode(self) -> None:
        """Test select returns an ExecutionMode enum value."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()
        result = selector.select()

        assert isinstance(result, ExecutionMode)


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="execution_selector_pure_llm")
class TestExecutionModeSelectorPureLLM:
    """Tests for PURE_LLM mode selection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_select_pure_llm_when_no_tools_or_skills(self) -> None:
        """Test PURE_LLM selected when no tools or skills needed."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()
        mode = selector.select(tool_count=0, skill_count=0)

        assert mode == ExecutionMode.PURE_LLM

    def test_select_pure_llm_for_simple_chat(self) -> None:
        """Test PURE_LLM for simple chat without tools."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()
        mode = selector.select(
            tool_count=0,
            skill_count=0,
            task_complexity="simple",
        )

        assert mode == ExecutionMode.PURE_LLM


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="execution_selector_tool_calling")
class TestExecutionModeSelectorToolCalling:
    """Tests for TOOL_CALLING mode selection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_select_tool_calling_for_simple_with_few_tools(self) -> None:
        """Test TOOL_CALLING for simple task with 1-3 tools."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()
        mode = selector.select(
            task_complexity="simple",
            tool_count=2,
            requires_exploration=False,
        )

        assert mode == ExecutionMode.TOOL_CALLING

    def test_select_tool_calling_for_low_risk(self) -> None:
        """Test TOOL_CALLING for low-risk tasks with tools."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()
        mode = selector.select(
            task_complexity="complicated",
            risk_level="low",
            tool_count=3,
            requires_exploration=False,
        )

        assert mode == ExecutionMode.TOOL_CALLING

    def test_select_tool_calling_is_default_with_tools(self) -> None:
        """Test TOOL_CALLING is default when tools present but no special requirements."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()
        mode = selector.select(tool_count=1)

        assert mode == ExecutionMode.TOOL_CALLING


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="execution_selector_react")
class TestExecutionModeSelectorReact:
    """Tests for REACT mode selection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_select_react_when_exploration_required(self) -> None:
        """Test REACT when exploration is needed."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()
        mode = selector.select(
            task_complexity="complicated",
            tool_count=3,
            requires_exploration=True,
        )

        assert mode == ExecutionMode.REACT

    def test_select_react_for_multi_step(self) -> None:
        """Test REACT when multi-step processing is needed."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()
        mode = selector.select(
            tool_count=2,
            requires_multi_step=True,
        )

        assert mode == ExecutionMode.REACT

    def test_select_react_for_analysis_task(self) -> None:
        """Test REACT for analysis tasks that need exploration."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()
        mode = selector.select(
            task_complexity="complicated",
            tool_count=4,
            requires_exploration=True,
            requires_multi_step=True,
        )

        assert mode == ExecutionMode.REACT


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="execution_selector_programmatic")
class TestExecutionModeSelectorProgrammatic:
    """Tests for PROGRAMMATIC mode selection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_select_programmatic_for_batch_operations(self) -> None:
        """Test PROGRAMMATIC for batch processing operations."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()
        mode = selector.select(
            tool_count=5,
            requires_batch_processing=True,
            requires_exploration=False,
        )

        assert mode == ExecutionMode.PROGRAMMATIC

    def test_select_programmatic_when_determinism_required(self) -> None:
        """Test PROGRAMMATIC when deterministic execution is needed."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()
        mode = selector.select(
            tool_count=3,
            requires_determinism=True,
        )

        assert mode == ExecutionMode.PROGRAMMATIC

    def test_select_programmatic_for_many_tools_no_exploration(self) -> None:
        """Test PROGRAMMATIC for many tools without exploration."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()
        mode = selector.select(
            tool_count=8,
            requires_exploration=False,
            requires_batch_processing=True,
        )

        assert mode == ExecutionMode.PROGRAMMATIC


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="execution_selector_orchestrator")
class TestExecutionModeSelectorOrchestrator:
    """Tests for ORCHESTRATOR mode selection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_select_orchestrator_for_complex_high_risk(self) -> None:
        """Test ORCHESTRATOR for complex, high-risk tasks."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()
        mode = selector.select(
            task_complexity="complex",
            risk_level="high",
            tool_count=5,
        )

        assert mode == ExecutionMode.ORCHESTRATOR

    def test_select_orchestrator_when_approval_required(self) -> None:
        """Test ORCHESTRATOR when human approval is needed."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()
        mode = selector.select(
            tool_count=3,
            requires_approval=True,
        )

        assert mode == ExecutionMode.ORCHESTRATOR

    def test_select_orchestrator_for_external_dependencies(self) -> None:
        """Test ORCHESTRATOR when external dependencies exist."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()
        mode = selector.select(
            tool_count=2,
            task_complexity="complex",
            has_external_dependencies=True,
        )

        assert mode == ExecutionMode.ORCHESTRATOR


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="execution_selector_edge_cases")
class TestExecutionModeSelectorEdgeCases:
    """Tests for edge cases and special scenarios."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_select_with_only_skills(self) -> None:
        """Test selection when only skills are present (no tools)."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()
        mode = selector.select(
            tool_count=0,
            skill_count=3,
        )

        # Skills imply capability needs, so not PURE_LLM
        assert mode in (ExecutionMode.TOOL_CALLING, ExecutionMode.REACT)

    def test_select_with_mixed_requirements(self) -> None:
        """Test selection with competing requirements."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()
        # Both exploration and batch - exploration wins (REACT)
        mode = selector.select(
            tool_count=5,
            requires_exploration=True,
            requires_batch_processing=True,
        )

        # REACT wins when exploration is needed
        assert mode == ExecutionMode.REACT

    def test_select_all_defaults(self) -> None:
        """Test selection with all default values."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()
        mode = selector.select()

        # No tools = PURE_LLM
        assert mode == ExecutionMode.PURE_LLM

    def test_select_clarification_triggers_orchestrator(self) -> None:
        """Test that clarification requirement triggers ORCHESTRATOR."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()
        mode = selector.select(
            tool_count=2,
            requires_clarification=True,
        )

        assert mode == ExecutionMode.ORCHESTRATOR
