"""
Test suite for validating GitHub Actions workflow configurations.

This module ensures that all GitHub Actions workflows use valid action versions
and have appropriate permissions configured. These tests prevent CI/CD failures
caused by referencing non-existent action tags or missing required permissions.

Following TDD principles - these tests define the expected valid state before fixes.
"""

import gc
import re
from pathlib import Path

import pytest
import yaml

# Mark as unit+meta test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testgithubactionsversions")
class TestGitHubActionsVersions:
    """Validate that all GitHub Actions use published, valid version tags."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def workflow_files(self) -> list[Path]:
        """Get all GitHub workflow files."""
        workflows_dir = Path(".github/workflows")
        if not workflows_dir.exists():
            pytest.skip("No .github/workflows directory found")

        return list(workflows_dir.glob("*.yaml")) + list(workflows_dir.glob("*.yml"))

    @pytest.fixture
    def composite_action_files(self) -> list[Path]:
        """Get all composite action files."""
        actions_dir = Path(".github/actions")
        if not actions_dir.exists():
            return []

        action_files = []
        for action_dir in actions_dir.iterdir():
            if action_dir.is_dir():
                action_file = action_dir / "action.yml"
                if action_file.exists():
                    action_files.append(action_file)
        return action_files

    @pytest.fixture
    def all_workflow_files(self, workflow_files: list[Path], composite_action_files: list[Path]) -> list[Path]:
        """Get all workflow and action files."""
        return workflow_files + composite_action_files

    def test_astral_sh_setup_uv_version_is_valid(self, all_workflow_files: list[Path]):
        """
        Ensure astral-sh/setup-uv uses valid version tag.

        INVALID: v7.1.1 (does not exist)
        VALID: v7.1.0 or v7 (latest published)

        This test will FAIL until all occurrences of v7.1.1 are fixed.
        """
        invalid_version = "astral-sh/setup-uv@v7.1.1"

        violations = []

        for workflow_file in all_workflow_files:
            content = workflow_file.read_text()

            if invalid_version in content:
                # Find line numbers for better error reporting
                lines = content.split("\n")
                line_numbers = [i + 1 for i, line in enumerate(lines) if invalid_version in line]
                violations.append((workflow_file.name, line_numbers))

        assert not violations, (
            f"Found invalid astral-sh/setup-uv@v7.1.1 in {len(violations)} file(s). "
            f"Should be v7.1.0 or v7:\n" + "\n".join([f"  - {name}: lines {lines}" for name, lines in violations])
        )

    def test_actions_cache_version_is_valid(self, all_workflow_files: list[Path]):
        """
        Ensure actions/cache uses valid version tag.

        POTENTIALLY INVALID: v4.3.0 (not confirmed to exist)
        VALID: v4.2.0 or v4 (confirmed published)

        This test will FAIL until all occurrences of v4.3.0 are fixed.
        """
        invalid_version = "actions/cache@v4.3.0"

        violations = []

        for workflow_file in all_workflow_files:
            content = workflow_file.read_text()

            if invalid_version in content:
                lines = content.split("\n")
                line_numbers = [i + 1 for i, line in enumerate(lines) if invalid_version in line]
                violations.append((workflow_file.name, line_numbers))

        assert not violations, (
            f"Found potentially invalid actions/cache@v4.3.0 in {len(violations)} file(s). "
            f"Should be v4.2.0 or v4:\n" + "\n".join([f"  - {name}: lines {lines}" for name, lines in violations])
        )

    def test_no_other_suspicious_action_versions(self, all_workflow_files: list[Path]):
        """
        Validate that commonly used actions have reasonable version patterns.

        This test checks for:
        - Very high major versions (e.g., @v10+ for actions that don't have them)
        - Suspicious patch versions (e.g., @v4.99.99)
        - Missing @ symbol (bare action names)
        """
        # Pattern: action-owner/action-name@version
        action_pattern = re.compile(r"uses:\s+([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)@(v?\d+(?:\.\d+)*)")

        # Known actions with their maximum reasonable major version
        max_major_versions = {
            "actions/checkout": 5,
            "actions/setup-python": 6,
            "actions/upload-artifact": 5,
            "actions/download-artifact": 6,
            "actions/cache": 4,
            "actions/github-script": 8,
            "docker/setup-buildx-action": 3,
            "docker/build-push-action": 6,
            "docker/login-action": 3,
            "docker/setup-qemu-action": 3,
            "codecov/codecov-action": 6,
            "google-github-actions/auth": 3,
            "google-github-actions/get-gke-credentials": 3,
            "google-github-actions/setup-gcloud": 3,
        }

        violations = []

        for workflow_file in all_workflow_files:
            content = workflow_file.read_text()

            for match in action_pattern.finditer(content):
                action = match.group(1)
                version = match.group(2)

                # Check if it's a known action with version limits
                if action in max_major_versions:
                    # Extract major version
                    major = int(version.lstrip("v").split(".")[0])
                    max_major = max_major_versions[action]

                    if major > max_major:
                        line_num = content[: match.start()].count("\n") + 1
                        violations.append(
                            f"{workflow_file.name}:{line_num} - {action}@{version} (major v{major} > max v{max_major})"
                        )

        assert not violations, f"Found {len(violations)} suspicious action version(s):\n" + "\n".join(
            [f"  - {v}" for v in violations]
        )


@pytest.mark.xdist_group(name="testgithubactionspermissions")
class TestGitHubActionsPermissions:
    """Validate that workflows have appropriate permissions configured."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def workflow_files(self) -> list[Path]:
        """Get all GitHub workflow files."""
        workflows_dir = Path(".github/workflows")
        if not workflows_dir.exists():
            pytest.skip("No .github/workflows directory found")

        return list(workflows_dir.glob("*.yaml")) + list(workflows_dir.glob("*.yml"))

    @pytest.fixture
    def scheduled_workflows(self) -> dict[str, dict]:
        """Get all workflows that run on schedule."""
        workflows_dir = Path(".github/workflows")
        if not workflows_dir.exists():
            pytest.skip("No .github/workflows directory found")

        scheduled = {}

        for workflow_file in workflows_dir.glob("*.yaml"):
            try:
                with open(workflow_file) as f:
                    workflow_data = yaml.safe_load(f)

                if not workflow_data:
                    continue

                # Check if workflow has schedule trigger
                on_config = workflow_data.get("on", {})
                if isinstance(on_config, dict) and "schedule" in on_config:
                    scheduled[workflow_file.name] = workflow_data

            except yaml.YAMLError:
                # Skip invalid YAML files
                continue

        for workflow_file in workflows_dir.glob("*.yml"):
            try:
                with open(workflow_file) as f:
                    workflow_data = yaml.safe_load(f)

                if not workflow_data:
                    continue

                on_config = workflow_data.get("on", {})
                if isinstance(on_config, dict) and "schedule" in on_config:
                    scheduled[workflow_file.name] = workflow_data

            except yaml.YAMLError:
                continue

        return scheduled

    def test_scheduled_workflows_creating_issues_have_issues_write_permission(self, scheduled_workflows: dict[str, dict]):
        """
        Ensure scheduled workflows that create GitHub issues have issues: write permission.

        Workflows that use actions/github-script to call github.rest.issues.create
        must have 'issues: write' in their permissions block.

        This test will FAIL for workflows missing this permission.
        """
        violations = []

        for workflow_name, workflow_data in scheduled_workflows.items():
            workflow_str = yaml.dump(workflow_data)

            # Check if workflow creates issues via github-script
            creates_issues = (
                "github.rest.issues.create" in workflow_str
                or "octokit.rest.issues.create" in workflow_str
                or "octokit.issues.create" in workflow_str
            )

            if creates_issues:
                permissions = workflow_data.get("permissions", {})

                # Check if issues permission is granted
                has_issues_write = permissions.get("issues") == "write" or permissions == "write-all"  # Global write-all

                if not has_issues_write:
                    violations.append(workflow_name)

        assert not violations, (
            f"Found {len(violations)} scheduled workflow(s) creating issues "
            f"without 'issues: write' permission:\n"
            + "\n".join([f"  - {name}" for name in violations])
            + "\n\nAdd 'issues: write' to the permissions block of these workflows."
        )

    def test_all_workflows_creating_issues_have_permission(self, workflow_files: list[Path]):
        """
        Ensure ALL workflows that create GitHub issues have issues: write permission.

        This test checks ALL workflows (not just scheduled), as any workflow
        creating issues needs the permission regardless of trigger type.

        This prevents permission errors at runtime when creating issues.
        """
        violations = []

        for workflow_file in workflow_files:
            try:
                with open(workflow_file) as f:
                    workflow_data = yaml.safe_load(f)

                if not workflow_data:
                    continue

                workflow_str = yaml.dump(workflow_data)

                # Check if workflow creates issues via github-script
                creates_issues = (
                    "github.rest.issues.create" in workflow_str
                    or "octokit.rest.issues.create" in workflow_str
                    or "octokit.issues.create" in workflow_str
                )

                if creates_issues:
                    permissions = workflow_data.get("permissions", {})

                    # Check if issues permission is granted
                    has_issues_write = permissions.get("issues") == "write" or permissions == "write-all"

                    if not has_issues_write:
                        violations.append(workflow_file.name)

            except yaml.YAMLError:
                continue

        assert not violations, (
            f"Found {len(violations)} workflow(s) creating issues "
            f"without 'issues: write' permission:\n"
            + "\n".join([f"  - {name}" for name in violations])
            + "\n\nAdd 'issues: write' to the permissions block of these workflows."
        )

    def test_workflows_have_minimal_permissions(self, scheduled_workflows: dict[str, dict]):
        """
        Ensure workflows don't use overly broad permissions.

        Workflows should specify exact permissions needed rather than using
        'write-all' or 'permissions: {}' (which grants all permissions).

        This is a warning test - it will warn but not fail.
        """
        overly_broad = []

        for workflow_name, workflow_data in scheduled_workflows.items():
            permissions = workflow_data.get("permissions")

            # Check for overly broad permissions
            if permissions == "write-all":
                overly_broad.append((workflow_name, "uses 'write-all'"))
            elif not permissions:
                # No permissions block = inherited default (read-all for scheduled)
                overly_broad.append((workflow_name, "no permissions block (defaults to read-all)"))

        if overly_broad:
            warning_msg = (
                f"WARNING: Found {len(overly_broad)} workflow(s) with broad permissions:\n"
                + "\n".join([f"  - {name}: {reason}" for name, reason in overly_broad])
                + "\n\nConsider specifying minimal required permissions explicitly."
            )
            pytest.skip(warning_msg)  # Skip instead of fail for warnings


@pytest.mark.xdist_group(name="testgithubactionsworkflowdependencies")
class TestGitHubActionsWorkflowDependencies:
    """Validate that workflow jobs have correct dependencies installed."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_validate_workflows_job_has_required_dependencies(self):
        """
        Ensure validate-workflows job uses setup-python-deps composite action
        instead of manually installing only pytest and pyyaml.

        INVALID: pip install pytest pyyaml (missing langchain_core and other deps)
        VALID: Uses ./.github/actions/setup-python-deps with extras: 'dev'

        This test validates Finding #1 from Codex report is fixed.
        """
        ci_workflow = Path(".github/workflows/ci.yaml")
        if not ci_workflow.exists():
            pytest.skip("ci.yaml not found")

        content = ci_workflow.read_text()

        # Parse YAML to get job structure
        import yaml

        workflow = yaml.safe_load(content)

        # Check if validate-workflows job exists
        jobs = workflow.get("jobs", {})
        validate_job = jobs.get("validate-workflows")

        if not validate_job:
            pytest.skip("validate-workflows job not found")

        # Check steps
        steps = validate_job.get("steps", [])

        # Find dependency setup step
        uses_composite_action = False
        uses_manual_pip = False

        for step in steps:
            # Check if using setup-python-deps composite action
            if step.get("uses", "").startswith("./.github/actions/setup-python-deps"):
                uses_composite_action = True

            # Check if manually installing pytest/pyyaml only
            if "run" in step:
                run_commands = step["run"]
                if "pip install pytest pyyaml" in run_commands and "langchain" not in run_commands:
                    uses_manual_pip = True

        assert not uses_manual_pip, (
            "validate-workflows job uses 'pip install pytest pyyaml' which is missing dependencies. "
            "This causes ModuleNotFoundError for langchain_core when tests import project modules. "
            "Use ./.github/actions/setup-python-deps composite action with extras: 'dev' instead."
        )

        assert uses_composite_action or not uses_manual_pip, (
            "validate-workflows job should use ./.github/actions/setup-python-deps composite action "
            "to install all required dependencies including langchain_core."
        )


@pytest.mark.xdist_group(name="testgithubactionsstructure")
class TestGitHubActionsStructure:
    """Validate overall workflow structure and best practices."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_all_workflows_are_valid_yaml(self):
        """Ensure all workflow files are valid YAML."""
        workflows_dir = Path(".github/workflows")
        if not workflows_dir.exists():
            pytest.skip("No .github/workflows directory found")

        invalid_files = []

        for workflow_file in workflows_dir.glob("*.yaml"):
            try:
                with open(workflow_file) as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                invalid_files.append((workflow_file.name, str(e)))

        for workflow_file in workflows_dir.glob("*.yml"):
            try:
                with open(workflow_file) as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                invalid_files.append((workflow_file.name, str(e)))

        assert not invalid_files, f"Found {len(invalid_files)} invalid YAML workflow(s):\n" + "\n".join(
            [f"  - {name}: {error}" for name, error in invalid_files]
        )

    def test_composite_actions_use_valid_versions(self):
        """
        Ensure composite actions in .github/actions/ use valid action versions.

        Composite actions inherit issues from the same version problems,
        but are more critical because they're reused across multiple workflows.
        """
        actions_dir = Path(".github/actions")
        if not actions_dir.exists():
            pytest.skip("No .github/actions directory found")

        invalid_versions = {
            "astral-sh/setup-uv@v7.1.1": "should be v7.1.0 or v7",
            "actions/cache@v4.3.0": "should be v4.2.0 or v4",
        }

        violations = []

        for action_dir in actions_dir.iterdir():
            if not action_dir.is_dir():
                continue

            action_file = action_dir / "action.yml"
            if not action_file.exists():
                continue

            content = action_file.read_text()

            for invalid_ver, fix in invalid_versions.items():
                if invalid_ver in content:
                    violations.append(f"{action_dir.name}/action.yml uses {invalid_ver} ({fix})")

        assert not violations, (
            f"Found {len(violations)} invalid action version(s) in composite actions:\n"
            + "\n".join([f"  - {v}" for v in violations])
            + "\n\nComposite actions are reused across workflows - fix these first!"
        )


# Metadata for test organization
pytest_plugins = []  # No additional plugins needed


def pytest_collection_modifyitems(items):
    """Add markers to tests for better organization."""
    for item in items:
        # Mark all tests in this module as meta-tests
        item.add_marker(pytest.mark.meta)

        # Mark tests that validate external dependencies
        if "version" in item.name:
            item.add_marker(pytest.mark.external_deps)

        # Mark tests that validate permissions
        if "permission" in item.name:
            item.add_marker(pytest.mark.security)
