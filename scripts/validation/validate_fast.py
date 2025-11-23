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
SCRIPTS = [
    "scripts/validation/validate_pytest_config.py",
    "scripts/validation/validate_pre_push_hook.py",
    "scripts/validation/validate_repo_root_calculations.py",
    "scripts/validation/validate_test_time_bombs.py",
    "scripts/validation/validate_async_fixture_scope.py",
    "scripts/validation/validate_migration_idempotency.py",
    "scripts/validation/validate_api_schemas.py",
    "scripts/validation/check_async_mock_usage.py",
    "scripts/validation/check_test_memory_safety.py",
    "scripts/validation/validate_serviceaccount_names.py",
    "scripts/validation/validate_test_ids.py",
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
