"""
Unit tests for LoopAgent Pattern (ADR-0084 / Google ADK parity)

TDD: RED phase - Tests for the LoopAgent orchestration pattern.

LoopAgent provides:
- Iterative task execution until a condition is met
- Maximum iteration limits to prevent infinite loops
- Termination condition evaluation
- Continue on error option
- Iteration state tracking

Reference: Google ADK LoopAgent pattern
"""

from __future__ import annotations

import gc
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import pytest

if TYPE_CHECKING:
    pass

pytestmark = [pytest.mark.unit, pytest.mark.agents]


# =============================================================================
# Test Data Classes
# =============================================================================


@dataclass
class LoopTask:
    """Test task for loop iterations."""

    iteration: int = 0
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class LoopResult:
    """Test result from loop iteration."""

    iteration: int
    success: bool
    should_terminate: bool = False
    result: dict[str, Any] | None = None
    error: str | None = None


# =============================================================================
# Feature Flag Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_loop_agent_flag")
class TestLoopAgentFeatureFlag:
    """Test LoopAgent feature flag integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_loop_agent_feature_flag_exists(self) -> None:
        """GIVEN the feature flags module
        WHEN accessing enable_loop_agent
        THEN it should exist as a boolean field with default=False
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_loop_agent")
        assert isinstance(flags.enable_loop_agent, bool)
        # Default should be False (experimental feature)
        assert flags.enable_loop_agent is False

    def test_loop_agent_disabled_raises_error(self) -> None:
        """GIVEN loop_agent feature flag is disabled
        WHEN attempting to create a LoopAgent
        THEN it should raise a FeatureDisabledError
        """
        from mcp_server_langgraph.agents.loop_agent import LoopAgent
        from mcp_server_langgraph.core.exceptions import FeatureDisabledError

        with patch("mcp_server_langgraph.agents.loop_agent.feature_flags") as mock_flags:
            mock_flags.enable_loop_agent = False
            # Mock require_feature to actually raise the error
            mock_flags.require_feature.side_effect = FeatureDisabledError("Loop Agent", "enable_loop_agent")

            with pytest.raises(FeatureDisabledError):
                LoopAgent(max_iterations=5)


# =============================================================================
# LoopAgent Module Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_loop_agent_module")
class TestLoopAgentModule:
    """Test the LoopAgent module structure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_loop_agent_exists(self) -> None:
        """GIVEN the agents module
        WHEN importing LoopAgent
        THEN it should be available
        """
        from mcp_server_langgraph.agents.loop_agent import LoopAgent

        assert LoopAgent is not None

    def test_loop_agent_extends_base_orchestrator(self) -> None:
        """GIVEN a LoopAgent instance
        WHEN checking inheritance
        THEN it should extend BaseOrchestrator
        """
        from mcp_server_langgraph.agents.base_orchestrator import BaseOrchestrator
        from mcp_server_langgraph.agents.loop_agent import LoopAgent

        assert issubclass(LoopAgent, BaseOrchestrator)

    def test_loop_agent_has_required_methods(self) -> None:
        """GIVEN a LoopAgent class
        WHEN checking for required methods
        THEN it should have execute_loop and check_termination methods
        """
        from mcp_server_langgraph.agents.loop_agent import LoopAgent

        assert hasattr(LoopAgent, "execute_loop")
        assert callable(getattr(LoopAgent, "execute_loop", None))
        assert hasattr(LoopAgent, "check_termination")
        assert callable(getattr(LoopAgent, "check_termination", None))


# =============================================================================
# LoopAgent Initialization Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_loop_agent_init")
class TestLoopAgentInitialization:
    """Test LoopAgent initialization and configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_loop_agent_requires_max_iterations(self) -> None:
        """GIVEN LoopAgent initialization
        WHEN max_iterations is not provided
        THEN it should raise a ValueError
        """
        from mcp_server_langgraph.agents.loop_agent import LoopAgent

        with patch("mcp_server_langgraph.agents.loop_agent.feature_flags") as mock_flags:
            mock_flags.enable_loop_agent = True

            with pytest.raises(TypeError):
                LoopAgent()  # Missing required max_iterations

    def test_loop_agent_accepts_max_iterations(self) -> None:
        """GIVEN LoopAgent initialization
        WHEN max_iterations is provided
        THEN it should store the value
        """
        from mcp_server_langgraph.agents.loop_agent import LoopAgent

        with patch("mcp_server_langgraph.agents.loop_agent.feature_flags") as mock_flags:
            mock_flags.enable_loop_agent = True

            agent = LoopAgent(max_iterations=10)
            assert agent.max_iterations == 10

    def test_loop_agent_accepts_termination_condition(self) -> None:
        """GIVEN LoopAgent initialization
        WHEN a termination_condition callable is provided
        THEN it should store the callable
        """
        from mcp_server_langgraph.agents.loop_agent import LoopAgent

        with patch("mcp_server_langgraph.agents.loop_agent.feature_flags") as mock_flags:
            mock_flags.enable_loop_agent = True

            def my_condition(result: Any) -> bool:
                return result.get("done", False)

            agent = LoopAgent(max_iterations=10, termination_condition=my_condition)
            assert agent.termination_condition is my_condition

    def test_loop_agent_continue_on_error_default_false(self) -> None:
        """GIVEN LoopAgent initialization
        WHEN continue_on_error is not specified
        THEN it should default to False
        """
        from mcp_server_langgraph.agents.loop_agent import LoopAgent

        with patch("mcp_server_langgraph.agents.loop_agent.feature_flags") as mock_flags:
            mock_flags.enable_loop_agent = True

            agent = LoopAgent(max_iterations=10)
            assert agent.continue_on_error is False


# =============================================================================
# LoopAgent Execution Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_loop_agent_execution")
class TestLoopAgentExecution:
    """Test LoopAgent execution behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_execute_loop_runs_task(self) -> None:
        """GIVEN a LoopAgent with a task function
        WHEN execute_loop is called
        THEN it should run the task at least once
        """
        from mcp_server_langgraph.agents.loop_agent import LoopAgent

        with patch("mcp_server_langgraph.agents.loop_agent.feature_flags") as mock_flags:
            mock_flags.enable_loop_agent = True

            task_fn = AsyncMock(return_value={"done": True})
            agent = LoopAgent(max_iterations=5)

            result = await agent.execute_loop(task_fn)

            task_fn.assert_called()
            assert result is not None

    @pytest.mark.asyncio
    async def test_execute_loop_respects_max_iterations(self) -> None:
        """GIVEN a LoopAgent with max_iterations=3
        WHEN execute_loop runs with a task that never terminates
        THEN it should stop after 3 iterations
        """
        from mcp_server_langgraph.agents.loop_agent import LoopAgent

        with patch("mcp_server_langgraph.agents.loop_agent.feature_flags") as mock_flags:
            mock_flags.enable_loop_agent = True

            task_fn = AsyncMock(return_value={"done": False})
            agent = LoopAgent(max_iterations=3)

            result = await agent.execute_loop(task_fn)

            assert task_fn.call_count == 3
            assert result["iterations_completed"] == 3

    @pytest.mark.asyncio
    async def test_execute_loop_terminates_on_condition(self) -> None:
        """GIVEN a LoopAgent with a termination condition
        WHEN the condition is met
        THEN the loop should terminate early
        """
        from mcp_server_langgraph.agents.loop_agent import LoopAgent

        with patch("mcp_server_langgraph.agents.loop_agent.feature_flags") as mock_flags:
            mock_flags.enable_loop_agent = True

            # Task returns done=True on 3rd iteration
            call_count = 0

            async def task_fn():
                nonlocal call_count
                call_count += 1
                return {"done": call_count >= 3, "iteration": call_count}

            agent = LoopAgent(
                max_iterations=10,
                termination_condition=lambda r: r.get("done", False),
            )

            result = await agent.execute_loop(task_fn)

            assert call_count == 3
            assert result["terminated_early"] is True

    @pytest.mark.asyncio
    async def test_execute_loop_passes_context_between_iterations(self) -> None:
        """GIVEN a LoopAgent with context passing
        WHEN executing iterations
        THEN the result of each iteration should be available to the next
        """
        from mcp_server_langgraph.agents.loop_agent import LoopAgent

        with patch("mcp_server_langgraph.agents.loop_agent.feature_flags") as mock_flags:
            mock_flags.enable_loop_agent = True

            async def accumulating_task(context: dict[str, Any]) -> dict[str, Any]:
                count = context.get("count", 0) + 1
                return {"count": count, "done": count >= 3}

            agent = LoopAgent(
                max_iterations=10,
                termination_condition=lambda r: r.get("done", False),
            )

            result = await agent.execute_loop(accumulating_task, initial_context={})

            assert result["final_result"]["count"] == 3


# =============================================================================
# LoopAgent Error Handling Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_loop_agent_errors")
class TestLoopAgentErrorHandling:
    """Test LoopAgent error handling behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_execute_loop_stops_on_error_by_default(self) -> None:
        """GIVEN a LoopAgent with continue_on_error=False
        WHEN a task raises an exception
        THEN the loop should stop and return error info
        """
        from mcp_server_langgraph.agents.loop_agent import LoopAgent

        with patch("mcp_server_langgraph.agents.loop_agent.feature_flags") as mock_flags:
            mock_flags.enable_loop_agent = True

            call_count = 0

            async def failing_task():
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise ValueError("Task failed")
                return {"iteration": call_count}

            agent = LoopAgent(max_iterations=5, continue_on_error=False)

            result = await agent.execute_loop(failing_task)

            assert call_count == 2
            assert result["error"] is not None
            assert result["failed_at_iteration"] == 2

    @pytest.mark.asyncio
    async def test_execute_loop_continues_on_error_when_enabled(self) -> None:
        """GIVEN a LoopAgent with continue_on_error=True
        WHEN a task raises an exception
        THEN the loop should continue and record the error
        """
        from mcp_server_langgraph.agents.loop_agent import LoopAgent

        with patch("mcp_server_langgraph.agents.loop_agent.feature_flags") as mock_flags:
            mock_flags.enable_loop_agent = True

            call_count = 0

            async def sometimes_failing_task():
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise ValueError("Task failed")
                return {"iteration": call_count, "done": call_count >= 4}

            agent = LoopAgent(
                max_iterations=5,
                continue_on_error=True,
                termination_condition=lambda r: r.get("done", False),
            )

            result = await agent.execute_loop(sometimes_failing_task)

            assert call_count == 4
            assert len(result["errors"]) == 1
            assert result["errors"][0]["iteration"] == 2


# =============================================================================
# LoopAgent State Tracking Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_loop_agent_state")
class TestLoopAgentStateTracking:
    """Test LoopAgent iteration state tracking."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_execute_loop_tracks_all_results(self) -> None:
        """GIVEN a LoopAgent
        WHEN executing multiple iterations
        THEN all iteration results should be tracked
        """
        from mcp_server_langgraph.agents.loop_agent import LoopAgent

        with patch("mcp_server_langgraph.agents.loop_agent.feature_flags") as mock_flags:
            mock_flags.enable_loop_agent = True

            iteration = 0

            async def tracking_task():
                nonlocal iteration
                iteration += 1
                return {"iteration": iteration, "done": iteration >= 3}

            agent = LoopAgent(
                max_iterations=10,
                termination_condition=lambda r: r.get("done", False),
            )

            result = await agent.execute_loop(tracking_task)

            assert len(result["iteration_results"]) == 3
            assert result["iteration_results"][0]["iteration"] == 1
            assert result["iteration_results"][2]["iteration"] == 3

    @pytest.mark.asyncio
    async def test_execute_loop_records_timing(self) -> None:
        """GIVEN a LoopAgent
        WHEN executing iterations
        THEN timing information should be recorded
        """
        from mcp_server_langgraph.agents.loop_agent import LoopAgent

        with patch("mcp_server_langgraph.agents.loop_agent.feature_flags") as mock_flags:
            mock_flags.enable_loop_agent = True

            task_fn = AsyncMock(return_value={"done": True})
            agent = LoopAgent(max_iterations=5)

            result = await agent.execute_loop(task_fn)

            assert "total_duration_ms" in result
            assert result["total_duration_ms"] >= 0


# =============================================================================
# Module Exports Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_loop_agent_exports")
class TestLoopAgentExports:
    """Test module exports for LoopAgent."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_exports_loop_agent(self) -> None:
        """GIVEN the agents module
        WHEN checking exports
        THEN LoopAgent should be exported
        """
        from mcp_server_langgraph.agents import LoopAgent

        assert LoopAgent is not None

    def test_exports_loop_config(self) -> None:
        """GIVEN the agents module
        WHEN checking exports
        THEN LoopConfig should be exported
        """
        from mcp_server_langgraph.agents import LoopConfig

        assert LoopConfig is not None

    def test_exports_loop_result(self) -> None:
        """GIVEN the agents module
        WHEN checking exports
        THEN LoopResult should be exported
        """
        from mcp_server_langgraph.agents import LoopResult

        assert LoopResult is not None
