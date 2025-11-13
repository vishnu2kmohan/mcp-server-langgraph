"""
Meta-validation: Ensure local validation matches CI validation exactly.

This test suite ensures that:
1. Pre-push hooks exist and have correct permissions
2. Pre-push hooks contain all required validation steps
3. Makefile targets match pre-push hook validation
4. Local validation steps match CI validation steps
5. No validation gaps exist between local and CI environments

TDD Principle: These tests MUST pass to ensure developers never experience CI surprises.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Set

import pytest
import yaml


class TestPrePushHookConfiguration:
    """Validate pre-push hook is configured correctly."""

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root directory."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def pre_push_hook_path(self, repo_root: Path) -> Path:
        """Get path to pre-push hook."""
        return repo_root / ".git" / "hooks" / "pre-push"

    def test_pre_push_hook_exists(self, pre_push_hook_path: Path):
        """Test that pre-push hook file exists."""
        assert pre_push_hook_path.exists(), (
            "Pre-push hook does not exist at .git/hooks/pre-push\n"
            "Run 'make git-hooks' or 'pre-commit install --hook-type pre-push'"
        )

    def test_pre_push_hook_is_executable(self, pre_push_hook_path: Path):
        """Test that pre-push hook has execute permissions."""
        assert os.access(pre_push_hook_path, os.X_OK), (
            f"Pre-push hook exists but is not executable: {pre_push_hook_path}\n" f"Fix: chmod +x {pre_push_hook_path}"
        )

    def test_pre_push_hook_is_bash_script(self, pre_push_hook_path: Path):
        """Test that pre-push hook is a bash script."""
        with open(pre_push_hook_path, "r") as f:
            first_line = f.readline().strip()

        assert first_line in [
            "#!/bin/bash",
            "#!/usr/bin/env bash",
        ], f"Pre-push hook must be a bash script, got shebang: {first_line}"

    def test_pre_push_hook_validates_lockfile(self, pre_push_hook_path: Path):
        """Test that pre-push hook validates lockfile."""
        with open(pre_push_hook_path, "r") as f:
            content = f.read()

        assert "uv lock --check" in content, (
            "Pre-push hook must validate lockfile with 'uv lock --check'\n"
            "This prevents out-of-sync lockfiles from being pushed"
        )

    def test_pre_push_hook_validates_workflows(self, pre_push_hook_path: Path):
        """Test that pre-push hook validates GitHub workflows."""
        with open(pre_push_hook_path, "r") as f:
            content = f.read()

        required_workflow_tests = [
            "test_workflow_syntax.py",
            "test_workflow_security.py",
            "test_workflow_dependencies.py",
            "test_docker_paths.py",
        ]

        for test_file in required_workflow_tests:
            assert test_file in content, (
                f"Pre-push hook must run workflow validation test: {test_file}\n"
                f"This prevents workflow errors from reaching CI"
            )

    def test_pre_push_hook_runs_mypy(self, pre_push_hook_path: Path):
        """Test that pre-push hook runs MyPy type checking."""
        with open(pre_push_hook_path, "r") as f:
            content = f.read()

        assert "mypy src/mcp_server_langgraph" in content, (
            "Pre-push hook must run MyPy type checking\n" "This catches type errors before CI"
        )

        # MyPy should be non-blocking (warning only)
        assert "false" in content or "non-blocking" in content.lower(), "MyPy should be non-blocking in pre-push hook"

    def test_pre_push_hook_runs_precommit_all_files(self, pre_push_hook_path: Path):
        """Test that pre-push hook runs pre-commit on ALL files."""
        with open(pre_push_hook_path, "r") as f:
            content = f.read()

        assert "pre-commit run --all-files" in content, (
            "Pre-push hook must run 'pre-commit run --all-files'\n" "Running on changed files only causes CI surprises"
        )

    def test_pre_push_hook_runs_property_tests_with_ci_profile(self, pre_push_hook_path: Path):
        """Test that pre-push hook runs property tests with CI profile."""
        with open(pre_push_hook_path, "r") as f:
            content = f.read()

        assert "HYPOTHESIS_PROFILE=ci" in content, (
            "Pre-push hook must set HYPOTHESIS_PROFILE=ci for property tests\n"
            "Local uses 25 examples, CI uses 100 - this prevents CI-only failures"
        )

        assert "pytest -m property" in content or "pytest.*property" in content, "Pre-push hook must run property tests"

    def test_pre_push_hook_has_clear_phases(self, pre_push_hook_path: Path):
        """Test that pre-push hook has clearly defined validation phases."""
        with open(pre_push_hook_path, "r") as f:
            content = f.read()

        expected_phases = [
            "PHASE 1",  # Fast checks
            "PHASE 2",  # Type checking
            "PHASE 3",  # Pre-commit hooks
            "PHASE 4",  # Property tests
        ]

        for phase in expected_phases:
            assert phase in content, f"Pre-push hook should have clearly labeled {phase} for readability"

    def test_pre_push_hook_provides_helpful_error_messages(self, pre_push_hook_path: Path):
        """Test that pre-push hook provides helpful troubleshooting info."""
        with open(pre_push_hook_path, "r") as f:
            content = f.read()

        # Should mention how to bypass (for emergencies)
        assert "--no-verify" in content, "Pre-push hook should document emergency bypass with --no-verify"

        # Should provide fix instructions
        assert "To fix" in content or "Fix:" in content, "Pre-push hook should provide troubleshooting instructions"


class TestMakefileValidationTarget:
    """Validate Makefile validate-pre-push target."""

    @pytest.fixture
    def makefile_path(self) -> Path:
        """Get path to Makefile."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip()) / "Makefile"

    @pytest.fixture
    def makefile_content(self, makefile_path: Path) -> str:
        """Read Makefile content."""
        with open(makefile_path, "r") as f:
            return f.read()

    def test_validate_pre_push_target_exists(self, makefile_content: str):
        """Test that validate-pre-push target exists in Makefile."""
        assert re.search(r"^validate-pre-push:", makefile_content, re.MULTILINE), (
            "Makefile must have 'validate-pre-push' target\n" "This provides manual validation matching pre-push hook"
        )

    def test_validate_pre_push_in_phony_targets(self, makefile_content: str):
        """Test that validate-pre-push is declared as .PHONY."""
        # Extract .PHONY line
        phony_match = re.search(r"^\.PHONY:.*$", makefile_content, re.MULTILINE)
        assert phony_match, "Makefile should have .PHONY declaration"

        phony_line = phony_match.group(0)
        assert "validate-pre-push" in phony_line, "validate-pre-push must be declared in .PHONY targets"

    def test_validate_pre_push_runs_lockfile_check(self, makefile_content: str):
        """Test that validate-pre-push target validates lockfile."""
        # Find validate-pre-push target section
        target_match = re.search(
            r"^validate-pre-push:.*?(?=^[a-zA-Z]|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )
        assert target_match, "Could not find validate-pre-push target"

        target_content = target_match.group(0)
        assert "uv lock --check" in target_content, "validate-pre-push target must run 'uv lock --check'"

    def test_validate_pre_push_runs_workflow_tests(self, makefile_content: str):
        """Test that validate-pre-push target runs workflow validation tests."""
        target_match = re.search(
            r"^validate-pre-push:.*?(?=^[a-zA-Z]|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )
        assert target_match, "Could not find validate-pre-push target"

        target_content = target_match.group(0)

        required_tests = [
            "test_workflow_syntax.py",
            "test_workflow_security.py",
            "test_workflow_dependencies.py",
            "test_docker_paths.py",
        ]

        for test in required_tests:
            assert test in target_content, f"validate-pre-push must run {test}"

    def test_validate_pre_push_runs_mypy(self, makefile_content: str):
        """Test that validate-pre-push target runs MyPy."""
        target_match = re.search(
            r"^validate-pre-push:.*?(?=^[a-zA-Z]|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )
        assert target_match, "Could not find validate-pre-push target"

        target_content = target_match.group(0)
        assert "mypy src/mcp_server_langgraph" in target_content, "validate-pre-push must run MyPy type checking"

    def test_validate_pre_push_runs_precommit_all_files(self, makefile_content: str):
        """Test that validate-pre-push runs pre-commit on all files."""
        target_match = re.search(
            r"^validate-pre-push:.*?(?=^[a-zA-Z]|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )
        assert target_match, "Could not find validate-pre-push target"

        target_content = target_match.group(0)
        assert "pre-commit run --all-files" in target_content, "validate-pre-push must run 'pre-commit run --all-files'"

    def test_validate_pre_push_runs_property_tests_with_ci_profile(self, makefile_content: str):
        """Test that validate-pre-push runs property tests with CI profile."""
        target_match = re.search(
            r"^validate-pre-push:.*?(?=^[a-zA-Z]|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )
        assert target_match, "Could not find validate-pre-push target"

        target_content = target_match.group(0)
        assert "HYPOTHESIS_PROFILE=ci" in target_content, "validate-pre-push must set HYPOTHESIS_PROFILE=ci"

        assert "-m property" in target_content, "validate-pre-push must run property tests"

    def test_validate_pre_push_in_help_output(self, makefile_content: str):
        """Test that validate-pre-push is documented in help target."""
        # Find help or help-common target
        help_match = re.search(
            r"^help(-common)?:.*?(?=^[a-zA-Z]|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )
        assert help_match, "Could not find help target"

        help_content = help_match.group(0)
        assert "validate-pre-push" in help_content, "validate-pre-push should be documented in make help output"


class TestLocalCIParity:
    """Validate that local validation matches CI validation."""

    @pytest.fixture
    def ci_workflow_path(self) -> Path:
        """Get path to main CI workflow."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        repo_root = Path(result.stdout.strip())
        return repo_root / ".github" / "workflows" / "ci.yaml"

    @pytest.fixture
    def ci_workflow(self, ci_workflow_path: Path) -> dict:
        """Load CI workflow YAML."""
        with open(ci_workflow_path, "r") as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def pre_push_hook_path(self) -> Path:
        """Get path to pre-push hook."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        repo_root = Path(result.stdout.strip())
        return repo_root / ".git" / "hooks" / "pre-push"

    @pytest.fixture
    def pre_push_content(self, pre_push_hook_path: Path) -> str:
        """Read pre-push hook content."""
        with open(pre_push_hook_path, "r") as f:
            return f.read()

    def test_lockfile_validation_matches_ci(self, ci_workflow: dict, pre_push_content: str):
        """Test that lockfile validation command matches CI."""
        # CI should run uv lock --check
        ci_content = yaml.dump(ci_workflow)

        if "uv lock --check" in ci_content or "uv sync --frozen" in ci_content:
            # Local pre-push should also check lockfile
            assert "uv lock --check" in pre_push_content, "Local pre-push must validate lockfile like CI does"

    def test_precommit_scope_matches_ci(self, ci_workflow: dict, pre_push_content: str):
        """Test that pre-commit scope matches CI (all files)."""
        ci_content = yaml.dump(ci_workflow)

        if "pre-commit run" in ci_content:
            # CI runs on all files
            if "--all-files" in ci_content:
                assert "--all-files" in pre_push_content, (
                    "Local pre-push must run pre-commit on all files like CI does\n"
                    "Running on changed files only causes CI surprises"
                )

    def test_hypothesis_profile_matches_ci(self, ci_workflow: dict, pre_push_content: str):
        """Test that Hypothesis profile matches CI."""
        ci_content = yaml.dump(ci_workflow)

        if "HYPOTHESIS_PROFILE" in ci_content:
            # Extract CI profile
            if "HYPOTHESIS_PROFILE=ci" in ci_content or "HYPOTHESIS_PROFILE: ci" in ci_content:
                assert "HYPOTHESIS_PROFILE=ci" in pre_push_content, (
                    "Local pre-push must use same Hypothesis profile as CI\n"
                    "CI uses 100 examples, local dev uses 25 - this causes failures"
                )

    def test_workflow_validation_matches_ci(self, ci_workflow: dict, pre_push_content: str):
        """Test that workflow validation tests match what CI runs."""
        # CI has workflow validation job
        jobs = ci_workflow.get("jobs", {})

        workflow_validation_jobs = [
            job_name
            for job_name, job_config in jobs.items()
            if "workflow" in job_name.lower() or "actionlint" in str(job_config).lower()
        ]

        if workflow_validation_jobs:
            # Local should also validate workflows
            assert "test_workflow" in pre_push_content, "Local pre-push should validate workflows like CI does"


class TestCIGapPrevention:
    """Tests to prevent CI validation gaps from being introduced."""

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())

    def test_ci_workflow_has_validation_job(self, repo_root: Path):
        """Test that CI workflow has comprehensive validation."""
        ci_path = repo_root / ".github" / "workflows" / "ci.yaml"

        with open(ci_path, "r") as f:
            ci_content = yaml.safe_load(f)

        jobs = ci_content.get("jobs", {})

        # Should have pre-commit or validation job
        validation_jobs = [
            job for job in jobs.keys() if any(keyword in job.lower() for keyword in ["pre-commit", "validate", "lint"])
        ]

        assert validation_jobs, "CI workflow should have validation/pre-commit/lint job"

    def test_contributing_docs_mention_validate_pre_push(self, repo_root: Path):
        """Test that CONTRIBUTING.md documents validate-pre-push."""
        contributing_path = repo_root / "CONTRIBUTING.md"

        with open(contributing_path, "r") as f:
            content = f.read()

        assert "validate-pre-push" in content, "CONTRIBUTING.md should document validate-pre-push requirement"

        assert "make validate-pre-push" in content, "CONTRIBUTING.md should show the command to run"

    def test_readme_or_quickstart_mentions_validation(self, repo_root: Path):
        """Test that quick start documentation mentions validation."""
        readme_path = repo_root / "README.md"

        if readme_path.exists():
            with open(readme_path, "r") as f:
                content = f.read()

            # Should mention validation or testing before push
            validation_keywords = ["validate", "pre-push", "before push", "CI"]
            has_validation_info = any(keyword in content for keyword in validation_keywords)

            # Not strictly required in README, but good practice
            # So this is informational rather than blocking
            if not has_validation_info:
                pytest.skip("README doesn't mention validation (optional)")


class TestRegressionPrevention:
    """Tests to ensure validation doesn't regress over time."""

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())

    def test_this_test_file_runs_in_ci(self, repo_root: Path):
        """Meta-test: Ensure this test file itself runs in CI."""
        ci_path = repo_root / ".github" / "workflows" / "ci.yaml"

        with open(ci_path, "r") as f:
            ci_content = f.read()

        # This test file should be covered by pytest runs in CI
        # CI should run tests that include meta tests
        assert "pytest" in ci_content, "CI should run pytest"

        # Even better if it specifically mentions meta tests
        # But not required - general pytest run should cover it

    def test_pre_push_hook_is_version_controlled_or_documented(self, repo_root: Path):
        """Test that pre-push hook setup is documented."""
        # .git/hooks/pre-push is not version controlled
        # But there should be documentation on how to set it up

        contributing_path = repo_root / "CONTRIBUTING.md"

        with open(contributing_path, "r") as f:
            content = f.read()

        # Should document hook setup
        setup_keywords = ["git-hooks", "pre-commit install", "hook setup"]
        has_setup_docs = any(keyword in content.lower() for keyword in setup_keywords)

        assert has_setup_docs, "CONTRIBUTING.md should document how to set up git hooks"

    def test_minimum_validation_steps_documented(self, repo_root: Path):
        """Test that minimum required validation steps are documented."""
        contributing_path = repo_root / "CONTRIBUTING.md"

        with open(contributing_path, "r") as f:
            content = f.read()

        # Key validation steps that must be documented
        required_steps = [
            "lockfile",  # Lockfile validation
            "pre-commit",  # Pre-commit hooks
            "workflow",  # Workflow validation
        ]

        for step in required_steps:
            assert step.lower() in content.lower(), f"CONTRIBUTING.md should document '{step}' validation"
