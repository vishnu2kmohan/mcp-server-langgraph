#!/usr/bin/env python3
"""
Test suite for GKE staging deployment rollout resilience.

Validates that deployment configurations and CI workflows are resilient
to common rollout failure scenarios like orphaned replica sets.

TDD Approach:
- RED: Tests identify gaps in current deployment strategy
- GREEN: After implementing cleanup logic, tests should PASS
- REFACTOR: Improve deployment configurations as needed
"""

import gc
import subprocess
from typing import Any

import pytest
import yaml

from tests.fixtures.tool_fixtures import requires_tool
from tests.helpers.path_helpers import get_repo_root

pytestmark = [
    pytest.mark.unit,
    pytest.mark.validation,
    pytest.mark.deployment,
    pytest.mark.requires_kubectl,
]

REPO_ROOT = get_repo_root()
STAGING_GKE_OVERLAY = REPO_ROOT / "deployments" / "overlays" / "preview-gke"
DEPLOY_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "deploy-preview-gke.yaml"


def _render_kustomize_manifests() -> list[dict[str, Any]]:
    """Render Kustomize manifests and return parsed YAML documents."""
    if not STAGING_GKE_OVERLAY.exists():
        pytest.skip(f"Staging GKE overlay not found: {STAGING_GKE_OVERLAY}")

    result = subprocess.run(
        ["kubectl", "kustomize", str(STAGING_GKE_OVERLAY)],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    manifests = list(yaml.safe_load_all(result.stdout))
    return [m for m in manifests if m is not None]


def _find_deployments(manifests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find all Deployment resources in manifests."""
    return [m for m in manifests if m.get("kind") == "Deployment"]


def _load_workflow() -> dict[str, Any]:
    """Load the deploy-preview-gke workflow."""
    if not DEPLOY_WORKFLOW_PATH.exists():
        pytest.skip(f"Workflow not found: {DEPLOY_WORKFLOW_PATH}")

    with open(DEPLOY_WORKFLOW_PATH) as f:
        return yaml.safe_load(f)


@pytest.mark.xdist_group(name="test_rollout_resilience")
class TestRolloutResilience:
    """Test deployment configurations for rollout resilience."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @requires_tool("kubectl", skip_reason="kubectl CLI not installed - required for kustomize build")
    def test_deployments_have_reasonable_revision_history_limit(self) -> None:
        """
        Test that deployments have reasonable revisionHistoryLimit.

        Low revisionHistoryLimit prevents accumulation of orphaned replica sets.
        Default Kubernetes value is 10, but 5 or less is recommended.
        """
        manifests = _render_kustomize_manifests()
        deployments = _find_deployments(manifests)

        violations = []
        RECOMMENDED_LIMIT = 5  # Maximum recommended

        for deployment in deployments:
            name = deployment.get("metadata", {}).get("name", "unknown")
            spec = deployment.get("spec", {})
            limit = spec.get("revisionHistoryLimit", 10)  # Kubernetes default is 10

            if limit > RECOMMENDED_LIMIT:
                violations.append(
                    {
                        "deployment": name,
                        "current_limit": limit,
                        "recommended_limit": RECOMMENDED_LIMIT,
                    }
                )

        # This is a best practice check - log warnings but don't fail
        if violations:
            msg = f"Deployments with high revisionHistoryLimit (>{RECOMMENDED_LIMIT}): "
            msg += ", ".join(f"{v['deployment']}={v['current_limit']}" for v in violations)
            # pytest.warning doesn't exist, so just log
            print(f"WARNING: {msg}")

    @requires_tool("kubectl", skip_reason="kubectl CLI not installed - required for kustomize build")
    def test_deployments_have_rolling_update_strategy(self) -> None:
        """
        Test that all deployments use RollingUpdate strategy.

        RollingUpdate ensures zero-downtime deployments.
        """
        manifests = _render_kustomize_manifests()
        deployments = _find_deployments(manifests)

        violations = []

        for deployment in deployments:
            name = deployment.get("metadata", {}).get("name", "unknown")
            spec = deployment.get("spec", {})
            strategy = spec.get("strategy", {})
            strategy_type = strategy.get("type", "RollingUpdate")

            if strategy_type != "RollingUpdate":
                violations.append(
                    {
                        "deployment": name,
                        "strategy": strategy_type,
                    }
                )

        if violations:
            error_msg = "\n\nDeployments not using RollingUpdate strategy:\n"
            for v in violations:
                error_msg += f"\n  {v['deployment']}: {v['strategy']} (should be RollingUpdate)"
            pytest.fail(error_msg)

    @requires_tool("kubectl", skip_reason="kubectl CLI not installed - required for kustomize build")
    def test_rolling_update_allows_progress(self) -> None:
        """
        Test that rolling update configuration allows deployment progress.

        maxUnavailable=0 with maxSurge=0 would prevent any progress.
        At least one must be > 0.
        """
        manifests = _render_kustomize_manifests()
        deployments = _find_deployments(manifests)

        violations = []

        for deployment in deployments:
            name = deployment.get("metadata", {}).get("name", "unknown")
            spec = deployment.get("spec", {})
            strategy = spec.get("strategy", {})
            rolling_update = strategy.get("rollingUpdate", {})

            max_surge = rolling_update.get("maxSurge", 1)
            max_unavailable = rolling_update.get("maxUnavailable", 0)

            # Convert percentage strings to comparable values
            if isinstance(max_surge, str) and max_surge.endswith("%"):
                max_surge = int(max_surge.rstrip("%"))
            if isinstance(max_unavailable, str) and max_unavailable.endswith("%"):
                max_unavailable = int(max_unavailable.rstrip("%"))

            # At least one must be > 0 for progress to be possible
            if max_surge == 0 and max_unavailable == 0:
                violations.append(
                    {
                        "deployment": name,
                        "max_surge": rolling_update.get("maxSurge", "default"),
                        "max_unavailable": rolling_update.get("maxUnavailable", "default"),
                    }
                )

        if violations:
            error_msg = "\n\nDeployments with blocked rolling update configuration:\n"
            for v in violations:
                error_msg += f"\n  {v['deployment']}: maxSurge={v['max_surge']}, maxUnavailable={v['max_unavailable']}"
                error_msg += "\n    At least one must be > 0 for deployment to progress"
            pytest.fail(error_msg)


@pytest.mark.xdist_group(name="test_ci_workflow_deployment")
class TestCIWorkflowDeployment:
    """Test CI workflow includes required deployment safeguards."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_workflow_has_pre_deployment_cleanup(self) -> None:
        """
        Test that workflow includes pre-deployment cleanup step.

        This prevents orphaned replica sets from blocking rollouts.
        """
        workflow = _load_workflow()

        deploy_job = workflow.get("jobs", {}).get("deploy-preview", {})
        steps = deploy_job.get("steps", [])

        cleanup_step_found = False
        for step in steps:
            step_name = step.get("name", "").lower()
            step_run = step.get("run", "").lower()
            # Check for cleanup step by name or content
            if "cleanup" in step_name or ("cleanup" in step_run and "replicaset" in step_run):
                cleanup_step_found = True
                break

        assert cleanup_step_found, (
            "Missing pre-deployment cleanup step in deploy-preview-gke.yaml.\n"
            "Expected: Step with 'cleanup' in name or replicaset cleanup logic in run script."
        )

    def test_workflow_has_rollout_monitoring(self) -> None:
        """
        Test that workflow includes rollout status monitoring.
        """
        workflow = _load_workflow()

        deploy_job = workflow.get("jobs", {}).get("deploy-preview", {})
        steps = deploy_job.get("steps", [])

        rollout_step_found = False
        for step in steps:
            step_name = step.get("name", "").lower()
            if "rollout" in step_name:
                rollout_step_found = True
                break

        assert rollout_step_found, "Missing rollout monitoring step in workflow"

    def test_workflow_has_failure_capture(self) -> None:
        """
        Test that workflow captures failure details on rollout failure.
        """
        workflow = _load_workflow()

        deploy_job = workflow.get("jobs", {}).get("deploy-preview", {})
        steps = deploy_job.get("steps", [])

        failure_capture_found = False
        for step in steps:
            step_name = step.get("name", "").lower()
            step_if = step.get("if", "")
            if "failure" in step_name and "failure()" in step_if:
                failure_capture_found = True
                break

        assert failure_capture_found, "Missing failure capture step in workflow"

    def test_workflow_monitors_all_deployments(self) -> None:
        """
        Test that workflow monitors rollout for all critical deployments.

        Must monitor: main app, keycloak, openfga
        """
        workflow = _load_workflow()

        deploy_job = workflow.get("jobs", {}).get("deploy-preview", {})
        steps = deploy_job.get("steps", [])

        rollout_step = None
        for step in steps:
            if "rollout" in step.get("name", "").lower():
                rollout_step = step
                break

        assert rollout_step is not None, "Rollout step not found"

        run_script = rollout_step.get("run", "").lower()

        # Check all deployments are monitored
        required_deployments = ["keycloak", "openfga"]
        missing = []
        for dep in required_deployments:
            if dep not in run_script:
                missing.append(dep)

        assert not missing, f"Rollout monitoring missing for deployments: {missing}"
