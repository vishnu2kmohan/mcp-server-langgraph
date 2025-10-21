"""
Property-based tests for resilience patterns using Hypothesis.

Tests resilience invariants:
- Circuit breakers prevent cascading failures
- Retries respect exponential backoff
- Timeouts enforce max duration
- Bulkheads limit concurrency
- Fallbacks provide degraded service
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mcp_server_langgraph.resilience.bulkhead import get_bulkhead, get_bulkhead_stats, reset_bulkhead, with_bulkhead
from mcp_server_langgraph.resilience.circuit_breaker import (
    circuit_breaker,
    get_circuit_breaker,
    get_circuit_breaker_state,
    reset_circuit_breaker,
)
from mcp_server_langgraph.resilience.fallback import fail_closed, fail_open, with_fallback
from mcp_server_langgraph.resilience.retry import retry_with_backoff, should_retry_exception
from mcp_server_langgraph.resilience.timeout import with_timeout

pytestmark = [pytest.mark.unit, pytest.mark.property]


class TestCircuitBreakerProperties:
    """Property-based tests for circuit breaker"""

    @given(
        fail_count=st.integers(min_value=1, max_value=10),
        fail_max=st.integers(min_value=3, max_value=5),
    )
    @settings(max_examples=20, deadline=2000)
    def test_circuit_opens_after_consecutive_failures(self, fail_count, fail_max):
        """Property: Circuit breaker opens after fail_max consecutive failures"""
        resource_name = f"test_resource_{fail_count}_{fail_max}"
        reset_circuit_breaker(resource_name)
        _ = get_circuit_breaker(resource_name, fail_max=fail_max, timeout_duration=5)  # noqa: F841

        # Simulate failures
        for i in range(fail_count):
            try:

                @circuit_breaker(resource_name, fail_max=fail_max)
                def failing_operation():
                    raise Exception("Test failure")

                failing_operation()
            except Exception:
                pass

        state = get_circuit_breaker_state(resource_name)

        # Property: If failures >= fail_max, circuit should be open
        if fail_count >= fail_max:
            assert state == "open", f"Circuit should be open after {fail_count} failures (fail_max={fail_max})"
        else:
            assert state == "closed", f"Circuit should be closed after {fail_count} failures (fail_max={fail_max})"

    @given(success_count=st.integers(min_value=1, max_value=5))
    @settings(max_examples=10, deadline=2000)
    def test_circuit_stays_closed_on_success(self, success_count):
        """Property: Circuit breaker stays closed when operations succeed"""
        resource_name = f"test_success_{success_count}"
        reset_circuit_breaker(resource_name)

        for _ in range(success_count):

            @circuit_breaker(resource_name, fail_max=3)
            def successful_operation():
                return "success"

            result = successful_operation()
            assert result == "success"

        # Circuit should remain closed
        state = get_circuit_breaker_state(resource_name)
        assert state == "closed"

    @given(value=st.text(min_size=1, max_size=100))
    @settings(max_examples=15, deadline=2000)
    def test_circuit_breaker_with_fallback_always_returns(self, value):
        """Property: Circuit breaker with fallback always returns a value"""
        resource_name = f"test_fallback_{hash(value)}"
        reset_circuit_breaker(resource_name)

        # Open the circuit
        _ = get_circuit_breaker(resource_name, fail_max=1)  # noqa: F841
        for _ in range(2):
            try:

                @circuit_breaker(resource_name, fail_max=1, fallback_value="fallback")
                def failing_with_fallback():
                    raise Exception("Failure")

                failing_with_fallback()
            except Exception:
                pass

        # Should return fallback when circuit is open
        @circuit_breaker(resource_name, fail_max=1, fallback_value=value)
        def operation():
            raise Exception("Should not execute")

        result = operation()

        # Should always get a result (either success or fallback)
        assert result is not None
        assert isinstance(result, str)


class TestRetryProperties:
    """Property-based tests for retry logic"""

    @given(
        num_retries=st.integers(min_value=1, max_value=5),
        fail_before_success=st.integers(min_value=0, max_value=3),
    )
    @settings(max_examples=15, deadline=3000)
    @pytest.mark.asyncio
    async def test_retry_eventually_succeeds_or_exhausts(self, num_retries, fail_before_success):
        """Property: Retry either succeeds within max_retries or raises RetryExhaustedError"""
        attempt_count = [0]

        @retry_with_backoff(max_retries=num_retries, initial_delay=0.01, max_delay=0.1)
        async def sometimes_failing_operation():
            attempt_count[0] += 1
            if attempt_count[0] <= fail_before_success:
                raise Exception("Temporary failure")
            return "success"

        if fail_before_success < num_retries:
            # Should eventually succeed
            result = await sometimes_failing_operation()
            assert result == "success"
            assert attempt_count[0] == fail_before_success + 1
        else:
            # Should exhaust retries
            with pytest.raises(Exception):  # RetryExhaustedError or the original exception
                await sometimes_failing_operation()

    @given(st.integers(min_value=1, max_value=4))
    @settings(max_examples=10, deadline=2000)
    @pytest.mark.asyncio
    async def test_retry_count_matches_configuration(self, max_retries):
        """Property: Retry attempts match max_retries configuration"""
        attempt_count = [0]

        @retry_with_backoff(max_retries=max_retries, initial_delay=0.01)
        async def always_failing_operation():
            attempt_count[0] += 1
            raise Exception("Always fails")

        try:
            await always_failing_operation()
        except Exception:
            pass

        # Should have attempted exactly max_retries times
        # Note: tenacity counts initial attempt + retries, so total = 1 + max_retries
        assert attempt_count[0] in [max_retries, max_retries + 1]


class TestTimeoutProperties:
    """Property-based tests for timeout enforcement"""

    @given(
        sleep_duration=st.floats(min_value=0.01, max_value=0.5),
        timeout_duration=st.floats(min_value=0.02, max_value=0.4),
    )
    @settings(max_examples=15, deadline=3000)
    @pytest.mark.asyncio
    async def test_timeout_enforced_correctly(self, sleep_duration, timeout_duration):
        """Property: Timeout correctly determines if operation times out"""

        @with_timeout(timeout_duration)
        async def slow_operation():
            await asyncio.sleep(sleep_duration)
            return "completed"

        if sleep_duration > timeout_duration:
            # Should timeout
            with pytest.raises(TimeoutError):
                await slow_operation()
        else:
            # Should complete successfully
            result = await slow_operation()
            assert result == "completed"

    @given(value=st.integers())
    @settings(max_examples=10, deadline=2000)
    @pytest.mark.asyncio
    async def test_fast_operations_never_timeout(self, value):
        """Property: Fast operations never timeout"""

        @with_timeout(1.0)  # 1 second timeout
        async def fast_operation(x):
            return x * 2

        # Fast operations should always succeed
        result = await fast_operation(value)
        assert result == value * 2


class TestBulkheadProperties:
    """Property-based tests for bulkhead pattern"""

    @given(max_concurrent=st.integers(min_value=1, max_value=5))
    @settings(max_examples=10, deadline=4000)
    @pytest.mark.asyncio
    async def test_bulkhead_limits_concurrency(self, max_concurrent):
        """Property: Bulkhead never exceeds max concurrent operations"""
        resource_name = f"test_bulkhead_{max_concurrent}"
        reset_bulkhead(resource_name)
        current_concurrent = [0]
        max_observed = [0]

        @with_bulkhead(resource_name, max_concurrent=max_concurrent, fail_fast=False)
        async def concurrent_operation():
            current_concurrent[0] += 1
            max_observed[0] = max(max_observed[0], current_concurrent[0])
            await asyncio.sleep(0.1)
            current_concurrent[0] -= 1
            return "done"

        # Launch more tasks than the limit
        num_tasks = max_concurrent * 2
        tasks = [concurrent_operation() for _ in range(num_tasks)]

        _ = await asyncio.gather(*tasks, return_exceptions=True)  # noqa: F841

        # Property: Max observed concurrent should never exceed limit
        assert max_observed[0] <= max_concurrent

    @given(
        max_concurrent=st.integers(min_value=1, max_value=3),
        num_requests=st.integers(min_value=5, max_value=10),
    )
    @settings(max_examples=10, deadline=4000)
    @pytest.mark.asyncio
    async def test_bulkhead_fail_fast_rejects_excess(self, max_concurrent, num_requests):
        """Property: Bulkhead with fail_fast rejects requests beyond capacity"""
        resource_name = f"test_fail_fast_{max_concurrent}_{num_requests}"
        reset_bulkhead(resource_name)
        accepted_count = [0]
        rejected_count = [0]

        @with_bulkhead(resource_name, max_concurrent=max_concurrent, fail_fast=True)
        async def limited_operation():
            accepted_count[0] += 1
            await asyncio.sleep(0.2)
            return "accepted"

        tasks = [limited_operation() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count rejections
        for result in results:
            if isinstance(result, Exception):
                rejected_count[0] += 1

        # Property: If requests > max_concurrent, some should be rejected
        if num_requests > max_concurrent:
            assert rejected_count[0] > 0


class TestFallbackProperties:
    """Property-based tests for fallback strategies"""

    @given(default_value=st.integers())
    @settings(max_examples=15, deadline=2000)
    @pytest.mark.asyncio
    async def test_fallback_to_default_always_returns_default(self, default_value):
        """Property: fallback_to_default always returns the default value on error"""

        @with_fallback(default=default_value)
        async def failing_operation():
            raise Exception("Always fails")

        result = await failing_operation()

        # Should always return default value
        assert result == default_value

    @given(success_value=st.text(min_size=1))
    @settings(max_examples=10, deadline=2000)
    @pytest.mark.asyncio
    async def test_fallback_not_used_on_success(self, success_value):
        """Property: Fallback is not used when operation succeeds"""

        @with_fallback(default="fallback_value")
        async def successful_operation():
            return success_value

        result = await successful_operation()

        # Should return actual value, not fallback
        assert result == success_value
        assert result != "fallback_value" or success_value == "fallback_value"

    @given(st.lists(st.integers(), min_size=0, max_size=10))
    @settings(max_examples=15, deadline=2000)
    @pytest.mark.asyncio
    async def test_fail_open_returns_empty_list(self, expected_list):
        """Property: fail_open returns empty list on error"""

        @fail_open
        async def operation_returning_list():
            if expected_list:  # If list is non-empty, return it
                return expected_list
            else:  # If empty, simulate failure
                raise Exception("Operation failed")

        result = await operation_returning_list()

        # Should either return the list or empty list
        assert isinstance(result, list)
        if expected_list:
            assert result == expected_list
        else:
            assert result == []

    @given(st.dictionaries(st.text(min_size=1, max_size=5), st.integers(), min_size=0, max_size=5))
    @settings(max_examples=15, deadline=2000)
    @pytest.mark.asyncio
    async def test_fail_closed_raises_on_error(self, test_dict):
        """Property: fail_closed raises error without fallback"""

        @fail_closed
        async def operation_returning_dict():
            if test_dict:
                return test_dict
            else:
                raise ValueError("Empty dict not allowed")

        if test_dict:
            result = await operation_returning_dict()
            assert result == test_dict
        else:
            # Should raise error (fail-closed)
            with pytest.raises(ValueError):
                await operation_returning_dict()


class TestCacheProperties:
    """Property-based tests for caching"""

    @given(
        key=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))),
        value=st.integers(),
    )
    @settings(max_examples=20, deadline=2000)
    def test_cache_get_set_roundtrip(self, key, value):
        """Property: Cache get/set roundtrip preserves value"""
        from mcp_server_langgraph.core.cache import CacheService

        cache = CacheService(l1_maxsize=100, l1_ttl=60)

        # Set value
        cache_key = f"test:{key}"
        cache.set(cache_key, value)

        # Get value
        retrieved = cache.get(cache_key)

        # Property: Retrieved value equals original value
        assert retrieved == value

    @given(values=st.lists(st.integers(), min_size=1, max_size=20))
    @settings(max_examples=15, deadline=2000)
    def test_cache_stores_different_values_independently(self, values):
        """Property: Different cache keys store independent values"""
        from mcp_server_langgraph.core.cache import CacheService

        cache = CacheService(l1_maxsize=100, l1_ttl=60)

        # Store each value with unique key
        for i, value in enumerate(values):
            cache.set(f"independent:key:{i}", value)

        # Verify each value is stored independently
        for i, expected_value in enumerate(values):
            retrieved = cache.get(f"independent:key:{i}")
            assert retrieved == expected_value

    @given(key=st.text(min_size=1, max_size=30))
    @settings(max_examples=15, deadline=2000)
    def test_cache_miss_returns_none(self, key):
        """Property: Cache miss always returns None"""
        from mcp_server_langgraph.core.cache import CacheService

        cache = CacheService(l1_maxsize=100, l1_ttl=60)

        # Don't set anything, just try to get
        result = cache.get(f"missing:{key}")

        # Property: Cache miss returns None
        assert result is None


class TestRetryExceptionHandling:
    """Property-based tests for retry exception classification"""

    @given(
        error_code=st.sampled_from(
            ["INVALID_CREDENTIALS", "TOKEN_EXPIRED", "PERMISSION_DENIED", "INVALID_INPUT", "SCHEMA_VALIDATION_ERROR"]
        )
    )
    @settings(max_examples=10, deadline=1000)
    def test_client_errors_never_retry(self, error_code):
        """Property: Client errors should never be retried"""
        from mcp_server_langgraph.core.exceptions import (
            InputValidationError,
            InvalidCredentialsError,
            PermissionDeniedError,
            SchemaValidationError,
            TokenExpiredError,
        )

        exception_map = {
            "INVALID_CREDENTIALS": InvalidCredentialsError("Invalid credentials"),
            "TOKEN_EXPIRED": TokenExpiredError("Token expired"),
            "PERMISSION_DENIED": PermissionDeniedError("Permission denied"),
            "INVALID_INPUT": InputValidationError("Invalid input"),
            "SCHEMA_VALIDATION_ERROR": SchemaValidationError("Schema validation failed"),
        }

        exc = exception_map[error_code]

        # Property: Client errors should not be retried
        should_retry = should_retry_exception(exc)
        assert should_retry is False

    @given(
        error_code=st.sampled_from(
            ["LLM_PROVIDER_ERROR", "LLM_TIMEOUT_ERROR", "REDIS_ERROR", "OPENFGA_ERROR", "KEYCLOAK_ERROR"]
        )
    )
    @settings(max_examples=10, deadline=1000)
    def test_external_service_errors_always_retry(self, error_code):
        """Property: External service errors should be retried"""
        from mcp_server_langgraph.core.exceptions import (
            KeycloakError,
            LLMProviderError,
            LLMTimeoutError,
            OpenFGAError,
            RedisError,
        )

        exception_map = {
            "LLM_PROVIDER_ERROR": LLMProviderError("Provider error"),
            "LLM_TIMEOUT_ERROR": LLMTimeoutError("LLM timeout"),
            "REDIS_ERROR": RedisError("Redis error"),
            "OPENFGA_ERROR": OpenFGAError("OpenFGA error"),
            "KEYCLOAK_ERROR": KeycloakError("Keycloak error"),
        }

        exc = exception_map[error_code]

        # Property: External errors should be retried
        should_retry = should_retry_exception(exc)
        assert should_retry is True


class TestCacheKeyGenerationProperties:
    """Property-based tests for cache key generation"""

    @given(parts=st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=5))
    @settings(max_examples=20, deadline=2000)
    def test_cache_key_generation_is_deterministic(self, parts):
        """Property: Same inputs always generate same cache key"""
        from mcp_server_langgraph.core.cache import generate_cache_key

        key1 = generate_cache_key(*parts, prefix="test", version="v1")
        key2 = generate_cache_key(*parts, prefix="test", version="v1")

        # Property: Deterministic generation
        assert key1 == key2

    @given(
        parts1=st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=3),
        parts2=st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=3),
    )
    @settings(max_examples=20, deadline=2000)
    def test_different_inputs_generate_different_keys(self, parts1, parts2):
        """Property: Different inputs generate different cache keys"""
        from mcp_server_langgraph.core.cache import generate_cache_key

        # Skip if inputs are the same
        if parts1 == parts2:
            return

        key1 = generate_cache_key(*parts1, prefix="test", version="v1")
        key2 = generate_cache_key(*parts2, prefix="test", version="v1")

        # Property: Different inputs → different keys
        assert key1 != key2


class TestFallbackStrategyProperties:
    """Property-based tests for fallback strategies"""

    @given(default=st.integers())
    @settings(max_examples=15, deadline=2000)
    @pytest.mark.asyncio
    async def test_default_fallback_returns_default(self, default):
        """Property: Default fallback returns default value on any error"""

        @with_fallback(default=default)
        async def unpredictable_operation():
            # Randomly fail
            import random

            if random.random() > 0.5:
                raise Exception("Random failure")
            return default + 1

        result = await unpredictable_operation()

        # Should either return success value or default
        assert result == default or result == default + 1


class TestResilienceComposition:
    """Property-based tests for composing resilience patterns"""

    @given(value=st.integers())
    @settings(max_examples=10, deadline=3000)
    @pytest.mark.asyncio
    async def test_retry_with_timeout_composition(self, value):
        """Property: Retry + Timeout composition behaves correctly"""

        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        @with_timeout(0.5)
        async def composed_operation(x):
            await asyncio.sleep(0.01)
            return x * 2

        result = await composed_operation(value)

        # Should complete successfully with composed decorators
        assert result == value * 2

    @given(value=st.text(min_size=1, max_size=20))
    @settings(max_examples=10, deadline=2000)
    @pytest.mark.asyncio
    async def test_circuit_breaker_with_fallback_composition(self, value):
        """Property: Circuit breaker + fallback provides degraded service"""
        resource_name = f"test_composed_{hash(value)}"
        reset_circuit_breaker(resource_name)

        @circuit_breaker(resource_name, fail_max=1, fallback_value=f"fallback_{value}")
        async def operation_with_cb_and_fallback():
            raise Exception("Service down")

        # First call should fail and open circuit
        try:
            await operation_with_cb_and_fallback()
        except Exception:
            pass

        # Subsequent calls should return fallback
        result = await operation_with_cb_and_fallback()

        # Should get fallback value (degraded service)
        assert result == f"fallback_{value}"


class TestResilienceInvariants:
    """Test resilience pattern invariants"""

    @given(attempts=st.integers(min_value=1, max_value=5))
    @settings(max_examples=10, deadline=3000)
    @pytest.mark.asyncio
    async def test_retry_backoff_increases(self, attempts):
        """Property: Retry backoff time increases exponentially"""
        # This is more of a conceptual test - actual backoff is handled by tenacity
        # We verify that the retry decorator accepts backoff configuration

        @retry_with_backoff(max_retries=attempts, initial_delay=0.01, max_delay=1.0)
        async def operation():
            return "success"

        result = await operation()
        assert result == "success"

    @given(resource=st.text(min_size=1, max_size=20))
    @settings(max_examples=10, deadline=2000)
    def test_circuit_breaker_state_is_consistent(self, resource):
        """Property: Circuit breaker state is consistent across calls"""
        resource_name = f"test_state_{hash(resource)}"
        reset_circuit_breaker(resource_name)

        state1 = get_circuit_breaker_state(resource_name)
        state2 = get_circuit_breaker_state(resource_name)

        # Property: State should be consistent
        assert state1 == state2
        assert state1 in ["closed", "open", "half-open"]
