"""
Meta-tests to validate OpenAI Codex findings remediation.

These tests validate that identified issues have been properly fixed:
1. E2E tests use real clients instead of mocks
2. Documentation accurately reflects implementation
3. No bare @pytest.mark.skip markers (should use xfail with strict=True)
4. TODO tests have proper xfail markers

These tests follow TDD: they FAIL initially (RED), pass after fixes (GREEN).
"""

import ast
import re
from pathlib import Path
from typing import List, Tuple

import pytest


class TestCodexFindingsRemediation:
    """
    Meta-tests validating OpenAI Codex findings have been addressed.

    GIVEN: OpenAI Codex identified 4 valid issues in test suite
    WHEN: Fixes are implemented following TDD principles
    THEN: These meta-tests validate the fixes are complete
    """

    @pytest.fixture
    def project_root(self) -> Path:
        """Get project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def e2e_test_file(self, project_root: Path) -> Path:
        """Get E2E test file path."""
        return project_root / "tests" / "e2e" / "test_full_user_journey.py"

    @pytest.fixture
    def helpers_file(self, project_root: Path) -> Path:
        """Get E2E helpers file path."""
        return project_root / "tests" / "e2e" / "helpers.py"

    @pytest.fixture
    def cost_tracker_test_file(self, project_root: Path) -> Path:
        """Get cost tracker test file path."""
        return project_root / "tests" / "monitoring" / "test_cost_tracker.py"

    @pytest.fixture
    def gdpr_test_file(self, project_root: Path) -> Path:
        """Get GDPR test file path."""
        return project_root / "tests" / "test_gdpr.py"

    def _parse_python_file(self, file_path: Path) -> ast.Module:
        """Parse Python file into AST."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return ast.parse(content, filename=str(file_path))

    def _find_imports(self, tree: ast.Module) -> List[Tuple[str, List[str]]]:
        """
        Find all imports in AST.

        Returns:
            List of (module, names) tuples
            e.g., [('tests.e2e.helpers', ['mock_keycloak_auth'])]
        """
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [alias.name for alias in node.names]
                imports.append((module, names))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, [alias.name]))
        return imports

    def _find_function_calls(self, tree: ast.Module) -> List[str]:
        """Find all function call names in AST."""
        calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.append(node.func.attr)
        return calls

    def _find_decorators(self, tree: ast.Module) -> List[Tuple[str, ast.FunctionDef]]:
        """
        Find all test function decorators.

        Returns:
            List of (decorator_name, function_def) tuples
        """
        decorators = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test_"):
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Attribute):
                            # @pytest.mark.skip
                            if isinstance(decorator.value, ast.Attribute):
                                # @pytest.mark.xfail
                                full_name = f"{decorator.value.value.id}.{decorator.value.attr}.{decorator.attr}"
                                decorators.append((full_name, node))
                        elif isinstance(decorator, ast.Call):
                            # @pytest.mark.skip(reason="...")
                            if isinstance(decorator.func, ast.Attribute):
                                if isinstance(decorator.func.value, ast.Attribute):
                                    full_name = (
                                        f"{decorator.func.value.value.id}.{decorator.func.value.attr}.{decorator.func.attr}"
                                    )
                                    decorators.append((full_name, node))
        return decorators

    def _function_is_todo_placeholder(self, func_node: ast.FunctionDef) -> bool:
        """
        Check if function is a TODO placeholder.

        A function is a TODO placeholder ONLY if:
        - Body contains only 'pass' statement (or empty after docstring)
        - Explicitly has TODO comment in docstring

        This is strict to avoid false positives on implemented tests.
        """
        # Check for single 'pass' statement or empty body
        body = func_node.body

        # Skip docstring if present
        start_idx = 0
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            start_idx = 1

        # Check remaining body
        actual_body = body[start_idx:]

        # Must have only pass or be empty
        if not (len(actual_body) == 0 or (len(actual_body) == 1 and isinstance(actual_body[0], ast.Pass))):
            return False  # Has implementation, not a placeholder

        # Must have TODO in docstring to be considered a placeholder
        docstring = ast.get_docstring(func_node)
        if docstring and "TODO" in docstring.upper():
            return True

        return False

    def test_e2e_uses_real_clients_not_mocks(self, e2e_test_file: Path):
        """
        GIVEN: E2E test file (test_full_user_journey.py)
        WHEN: Checking imports and function calls
        THEN: Should import from real_clients, not helpers mocks
        AND: Should call real_keycloak_auth and real_mcp_client
        AND: Should NOT call mock_keycloak_auth or mock_mcp_client

        Codex Finding #3: E2E tests still use mock_keycloak_auth/mock_mcp_client
        """
        tree = self._parse_python_file(e2e_test_file)
        imports = self._find_imports(tree)
        calls = self._find_function_calls(tree)

        # Check imports
        mock_imports = [
            (module, names)
            for module, names in imports
            if module == "tests.e2e.helpers" and any(name in ["mock_keycloak_auth", "mock_mcp_client"] for name in names)
        ]

        real_client_imports = [(module, names) for module, names in imports if module == "tests.e2e.real_clients"]

        # Assertions
        assert not mock_imports, (
            f"E2E test file should NOT import mocks from helpers. "
            f"Found: {mock_imports}. "
            f"Use 'from tests.e2e.real_clients import real_keycloak_auth, real_mcp_client' instead."
        )

        assert real_client_imports, (
            "E2E test file should import from tests.e2e.real_clients. "
            "Expected 'from tests.e2e.real_clients import real_keycloak_auth, real_mcp_client'"
        )

        # Check function calls
        assert (
            "mock_keycloak_auth" not in calls
        ), "E2E tests should NOT call mock_keycloak_auth. Use real_keycloak_auth instead."

        assert "mock_mcp_client" not in calls, "E2E tests should NOT call mock_mcp_client. Use real_mcp_client instead."

        assert "real_keycloak_auth" in calls or "real_mcp_client" in calls, (
            "E2E tests should call real client functions. "
            "Expected real_keycloak_auth and/or real_mcp_client in function calls."
        )

    def test_helpers_documentation_reflects_reality(self, helpers_file: Path):
        """
        GIVEN: E2E helpers file with documentation
        WHEN: Checking documentation claims vs implementation
        THEN: Documentation should NOT claim migration is complete
        OR: If claiming complete, real clients must be fully implemented

        Codex Finding #4: Documentation claims "Migrated" but code uses mocks
        """
        with open(helpers_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for completion claims
        completion_patterns = [
            r"STATUS:\s*✅\s*Migrated",
            r"Phase.*complete",
            r"Migration.*complete",
        ]

        has_completion_claim = any(re.search(pattern, content, re.IGNORECASE) for pattern in completion_patterns)

        if has_completion_claim:
            # If claiming complete, verify real clients exist and are used
            assert "class RealKeycloakAuth" in content or "real_keycloak_auth" in content, (
                "helpers.py claims migration complete but doesn't implement RealKeycloakAuth. "
                "Either implement real clients or update documentation to reflect current status."
            )

            assert "class RealMCPClient" in content or "real_mcp_client" in content, (
                "helpers.py claims migration complete but doesn't implement RealMCPClient. "
                "Either implement real clients or update documentation to reflect current status."
            )
        else:
            # Documentation should accurately describe the file's purpose
            # Either "In Progress", "TODO", "Mock", or clearly explain real clients are elsewhere
            has_status_indicator = (
                "In Progress" in content
                or "TODO" in content.upper()
                or "Mock implementations" in content
                or "real_clients.py" in content  # Points to real implementation
            )

            assert has_status_indicator, (
                "helpers.py documentation should clearly indicate file purpose "
                "(Mock implementations, In Progress, or pointer to real_clients.py)"
            )

    def test_no_bare_skip_markers(self, cost_tracker_test_file: Path):
        """
        GIVEN: Test files with @pytest.mark.skip markers
        WHEN: Checking for proper test markers
        THEN: Should use @pytest.mark.xfail(strict=True) instead of skip
        AND: Should include descriptive reason parameter

        Codex Finding #6: test_cost_tracker.py has @pytest.mark.skip
        without xfail(strict=True)

        Note: Some skip markers are acceptable (e.g., skip if dependency missing).
        This test focuses on skip markers that should be xfail for incomplete features.
        """
        tree = self._parse_python_file(cost_tracker_test_file)
        decorators = self._find_decorators(tree)

        # Find skip decorators
        skip_decorators = [(dec_name, func) for dec_name, func in decorators if "mark.skip" in dec_name]

        # Find xfail decorators
        xfail_decorators = [(dec_name, func) for dec_name, func in decorators if "mark.xfail" in dec_name]

        # In cost_tracker.py, we expect xfail for incomplete API tests
        # Original finding: Lines 483-542 have 4 skip markers that should be xfail
        test_functions_with_skip = [func.name for _, func in skip_decorators]

        # These specific tests should NOT use skip (they should use xfail instead)
        # Look for cost-related tests (broader pattern since tests don't all have "api")
        problematic_skips = [name for name in test_functions_with_skip if "cost" in name.lower()]

        assert len(problematic_skips) == 0, (
            f"Found {len(problematic_skips)} cost-related tests with @pytest.mark.skip "
            f"that should use @pytest.mark.xfail(strict=True) instead: {problematic_skips}. "
            f"Use xfail for incomplete features so tests auto-detect when APIs are ready."
        )

        # Verify xfail decorators exist for cost-related tests
        xfail_test_names = [func.name for _, func in xfail_decorators]
        cost_xfails = [
            name for name in xfail_test_names if "cost" in name.lower() or "budget" in name.lower() or "export" in name.lower()
        ]

        assert len(cost_xfails) >= 4, (
            f"Expected at least 4 cost-related tests with @pytest.mark.xfail(strict=True). "
            f"Found {len(cost_xfails)}: {cost_xfails}. "
            f"Convert skip markers to xfail for incomplete cost tracking features."
        )

    def test_todo_tests_have_xfail_markers(self, gdpr_test_file: Path):
        """
        GIVEN: Test files with TODO placeholder tests
        WHEN: Checking test functions with only 'pass' and TODO comments
        THEN: Should have @pytest.mark.xfail(strict=True) decorator

        Codex Finding #9: test_gdpr.py:728-731 has TODO test without xfail marker
        """
        tree = self._parse_python_file(gdpr_test_file)
        decorators = self._find_decorators(tree)

        # Get all test functions
        test_functions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
        ]

        # Find TODO placeholder tests
        todo_placeholders = [func for func in test_functions if self._function_is_todo_placeholder(func)]

        # Check each TODO placeholder has xfail
        for func in todo_placeholders:
            func_decorators = [dec_name for dec_name, dec_func in decorators if dec_func.name == func.name]

            has_xfail = any("mark.xfail" in dec for dec in func_decorators)

            assert has_xfail, (
                f"TODO placeholder test '{func.name}' at line {func.lineno} "
                f"should have @pytest.mark.xfail(strict=True) decorator. "
                f"Found decorators: {func_decorators}. "
                f"Add xfail marker to prevent false test coverage confidence."
            )

        # Note: Original Codex finding mentioned test_concurrent_deletion_attempts
        # but that test is actually fully implemented (not a placeholder).
        # The general TODO placeholder check above is sufficient.

    def test_hypothesis_configuration_is_guarded(self, project_root: Path):
        """
        GIVEN: tests/conftest.py with Hypothesis configuration
        WHEN: Hypothesis is not available (import fails)
        THEN: Hypothesis profile configuration should be wrapped in availability check
        AND: Should not cause AttributeError when settings is None

        Codex Finding #3 (New): Hypothesis configuration runs unconditionally
        even when import fails, causing AttributeError on machines without Hypothesis.
        """
        conftest_file = project_root / "tests" / "conftest.py"

        # Read file content for analysis
        with open(conftest_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify Hypothesis import has try/except guard with HYPOTHESIS_AVAILABLE flag
        assert "try:" in content, "Expected try/except block for Hypothesis import"
        assert "from hypothesis import settings" in content, "Expected Hypothesis import"
        assert "HYPOTHESIS_AVAILABLE = True" in content, "Expected HYPOTHESIS_AVAILABLE flag"
        assert "except ImportError:" in content, "Expected ImportError handler"
        assert "HYPOTHESIS_AVAILABLE = False" in content, "Expected HYPOTHESIS_AVAILABLE = False in except"
        assert "settings = None" in content, "Expected settings = None when import fails"

        # Verify settings.register_profile is guarded by if HYPOTHESIS_AVAILABLE
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "settings.register_profile" in line or "settings.load_profile" in line:
                # Search backwards to find if block guard
                found_guard = self._find_availability_guard(lines, i)
                assert found_guard, (
                    f"Hypothesis configuration at line {i + 1} is not guarded. "
                    f"settings.register_profile() and settings.load_profile() calls "
                    f"MUST be wrapped in 'if HYPOTHESIS_AVAILABLE:' block to prevent "
                    f"AttributeError when Hypothesis is not installed."
                )

    def _find_availability_guard(self, lines: List[str], current_line: int) -> bool:
        """Helper: Check if line is inside 'if HYPOTHESIS_AVAILABLE:' block."""
        for j in range(current_line - 1, max(0, current_line - 50), -1):
            if re.match(r"^if\s+HYPOTHESIS_AVAILABLE\s*:", lines[j]):
                return True
            # Stop at other top-level statements
            if lines[j] and not lines[j].startswith((" ", "\t", "#")) and lines[j].strip():
                break
        return False


class TestCodexValidationMetaTest:
    """Meta-test the meta-tests themselves."""

    def test_codex_validation_file_exists(self):
        """
        GIVEN: Meta-test file for Codex validations
        WHEN: Checking file existence
        THEN: This file should exist at tests/meta/test_codex_validations.py
        """
        test_file = Path(__file__)
        assert test_file.name == "test_codex_validations.py"
        assert test_file.parent.name == "meta"
        assert test_file.exists()

    def test_meta_tests_are_well_documented(self):
        """
        GIVEN: Meta-test file
        WHEN: Checking documentation
        THEN: Each test should have clear docstring with GIVEN/WHEN/THEN
        """
        with open(__file__, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        test_methods = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
        ]

        for test_func in test_methods:
            docstring = ast.get_docstring(test_func)
            assert docstring, f"Test {test_func.name} should have docstring"
            assert (
                "GIVEN" in docstring or "WHEN" in docstring or "THEN" in docstring
            ), f"Test {test_func.name} should use GIVEN/WHEN/THEN format"
