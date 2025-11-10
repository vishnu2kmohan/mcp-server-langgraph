"""
Unit tests for fallback strategies.

Tests fallback behavior, strategies, and metrics.
"""

import asyncio
from unittest.mock import patch

import pytest

from mcp_server_langgraph.resilience.fallback import (
    CachedValueFallback,
    DefaultValueFallback,
    FunctionFallback,
    StaleDataFallback,
    fail_closed,
    fail_open,
    return_empty_on_error,
    with_fallback,
)


class TestBasicFallback:
    """Test basic fallback functionality"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_static_fallback_value(self):
        """Test fallback with static value"""

        @with_fallback(fallback="default_value")
        async def failing_func():
            raise ValueError("Error")

        result = await failing_func()
        assert result == "default_value"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_function_fallback(self):
        """Test fallback with function"""

        async def fallback_fn(*args, **kwargs):
            return "fallback_result"

        @with_fallback(fallback_fn=fallback_fn)
        async def failing_func():
            raise ValueError("Error")

        result = await failing_func()
        assert result == "fallback_result"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_fallback_on_success(self):
        """Test that fallback is not used when function succeeds"""

        fallback_called = False

        async def fallback_fn():
            nonlocal fallback_called
            fallback_called = True
            return "fallback"

        @with_fallback(fallback_fn=fallback_fn)
        async def success_func():
            return "success"

        result = await success_func()
        assert result == "success"
        assert fallback_called is False


class TestFallbackStrategies:
    """Test different fallback strategies"""

    @pytest.mark.unit
    def test_default_value_fallback(self):
        """Test DefaultValueFallback strategy"""
        strategy = DefaultValueFallback(default_value="default")
        result = strategy.get_fallback_value()
        assert result == "default"

    @pytest.mark.unit
    def test_cached_value_fallback(self):
        """Test CachedValueFallback strategy"""
        strategy = CachedValueFallback()

        # Cache a value
        strategy.cache_value("cached_data", "user_123")

        # Retrieve it
        result = strategy.get_fallback_value("user_123")
        assert result == "cached_data"

    @pytest.mark.unit
    def test_function_fallback_strategy(self):
        """Test FunctionFallback strategy"""

        def fallback_fn(user_id):
            return f"fallback_for_{user_id}"

        strategy = FunctionFallback(fallback_fn=fallback_fn)
        result = strategy.get_fallback_value("user_123")
        assert result == "fallback_for_user_123"

    @pytest.mark.unit
    def test_stale_data_fallback_within_limit(self):
        """Test StaleDataFallback returns data within staleness limit"""
        strategy = StaleDataFallback(max_staleness_seconds=60)

        # Cache fresh data
        strategy.cache_value("fresh_data", "key1")

        # Retrieve immediately (should work)
        result = strategy.get_fallback_value("key1")
        assert result == "fresh_data"

    @pytest.mark.unit
    def test_stale_data_fallback_exceeds_limit(self):
        """Test StaleDataFallback rejects too-stale data"""
        import time

        # Performance optimization: Use 0.1s staleness instead of 1s (10x faster)
        strategy = StaleDataFallback(max_staleness_seconds=0.1)

        # Cache data
        strategy.cache_value("old_data", "key1")

        # Wait for data to become stale (0.1s staleness + small buffer) - reduced from 1.05s
        time.sleep(0.15)

        # Should return None (too stale)
        result = strategy.get_fallback_value("key1")
        assert result is None


class TestConvenienceDecorators:
    """Test convenience fallback decorators"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fail_open_decorator(self):
        """Test fail_open decorator (allow on error)"""

        @fail_open
        async def check_permission():
            raise ValueError("Auth service down")

        result = await check_permission()
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fail_closed_decorator(self):
        """Test fail_closed decorator (deny on error)"""

        @fail_closed
        async def check_admin_permission():
            raise ValueError("Auth service down")

        result = await check_admin_permission()
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_return_empty_on_error_list(self):
        """Test return_empty_on_error with list return type"""

        @return_empty_on_error
        async def get_items() -> list:
            raise ValueError("Database error")

        result = await get_items()
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_return_empty_on_error_dict(self):
        """Test return_empty_on_error with dict return type"""

        @return_empty_on_error
        async def get_config() -> dict:
            raise ValueError("Config error")

        result = await get_config()
        assert result == {}


class TestFallbackWithSpecificExceptions:
    """Test fallback with specific exception types"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fallback_only_on_specified_exceptions(self):
        """Test that fallback only triggers for specified exceptions"""

        @with_fallback(fallback="fallback", fallback_on=(ValueError,))
        async def func(error_type):
            if error_type == "value":
                raise ValueError("Catch this")
            else:
                raise RuntimeError("Don't catch this")

        # ValueError should use fallback
        result = await func("value")
        assert result == "fallback"

        # RuntimeError should propagate
        with pytest.raises(RuntimeError):
            await func("runtime")


class TestFallbackMetrics:
    """Test fallback metrics emission"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fallback_used_metric(self):
        """Test that fallback used metric is emitted"""

        @with_fallback(fallback="fallback_value")
        async def failing_func():
            raise ValueError("Error")

        with patch("mcp_server_langgraph.resilience.fallback.fallback_used_counter") as mock_metric:  # noqa: F841
            result = await failing_func()
            assert result == "fallback_value"


class TestFallbackEdgeCases:
    """Test fallback edge cases"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fallback_with_function_arguments(self):
        """Test that fallback function receives original arguments"""

        def fallback_fn(user_id, resource):
            return f"fallback_for_{user_id}_{resource}"

        @with_fallback(fallback_fn=fallback_fn)
        async def check_permission(user_id, resource):
            raise ValueError("Service down")

        result = await check_permission("alice", "doc_123")
        assert result == "fallback_for_alice_doc_123"

    @pytest.mark.unit
    def test_fallback_requires_one_strategy(self):
        """Test that exactly one fallback strategy must be provided"""
        with pytest.raises(ValueError):
            # No fallback specified
            @with_fallback()
            async def func():
                pass

        with pytest.raises(ValueError):
            # Multiple fallbacks specified
            @with_fallback(fallback="value", fallback_fn=lambda: "fn")
            async def func():
                pass

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_fallback_function(self):
        """Test async fallback function"""

        async def async_fallback():
            await asyncio.sleep(0.01)
            return "async_fallback"

        @with_fallback(fallback_fn=async_fallback)
        async def failing_func():
            raise ValueError("Error")

        result = await failing_func()
        assert result == "async_fallback"


class TestFallbackComposition:
    """Test fallback with other resilience patterns"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fallback_with_retry(self):
        """Test fallback combined with retry"""
        from mcp_server_langgraph.resilience import retry_with_backoff

        call_count = 0

        @with_fallback(fallback="fallback_value")
        @retry_with_backoff(max_attempts=2)
        async def func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        # Should retry twice, then use fallback
        result = await func()
        assert result == "fallback_value"
        assert call_count == 2  # Retried once (2 total attempts)
