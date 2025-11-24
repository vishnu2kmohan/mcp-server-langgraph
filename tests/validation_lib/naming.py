#!/usr/bin/env python3
"""
Validation library for test naming conventions.

This module validates that test files and test functions follow the project's
naming conventions as documented in CLAUDE.md:

Test Files:
- Must use `test_*.py` pattern
- Should NOT use `*_test.py` pattern (although technically valid, not used in this repo)

Test Functions:
- Must use `test_<function>_<scenario>_<expected_result>` pattern
- Should be descriptive and explain WHAT is tested and WHAT the expected outcome is
- Should avoid generic names like test_1, test_case_1, test_function, etc.

Examples of GOOD test names:
- test_calculate_total_with_empty_cart_returns_zero
- test_user_login_with_invalid_password_raises_authentication_error
- test_order_processing_with_expired_payment_method_sends_notification

Examples of BAD test names:
- test_calculation
- test_user
- test_case_1
- test_1

Usage:
    from tests.validation_lib import test_naming

    violations = test_naming.check_file("tests/test_feature.py")
    test_naming.print_violations(violations)
"""

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Violation:
    """Represents a test naming violation."""

    file: str
    line: int
    name: str
    issue: str
    suggestion: str


# Patterns for test files
VALID_TEST_FILE_PATTERN = re.compile(r"^test_.*\.py$")
DISCOURAGED_TEST_FILE_PATTERN = re.compile(r"^.*_test\.py$")

# Patterns for bad test names
BAD_PATTERNS = [
    (re.compile(r"^test_\d+$"), "Numbered test (e.g., test_1, test_2)"),
    (re.compile(r"^test_case_\d+$"), "Generic test_case_N pattern"),
    (re.compile(r"^test_[a-z]+$"), "Single word test name (too generic)"),
    (re.compile(r"^test_it_works$"), "Generic 'it works' test"),
    (re.compile(r"^test_success$"), "Generic 'success' test"),
    (re.compile(r"^test_failure$"), "Generic 'failure' test"),
    (re.compile(r"^test_basic$"), "Generic 'basic' test"),
    (re.compile(r"^test_advanced$"), "Generic 'advanced' test"),
]

# Minimum words in a good test name (function_scenario_result)
MIN_WORDS_IN_TEST_NAME = 3


def find_test_files(directory: str) -> list[str]:
    """
    Find all test files in the given directory.

    Args:
        directory: Path to directory to search

    Returns:
        List of test file paths
    """
    test_dir = Path(directory)
    if not test_dir.exists():
        return []

    # Find all test_*.py files recursively
    test_files = list(test_dir.rglob("test_*.py"))

    # Convert to strings and filter out __pycache__
    return [str(f) for f in test_files if "__pycache__" not in str(f)]


def check_file_name(file_path: str) -> list[Violation]:
    """
    Check if test file name follows conventions.

    Args:
        file_path: Path to test file

    Returns:
        List of violations
    """
    violations = []
    file_name = Path(file_path).name

    # Skip conftest.py files (pytest configuration, not tests)
    if file_name == "conftest.py":
        return violations

    # Skip validation library files
    if "validation_lib" in file_path:
        return violations

    # Check if it's a test file (has 'test' in name)
    if "test" not in file_name.lower():
        return violations  # Not a test file, skip

    # Check for discouraged *_test.py pattern
    if DISCOURAGED_TEST_FILE_PATTERN.match(file_name):
        violations.append(
            Violation(
                file=file_path,
                line=1,
                name=file_name,
                issue="Uses discouraged *_test.py pattern",
                suggestion=f"Rename to test_{file_name.replace('_test.py', '.py')}",
            )
        )

    # Check for valid test_*.py pattern
    if not VALID_TEST_FILE_PATTERN.match(file_name) and "test" in file_name.lower():
        if not file_name.endswith("_test.py"):  # Already flagged above
            violations.append(
                Violation(
                    file=file_path,
                    line=1,
                    name=file_name,
                    issue="Test file doesn't follow test_*.py pattern",
                    suggestion="Rename to test_<descriptive_name>.py",
                )
            )

    return violations


def check_test_function_name(func_name: str, file_path: str, line: int) -> list[Violation]:
    """
    Check if test function name follows conventions.

    Args:
        func_name: Name of test function
        file_path: Path to file containing function
        line: Line number where function is defined

    Returns:
        List of violations
    """
    violations = []

    # Skip if not a test function
    if not func_name.startswith("test_"):
        return violations

    # Check against known bad patterns
    for pattern, issue in BAD_PATTERNS:
        if pattern.match(func_name):
            violations.append(
                Violation(
                    file=file_path,
                    line=line,
                    name=func_name,
                    issue=issue,
                    suggestion="Use descriptive name: test_<function>_<scenario>_<expected_result>",
                )
            )
            return violations  # One violation is enough

    # Check if name has enough words (underscores separate words)
    words = func_name.split("_")[1:]  # Remove 'test' prefix
    if len(words) < MIN_WORDS_IN_TEST_NAME:
        violations.append(
            Violation(
                file=file_path,
                line=line,
                name=func_name,
                issue=f"Test name too generic (only {len(words)} word(s))",
                suggestion="Use pattern: test_<function>_<scenario>_<expected_result> (at least 3 parts)",
            )
        )

    return violations


def check_file(file_path: str) -> list[Violation]:
    """
    Check a single test file for naming violations.

    Args:
        file_path: Path to test file

    Returns:
        List of violations found
    """
    violations = []

    # Skip conftest.py files entirely (pytest configuration, not tests)
    if Path(file_path).name == "conftest.py":
        return violations

    # Skip validation library files
    if "validation_lib" in file_path:
        return violations

    # Check file name
    violations.extend(check_file_name(file_path))

    # Parse file to check function names
    try:
        with open(file_path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=file_path)
    except Exception:
        # If we can't parse, skip function checks
        return violations

    # Check all function definitions
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Skip fixtures - they can have any name including test_ prefix
            is_fixture = any(
                isinstance(dec, ast.Name) and dec.id == "fixture" or isinstance(dec, ast.Attribute) and dec.attr == "fixture"
                for dec in node.decorator_list
            )

            if is_fixture:
                continue  # Skip pytest fixtures

            func_violations = check_test_function_name(node.name, file_path, node.lineno)
            violations.extend(func_violations)

    return violations


def print_violations(violations: list[Violation]) -> None:
    """
    Print violations in a user-friendly format.

    Args:
        violations: List of violations to print
    """
    if not violations:
        print("✅ All test naming conventions validated successfully!")
        return

    print(f"\n❌ Found {len(violations)} test naming violation(s):\n")

    # Group by file
    by_file = {}
    for v in violations:
        if v.file not in by_file:
            by_file[v.file] = []
        by_file[v.file].append(v)

    # Print grouped by file
    for file_path, file_violations in sorted(by_file.items()):
        print(f"📁 {file_path}")
        for v in file_violations:
            print(f"   Line {v.line}: {v.name}")
            print(f"   Issue: {v.issue}")
            print(f"   Suggestion: {v.suggestion}")
            print()

    print("\n📖 See CLAUDE.md for test naming conventions")
    print("   Good: test_calculate_total_with_empty_cart_returns_zero")
    print("   Bad: test_calculation, test_1, test_case_1")
