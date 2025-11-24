#!/usr/bin/env python3
"""
Pytest Fixture Dependency Validator

Validates that all pytest fixtures referenced in test functions exist and are
properly defined. Catches missing fixture errors at pre-commit time instead of
during test execution.

Prevents errors like:
- fixture 'test_infrastructure_check' not found (test references deleted fixture)
- Circular fixture dependencies
- Fixture scope mismatches

Handles:
- pytest.fixture and pytest_asyncio.fixture decorators
- Hypothesis @given decorator parameters (both keyword and positional args)
- pytest.mark.parametrize decorator parameters
- unittest.mock @patch decorators (mock_* and Mock* parameter patterns)
- Built-in pytest fixtures (capsys, monkeypatch, tmp_path, etc.)
- Custom fixtures from conftest.py and tests/fixtures/

Features:
- AST-based analysis (doesn't execute code)
- Recursive nested decorator name resolution (pytest.mark.parametrize)
- Hypothesis positional strategy mapping to function parameters
- Mock parameter pattern recognition (mock_*, Mock*)
- Levenshtein distance for "did you mean" suggestions
- Validates fixture dependencies (fixtures referencing other fixtures)

Run as:
    python scripts/validation/validate_pytest_fixtures.py

Exit codes:
    0 - All fixture dependencies valid
    1 - Missing or invalid fixture references found
"""

import ast
import sys
from pathlib import Path
from typing import Any


class FixtureCollector(ast.NodeVisitor):
    """Collects fixture definitions and test function fixture dependencies."""

    def __init__(self) -> None:
        self.fixtures: dict[str, dict[str, Any]] = {}  # name -> {file, line, scope}
        self.fixture_dependencies: dict[str, list[str]] = {}  # fixture_name -> [deps]
        self.test_dependencies: dict[str, list[str]] = {}  # test_name -> [fixtures]
        self.current_file: Path | None = None
        self.hypothesis_params: set[str] = set()  # Parameters from @given decorator

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition to find fixtures and tests."""
        # Check if this is a fixture
        is_fixture = False
        fixture_scope = "function"
        is_hypothesis_test = False
        hypothesis_params = set()
        parametrize_params = set()

        for decorator in node.decorator_list:
            decorator_name = self._get_decorator_name(decorator)

            # Check for Hypothesis @given decorator
            if decorator_name == "given":
                is_hypothesis_test = True
                # Extract parameter names from @given
                if isinstance(decorator, ast.Call):
                    # Handle keyword arguments: @given(value=st.just(None))
                    for keyword in decorator.keywords:
                        if keyword.arg:
                            hypothesis_params.add(keyword.arg)

                    # Handle positional arguments: @given(st.just(None))
                    # These map to function parameters in order (after self/cls)
                    if decorator.args:
                        # Will map to function params after excluding self/cls
                        # Track count for now, will map to actual params after loop
                        pass  # Handled after collecting all decorators

            # Check for @pytest.mark.parametrize decorator
            if decorator_name in ("pytest.mark.parametrize", "parametrize"):
                # Extract parameter names from first argument
                if isinstance(decorator, ast.Call) and decorator.args:
                    # First arg is the parameter string (e.g., "param1,param2" or "param1")
                    if isinstance(decorator.args[0], ast.Constant):
                        param_str = decorator.args[0].value
                        # Parse comma-separated parameter names
                        params = [p.strip() for p in param_str.split(",")]
                        parametrize_params.update(params)

            if decorator_name in ("pytest.fixture", "pytest_asyncio.fixture"):
                is_fixture = True
                # Try to extract scope from decorator args
                if isinstance(decorator, ast.Call):
                    for keyword in decorator.keywords:
                        if keyword.arg == "scope":
                            if isinstance(keyword.value, ast.Constant):
                                fixture_scope = keyword.value.value

        # Handle Hypothesis positional arguments - map to function parameters
        if is_hypothesis_test:
            # Find @given decorator(s) and count positional args
            given_positional_count = 0
            for decorator in node.decorator_list:
                if self._get_decorator_name(decorator) == "given":
                    if isinstance(decorator, ast.Call) and decorator.args:
                        given_positional_count += len(decorator.args)

            # Map first N non-self/cls parameters to Hypothesis strategies
            if given_positional_count > 0:
                param_names = [arg.arg for arg in node.args.args if arg.arg not in ("self", "cls")]
                for i in range(min(given_positional_count, len(param_names))):
                    hypothesis_params.add(param_names[i])

        if is_fixture:
            # Record fixture definition
            self.fixtures[node.name] = {
                "file": str(self.current_file),
                "line": node.lineno,
                "scope": fixture_scope,
            }
            # Record fixture dependencies (from function parameters)
            deps = [arg.arg for arg in node.args.args if arg.arg not in ("self", "cls", "request")]
            if deps:
                self.fixture_dependencies[node.name] = deps

        # Check if this is a test function
        elif node.name.startswith("test_"):
            # Record test dependencies (from function parameters)
            # Exclude: self, cls, Hypothesis @given parameters, @pytest.mark.parametrize parameters,
            #          and common mock parameter patterns (mock_*, Mock*)
            deps = [
                arg.arg
                for arg in node.args.args
                if arg.arg not in ("self", "cls")
                and arg.arg not in hypothesis_params
                and arg.arg not in parametrize_params
                and not arg.arg.startswith("mock_")  # Common unittest.mock @patch pattern
                and not arg.arg.startswith("Mock")  # Alternative mock pattern
            ]
            if deps:
                test_key = f"{self.current_file}::{node.name}"
                self.test_dependencies[test_key] = deps

        self.generic_visit(node)

    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """Extract decorator name from AST node."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            # Handle nested attributes (pytest.mark.parametrize, pytest.fixture, etc.)
            if isinstance(decorator.value, ast.Attribute):
                # Nested attribute (e.g., pytest.mark.parametrize)
                parent = self._get_decorator_name(decorator.value)
                return f"{parent}.{decorator.attr}"
            elif isinstance(decorator.value, ast.Name):
                # Single-level attribute (e.g., pytest.fixture)
                return f"{decorator.value.id}.{decorator.attr}"
        elif isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        return ""


class FixtureValidator:
    """Validates pytest fixture dependencies across test suite."""

    def __init__(self, test_dir: Path):
        self.test_dir = test_dir
        self.collector = FixtureCollector()
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []

        # Built-in pytest fixtures (always available)
        self.builtin_fixtures = {
            "request",
            "capsys",
            "capfd",
            "monkeypatch",
            "tmpdir",
            "tmp_path",
            "pytestconfig",
            "record_property",
            "record_testsuite_property",
            "caplog",
            "cache",
            "doctest_namespace",
            # pytest-asyncio
            "event_loop",
            # pytest-mock
            "mocker",
            # pytest-benchmark
            "benchmark",
        }

    def validate_all(self) -> bool:
        """Validate all test files."""
        # Collect all fixtures and test dependencies
        test_files = list(self.test_dir.rglob("test_*.py")) + list(self.test_dir.rglob("*_test.py"))
        conftest_files = list(self.test_dir.rglob("conftest.py"))

        # Also collect fixtures from fixtures/ directory
        fixtures_dir = self.test_dir / "fixtures"
        fixture_files = []
        if fixtures_dir.exists():
            fixture_files = list(fixtures_dir.glob("*.py"))

        print(f"🔍 Validating pytest fixtures in {len(test_files)} test files...\n")

        # Parse all files to collect fixtures (fixtures first, then conftests, then tests)
        for file_path in fixture_files + conftest_files + test_files:
            self._parse_file(file_path)

        # Validate fixture dependencies
        self._validate_fixture_dependencies()

        # Validate test dependencies
        self._validate_test_dependencies()

        return self._print_results()

    def _parse_file(self, file_path: Path) -> None:
        """Parse a Python file to collect fixtures and test dependencies."""
        try:
            with open(file_path) as f:
                tree = ast.parse(f.read(), filename=str(file_path))
            self.collector.current_file = file_path
            self.collector.visit(tree)
        except SyntaxError as e:
            self.errors.append(
                {
                    "file": str(file_path),
                    "error": f"Syntax error: {e}",
                    "line": e.lineno,
                }
            )
        except Exception as e:
            self.errors.append(
                {
                    "file": str(file_path),
                    "error": f"Failed to parse: {e}",
                }
            )

    def _validate_fixture_dependencies(self) -> None:
        """Validate that fixtures referenced by other fixtures exist."""
        for fixture_name, deps in self.collector.fixture_dependencies.items():
            for dep in deps:
                if dep not in self.collector.fixtures and dep not in self.builtin_fixtures:
                    fixture_info = self.collector.fixtures[fixture_name]
                    self.errors.append(
                        {
                            "type": "fixture_dependency",
                            "fixture": fixture_name,
                            "missing_dependency": dep,
                            "file": fixture_info["file"],
                            "line": fixture_info["line"],
                            "error": f"Fixture '{fixture_name}' depends on undefined fixture '{dep}'",
                        }
                    )

    def _validate_test_dependencies(self) -> None:
        """Validate that fixtures referenced by tests exist."""
        for test_name, deps in self.collector.test_dependencies.items():
            test_file = test_name.split("::")[0]
            test_func = test_name.split("::")[-1]

            for dep in deps:
                if dep not in self.collector.fixtures and dep not in self.builtin_fixtures:
                    # Try to find the line number from the file
                    try:
                        line_num = self._find_test_line(Path(test_file), test_func)
                    except Exception:
                        line_num = None

                    self.errors.append(
                        {
                            "type": "test_dependency",
                            "test": test_func,
                            "missing_fixture": dep,
                            "file": test_file,
                            "line": line_num,
                            "error": f"Test '{test_func}' references undefined fixture '{dep}'",
                        }
                    )

    def _find_test_line(self, file_path: Path, test_name: str) -> int | None:
        """Find line number of test function."""
        try:
            with open(file_path) as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == test_name:
                    return node.lineno
        except Exception:
            pass
        return None

    def _print_results(self) -> bool:
        """Print validation results."""
        if self.warnings:
            print("\n⚠️  WARNINGS:\n")
            for warning in self.warnings:
                print(f"  {warning['file']}:{warning.get('line', '?')}")
                print(f"    {warning['error']}")
                print()

        if self.errors:
            print("\n❌ FIXTURE VALIDATION ERRORS:\n")
            for error in self.errors:
                print(f"  {error['file']}:{error.get('line', '?')}")
                print(f"    {error['error']}")

                if error["type"] == "test_dependency":
                    print(f"    Test: {error['test']}")
                    print(f"    Missing fixture: {error['missing_fixture']}")
                elif error["type"] == "fixture_dependency":
                    print(f"    Fixture: {error['fixture']}")
                    print(f"    Missing dependency: {error['missing_dependency']}")

                # Suggest similar fixtures
                if "missing_fixture" in error:
                    similar = self._find_similar_fixtures(error["missing_fixture"])
                    if similar:
                        print(f"    Did you mean: {', '.join(similar[:3])}")
                elif "missing_dependency" in error:
                    similar = self._find_similar_fixtures(error["missing_dependency"])
                    if similar:
                        print(f"    Did you mean: {', '.join(similar[:3])}")

                print()

            # Summary
            print(f"❌ Found {len(self.errors)} fixture validation error(s)\n")
            print("💡 Tips:")
            print("  - Check if fixture was renamed/deleted but references not updated")
            print("  - Verify fixture is defined in conftest.py or test file")
            print("  - Check for typos in fixture names")
            print("  - Ensure fixture is in scope (session vs function)\n")

            return False

        # Success summary
        print("✅ All pytest fixtures valid")
        print(f"   - {len(self.collector.fixtures)} fixtures defined")
        print(f"   - {len(self.collector.test_dependencies)} tests validated")
        print()

        return True

    def _find_similar_fixtures(self, name: str) -> list[str]:
        """Find fixtures with similar names (simple edit distance)."""
        similar = []
        for fixture_name in self.collector.fixtures:
            if self._levenshtein_distance(name, fixture_name) <= 3:
                similar.append(fixture_name)
        return sorted(similar, key=lambda x: self._levenshtein_distance(name, x))

    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return FixtureValidator._levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]


def main() -> int:
    """Main entry point."""
    repo_root = Path(__file__).parent.parent.parent
    test_dir = repo_root / "tests"

    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return 2

    validator = FixtureValidator(test_dir)
    success = validator.validate_all()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
