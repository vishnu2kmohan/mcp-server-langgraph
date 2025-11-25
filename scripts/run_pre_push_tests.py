#!/usr/bin/env python3
"""
Pre-push test orchestrator - consolidates 5 separate pytest sessions into one.

This script addresses OpenAI Codex Finding 2a: Duplicate pytest sessions.

Problem:
  .pre-commit-config.yaml had 5 separate pytest invocations which caused:
  - 5x test discovery overhead (10-25s wasted)
  - 5 separate Python interpreter processes
  - Lock contention on .pytest_cache and .coverage files

  Each session performed full test discovery, causing:
  - 5x test discovery overhead (10-25s wasted)
  - 5 separate Python interpreter processes
  - Lock contention on .pytest_cache and .coverage files

Solution:
  Single pytest session with combined marker logic:
  - Discovers tests once (2-5s instead of 10-25s)
  - Single Python process with xdist workers
  - No cache/coverage lock contention
  - Same test coverage as before

Time savings: 8-20 seconds per pre-push

Environment variables:
  - OTEL_SDK_DISABLED=true (set by pre-commit hook)
  - CI_PARITY=1 (optional: run integration tests if Docker available)

Usage:
  # Via pre-commit hook (automatic)
  git push

  # Manual invocation
  python scripts/run_pre_push_tests.py

  # With integration tests (if Docker available)
  CI_PARITY=1 python scripts/run_pre_push_tests.py
"""

import os
import subprocess
import sys


def check_docker_available() -> bool:
    """Check if Docker daemon is available."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def should_run_meta_tests() -> bool:
    """
    Check if meta tests should run based on changed files.

    Meta tests validate test infrastructure (hooks, CI workflows, fixtures, etc.)
    They should run when workflow-related files change, but can be skipped for
    regular code changes to maintain fast pre-push validation.

    Modern Best Practice (Phase 3.1 refactor - 2025-11-24):
    Uses 3-level fallback strategy to determine changed files:
    1. PRE_COMMIT_FROM_REF/TO_REF (provided by pre-commit during hooks)
    2. git merge-base @{u} HEAD (shows unpushed changes)
    3. git diff HEAD (fallback for detached/local branches)

    Returns:
        True if workflow files changed (run meta tests)
        False if only non-workflow files changed (skip meta tests for performance)

    Workflow-related patterns that trigger meta tests:
    - .github/ (CI workflows, actions)
    - .pre-commit-config.yaml (hook configuration)
    - pytest.ini or pyproject.toml (test configuration)
    - tests/conftest.py (shared fixtures)

    Reference: Codex Audit Finding - Make/Test Flow Issue 1.4
    Reference: Phase 3.1 - Modern best practice with pre-commit alignment
    """
    # Workflow-related files that trigger meta tests
    workflow_patterns = [
        ".github/",
        ".pre-commit-config.yaml",
        "pytest.ini",
        "pyproject.toml",
        "tests/conftest.py",
    ]

    # Strategy 1: Use PRE_COMMIT_FROM_REF/TO_REF if available (during pre-commit hook execution)
    from_ref = os.getenv("PRE_COMMIT_FROM_REF")
    to_ref = os.getenv("PRE_COMMIT_TO_REF")

    try:
        if from_ref and to_ref:
            # Pre-commit provides exact ref range being pushed
            result = subprocess.run(
                ["git", "diff", "--name-only", from_ref, to_ref],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
        else:
            # Strategy 2: Try merge-base with upstream tracking branch
            # This shows all changes since last push to upstream
            try:
                merge_base_result = subprocess.run(
                    ["git", "merge-base", "@{u}", "HEAD"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=5,
                )
                merge_base = merge_base_result.stdout.strip()
                result = subprocess.run(
                    ["git", "diff", "--name-only", merge_base, "HEAD"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=5,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                # Strategy 3: Final fallback to diff HEAD (detached HEAD, no upstream, etc.)
                result = subprocess.run(
                    ["git", "diff", "--name-only", "HEAD"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=5,
                )
    except subprocess.TimeoutExpired:
        # Can't determine changes, run meta tests to be safe
        return True

    if result.returncode != 0:
        # Can't determine changes, run meta tests to be safe
        return True

    changed_files = result.stdout.strip().split("\n") if result.stdout.strip() else []

    # Check if any workflow file changed
    for changed_file in changed_files:
        for pattern in workflow_patterns:
            if pattern in changed_file:
                return True

    return False


def is_quiet_mode() -> bool:
    """
    Check if quiet mode should be enabled.

    Quiet mode suppresses verbose pytest output while still showing errors/failures.
    This prevents BlockingIOError when git push output buffer fills up.

    Quiet mode is enabled when:
    - QUIET_MODE=1 environment variable is set
    - Running inside a pre-commit hook (GIT_AUTHOR_NAME set by git)
    - Output is not a TTY (piped/redirected)

    Returns:
        True if quiet mode should be enabled
    """
    # Explicit environment variable
    if os.getenv("QUIET_MODE") == "1":
        return True

    # Running in pre-commit hook context (pre-commit sets this)
    if os.getenv("PRE_COMMIT") == "1":
        return True

    # Output is piped/redirected (not a terminal)
    if not sys.stdout.isatty():
        return True

    return False


def main() -> int:
    """
    Run consolidated pre-push test suite.

    Returns:
        0 if all tests pass, non-zero otherwise
    """
    # Check if quiet mode should be enabled
    quiet = is_quiet_mode()

    # Build pytest arguments
    # NOTE: --testmon removed due to pytest-xdist incompatibility (Codex Audit 2025-11-24)
    # Testmon's change tracking doesn't work reliably with xdist's worker isolation.
    # This can lead to tests being skipped incorrectly or stale cache issues after branch switches.
    # Trade-off: Slightly longer test runs (~10-15% slower) but guaranteed correctness.
    # See: docs-internal/HOOK_PERFORMANCE_OPTIMIZATION_PLAN.md:392-409
    pytest_args = [
        "pytest",
        "-n",
        "auto",  # Parallel execution with pytest-xdist
        "-x",  # Stop on first failure (fail-fast)
    ]

    if quiet:
        # Quiet mode: minimal output, but show errors/failures/warnings
        pytest_args.extend(
            [
                "-q",  # Quiet mode (dots instead of verbose)
                "--tb=line",  # Single-line tracebacks (still shows errors)
                "--no-header",  # Skip pytest header
            ]
        )
    else:
        # Normal mode: verbose output
        pytest_args.append("--tb=short")  # Short traceback format

    # Combined marker expression that covers all 5 original hooks:
    # 1. unit and not llm (run-unit-tests)
    # 2. smoke tests (run-smoke-tests)
    # 3. api and unit and not llm (run-api-tests)
    # 4. mcp-server tests (run-mcp-server-tests)
    # 5. property tests (run-property-tests)
    #
    # Strategy: Use marker OR logic to combine all test categories
    # Note: Smoke tests are unit tests in tests/smoke/, so covered by "unit"
    # Note: API tests are marked as "api and unit", so covered by "api"
    # Note: MCP server tests are in tests/unit/, marked as unit
    #
    # Codex Audit Fix (2025-11-24): Conditional meta-test inclusion
    # Meta-tests validate infrastructure (git hooks, CI workflows, fixtures, etc.)
    # They should run when workflow files change, but can be skipped for performance
    # when only regular code changes. This prevents workflow drift while maintaining
    # fast pre-push validation.
    #
    # Reference: Codex Audit Finding - Make/Test Flow Issue 1.4
    if should_run_meta_tests():
        # Workflow files changed - include meta tests for infrastructure validation
        # Exclude integration tests - they require Docker infrastructure (use CI_PARITY=1 to include)
        marker_expression = "(unit or api or property or meta) and not llm and not integration"
        if not quiet:
            print("🔍 Workflow files changed - including meta tests (infrastructure validation)")
    else:
        # Only code files changed - skip meta tests for performance
        # Exclude integration tests - they require Docker infrastructure (use CI_PARITY=1 to include)
        marker_expression = "(unit or api or property) and not llm and not meta and not integration"

    # Store marker index for later modification (CI_PARITY support)
    marker_index = len(pytest_args) + 1  # +1 because "-m" is inserted first
    pytest_args.extend(["-m", marker_expression])

    # Specify test directory
    pytest_args.append("tests/")

    # Check for CI_PARITY=1 to include integration tests
    ci_parity = os.getenv("CI_PARITY") == "1"
    if ci_parity:
        # User requested CI-equivalent validation
        if check_docker_available():
            if not quiet:
                print("▶ CI_PARITY=1 detected: Including integration tests (Docker available)")
            # Add integration marker to expression (but still exclude meta-tests)
            # (unit or api or property or integration) and not llm and not meta
            marker_expression = "(unit or api or property or integration) and not llm and not meta"
            pytest_args[marker_index] = marker_expression  # Use stored index instead of fragile .index()
        else:
            if not quiet:
                print("⚠  CI_PARITY=1 detected but Docker unavailable")
                print("✓ Will run: unit, api, property tests")
                print("✗ Won't run: integration tests (require Docker daemon)")
                print("→ Action: Start Docker Desktop or omit CI_PARITY=1 for faster pre-push")

    # Ensure OTEL_SDK_DISABLED and HYPOTHESIS_PROFILE for consistent environment
    env = os.environ.copy()
    env["OTEL_SDK_DISABLED"] = "true"
    # Prevent BlockingIOError when pre-commit captures massive output
    env["PYTHONUNBUFFERED"] = "1"

    # Codex Finding #4 Fix (2025-11-23): Environment-aware Hypothesis profiles
    # Use dev profile (25 examples) locally for faster iteration
    # Use ci profile (100 examples) in CI or when explicitly requested
    if "HYPOTHESIS_PROFILE" not in env:
        # Auto-detect: Use CI profile in CI/CD or when CI_PARITY requested
        if env.get("CI") or env.get("CI_PARITY") == "1":
            env["HYPOTHESIS_PROFILE"] = "ci"
        else:
            env["HYPOTHESIS_PROFILE"] = "dev"  # Fast iteration for local dev

    hypothesis_profile = env["HYPOTHESIS_PROFILE"]
    examples_count = "100" if hypothesis_profile == "ci" else "25"

    # Run pytest via uv run (auto-syncs if needed)
    if not quiet:
        print(f"▶ Running consolidated pre-push tests: {' '.join(pytest_args)}")
        print(f"  Marker expression: {marker_expression}")
        print(f"  Hypothesis profile: {hypothesis_profile} ({examples_count} examples)")
        if hypothesis_profile == "dev":
            print("  💡 Tip: Use CI_PARITY=1 git push for full CI validation (100 examples)")
        print()

    result = subprocess.run(
        ["uv", "run"] + pytest_args,
        env=env,
    )

    if result.returncode == 0:
        if not quiet:
            print()
            print("✓ All pre-push tests passed")
            print("  Tests consolidated from 5 sessions → 1 session (8-20s faster)")
    else:
        # Always show failure message (even in quiet mode)
        print()
        print("✗ Pre-push tests failed")
        print("  Fix failing tests before pushing")

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
