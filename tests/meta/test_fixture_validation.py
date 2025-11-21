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
import gc
from pathlib import Path

import pytest

pytestmark = pytest.mark.meta


@pytest.mark.xdist_group(name="testfixturedecorators")
class TestFixtureDecorators:
    """Meta-tests to validate pytest fixture decorators"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

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
            "caplog",  # Built-in logging capture
            "capfdbinary",
            "capsysbinary",
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
            "benchmark",  # pytest-benchmark
        }

        # Find test functions with undefined fixture parameters
        violations = []
        tests_dir = Path(__file__).parent.parent

        for test_file in tests_dir.rglob("test_*.py"):
            if test_file.parent.name == "meta":
                continue

            try:
                with open(test_file, encoding="utf-8") as f:
                    content = f.read()
                    tree = ast.parse(content, filename=str(test_file))

                # Only check top-level functions (not nested inside other functions)
                for node in tree.body:
                    # Handle module-level functions and class methods
                    if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                        self._check_test_function_params(
                            node, test_file, tests_dir, defined_fixtures, builtin_fixtures, violations
                        )
                    elif isinstance(node, ast.ClassDef):
                        # Check class methods
                        for class_node in node.body:
                            if isinstance(class_node, ast.FunctionDef) and class_node.name.startswith("test_"):
                                self._check_test_function_params(
                                    class_node, test_file, tests_dir, defined_fixtures, builtin_fixtures, violations
                                )

            except (SyntaxError, UnicodeDecodeError):
                continue

        if violations:
            error_msg = "Found test functions with undefined fixture parameters:\n"
            for file_path, test_name, param_name, line_num in violations:
                error_msg += f"\n  {file_path}:{line_num} - {test_name}()\n"
                error_msg += f"    Parameter '{param_name}' is not a defined fixture\n"
            error_msg += "\nEnsure all test parameters have corresponding @pytest.fixture definitions."
            pytest.fail(error_msg)

    def _find_generator_functions_without_fixture_decorator(self) -> list[tuple[str, str, int]]:
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
                    with open(test_file, encoding="utf-8") as f:
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

    def _check_test_function_params(
        self,
        func_node: ast.FunctionDef,
        test_file: Path,
        tests_dir: Path,
        defined_fixtures: set[str],
        builtin_fixtures: set[str],
        violations: list[tuple[str, str, str, int]],
    ) -> None:
        """
        Check test function parameters for valid fixtures

        Args:
            func_node: AST node for the test function
            test_file: Path to the test file
            tests_dir: Base tests directory
            defined_fixtures: Set of defined fixture names
            builtin_fixtures: Set of builtin fixture names
            violations: List to append violations to
        """
        # Skip Hypothesis tests (they use strategies, not fixtures)
        if self._has_hypothesis_given_decorator(func_node):
            return

        # Get parametrize parameter names for this test
        parametrize_params = self._get_parametrize_params(func_node)

        # Get patch parameter names (from @patch decorators)
        patch_params = self._get_patch_params(func_node)

        # Check each parameter
        for arg in func_node.args.args:
            param_name = arg.arg
            if param_name == "self":
                continue

            # Skip parametrize parameters
            if param_name in parametrize_params:
                continue

            # Skip patch parameters (from @patch decorators)
            if param_name in patch_params:
                continue

            # Check if fixture exists
            if param_name not in defined_fixtures and param_name not in builtin_fixtures:
                rel_path = test_file.relative_to(tests_dir.parent)
                violations.append((str(rel_path), func_node.name, param_name, func_node.lineno))

    def _get_parametrize_params(self, func_node: ast.FunctionDef) -> set[str]:
        """
        Get parameter names from @pytest.mark.parametrize decorators

        Args:
            func_node: AST node for the function

        Returns:
            Set of parameter names from parametrize decorators
        """
        params = set()

        for decorator in func_node.decorator_list:
            # Check for @pytest.mark.parametrize("param_name", ...)
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    # Check if it's pytest.mark.parametrize
                    if (
                        isinstance(decorator.func.value, ast.Attribute)
                        and isinstance(decorator.func.value.value, ast.Name)
                        and decorator.func.value.value.id == "pytest"
                        and decorator.func.value.attr == "mark"
                        and decorator.func.attr == "parametrize"
                    ):
                        # Get first argument (parameter names)
                        if decorator.args and isinstance(decorator.args[0], ast.Constant):
                            param_str = decorator.args[0].value
                            # Handle "param" or "param1,param2" formats
                            param_names = [p.strip() for p in param_str.split(",")]
                            params.update(param_names)

        return params

    def _get_patch_params(self, func_node: ast.FunctionDef) -> set[str]:
        """
        Get parameter names from @patch decorators

        @patch decorators inject mock objects as function parameters.
        Multiple @patch decorators inject parameters in reverse order.

        Args:
            func_node: AST node for the function

        Returns:
            Set of parameter names that come from @patch decorators
        """
        # Count @patch decorators (they inject parameters in reverse order)
        patch_count = 0

        for decorator in func_node.decorator_list:
            # Check for @patch("...") or @patch.object(...)
            if isinstance(decorator, ast.Call):
                if (
                    isinstance(decorator.func, ast.Name)
                    and decorator.func.id == "patch"
                    or isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr in ["object", "dict", "multiple"]
                ):
                    patch_count += 1

        # Get the last N parameters (where N = patch_count)
        # @patch decorators inject parameters in reverse order of application
        if patch_count > 0 and func_node.args.args:
            # Skip 'self' if present
            args = [arg.arg for arg in func_node.args.args if arg.arg != "self"]
            # Last N parameters are from @patch decorators
            return set(args[:patch_count]) if patch_count <= len(args) else set(args)

        return set()

    def _find_placeholder_tests(self) -> list[tuple[str, str, int]]:
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
                with open(test_file, encoding="utf-8") as f:
                    content = f.read()
                    tree = ast.parse(content, filename=str(test_file))

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                        # Check if function has only 'pass' statement
                        if self._has_only_pass_statement(node):
                            # Check if it's marked with xfail, skip, or documentation (those are OK)
                            if not self._has_skip_xfail_or_documentation_marker(node):
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
            # Skip docstrings (first Expr node with Constant)
            # Note: Using ast.Constant (Python 3.8+) instead of deprecated ast.Str (removed in Python 3.14)
            if isinstance(stmt, ast.Expr):
                if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                    continue
            body_statements.append(stmt)

        # Check if only statement is 'pass'
        if len(body_statements) == 1:
            if isinstance(body_statements[0], ast.Pass):
                return True

        return False

    def _has_skip_xfail_or_documentation_marker(self, func_node: ast.FunctionDef) -> bool:
        """
        Check if a function has @pytest.mark.skip, @pytest.mark.xfail, or @pytest.mark.documentation

        Args:
            func_node: AST node for the function

        Returns:
            True if function has skip, xfail, or documentation marker, False otherwise
        """
        for decorator in func_node.decorator_list:
            # Check for @pytest.mark.skip, @pytest.mark.xfail, or @pytest.mark.documentation
            if isinstance(decorator, ast.Attribute):
                if (
                    isinstance(decorator.value, ast.Attribute)
                    and isinstance(decorator.value.value, ast.Name)
                    and decorator.value.value.id == "pytest"
                    and decorator.value.attr == "mark"
                    and decorator.attr in ["skip", "xfail", "documentation"]
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

    @pytest.mark.unit
    def test_fixture_scope_dependencies_are_compatible(self):
        """
        TDD REGRESSION TEST: Ensure fixture scopes are compatible with their dependencies

        GIVEN: All fixtures in conftest.py and test files
        WHEN: Analyzing fixture dependencies
        THEN: Fixtures with wider scopes should not depend on fixtures with narrower scopes

        Scope hierarchy (widest to narrowest):
        - session: Fixture runs once per test session
        - package: Fixture runs once per package
        - module: Fixture runs once per module
        - class: Fixture runs once per class
        - function: Fixture runs once per test function (default)

        RULE: A fixture can only depend on fixtures with equal or wider scope.
        Example violations:
        - session-scoped fixture depending on function-scoped fixture ❌
        - module-scoped fixture depending on function-scoped fixture ❌
        - function-scoped fixture depending on session-scoped fixture ✅ (OK)

        This prevents pytest ScopeMismatch errors and ensures fixtures work correctly.
        """
        violations = self._find_fixture_scope_violations()

        if violations:
            error_msg = "Found fixture scope compatibility violations:\n"
            for file_path, fixture_name, fixture_scope, dep_name, dep_scope, line_num in violations:
                error_msg += f"\n  {file_path}:{line_num} - {fixture_name}() [scope={fixture_scope}]\n"
                error_msg += f"    depends on: {dep_name}() [scope={dep_scope}]\n"
                error_msg += f"    ❌ {fixture_scope}-scoped fixture cannot depend on {dep_scope}-scoped fixture\n"
            error_msg += (
                "\n💡 Fix: Change fixture scope to match or be narrower than its dependencies.\n"
                "Example: If fixture depends on function-scoped fixtures, it must also be function-scoped."
            )
            pytest.fail(error_msg)

    def _find_fixture_scope_violations(self) -> list[tuple[str, str, str, str, str, int]]:
        """
        Find fixtures with scope incompatibilities

        Returns:
            List of (file_path, fixture_name, fixture_scope, dependency_name, dependency_scope, line_number) tuples
        """
        violations = []
        tests_dir = Path(__file__).parent.parent

        # Define scope hierarchy (wider scopes have higher values)
        scope_hierarchy = {
            "function": 1,  # Narrowest scope (default)
            "class": 2,
            "module": 3,
            "package": 4,
            "session": 5,  # Widest scope
        }

        # Get all fixtures with their scopes and dependencies
        fixtures_info = self._get_all_fixtures_with_dependencies()

        # Check each fixture
        for fixture_file, fixture_name, fixture_scope, dep_names, line_num in fixtures_info:
            # Get scope value (default to function if not specified)
            fixture_scope_value = scope_hierarchy.get(fixture_scope, scope_hierarchy["function"])

            # Check each dependency
            for dep_name in dep_names:
                # Find the dependency fixture
                dep_scope = None
                dep_found = False
                for dep_file, dep_fixture_name, dep_fixture_scope, _, _ in fixtures_info:
                    if dep_fixture_name == dep_name:
                        dep_scope = dep_fixture_scope
                        dep_found = True
                        break

                # Only check fixtures (skip built-in params like 'request', 'monkeypatch', etc.)
                if dep_found:
                    dep_scope_value = scope_hierarchy.get(dep_scope, scope_hierarchy["function"])

                    # Violation: Fixture has wider scope than its dependency
                    if fixture_scope_value > dep_scope_value:
                        rel_path = fixture_file.relative_to(tests_dir.parent)
                        violations.append(
                            (
                                str(rel_path),
                                fixture_name,
                                fixture_scope or "function",
                                dep_name,
                                dep_scope or "function",
                                line_num,
                            )
                        )

        return violations

    def _get_all_fixtures_with_dependencies(self) -> list[tuple[Path, str, str, list[str], int]]:
        """
        Get all fixtures with their scopes and parameter dependencies

        Returns:
            List of (file_path, fixture_name, scope, dependency_names, line_number) tuples
        """
        fixtures_info = []
        tests_dir = Path(__file__).parent.parent

        # Search in conftest.py and test files
        search_patterns = ["test_*.py", "conftest.py"]

        for pattern in search_patterns:
            for test_file in tests_dir.rglob(pattern):
                try:
                    with open(test_file) as f:
                        content = f.read()
                        tree = ast.parse(content, filename=str(test_file))

                    for node in ast.walk(tree):
                        # Check both regular and async functions
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if self._has_fixture_decorator(node):
                                # Get fixture scope
                                scope = self._get_fixture_scope(node)

                                # Get parameter names (dependencies)
                                param_names = [arg.arg for arg in node.args.args if arg.arg != "self"]

                                fixtures_info.append((test_file, node.name, scope, param_names, node.lineno))

                except (SyntaxError, UnicodeDecodeError):
                    continue

        return fixtures_info

    def _get_fixture_scope(self, func_node: ast.FunctionDef) -> str:
        """
        Extract the scope parameter from @pytest.fixture decorator

        Args:
            func_node: AST node for the fixture function

        Returns:
            Scope string ("session", "module", "class", "function") or None if not specified
        """
        for decorator in func_node.decorator_list:
            # Check for @pytest.fixture(scope="session")
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if (
                        isinstance(decorator.func.value, ast.Name)
                        and decorator.func.value.id == "pytest"
                        and decorator.func.attr == "fixture"
                    ):
                        # Look for scope keyword argument
                        for keyword in decorator.keywords:
                            if keyword.arg == "scope":
                                if isinstance(keyword.value, ast.Constant):
                                    return keyword.value.value

        # No scope specified = function scope (default)
        return None

    def _get_all_defined_fixtures(self) -> set[str]:
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
                    with open(test_file, encoding="utf-8") as f:
                        content = f.read()
                        tree = ast.parse(content, filename=str(test_file))

                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            if self._has_fixture_decorator(node):
                                fixtures.add(node.name)

                except (SyntaxError, UnicodeDecodeError):
                    continue

        return fixtures
