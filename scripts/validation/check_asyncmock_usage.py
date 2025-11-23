#!/usr/bin/env python3
"""
Validate AsyncMock usage in test files.

Ensures that AsyncMock is always instantiated with (), not assigned as a class.

CORRECT:
    mock.method = AsyncMock(return_value=1)
    mock.method = AsyncMock()

INCORRECT:
    mock.method = AsyncMock  # Class assignment
    mock.method = AsyncMock  # noqa: async-mock-config(return_value=1)

This script prevents the common bug where AsyncMock class is assigned instead
of an AsyncMock instance, which causes "object AsyncMock can't be used in
'await' expression" errors.

Exit codes:
    0: No issues found
    1: AsyncMock class assignments detected
"""

import re
import sys
from pathlib import Path


def check_file(file_path: Path) -> list[tuple[int, str]]:
    """
    Check a file for AsyncMock class assignments.

    Args:
        file_path: Path to Python file to check

    Returns:
        List of (line_number, line_content) tuples for violations
    """
    violations = []

    try:
        content = file_path.read_text()
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
        return violations

    # Pattern: = AsyncMock followed by whitespace and comment (not parentheses)
    # Matches: = AsyncMock  # comment
    # Doesn't match: = AsyncMock() or = AsyncMock(...)
    pattern = re.compile(
        r"=\s+AsyncMock\s+#",  # Assignment to AsyncMock class with comment
        re.MULTILINE,
    )

    for line_num, line in enumerate(content.splitlines(), start=1):
        # Skip if line is in a string literal (basic check)
        if line.strip().startswith(("#", '"', "'")):
            continue

        if pattern.search(line):
            violations.append((line_num, line.strip()))

    return violations


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        # Default to scanning tests/ directory
        repo_root = Path(__file__).parent.parent.parent
        files_to_check = list((repo_root / "tests").rglob("*.py"))
    else:
        files_to_check = [Path(f) for f in sys.argv[1:]]

    all_violations = []

    for file_path in files_to_check:
        if not file_path.exists():
            print(f"Warning: File not found: {file_path}", file=sys.stderr)
            continue

        if not file_path.suffix == ".py":
            continue

        violations = check_file(file_path)

        if violations:
            all_violations.extend((file_path, line_num, line) for line_num, line in violations)

    if all_violations:
        print("ERROR: AsyncMock class assignments detected (should be AsyncMock() instances)")
        print()
        print("Found AsyncMock assigned as class instead of instance:")
        print()

        for file_path, line_num, line in all_violations:
            print(f"  {file_path}:{line_num}")
            print(f"    {line}")
            print()

        print("Fix: Replace AsyncMock class with AsyncMock() instance")
        print()
        print("WRONG:  mock.method = AsyncMock  # noqa: async-mock-config(return_value=1)")
        print("RIGHT:  mock.method = AsyncMock(return_value=1)")
        print()
        print("WRONG:  mock.method = AsyncMock  # noqa: async-mock-config()")
        print("RIGHT:  mock.method = AsyncMock()")
        print()

        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
