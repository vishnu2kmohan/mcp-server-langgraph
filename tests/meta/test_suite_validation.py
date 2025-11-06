"""
Meta-tests to validate test suite structure and prevent regressions

TDD Regression Tests: These meta-tests validate the test suite itself
to prevent recurrence of structural issues identified by OpenAI Codex.

Tests cover:
1. No conflicting pytest markers (unit + integration on same class)
2. Optional imports use proper guards (pytest.importorskip or try/except)
3. Infrastructure fixtures use pytest.skip, not pytest.fail

These tests ensure the test suite remains maintainable and follows best practices.

References:
- OpenAI Codex findings: Conflicting markers, unguarded imports, pytest.fail usage
- pytest best practices
"""

import ast
import os
from pathlib import Path
from typing import List, Set, Tuple

import pytest


class TestMarkerConsistency:
    """Meta-tests to validate pytest marker consistency across test suite"""

    @pytest.mark.unit
    def test_no_conflicting_unit_and_integration_markers(self):
        """
        TDD REGRESSION TEST: Ensure no test class has both unit and integration markers

        GIVEN: All test files in the test suite
        WHEN: Scanning for pytest markers on test classes
        THEN: No test class should have both 'unit' and 'integration' markers
        """
        conflicts = self._find_conflicting_markers(
            marker_pairs=[
                ("unit", "integration"),
                ("unit", "e2e"),
            ]
        )

        if conflicts:
            error_msg = "Found test classes with conflicting pytest markers:\n"
            for file_path, class_name, markers in conflicts:
                error_msg += f"\n  {file_path}::{class_name}\n"
                error_msg += f"    Markers: {', '.join(sorted(markers))}\n"
            error_msg += "\nTests should be categorized as either 'unit', 'integration', or 'e2e', not multiple."
            pytest.fail(error_msg)

    @pytest.mark.unit
    def test_integration_tests_properly_marked(self):
        """
        TDD: Ensure integration tests are consistently marked

        GIVEN: All test files
        WHEN: Scanning for integration test patterns
        THEN: Tests with real infrastructure should have @pytest.mark.integration
        """
        # This is a placeholder for future enhancement
        # Could scan for patterns like "docker", "keycloak", "openfga" in test names
        # and verify they have integration markers
        pass

    def _find_conflicting_markers(self, marker_pairs: List[Tuple[str, str]]) -> List[Tuple[str, str, Set[str]]]:
        """
        Find test classes with conflicting pytest markers

        Args:
            marker_pairs: List of (marker1, marker2) tuples to check for conflicts

        Returns:
            List of (file_path, class_name, markers) tuples for conflicting classes
        """
        conflicts = []
        tests_dir = Path(__file__).parent.parent  # Go up from meta/ to tests/

        for test_file in tests_dir.rglob("test_*.py"):
            if test_file.parent.name == "meta":
                # Skip meta-tests
                continue

            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=str(test_file))

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                        markers = self._extract_markers_from_class(node)

                        # Check each marker pair for conflicts
                        for marker1, marker2 in marker_pairs:
                            if marker1 in markers and marker2 in markers:
                                rel_path = test_file.relative_to(tests_dir.parent)
                                conflicts.append((str(rel_path), node.name, markers))
                                break  # Only report each class once

            except (SyntaxError, UnicodeDecodeError):
                # Skip files that can't be parsed
                continue

        return conflicts

    def _extract_markers_from_class(self, class_node: ast.ClassDef) -> Set[str]:
        """
        Extract pytest marker names from a test class

        Args:
            class_node: AST node for the class

        Returns:
            Set of marker names (e.g., {'unit', 'integration', 'slow'})
        """
        markers = set()

        for decorator in class_node.decorator_list:
            marker_name = self._extract_marker_name(decorator)
            if marker_name:
                markers.add(marker_name)

        return markers

    def _extract_marker_name(self, decorator: ast.expr) -> str:
        """
        Extract marker name from a decorator node

        Handles:
        - @pytest.mark.unit
        - @pytest.mark.integration
        - @pytest.mark.slow

        Args:
            decorator: AST node for the decorator

        Returns:
            Marker name or empty string if not a pytest marker
        """
        if isinstance(decorator, ast.Attribute):
            # @pytest.mark.unit
            if (
                isinstance(decorator.value, ast.Attribute)
                and isinstance(decorator.value.value, ast.Name)
                and decorator.value.value.id == "pytest"
                and decorator.value.attr == "mark"
            ):
                return decorator.attr
        return ""


class TestImportGuards:
    """Meta-tests to validate import guards for optional dependencies"""

    @pytest.mark.unit
    def test_optional_imports_use_guards(self):
        """
        TDD REGRESSION TEST: Ensure optional imports use pytest.importorskip or try/except

        GIVEN: All test files
        WHEN: Scanning for imports of optional packages
        THEN: They should use pytest.importorskip or try/except ImportError
        """
        optional_packages = {
            "python_on_whales",
            "qdrant_client",
            # Note: httpx is a core dependency, not optional
            # Note: pytest_asyncio, freezegun are in dev dependencies
        }

        issues = []
        tests_dir = Path(__file__).parent.parent

        for test_file in tests_dir.rglob("*.py"):
            if test_file.parent.name == "meta":
                # Skip meta-tests
                continue

            # Read file content
            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")

                # Check for unguarded module-level imports
                for package in optional_packages:
                    # Look for "import package" or "from package import X"
                    import_pattern = f"import {package}"
                    from_pattern = f"from {package} import"

                    for line_num, line in enumerate(lines, 1):
                        stripped = line.strip()

                        # Skip comments and docstrings
                        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                            continue

                        if import_pattern in stripped or from_pattern in stripped:
                            # Check if it's guarded
                            # Look backwards for pytest.importorskip or try:
                            is_guarded = False

                            # Check previous lines for guards
                            for prev_line in lines[max(0, line_num - 10) : line_num]:
                                if "pytest.importorskip" in prev_line:
                                    is_guarded = True
                                    break
                                if "try:" in prev_line or "except ImportError" in prev_line:
                                    is_guarded = True
                                    break

                            if not is_guarded:
                                rel_path = test_file.relative_to(tests_dir.parent)
                                issues.append(f"{rel_path}:{line_num} - Unguarded import of optional package '{package}'")

            except (UnicodeDecodeError, FileNotFoundError):
                continue

        if issues:
            error_msg = "Found unguarded imports of optional packages:\n"
            error_msg += "\n".join(f"  {issue}" for issue in issues)
            error_msg += "\n\nUse pytest.importorskip() or try/except ImportError for optional dependencies."
            pytest.fail(error_msg)


class TestInfrastructureFixtures:
    """Meta-tests to validate infrastructure fixture behavior"""

    @pytest.mark.unit
    def test_infrastructure_fixtures_use_skip_not_fail(self):
        """
        TDD REGRESSION TEST: Ensure infrastructure fixtures use pytest.skip, not pytest.fail

        GIVEN: conftest.py with infrastructure fixtures
        WHEN: Health checks fail
        THEN: Should use pytest.skip(), not pytest.fail()
        """
        conftest_path = Path(__file__).parent.parent / "conftest.py"

        with open(conftest_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check that pytest.fail is NOT used in infrastructure health checks
        # but pytest.skip IS used
        issues = []

        if "pytest.fail(" in content:
            # Look for lines with pytest.fail in health check context
            lines = content.split("\n")
            for line_num, line in enumerate(lines, 1):
                if "pytest.fail(" in line and ("ready" in line.lower() or "health" in line.lower()):
                    issues.append(f"Line {line_num}: Uses pytest.fail() in health check: {line.strip()}")

        if issues:
            error_msg = "Found pytest.fail() in infrastructure health checks:\n"
            error_msg += "\n".join(f"  {issue}" for issue in issues)
            error_msg += "\n\nUse pytest.skip() for infrastructure unavailability, not pytest.fail()."
            pytest.fail(error_msg)

        # Verify pytest.skip is used
        if "pytest.skip(" not in content:
            pytest.fail("conftest.py should use pytest.skip() for infrastructure unavailability")
