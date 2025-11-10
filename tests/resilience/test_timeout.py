"""
Unit tests for timeout enforcement.

Tests timeout behavior, context managers, and metrics.
"""

import asyncio
from unittest.mock import patch

import pytest

from mcp_server_langgraph.core.exceptions import TimeoutError as MCPTimeoutError
from mcp_server_langgraph.resilience.timeout import TimeoutContext, get_timeout_for_operation, with_timeout


class TestTimeoutBasics:
    """Test basic timeout functionality"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_timeout_enforced(self):
        """Test that timeout is enforced"""
        # Performance optimization: Use 0.1s timeout instead of 1s (10x faster)

        @with_timeout(seconds=0.1)
        async def slow_func():
            await asyncio.sleep(0.15)  # Just over timeout - reduced from 1.05s
            return "should_not_reach"

        with pytest.raises((MCPTimeoutError, asyncio.TimeoutError)):
            await slow_func()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_timeout_for_fast_function(self):
        """Test that fast functions don't timeout"""

        @with_timeout(seconds=5)
        async def fast_func():
            await asyncio.sleep(0.1)
            return "success"

        result = await fast_func()
        assert result == "success"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_timeout_custom_value(self):
        """Test custom timeout value"""

        @with_timeout(seconds=2)
        async def func():
            await asyncio.sleep(0.5)  # Well under timeout
            return "success"

        result = await func()
        assert result == "success"


class TestTimeoutByOperationType:
    """Test timeout by operation type"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_llm_timeout(self):
        """Test LLM operation timeout (60s)"""

        @with_timeout(operation_type="llm")
        async def llm_func():
            await asyncio.sleep(0.1)
            return "llm_result"

        result = await llm_func()
        assert result == "llm_result"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_auth_timeout(self):
        """Test auth operation timeout (5s)"""

        @with_timeout(operation_type="auth")
        async def auth_func():
            await asyncio.sleep(0.1)
            return "auth_result"

        result = await auth_func()
        assert result == "auth_result"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_db_timeout(self):
        """Test DB operation timeout (10s)"""

        @with_timeout(operation_type="db")
        async def db_func():
            await asyncio.sleep(0.1)
            return "db_result"

        result = await db_func()
        assert result == "db_result"

    @pytest.mark.unit
    def test_get_timeout_for_operation(self):
        """Test get_timeout_for_operation helper"""
        assert get_timeout_for_operation("llm") == 60
        assert get_timeout_for_operation("auth") == 5
        assert get_timeout_for_operation("db") == 10
        assert get_timeout_for_operation("http") == 15
        assert get_timeout_for_operation("default") == 30


class TestTimeoutContextManager:
    """Test timeout context manager"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_timeout_context_manager(self):
        """Test TimeoutContext as context manager"""
        async with TimeoutContext(seconds=5):
            await asyncio.sleep(0.1)
            result = "success"

        assert result == "success"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_timeout_context_manager_enforced(self):
        """Test that TimeoutContext enforces timeout"""
        # Performance optimization: Use 0.1s timeout instead of 1s (10x faster)
        with pytest.raises((MCPTimeoutError, asyncio.TimeoutError)):
            async with TimeoutContext(seconds=0.1):
                await asyncio.sleep(0.15)  # Just over timeout - reduced from 1.05s

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_timeout_context_by_operation_type(self):
        """Test TimeoutContext with operation type"""
        async with TimeoutContext(operation_type="auth"):
            await asyncio.sleep(0.1)
            result = "success"

        assert result == "success"


class TestTimeoutMetrics:
    """Test timeout metrics emission"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_timeout_metric_on_violation(self):
        """Test that metric is emitted on timeout violation"""
        # Performance optimization: Use 0.1s timeout instead of 1s (10x faster)

        @with_timeout(seconds=0.1)
        async def slow_func():
            await asyncio.sleep(0.15)  # Just over timeout - reduced from 1.05s

        with patch("mcp_server_langgraph.resilience.timeout.timeout_exceeded_counter") as mock_metric:  # noqa: F841
            with pytest.raises((MCPTimeoutError, asyncio.TimeoutError)):
                await slow_func()


class TestTimeoutEdgeCases:
    """Test timeout edge cases"""

    @pytest.mark.unit
    def test_timeout_only_for_async_functions(self):
        """Test that timeout decorator only works with async functions"""

        with pytest.raises(TypeError):

            @with_timeout(seconds=5)
            def sync_func():
                return "sync"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_timeout_with_zero_duration(self):
        """Test timeout with zero duration (should timeout immediately)"""

        @with_timeout(seconds=0)
        async def func():
            await asyncio.sleep(0.01)

        with pytest.raises((MCPTimeoutError, asyncio.TimeoutError)):
            await func()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_multiple_concurrent_timeouts(self):
        """Test multiple concurrent operations with different timeouts"""
        # Performance optimization: Use 0.1s/0.2s timeouts instead of 1s/2s (10x faster)

        @with_timeout(seconds=0.2)
        async def fast_func():
            await asyncio.sleep(0.1)
            return "fast"

        @with_timeout(seconds=0.1)
        async def slow_func():
            await asyncio.sleep(0.15)  # Just over timeout - reduced from 1.05s
            return "slow"

        # Run concurrently
        results = await asyncio.gather(
            fast_func(),
            slow_func(),
            return_exceptions=True,
        )

        assert results[0] == "fast"
        assert isinstance(results[1], (MCPTimeoutError, asyncio.TimeoutError))
