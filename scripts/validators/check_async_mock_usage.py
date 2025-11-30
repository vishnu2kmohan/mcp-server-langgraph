#!/usr/bin/env python3
"""
Validation script to detect async methods mocked without AsyncMock.

This script is a thin wrapper around tests.validation_lib.async_mocks module.
All validation logic lives in the shared library for better testability and consistency.

This script prevents hanging tests by detecting patterns where:
- patch.object() or patch() is used without new_callable=AsyncMock
- The mocked method is awaited in the code under test

Detection Strategy:
1. Static Analysis (Preferred): When module path is available (e.g., patch("module.func")),
   parses source code to definitively determine if function is async
2. Pattern Matching (Fallback): Uses conservative async naming patterns (send_, async_, fetch_)
3. Whitelist: Known synchronous functions that match async patterns

False Positive Prevention:
- Removed overly broad patterns (get_, create_, update_, delete_)
- Added static analysis for definitive async detection
- Maintains whitelist for edge cases
- Supports # noqa: async-mock comment suppression

Exit codes:
    0: All async mocks are correctly configured
    1: Found async methods mocked incorrectly (will cause hanging)
"""

import sys
from pathlib import Path

# Add project root to path to enable imports from tests/
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Import validation logic from shared library
from tests.validation_lib import async_mocks  # noqa: E402


def main() -> int:
    """Main entry point."""
    # Determine which files to check
    if len(sys.argv) > 1:
        # Pre-commit mode: check specific files
        files_to_check = [f for f in sys.argv[1:] if f.endswith(".py")]
    else:
        # Standalone mode: check all test files
        repo_root = Path(__file__).parent.parent.parent
        files_to_check = [str(p) for p in (repo_root / "tests").rglob("*.py")]

    if not files_to_check:
        print("No test files to check.")
        return 0

    all_issues = []

    for filepath in files_to_check:
        # Only check Python files
        if not filepath.endswith(".py"):
            continue

        issues = async_mocks.check_async_mock_usage(filepath)
        if issues:
            all_issues.extend([(filepath, line, msg) for line, msg in issues])

    if all_issues:
        print("❌ Found async mock issues:\n")
        for filepath, line, msg in all_issues:
            print(f"{filepath}:{line} - {msg}")

        unique_files = {issue[0] for issue in all_issues}
        print(f"\n❌ {len(all_issues)} issues found in {len(unique_files)} files")
        print("\n💡 Fix: Import AsyncMock and add new_callable=AsyncMock to patch calls")
        print("   Example: patch.object(obj, 'async_method', new_callable=AsyncMock)")
        return 1
    else:
        print("✅ All async mocks are correctly configured!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
