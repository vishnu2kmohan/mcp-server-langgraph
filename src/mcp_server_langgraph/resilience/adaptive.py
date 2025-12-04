"""
Adaptive bulkhead with self-tuning concurrency limits.

Implements AIMD (Additive Increase Multiplicative Decrease) algorithm to
automatically adjust concurrency limits based on observed error rates.

Key features:
- Monitors 429/529 error rates in sliding window
- Multiplicatively decreases limit on errors (fast decrease)
- Additively increases limit on success streaks (slow recovery)
- Respects floor and ceiling limits

This is similar to TCP congestion control (Jacobson 1988) and provides
self-healing behavior for rate limit issues.

See ADR-0026 for design rationale.
"""

import asyncio
import logging
import threading
import time
from collections import deque

from opentelemetry import trace

from mcp_server_langgraph.resilience.config import get_provider_limit

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


# =============================================================================
# Adaptive Bulkhead Configuration
# =============================================================================

# Default AIMD parameters
DEFAULT_MIN_LIMIT = 2
DEFAULT_MAX_LIMIT = 50
DEFAULT_INITIAL_LIMIT = 10
DEFAULT_ERROR_THRESHOLD = 0.1  # 10% error rate triggers decrease
DEFAULT_DECREASE_FACTOR = 0.75  # Reduce by 25% on error
DEFAULT_INCREASE_AMOUNT = 1  # Add 1 on success streak
DEFAULT_SUCCESS_STREAK_THRESHOLD = 10  # 10 successes to trigger increase
DEFAULT_WINDOW_SIZE = 100  # Sliding window for error rate calculation


# =============================================================================
# Adaptive Bulkhead Implementation
# =============================================================================


class AdaptiveBulkhead:
    """
    Self-tuning bulkhead with AIMD algorithm.

    Automatically adjusts concurrency limit based on error rates:
    - On error: limit = max(min_limit, limit * decrease_factor)
    - On success streak: limit = min(max_limit, limit + increase_amount)

    Attributes:
        min_limit: Floor for concurrency limit
        max_limit: Ceiling for concurrency limit
        current_limit: Current concurrency limit
        error_threshold: Error rate that triggers decrease

    Example:
        >>> bulkhead = AdaptiveBulkhead(min_limit=5, max_limit=50, initial_limit=10)
        >>> semaphore = bulkhead.get_semaphore()
        >>> async with semaphore:
        ...     try:
        ...         result = await call_api()
        ...         bulkhead.record_success()
        ...     except RateLimitError:
        ...         bulkhead.record_error()
    """

    def __init__(
        self,
        min_limit: int = DEFAULT_MIN_LIMIT,
        max_limit: int = DEFAULT_MAX_LIMIT,
        initial_limit: int | None = None,
        error_threshold: float = DEFAULT_ERROR_THRESHOLD,
        decrease_factor: float = DEFAULT_DECREASE_FACTOR,
        increase_amount: int = DEFAULT_INCREASE_AMOUNT,
        success_streak_threshold: int = DEFAULT_SUCCESS_STREAK_THRESHOLD,
        window_size: int = DEFAULT_WINDOW_SIZE,
    ):
        """
        Initialize adaptive bulkhead.

        Args:
            min_limit: Minimum concurrency limit (floor)
            max_limit: Maximum concurrency limit (ceiling)
            initial_limit: Starting limit (defaults to (min + max) / 2)
            error_threshold: Error rate that triggers limit decrease
            decrease_factor: Multiplicative decrease factor (0-1)
            increase_amount: Additive increase on success streak
            success_streak_threshold: Successes needed to trigger increase
            window_size: Size of sliding window for error rate
        """
        self.min_limit = min_limit
        self.max_limit = max_limit
        self.error_threshold = error_threshold
        self.decrease_factor = decrease_factor
        self.increase_amount = increase_amount
        self.success_streak_threshold = success_streak_threshold
        self.window_size = window_size

        # Set initial limit
        if initial_limit is not None:
            self._current_limit = float(max(min_limit, min(max_limit, initial_limit)))
        else:
            self._current_limit = float((min_limit + max_limit) // 2)

        # Tracking state
        self._success_streak = 0
        self._samples: deque[bool] = deque(maxlen=window_size)  # True = success, False = error
        self._lock = threading.Lock()
        self._semaphore: asyncio.Semaphore | None = None
        self._last_update = time.monotonic()

        logger.info(
            "Initialized adaptive bulkhead",
            extra={
                "min_limit": min_limit,
                "max_limit": max_limit,
                "initial_limit": self._current_limit,
                "error_threshold": error_threshold,
            },
        )

    @property
    def current_limit(self) -> int:
        """Get current concurrency limit (integer)."""
        return int(self._current_limit)

    def record_success(self) -> None:
        """Record a successful operation."""
        with self._lock:
            self._samples.append(True)
            self._success_streak += 1

            # Check if we should increase limit
            if self._success_streak >= self.success_streak_threshold:
                old_limit = self._current_limit
                self._current_limit = min(self.max_limit, self._current_limit + self.increase_amount)
                self._success_streak = 0  # Reset streak after increase
                self._invalidate_semaphore()

                if self._current_limit > old_limit:
                    logger.info(
                        f"Adaptive bulkhead increased limit: {old_limit:.0f} -> {self._current_limit:.0f}",
                        extra={
                            "old_limit": old_limit,
                            "new_limit": self._current_limit,
                            "reason": "success_streak",
                        },
                    )

    def record_error(self) -> None:
        """Record an error (429/529 or similar)."""
        with self._lock:
            self._samples.append(False)
            self._success_streak = 0  # Reset streak on error

            # Decrease limit multiplicatively
            old_limit = self._current_limit
            self._current_limit = max(self.min_limit, self._current_limit * self.decrease_factor)
            self._invalidate_semaphore()

            logger.warning(
                f"Adaptive bulkhead decreased limit: {old_limit:.0f} -> {self._current_limit:.0f}",
                extra={
                    "old_limit": old_limit,
                    "new_limit": self._current_limit,
                    "reason": "error",
                },
            )

    def get_error_rate(self) -> float:
        """
        Get current error rate from sliding window.

        Returns:
            Error rate as float (0.0 - 1.0)
        """
        with self._lock:
            if not self._samples:
                return 0.0
            errors = sum(1 for s in self._samples if not s)
            return errors / len(self._samples)

    def get_semaphore(self) -> asyncio.Semaphore:
        """
        Get asyncio semaphore with current limit.

        Returns a new semaphore if limit has changed since last call.

        Returns:
            asyncio.Semaphore configured for current limit
        """
        with self._lock:
            if self._semaphore is None or self._needs_new_semaphore():
                self._semaphore = asyncio.Semaphore(self.current_limit)
                self._last_update = time.monotonic()
            return self._semaphore

    def _invalidate_semaphore(self) -> None:
        """Mark semaphore as needing update."""
        self._semaphore = None

    def _needs_new_semaphore(self) -> bool:
        """Check if semaphore needs to be recreated."""
        if self._semaphore is None:
            return True
        # Check if limit has changed
        return self._semaphore._value != self.current_limit

    def get_stats(self) -> dict[str, int | float]:
        """Get current bulkhead statistics."""
        with self._lock:
            return {
                "current_limit": self.current_limit,
                "min_limit": self.min_limit,
                "max_limit": self.max_limit,
                "error_rate": self.get_error_rate(),
                "success_streak": self._success_streak,
                "samples_count": len(self._samples),
            }


# =============================================================================
# Provider Adaptive Bulkhead Factory
# =============================================================================

_provider_adaptive_bulkheads: dict[str, AdaptiveBulkhead] = {}
_bulkhead_lock = threading.Lock()


def get_provider_adaptive_bulkhead(provider: str) -> AdaptiveBulkhead:
    """
    Get or create an adaptive bulkhead for a specific LLM provider.

    Uses provider-specific limits from configuration as initial/max values.

    Args:
        provider: LLM provider name (e.g., "anthropic", "openai")

    Returns:
        AdaptiveBulkhead configured for the provider
    """
    with _bulkhead_lock:
        if provider in _provider_adaptive_bulkheads:
            return _provider_adaptive_bulkheads[provider]

        # Get provider-specific limits
        base_limit = get_provider_limit(provider)

        # Configure adaptive bulkhead based on provider limits
        bulkhead = AdaptiveBulkhead(
            min_limit=max(2, base_limit // 4),  # Floor at 25% of base
            max_limit=base_limit * 2,  # Ceiling at 200% of base
            initial_limit=base_limit,  # Start at base limit
            error_threshold=0.1,  # 10% error rate triggers decrease
        )

        _provider_adaptive_bulkheads[provider] = bulkhead

        logger.info(
            f"Created adaptive bulkhead for {provider}",
            extra={
                "provider": provider,
                "initial_limit": base_limit,
                "min_limit": bulkhead.min_limit,
                "max_limit": bulkhead.max_limit,
            },
        )

        return bulkhead


def reset_all_adaptive_bulkheads() -> None:
    """
    Reset all adaptive bulkheads (for testing).

    Warning: Only use for testing! In production, bulkheads should not be reset.
    """
    with _bulkhead_lock:
        _provider_adaptive_bulkheads.clear()
        logger.warning("All adaptive bulkheads reset (testing only)")


def get_all_adaptive_bulkhead_stats() -> dict[str, dict[str, int | float]]:
    """
    Get statistics for all adaptive bulkheads.

    Returns:
        Dict mapping provider to bulkhead stats
    """
    with _bulkhead_lock:
        return {provider: bulkhead.get_stats() for provider, bulkhead in _provider_adaptive_bulkheads.items()}
