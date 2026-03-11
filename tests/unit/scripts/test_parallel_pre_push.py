"""
Tests for parallel_pre_push.sh - Parallel Pre-Push Lane Orchestrator.

Validates:
1. Lane selection returns correct count for different resource profiles
2. Dry-run mode outputs expected lane configuration
3. Hook drift detection catches unmapped hooks
4. Exit code is nonzero when any lane fails
5. PRE_PUSH_SEQUENTIAL=1 falls back to standard pre-commit
6. Signal handling cleans up child processes
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.helpers.path_helpers import get_repo_root

pytestmark = [pytest.mark.unit]

PROJECT_ROOT = get_repo_root()
PRE_PUSH_SCRIPT = PROJECT_ROOT / "scripts" / "hooks" / "parallel_pre_push.sh"


class TestParallelPrePushScript:
    """Tests for the parallel_pre_push.sh lane orchestrator."""

    def test_script_exists_at_expected_path(self) -> None:
        """parallel_pre_push.sh must exist at expected location."""
        assert PRE_PUSH_SCRIPT.exists(), f"scripts/hooks/parallel_pre_push.sh not found at {PRE_PUSH_SCRIPT}"

    def test_script_is_executable(self) -> None:
        """parallel_pre_push.sh must be executable."""
        assert PRE_PUSH_SCRIPT.stat().st_mode & 0o111, "scripts/hooks/parallel_pre_push.sh is not executable"

    def test_five_lanes_defined(self) -> None:
        """Script must define exactly 5 lanes."""
        content = PRE_PUSH_SCRIPT.read_text()
        for lane in [
            "python-tests",
            "frontend",
            "security",
            "type-check-validators",
            "infra-docs",
        ]:
            assert lane in content, f"Lane '{lane}' not defined in script"

    def test_ci_mode_limits_to_2_lanes(self) -> None:
        """CI mode should limit to 2 concurrent lanes."""
        content = PRE_PUSH_SCRIPT.read_text()
        # The get_max_lanes function should return 2 in CI mode
        assert "echo 2" in content, "CI mode should return 2 for max lanes"

    def test_beefy_machine_runs_5_lanes(self) -> None:
        """Machines with 32GB+ free memory and 8+ cores should run 5 lanes."""
        content = PRE_PUSH_SCRIPT.read_text()
        assert "echo 5" in content, "Beefy machines should run all 5 lanes in parallel"

    def test_sequential_fallback_env_var_supported(self) -> None:
        """PRE_PUSH_SEQUENTIAL=1 should fall back to standard pre-commit."""
        content = PRE_PUSH_SCRIPT.read_text()
        assert "PRE_PUSH_SEQUENTIAL" in content, "Script must support PRE_PUSH_SEQUENTIAL env var"
        assert "pre-commit run --hook-stage pre-push" in content, (
            "Sequential fallback must call pre-commit run --hook-stage pre-push"
        )

    def test_hook_drift_validation(self) -> None:
        """Script must validate that all pre-push hooks are assigned to lanes."""
        content = PRE_PUSH_SCRIPT.read_text()
        assert "validate_lane_coverage" in content, "Script must include hook drift validation function"
        assert "not assigned to any lane" in content.lower() or "not assigned" in content.lower(), (
            "Drift validation must report unassigned hooks"
        )

    def test_signal_handling_cleanup(self) -> None:
        """Script must trap EXIT/INT/TERM to clean up child processes."""
        content = PRE_PUSH_SCRIPT.read_text()
        assert "trap" in content, "Script must set up signal traps"
        assert "cleanup" in content, "Script must define a cleanup function"

    def test_durable_lane_logs(self) -> None:
        """Lane logs must persist at a well-known path for post-hoc diagnosis."""
        content = PRE_PUSH_SCRIPT.read_text()
        assert "/tmp/pre-push-lanes" in content, "Logs must use durable /tmp/pre-push-lanes/ directory"
        # cleanup() must NOT delete logs (they're for post-hoc diagnosis)
        # Extract the cleanup function body and verify no rm -rf
        cleanup_start = content.index("cleanup()")
        cleanup_end = content.index("trap cleanup", cleanup_start)
        cleanup_body = content[cleanup_start:cleanup_end]
        assert "rm -rf" not in cleanup_body, "cleanup() must NOT delete lane logs"

    def test_pre_commit_home_isolation(self) -> None:
        """Each lane must use isolated PRE_COMMIT_HOME to prevent cache corruption."""
        content = PRE_PUSH_SCRIPT.read_text()
        assert "PRE_COMMIT_HOME" in content, "Script must set per-lane PRE_COMMIT_HOME for cache isolation"
        assert "pre-commit-lane-" in content, "Lane cache directories must use 'pre-commit-lane-' prefix"

    def test_dry_run_mode(self) -> None:
        """Dry-run mode should output lane configuration."""
        result = subprocess.run(
            ["bash", str(PRE_PUSH_SCRIPT)],
            env={
                "PRE_PUSH_DRY_RUN": "1",
                "FROM_REF": "HEAD~1",
                "TO_REF": "HEAD",
                "PATH": "/usr/bin:/bin:/usr/local/bin",
                "HOME": str(Path.home()),
            },
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        # Dry-run may fail if PyYAML not available for drift check, which is OK
        assert "max_lanes" in result.stdout, f"Dry-run output should include max_lanes. stdout: {result.stdout[:500]}"

    def test_ci_dry_run_shows_2_lanes(self) -> None:
        """CI dry-run should show max_lanes=2."""
        result = subprocess.run(
            ["bash", str(PRE_PUSH_SCRIPT)],
            env={
                "PRE_PUSH_DRY_RUN": "1",
                "CI": "true",
                "FROM_REF": "HEAD~1",
                "TO_REF": "HEAD",
                "PATH": "/usr/bin:/bin:/usr/local/bin",
                "HOME": str(Path.home()),
            },
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        assert "max_lanes=2" in result.stdout, f"CI mode should show max_lanes=2. stdout: {result.stdout[:500]}"

    def test_ref_parsing_fallback(self) -> None:
        """Script should fall back to HEAD~1..HEAD when no stdin refs available."""
        content = PRE_PUSH_SCRIPT.read_text()
        assert "HEAD~1" in content, "Script must have HEAD~1 fallback for FROM_REF"
        assert "HEAD" in content, "Script must have HEAD fallback for TO_REF"

    def test_per_lane_exit_code_tracking(self) -> None:
        """Script must track exit codes per lane for summary reporting."""
        content = PRE_PUSH_SCRIPT.read_text()
        assert "exit_code" in content.lower() or "exit_codes" in content.lower(), "Script must track per-lane exit codes"

    def test_overall_nonzero_exit_on_lane_failure(self) -> None:
        """Overall exit code must be nonzero if any lane fails."""
        content = PRE_PUSH_SCRIPT.read_text()
        assert "overall_exit=1" in content or "overall_exit = 1" in content, (
            "Script must set nonzero overall exit code on lane failure"
        )

    def test_frontend_lane_reduces_shard_concurrency(self) -> None:
        """Frontend lane must cap shard concurrency to prevent OOM when running in parallel.

        When the orchestrator runs all 5 lanes concurrently, the frontend shard runner
        must not use its default concurrency (8) because Python tests are also consuming
        CPU and memory. The orchestrator should set VITEST_SHARD_CONCURRENCY_MAX to a
        reduced value (1/6 of standalone, min 2) for the frontend lane.
        """
        content = PRE_PUSH_SCRIPT.read_text()
        assert "VITEST_SHARD_CONCURRENCY_MAX" in content, (
            "Orchestrator must set VITEST_SHARD_CONCURRENCY_MAX for frontend lane "
            "to prevent OOM when running concurrently with Python tests"
        )
        assert "/ 6" in content or "/6" in content, (
            "Frontend shard concurrency must be reduced to 1/6 of standalone limit "
            "when running in parallel (12/6=2 shards fits within memory budget)"
        )

    def test_git_index_file_isolation_per_lane(self) -> None:
        """Each lane must use isolated GIT_INDEX_FILE to prevent index.lock contention."""
        content = PRE_PUSH_SCRIPT.read_text()
        assert "GIT_INDEX_FILE" in content, "Script must set per-lane GIT_INDEX_FILE for index isolation"
        assert ".git-index-" in content, "Lane index files must use '.git-index-' prefix"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
