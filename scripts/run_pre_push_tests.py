#!/usr/bin/env python3
"""
Pre-push test orchestrator - consolidates 21 separate pytest sessions into one.

This script addresses OpenAI Codex Finding 2a: Duplicate pytest sessions.

Problem:
  .pre-commit-config.yaml had 21 separate pytest invocations which caused:
  - 21x test discovery overhead (~4.5 minutes wasted)
  - 21 separate Python interpreter processes
  - Lock contention on .pytest_cache and .coverage files

Solution:
  Single pytest session with combined marker logic:
  - Discovers tests once (~13s instead of ~4.5 min)
  - Single Python process with xdist workers
  - No cache/coverage lock contention
  - Same test coverage as before

Time savings: ~4 minutes per pre-push

Consolidated test categories:
  - unit: Unit tests (fast, no external dependencies)
  - api: API endpoint tests
  - property: Property-based tests (Hypothesis)
  - validation: Deployment/configuration validation tests (Helm, Kustomize, etc.)
  - meta: Meta tests (conditionally, when workflow files change)

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

  # Run all tests without stopping on first failure (CI diagnostics)
  python scripts/run_pre_push_tests.py --no-fail-fast
"""

import argparse
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


def matches_workflow_pattern(changed_file: str) -> bool:
    """
    Check if a changed file matches workflow/infrastructure patterns.

    This function determines whether a file change should trigger meta test
    execution during pre-push validation.

    Args:
        changed_file: Path to the changed file (relative to repo root)

    Returns:
        True if the file is infrastructure-related and should trigger meta tests
        False if the file is regular source/test code

    Patterns that trigger meta tests:
    - .github/ (CI workflows, actions)
    - scripts/validators/ (validation scripts)
    - scripts/security/ (security scanning scripts)
    - scripts/run_pre_push_tests.py (this orchestrator)
    - .githooks/ (git hook scripts)
    - .pre-commit-hooks/ (pre-commit hook scripts)
    - .pre-commit-config.yaml (hook configuration)
    - pytest.ini (test configuration)
    - pyproject.toml (root only, not clients/*/pyproject.toml)
    - Makefile (build/test targets)
    - tests/**/conftest.py (fixture files at any level)

    Reference: Codex Audit - Change detection gaps (2025-12-01)
    Reference: P0-1 - Pre-commit/Pre-push Hook & CI Pipeline Remediation Plan
    """
    # Directory patterns (prefix match)
    workflow_dirs = [
        ".github/",
        "scripts/validators/",
        "scripts/security/",
        ".githooks/",
        ".pre-commit-hooks/",
    ]
    for dir_prefix in workflow_dirs:
        if changed_file.startswith(dir_prefix):
            return True

    # Any conftest.py in tests/ (root or subdirectories)
    if changed_file.startswith("tests/") and changed_file.endswith("conftest.py"):
        return True

    # Exact file patterns (not substring match)
    exact_patterns = [
        ".pre-commit-config.yaml",
        "pytest.ini",
        "pyproject.toml",  # Only root pyproject.toml, not clients/*/pyproject.toml
        "Makefile",
        "scripts/run_pre_push_tests.py",
    ]
    return changed_file in exact_patterns


def should_run_meta_tests() -> bool:
    """
    Check if meta tests should run based on changed files.

    Meta tests validate test infrastructure (hooks, CI workflows, fixtures, etc.)
    They should run when workflow-related files change, but can be skipped for
    regular code changes to maintain fast pre-push validation.

    Enhanced Fallback Strategy (P0-1 fix - 2025-11-27):
    Uses 4-level fallback strategy to determine changed files:
    1. PRE_COMMIT_FROM_REF/TO_REF (provided by pre-commit during hooks)
    2. git merge-base @{u} HEAD (shows unpushed changes)
    3. git merge-base origin/main HEAD (for new branches without upstream)
    4. git show --name-only HEAD (shows last commit's files)

    Returns:
        True if workflow files changed (run meta tests)
        False if only non-workflow files changed (skip meta tests for performance)

    Reference: Codex Audit Finding - Make/Test Flow Issue 1.4
    Reference: P0-1 - Pre-commit/Pre-push Hook & CI Pipeline Remediation Plan
    """

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
                # Strategy 3: Try merge-base with origin/main (for new branches)
                try:
                    merge_base_result = subprocess.run(
                        ["git", "merge-base", "origin/main", "HEAD"],
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
                    # Strategy 4: Final fallback to git show (shows last commit)
                    # Better than git diff HEAD which shows uncommitted changes
                    result = subprocess.run(
                        ["git", "show", "--name-only", "--format=", "HEAD"],
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
        if matches_workflow_pattern(changed_file):
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


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run consolidated pre-push test suite.",
        epilog="Reference: Codex Audit Finding 2a - Duplicate pytest sessions",
    )
    parser.add_argument(
        "--no-fail-fast",
        action="store_true",
        help="Run all tests even if some fail (useful for CI diagnostics)",
    )
    return parser.parse_args()


def sync_dev_dependencies(quiet: bool = False) -> bool:
    """
    Sync dev dependencies to ensure CI parity.

    Pre-push hook uses `uv run --frozen` which relies on existing venv state.
    CI explicitly installs dev extras via `uv sync --frozen --extra dev`.
    This function ensures local pre-push has the same dependencies as CI.

    Added 2025-11-28 to fix CI parity gap where tests could fail locally
    due to missing dev dependencies (e.g., yamllint) that CI always has.

    Args:
        quiet: If True, suppress output messages.

    Returns:
        True if sync succeeded, False otherwise.
    """
    if not quiet:
        print("▶ Syncing dev dependencies for CI parity...")

    result = subprocess.run(
        ["uv", "sync", "--frozen", "--extra", "dev"],
        capture_output=quiet,
        timeout=120,  # 2 minute timeout for sync
    )

    if result.returncode != 0:
        print("✗ Failed to sync dev dependencies")
        if quiet and result.stderr:
            print(result.stderr.decode())
        return False

    if not quiet:
        print("✓ Dev dependencies synced")

    return True


def main() -> int:
    """
    Run consolidated pre-push test suite.

    Returns:
        0 if all tests pass, non-zero otherwise
    """
    # Parse command-line arguments
    args = parse_args()

    # Check if quiet mode should be enabled
    quiet = is_quiet_mode()

    # Sync dev dependencies for CI parity (added 2025-11-28)
    # This ensures pre-push tests have the same dependencies as CI.
    # Without this, tests could fail due to missing dev dependencies
    # (e.g., yamllint) that CI always has via `uv sync --extra dev`.
    if not sync_dev_dependencies(quiet):
        return 1

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
    ]

    # P2-2 (2025-11-27): Configurable fail-fast behavior
    # Default: -x (stop on first failure) for fast feedback during development
    # --no-fail-fast: Run all tests even if some fail (useful for CI diagnostics)
    if not args.no_fail_fast:
        pytest_args.append("-x")  # Stop on first failure (fail-fast)

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

    # Combined marker expression that consolidates 21 separate pytest hooks:
    #
    # Always included:
    # - unit: Unit tests (fast, no external dependencies)
    # - api: API endpoint tests
    # - property: Property-based tests (Hypothesis)
    # - validation: Deployment/configuration validation tests
    #
    # Conditionally included:
    # - meta: Meta tests (only when workflow files change)
    #
    # Excluded:
    # - llm: LLM tests (expensive, require API keys)
    # - integration: Integration tests (require Docker, use CI_PARITY=1 to include)
    #
    # This consolidation reduces test discovery overhead from ~4.5 min to ~13 sec.
    # Reference: Codex Audit Finding - Make/Test Flow Issue 1.4
    if should_run_meta_tests():
        # Workflow files changed - include meta tests for infrastructure validation
        marker_expression = "(unit or api or property or validation or meta) and not llm and not integration"
        if not quiet:
            print("🔍 Workflow files changed - including meta tests (infrastructure validation)")
    else:
        # Only code files changed - skip meta tests for performance
        marker_expression = "(unit or api or property or validation) and not llm and not meta and not integration"

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
            marker_expression = "(unit or api or property or validation or integration) and not llm and not meta"
            pytest_args[marker_index] = marker_expression  # Use stored index instead of fragile .index()
        else:
            if not quiet:
                print("⚠  CI_PARITY=1 detected but Docker unavailable")
                print("✓ Will run: unit, api, property, validation tests")
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
            print("  Tests consolidated from 21 sessions → 1 session (~4 min faster)")
    else:
        # Always show failure message (even in quiet mode)
        print()
        print("✗ Pre-push tests failed")
        print("  Fix failing tests before pushing")

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
