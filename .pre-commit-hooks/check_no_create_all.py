#!/usr/bin/env python3
"""
Pre-commit hook: Prevent SQLAlchemy create_all() usage in production code.

This hook ensures that all database schema management is handled by Alembic
migrations, not by create_all() calls which cause schema drift between
development and production environments.

Usage (automatically via pre-commit):
    pre-commit run check-no-create-all --all-files

Manual usage:
    python .pre-commit-hooks/check_no_create_all.py src/

Exit codes:
    0: No violations found
    1: create_all() usage detected
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Patterns that indicate create_all() usage
CREATE_ALL_PATTERNS = [
    r"\.create_all\s*\(",
    r"metadata\.create_all",
    r"Base\.metadata\.create_all",
    r"run_sync\s*\(\s*\w+\.metadata\.create_all",
]

# Files that are explicitly allowed to have create_all()
ALLOWED_PATTERNS = [
    "conftest.py",
    "test_",
    "alembic/",
    ".pre-commit-hooks/",
]


def is_allowed_file(file_path: Path) -> bool:
    """Check if file is in the allowed list."""
    path_str = str(file_path)
    return any(allowed in path_str for allowed in ALLOWED_PATTERNS)


def check_file(file_path: Path) -> list[tuple[int, str]]:
    """
    Check a single file for create_all() violations.

    Returns:
        List of (line_number, line_content) tuples for violations
    """
    violations = []
    combined_pattern = re.compile("|".join(CREATE_ALL_PATTERNS))

    try:
        content = file_path.read_text(encoding="utf-8")
        for line_num, line in enumerate(content.splitlines(), start=1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            if combined_pattern.search(line):
                violations.append((line_num, stripped))
    except (OSError, UnicodeDecodeError):
        pass

    return violations


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Check for SQLAlchemy create_all() usage in source code")
    parser.add_argument(
        "files",
        nargs="*",
        help="Files to check (default: all Python files in src/)",
    )
    args = parser.parse_args()

    # Get files to check
    if args.files:
        files_to_check = [Path(f) for f in args.files if f.endswith(".py")]
    else:
        src_dir = Path(__file__).parent.parent / "src"
        files_to_check = list(src_dir.rglob("*.py"))

    # Check each file
    all_violations: list[tuple[Path, int, str]] = []
    for file_path in files_to_check:
        if is_allowed_file(file_path):
            continue

        violations = check_file(file_path)
        for line_num, content in violations:
            all_violations.append((file_path, line_num, content))

    # Report results
    if all_violations:
        print("ERROR: Found create_all() usage in production code!")
        print("")
        print("Violations:")
        for file_path, line_num, content in all_violations:
            print(f"  {file_path}:{line_num}: {content}")
        print("")
        print("SOLUTION:")
        print("  All database schema management must use Alembic migrations.")
        print("")
        print("  1. Remove the create_all() call")
        print("  2. Create a migration: alembic revision --autogenerate -m 'description'")
        print("  3. Apply the migration: alembic upgrade head")
        print("")
        print("  See: alembic/README.md for migration best practices.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
