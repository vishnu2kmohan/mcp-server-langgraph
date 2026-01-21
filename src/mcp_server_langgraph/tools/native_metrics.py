"""
Native Tools Metrics (v7)

OpenTelemetry metrics for native LLM provider tool observability:
- Tool selection counts (native vs builtin vs mcp)
- Execution latency by provider and tool
- Error rates and fallback tracking
- Preference-based selection tracking

These metrics integrate with the existing observability stack.

Usage:
    from mcp_server_langgraph.tools.native_metrics import (
        record_native_tool_selection,
        record_tool_source_selection,
        record_native_tool_execution,
        record_native_tool_error,
        record_native_fallback,
        record_builtin_tool_execution,
        get_metrics_aggregator,
    )

    # Record when native tool is selected
    record_native_tool_selection(
        tool_name="web_search",
        provider="anthropic",
        preference="auto",
    )

    # Record execution latency
    record_native_tool_execution(
        tool_name="web_search",
        provider="anthropic",
        duration_ms=150.5,
        success=True,
    )

    # Get comparison data for dashboard
    aggregator = get_metrics_aggregator()
    data = aggregator.get_comparison_data()
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Any

from opentelemetry import metrics

# Get meter from observability stack
meter = metrics.get_meter(__name__)


# ==============================================================================
# Label Constants
# ==============================================================================

NATIVE_TOOL_SELECTION_LABELS = [
    "tool_name",
    "provider",
    "preference",
]

TOOL_SOURCE_SELECTION_LABELS = [
    "tool_name",
    "source",
    "model",
]

NATIVE_EXECUTION_LABELS = [
    "tool_name",
    "provider",
    "success",
]

NATIVE_ERROR_LABELS = [
    "tool_name",
    "provider",
    "error_type",
]

NATIVE_FALLBACK_LABELS = [
    "tool_name",
    "from_provider",
    "to_source",
    "reason",
]


# ==============================================================================
# OpenTelemetry Metrics Instruments
# ==============================================================================

native_tool_selection_counter = meter.create_counter(
    name="native_tool.selection.count",
    description="Total native tool selections",
    unit="1",
)

tool_source_selection_counter = meter.create_counter(
    name="tool.source.selection.count",
    description="Tool selections by source (native/builtin/mcp)",
    unit="1",
)

native_tool_execution_histogram = meter.create_histogram(
    name="native_tool.execution.duration",
    description="Native tool execution duration in milliseconds",
    unit="ms",
)

native_tool_error_counter = meter.create_counter(
    name="native_tool.errors.count",
    description="Total native tool errors",
    unit="1",
)

native_fallback_counter = meter.create_counter(
    name="native_tool.fallback.count",
    description="Native tool fallbacks to builtin",
    unit="1",
)

builtin_tool_execution_histogram = meter.create_histogram(
    name="builtin_tool.execution.duration",
    description="Builtin tool execution duration in milliseconds",
    unit="ms",
)

# Circuit breaker state gauge (0=closed, 0.5=half-open, 1=open)
# Note: Using observable gauge for current state
_circuit_breaker_state_gauge = meter.create_gauge(
    name="native_tool.circuit_breaker.state",
    description="Circuit breaker state (0=closed, 0.5=half-open, 1=open)",
    unit="1",
)

circuit_breaker_state_changes_counter = meter.create_counter(
    name="native_tool.circuit_breaker.state_changes",
    description="Total circuit breaker state changes",
    unit="1",
)


def record_circuit_breaker_state(provider: str, state: str) -> None:
    """Record circuit breaker state for a provider.

    Args:
        provider: Provider name (e.g., "anthropic", "google")
        state: State value ("closed", "half_open", "open")
    """
    state_value = {"closed": 0, "half_open": 0.5, "open": 1}.get(state, 0)
    _circuit_breaker_state_gauge.set(state_value, {"provider": provider})


def record_circuit_breaker_state_change(
    provider: str,
    from_state: str,
    to_state: str,
) -> None:
    """Record circuit breaker state change.

    Args:
        provider: Provider name
        from_state: Previous state
        to_state: New state
    """
    circuit_breaker_state_changes_counter.add(
        1,
        {
            "provider": provider,
            "from_state": from_state,
            "to_state": to_state,
        },
    )


# ==============================================================================
# In-Memory Metrics Aggregator (for API queries)
# ==============================================================================


@dataclass
class ToolMetricsSnapshot:
    """Snapshot of metrics for a single tool."""

    tool_name: str
    source: str  # "native", "builtin", "mcp"
    provider: str | None
    selection_count: int = 0
    execution_count: int = 0
    error_count: int = 0
    fallback_count: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if self.execution_count == 0:
            return 0.0
        return self.total_latency_ms / self.execution_count


class NativeToolMetricsAggregator:
    """In-memory aggregator for native tool metrics.

    Stores recent metrics for API querying. Data is ephemeral
    and cleared on restart. For persistent metrics, use Prometheus/Grafana.
    """

    def __init__(self, max_entries: int = 1000) -> None:
        self._lock = Lock()
        self._max_entries = max_entries
        # Key: (tool_name, source, provider)
        self._metrics: dict[tuple[str, str, str | None], ToolMetricsSnapshot] = {}
        # Recent latency samples for percentile calculations
        self._latency_samples: dict[tuple[str, str], list[float]] = {}
        self._start_time = time.time()

    def _get_or_create(
        self,
        tool_name: str,
        source: str,
        provider: str | None = None,
    ) -> ToolMetricsSnapshot:
        """Get or create metrics snapshot for a tool."""
        key = (tool_name, source, provider)
        if key not in self._metrics:
            self._metrics[key] = ToolMetricsSnapshot(
                tool_name=tool_name,
                source=source,
                provider=provider,
            )
        return self._metrics[key]

    def record_selection(
        self,
        tool_name: str,
        source: str,
        provider: str | None = None,
    ) -> None:
        """Record a tool selection event."""
        with self._lock:
            snapshot = self._get_or_create(tool_name, source, provider)
            snapshot.selection_count += 1

    def record_execution(
        self,
        tool_name: str,
        source: str,
        duration_ms: float,
        success: bool,
        provider: str | None = None,
    ) -> None:
        """Record a tool execution event with latency."""
        with self._lock:
            snapshot = self._get_or_create(tool_name, source, provider)
            snapshot.execution_count += 1
            snapshot.total_latency_ms += duration_ms
            snapshot.min_latency_ms = min(snapshot.min_latency_ms, duration_ms)
            snapshot.max_latency_ms = max(snapshot.max_latency_ms, duration_ms)

            if not success:
                snapshot.error_count += 1

            # Store latency sample for percentile calculation
            key = (tool_name, source)
            if key not in self._latency_samples:
                self._latency_samples[key] = []
            samples = self._latency_samples[key]
            samples.append(duration_ms)
            # Keep only recent samples
            if len(samples) > 1000:
                self._latency_samples[key] = samples[-500:]

    def record_error(
        self,
        tool_name: str,
        source: str,
        provider: str | None = None,
    ) -> None:
        """Record a tool error."""
        with self._lock:
            snapshot = self._get_or_create(tool_name, source, provider)
            snapshot.error_count += 1

    def record_fallback(
        self,
        tool_name: str,
        from_provider: str,
        to_source: str,
        reason: str,
    ) -> None:
        """Record a fallback from native to builtin."""
        with self._lock:
            # Record on the native side
            native_snapshot = self._get_or_create(tool_name, "native", from_provider)
            native_snapshot.fallback_count += 1

    def get_comparison_data(self) -> dict[str, Any]:
        """Get comparison data between native and builtin tools.

        Returns aggregated metrics suitable for dashboard display.
        """
        with self._lock:
            # Group by tool name
            tools: dict[str, dict[str, Any]] = {}

            for (tool_name, source, provider), snapshot in self._metrics.items():
                if tool_name not in tools:
                    tools[tool_name] = {
                        "tool_name": tool_name,
                        "native": None,
                        "builtin": None,
                        "mcp": None,
                    }

                latency_key = (tool_name, source)
                samples = self._latency_samples.get(latency_key, [])

                # Calculate percentiles
                p50 = self._percentile(samples, 50) if samples else 0.0
                p95 = self._percentile(samples, 95) if samples else 0.0
                p99 = self._percentile(samples, 99) if samples else 0.0

                tools[tool_name][source] = {
                    "provider": provider,
                    "selection_count": snapshot.selection_count,
                    "execution_count": snapshot.execution_count,
                    "error_count": snapshot.error_count,
                    "fallback_count": snapshot.fallback_count,
                    "avg_latency_ms": round(snapshot.avg_latency_ms, 2),
                    "min_latency_ms": round(snapshot.min_latency_ms, 2)
                    if snapshot.min_latency_ms != float("inf")
                    else 0.0,
                    "max_latency_ms": round(snapshot.max_latency_ms, 2),
                    "p50_latency_ms": round(p50, 2),
                    "p95_latency_ms": round(p95, 2),
                    "p99_latency_ms": round(p99, 2),
                    "error_rate": round(
                        snapshot.error_count / snapshot.execution_count * 100, 2
                    )
                    if snapshot.execution_count > 0
                    else 0.0,
                }

            # Calculate summary stats
            total_native_selections = sum(
                s.selection_count
                for (_, source, _), s in self._metrics.items()
                if source == "native"
            )
            total_builtin_selections = sum(
                s.selection_count
                for (_, source, _), s in self._metrics.items()
                if source == "builtin"
            )
            total_native_errors = sum(
                s.error_count
                for (_, source, _), s in self._metrics.items()
                if source == "native"
            )
            total_builtin_errors = sum(
                s.error_count
                for (_, source, _), s in self._metrics.items()
                if source == "builtin"
            )

            return {
                "tools": list(tools.values()),
                "summary": {
                    "native_selections": total_native_selections,
                    "builtin_selections": total_builtin_selections,
                    "native_errors": total_native_errors,
                    "builtin_errors": total_builtin_errors,
                    "uptime_seconds": round(time.time() - self._start_time, 0),
                },
            }

    def _percentile(self, samples: list[float], p: float) -> float:
        """Calculate percentile from samples."""
        if not samples:
            return 0.0
        sorted_samples = sorted(samples)
        idx = int(len(sorted_samples) * p / 100)
        return sorted_samples[min(idx, len(sorted_samples) - 1)]

    def reset(self) -> None:
        """Reset all metrics (for testing)."""
        with self._lock:
            self._metrics.clear()
            self._latency_samples.clear()
            self._start_time = time.time()


# Global aggregator instance
_aggregator = NativeToolMetricsAggregator()


def get_metrics_aggregator() -> NativeToolMetricsAggregator:
    """Get the global metrics aggregator instance."""
    return _aggregator


# ==============================================================================
# Recording Functions (OpenTelemetry + In-Memory Aggregator)
# ==============================================================================


def record_native_tool_selection(
    tool_name: str,
    provider: str,
    preference: str,
) -> None:
    """Record a native tool selection event.

    Args:
        tool_name: Name of the tool (e.g., "web_search")
        provider: Native provider (e.g., "anthropic", "google")
        preference: User preference that led to selection
    """
    labels = {
        "tool_name": tool_name,
        "provider": provider,
        "preference": preference,
    }
    native_tool_selection_counter.add(1, labels)
    _aggregator.record_selection(tool_name, "native", provider)


def record_tool_source_selection(
    tool_name: str,
    source: str,
    model: str,
) -> None:
    """Record a tool source selection event.

    Args:
        tool_name: Name of the tool
        source: Source selected ("native", "builtin", "mcp")
        model: Model that made the selection
    """
    # Truncate model name to avoid high-cardinality labels
    model_short = model[:32] if len(model) > 32 else model
    labels = {
        "tool_name": tool_name,
        "source": source,
        "model": model_short,
    }
    tool_source_selection_counter.add(1, labels)
    _aggregator.record_selection(tool_name, source, None)


def record_native_tool_execution(
    tool_name: str,
    provider: str,
    duration_ms: float,
    success: bool,
) -> None:
    """Record native tool execution latency.

    Args:
        tool_name: Name of the tool
        provider: Native provider
        duration_ms: Execution duration in milliseconds
        success: Whether execution succeeded
    """
    labels = {
        "tool_name": tool_name,
        "provider": provider,
        "success": str(success).lower(),
    }
    native_tool_execution_histogram.record(duration_ms, labels)
    _aggregator.record_execution(tool_name, "native", duration_ms, success, provider)


def record_native_tool_error(
    tool_name: str,
    provider: str,
    error_type: str,
) -> None:
    """Record a native tool error.

    Args:
        tool_name: Name of the tool
        provider: Native provider
        error_type: Type of error (e.g., "timeout", "rate_limit", "api_error")
    """
    labels = {
        "tool_name": tool_name,
        "provider": provider,
        "error_type": error_type,
    }
    native_tool_error_counter.add(1, labels)
    _aggregator.record_error(tool_name, "native", provider)


def record_native_fallback(
    tool_name: str,
    from_provider: str,
    to_source: str,
    reason: str,
) -> None:
    """Record a fallback from native to builtin.

    Args:
        tool_name: Name of the tool
        from_provider: Native provider that failed
        to_source: Fallback source ("builtin" or "mcp")
        reason: Reason for fallback (e.g., "error", "timeout", "unavailable")
    """
    labels = {
        "tool_name": tool_name,
        "from_provider": from_provider,
        "to_source": to_source,
        "reason": reason,
    }
    native_fallback_counter.add(1, labels)
    _aggregator.record_fallback(tool_name, from_provider, to_source, reason)


def record_builtin_tool_execution(
    tool_name: str,
    duration_ms: float,
    success: bool,
) -> None:
    """Record builtin tool execution latency (for comparison).

    This function should be called from the tool execution layer
    to track builtin tool performance alongside native tools.

    Args:
        tool_name: Name of the tool
        duration_ms: Execution duration in milliseconds
        success: Whether execution succeeded
    """
    _aggregator.record_execution(tool_name, "builtin", duration_ms, success, None)
