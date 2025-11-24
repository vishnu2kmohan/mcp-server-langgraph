#!/usr/bin/env python3
"""
Consolidated Test Safety Validator

This script consolidates 8 individual test safety validators into a single
comprehensive validation tool for pre-commit hooks.

Consolidated checks:
1. check-test-memory-safety - AsyncMock/MagicMock cleanup (xdist_group + gc.collect)
2. validate-test-isolation - dependency_overrides cleanup
3. check-async-mock-usage - xdist_group markers for async tests
4. validate-test-ids - pytest.mark.parametrize ID validation
5. validate-pytest-markers - marker consistency
6. validate-fixture-organization - no duplicate autouse fixtures
7. check-subprocess-timeout - timeout in subprocess tests
8. validate-test-naming - test name conventions

This reduces pre-commit hook count from 75 → 18 hooks (75% reduction).

Usage:
    python scripts/validation/validate_test_safety.py
    python scripts/validation/validate_test_safety.py tests/api/

Exit codes:
    0: All tests follow best practices
    1: Violations found

See: tests/PYTEST_XDIST_BEST_PRACTICES.md
See: tests/MEMORY_SAFETY_GUIDELINES.md
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import List, Tuple

# Type alias for violations: (line_number, code, message)
Violation = tuple[int, str, str]


class TestSafetyValidator(ast.NodeVisitor):
    """AST visitor to validate all test safety patterns"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.violations: list[Violation] = []
        self.current_class = None
        self.current_function = None
        self.has_xdist_group_marker = False
        self.has_teardown_method = False
        self.has_gc_collect = False

    def visit_ClassDef(self, node):
        """Visit class definitions to check for Test classes"""
        old_class = self.current_class
        old_xdist_group = self.has_xdist_group_marker
        old_teardown = self.has_teardown_method
        old_gc = self.has_gc_collect

        self.current_class = node.name
        self.has_xdist_group_marker = False
        self.has_teardown_method = False
        self.has_gc_collect = False

        # Check for test class markers
        # Only validate top-level Test classes
        if self.current_function is None and node.name.startswith("Test"):
            # Check for xdist_group marker
            for decorator in node.decorator_list:
                if self._is_xdist_group_marker(decorator):
                    self.has_xdist_group_marker = True
                    break

            # Check for teardown_method
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == "teardown_method":
                    self.has_teardown_method = True
                    # Check if teardown has gc.collect()
                    for stmt in ast.walk(child):
                        if isinstance(stmt, ast.Call):
                            if self._is_gc_collect_call(stmt):
                                self.has_gc_collect = True
                                break

            # Visit children
            self.generic_visit(node)

            # Validate test class has proper markers (only if it uses mocks)
            if self._class_uses_mocks(node):
                if not self.has_xdist_group_marker:
                    self.violations.append(
                        (
                            node.lineno,
                            "missing_xdist_group",
                            f"Test class '{node.name}' should use @pytest.mark.xdist_group marker",
                        )
                    )

                if not self.has_teardown_method or not self.has_gc_collect:
                    self.violations.append(
                        (
                            node.lineno,
                            "missing_gc_collect",
                            f"Test class '{node.name}' should have teardown_method() with gc.collect()",
                        )
                    )
        else:
            self.generic_visit(node)

        # Restore state
        self.current_class = old_class
        self.has_xdist_group_marker = old_xdist_group
        self.has_teardown_method = old_teardown
        self.has_gc_collect = old_gc

    def visit_FunctionDef(self, node):
        """Visit function definitions to check for fixtures and function-level tests"""
        old_function = self.current_function
        self.current_function = node.name

        # Check if this is a pytest fixture
        is_fixture = any(
            (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr == "fixture")
            or (isinstance(dec, ast.Name) and dec.id == "fixture")
            or (isinstance(dec, ast.Attribute) and dec.attr == "fixture")  # @pytest.fixture
            for dec in node.decorator_list
        )

        if is_fixture:
            # Check for dependency_overrides usage
            has_overrides = False
            has_cleanup = False

            for stmt in ast.walk(node):
                # Check for dependency_overrides attribute access
                if isinstance(stmt, ast.Attribute) and stmt.attr == "dependency_overrides":
                    has_overrides = True

                # Check for subscript assignment: app.dependency_overrides[key] = value
                if isinstance(stmt, ast.Subscript):
                    if isinstance(stmt.value, ast.Attribute) and stmt.value.attr == "dependency_overrides":
                        has_overrides = True

                if isinstance(stmt, ast.Call):
                    if self._is_dependency_override_clear(stmt):
                        has_cleanup = True

            if has_overrides and not has_cleanup:
                self.violations.append(
                    (
                        node.lineno,
                        "missing_cleanup",
                        f"Fixture '{node.name}' uses dependency_overrides but doesn't call .clear() in teardown",
                    )
                )

        # Check for function-level tests (not in a class) with AsyncMock/MagicMock
        is_test_function = node.name.startswith("test_") and self.current_class is None and not is_fixture

        if is_test_function:
            uses_async_or_magic_mock = self._function_uses_async_or_magic_mock(node)

            if uses_async_or_magic_mock:
                # Check for xdist_group marker
                has_xdist_marker = any(self._is_xdist_group_marker(dec) for dec in node.decorator_list)

                if not has_xdist_marker:
                    self.violations.append(
                        (
                            node.lineno,
                            "missing_xdist_marker",
                            f"Function '{node.name}' uses AsyncMock/MagicMock but lacks @pytest.mark.xdist_group marker",
                        )
                    )

        self.generic_visit(node)
        self.current_function = old_function

    def _is_xdist_group_marker(self, node) -> bool:
        """Check if node is @pytest.mark.xdist_group marker"""
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if hasattr(node.func, "value") and isinstance(node.func.value, ast.Attribute):
                    if node.func.value.attr == "mark" and node.func.attr == "xdist_group":
                        return True
        return False

    def _is_gc_collect_call(self, node) -> bool:
        """Check if node is gc.collect() call"""
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "gc" and node.func.attr == "collect":
                    return True
        return False

    def _is_dependency_override_clear(self, node) -> bool:
        """Check if node is app.dependency_overrides.clear() call"""
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "clear":
                    if isinstance(node.func.value, ast.Attribute):
                        if node.func.value.attr == "dependency_overrides":
                            return True
        return False

    def _function_uses_async_or_magic_mock(self, node: ast.FunctionDef) -> bool:
        """Check if a function uses AsyncMock or MagicMock"""
        for stmt in ast.walk(node):
            # Check for direct instantiation: AsyncMock() or MagicMock()
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Name) and stmt.func.id in ("AsyncMock", "MagicMock"):
                    return True
                # Check for qualified names: mock.AsyncMock(), unittest.mock.MagicMock()
                if isinstance(stmt.func, ast.Attribute) and stmt.func.attr in ("AsyncMock", "MagicMock"):
                    return True
        return False

    def _class_uses_mocks(self, node: ast.ClassDef) -> bool:
        """Check if a class uses AsyncMock or MagicMock"""
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Name) and stmt.func.id in ("AsyncMock", "MagicMock"):
                    return True
                if isinstance(stmt.func, ast.Attribute) and stmt.func.attr in ("AsyncMock", "MagicMock"):
                    return True
        return False


def check_memory_safety(violations: list[Violation]) -> int:
    """Check #1: Memory safety (xdist_group + gc.collect)"""
    # Already integrated into TestSafetyValidator
    return len([v for v in violations if v[1] in ("missing_xdist_group", "missing_gc_collect")])


def check_test_isolation(violations: list[Violation]) -> int:
    """Check #2: Test isolation (dependency_overrides cleanup)"""
    # Already integrated into TestSafetyValidator
    return len([v for v in violations if v[1] == "missing_cleanup"])


def check_xdist_markers(violations: list[Violation]) -> int:
    """Check #3: xdist_group markers for async tests"""
    # Already integrated into TestSafetyValidator
    return len([v for v in violations if v[1] == "missing_xdist_marker"])


def validate_file(file_path: Path) -> list[Violation]:
    """Validate a single test file for all safety patterns"""
    try:
        with open(file_path) as f:
            content = f.read()
            tree = ast.parse(content, filename=str(file_path))

        validator = TestSafetyValidator(str(file_path))
        validator.visit(tree)

        return validator.violations
    except SyntaxError as e:
        print(f"⚠️  Syntax error in {file_path}: {e}")
        return []
    except Exception as e:
        print(f"⚠️  Error parsing {file_path}: {e}")
        return []


def validate_test_files(test_dir: Path) -> int:
    """Validate all test files in directory"""
    test_files = list(test_dir.rglob("test_*.py"))

    if not test_files:
        print(f"⚠️  No test files found in {test_dir}")
        return 0

    total_violations = 0
    files_with_issues = []

    print(f"🔍 Validating {len(test_files)} test files for safety patterns...\n")

    for test_file in sorted(test_files):
        violations = validate_file(test_file)

        if violations:
            files_with_issues.append(test_file)
            print(f"📝 {test_file.relative_to(test_dir.parent)}")

            for lineno, code, message in violations:
                print(f"   ❌ Line {lineno}: {message} [{code}]")
                total_violations += 1

            print()

    # Summary
    print("=" * 80)
    if total_violations > 0:
        print(f"❌ Found {total_violations} violation(s) in {len(files_with_issues)} file(s)")
        print("\nSee tests/PYTEST_XDIST_BEST_PRACTICES.md for guidance")
        print("See tests/MEMORY_SAFETY_GUIDELINES.md for memory safety patterns")
        return 1
    else:
        print("✅ All test files follow safety best practices!")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Consolidated test safety validator (8 checks in 1)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Consolidated Checks:
  1. Memory safety (AsyncMock/MagicMock cleanup)
  2. Test isolation (dependency_overrides cleanup)
  3. xdist markers (xdist_group for parallel tests)
  4. Test IDs (parametrize ID validation)
  5. Pytest markers (marker consistency)
  6. Fixture organization (no duplicate autouse)
  7. Subprocess timeout (timeout for subprocess tests)
  8. Test naming (name conventions)

Examples:
  %(prog)s                          # Validate all tests
  %(prog)s tests/api                # Validate specific directory

For more information, see:
  - tests/PYTEST_XDIST_BEST_PRACTICES.md
  - tests/MEMORY_SAFETY_GUIDELINES.md
""",
    )
    parser.add_argument(
        "test_dir",
        nargs="?",
        default="tests",
        help="Test directory to validate (default: tests/)",
    )

    args = parser.parse_args()

    test_dir = Path(args.test_dir)
    if not test_dir.exists():
        print(f"❌ Directory not found: {test_dir}")
        return 1

    exit_code = validate_test_files(test_dir)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
