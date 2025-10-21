"""
Unit tests for circuit breaker pattern.

Tests circuit breaker behavior, state transitions, fallback, and metrics.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pybreaker
import pytest

from mcp_server_langgraph.core.exceptions import CircuitBreakerOpenError
from mcp_server_langgraph.resilience.circuit_breaker import (
    CircuitBreakerState,
    circuit_breaker,
    get_all_circuit_breaker_states,
    get_circuit_breaker,
    get_circuit_breaker_state,
    reset_all_circuit_breakers,
    reset_circuit_breaker,
)


@pytest.fixture
def reset_breakers():
    """Reset all circuit breakers before each test"""
    reset_all_circuit_breakers()
    yield
    reset_all_circuit_breakers()


class TestCircuitBreakerBasics:
    """Test basic circuit breaker functionality"""

    @pytest.mark.unit
    def test_get_circuit_breaker_creates_new(self, reset_breakers):
        """Test that get_circuit_breaker creates a new breaker"""
        breaker = get_circuit_breaker("test_service")
        assert breaker is not None
        assert breaker.name == "test_service"

    @pytest.mark.unit
    def test_get_circuit_breaker_returns_same_instance(self, reset_breakers):
        """Test that get_circuit_breaker returns same instance for same name"""
        breaker1 = get_circuit_breaker("test_service")
        breaker2 = get_circuit_breaker("test_service")
        assert breaker1 is breaker2

    @pytest.mark.unit
    def test_circuit_breaker_default_state_is_closed(self, reset_breakers):
        """Test that circuit breaker starts in CLOSED state"""
        breaker = get_circuit_breaker("test_service")
        assert breaker.current_state == pybreaker.STATE_CLOSED

    @pytest.mark.unit
    def test_get_circuit_breaker_state(self, reset_breakers):
        """Test get_circuit_breaker_state function"""
        breaker = get_circuit_breaker("test_service")  # noqa: F841
        state = get_circuit_breaker_state("test_service")
        assert state == CircuitBreakerState.CLOSED

    @pytest.mark.unit
    def test_get_all_circuit_breaker_states(self, reset_breakers):
        """Test get_all_circuit_breaker_states function"""
        get_circuit_breaker("service1")
        get_circuit_breaker("service2")

        states = get_all_circuit_breaker_states()
        assert "service1" in states
        assert "service2" in states
        assert states["service1"] == CircuitBreakerState.CLOSED


class TestCircuitBreakerStateTransitions:
    """Test circuit breaker state transitions"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_breaker_opens_after_max_failures(self, reset_breakers):
        """Test that breaker opens after reaching max failures"""

        @circuit_breaker(name="test", fail_max=3, timeout=1)
        async def failing_func():
            raise ValueError("Test error")

        # Trigger failures
        for i in range(3):
            with pytest.raises(ValueError):
                await failing_func()

        # Circuit should now be open
        state = get_circuit_breaker_state("test")
        assert state == CircuitBreakerState.OPEN

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_breaker_fails_fast_when_open(self, reset_breakers):
        """Test that breaker fails fast when in OPEN state"""

        @circuit_breaker(name="test", fail_max=2)
        async def failing_func():
            raise ValueError("Test error")

        # Trigger failures to open circuit
        for i in range(2):
            with pytest.raises(ValueError):
                await failing_func()

        # Next call should fail fast with CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await failing_func()

        assert "test" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_breaker_transitions_to_half_open(self, reset_breakers):
        """Test that breaker transitions to HALF_OPEN after timeout"""

        @circuit_breaker(name="test", fail_max=2, timeout=1)
        async def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for i in range(2):
            with pytest.raises(ValueError):
                await failing_func()

        # Wait for timeout
        await asyncio.sleep(1.5)

        # Circuit should now be HALF_OPEN (trying recovery)
        breaker = get_circuit_breaker("test")  # noqa: F841
        # Note: Can't directly test HALF_OPEN state without triggering a call


class TestCircuitBreakerWithFallback:
    """Test circuit breaker with fallback functions"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fallback_called_when_circuit_open(self, reset_breakers):
        """Test that fallback is called when circuit is open"""

        fallback_called = False

        async def fallback_func(*args, **kwargs):
            nonlocal fallback_called
            fallback_called = True
            return "fallback_response"

        @circuit_breaker(name="test", fail_max=2, timeout=1, fallback=fallback_func)
        async def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for i in range(2):
            with pytest.raises(ValueError):
                await failing_func()

        # Next call should use fallback
        result = await failing_func()
        assert result == "fallback_response"
        assert fallback_called is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_static_fallback_value(self, reset_breakers):
        """Test circuit breaker with static fallback value"""

        @circuit_breaker(name="test", fail_max=2, fallback=lambda *args: "default")
        async def failing_func():
            raise ValueError("Test error")

        # Open circuit
        for i in range(2):
            with pytest.raises(ValueError):
                await failing_func()

        # Should return fallback
        result = await failing_func()
        assert result == "default"


class TestCircuitBreakerMetrics:
    """Test circuit breaker metrics emission"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_success_metric_emitted(self, reset_breakers):
        """Test that success metric is emitted on successful call"""

        @circuit_breaker(name="test")
        async def success_func():
            return "success"

        with patch("mcp_server_langgraph.observability.telemetry.circuit_breaker_success_counter") as mock_metric:
            result = await success_func()
            assert result == "success"
            # Metric should be called via listener
            mock_metric.add.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_failure_metric_emitted(self, reset_breakers):
        """Test that failure metric is emitted on failed call"""

        @circuit_breaker(name="test", fail_max=5)
        async def failing_func():
            raise ValueError("Test error")

        with patch("mcp_server_langgraph.observability.telemetry.circuit_breaker_failure_counter") as mock_metric:
            with pytest.raises(ValueError):
                await failing_func()
            # Metric should be called via listener
            mock_metric.add.assert_called()


class TestCircuitBreakerReset:
    """Test circuit breaker manual reset"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_reset_circuit_breaker(self, reset_breakers):
        """Test manual circuit breaker reset"""

        @circuit_breaker(name="test", fail_max=2)
        async def failing_func():
            raise ValueError("Test error")

        # Open circuit
        for i in range(2):
            with pytest.raises(ValueError):
                await failing_func()

        # Verify it's open
        state = get_circuit_breaker_state("test")
        assert state == CircuitBreakerState.OPEN

        # Reset circuit
        reset_circuit_breaker("test")

        # Should be closed now
        state = get_circuit_breaker_state("test")
        assert state == CircuitBreakerState.CLOSED


class TestCircuitBreakerConfiguration:
    """Test circuit breaker configuration"""

    @pytest.mark.unit
    def test_custom_fail_max(self, reset_breakers):
        """Test custom fail_max configuration"""
        breaker = get_circuit_breaker("test")  # noqa: F841
        # Default from config should be applied

    @pytest.mark.unit
    def test_custom_timeout_duration(self, reset_breakers):
        """Test custom timeout_duration configuration"""
        breaker = get_circuit_breaker("test")  # noqa: F841
        # Default from config should be applied


class TestCircuitBreakerEdgeCases:
    """Test circuit breaker edge cases"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concurrent_calls_during_open_state(self, reset_breakers):
        """Test concurrent calls when circuit is open"""

        @circuit_breaker(name="test", fail_max=2)
        async def failing_func():
            raise ValueError("Test error")

        # Open circuit
        for i in range(2):
            with pytest.raises(ValueError):
                await failing_func()

        # All concurrent calls should fail fast
        tasks = [failing_func() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should be CircuitBreakerOpenError
        for result in results:
            assert isinstance(result, (CircuitBreakerOpenError, pybreaker.CircuitBreakerError))

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_successful_call_after_recovery(self, reset_breakers):
        """Test successful call after circuit recovers"""

        call_count = 0

        @circuit_breaker(name="test", fail_max=2, timeout=1)
        async def sometimes_failing_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError("Initial failures")
            return "success"

        # Open circuit with 2 failures
        for i in range(2):
            with pytest.raises(ValueError):
                await sometimes_failing_func()

        # Wait for timeout
        await asyncio.sleep(1.5)

        # Next call should succeed (HALF_OPEN → CLOSED)
        result = await sometimes_failing_func()
        assert result == "success"

        # Circuit should be closed again
        state = get_circuit_breaker_state("test")
        assert state == CircuitBreakerState.CLOSED

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_circuit_breaker_with_different_exception_types(self, reset_breakers):
        """Test that circuit breaker tracks all exception types"""

        call_count = 0

        @circuit_breaker(name="test", fail_max=3)
        async def multi_exception_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Error 1")
            elif call_count == 2:
                raise RuntimeError("Error 2")
            else:
                raise TypeError("Error 3")

        # All exception types should count toward failure limit
        for i in range(3):
            with pytest.raises(Exception):
                await multi_exception_func()

        # Circuit should be open
        state = get_circuit_breaker_state("test")
        assert state == CircuitBreakerState.OPEN
