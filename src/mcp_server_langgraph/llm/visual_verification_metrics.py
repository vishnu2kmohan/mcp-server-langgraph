"""
Visual Verification metrics instrumentation.

Prometheus metrics for visual verification operations:
- visual_verification_requests_total: Total visual verification requests by status
- visual_verification_duration_seconds: Visual verification latency histogram
- visual_verification_score: Visual verification score distribution
- visual_verification_urls_total: Total URLs verified

These metrics are scraped by Alloy and displayed in Grafana dashboards.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# =============================================================================
# BOUNDED LABEL CONSTANTS
# =============================================================================
# These constants define the allowed values for metric labels to prevent
# cardinality explosion. Unknown values are mapped to "other".

BOUNDED_STATUSES: frozenset[str] = frozenset(
    {
        "success",
        "failed",
        "screenshot_error",
        "timeout",
        "skipped",
        "other",
    }
)


def normalize_verification_status(status: str) -> str:
    """
    Normalize verification status to bounded value.

    Args:
        status: Raw status name

    Returns:
        Bounded status name or "other" if not in allowed set
    """
    if status in BOUNDED_STATUSES:
        return status
    return "other"


# Lazy-load prometheus_client to handle missing dependency
_metrics_available: bool | None = None
_visual_verification_requests_total: Any = None
_visual_verification_duration: Any = None
_visual_verification_score: Any = None
_visual_verification_urls_total: Any = None
_visual_verification_retries_total: Any = None
_screenshot_cache_hits_total: Any = None
_screenshot_cache_misses_total: Any = None


def _init_metrics() -> bool:
    """Initialize visual verification metrics lazily."""
    global _metrics_available  # noqa: PLW0603
    global _visual_verification_requests_total  # noqa: PLW0603
    global _visual_verification_duration  # noqa: PLW0603
    global _visual_verification_score  # noqa: PLW0603
    global _visual_verification_urls_total  # noqa: PLW0603
    global _visual_verification_retries_total  # noqa: PLW0603
    global _screenshot_cache_hits_total  # noqa: PLW0603
    global _screenshot_cache_misses_total  # noqa: PLW0603

    if _metrics_available is not None:
        return _metrics_available

    try:
        from prometheus_client import Counter, Histogram

        _visual_verification_requests_total = Counter(
            "visual_verification_requests_total",
            "Total visual verification requests by status",
            ["status"],  # status: success, failed, screenshot_error, timeout
        )

        _visual_verification_duration = Histogram(
            "visual_verification_duration_seconds",
            "Visual verification duration in seconds",
            [],  # No labels to keep cardinality low
            buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 15.0, 30.0, 60.0),
        )

        _visual_verification_score = Histogram(
            "visual_verification_score",
            "Visual verification score distribution (0.0-1.0)",
            [],  # No labels to keep cardinality low
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
        )

        _visual_verification_urls_total = Counter(
            "visual_verification_urls_total",
            "Total URLs verified through visual verification",
            [],  # No labels to keep cardinality low
        )

        _visual_verification_retries_total = Counter(
            "visual_verification_retries_total",
            "Total visual verification retry attempts",
            ["operation"],  # operation: screenshot, llm
        )

        _screenshot_cache_hits_total = Counter(
            "screenshot_cache_hits_total",
            "Total screenshot cache hits",
            [],  # No labels to keep cardinality low
        )

        _screenshot_cache_misses_total = Counter(
            "screenshot_cache_misses_total",
            "Total screenshot cache misses",
            [],  # No labels to keep cardinality low
        )

        _metrics_available = True
        return True

    except ImportError:
        _metrics_available = False
        return False


# Initialize on module load
_init_metrics()


def record_visual_verification_request(status: str) -> None:
    """
    Record a visual verification request.

    Args:
        status: Request status (success, failed, screenshot_error, timeout)
    """
    if not _metrics_available:
        return

    try:
        if _visual_verification_requests_total:
            normalized_status = normalize_verification_status(status)
            _visual_verification_requests_total.labels(status=normalized_status).inc()
    except Exception as e:
        logger.debug("Failed to record visual verification request metric: %s", e)


def record_visual_verification_duration(duration_ms: float) -> None:
    """
    Record visual verification duration.

    Args:
        duration_ms: Duration in milliseconds
    """
    if not _metrics_available:
        return

    try:
        if _visual_verification_duration:
            # Convert ms to seconds for histogram
            duration_seconds = duration_ms / 1000.0
            _visual_verification_duration.observe(duration_seconds)
    except Exception as e:
        logger.debug("Failed to record visual verification duration metric: %s", e)


def record_visual_verification_score(score: float) -> None:
    """
    Record visual verification score.

    Args:
        score: Verification score (0.0 to 1.0)
    """
    if not _metrics_available:
        return

    try:
        if _visual_verification_score:
            # Clamp score to valid range
            clamped_score = max(0.0, min(1.0, score))
            _visual_verification_score.observe(clamped_score)
    except Exception as e:
        logger.debug("Failed to record visual verification score metric: %s", e)


def record_visual_verification_urls(count: int) -> None:
    """
    Record number of URLs verified.

    Args:
        count: Number of URLs verified
    """
    if not _metrics_available:
        return

    try:
        if _visual_verification_urls_total:
            _visual_verification_urls_total.inc(count)
    except Exception as e:
        logger.debug("Failed to record visual verification URLs metric: %s", e)


def record_visual_verification_retry(operation: str) -> None:
    """
    Record a visual verification retry attempt.

    Args:
        operation: The operation being retried (screenshot, llm)
    """
    if not _metrics_available:
        return

    try:
        if _visual_verification_retries_total:
            # Bound operation to known values
            bounded_op = operation if operation in ("screenshot", "llm") else "other"
            _visual_verification_retries_total.labels(operation=bounded_op).inc()
    except Exception as e:
        logger.debug("Failed to record visual verification retry metric: %s", e)


def record_screenshot_cache_hit() -> None:
    """Record a screenshot cache hit."""
    if not _metrics_available:
        return

    try:
        if _screenshot_cache_hits_total:
            _screenshot_cache_hits_total.inc()
    except Exception as e:
        logger.debug("Failed to record screenshot cache hit metric: %s", e)


def record_screenshot_cache_miss() -> None:
    """Record a screenshot cache miss."""
    if not _metrics_available:
        return

    try:
        if _screenshot_cache_misses_total:
            _screenshot_cache_misses_total.inc()
    except Exception as e:
        logger.debug("Failed to record screenshot cache miss metric: %s", e)
