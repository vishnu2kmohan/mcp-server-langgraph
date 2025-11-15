"""
Slow Test Detection - Identify Individual Slow Tests

Validates that individual unit tests complete quickly (< 10 seconds).

This meta-test prevents performance regression by detecting:
- Individual unit tests > 10 seconds
- Common slow test patterns

Performance guidelines:
- Unit tests: < 1s ✅ IDEAL
- Integration tests: < 5s ✅ ACCEPTABLE
- E2E tests: < 30s ✅ ACCEPTABLE
- Unit tests > 10s: ❌ NEEDS OPTIMIZATION

Why this matters:
- Unit tests should be fast for TDD workflow
- Slow tests indicate integration/E2E behavior in unit tests
- Each slow test compounds total suite time

Common causes of slow tests:
1. **Circuit breaker timeouts** (30-60s) → Use fast_resilience_config
2. **Retry delays** (3 attempts × retries) → Mock retry logic
3. **Real LangGraph execution** (14-29s) → Mock graph components
4. **Sleep/time.sleep()** → Use freezegun
5. **Real I/O** (network, disk, DB) → Use mocks
6. **Large datasets** → Use smaller test data

How to fix:
1. Identify: pytest --durations=20
2. Analyze: Look at test implementation
3. Optimize: Apply appropriate technique above

Related:
- tests/meta/test_performance_regression_suite.py - Suite-level performance
- tests/conftest.py:fast_resilience_config - Fast CB configuration
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = [pytest.mark.unit, pytest.mark.meta]


@pytest.mark.meta
@pytest.mark.performance
def test_no_slow_unit_tests():
    """
    Test that no individual unit test takes > 10 seconds.

    This catches performance regressions at the individual test level.

    Known slow tests (to be optimized in future):
    - OpenFGA circuit breaker tests: 45s (retry logic optimization needed)
    - Agent tests: 14-29s (LangGraph mocking needed)
    - Retry timing test: 14s (freezegun needed)

    These are documented and tracked. New slow tests should not be added.
    """
    # Skip in xdist workers
    if os.getenv("PYTEST_XDIST_WORKER"):
        pytest.skip("Slow test detection must run sequentially")

    project_root = Path(__file__).parent.parent.parent
    assert (project_root / "pyproject.toml").exists()

    # Run unit tests with detailed timing
    result = subprocess.run(
        [
            "pytest",
            "-m",
            "unit",
            "--durations=0",  # Show all durations
            "-q",
            "--tb=no",
            "--no-header",
            "-x",  # Stop on first failure for faster feedback
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=300,  # 5 minute timeout
    )

    output = result.stdout + result.stderr

    # Parse test durations
    # Format: "0.12s call     tests/test_file.py::test_name"
    duration_pattern = r"([\d.]+)s\s+call\s+(.+?)(?:\s|$)"
    slow_tests = []

    for line in output.split("\n"):
        match = re.search(duration_pattern, line)
        if match:
            duration = float(match.group(1))
            test_name = match.group(2).strip()

            # Threshold: 10 seconds
            if duration > 10.0:
                slow_tests.append((test_name, duration))

    # Known slow tests (documented, tracked for future optimization)
    KNOWN_SLOW_TESTS = {
        # OpenFGA circuit breaker tests: OPTIMIZED (45s → <3s with fast_retry_config) ✅
        # - test_circuit_breaker_fails_closed_for_critical_resources
        # - test_circuit_breaker_fails_open_for_non_critical_resources
        # - test_circuit_breaker_defaults_to_critical_true
        # Phase 3 optimization complete (2025-11-15)
        # Agent tests: 14-29s each (needs LangGraph mocking)
        "tests/test_agent.py::TestAgentGraph::test_agent_with_langsmith_enabled",
        "tests/test_agent.py::TestAgentGraph::test_handles_very_long_conversation_history",
        "tests/test_agent.py::TestAgentGraph::test_agent_without_langsmith",
        "tests/test_agent.py::TestAgentGraph::test_route_input_to_tools",
        "tests/test_agent.py::TestAgentGraph::test_handles_missing_optional_fields",
        "tests/test_agent.py::TestAgentGraph::test_route_with_calculate_keyword",
        "tests/test_agent.py::TestAgentGraph::test_route_input_to_respond",
        "tests/test_agent.py::TestAgentGraph::test_agent_with_conversation_history",
        # Retry timing test: OPTIMIZED (14s → 0.56s with mocked asyncio.sleep) ✅
        # - test_exponential_backoff_timing (removed, now fast)
        # Phase 3 optimization complete (2025-11-15)
    }

    # Filter out known slow tests
    new_slow_tests = [(name, duration) for name, duration in slow_tests if name not in KNOWN_SLOW_TESTS]

    if new_slow_tests:
        error_msg = (
            f"Found {len(new_slow_tests)} new slow tests (> 10s):\n\n" "These tests should be optimized before merging:\n\n"
        )

        for test_name, duration in sorted(new_slow_tests, key=lambda x: x[1], reverse=True):
            error_msg += f"  {duration:6.2f}s  {test_name}\n"

        error_msg += (
            "\n"
            "Optimization strategies:\n"
            "1. Circuit breaker tests → Use fast_resilience_config fixture\n"
            "2. Retry tests → Use freezegun to mock time\n"
            "3. Agent tests → Mock ContextManager/OutputVerifier\n"
            "4. I/O operations → Use mocks instead of real I/O\n"
            "5. Sleep calls → Use freezegun or remove entirely\n"
        )

        pytest.fail(error_msg)

    # Log known slow tests for visibility
    if slow_tests:
        print(f"\n⚠️  Found {len(slow_tests)} known slow tests (documented for future optimization):")
        for test_name, duration in sorted(slow_tests, key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {duration:6.2f}s  {test_name}")

    print(f"\n✅ No new slow tests detected (checked {len(slow_tests)} known slow tests)")
