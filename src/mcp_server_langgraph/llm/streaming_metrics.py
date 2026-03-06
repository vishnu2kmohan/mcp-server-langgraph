"""
LLM streaming metrics.

Prometheus metrics for streaming LLM operations:
- llm_streaming_ttfc_seconds: Time To First Chunk histogram
- llm_streaming_inter_chunk_latency_seconds: Inter-chunk latency histogram
- llm_streaming_duration_seconds: Total streaming duration histogram
- llm_streaming_chunks_total: Counter of chunks emitted

These metrics are scraped by Alloy and displayed in the LLM Streaming Grafana dashboard.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from mcp_server_langgraph.llm.metrics import get_model_family, normalize_status

logger = logging.getLogger(__name__)


# =============================================================================
# Feature Flag Check
# =============================================================================


def _is_streaming_metrics_enabled() -> bool:
    """
    Check if streaming metrics are enabled via feature flag.

    Returns:
        True if enable_streaming_metrics feature flag is True, False otherwise.
    """
    try:
        from mcp_server_langgraph.core.feature_flags import get_feature_flags

        return get_feature_flags().enable_streaming_metrics
    except Exception:
        # If feature flags unavailable, default to enabled
        return True


# =============================================================================
# Prometheus Metrics (Lazy Initialization)
# =============================================================================

_metrics_available: bool | None = None
_llm_streaming_ttfc: Any = None
_llm_streaming_inter_chunk_latency: Any = None
_llm_streaming_duration: Any = None
_llm_streaming_chunks: Any = None


def _init_metrics() -> bool:
    """Initialize streaming metrics lazily."""
    global _metrics_available
    global _llm_streaming_ttfc
    global _llm_streaming_inter_chunk_latency
    global _llm_streaming_duration
    global _llm_streaming_chunks

    if _metrics_available is not None:
        return _metrics_available

    try:
        from prometheus_client import Counter, Histogram

        # Time To First Chunk - measures initial latency before streaming starts
        # Buckets optimized for sub-second to multi-second latencies
        _llm_streaming_ttfc = Histogram(
            "llm_streaming_ttfc_seconds",
            "Time to first chunk in seconds",
            ["model", "provider"],
            buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
        )

        # Inter-chunk latency - measures gap between consecutive chunks
        # Buckets optimized for millisecond-level latencies
        _llm_streaming_inter_chunk_latency = Histogram(
            "llm_streaming_inter_chunk_latency_seconds",
            "Latency between consecutive chunks in seconds",
            ["model", "provider"],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
        )

        # Total streaming duration - measures end-to-end streaming time
        _llm_streaming_duration = Histogram(
            "llm_streaming_duration_seconds",
            "Total streaming duration in seconds",
            ["model", "provider", "status"],
            buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
        )

        # Total chunks emitted - tracks streaming volume
        _llm_streaming_chunks = Counter(
            "llm_streaming_chunks_total",
            "Total number of chunks emitted",
            ["model", "provider"],
        )

        _metrics_available = True
        return True

    except ImportError:
        logger.debug("prometheus_client not available, streaming metrics disabled")
        _metrics_available = False
        return False


# Initialize on module load
_init_metrics()


# =============================================================================
# Metric Recording Functions
# =============================================================================


def record_ttfc(model: str, ttfc_seconds: float, provider: str = "unknown") -> None:
    """
    Record Time To First Chunk metric.

    Args:
        model: Model name (e.g., "gpt-4", "claude-3-opus")
        ttfc_seconds: Time to first chunk in seconds
        provider: LLM provider (e.g., "openai", "anthropic", "google")
    """
    if not _metrics_available or not _is_streaming_metrics_enabled():
        return

    try:
        if _llm_streaming_ttfc:
            model_family = get_model_family(model)
            _llm_streaming_ttfc.labels(model=model_family, provider=provider).observe(ttfc_seconds)
    except Exception as e:
        logger.debug("Failed to record TTFC metric: %s", e)


def record_inter_chunk_latency(model: str, latency_seconds: float, provider: str = "unknown") -> None:
    """
    Record inter-chunk latency metric.

    Args:
        model: Model name
        latency_seconds: Latency between chunks in seconds
        provider: LLM provider
    """
    if not _metrics_available or not _is_streaming_metrics_enabled():
        return

    try:
        if _llm_streaming_inter_chunk_latency:
            model_family = get_model_family(model)
            _llm_streaming_inter_chunk_latency.labels(model=model_family, provider=provider).observe(latency_seconds)
    except Exception as e:
        logger.debug("Failed to record inter-chunk latency metric: %s", e)


def record_streaming_duration(
    model: str,
    duration_seconds: float,
    provider: str = "unknown",
    status: str = "success",
) -> None:
    """
    Record total streaming duration metric.

    Args:
        model: Model name
        duration_seconds: Total streaming duration in seconds
        provider: LLM provider
        status: Streaming status ("success", "error", "timeout", "cancelled")
    """
    if not _metrics_available or not _is_streaming_metrics_enabled():
        return

    try:
        if _llm_streaming_duration:
            model_family = get_model_family(model)
            normalized_status = normalize_status(status)
            _llm_streaming_duration.labels(
                model=model_family,
                provider=provider,
                status=normalized_status,
            ).observe(duration_seconds)
    except Exception as e:
        logger.debug("Failed to record streaming duration metric: %s", e)


def record_chunk_count(model: str, count: int, provider: str = "unknown") -> None:
    """
    Record total chunks emitted for a streaming response.

    Args:
        model: Model name
        count: Number of chunks emitted
        provider: LLM provider
    """
    if not _metrics_available or not _is_streaming_metrics_enabled():
        return

    try:
        if _llm_streaming_chunks:
            model_family = get_model_family(model)
            _llm_streaming_chunks.labels(model=model_family, provider=provider).inc(count)
    except Exception as e:
        logger.debug("Failed to record chunk count metric: %s", e)


# =============================================================================
# Context Manager for Tracking Streaming Metrics
# =============================================================================


class StreamingMetricsContext:
    """
    Context manager for tracking streaming metrics throughout a streaming response.

    Usage:
        ctx = StreamingMetricsContext(model="gpt-4", provider="openai")
        ctx.start()

        async for chunk in stream:
            if ctx.first_chunk_received:
                ctx.record_chunk()
            else:
                ctx.record_first_chunk()
            yield chunk

        ctx.finalize(status="success")

    Attributes:
        ttfc_seconds: Time to first chunk (set after record_first_chunk)
        duration_seconds: Total duration (set after finalize)
        chunk_count: Number of chunks received
        finalized: Whether finalize() has been called
    """

    def __init__(self, model: str, provider: str = "unknown") -> None:
        """
        Initialize streaming metrics context.

        Args:
            model: Model name for metrics labels
            provider: Provider name for metrics labels
        """
        self.model = model
        self.provider = provider

        # Timing state
        self._start_time: float | None = None
        self._first_chunk_time: float | None = None
        self._last_chunk_time: float | None = None
        self._end_time: float | None = None

        # Metrics values (exposed for testing)
        self.ttfc_seconds: float | None = None
        self.duration_seconds: float | None = None
        self.chunk_count: int = 0
        self.finalized: bool = False

    def start(self) -> None:
        """Mark the start of streaming."""
        self._start_time = time.perf_counter()

    def record_first_chunk(self) -> None:
        """Record receipt of the first chunk."""
        if self._start_time is None:
            logger.warning("record_first_chunk called before start()")
            return

        now = time.perf_counter()
        self._first_chunk_time = now
        self._last_chunk_time = now
        self.chunk_count = 1

        # Calculate and record TTFC
        self.ttfc_seconds = now - self._start_time
        record_ttfc(self.model, self.ttfc_seconds, self.provider)

    @property
    def first_chunk_received(self) -> bool:
        """Check if first chunk has been received."""
        return self._first_chunk_time is not None

    def record_chunk(self) -> None:
        """Record receipt of a subsequent chunk."""
        if self._last_chunk_time is None:
            logger.warning("record_chunk called before record_first_chunk()")
            return

        now = time.perf_counter()
        inter_chunk_latency = now - self._last_chunk_time
        self._last_chunk_time = now
        self.chunk_count += 1

        # Record inter-chunk latency
        record_inter_chunk_latency(self.model, inter_chunk_latency, self.provider)

    def finalize(self, status: str = "success") -> None:
        """
        Finalize metrics and emit aggregated values.

        Args:
            status: Final status of streaming ("success", "error", "timeout", "cancelled")
        """
        if self.finalized:
            return

        self._end_time = time.perf_counter()
        self.finalized = True

        if self._start_time is not None:
            self.duration_seconds = self._end_time - self._start_time
            record_streaming_duration(self.model, self.duration_seconds, self.provider, status)

        if self.chunk_count > 0:
            record_chunk_count(self.model, self.chunk_count, self.provider)
