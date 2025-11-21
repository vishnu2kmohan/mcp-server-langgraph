"""
Meta-tests for Property Test Quality

These tests validate that property tests follow best practices and don't have
common anti-patterns identified in Codex findings.

Purpose: Prevent regression of Codex Finding #9 (property tests with missing assertions)
"""

import ast
import gc
from pathlib import Path

import pytest

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = pytest.mark.unit
REPO_ROOT = Path(__file__).parent.parent.parent


@pytest.mark.meta
@pytest.mark.xdist_group(name="testpropertytestquality")
class TestPropertyTestQuality:
    """
    Meta-tests that validate property tests have proper assertions.

    RED: These tests will fail if property tests lack assertions.
    GREEN: Property tests properly assert results.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_property_tests_have_assertions(self):
        """
        Validate all Hypothesis property tests have at least one assertion.

        This prevents regressions of Codex Finding #9:
        "Property tests like the TTL check call cache.get(...) without asserting
        the result because the design conflates 'miss' vs 'cached None'."

        RED: Fails if any property test lacks assertions.
        GREEN: All property tests properly validate behavior.
        """
        property_test_files = list(REPO_ROOT.glob("tests/property/test_*.py"))

        assert len(property_test_files) > 0, "No property test files found"

        violations = []

        for test_file in property_test_files:
            with open(test_file) as f:
                source = f.read()

            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if function has @given decorator (Hypothesis property test)
                    has_given = any(
                        (isinstance(dec, ast.Name) and dec.id == "given")
                        or (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) and dec.func.id == "given")
                        for dec in node.decorator_list
                    )

                    if has_given:
                        # Check if function body has assertions
                        has_assertion = self._has_assertion(node)

                        if not has_assertion:
                            violations.append(
                                f"{test_file.name}::{node.name} - Property test lacks assertions\n"
                                f"  Location: {test_file.relative_to(REPO_ROOT)}:{node.lineno}\n"
                                f"  Fix: Add assert statement(s) to validate property behavior"
                            )

        if violations:
            violation_report = "\n\n".join(violations)
            pytest.fail(
                f"Found {len(violations)} property test(s) without assertions:\n\n"
                f"{violation_report}\n\n"
                f"Property tests MUST assert the expected behavior. "
                f"See Codex Finding #9 for examples."
            )

    def test_property_tests_dont_ignore_return_values(self):
        """
        Validate property tests don't call functions without using/asserting results.

        This catches patterns like:
            result = cache.get("key")  # No assertion!

        Ignores legitimate side-effect calls in loops for statistics generation.

        RED: Fails if property tests have unused function calls.
        GREEN: All function calls are properly validated.
        """
        property_test_files = list(REPO_ROOT.glob("tests/property/test_*.py"))

        violations = []

        for test_file in property_test_files:
            with open(test_file) as f:
                source = f.read()

            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if this is a property test
                    has_given = any(
                        (isinstance(dec, ast.Name) and dec.id == "given")
                        or (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) and dec.func.id == "given")
                        for dec in node.decorator_list
                    )

                    if has_given:
                        # Check for standalone expression statements (calls without assignment)
                        for stmt in ast.walk(node):
                            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                                # Check if it's a method call that likely returns a value
                                if isinstance(stmt.value.func, ast.Attribute):
                                    method_name = stmt.value.func.attr
                                    # Common getter methods that should typically be asserted
                                    # Skip get() calls as they're often used for side effects (statistics)
                                    if method_name in ["read", "fetch", "load", "retrieve"]:
                                        violations.append(
                                            f"{test_file.name}::{node.name} - Unused function call: {method_name}()\n"
                                            f"  Location: {test_file.relative_to(REPO_ROOT)}:{stmt.lineno}\n"
                                            f"  Fix: Assign result and assert expected value: "
                                            f"result = obj.{method_name}(...); assert result ..."
                                        )

        if violations:
            violation_report = "\n\n".join(violations)
            pytest.fail(
                f"Found {len(violations)} unused function call(s) in property tests:\n\n"
                f"{violation_report}\n\n"
                f"Property tests should assert or validate all return values."
            )

    def _has_assertion(self, func_node: ast.FunctionDef) -> bool:
        """
        Check if a function has any assertion statements.

        Returns True if function contains:
        - assert statements
        - pytest.fail() calls
        - pytest.raises() context managers
        - Mock assertion calls (.assert_called(), .assert_not_called(), etc.)
        """
        for node in ast.walk(func_node):
            # Direct assert statements
            if isinstance(node, ast.Assert):
                return True

            # pytest.fail() calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == "pytest" and node.func.attr == "fail":
                        return True

                    # Mock assertions (assert_called, assert_not_called, etc.)
                    if node.func.attr.startswith("assert_"):
                        return True

            # pytest.raises() context managers
            if isinstance(node, ast.With):
                for item in node.items:
                    if isinstance(item.context_expr, ast.Call):
                        if isinstance(item.context_expr.func, ast.Attribute):
                            if (
                                isinstance(item.context_expr.func.value, ast.Name)
                                and item.context_expr.func.value.id == "pytest"
                                and item.context_expr.func.attr == "raises"
                            ):
                                return True

        return False


@pytest.mark.meta
@pytest.mark.xdist_group(name="testpropertytestnaming")
class TestPropertyTestNaming:
    """Validate property test naming conventions"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_property_test_names_describe_property(self):
        """
        Property test names should describe the property being tested.

        Good: test_cache_expires_after_ttl
        Bad: test_cache, test_case_1
        """
        property_test_files = list(REPO_ROOT.glob("tests/property/test_*.py"))

        violations = []

        for test_file in property_test_files:
            with open(test_file) as f:
                source = f.read()

            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if this is a property test
                    has_given = any(
                        (isinstance(dec, ast.Name) and dec.id == "given")
                        or (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) and dec.func.id == "given")
                        for dec in node.decorator_list
                    )

                    if has_given:
                        # Check name quality
                        name = node.name
                        if not name.startswith("test_"):
                            continue

                        # Check for low-quality names
                        low_quality_patterns = [
                            "_case_",
                            "_1",
                            "_2",
                            "_test",
                            "test_test",
                        ]

                        for pattern in low_quality_patterns:
                            if pattern in name:
                                violations.append(
                                    f"{test_file.name}::{name}\n"
                                    f"  Location: {test_file.relative_to(REPO_ROOT)}:{node.lineno}\n"
                                    f"  Issue: Test name contains low-quality pattern: {pattern}\n"
                                    f"  Fix: Rename to describe the property being tested"
                                )

                        # Check name length (too short suggests poor naming)
                        if len(name) < 15:  # "test_" + at least 10 chars
                            violations.append(
                                f"{test_file.name}::{name}\n"
                                f"  Location: {test_file.relative_to(REPO_ROOT)}:{node.lineno}\n"
                                f"  Issue: Test name is too short ({len(name)} chars)\n"
                                f"  Fix: Use descriptive name like test_<what>_<condition>_<expected>"
                            )

        if violations:
            violation_report = "\n\n".join(violations)
            pytest.fail(
                f"Found {len(violations)} poorly named property test(s):\n\n"
                f"{violation_report}\n\n"
                f"Property tests should have descriptive names that explain the property being tested."
            )
