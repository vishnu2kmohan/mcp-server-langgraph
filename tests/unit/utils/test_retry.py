"""
Unit tests for retry utilities with exponential backoff.

Tests the retry_with_backoff function and async_retry decorator.
"""

import gc
from unittest.mock import AsyncMock, patch

import pytest

from mcp_server_langgraph.utils.retry import async_retry, retry_with_backoff

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_utils_retry")
class TestRetryWithBackoff:
    """Tests for retry_with_backoff function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success_first_try(self) -> None:
        """Test that function succeeds on first try without retry."""
        call_count = 0

        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_with_backoff(success_func, max_retries=3)

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success_after_retries(self) -> None:
        """Test that function succeeds after failing initially."""
        call_count = 0

        async def eventual_success_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await retry_with_backoff(
                eventual_success_func,
                max_retries=3,
                initial_delay=0.1,
            )

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_backoff_exhausts_retries(self) -> None:
        """Test that exception is raised after max retries."""
        call_count = 0

        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Permanent failure")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(Exception, match="Failed after 4 attempts"):
                await retry_with_backoff(
                    always_fails,
                    max_retries=3,
                    initial_delay=0.1,
                )

        assert call_count == 4  # Initial + 3 retries

    @pytest.mark.asyncio
    async def test_retry_with_backoff_respects_retryable_exceptions(self) -> None:
        """Test that only specified exception types are retried."""
        call_count = 0

        async def raises_runtime_error():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Not retryable")

        with pytest.raises(RuntimeError, match="Not retryable"):
            await retry_with_backoff(
                raises_runtime_error,
                max_retries=3,
                retryable_exceptions=(ValueError,),
            )

        assert call_count == 1  # No retries for non-matching exception

    @pytest.mark.asyncio
    async def test_retry_with_backoff_timeout_exceeded(self) -> None:
        """Test that retry stops when timeout is exceeded."""
        call_count = 0

        async def slow_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Failure")

        # Simulate time passing - needs enough values for all time.time() calls
        with (
            patch("mcp_server_langgraph.utils.retry.time.time") as mock_time,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            # Start time at 0, then elapsed times that exceed timeout
            mock_time.side_effect = [0, 0, 120, 120, 120, 120, 120, 120]

            with pytest.raises(Exception, match="Retry timeout exceeded"):
                await retry_with_backoff(
                    slow_fail,
                    max_retries=5,
                    initial_delay=0.1,
                    max_timeout=60.0,
                )

        assert call_count == 2  # Stopped after timeout check

    @pytest.mark.asyncio
    async def test_retry_with_backoff_exponential_delay(self) -> None:
        """Test that delay increases exponentially."""
        call_count = 0
        sleep_durations = []

        async def mock_sleep(duration):
            sleep_durations.append(duration)

        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise ValueError("Retry")
            return "done"

        with patch("asyncio.sleep", side_effect=mock_sleep):
            result = await retry_with_backoff(
                failing_func,
                max_retries=5,
                initial_delay=1.0,
                exponential_base=2.0,
                jitter=False,
                max_delay=32.0,
            )

        assert result == "done"
        # Delays should be approximately: 1*2^0=1, 1*2^1=2, 1*2^2=4
        assert len(sleep_durations) == 3
        assert sleep_durations[0] == pytest.approx(1.0, rel=0.1)
        assert sleep_durations[1] == pytest.approx(2.0, rel=0.1)
        assert sleep_durations[2] == pytest.approx(4.0, rel=0.1)

    @pytest.mark.asyncio
    async def test_retry_with_backoff_respects_max_delay(self) -> None:
        """Test that delay is capped at max_delay."""
        sleep_durations = []

        async def mock_sleep(duration):
            sleep_durations.append(duration)

        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 5:
                raise ValueError("Retry")
            return "done"

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await retry_with_backoff(
                failing_func,
                max_retries=5,
                initial_delay=1.0,
                exponential_base=10.0,  # Would give 10, 100, 1000...
                max_delay=5.0,
                jitter=False,
            )

        # All delays should be capped at max_delay=5.0
        for duration in sleep_durations:
            assert duration <= 5.0

    @pytest.mark.asyncio
    async def test_retry_with_backoff_jitter(self) -> None:
        """Test that jitter adds randomness to delay."""
        sleep_durations = []

        async def mock_sleep(duration):
            sleep_durations.append(duration)

        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Retry")
            return "done"

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await retry_with_backoff(
                failing_func,
                max_retries=3,
                initial_delay=1.0,
                exponential_base=2.0,
                jitter=True,  # Enable jitter
                max_delay=32.0,
            )

        # With jitter, delays should be within ±20% of base calculation
        # Base delay 1: jittered should be 0.8-1.2
        # Base delay 2: jittered should be 1.6-2.4
        assert 0.8 <= sleep_durations[0] <= 1.2
        assert 1.6 <= sleep_durations[1] <= 2.4


@pytest.mark.xdist_group(name="test_utils_retry")
class TestAsyncRetryDecorator:
    """Tests for async_retry decorator."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_async_retry_decorator_success(self) -> None:
        """Test that decorated function works correctly."""
        call_count = 0

        @async_retry(max_retries=3, initial_delay=0.1)
        async def decorated_func():
            nonlocal call_count
            call_count += 1
            return "success"

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await decorated_func()

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_retry_decorator_retries_on_failure(self) -> None:
        """Test that decorated function retries on failure."""
        call_count = 0

        @async_retry(max_retries=3, initial_delay=0.1)
        async def decorated_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry")
            return "recovered"

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await decorated_func()

        assert result == "recovered"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_async_retry_decorator_with_arguments(self) -> None:
        """Test that decorated function handles arguments correctly."""
        call_count = 0

        @async_retry(max_retries=2, initial_delay=0.1)
        async def add_numbers(a: int, b: int) -> int:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry")
            return a + b

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await add_numbers(3, 4)

        assert result == 7
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_async_retry_decorator_preserves_function_name(self) -> None:
        """Test that decorator preserves function metadata."""

        @async_retry(max_retries=2)
        async def my_important_function():
            return "result"

        assert my_important_function.__name__ == "my_important_function"

    @pytest.mark.asyncio
    async def test_async_retry_decorator_exhausts_retries(self) -> None:
        """Test that decorator raises after max retries."""

        @async_retry(max_retries=2, initial_delay=0.1)
        async def always_fails():
            raise ValueError("Always fails")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(Exception, match="Failed after 3 attempts"):
                await always_fails()
