"""
Test Pre-Commit Hook Cross-Platform Compatibility

This test validates that pre-commit hooks are compatible with all platforms
(Linux, macOS, Windows) and all shells (bash, zsh, fish, PowerShell).

Background:
Some hooks were using `bash -c 'source .venv/bin/activate && pytest ...'` which:
1. Only works on bash (not sh, zsh, fish, PowerShell)
2. Only works on Unix (.venv/bin/activate doesn't exist on Windows)
3. Assumes .venv exists and is activated

Related Issues:
- Finding F: Two pre-push hooks use bash -c instead of uv run
- Cross-platform CI failures on Windows runners
"""

import gc
import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.meta


@pytest.mark.xdist_group(name="precommit_cross_platform")
class TestPreCommitCrossPlatformCompatibility:
    """Validates pre-commit hooks work across all platforms."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @property
    def precommit_config_path(self) -> Path:
        """Path to .pre-commit-config.yaml."""
        repo_root = Path(__file__).parent.parent.parent
        return repo_root / ".pre-commit-config.yaml"

    def test_precommit_config_file_exists_in_repo_root(self):
        """Verify .pre-commit-config.yaml exists."""
        assert self.precommit_config_path.exists(), f"Pre-commit config not found: {self.precommit_config_path}"

    def test_no_bash_c_source_venv(self):
        """
        CRITICAL: Verify hooks don't use 'bash -c source .venv/bin/activate'.

        This pattern breaks cross-platform compatibility:
        - Windows: .venv/bin/activate doesn't exist (uses Scripts/activate.bat)
        - Fish shell: Uses 'source .venv/bin/activate.fish'
        - PowerShell: Uses .venv/Scripts/Activate.ps1

        The correct approach is to use 'uv run' which handles environments cross-platform.
        """
        with open(self.precommit_config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        problematic_hooks = []

        # Check all repos
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                hook_id = hook.get("id", "unknown")
                entry = hook.get("entry", "")

                # Check for bash -c with source .venv
                if "bash -c" in entry and "source .venv" in entry:
                    problematic_hooks.append(
                        {
                            "id": hook_id,
                            "entry": entry,
                            "repo": repo.get("repo", "local"),
                        }
                    )

                # Also check for direct source .venv (without bash -c)
                if "source .venv" in entry or "source ~/.venv" in entry:
                    problematic_hooks.append(
                        {
                            "id": hook_id,
                            "entry": entry,
                            "repo": repo.get("repo", "local"),
                        }
                    )

        if problematic_hooks:
            error_lines = [
                "Found pre-commit hooks using non-cross-platform virtualenv activation:",
                "",
            ]

            for hook in problematic_hooks:
                error_lines.append(f"Hook: {hook['id']}")
                error_lines.append(f"  Entry: {hook['entry']}")
                error_lines.append(f"  Repo: {hook['repo']}")
                error_lines.append("")

            error_lines.extend(
                [
                    "Problem: 'bash -c source .venv/bin/activate' only works on:",
                    "  - Unix systems (not Windows)",
                    "  - bash shell (not zsh, fish, PowerShell)",
                    "  - When .venv is already created",
                    "",
                    "Fix: Use 'uv run' instead:",
                    "  OLD: bash -c 'source .venv/bin/activate && pytest ...'",
                    "  NEW: uv run pytest ...",
                    "",
                    "Benefits of 'uv run':",
                    "  ✓ Cross-platform (Windows, macOS, Linux)",
                    "  ✓ Shell-agnostic (bash, zsh, fish, PowerShell)",
                    "  ✓ Automatically creates venv if needed",
                    "  ✓ Uses project's exact dependencies via uv.lock",
                ]
            )

            raise AssertionError("\n".join(error_lines))

    def test_python_hooks_use_uv_run(self):
        """
        Verify Python-based hooks use 'uv run' for cross-platform compatibility.

        This ensures hooks work consistently across all environments without
        requiring manual virtualenv activation.
        """
        with open(self.precommit_config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        python_hooks_without_uv = []

        for repo in config.get("repos", []):
            # Skip non-local repos (they manage their own environments)
            if repo.get("repo") != "local":
                continue

            for hook in repo.get("hooks", []):
                hook_id = hook.get("id", "unknown")
                entry = hook.get("entry", "")
                language = hook.get("language", "")

                # If it's a Python script/pytest hook, it should use uv run
                is_python_hook = (
                    "python" in entry.lower() or "pytest" in entry.lower() or language == "python" or language == "system"
                )

                if is_python_hook:
                    # Check if it uses uv run
                    uses_uv_run = "uv run" in entry

                    # Exception: Hooks that just check files (not execute Python)
                    is_file_check = (
                        entry.startswith("bash")
                        and "test -f" in entry
                        or entry.startswith("sh")
                        and "-c" in entry
                        and "test" in entry
                    )

                    if not uses_uv_run and not is_file_check:
                        python_hooks_without_uv.append(
                            {
                                "id": hook_id,
                                "entry": entry,
                                "language": language,
                            }
                        )

        # This is a recommendation, not a hard requirement
        # Some hooks might legitimately not need uv run
        if python_hooks_without_uv:
            # Check if these are the known problematic ones
            known_problematic = [
                hook for hook in python_hooks_without_uv if "bash -c" in hook["entry"] and "source" in hook["entry"]
            ]

            if known_problematic:
                error_lines = [
                    "Found Python hooks that should use 'uv run' for cross-platform compatibility:",
                    "",
                ]

                for hook in known_problematic:
                    error_lines.append(f"Hook: {hook['id']}")
                    error_lines.append(f"  Entry: {hook['entry']}")
                    error_lines.append(f"  Language: {hook['language']}")
                    error_lines.append("")

                error_lines.append("Consider using 'uv run <command>' for consistent environment management.")

                # This is informational for now
                pytest.skip("\n".join(error_lines))

    def test_hooks_dont_hardcode_shell(self):
        """
        Verify hooks don't hardcode specific shells.

        Cross-platform hooks should work in any shell, not just bash.
        """
        with open(self.precommit_config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        shell_hardcoded_hooks = []

        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                hook_id = hook.get("id", "unknown")
                entry = hook.get("entry", "")

                # Check for hardcoded shell invocations (except legitimate uses)
                has_bash_c = re.search(r'\bbash\s+-c\s+["\']', entry)
                has_sh_c = re.search(r'\bsh\s+-c\s+["\']', entry)
                has_zsh_c = re.search(r'\bzsh\s+-c\s+["\']', entry)

                if has_bash_c or has_sh_c or has_zsh_c:
                    # Exception: Legitimate shell scripting (not venv activation)
                    is_legitimate_shell_use = (
                        "uv run" in entry  # Already using uv
                        or "git" in entry  # Git commands
                        or "find" in entry  # File operations
                        or "grep" in entry  # Search operations
                        or "echo" in entry  # Simple output
                    )

                    if not is_legitimate_shell_use:
                        shell_hardcoded_hooks.append(
                            {
                                "id": hook_id,
                                "entry": entry,
                            }
                        )

        if shell_hardcoded_hooks:
            error_lines = [
                "Found hooks with hardcoded shell invocations:",
                "",
                "These may not work across all platforms/shells.",
                "",
            ]

            for hook in shell_hardcoded_hooks:
                error_lines.append(f"Hook: {hook['id']}")
                error_lines.append(f"  Entry: {hook['entry']}")
                error_lines.append("")

            # This is informational, not a failure
            pytest.skip("\n".join(error_lines))

    def test_validate_test_dependencies_hook_uses_uv(self):
        """
        Specific test for validate-test-dependencies hook.

        This was one of the two hooks identified in Finding F that used
        'bash -c source .venv/bin/activate && pytest ...'.
        """
        with open(self.precommit_config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Find the validate-test-dependencies hook
        hook_found = False
        hook_entry = None

        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                if hook.get("id") == "validate-test-dependencies":
                    hook_found = True
                    hook_entry = hook.get("entry", "")
                    break

        if not hook_found:
            pytest.skip("validate-test-dependencies hook not found in config")

        # Should use 'uv run pytest', not 'bash -c source .venv'
        assert "uv run" in hook_entry, (
            f"validate-test-dependencies hook should use 'uv run pytest', not bash -c\n"
            f"Current entry: {hook_entry}\n"
            f"Expected pattern: uv run pytest ..."
        )

        assert "bash -c" not in hook_entry or "source .venv" not in hook_entry, (
            f"validate-test-dependencies hook should not use 'bash -c source .venv'\nCurrent entry: {hook_entry}"
        )

    def test_validate_fixture_scopes_hook_uses_uv(self):
        """
        Specific test for validate-fixture-scopes hook.

        This was the second hook identified in Finding F that used
        'bash -c source .venv/bin/activate && pytest ...'.
        """
        with open(self.precommit_config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Find the validate-fixture-scopes hook
        hook_found = False
        hook_entry = None

        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                if hook.get("id") == "validate-fixture-scopes":
                    hook_found = True
                    hook_entry = hook.get("entry", "")
                    break

        if not hook_found:
            pytest.skip("validate-fixture-scopes hook not found in config")

        # Should use 'uv run pytest', not 'bash -c source .venv'
        assert "uv run" in hook_entry, (
            f"validate-fixture-scopes hook should use 'uv run pytest', not bash -c\n"
            f"Current entry: {hook_entry}\n"
            f"Expected pattern: uv run pytest ..."
        )

        assert "bash -c" not in hook_entry or "source .venv" not in hook_entry, (
            f"validate-fixture-scopes hook should not use 'bash -c source .venv'\nCurrent entry: {hook_entry}"
        )


@pytest.mark.xdist_group(name="precommit_environment_isolation")
class TestPreCommitEnvironmentIsolation:
    """Validates hooks use proper environment isolation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @property
    def precommit_config_path(self) -> Path:
        """Path to .pre-commit-config.yaml."""
        repo_root = Path(__file__).parent.parent.parent
        return repo_root / ".pre-commit-config.yaml"

    def test_hooks_use_consistent_python_environment(self):
        """
        Verify all Python hooks use consistent environment management.

        All Python hooks should either:
        1. Use 'uv run' (recommended for local hooks)
        2. Use language: python with additional_dependencies
        3. Be in a non-local repo (pre-commit manages environment)
        """
        with open(self.precommit_config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        inconsistent_hooks = []

        for repo in config.get("repos", []):
            # Skip non-local repos
            if repo.get("repo") != "local":
                continue

            for hook in repo.get("hooks", []):
                hook_id = hook.get("id", "unknown")
                entry = hook.get("entry", "")
                language = hook.get("language", "")

                # Check if it's a Python hook
                is_python_hook = "pytest" in entry or "python" in entry or language == "python"

                if is_python_hook and language == "system":
                    # System language hooks should use uv run
                    if "uv run" not in entry:
                        inconsistent_hooks.append(
                            {
                                "id": hook_id,
                                "entry": entry,
                                "language": language,
                                "issue": "Uses language: system but not uv run",
                            }
                        )

        # This is informational - the pattern of language:system + uv run is intentional
        if inconsistent_hooks:
            info_lines = [
                "Python hooks with language: system should use 'uv run':",
                "",
            ]

            for hook in inconsistent_hooks:
                info_lines.append(f"Hook: {hook['id']}")
                info_lines.append(f"  {hook['issue']}")
                info_lines.append(f"  Entry: {hook['entry']}")
                info_lines.append("")

            # Don't fail, just inform
            pytest.skip("\n".join(info_lines))
