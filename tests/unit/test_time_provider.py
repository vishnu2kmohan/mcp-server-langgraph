"""
Unit tests for TimeProvider abstraction and VirtualClock implementation.

These tests validate the time provider pattern that enables fast-forwarding time
in tests without real sleep() calls, eliminating 50+ seconds of sleep overhead.

TDD: These tests are written FIRST (RED phase) before implementing the time provider.
"""

import gc
import os
import time
from typing import Protocol
from unittest.mock import AsyncMock, MagicMock

import pytest

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


# Test the Protocol definition
def test_time_provider_protocol_defines_required_methods():
    """TimeProvider protocol must define time(), sleep(), and monotonic() methods."""
    from mcp_server_langgraph.core.time_provider import TimeProvider

    # Protocol should have these methods
    assert hasattr(TimeProvider, "time")
    assert hasattr(TimeProvider, "sleep")
    assert hasattr(TimeProvider, "monotonic")


@pytest.mark.xdist_group(name="time_provider")
class TestRealTimeProvider:
    """Tests for RealTimeProvider (wrapper around Python's time module)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_real_time_provider_returns_current_time(self):
        """RealTimeProvider.time() should return current Unix timestamp."""
        from mcp_server_langgraph.core.time_provider import RealTimeProvider

        provider = RealTimeProvider()
        before = time.time()
        result = provider.time()
        after = time.time()

        assert before <= result <= after, "time() should return current Unix timestamp"

    def test_real_time_provider_sleep_blocks_for_duration(self):
        """RealTimeProvider.sleep() should block for specified duration."""
        from mcp_server_langgraph.core.time_provider import RealTimeProvider

        provider = RealTimeProvider()
        start = time.time()
        provider.sleep(0.05)  # 50ms
        elapsed = time.time() - start

        assert 0.04 <= elapsed <= 0.1, f"sleep(0.05) should block ~50ms, got {elapsed:.3f}s"

    def test_real_time_provider_monotonic_increases(self):
        """RealTimeProvider.monotonic() should return monotonically increasing values."""
        from mcp_server_langgraph.core.time_provider import RealTimeProvider

        provider = RealTimeProvider()
        first = provider.monotonic()
        time.sleep(0.01)
        second = provider.monotonic()

        assert second > first, "monotonic() should increase over time"


@pytest.mark.xdist_group(name="time_provider")
class TestVirtualClock:
    """Tests for VirtualClock (fast-forward time without real sleep)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_virtual_clock_starts_at_zero(self):
        """VirtualClock should start at time=0.0 by default."""
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock()
        assert clock.time() == 0.0, "VirtualClock should start at time=0.0"
        assert clock.monotonic() == 0.0, "VirtualClock monotonic should start at 0.0"

    def test_virtual_clock_starts_at_custom_time(self):
        """VirtualClock should allow custom start time."""
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock(start_time=1000.0)
        assert clock.time() == 1000.0, "VirtualClock should start at custom time"

    def test_virtual_clock_advance_increases_time(self):
        """VirtualClock.advance() should increase current time."""
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock()
        assert clock.time() == 0.0

        clock.advance(5.0)
        assert clock.time() == 5.0, "advance(5.0) should increase time to 5.0"

        clock.advance(2.5)
        assert clock.time() == 7.5, "advance(2.5) should increase time to 7.5"

    def test_virtual_clock_sleep_advances_time_instantly(self):
        """VirtualClock.sleep() should advance time without real blocking."""
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock()
        start_wall_time = time.time()

        # This should NOT actually sleep 10 seconds
        clock.sleep(10.0)

        wall_time_elapsed = time.time() - start_wall_time
        assert wall_time_elapsed < 0.1, f"sleep(10.0) should be instant, took {wall_time_elapsed:.3f}s"
        assert clock.time() == 10.0, "sleep(10.0) should advance virtual time to 10.0"

    def test_virtual_clock_sleep_zero_does_nothing(self):
        """VirtualClock.sleep(0) should not change time."""
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock()
        clock.advance(5.0)
        clock.sleep(0)

        assert clock.time() == 5.0, "sleep(0) should not change time"

    def test_virtual_clock_sleep_negative_raises_error(self):
        """VirtualClock.sleep() with negative duration should raise ValueError."""
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock()
        with pytest.raises(ValueError, match="sleep duration must be non-negative"):
            clock.sleep(-1.0)

    def test_virtual_clock_monotonic_tracks_time(self):
        """VirtualClock.monotonic() should track current time."""
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock()
        assert clock.monotonic() == 0.0

        clock.advance(3.0)
        assert clock.monotonic() == 3.0

        clock.sleep(2.0)
        assert clock.monotonic() == 5.0

    def test_virtual_clock_multiple_instances_independent(self):
        """Multiple VirtualClock instances should be independent."""
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock1 = VirtualClock()
        clock2 = VirtualClock(start_time=100.0)

        clock1.advance(5.0)
        assert clock1.time() == 5.0
        assert clock2.time() == 100.0, "clock2 should be unaffected by clock1"

        clock2.sleep(10.0)
        assert clock1.time() == 5.0, "clock1 should be unaffected by clock2"
        assert clock2.time() == 110.0


@pytest.mark.xdist_group(name="time_provider")
class TestAsyncVirtualClock:
    """Tests for VirtualClock with async sleep support."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_virtual_clock_async_sleep_advances_time_instantly(self):
        """VirtualClock.async_sleep() should advance time without real blocking."""
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock()
        start_wall_time = time.time()

        # This should NOT actually sleep 10 seconds
        await clock.async_sleep(10.0)

        wall_time_elapsed = time.time() - start_wall_time
        assert wall_time_elapsed < 0.1, f"async_sleep(10.0) should be instant, took {wall_time_elapsed:.3f}s"
        assert clock.time() == 10.0, "async_sleep(10.0) should advance virtual time to 10.0"

    @pytest.mark.asyncio
    async def test_virtual_clock_async_sleep_negative_raises_error(self):
        """VirtualClock.async_sleep() with negative duration should raise ValueError."""
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock()
        with pytest.raises(ValueError, match="sleep duration must be non-negative"):
            await clock.async_sleep(-1.0)

    @pytest.mark.asyncio
    async def test_virtual_clock_async_sleep_multiple_tasks(self):
        """VirtualClock.async_sleep() should advance time consistently across tasks."""
        import asyncio

        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock()

        async def task_a():
            await clock.async_sleep(5.0)
            return clock.time()

        async def task_b():
            await clock.async_sleep(3.0)
            return clock.time()

        # Both tasks advance the clock sequentially due to locking
        result_a, result_b = await asyncio.gather(task_a(), task_b())

        # Final time should be sum of both sleeps (sequential execution with lock)
        assert clock.time() == 8.0, f"Clock should be at 8.0 (5.0 + 3.0), got {clock.time()}"


@pytest.mark.xdist_group(name="time_provider")
class TestTimeProviderIntegration:
    """Integration tests proving TimeProvider works with real components."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_time_provider_protocol_satisfied_by_implementations(self):
        """Verify RealTimeProvider and VirtualClock satisfy TimeProvider protocol."""
        from mcp_server_langgraph.core.time_provider import RealTimeProvider, TimeProvider, VirtualClock

        # Both implementations should satisfy the protocol
        real_provider: TimeProvider = RealTimeProvider()
        virtual_clock: TimeProvider = VirtualClock()

        # Verify they have the required methods
        assert callable(real_provider.time)
        assert callable(real_provider.sleep)
        assert callable(real_provider.monotonic)
        assert callable(real_provider.async_sleep)

        assert callable(virtual_clock.time)
        assert callable(virtual_clock.sleep)
        assert callable(virtual_clock.monotonic)
        assert callable(virtual_clock.async_sleep)

    def test_virtual_clock_enables_instant_ttl_testing(self):
        """Demonstrate that VirtualClock eliminates sleep overhead in TTL tests."""
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock()

        # Simulate a TTL check that would normally require sleep
        cache_time = clock.time()

        # Instead of time.sleep(1.0), we instantly advance
        start_wall_time = time.time()
        clock.advance(1.0)
        wall_time_elapsed = time.time() - start_wall_time

        # Verify it was instant
        assert wall_time_elapsed < 0.01, "Virtual time advance should be instant"

        # Check if TTL expired
        ttl = 0.5
        is_expired = (clock.time() - cache_time) > ttl
        assert is_expired, "Value should be expired after advancing past TTL"


# Note: Bulkhead tests removed - BulkheadContext uses semaphores, not sleep,
# so it doesn't need time_provider injection for performance optimization
