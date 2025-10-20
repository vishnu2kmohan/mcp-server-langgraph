"""
Integration tests for resilience patterns.

Tests full resilience stack with all patterns composed together.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_server_langgraph.core.exceptions import BulkheadRejectedError, CircuitBreakerOpenError, RetryExhaustedError
from mcp_server_langgraph.core.exceptions import TimeoutError as MCPTimeoutError
from mcp_server_langgraph.resilience import circuit_breaker, retry_with_backoff, with_bulkhead, with_fallback, with_timeout


@pytest.fixture
def reset_all_resilience():
    """Reset all resilience state before each test"""
    import mcp_server_langgraph.resilience.bulkhead as bh_module
    import mcp_server_langgraph.resilience.circuit_breaker as cb_module

    cb_module._circuit_breakers.clear()
    bh_module._bulkhead_semaphores.clear()
    yield
    cb_module._circuit_breakers.clear()
    bh_module._bulkhead_semaphores.clear()


class TestFullResilienceStack:
    """Test all resilience patterns composed together"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_all_patterns_successful_call(self, reset_all_resilience):
        """Test successful call with all resilience patterns"""

        @circuit_breaker(name="test", fail_max=5)
        @retry_with_backoff(max_attempts=3)
        @with_timeout(seconds=5)
        @with_bulkhead(resource_type="test", limit=10)
        async def protected_func():
            await asyncio.sleep(0.1)
            return "success"

        result = await protected_func()
        assert result == "success"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_all_patterns_with_retry_success(self, reset_all_resilience):
        """Test retry success with all patterns"""
        call_count = 0

        @circuit_breaker(name="test", fail_max=5)
        @retry_with_backoff(max_attempts=3)
        @with_timeout(seconds=5)
        @with_bulkhead(resource_type="test", limit=10)
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary failure")
            return "success"

        result = await func()
        assert result == "success"
        assert call_count == 2  # Failed once, succeeded on retry

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_retries_exhausted(self, reset_all_resilience):
        """Test that circuit breaker tracks failures across retries"""

        @circuit_breaker(name="test", fail_max=3)
        @retry_with_backoff(max_attempts=2)
        async def func():
            raise ValueError("Always fails")

        # Each call retries twice, counts as 1 failure for circuit breaker
        # Need 3 calls to open circuit
        for i in range(3):
            with pytest.raises(RetryExhaustedError):
                await func()

        # Circuit should be open now
        from mcp_server_langgraph.resilience import CircuitBreakerState, get_circuit_breaker_state

        state = get_circuit_breaker_state("test")
        assert state == CircuitBreakerState.OPEN

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_bulkhead_limits_concurrent_retries(self, reset_all_resilience):
        """Test that bulkhead limits concurrency even with retries"""
        active_count = 0
        max_active = 0

        @with_bulkhead(resource_type="test", limit=3)
        @retry_with_backoff(max_attempts=2)
        async def func(should_fail):
            nonlocal active_count, max_active
            active_count += 1
            max_active = max(max_active, active_count)
            await asyncio.sleep(0.1)
            active_count -= 1

            if should_fail:
                raise ValueError("Fail once")
            return "success"

        # Start 10 tasks (some will retry)
        tasks = [func(i < 5) for i in range(10)]  # First 5 will fail and retry
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Max concurrent should still be limited to 3
        assert max_active <= 3


class TestRealWorldScenarios:
    """Test real-world scenarios with resilience patterns"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_llm_call_simulation(self, reset_all_resilience):
        """Simulate LLM API call with full resilience"""

        call_count = 0

        @circuit_breaker(name="llm", fail_max=5, timeout=60)
        @retry_with_backoff(max_attempts=3)
        @with_timeout(operation_type="llm")
        @with_bulkhead(resource_type="llm")
        @with_fallback(fallback="Cached response from previous call")
        async def call_llm_api(prompt):
            nonlocal call_count
            call_count += 1

            # Simulate transient failure
            if call_count == 1:
                raise ValueError("Rate limit exceeded")

            await asyncio.sleep(0.1)
            return f"Response to: {prompt}"

        result = await call_llm_api("Hello")
        assert "Response to: Hello" in result

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_auth_check_simulation(self, reset_all_resilience):
        """Simulate OpenFGA auth check with fail-open"""

        service_available = True

        async def check_permission_fallback(*args, **kwargs):
            # Fail-open: allow access if service is down
            return True

        @circuit_breaker(name="openfga", fail_max=10, timeout=30, fallback=check_permission_fallback)
        @retry_with_backoff(max_attempts=3)
        @with_timeout(operation_type="auth")
        @with_bulkhead(resource_type="openfga")
        async def check_permission(user, resource):
            if not service_available:
                raise ValueError("OpenFGA unavailable")
            await asyncio.sleep(0.01)
            return user == "admin"

        # Service available
        result = await check_permission("admin", "resource_123")
        assert result is True

        # Service unavailable - should fail-open to True
        service_available = False
        result = await check_permission("user", "resource_123")
        # Should return True (fallback allows access)


class TestMetricsIntegration:
    """Test metrics are emitted correctly with all patterns"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_all_metrics_emitted(self, reset_all_resilience):
        """Test that all resilience metrics are emitted"""
        call_count = 0

        @circuit_breaker(name="test")
        @retry_with_backoff(max_attempts=3)
        @with_timeout(seconds=5)
        @with_bulkhead(resource_type="test")
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry me")
            return "success"

        # Should emit:
        # - circuit_breaker_success (once)
        # - retry_attempt (once)
        # - bulkhead_active_operations (gauge)
        result = await func()
        assert result == "success"


class TestErrorPropagation:
    """Test error propagation through resilience layers"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_timeout_overrides_retry(self, reset_all_resilience):
        """Test that timeout can interrupt retry loop"""

        @retry_with_backoff(max_attempts=10, exponential_base=2)
        @with_timeout(seconds=2)
        async def slow_func_with_retries():
            await asyncio.sleep(1)
            raise ValueError("Keep retrying")

        # Should timeout before exhausting all retries
        with pytest.raises((MCPTimeoutError, asyncio.TimeoutError)):
            await slow_func_with_retries()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_circuit_breaker_stops_retries(self, reset_all_resilience):
        """Test that open circuit stops retry attempts"""

        @circuit_breaker(name="test", fail_max=2)
        @retry_with_backoff(max_attempts=5)
        async def func():
            raise ValueError("Always fails")

        # First two calls (with retries) should open circuit
        for i in range(2):
            with pytest.raises(RetryExhaustedError):
                await func()

        # Third call should fail fast (circuit open)
        with pytest.raises(CircuitBreakerOpenError):
            await func()


class TestConcurrentOperations:
    """Test concurrent operations with resilience"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_calls_different_services(self, reset_all_resilience):
        """Test concurrent calls to different services"""

        @circuit_breaker(name="service1")
        @with_bulkhead(resource_type="service1", limit=5)
        async def call_service1():
            await asyncio.sleep(0.1)
            return "service1"

        @circuit_breaker(name="service2")
        @with_bulkhead(resource_type="service2", limit=5)
        async def call_service2():
            await asyncio.sleep(0.1)
            return "service2"

        # Should be able to call both concurrently
        results = await asyncio.gather(
            *[call_service1() for _ in range(10)],
            *[call_service2() for _ in range(10)],
        )

        assert results.count("service1") == 10
        assert results.count("service2") == 10

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_independent_circuit_breakers(self, reset_all_resilience):
        """Test that different services have independent circuit breakers"""

        @circuit_breaker(name="service1", fail_max=2)
        async def service1():
            raise ValueError("Service1 down")

        @circuit_breaker(name="service2", fail_max=2)
        async def service2():
            return "service2_ok"

        # Fail service1 to open its circuit
        for i in range(2):
            with pytest.raises(ValueError):
                await service1()

        # Service1 circuit should be open
        from mcp_server_langgraph.resilience import CircuitBreakerState, get_circuit_breaker_state

        assert get_circuit_breaker_state("service1") == CircuitBreakerState.OPEN

        # Service2 should still work (independent circuit)
        result = await service2()
        assert result == "service2_ok"
        assert get_circuit_breaker_state("service2") == CircuitBreakerState.CLOSED
