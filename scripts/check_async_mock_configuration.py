#!/usr/bin/env python3
"""
Pre-commit hook: Detect unconfigured AsyncMock instances.

This script is a thin wrapper around tests.validation_lib.async_mocks module.
All validation logic lives in the shared library for better testability and consistency.

This script identifies AsyncMock() instances that lack explicit return_value
or side_effect configuration, which can cause subtle bugs in authorization
checks and parallel test execution.

Configuration Detection:
- Constructor kwargs: AsyncMock(return_value=..., side_effect=..., spec=...)
- Post-creation assignment: mock.return_value = ... or mock.side_effect = ...
- Spec configuration: AsyncMock(spec=SomeClass) is considered configured

False Positive Prevention:
- Supports # noqa: async-mock-config inline suppression
- Recognizes constructor keyword arguments
- Scopes analysis to function boundaries

Exit codes:
    0: All AsyncMock instances are properly configured
    1: Found unconfigured AsyncMock instances (blocking)

Usage:
    python scripts/check_async_mock_configuration.py [files...]
"""
import sys
from pathlib import Path

# Add project root to path to enable imports from tests/
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Import validation logic from shared library
from tests.validation_lib import async_mocks  # noqa: E402


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: check_async_mock_configuration.py <file> [<file> ...]", file=sys.stderr)
        return 1

    files = sys.argv[1:]
    all_issues = []

    for filepath in files:
        # Only check test files
        if not filepath.startswith("tests/") or not filepath.endswith(".py"):
            continue

        issues = async_mocks.check_async_mock_configuration(filepath)
        if issues:
            all_issues.extend([(filepath, line, msg) for line, msg in issues])

    if all_issues:
        print("❌ Found unconfigured AsyncMock instances:\n", file=sys.stderr)
        for filepath, line_num, message in all_issues:
            print(f"  {filepath}:{line_num} - {message}", file=sys.stderr)

        print("\n📖 Fix: Add explicit return_value or side_effect configuration:", file=sys.stderr)
        print("   Option 1 - Constructor kwargs: mock = AsyncMock(return_value=value)", file=sys.stderr)
        print("   Option 2 - Post-creation: mock.method.return_value = expected_value", file=sys.stderr)
        print("   Option 3 - Spec: mock = AsyncMock(spec=SomeClass)", file=sys.stderr)
        print("   Option 4 - Suppress: mock = AsyncMock()  # noqa: async-mock-config", file=sys.stderr)
        print("\nSee: tests/ASYNC_MOCK_GUIDELINES.md for best practices\n", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
