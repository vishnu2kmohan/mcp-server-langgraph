"""
Test that Trivy security scanning uses rendered manifests instead of raw patches.

This test validates the fix for the Codex finding where Trivy was scanning
raw Kustomize overlay patches directly, producing false positives because
security contexts from base manifests were not visible.

The correct approach is to:
1. Render the complete manifest using `kubectl kustomize`
2. Scan the rendered output with Trivy
3. Ensure security contexts are properly evaluated in context

Reference: Codex finding - Deploy to GKE Staging (run 19250053057) failures
"""

from pathlib import Path

import pytest
import yaml

from tests.fixtures.tool_fixtures import requires_tool

# Mark as unit+meta test to ensure it runs in CI
pytestmark = pytest.mark.unit


def test_deploy_staging_gke_workflow_renders_manifests_before_trivy_scan():
    """
    Verify that the deploy-staging-gke workflow renders Kustomize manifests
    before running Trivy security scans.

    This prevents false positives from scanning incomplete patch files.

    Expected workflow structure:
    1. Step: Render Kustomize manifests
       - Run: kubectl kustomize deployments/overlays/staging-gke > /tmp/staging-manifests.yaml
    2. Step: Security scan rendered manifests
       - scan-ref: /tmp/staging-manifests.yaml (NOT the overlay directory)
    """
    repo_root = Path(__file__).parent.parent.parent
    workflow_path = repo_root / ".github/workflows/deploy-staging-gke.yaml"

    assert workflow_path.exists(), f"Workflow file not found: {workflow_path}"

    with open(workflow_path) as f:
        workflow_content = f.read()
        workflow_yaml = yaml.safe_load(workflow_content)

    # Find the security scanning job
    jobs = workflow_yaml.get("jobs", {})

    # Look for Trivy security scan step
    trivy_step = None
    kustomize_render_step = None

    for job_name, job_config in jobs.items():
        steps = job_config.get("steps", [])
        for step in steps:
            step_name = step.get("name", "").lower()

            # Find kustomize render step
            if "render" in step_name and "kustomize" in step_name:
                kustomize_render_step = step

            # Find Trivy security scan step
            if "security" in step_name and "scan" in step_name:
                # Check if it's using trivy-action
                if "aquasecurity/trivy-action" in step.get("uses", ""):
                    trivy_step = step

    # Validate that we found both steps
    assert kustomize_render_step is not None, (
        "Missing step to render Kustomize manifests. "
        "Expected a step with 'kubectl kustomize deployments/overlays/staging-gke'"
    )

    assert trivy_step is not None, "Missing Trivy security scan step. Expected step using aquasecurity/trivy-action"

    # Validate kustomize render step creates temp file
    kustomize_run_cmd = kustomize_render_step.get("run", "")
    assert "kubectl kustomize" in kustomize_run_cmd, "Kustomize render step must use 'kubectl kustomize'"
    assert "deployments/overlays/staging-gke" in kustomize_run_cmd, "Kustomize render step must target staging-gke overlay"
    # Intentionally checking for /tmp/ path in CI workflow validation
    assert (
        "/tmp/staging-manifests" in kustomize_run_cmd or "/tmp/staging.yaml" in kustomize_run_cmd  # nosec B108
    ), "Kustomize render step must output to /tmp/ file for Trivy scanning"  # nosec B108

    # Validate Trivy scans the rendered manifest file, NOT the overlay directory
    trivy_with = trivy_step.get("with", {})
    scan_ref = trivy_with.get("scan-ref", "")

    assert scan_ref != "deployments/overlays/staging-gke", (
        "Trivy must NOT scan raw overlay directory. "
        "This produces false positives because patches are incomplete without base manifests."
    )

    # Intentionally checking for /tmp/ path in CI workflow validation
    assert "/tmp/" in scan_ref, f"Trivy scan-ref should point to rendered manifest in /tmp/, got: {scan_ref}"  # nosec B108

    # Validate scan type is 'config'
    assert trivy_with.get("scan-type") == "config", "Trivy scan-type must be 'config' for Kubernetes manifest scanning"

    # Validate severity includes CRITICAL and HIGH
    severity = trivy_with.get("severity", "")
    assert "CRITICAL" in severity, "Trivy severity must include CRITICAL"
    assert "HIGH" in severity, "Trivy severity must include HIGH"


def test_trivy_scan_allows_documented_suppressions():
    """
    Verify that Trivy scanning policy allows documented suppressions for false positives.

    Per user requirement: "Suppress with .trivyignore (Recommended)"

    Policy:
    - Root-level .trivyignore IS allowed (required for CI pre-commit hooks running from repo root)
    - Environment-specific .trivyignore files ARE allowed (staging-gke, production-gke, etc.)
    - Intermediate global .trivyignore files (deployments/.trivyignore) are NOT allowed
    - All suppressions must be documented (validated by test_trivy_suppressions.py)
    """
    repo_root = Path(__file__).parent.parent.parent

    # Root .trivyignore IS allowed - needed for CI pre-commit hooks
    # It should reference subdirectory files for detailed documentation
    root_trivyignore = repo_root / ".trivyignore"
    if root_trivyignore.exists():
        content = root_trivyignore.read_text()
        # Verify it references the detailed documentation files
        assert "deployments/base/.trivyignore" in content or "See:" in content, (
            "Root .trivyignore must reference detailed documentation in subdirectory files. "
            "Add a comment pointing to deployments/base/.trivyignore or overlay-specific files."
        )

    # Intermediate global .trivyignore files are NOT allowed (too broad)
    disallowed_global_locations = [
        repo_root / "deployments" / ".trivyignore",
        repo_root / "deployments" / "overlays" / ".trivyignore",
    ]

    for ignore_file in disallowed_global_locations:
        assert not ignore_file.exists(), (
            f"Found global .trivyignore file at {ignore_file}. "
            "Intermediate global suppressions are not allowed - they could hide real security issues. "
            "Use environment-specific .trivyignore files in overlay directories instead "
            "(e.g., deployments/overlays/staging-gke/.trivyignore)."
        )

    # Environment-specific .trivyignore files ARE allowed
    # They are validated by test_trivy_suppressions.py to ensure proper documentation


@requires_tool("trivy")
def test_rendered_manifests_include_security_contexts():
    """
    Validate that rendered Kustomize manifests contain proper security contexts.

    This is a smoke test to ensure that when we render the staging overlay,
    the security contexts from both base and patches are properly merged.

    Expected security contexts (from qdrant-patch.yaml):
    - readOnlyRootFilesystem: true
    - runAsNonRoot: true
    - capabilities drop: [ALL]
    """
    import subprocess

    repo_root = Path(__file__).parent.parent.parent

    # Render the staging overlay
    result = subprocess.run(
        ["kubectl", "kustomize", "deployments/overlays/staging-gke"],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        timeout=60,
    )

    assert result.returncode == 0, f"kubectl kustomize failed: {result.stderr}"

    # Parse rendered YAML
    rendered_docs = list(yaml.safe_load_all(result.stdout))

    # Find Qdrant deployment (the one with security context patches)
    # Note: staging overlay adds "staging-" prefix to all resource names
    qdrant_deployment = None
    for doc in rendered_docs:
        if doc is None:
            continue
        if doc.get("kind") == "Deployment" and doc.get("metadata", {}).get("name") == "staging-qdrant":
            qdrant_deployment = doc
            break

    assert qdrant_deployment is not None, (
        "Qdrant deployment not found in rendered manifests. "
        "Expected 'staging-qdrant' (with namePrefix from kustomization.yaml)"
    )

    # Extract security context from container spec
    containers = qdrant_deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])

    assert len(containers) > 0, "No containers found in Qdrant deployment"

    qdrant_container = containers[0]
    security_context = qdrant_container.get("securityContext", {})

    # Validate security hardening
    assert (
        security_context.get("readOnlyRootFilesystem") is True
    ), "Expected readOnlyRootFilesystem: true from qdrant-patch.yaml"
    assert security_context.get("runAsNonRoot") is True, "Expected runAsNonRoot: true for security hardening"

    capabilities = security_context.get("capabilities", {})
    drop_caps = capabilities.get("drop", [])
    assert "ALL" in drop_caps, "Expected capabilities.drop: [ALL] for security hardening"


def test_workflow_step_order_is_correct():
    """
    Verify that the Kustomize render step comes BEFORE the Trivy scan step.

    This ensures the manifest is rendered before it's scanned.
    """
    repo_root = Path(__file__).parent.parent.parent
    workflow_path = repo_root / ".github/workflows/deploy-staging-gke.yaml"

    with open(workflow_path) as f:
        workflow_yaml = yaml.safe_load(f)

    jobs = workflow_yaml.get("jobs", {})

    for job_name, job_config in jobs.items():
        steps = job_config.get("steps", [])

        kustomize_index = None
        trivy_index = None

        for idx, step in enumerate(steps):
            step_name = step.get("name", "").lower()

            if "render" in step_name and "kustomize" in step_name:
                kustomize_index = idx

            if "security" in step_name and "scan" in step_name:
                if "aquasecurity/trivy-action" in step.get("uses", ""):
                    trivy_index = idx

        # If both steps exist in this job, verify order
        if kustomize_index is not None and trivy_index is not None:
            assert kustomize_index < trivy_index, (
                f"Kustomize render step (index {kustomize_index}) must come BEFORE "
                f"Trivy scan step (index {trivy_index}). "
                "Cannot scan manifests before rendering them!"
            )
