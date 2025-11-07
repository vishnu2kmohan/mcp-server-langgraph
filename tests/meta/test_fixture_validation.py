"""
Meta-tests to validate pytest fixture definitions and prevent missing decorators

TDD Regression Test: Validates that all fixture-like functions have proper @pytest.fixture decorators
to prevent silent failures where fixtures don't actually execute.

Tests cover:
1. Generator-returning functions have @pytest.fixture decorator
2. Functions used as test parameters have @pytest.fixture decorator

These tests ensure fixtures are properly configured and will execute as expected.

References:
- OpenAI Codex finding: test_health_check.py:11 missing @pytest.fixture (now fixed)
- pytest fixture documentation
"""

import ast
from pathlib import Path
from typing import List, Set, Tuple

import pytest


class TestFixtureDecorators:
    """Meta-tests to validate pytest fixture decorators"""

    @pytest.mark.unit
    def test_no_placeholder_tests_with_only_pass(self):
        """
        TDD REGRESSION TEST: Ensure test functions don't have only 'pass' statement

        GIVEN: All test files in the test suite
        WHEN: Scanning for test functions
        THEN: No test should have only 'pass' as its body (unless it's xfail/skip)

        This prevents incomplete tests from silently passing.
        Tests should either:
        1. Have actual test logic
        2. Use @pytest.mark.xfail(strict=True) if not implemented yet
        3. Use @pytest.mark.skip with a valid reason
        """
        violations = self._find_placeholder_tests()

        if violations:
            error_msg = "Found test functions with only 'pass' statement:\n"
            for file_path, test_name, line_num in violations:
                error_msg += f"\n  {file_path}:{line_num} - {test_name}()\n"
            error_msg += (
                "\n❌ Remove 'pass'-only tests or mark them with @pytest.mark.xfail(strict=True).\n"
                "✅ Every test should either have assertions or be explicitly marked as incomplete."
            )
            pytest.fail(error_msg)

    @pytest.mark.unit
    def test_generator_functions_have_fixture_decorator(self):
        """
        TDD REGRESSION TEST: Ensure Generator-returning functions have @pytest.fixture decorator

        GIVEN: All test files and conftest.py in the test suite
        WHEN: Scanning for functions that return Generator types
        THEN: They should have @pytest.fixture decorator if they look like fixtures

        This prevents bugs where fixture-like functions don't execute because
        they're missing the decorator, causing tests to silently fail or use
        wrong fixtures.
        """
        violations = self._find_generator_functions_without_fixture_decorator()

        if violations:
            error_msg = "Found Generator-returning functions without @pytest.fixture decorator:\n"
            for file_path, func_name, line_num in violations:
                error_msg += f"\n  {file_path}:{line_num} - function '{func_name}()'\n"
                error_msg += "    This function returns Generator but lacks @pytest.fixture decorator\n"
            error_msg += (
                "\nAdd @pytest.fixture decorator to these functions to ensure they work as fixtures.\n"
                "If they're not meant to be fixtures, rename them to not follow fixture naming patterns."
            )
            pytest.fail(error_msg)

    @pytest.mark.unit
    def test_fixture_parameters_have_valid_fixtures(self):
        """
        TDD REGRESSION TEST: Ensure test functions only reference valid fixtures

        GIVEN: All test files
        WHEN: Scanning for test function parameters
        THEN: Each parameter should either:
            - Have a corresponding @pytest.fixture in scope
            - Be a built-in pytest fixture (e.g., request, monkeypatch)
            - Be from pytest-asyncio (e.g., event_loop)

        This catches typos in fixture names and ensures all fixtures are properly defined.
        """
        # Get all defined fixtures
        defined_fixtures = self._get_all_defined_fixtures()

        # Built-in and plugin fixtures
        builtin_fixtures = {
            "request",
            "monkeypatch",
            "capsys",
            "capfd",
            "tmpdir",
            "tmp_path",
            "pytestconfig",
            "cache",
            "record_property",
            "record_xml_attribute",
            "recwarn",
            "event_loop",  # pytest-asyncio
            "unused_tcp_port",  # pytest-asyncio
            "unused_tcp_port_factory",  # pytest-asyncio
        }

        # Find test functions with undefined fixture parameters
        violations = []
        tests_dir = Path(__file__).parent.parent

        for test_file in tests_dir.rglob("test_*.py"):
            if test_file.parent.name == "meta":
                continue

            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    tree = ast.parse(content, filename=str(test_file))

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                        # Skip Hypothesis tests (they use strategies, not fixtures)
                        if self._has_hypothesis_given_decorator(node):
                            continue

                        # Check each parameter
                        for arg in node.args.args:
                            param_name = arg.arg
                            if param_name == "self":
                                continue

                            # Check if fixture exists
                            if param_name not in defined_fixtures and param_name not in builtin_fixtures:
                                rel_path = test_file.relative_to(tests_dir.parent)
                                violations.append((str(rel_path), node.name, param_name, node.lineno))

            except (SyntaxError, UnicodeDecodeError):
                continue

        if violations:
            error_msg = "Found test functions with undefined fixture parameters:\n"
            for file_path, test_name, param_name, line_num in violations:
                error_msg += f"\n  {file_path}:{line_num} - {test_name}()\n"
                error_msg += f"    Parameter '{param_name}' is not a defined fixture\n"
            error_msg += "\nEnsure all test parameters have corresponding @pytest.fixture definitions."
            pytest.fail(error_msg)

    def _find_generator_functions_without_fixture_decorator(self) -> List[Tuple[str, str, int]]:
        """
        Find Generator-returning functions without @pytest.fixture decorator

        Returns:
            List of (file_path, function_name, line_number) tuples
        """
        violations = []
        tests_dir = Path(__file__).parent.parent

        # Check both test files and conftest.py
        search_patterns = ["test_*.py", "conftest.py"]

        for pattern in search_patterns:
            for test_file in tests_dir.rglob(pattern):
                if test_file.parent.name == "meta":
                    continue

                try:
                    with open(test_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        tree = ast.parse(content, filename=str(test_file))

                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            # Check if function returns Generator
                            if self._returns_generator(node):
                                # Check if it has @pytest.fixture decorator
                                if not self._has_fixture_decorator(node):
                                    # Check if it looks like a fixture (naming patterns)
                                    if self._looks_like_fixture(node.name):
                                        rel_path = test_file.relative_to(tests_dir.parent)
                                        violations.append((str(rel_path), node.name, node.lineno))

                except (SyntaxError, UnicodeDecodeError):
                    continue

        return violations

    def _returns_generator(self, func_node: ast.FunctionDef) -> bool:
        """
        Check if a function has Generator return type annotation

        Args:
            func_node: AST node for the function

        Returns:
            True if function returns Generator, False otherwise
        """
        if not func_node.returns:
            # Also check for yield statements (generators without type hints)
            for node in ast.walk(func_node):
                if isinstance(node, (ast.Yield, ast.YieldFrom)):
                    return True
            return False

        # Check type annotation
        return_annotation = func_node.returns

        # Handle Generator[...] type annotation
        if isinstance(return_annotation, ast.Subscript):
            if isinstance(return_annotation.value, ast.Name):
                if return_annotation.value.id == "Generator":
                    return True

        # Also check for yield in function body (runtime behavior)
        for node in ast.walk(func_node):
            if isinstance(node, (ast.Yield, ast.YieldFrom)):
                return True

        return False

    def _has_fixture_decorator(self, func_node: ast.FunctionDef) -> bool:
        """
        Check if a function has @pytest.fixture decorator

        Args:
            func_node: AST node for the function

        Returns:
            True if function has @pytest.fixture, False otherwise
        """
        for decorator in func_node.decorator_list:
            # @pytest.fixture
            if isinstance(decorator, ast.Attribute):
                if isinstance(decorator.value, ast.Name) and decorator.value.id == "pytest" and decorator.attr == "fixture":
                    return True

            # @pytest.fixture(...)
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if (
                        isinstance(decorator.func.value, ast.Name)
                        and decorator.func.value.id == "pytest"
                        and decorator.func.attr == "fixture"
                    ):
                        return True

        return False

    def _looks_like_fixture(self, func_name: str) -> bool:
        """
        Check if a function name follows fixture naming conventions

        Args:
            func_name: Name of the function

        Returns:
            True if name looks like a fixture, False otherwise
        """
        # Common fixture name patterns
        fixture_patterns = [
            "test_",
            "mock_",
            "sample_",
            "_client",
            "_session",
            "_connection",
            "_fixture",
            "_factory",
            "_db",
            "_app",
            "_api",
            "_service",
        ]

        name_lower = func_name.lower()

        for pattern in fixture_patterns:
            if pattern in name_lower:
                return True

        return False

    def _has_hypothesis_given_decorator(self, func_node: ast.FunctionDef) -> bool:
        """
        Check if a function has @given decorator from Hypothesis

        Args:
            func_node: AST node for the function

        Returns:
            True if function has @given decorator, False otherwise
        """
        for decorator in func_node.decorator_list:
            # @given(...) or @hypothesis.given(...)
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name) and decorator.func.id == "given":
                    return True
                elif isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr == "given":
                        return True

        return False

    def _find_placeholder_tests(self) -> List[Tuple[str, str, int]]:
        """
        Find test functions that have only 'pass' statement

        Returns:
            List of (file_path, function_name, line_number) tuples
        """
        violations = []
        tests_dir = Path(__file__).parent.parent

        for test_file in tests_dir.rglob("test_*.py"):
            if test_file.parent.name == "meta":
                continue

            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    tree = ast.parse(content, filename=str(test_file))

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                        # Check if function has only 'pass' statement
                        if self._has_only_pass_statement(node):
                            # Check if it's marked with xfail or skip (those are OK)
                            if not self._has_skip_or_xfail_marker(node):
                                rel_path = test_file.relative_to(tests_dir.parent)
                                violations.append((str(rel_path), node.name, node.lineno))

            except (SyntaxError, UnicodeDecodeError):
                continue

        return violations

    def _has_only_pass_statement(self, func_node: ast.FunctionDef) -> bool:
        """
        Check if a function has only 'pass' as its body

        Args:
            func_node: AST node for the function

        Returns:
            True if function has only 'pass', False otherwise
        """
        # Filter out docstrings
        body_statements = []
        for stmt in func_node.body:
            # Skip docstrings (first Expr node with Constant/Str)
            if isinstance(stmt, ast.Expr):
                if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                    continue
                elif isinstance(stmt.value, ast.Str):  # Python 3.7 compatibility
                    continue
            body_statements.append(stmt)

        # Check if only statement is 'pass'
        if len(body_statements) == 1:
            if isinstance(body_statements[0], ast.Pass):
                return True

        return False

    def _has_skip_or_xfail_marker(self, func_node: ast.FunctionDef) -> bool:
        """
        Check if a function has @pytest.mark.skip or @pytest.mark.xfail

        Args:
            func_node: AST node for the function

        Returns:
            True if function has skip or xfail marker, False otherwise
        """
        for decorator in func_node.decorator_list:
            # Check for @pytest.mark.skip or @pytest.mark.xfail
            if isinstance(decorator, ast.Attribute):
                if (
                    isinstance(decorator.value, ast.Attribute)
                    and isinstance(decorator.value.value, ast.Name)
                    and decorator.value.value.id == "pytest"
                    and decorator.value.attr == "mark"
                    and decorator.attr in ["skip", "xfail"]
                ):
                    return True
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if (
                        isinstance(decorator.func.value, ast.Attribute)
                        and isinstance(decorator.func.value.value, ast.Name)
                        and decorator.func.value.value.id == "pytest"
                        and decorator.func.value.attr == "mark"
                        and decorator.func.attr in ["skip", "xfail"]
                    ):
                        return True

        return False

    def _get_all_defined_fixtures(self) -> Set[str]:
        """
        Get all fixture names defined in the test suite

        Returns:
            Set of fixture names
        """
        fixtures = set()
        tests_dir = Path(__file__).parent.parent

        # Search in conftest.py and all test files
        search_patterns = ["test_*.py", "conftest.py"]

        for pattern in search_patterns:
            for test_file in tests_dir.rglob(pattern):
                try:
                    with open(test_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        tree = ast.parse(content, filename=str(test_file))

                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            if self._has_fixture_decorator(node):
                                fixtures.add(node.name)

                except (SyntaxError, UnicodeDecodeError):
                    continue

        return fixtures
