"""
Unit tests for native tool fallback chain (v7).

Tests for automatic fallback from native to builtin tools
when native tools fail.
"""

import gc
from unittest.mock import AsyncMock

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.xdist_group(name="test_native_fallback")]


class TestNativeToolFallbackChain:
    """Tests for NativeToolFallbackChain class."""

    def teardown_method(self) -> None:
        """Reset state and force GC."""
        from mcp_server_langgraph.tools.native_handler import reset_fallback_chain
        from mcp_server_langgraph.tools.native_metrics import get_metrics_aggregator

        reset_fallback_chain()
        get_metrics_aggregator().reset()
        gc.collect()

    def test_fallback_chain_exists(self):
        """get_fallback_chain should return a chain instance."""
        from mcp_server_langgraph.tools.native_handler import get_fallback_chain

        chain = get_fallback_chain()
        assert chain is not None

    def test_get_builtin_equivalent_web_search(self):
        """get_builtin_equivalent should return correct mapping."""
        from mcp_server_langgraph.tools.native_handler import (
            NativeToolFallbackChain,
        )

        chain = NativeToolFallbackChain()
        assert chain.get_builtin_equivalent("web_search") == "web_search"
        assert chain.get_builtin_equivalent("code_execution") == "execute_python"
        assert chain.get_builtin_equivalent("unknown_tool") is None

    @pytest.mark.asyncio
    async def test_execute_native_success(self):
        """execute_with_fallback should return native result on success."""
        from mcp_server_langgraph.tools.native_handler import (
            NativeToolFallbackChain,
        )

        chain = NativeToolFallbackChain()

        native_executor = AsyncMock(return_value="native result")
        builtin_executor = AsyncMock(return_value="builtin result")

        result, source = await chain.execute_with_fallback(
            tool_name="web_search",
            args={"query": "AI news"},
            native_executor=native_executor,
            builtin_executor=builtin_executor,
            provider="anthropic",
        )

        assert result == "native result"
        assert source == "native"
        native_executor.assert_called_once()
        builtin_executor.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_fallback_on_native_failure(self):
        """execute_with_fallback should fall back to builtin on native failure."""
        from mcp_server_langgraph.tools.native_handler import (
            NativeToolFallbackChain,
        )

        chain = NativeToolFallbackChain(max_native_retries=0)

        native_executor = AsyncMock(side_effect=RuntimeError("Native failed"))
        builtin_executor = AsyncMock(return_value="builtin result")

        result, source = await chain.execute_with_fallback(
            tool_name="web_search",
            args={"query": "AI news"},
            native_executor=native_executor,
            builtin_executor=builtin_executor,
            provider="anthropic",
        )

        assert result == "builtin result"
        assert source == "builtin"
        native_executor.assert_called_once()
        builtin_executor.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_retry_then_fallback(self):
        """execute_with_fallback should retry before falling back."""
        from mcp_server_langgraph.tools.native_handler import (
            NativeToolFallbackChain,
        )

        chain = NativeToolFallbackChain(max_native_retries=2)

        native_executor = AsyncMock(side_effect=RuntimeError("Native failed"))
        builtin_executor = AsyncMock(return_value="builtin result")

        result, source = await chain.execute_with_fallback(
            tool_name="web_search",
            args={"query": "AI news"},
            native_executor=native_executor,
            builtin_executor=builtin_executor,
            provider="anthropic",
        )

        assert result == "builtin result"
        assert source == "builtin"
        # Should have retried 3 times (1 + 2 retries)
        assert native_executor.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_no_fallback_disabled(self):
        """execute_with_fallback should raise if fallback disabled."""
        from mcp_server_langgraph.tools.native_handler import (
            NativeToolFallbackChain,
        )

        chain = NativeToolFallbackChain(max_native_retries=0, enable_fallback=False)

        native_executor = AsyncMock(side_effect=RuntimeError("Native failed"))
        builtin_executor = AsyncMock(return_value="builtin result")

        with pytest.raises(RuntimeError, match="Native failed"):
            await chain.execute_with_fallback(
                tool_name="web_search",
                args={"query": "AI news"},
                native_executor=native_executor,
                builtin_executor=builtin_executor,
                provider="anthropic",
            )

    @pytest.mark.asyncio
    async def test_execute_no_builtin_available(self):
        """execute_with_fallback should raise if no builtin available."""
        from mcp_server_langgraph.tools.native_handler import (
            NativeToolFallbackChain,
        )

        chain = NativeToolFallbackChain(max_native_retries=0)

        native_executor = AsyncMock(side_effect=RuntimeError("Native failed"))

        with pytest.raises(RuntimeError, match="Native failed"):
            await chain.execute_with_fallback(
                tool_name="web_search",
                args={"query": "AI news"},
                native_executor=native_executor,
                builtin_executor=None,
                provider="anthropic",
            )

    @pytest.mark.asyncio
    async def test_execute_both_fail(self):
        """execute_with_fallback should raise if both fail."""
        from mcp_server_langgraph.tools.native_handler import (
            NativeToolFallbackChain,
        )

        chain = NativeToolFallbackChain(max_native_retries=0)

        native_executor = AsyncMock(side_effect=RuntimeError("Native failed"))
        builtin_executor = AsyncMock(side_effect=RuntimeError("Builtin also failed"))

        with pytest.raises(RuntimeError, match="Builtin also failed"):
            await chain.execute_with_fallback(
                tool_name="web_search",
                args={"query": "AI news"},
                native_executor=native_executor,
                builtin_executor=builtin_executor,
                provider="anthropic",
            )


class TestErrorClassification:
    """Tests for error type classification."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_classify_timeout_error(self):
        """Should classify timeout errors correctly."""
        from mcp_server_langgraph.tools.native_handler import (
            NativeToolFallbackChain,
        )

        chain = NativeToolFallbackChain()

        assert chain._classify_error(TimeoutError("Request timed out")) == "timeout"
        assert chain._classify_error(Exception("Operation timeout")) == "timeout"

    def test_classify_rate_limit_error(self):
        """Should classify rate limit errors correctly."""
        from mcp_server_langgraph.tools.native_handler import (
            NativeToolFallbackChain,
        )

        chain = NativeToolFallbackChain()

        assert chain._classify_error(Exception("Rate limit exceeded")) == "rate_limit"

    def test_classify_quota_error(self):
        """Should classify quota errors correctly."""
        from mcp_server_langgraph.tools.native_handler import (
            NativeToolFallbackChain,
        )

        chain = NativeToolFallbackChain()

        assert chain._classify_error(Exception("Quota exceeded")) == "quota_exceeded"

    def test_classify_auth_error(self):
        """Should classify auth errors correctly."""
        from mcp_server_langgraph.tools.native_handler import (
            NativeToolFallbackChain,
        )

        chain = NativeToolFallbackChain()

        assert chain._classify_error(Exception("Unauthorized access")) == "auth_error"
        assert chain._classify_error(Exception("Auth failed")) == "auth_error"

    def test_classify_network_error(self):
        """Should classify network errors correctly."""
        from mcp_server_langgraph.tools.native_handler import (
            NativeToolFallbackChain,
        )

        chain = NativeToolFallbackChain()

        assert chain._classify_error(Exception("Connection refused")) == "network_error"
        assert chain._classify_error(Exception("Network error")) == "network_error"

    def test_classify_unknown_error(self):
        """Should classify unknown errors as unknown."""
        from mcp_server_langgraph.tools.native_handler import (
            NativeToolFallbackChain,
        )

        chain = NativeToolFallbackChain()

        assert chain._classify_error(Exception("Something went wrong")) == "unknown"


class TestFallbackMetrics:
    """Tests for fallback metrics recording."""

    def teardown_method(self) -> None:
        """Reset state and force GC."""
        from mcp_server_langgraph.tools.native_handler import reset_fallback_chain
        from mcp_server_langgraph.tools.native_metrics import get_metrics_aggregator

        reset_fallback_chain()
        get_metrics_aggregator().reset()
        gc.collect()

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_success(self):
        """Metrics should be recorded on successful native execution."""
        from mcp_server_langgraph.tools.native_handler import (
            NativeToolFallbackChain,
        )
        from mcp_server_langgraph.tools.native_metrics import get_metrics_aggregator

        chain = NativeToolFallbackChain()
        native_executor = AsyncMock(return_value="result")

        await chain.execute_with_fallback(
            tool_name="web_search",
            args={"query": "test"},
            native_executor=native_executor,
            builtin_executor=None,
            provider="anthropic",
        )

        data = get_metrics_aggregator().get_comparison_data()
        assert len(data["tools"]) == 1
        assert data["tools"][0]["native"]["execution_count"] == 1

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_fallback(self):
        """Metrics should be recorded on fallback execution."""
        from mcp_server_langgraph.tools.native_handler import (
            NativeToolFallbackChain,
        )
        from mcp_server_langgraph.tools.native_metrics import get_metrics_aggregator

        chain = NativeToolFallbackChain(max_native_retries=0)
        native_executor = AsyncMock(side_effect=RuntimeError("fail"))
        builtin_executor = AsyncMock(return_value="result")

        await chain.execute_with_fallback(
            tool_name="web_search",
            args={"query": "test"},
            native_executor=native_executor,
            builtin_executor=builtin_executor,
            provider="anthropic",
        )

        data = get_metrics_aggregator().get_comparison_data()
        assert len(data["tools"]) == 1
        # Should have native error and builtin execution
        assert data["tools"][0]["native"]["error_count"] == 1
        assert data["tools"][0]["native"]["fallback_count"] == 1
        assert data["tools"][0]["builtin"]["execution_count"] == 1
