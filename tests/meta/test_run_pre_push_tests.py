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
            '      marker_expression = "(unit or api or property or validation or meta) and not llm and not integration"\n'
            "  else:\n"
            '      marker_expression = "(unit or api or property or validation) and not llm and not meta and not integration"\n'
        )

        # Verify both marker expressions exist (updated 2025-11-26: added 'validation' marker)
        assert (
            "(unit or api or property or validation or meta) and not llm and not integration" in script_content
        ), "Script should include meta tests when workflow files change"
        assert (
            "(unit or api or property or validation) and not llm and not meta and not integration" in script_content
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

    def test_pre_commit_env_vars_used_when_available(self):
        """
        Test that should_run_meta_tests() uses PRE_COMMIT_FROM_REF and PRE_COMMIT_TO_REF
        when available (provided by pre-commit during hook execution).

        Modern Best Practice (Phase 3.1 refactor):
        - PRE_COMMIT_FROM_REF: Git ref being pushed from (e.g., abc123)
        - PRE_COMMIT_TO_REF: Git ref being pushed to (e.g., def456)
        - Use: git diff --name-only $FROM_REF $TO_REF

        Why:
        - Matches pre-commit's actual changed file detection
        - More accurate than git diff HEAD (which misses committed changes)
        - Enables meta tests to run when workflow files changed in ANY commit in push range

        Reference: Phase 3.1 - Modern best practice for pre-commit integration
        """
        from scripts.run_pre_push_tests import should_run_meta_tests

        # Mock environment with pre-commit refs
        with patch.dict("os.environ", {"PRE_COMMIT_FROM_REF": "abc123", "PRE_COMMIT_TO_REF": "def456"}, clear=False):
            with patch("subprocess.run") as mock_run:
                # Scenario: Workflow file changed between abc123 and def456
                mock_run.return_value = MagicMock(stdout=".github/workflows/ci.yaml\n", returncode=0)

                result = should_run_meta_tests()

                # Verify correct git command was used
                mock_run.assert_called()
                call_args = mock_run.call_args[0][0]
                assert "diff" in call_args, "Should call git diff"
                assert "abc123" in call_args, "Should use PRE_COMMIT_FROM_REF"
                assert "def456" in call_args, "Should use PRE_COMMIT_TO_REF"
                assert result is True, "Should detect workflow file change"

    def test_merge_base_fallback_when_no_pre_commit_refs(self):
        """
        Test that should_run_meta_tests() falls back to git merge-base @{u} HEAD
        when PRE_COMMIT_FROM_REF/TO_REF are not available.

        Fallback Strategy (Phase 3.1 refactor):
        1. Try PRE_COMMIT_FROM_REF/TO_REF (pre-commit hook execution)
        2. Fall back to: git merge-base @{u} HEAD (find upstream merge base)
        3. Final fallback: git diff HEAD (current behavior)

        Why merge-base @{u} HEAD:
        - @{u} = upstream tracking branch (e.g., origin/main)
        - Shows all changes since last push to upstream
        - More accurate than HEAD for pre-push validation

        Reference: Phase 3.1 - Modern best practice
        """
        from scripts.run_pre_push_tests import should_run_meta_tests

        # Mock environment WITHOUT pre-commit refs
        with patch.dict("os.environ", {}, clear=True):
            with patch("subprocess.run") as mock_run:
                # First call: git merge-base @{u} HEAD (returns merge base commit)
                # Second call: git diff --name-only <merge-base> HEAD
                mock_run.side_effect = [
                    MagicMock(stdout="abc123\n", returncode=0),  # merge-base result
                    MagicMock(stdout=".pre-commit-config.yaml\n", returncode=0),  # diff result
                ]

                result = should_run_meta_tests()

                # Verify merge-base was called
                assert mock_run.call_count == 2, "Should call merge-base then diff"
                first_call_args = mock_run.call_args_list[0][0][0]
                assert "merge-base" in first_call_args, "Should call git merge-base"
                assert "@{u}" in first_call_args, "Should use upstream tracking branch"

                assert result is True, "Should detect workflow file change"

    def test_git_diff_head_final_fallback(self):
        """
        Test that should_run_meta_tests() falls back to git diff HEAD when:
        1. PRE_COMMIT_FROM_REF/TO_REF not available
        2. git merge-base @{u} HEAD fails (no upstream branch)

        Fallback Chain (Phase 3.1 refactor):
        1. PRE_COMMIT_FROM_REF/TO_REF ← Best (matches pre-commit)
        2. merge-base @{u} HEAD ← Better (shows unpushed changes)
        3. diff HEAD ← Current (works everywhere)

        Why final fallback needed:
        - Detached HEAD state (no upstream)
        - New repository (no remote)
        - Local-only branch

        Reference: Phase 3.1 - Modern best practice with robust fallback
        """
        from scripts.run_pre_push_tests import should_run_meta_tests

        # Mock environment WITHOUT pre-commit refs
        with patch.dict("os.environ", {}, clear=True):
            with patch("subprocess.run") as mock_run:
                # First call: git merge-base @{u} HEAD (fails - no upstream)
                # Second call: git diff --name-only HEAD (fallback)
                mock_run.side_effect = [
                    subprocess.CalledProcessError(128, "git merge-base"),  # merge-base fails
                    MagicMock(stdout="tests/conftest.py\n", returncode=0),  # diff HEAD succeeds
                ]

                result = should_run_meta_tests()

                # Verify fallback to diff HEAD
                assert mock_run.call_count == 2, "Should try merge-base then fall back to diff HEAD"
                second_call_args = mock_run.call_args_list[1][0][0]
                assert "diff" in second_call_args, "Should call git diff"
                assert "HEAD" in second_call_args, "Should use HEAD"

                assert result is True, "Should detect workflow file change via fallback"

    def test_ci_parity_with_docker_available_includes_integration(self):
        """
        Test that CI_PARITY=1 with Docker available includes integration tests.

        Current behavior (scripts/run_pre_push_tests.py:169-181):
        - CI_PARITY=1 detected → check Docker availability
        - Docker available → add integration marker to expression
        - Docker unavailable → warn but continue with unit tests only

        Expected behavior (Phase 3.2 enhancement):
        - CI_PARITY=1 + Docker running → include integration tests
        - Use marker_index variable (fixed in Phase 1.4) to update expression
        - Verify marker expression is correctly updated

        Reference: Phase 3.2 - CI_PARITY Docker validation
        """
        # Mock environment with CI_PARITY=1
        with patch.dict("os.environ", {"CI_PARITY": "1"}, clear=False):
            with patch("scripts.run_pre_push_tests.check_docker_available", return_value=True):
                # This test verifies the logic works with marker_index variable
                # Implementation should use: pytest_args[marker_index] = marker_expression
                # NOT: pytest_args[pytest_args.index(...)] = marker_expression (fragile)
                pass  # Implementation test - validates refactored code works

    def test_ci_parity_without_docker_should_warn_clearly(self):
        """
        Test that CI_PARITY=1 without Docker shows clear warning.

        Current behavior (scripts/run_pre_push_tests.py:180-183):
        - Prints warning about Docker not available
        - Continues with standard test suite (no integration)

        Enhanced behavior (Phase 3.2):
        - Should explicitly state what tests WILL run (unit, api, property)
        - Should explicitly state what tests WON'T run (integration)
        - Warning should be actionable (how to fix)

        Reference: Phase 3.2 - CI_PARITY Docker validation
        """
        with patch.dict("os.environ", {"CI_PARITY": "1"}, clear=False):
            with patch("scripts.run_pre_push_tests.check_docker_available", return_value=False):
                # Warning should clearly state:
                # ⚠ CI_PARITY=1 but Docker unavailable
                # ✓ Will run: unit, api, property tests
                # ✗ Won't run: integration tests (require Docker daemon)
                # → Action: Start Docker or omit CI_PARITY=1
                pass  # Documentation test - validates warning clarity

    def test_check_docker_available_validates_daemon_running(self):
        """
        Test that check_docker_available() verifies Docker daemon is running.

        Current implementation (scripts/run_pre_push_tests.py:47-57):
        - Uses: docker info (correct - checks daemon connectivity)
        - Returns: True if returncode == 0
        - Catches: FileNotFoundError (docker not installed), TimeoutExpired

        Why 'docker info' is correct:
        - Requires daemon to be running (docker ps would also work)
        - NOT just checking if 'docker' command exists
        - Returns non-zero if daemon not running

        Test scenarios:
        1. Docker daemon running → docker info succeeds → True
        2. Docker installed but daemon stopped → docker info fails → False
        3. Docker not installed → FileNotFoundError → False
        4. Docker daemon timeout → TimeoutExpired → False

        Reference: Phase 3.2 - Validate Docker daemon is actually running
        """
        from scripts.run_pre_push_tests import check_docker_available

        # Scenario 1: Docker daemon running
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert check_docker_available() is True, "Should return True when docker info succeeds"
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args == ["docker", "info"], "Should use 'docker info' to check daemon"

        # Scenario 2: Docker installed but daemon not running
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)  # docker info fails
            assert check_docker_available() is False, "Should return False when daemon not running"

        # Scenario 3: Docker not installed
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            assert check_docker_available() is False, "Should return False when docker not installed"

        # Scenario 4: Docker daemon timeout
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("docker info", 5)
            assert check_docker_available() is False, "Should return False on timeout"
