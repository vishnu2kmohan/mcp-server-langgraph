#!/usr/bin/env python3
"""
Test ID Pollution Prevention - Pre-commit Validation Script.

This script is a thin wrapper around tests.validation_lib.test_ids module.
All validation logic lives in the shared library for better testability and consistency.

CRITICAL: Hardcoded IDs like "user:alice" or "apikey_test123" in integration tests
cause state pollution in pytest-xdist parallel execution, leading to flaky tests
and intermittent failures when multiple workers access shared databases.

Scope:
- ✅ VALIDATES: Integration tests that interact with real databases/services
- ⏭️  SKIPS: Unit tests with InMemory backends (no pollution risk)
- ⏭️  SKIPS: Mock configurations in unit tests (isolated from external state)
- ⏭️  SKIPS: Assertion validations of response formats

Worker-safe helper usage (for integration tests):
    from tests.conftest import get_user_id, get_api_key_id

    @pytest.mark.integration
    def test_something(db_session):
        user_id = get_user_id()  # ✅ Worker-safe
        apikey_id = get_api_key_id()  # ✅ Worker-safe

Exit codes:
    0: All tests pass (no hardcoded IDs in integration tests)
    1: Validation failed (hardcoded IDs detected in integration tests)

Usage:
    python scripts/validate_test_ids.py tests/test_example.py

Related:
    - tests/conftest.py: Worker-safe ID helper implementations
    - tests/meta/test_id_pollution_prevention.py: Meta-tests for this script
    - .pre-commit-config.yaml: Hook configuration
    - adr/adr-0058-pytest-xdist-state-pollution-prevention.md: Architecture decision
"""

import argparse
import sys
from pathlib import Path

# Add project root to path to enable imports from tests/
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Import validation logic from shared library
import scripts.validators.validate_ids as test_ids  # noqa: E402


def main() -> int:
    """
    Main entry point for validation script.

    Returns:
        Exit code: 0 if all files pass, 1 if any file fails
    """
    parser = argparse.ArgumentParser(description="Validate test files for hardcoded IDs (prevents pytest-xdist pollution)")
    parser.add_argument("files", nargs="*", type=Path, help="Test file(s) to validate")
    args = parser.parse_args()

    files_to_check = args.files
    if not files_to_check:
        # Scan all python files in tests/
        repo_root = Path(__file__).parent.parent.parent
        files_to_check = sorted((repo_root / "tests").rglob("*.py"))

    if not files_to_check:
        print("No test files to check.")
        return 0

    all_passed = True

    for file_path in files_to_check:
        if not file_path.exists():
            print(f"❌ File not found: {file_path}", file=sys.stderr)
            all_passed = False
            continue

        # Only validate Python test files
        if file_path.suffix != ".py":
            continue

        # Only validate files in tests/ directory OR test files (test_*.py)
        file_str = str(file_path)
        is_test_file = "test_" in file_path.name and file_path.name.startswith("test_")
        is_in_tests_dir = "tests/" in file_str or "/tests/" in file_str

        if not (is_test_file or is_in_tests_dir):
            continue

        # Validate file using shared library
        if not test_ids.validate_test_file(file_path):
            all_passed = False

            # Check for hardcoded ID violations
            violations = test_ids.find_hardcoded_ids(file_path)
            if violations:
                print(f"\n❌ VALIDATION FAILED: {file_path}", file=sys.stderr)
                print(f"\nFound {len(violations)} hardcoded ID(s):\n", file=sys.stderr)

                for line_num, line_content, description in violations:
                    print(f"  Line {line_num}: {description}", file=sys.stderr)
                    print(f"    {line_content}", file=sys.stderr)

                print("\n💡 How to fix:", file=sys.stderr)
                print("  Use worker-safe ID helpers instead of hardcoded IDs:\n", file=sys.stderr)
                print("    from tests.conftest import get_user_id, get_api_key_id\n", file=sys.stderr)
                print("    def test_something():", file=sys.stderr)
                print("        user_id = get_user_id()  # ✅ Worker-safe", file=sys.stderr)
                print("        apikey_id = get_api_key_id()  # ✅ Worker-safe\n", file=sys.stderr)
                print("  See: tests/conftest.py for helper function documentation", file=sys.stderr)
                print("  See: tests/meta/test_id_pollution_prevention.py for examples\n", file=sys.stderr)

            # Check for integration test strictness violations
            integration_violations = test_ids.get_integration_violations(file_path)
            if integration_violations:
                print(f"\n❌ INTEGRATION POLICY FAILED: {file_path}", file=sys.stderr)
                for violation in integration_violations:
                    print(f"  - {violation}", file=sys.stderr)
                print()
        else:
            # Validation passed - provide informative message about why
            # Check in priority order: exempt files, unit tests with InMemory, worker-safe helpers, clean files
            if test_ids.is_file_exempt(file_path):
                print(f"⏭️  {file_path} - Exempt (special case)")
            elif test_ids.is_unit_test_with_inmemory(file_path):
                print(f"⏭️  {file_path} - Unit test with InMemory backend (no pollution risk)")
            elif test_ids.check_worker_safe_usage(file_path):
                print(f"✅ {file_path} - Uses worker-safe ID helpers")
            else:
                print(f"✅ {file_path} - No hardcoded IDs found")

    if all_passed:
        return 0
    else:
        print("\n🔴 ID POLLUTION PREVENTION FAILED", file=sys.stderr)
        print("Fix hardcoded IDs before committing.\n", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
