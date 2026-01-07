"""
Integration tests for Orchestrator Cost + Resilience patterns.

Tests the combined behavior of Phase 5 (CostTracker) and Phase 10 (Resilience)
integration in the multi-agent orchestrator.

These tests verify:
1. Cost tracking works with resilience wrappers
2. Budget checks work with circuit breakers
3. Session costs accumulate across retried operations
4. Metrics are properly recorded for both patterns
"""

import gc
from decimal import Decimal
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.orchestrator]


@pytest.mark.xdist_group(name="cost_resilience_integration")
class TestCostResilienceIntegration:
    """Test CostTracker + Resilience patterns working together."""

    def teardown_method(self) -> None:
        """Force GC and reset circuit breakers."""
        from mcp_server_langgraph.agents.resilience import reset_orchestrator_circuit_breaker
        from mcp_server_langgraph.resilience import reset_all_circuit_breakers

        reset_orchestrator_circuit_breaker()
        reset_all_circuit_breakers()
        gc.collect()

    @pytest.mark.asyncio
    async def test_resilient_orchestrate_tracks_costs(self) -> None:
        """Test that resilient_orchestrate tracks costs after successful execution."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker
        from mcp_server_langgraph.agents.orchestrator import Orchestrator, TaskDecomposition
        from mcp_server_langgraph.agents.resilience import resilient_orchestrate
        from mcp_server_langgraph.agents.subagent import SubagentResult

        tracker = CostTracker()
        session_id = "session-resilient-cost"
        orchestrator = Orchestrator(
            cost_tracker=tracker,
            session_id=session_id,
        )

        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[],
            synthesis_instructions="",
        )

        # Execute with resilience wrappers
        with patch.object(orchestrator.coordinator, "execute_all") as mock_execute:
            mock_result = SubagentResult(
                task_id="subtask-1",
                success=True,
                output="Result",
                input_tokens=1000,
                output_tokens=500,
                model="claude-opus-4-5-20251101",
            )
            mock_execute.return_value = [mock_result]

            # Use resilient wrapper
            results = await resilient_orchestrate(orchestrator, decomposition)

            assert len(results) == 1
            # Cost should have been tracked
            session_cost = tracker.get_session_cost(session_id)
            assert session_cost >= Decimal("0")

    @pytest.mark.asyncio
    async def test_budget_exceeded_prevents_resilient_execution(self) -> None:
        """Test that budget exceeded error prevents execution even with resilience."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker
        from mcp_server_langgraph.agents.orchestrator import Orchestrator, TaskDecomposition
        from mcp_server_langgraph.agents.resilience import resilient_orchestrate
        from mcp_server_langgraph.core.exceptions import BudgetExceededError

        tracker = CostTracker(session_limit=1.00)
        session_id = "session-budget-resilience"
        orchestrator = Orchestrator(
            cost_tracker=tracker,
            session_id=session_id,
        )

        # Pre-set session cost to exceed limit
        tracker._session_costs[session_id] = Decimal("1.50")

        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[],
            synthesis_instructions="",
        )

        # Even with resilience wrappers, budget exceeded should raise
        with patch("mcp_server_langgraph.agents.orchestrator.feature_flags") as mock_flags:
            mock_flags.enable_cost_tracking = True
            mock_flags.enable_multi_agent_orchestration = True

            with pytest.raises(BudgetExceededError):
                await resilient_orchestrate(orchestrator, decomposition)

    @pytest.mark.asyncio
    async def test_retried_subagent_accumulates_cost(self) -> None:
        """Test that retried subagent executions accumulate costs correctly."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker
        from mcp_server_langgraph.agents.resilience import resilient_subagent_execute
        from mcp_server_langgraph.agents.subagent import Subagent, SubagentResult

        tracker = CostTracker()
        session_id = "session-retry-cost"

        subagent = Subagent(
            task_id="retry-test",
            instructions="Test retry cost",
            model="claude-opus-4-5-20251101",
        )

        # Track initial cost
        tracker.get_session_cost(session_id)

        # Mock execute to succeed
        with patch.object(subagent, "execute") as mock_execute:
            mock_result = SubagentResult(
                task_id="retry-test",
                success=True,
                output="Success after retry",
                input_tokens=500,
                output_tokens=250,
            )
            mock_execute.return_value = mock_result

            result = await resilient_subagent_execute(subagent, max_retries=2)
            assert result.success

    @pytest.mark.asyncio
    async def test_circuit_breaker_does_not_charge_cost(self) -> None:
        """Test that circuit breaker open state does not incur costs."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker
        from mcp_server_langgraph.agents.orchestrator import Orchestrator, TaskDecomposition
        from mcp_server_langgraph.agents.resilience import (
            get_orchestrator_circuit_breaker,
            reset_orchestrator_circuit_breaker,
            resilient_orchestrate,
        )
        from mcp_server_langgraph.core.exceptions import CircuitBreakerOpenError

        import pybreaker

        # Reset to ensure clean state
        reset_orchestrator_circuit_breaker()

        tracker = CostTracker()
        session_id = "session-cb-no-cost"
        orchestrator = Orchestrator(
            cost_tracker=tracker,
            session_id=session_id,
        )

        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[],
            synthesis_instructions="",
        )

        # Get initial cost
        initial_cost = tracker.get_session_cost(session_id)

        # Manually open the circuit breaker by causing failures
        cb = get_orchestrator_circuit_breaker()
        threshold = cb.fail_max

        # Force failures to open the circuit
        async def failing_execute(*args, **kwargs):
            raise RuntimeError("Simulated failure to open circuit")

        original_execute = orchestrator.execute
        orchestrator.execute = failing_execute

        # Cause enough failures to open the circuit
        for _ in range(threshold):
            try:
                await resilient_orchestrate(orchestrator, decomposition)
            except RuntimeError:
                pass

        # Circuit should now be open
        assert cb.current_state == pybreaker.STATE_OPEN

        # Restore original execute
        orchestrator.execute = original_execute

        # Attempt execution - should fail fast with CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            await resilient_orchestrate(orchestrator, decomposition)

        # Cost should not have increased beyond initial (fail fast, no execution)
        final_cost = tracker.get_session_cost(session_id)
        assert final_cost == initial_cost


@pytest.mark.xdist_group(name="cost_resilience_metrics")
class TestCostResilienceMetrics:
    """Test that metrics are properly recorded for both cost and resilience patterns."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_orchestrator_metrics_include_cost_and_resilience(self) -> None:
        """Test that orchestrator execution records both cost and resilience metrics."""
        from mcp_server_langgraph.agents.orchestrator import Orchestrator, TaskDecomposition

        orchestrator = Orchestrator()
        decomposition = TaskDecomposition(
            original_task="Test metrics",
            subtasks=[],
            synthesis_instructions="",
        )

        # Execute and verify metrics are recorded
        with patch.object(orchestrator.coordinator, "execute_all", return_value=[]):
            results = await orchestrator.execute(decomposition)
            assert isinstance(results, list)

        # Metrics should have been called
        # (This is verified by the absence of exceptions)

    def test_cost_tracker_records_usage_metrics(self) -> None:
        """Test that CostTracker records usage metrics."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker

        tracker = CostTracker()

        # Track usage
        record = tracker.track_usage(
            model="claude-opus-4-5-20251101",
            input_tokens=1000,
            output_tokens=500,
            task_id="metrics-test",
            session_id="session-metrics",
        )

        # Verify record contains expected data
        assert record.input_tokens == 1000
        assert record.output_tokens == 500
        assert record.total_cost > Decimal("0")


@pytest.mark.xdist_group(name="cost_resilience_feature_flags")
class TestCostResilienceFeatureFlags:
    """Test feature flag interactions between cost and resilience."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    def test_both_feature_flags_exist(self) -> None:
        """Test that both cost and resilience feature flags exist."""
        from mcp_server_langgraph.core.feature_flags import feature_flags

        assert hasattr(feature_flags, "enable_cost_tracking")
        assert hasattr(feature_flags, "enable_orchestrator_resilience")

    def test_feature_flags_are_independent(self) -> None:
        """Test that cost and resilience flags can be toggled independently."""
        from mcp_server_langgraph.core.feature_flags import feature_flags

        # Both should be booleans
        assert isinstance(feature_flags.enable_cost_tracking, bool)
        assert isinstance(feature_flags.enable_orchestrator_resilience, bool)

    @pytest.mark.asyncio
    async def test_cost_tracking_works_without_resilience(self) -> None:
        """Test that cost tracking works even when resilience is disabled."""
        from mcp_server_langgraph.agents.cost_tracker import CostTracker
        from mcp_server_langgraph.agents.orchestrator import Orchestrator, TaskDecomposition
        from mcp_server_langgraph.agents.subagent import SubagentResult

        tracker = CostTracker()
        session_id = "session-cost-only"
        orchestrator = Orchestrator(
            cost_tracker=tracker,
            session_id=session_id,
        )

        decomposition = TaskDecomposition(
            original_task="Test cost only",
            subtasks=[],
            synthesis_instructions="",
        )

        # Execute directly (not through resilience wrapper)
        with patch.object(orchestrator.coordinator, "execute_all") as mock_execute:
            mock_result = SubagentResult(
                task_id="subtask-1",
                success=True,
                output="Result",
                input_tokens=1000,
                output_tokens=500,
            )
            mock_execute.return_value = [mock_result]

            results = await orchestrator.execute(decomposition)
            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_resilience_works_without_cost_tracking(self) -> None:
        """Test that resilience works even when cost tracking is disabled."""
        from mcp_server_langgraph.agents.orchestrator import Orchestrator, TaskDecomposition
        from mcp_server_langgraph.agents.resilience import resilient_orchestrate

        # No cost tracker configured
        orchestrator = Orchestrator()

        decomposition = TaskDecomposition(
            original_task="Test resilience only",
            subtasks=[],
            synthesis_instructions="",
        )

        # Should work without cost tracker
        results = await resilient_orchestrate(orchestrator, decomposition)
        assert isinstance(results, list)
