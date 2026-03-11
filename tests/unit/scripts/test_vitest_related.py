"""
Tests for vitest --related integration in frontend-test pre-push hook.

Validates:
1. Falls back to full suite when config files changed
2. Falls back when upstream is unset (first push)
3. Uses --related for small changesets (<= 10 files)
4. Falls back to full suite for large changesets (> 10 files)

These tests validate the hook entry in .pre-commit-config.yaml rather than
a standalone script, so they check the config content directly.
"""

from __future__ import annotations


import pytest
import yaml

from tests.helpers.path_helpers import get_repo_root

pytestmark = [pytest.mark.unit]

PROJECT_ROOT = get_repo_root()
PRE_COMMIT_CONFIG = PROJECT_ROOT / ".pre-commit-config.yaml"


def get_frontend_test_hook() -> dict | None:
    """Extract the frontend-test hook entry from .pre-commit-config.yaml."""
    with open(PRE_COMMIT_CONFIG) as f:
        config = yaml.safe_load(f)

    for repo in config.get("repos", []):
        for hook in repo.get("hooks", []):
            if hook.get("id") == "frontend-test":
                return hook
    return None


class TestVitestRelatedHook:
    """Tests for the vitest --related integration in frontend-test hook."""

    def test_pre_commit_config_exists(self) -> None:
        """.pre-commit-config.yaml must exist."""
        assert PRE_COMMIT_CONFIG.exists()

    def test_frontend_test_hook_exists(self) -> None:
        """frontend-test hook must be defined in .pre-commit-config.yaml."""
        hook = get_frontend_test_hook()
        assert hook is not None, "frontend-test hook not found in .pre-commit-config.yaml"

    def test_hook_uses_vitest_related(self) -> None:
        """Hook entry must use vitest --related for small changesets."""
        hook = get_frontend_test_hook()
        assert hook is not None
        entry = hook.get("entry", "")
        assert "--related" in entry, "frontend-test hook must use 'vitest --related' for small changesets"

    def test_hook_detects_upstream_tracking(self) -> None:
        """Hook must detect whether upstream tracking branch exists."""
        hook = get_frontend_test_hook()
        assert hook is not None
        entry = hook.get("entry", "")
        assert "@{push}" in entry, "Hook must use @{push} to detect upstream tracking branch"

    def test_hook_falls_back_on_no_upstream(self) -> None:
        """Hook must fall back to full suite when no upstream tracking branch."""
        hook = get_frontend_test_hook()
        assert hook is not None
        entry = hook.get("entry", "")
        assert "first push" in entry.lower() or "no upstream" in entry.lower(), (
            "Hook must handle first-push (no upstream) case"
        )

    def test_hook_falls_back_on_config_change(self) -> None:
        """Hook must fall back to full suite when config files changed."""
        hook = get_frontend_test_hook()
        assert hook is not None
        entry = hook.get("entry", "")
        # Must check for config file changes
        for config_file in ["package.json", "vite.config.ts", "vitest.config.ts", "tsconfig.json"]:
            assert config_file in entry, f"Hook must detect changes to {config_file} for full-suite fallback"

    def test_hook_has_file_count_threshold(self) -> None:
        """Hook must have a file count threshold (10) for switching to full suite."""
        hook = get_frontend_test_hook()
        assert hook is not None
        entry = hook.get("entry", "")
        assert "10" in entry, "Hook must have file count threshold of 10 for --related vs full suite"

    def test_hook_is_pre_push_stage(self) -> None:
        """frontend-test hook must be at pre-push stage."""
        hook = get_frontend_test_hook()
        assert hook is not None
        stages = hook.get("stages", [])
        assert "pre-push" in stages, "frontend-test hook must run at pre-push stage"

    def test_hook_filters_frontend_files(self) -> None:
        """Hook must only trigger on frontend source files."""
        hook = get_frontend_test_hook()
        assert hook is not None
        files_pattern = hook.get("files", "")
        assert "frontend" in files_pattern, "Hook must filter for frontend source files"
        assert "ts" in files_pattern, "Hook must filter for TypeScript files (ts/tsx in regex pattern)"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
