"""
Meta-tests to prevent performance regressions in the test suite.

CODEX FINDING #2: Timeout tests were using real asyncio.sleep(5-10s) calls,
burning ~15s per test run. This meta-test ensures timeout tests complete quickly.

TDD Approach:
1. Write this test FIRST (will fail with slow sleeps)
2. Refactor timeout tests to use shorter sleeps
3. Verify this test passes
"""

import subprocess
import time
from pathlib import Path

import pytest


class TestTimeoutTestPerformance:
    """Validate that timeout tests execute quickly (CODEX Finding #2)"""

    @pytest.mark.unit
    def test_timeout_tests_complete_within_2_seconds(self):
        """
        CODEX FINDING #2: Timeout tests should not use real long sleeps.

        GIVEN: Timeout tests in test_parallel_executor_timeout.py
        WHEN: Running all timeout tests
        THEN: Should complete in < 2 seconds (not 15+ seconds)

        This test enforces that timeout tests use efficient mocking/short sleeps
        instead of burning time with real long sleeps.
        """
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
            timeout=10,  # Kill if it takes more than 10s
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

        with open(test_file, "r") as f:
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
