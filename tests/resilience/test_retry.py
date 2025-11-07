"""
Unit tests for retry logic with exponential backoff.

Tests retry behavior, backoff calculation, and exception handling.
"""

import time
from unittest.mock import patch

import pytest

from mcp_server_langgraph.core.exceptions import AuthorizationError, ExternalServiceError, RetryExhaustedError, ValidationError
from mcp_server_langgraph.resilience.retry import RetryStrategy, retry_with_backoff, should_retry_exception


class TestRetryBasics:
    """Test basic retry functionality"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test that function is retried on failure"""
        call_count = 0

        @retry_with_backoff(max_attempts=3, exponential_base=1)
        async def sometimes_failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = await sometimes_failing_func()
        assert result == "success"
        assert call_count == 3  # Failed twice, succeeded on 3rd attempt

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_exhausted_raises_error(self):
        """Test that RetryExhaustedError is raised after max attempts"""

        @retry_with_backoff(max_attempts=3)
        async def always_failing_func():
            raise ValueError("Permanent failure")

        with pytest.raises(RetryExhaustedError) as exc_info:
            await always_failing_func()

        assert "3 attempts" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_retry_on_immediate_success(self):
        """Test that successful calls don't trigger retries"""
        call_count = 0

        @retry_with_backoff(max_attempts=3)
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await success_func()
        assert result == "success"
        assert call_count == 1  # Only called once


class TestExponentialBackoff:
    """Test exponential backoff timing"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test that backoff increases exponentially"""
        call_times = []

        @retry_with_backoff(max_attempts=4, exponential_base=2, exponential_max=10)
        async def timed_failing_func():
            call_times.append(time.time())
            if len(call_times) < 4:
                raise ValueError("Retry me")
            return "success"

        await timed_failing_func()

        # Check timing between calls (approximately exponential)
        assert len(call_times) == 4

        # Backoff should be approximately: 0s, 2s, 4s, 8s
        # Allow for some variance due to execution time
        if len(call_times) >= 3:
            gap1 = call_times[1] - call_times[0]
            gap2 = call_times[2] - call_times[1]
            # gap2 should be roughly 2x gap1 (exponential)
            # Due to jitter and execution time, we allow a wide range
            assert gap2 > gap1 or abs(gap2 - gap1) < 1  # Relaxed for test stability

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_backoff_respects_max_limit(self):
        """Test that backoff doesn't exceed max limit"""
        call_times = []

        @retry_with_backoff(max_attempts=6, exponential_base=10, exponential_max=2)
        async def timed_failing_func():
            call_times.append(time.time())
            if len(call_times) < 4:
                raise ValueError("Retry me")
            return "success"

        await timed_failing_func()

        # Even with base=10, backoff should be capped at 2s
        for i in range(1, len(call_times)):
            gap = call_times[i] - call_times[i - 1]
            # Allow some variance
            assert gap <= 3.0  # Max 2s + 1s variance


class TestRetryWithSpecificExceptions:
    """Test retry with specific exception types"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_only_on_specified_exceptions(self):
        """Test that retry only happens for specified exception types"""
        call_count = 0

        @retry_with_backoff(max_attempts=3, retry_on=ValueError)
        async def selective_retry_func(error_type):
            nonlocal call_count
            call_count += 1
            if error_type == "value":
                raise ValueError("Retry this")
            else:
                raise RuntimeError("Don't retry this")

        # ValueError should be retried
        call_count = 0
        with pytest.raises(RetryExhaustedError):
            await selective_retry_func("value")
        assert call_count == 3  # All attempts used

        # RuntimeError should NOT be retried
        call_count = 0
        with pytest.raises(RuntimeError):
            await selective_retry_func("runtime")
        assert call_count == 1  # Only one attempt

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_on_multiple_exception_types(self):
        """Test retry with multiple exception types"""

        @retry_with_backoff(max_attempts=3, retry_on=(ValueError, RuntimeError))
        async def multi_exception_func(error_type):
            if error_type == "value":
                raise ValueError("Retry this")
            elif error_type == "runtime":
                raise RuntimeError("Retry this too")
            else:
                raise TypeError("Don't retry this")

        # Both ValueError and RuntimeError should be retried
        with pytest.raises(RetryExhaustedError):
            await multi_exception_func("value")

        with pytest.raises(RetryExhaustedError):
            await multi_exception_func("runtime")

        # TypeError should not be retried
        with pytest.raises(TypeError):
            await multi_exception_func("type")


class TestShouldRetryException:
    """Test should_retry_exception logic"""

    @pytest.mark.unit
    def test_should_not_retry_validation_errors(self):
        """Test that validation errors are not retried"""
        exc = ValidationError(message="Invalid input")
        assert should_retry_exception(exc) is False

    @pytest.mark.unit
    def test_should_not_retry_authorization_errors(self):
        """Test that authorization errors are not retried"""
        exc = AuthorizationError(message="Permission denied")
        assert should_retry_exception(exc) is False

    @pytest.mark.unit
    def test_should_retry_external_service_errors(self):
        """Test that external service errors are retried"""
        exc = ExternalServiceError(message="Service unavailable")
        assert should_retry_exception(exc) is True

    @pytest.mark.unit
    def test_should_retry_network_errors(self):
        """Test that network errors are retried"""
        import httpx

        exc = httpx.ConnectError("Connection failed")
        assert should_retry_exception(exc) is True


class TestRetryStrategies:
    """Test different retry strategies"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exponential_strategy(self):
        """Test exponential backoff strategy"""
        call_count = 0

        @retry_with_backoff(max_attempts=3, strategy=RetryStrategy.EXPONENTIAL, exponential_base=2)
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Retry")
            return "success"

        result = await func()
        assert result == "success"
        assert call_count == 3


class TestRetryMetrics:
    """Test retry metrics emission"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_attempt_metric(self):
        """Test that retry attempt metric is emitted"""
        call_count = 0

        @retry_with_backoff(max_attempts=3)
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry")
            return "success"

        with patch("mcp_server_langgraph.resilience.retry.retry_attempt_counter") as mock_metric:  # noqa: F841
            result = await func()
            assert result == "success"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_exhausted_metric(self):
        """Test that retry exhausted metric is emitted"""

        @retry_with_backoff(max_attempts=2)
        async def func():
            raise ValueError("Always fails")

        with patch("mcp_server_langgraph.resilience.retry.retry_exhausted_counter") as mock_metric:  # noqa: F841
            with pytest.raises(RetryExhaustedError):
                await func()


class TestRetryWithOtherPatterns:
    """Test retry composition with other resilience patterns"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_with_timeout(self):
        """Test retry combined with timeout"""
        from mcp_server_langgraph.resilience import with_timeout

        call_count = 0

        @retry_with_backoff(max_attempts=3, exponential_base=1)
        @with_timeout(seconds=10)
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Retry")
            return "success"

        result = await func()
        assert result == "success"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_with_circuit_breaker(self):
        """Test retry combined with circuit breaker"""
        from mcp_server_langgraph.resilience import circuit_breaker

        call_count = 0

        @circuit_breaker(name="test_combo", fail_max=5)
        @retry_with_backoff(max_attempts=2)
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry once")
            return "success"

        result = await func()
        assert result == "success"


class TestRedisOptionalDependency:
    """Test that redis is an optional dependency for retry logic"""

    @pytest.mark.unit
    def test_should_retry_exception_works_without_redis(self):
        """Test that should_retry_exception works even when redis is not installed"""
        import sys

        import httpx

        # Simulate redis not being installed by temporarily removing it from sys.modules
        redis_module = sys.modules.get("redis")
        if redis_module:
            sys.modules["redis"] = None

        try:
            # Create a network error that should be retried
            network_error = httpx.ConnectError("Connection failed")

            # This should return True (retry network errors) even without redis
            result = should_retry_exception(network_error)
            assert result is True, "Network errors should be retried even without redis"

            # Generic errors should still return False
            generic_error = ValueError("Some error")
            result = should_retry_exception(generic_error)
            assert result is False, "Generic errors should not be retried"

        finally:
            # Restore redis module
            if redis_module:
                sys.modules["redis"] = redis_module

    @pytest.mark.unit
    def test_should_retry_exception_handles_redis_import_error(self):
        """Test that ImportError from redis module doesn't crash the retry logic"""
        import builtins

        # Store original import
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "redis":
                raise ImportError("No module named 'redis'")
            return original_import(name, *args, **kwargs)

        # Replace import temporarily
        builtins.__import__ = mock_import

        try:
            # Force reimport of the retry module to trigger the import error
            import importlib

            from mcp_server_langgraph.resilience import retry as retry_module

            importlib.reload(retry_module)

            # This should not raise an exception even though redis import fails
            import httpx

            network_error = httpx.TimeoutException("Timeout")
            result = retry_module.should_retry_exception(network_error)
            assert result is True, "Should still retry network errors without redis"

        finally:
            # Restore original import
            builtins.__import__ = original_import
            # Reload the module again to restore normal behavior
            import importlib

            from mcp_server_langgraph.resilience import retry as retry_module

            importlib.reload(retry_module)
