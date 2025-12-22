"""
Benchmark Test Configuration.

This conftest.py automatically handles pytest-benchmark marker application:
1. All tests in benchmarks/ are marked with 'benchmark' and 'performance'
2. Tests using the 'benchmark' fixture are skipped when --benchmark-disable
3. Tests NOT using 'benchmark' fixture run as regular unit tests

Usage:
    # Run only benchmark-fixture tests with benchmarking
    pytest tests/benchmarks/ --benchmark-enable -m benchmark

    # Run scalability/validation tests (no fixture) as unit tests
    pytest tests/benchmarks/ -m unit

    # Run all benchmarks with metrics
    pytest tests/benchmarks/ --benchmark-enable --benchmark-autosave
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from _pytest.config import Config
    from _pytest.nodes import Item


def pytest_configure(config: Config) -> None:
    """Register custom markers for benchmark tests."""
    config.addinivalue_line(
        "markers",
        "benchmark_fixture: Tests that use the benchmark fixture (auto-detected)",
    )


def pytest_collection_modifyitems(config: Config, items: list[Item]) -> None:
    """
    Auto-apply markers to benchmark tests.

    - All tests in benchmarks/ get 'performance' marker
    - Tests using 'benchmark' fixture get 'benchmark_fixture' marker
    - Tests NOT using fixture get 'unit' marker for regular runs
    """
    for item in items:
        # Only process tests in benchmarks directory
        if "benchmarks" not in str(item.fspath):
            continue

        # Add performance marker to all benchmark tests
        item.add_marker(pytest.mark.performance)

        # Check if test uses the benchmark fixture
        if "benchmark" in getattr(item, "fixturenames", []):
            item.add_marker(pytest.mark.benchmark_fixture)
            # These tests are auto-skipped when --benchmark-disable is active
            # pytest-benchmark handles this automatically
        else:
            # Tests without benchmark fixture are regular unit tests
            # They can run without --benchmark-enable
            if not any(m.name == "unit" for m in item.iter_markers()):
                item.add_marker(pytest.mark.unit)


@pytest.fixture(scope="function", autouse=True)
def benchmark_cleanup() -> None:
    """Force garbage collection after each benchmark to prevent memory issues."""
    yield
    gc.collect()


@pytest.fixture(scope="session")
def benchmark_config() -> dict[str, int | bool]:
    """Shared benchmark configuration."""
    return {
        "small_dataset": 100,
        "medium_dataset": 500,
        "large_dataset": 1000,
        "stress_dataset": 5000,
        "enable_profiling": False,
    }
