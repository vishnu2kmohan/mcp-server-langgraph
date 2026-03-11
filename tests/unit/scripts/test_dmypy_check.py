"""
Tests for dmypy_check.sh - MyPy Daemon Wrapper.

Validates:
1. CI mode uses standard mypy (not dmypy daemon)
2. Local mode uses dmypy for incremental checking
3. Stale lockfile recovery (kill + retry) logic is present
"""

from __future__ import annotations


import pytest

from tests.helpers.path_helpers import get_repo_root

pytestmark = [pytest.mark.unit]

PROJECT_ROOT = get_repo_root()
DMYPY_SCRIPT = PROJECT_ROOT / "scripts" / "hooks" / "dmypy_check.sh"


class TestDmypyCheckScript:
    """Tests for the dmypy_check.sh hook wrapper."""

    def test_script_exists_at_expected_path(self) -> None:
        """dmypy_check.sh must exist at the expected location."""
        assert DMYPY_SCRIPT.exists(), f"scripts/hooks/dmypy_check.sh not found at {DMYPY_SCRIPT}"

    def test_script_is_executable(self) -> None:
        """dmypy_check.sh must be executable."""
        assert DMYPY_SCRIPT.stat().st_mode & 0o111, "scripts/hooks/dmypy_check.sh is not executable"

    def test_ci_mode_uses_standard_mypy(self) -> None:
        """In CI mode, the script should invoke standard mypy (not dmypy)."""
        content = DMYPY_SCRIPT.read_text()
        # Must check for CI env var
        assert "CI" in content, "Script must check CI environment variable"
        # Must have a code path that calls mypy (not dmypy)
        assert "uv run --frozen mypy" in content, "CI path must use standard 'uv run --frozen mypy'"

    def test_local_mode_uses_dmypy(self) -> None:
        """In local mode, the script should use dmypy for incremental checking."""
        content = DMYPY_SCRIPT.read_text()
        assert "dmypy check" in content, "Local path must use 'dmypy check' for incremental type checking"
        assert "dmypy start" in content, "Local path must start dmypy daemon if not running"

    def test_stale_lockfile_recovery(self) -> None:
        """Script must handle stale lockfile by killing daemon and retrying."""
        content = DMYPY_SCRIPT.read_text()
        assert "dmypy kill" in content, "Script must handle stale lockfile recovery via 'dmypy kill'"
        # Should mention stale lockfile in a comment or message
        assert "stale" in content.lower(), "Script should document stale lockfile recovery logic"

    def test_uses_project_config(self) -> None:
        """Script must use project mypy config (pyproject.toml)."""
        content = DMYPY_SCRIPT.read_text()
        assert "--config-file=pyproject.toml" in content, "Script must pass --config-file=pyproject.toml to mypy/dmypy"

    def test_show_error_codes(self) -> None:
        """Script must enable error codes for actionable output."""
        content = DMYPY_SCRIPT.read_text()
        assert "--show-error-codes" in content, "Script must pass --show-error-codes for actionable diagnostics"

    def test_github_actions_detection(self) -> None:
        """Script should also detect GITHUB_ACTIONS env var for CI mode."""
        content = DMYPY_SCRIPT.read_text()
        assert "GITHUB_ACTIONS" in content, "Script should detect GITHUB_ACTIONS env var for CI mode"

    def test_dmypy_check_does_not_pass_mypy_flags(self) -> None:
        """dmypy check must NOT pass mypy flags via '--' (they are treated as filenames).

        The dmypy check subcommand only accepts file/directory positional args.
        Config flags (--config-file, --show-error-codes, --pretty) must be set
        during 'dmypy start', not during 'dmypy check'.
        """
        content = DMYPY_SCRIPT.read_text()
        # Find the dmypy check line(s)
        lines = content.splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if "dmypy check" in stripped and "dmypy start" not in stripped:
                # Get the full command (may span multiple lines with backslash continuation)
                full_cmd = stripped
                j = i
                while full_cmd.endswith("\\") and j + 1 < len(lines):
                    j += 1
                    full_cmd += " " + lines[j].strip()
                # dmypy check should NOT have -- followed by mypy flags
                assert "-- " not in full_cmd and "-- \\" not in full_cmd, (
                    f"dmypy check must not pass mypy flags via '--'. "
                    f"Found: {full_cmd!r}. "
                    f"Fix: pass --config-file, --show-error-codes, --pretty to 'dmypy start' instead."
                )

    def test_dmypy_start_includes_all_mypy_flags(self) -> None:
        """dmypy start must include all mypy flags (config, error codes, pretty)."""
        content = DMYPY_SCRIPT.read_text()
        # Find executable dmypy start lines (not comments or echo statements)
        lines = content.splitlines()
        start_cmds = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Skip comments and echo/print statements
            if stripped.startswith("#") or stripped.startswith("echo "):
                continue
            if "dmypy start" in stripped:
                full_cmd = stripped
                j = i
                while full_cmd.endswith("\\") and j + 1 < len(lines):
                    j += 1
                    full_cmd += " " + lines[j].strip()
                start_cmds.append(full_cmd)
        assert len(start_cmds) > 0, "Script must have executable dmypy start commands"
        # At least one start command must include all flags
        has_all_flags = any(
            "--config-file=pyproject.toml" in cmd and "--show-error-codes" in cmd and "--pretty" in cmd for cmd in start_cmds
        )
        assert has_all_flags, (
            f"At least one dmypy start command must include --config-file, --show-error-codes, --pretty. Found: {start_cmds}"
        )

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
