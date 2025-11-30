#!/usr/bin/env python3
"""
Consolidated fast validator runner.
Runs multiple lightweight validation scripts in a single process/environment
to minimize pre-commit overhead.
"""

import sys
import subprocess
from pathlib import Path
import time

REPO_ROOT = Path(__file__).resolve().parents[2]

# List of scripts to run.
# Ensure these scripts accept no arguments or have default behavior suitable for 'all files' check.
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
SCRIPTS = [
    "scripts/validators/validate_pre_push_hook.py",
    "scripts/validators/validate_repo_root_calculations.py",
    "scripts/validators/validate_test_time_bombs.py",
    "scripts/validators/validate_async_fixture_scope.py",
    "scripts/validators/validate_migration_idempotency.py",
    "scripts/validators/validate_api_schemas.py",
    "scripts/validators/validate_serviceaccount_names.py",
]


def run_script(script_rel_path):
    script_path = REPO_ROOT / script_rel_path
    if not script_path.exists():
        print(f"⚠️  Script not found: {script_rel_path}")
        return 1

    print(f"▶ Running {script_rel_path}...")
    start = time.time()
    try:
        # Run with same python interpreter
        result = subprocess.run([sys.executable, str(script_path)], cwd=REPO_ROOT, capture_output=True, text=True)
        duration = time.time() - start

        if result.returncode == 0:
            print(f"  ✓ Passed ({duration:.2f}s)")
            return 0
        else:
            print(f"  ✗ Failed ({duration:.2f}s)")
            # Indent output
            if result.stdout:
                print("    " + result.stdout.replace("\n", "\n    "))
            if result.stderr:
                print("    " + result.stderr.replace("\n", "\n    "))
            return result.returncode
    except Exception as e:
        print(f"  ✗ Error running script: {e}")
        return 1


def main():
    failures = 0
    print(f"🚀 Running consolidated fast validators ({len(SCRIPTS)} checks)...")
    print("   Note: 4 validators run as individual hooks (validate-pytest-config, check-test-memory-safety,")
    print("         check-async-mock-usage, validate-test-ids) for better fail-fast behavior")
    print("-" * 60)

    for script in SCRIPTS:
        if run_script(script) != 0:
            failures += 1

    print("-" * 60)
    if failures == 0:
        print("✅ All fast validators passed")
        return 0
    else:
        print(f"❌ {failures} validator(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
