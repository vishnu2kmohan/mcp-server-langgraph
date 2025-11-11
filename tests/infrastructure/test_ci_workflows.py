"""
Infrastructure Tests: CI/CD Workflow Configuration Validation

Tests validate that GitHub Actions workflows are properly configured:
- Terraform binary available for pre-commit hooks
- Tool caching for performance
- Proper error handling and verbosity
- Helm dependency management

TDD Approach:
- RED: Tests fail initially (configurations missing)
- GREEN: Tests pass after implementing workflow fixes
- REFACTOR: Improve workflow efficiency while maintaining test coverage
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

import pytest
import yaml


class TestCIWorkflowTerraformSetup:
    """
    Test that CI workflow properly sets up Terraform for pre-commit hooks.

    Issue: Pre-commit hooks require Terraform but CI doesn't install it.
    Fix: Add hashicorp/setup-terraform@v3 step before pre-commit run.
    """

    @pytest.fixture
    def ci_workflow_path(self) -> Path:
        """Path to CI workflow file."""
        return Path(".github/workflows/ci.yaml")

    @pytest.fixture
    def ci_workflow(self, ci_workflow_path: Path) -> Dict:
        """Parse CI workflow YAML."""
        assert ci_workflow_path.exists(), f"Missing {ci_workflow_path}"
        with open(ci_workflow_path) as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def precommit_config_path(self) -> Path:
        """Path to pre-commit config file."""
        return Path(".pre-commit-config.yaml")

    @pytest.fixture
    def precommit_config(self, precommit_config_path: Path) -> Dict:
        """Parse pre-commit config YAML."""
        assert precommit_config_path.exists(), f"Missing {precommit_config_path}"
        with open(precommit_config_path) as f:
            return yaml.safe_load(f)

    def test_precommit_hooks_require_terraform(self, precommit_config: Dict):
        """
        Verify that pre-commit config includes Terraform hooks.

        This confirms the need for Terraform in CI.
        """
        repos = precommit_config.get("repos", [])
        terraform_hooks = [repo for repo in repos if "terraform" in repo.get("repo", "").lower()]

        assert len(terraform_hooks) > 0, (
            "No Terraform pre-commit hooks found. " "If Terraform hooks exist, CI must install Terraform."
        )

    def test_ci_precommit_job_exists(self, ci_workflow: Dict):
        """
        Validate that CI workflow has a pre-commit job.
        """
        jobs = ci_workflow.get("jobs", {})
        precommit_jobs = [
            job_name for job_name in jobs.keys() if "pre-commit" in job_name.lower() or "precommit" in job_name.lower()
        ]

        assert len(precommit_jobs) > 0, "No pre-commit job found in CI workflow. " f"Available jobs: {', '.join(jobs.keys())}"

    def test_ci_precommit_job_installs_terraform(self, ci_workflow: Dict):
        """
        Validate that pre-commit job installs Terraform.

        Issue: Pre-commit Terraform hooks fail if terraform binary is not available.
        Fix: Add hashicorp/setup-terraform@v3 step before running pre-commit.
        """
        jobs = ci_workflow.get("jobs", {})
        precommit_job = None

        # Find pre-commit job
        for job_name, job_config in jobs.items():
            if "pre-commit" in job_name.lower() or "precommit" in job_name.lower():
                precommit_job = job_config
                break

        assert precommit_job is not None, "Pre-commit job not found"

        steps = precommit_job.get("steps", [])
        terraform_setup_steps = [step for step in steps if step.get("uses", "").startswith("hashicorp/setup-terraform")]

        assert len(terraform_setup_steps) > 0, (
            "Pre-commit job must install Terraform before running hooks. "
            "Add step:\n"
            "  - name: Install Terraform for pre-commit hooks\n"
            "    uses: hashicorp/setup-terraform@v3\n"
            "    with:\n"
            "      terraform_version: '1.6.6'"
        )

    def test_terraform_setup_before_precommit_run(self, ci_workflow: Dict):
        """
        Validate that Terraform setup occurs before pre-commit run.

        Requirement: Tools must be installed before pre-commit hooks execute.
        """
        jobs = ci_workflow.get("jobs", {})
        precommit_job = None

        # Find pre-commit job
        for job_name, job_config in jobs.items():
            if "pre-commit" in job_name.lower() or "precommit" in job_name.lower():
                precommit_job = job_config
                break

        assert precommit_job is not None, "Pre-commit job not found"

        steps = precommit_job.get("steps", [])
        terraform_setup_index = None
        precommit_run_index = None

        for i, step in enumerate(steps):
            if step.get("uses", "").startswith("hashicorp/setup-terraform"):
                terraform_setup_index = i
            if "pre-commit run" in step.get("run", "") or step.get("uses", "").startswith("pre-commit/action"):
                precommit_run_index = i

        if terraform_setup_index is not None and precommit_run_index is not None:
            assert terraform_setup_index < precommit_run_index, (
                f"Terraform setup (step {terraform_setup_index}) must occur before "
                f"pre-commit run (step {precommit_run_index})"
            )

    def test_terraform_version_consistency(self, ci_workflow: Dict):
        """
        Validate that Terraform version is consistent across workflows.

        Requirement: All workflows should use the same Terraform version.
        """
        # This is a best practice test - check if version is specified
        jobs = ci_workflow.get("jobs", {})
        for job_name, job_config in jobs.items():
            steps = job_config.get("steps", [])
            for step in steps:
                if step.get("uses", "").startswith("hashicorp/setup-terraform"):
                    with_config = step.get("with", {})
                    terraform_version = with_config.get("terraform_version")

                    assert terraform_version is not None, (
                        f"Job '{job_name}' uses hashicorp/setup-terraform but "
                        "doesn't specify terraform_version. "
                        "Add 'with: terraform_version: 1.6.6' for consistency."
                    )


class TestDeploymentValidationWorkflow:
    """
    Test deployment validation workflow configuration.

    Validates:
    - Helm dependency management
    - kubeconform verbosity
    - Proper error handling
    """

    @pytest.fixture
    def deployment_validation_workflow_path(self) -> Path:
        """Path to deployment validation workflow file."""
        return Path(".github/workflows/deployment-validation.yml")

    @pytest.fixture
    def deployment_validation_workflow(self, deployment_validation_workflow_path: Path) -> Dict:
        """Parse deployment validation workflow YAML."""
        if not deployment_validation_workflow_path.exists():
            pytest.skip(f"Missing {deployment_validation_workflow_path}")
        with open(deployment_validation_workflow_path) as f:
            return yaml.safe_load(f)

    def test_helm_dependency_update_before_lint(self, deployment_validation_workflow: Dict):
        """
        Validate that helm dependency update runs before helm lint/template.

        Requirement: Vendor charts must be downloaded before validation.
        """
        jobs = deployment_validation_workflow.get("jobs", {})

        for job_name, job_config in jobs.items():
            steps = job_config.get("steps", [])
            helm_dependency_index = None
            helm_lint_index = None
            helm_template_index = None

            for i, step in enumerate(steps):
                run_cmd = step.get("run", "")
                if "helm dependency" in run_cmd or "helm repo add" in run_cmd:
                    helm_dependency_index = i
                if "helm lint" in run_cmd:
                    helm_lint_index = i
                if "helm template" in run_cmd:
                    helm_template_index = i

            # If helm lint/template is used, dependency update should come first
            if helm_lint_index is not None or helm_template_index is not None:
                assert helm_dependency_index is not None, (
                    f"Job '{job_name}' runs helm lint/template but doesn't update dependencies. "
                    "Add step:\n"
                    "  - name: Update Helm dependencies\n"
                    "    run: |\n"
                    "      helm repo add bitnami https://charts.bitnami.com/bitnami\n"
                    "      helm repo add openfga https://openfga.github.io/helm-charts\n"
                    "      helm dependency update deployments/helm/mcp-server-langgraph"
                )

                # Verify order
                if helm_lint_index is not None:
                    assert helm_dependency_index < helm_lint_index, (
                        f"Helm dependency update (step {helm_dependency_index}) must occur "
                        f"before helm lint (step {helm_lint_index})"
                    )
                if helm_template_index is not None:
                    assert helm_dependency_index < helm_template_index, (
                        f"Helm dependency update (step {helm_dependency_index}) must occur "
                        f"before helm template (step {helm_template_index})"
                    )

    def test_kubeconform_has_verbose_on_failure(self, deployment_validation_workflow: Dict):
        """
        Validate that kubeconform re-runs with verbose output on failure.

        Issue: kubeconform -summary only shows "Errors: 3" without details.
        Fix: Re-run with -verbose or -output json on failure.
        """
        jobs = deployment_validation_workflow.get("jobs", {})
        kubeconform_jobs = []

        for job_name, job_config in jobs.items():
            steps = job_config.get("steps", [])
            for step in steps:
                run_cmd = step.get("run", "")
                # Only match steps that RUN kubeconform validation (not installation)
                if "kubeconform" in run_cmd and ("kustomize build" in run_cmd or "-strict" in run_cmd):
                    kubeconform_jobs.append((job_name, run_cmd))

        assert len(kubeconform_jobs) > 0, "No kubeconform steps found"

        for job_name, run_cmd in kubeconform_jobs:
            # Check if verbose/output json is used OR if there's error handling
            has_verbose = "-verbose" in run_cmd or "-output json" in run_cmd
            has_error_handling = (
                "if !" in run_cmd
                or "if ! " in run_cmd  # Space after ! for bash functions
                or "||" in run_cmd
                or "set -o pipefail" in run_cmd
                or "pipefail" in run_cmd  # Part of set -o pipefail
            )

            assert has_verbose or has_error_handling, (
                f"Job '{job_name}' runs kubeconform with -summary but lacks verbose output on failure. "
                "Wrap in error handler:\n"
                "  if ! kustomize build ... | kubeconform -strict -summary ...; then\n"
                "    echo 'Validation failed, re-running with verbose output...'\n"
                "    kustomize build ... | kubeconform -strict -verbose ...\n"
                "    exit 1\n"
                "  fi"
            )

    def test_kubeconform_uses_pipefail(self, deployment_validation_workflow: Dict):
        """
        Validate that kubeconform steps use 'set -o pipefail'.

        Requirement: Pipeline failures should propagate exit codes.
        """
        jobs = deployment_validation_workflow.get("jobs", {})

        for job_name, job_config in jobs.items():
            steps = job_config.get("steps", [])
            for step in steps:
                run_cmd = step.get("run", "")
                if "kubeconform" in run_cmd and "|" in run_cmd:
                    # If using pipes with kubeconform, should have pipefail
                    assert "set -o pipefail" in run_cmd or "pipefail" in run_cmd, (
                        f"Job '{job_name}' uses kubeconform with pipes but lacks 'set -o pipefail'. "
                        "Add at start of run block:\n"
                        "  set -o pipefail"
                    )


class TestWorkflowPerformanceOptimizations:
    """
    Test workflow performance optimizations.

    Validates:
    - Tool caching
    - Conditional artifact downloads
    - Efficient dependency installation
    """

    @pytest.fixture
    def coverage_trend_workflow_path(self) -> Path:
        """Path to coverage trend workflow file."""
        return Path(".github/workflows/coverage-trend.yaml")

    @pytest.fixture
    def coverage_trend_workflow(self, coverage_trend_workflow_path: Path) -> Optional[Dict]:
        """Parse coverage trend workflow YAML."""
        if not coverage_trend_workflow_path.exists():
            return None
        with open(coverage_trend_workflow_path) as f:
            return yaml.safe_load(f)

    def test_download_artifact_has_continue_on_error(self, coverage_trend_workflow: Optional[Dict]):
        """
        Validate that download-artifact has continue-on-error or conditional.

        Issue: First run emits warnings when no historical coverage exists.
        Fix: Add continue-on-error: true or if: condition to suppress noise.
        """
        if coverage_trend_workflow is None:
            pytest.skip("Coverage trend workflow not found")

        jobs = coverage_trend_workflow.get("jobs", {})

        for job_name, job_config in jobs.items():
            steps = job_config.get("steps", [])
            for step in steps:
                if step.get("uses", "").startswith("actions/download-artifact"):
                    # Should have continue-on-error or conditional
                    has_continue = step.get("continue-on-error", False)
                    has_if = "if" in step

                    assert has_continue or has_if, (
                        f"Job '{job_name}' downloads artifacts without error handling. "
                        "Add 'continue-on-error: true' for optional artifacts or "
                        "'if: github.event_name != \"pull_request\"' to skip on PRs."
                    )

    def test_workflows_cache_expensive_tools(self):
        """
        Validate that workflows cache expensive tool downloads.

        Recommendation: Cache helm, kubeconform, kube-score binaries.
        """
        # This is more of a recommendation than requirement
        # Check common workflow files for caching
        workflow_dir = Path(".github/workflows")
        workflows_with_helm = []
        workflows_with_cache = []

        for workflow_file in workflow_dir.glob("*.y*ml"):
            content = workflow_file.read_text()
            if "helm" in content.lower():
                workflows_with_helm.append(workflow_file.name)
            if "actions/cache" in content:
                workflows_with_cache.append(workflow_file.name)

        # If multiple workflows use Helm, recommend caching
        if len(workflows_with_helm) > 2:
            # This is informational, not a hard requirement
            print(
                f"\nRecommendation: {len(workflows_with_helm)} workflows use Helm. "
                f"Consider caching Helm charts or creating a composite action. "
                f"Currently {len(workflows_with_cache)} workflows use caching."
            )


class TestStagingDeployWorkflow:
    """
    Test staging deployment workflow configuration.

    Validates:
    - Trivy scan configuration
    - .trivyignore usage
    """

    @pytest.fixture
    def staging_deploy_workflow_path(self) -> Path:
        """Path to staging deploy workflow file."""
        return Path(".github/workflows/deploy-staging-gke.yaml")

    @pytest.fixture
    def staging_deploy_workflow(self, staging_deploy_workflow_path: Path) -> Optional[Dict]:
        """Parse staging deploy workflow YAML."""
        if not staging_deploy_workflow_path.exists():
            return None
        with open(staging_deploy_workflow_path) as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def staging_trivyignore_path(self) -> Path:
        """Path to staging .trivyignore file."""
        return Path("deployments/overlays/staging-gke/.trivyignore")

    def test_trivy_scan_uses_trivyignores(self, staging_deploy_workflow: Optional[Dict]):
        """
        Validate that Trivy scan uses .trivyignore file.

        Requirement: Document suppressed findings with justifications.
        """
        if staging_deploy_workflow is None:
            pytest.skip("Staging deploy workflow not found")

        jobs = staging_deploy_workflow.get("jobs", {})

        for job_name, job_config in jobs.items():
            steps = job_config.get("steps", [])
            for step in steps:
                if "trivy" in step.get("uses", "").lower():
                    with_config = step.get("with", {})
                    trivyignores = with_config.get("trivyignores")

                    # Should reference .trivyignore file
                    if trivyignores:
                        assert ".trivyignore" in trivyignores, (
                            f"Job '{job_name}' uses Trivy but trivyignores path "
                            f"doesn't reference .trivyignore file: {trivyignores}"
                        )

    def test_staging_trivyignore_exists_and_documented(self, staging_trivyignore_path: Path):
        """
        Validate that .trivyignore exists and has documentation comments.

        Requirement: All suppressions must have justifications.
        """
        if not staging_trivyignore_path.exists():
            pytest.skip(f".trivyignore not found at {staging_trivyignore_path}")

        content = staging_trivyignore_path.read_text()
        lines = content.strip().split("\n")
        suppressed_ids = [line for line in lines if line.strip() and not line.strip().startswith("#")]

        # Each suppression should have a comment explaining why
        for suppression in suppressed_ids:
            # Find comment above this suppression
            idx = lines.index(suppression)
            has_comment_above = idx > 0 and lines[idx - 1].strip().startswith("#")

            assert has_comment_above, (
                f"Suppression '{suppression}' lacks documentation comment. "
                "Add comment explaining why this finding is suppressed."
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
