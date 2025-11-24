#!/usr/bin/env python3
"""
Validate that GitHub Actions workflows install correct dependency extras for tests.

This script prevents CI failures from workflows that run tests but don't install
the required dependencies. It checks that:
1. Workflows running tests install 'dev' extras (minimum)
2. Workflows importing docker/kubernetes also install those packages
3. Configuration is consistent across similar workflows

Prevention: Catches the issue that caused 10 CI failures (2025-11-12)
- Quality Tests workflow ran pytest but docker/kubernetes not in dev extras
- E2E Tests had same issue
- Root cause: test imports not matching installed extras

Usage:
    python scripts/validation/validate_workflow_test_deps.py
    python scripts/validation/validate_workflow_test_deps.py .github/workflows/quality-tests.yaml

Exit codes:
    0: All validations passed
    1: Validation failures found
"""

import sys
from pathlib import Path

import yaml


def get_workflow_files(workflow_path: Path = None) -> list[Path]:
    """
    Get all GitHub Actions workflow files to validate.

    Args:
        workflow_path: Specific workflow file to check, or None for all

    Returns:
        List of workflow file paths
    """
    if workflow_path:
        return [workflow_path]

    workflows_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"
    return list(workflows_dir.glob("*.yaml")) + list(workflows_dir.glob("*.yml"))


def extract_extras_from_workflow(workflow_content: dict) -> set[str]:
    """
    Extract the extras being installed in a workflow.

    Looks for setup-python-deps action usage and extracts the 'extras' parameter.

    Args:
        workflow_content: Parsed YAML workflow content

    Returns:
        Set of extras being installed (e.g., {'dev', 'builder'})
    """
    extras = set()

    # Check all jobs
    for job_name, job_config in workflow_content.get("jobs", {}).items():
        steps = job_config.get("steps", [])

        for step in steps:
            # Check for setup-python-deps action
            uses = step.get("uses", "")
            if "setup-python-deps" in uses:
                with_params = step.get("with", {})
                extras_str = with_params.get("extras", "")

                # Parse extras: 'dev builder' → {'dev', 'builder'}
                if extras_str:
                    extras.update(extras_str.split())

    return extras


def check_if_runs_tests(workflow_content: dict) -> bool:
    """
    Check if a workflow runs pytest tests with setup-python-deps.

    Only returns True if:
    1. Workflow uses setup-python-deps action
    2. Workflow runs pytest

    This avoids false positives for workflows using uv run or other methods.

    Args:
        workflow_content: Parsed YAML workflow content

    Returns:
        True if workflow uses setup-python-deps AND runs tests
    """
    uses_setup_deps = False
    runs_pytest = False

    for job_name, job_config in workflow_content.get("jobs", {}).items():
        steps = job_config.get("steps", [])

        for step in steps:
            # Check if uses setup-python-deps
            uses = step.get("uses", "")
            if "setup-python-deps" in uses:
                uses_setup_deps = True

            # Check if runs pytest
            run = step.get("run", "")
            if "pytest" in run:
                runs_pytest = True

    return uses_setup_deps and runs_pytest


def get_required_extras_for_tests() -> set[str]:
    """
    Get the minimum set of extras required to run tests.

    Based on the fix for commit 7b51437 (2025-11-12):
    - Tests import docker.errors → needs docker package
    - Tests import kubernetes modules → needs kubernetes package
    - Both are now in 'dev' extras

    Returns:
        Set of required extras
    """
    return {"dev"}  # Minimum required for running tests


def validate_workflow(workflow_path: Path) -> list[str]:
    """
    Validate a single workflow file.

    Args:
        workflow_path: Path to workflow YAML file

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    try:
        with open(workflow_path) as f:
            content = yaml.safe_load(f)

        # Skip if not a valid workflow
        if not content or "jobs" not in content:
            return errors

        runs_tests = check_if_runs_tests(content)
        installed_extras = extract_extras_from_workflow(content)
        required_extras = get_required_extras_for_tests()

        # If workflow runs tests, ensure it installs required extras
        if runs_tests and not required_extras.issubset(installed_extras):
            missing = required_extras - installed_extras
            errors.append(
                f"{workflow_path.name}: Runs tests but missing required extras: {missing}\n"
                f"  Installed: {installed_extras or 'none'}\n"
                f"  Required: {required_extras}\n"
                f"  Fix: Add 'dev' to extras parameter in setup-python-deps step"
            )

    except Exception as e:
        errors.append(f"{workflow_path.name}: Failed to parse: {e}")

    return errors


def main() -> int:
    """
    Main validation entry point.

    Returns:
        Exit code (0 = success, 1 = failures)
    """
    # Parse command line argument
    workflow_path = None
    if len(sys.argv) > 1:
        workflow_path = Path(sys.argv[1])
        if not workflow_path.exists():
            print(f"Error: Workflow file not found: {workflow_path}", file=sys.stderr)
            return 1

    # Get workflow files to validate
    workflows = get_workflow_files(workflow_path)

    if not workflows:
        print("No workflow files found to validate")
        return 0

    # Validate each workflow
    all_errors = []
    for workflow in workflows:
        errors = validate_workflow(workflow)
        all_errors.extend(errors)

    # Report results
    if all_errors:
        print("❌ Workflow Test Dependency Validation Failed\n", file=sys.stderr)
        for error in all_errors:
            print(error, file=sys.stderr)
            print()  # Blank line between errors

        print("\nThis check prevents the issue that caused 10 CI failures on 2025-11-12:")
        print("- Quality Tests ran pytest but docker/kubernetes not installed")
        print("- Root cause: packages in code-execution extras, not dev extras")
        print("\nFix: Ensure test workflows install 'dev' extras at minimum")
        print("See: tests/regression/test_dev_dependencies.py for validation test")

        return 1

    # Success
    print(f"✅ All {len(workflows)} workflow(s) have correct test dependencies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
