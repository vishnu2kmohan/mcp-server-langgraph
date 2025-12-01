"""
TDD: Test change detection patterns for validator infrastructure.

This meta-test ensures that changes to validator scripts, Makefile, and other
infrastructure files trigger meta test execution during pre-push.

Reference: Codex Audit - Change detection gaps in run_pre_push_tests.py
"""

import gc

import pytest

pytestmark = pytest.mark.meta


@pytest.mark.xdist_group(name="change_detection")
class TestChangeDetectionPatterns:
    """Verify critical paths trigger meta tests."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.parametrize(
        "path,expected",
        [
            # NEW PATTERNS - Should trigger meta tests (currently fail)
            ("scripts/validators/check_test_memory_safety.py", True),
            ("scripts/validators/validate_fast.py", True),
            ("scripts/validators/validate_pytest_fixtures.py", True),
            ("scripts/security/run_security_suite.py", True),
            ("scripts/security/scan_helm_templates.sh", True),
            ("scripts/run_pre_push_tests.py", True),
            (".githooks/pre-commit-dependency-validation", True),
            (".pre-commit-hooks/check_subprocess_timeout.py", True),
            (".pre-commit-hooks/check_banned_imports.py", True),
            ("Makefile", True),
            # Subdirectory conftest.py files
            ("tests/unit/conftest.py", True),
            ("tests/integration/conftest.py", True),
            ("tests/meta/conftest.py", True),
            ("tests/e2e/conftest.py", True),
            # EXISTING PATTERNS - Should still trigger meta tests (currently pass)
            (".github/workflows/ci.yaml", True),
            (".github/actions/setup/action.yml", True),
            (".pre-commit-config.yaml", True),
            ("pytest.ini", True),
            ("pyproject.toml", True),
            ("tests/conftest.py", True),
            # NEGATIVE CASES - Should NOT trigger meta tests
            ("src/mcp_server_langgraph/main.py", False),
            ("src/mcp_server_langgraph/core/dependencies.py", False),
            ("tests/unit/test_auth.py", False),
            ("tests/integration/test_api.py", False),
            ("docs/getting-started.mdx", False),
            ("README.md", False),
            ("deployments/helm/values.yaml", False),
            # Edge cases
            ("clients/python/pyproject.toml", False),  # Not root pyproject.toml
            ("some_pyproject.toml", False),  # Not exactly pyproject.toml
        ],
    )
    def test_matches_workflow_pattern(self, path: str, expected: bool) -> None:
        """Test that workflow pattern matching is correct."""
        # Import inside test for xdist isolation
        from scripts.run_pre_push_tests import matches_workflow_pattern

        assert matches_workflow_pattern(path) == expected, f"Expected matches_workflow_pattern('{path}') to be {expected}"


@pytest.mark.xdist_group(name="change_detection")
class TestChangeDetectionIntegration:
    """Integration tests for should_run_meta_tests() function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def _create_git_mock(self, monkeypatch: pytest.MonkeyPatch, changed_files: str) -> None:
        """Create a fully-isolated git mock for testing should_run_meta_tests.

        This helper ensures tests are isolated from real git state by mocking
        ALL git subprocess calls. Without this, CI tests fail because real
        git commands return the actual PR changed files.
        """
        import subprocess
        from unittest.mock import MagicMock

        # Clear any PRE_COMMIT env vars that might affect behavior
        monkeypatch.delenv("PRE_COMMIT_FROM_REF", raising=False)
        monkeypatch.delenv("PRE_COMMIT_TO_REF", raising=False)

        mock_diff_result = MagicMock()
        mock_diff_result.returncode = 0
        mock_diff_result.stdout = changed_files

        def mock_run(args, **kwargs):
            if args[0] == "git":
                if "merge-base" in args:
                    raise subprocess.CalledProcessError(1, args)
                if "diff" in args or "show" in args:
                    return mock_diff_result
            raise RuntimeError(f"Unexpected subprocess call: {args}")

        monkeypatch.setattr(subprocess, "run", mock_run)

    def test_validator_script_change_triggers_meta_tests(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify that changes to validator scripts trigger meta tests."""
        self._create_git_mock(monkeypatch, "scripts/validators/check_test_memory_safety.py\n")

        from scripts.run_pre_push_tests import should_run_meta_tests

        assert should_run_meta_tests() is True

    def test_makefile_change_triggers_meta_tests(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify that Makefile changes trigger meta tests."""
        self._create_git_mock(monkeypatch, "Makefile\n")

        from scripts.run_pre_push_tests import should_run_meta_tests

        assert should_run_meta_tests() is True

    def test_subdirectory_conftest_triggers_meta_tests(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify that subdirectory conftest.py changes trigger meta tests."""
        self._create_git_mock(monkeypatch, "tests/unit/conftest.py\n")

        from scripts.run_pre_push_tests import should_run_meta_tests

        assert should_run_meta_tests() is True

    def test_source_code_only_skips_meta_tests(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify that only source code changes skip meta tests."""
        self._create_git_mock(
            monkeypatch,
            "src/mcp_server_langgraph/main.py\nsrc/mcp_server_langgraph/auth/keycloak.py\n",
        )

        from scripts.run_pre_push_tests import should_run_meta_tests

        assert should_run_meta_tests() is False
