"""
Test suite for validating .gitignore patterns and preventing local config commits.

This test module ensures that personal/local configuration files are never
accidentally committed to version control, following security and collaboration
best practices.
"""

import gc
import subprocess
from pathlib import Path
from typing import List, Set

import pytest


# Mark this as both unit and meta test to ensure it runs in CI
pytestmark = [pytest.mark.unit, pytest.mark.meta]


@pytest.mark.xdist_group(name="testgitignorevalidation")
class TestGitignoreValidation:
    """Validate .gitignore patterns and tracked files."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @staticmethod
    def get_tracked_files() -> set[str]:
        """Get all files tracked by git."""
        result = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True, timeout=60)
        return set(result.stdout.strip().split("\n"))

    @staticmethod
    def get_gitignore_patterns() -> list[str]:
        """Read .gitignore patterns."""
        gitignore_path = Path(".gitignore")
        if not gitignore_path.exists():
            return []

        patterns = []
        with open(gitignore_path) as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith("#"):
                    patterns.append(line)
        return patterns

    def test_no_local_config_files_tracked(self):
        """
        CRITICAL: Verify no .local. files are tracked in git.

        Files matching *.local.* pattern should never be committed as they
        contain personal preferences and machine-specific configurations.
        """
        tracked = self.get_tracked_files()
        local_files = [f for f in tracked if ".local." in f]

        assert not local_files, (
            f"Found {len(local_files)} .local. files tracked in git:\n"
            + "\n".join(f"  - {f}" for f in local_files)
            + "\n\nThese files should be in .gitignore!"
        )

    def test_no_claude_settings_local_tracked(self):
        """
        CRITICAL: Verify .claude/settings.local.json is not tracked.

        According to Claude Code documentation, settings.local.json should
        never be committed to version control.
        """
        tracked = self.get_tracked_files()
        settings_local_files = [f for f in tracked if f.endswith("settings.local.json")]

        assert not settings_local_files, (
            "Found settings.local.json files tracked in git:\n"
            + "\n".join(f"  - {f}" for f in settings_local_files)
            + "\n\nPer Claude Code docs, these should NEVER be committed!"
        )

    def test_gitignore_has_local_patterns(self):
        """
        Verify .gitignore contains patterns to exclude .local. files.
        """
        patterns = self.get_gitignore_patterns()

        # Check for various .local. patterns
        has_local_json = any("*.local.json" in p for p in patterns)
        has_settings_local = any("settings.local.json" in p for p in patterns)

        assert has_local_json or has_settings_local, (
            ".gitignore should contain patterns like:\n"
            "  *.local.json\n"
            "  **/*.local.json\n"
            "  .claude/settings.local.json"
        )

    def test_no_env_local_files_tracked(self):
        """
        Verify no .env.local or .env.*.local files are tracked.

        These contain environment-specific secrets and should never be committed.
        """
        tracked = self.get_tracked_files()
        env_local_files = [f for f in tracked if ".env.local" in f or ".env." in f and ".local" in f]

        assert not env_local_files, (
            "Found .env.local files tracked in git:\n"
            + "\n".join(f"  - {f}" for f in env_local_files)
            + "\n\nThese contain secrets and should NEVER be committed!"
        )

    def test_no_personal_ide_configs_tracked(self):
        """
        Verify personal IDE configuration files are not tracked.

        Files like .vscode/settings.json should be local to each developer.
        """
        tracked = self.get_tracked_files()
        personal_configs = [
            f
            for f in tracked
            if any(
                pattern in f
                for pattern in [
                    ".vscode/settings.json",
                    ".idea/workspace.xml",
                    "*.code-workspace",
                ]
            )
        ]

        assert not personal_configs, (
            "Found personal IDE configs tracked in git:\n"
            + "\n".join(f"  - {f}" for f in personal_configs)
            + "\n\nThese are user-specific and should be gitignored!"
        )

    def test_gitignore_exists_and_valid(self):
        """Verify .gitignore file exists and is valid."""
        gitignore_path = Path(".gitignore")
        assert gitignore_path.exists(), ".gitignore file must exist"

        patterns = self.get_gitignore_patterns()
        assert len(patterns) > 0, ".gitignore should contain patterns"

    def test_no_backup_files_tracked(self):
        """Verify no backup files (*.bak, *.backup) are tracked."""
        tracked = self.get_tracked_files()
        backup_files = [f for f in tracked if f.endswith((".bak", ".backup", ".tmp", ".temp"))]

        assert not backup_files, "Found backup/temp files tracked in git:\n" + "\n".join(f"  - {f}" for f in backup_files)


@pytest.mark.xdist_group(name="testgitignorecomprehensiveness")
class TestGitignoreComprehensiveness:
    """Test that .gitignore covers all necessary patterns."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_has_python_patterns(self):
        """Verify .gitignore has Python-specific patterns."""
        gitignore_path = Path(".gitignore")
        content = gitignore_path.read_text()

        required_patterns = [
            "__pycache__",
            "*.pyc",
            ".pytest_cache",
            ".coverage",
            ".mypy_cache",
        ]

        for pattern in required_patterns:
            assert pattern in content, f"Missing Python pattern '{pattern}' in .gitignore"

    def test_has_secret_patterns(self):
        """Verify .gitignore excludes secret files."""
        gitignore_path = Path(".gitignore")
        content = gitignore_path.read_text()

        required_patterns = [
            ".env",
            "*.pem",
            "*.key",
        ]

        for pattern in required_patterns:
            assert pattern in content, f"Missing secret pattern '{pattern}' in .gitignore"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
