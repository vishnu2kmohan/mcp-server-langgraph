#!/usr/bin/env python3
"""
Validation script for test naming conventions.

This script is a thin wrapper around tests.validation_lib.naming module.
All validation logic lives in the shared library for better testability and consistency.

The test naming conventions require:
1. Test files use test_*.py pattern (not *_test.py)
2. Test functions use descriptive names: test_<function>_<scenario>_<expected_result>
3. Avoid generic names like test_1, test_case_1, test_function, etc.

Examples of GOOD test names:
- test_calculate_total_with_empty_cart_returns_zero
- test_user_login_with_invalid_password_raises_authentication_error
- test_order_processing_with_expired_payment_method_sends_notification

Examples of BAD test names:
- test_calculation (too generic)
- test_user (too vague)
- test_case_1 (meaningless)

Usage:
    python scripts/validation/check_test_naming.py [file1.py file2.py ...]

Exit codes:
    0: All tests pass naming convention validation
    1: Violations found

See: CLAUDE.md for complete test naming conventions
"""

import sys
from pathlib import Path

# Add project root to path to enable imports from tests/
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Import validation logic from shared library
from tests.validation_lib import naming as test_naming  # noqa: E402


def main() -> int:
    """Main entry point."""
    # Determine which files to check
    if len(sys.argv) > 1:
        # Pre-commit mode: check specific files
        files_to_check = [f for f in sys.argv[1:] if f.endswith(".py") and "test" in f]
    else:
        # Standalone mode: check all test files
        repo_root = Path(__file__).parent.parent.parent
        files_to_check = test_naming.find_test_files(str(repo_root / "tests"))

    if not files_to_check:
        print("No test files to check.")
        return 0

    # Check all files
    all_violations = []
    for file_path in files_to_check:
        violations = test_naming.check_file(file_path)
        all_violations.extend(violations)

    # Print results
    test_naming.print_violations(all_violations)

    # Return exit code
    return 1 if all_violations else 0


if __name__ == "__main__":
    sys.exit(main())
