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
import gc
import os
from pathlib import Path
from typing import List, Set, Tuple

import pytest


@pytest.mark.xdist_group(name="testmarkerconsistency")
class TestMarkerConsistency:
    """Meta-tests to validate pytest marker consistency across test suite"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

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
    def test_unimplemented_features_use_xfail_strict(self):
        """
        TDD REGRESSION TEST: Ensure unimplemented features use xfail(strict=True) not skip

        GIVEN: All test files in the test suite
        WHEN: Scanning for tests with "not implemented" in skip/xfail reasons
        THEN: They should use @pytest.mark.xfail(strict=True), not @pytest.mark.skip

        Rationale:
        - skip: Test is silently skipped, no notification when implementation is ready
        - xfail(strict=True): Test FAILS CI when it starts passing, alerting team to remove marker
        """
        violations = self._find_skip_markers_for_unimplemented_features()

        if violations:
            error_msg = "Found tests using @pytest.mark.skip for unimplemented features:\n"
            for file_path, test_name, line_num, reason in violations:
                error_msg += f"\n  {file_path}:{line_num} - {test_name}\n"
                error_msg += f"    Reason: {reason}\n"
            error_msg += (
                "\n❌ Use @pytest.mark.xfail(strict=True, reason=...) instead of skip for unimplemented features.\n"
                "✅ This ensures CI fails when the feature is implemented, alerting you to enable the test."
            )
            pytest.fail(error_msg)

    @pytest.mark.unit
    def test_integration_tests_properly_marked(self):
        """
        TDD REGRESSION TEST: Ensure integration tests are consistently marked

        GIVEN: All test files
        WHEN: Scanning for integration test patterns (infrastructure usage)
        THEN: Tests with real infrastructure should have @pytest.mark.integration

        Infrastructure patterns include:
        - test_infrastructure fixture usage
        - Real database/Redis/OpenFGA client fixtures
        - Docker/Keycloak/MCP references in test names or function parameters
        """
        violations = self._find_unmarked_integration_tests()

        if violations:
            error_msg = "Found tests using infrastructure without @pytest.mark.integration:\n"
            for file_path, test_name, line_num, pattern in violations:
                error_msg += f"\n  {file_path}:{line_num} - {test_name}\n"
                error_msg += f"    Pattern detected: {pattern}\n"
            error_msg += (
                "\n❌ Add @pytest.mark.integration to tests that use real infrastructure.\n"
                "✅ This ensures proper test categorization and allows selective execution."
            )
            pytest.fail(error_msg)

    @pytest.mark.unit
    def test_integration_tests_use_conditional_skips_not_hard_skips(self):
        """
        TDD REGRESSION TEST: Integration tests should use conditional skips, not hard skips

        GIVEN: All test files marked with @pytest.mark.integration
        WHEN: Scanning for @pytest.mark.skip decorators
        THEN: Integration tests should use skipif with availability checks
        OR: Use fixtures that auto-skip when infrastructure unavailable

        Rationale:
        - Hard skip: Test never runs, even when infrastructure is available
        - Conditional skip: Test runs when infrastructure is available (CI, local dev)
        - This enables tests to run in environments where infrastructure exists

        Codex Finding: "Several integration tests are permanently skipped"
        """
        violations = self._find_hard_skips_in_integration_tests()

        if violations:
            error_msg = "Found integration tests with hard @pytest.mark.skip:\n"
            for file_path, test_name, line_num, reason in violations:
                error_msg += f"\n  {file_path}:{line_num} - {test_name}\n"
                error_msg += f"    Reason: {reason}\n"
            error_msg += (
                "\n❌ Integration tests should NOT use hard @pytest.mark.skip.\n"
                "✅ Instead, use one of these approaches:\n"
                "   1. Use @pytest.mark.skipif with environment variable check:\n"
                "      @pytest.mark.skipif(not os.getenv('RUN_INTEGRATION_TESTS'), reason='...')\n"
                "   2. Use infrastructure fixtures that auto-skip when unavailable:\n"
                "      def test_my_feature(openfga_client_real):  # Auto-skips if unavailable\n"
                "   3. Check fixture availability in test setup:\n"
                "      if not integration_test_env: pytest.skip('...')\n"
            )
            pytest.fail(error_msg)

    def _find_unmarked_integration_tests(self) -> List[Tuple[str, str, int, str]]:
        """
        Find tests that use infrastructure but lack @pytest.mark.integration

        Returns:
            List of (file_path, test_name, line_number, pattern) tuples
        """
        violations = []
        tests_dir = Path(__file__).parent.parent

        # ONLY check for REAL infrastructure fixture usage (not mocks)
        # These fixtures indicate actual infrastructure is being used
        infrastructure_fixtures = {
            "test_infrastructure",  # Docker-compose based infrastructure
            "test_fastapi_app",  # Full FastAPI app with real dependencies
            "postgres_connection_real",  # Real Postgres connection
            "redis_client_real",  # Real Redis client
            "openfga_client_real",  # Real OpenFGA client (not mocked)
            "real_keycloak_auth",  # Real Keycloak auth (not mocked)
            "real_mcp_client",  # Real MCP client (not mocked)
        }

        # Don't use keyword matching - too many false positives from unit tests
        # that mention infrastructure in names but use mocks
        infrastructure_keywords = set()

        for test_file in tests_dir.rglob("test_*.py"):
            # Skip meta-tests and e2e tests (e2e has own marker)
            if test_file.parent.name in ["meta", "e2e"]:
                continue

            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    tree = ast.parse(content, filename=str(test_file))

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                        # Check if test has integration marker
                        has_integration_marker = self._has_marker(node, "integration")

                        if not has_integration_marker:
                            # Check for infrastructure usage
                            detected_pattern = self._detect_infrastructure_usage(
                                node, infrastructure_fixtures, infrastructure_keywords
                            )

                            if detected_pattern:
                                rel_path = test_file.relative_to(tests_dir.parent)
                                violations.append((str(rel_path), node.name, node.lineno, detected_pattern))

            except (SyntaxError, UnicodeDecodeError):
                continue

        return violations

    def _has_marker(self, func_node: ast.FunctionDef, marker_name: str) -> bool:
        """Check if a test function has a specific marker"""
        for decorator in func_node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                if (
                    isinstance(decorator.value, ast.Attribute)
                    and isinstance(decorator.value.value, ast.Name)
                    and decorator.value.value.id == "pytest"
                    and decorator.value.attr == "mark"
                    and decorator.attr == marker_name
                ):
                    return True
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if (
                        isinstance(decorator.func.value, ast.Attribute)
                        and isinstance(decorator.func.value.value, ast.Name)
                        and decorator.func.value.value.id == "pytest"
                        and decorator.func.value.attr == "mark"
                        and decorator.func.attr == marker_name
                    ):
                        return True
        return False

    def _detect_infrastructure_usage(
        self, func_node: ast.FunctionDef, infrastructure_fixtures: set, infrastructure_keywords: set
    ) -> str:
        """
        Detect if a test uses infrastructure patterns

        Returns:
            Description of detected pattern, or empty string if none found
        """
        # Check function parameters for infrastructure fixtures
        for arg in func_node.args.args:
            if arg.arg in infrastructure_fixtures:
                return f"Uses infrastructure fixture: {arg.arg}"

        # Check function name and docstring for infrastructure keywords
        func_name_lower = func_node.name.lower()
        for keyword in infrastructure_keywords:
            if keyword in func_name_lower:
                return f"Function name contains: {keyword}"

        # Check docstring
        docstring = ast.get_docstring(func_node)
        if docstring:
            docstring_lower = docstring.lower()
            for keyword in infrastructure_keywords:
                if keyword in docstring_lower:
                    return f"Docstring mentions: {keyword}"

        return ""

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

    def _find_hard_skips_in_integration_tests(self) -> List[Tuple[str, str, int, str]]:
        """
        Find integration tests using hard @pytest.mark.skip instead of conditional skips

        Returns:
            List of (file_path, test_name, line_number, reason) tuples
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

                # Build a map of nodes to their parents (single pass)
                parent_map = {}
                for parent in ast.walk(tree):
                    for child in ast.iter_child_nodes(parent):
                        parent_map[child] = parent

                # Check test functions and classes for integration marker
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                        # Check if test or its parent class has integration marker
                        has_integration_marker = self._has_marker(node, "integration")

                        # Also check parent class if this is a method
                        if not has_integration_marker:
                            # Look up parent from pre-built map (O(1) instead of O(n))
                            parent = parent_map.get(node)
                            if parent and isinstance(parent, ast.ClassDef):
                                has_integration_marker = self._has_marker(parent, "integration")

                        if has_integration_marker:
                            # Check for hard skip markers
                            skip_reason = None
                            for decorator in node.decorator_list:
                                skip_reason = self._extract_skip_reason(decorator)
                                if skip_reason:
                                    break

                            if skip_reason:
                                rel_path = test_file.relative_to(tests_dir.parent)
                                violations.append((str(rel_path), node.name, node.lineno, skip_reason))

            except (SyntaxError, UnicodeDecodeError):
                continue

        return violations

    def _find_skip_markers_for_unimplemented_features(self) -> List[Tuple[str, str, int, str]]:
        """
        Find tests using @pytest.mark.skip for unimplemented features

        Returns:
            List of (file_path, test_name, line_number, reason) tuples
        """
        violations = []
        tests_dir = Path(__file__).parent.parent

        # Keywords that indicate unimplemented features
        unimplemented_keywords = [
            "not implemented",
            "not yet implemented",
            "todo",
            "coming soon",
            "future",
            "pending implementation",
        ]

        for test_file in tests_dir.rglob("test_*.py"):
            if test_file.parent.name == "meta":
                continue

            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    tree = ast.parse(content, filename=str(test_file))

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                        # Check decorators for skip markers
                        for decorator in node.decorator_list:
                            skip_reason = self._extract_skip_reason(decorator)

                            if skip_reason:
                                # Check if reason indicates unimplemented feature
                                reason_lower = skip_reason.lower()
                                if any(keyword in reason_lower for keyword in unimplemented_keywords):
                                    rel_path = test_file.relative_to(tests_dir.parent)
                                    violations.append((str(rel_path), node.name, node.lineno, skip_reason))

            except (SyntaxError, UnicodeDecodeError):
                continue

        return violations

    def _extract_skip_reason(self, decorator: ast.expr) -> str:
        """
        Extract reason from @pytest.mark.skip(reason=...) decorator

        Args:
            decorator: AST node for the decorator

        Returns:
            Skip reason string or empty string if not a skip marker
        """
        # Handle @pytest.mark.skip(reason="...")
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                if (
                    isinstance(decorator.func.value, ast.Attribute)
                    and isinstance(decorator.func.value.value, ast.Name)
                    and decorator.func.value.value.id == "pytest"
                    and decorator.func.value.attr == "mark"
                    and decorator.func.attr == "skip"
                ):
                    # Extract reason from keyword arguments
                    for keyword in decorator.keywords:
                        if keyword.arg == "reason":
                            if isinstance(keyword.value, ast.Constant):
                                return keyword.value.value
                            # Note: ast.Str removed - deprecated since Python 3.8, removed in Python 3.14
                            # All string constants are now ast.Constant nodes

        return ""


@pytest.mark.xdist_group(name="testimportguards")
class TestImportGuards:
    """Meta-tests to validate import guards for optional dependencies"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

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


@pytest.mark.xdist_group(name="testinfrastructurefixtures")
class TestInfrastructureFixtures:
    """Meta-tests to validate infrastructure fixture behavior"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

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


@pytest.mark.xdist_group(name="testclitoolguards")
class TestCLIToolGuards:
    """Meta-tests to validate CLI tool availability guards (OpenAI Codex Finding #1)"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_cli_tool_tests_have_skipif_guards(self):
        """
        TDD REGRESSION TEST: Ensure tests using CLI tools have proper skipif guards.

        CODEX FINDING #1: tests/test_ci_cd_validation.py:61 invokes kustomize
        unconditionally, causing hard failures when CLI is absent.

        GIVEN: All test files that invoke external CLI tools
        WHEN: Scanning for subprocess.run() calls to CLI tools
        THEN: Tests should use session-scoped availability fixtures and skipif guards

        CLI tools to guard:
        - kustomize
        - kubectl
        - helm
        - docker
        """
        violations = self._find_unguarded_cli_tool_usage()

        if violations:
            error_msg = "Found tests invoking CLI tools without proper guards:\n"
            for file_path, test_name, line_num, cli_tool in violations:
                error_msg += f"\n  {file_path}:{line_num} - {test_name}\n"
                error_msg += f"    Invokes: {cli_tool}\n"
            error_msg += (
                "\n❌ CLI tools should be guarded with skipif decorators.\n"
                "\n✅ Recommended pattern:\n"
                "   @pytest.fixture(scope='session')\n"
                "   def kustomize_available():\n"
                "       return shutil.which('kustomize') is not None\n"
                "\n   @pytest.mark.skipif(not kustomize_available, reason='kustomize not installed')\n"
                "   def test_kustomize_build(...):\n"
                "       ...\n"
            )
            pytest.fail(error_msg)

    def _find_unguarded_cli_tool_usage(self) -> List[Tuple[str, str, int, str]]:
        """
        Find tests that invoke CLI tools without proper guards.

        Returns:
            List of (file_path, test_name, line_number, cli_tool) tuples
        """
        violations = []
        tests_dir = Path(__file__).parent.parent

        # CLI tools that require guards
        cli_tools = {
            "kustomize": "requires_kustomize",
            "kubectl": "requires_kubectl",
            "helm": "requires_helm",
        }

        for test_file in tests_dir.rglob("test_*.py"):
            if test_file.parent.name == "meta":
                continue

            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    tree = ast.parse(content, filename=str(test_file))

                # Find all test functions and their parent classes
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                        # Check for CLI tool invocations in this test
                        cli_tool_used = self._detect_cli_tool_usage(node, cli_tools.keys(), content)

                        if cli_tool_used:
                            # Check if test has guard (skipif decorator, runtime check, requires_* marker, or class marker)
                            has_guard = (
                                self._has_skipif_guard(node, cli_tools[cli_tool_used])
                                or self._has_runtime_skip_check(node, cli_tool_used, content)
                                or self._has_requires_marker(node, cli_tools[cli_tool_used])
                                or self._has_class_marker(node, tree, cli_tools[cli_tool_used])
                            )

                            if not has_guard:
                                rel_path = test_file.relative_to(tests_dir.parent)
                                violations.append((str(rel_path), node.name, node.lineno, cli_tool_used))

            except (SyntaxError, UnicodeDecodeError):
                continue

        return violations

    def _detect_cli_tool_usage(self, func_node: ast.FunctionDef, cli_tools: set, file_content: str) -> str:
        """
        Detect if a test function invokes CLI tools via subprocess.

        Args:
            func_node: AST node for the test function
            cli_tools: Set of CLI tool names to detect
            file_content: Full file content for line-based checks

        Returns:
            CLI tool name if detected, empty string otherwise
        """
        # Walk the function body to find subprocess.run calls
        for node in ast.walk(func_node):
            # Check for subprocess.run(["tool", ...])
            if isinstance(node, ast.Call):
                # Check if it's subprocess.run or subprocess.Popen
                is_subprocess_call = False
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ["run", "Popen", "call", "check_output"]:
                        is_subprocess_call = True

                if is_subprocess_call and node.args:
                    # Check first argument (command list)
                    first_arg = node.args[0]
                    if isinstance(first_arg, ast.List) and first_arg.elts:
                        # Check first element of command list
                        # Note: Using ast.Constant (Python 3.8+) instead of deprecated ast.Str (removed in Python 3.14)
                        cmd_elem = first_arg.elts[0]
                        if isinstance(cmd_elem, ast.Constant):
                            cmd = cmd_elem.value
                            if cmd in cli_tools:
                                return cmd

        return ""

    def _has_skipif_guard(self, func_node: ast.FunctionDef, expected_marker: str) -> bool:
        """
        Check if a test function has skipif guard for a CLI tool.

        Args:
            func_node: AST node for the test function
            expected_marker: Expected marker name (e.g., "requires_kustomize")

        Returns:
            True if proper skipif guard exists, False otherwise
        """
        for decorator in func_node.decorator_list:
            # Check for @pytest.mark.skipif(...)
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if (
                        isinstance(decorator.func.value, ast.Attribute)
                        and isinstance(decorator.func.value.value, ast.Name)
                        and decorator.func.value.value.id == "pytest"
                        and decorator.func.value.attr == "mark"
                        and decorator.func.attr == "skipif"
                    ):
                        # Found skipif decorator
                        return True

        return False

    def _has_requires_marker(self, func_node: ast.FunctionDef, expected_marker: str) -> bool:
        """
        Check if a test function has @pytest.mark.requires_* marker.

        These markers trigger auto-skip via pytest_collection_modifyitems hook
        in conftest.py when the CLI tool is not installed.

        Args:
            func_node: AST node for the test function
            expected_marker: Expected marker name (e.g., "requires_kustomize")

        Returns:
            True if requires_* marker exists, False otherwise
        """
        for decorator in func_node.decorator_list:
            marker_name = self._extract_marker_name(decorator)
            if marker_name == expected_marker:
                return True
        return False

    def _has_runtime_skip_check(self, func_node: ast.FunctionDef, cli_tool: str, file_content: str) -> bool:
        """
        Check if a test function has runtime skip check using shutil.which().

        Args:
            func_node: AST node for the test function
            cli_tool: CLI tool name (e.g., "kustomize")
            file_content: Full file content

        Returns:
            True if runtime skip check exists, False otherwise
        """
        # Look for pattern: if not shutil.which("tool"): pytest.skip(...)
        for node in ast.walk(func_node):
            if isinstance(node, ast.If):
                # Check if this is a skip check
                test = node.test
                # Pattern: not shutil.which("tool")
                if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
                    if isinstance(test.operand, ast.Call):
                        # Check if it's shutil.which call
                        if isinstance(test.operand.func, ast.Attribute):
                            if (
                                isinstance(test.operand.func.value, ast.Name)
                                and test.operand.func.value.id == "shutil"
                                and test.operand.func.attr == "which"
                            ):
                                # Check if first argument is the CLI tool
                                if test.operand.args and isinstance(test.operand.args[0], ast.Constant):
                                    if test.operand.args[0].value == cli_tool:
                                        # Found the check, now verify it calls pytest.skip
                                        for stmt in node.body:
                                            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                                                if isinstance(stmt.value.func, ast.Attribute):
                                                    if (
                                                        isinstance(stmt.value.func.value, ast.Name)
                                                        and stmt.value.func.value.id == "pytest"
                                                        and stmt.value.func.attr == "skip"
                                                    ):
                                                        return True
        return False

    def _has_class_marker(self, func_node: ast.FunctionDef, tree: ast.Module, expected_marker: str) -> bool:
        """
        Check if a test function's parent class has the expected marker.

        Args:
            func_node: AST node for the test function
            tree: Full AST tree
            expected_marker: Expected marker name (e.g., "requires_kustomize")

        Returns:
            True if parent class has the marker, False otherwise
        """
        # Find the parent class of this function
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if this class contains the function
                for item in node.body:
                    if item == func_node:
                        # Found parent class, check for marker
                        for decorator in node.decorator_list:
                            marker_name = self._extract_marker_name(decorator)
                            if marker_name == expected_marker:
                                return True
        return False

    def _extract_marker_name(self, decorator: ast.expr) -> str:
        """
        Extract marker name from a decorator node.

        Handles:
        - @pytest.mark.unit
        - @pytest.mark.integration
        - @pytest.mark.requires_kubectl
        - @pytest.mark.requires_kustomize

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
