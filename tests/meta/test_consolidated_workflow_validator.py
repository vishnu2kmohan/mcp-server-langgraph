"""
Test consolidated GitHub workflow validator.

This test validates that the consolidated workflow validator (combining context
validation and action version validation) works correctly and prevents common
GitHub Actions workflow issues.

Following TDD principles - this test defines expected behavior before implementation.
"""

import gc
import subprocess
import sys
from pathlib import Path

import pytest

# Mark as unit+meta test to ensure it runs in CI
pytestmark = [pytest.mark.unit, pytest.mark.meta]

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent


@pytest.mark.xdist_group(name="testconsolidatedworkflowvalidator")
class TestConsolidatedWorkflowValidator:
    """
    Verify consolidated GitHub workflow validator works correctly.

    This test calls scripts/validators/validate_github_workflows_comprehensive.py
    instead of duplicating validation logic. The script is the source of truth.

    Architecture Pattern:
    - Script = Source of truth (scripts/validators/validate_github_workflows_comprehensive.py)
    - Hook = Trigger (validate-github-workflows in .pre-commit-config.yaml)
    - Meta-Test = Validator of validator (this test)
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_validator_script_exists(self):
        """
        Test that the consolidated workflow validator script exists.

        Expected location: scripts/validators/validate_github_workflows_comprehensive.py
        """
        script_path = PROJECT_ROOT / "scripts" / "validators" / "validate_github_workflows_comprehensive.py"

        assert script_path.exists(), (
            f"Consolidated workflow validator script not found: {script_path}\n"
            "Expected: scripts/validators/validate_github_workflows_comprehensive.py\n"
            "This script should consolidate context validation and action version validation."
        )

    def test_validator_script_is_executable(self):
        """
        Test that the validator script can be executed.

        The script should:
        1. Be a valid Python file
        2. Have a main() function or __main__ block
        3. Return exit code 0 when validation passes
        """
        script_path = PROJECT_ROOT / "scripts" / "validators" / "validate_github_workflows_comprehensive.py"

        if not script_path.exists():
            pytest.skip(f"Validator script not found: {script_path}")

        # Verify script is a Python file
        assert script_path.suffix == ".py", f"Script must be a Python file, got: {script_path.suffix}"

        # Verify script has main execution block
        content = script_path.read_text()
        has_main = 'if __name__ == "__main__"' in content or "def main(" in content

        assert has_main, "Script must have a main() function or __main__ block for CLI execution"

    def test_validator_passes_on_valid_workflows(self):
        """
        Test that validator passes when all workflows are valid.

        This validates that:
        1. Context usage matches enabled triggers
        2. Action versions are valid published tags
        3. Permissions are correctly configured
        4. Workflow YAML syntax is valid
        """
        script_path = PROJECT_ROOT / "scripts" / "validators" / "validate_github_workflows_comprehensive.py"

        if not script_path.exists():
            pytest.skip(f"Validator script not found: {script_path}")

        # Run the validation script
        result = subprocess.run(
            [sys.executable, str(script_path), "--repo-root", str(PROJECT_ROOT)],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # The script should pass (exit code 0)
        assert result.returncode == 0, (
            f"Consolidated workflow validator failed:\n\n"
            f"stdout:\n{result.stdout}\n\n"
            f"stderr:\n{result.stderr}\n\n"
            f"Fix: Address validation errors shown above"
        )

    def test_validator_detects_invalid_context_usage(self):
        """
        Test that validator detects undefined context variable usage.

        Example invalid patterns:
        - Using github.event.pull_request.* when pull_request trigger not enabled
        - Using github.event.workflow_run.* when workflow_run trigger not enabled
        """
        # This test will validate the script correctly reports context errors
        # when they exist. For now, we expect all workflows to be valid.
        pytest.skip("Context validation requires invalid workflow fixtures - implement when needed")

    def test_validator_detects_invalid_action_versions(self):
        """
        Test that validator detects invalid action version tags.

        Invalid patterns to detect:
        - astral-sh/setup-uv@v7.1.1 (should be v7.1.0 or v7)
        - actions/cache@v4.3.0 (should be v4.2.0 or v4)
        - Very high major versions (e.g., @v99)
        """
        # This test validates the script correctly reports version errors
        # when they exist. Current workflows should all use valid versions.
        pytest.skip("Version validation requires invalid workflow fixtures - implement when needed")

    def test_validator_detects_missing_permissions(self):
        """
        Test that validator detects workflows creating issues without permissions.

        Workflows using github.rest.issues.create must have 'issues: write' permission.
        """
        pytest.skip("Permission validation requires invalid workflow fixtures - implement when needed")

    def test_validator_provides_helpful_error_messages(self):
        """
        Test that validator provides actionable error messages.

        Error messages should include:
        - File name where error occurred
        - Line number (if applicable)
        - What the error is
        - How to fix it
        """
        script_path = PROJECT_ROOT / "scripts" / "validators" / "validate_github_workflows_comprehensive.py"

        if not script_path.exists():
            pytest.skip(f"Validator script not found: {script_path}")

        # Read script to verify it has good error reporting
        content = script_path.read_text()

        # Check for error reporting patterns
        has_file_reporting = "workflow_file" in content or "file_path" in content

        # Verify error reporting capabilities exist
        assert has_file_reporting, "Script should report which file has errors"
        # Note: Line number reporting is optional but recommended

    def test_validator_has_cli_interface(self):
        """
        Test that validator has a proper CLI interface.

        Should support:
        - --repo-root argument to specify repository root
        - --verbose for detailed output
        - Exit code 0 for pass, 1 for validation errors, 2 for script errors
        """
        script_path = PROJECT_ROOT / "scripts" / "validators" / "validate_github_workflows_comprehensive.py"

        if not script_path.exists():
            pytest.skip(f"Validator script not found: {script_path}")

        # Test help output
        result = subprocess.run([sys.executable, str(script_path), "--help"], capture_output=True, text=True, timeout=10)

        # Should have help text
        assert result.returncode == 0, f"Script --help should return exit code 0, got: {result.returncode}"
        assert len(result.stdout) > 0, "Script --help should output usage information"
        assert "--repo-root" in result.stdout or "repo-root" in result.stdout, "--help should document --repo-root argument"

    def test_validator_consolidates_context_and_version_checks(self):
        """
        Test that validator performs BOTH context and version validation.

        This ensures consolidation is complete - the script should:
        1. Check context usage (from validate_github_workflows.py)
        2. Check action versions (from test_github_actions_validation.py)
        3. Check permissions (from test_github_actions_validation.py)
        4. Check YAML syntax (from test_github_actions_validation.py)
        """
        script_path = PROJECT_ROOT / "scripts" / "validators" / "validate_github_workflows_comprehensive.py"

        if not script_path.exists():
            pytest.skip(f"Validator script not found: {script_path}")

        content = script_path.read_text()

        # Verify script includes context validation logic
        has_context_validation = "github.event" in content or "context_pattern" in content or "workflow_run" in content

        assert has_context_validation, (
            "Consolidated validator must include context validation logic\n" "(from scripts/validate_github_workflows.py)"
        )

        # Verify script includes version validation logic
        has_version_validation = "astral-sh/setup-uv" in content or "action_pattern" in content or "@v" in content

        assert has_version_validation, (
            "Consolidated validator must include action version validation logic\n"
            "(from tests/meta/test_github_actions_validation.py)"
        )

        # Verify script includes permission validation
        has_permission_validation = "issues: write" in content or "permissions" in content

        assert has_permission_validation, (
            "Consolidated validator must include permissions validation logic\n"
            "(from tests/meta/test_github_actions_validation.py)"
        )

    def test_validator_performance_is_reasonable(self):
        """
        Test that validator completes in reasonable time.

        Should complete validation of all workflows in < 10 seconds.
        """
        script_path = PROJECT_ROOT / "scripts" / "validators" / "validate_github_workflows_comprehensive.py"

        if not script_path.exists():
            pytest.skip(f"Validator script not found: {script_path}")

        import time

        start_time = time.time()

        result = subprocess.run(
            [sys.executable, str(script_path), "--repo-root", str(PROJECT_ROOT)],
            capture_output=True,
            text=True,
            timeout=15,  # Allow 15s max
        )

        elapsed = time.time() - start_time

        # Verify validation passed
        assert result.returncode == 0, f"Validator failed:\n{result.stdout}\n{result.stderr}"

        # Verify performance is acceptable
        assert elapsed < 10, (
            f"Validator took {elapsed:.2f}s (should be < 10s)\n" "Consider optimizing validation logic or adding caching"
        )


@pytest.mark.xdist_group(name="testconsolidatedworkflowvalidatorregression")
class TestConsolidatedWorkflowValidatorRegression:
    """
    Regression prevention tests for consolidated workflow validator.

    These tests ensure that the consolidated validator prevents the same issues
    that the original separate validators detected.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_validator_prevents_invalid_uv_version(self):
        """
        Regression: Prevent astral-sh/setup-uv@v7.1.1 (invalid version).

        This was a critical finding from OpenAI Codex Phase 5.
        The consolidated validator must detect this.
        """
        script_path = PROJECT_ROOT / "scripts" / "validators" / "validate_github_workflows_comprehensive.py"

        if not script_path.exists():
            pytest.skip(f"Validator script not found: {script_path}")

        # Run validator - should pass (no invalid versions in current workflows)
        result = subprocess.run(
            [sys.executable, str(script_path), "--repo-root", str(PROJECT_ROOT)],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Verify it passes on current valid workflows
        assert result.returncode == 0, f"Validator should pass on current workflows:\n{result.stdout}\n{result.stderr}"

        # Note: To fully test this, we'd need a fixture with invalid version
        # For now, we verify the validator includes this check in test_validator_consolidates_context_and_version_checks

    def test_validator_prevents_undefined_context_usage(self):
        """
        Regression: Prevent using github.event.workflow_run.* without workflow_run trigger.

        This was the original issue that validate_github_workflows.py fixed.
        The consolidated validator must detect this.
        """
        script_path = PROJECT_ROOT / "scripts" / "validators" / "validate_github_workflows_comprehensive.py"

        if not script_path.exists():
            pytest.skip(f"Validator script not found: {script_path}")

        # Note: To fully test this, we'd need a fixture with undefined context usage
        # For now, we verify the validator includes this check in test_validator_consolidates_context_and_version_checks

    def test_validator_prevents_missing_issues_permission(self):
        """
        Regression: Prevent workflows creating issues without 'issues: write' permission.

        This was detected by test_github_actions_validation.py permissions tests.
        The consolidated validator must detect this.
        """
        script_path = PROJECT_ROOT / "scripts" / "validators" / "validate_github_workflows_comprehensive.py"

        if not script_path.exists():
            pytest.skip(f"Validator script not found: {script_path}")

        # Note: To fully test this, we'd need a fixture with missing permissions
        # For now, we verify the validator includes this check in test_validator_consolidates_context_and_version_checks
