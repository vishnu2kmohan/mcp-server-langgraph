"""
Performance Regression Test - Test Suite Duration

Validates that the entire unit test suite completes within acceptable time limits.

This meta-test prevents performance regression by failing if:
- Total test suite duration > 120 seconds (2 minutes)

Performance targets based on Codex findings:
- Current: 220s (3m 40s) ❌ TOO SLOW
- Target: < 120s (2 minutes) ✅ ACCEPTABLE
- Ideal: < 60s (1 minute) ⭐ EXCELLENT

Why this matters:
- Fast tests = faster development iteration
- Slow tests discourage running tests frequently
- Performance regressions accumulate over time

How to fix if this test fails:
1. Check test durations: pytest --durations=20
2. Look for tests > 5s (should be < 1s for unit tests)
3. Common causes:
   - Unnecessary sleeps/waits
   - Real I/O instead of mocks
   - Circuit breaker/retry delays
   - Large dataset generation
4. Optimization strategies:
   - Use fast_resilience_config fixture for CB tests
   - Use freezegun for time-based tests
   - Mock expensive operations
   - Reduce test data size

Related:
- tests/meta/test_slow_test_detection.py - Detects individual slow tests
- tests/conftest.py:fast_resilience_config - Reduces CB timeouts
"""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.meta
@pytest.mark.performance
def test_unit_test_suite_performance():
    """
    Test that unit test suite completes within 120 seconds.

    This is a meta-test that validates test suite performance to prevent regression.

    IMPORTANT: This test runs the full unit test suite, so it's slow by design.
    It should be run:
    - In CI/CD to catch performance regressions
    - Before releases to ensure acceptable performance
    - NOT in regular development (too slow for TDD workflow)

    Skip in development with: pytest -m "not performance"
    """
    # Skip in xdist workers (this test must run sequentially)
    if os.getenv("PYTEST_XDIST_WORKER"):
        pytest.skip("Performance regression test must run sequentially, not in xdist workers")

    # Find project root (where pyproject.toml exists)
    project_root = Path(__file__).parent.parent.parent
    assert (project_root / "pyproject.toml").exists(), "Could not find project root"

    # Run unit tests with timing
    # Use -m unit to run only unit tests (fast)
    # Use --durations=0 to get all test durations
    # Use -q for quiet output (less noise)
    result = subprocess.run(
        ["pytest", "-m", "unit", "--durations=0", "-q", "--tb=no", "--no-header"],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=180,  # 3 minute timeout (generous buffer)
    )

    # Parse output to find total duration
    # pytest outputs: "====== X passed in Y.YYs ======"
    output = result.stdout + result.stderr
    duration_line = [line for line in output.split("\n") if "passed in" in line or "failed in" in line]

    if not duration_line:
        pytest.fail(f"Could not parse test duration from output:\n{output}")

    # Extract duration (e.g., "2033 passed in 220.72s")
    import re

    match = re.search(r"in ([\d.]+)s", duration_line[-1])
    if not match:
        pytest.fail(f"Could not extract duration from: {duration_line[-1]}")

    duration_seconds = float(match.group(1))

    # Performance target: < 120 seconds
    MAX_DURATION = 120.0

    assert duration_seconds < MAX_DURATION, (
        f"Test suite too slow: {duration_seconds:.2f}s (limit: {MAX_DURATION}s)\n"
        f"Performance regression detected!\n"
        f"\n"
        f"To diagnose:\n"
        f"1. Run: pytest -m unit --durations=20\n"
        f"2. Look for tests > 5s\n"
        f"3. Common fixes:\n"
        f"   - Remove sleeps/waits\n"
        f"   - Mock I/O operations\n"
        f"   - Use fast_resilience_config for CB tests\n"
        f"   - Use freezegun for time-based tests\n"
        f"\n"
        f"Current slowest tests:\n"
        f"  - OpenFGA circuit breaker: 45s (needs retry optimization)\n"
        f"  - Agent tests: 14-29s each (needs mocking refactor)\n"
    )

    # Log success for visibility
    print(f"\n✅ Test suite performance: {duration_seconds:.2f}s (limit: {MAX_DURATION}s)")
