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
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Import validation logic from shared library
from tests.validation_lib import async_mocks  # noqa: E402


def main():
    """Main entry point."""
    # Get test files from command line or scan tests/ directory
    if len(sys.argv) > 1:
        test_files = [Path(arg) for arg in sys.argv[1:]]
    else:
        test_files = list(Path("tests").rglob("test_*.py"))

    if not test_files:
        print("No test files found.")
        return 0

    print(f"🔍 Checking {len(test_files)} test files for async mock issues...\n")

    all_issues = []
    files_with_issues = []

    for filepath in test_files:
        if not filepath.exists():
            print(f"⚠️  File not found: {filepath}", file=sys.stderr)
            continue

        issues = async_mocks.check_async_mock_usage(str(filepath))
        if issues:
            all_issues.extend([(filepath, line, msg) for line, msg in issues])
            files_with_issues.append(filepath)

    if all_issues:
        print("❌ Found async mock issues:\n")
        for filepath, line, msg in all_issues:
            print(f"{filepath}:{line} - {msg}")

        print(f"\n❌ {len(all_issues)} issues found in {len(files_with_issues)} files")
        print("\n💡 Fix: Import AsyncMock and add new_callable=AsyncMock to patch calls")
        print("   Example: patch.object(obj, 'async_method', new_callable=AsyncMock)")
        return 1
    print("✅ All async mocks are correctly configured!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
