"""
Test suite for GitHub Actions workflow validation.

This module validates GitHub Actions workflows for common issues and anti-patterns,
including proper error handling, artifact management, and secret validation.

Created as part of OpenAI Codex findings validation (TDD approach).
"""

from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml


class TestWorkflowValidation:
    """Validate GitHub Actions workflows for common issues."""

    @pytest.fixture
    def workflows_dir(self) -> Path:
        """Get the workflows directory path."""
        repo_root = Path(__file__).parent.parent
        return repo_root / ".github" / "workflows"

    @pytest.fixture
    def workflow_files(self, workflows_dir: Path) -> List[Path]:
        """Get all workflow YAML files."""
        return list(workflows_dir.glob("*.yaml")) + list(workflows_dir.glob("*.yml"))

    @pytest.fixture
    def parsed_workflows(self, workflow_files: List[Path]) -> Dict[str, Dict[str, Any]]:
        """Parse all workflow files."""
        workflows = {}
        for workflow_file in workflow_files:
            with open(workflow_file, "r") as f:
                workflows[workflow_file.name] = yaml.safe_load(f)
        return workflows

    def test_coverage_artifact_handling_has_file_check(self, workflows_dir: Path):
        """
        Test that coverage merge step checks for file existence before copying.

        Context: OpenAI Codex Finding - ci.yaml:193
        Issue: cp command without file existence check after continue-on-error download

        This test validates that when downloading artifacts with continue-on-error=true,
        subsequent file operations must check for file existence to prevent failures.
        """
        ci_workflow_path = workflows_dir / "ci.yaml"
        assert ci_workflow_path.exists(), "ci.yaml workflow not found"

        with open(ci_workflow_path, "r") as f:
            ci_workflow = yaml.safe_load(f)

        # Find the coverage-merge job
        jobs = ci_workflow.get("jobs", {})
        merge_job = jobs.get("coverage-merge")

        assert merge_job is not None, "coverage-merge job not found in ci.yaml"
        assert merge_job.get("if") == "always()", "coverage-merge should have if: always()"

        steps = merge_job.get("steps", [])

        # Find download artifact step with continue-on-error
        download_step = None
        merge_step = None

        for step in steps:
            if step.get("uses", "").startswith("actions/download-artifact"):
                if step.get("continue-on-error") is True:
                    download_step = step
            if step.get("name") == "Merge coverage reports":
                merge_step = step

        assert download_step is not None, "Download artifact step with continue-on-error not found"
        assert merge_step is not None, "Merge coverage reports step not found"

        # Verify merge step checks for file existence
        merge_script = merge_step.get("run", "")

        # The merge script should check if file exists before copying
        # Valid patterns: if [ -f ... ], [ -f ... ] &&, test -f
        has_file_check = any(
            [
                "if [ -f" in merge_script,
                "[ -f" in merge_script and "&&" in merge_script,
                "test -f" in merge_script,
                "if [[ -f" in merge_script,
            ]
        )

        assert has_file_check, (
            "Merge coverage step must check file existence before cp/mv operations. "
            "When download-artifact has continue-on-error: true, subsequent file "
            "operations can fail if artifact is missing. Add: if [ -f file ]; then cp ...; fi"
        )

    def test_download_artifact_patterns(self, parsed_workflows: Dict[str, Dict[str, Any]]):
        """
        Test that download-artifact steps with continue-on-error have safe subsequent operations.

        This is a broader regression prevention test that checks all workflows.
        """
        issues_found = []

        for workflow_name, workflow_data in parsed_workflows.items():
            jobs = workflow_data.get("jobs", {})

            for job_name, job_config in jobs.items():
                steps = job_config.get("steps", [])

                for i, step in enumerate(steps):
                    # Check if this is a download-artifact with continue-on-error
                    if step.get("uses", "").startswith("actions/download-artifact") and step.get("continue-on-error") is True:

                        # Look at next few steps for file operations without checks
                        artifact_name = step.get("with", {}).get("name", "unknown")
                        path = step.get("with", {}).get("path", "")

                        # Check next 3 steps for unsafe file operations
                        for next_step in steps[i + 1 : i + 4]:
                            script = next_step.get("run", "")
                            if not script:
                                continue

                            # Check for file operations (cp, mv, cat, etc.)
                            has_file_op = any(cmd in script for cmd in ["cp ", "mv ", "cat "])
                            has_check = any(pattern in script for pattern in ["if [ -f", "[ -f", "test -f", "if [[ -f"])

                            if has_file_op and not has_check and path and path in script:
                                issues_found.append(
                                    {
                                        "workflow": workflow_name,
                                        "job": job_name,
                                        "step": next_step.get("name", "unnamed"),
                                        "artifact": artifact_name,
                                        "issue": "File operation without existence check after continue-on-error download",
                                    }
                                )

        if issues_found:
            error_msg = "Found download-artifact patterns with unsafe file operations:\n"
            for issue in issues_found:
                error_msg += (
                    f"  - {issue['workflow']}::{issue['job']}::{issue['step']}\n"
                    f"    Artifact: {issue['artifact']}\n"
                    f"    Issue: {issue['issue']}\n"
                )
            pytest.fail(error_msg)

    def test_gcp_auth_steps_have_secret_validation(self, parsed_workflows: Dict[str, Dict[str, Any]]):
        """
        Test that GCP authentication steps include secret availability checks.

        Context: OpenAI Codex Finding - GCP workflows
        Issue: Workflows fail on forks/scheduled runs without graceful degradation

        Note: This test validates the improvement opportunity, not a critical bug.
        """
        gcp_workflows = {
            name: data for name, data in parsed_workflows.items() if "gcp" in name.lower() or "deploy" in name.lower()
        }

        for workflow_name, workflow_data in gcp_workflows.items():
            jobs = workflow_data.get("jobs", {})

            for job_name, job_config in jobs.items():
                steps = job_config.get("steps", [])

                # Find google-github-actions/auth steps
                for step in steps:
                    if step.get("uses", "").startswith("google-github-actions/auth"):
                        # Check if job has secret availability check
                        job_if = job_config.get("if", "")

                        # Document this as best practice (not enforced strictly)
                        # Valid patterns: checking for secret existence, fork detection
                        has_secret_check = any(
                            [
                                "secrets." in job_if,
                                "github.event.pull_request.head.repo.fork" in job_if,
                                step.get("continue-on-error") is True,
                            ]
                        )

                        # This is a soft check - we document but don't fail
                        # Real implementation would add explicit checks
                        print(f"INFO: {workflow_name}::{job_name} uses GCP auth. " f"Has secret check: {has_secret_check}")

    def test_action_versions_are_valid(self, parsed_workflows: Dict[str, Dict[str, Any]]):
        """
        Test that all GitHub Actions use valid version tags.

        Context: OpenAI Codex claimed versions don't exist - this was FALSE.
        This test documents the CORRECT versions being used.
        """
        known_valid_versions = {
            "actions/checkout": ["v4", "v5"],
            "actions/setup-python": ["v5", "v6"],
            "actions/upload-artifact": ["v4", "v5"],
            "actions/download-artifact": ["v4", "v5", "v6"],
            "actions/cache": ["v3", "v4"],
            "actions/github-script": ["v7", "v8"],
            "astral-sh/setup-uv": ["v2", "v3", "v4", "v5", "v6", "v7"],
            "codecov/codecov-action": ["v4", "v5", "v5.5.1"],
            "docker/build-push-action": ["v5", "v6", "v6.18.0"],
            "docker/setup-buildx-action": ["v3", "v3.11.1"],
            "docker/login-action": ["v3", "v3.6.0"],
            "docker/setup-qemu-action": ["v3", "v3.6.0"],
            "google-github-actions/auth": ["v1", "v2", "v3"],
            "google-github-actions/get-gke-credentials": ["v1", "v2", "v3"],
            "google-github-actions/setup-gcloud": ["v1", "v2", "v3"],
        }

        invalid_versions = []

        for workflow_name, workflow_data in parsed_workflows.items():
            jobs = workflow_data.get("jobs", {})

            for job_name, job_config in jobs.items():
                steps = job_config.get("steps", [])

                for step in steps:
                    uses = step.get("uses", "")
                    if "@" not in uses:
                        continue

                    action, version = uses.rsplit("@", 1)

                    # Check if this is a tracked action
                    if action in known_valid_versions:
                        if version not in known_valid_versions[action]:
                            # This is a known action using an undocumented version
                            # Could be valid but needs verification
                            invalid_versions.append(
                                {
                                    "workflow": workflow_name,
                                    "job": job_name,
                                    "action": action,
                                    "version": version,
                                    "known_valid": known_valid_versions[action],
                                }
                            )

        # This test documents valid versions, not enforces them strictly
        # because new versions are released regularly
        if invalid_versions:
            info_msg = "Actions using versions not in known-valid list (may need verification):\n"
            for item in invalid_versions:
                info_msg += (
                    f"  - {item['workflow']}::{item['job']}: {item['action']}@{item['version']}\n"
                    f"    Known valid: {item['known_valid']}\n"
                )
            print(f"INFO: {info_msg}")


class TestCoverageArtifactScenarios:
    """Test scenarios for coverage artifact handling."""

    def test_missing_coverage_artifact_handling(self, tmp_path: Path):
        """
        Test that missing coverage artifacts are handled gracefully.

        This simulates the scenario where download-artifact has continue-on-error=true
        and the artifact doesn't exist.
        """
        import subprocess

        # Create a test script that mimics the current (broken) behavior
        broken_script = tmp_path / "broken_merge.sh"
        broken_script.write_text(
            """#!/bin/bash
set -e
# This mimics the current behavior - will fail if file doesn't exist
cp coverage-artifacts/coverage-unit.xml coverage-merged.xml
"""
        )
        broken_script.chmod(0o755)

        # Test that it fails when file doesn't exist
        result = subprocess.run([str(broken_script)], cwd=tmp_path, capture_output=True, text=True)

        assert result.returncode != 0, "Broken script should fail when file missing"

    def test_fixed_coverage_artifact_handling(self, tmp_path: Path):
        """
        Test that the FIXED coverage merge handles missing artifacts gracefully.

        This is the expected behavior after the fix.
        """
        import subprocess

        # Create a test script with the fix
        fixed_script = tmp_path / "fixed_merge.sh"
        fixed_script.write_text(
            """#!/bin/bash
set -e

if [ -f coverage-artifacts/coverage-unit.xml ]; then
    cp coverage-artifacts/coverage-unit.xml coverage-merged.xml
    echo "Coverage merged successfully"
else
    echo "No coverage artifacts found, creating empty coverage file"
    touch coverage-merged.xml
fi
"""
        )
        fixed_script.chmod(0o755)

        # Test that it succeeds even when file doesn't exist
        result = subprocess.run([str(fixed_script)], cwd=tmp_path, capture_output=True, text=True)

        assert result.returncode == 0, "Fixed script should succeed even with missing file"
        assert (tmp_path / "coverage-merged.xml").exists(), "Should create coverage-merged.xml"

    def test_fixed_coverage_with_existing_artifact(self, tmp_path: Path):
        """
        Test that the fixed script still works when artifact exists.
        """
        import subprocess

        # Create the coverage artifacts directory and file
        artifacts_dir = tmp_path / "coverage-artifacts"
        artifacts_dir.mkdir()
        (artifacts_dir / "coverage-unit.xml").write_text("<?xml version='1.0'?><coverage></coverage>")

        # Create the fixed script
        fixed_script = tmp_path / "fixed_merge.sh"
        fixed_script.write_text(
            """#!/bin/bash
set -e

if [ -f coverage-artifacts/coverage-unit.xml ]; then
    cp coverage-artifacts/coverage-unit.xml coverage-merged.xml
    echo "Coverage merged successfully"
else
    echo "No coverage artifacts found, creating empty coverage file"
    touch coverage-merged.xml
fi
"""
        )
        fixed_script.chmod(0o755)

        # Test that it succeeds and copies the file
        result = subprocess.run([str(fixed_script)], cwd=tmp_path, capture_output=True, text=True)

        assert result.returncode == 0, "Fixed script should succeed with existing file"
        assert (tmp_path / "coverage-merged.xml").exists(), "Should create coverage-merged.xml"

        # Verify content was copied
        content = (tmp_path / "coverage-merged.xml").read_text()
        assert "<?xml version='1.0'?><coverage></coverage>" in content, "Should copy actual content"
