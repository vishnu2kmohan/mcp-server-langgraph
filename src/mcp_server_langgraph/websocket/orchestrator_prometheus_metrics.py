"""
Prometheus-compatible orchestrator status metrics.

These metrics are exposed via the /metrics endpoint for Alloy/Prometheus scraping.
They track orchestrator status, task lifecycle, and queue depth.

Metrics:
- orchestrator_ws_subscribers: Active WebSocket subscriber count (Gauge)
- orchestrator_active_tasks: Currently processing task count (Gauge)
- orchestrator_queue_depth: Pending task queue depth (Gauge)
- orchestrator_tasks_started_total: Total tasks started (Counter)
- orchestrator_tasks_completed_total: Total tasks completed successfully (Counter)
- orchestrator_tasks_failed_total: Total tasks failed (Counter)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Lazy-load prometheus_client to handle missing dependency
_metrics_available: bool | None = None
_orchestrator_ws_subscribers: Any = None
_orchestrator_active_tasks: Any = None
_orchestrator_queue_depth: Any = None
_orchestrator_tasks_started_total: Any = None
_orchestrator_tasks_completed_total: Any = None
_orchestrator_tasks_failed_total: Any = None


def _init_metrics() -> bool:
    """Initialize Prometheus orchestrator metrics lazily."""
    global _metrics_available
    global _orchestrator_ws_subscribers
    global _orchestrator_active_tasks
    global _orchestrator_queue_depth
    global _orchestrator_tasks_started_total
    global _orchestrator_tasks_completed_total
    global _orchestrator_tasks_failed_total

    if _metrics_available is not None:
        return _metrics_available

    try:
        from prometheus_client import Counter, Gauge

        # Subscriber gauge
        _orchestrator_ws_subscribers = Gauge(
            "orchestrator_ws_subscribers",
            "Active WebSocket subscriber count for orchestrator status",
        )

        # Active tasks gauge
        _orchestrator_active_tasks = Gauge(
            "orchestrator_active_tasks",
            "Currently processing task count",
            ["category"],  # ux, session, conversation, canvas, etc.
        )

        # Queue depth gauge
        _orchestrator_queue_depth = Gauge(
            "orchestrator_queue_depth",
            "Pending task queue depth",
        )

        # Task lifecycle counters
        _orchestrator_tasks_started_total = Counter(
            "orchestrator_tasks_started_total",
            "Total tasks started",
            ["category", "task_type"],
        )

        _orchestrator_tasks_completed_total = Counter(
            "orchestrator_tasks_completed_total",
            "Total tasks completed successfully",
            ["category", "task_type"],
        )

        _orchestrator_tasks_failed_total = Counter(
            "orchestrator_tasks_failed_total",
            "Total tasks failed",
            ["category", "task_type", "reason"],
        )

        _metrics_available = True
        logger.debug("Prometheus orchestrator metrics initialized successfully")

    except ImportError:
        _metrics_available = False
        logger.debug("prometheus_client not available, orchestrator metrics disabled")
    except Exception as e:
        _metrics_available = False
        logger.warning(f"Failed to initialize orchestrator metrics: {e}")

    return _metrics_available


def record_subscriber_change(delta: int) -> None:
    """Record a change in subscriber count.

    Args:
        delta: The change in subscribers (+1 for new, -1 for disconnected)
    """
    if not _init_metrics():
        return

    try:
        if delta > 0:
            _orchestrator_ws_subscribers.inc(delta)
        elif delta < 0:
            _orchestrator_ws_subscribers.dec(abs(delta))
    except Exception as e:
        logger.debug(f"Failed to record subscriber change: {e}")


def record_task_started(category: str, task_type: str) -> None:
    """Record a task started event.

    Args:
        category: Task category (ux, session, conversation, etc.)
        task_type: Type of task (persona_analysis, error_analysis, etc.)
    """
    if not _init_metrics():
        return

    try:
        _orchestrator_tasks_started_total.labels(
            category=category,
            task_type=task_type,
        ).inc()
        _orchestrator_active_tasks.labels(category=category).inc()
    except Exception as e:
        logger.debug(f"Failed to record task started: {e}")


def record_task_completed(category: str, task_type: str) -> None:
    """Record a task completed event.

    Args:
        category: Task category (ux, session, conversation, etc.)
        task_type: Type of task (persona_analysis, error_analysis, etc.)
    """
    if not _init_metrics():
        return

    try:
        _orchestrator_tasks_completed_total.labels(
            category=category,
            task_type=task_type,
        ).inc()
        _orchestrator_active_tasks.labels(category=category).dec()
    except Exception as e:
        logger.debug(f"Failed to record task completed: {e}")


def record_task_failed(category: str, task_type: str, reason: str = "unknown") -> None:
    """Record a task failed event.

    Args:
        category: Task category (ux, session, conversation, etc.)
        task_type: Type of task (persona_analysis, error_analysis, etc.)
        reason: Failure reason (timeout, rate_limit, internal_error, etc.)
    """
    if not _init_metrics():
        return

    try:
        _orchestrator_tasks_failed_total.labels(
            category=category,
            task_type=task_type,
            reason=reason,
        ).inc()
        _orchestrator_active_tasks.labels(category=category).dec()
    except Exception as e:
        logger.debug(f"Failed to record task failed: {e}")


def set_queue_depth(depth: int) -> None:
    """Set the current queue depth.

    Args:
        depth: Current number of tasks waiting in queue
    """
    if not _init_metrics():
        return

    try:
        _orchestrator_queue_depth.set(depth)
    except Exception as e:
        logger.debug(f"Failed to set queue depth: {e}")


def set_active_tasks(count: int) -> None:
    """Set the total active task count.

    Note: This sets an aggregate count. For per-category tracking,
    use record_task_started/completed/failed.

    Args:
        count: Current number of active tasks
    """
    if not _init_metrics():
        return

    try:
        # Since we have per-category gauges, we use a labeled gauge
        # For aggregate, we use a special "total" category
        _orchestrator_active_tasks.labels(category="total").set(count)
    except Exception as e:
        logger.debug(f"Failed to set active tasks: {e}")
