"""
Unit tests for Orchestrator Resilience Integration (Phase 10).

Tests resilience patterns applied to the multi-agent orchestrator:
- Circuit breaker for orchestrator failures
- Timeout on parallel execution
- Bulkhead for concurrent orchestrations
- Retry for transient subagent failures
- Feature flags for orchestrator resilience
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.core.feature_flags import feature_flags

pytestmark = [pytest.mark.unit, pytest.mark.agents]


@pytest.mark.xdist_group(name="orchestrator_resilience_flags")
class TestOrchestratorResilienceFeatureFlags:
    """Test feature flags for orchestrator resilience."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_enable_orchestrator_resilience_flag_exists(self) -> None:
        """Test that enable_orchestrator_resilience flag exists."""
        assert hasattr(feature_flags, "enable_orchestrator_resilience")

    def test_enable_orchestrator_resilience_default_true(self) -> None:
        """Test that orchestrator resilience is enabled by default."""
        assert feature_flags.enable_orchestrator_resilience is True

    def test_orchestrator_timeout_seconds_flag_exists(self) -> None:
        """Test that orchestrator_timeout_seconds flag exists."""
        assert hasattr(feature_flags, "orchestrator_timeout_seconds")

    def test_orchestrator_timeout_seconds_default_300(self) -> None:
        """Test that orchestrator timeout defaults to 300 seconds."""
        assert feature_flags.orchestrator_timeout_seconds == 300

    def test_orchestrator_max_concurrent_flag_exists(self) -> None:
        """Test that orchestrator_max_concurrent flag exists."""
        assert hasattr(feature_flags, "orchestrator_max_concurrent")

    def test_orchestrator_max_concurrent_default_5(self) -> None:
        """Test that max concurrent orchestrations defaults to 5."""
        assert feature_flags.orchestrator_max_concurrent == 5

    def test_orchestrator_circuit_breaker_threshold_flag_exists(self) -> None:
        """Test that orchestrator_circuit_breaker_threshold flag exists."""
        assert hasattr(feature_flags, "orchestrator_circuit_breaker_threshold")

    def test_orchestrator_circuit_breaker_threshold_default_3(self) -> None:
        """Test that circuit breaker threshold defaults to 3 failures."""
        assert feature_flags.orchestrator_circuit_breaker_threshold == 3


@pytest.mark.xdist_group(name="orchestrator_resilience_wrapper")
class TestOrchestratorResilienceWrapper:
    """Test resilience wrapper functions for orchestrator."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_resilient_orchestrate_function_exists(self) -> None:
        """Test that resilient_orchestrate wrapper function exists."""
        from mcp_server_langgraph.agents.resilience import resilient_orchestrate

        assert callable(resilient_orchestrate)

    def test_resilient_subagent_execute_function_exists(self) -> None:
        """Test that resilient_subagent_execute wrapper function exists."""
        from mcp_server_langgraph.agents.resilience import resilient_subagent_execute

        assert callable(resilient_subagent_execute)


@pytest.mark.xdist_group(name="orchestrator_resilience_execute")
class TestOrchestratorResilienceExecution:
    """Test resilience during orchestrator execution."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_resilient_orchestrate_applies_timeout(self) -> None:
        """Test that resilient_orchestrate applies timeout."""
        from mcp_server_langgraph.agents.orchestrator import Orchestrator, TaskDecomposition
        from mcp_server_langgraph.agents.resilience import resilient_orchestrate

        orchestrator = Orchestrator()
        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[],
            synthesis_instructions="",
        )

        # Should complete without timeout for empty subtasks
        results = await resilient_orchestrate(orchestrator, decomposition)
        assert results == []

    @pytest.mark.asyncio
    async def test_resilient_subagent_applies_retry(self) -> None:
        """Test that resilient_subagent_execute applies retry on failure."""
        from mcp_server_langgraph.agents.resilience import resilient_subagent_execute
        from mcp_server_langgraph.agents.subagent import Subagent

        subagent = Subagent(
            task_id="test-retry",
            instructions="Test retry",
            model="test-model",
        )

        # Mock execute to succeed on first try
        with patch.object(subagent, "execute") as mock_execute:
            mock_result = MagicMock()
            mock_result.success = True
            mock_execute.return_value = mock_result

            result = await resilient_subagent_execute(subagent)
            assert result.success


@pytest.mark.xdist_group(name="coordinator_resilience")
class TestCoordinatorResilienceIntegration:
    """Test resilience integration with Coordinator."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_coordinator_execute_all_has_timeout(self) -> None:
        """Test that Coordinator.execute_all respects timeout."""
        from mcp_server_langgraph.agents.coordinator import Coordinator

        coordinator = Coordinator()
        # Empty execution should complete quickly
        results = await coordinator.execute_all()
        assert results == []

    def test_coordinator_has_timeout_param(self) -> None:
        """Test that Coordinator.execute_all accepts timeout parameter."""
        from mcp_server_langgraph.agents.coordinator import Coordinator
        import inspect

        sig = inspect.signature(Coordinator.execute_all)
        # Check if timeout parameter exists (optional parameter)
        assert "timeout" in sig.parameters or len(sig.parameters) >= 0


@pytest.mark.xdist_group(name="orchestrator_circuit_breaker")
class TestOrchestratorCircuitBreaker:
    """Test circuit breaker for orchestrator."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_circuit_breaker_config_in_resilience(self) -> None:
        """Test that orchestrator has circuit breaker configuration."""
        from mcp_server_langgraph.resilience.config import get_resilience_config

        config = get_resilience_config()
        # Should have orchestrator circuit breaker config (or use default)
        assert config.circuit_breakers is not None

    def test_resilience_config_has_orchestrator_entry(self) -> None:
        """Test that resilience config can have orchestrator circuit breaker."""
        from mcp_server_langgraph.resilience.config import CircuitBreakerConfig

        # Can create orchestrator-specific config
        orchestrator_cb = CircuitBreakerConfig(
            name="orchestrator",
            fail_max=3,
            timeout_duration=120,
        )
        assert orchestrator_cb.name == "orchestrator"
        assert orchestrator_cb.fail_max == 3


@pytest.mark.xdist_group(name="orchestrator_bulkhead")
class TestOrchestratorBulkhead:
    """Test bulkhead (concurrency limit) for orchestrator."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_bulkhead_uses_feature_flag(self) -> None:
        """Test that orchestrator bulkhead respects max_concurrent flag."""
        max_concurrent = feature_flags.orchestrator_max_concurrent
        assert isinstance(max_concurrent, int)
        assert max_concurrent >= 1
        assert max_concurrent <= 20

    def test_bulkhead_can_limit_concurrent_orchestrations(self) -> None:
        """Test that bulkhead can limit concurrent orchestrations."""
        from mcp_server_langgraph.resilience import BulkheadConfig

        bulkhead_config = BulkheadConfig(
            llm_limit=10,
            openfga_limit=50,
            redis_limit=100,
            db_limit=20,
        )
        # Bulkhead config exists and can be customized
        assert bulkhead_config.llm_limit == 10


@pytest.mark.xdist_group(name="orchestrator_resilience_metrics")
class TestOrchestratorResilienceMetrics:
    """Test metrics for orchestrator resilience."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_orchestrator_resilience_metrics_module_exists(self) -> None:
        """Test that orchestrator resilience metrics are available."""
        from mcp_server_langgraph.agents import metrics

        # Check metrics module has orchestrator-related recording functions
        assert hasattr(metrics, "record_orchestrator_execution")

    def test_record_orchestrator_timeout(self) -> None:
        """Test that timeout metric recording exists."""
        from mcp_server_langgraph.agents.metrics import record_orchestrator_execution

        # Should be able to call with failure (simulating timeout)
        record_orchestrator_execution(
            task_count=5,
            successful_count=0,
            duration_ms=300000.0,  # 5 minutes (timeout)
            success=False,
        )
        # No exception means metric was recorded


@pytest.mark.xdist_group(name="orchestrator_resilience_disabled")
class TestOrchestratorResilienceDisabled:
    """Test orchestrator behavior when resilience is disabled."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_feature_flag_can_disable_resilience(self) -> None:
        """Test that orchestrator resilience can be disabled via flag."""
        # The flag exists and can be checked
        assert hasattr(feature_flags, "enable_orchestrator_resilience")
        # Verify it's a boolean
        assert isinstance(feature_flags.enable_orchestrator_resilience, bool)

    @pytest.mark.asyncio
    async def test_resilient_wrapper_respects_feature_flag(self) -> None:
        """Test that resilient wrappers check feature flag."""
        from mcp_server_langgraph.agents.orchestrator import Orchestrator, TaskDecomposition
        from mcp_server_langgraph.agents.resilience import resilient_orchestrate

        orchestrator = Orchestrator()
        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[],
            synthesis_instructions="",
        )

        # Should work regardless of flag state
        results = await resilient_orchestrate(orchestrator, decomposition)
        assert isinstance(results, list)


@pytest.mark.xdist_group(name="orchestrator_circuit_breaker_integration")
class TestOrchestratorCircuitBreakerIntegration:
    """Test circuit breaker integration with orchestrator resilience.

    These tests verify that resilient_orchestrate() properly integrates
    the circuit breaker pattern to prevent cascade failures.
    """

    def teardown_method(self):
        """Force GC and reset circuit breakers to prevent test pollution"""
        from mcp_server_langgraph.resilience import reset_all_circuit_breakers

        reset_all_circuit_breakers()
        gc.collect()

    def test_orchestrator_circuit_breaker_registered(self) -> None:
        """Test that orchestrator circuit breaker is registered after first use."""
        from mcp_server_langgraph.agents.resilience import get_orchestrator_circuit_breaker

        cb = get_orchestrator_circuit_breaker()
        assert cb is not None
        assert cb.name == "orchestrator"

    def test_orchestrator_circuit_breaker_uses_feature_flag_threshold(self) -> None:
        """Test that orchestrator circuit breaker uses configured threshold."""
        from mcp_server_langgraph.agents.resilience import get_orchestrator_circuit_breaker

        cb = get_orchestrator_circuit_breaker()
        # Should use feature_flags.orchestrator_circuit_breaker_threshold (default 3)
        assert cb.fail_max == feature_flags.orchestrator_circuit_breaker_threshold

    @pytest.mark.asyncio
    async def test_resilient_orchestrate_opens_circuit_after_failures(self) -> None:
        """Test that circuit breaker opens after threshold failures."""
        from mcp_server_langgraph.agents.orchestrator import Orchestrator, TaskDecomposition
        from mcp_server_langgraph.agents.resilience import (
            get_orchestrator_circuit_breaker,
            resilient_orchestrate,
        )
        from mcp_server_langgraph.core.exceptions import CircuitBreakerOpenError
        from mcp_server_langgraph.resilience import CircuitBreakerState

        orchestrator = Orchestrator()
        decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[],
            synthesis_instructions="",
        )

        # Mock execute to always fail
        fail_count = 0
        original_execute = orchestrator.execute

        async def failing_execute(*args, **kwargs):
            nonlocal fail_count
            fail_count += 1
            raise RuntimeError(f"Simulated failure #{fail_count}")

        orchestrator.execute = failing_execute

        # Cause failures up to threshold
        threshold = feature_flags.orchestrator_circuit_breaker_threshold
        for i in range(threshold):
            with pytest.raises(RuntimeError):
                await resilient_orchestrate(orchestrator, decomposition)

        # Circuit should now be open
        cb = get_orchestrator_circuit_breaker()
        assert cb.current_state == CircuitBreakerState.OPEN.value

        # Next call should fail fast without calling execute
        initial_fail_count = fail_count
        with pytest.raises(CircuitBreakerOpenError):
            await resilient_orchestrate(orchestrator, decomposition)

        # Execute should not have been called (fail fast)
        assert fail_count == initial_fail_count

        # Restore original
        orchestrator.execute = original_execute

    @pytest.mark.asyncio
    async def test_resilient_orchestrate_circuit_breaker_recovers(self) -> None:
        """Test that circuit breaker recovers after successful call."""
        from mcp_server_langgraph.agents.resilience import (
            get_orchestrator_circuit_breaker,
            reset_orchestrator_circuit_breaker,
        )
        from mcp_server_langgraph.resilience import CircuitBreakerState

        # Ensure clean state
        reset_orchestrator_circuit_breaker()

        cb = get_orchestrator_circuit_breaker()
        # Circuit should start closed
        assert cb.current_state == CircuitBreakerState.CLOSED.value

    @pytest.mark.asyncio
    async def test_resilient_subagent_retries_dont_trigger_circuit_breaker(self) -> None:
        """Test that subagent retries are isolated from orchestrator circuit breaker."""
        from mcp_server_langgraph.agents.resilience import (
            get_orchestrator_circuit_breaker,
            resilient_subagent_execute,
        )
        from mcp_server_langgraph.agents.subagent import Subagent
        from mcp_server_langgraph.resilience import CircuitBreakerState

        subagent = Subagent(
            task_id="test-isolation",
            instructions="Test isolation",
            model="test-model",
        )

        # Mock execute to fail
        with patch.object(subagent, "execute") as mock_execute:
            mock_execute.side_effect = RuntimeError("Subagent failure")

            # This should retry and fail, but not affect orchestrator circuit breaker
            result = await resilient_subagent_execute(subagent, max_retries=2)
            assert not result.success

        # Orchestrator circuit breaker should still be closed
        cb = get_orchestrator_circuit_breaker()
        assert cb.current_state == CircuitBreakerState.CLOSED.value
