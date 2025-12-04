"""
Unit tests for adaptive bulkhead.

TDD tests for self-tuning concurrency limits based on error rates:
- Monitors 429/529 error rates
- Automatically reduces concurrency when errors spike
- Slowly increases concurrency when errors subside
- Has configurable floor and ceiling

This implements an AIMD (Additive Increase Multiplicative Decrease) algorithm:
- Decrease: On error, reduce limit by factor (e.g., 0.75)
- Increase: On success, increase limit by constant (e.g., +1)
- Smoothing: Use exponential moving average for error rate

Reference: TCP congestion control (Jacobson 1988)
"""

import asyncio
import gc

import pytest

pytestmark = pytest.mark.unit


# =============================================================================
# Test Adaptive Bulkhead Configuration
# =============================================================================


@pytest.mark.xdist_group(name="adaptive_bulkhead")
class TestAdaptiveBulkheadConfig:
    """Test adaptive bulkhead configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_adaptive_bulkhead_init(self):
        """AdaptiveBulkhead should initialize with limits and thresholds."""
        from mcp_server_langgraph.resilience.adaptive import AdaptiveBulkhead

        bulkhead = AdaptiveBulkhead(
            min_limit=5,
            max_limit=50,
            initial_limit=10,
            error_threshold=0.1,  # 10% error rate triggers decrease
        )

        assert bulkhead.min_limit == 5
        assert bulkhead.max_limit == 50
        assert bulkhead.current_limit == 10
        assert bulkhead.error_threshold == 0.1

    @pytest.mark.unit
    def test_adaptive_bulkhead_defaults(self):
        """Should have sensible defaults."""
        from mcp_server_langgraph.resilience.adaptive import AdaptiveBulkhead

        bulkhead = AdaptiveBulkhead()

        assert bulkhead.min_limit >= 1
        assert bulkhead.max_limit >= bulkhead.min_limit
        assert bulkhead.min_limit <= bulkhead.current_limit <= bulkhead.max_limit


# =============================================================================
# Test AIMD Algorithm
# =============================================================================


@pytest.mark.xdist_group(name="adaptive_bulkhead")
class TestAdaptiveBulkheadAIMD:
    """Test Additive Increase Multiplicative Decrease algorithm."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_decrease_on_error(self):
        """Limit should decrease multiplicatively on error."""
        from mcp_server_langgraph.resilience.adaptive import AdaptiveBulkhead

        bulkhead = AdaptiveBulkhead(
            min_limit=5,
            max_limit=50,
            initial_limit=20,
            decrease_factor=0.75,
        )

        # Record an error
        bulkhead.record_error()

        # Limit should decrease by factor
        assert bulkhead.current_limit == pytest.approx(15, abs=1)  # 20 * 0.75 = 15

    @pytest.mark.unit
    def test_decrease_respects_floor(self):
        """Limit should not go below min_limit."""
        from mcp_server_langgraph.resilience.adaptive import AdaptiveBulkhead

        bulkhead = AdaptiveBulkhead(
            min_limit=5,
            max_limit=50,
            initial_limit=6,
            decrease_factor=0.5,
        )

        # Record error that would push below min
        bulkhead.record_error()

        # Should clamp to min_limit
        assert bulkhead.current_limit >= 5

    @pytest.mark.unit
    def test_increase_on_success(self):
        """Limit should increase additively on success streak."""
        from mcp_server_langgraph.resilience.adaptive import AdaptiveBulkhead

        bulkhead = AdaptiveBulkhead(
            min_limit=5,
            max_limit=50,
            initial_limit=10,
            increase_amount=1,
            success_streak_threshold=5,
        )

        # Record enough successes to trigger increase
        for _ in range(5):
            bulkhead.record_success()

        # Limit should increase
        assert bulkhead.current_limit >= 11

    @pytest.mark.unit
    def test_increase_respects_ceiling(self):
        """Limit should not exceed max_limit."""
        from mcp_server_langgraph.resilience.adaptive import AdaptiveBulkhead

        bulkhead = AdaptiveBulkhead(
            min_limit=5,
            max_limit=15,
            initial_limit=14,
            increase_amount=5,
            success_streak_threshold=1,
        )

        # Record success
        bulkhead.record_success()

        # Should clamp to max_limit
        assert bulkhead.current_limit <= 15

    @pytest.mark.unit
    def test_error_resets_success_streak(self):
        """Error should reset success streak counter."""
        from mcp_server_langgraph.resilience.adaptive import AdaptiveBulkhead

        bulkhead = AdaptiveBulkhead(
            min_limit=5,
            max_limit=50,
            initial_limit=10,
            success_streak_threshold=5,
        )

        # Build up success streak
        for _ in range(4):
            bulkhead.record_success()

        # Error resets the streak
        bulkhead.record_error()

        # Need 5 more successes to increase
        for _ in range(4):
            bulkhead.record_success()

        # Should not have increased yet (streak was reset)
        assert bulkhead.current_limit < 12  # Allow for error decrease


# =============================================================================
# Test Error Rate Tracking
# =============================================================================


@pytest.mark.xdist_group(name="adaptive_bulkhead")
class TestAdaptiveBulkheadErrorTracking:
    """Test error rate calculation and tracking."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_error_rate_calculation(self):
        """Error rate should be calculated correctly."""
        from mcp_server_langgraph.resilience.adaptive import AdaptiveBulkhead

        bulkhead = AdaptiveBulkhead(initial_limit=10, window_size=10)

        # 3 errors, 7 successes = 30% error rate
        for _ in range(7):
            bulkhead.record_success()
        for _ in range(3):
            bulkhead.record_error()

        error_rate = bulkhead.get_error_rate()
        assert error_rate == pytest.approx(0.3, abs=0.05)

    @pytest.mark.unit
    def test_sliding_window_discards_old_samples_keeps_recent(self):
        """Error rate should use sliding window, not all-time."""
        from mcp_server_langgraph.resilience.adaptive import AdaptiveBulkhead

        bulkhead = AdaptiveBulkhead(initial_limit=10, window_size=5)

        # Old errors (will fall out of window)
        for _ in range(5):
            bulkhead.record_error()

        # New successes (will be in window)
        for _ in range(5):
            bulkhead.record_success()

        # Error rate should be low (only recent samples count)
        error_rate = bulkhead.get_error_rate()
        assert error_rate < 0.2  # Recent samples are all successes


# =============================================================================
# Test Semaphore Integration
# =============================================================================


@pytest.mark.xdist_group(name="adaptive_bulkhead")
class TestAdaptiveBulkheadSemaphore:
    """Test integration with asyncio semaphore."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        """Semaphore should limit concurrent operations."""
        from mcp_server_langgraph.resilience.adaptive import AdaptiveBulkhead

        bulkhead = AdaptiveBulkhead(initial_limit=2)
        semaphore = bulkhead.get_semaphore()

        concurrent = 0
        max_concurrent = 0

        async def work():
            nonlocal concurrent, max_concurrent
            async with semaphore:
                concurrent += 1
                max_concurrent = max(max_concurrent, concurrent)
                await asyncio.sleep(0.01)
                concurrent -= 1

        # Start 5 concurrent tasks but limit is 2
        await asyncio.gather(*[work() for _ in range(5)])

        # Max concurrent should be limited
        assert max_concurrent <= 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_semaphore_updates_on_limit_change(self):
        """Semaphore should reflect limit changes."""
        from mcp_server_langgraph.resilience.adaptive import AdaptiveBulkhead

        bulkhead = AdaptiveBulkhead(
            min_limit=5,
            max_limit=20,
            initial_limit=10,
            decrease_factor=0.5,
        )

        # Get initial semaphore
        sem1 = bulkhead.get_semaphore()
        initial_value = sem1._value

        # Record error to decrease limit
        bulkhead.record_error()

        # New semaphore should have lower limit
        sem2 = bulkhead.get_semaphore()
        new_value = sem2._value

        # Value should be lower after error
        assert new_value < initial_value


# =============================================================================
# Test Provider Integration
# =============================================================================


@pytest.mark.xdist_group(name="adaptive_bulkhead")
class TestAdaptiveBulkheadProvider:
    """Test provider-specific adaptive bulkheads."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()
        from mcp_server_langgraph.resilience.adaptive import reset_all_adaptive_bulkheads

        reset_all_adaptive_bulkheads()

    @pytest.mark.unit
    def test_get_provider_adaptive_bulkhead(self):
        """Should create adaptive bulkhead for provider."""
        from mcp_server_langgraph.resilience.adaptive import (
            AdaptiveBulkhead,
            get_provider_adaptive_bulkhead,
        )

        bulkhead = get_provider_adaptive_bulkhead("anthropic")
        assert isinstance(bulkhead, AdaptiveBulkhead)

    @pytest.mark.unit
    def test_provider_bulkhead_caches(self):
        """Same provider should return same bulkhead."""
        from mcp_server_langgraph.resilience.adaptive import get_provider_adaptive_bulkhead

        b1 = get_provider_adaptive_bulkhead("openai")
        b2 = get_provider_adaptive_bulkhead("openai")
        assert b1 is b2

    @pytest.mark.unit
    def test_different_providers_different_bulkheads(self):
        """Different providers should have separate bulkheads."""
        from mcp_server_langgraph.resilience.adaptive import get_provider_adaptive_bulkhead

        anthropic = get_provider_adaptive_bulkhead("anthropic")
        openai = get_provider_adaptive_bulkhead("openai")
        assert anthropic is not openai
