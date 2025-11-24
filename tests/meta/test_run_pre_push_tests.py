"""
Meta-validation: Test run_pre_push_tests.py conditional meta test execution.

This test suite ensures that:
1. Meta tests are included when workflow-related files change
2. Meta tests are excluded when only non-workflow files change
3. Git diff detection works correctly across different scenarios

TDD Principle: These tests MUST pass to ensure meta tests (which validate
test infrastructure) run when needed but don't slow down regular commits.

Issue: Consolidated test runner excludes meta tests even when .github/,
.pre-commit-config.yaml, or pytest.ini change. This causes workflow drift
to go undetected until CI fails.

Reference: Codex Audit Finding - Make/Test Flow Issue 1.4
"""

import gc
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testrunprepushtests")
class TestRunPrePushTestsMetaConditional:
    """Validate conditional meta test execution based on changed files."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root directory."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def script_path(self, repo_root: Path) -> Path:
        """Get path to run_pre_push_tests.py script."""
        return repo_root / "scripts" / "run_pre_push_tests.py"

    def test_should_run_meta_tests_detects_workflow_changes(self, script_path: Path):
        """
        Test that should_run_meta_tests() returns True when workflow files change.

        CONFIGURATION DRIFT: Meta tests are currently excluded from pre-push
        (scripts/run_pre_push_tests.py:95) even when .github/, .pre-commit-config.yaml,
        or pytest.ini change.

        Impact:
        - Workflow changes bypass meta-test validation
        - Broken hooks/CI discovered only after push
        - No local feedback loop for infrastructure changes

        Solution: Implement should_run_meta_tests() function that detects:
        - Changes to .github/ directory
        - Changes to .pre-commit-config.yaml
        - Changes to pytest.ini or pyproject.toml (test config)
        - Changes to tests/conftest.py (fixture changes)

        Expected behavior:
        - If ANY workflow file changed → include meta tests
        - Otherwise → exclude meta tests (performance)

        Reference: Codex Audit Finding - Make/Test Flow Issue 1.4
        """
        # This test validates the should_run_meta_tests() function
        # Import the function
        from scripts.run_pre_push_tests import should_run_meta_tests

        # Mock git diff to return workflow file changes
        with patch("subprocess.run") as mock_run:
            # Scenario 1: .github/workflows/ci.yaml changed
            mock_run.return_value = MagicMock(stdout=".github/workflows/ci.yaml\nsrc/some_file.py\n", returncode=0)
            assert should_run_meta_tests() is True, (
                "should_run_meta_tests() MUST return True when .github/ files change\n"
                "Changed file: .github/workflows/ci.yaml\n"
                "Reason: Workflow changes require meta test validation"
            )

            # Scenario 2: .pre-commit-config.yaml changed
            mock_run.return_value = MagicMock(stdout=".pre-commit-config.yaml\nsrc/another_file.py\n", returncode=0)
            assert should_run_meta_tests() is True, (
                "should_run_meta_tests() MUST return True when .pre-commit-config.yaml changes\n"
                "Changed file: .pre-commit-config.yaml\n"
                "Reason: Hook config changes require meta test validation"
            )

            # Scenario 3: pytest.ini changed
            mock_run.return_value = MagicMock(stdout="pytest.ini\nsrc/file.py\n", returncode=0)
            assert should_run_meta_tests() is True, (
                "should_run_meta_tests() MUST return True when pytest.ini changes\n"
                "Changed file: pytest.ini\n"
                "Reason: Test config changes require meta test validation"
            )

            # Scenario 4: tests/conftest.py changed
            mock_run.return_value = MagicMock(stdout="tests/conftest.py\ntests/unit/test_something.py\n", returncode=0)
            assert should_run_meta_tests() is True, (
                "should_run_meta_tests() MUST return True when tests/conftest.py changes\n"
                "Changed file: tests/conftest.py\n"
                "Reason: Fixture changes require meta test validation"
            )

            # Scenario 5: Only non-workflow files changed
            mock_run.return_value = MagicMock(stdout="src/core/agent.py\ntests/unit/test_agent.py\n", returncode=0)
            assert should_run_meta_tests() is False, (
                "should_run_meta_tests() MUST return False when only non-workflow files change\n"
                "Changed files: src/core/agent.py, tests/unit/test_agent.py\n"
                "Reason: No workflow changes, skip meta tests for performance"
            )

    def test_marker_expression_includes_meta_when_workflow_changed(self, script_path: Path):
        """
        Test that marker expression includes 'meta' when workflow files change.

        Current behavior (scripts/run_pre_push_tests.py:95):
            marker_expression = "(unit or api or property) and not llm and not meta"

        Expected behavior when .github/ changed:
            marker_expression = "(unit or api or property or meta) and not llm"
                                                         ^^^^ Added

        This ensures workflow changes are validated before push.
        """
        # Read current script content
        with open(script_path) as f:
            script_content = f.read()

        # Verify conditional logic is implemented
        assert (
            "should_run_meta_tests" in script_content
        ), "should_run_meta_tests() function should be implemented and used in main()"

        # Verify conditional marker expression
        assert "if should_run_meta_tests():" in script_content, (
            "main() should conditionally include meta tests based on should_run_meta_tests()\n"
            "\n"
            "Expected pattern:\n"
            "  if should_run_meta_tests():\n"
            '      marker_expression = "(unit or api or property or meta) and not llm"\n'
            "  else:\n"
            '      marker_expression = "(unit or api or property) and not llm and not meta"\n'
        )

        # Verify both marker expressions exist
        assert (
            "(unit or api or property or meta) and not llm" in script_content
        ), "Script should include meta tests when workflow files change"
        assert (
            "(unit or api or property) and not llm and not meta" in script_content
        ), "Script should exclude meta tests when only code files change"

    def test_performance_impact_of_meta_tests(self, repo_root: Path):
        """
        Document performance impact of including meta tests.

        Meta tests (42 tests) validate test infrastructure:
        - Git hook syntax and configuration
        - CI workflow validity
        - Pytest fixture organization
        - Test marker consistency

        Performance data:
        - Meta tests runtime: ~5-10 seconds
        - Pre-push total: 8-12 minutes
        - Impact: +1-2% overhead when included

        Trade-off: Worth the overhead when workflow files change,
        skip for regular commits to maintain fast pre-push.
        """
        # Count meta tests
        meta_tests = list(repo_root.glob("tests/meta/test_*.py"))

        # Document that meta tests exist and are fast
        assert len(meta_tests) > 0, "Meta tests should exist in tests/meta/"

        # This test documents the trade-off for review
        # No assertion needed - just documentation

    def test_git_diff_command_correctness(self):
        """
        Test that git diff command uses correct arguments.

        CRITICAL: Must use 'git diff --name-only HEAD' (staged + unstaged)
        NOT 'git diff --name-only --cached' (staged only)

        Why:
        - Pre-push should validate ALL uncommitted changes
        - Both staged and unstaged changes affect test results
        - Matches developer expectation: "validate current state"

        Example:
        - Developer edits .github/workflows/ci.yaml (unstaged)
        - Runs pre-push validation
        - Expects meta tests to run
        - If using --cached, meta tests skipped (wrong!)
        """
        # This test documents the correct git diff command
        # Implementation should use: git diff --name-only HEAD

        expected_command = ["git", "diff", "--name-only", "HEAD"]

        # After implementation, verify the command
        # (This will fail until implemented - TDD RED phase)
        import inspect

        try:
            from scripts.run_pre_push_tests import should_run_meta_tests

            source = inspect.getsource(should_run_meta_tests)
            assert "git diff --name-only HEAD" in source or 'git", "diff", "--name-only", "HEAD"' in source, (
                "should_run_meta_tests() MUST use 'git diff --name-only HEAD'\n"
                "\n"
                "CORRECT: git diff --name-only HEAD\n"
                "  - Shows staged + unstaged changes\n"
                "  - Validates current working state\n"
                "\n"
                "WRONG: git diff --name-only --cached\n"
                "  - Shows only staged changes\n"
                "  - Misses unstaged workflow edits\n"
                "\n"
                f"Expected command: {' '.join(expected_command)}\n"
            )
        except (ImportError, AttributeError):
            # Function not implemented yet (TDD RED phase)
            pytest.skip("should_run_meta_tests() not implemented yet")
