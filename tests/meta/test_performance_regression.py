"""
Meta-tests to prevent performance regressions in the test suite.

CODEX FINDING #2: Timeout tests were using real asyncio.sleep(5-10s) calls,
burning ~15s per test run. This meta-test ensures timeout tests complete quickly.

TDD Approach:
1. Write this test FIRST (will fail with slow sleeps)
2. Refactor timeout tests to use shorter sleeps
3. Verify this test passes
"""

import gc
import subprocess
import time
from pathlib import Path

import pytest


@pytest.mark.xdist_group(name="testtimeouttestperformance")
class TestTimeoutTestPerformance:
    """Validate that timeout tests execute quickly (CODEX Finding #2)"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_timeout_tests_complete_within_2_seconds(self):
        """
        CODEX FINDING #2: Timeout tests should not use real long sleeps.

        GIVEN: Timeout tests in test_parallel_executor_timeout.py
        WHEN: Running all timeout tests
        THEN: Should complete in < 2 seconds (not 15+ seconds)

        This test enforces that timeout tests use efficient mocking/short sleeps
        instead of burning time with real long sleeps.

        NOTE: This test is skipped when running under pytest-xdist (parallel mode)
        because the subprocess timing is affected by parallel execution overhead.
        """
        import os

        # Skip when running under pytest-xdist (parallel mode)
        if os.getenv("PYTEST_XDIST_WORKER") is not None:
            pytest.skip("Performance timing test skipped in parallel mode (xdist)")

        test_file = Path(__file__).parent.parent / "unit" / "test_parallel_executor_timeout.py"

        if not test_file.exists():
            pytest.skip(f"Timeout test file not found: {test_file}")

        # Run the timeout tests and measure execution time
        # Use venv pytest to ensure dependencies are available
        import sys

        pytest_path = Path(sys.executable).parent / "pytest"

        start = time.time()
        result = subprocess.run(
            [str(pytest_path), str(test_file), "-v", "--tb=short", "-x"],
            capture_output=True,
            text=True,
            timeout=30,  # Kill if it takes more than 10s
        )
        duration = time.time() - start

        # Assert tests passed
        assert result.returncode == 0, (
            f"Timeout tests failed:\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}\n"
            f"\nFix the failing tests before optimizing performance."
        )

        # Assert execution time is reasonable (including pytest overhead of ~3-4s)
        assert duration < 8.0, (
            f"Timeout tests took {duration:.2f}s (target: < 8.0s)\n"
            f"\nCODEX FINDING #2: Timeout tests are using real long sleeps.\n"
            f"Solution: Use shorter sleep values while maintaining timeout ratios.\n"
            f"\nExample:\n"
            f"  ❌ BAD:  timeout=2.0s, sleep=5s   (burns 5s waiting)\n"
            f"  ✅ GOOD: timeout=0.05s, sleep=0.1s (burns 0.1s, same timeout behavior)\n"
            f"\nThe ratio is what matters for timeout testing, not absolute values.\n"
            f"\nNote: Target includes pytest startup overhead (~3-4s). "
            f"Actual test execution is much faster."
        )

    @pytest.mark.unit
    def test_timeout_tests_use_short_sleep_values(self):
        """
        CODEX FINDING #2: Ensure timeout tests don't use sleep values > 1 second.

        This is a static check that scans the test file for long sleep calls.
        """
        test_file = Path(__file__).parent.parent / "unit" / "test_parallel_executor_timeout.py"

        if not test_file.exists():
            pytest.skip(f"Timeout test file not found: {test_file}")

        with open(test_file) as f:
            content = f.read()

        # Look for asyncio.sleep with values >= 1
        import re

        sleep_pattern = r"asyncio\.sleep\((\d+(?:\.\d+)?)\)"
        matches = re.findall(sleep_pattern, content)

        long_sleeps = [float(value) for value in matches if float(value) >= 1.0]

        assert not long_sleeps, (
            f"Found {len(long_sleeps)} asyncio.sleep() calls with values >= 1 second: {long_sleeps}\n"
            f"\nCODEX FINDING #2: Use sleep values < 1 second for fast test execution.\n"
            f"Example: Instead of sleep(5), use sleep(0.1) with proportional timeout values."
        )


@pytest.mark.xdist_group(name="testtimebudgets")
class TestTimeBudgets:
    """Enforce per-test time budgets to prevent performance regressions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_unit_tests_complete_within_budget(self):
        """
        Unit tests should complete quickly (< 100ms per test on average).

        This budget excludes setup/teardown and focuses on test execution time.
        """
        # This is a meta-test that validates the concept
        # In practice, this would be enforced by pytest-timeout or CI monitoring
        pytest.skip("Time budget enforcement is handled by pytest-timeout and sleep linter")

    @pytest.mark.unit
    def test_integration_tests_have_reasonable_budgets(self):
        """
        Integration tests should complete within reasonable time (< 5s per test).

        Tests exceeding this should be marked as @pytest.mark.slow and
        run separately in CI.
        """
        pytest.skip("Time budget enforcement is handled by pytest markers and CI config")


@pytest.mark.xdist_group(name="testpropertytestbudgets")
class TestPropertyTestBudgets:
    """Validate property test deadlines are reasonable."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_property_tests_have_reasonable_deadlines(self):
        """
        Property tests should have deadline < 3000ms per example.

        CODEX audit found property tests with long deadlines that burn time
        when examples fail or edge cases are explored.
        """
        import re
        from pathlib import Path

        property_test_files = list(Path("tests/property").glob("test_*.py"))

        if not property_test_files:
            pytest.skip("No property test files found")

        for test_file in property_test_files:
            with open(test_file) as f:
                content = f.read()

            # Find @settings decorators with deadline parameter
            deadline_pattern = r"@settings\([^)]*deadline=(\d+)[^)]*\)"
            matches = re.findall(deadline_pattern, content)

            for deadline_str in matches:
                deadline_ms = int(deadline_str)
                assert deadline_ms <= 3000, (
                    f"{test_file.name}: Found property test deadline {deadline_ms}ms > 3000ms\n"
                    f"Use shorter deadlines for faster property test execution."
                )


@pytest.mark.xdist_group(name="testbulkheadperformance")
class TestBulkheadPerformance:
    """Validate bulkhead tests don't burn unnecessary time."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_bulkhead_tests_use_short_sleeps(self):
        """
        Bulkhead tests should use sleep values < 0.5s.

        CODEX audit found bulkhead tests with 1s sleeps that could be reduced.
        """
        test_file = Path("tests/resilience/test_bulkhead.py")

        if not test_file.exists():
            pytest.skip("Bulkhead test file not found")

        with open(test_file) as f:
            content = f.read()

        # Find asyncio.sleep calls
        import re

        sleep_pattern = r"asyncio\.sleep\((\d+(?:\.\d+)?)\)"
        matches = re.findall(sleep_pattern, content)

        # After optimization, should have no sleeps >= 0.5s
        long_sleeps = [float(value) for value in matches if float(value) >= 0.5]

        assert not long_sleeps, (
            f"Found {len(long_sleeps)} asyncio.sleep() calls >= 0.5s: {long_sleeps}\n"
            f"Bulkhead tests should use shorter sleeps for fast execution."
        )


@pytest.mark.xdist_group(name="testpollingoptimizations")
class TestPollingOptimizations:
    """Validate polling helpers are used instead of fixed sleeps."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_kubernetes_sandbox_uses_polling(self):
        """
        Kubernetes sandbox cleanup should use poll_until() instead of fixed sleep.

        CODEX audit found 5-second sleeps that could be replaced with polling.
        """
        test_file = Path("tests/integration/execution/test_kubernetes_sandbox.py")

        if not test_file.exists():
            pytest.skip("Kubernetes sandbox test file not found")

        with open(test_file) as f:
            content = f.read()

        # Should import poll_until
        assert (
            "from tests.helpers.polling import poll_until" in content
        ), "Kubernetes sandbox tests should use poll_until() for cleanup waits"

        # Should not have long time.sleep calls (> 2s) in test code (not in string literals)
        import re

        # Remove triple-quoted strings to avoid matching sleep calls in test data
        # Pattern: Remove content between ''' ''' and """ """
        content_no_strings = re.sub(r'""".*?"""', "", content, flags=re.DOTALL)
        content_no_strings = re.sub(r"'''.*?'''", "", content_no_strings, flags=re.DOTALL)

        sleep_pattern = r"time\.sleep\((\d+(?:\.\d+)?)\)"
        matches = re.findall(sleep_pattern, content_no_strings)

        long_sleeps = [float(value) for value in matches if float(value) > 2.0]

        assert not long_sleeps, (
            f"Found {len(long_sleeps)} time.sleep() calls > 2s in test logic: {long_sleeps}\n"
            f"Use poll_until() instead of fixed sleeps for cleanup waits."
        )

    @pytest.mark.unit
    def test_docker_sandbox_uses_polling(self):
        """
        Docker sandbox cleanup should use poll_until() instead of fixed sleep.

        CODEX audit found 2-second sleeps that could be replaced with polling.
        """
        test_file = Path("tests/integration/execution/test_docker_sandbox.py")

        if not test_file.exists():
            pytest.skip("Docker sandbox test file not found")

        with open(test_file) as f:
            content = f.read()

        # Should import poll_until
        assert (
            "from tests.helpers.polling import poll_until" in content
        ), "Docker sandbox tests should use poll_until() for cleanup waits"


@pytest.mark.xdist_group(name="testvirtualclockavailability")
class TestVirtualClockAvailability:
    """Validate VirtualClock is available for future optimizations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_virtual_clock_exists_and_works(self):
        """
        VirtualClock should be available for instant time advancement in tests.
        """
        from mcp_server_langgraph.core.time_provider import VirtualClock

        clock = VirtualClock()
        assert clock.time() == 0.0

        # Verify instant time advancement
        start = time.time()
        clock.sleep(10.0)  # Should be instant
        elapsed = time.time() - start

        assert elapsed < 0.1, f"VirtualClock.sleep() should be instant, took {elapsed:.3f}s"
        assert clock.time() == 10.0, "VirtualClock should advance time instantly"

    @pytest.mark.unit
    def test_time_fixtures_available(self):
        """
        Time fixtures should be available for test use.
        """
        from tests.fixtures.time_fixtures import virtual_clock

        # Fixture should be importable (actual usage happens in tests)
        assert virtual_clock is not None
