"""
LLM service business metrics.

Prometheus metrics for LLM operations:
- llm_token_usage_total: Token usage by model and type (prompt, completion)
- llm_request_duration_seconds: LLM request latency histogram
- llm_requests_total: Total LLM requests by model and status

These metrics are scraped by Alloy and displayed in the LLM Performance Grafana dashboard.
"""

from typing import Any

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
    except Exception:
        pass  # Don't let metrics failures break the app


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
    except Exception:
        pass


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
    except Exception:
        pass
