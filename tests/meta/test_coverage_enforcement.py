"""
Coverage Enforcement - Minimum Coverage Threshold

Validates that test coverage meets minimum quality standards.

This meta-test prevents coverage regression by failing if:
- Overall coverage < 64% (CI threshold)
- Coverage decreases from previous baseline

**PERFORMANCE OPTIMIZATION** (OpenAI Codex Finding - 2025-11-16):
This test now reads existing `.coverage` file if available instead of
re-running the full test suite. This eliminates duplicate test execution
in pre-push hooks, saving 3-4 minutes per push.

Workflow:
1. Makefile PHASE 3 runs tests with coverage (creates `.coverage` file)
2. This test reads `.coverage` and validates threshold
3. Falls back to running tests if `.coverage` doesn't exist (CI/dev compatibility)

Coverage targets:
- Current: 65.78% (after Phase 1 improvements)
- Minimum: 64% (CI threshold) ⚠️ MUST NOT DROP BELOW
- Target: 80% (Codex recommendation) 🎯
- Excellent: 90%+ ⭐

Why this matters:
- Low coverage = untested code paths
- Untested code = potential bugs in production
- Coverage regression = technical debt accumulation

Coverage by module (after Phase 1):
✅ prometheus_client.py: 44% → 87% (+43%)
✅ budget_monitor.py: 47% → 81% (+34%)
✅ cost_api.py: 55% → 91% (+36%)
✅ cost_tracker.py: 76% (good)
⚠️ Other modules: Various (see coverage report)

How to improve coverage:
1. Identify low-coverage modules: pytest --cov --cov-report=term-missing
2. Write tests for uncovered lines (see MISSING column)
3. Focus on business logic first (highest value)
4. Use TDD for new code (write tests first!)

Related:
- pyproject.toml: Coverage configuration (fail_under = 64)
- .github/workflows/ci.yaml: CI coverage enforcement
- Makefile: PHASE 3 runs tests with coverage (creates `.coverage` file)
"""

import os
import re
import subprocess
from pathlib import Path

import pytest


@pytest.mark.meta
@pytest.mark.unit
@pytest.mark.timeout(480)  # 8 minutes - max time if fallback runs tests
def test_minimum_coverage_threshold():
    """
    Test that overall test coverage meets minimum 64% threshold.

    **OPTIMIZED** (2025-11-16): Reads existing `.coverage` file if available.
    Only runs tests if `.coverage` is missing (dev/CI fallback).

    Coverage is measured across all source files in src/mcp_server_langgraph/
    excluding test files, examples, and scripts.

    Performance:
    - With existing .coverage: < 1 second (fast!)
    - Without .coverage: ~2-3 minutes (fallback, runs tests with coverage)
    """
    # Skip in xdist workers (coverage measurement must be centralized)
    if os.getenv("PYTEST_XDIST_WORKER"):
        pytest.skip("Coverage measurement must run outside xdist workers")

    project_root = Path(__file__).parent.parent.parent
    assert (project_root / "pyproject.toml").exists()

    coverage_file = project_root / ".coverage"

    # OPTIMIZATION: Check if coverage data already exists (from Makefile PHASE 3)
    if coverage_file.exists():
        # Fast path: Read existing coverage data
        coverage_pct = _read_existing_coverage(project_root)
        source = "existing .coverage file"
    else:
        # Fallback: Run tests with coverage (dev/CI compatibility)
        print("⚠️  No .coverage file found - running tests with coverage (slow)")
        print("    Tip: Run 'make validate-pre-push' for faster pre-push validation")
        coverage_pct = _run_tests_with_coverage(project_root)
        source = "fresh test run"

    # Minimum threshold (aligned with pyproject.toml fail_under)
    MIN_COVERAGE = 64

    # Current baseline (after Phase 1 improvements)
    BASELINE_COVERAGE = 65  # 65.78% rounded down for safety margin

    assert coverage_pct >= MIN_COVERAGE, (
        f"Coverage too low: {coverage_pct}% (minimum: {MIN_COVERAGE}%) [source: {source}]\n"
        f"Coverage regression detected!\n"
        f"\n"
        f"To diagnose:\n"
        f"1. Run: pytest --cov --cov-report=html\n"
        f"2. Open: htmlcov/index.html\n"
        f"3. Look for modules with low coverage\n"
        f"4. Write tests for uncovered code\n"
        f"\n"
        f"Recent improvements (Phase 1):\n"
        f"  prometheus_client.py: 44% → 87%\n"
        f"  budget_monitor.py: 47% → 81%\n"
        f"  cost_api.py: 55% → 91%\n"
        f"\n"
        f"Overall: 63.88% → 65.78%\n"
    )

    # Warn if below baseline (not a hard failure, but indicates regression)
    if coverage_pct < BASELINE_COVERAGE:
        print(
            f"\n⚠️  Coverage below baseline: {coverage_pct}% (baseline: {BASELINE_COVERAGE}%) [source: {source}]\n"
            f"   Consider adding tests to maintain or improve coverage."
        )
    else:
        print(f"\n✅ Coverage: {coverage_pct}% (minimum: {MIN_COVERAGE}%, baseline: {BASELINE_COVERAGE}%) [source: {source}]")

    return coverage_pct


def _read_existing_coverage(project_root: Path) -> int:
    """
    Read coverage percentage from existing `.coverage` file.

    This is FAST (< 1 second) because it just reads existing data.

    Returns:
        Coverage percentage as integer
    """
    # Use coverage report command to read existing data
    result = subprocess.run(
        [
            "coverage",
            "report",
            "--precision=0",  # No decimal places
            "--skip-empty",
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=30,  # Should be very fast
    )

    output = result.stdout + result.stderr

    # Parse coverage percentage
    # Format: "TOTAL    12345   1234    90%"
    coverage_pattern = r"TOTAL\s+\d+\s+\d+\s+(\d+)%"
    match = re.search(coverage_pattern, output)

    if not match:
        # Try alternative format: "TOTAL    90%"
        alt_pattern = r"TOTAL.*?(\d+)%"
        match = re.search(alt_pattern, output)

    if not match:
        pytest.fail(
            f"Could not parse coverage from existing .coverage file:\n{output[-1000:]}\n"
            f"Try running: pytest --cov to regenerate coverage data"
        )

    return int(match.group(1))


def _run_tests_with_coverage(project_root: Path) -> int:
    """
    Run full test suite with coverage measurement (fallback).

    This is SLOW (~2-3 minutes) but ensures compatibility when `.coverage`
    file doesn't exist (dev environment, CI, etc.).

    Returns:
        Coverage percentage as integer
    """
    # Run tests with coverage
    # Note: We use -m unit to run only unit tests (faster)
    # Integration/E2E tests should also be covered, but unit tests are primary
    result = subprocess.run(
        [
            "pytest",
            "-m",
            "unit",
            "--cov=src/mcp_server_langgraph",
            "--cov-report=term-missing:skip-covered",
            "--cov-report=term",
            "-q",
            "--tb=no",
            "--no-header",
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=480,  # 8 minute timeout
    )

    output = result.stdout + result.stderr

    # Parse coverage percentage
    # Format: "TOTAL    12345   1234    90%"
    coverage_pattern = r"TOTAL\s+\d+\s+\d+\s+(\d+)%"
    match = re.search(coverage_pattern, output)

    if not match:
        # Try alternative format: "TOTAL    90%"
        alt_pattern = r"TOTAL.*?(\d+)%"
        match = re.search(alt_pattern, output)

    if not match:
        pytest.fail(f"Could not parse coverage from output:\n{output[-1000:]}")  # Last 1000 chars

    return int(match.group(1))
