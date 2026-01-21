"""
Unit tests for fallback chain integration with agent graph (v7).

TDD tests for the integration of NativeToolFallbackChain
with the agent graph tool execution path.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.xdist_group(name="test_agent_graph_fallback")]


class TestExecuteToolWithFallback:
    """Tests for execute_tool_with_fallback function."""

    def teardown_method(self) -> None:
        """Reset state and force GC."""
        from mcp_server_langgraph.tools.native_handler import reset_fallback_chain
        from mcp_server_langgraph.tools.native_metrics import get_metrics_aggregator

        reset_fallback_chain()
        get_metrics_aggregator().reset()
        gc.collect()

    @pytest.mark.asyncio
    async def test_execute_tool_with_fallback_exists(self):
        """execute_tool_with_fallback function should exist."""
        from mcp_server_langgraph.core.tool_executor import (
            execute_tool_with_fallback,
        )

        assert execute_tool_with_fallback is not None

    @pytest.mark.asyncio
    async def test_execute_builtin_tool_directly(self):
        """Builtin tools should execute without fallback chain."""
        from mcp_server_langgraph.core.tool_executor import (
            execute_tool_with_fallback,
        )

        mock_tool = MagicMock()
        mock_tool.ainvoke = AsyncMock(return_value="builtin result")

        with patch(
            "mcp_server_langgraph.core.tool_executor.get_tool_by_name",
            return_value=mock_tool,
        ):
            result, source = await execute_tool_with_fallback(
                tool_name="calculator",
                tool_args={"a": 1, "b": 2},
                tool_preference="builtin",
                model_name="gpt-4",
            )

        assert result == "builtin result"
        assert source == "builtin"

    @pytest.mark.asyncio
    async def test_execute_native_tool_success(self):
        """Native tools should execute via fallback chain on success."""
        from mcp_server_langgraph.core.tool_executor import (
            execute_tool_with_fallback,
        )

        mock_native_executor = AsyncMock(return_value="native result")
        mock_builtin_tool = MagicMock()
        mock_builtin_tool.ainvoke = AsyncMock(return_value="builtin result")

        with patch(
            "mcp_server_langgraph.core.tool_executor.get_tool_by_name",
            return_value=mock_builtin_tool,
        ), patch(
            "mcp_server_langgraph.core.tool_executor._get_native_executor",
            return_value=mock_native_executor,
        ), patch(
            "mcp_server_langgraph.core.tool_executor._should_use_native",
            return_value=True,
        ):
            result, source = await execute_tool_with_fallback(
                tool_name="web_search",
                tool_args={"query": "AI news"},
                tool_preference="native",
                model_name="claude-sonnet-4-20250514",
            )

        assert result == "native result"
        assert source == "native"

    @pytest.mark.asyncio
    async def test_execute_native_tool_fallback(self):
        """Native tools should fall back to builtin on failure."""
        from mcp_server_langgraph.core.tool_executor import (
            execute_tool_with_fallback,
        )

        mock_native_executor = AsyncMock(side_effect=RuntimeError("Native failed"))
        mock_builtin_tool = MagicMock()
        mock_builtin_tool.ainvoke = AsyncMock(return_value="builtin result")

        with patch(
            "mcp_server_langgraph.core.tool_executor.get_tool_by_name",
            return_value=mock_builtin_tool,
        ), patch(
            "mcp_server_langgraph.core.tool_executor._get_native_executor",
            return_value=mock_native_executor,
        ), patch(
            "mcp_server_langgraph.core.tool_executor._should_use_native",
            return_value=True,
        ):
            result, source = await execute_tool_with_fallback(
                tool_name="web_search",
                tool_args={"query": "AI news"},
                tool_preference="native",
                model_name="claude-sonnet-4-20250514",
            )

        assert result == "builtin result"
        assert source == "builtin"

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self):
        """Should return error message when tool not found."""
        from mcp_server_langgraph.core.tool_executor import (
            execute_tool_with_fallback,
        )

        with patch(
            "mcp_server_langgraph.core.tool_executor.get_tool_by_name",
            return_value=None,
        ):
            result, source = await execute_tool_with_fallback(
                tool_name="unknown_tool",
                tool_args={},
                tool_preference="auto",
                model_name="gpt-4",
            )

        assert "not found" in result.lower()
        assert source == "error"

    @pytest.mark.asyncio
    async def test_auto_preference_uses_native_when_available(self):
        """Auto preference should use native when model supports it."""
        from mcp_server_langgraph.core.tool_executor import (
            execute_tool_with_fallback,
        )

        mock_native_executor = AsyncMock(return_value="native result")
        mock_builtin_tool = MagicMock()
        mock_builtin_tool.ainvoke = AsyncMock(return_value="builtin result")

        with patch(
            "mcp_server_langgraph.core.tool_executor.get_tool_by_name",
            return_value=mock_builtin_tool,
        ), patch(
            "mcp_server_langgraph.core.tool_executor._get_native_executor",
            return_value=mock_native_executor,
        ), patch(
            "mcp_server_langgraph.core.tool_executor._should_use_native",
            return_value=True,
        ):
            result, source = await execute_tool_with_fallback(
                tool_name="web_search",
                tool_args={"query": "AI news"},
                tool_preference="auto",
                model_name="claude-sonnet-4-20250514",
            )

        assert result == "native result"
        assert source == "native"


class TestCircuitBreakerIntegration:
    """Tests for circuit breaker integration."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """Circuit breaker should open after consecutive failures."""
        from mcp_server_langgraph.core.tool_executor import (
            NativeToolCircuitBreaker,
        )

        breaker = NativeToolCircuitBreaker(failure_threshold=3)

        # Record 3 failures
        for _ in range(3):
            breaker.record_failure("anthropic")

        assert breaker.is_open("anthropic") is True

    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_after_success(self):
        """Circuit breaker should reset after successful execution."""
        from mcp_server_langgraph.core.tool_executor import (
            NativeToolCircuitBreaker,
        )

        breaker = NativeToolCircuitBreaker(failure_threshold=3)

        # Record 2 failures (not enough to open)
        breaker.record_failure("anthropic")
        breaker.record_failure("anthropic")

        # Record success - should reset
        breaker.record_success("anthropic")

        assert breaker.is_open("anthropic") is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_after_timeout(self):
        """Circuit breaker should allow retry after timeout."""
        import time

        from mcp_server_langgraph.core.tool_executor import (
            NativeToolCircuitBreaker,
        )

        breaker = NativeToolCircuitBreaker(
            failure_threshold=2,
            reset_timeout_seconds=0.1,  # 100ms for testing
        )

        # Open the circuit
        breaker.record_failure("anthropic")
        breaker.record_failure("anthropic")
        assert breaker.is_open("anthropic") is True

        # Wait for timeout
        time.sleep(0.15)

        # Should be half-open (allow retry)
        assert breaker.is_open("anthropic") is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_per_provider(self):
        """Circuit breaker should be per-provider."""
        from mcp_server_langgraph.core.tool_executor import (
            NativeToolCircuitBreaker,
        )

        breaker = NativeToolCircuitBreaker(failure_threshold=2)

        # Open circuit for anthropic
        breaker.record_failure("anthropic")
        breaker.record_failure("anthropic")

        assert breaker.is_open("anthropic") is True
        assert breaker.is_open("google") is False
