"""
Unit tests for native tools metrics (v7).

TDD tests for OpenTelemetry metrics tracking native tool usage,
latency comparisons, and error rates.

RED Phase: These tests define the expected behavior.
GREEN Phase: Implementation in tools/native_metrics.py will make them pass.
"""

import gc
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.xdist_group(name="test_native_tools_metrics")]


class TestNativeToolsMetricsDefinition:
    """Tests for native tools metrics definitions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    def test_native_tool_selection_counter_exists(self):
        """A counter for native tool selections should exist."""
        from mcp_server_langgraph.tools.native_metrics import (
            native_tool_selection_counter,
        )

        assert native_tool_selection_counter is not None

    def test_native_tool_execution_histogram_exists(self):
        """A histogram for native tool execution latency should exist."""
        from mcp_server_langgraph.tools.native_metrics import (
            native_tool_execution_histogram,
        )

        assert native_tool_execution_histogram is not None

    def test_native_tool_error_counter_exists(self):
        """A counter for native tool errors should exist."""
        from mcp_server_langgraph.tools.native_metrics import (
            native_tool_error_counter,
        )

        assert native_tool_error_counter is not None

    def test_tool_source_selection_counter_exists(self):
        """A counter for tool source selections (native/builtin/mcp) should exist."""
        from mcp_server_langgraph.tools.native_metrics import (
            tool_source_selection_counter,
        )

        assert tool_source_selection_counter is not None

    def test_native_fallback_counter_exists(self):
        """A counter for native-to-builtin fallbacks should exist."""
        from mcp_server_langgraph.tools.native_metrics import (
            native_fallback_counter,
        )

        assert native_fallback_counter is not None


class TestNativeToolsMetricsRecording:
    """Tests for native tools metrics recording functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    def test_record_native_tool_selection(self):
        """record_native_tool_selection should record a selection event."""
        from mcp_server_langgraph.tools.native_metrics import (
            record_native_tool_selection,
        )

        # Should not raise
        record_native_tool_selection(
            tool_name="web_search",
            provider="anthropic",
            preference="auto",
        )

    def test_record_tool_source_selection(self):
        """record_tool_source_selection should record source selection."""
        from mcp_server_langgraph.tools.native_metrics import (
            record_tool_source_selection,
        )

        # Should not raise
        record_tool_source_selection(
            tool_name="web_search",
            source="native",
            model="claude-sonnet-4-20250514",
        )

    def test_record_native_tool_execution(self):
        """record_native_tool_execution should record latency."""
        from mcp_server_langgraph.tools.native_metrics import (
            record_native_tool_execution,
        )

        # Should not raise
        record_native_tool_execution(
            tool_name="web_search",
            provider="anthropic",
            duration_ms=150.5,
            success=True,
        )

    def test_record_native_tool_error(self):
        """record_native_tool_error should record error events."""
        from mcp_server_langgraph.tools.native_metrics import (
            record_native_tool_error,
        )

        # Should not raise
        record_native_tool_error(
            tool_name="web_search",
            provider="anthropic",
            error_type="timeout",
        )

    def test_record_native_fallback(self):
        """record_native_fallback should record fallback events."""
        from mcp_server_langgraph.tools.native_metrics import (
            record_native_fallback,
        )

        # Should not raise
        record_native_fallback(
            tool_name="web_search",
            from_provider="anthropic",
            to_source="builtin",
            reason="error",
        )


class TestNativeToolsMetricsLabels:
    """Tests for metric label validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    def test_native_tool_selection_labels(self):
        """Native tool selection should have correct labels."""
        from mcp_server_langgraph.tools.native_metrics import (
            NATIVE_TOOL_SELECTION_LABELS,
        )

        assert "tool_name" in NATIVE_TOOL_SELECTION_LABELS
        assert "provider" in NATIVE_TOOL_SELECTION_LABELS
        assert "preference" in NATIVE_TOOL_SELECTION_LABELS

    def test_tool_source_selection_labels(self):
        """Tool source selection should have correct labels."""
        from mcp_server_langgraph.tools.native_metrics import (
            TOOL_SOURCE_SELECTION_LABELS,
        )

        assert "tool_name" in TOOL_SOURCE_SELECTION_LABELS
        assert "source" in TOOL_SOURCE_SELECTION_LABELS
        assert "model" in TOOL_SOURCE_SELECTION_LABELS

    def test_native_execution_labels(self):
        """Native execution should have correct labels."""
        from mcp_server_langgraph.tools.native_metrics import (
            NATIVE_EXECUTION_LABELS,
        )

        assert "tool_name" in NATIVE_EXECUTION_LABELS
        assert "provider" in NATIVE_EXECUTION_LABELS
        assert "success" in NATIVE_EXECUTION_LABELS


class TestNativeToolMetricsAggregator:
    """Tests for the in-memory metrics aggregator (v7)."""

    def teardown_method(self) -> None:
        """Reset aggregator and force GC."""
        from mcp_server_langgraph.tools.native_metrics import get_metrics_aggregator

        get_metrics_aggregator().reset()
        gc.collect()

    def test_aggregator_exists_returns_true(self):
        """get_metrics_aggregator should return an aggregator instance."""
        from mcp_server_langgraph.tools.native_metrics import get_metrics_aggregator

        aggregator = get_metrics_aggregator()
        assert aggregator is not None

    def test_aggregator_record_selection(self):
        """Aggregator should record selection events."""
        from mcp_server_langgraph.tools.native_metrics import get_metrics_aggregator

        aggregator = get_metrics_aggregator()
        aggregator.record_selection("web_search", "native", "anthropic")
        aggregator.record_selection("web_search", "builtin")

        data = aggregator.get_comparison_data()
        assert len(data["tools"]) == 1
        assert data["tools"][0]["tool_name"] == "web_search"
        assert data["tools"][0]["native"]["selection_count"] == 1
        assert data["tools"][0]["builtin"]["selection_count"] == 1

    def test_aggregator_record_execution(self):
        """Aggregator should record execution events with latency."""
        from mcp_server_langgraph.tools.native_metrics import get_metrics_aggregator

        aggregator = get_metrics_aggregator()
        aggregator.record_execution("web_search", "native", 100.0, True, "anthropic")
        aggregator.record_execution("web_search", "native", 200.0, True, "anthropic")
        aggregator.record_execution("web_search", "builtin", 150.0, True)

        data = aggregator.get_comparison_data()
        native = data["tools"][0]["native"]
        builtin = data["tools"][0]["builtin"]

        assert native["execution_count"] == 2
        assert native["avg_latency_ms"] == 150.0  # (100 + 200) / 2
        assert native["min_latency_ms"] == 100.0
        assert native["max_latency_ms"] == 200.0
        assert builtin["execution_count"] == 1
        assert builtin["avg_latency_ms"] == 150.0

    def test_aggregator_record_error(self):
        """Aggregator should record error events."""
        from mcp_server_langgraph.tools.native_metrics import get_metrics_aggregator

        aggregator = get_metrics_aggregator()
        aggregator.record_execution("web_search", "native", 100.0, False, "anthropic")
        aggregator.record_error("web_search", "native", "anthropic")

        data = aggregator.get_comparison_data()
        native = data["tools"][0]["native"]

        # 1 error from record_execution (success=False) + 1 from record_error
        assert native["error_count"] == 2

    def test_aggregator_record_fallback(self):
        """Aggregator should record fallback events."""
        from mcp_server_langgraph.tools.native_metrics import get_metrics_aggregator

        aggregator = get_metrics_aggregator()
        aggregator.record_fallback("web_search", "anthropic", "builtin", "error")

        data = aggregator.get_comparison_data()
        native = data["tools"][0]["native"]

        assert native["fallback_count"] == 1

    def test_aggregator_summary_includes_stats(self):
        """Aggregator should calculate summary statistics."""
        from mcp_server_langgraph.tools.native_metrics import get_metrics_aggregator

        aggregator = get_metrics_aggregator()
        aggregator.record_selection("web_search", "native", "anthropic")
        aggregator.record_selection("web_search", "builtin")
        aggregator.record_selection("calculator", "builtin")

        data = aggregator.get_comparison_data()
        summary = data["summary"]

        assert summary["native_selections"] == 1
        assert summary["builtin_selections"] == 2
        assert summary["uptime_seconds"] >= 0

    def test_aggregator_reset_clears_data(self):
        """Aggregator reset should clear all metrics."""
        from mcp_server_langgraph.tools.native_metrics import get_metrics_aggregator

        aggregator = get_metrics_aggregator()
        aggregator.record_selection("web_search", "native", "anthropic")
        aggregator.reset()

        data = aggregator.get_comparison_data()
        assert len(data["tools"]) == 0

    def test_record_builtin_tool_execution(self):
        """record_builtin_tool_execution should record builtin latency."""
        from mcp_server_langgraph.tools.native_metrics import (
            get_metrics_aggregator,
            record_builtin_tool_execution,
        )

        record_builtin_tool_execution("web_search", 100.0, True)

        aggregator = get_metrics_aggregator()
        data = aggregator.get_comparison_data()

        assert len(data["tools"]) == 1
        assert data["tools"][0]["builtin"]["execution_count"] == 1

    def test_recording_functions_update_aggregator(self):
        """All recording functions should update the aggregator."""
        from mcp_server_langgraph.tools.native_metrics import (
            get_metrics_aggregator,
            record_native_tool_execution,
            record_native_tool_selection,
        )

        record_native_tool_selection("code_execution", "anthropic", "native")
        record_native_tool_execution("code_execution", "anthropic", 500.0, True)

        data = get_metrics_aggregator().get_comparison_data()
        native = data["tools"][0]["native"]

        assert native["selection_count"] == 1
        assert native["execution_count"] == 1
        assert native["avg_latency_ms"] == 500.0
