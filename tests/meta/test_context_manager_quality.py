"""
Meta-tests for Context Manager Test Quality

These tests validate that context manager tests properly assert __exit__ is called.

Purpose: Prevent regression of Codex Finding #3 (Redis checkpointer tests lack __exit__ assertions)
"""

import ast
import gc
from pathlib import Path

import pytest

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = [pytest.mark.unit, pytest.mark.meta]

REPO_ROOT = Path(__file__).parent.parent.parent


@pytest.mark.meta
@pytest.mark.xdist_group(name="testcontextmanagertestquality")
class TestContextManagerTestQuality:
    """
    Meta-tests that validate context manager tests have proper cleanup assertions.

    RED: These tests will fail if context manager tests lack __exit__ assertions.
    GREEN: Context manager tests properly validate cleanup.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_context_manager_tests_assert_exit(self):
        """
        Validate tests of context managers assert __exit__ is called.

        This prevents regressions of Codex Finding #3:
        "The Redis checkpointer lifecycle tests promise to guard cleanup but never
        assert that the context manager is closed, so regressions will slip through silently."

        RED: Fails if context manager tests lack __exit__ assertions.
        GREEN: All context manager tests properly validate cleanup.
        """
        test_files = list(REPO_ROOT.glob("tests/**/test_*.py"))

        violations = []

        for test_file in test_files:
            # Skip this meta-test file
            if "meta" in str(test_file):
                continue

            with open(test_file, "r") as f:
                source = f.read()

            # Check if file tests context managers
            if "__enter__" not in source and "__exit__" not in source:
                continue  # No context manager testing in this file

            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if test name suggests context manager testing
                    if not node.name.startswith("test_"):
                        continue

                    # Look for context manager patterns
                    func_source = ast.get_source_segment(source, node)
                    if not func_source:
                        continue

                    # Check if test sets up __enter__ mock (not just code containing __enter__)
                    has_enter_mock = (
                        "__enter__ =" in func_source  # Assignment to __enter__
                        or ".__enter__" in func_source  # Mock/access to __enter__
                    ) and "MagicMock" in func_source  # Actual mocking happening

                    # Skip if __enter__ is just in a code string being validated
                    if '"""' in func_source or "'''" in func_source:
                        # Check if __enter__ only appears in docstrings or code strings
                        code_strings = []
                        in_string = False
                        for line in func_source.split("\n"):
                            if '"""' in line or "'''" in line:
                                in_string = not in_string
                            if in_string:
                                code_strings.append(line)

                        # If __enter__ only in code strings, skip
                        if all("__enter__" not in line for line in func_source.split("\n") if line not in code_strings):
                            has_enter_mock = False

                    if has_enter_mock:
                        # Verify it also asserts __exit__
                        has_exit_assert = self._has_exit_assertion(func_source)

                        if not has_exit_assert:
                            violations.append(
                                f"{test_file.name}::{node.name}\n"
                                f"  Location: {test_file.relative_to(REPO_ROOT)}:{node.lineno}\n"
                                f"  Issue: Test mocks __enter__ but doesn't assert __exit__ is called\n"
                                f"  Fix: Add assertion: mock_ctx.__exit__.assert_called_once_with(None, None, None)"
                            )

        if violations:
            violation_report = "\n\n".join(violations)
            pytest.fail(
                f"Found {len(violations)} context manager test(s) without __exit__ assertions:\n\n"
                f"{violation_report}\n\n"
                f"Context manager tests MUST assert that __exit__ is properly called. "
                f"See Codex Finding #3 for examples."
            )

    def test_context_manager_cleanup_functions_exist(self):
        """
        Validate that context manager tests actually call cleanup functions.

        This ensures tests don't just create context managers but also test their cleanup.

        RED: Fails if cleanup functions aren't called.
        GREEN: All tests properly invoke cleanup.
        """
        test_files = list(REPO_ROOT.glob("tests/**/test_*.py"))

        violations = []

        for test_file in test_files:
            # Skip meta-tests
            if "meta" in str(test_file):
                continue

            with open(test_file, "r") as f:
                source = f.read()

            # Check if file has cleanup-related functions
            if "cleanup" not in source.lower() and "__exit__" not in source:
                continue

            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not node.name.startswith("test_"):
                        continue

                    # Check for cleanup function patterns
                    func_source = ast.get_source_segment(source, node)
                    if not func_source:
                        continue

                    # If test mentions cleanup in name or docstring
                    mentions_cleanup = "cleanup" in node.name.lower()
                    if node.returns and isinstance(node.returns, ast.Constant):
                        mentions_cleanup = mentions_cleanup or "cleanup" in str(node.returns.value).lower()

                    if mentions_cleanup:
                        # Verify cleanup function is actually called
                        has_cleanup_call = "cleanup(" in func_source or "cleanup_" in func_source or "__exit__" in func_source

                        if not has_cleanup_call:
                            violations.append(
                                f"{test_file.name}::{node.name}\n"
                                f"  Location: {test_file.relative_to(REPO_ROOT)}:{node.lineno}\n"
                                f"  Issue: Test mentions 'cleanup' but doesn't call cleanup function\n"
                                f"  Fix: Actually invoke the cleanup function being tested"
                            )

        if violations:
            violation_report = "\n\n".join(violations)
            pytest.fail(
                f"Found {len(violations)} test(s) that mention cleanup but don't call it:\n\n"
                f"{violation_report}\n\n"
                f"Tests should actually invoke the cleanup functions they claim to test."
            )

    def _has_exit_assertion(self, source: str) -> bool:
        """
        Check if source code asserts __exit__ is called.

        Returns True if source contains patterns like:
        - __exit__.called
        - __exit__.assert_called
        - __exit__.assert_called_once
        - assert mock_ctx.__exit__.called
        """
        exit_assertion_patterns = [
            "__exit__.called",
            "__exit__.assert_called",
            "__exit__.assert_called_once",
            "assert_called_once_with(None, None, None)",  # Common __exit__ args
        ]

        return any(pattern in source for pattern in exit_assertion_patterns)


@pytest.mark.meta
@pytest.mark.xdist_group(name="testcontextmanagernaming")
class TestContextManagerNaming:
    """Validate context manager test naming conventions"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_context_manager_tests_have_descriptive_names(self):
        """
        Context manager tests should describe what cleanup behavior is being tested.

        Good: test_redis_checkpointer_context_manager_cleanup
        Bad: test_context_manager, test_cleanup
        """
        test_files = list(REPO_ROOT.glob("tests/**/test_*.py"))

        violations = []

        for test_file in test_files:
            # Skip meta-tests
            if "meta" in str(test_file):
                continue

            with open(test_file, "r") as f:
                source = f.read()

            if "__enter__" not in source and "__exit__" not in source:
                continue

            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not node.name.startswith("test_"):
                        continue

                    func_source = ast.get_source_segment(source, node)
                    if not func_source or "__enter__" not in func_source:
                        continue

                    # Check name quality
                    name = node.name
                    low_quality_patterns = ["test_context", "test_manager", "test_cleanup"]

                    if name in low_quality_patterns:
                        violations.append(
                            f"{test_file.name}::{name}\n"
                            f"  Location: {test_file.relative_to(REPO_ROOT)}:{node.lineno}\n"
                            f"  Issue: Test name is too generic\n"
                            f"  Fix: Use descriptive name like test_<resource>_context_manager_<behavior>"
                        )

        if violations:
            violation_report = "\n\n".join(violations)
            pytest.fail(
                f"Found {len(violations)} poorly named context manager test(s):\n\n"
                f"{violation_report}\n\n"
                f"Context manager tests should have descriptive names."
            )
