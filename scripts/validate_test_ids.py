#!/usr/bin/env python3
"""
Test ID Pollution Prevention - Pre-commit Validation Script

This script validates that test files use worker-safe ID helpers instead of hardcoded IDs.

CRITICAL: Hardcoded IDs like "user:alice" or "apikey_test123" cause state pollution
in pytest-xdist parallel execution, leading to flaky tests and intermittent failures.

Prevention mechanism:
- Pre-commit hook runs this script on test files before allowing commit
- Script detects hardcoded ID patterns and blocks commit with helpful error message
- Developers must use worker-safe helpers (get_user_id, get_api_key_id)

Worker-safe helper usage:
    from tests.conftest import get_user_id, get_api_key_id

    def test_something():
        user_id = get_user_id()  # ✅ Worker-safe
        apikey_id = get_api_key_id()  # ✅ Worker-safe

        # NOT: user_id = "user:alice"  # ❌ Hardcoded - will fail validation
        # NOT: apikey_id = "apikey_test123"  # ❌ Hardcoded - will fail validation

Exit codes:
    0: All tests pass (no hardcoded IDs found)
    1: Validation failed (hardcoded IDs detected)

Usage:
    # Validate single file
    python scripts/validate_test_ids.py tests/test_example.py

    # Validate multiple files (pre-commit hook usage)
    python scripts/validate_test_ids.py tests/test_a.py tests/test_b.py

Related:
    - tests/conftest.py: Worker-safe ID helper implementations
    - tests/meta/test_id_pollution_prevention.py: Meta-tests for this script
    - .pre-commit-config.yaml: Hook configuration
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Patterns that indicate hardcoded IDs (violations)
HARDCODED_ID_PATTERNS = [
    # User IDs in OpenFGA format
    (r'"user:[a-zA-Z0-9_-]+"', "Hardcoded user ID in quotes"),
    (r"'user:[a-zA-Z0-9_-]+'", "Hardcoded user ID in quotes"),
    # API key IDs
    (r'"apikey_[a-zA-Z0-9_-]+"', "Hardcoded API key ID in quotes"),
    (r"'apikey_[a-zA-Z0-9_-]+'", "Hardcoded API key ID in quotes"),
]

# Patterns that indicate legitimate usage (allowed)
LEGITIMATE_PATTERNS = [
    # OpenFGA format assertions with explicit comment
    r'assert.*"user:[a-zA-Z0-9_-]+".*#.*OpenFGA format',
    r"assert.*'user:[a-zA-Z0-9_-]+'.*#.*OpenFGA format",
    # Docstring examples
    r'""".*user:[a-zA-Z0-9_-]+.*"""',
    r"'''.*user:[a-zA-Z0-9_-]+.*'''",
    # Comments (documentation)
    r"#.*user:[a-zA-Z0-9_-]+",
    r"#.*apikey_[a-zA-Z0-9_-]+",
]

# Files that are allowed to have hardcoded IDs (special cases)
EXEMPT_FILES = [
    "conftest.py",  # Has docstrings and sample fixtures with example IDs
    "test_id_pollution_prevention.py",  # Meta-test that tests this validation script
    "test_openfga_client.py",  # Unit tests for OpenFGA client library interface (uses mocked data)
]


def is_file_exempt(file_path: Path) -> bool:
    """Check if file is exempt from validation (special cases like conftest.py, meta-tests)."""
    return any(exempt in str(file_path) for exempt in EXEMPT_FILES)


def is_legitimate_usage(line: str) -> bool:
    """
    Check if line contains legitimate ID usage (e.g., docstrings, comments, assertions).

    Legitimate uses include:
    - Docstring examples explaining ID formats
    - Comments documenting expected formats
    - Assertions checking OpenFGA format (with # OpenFGA format comment)

    Args:
        line: Line of code to check

    Returns:
        True if usage is legitimate (allowed), False otherwise
    """
    for pattern in LEGITIMATE_PATTERNS:
        if re.search(pattern, line):
            return True
    return False


def find_hardcoded_ids(file_path: Path) -> List[Tuple[int, str, str]]:
    """
    Find hardcoded ID patterns in a test file.

    Args:
        file_path: Path to test file to validate

    Returns:
        List of violations: [(line_number, line_content, violation_description), ...]
    """
    violations = []

    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        for line_num, line in enumerate(lines, start=1):
            # Skip legitimate usage (docstrings, comments, documented assertions)
            if is_legitimate_usage(line):
                continue

            # Check for hardcoded ID patterns
            for pattern, description in HARDCODED_ID_PATTERNS:
                if re.search(pattern, line):
                    violations.append((line_num, line.strip(), description))

    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}", file=sys.stderr)
        sys.exit(1)

    return violations


def check_worker_safe_usage(file_path: Path) -> bool:
    """
    Check if file uses worker-safe ID helpers.

    This is informational only - not required if file doesn't use IDs at all.

    Args:
        file_path: Path to test file

    Returns:
        True if file uses worker-safe helpers, False otherwise
    """
    try:
        content = file_path.read_text(encoding="utf-8")

        worker_safe_patterns = [
            r"from tests\.conftest import.*get_user_id",
            r"from tests\.conftest import.*get_api_key_id",
            r"get_user_id\(\)",
            r"get_api_key_id\(\)",
        ]

        for pattern in worker_safe_patterns:
            if re.search(pattern, content):
                return True

    except Exception:
        pass

    return False


def validate_test_file(file_path: Path) -> bool:
    """
    Validate a single test file for hardcoded IDs.

    Args:
        file_path: Path to test file to validate

    Returns:
        True if validation passes (no hardcoded IDs), False otherwise
    """
    # Skip exempt files (conftest.py, meta-tests)
    if is_file_exempt(file_path):
        print(f"⏭️  {file_path} - Exempt (special case)")
        return True

    violations = find_hardcoded_ids(file_path)

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

        return False

    # Validation passed
    uses_helpers = check_worker_safe_usage(file_path)
    if uses_helpers:
        print(f"✅ {file_path} - Uses worker-safe ID helpers")
    else:
        print(f"✅ {file_path} - No hardcoded IDs found")

    return True


def main() -> int:
    """
    Main entry point for validation script.

    Returns:
        Exit code: 0 if all files pass, 1 if any file fails
    """
    parser = argparse.ArgumentParser(description="Validate test files for hardcoded IDs (prevents pytest-xdist pollution)")
    parser.add_argument("files", nargs="+", type=Path, help="Test file(s) to validate")
    args = parser.parse_args()

    all_passed = True

    for file_path in args.files:
        if not file_path.exists():
            print(f"❌ File not found: {file_path}", file=sys.stderr)
            all_passed = False
            continue

        # Only validate Python test files
        if not file_path.suffix == ".py":
            continue

        # Only validate files in tests/ directory OR test files (test_*.py)
        file_str = str(file_path)
        is_test_file = "test_" in file_path.name and file_path.name.startswith("test_")
        is_in_tests_dir = "tests/" in file_str or "/tests/" in file_str

        if not (is_test_file or is_in_tests_dir):
            continue

        # Validate file
        if not validate_test_file(file_path):
            all_passed = False

    if all_passed:
        return 0
    else:
        print("\n🔴 ID POLLUTION PREVENTION FAILED", file=sys.stderr)
        print("Fix hardcoded IDs before committing.\n", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
