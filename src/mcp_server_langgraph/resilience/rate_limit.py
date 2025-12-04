"""
Token bucket rate limiter for pre-emptive rate limiting.

Implements the token bucket algorithm to limit request rates before hitting
upstream provider limits. This provides smoother request distribution and
prevents 429/529 errors.

Key features:
- Burst capacity: Allows short bursts up to bucket capacity
- Steady rate: Limits sustained throughput to refill rate
- Async support: Non-blocking acquire with wait capability
- Provider-aware: Different limits per LLM provider

See ADR-0026 for design rationale.

Reference: https://en.wikipedia.org/wiki/Token_bucket
"""

import asyncio
import functools
import logging
import os
import threading
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

P = ParamSpec("P")
T = TypeVar("T")


# =============================================================================
# Provider Rate Limit Configuration
# =============================================================================
# These are RPM (requests per minute) limits based on provider documentation.
# Formula: refill_rate = RPM / 60 (converts to requests per second)
# Burst capacity = refill_rate * typical_request_duration (allows ~10s worth of requests)

PROVIDER_RATE_LIMITS: dict[str, dict[str, float]] = {
    # Anthropic Claude (direct API): Tier 1 default (50 RPM)
    # Higher tiers can be set via RATE_LIMIT_ANTHROPIC_RPM env var
    "anthropic": {"rpm": 50.0, "burst_seconds": 10.0},
    # OpenAI GPT-4: Moderate tier (~500 RPM)
    "openai": {"rpm": 500.0, "burst_seconds": 10.0},
    # Google Gemini via AI Studio
    "google": {"rpm": 300.0, "burst_seconds": 10.0},
    # Google Vertex AI - Gemini models (vishnu-sandbox-20250310):
    # Gemini 2.5 Flash/Pro: 3.4M TPM → ~1400 RPM (2500 tokens/req)
    # Use 600 RPM to leave headroom
    "vertex_ai": {"rpm": 600.0, "burst_seconds": 15.0},
    # Anthropic Claude via Vertex AI (MaaS) - vishnu-sandbox-20250310:
    # Claude Opus 4.5: 1,200 RPM, Sonnet 4.5: higher, Haiku 4.5: higher
    # Use Opus 4.5 as baseline (most restrictive 4.5 model)
    "vertex_ai_anthropic": {"rpm": 1000.0, "burst_seconds": 10.0},
    # AWS Bedrock: Claude Opus is most restrictive (50 RPM)
    "bedrock": {"rpm": 50.0, "burst_seconds": 10.0},
    # Ollama: Local model, no upstream limits
    "ollama": {"rpm": 1000.0, "burst_seconds": 30.0},
    # Azure OpenAI: Similar to OpenAI
    "azure": {"rpm": 500.0, "burst_seconds": 10.0},
}

DEFAULT_RATE_LIMIT: dict[str, float] = {"rpm": 60.0, "burst_seconds": 10.0}


def get_provider_rate_config(provider: str) -> dict[str, float]:
    """
    Get rate limit configuration for a provider.

    Checks environment variable first (RATE_LIMIT_<PROVIDER>_RPM),
    then falls back to default for that provider.

    Args:
        provider: Provider name (e.g., "anthropic", "openai")

    Returns:
        Dict with 'rpm' and 'burst_seconds' keys
    """
    # Check for environment variable override
    env_var = f"RATE_LIMIT_{provider.upper()}_RPM"
    env_value = os.getenv(env_var)

    config = PROVIDER_RATE_LIMITS.get(provider, DEFAULT_RATE_LIMIT).copy()

    if env_value is not None:
        try:
            config["rpm"] = float(env_value)
        except ValueError:
            logger.warning(
                f"Invalid {env_var}={env_value}, using default",
                extra={"env_var": env_var, "invalid_value": env_value},
            )

    return config


# =============================================================================
# Token Bucket Implementation
# =============================================================================


class TokenBucket:
    """
    Thread-safe token bucket rate limiter.

    The token bucket algorithm allows bursting up to a maximum capacity,
    then limits sustained throughput to the refill rate.

    Attributes:
        capacity: Maximum number of tokens in bucket (burst limit)
        refill_rate: Tokens added per second (sustained rate)
        tokens: Current number of available tokens

    Example:
        >>> bucket = TokenBucket(capacity=10, refill_rate=1.0)
        >>> if bucket.try_acquire():
        ...     await call_api()
        >>> # Or with async waiting:
        >>> await bucket.acquire()  # Waits if needed
        >>> await call_api()
    """

    def __init__(self, capacity: float, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum tokens (burst capacity)
            refill_rate: Tokens per second (sustained rate)
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._tokens = capacity  # Start full
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    @property
    def tokens(self) -> float:
        """Get current token count (after refill)."""
        self._refill()
        return self._tokens

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._last_refill = now

            # Add tokens based on elapsed time
            self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)

    def try_acquire(self, tokens: float = 1) -> bool:
        """
        Try to acquire tokens without blocking.

        Args:
            tokens: Number of tokens to acquire (default: 1)

        Returns:
            True if tokens acquired, False otherwise
        """
        # Can never acquire more than capacity
        if tokens > self.capacity:
            return False

        self._refill()

        with self._lock:
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    async def acquire(self, tokens: float = 1, timeout: float | None = None) -> None:
        """
        Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire (default: 1)
            timeout: Maximum time to wait in seconds (None = wait forever)

        Raises:
            asyncio.TimeoutError: If cannot acquire within timeout
            ValueError: If tokens > capacity
        """
        if tokens > self.capacity:
            raise ValueError(f"Cannot acquire {tokens} tokens (capacity: {self.capacity})")

        start = time.monotonic()

        while True:
            if self.try_acquire(tokens):
                return

            # Calculate wait time for enough tokens
            self._refill()
            tokens_needed = tokens - self._tokens
            wait_time = tokens_needed / self.refill_rate

            # Check timeout
            if timeout is not None:
                elapsed = time.monotonic() - start
                remaining = timeout - elapsed
                if remaining <= 0:
                    raise TimeoutError(f"Could not acquire {tokens} tokens within {timeout}s")
                wait_time = min(wait_time, remaining)

            # Wait for tokens to refill
            await asyncio.sleep(max(0.01, wait_time))  # Min 10ms to avoid busy loop


# =============================================================================
# Provider Token Bucket Factory
# =============================================================================

_provider_token_buckets: dict[str, TokenBucket] = {}
_bucket_lock = threading.Lock()


def get_provider_token_bucket(provider: str) -> TokenBucket:
    """
    Get or create a token bucket for a specific LLM provider.

    Uses provider-specific rate limits from configuration or environment.

    Args:
        provider: LLM provider name (e.g., "anthropic", "openai")

    Returns:
        TokenBucket configured for the provider's rate limits
    """
    with _bucket_lock:
        if provider in _provider_token_buckets:
            return _provider_token_buckets[provider]

        config = get_provider_rate_config(provider)
        rpm = config["rpm"]
        burst_seconds = config["burst_seconds"]

        # Convert RPM to tokens per second
        refill_rate = rpm / 60.0

        # Burst capacity = refill_rate * burst_seconds
        capacity = refill_rate * burst_seconds

        bucket = TokenBucket(capacity=capacity, refill_rate=refill_rate)
        _provider_token_buckets[provider] = bucket

        logger.info(
            f"Created token bucket for {provider}",
            extra={
                "provider": provider,
                "rpm": rpm,
                "refill_rate": refill_rate,
                "capacity": capacity,
            },
        )

        return bucket


def reset_all_token_buckets() -> None:
    """
    Reset all token buckets (for testing).

    Warning: Only use for testing! In production, buckets should not be reset.
    """
    with _bucket_lock:
        _provider_token_buckets.clear()
        logger.warning("All token buckets reset (testing only)")


# =============================================================================
# Rate Limiter Decorator
# =============================================================================


def rate_limited(
    provider: str | None = None,
    capacity: float | None = None,
    refill_rate: float | None = None,
    timeout: float | None = 30.0,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to rate-limit a function using token bucket.

    Args:
        provider: LLM provider name (uses provider-specific limits)
        capacity: Override bucket capacity (burst limit)
        refill_rate: Override refill rate (tokens/sec)
        timeout: Max wait time for tokens (None = wait forever)

    Usage:
        @rate_limited(provider="anthropic")
        async def call_claude(prompt: str) -> str:
            return await client.generate(prompt)

        # Or with explicit limits:
        @rate_limited(capacity=5, refill_rate=1.0)
        async def my_function():
            pass
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Get or create bucket
        if provider:
            bucket = get_provider_token_bucket(provider)
        elif capacity is not None and refill_rate is not None:
            # Create a custom bucket for this decorator
            bucket = TokenBucket(capacity=capacity, refill_rate=refill_rate)
        else:
            raise ValueError("Must specify either 'provider' or both 'capacity' and 'refill_rate'")

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            with tracer.start_as_current_span(
                f"rate_limit.{func.__name__}",
                attributes={
                    "rate_limit.provider": provider or "custom",
                    "rate_limit.capacity": bucket.capacity,
                    "rate_limit.refill_rate": bucket.refill_rate,
                    "rate_limit.tokens_available": bucket.tokens,
                },
            ) as span:
                # Acquire token (may wait)
                await bucket.acquire(timeout=timeout)
                span.set_attribute("rate_limit.acquired", True)

                return await func(*args, **kwargs)  # type: ignore[misc, no-any-return]

        # Only works with async functions
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(f"@rate_limited can only be applied to async functions, got {func.__name__}")

        return async_wrapper  # type: ignore[return-value]

    return decorator
