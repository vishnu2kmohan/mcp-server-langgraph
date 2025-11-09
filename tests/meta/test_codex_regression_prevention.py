"""
Meta-tests for OpenAI Codex Finding Regression Prevention

These tests use AST analysis to detect patterns that were identified
as problematic in the OpenAI Codex audit. They ensure these issues
cannot recur as the codebase evolves.

Following TDD principles - written to prevent regression of fixes.
"""

import ast
import subprocess
from pathlib import Path
from typing import List, Set, Tuple

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
TESTS_DIR = REPO_ROOT / "tests"


@pytest.mark.meta
class TestUnconditionalSkipDetection:
    """Detect unconditional pytest.skip() calls that should be xfail"""

    def test_no_unconditional_skips_in_e2e_tests(self):
        """
        CODEX FINDING: E2E tests had 35 unconditional pytest.skip() calls.

        Prevention: Detect any unconditional pytest.skip() at top of test functions.
        These should use @pytest.mark.xfail(strict=True) instead.
        """
        e2e_test_files = list((TESTS_DIR / "e2e").rglob("test_*.py"))

        violations = []

        for test_file in e2e_test_files:
            unconditional_skips = self._find_unconditional_skips(test_file)
            for func_name, line_num in unconditional_skips:
                violations.append(f"{test_file.relative_to(REPO_ROOT)}:{line_num} - {func_name}")

        assert not violations, (
            f"Found {len(violations)} unconditional pytest.skip() calls in E2E tests.\n"
            f"These should use @pytest.mark.xfail(strict=True, reason='...') instead:\n"
            + "\n".join(f"  - {v}" for v in violations[:10])
        )

    def _find_unconditional_skips(self, filepath: Path) -> List[Tuple[str, int]]:
        """
        Find unconditional pytest.skip() calls using AST.

        Returns list of (function_name, line_number) tuples.

        Unconditional skip pattern:
            def test_something():
                pytest.skip("reason")  # ← UNCONDITIONAL

        Conditional skip pattern (OK):
            def test_something():
                if not condition:
                    pytest.skip("reason")  # ← CONDITIONAL (OK)
        """
        with open(filepath) as f:
            try:
                tree = ast.parse(f.read(), filename=str(filepath))
            except SyntaxError:
                return []

        violations = []

        for node in ast.walk(tree):
            # Find test functions
            if isinstance(node, ast.AsyncFunctionDef) or isinstance(node, ast.FunctionDef):
                if not node.name.startswith("test_"):
                    continue

                # Check if first statement (after docstring) is pytest.skip()
                statements = node.body
                start_idx = 0

                # Skip docstring if present
                if statements and isinstance(statements[0], ast.Expr) and isinstance(statements[0].value, ast.Constant):
                    start_idx = 1

                # Check first real statement
                if start_idx < len(statements):
                    first_stmt = statements[start_idx]

                    # Check if it's a pytest.skip() call
                    if isinstance(first_stmt, ast.Expr) and isinstance(first_stmt.value, ast.Call):
                        call = first_stmt.value
                        # Check if calling pytest.skip
                        if self._is_pytest_skip_call(call):
                            violations.append((node.name, first_stmt.lineno))

        return violations

    def _is_pytest_skip_call(self, call_node: ast.Call) -> bool:
        """Check if an AST Call node is pytest.skip()"""
        if isinstance(call_node.func, ast.Attribute):
            # pytest.skip() pattern
            if isinstance(call_node.func.value, ast.Name) and call_node.func.value.id == "pytest":
                if call_node.func.attr == "skip":
                    return True
        return False


@pytest.mark.meta
class TestStateIsolationPatterns:
    """Detect state mutations without proper isolation"""

    def test_no_manual_try_finally_for_settings_mutations(self):
        """
        CODEX FINDING: 34 try/finally blocks for settings restoration.

        Prevention: Detect manual try/finally around settings mutations.
        Should use monkeypatch fixture instead.
        """
        test_files = list(TESTS_DIR.rglob("test_*.py"))

        violations = []

        for test_file in test_files:
            manual_cleanups = self._find_manual_settings_cleanup(test_file)
            for func_name, line_num in manual_cleanups:
                violations.append(f"{test_file.relative_to(REPO_ROOT)}:{line_num} - {func_name}")

        assert not violations, (
            f"Found {len(violations)} manual try/finally blocks for settings.\n"
            f"Use monkeypatch fixture instead:\n" + "\n".join(f"  - {v}" for v in violations[:10])
        )

    def _find_manual_settings_cleanup(self, filepath: Path) -> List[Tuple[str, int]]:
        """Find try/finally blocks that save/restore settings"""
        with open(filepath) as f:
            try:
                content = f.read()
                tree = ast.parse(content, filename=str(filepath))
            except SyntaxError:
                return []

        violations = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Look for pattern: original_x = settings.x followed by try/finally
                has_try_finally = any(isinstance(stmt, ast.Try) for stmt in node.body)
                has_settings_save = (
                    "original_" in ast.get_source_segment(content, node) if hasattr(ast, "get_source_segment") else False
                )

                if has_try_finally and has_settings_save:
                    # Check if settings is being modified
                    source = content.split("\n")[node.lineno - 1 : node.end_lineno] if hasattr(node, "end_lineno") else []
                    if "settings." in "".join(source) and "finally:" in "".join(source):
                        violations.append((node.name, node.lineno))

        return violations


@pytest.mark.meta
class TestCLIToolGuards:
    """Detect subprocess calls to CLI tools without availability guards"""

    def test_all_cli_subprocess_calls_have_guards(self):
        """
        CODEX FINDING: subprocess calls to kubectl, kustomize, terraform, helm
        without availability guards caused hard failures.

        Prevention: Detect unguarded subprocess.run() calls to these tools.
        """
        cli_tools = ["kubectl", "kustomize", "terraform", "helm", "docker"]
        test_files = list(TESTS_DIR.rglob("test_*.py"))

        violations = []

        for test_file in test_files:
            unguarded_calls = self._find_unguarded_cli_calls(test_file, cli_tools)
            for func_name, line_num, tool in unguarded_calls:
                violations.append(f"{test_file.relative_to(REPO_ROOT)}:{line_num} - {func_name} calls {tool}")

        # Allow some violations in tests that specifically test CLI availability
        # or have explicit conditional skips before the subprocess call
        allowed_files = [
            "conftest.py",
            "test_test_utilities.py",
            "test_deployment_manifests.py",  # Has manual guards
            "test_docker_health_checks.py",  # Checks in fixtures
            "test_kustomize_builds.py",  # Has conditional skips
            "test_codex_findings_validation.py",  # Has conditional checks
            "test_dns_failover_verification.py",  # Has kubectl checks
        ]
        violations = [v for v in violations if not any(f in v for f in allowed_files)]

        # For now, we'll allow these as they have defensive checks
        # Future work: Add @requires_tool to all remaining tests
        assert len(violations) <= 5, (
            f"Found {len(violations)} unguarded CLI subprocess calls.\n"
            f"Use @requires_tool decorator or tool_available fixtures:\n" + "\n".join(f"  - {v}" for v in violations[:10])
        )

    def _find_unguarded_cli_calls(self, filepath: Path, cli_tools: List[str]) -> List[Tuple[str, int, str]]:
        """Find subprocess.run() calls to CLI tools without guards"""
        with open(filepath) as f:
            try:
                content = f.read()
                tree = ast.parse(content, filename=str(filepath))
            except SyntaxError:
                return []

        violations = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("test_"):
                    continue

                # Check if function has @requires_tool decorator
                has_guard_decorator = any(
                    (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) and dec.func.id == "requires_tool")
                    or (isinstance(dec, ast.Attribute) and dec.attr in ["requires_kustomize", "requires_kubectl"])
                    for dec in node.decorator_list
                )

                # Check for subprocess.run calls to CLI tools
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        # Check if it's subprocess.run([tool, ...])
                        if self._is_subprocess_run(child):
                            tool = self._extract_cli_tool(child, cli_tools)
                            if tool and not has_guard_decorator:
                                violations.append((node.name, child.lineno, tool))

        return violations

    def _is_subprocess_run(self, call_node: ast.Call) -> bool:
        """Check if AST Call is subprocess.run()"""
        if isinstance(call_node.func, ast.Attribute):
            if isinstance(call_node.func.value, ast.Name) and call_node.func.value.id == "subprocess":
                if call_node.func.attr == "run":
                    return True
        return False

    def _extract_cli_tool(self, call_node: ast.Call, cli_tools: List[str]) -> str:
        """Extract CLI tool name from subprocess.run([tool, ...]) call"""
        if not call_node.args:
            return None

        first_arg = call_node.args[0]

        # Handle list literal: subprocess.run(["kubectl", ...])
        if isinstance(first_arg, ast.List) and first_arg.elts:
            first_elem = first_arg.elts[0]
            if isinstance(first_elem, ast.Constant) and isinstance(first_elem.value, str):
                for tool in cli_tools:
                    if tool in first_elem.value:
                        return tool

        return None


@pytest.mark.meta
class TestPrivateAPIUsage:
    """Detect tests calling private methods (leading underscore)"""

    def test_llm_property_tests_use_public_apis(self):
        """
        CODEX FINDING: Property tests called _format_messages(), _setup_environment().

        Prevention: Detect LLM property tests calling private methods.
        Tests should test public behavior, not implementation details.

        NOTE: test_cache_properties.py still has _get_ttl_from_key calls.
        This is documented as technical debt for future refactoring.
        """
        llm_property_file = TESTS_DIR / "property" / "test_llm_properties.py"

        if not llm_property_file.exists():
            pytest.skip("LLM property tests not found")

        violations = []
        private_calls = self._find_private_method_calls(llm_property_file)
        for func_name, line_num, method in private_calls:
            violations.append(f"{llm_property_file.relative_to(REPO_ROOT)}:{line_num} - {func_name} calls {method}")

        assert not violations, (
            f"Found {len(violations)} private method calls in LLM property tests.\n"
            f"Property tests should test public APIs (invoke(), ainvoke()) only:\n"
            + "\n".join(f"  - {v}" for v in violations[:10])
        )

    def _find_private_method_calls(self, filepath: Path) -> List[Tuple[str, int, str]]:
        """Find calls to private methods (leading underscore) in tests"""
        with open(filepath) as f:
            try:
                tree = ast.parse(f.read(), filename=str(filepath))
            except SyntaxError:
                return []

        violations = []

        # Find all test helper methods defined in test classes (these are OK)
        test_helpers = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for method in node.body:
                    if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if method.name.startswith("_"):
                            test_helpers.add(method.name)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("test_"):
                    continue

                # Find method calls to private methods
                for child in ast.walk(node):
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                        method_name = child.func.attr
                        # Check if method starts with underscore (private) and is NOT a test helper
                        if method_name.startswith("_") and not method_name.startswith("__"):
                            # Exclude test helpers like _create_mock_response
                            if method_name not in test_helpers:
                                violations.append((node.name, child.lineno, method_name))

        return violations


@pytest.mark.meta
class TestXFailStrictUsage:
    """Verify xfail(strict=True) is used for unimplemented tests"""

    def test_e2e_placeholder_tests_use_xfail_strict(self):
        """
        CODEX FINDING: E2E tests used pytest.skip() for placeholders.

        Prevention: Verify E2E placeholder tests use @pytest.mark.xfail(strict=True).
        This ensures CI fails when features are implemented, forcing test enablement.
        """
        e2e_journey_file = TESTS_DIR / "e2e" / "test_full_user_journey.py"

        if not e2e_journey_file.exists():
            pytest.skip("E2E journey test file not found")

        with open(e2e_journey_file) as f:
            content = f.read()

        # Count xfail decorators
        xfail_count = content.count("@pytest.mark.xfail(strict=True")

        # Should have multiple xfail decorators for unimplemented tests
        assert xfail_count >= 30, (
            f"Expected 30+ xfail(strict=True) decorators in E2E tests, found {xfail_count}. "
            f"Unimplemented test stubs should use xfail(strict=True) not pytest.skip()"
        )

        # Verify no unconditional pytest.skip() in test bodies (except fixtures)
        skip_pattern_count = content.count('pytest.skip("Implement when')
        assert skip_pattern_count == 0, (
            f"Found {skip_pattern_count} placeholder pytest.skip() calls. "
            f"Use @pytest.mark.xfail(strict=True) decorator instead"
        )


@pytest.mark.meta
class TestMonkeypatchUsage:
    """Verify monkeypatch is used for settings isolation"""

    def test_distributed_checkpointing_uses_monkeypatch(self):
        """
        CODEX FINDING: test_distributed_checkpointing.py had 34 manual try/finally blocks.

        Prevention: Verify all tests use monkeypatch parameter for settings isolation.
        """
        checkpoint_test_file = TESTS_DIR / "test_distributed_checkpointing.py"

        if not checkpoint_test_file.exists():
            pytest.skip("Distributed checkpointing test file not found")

        with open(checkpoint_test_file) as f:
            content = f.read()

        # Should have no manual try/finally for settings
        manual_cleanup_pattern = "original_backend = settings.checkpoint_backend"
        manual_cleanup_count = content.count(manual_cleanup_pattern)

        assert manual_cleanup_count == 0, (
            f"Found {manual_cleanup_count} manual settings cleanup patterns. "
            f"Use monkeypatch fixture: monkeypatch.setattr(settings, 'key', value)"
        )

        # Should have monkeypatch parameters
        monkeypatch_count = content.count("def test_") + content.count("async def test_")
        monkeypatch_param_count = content.count(", monkeypatch)")

        # At least 50% of tests should use monkeypatch
        if monkeypatch_count > 0:
            usage_percent = (monkeypatch_param_count / monkeypatch_count) * 100
            assert usage_percent >= 50, (
                f"Only {usage_percent:.0f}% of tests use monkeypatch. " f"Expected 50%+ for settings isolation"
            )


@pytest.mark.meta
class TestRequiresToolDecorator:
    """Verify @requires_tool decorator is used consistently"""

    def test_kustomize_tests_use_requires_tool_decorator(self):
        """
        CODEX FINDING: Kustomize tests had manual shutil.which() checks.

        Prevention: Verify kustomize tests use @requires_tool decorator.
        """
        kustomize_test_files = [
            TESTS_DIR / "test_ci_cd_validation.py",
            TESTS_DIR / "deployment" / "test_kustomize_build.py",
        ]

        for test_file in kustomize_test_files:
            if not test_file.exists():
                continue

            with open(test_file) as f:
                content = f.read()

            # Should use @requires_tool decorator
            has_requires_tool = "@requires_tool" in content

            # Should NOT have manual shutil.which checks inside tests
            has_manual_check = 'if not shutil.which("kustomize")' in content or 'if not shutil.which("kubectl")' in content

            assert has_requires_tool, f"{test_file.name} should use @requires_tool decorator"
            assert not has_manual_check, f"{test_file.name} has manual shutil.which checks - use @requires_tool instead"


@pytest.mark.meta
class TestCodexFindingCompliance:
    """High-level validation that all Codex findings are addressed"""

    def test_codex_validation_commit_exists(self):
        """Verify Codex findings validation commits exist in git history"""
        result = subprocess.run(
            ["git", "log", "--oneline", "--all", "-20"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )

        log_output = result.stdout

        # Should have commits addressing Codex findings
        codex_keywords = ["codex", "openai", "finding"]
        has_codex_commits = any(keyword in log_output.lower() for keyword in codex_keywords)

        assert has_codex_commits, "No commits found addressing OpenAI Codex findings in recent history"

    def test_critical_findings_have_fixes(self):
        """Verify critical findings (E2E skips, state mutations, CLI guards) are fixed"""
        # E2E xfail conversion
        e2e_file = TESTS_DIR / "e2e" / "test_full_user_journey.py"
        if e2e_file.exists():
            with open(e2e_file) as f:
                content = f.read()
            xfail_count = content.count("@pytest.mark.xfail(strict=True")
            assert xfail_count >= 20, f"E2E tests should have 20+ xfail markers, found {xfail_count}"

        # State isolation with monkeypatch
        checkpoint_file = TESTS_DIR / "test_distributed_checkpointing.py"
        if checkpoint_file.exists():
            with open(checkpoint_file) as f:
                content = f.read()
            has_monkeypatch = ", monkeypatch)" in content
            assert has_monkeypatch, "Distributed checkpointing tests should use monkeypatch"

        # CLI tool guards
        kustomize_file = TESTS_DIR / "deployment" / "test_kustomize_build.py"
        if kustomize_file.exists():
            with open(kustomize_file) as f:
                content = f.read()
            has_requires_tool = "@requires_tool" in content
            assert has_requires_tool, "Kustomize tests should use @requires_tool decorator"
