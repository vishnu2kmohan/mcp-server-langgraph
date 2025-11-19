"""
Performance Test Configuration and Fixtures

Provides enhanced pytest-benchmark fixtures for percentile-based performance assertions.
"""

import asyncio
import inspect
import time
from collections.abc import Callable
from typing import List

import pytest


class PercentileBenchmark:
    """
    Wrapper around pytest-benchmark that provides percentile-based assertions.

    Instead of asserting on mean/average (which can be volatile), this allows
    asserting on p95/p99 percentiles for more stable performance tests.

    Example:
        def test_performance(percentile_benchmark):
            result = percentile_benchmark(expensive_function, arg1, arg2)

            # Assert p95 latency is under 10ms
            percentile_benchmark.assert_percentile(95, 0.010)

            # Assert p99 latency is under 15ms
            percentile_benchmark.assert_percentile(99, 0.015)
    """

    def __init__(self, benchmark):
        """Initialize with pytest-benchmark fixture"""
        self._benchmark = benchmark
        self._times: list[float] = []

    def __call__(self, func: Callable, *args, **kwargs):
        """
        Benchmark a function and collect timing data.

        Supports both synchronous and asynchronous functions. For async functions,
        reuses a single event loop across all iterations for accurate benchmarking.

        Args:
            func: Function to benchmark (sync or async)
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of the benchmarked function
        """
        # Detect if function is async
        is_async = inspect.iscoroutinefunction(func)

        if is_async:
            # For async functions: create ONE event loop and reuse it
            # This prevents the overhead of creating/destroying 100 event loops
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:

                def async_wrapper():
                    start = time.perf_counter()
                    result = loop.run_until_complete(func(*args, **kwargs))
                    end = time.perf_counter()
                    self._times.append(end - start)
                    return result

                # Use pedantic mode with SINGLE event loop (much faster and more accurate)
                result = self._benchmark.pedantic(
                    async_wrapper,
                    iterations=100,  # 100 samples for accurate percentile calculation
                    rounds=1,  # Single round to avoid excessive repetition
                )

                return result

            finally:
                # Clean up event loop after all iterations complete
                loop.close()

        else:
            # Synchronous function: original implementation

            def wrapper():
                start = time.perf_counter()
                result = func(*args, **kwargs)
                end = time.perf_counter()
                self._times.append(end - start)
                return result

            # Use pedantic mode to collect multiple samples for accurate percentile statistics
            # NOTE: 100 iterations are intentional for statistical accuracy in percentile calculations.
            # This is FAST because all benchmarks use mocked clients with simulated latency,
            # avoiding real I/O operations. Typical runtime: < 5 seconds per benchmark.
            result = self._benchmark.pedantic(
                wrapper,
                iterations=100,  # 100 samples for accurate percentile calculation (p50, p95, p99)
                rounds=1,  # Single round to avoid excessive repetition
            )

            return result

    def assert_percentile(self, percentile: int, max_seconds: float, description: str = ""):
        """
        Assert that a specific percentile is below a threshold.

        Args:
            percentile: Percentile to check (e.g., 95 for p95, 99 for p99)
            max_seconds: Maximum allowed time in seconds
            description: Optional description for assertion message

        Raises:
            AssertionError: If percentile exceeds threshold
        """
        if not self._times:
            raise ValueError("No timing data collected - did you call the benchmark first?")

        value = self._calculate_percentile(percentile)
        label = f" ({description})" if description else ""

        assert value < max_seconds, f"p{percentile}{label}: {value * 1000:.2f}ms (target: < {max_seconds * 1000:.0f}ms)"

    def _calculate_percentile(self, percentile: int) -> float:
        """
        Calculate percentile from collected timing data.

        Args:
            percentile: Percentile to calculate (0-100)

        Returns:
            Percentile value in seconds
        """
        sorted_times = sorted(self._times)
        index = int(len(sorted_times) * (percentile / 100.0))
        # Clamp to valid range
        index = max(0, min(index, len(sorted_times) - 1))
        return sorted_times[index]

    @property
    def stats(self) -> dict:
        """
        Compute statistics from collected timing data.

        Returns:
            Dictionary with mean, p50, p95, p99, min, max
        """
        if not self._times:
            return {}

        sorted_times = sorted(self._times)
        return {
            "mean": sum(self._times) / len(self._times),
            "p50": self._calculate_percentile(50),
            "p95": self._calculate_percentile(95),
            "p99": self._calculate_percentile(99),
            "min": sorted_times[0],
            "max": sorted_times[-1],
            "samples": len(self._times),
        }


@pytest.fixture
def percentile_benchmark(benchmark):
    """
    Enhanced pytest-benchmark fixture with percentile assertion support.

    Usage:
        def test_my_performance(percentile_benchmark):
            result = percentile_benchmark(my_function, arg1, arg2)
            percentile_benchmark.assert_percentile(95, 0.005)  # p95 < 5ms
            percentile_benchmark.assert_percentile(99, 0.010)  # p99 < 10ms

    Args:
        benchmark: pytest-benchmark fixture

    Returns:
        PercentileBenchmark: Enhanced benchmark fixture
    """
    return PercentileBenchmark(benchmark)
