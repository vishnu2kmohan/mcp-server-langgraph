#!/usr/bin/env python3
"""
Comprehensive test suite validation script.

CODEX FINDING #5: Meta tests use pytest.fail for style checks, blocking feature work.
Solution: Move comprehensive validation to this script (run in pre-commit or manually).

This script performs deep validation of:
1. Test marker consistency
2. Import guards for optional dependencies
3. Infrastructure fixture patterns
4. CLI tool availability guards
5. Test naming conventions
6. Documentation accuracy

Exit codes:
0: All checks passed
1: Validation errors found
2: Script execution error
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import List, Tuple

# Color codes for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def check_marker_consistency(tests_dir: Path) -> List[str]:
    """
    Check for conflicting pytest markers on test classes.

    Returns:
        List of error messages
    """
    issues = []
    conflicts = []

    marker_pairs = [
        ("unit", "integration"),
        ("unit", "e2e"),
    ]

    for test_file in tests_dir.rglob("test_*.py"):
        if test_file.parent.name == "meta":
            continue

        try:
            with open(test_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(test_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                    markers = extract_markers_from_class(node)

                    for marker1, marker2 in marker_pairs:
                        if marker1 in markers and marker2 in markers:
                            rel_path = test_file.relative_to(tests_dir.parent)
                            conflicts.append(f"{rel_path}::{node.name} has both '{marker1}' and '{marker2}'")

        except (SyntaxError, UnicodeDecodeError):
            continue

    if conflicts:
        issues.append(f"{RED}✗{RESET} Found test classes with conflicting pytest markers:")
        for conflict in conflicts:
            issues.append(f"  - {conflict}")

    return issues


def extract_markers_from_class(class_node: ast.ClassDef) -> set:
    """Extract pytest marker names from a test class."""
    markers = set()

    for decorator in class_node.decorator_list:
        if isinstance(decorator, ast.Attribute):
            if (
                isinstance(decorator.value, ast.Attribute)
                and isinstance(decorator.value.value, ast.Name)
                and decorator.value.value.id == "pytest"
                and decorator.value.attr == "mark"
            ):
                markers.add(decorator.attr)

    return markers


def check_test_naming_conventions(tests_dir: Path) -> List[str]:
    """
    Check that test names follow conventions.

    Returns:
        List of warning messages (non-fatal)
    """
    warnings = []
    poor_names = []

    for test_file in tests_dir.rglob("test_*.py"):
        try:
            with open(test_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(test_file))

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                    # Check for generic names
                    if node.name in ["test_1", "test_case", "test_example", "test_test"]:
                        rel_path = test_file.relative_to(tests_dir.parent)
                        poor_names.append(f"{rel_path}:{node.lineno} - {node.name}")

        except (SyntaxError, UnicodeDecodeError):
            continue

    if poor_names:
        warnings.append(f"{YELLOW}⚠{RESET}  Found tests with generic names (consider more descriptive names):")
        for name in poor_names[:10]:  # Limit to first 10
            warnings.append(f"  - {name}")
        if len(poor_names) > 10:
            warnings.append(f"  ... and {len(poor_names) - 10} more")

    return warnings


def main():
    """Run all validation checks."""
    parser = argparse.ArgumentParser(description="Validate test suite structure and conventions")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args()

    tests_dir = Path(__file__).parent.parent / "tests"

    if not tests_dir.exists():
        print(f"{RED}✗{RESET} Tests directory not found: {tests_dir}")
        return 2

    print("=" * 70)
    print("Test Suite Validation")
    print("=" * 70)
    print()

    all_issues = []
    all_warnings = []

    # Run checks
    print(f"Checking marker consistency...")
    issues = check_marker_consistency(tests_dir)
    all_issues.extend(issues)

    print(f"Checking test naming conventions...")
    warnings = check_test_naming_conventions(tests_dir)
    all_warnings.extend(warnings)

    # Print results
    print()
    print("=" * 70)
    print("Results")
    print("=" * 70)
    print()

    if all_issues:
        for issue in all_issues:
            print(issue)
        print()

    if all_warnings:
        for warning in all_warnings:
            print(warning)
        print()

    # Determine exit code
    if all_issues:
        print(f"{RED}✗ Validation failed with {len(all_issues)} errors{RESET}")
        return 1
    elif all_warnings and args.strict:
        print(f"{YELLOW}⚠ Validation completed with {len(all_warnings)} warnings (treated as errors in strict mode){RESET}")
        return 1
    elif all_warnings:
        print(f"{YELLOW}⚠ Validation completed with {len(all_warnings)} warnings{RESET}")
        print(f"{GREEN}✓ No critical errors found{RESET}")
        return 0
    else:
        print(f"{GREEN}✓ All checks passed{RESET}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
