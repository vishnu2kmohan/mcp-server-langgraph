#!/usr/bin/env python3
"""
Consolidated fast validator runner.

Runs multiple lightweight validation scripts to minimize pre-commit overhead.
Supports two execution modes:
- Inline (default): Imports and calls validator main() functions directly
- Subprocess: Spawns separate Python processes (legacy, for debugging)

Performance Improvement (Phase 4 - 2025-12-01):
- Inline mode eliminates ~350-700ms subprocess overhead (7 interpreter startups)
- Expected time savings: 8-17% on ~4s baseline
"""

import inspect
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# List of validator modules to run.
# Each module must have a main() function that returns 0 (pass), 1 (fail), or 2 (error).
#
# Deduplication (2025-11-23 - Codex Finding #1):
# Removed 4 validators that are also registered as individual hooks in .pre-commit-config.yaml:
# - validate_pytest_config.py → individual hook: validate-pytest-config (line 1565)
# - check_test_memory_safety.py → individual hook: check-test-memory-safety (line 1576)
# - check_async_mock_usage.py → individual hook: check-async-mock-usage (line 1587)
# - validate_test_ids.py → individual hook: validate-test-ids (line 1619)
#
# These run as individual hooks for better fail-fast behavior and clearer error messages.
# validate-fast now focuses on lightweight validators without dedicated hooks.
VALIDATORS = [
    ("validate_pre_push_hook", "scripts.validators.validate_pre_push_hook"),
    ("validate_repo_root_calculations", "scripts.validators.validate_repo_root_calculations"),
    ("validate_test_time_bombs", "scripts.validators.validate_test_time_bombs"),
    ("validate_async_fixture_scope", "scripts.validators.validate_async_fixture_scope"),
    ("validate_migration_idempotency", "scripts.validators.validate_migration_idempotency"),
    ("validate_api_schemas", "scripts.validators.validate_api_schemas"),
    ("validate_serviceaccount_names", "scripts.validators.validate_serviceaccount_names"),
]

# Legacy: Script paths for subprocess mode
SCRIPTS = [
    "scripts/validators/validate_pre_push_hook.py",
    "scripts/validators/validate_repo_root_calculations.py",
    "scripts/validators/validate_test_time_bombs.py",
    "scripts/validators/validate_async_fixture_scope.py",
    "scripts/validators/validate_migration_idempotency.py",
    "scripts/validators/validate_api_schemas.py",
    "scripts/validators/validate_serviceaccount_names.py",
]


def run_validator_inline(name: str, module_path: str) -> tuple[int, float]:
    """
    Run a validator by importing and calling its main() function.

    Args:
        name: Display name for the validator
        module_path: Full module import path (e.g., 'scripts.validators.validate_foo')

    Returns:
        Tuple of (exit_code, duration_seconds)
    """
    import importlib

    # Ensure repo root is in Python path for module imports
    repo_root_str = str(REPO_ROOT)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

    print(f"▶ Running {name}...")
    start = time.time()

    try:
        module = importlib.import_module(module_path)
        main_fn = module.main

        # Check if main() accepts arguments (for argparse validators)
        sig = inspect.signature(main_fn)
        if sig.parameters:
            result = main_fn([])  # Pass empty list for argparse validators
        else:
            result = main_fn()

        duration = time.time() - start

        if result == 0:
            print(f"  ✓ Passed ({duration:.2f}s)")
        else:
            print(f"  ✗ Failed ({duration:.2f}s)")

        return result, duration

    except Exception as e:
        duration = time.time() - start
        print(f"  ✗ Error ({duration:.2f}s): {e}")
        return 2, duration


def run_validators_inline() -> int:
    """
    Run all validators using inline mode (direct function calls).

    Returns:
        0 if all validators pass, 1 if any fail
    """
    failures = 0
    total_time = 0.0

    print(f"🚀 Running consolidated fast validators ({len(VALIDATORS)} checks) [inline mode]...")
    print("   Note: 4 validators run as individual hooks (validate-pytest-config, check-test-memory-safety,")
    print("         check-async-mock-usage, validate-test-ids) for better fail-fast behavior")
    print("-" * 60)

    for name, module_path in VALIDATORS:
        result, duration = run_validator_inline(name, module_path)
        total_time += duration
        if result != 0:
            failures += 1

    print("-" * 60)
    if failures == 0:
        print(f"✅ All fast validators passed ({total_time:.2f}s total)")
        return 0
    else:
        print(f"❌ {failures} validator(s) failed ({total_time:.2f}s total)")
        return 1


def run_script_subprocess(script_rel_path: str) -> tuple[int, float]:
    """
    Run a validator as a subprocess (legacy mode).

    Args:
        script_rel_path: Relative path to the script from repo root

    Returns:
        Tuple of (exit_code, duration_seconds)
    """
    script_path = REPO_ROOT / script_rel_path
    if not script_path.exists():
        print(f"⚠️  Script not found: {script_rel_path}")
        return 1, 0.0

    print(f"▶ Running {script_rel_path}...")
    start = time.time()
    try:
        result = subprocess.run([sys.executable, str(script_path)], cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)
        duration = time.time() - start

        if result.returncode == 0:
            print(f"  ✓ Passed ({duration:.2f}s)")
            return 0, duration
        else:
            print(f"  ✗ Failed ({duration:.2f}s)")
            if result.stdout:
                print("    " + result.stdout.replace("\n", "\n    "))
            if result.stderr:
                print("    " + result.stderr.replace("\n", "\n    "))
            return result.returncode, duration
    except subprocess.TimeoutExpired:
        duration = time.time() - start
        print(f"  ✗ Timeout after {duration:.2f}s")
        return 2, duration
    except Exception as e:
        duration = time.time() - start
        print(f"  ✗ Error running script: {e}")
        return 1, duration


def run_validators_subprocess() -> int:
    """
    Run all validators using subprocess mode (legacy, for debugging).

    Returns:
        0 if all validators pass, 1 if any fail
    """
    failures = 0
    total_time = 0.0

    print(f"🚀 Running consolidated fast validators ({len(SCRIPTS)} checks) [subprocess mode]...")
    print("   Note: 4 validators run as individual hooks (validate-pytest-config, check-test-memory-safety,")
    print("         check-async-mock-usage, validate-test-ids) for better fail-fast behavior")
    print("-" * 60)

    for script in SCRIPTS:
        result, duration = run_script_subprocess(script)
        total_time += duration
        if result != 0:
            failures += 1

    print("-" * 60)
    if failures == 0:
        print(f"✅ All fast validators passed ({total_time:.2f}s total)")
        return 0
    else:
        print(f"❌ {failures} validator(s) failed ({total_time:.2f}s total)")
        return 1


def main() -> int:
    """
    Main entry point.

    Uses inline mode by default for performance.
    Set VALIDATE_FAST_SUBPROCESS=1 environment variable to use subprocess mode.
    """
    import os

    if os.environ.get("VALIDATE_FAST_SUBPROCESS") == "1":
        return run_validators_subprocess()
    else:
        return run_validators_inline()


if __name__ == "__main__":
    sys.exit(main())
