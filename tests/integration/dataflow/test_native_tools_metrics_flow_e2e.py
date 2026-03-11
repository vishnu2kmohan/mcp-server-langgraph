"""
E2E Integration Test: Native Tools Metrics Data Flow

Tests the complete native tools metrics data flow:
    Tool Selection → record_* functions → Aggregator → Comparison Data → API

This test verifies that native tool metrics are properly recorded and
aggregated for comparison dashboards.

Following memory safety patterns for pytest-xdist (see CLAUDE.md).
"""

import gc
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.native_tools,
    pytest.mark.asyncio,
    pytest.mark.xdist_group(name="native_tools_metrics_flow_e2e"),
]


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def unique_tool_name() -> str:
    """Generate unique tool name for test isolation."""
    return f"test_tool_{uuid4().hex[:8]}"


@pytest.fixture
def fresh_aggregator():
    """Create a fresh metrics aggregator for test isolation."""
    from mcp_server_langgraph.tools.native_metrics import NativeToolMetricsAggregator

    return NativeToolMetricsAggregator()


# ============================================================================
# E2E Native Tools Metrics Flow Tests
# ============================================================================


@pytest.mark.xdist_group("test_native_tool_metrics_recording")
class TestNativeToolMetricsRecording:
    """
    E2E tests for native tool metrics recording.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_record_native_tool_selection(
        self,
        unique_tool_name,
        fresh_aggregator,
    ):
        """
        E2E: Verify native tool selection is recorded.

        GIVEN: A metrics aggregator
        WHEN: A native tool selection is recorded
        THEN: The aggregator contains the selection count
        """
        # Record selection directly to our aggregator
        fresh_aggregator.record_selection(
            tool_name=unique_tool_name,
            source="native",
            provider="anthropic",
        )

        # Get comparison data
        data = fresh_aggregator.get_comparison_data()

        # Find our tool in the data
        tool_data = next(
            (t for t in data["tools"] if t["tool_name"] == unique_tool_name),
            None,
        )

        assert tool_data is not None
        assert tool_data["native"]["selection_count"] == 1
        assert tool_data["native"]["provider"] == "anthropic"

    async def test_record_tool_source_selection(
        self,
        unique_tool_name,
        fresh_aggregator,
    ):
        """
        E2E: Verify tool source selection is recorded for all sources.

        GIVEN: A metrics aggregator
        WHEN: Tool selections from different sources are recorded
        THEN: Each source has correct selection counts
        """
        # Record selections from different sources
        fresh_aggregator.record_selection(unique_tool_name, "native", "anthropic")
        fresh_aggregator.record_selection(unique_tool_name, "native", "anthropic")
        fresh_aggregator.record_selection(unique_tool_name, "builtin", None)

        data = fresh_aggregator.get_comparison_data()
        tool_data = next(
            (t for t in data["tools"] if t["tool_name"] == unique_tool_name),
            None,
        )

        assert tool_data is not None
        assert tool_data["native"]["selection_count"] == 2
        assert tool_data["builtin"]["selection_count"] == 1

    async def test_record_native_tool_execution(
        self,
        unique_tool_name,
        fresh_aggregator,
    ):
        """
        E2E: Verify native tool execution is recorded with latency.

        GIVEN: A metrics aggregator
        WHEN: A native tool execution is recorded
        THEN: The aggregator contains execution count and latency
        """
        fresh_aggregator.record_execution(
            tool_name=unique_tool_name,
            source="native",
            duration_ms=150.5,
            success=True,
            provider="anthropic",
        )

        data = fresh_aggregator.get_comparison_data()
        tool_data = next(
            (t for t in data["tools"] if t["tool_name"] == unique_tool_name),
            None,
        )

        assert tool_data is not None
        native = tool_data["native"]
        assert native["execution_count"] == 1
        assert native["avg_latency_ms"] == 150.5
        assert native["min_latency_ms"] == 150.5
        assert native["max_latency_ms"] == 150.5

    async def test_record_native_tool_error(
        self,
        unique_tool_name,
        fresh_aggregator,
    ):
        """
        E2E: Verify native tool errors are recorded.

        GIVEN: A metrics aggregator
        WHEN: Native tool errors are recorded
        THEN: The aggregator contains error counts
        """
        # Record some executions with failures
        fresh_aggregator.record_execution(
            tool_name=unique_tool_name,
            source="native",
            duration_ms=100.0,
            success=True,
            provider="anthropic",
        )
        fresh_aggregator.record_execution(
            tool_name=unique_tool_name,
            source="native",
            duration_ms=50.0,
            success=False,  # Failed
            provider="anthropic",
        )

        data = fresh_aggregator.get_comparison_data()
        tool_data = next(
            (t for t in data["tools"] if t["tool_name"] == unique_tool_name),
            None,
        )

        assert tool_data is not None
        native = tool_data["native"]
        assert native["execution_count"] == 2
        assert native["error_count"] == 1
        assert native["error_rate"] == 50.0  # 1 error out of 2 executions

    async def test_record_native_fallback(
        self,
        unique_tool_name,
        fresh_aggregator,
    ):
        """
        E2E: Verify native tool fallbacks are recorded.

        GIVEN: A metrics aggregator
        WHEN: A fallback from native to builtin is recorded
        THEN: The aggregator contains fallback counts
        """
        fresh_aggregator.record_fallback(
            tool_name=unique_tool_name,
            from_provider="anthropic",
            to_source="builtin",
            reason="error",
        )

        data = fresh_aggregator.get_comparison_data()
        tool_data = next(
            (t for t in data["tools"] if t["tool_name"] == unique_tool_name),
            None,
        )

        assert tool_data is not None
        assert tool_data["native"]["fallback_count"] == 1


@pytest.mark.xdist_group("test_metrics_aggregator_comparison")
class TestMetricsAggregatorComparison:
    """
    E2E tests for native vs builtin tool comparison metrics.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_comparison_data_structure(
        self,
        unique_tool_name,
        fresh_aggregator,
    ):
        """
        E2E: Verify comparison data has correct structure.

        GIVEN: Metrics for both native and builtin tools
        WHEN: Getting comparison data
        THEN: The data structure is correct for dashboard display
        """
        # Record data for both native and builtin
        fresh_aggregator.record_selection(unique_tool_name, "native", "anthropic")
        fresh_aggregator.record_execution(unique_tool_name, "native", 100.0, True, "anthropic")
        fresh_aggregator.record_selection(unique_tool_name, "builtin", None)
        fresh_aggregator.record_execution(unique_tool_name, "builtin", 200.0, True, None)

        data = fresh_aggregator.get_comparison_data()

        # Verify top-level structure
        assert "tools" in data
        assert "summary" in data

        # Verify summary structure
        summary = data["summary"]
        assert "native_selections" in summary
        assert "builtin_selections" in summary
        assert "native_errors" in summary
        assert "builtin_errors" in summary
        assert "uptime_seconds" in summary

        # Verify tool data structure
        tool_data = next(
            (t for t in data["tools"] if t["tool_name"] == unique_tool_name),
            None,
        )
        assert tool_data is not None
        assert "tool_name" in tool_data
        assert "native" in tool_data
        assert "builtin" in tool_data
        assert "mcp" in tool_data

    async def test_latency_percentiles(
        self,
        unique_tool_name,
        fresh_aggregator,
    ):
        """
        E2E: Verify latency percentiles are calculated.

        GIVEN: Multiple execution latency samples
        WHEN: Getting comparison data
        THEN: Percentiles (p50, p95, p99) are calculated
        """
        # Record multiple executions with varying latencies
        latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        for latency in latencies:
            fresh_aggregator.record_execution(unique_tool_name, "native", latency, True, "anthropic")

        data = fresh_aggregator.get_comparison_data()
        tool_data = next(
            (t for t in data["tools"] if t["tool_name"] == unique_tool_name),
            None,
        )

        assert tool_data is not None
        native = tool_data["native"]

        # Verify percentile fields exist
        assert "p50_latency_ms" in native
        assert "p95_latency_ms" in native
        assert "p99_latency_ms" in native

        # Verify percentile values are reasonable
        assert native["p50_latency_ms"] >= native["min_latency_ms"]
        assert native["p99_latency_ms"] <= native["max_latency_ms"]

    async def test_summary_totals(
        self,
        fresh_aggregator,
    ):
        """
        E2E: Verify summary totals are correctly aggregated.

        GIVEN: Metrics for multiple tools
        WHEN: Getting comparison data
        THEN: Summary totals correctly aggregate across all tools
        """
        # Record data for multiple tools
        tools = ["tool_a", "tool_b", "tool_c"]

        for tool in tools:
            fresh_aggregator.record_selection(tool, "native", "anthropic")
            fresh_aggregator.record_selection(tool, "builtin", None)
            fresh_aggregator.record_execution(tool, "native", 100.0, True, "anthropic")
            fresh_aggregator.record_execution(tool, "native", 50.0, False, "anthropic")

        data = fresh_aggregator.get_comparison_data()
        summary = data["summary"]

        # 3 tools, 1 native selection each = 3
        assert summary["native_selections"] == 3
        # 3 tools, 1 builtin selection each = 3
        assert summary["builtin_selections"] == 3
        # 3 tools, 1 native error each (from failed execution) = 3
        assert summary["native_errors"] == 3
        assert summary["builtin_errors"] == 0


@pytest.mark.xdist_group("test_metrics_aggregator_reset")
class TestMetricsAggregatorReset:
    """
    E2E tests for metrics aggregator reset functionality.
    """

    def setup_method(self):
        """Reset singleton dependencies."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    async def test_aggregator_reset(
        self,
        unique_tool_name,
        fresh_aggregator,
    ):
        """
        E2E: Verify aggregator can be reset for testing.

        GIVEN: An aggregator with recorded metrics
        WHEN: The aggregator is reset
        THEN: All metrics are cleared
        """
        # Record some metrics
        fresh_aggregator.record_selection(unique_tool_name, "native", "anthropic")
        fresh_aggregator.record_execution(unique_tool_name, "native", 100.0, True, "anthropic")

        # Verify data exists
        data = fresh_aggregator.get_comparison_data()
        assert len(data["tools"]) > 0

        # Reset
        fresh_aggregator.reset()

        # Verify data is cleared
        data = fresh_aggregator.get_comparison_data()
        assert len(data["tools"]) == 0
        assert data["summary"]["native_selections"] == 0


@pytest.mark.xdist_group("test_global_metrics_functions")
class TestGlobalMetricsFunctions:
    """
    E2E tests for global metrics recording functions.
    """

    def setup_method(self):
        """Reset singleton dependencies and metrics aggregator."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies
        from mcp_server_langgraph.tools.native_metrics import get_metrics_aggregator

        reset_singleton_dependencies()
        # Reset the global aggregator for test isolation
        get_metrics_aggregator().reset()

    def teardown_method(self):
        """Force GC."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies
        from mcp_server_langgraph.tools.native_metrics import get_metrics_aggregator

        reset_singleton_dependencies()
        get_metrics_aggregator().reset()
        gc.collect()

    async def test_global_record_native_tool_selection(
        self,
    ):
        """
        E2E: Verify global record_native_tool_selection updates aggregator.

        GIVEN: The global metrics aggregator
        WHEN: record_native_tool_selection is called
        THEN: The global aggregator is updated
        """
        from mcp_server_langgraph.tools.native_metrics import (
            get_metrics_aggregator,
            record_native_tool_selection,
        )

        # Record via global function
        record_native_tool_selection(
            tool_name="web_search",
            provider="anthropic",
            preference="auto",
        )

        # Verify global aggregator has the data
        aggregator = get_metrics_aggregator()
        data = aggregator.get_comparison_data()

        tool_data = next(
            (t for t in data["tools"] if t["tool_name"] == "web_search"),
            None,
        )
        assert tool_data is not None
        assert tool_data["native"]["selection_count"] == 1

    async def test_global_record_native_tool_execution(
        self,
    ):
        """
        E2E: Verify global record_native_tool_execution updates aggregator.

        GIVEN: The global metrics aggregator
        WHEN: record_native_tool_execution is called
        THEN: The global aggregator has execution data
        """
        from mcp_server_langgraph.tools.native_metrics import (
            get_metrics_aggregator,
            record_native_tool_execution,
        )

        # Record via global function
        record_native_tool_execution(
            tool_name="code_execution",
            provider="anthropic",
            duration_ms=250.0,
            success=True,
        )

        # Verify global aggregator has the data
        aggregator = get_metrics_aggregator()
        data = aggregator.get_comparison_data()

        tool_data = next(
            (t for t in data["tools"] if t["tool_name"] == "code_execution"),
            None,
        )
        assert tool_data is not None
        assert tool_data["native"]["execution_count"] == 1
        assert tool_data["native"]["avg_latency_ms"] == 250.0

    async def test_global_record_native_fallback(
        self,
    ):
        """
        E2E: Verify global record_native_fallback updates aggregator.

        GIVEN: The global metrics aggregator
        WHEN: record_native_fallback is called
        THEN: The global aggregator has fallback data
        """
        from mcp_server_langgraph.tools.native_metrics import (
            get_metrics_aggregator,
            record_native_fallback,
        )

        # Record via global function
        record_native_fallback(
            tool_name="web_search",
            from_provider="anthropic",
            to_source="builtin",
            reason="circuit_breaker_open",
        )

        # Verify global aggregator has the data
        aggregator = get_metrics_aggregator()
        data = aggregator.get_comparison_data()

        tool_data = next(
            (t for t in data["tools"] if t["tool_name"] == "web_search"),
            None,
        )
        assert tool_data is not None
        assert tool_data["native"]["fallback_count"] == 1
