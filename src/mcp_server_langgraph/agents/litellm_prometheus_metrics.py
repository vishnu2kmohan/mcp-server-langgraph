"""
LiteLLM Model Sync Prometheus Metrics.

Prometheus-compatible metrics for LiteLLM model sync operations.
These metrics are exposed via the /metrics endpoint for Alloy/Prometheus scraping.

Sprint 2 - Enhanced Model Selector: LiteLLM Sync Observability

Metrics:
- litellm_sync_total: Total sync operations by result (success/failure)
- litellm_sync_duration_seconds: Sync duration histogram
- litellm_sync_models_updated_total: Total models updated
- litellm_sync_last_success_timestamp: Last successful sync timestamp
- litellm_sync_errors_total: Sync errors by error type

Usage:
    from mcp_server_langgraph.agents.litellm_prometheus_metrics import (
        record_sync_success,
        record_sync_failure,
        record_models_updated,
    )

    # After successful sync
    record_sync_success(duration_seconds=1.5, models_updated=5)

    # After failed sync
    record_sync_failure(error_type="connection_error", duration_seconds=0.3)
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Lazy-load prometheus_client to handle missing dependency
_metrics_available: bool | None = None
_litellm_sync_total: Any = None
_litellm_sync_duration_seconds: Any = None
_litellm_sync_models_updated_total: Any = None
_litellm_sync_last_success_timestamp: Any = None
_litellm_sync_errors_total: Any = None


def _init_metrics() -> bool:
    """Initialize Prometheus LiteLLM sync metrics lazily.

    Returns:
        True if metrics are available, False if prometheus_client is not installed.
    """
    global _metrics_available
    global _litellm_sync_total
    global _litellm_sync_duration_seconds
    global _litellm_sync_models_updated_total
    global _litellm_sync_last_success_timestamp
    global _litellm_sync_errors_total

    if _metrics_available is not None:
        return _metrics_available

    try:
        from prometheus_client import Counter, Gauge, Histogram

        # Sync operation counter (success/failure)
        _litellm_sync_total = Counter(
            "litellm_sync_total",
            "Total LiteLLM model sync operations by result",
            ["result"],  # result: success, failure
        )

        # Sync duration histogram
        _litellm_sync_duration_seconds = Histogram(
            "litellm_sync_duration_seconds",
            "LiteLLM model sync duration in seconds",
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
        )

        # Models updated counter
        _litellm_sync_models_updated_total = Counter(
            "litellm_sync_models_updated_total",
            "Total number of models updated during LiteLLM sync",
        )

        # Last successful sync timestamp
        _litellm_sync_last_success_timestamp = Gauge(
            "litellm_sync_last_success_timestamp",
            "Unix timestamp of the last successful LiteLLM sync",
        )

        # Sync errors counter by error type
        _litellm_sync_errors_total = Counter(
            "litellm_sync_errors_total",
            "Total LiteLLM sync errors by error type",
            ["error_type"],  # error_type: connection_error, parse_error, timeout, etc.
        )

        _metrics_available = True
        logger.debug("LiteLLM Prometheus metrics initialized successfully")
        return True

    except ImportError:
        _metrics_available = False
        logger.debug("prometheus_client not available, LiteLLM metrics disabled")
        return False


def record_sync_success(duration_seconds: float, models_updated: int) -> None:
    """Record a successful LiteLLM sync operation.

    Args:
        duration_seconds: How long the sync took in seconds.
        models_updated: Number of models that had pricing updated.
    """
    if not _init_metrics():
        return

    try:
        if _litellm_sync_total:
            _litellm_sync_total.labels(result="success").inc()

        if _litellm_sync_duration_seconds:
            _litellm_sync_duration_seconds.observe(duration_seconds)

        if _litellm_sync_models_updated_total and models_updated > 0:
            _litellm_sync_models_updated_total.inc(models_updated)

        if _litellm_sync_last_success_timestamp:
            _litellm_sync_last_success_timestamp.set(time.time())

    except Exception as e:
        logger.debug(f"Failed to record LiteLLM sync success metrics: {e}")


def record_sync_failure(error_type: str, duration_seconds: float) -> None:
    """Record a failed LiteLLM sync operation.

    Args:
        error_type: Type of error that occurred (e.g., connection_error, timeout).
        duration_seconds: How long the sync attempt took before failing.
    """
    if not _init_metrics():
        return

    try:
        if _litellm_sync_total:
            _litellm_sync_total.labels(result="failure").inc()

        if _litellm_sync_duration_seconds:
            _litellm_sync_duration_seconds.observe(duration_seconds)

        if _litellm_sync_errors_total:
            _litellm_sync_errors_total.labels(error_type=error_type).inc()

    except Exception as e:
        logger.debug(f"Failed to record LiteLLM sync failure metrics: {e}")


def record_models_updated(count: int) -> None:
    """Record the number of models updated during a sync.

    This is a convenience function for incrementing the models updated counter
    separately from record_sync_success.

    Args:
        count: Number of models updated.
    """
    if not _init_metrics():
        return

    try:
        if _litellm_sync_models_updated_total and count > 0:
            _litellm_sync_models_updated_total.inc(count)

    except Exception as e:
        logger.debug(f"Failed to record LiteLLM models updated metric: {e}")
