"""
Unit tests for polling helper utilities.

These tests validate the poll_until() helper that enables fast polling-based
waits instead of fixed sleep() delays, saving ~9.5 seconds in integration tests.

TDD: These tests are written FIRST (RED phase) before implementing poll_until().
"""

import gc
import time
from collections.abc import Callable

import pytest


# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="polling_helpers")
class TestPollUntil:
    """Tests for poll_until() polling helper."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_poll_until_returns_true_immediately(self):
        """poll_until() should return immediately when condition is True."""
        from tests.helpers.polling import poll_until

        call_count = 0

        def always_true() -> bool:
            nonlocal call_count
            call_count += 1
            return True

        start = time.time()
        result = poll_until(always_true, interval=0.1, timeout=5.0)
        elapsed = time.time() - start

        assert result is True, "Should return True when condition met"
        assert call_count == 1, "Should only call condition once"
        assert elapsed < 0.1, f"Should return immediately, took {elapsed:.3f}s"

    def test_poll_until_waits_for_condition(self):
        """poll_until() should poll until condition becomes True."""
        from tests.helpers.polling import poll_until

        call_count = 0
        target_calls = 3

        def becomes_true() -> bool:
            nonlocal call_count
            call_count += 1
            return call_count >= target_calls

        start = time.time()
        result = poll_until(becomes_true, interval=0.05, timeout=5.0)
        elapsed = time.time() - start

        assert result is True, "Should return True when condition eventually met"
        assert call_count == target_calls, f"Expected {target_calls} calls, got {call_count}"
        # Should take approximately (target_calls - 1) * interval
        expected_time = (target_calls - 1) * 0.05
        assert expected_time <= elapsed < expected_time + 0.2, f"Should take ~{expected_time:.2f}s, took {elapsed:.3f}s"

    def test_poll_until_times_out(self):
        """poll_until() should return False on timeout."""
        from tests.helpers.polling import poll_until

        def always_false() -> bool:
            return False

        start = time.time()
        result = poll_until(always_false, interval=0.05, timeout=0.2)
        elapsed = time.time() - start

        assert result is False, "Should return False on timeout"
        assert 0.2 <= elapsed < 0.4, f"Should timeout after ~0.2s, took {elapsed:.3f}s"

    def test_poll_until_with_zero_timeout(self):
        """poll_until() should check condition once with timeout=0."""
        from tests.helpers.polling import poll_until

        call_count = 0

        def counter() -> bool:
            nonlocal call_count
            call_count += 1
            return False

        result = poll_until(counter, interval=0.1, timeout=0.0)

        assert result is False
        assert call_count == 1, "Should check condition exactly once"

    def test_poll_until_with_negative_timeout_raises(self):
        """poll_until() should raise ValueError for negative timeout."""
        from tests.helpers.polling import poll_until

        with pytest.raises(ValueError, match="timeout must be non-negative"):
            poll_until(lambda: True, interval=0.1, timeout=-1.0)

    def test_poll_until_with_negative_interval_raises(self):
        """poll_until() should raise ValueError for negative interval."""
        from tests.helpers.polling import poll_until

        with pytest.raises(ValueError, match="interval must be positive"):
            poll_until(lambda: True, interval=-0.1, timeout=1.0)

    def test_poll_until_with_zero_interval_raises(self):
        """poll_until() should raise ValueError for zero interval."""
        from tests.helpers.polling import poll_until

        with pytest.raises(ValueError, match="interval must be positive"):
            poll_until(lambda: True, interval=0.0, timeout=1.0)

    def test_poll_until_handles_exceptions(self):
        """poll_until() should treat exceptions as False and continue polling."""
        from tests.helpers.polling import poll_until

        call_count = 0

        def fails_then_succeeds() -> bool:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Not ready yet")
            return True

        result = poll_until(fails_then_succeeds, interval=0.05, timeout=1.0)

        assert result is True, "Should eventually succeed after exceptions"
        assert call_count == 3, "Should retry after exceptions"

    def test_poll_until_real_world_example(self):
        """poll_until() example: waiting for job completion."""
        from tests.helpers.polling import poll_until

        # Simulate a job that takes ~0.15s to complete
        class Job:
            def __init__(self):
                self.start_time = time.time()
                self.duration = 0.15

            def is_complete(self) -> bool:
                return (time.time() - self.start_time) >= self.duration

        job = Job()
        start = time.time()

        # Poll every 50ms for up to 1 second
        result = poll_until(job.is_complete, interval=0.05, timeout=1.0)
        elapsed = time.time() - start

        assert result is True, "Job should complete"
        # Should complete in ~0.15-0.20s (3-4 polls)
        assert 0.15 <= elapsed < 0.3, f"Should complete in ~0.15-0.20s, took {elapsed:.3f}s"

        # Much faster than time.sleep(1.0) alternative
        assert elapsed < 0.5, "Should be significantly faster than fixed sleep"


@pytest.mark.xdist_group(name="polling_helpers")
@pytest.mark.asyncio
class TestAsyncPollUntil:
    """Tests for async_poll_until() async polling helper."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_async_poll_until_returns_true_immediately(self):
        """async_poll_until() should return immediately when condition is True."""
        from tests.helpers.polling import async_poll_until

        call_count = 0

        async def always_true() -> bool:
            nonlocal call_count
            call_count += 1
            return True

        start = time.time()
        result = await async_poll_until(always_true, interval=0.1, timeout=5.0)
        elapsed = time.time() - start

        assert result is True
        assert call_count == 1
        assert elapsed < 0.1

    async def test_async_poll_until_waits_for_condition(self):
        """async_poll_until() should poll until condition becomes True."""
        from tests.helpers.polling import async_poll_until

        call_count = 0

        async def becomes_true() -> bool:
            nonlocal call_count
            call_count += 1
            return call_count >= 3

        result = await async_poll_until(becomes_true, interval=0.05, timeout=5.0)

        assert result is True
        assert call_count == 3

    async def test_async_poll_until_times_out(self):
        """async_poll_until() should return False on timeout."""
        from tests.helpers.polling import async_poll_until

        async def always_false() -> bool:
            return False

        start = time.time()
        result = await async_poll_until(always_false, interval=0.05, timeout=0.2)
        elapsed = time.time() - start

        assert result is False
        assert 0.2 <= elapsed < 0.4
