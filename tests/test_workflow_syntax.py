"""
Test workflow syntax validation using actionlint.

These tests ensure all GitHub Actions workflows are syntactically valid and
follow best practices, preventing deployment failures due to workflow errors.

TDD Approach (RED → GREEN → REFACTOR):
1. RED: Tests fail initially due to workflow syntax errors
2. GREEN: Fix workflows to make tests pass
3. REFACTOR: Improve workflow quality while keeping tests green
"""

import gc
import subprocess
from pathlib import Path

import pytest

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


def get_workflow_files():
    """Get all workflow YAML files."""
    workflows_dir = Path(__file__).parent.parent / ".github" / "workflows"
    return list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))


@pytest.mark.parametrize("workflow_file", get_workflow_files(), ids=lambda f: f.name)
def test_workflow_syntax_valid(workflow_file):
    """
    Test that each workflow file passes actionlint syntax validation.

    This test runs actionlint on each workflow file to ensure:
    - YAML syntax is valid
    - GitHub Actions syntax is valid
    - Expression syntax is correct
    - Job dependencies are properly declared
    - Context usage is valid (no secrets.* in job-level if conditions)

    Expected to FAIL initially (RED phase) due to known issues:
    - deploy-production-gke.yaml:545 - missing build-and-push dependency
    - dora-metrics.yaml:242 - invalid secrets.* in job if
    - observability-alerts.yaml:119,206,253 - invalid secrets.* in job if
    """
    result = subprocess.run(
        ["actionlint", "-no-color", "-shellcheck=", str(workflow_file)], capture_output=True, text=True, timeout=60
    )

    # Collect all errors for better debugging
    errors = []
    if result.returncode != 0:
        errors.append(f"Workflow: {workflow_file.name}")
        errors.append(result.stdout)
        errors.append(result.stderr)

    # Assert with detailed error message
    assert result.returncode == 0, "\n".join(errors)


def test_actionlint_installed():
    """
    Verify that actionlint is installed and available.

    This is a prerequisite test that ensures the validation tool is present.
    """
    result = subprocess.run(["which", "actionlint"], capture_output=True, timeout=60)

    assert (
        result.returncode == 0
    ), "actionlint is not installed. Install with: go install github.com/rhysd/actionlint/cmd/actionlint@latest"


def test_workflows_directory_exists():
    """Verify that the workflows directory exists."""
    workflows_dir = Path(__file__).parent.parent / ".github" / "workflows"
    assert workflows_dir.exists(), f"Workflows directory not found: {workflows_dir}"
    assert workflows_dir.is_dir(), f"Workflows path is not a directory: {workflows_dir}"


def test_at_least_one_workflow_exists():
    """Verify that at least one workflow file exists."""
    workflow_files = get_workflow_files()
    assert len(workflow_files) > 0, "No workflow files found in .github/workflows/"
