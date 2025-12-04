"""
Tests for staging GKE deployment workflow validation.

These tests ensure the CD pipeline and Kustomize configuration are correctly aligned,
preventing issues like:
- Image name mismatches that prevent pods from updating
- Missing rollout monitoring for dependent services
- Staging-production parity violations

See: ADR-0055 (Staging Deployment) and GitHub issue #xxx (pods not updating)
"""

import gc
import re
from pathlib import Path

import pytest
import yaml

# Module-level pytest markers for test categorization
# unit: These tests read file content only, no external dependencies
# ci: CI/CD pipeline validation tests
# deployment: Deployment configuration tests
# requires_kubectl: Tests reference kubectl commands (in workflow YAML validation)
#   Note: These tests don't actually RUN kubectl, they just validate workflow YAML
#   contains the correct kubectl commands. Marker satisfies meta-test detection.
pytestmark = [pytest.mark.unit, pytest.mark.ci, pytest.mark.deployment, pytest.mark.requires_kubectl]


@pytest.fixture(scope="module")
def workflow_content() -> str:
    """Load the staging GKE deployment workflow."""
    workflow_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "deploy-staging-gke.yaml"
    return workflow_path.read_text()


@pytest.fixture(scope="module")
def kustomization_content() -> dict:
    """Load the staging GKE kustomization.yaml."""
    kustomization_path = (
        Path(__file__).parent.parent.parent / "deployments" / "overlays" / "staging-gke" / "kustomization.yaml"
    )
    return yaml.safe_load(kustomization_path.read_text())


@pytest.mark.xdist_group(name="staging_deployment")
class TestImageNameConsistency:
    """Tests for image name consistency between workflow and kustomization."""

    def teardown_method(self) -> None:
        """Clean up after each test to prevent memory issues in xdist."""
        gc.collect()

    def test_workflow_uses_correct_kustomize_image_name(self, workflow_content: str, kustomization_content: dict) -> None:
        """
        Verify the workflow uses the correct image name that matches kustomization.yaml.

        The kustomize edit set image command must use the EXACT image name from
        kustomization.yaml's images[].name field, otherwise a new image entry
        is created instead of updating the existing one.

        Root cause: ghcr.io/vishnu2kmohan/mcp-server-langgraph vs mcp-server-langgraph mismatch
        """
        # Get the image name from kustomization.yaml
        images = kustomization_content.get("images", [])
        assert len(images) > 0, "Kustomization should have at least one image configuration"

        kustomization_image_name = images[0]["name"]
        assert kustomization_image_name, "Kustomization image name should not be empty"

        # Check the workflow uses the correct image name in kustomize edit set image
        # Pattern: kustomize edit set image <image-name>=<new-registry>
        # Note: Command may span multiple lines with backslash continuation
        kustomize_edit_pattern = r"kustomize edit set image\s*\\\n\s*(\S+)="

        match = re.search(kustomize_edit_pattern, workflow_content)
        assert match, "Workflow should contain 'kustomize edit set image' command"

        workflow_image_name = match.group(1)

        assert workflow_image_name == kustomization_image_name, (
            f"Image name mismatch! Workflow uses '{workflow_image_name}' "
            f"but kustomization.yaml uses '{kustomization_image_name}'. "
            "This causes the image tag to not be updated, resulting in pods not being recreated."
        )

    def test_kustomization_image_uses_full_registry_path(self, kustomization_content: dict) -> None:
        """
        Verify kustomization uses full registry path for image name matching.

        Codex Finding #6 (P1): Use full registry path to prevent ambiguity.
        """
        images = kustomization_content.get("images", [])
        assert len(images) > 0, "Kustomization should have image configuration"

        image_name = images[0]["name"]

        # Should be a full registry path, not just the image name
        assert "/" in image_name, f"Image name '{image_name}' should include registry path"
        assert image_name.startswith(("ghcr.io/", "gcr.io/", "docker.io/")), (
            f"Image name '{image_name}' should start with a known registry"
        )


@pytest.mark.xdist_group(name="staging_deployment")
class TestRolloutMonitoring:
    """Tests for deployment rollout monitoring coverage."""

    def teardown_method(self) -> None:
        """Clean up after each test to prevent memory issues in xdist."""
        gc.collect()

    def test_workflow_monitors_keycloak_deployment_rollout(self, workflow_content: str) -> None:
        """
        Verify the workflow monitors Keycloak deployment rollout.

        Missing rollout monitoring caused Keycloak CrashLoopBackOff to go undetected.
        """
        # Check for kubectl rollout status for Keycloak
        assert "staging-keycloak" in workflow_content, "Workflow should reference staging-keycloak deployment"
        assert "kubectl rollout status deployment/staging-keycloak" in workflow_content, (
            "Workflow should monitor Keycloak rollout status"
        )

    def test_workflow_monitors_openfga_deployment_rollout(self, workflow_content: str) -> None:
        """
        Verify the workflow monitors OpenFGA deployment rollout.

        All critical deployments should be monitored to prevent silent failures.
        """
        # Check for kubectl rollout status for OpenFGA
        assert "staging-openfga" in workflow_content, "Workflow should reference staging-openfga deployment"
        assert "kubectl rollout status deployment/staging-openfga" in workflow_content, (
            "Workflow should monitor OpenFGA rollout status"
        )

    def test_workflow_rollout_failures_block_pipeline_execution(self, workflow_content: str) -> None:
        """
        Verify rollout failures cause the pipeline to fail.

        The workflow should use blocking rollout checks, not just warnings.
        """
        # Look for the rollout step structure
        assert "Wait for rollout" in workflow_content, "Workflow should have a 'Wait for rollout' step"

        # The workflow should exit 1 on rollout failure
        assert "ROLLOUT_SUCCESS=false" in workflow_content or "exit 1" in workflow_content, (
            "Workflow should fail when deployments don't roll out successfully"
        )


@pytest.mark.xdist_group(name="staging_deployment")
class TestStagingProductionParity:
    """Tests for staging-production parity (12 Factor App compliance)."""

    def teardown_method(self) -> None:
        """Clean up after each test to prevent memory issues in xdist."""
        gc.collect()

    def test_staging_has_hpa_configuration_for_autoscaling(self, kustomization_content: dict) -> None:
        """
        Verify staging has HPA configuration for autoscaling parity.

        12 Factor App: "Keep development, staging, and production as similar as possible"
        """
        patches = kustomization_content.get("patches", [])
        patch_paths = [p.get("path", "") for p in patches if isinstance(p, dict)]

        assert "hpa-patch.yaml" in patch_paths, (
            "Staging should have HPA configuration for production parity. Missing hpa-patch.yaml in kustomization patches."
        )

    def test_staging_has_pdb_configuration_for_availability(self, kustomization_content: dict) -> None:
        """
        Verify staging has PodDisruptionBudget for availability parity.
        """
        resources = kustomization_content.get("resources", [])

        assert "pod-disruption-budget.yaml" in resources, (
            "Staging should have PodDisruptionBudget for production parity. "
            "Missing pod-disruption-budget.yaml in kustomization resources."
        )

    def test_staging_has_liveness_probe_patches_for_compliance(self, kustomization_content: dict) -> None:
        """
        Verify staging has differentiated liveness probes (kube-score compliance).

        kube-score requires readiness and liveness probes to be different.
        """
        patches = kustomization_content.get("patches", [])
        patch_paths = [p.get("path", "") for p in patches if isinstance(p, dict)]

        required_probe_patches = [
            "openfga-liveness-probe-patch.yaml",
            "otel-collector-liveness-probe-patch.yaml",
            "qdrant-liveness-probe-patch.yaml",
        ]

        for patch in required_probe_patches:
            assert patch in patch_paths, (
                f"Staging should have {patch} for kube-score compliance. Liveness and readiness probes must be differentiated."
            )


@pytest.mark.xdist_group(name="staging_deployment")
class TestGracefulShutdown:
    """Tests for graceful shutdown configuration."""

    def teardown_method(self) -> None:
        """Clean up after each test to prevent memory issues in xdist."""
        gc.collect()

    @pytest.fixture(scope="class")
    def staging_deployment_patch_content(self) -> dict:
        """Load the staging deployment patch."""
        patch_path = Path(__file__).parent.parent.parent / "deployments" / "overlays" / "staging-gke" / "deployment-patch.yaml"
        return yaml.safe_load(patch_path.read_text())

    def test_staging_has_termination_grace_period_configured(self, staging_deployment_patch_content: dict) -> None:
        """
        Verify staging deployment has terminationGracePeriodSeconds configured.

        LLM requests can take 30-60s, so pods need adequate time to finish.
        """
        spec = staging_deployment_patch_content.get("spec", {}).get("template", {}).get("spec", {})

        termination_grace_period = spec.get("terminationGracePeriodSeconds")

        assert termination_grace_period is not None, "Staging deployment should have terminationGracePeriodSeconds configured"
        assert termination_grace_period >= 60, (
            f"terminationGracePeriodSeconds ({termination_grace_period}) should be at least 60s "
            "to allow LLM requests to complete"
        )

    def test_staging_has_prestop_hook_for_draining(self, staging_deployment_patch_content: dict) -> None:
        """
        Verify staging deployment has preStop lifecycle hook.

        preStop hook allows load balancer to drain connections before SIGTERM.
        """
        containers = staging_deployment_patch_content.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])

        main_container = next((c for c in containers if c.get("name") == "mcp-server-langgraph"), None)
        assert main_container is not None, "Staging patch should define main container"

        lifecycle = main_container.get("lifecycle", {})
        prestop = lifecycle.get("preStop")

        assert prestop is not None, "Main container should have preStop lifecycle hook for graceful shutdown"

    def test_staging_has_startup_probe_for_slow_starts(self, staging_deployment_patch_content: dict) -> None:
        """
        Verify staging deployment has startupProbe configured.

        startupProbe prevents liveness/readiness probes from running until app is started.
        """
        containers = staging_deployment_patch_content.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])

        main_container = next((c for c in containers if c.get("name") == "mcp-server-langgraph"), None)
        assert main_container is not None, "Staging patch should define main container"

        startup_probe = main_container.get("startupProbe")

        assert startup_probe is not None, (
            "Main container should have startupProbe. Without startupProbe, liveness probe may kill pods during slow startup."
        )
