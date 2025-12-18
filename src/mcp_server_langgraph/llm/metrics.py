"""
LLM service business metrics.

Prometheus metrics for LLM operations:
- llm_token_usage_total: Token usage by model and type (prompt, completion)
- llm_request_duration_seconds: LLM request latency histogram
- llm_requests_total: Total LLM requests by model and status

These metrics are scraped by Alloy and displayed in the LLM Performance Grafana dashboard.
"""

import logging
import re
from typing import Any

# =============================================================================
# BOUNDED LABEL CONSTANTS
# =============================================================================
# These constants define the allowed values for metric labels to prevent
# cardinality explosion. Unknown values are mapped to "other".


logger = logging.getLogger(__name__)
BOUNDED_OPERATIONS: frozenset[str] = frozenset(
    {
        "chat",
        "completion",
        "embedding",
        "streaming",
        "tool_call",
        "function_call",
        "other",
    }
)

BOUNDED_STATUSES: frozenset[str] = frozenset(
    {
        "success",
        "error",
        "timeout",
        "rate_limited",
        "cancelled",
        "fallback",
        "other",
    }
)

# Model family patterns for bounded labels
# Maps regex patterns to normalized model family names
_MODEL_FAMILY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # OpenAI GPT models
    (re.compile(r"^gpt-4o", re.IGNORECASE), "gpt-4o"),
    (re.compile(r"^gpt-4", re.IGNORECASE), "gpt-4"),
    (re.compile(r"^gpt-3\.5", re.IGNORECASE), "gpt-3.5"),
    (re.compile(r"^gpt-5", re.IGNORECASE), "gpt-5"),
    (re.compile(r"^o1", re.IGNORECASE), "o1"),
    (re.compile(r"^o3", re.IGNORECASE), "o3"),
    # Anthropic Claude 4 models (new naming convention)
    (re.compile(r"claude-opus-4", re.IGNORECASE), "claude-4-opus"),
    (re.compile(r"claude-sonnet-4", re.IGNORECASE), "claude-4-sonnet"),
    (re.compile(r"claude-haiku-4", re.IGNORECASE), "claude-4-haiku"),
    # Anthropic Claude 3.5 models
    (re.compile(r"claude-3-5-sonnet", re.IGNORECASE), "claude-3.5-sonnet"),
    (re.compile(r"claude-3-5-haiku", re.IGNORECASE), "claude-3.5-haiku"),
    (re.compile(r"claude-3-5-opus", re.IGNORECASE), "claude-3.5-opus"),
    # Anthropic Claude 3 models
    (re.compile(r"claude-3-opus", re.IGNORECASE), "claude-3-opus"),
    (re.compile(r"claude-3-sonnet", re.IGNORECASE), "claude-3-sonnet"),
    (re.compile(r"claude-3-haiku", re.IGNORECASE), "claude-3-haiku"),
    # Google Gemini models
    (re.compile(r"gemini-2\.0-flash", re.IGNORECASE), "gemini-2.0-flash"),
    (re.compile(r"gemini-2\.0-pro", re.IGNORECASE), "gemini-2.0-pro"),
    (re.compile(r"gemini-1\.5-flash", re.IGNORECASE), "gemini-1.5-flash"),
    (re.compile(r"gemini-1\.5-pro", re.IGNORECASE), "gemini-1.5-pro"),
    (re.compile(r"gemini-pro", re.IGNORECASE), "gemini-pro"),
]


def get_model_family(model: str | None) -> str:
    """
    Extract bounded model family from model name.

    Maps detailed model names to bounded model families to prevent
    metric label cardinality explosion.

    Args:
        model: Full model name (e.g., "gpt-4-turbo-preview", "claude-3-opus-20240229")

    Returns:
        Bounded model family (e.g., "gpt-4", "claude-3-opus") or "other" for unknown models
    """
    if not model:
        return "unknown"

    for pattern, family in _MODEL_FAMILY_PATTERNS:
        if pattern.search(model):
            return family

    return "other"


def normalize_operation(operation: str) -> str:
    """
    Normalize operation to bounded value.

    Args:
        operation: Raw operation name

    Returns:
        Bounded operation name or "other" if not in allowed set
    """
    if operation in BOUNDED_OPERATIONS:
        return operation
    return "other"


def normalize_status(status: str) -> str:
    """
    Normalize status to bounded value.

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
_llm_token_usage_total: Any = None
_llm_request_duration: Any = None
_llm_requests_total: Any = None


def _init_metrics() -> bool:
    """Initialize LLM metrics lazily."""
    global _metrics_available  # noqa: PLW0603
    global _llm_token_usage_total  # noqa: PLW0603
    global _llm_request_duration  # noqa: PLW0603
    global _llm_requests_total  # noqa: PLW0603

    if _metrics_available is not None:
        return _metrics_available

    try:
        from prometheus_client import Counter, Histogram

        _llm_token_usage_total = Counter(
            "llm_tokens_total",  # Renamed to avoid conflict with cost_tracker.py
            "Total tokens used by model and type",
            ["model", "token_type"],  # token_type: prompt, completion
        )

        _llm_request_duration = Histogram(
            "llm_request_duration_seconds",
            "LLM request duration in seconds",
            ["model", "provider"],
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
        )

        _llm_requests_total = Counter(
            "llm_requests_total",
            "Total number of LLM requests",
            ["model", "provider", "status"],  # status: success, error, fallback
        )

        _metrics_available = True
        return True

    except ImportError:
        _metrics_available = False
        return False


# Initialize on module load
_init_metrics()


def record_llm_token_usage(model: str, prompt_tokens: int, completion_tokens: int) -> None:
    """
    Record LLM token usage.

    Args:
        model: Model name (e.g., "gpt-5", "gemini-2.5-flash")
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
    """
    if not _metrics_available:
        return

    try:
        if _llm_token_usage_total:
            # S106: token_type is a metrics label, not a password
            _llm_token_usage_total.labels(model=model, token_type="prompt").inc(prompt_tokens)  # noqa: S106
            _llm_token_usage_total.labels(model=model, token_type="completion").inc(completion_tokens)  # noqa: S106
    except Exception as e:
        logger.debug("Operation failed: %s", e)


def record_llm_request_duration(model: str, duration_ms: float, provider: str = "unknown") -> None:
    """
    Record LLM request duration.

    Args:
        model: Model name
        duration_ms: Duration in milliseconds
        provider: LLM provider (e.g., "openai", "anthropic", "google")
    """
    if not _metrics_available:
        return

    try:
        if _llm_request_duration:
            # Convert ms to seconds for histogram
            duration_seconds = duration_ms / 1000.0
            _llm_request_duration.labels(model=model, provider=provider).observe(duration_seconds)
    except Exception as e:
        logger.debug("Operation failed: %s", e)


def record_llm_request(model: str, provider: str, status: str) -> None:
    """
    Record an LLM request.

    Args:
        model: Model name
        provider: LLM provider
        status: Request status ("success", "error", "fallback")
    """
    if not _metrics_available:
        return

    try:
        if _llm_requests_total:
            _llm_requests_total.labels(model=model, provider=provider, status=status).inc()
    except Exception as e:
        logger.debug("Operation failed: %s", e)
