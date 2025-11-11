#!/usr/bin/env python3
"""
Dead Test Code Detection Script

Detects dead code after return statements in pytest fixtures.
This code never executes and represents lost test coverage.

Pattern detected:
    @pytest.fixture
    def my_fixture():
        return value

        # Dead code - never executes!
        assert something

Usage:
    python scripts/detect_dead_test_code.py tests/
    python scripts/detect_dead_test_code.py tests/builder/test_code_generator.py

Exit codes:
    0 - No dead code found
    1 - Dead code detected (blocks commit)
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple


def find_dead_code_in_fixtures(filepath: Path) -> List[Tuple[str, int, List[int]]]:
    """
    Find code after return statements in pytest fixtures.

    Returns list of (fixture_name, return_line, [dead_line_numbers]) tuples.
    """
    with open(filepath) as f:
        try:
            tree = ast.parse(f.read(), filename=str(filepath))
        except SyntaxError:
            return []

    violations = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Check if this is a pytest fixture
            is_fixture = any(
                (isinstance(dec, ast.Name) and dec.id == "fixture")
                or (isinstance(dec, ast.Attribute) and dec.attr == "fixture")
                for dec in node.decorator_list
            )

            if not is_fixture:
                continue

            # Find return statements
            for i, stmt in enumerate(node.body):
                if isinstance(stmt, ast.Return):
                    # Check if there's code after this return
                    remaining_stmts = node.body[i + 1 :]
                    if remaining_stmts:
                        # Filter out pass statements and ellipsis (legitimate in some cases)
                        dead_lines = []
                        for dead_stmt in remaining_stmts:
                            if not isinstance(dead_stmt, (ast.Pass, ast.Expr)):
                                dead_lines.append(dead_stmt.lineno)
                            elif isinstance(dead_stmt, ast.Expr) and not isinstance(dead_stmt.value, ast.Constant):
                                # Expressions that aren't just docstrings/ellipsis
                                dead_lines.append(dead_stmt.lineno)

                        if dead_lines:
                            violations.append((node.name, stmt.lineno, dead_lines))

    return violations


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/detect_dead_test_code.py <test_file_or_directory>")
        sys.exit(1)

    path = Path(sys.argv[1])

    # Collect all test files
    if path.is_file():
        test_files = [path]
    else:
        test_files = sorted(path.rglob("test_*.py"))

    violations = []

    for test_file in test_files:
        dead_code_instances = find_dead_code_in_fixtures(test_file)
        for fixture_name, return_line, dead_lines in dead_code_instances:
            violations.append(
                f"{test_file}:{return_line} - "
                f"Fixture '{fixture_name}' has {len(dead_lines)} lines of dead code after return"
            )

    if violations:
        print("=" * 80)
        print("❌ DEAD TEST CODE DETECTED")
        print("=" * 80)
        print()
        print(f"Found {len(violations)} fixtures with dead code after return statements.")
        print("Code after return statements never executes - extract into separate test functions:")
        print()
        for violation in violations:
            print(f"  - {violation}")
        print()
        print("Fix: Extract dead code into separate test function with proper test_ prefix.")
        print()
        print("Example:")
        print("  # Before (BAD):")
        print("  @pytest.fixture")
        print("  def my_fixture():")
        print("      return value")
        print()
        print("      # Dead code!")
        print("      assert something")
        print()
        print("  # After (GOOD):")
        print("  @pytest.fixture")
        print("  def my_fixture():")
        print("      return value")
        print()
        print("  def test_something():")
        print("      assert something")
        print()
        print("Regression prevention: Codex P0 finding (test_code_generator.py:33-64)")
        print("=" * 80)
        sys.exit(1)

    print("✓ No dead code found in test fixtures")
    sys.exit(0)


if __name__ == "__main__":
    main()
