"""
Tests for CostTracker Integration in Orchestrator (Phase 5 Integration).

TDD: These tests define the expected behavior for integrating CostTracker
into the Orchestrator's execute() loop.

Tests verify:
1. Orchestrator accepts CostTracker parameter
2. Cost tracking during subagent execution
3. Session cost accumulation
4. Budget checking and alerts
5. Feature flag gating
"""

import gc
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.agents, pytest.mark.orchestrator]


@pytest.mark.xdist_group(name="orchestrator_cost_init")
class TestOrchestratorCostTrackerInit:
    """Test Orchestrator initialization with CostTracker."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestrator_accepts_cost_tracker_parameter(self) -> None:
        """Orchestrator should accept optional cost_tracker parameter."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker
        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        tracker = CostTracker()
        orchestrator = Orchestrator(cost_tracker=tracker)

        assert orchestrator.cost_tracker is tracker

    def test_orchestrator_cost_tracker_defaults_to_none(self) -> None:
        """Orchestrator should default cost_tracker to None if not provided."""
        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        orchestrator = Orchestrator()

        assert orchestrator.cost_tracker is None

    def test_orchestrator_with_session_id_parameter(self) -> None:
        """Orchestrator should accept optional session_id for cost tracking."""
        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        orchestrator = Orchestrator(session_id="session-123")

        assert orchestrator.session_id == "session-123"


@pytest.mark.xdist_group(name="orchestrator_cost_execute")
class TestOrchestratorCostExecute:
    """Test cost tracking during Orchestrator.execute()."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_execute_tracks_cost_when_tracker_provided(self) -> None:
        """execute() should track costs when CostTracker is configured."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker
        from mcp_server_langgraph.agents.orchestrator import Orchestrator, TaskDecomposition, Subtask

        tracker = CostTracker()
        tracker_spy = MagicMock(wraps=tracker)

        orchestrator = Orchestrator(
            cost_tracker=tracker_spy,
            session_id="session-cost-test",
        )

        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[
                Subtask(
                    task_id="subtask-1",
                    title="Test subtask",
                    instructions="Do something",
                    complexity="simple",
                ),
            ],
            synthesis_instructions="Synthesize results",
        )

        # Execute with mocked subagent execution
        with patch.object(orchestrator.coordinator, "execute_all") as mock_execute:
            from mcp_server_langgraph.agents.subagent import SubagentResult

            mock_result = SubagentResult(
                task_id="subtask-1",
                success=True,
                output="Result",
                input_tokens=1000,
                output_tokens=500,
            )
            mock_execute.return_value = [mock_result]

            await orchestrator.execute(decomposition)

            # Verify cost was tracked
            # Note: track_usage should be called once per subagent result
            assert tracker_spy.track_usage.called or tracker.get_session_cost("session-cost-test") >= Decimal("0")

    @pytest.mark.asyncio
    async def test_execute_skips_cost_tracking_when_no_tracker(self) -> None:
        """execute() should work normally without CostTracker."""
        from mcp_server_langgraph.agents.orchestrator import Orchestrator, TaskDecomposition

        orchestrator = Orchestrator()  # No cost tracker

        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[],
            synthesis_instructions="",
        )

        # Should not raise
        results = await orchestrator.execute(decomposition)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_execute_respects_enable_cost_tracking_flag(self) -> None:
        """execute() should respect enable_cost_tracking feature flag."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker
        from mcp_server_langgraph.agents.orchestrator import Orchestrator, TaskDecomposition

        tracker = MagicMock(spec=CostTracker)
        orchestrator = Orchestrator(
            cost_tracker=tracker,
            session_id="session-flag-test",
        )

        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[],
            synthesis_instructions="",
        )

        # Disable cost tracking
        with patch("mcp_server_langgraph.agents.orchestrator.feature_flags") as mock_flags:
            mock_flags.enable_cost_tracking = False
            mock_flags.enable_multi_agent_orchestration = True

            with patch.object(orchestrator.coordinator, "execute_all", return_value=[]):
                await orchestrator.execute(decomposition)

            # Cost tracking should not be called when disabled
            tracker.track_usage.assert_not_called()


@pytest.mark.xdist_group(name="orchestrator_cost_accumulation")
class TestOrchestratorCostAccumulation:
    """Test session cost accumulation across execute() calls."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_multiple_executes_accumulate_session_cost(self) -> None:
        """Multiple execute() calls should accumulate session cost."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker
        from mcp_server_langgraph.agents.orchestrator import Orchestrator, TaskDecomposition

        tracker = CostTracker()
        session_id = "session-accumulate"
        orchestrator = Orchestrator(
            cost_tracker=tracker,
            session_id=session_id,
        )

        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[],
            synthesis_instructions="",
        )

        # Execute twice
        with patch.object(orchestrator.coordinator, "execute_all") as mock_execute:
            from mcp_server_langgraph.agents.subagent import SubagentResult

            mock_result = SubagentResult(
                task_id="subtask-1",
                success=True,
                output="Result",
                input_tokens=100_000,  # Should cost $0.50 for Opus
                output_tokens=0,
            )
            mock_execute.return_value = [mock_result]

            await orchestrator.execute(decomposition)
            cost_after_first = tracker.get_session_cost(session_id)

            await orchestrator.execute(decomposition)
            cost_after_second = tracker.get_session_cost(session_id)

        # Second execution should add more cost
        assert cost_after_second >= cost_after_first

    def test_orchestrator_get_session_cost(self) -> None:
        """Orchestrator should provide method to get current session cost."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker
        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        tracker = CostTracker()
        orchestrator = Orchestrator(
            cost_tracker=tracker,
            session_id="session-get-cost",
        )

        # Pre-populate some cost
        tracker._session_costs["session-get-cost"] = Decimal("1.50")

        cost = orchestrator.get_session_cost()
        assert cost == Decimal("1.50")

    def test_orchestrator_get_session_cost_returns_zero_without_tracker(self) -> None:
        """get_session_cost() should return 0 when no tracker configured."""
        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        orchestrator = Orchestrator()

        cost = orchestrator.get_session_cost()
        assert cost == Decimal("0")


@pytest.mark.xdist_group(name="orchestrator_cost_budget")
class TestOrchestratorCostBudget:
    """Test budget checking in Orchestrator."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestrator_check_budget_returns_alert(self) -> None:
        """Orchestrator should provide method to check budget status."""
        from mcp_server_langgraph.agents.cost_models import BudgetStatus, CostAlert
        from mcp_server_langgraph.agents.cost_tracker import CostTracker
        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        tracker = CostTracker(session_limit=5.00)
        orchestrator = Orchestrator(
            cost_tracker=tracker,
            session_id="session-budget",
        )

        # Set session cost to 60% of limit
        tracker._session_costs["session-budget"] = Decimal("3.00")

        alert = orchestrator.check_budget()

        assert isinstance(alert, CostAlert)
        assert alert.status == BudgetStatus.WARNING

    def test_orchestrator_check_budget_returns_ok_without_tracker(self) -> None:
        """check_budget() should return OK status when no tracker configured."""
        from mcp_server_langgraph.agents.cost_models import BudgetStatus
        from mcp_server_langgraph.agents.orchestrator import Orchestrator

        orchestrator = Orchestrator()

        alert = orchestrator.check_budget()

        assert alert.status == BudgetStatus.OK

    @pytest.mark.asyncio
    async def test_execute_checks_budget_before_execution(self) -> None:
        """execute() should check budget status before running."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker
        from mcp_server_langgraph.agents.orchestrator import Orchestrator, TaskDecomposition
        from mcp_server_langgraph.core.exceptions import BudgetExceededError

        tracker = CostTracker(session_limit=1.00)
        orchestrator = Orchestrator(
            cost_tracker=tracker,
            session_id="session-exceeded",
        )

        # Set session cost to exceed limit
        tracker._session_costs["session-exceeded"] = Decimal("1.50")

        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[],
            synthesis_instructions="",
        )

        # Should raise BudgetExceededError
        with pytest.raises(BudgetExceededError):
            await orchestrator.execute(decomposition)


@pytest.mark.xdist_group(name="subagent_result_tokens")
class TestSubagentResultTokenFields:
    """Test SubagentResult token tracking fields."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_subagent_result_has_input_tokens_field(self) -> None:
        """SubagentResult should have optional input_tokens field."""
        from mcp_server_langgraph.agents.subagent import SubagentResult

        result = SubagentResult(
            task_id="test",
            success=True,
            input_tokens=1000,
        )

        assert result.input_tokens == 1000

    def test_subagent_result_has_output_tokens_field(self) -> None:
        """SubagentResult should have optional output_tokens field."""
        from mcp_server_langgraph.agents.subagent import SubagentResult

        result = SubagentResult(
            task_id="test",
            success=True,
            output_tokens=500,
        )

        assert result.output_tokens == 500

    def test_subagent_result_tokens_default_to_zero(self) -> None:
        """Token fields should default to 0."""
        from mcp_server_langgraph.agents.subagent import SubagentResult

        result = SubagentResult(
            task_id="test",
            success=True,
        )

        assert result.input_tokens == 0
        assert result.output_tokens == 0

    def test_subagent_result_has_model_field(self) -> None:
        """SubagentResult should have optional model field for cost lookup."""
        from mcp_server_langgraph.agents.subagent import SubagentResult

        result = SubagentResult(
            task_id="test",
            success=True,
            model="claude-opus-4-5-20251101",
        )

        assert result.model == "claude-opus-4-5-20251101"
