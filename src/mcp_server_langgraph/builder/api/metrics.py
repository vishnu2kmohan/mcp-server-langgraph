"""
Builder service business metrics.

Prometheus metrics for Builder workflow operations:
- builder_code_generation_total: Code generation requests
- builder_code_generation_duration_seconds: Code generation latency
- builder_validation_total: Workflow validation requests
- builder_import_total: Code import requests
- builder_workflows_total: Total workflow count

These metrics are scraped by Alloy and displayed in the Builder Grafana dashboard.
"""

from typing import Any

# Lazy-load prometheus_client to handle missing dependency
_metrics_available: bool | None = None
_builder_code_generation_total: Any = None
_builder_code_generation_duration: Any = None
_builder_validation_total: Any = None
_builder_import_total: Any = None
_builder_workflows_total: Any = None


def _init_metrics() -> bool:
    """Initialize Builder metrics lazily."""
    global _metrics_available  # noqa: PLW0603
    global _builder_code_generation_total  # noqa: PLW0603
    global _builder_code_generation_duration  # noqa: PLW0603
    global _builder_validation_total  # noqa: PLW0603
    global _builder_import_total  # noqa: PLW0603
    global _builder_workflows_total  # noqa: PLW0603

    if _metrics_available is not None:
        return _metrics_available

    try:
        from prometheus_client import Counter, Gauge, Histogram

        _builder_code_generation_total = Counter(
            "builder_code_generation_total",
            "Total number of code generation requests",
            ["status"],  # success, error
        )

        _builder_code_generation_duration = Histogram(
            "builder_code_generation_duration_seconds",
            "Code generation duration in seconds",
            buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        )

        _builder_validation_total = Counter(
            "builder_validation_total",
            "Total number of workflow validation requests",
            ["status", "result"],  # status: success/error, result: valid/invalid
        )

        _builder_import_total = Counter(
            "builder_import_total",
            "Total number of code import requests",
            ["status"],  # success, error
        )

        _builder_workflows_total = Gauge(
            "builder_workflows_total",
            "Total number of stored workflows",
        )

        _metrics_available = True
        return True

    except ImportError:
        _metrics_available = False
        return False


# Initialize on module load
_init_metrics()


def record_code_generation(status: str, duration: float) -> None:
    """
    Record a code generation request.

    Args:
        status: "success" or "error"
        duration: Duration in seconds
    """
    if not _metrics_available:
        return

    try:
        if _builder_code_generation_total:
            _builder_code_generation_total.labels(status=status).inc()
        if _builder_code_generation_duration:
            _builder_code_generation_duration.observe(duration)
    except Exception:
        pass  # Don't let metrics failures break the app


def record_validation(status: str, result: str) -> None:
    """
    Record a workflow validation request.

    Args:
        status: "success" or "error"
        result: "valid" or "invalid"
    """
    if not _metrics_available:
        return

    try:
        if _builder_validation_total:
            _builder_validation_total.labels(status=status, result=result).inc()
    except Exception:
        pass


def record_import(status: str) -> None:
    """
    Record a code import request.

    Args:
        status: "success" or "error"
    """
    if not _metrics_available:
        return

    try:
        if _builder_import_total:
            _builder_import_total.labels(status=status).inc()
    except Exception:
        pass


def set_workflows_count(count: int) -> None:
    """
    Set the current workflow count.

    Args:
        count: Number of stored workflows
    """
    if not _metrics_available:
        return

    try:
        if _builder_workflows_total:
            _builder_workflows_total.set(count)
    except Exception:
        pass
