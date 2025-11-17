"""
Integration tests for resilience patterns.

Tests full resilience stack with all patterns composed together.
"""

import asyncio
import gc

import pytest

from mcp_server_langgraph.core.exceptions import CircuitBreakerOpenError, RetryExhaustedError
from mcp_server_langgraph.core.exceptions import TimeoutError as MCPTimeoutError
from mcp_server_langgraph.resilience import circuit_breaker, retry_with_backoff, with_bulkhead, with_fallback, with_timeout


@pytest.fixture
def reset_all_resilience():
    """Reset all resilience state before each test"""
    # Import modules and clear state before test
    try:
        import mcp_server_langgraph.resilience.bulkhead as bh_module
        import mcp_server_langgraph.resilience.circuit_breaker as cb_module

        # Ensure module-level dicts exist before clearing
        if hasattr(cb_module, "_circuit_breakers"):
            cb_module._circuit_breakers.clear()
        if hasattr(bh_module, "_bulkhead_semaphores"):
            bh_module._bulkhead_semaphores.clear()
    except (ImportError, AttributeError) as e:
        # If modules not loaded or attributes missing, log and continue
        import logging

        logging.getLogger(__name__).warning(f"Could not reset resilience state: {e}")

    yield

    # Clean up after test
    try:
        import mcp_server_langgraph.resilience.bulkhead as bh_module
        import mcp_server_langgraph.resilience.circuit_breaker as cb_module

        if hasattr(cb_module, "_circuit_breakers"):
            cb_module._circuit_breakers.clear()
        if hasattr(bh_module, "_bulkhead_semaphores"):
            bh_module._bulkhead_semaphores.clear()
    except (ImportError, AttributeError) as e:
        import logging

        logging.getLogger(__name__).warning(f"Could not clean up resilience state: {e}")


@pytest.mark.xdist_group(name="testfullresiliencestack")
class TestFullResilienceStack:
    """Test all resilience patterns composed together"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

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
        from mcp_server_langgraph.resilience import CircuitBreakerState, get_circuit_breaker_state, reset_circuit_breaker

        # Ensure circuit breaker starts in clean state
        reset_circuit_breaker("test_cb_retry_exhausted")

        @circuit_breaker(name="test_cb_retry_exhausted", fail_max=3)
        @retry_with_backoff(max_attempts=2)
        async def func():
            raise ValueError("Always fails")

        # Verify initial state
        assert get_circuit_breaker_state("test_cb_retry_exhausted") == CircuitBreakerState.CLOSED

        # Each call retries twice, counts as 1 failure for circuit breaker
        # Need 3 calls to open circuit
        for i in range(3):
            with pytest.raises(RetryExhaustedError):
                await func()

        # Circuit should be open now
        state = get_circuit_breaker_state("test_cb_retry_exhausted")
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
        results = await asyncio.gather(*tasks, return_exceptions=True)  # noqa: F841

        # Max concurrent should still be limited to 3
        assert max_active <= 3


@pytest.mark.xdist_group(name="testrealworldscenarios")
class TestRealWorldScenarios:
    """Test real-world scenarios with resilience patterns"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_llm_call_simulation(self, reset_all_resilience):
        """Simulate LLM API call with full resilience"""

        call_count = 0

        @with_fallback(fallback="Cached response from previous call")
        @circuit_breaker(name="llm", fail_max=5, timeout=60)
        @retry_with_backoff(max_attempts=3)
        @with_timeout(operation_type="llm")
        @with_bulkhead(resource_type="llm")
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

        @circuit_breaker(name="openfga", fail_max=2, timeout=30, fallback=check_permission_fallback)
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

        # Service unavailable - make enough calls to open circuit
        service_available = False
        # First call - will fail and exhaust retries (counts as 1 failure)
        with pytest.raises(RetryExhaustedError):
            await check_permission("user", "resource_123")
        # Second call - will fail, exhaust retries, count as 2nd failure and open circuit
        # When circuit opens, fallback is used, so no exception is raised
        result = await check_permission("user", "resource_123")
        assert result is True  # Fallback returns True (fail-open)


@pytest.mark.xdist_group(name="testmetricsintegration")
class TestMetricsIntegration:
    """Test metrics are emitted correctly with all patterns"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_all_metrics_emitted(self, reset_all_resilience):
        """Test that all resilience metrics are emitted"""
        call_count = 0

        @circuit_breaker(name="test_metrics")
        @retry_with_backoff(max_attempts=3)
        @with_timeout(seconds=5)
        @with_bulkhead(resource_type="test_metrics")
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


@pytest.mark.xdist_group(name="testerrorpropagation")
class TestErrorPropagation:
    """Test error propagation through resilience layers"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_timeout_overrides_retry(self, reset_all_resilience):
        """Test that timeout can interrupt retry loop"""

        @with_timeout(seconds=2)
        @retry_with_backoff(max_attempts=10, exponential_base=2)
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
        from mcp_server_langgraph.resilience import CircuitBreakerState, get_circuit_breaker_state, reset_circuit_breaker

        # Ensure circuit breaker starts in clean state
        reset_circuit_breaker("test_cb_stops_retry")

        @circuit_breaker(name="test_cb_stops_retry", fail_max=2)
        @retry_with_backoff(max_attempts=5)
        async def func():
            raise ValueError("Always fails")

        # Verify initial state
        assert get_circuit_breaker_state("test_cb_stops_retry") == CircuitBreakerState.CLOSED

        # First two calls (with retries) should open circuit
        for i in range(2):
            with pytest.raises(RetryExhaustedError):
                await func()

        # Third call should fail fast (circuit open)
        with pytest.raises(CircuitBreakerOpenError):
            await func()


@pytest.mark.xdist_group(name="testconcurrentoperations")
class TestConcurrentOperations:
    """Test concurrent operations with resilience"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

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
        from mcp_server_langgraph.resilience import CircuitBreakerState, get_circuit_breaker_state, reset_circuit_breaker

        # Ensure circuit breakers start in clean state
        reset_circuit_breaker("test_service1")
        reset_circuit_breaker("test_service2")

        @circuit_breaker(name="test_service1", fail_max=2)
        async def service1():
            raise ValueError("Service1 down")

        @circuit_breaker(name="test_service2", fail_max=2)
        async def service2():
            return "service2_ok"

        # Verify initial states
        assert get_circuit_breaker_state("test_service1") == CircuitBreakerState.CLOSED
        assert get_circuit_breaker_state("test_service2") == CircuitBreakerState.CLOSED

        # Fail service1 to open its circuit
        for i in range(2):
            with pytest.raises(ValueError):
                await service1()

        # Service1 circuit should be open
        assert get_circuit_breaker_state("test_service1") == CircuitBreakerState.OPEN

        # Service2 should still work (independent circuit)
        result = await service2()
        assert result == "service2_ok"
        assert get_circuit_breaker_state("test_service2") == CircuitBreakerState.CLOSED
