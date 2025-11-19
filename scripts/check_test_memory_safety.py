#!/usr/bin/env python3
"""
Validation script for pytest-xdist memory safety patterns.

This script is a thin wrapper around tests.validation_lib.memory_safety module.
All validation logic lives in the shared library for better testability and consistency.

The memory safety pattern requires:
1. Test classes using AsyncMock/MagicMock must have @pytest.mark.xdist_group decorator
2. Test classes must have teardown_method() with gc.collect()
3. Performance tests must skip when running under pytest-xdist workers

Background:
When running tests with pytest-xdist, AsyncMock/MagicMock objects create circular
references that prevent garbage collection, leading to memory explosion (observed:
217GB VIRT, 42GB RES). The 3-part pattern prevents this by:
- Grouping related tests in same worker (xdist_group)
- Forcing GC after each test (teardown_method + gc.collect)
- Skipping performance tests in parallel mode

Usage:
    python scripts/check_test_memory_safety.py [file1.py file2.py ...]

Exit codes:
    0: All tests pass memory safety validation
    1: Violations found

See: tests/MEMORY_SAFETY_GUIDELINES.md for complete documentation
"""

import sys
from pathlib import Path

# Import validation logic from shared library
from tests.validation_lib import memory_safety


def main() -> int:
    """Main entry point."""
    # Determine which files to check
    if len(sys.argv) > 1:
        # Pre-commit mode: check specific files
        files_to_check = [f for f in sys.argv[1:] if f.endswith(".py") and "test_" in f]
    else:
        # Standalone mode: check all test files
        repo_root = Path(__file__).parent.parent
        files_to_check = memory_safety.find_test_files(str(repo_root / "tests"))

    if not files_to_check:
        print("No test files to check.")
        return 0

    # Check all files
    all_violations = []
    for file_path in files_to_check:
        violations = memory_safety.check_file(file_path)
        all_violations.extend(violations)

    # Print results
    memory_safety.print_violations(all_violations)

    # Return exit code
    return 1 if all_violations else 0


if __name__ == "__main__":
    sys.exit(main())
