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

        assert "-m property" in content, "Pre-push hook must run property tests"

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


class TestPytestXdistParity:
    """Validate that local tests use pytest-xdist (-n auto) like CI does.

    CRITICAL: These tests enforce Codex finding #7 - ensure local pre-push runs
    tests in parallel with -n auto to catch pytest-xdist isolation bugs before CI.
    """

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

    @pytest.fixture
    def pre_push_hook_path(self, repo_root: Path) -> Path:
        """Get path to pre-push hook."""
        return repo_root / ".git" / "hooks" / "pre-push"

    @pytest.fixture
    def pre_push_content(self, pre_push_hook_path: Path) -> str:
        """Read pre-push hook content."""
        with open(pre_push_hook_path, "r") as f:
            return f.read()

    @pytest.fixture
    def ci_workflow_path(self, repo_root: Path) -> Path:
        """Get path to CI workflow."""
        return repo_root / ".github" / "workflows" / "ci.yaml"

    @pytest.fixture
    def ci_workflow_content(self, ci_workflow_path: Path) -> str:
        """Read CI workflow content."""
        with open(ci_workflow_path, "r") as f:
            return f.read()

    def test_unit_tests_use_pytest_xdist_n_auto(self, pre_push_content: str):
        """Test that unit tests run with -n auto for parallel execution.

        CRITICAL: Without -n auto, pytest-xdist isolation bugs are only caught in CI.
        This causes "works locally, fails in CI" issues.
        """
        # Find unit test command
        unit_test_pattern = r"uv run pytest.*tests/.*-m.*unit"

        # Check that unit tests exist in pre-push hook
        assert re.search(unit_test_pattern, pre_push_content), (
            "Pre-push hook must run unit tests\n" "Expected pattern: uv run pytest tests/ -m unit"
        )

        # Now check that unit tests use -n auto
        # The pattern should be: pytest -n auto OR pytest tests/ ... -n auto
        unit_test_lines = [
            line for line in pre_push_content.split("\n") if "pytest" in line and "unit" in line and "uv run" in line
        ]

        assert unit_test_lines, "Could not find unit test command in pre-push hook"

        for line in unit_test_lines:
            # Skip comments
            if line.strip().startswith("#"):
                continue

            assert "-n auto" in line, (
                f"Unit tests must use '-n auto' for parallel execution like CI does\n"
                f"Found: {line.strip()}\n"
                f"Expected: uv run pytest -n auto tests/ -m 'unit and not contract'\n"
                f"\n"
                f"Without -n auto:\n"
                f"  - Tests run 2-3x slower locally\n"
                f"  - pytest-xdist isolation bugs only caught in CI\n"
                f"  - 'Works locally, fails in CI' issues\n"
                f"\n"
                f"Fix: Add -n auto to pytest command in .git/hooks/pre-push:~100"
            )

    def test_smoke_tests_use_pytest_xdist_n_auto(self, pre_push_content: str):
        """Test that smoke tests run with -n auto for parallel execution."""
        # Find smoke test command
        smoke_test_lines = [
            line for line in pre_push_content.split("\n") if "pytest" in line and "smoke" in line and "uv run" in line
        ]

        assert smoke_test_lines, "Pre-push hook must run smoke tests"

        for line in smoke_test_lines:
            if line.strip().startswith("#"):
                continue

            assert "-n auto" in line, (
                f"Smoke tests must use '-n auto' for parallel execution\n"
                f"Found: {line.strip()}\n"
                f"Expected: uv run pytest -n auto tests/smoke/\n"
                f"Fix: Add -n auto to pytest command in .git/hooks/pre-push:~104"
            )

    def test_integration_tests_use_pytest_xdist_n_auto(self, pre_push_content: str):
        """Test that integration tests run with -n auto for parallel execution."""
        # Find integration test command
        integration_test_lines = [
            line for line in pre_push_content.split("\n") if "pytest" in line and "integration" in line and "uv run" in line
        ]

        assert integration_test_lines, "Pre-push hook must run integration tests"

        for line in integration_test_lines:
            if line.strip().startswith("#"):
                continue

            assert "-n auto" in line, (
                f"Integration tests must use '-n auto' for parallel execution\n"
                f"Found: {line.strip()}\n"
                f"Expected: uv run pytest -n auto tests/integration/ --lf\n"
                f"Fix: Add -n auto to pytest command in .git/hooks/pre-push:~108"
            )

    def test_property_tests_use_pytest_xdist_n_auto(self, pre_push_content: str):
        """Test that property tests run with -n auto for parallel execution."""
        # Find property test command
        property_test_lines = [
            line for line in pre_push_content.split("\n") if "pytest" in line and "property" in line and "uv run" in line
        ]

        assert property_test_lines, "Pre-push hook must run property tests"

        for line in property_test_lines:
            if line.strip().startswith("#"):
                continue

            # Property tests should use -n auto (they already have HYPOTHESIS_PROFILE=ci)
            assert "-n auto" in line, (
                f"Property tests must use '-n auto' for parallel execution\n"
                f"Found: {line.strip()}\n"
                f"Expected: HYPOTHESIS_PROFILE=ci OTEL_SDK_DISABLED=true uv run pytest -n auto -m property\n"
                f"Fix: Add -n auto to pytest command in .git/hooks/pre-push:~113"
            )

    def test_ci_uses_pytest_xdist_n_auto(self, ci_workflow_content: str):
        """Verify that CI uses -n auto (this is the baseline we're matching)."""
        # CI should use -n auto for unit tests
        assert "pytest -n auto" in ci_workflow_content, (
            "CI workflow must use 'pytest -n auto' for parallel execution\n" "If CI doesn't use it, this test needs updating"
        )


class TestOtelSdkDisabledParity:
    """Validate that local tests set OTEL_SDK_DISABLED=true like CI does.

    CRITICAL: These tests enforce Codex finding #2B - ensure local pre-push sets
    OTEL_SDK_DISABLED=true to match CI environment exactly.
    """

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

    @pytest.fixture
    def pre_push_hook_path(self, repo_root: Path) -> Path:
        """Get path to pre-push hook."""
        return repo_root / ".git" / "hooks" / "pre-push"

    @pytest.fixture
    def pre_push_content(self, pre_push_hook_path: Path) -> str:
        """Read pre-push hook content."""
        with open(pre_push_hook_path, "r") as f:
            return f.read()

    @pytest.fixture
    def ci_workflow_path(self, repo_root: Path) -> Path:
        """Get path to CI workflow."""
        return repo_root / ".github" / "workflows" / "ci.yaml"

    @pytest.fixture
    def ci_workflow_content(self, ci_workflow_path: Path) -> str:
        """Read CI workflow content."""
        with open(ci_workflow_path, "r") as f:
            return f.read()

    def test_unit_tests_set_otel_sdk_disabled(self, pre_push_content: str):
        """Test that unit tests set OTEL_SDK_DISABLED=true to match CI."""
        # Find unit test command lines
        unit_test_lines = [
            line
            for line in pre_push_content.split("\n")
            if "pytest" in line and "unit" in line and "uv run" in line and not line.strip().startswith("#")
        ]

        assert unit_test_lines, "Pre-push hook must run unit tests"

        for line in unit_test_lines:
            assert "OTEL_SDK_DISABLED=true" in line, (
                f"Unit tests must set OTEL_SDK_DISABLED=true to match CI environment\n"
                f"Found: {line.strip()}\n"
                f"Expected: OTEL_SDK_DISABLED=true uv run pytest -n auto ...\n"
                f"\n"
                f"Without OTEL_SDK_DISABLED=true:\n"
                f"  - OpenTelemetry SDK may initialize (performance overhead)\n"
                f"  - Different execution environment vs CI\n"
                f"  - Potential telemetry-related side effects\n"
                f"\n"
                f"Fix: Add OTEL_SDK_DISABLED=true to pytest command in .git/hooks/pre-push:~100"
            )

    def test_smoke_tests_set_otel_sdk_disabled(self, pre_push_content: str):
        """Test that smoke tests set OTEL_SDK_DISABLED=true to match CI."""
        smoke_test_lines = [
            line
            for line in pre_push_content.split("\n")
            if "pytest" in line and "smoke" in line and "uv run" in line and not line.strip().startswith("#")
        ]

        assert smoke_test_lines, "Pre-push hook must run smoke tests"

        for line in smoke_test_lines:
            assert "OTEL_SDK_DISABLED=true" in line, (
                f"Smoke tests must set OTEL_SDK_DISABLED=true to match CI\n"
                f"Found: {line.strip()}\n"
                f"Expected: OTEL_SDK_DISABLED=true uv run pytest -n auto tests/smoke/\n"
                f"Fix: Add OTEL_SDK_DISABLED=true to pytest command in .git/hooks/pre-push:~104"
            )

    def test_integration_tests_set_otel_sdk_disabled(self, pre_push_content: str):
        """Test that integration tests set OTEL_SDK_DISABLED=true to match CI."""
        integration_test_lines = [
            line
            for line in pre_push_content.split("\n")
            if "pytest" in line and "integration" in line and "uv run" in line and not line.strip().startswith("#")
        ]

        assert integration_test_lines, "Pre-push hook must run integration tests"

        for line in integration_test_lines:
            assert "OTEL_SDK_DISABLED=true" in line, (
                f"Integration tests must set OTEL_SDK_DISABLED=true to match CI\n"
                f"Found: {line.strip()}\n"
                f"Expected: OTEL_SDK_DISABLED=true uv run pytest -n auto tests/integration/\n"
                f"Fix: Add OTEL_SDK_DISABLED=true to pytest command in .git/hooks/pre-push:~108"
            )

    def test_property_tests_already_set_otel_sdk_disabled(self, pre_push_content: str):
        """Verify that property tests already set OTEL_SDK_DISABLED=true (should pass)."""
        property_test_lines = [
            line
            for line in pre_push_content.split("\n")
            if "pytest" in line and "property" in line and "uv run" in line and not line.strip().startswith("#")
        ]

        assert property_test_lines, "Pre-push hook must run property tests"

        for line in property_test_lines:
            assert "OTEL_SDK_DISABLED=true" in line, (
                f"Property tests must set OTEL_SDK_DISABLED=true\n" f"Found: {line.strip()}"
            )

    def test_ci_sets_otel_sdk_disabled(self, ci_workflow_content: str):
        """Verify that CI sets OTEL_SDK_DISABLED=true (this is the baseline)."""
        assert "OTEL_SDK_DISABLED=true" in ci_workflow_content, (
            "CI workflow must set OTEL_SDK_DISABLED=true for tests\n" "If CI doesn't use it, this test needs updating"
        )


class TestApiMcpTestSuiteParity:
    """Validate that local pre-push runs API/MCP test suites like CI does.

    CRITICAL: These tests enforce Codex finding #2D - ensure API and MCP tests
    run locally before push to prevent CI-only failures.
    """

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

    @pytest.fixture
    def pre_push_hook_path(self, repo_root: Path) -> Path:
        """Get path to pre-push hook."""
        return repo_root / ".git" / "hooks" / "pre-push"

    @pytest.fixture
    def pre_push_content(self, pre_push_hook_path: Path) -> str:
        """Read pre-push hook content."""
        with open(pre_push_hook_path, "r") as f:
            return f.read()

    @pytest.fixture
    def ci_workflow_path(self, repo_root: Path) -> Path:
        """Get path to CI workflow."""
        return repo_root / ".github" / "workflows" / "ci.yaml"

    @pytest.fixture
    def ci_workflow_content(self, ci_workflow_path: Path) -> str:
        """Read CI workflow content."""
        with open(ci_workflow_path, "r") as f:
            return f.read()

    def test_api_endpoint_tests_run_locally(self, pre_push_content: str):
        """Test that API endpoint tests run in pre-push hook like in CI."""
        # CI runs: pytest -n auto -m "api and unit and not llm"
        # Pre-push should too

        # Look for API test markers
        has_api_tests = (
            "api and unit" in pre_push_content or "'api and unit'" in pre_push_content or '"api and unit"' in pre_push_content
        )

        assert has_api_tests, (
            "Pre-push hook must run API endpoint tests to match CI\n"
            "\n"
            "CI runs (ci.yaml:249):\n"
            "  OTEL_SDK_DISABLED=true pytest -n auto -m 'api and unit and not llm'\n"
            "\n"
            "Pre-push hook should run:\n"
            "  OTEL_SDK_DISABLED=true uv run pytest -n auto -m 'api and unit and not llm' -v --tb=short\n"
            "\n"
            "Without API tests locally:\n"
            "  - Developers can push code that breaks API tests\n"
            "  - API failures only caught in CI\n"
            "  - Wastes CI time and developer time\n"
            "\n"
            "Fix: Add API test suite to Phase 3 in .git/hooks/pre-push"
        )

    def test_mcp_server_tests_run_locally(self, pre_push_content: str):
        """Test that MCP server tests run in pre-push hook like in CI."""
        # CI runs: pytest tests/unit/test_mcp_stdio_server.py -m "not llm"
        # Pre-push should too

        has_mcp_tests = "test_mcp_stdio_server.py" in pre_push_content

        assert has_mcp_tests, (
            "Pre-push hook must run MCP server tests to match CI\n"
            "\n"
            "CI runs (ci.yaml:253):\n"
            "  OTEL_SDK_DISABLED=true pytest tests/unit/test_mcp_stdio_server.py -m 'not llm'\n"
            "\n"
            "Pre-push hook should run:\n"
            "  OTEL_SDK_DISABLED=true uv run pytest -n auto tests/unit/test_mcp_stdio_server.py -m 'not llm' -v --tb=short\n"
            "\n"
            "Without MCP tests locally:\n"
            "  - MCP protocol changes can break without local detection\n"
            "  - MCP failures only caught in CI\n"
            "\n"
            "Fix: Add MCP test suite to Phase 3 in .git/hooks/pre-push"
        )

    def test_ci_runs_api_tests(self, ci_workflow_content: str):
        """Verify that CI runs API tests (this is the baseline)."""
        assert "api and unit" in ci_workflow_content, (
            "CI workflow must run API endpoint tests\n"
            "Expected: pytest -m 'api and unit'\n"
            "If CI doesn't run API tests, this test needs updating"
        )

    def test_ci_runs_mcp_tests(self, ci_workflow_content: str):
        """Verify that CI runs MCP tests (this is the baseline)."""
        assert "test_mcp_stdio_server.py" in ci_workflow_content, (
            "CI workflow must run MCP server tests\n"
            "Expected: pytest tests/unit/test_mcp_stdio_server.py\n"
            "If CI doesn't run MCP tests, this test needs updating"
        )


class TestMakefilePrePushParity:
    """Validate that Makefile validate-pre-push target matches pre-push hook exactly.

    CRITICAL: These tests enforce Codex finding #3 - ensure developers running
    'make validate-pre-push' get the same validation as the git pre-push hook.
    """

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

    @pytest.fixture
    def makefile_path(self, repo_root: Path) -> Path:
        """Get path to Makefile."""
        return repo_root / "Makefile"

    @pytest.fixture
    def makefile_content(self, makefile_path: Path) -> str:
        """Read Makefile content."""
        with open(makefile_path, "r") as f:
            return f.read()

    @pytest.fixture
    def pre_push_hook_path(self, repo_root: Path) -> Path:
        """Get path to pre-push hook."""
        return repo_root / ".git" / "hooks" / "pre-push"

    @pytest.fixture
    def pre_push_content(self, pre_push_hook_path: Path) -> str:
        """Read pre-push hook content."""
        with open(pre_push_hook_path, "r") as f:
            return f.read()

    def test_makefile_includes_unit_tests(self, makefile_content: str):
        """Test that Makefile validate-pre-push runs unit tests."""
        # Extract validate-pre-push target
        target_match = re.search(
            r"^validate-pre-push:.*?(?=^[a-zA-Z]|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )
        assert target_match, "Could not find validate-pre-push target in Makefile"

        target_content = target_match.group(0)

        # Should run unit tests
        has_unit_tests = "-m unit" in target_content or '-m "unit' in target_content or "-m 'unit" in target_content

        assert has_unit_tests, (
            "Makefile validate-pre-push must run unit tests to match pre-push hook\n"
            "\n"
            "Pre-push hook runs (Phase 3a):\n"
            "  OTEL_SDK_DISABLED=true uv run pytest -n auto tests/ -m 'unit and not contract'\n"
            "\n"
            "Makefile should include this in validate-pre-push target\n"
            "\n"
            "Without unit tests in Makefile:\n"
            "  - 'make validate-pre-push' gives false confidence\n"
            "  - Documentation claims it matches hook, but it doesn't\n"
            "  - Misleading for developers\n"
            "\n"
            "Fix: Add unit test phase to Makefile:~540 validate-pre-push target"
        )

    def test_makefile_includes_smoke_tests(self, makefile_content: str):
        """Test that Makefile validate-pre-push runs smoke tests."""
        target_match = re.search(
            r"^validate-pre-push:.*?(?=^[a-zA-Z]|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )
        assert target_match, "Could not find validate-pre-push target in Makefile"

        target_content = target_match.group(0)

        # Should run smoke tests
        has_smoke_tests = "tests/smoke" in target_content or "smoke" in target_content

        assert has_smoke_tests, (
            "Makefile validate-pre-push must run smoke tests to match pre-push hook\n"
            "Pre-push hook runs: uv run pytest -n auto tests/smoke/\n"
            "Fix: Add smoke test phase to Makefile validate-pre-push target"
        )

    def test_makefile_includes_integration_tests(self, makefile_content: str):
        """Test that Makefile validate-pre-push runs integration tests."""
        target_match = re.search(
            r"^validate-pre-push:.*?(?=^[a-zA-Z]|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )
        assert target_match, "Could not find validate-pre-push target in Makefile"

        target_content = target_match.group(0)

        # Should run integration tests
        has_integration_tests = "tests/integration" in target_content or "integration" in target_content

        assert has_integration_tests, (
            "Makefile validate-pre-push must run integration tests to match pre-push hook\n"
            "Pre-push hook runs: uv run pytest -n auto tests/integration/ --lf\n"
            "Fix: Add integration test phase to Makefile validate-pre-push target"
        )

    def test_makefile_includes_api_mcp_tests(self, makefile_content: str):
        """Test that Makefile validate-pre-push runs API/MCP tests."""
        target_match = re.search(
            r"^validate-pre-push:.*?(?=^[a-zA-Z]|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )
        assert target_match, "Could not find validate-pre-push target in Makefile"

        target_content = target_match.group(0)

        # Should run API/MCP tests
        has_api_tests = "api" in target_content or "test_mcp_stdio_server" in target_content

        assert has_api_tests, (
            "Makefile validate-pre-push must run API/MCP tests to match pre-push hook\n"
            "Pre-push hook should run:\n"
            "  - API tests: pytest -m 'api and unit'\n"
            "  - MCP tests: pytest tests/unit/test_mcp_stdio_server.py\n"
            "Fix: Add API/MCP test phases to Makefile validate-pre-push target"
        )

    def test_makefile_uses_n_auto(self, makefile_content: str):
        """Test that Makefile validate-pre-push uses -n auto like pre-push hook."""
        target_match = re.search(
            r"^validate-pre-push:.*?(?=^[a-zA-Z]|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )
        assert target_match, "Could not find validate-pre-push target in Makefile"

        target_content = target_match.group(0)

        # If it runs pytest, it should use -n auto
        if "pytest" in target_content:
            assert "-n auto" in target_content, (
                "Makefile validate-pre-push must use '-n auto' to match pre-push hook\n"
                "All pytest commands in validate-pre-push should include -n auto\n"
                "Fix: Add -n auto to pytest commands in Makefile validate-pre-push target"
            )

    def test_makefile_sets_otel_sdk_disabled(self, makefile_content: str):
        """Test that Makefile validate-pre-push sets OTEL_SDK_DISABLED=true."""
        target_match = re.search(
            r"^validate-pre-push:.*?(?=^[a-zA-Z]|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )
        assert target_match, "Could not find validate-pre-push target in Makefile"

        target_content = target_match.group(0)

        # If it runs pytest, it should set OTEL_SDK_DISABLED=true
        if "pytest" in target_content:
            assert "OTEL_SDK_DISABLED=true" in target_content, (
                "Makefile validate-pre-push must set OTEL_SDK_DISABLED=true to match pre-push hook\n"
                "All pytest commands should be prefixed with OTEL_SDK_DISABLED=true\n"
                "Fix: Add OTEL_SDK_DISABLED=true to pytest commands in Makefile"
            )


class TestActionlintHookStrictness:
    """Validate that actionlint hook fails on errors (no || true bypass).

    CRITICAL: Codex finding #1 - actionlint hook currently has || true which
    causes it to NEVER fail even when workflows are invalid. This creates a
    local/CI divergence where CI fails but local validation passes.
    """

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

    @pytest.fixture
    def pre_commit_config_path(self, repo_root: Path) -> Path:
        """Get path to pre-commit config."""
        return repo_root / ".pre-commit-config.yaml"

    @pytest.fixture
    def pre_commit_config_content(self, pre_commit_config_path: Path) -> str:
        """Read pre-commit config content."""
        with open(pre_commit_config_path, "r") as f:
            return f.read()

    def test_actionlint_hook_has_no_bypass(self, pre_commit_config_content: str):
        """Test that actionlint hook does NOT have || true bypass.

        CRITICAL: Without this test, developers can push invalid workflows that
        only fail in CI, wasting time and breaking builds.
        """
        # Find the actionlint hook entry
        actionlint_section_match = re.search(
            r"- repo:.*actionlint.*?(?=- repo:|\Z)",
            pre_commit_config_content,
            re.DOTALL,
        )

        assert actionlint_section_match, "Could not find actionlint hook in .pre-commit-config.yaml"

        actionlint_section = actionlint_section_match.group(0)

        # Check for || true bypass
        assert "|| true" not in actionlint_section, (
            "Actionlint hook MUST NOT have '|| true' bypass\n"
            "\n"
            "Current issue (Codex finding #1):\n"
            "  - .pre-commit-config.yaml:97 has: actionlint ... 2>&1 || true\n"
            "  - This causes hook to ALWAYS return exit code 0\n"
            "  - Invalid workflows pass locally but fail in CI\n"
            "\n"
            "Impact:\n"
            "  - Developers push broken workflow files\n"
            "  - CI catches errors that should have been caught locally\n"
            "  - Wastes developer time and CI resources\n"
            "\n"
            "CI behavior (ci.yaml:106-110):\n"
            "  actionlint -color -shellcheck= .github/workflows/*.{yml,yaml}\n"
            "  ^ No || true, fails on errors ✅\n"
            "\n"
            "Fix: Remove || true from .pre-commit-config.yaml:97\n"
            "  entry: bash -c 'actionlint -no-color -shellcheck= .github/workflows/*.{yml,yaml} 2>&1'\n"
        )

    def test_actionlint_hook_configured_for_pre_push(self, pre_commit_config_content: str):
        """Test that actionlint hook runs during pre-push stage."""
        actionlint_section_match = re.search(
            r"- repo:.*actionlint.*?(?=- repo:|\Z)",
            pre_commit_config_content,
            re.DOTALL,
        )

        assert actionlint_section_match, "Could not find actionlint hook"

        actionlint_section = actionlint_section_match.group(0)

        # Should be configured for pre-push stage
        assert (
            "stages:" in actionlint_section and "push" in actionlint_section
        ), "Actionlint hook should be configured to run during pre-push stage"


class TestMyPyBlockingParity:
    """Validate that MyPy blocking behavior matches between local and CI.

    CRITICAL: Codex finding #2 - MyPy is currently non-blocking in pre-push hook
    but blocking in CI. This creates local/CI divergence where type errors pass
    locally but fail in CI.
    """

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

    @pytest.fixture
    def pre_push_hook_path(self, repo_root: Path) -> Path:
        """Get path to pre-push hook."""
        return repo_root / ".git" / "hooks" / "pre-push"

    @pytest.fixture
    def pre_push_content(self, pre_push_hook_path: Path) -> str:
        """Read pre-push hook content."""
        with open(pre_push_hook_path, "r") as f:
            return f.read()

    @pytest.fixture
    def ci_workflow_path(self, repo_root: Path) -> Path:
        """Get path to CI workflow."""
        return repo_root / ".github" / "workflows" / "ci.yaml"

    @pytest.fixture
    def ci_workflow_content(self, ci_workflow_path: Path) -> str:
        """Read CI workflow content."""
        with open(ci_workflow_path, "r") as f:
            return f.read()

    def test_mypy_is_blocking_locally(self, pre_push_content: str):
        """Test that MyPy is BLOCKING in pre-push hook (matches CI).

        CRITICAL: User chose "Make local MyPy blocking (match CI strictness)".
        This test enforces that decision.
        """
        # Find the MyPy validation command
        # Pattern matches content between PHASE 2 and PHASE 3 headers
        mypy_section_match = re.search(
            r"(?:PHASE 2[^\n]*)(.*?)(?=(?:PHASE 3|\Z))",
            pre_push_content,
            re.DOTALL,
        )

        assert mypy_section_match, "Could not find PHASE 2 (type checking) in pre-push hook"

        phase_2_content = mypy_section_match.group(0)

        # Check that mypy validation exists in Phase 2
        assert "mypy" in phase_2_content.lower(), "Phase 2 should contain mypy validation"

        # Check that mypy is configured as blocking (has "true  #" and not "false  #")
        # The pattern "true  # " indicates blocking behavior, "false  #" indicates non-blocking
        has_blocking = "true  #" in phase_2_content
        has_non_blocking = "false  #" in phase_2_content

        assert has_blocking and not has_non_blocking, (
            "MyPy MUST be blocking in pre-push hook to match CI behavior\n"
            "\n"
            "Current issue (Codex finding #2):\n"
            "  - .git/hooks/pre-push:90 has: run_validation ... false  # Non-blocking\n"
            "  - This makes MyPy warnings-only, doesn't fail on errors\n"
            "  - CI has NO continue-on-error, so MyPy FAILS THE BUILD\n"
            "\n"
            "Impact:\n"
            "  - Type errors pass locally but fail in CI\n"
            "  - 'Works locally, fails in CI' syndrome\n"
            "  - Wastes developer time debugging in CI\n"
            "\n"
            "Local behavior (pre-push:87-90):\n"
            '  run_validation "MyPy Type Checking (Warning Only)" \\\n'
            '      "uv run mypy src/mcp_server_langgraph" \\\n'
            "      false  # Non-blocking ❌\n"
            "\n"
            "CI behavior (ci.yaml:255-260):\n"
            "  - name: Run mypy type checking\n"
            "    run: mypy src/mcp_server_langgraph --no-error-summary\n"
            "  ^ No continue-on-error, fails build ✅\n"
            "\n"
            "Fix: Change .git/hooks/pre-push:90 from 'false' to 'true'\n"
            '  run_validation "MyPy Type Checking (Critical)" \\\n'
            '      "uv run mypy src/mcp_server_langgraph --no-error-summary" \\\n'
            "      true  # Critical (matches CI)\n"
        )

    def test_mypy_comment_reflects_blocking_behavior(self, pre_push_content: str):
        """Test that MyPy phase comment reflects blocking behavior."""
        # Pattern matches content between PHASE 2 and PHASE 3 headers
        phase_2_match = re.search(
            r"(?:PHASE 2[^\n]*)(.*?)(?=(?:PHASE 3|\Z))",
            pre_push_content,
            re.DOTALL,
        )

        assert phase_2_match, "Could not find PHASE 2"

        phase_2_content = phase_2_match.group(0)

        # Should NOT say "Warning Only" if it's blocking
        # Should say "Critical" or similar
        if "false" not in phase_2_content:  # If it's blocking
            assert "Warning Only" not in phase_2_content or "Critical" in phase_2_content, (
                "MyPy phase comment should reflect that it's CRITICAL/BLOCKING\n"
                "Comments should match behavior to avoid confusion\n"
                "Fix: Update comment in .git/hooks/pre-push:83-87 to say 'Critical' not 'Warning Only'"
            )

    def test_ci_mypy_is_blocking(self, ci_workflow_content: str):
        """Test that CI MyPy step is blocking (no continue-on-error)."""
        # Find the mypy step - match only until the next step starts
        mypy_step_match = re.search(
            r"(- name:.*mypy.*?\n\s+run:.*?)(?=\n\s+- name:|\Z)",
            ci_workflow_content,
            re.DOTALL | re.IGNORECASE,
        )

        assert mypy_step_match, "Could not find mypy step in CI workflow"

        mypy_step = mypy_step_match.group(1)

        # Should NOT have continue-on-error: true
        assert "continue-on-error: true" not in mypy_step, (
            "CI MyPy step must NOT have 'continue-on-error: true'\n"
            "MyPy should fail the build in CI (and locally) to maintain quality\n"
            "If this test fails, CI has been made non-blocking - align local to match"
        )


class TestIsolationValidationStrictness:
    """Validate that test isolation validation script promotes warnings to errors.

    CRITICAL: Codex finding from pytest-xdist section - validate_test_isolation.py
    currently returns 0 (success) when tests are missing xdist_group or gc.collect,
    allowing regressions to slip through.
    """

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

    @pytest.fixture
    def validation_script_path(self, repo_root: Path) -> Path:
        """Get path to validation script."""
        return repo_root / "scripts" / "validation" / "validate_test_isolation.py"

    @pytest.fixture
    def validation_script_content(self, validation_script_path: Path) -> str:
        """Read validation script content."""
        with open(validation_script_path, "r") as f:
            return f.read()

    def test_missing_xdist_group_is_error_not_warning(self, validation_script_content: str):
        """Test that missing xdist_group marker is treated as ERROR not WARNING.

        CRITICAL: User chose "Promote warnings to errors (strict enforcement)".
        Missing xdist_group markers cause memory explosion in pytest-xdist.
        """
        # Find where xdist_group violations are appended
        # Look for the code that handles missing xdist_group
        xdist_group_check = re.search(
            r"if not self\.has_xdist_group_marker.*?self\.(warnings|violations)\.append",
            validation_script_content,
            re.DOTALL,
        )

        assert xdist_group_check, "Could not find xdist_group validation logic"

        check_code = xdist_group_check.group(0)

        # Should append to 'violations' NOT 'warnings'
        assert "self.violations.append" in check_code, (
            "Missing xdist_group marker MUST be treated as VIOLATION not WARNING\n"
            "\n"
            "Current issue (Codex finding - pytest-xdist section):\n"
            "  - validate_test_isolation.py:79-94 appends to self.warnings\n"
            "  - Script returns 0 (success) when warnings present\n"
            "  - Allows regressions to slip through\n"
            "\n"
            "Impact (ADR-0052, Memory Safety Guidelines):\n"
            "  - Missing @pytest.mark.xdist_group causes memory explosion\n"
            "  - Observed: 217GB VIRT, 42GB RES memory usage\n"
            "  - Tests become too slow or OOM kill\n"
            "\n"
            "Fix: Change scripts/validation/validate_test_isolation.py:79-94\n"
            "  From: self.warnings.append(...)\n"
            "  To:   self.violations.append(...)\n"
        )

    def test_missing_gc_collect_is_error_not_warning(self, validation_script_content: str):
        """Test that missing gc.collect() is treated as ERROR not WARNING."""
        # Find where gc.collect violations are appended
        gc_collect_check = re.search(
            r"if not self\.has_teardown_method or not self\.has_gc_collect.*?self\.(warnings|violations)\.append",
            validation_script_content,
            re.DOTALL,
        )

        assert gc_collect_check, "Could not find gc.collect validation logic"

        check_code = gc_collect_check.group(0)

        # Should append to 'violations' NOT 'warnings'
        assert "self.violations.append" in check_code, (
            "Missing gc.collect() MUST be treated as VIOLATION not WARNING\n"
            "\n"
            "Missing teardown_method() with gc.collect() causes pytest-xdist OOM:\n"
            "  - AsyncMock/MagicMock create circular references\n"
            "  - Without explicit GC, workers accumulate mocks\n"
            "  - Memory explosion: 200GB+ observed\n"
            "\n"
            "Fix: Change scripts/validation/validate_test_isolation.py:79-94\n"
            "  From: self.warnings.append(...)\n"
            "  To:   self.violations.append(...)\n"
        )


class TestMakefileDependencyExtras:
    """Validate that Makefile install-dev includes all required dependency extras.

    CRITICAL: Codex finding #4 - install-dev runs 'uv sync' without --extra flags,
    while CI uses --extra dev --extra builder. This causes missing import errors
    when running pre-push validation locally.
    """

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

    @pytest.fixture
    def makefile_path(self, repo_root: Path) -> Path:
        """Get path to Makefile."""
        return repo_root / "Makefile"

    @pytest.fixture
    def makefile_content(self, makefile_path: Path) -> str:
        """Read Makefile content."""
        with open(makefile_path, "r") as f:
            return f.read()

    @pytest.fixture
    def ci_workflow_path(self, repo_root: Path) -> Path:
        """Get path to CI workflow."""
        return repo_root / ".github" / "workflows" / "ci.yaml"

    @pytest.fixture
    def ci_workflow_content(self, ci_workflow_path: Path) -> str:
        """Read CI workflow content."""
        with open(ci_workflow_path, "r") as f:
            return f.read()

    def test_install_dev_includes_dev_extra(self, makefile_content: str):
        """Test that install-dev target includes --extra dev.

        CRITICAL: User chose "Add --extra dev --extra builder to install-dev".
        Without dev extra, pytest and testing tools are missing.
        """
        # Find install-dev target
        install_dev_match = re.search(
            r"^install-dev:.*?(?=^[a-zA-Z]|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )

        assert install_dev_match, "Could not find install-dev target in Makefile"

        install_dev_content = install_dev_match.group(0)

        # Should have uv sync with --extra dev
        assert "--extra dev" in install_dev_content, (
            "Makefile install-dev MUST include '--extra dev' to match CI\n"
            "\n"
            "Current issue (Codex finding #4):\n"
            "  - Makefile:182 runs: uv sync\n"
            "  - CI runs: uv sync --extra dev --extra builder\n"
            "  - Missing dev extra means no pytest, mypy, black, etc.\n"
            "\n"
            "Impact:\n"
            "  - Developers hit ImportError when running pre-push validation\n"
            "  - 'make validate-pre-push' fails with missing packages\n"
            "  - Documentation says to use install-dev, but it's incomplete\n"
            "\n"
            "CI behavior (ci.yaml:200-214):\n"
            "  uv sync --python $VERSION --frozen --extra dev --extra builder\n"
            "  ^ Includes dev extras ✅\n"
            "\n"
            "Fix: Update Makefile:182\n"
            "  From: uv sync\n"
            "  To:   uv sync --extra dev --extra builder\n"
        )

    def test_install_dev_includes_builder_extra(self, makefile_content: str):
        """Test that install-dev target includes --extra builder.

        Required because unit tests import builder modules (per CI comments).
        """
        install_dev_match = re.search(
            r"^install-dev:.*?(?=^[a-zA-Z]|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )

        assert install_dev_match, "Could not find install-dev target in Makefile"

        install_dev_content = install_dev_match.group(0)

        # Should have uv sync with --extra builder
        assert "--extra builder" in install_dev_content, (
            "Makefile install-dev MUST include '--extra builder' to match CI\n"
            "\n"
            "Why builder extra is required (from ci.yaml:210-213):\n"
            "  'dev: Testing framework (pytest, pytest-cov, black, mypy, etc.)'\n"
            "  'builder: Visual workflow builder (black, jinja2, ast-comments)'\n"
            "  'Both required because unit tests import builder modules'\n"
            "\n"
            "Without builder extra:\n"
            "  - Unit tests fail with ImportError\n"
            "  - Builder tool development impossible locally\n"
            "\n"
            "Fix: Update Makefile:182 to include both extras"
        )

    def test_ci_uses_dev_and_builder_extras(self, ci_workflow_content: str):
        """Verify that CI uses both dev and builder extras (baseline check)."""
        # CI should have both extras
        assert "--extra dev" in ci_workflow_content and "--extra builder" in ci_workflow_content, (
            "CI workflow must use both --extra dev and --extra builder\n"
            "This is the baseline that local install-dev should match\n"
            "If CI doesn't use these extras, update this test"
        )


class TestPrePushDependencyValidation:
    """Validate that pre-push hook includes dependency validation (uv pip check).

    CRITICAL: User chose "Yes, add uv pip check to pre-push". CI runs this check
    (ci.yaml:220-235) but pre-push hook doesn't, allowing dependency conflicts
    to slip through to CI.
    """

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

    @pytest.fixture
    def pre_push_hook_path(self, repo_root: Path) -> Path:
        """Get path to pre-push hook."""
        return repo_root / ".git" / "hooks" / "pre-push"

    @pytest.fixture
    def pre_push_content(self, pre_push_hook_path: Path) -> str:
        """Read pre-push hook content."""
        with open(pre_push_hook_path, "r") as f:
            return f.read()

    @pytest.fixture
    def ci_workflow_path(self, repo_root: Path) -> Path:
        """Get path to CI workflow."""
        return repo_root / ".github" / "workflows" / "ci.yaml"

    @pytest.fixture
    def ci_workflow_content(self, ci_workflow_path: Path) -> str:
        """Read CI workflow content."""
        with open(ci_workflow_path, "r") as f:
            return f.read()

    def test_pre_push_includes_uv_pip_check(self, pre_push_content: str):
        """Test that pre-push hook Phase 1 includes 'uv pip check'.

        CRITICAL: User chose to add this check. Without it, dependency conflicts
        pass locally but fail in CI.
        """
        # Find Phase 1 (fast checks)
        # Pattern matches content between PHASE 1 and PHASE 2 headers
        # Use DOTALL to match across newlines
        phase_1_match = re.search(
            r"(?:PHASE 1[^\n]*)(.*?)(?=(?:PHASE 2|\Z))",
            pre_push_content,
            re.DOTALL,
        )

        assert phase_1_match, "Could not find PHASE 1 in pre-push hook"

        phase_1_content = phase_1_match.group(0)

        # Should contain 'uv pip check' command
        assert "uv pip check" in phase_1_content, (
            "Pre-push hook Phase 1 MUST include 'uv pip check' to match CI\n"
            "\n"
            "Current issue:\n"
            "  - CI validates dependencies with uv pip check (ci.yaml:220-235)\n"
            "  - Pre-push hook Phase 1 doesn't include this check\n"
            "  - Dependency conflicts only caught in CI\n"
            "\n"
            "Impact:\n"
            "  - Conflicting dependencies pass locally, fail in CI\n"
            "  - Version mismatches go undetected until push\n"
            "  - Wastes CI time and developer time\n"
            "\n"
            "CI behavior (ci.yaml:220-235):\n"
            "  - name: Validate lockfile is up-to-date\n"
            "    run: |\n"
            "      uv lock --check || { ... }\n"
            "  (Includes dependency validation)\n"
            "\n"
            "Fix: Add to .git/hooks/pre-push Phase 1 (after uv lock --check):\n"
            '  echo "  → Validating dependency tree..."\n'
            "  uv pip check || {\n"
            '    echo "❌ Dependency conflicts detected!"\n'
            "    echo \"Fix: Run 'uv pip check' to see details\"\n"
            "    exit 1\n"
            "  }\n"
        )

    def test_ci_includes_dependency_validation(self, ci_workflow_content: str):
        """Verify that CI includes dependency validation (baseline check)."""
        # CI should validate dependencies
        # This might be in lockfile validation step
        has_lockfile_check = "uv lock --check" in ci_workflow_content
        has_frozen_sync = "--frozen" in ci_workflow_content

        assert has_lockfile_check or has_frozen_sync, (
            "CI workflow must validate dependencies\n"
            "Expected: uv lock --check OR uv sync --frozen\n"
            "This is the baseline that pre-push should match"
        )


class TestPreCommitHookStageFlag:
    """Validate that Makefile validate-pre-push uses --hook-stage push.

    CRITICAL: Codex finding #3 - Makefile validate-pre-push runs
    'pre-commit run --all-files' without --hook-stage push, so none of the
    push-only hooks execute when developers follow documented command.
    """

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

    @pytest.fixture
    def makefile_path(self, repo_root: Path) -> Path:
        """Get path to Makefile."""
        return repo_root / "Makefile"

    @pytest.fixture
    def makefile_content(self, makefile_path: Path) -> str:
        """Read Makefile content."""
        with open(makefile_path, "r") as f:
            return f.read()

    def test_validate_pre_push_uses_hook_stage_push(self, makefile_content: str):
        """Test that validate-pre-push includes --hook-stage push flag.

        CRITICAL: Without --hook-stage push, the 45 push-stage hooks configured
        in .pre-commit-config.yaml won't execute, creating false confidence.
        """
        # Find validate-pre-push target
        target_match = re.search(
            r"^validate-pre-push:.*?(?=^[a-zA-Z]|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )

        assert target_match, "Could not find validate-pre-push target in Makefile"

        target_content = target_match.group(0)

        # Find pre-commit run commands
        precommit_commands = re.findall(r"pre-commit run[^\n]*", target_content)

        assert precommit_commands, "validate-pre-push should run pre-commit"

        # At least one pre-commit command should have --hook-stage push
        has_hook_stage_push = any("--hook-stage push" in cmd for cmd in precommit_commands)

        assert has_hook_stage_push, (
            "Makefile validate-pre-push MUST use '--hook-stage push' flag\n"
            "\n"
            "Current issue (Codex finding #3):\n"
            "  - Makefile:570 runs: pre-commit run --all-files\n"
            "  - Missing --hook-stage push flag\n"
            "  - None of the 45 push-stage hooks execute!\n"
            "  - CONTRIBUTING.md:28 documents 'make validate-pre-push' as the command to use\n"
            "\n"
            "Impact:\n"
            "  - Developers run 'make validate-pre-push' thinking it validates everything\n"
            "  - Push-only hooks (actionlint, workflow validation, etc.) don't run\n"
            "  - False confidence: validation passes but push will fail\n"
            "  - Documentation misleads developers\n"
            "\n"
            "Pre-push hooks that are skipped without --hook-stage push:\n"
            "  - actionlint-workflow-validation (validates GitHub Actions)\n"
            "  - validate-pytest-xdist-enforcement\n"
            "  - check-test-memory-safety\n"
            "  - ... and 42 more hooks!\n"
            "\n"
            "Git pre-push hook behavior:\n"
            "  Uses: pre-commit run --all-files --hook-stage push ✅\n"
            "\n"
            "Fix: Update Makefile:570\n"
            "  From: pre-commit run --all-files\n"
            "  To:   pre-commit run --all-files --hook-stage push\n"
        )


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
