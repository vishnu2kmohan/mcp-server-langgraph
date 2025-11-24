#!/usr/bin/env python3
"""
Test suite for Kustomize build validation.

Ensures that all Kustomize overlays build successfully and produce
valid Kubernetes manifests without errors or warnings.
"""

import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.fixtures.tool_fixtures import requires_tool

# Mark as unit test to ensure it runs in CI (deployment validation)
pytestmark = pytest.mark.unit
REPO_ROOT = Path(__file__).parent.parent.parent
OVERLAYS_DIR = REPO_ROOT / "deployments" / "overlays"
CLOUD_OVERLAYS_DIR = REPO_ROOT / "deployments" / "kubernetes" / "overlays"

# All overlays that should build successfully
OVERLAYS_TO_TEST = [
    OVERLAYS_DIR / "staging-gke",
]

# Cloud-specific overlays (AWS, GCP, Azure)
# Codex Finding #2 (P0): These currently fail due to ConfigMap generator issue
CLOUD_OVERLAYS_TO_TEST = [
    CLOUD_OVERLAYS_DIR / "aws",
    CLOUD_OVERLAYS_DIR / "gcp",
    CLOUD_OVERLAYS_DIR / "azure",
]


@requires_tool("kustomize")
def build_kustomize(overlay_dir: Path) -> tuple[str, str, int]:
    """
    Build Kustomize manifests.

    Returns: (stdout, stderr, returncode)
    """
    result = subprocess.run(["kubectl", "kustomize", str(overlay_dir)], capture_output=True, text=True, timeout=60)
    return result.stdout, result.stderr, result.returncode


def parse_manifests(manifest_text: str) -> list[dict[str, Any]]:
    """Parse YAML manifests from text."""
    return [m for m in yaml.safe_load_all(manifest_text) if m]


@requires_tool("kubectl", skip_reason="kubectl CLI not installed - required for kustomize build")
@pytest.mark.parametrize("overlay_dir", OVERLAYS_TO_TEST)
def test_overlay_builds_successfully(overlay_dir: Path):
    """Test that overlay builds without errors."""
    stdout, stderr, returncode = build_kustomize(overlay_dir)

    assert returncode == 0, f"Kustomize build failed for {overlay_dir.name}:\n" f"stderr: {stderr}\n" f"stdout: {stdout}"


@requires_tool("kubectl", skip_reason="kubectl CLI not installed - required for kustomize build")
@pytest.mark.parametrize("overlay_dir", OVERLAYS_TO_TEST)
def test_overlay_produces_valid_yaml(overlay_dir: Path):
    """Test that overlay produces valid YAML."""
    stdout, stderr, returncode = build_kustomize(overlay_dir)

    assert returncode == 0, f"Build failed: {stderr}"

    try:
        manifests = parse_manifests(stdout)
        assert len(manifests) > 0, "Build produced no manifests"
    except yaml.YAMLError as e:
        pytest.fail(f"Build produced invalid YAML: {e}")


@requires_tool("kubectl", skip_reason="kubectl CLI not installed - required for manifest validation")
@pytest.mark.parametrize("overlay_dir", OVERLAYS_TO_TEST)
def test_all_manifests_have_required_fields(overlay_dir: Path):
    """Test that all manifests have required Kubernetes fields."""
    stdout, _, returncode = build_kustomize(overlay_dir)
    assert returncode == 0

    manifests = parse_manifests(stdout)

    for i, manifest in enumerate(manifests):
        # Every manifest must have these fields
        assert "apiVersion" in manifest, f"Manifest {i} missing apiVersion"
        assert "kind" in manifest, f"Manifest {i} missing kind"
        assert "metadata" in manifest, f"Manifest {i} missing metadata"

        # Metadata must have name (except for some special cases)
        metadata = manifest.get("metadata", {})
        kind = manifest.get("kind")

        if kind not in ["List"]:  # List items don't need names
            assert "name" in metadata, f"Manifest {i} (kind: {kind}) missing metadata.name"


@requires_tool("kubectl", skip_reason="kubectl CLI not installed - required for namespace validation")
@pytest.mark.parametrize("overlay_dir", OVERLAYS_TO_TEST)
def test_namespace_consistency_across_all_resources_matches_overlay(overlay_dir: Path):
    """Test that all namespaced resources use the correct namespace."""
    stdout, _, returncode = build_kustomize(overlay_dir)
    assert returncode == 0

    manifests = parse_manifests(stdout)

    # Extract expected namespace from Namespace resource or kustomization.yaml
    expected_namespace = None

    for manifest in manifests:
        if manifest.get("kind") == "Namespace":
            expected_namespace = manifest.get("metadata", {}).get("name")
            break

    if not expected_namespace:
        # Try to read from kustomization.yaml
        kustomization_file = overlay_dir / "kustomization.yaml"
        if kustomization_file.exists():
            with open(kustomization_file) as f:
                kustomization = yaml.safe_load(f)
                expected_namespace = kustomization.get("namespace")

    # Namespaced resource kinds
    namespaced_kinds = {
        "Deployment",
        "Service",
        "ConfigMap",
        "Secret",
        "ServiceAccount",
        "Pod",
        "PersistentVolumeClaim",
        "Ingress",
        "NetworkPolicy",
        "HorizontalPodAutoscaler",
        "VerticalPodAutoscaler",
        "SecretStore",
        "ExternalSecret",
    }

    if expected_namespace:
        for manifest in manifests:
            kind = manifest.get("kind")
            if kind in namespaced_kinds:
                namespace = manifest.get("metadata", {}).get("namespace")
                name = manifest.get("metadata", {}).get("name")

                assert namespace == expected_namespace, (
                    f"Resource {kind}/{name} has namespace '{namespace}' " f"but expected '{expected_namespace}'"
                )


@requires_tool("kubectl", skip_reason="kubectl CLI not installed - required for duplicate resource detection")
@pytest.mark.parametrize("overlay_dir", OVERLAYS_TO_TEST)
def test_no_duplicate_resources(overlay_dir: Path):
    """Test that there are no duplicate resources (same kind/name/namespace)."""
    stdout, _, returncode = build_kustomize(overlay_dir)
    assert returncode == 0

    manifests = parse_manifests(stdout)

    seen = set()
    duplicates = []

    for manifest in manifests:
        kind = manifest.get("kind")
        metadata = manifest.get("metadata", {})
        name = metadata.get("name")
        namespace = metadata.get("namespace", "cluster-scoped")

        resource_id = (kind, namespace, name)

        if resource_id in seen:
            duplicates.append(f"{kind}/{namespace}/{name}")
        else:
            seen.add(resource_id)

    assert not duplicates, f"Duplicate resources found: {duplicates}"


@requires_tool("kubectl", skip_reason="kubectl CLI not installed - required for selector validation")
@pytest.mark.parametrize("overlay_dir", OVERLAYS_TO_TEST)
def test_deployments_have_valid_selectors(overlay_dir: Path):
    """Test that all Deployments have matching selectors and labels."""
    stdout, _, returncode = build_kustomize(overlay_dir)
    assert returncode == 0

    manifests = parse_manifests(stdout)

    for manifest in manifests:
        if manifest.get("kind") != "Deployment":
            continue

        name = manifest.get("metadata", {}).get("name")
        spec = manifest.get("spec", {})

        # Must have selector
        selector = spec.get("selector", {})
        assert selector, f"Deployment {name} has no selector"

        # Must have matchLabels
        match_labels = selector.get("matchLabels", {})
        assert match_labels, f"Deployment {name} has no matchLabels"

        # Template labels must include all matchLabels
        template_labels = spec.get("template", {}).get("metadata", {}).get("labels", {})

        for key, value in match_labels.items():
            assert key in template_labels, f"Deployment {name}: matchLabel '{key}' not in template labels"
            assert (
                template_labels[key] == value
            ), f"Deployment {name}: matchLabel '{key}={value}' != template '{template_labels[key]}'"


@requires_tool("kubectl", skip_reason="kubectl CLI not installed - required for service validation")
@pytest.mark.parametrize("overlay_dir", OVERLAYS_TO_TEST)
def test_services_have_valid_selectors(overlay_dir: Path):
    """Test that all Services (except ExternalName) have valid selectors."""
    stdout, _, returncode = build_kustomize(overlay_dir)
    assert returncode == 0

    manifests = parse_manifests(stdout)

    deployments_labels = {}

    # First, collect all deployment labels
    for manifest in manifests:
        if manifest.get("kind") == "Deployment":
            name = manifest.get("metadata", {}).get("name")
            labels = manifest.get("spec", {}).get("template", {}).get("metadata", {}).get("labels", {})
            deployments_labels[name] = labels

    # Then check that ClusterIP services have matching selectors
    for manifest in manifests:
        if manifest.get("kind") != "Service":
            continue

        spec = manifest.get("spec", {})
        service_name = manifest.get("metadata", {}).get("name")

        # Skip ExternalName and headless services with manual endpoints
        if spec.get("type") == "ExternalName":
            continue

        # Skip headless services (clusterIP: None) with manual endpoints (no selector)
        # These use Endpoints objects instead of selectors
        if spec.get("clusterIP") == "None":
            continue

        selector = spec.get("selector", {})

        # Services should have selectors (except ExternalName and headless)
        if spec.get("type") != "ExternalName":
            assert selector, f"Service {service_name} has no selector"


@requires_tool("kubectl", skip_reason="kubectl CLI not installed - required for container image validation")
@pytest.mark.parametrize("overlay_dir", OVERLAYS_TO_TEST)
def test_container_images_have_tags(overlay_dir: Path):
    """Test that all container images have explicit tags (not 'latest')."""
    stdout, _, returncode = build_kustomize(overlay_dir)
    assert returncode == 0

    manifests = parse_manifests(stdout)

    issues = []

    for manifest in manifests:
        kind = manifest.get("kind")
        if kind not in ["Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob"]:
            continue

        name = manifest.get("metadata", {}).get("name")

        # Get containers
        if kind == "CronJob":
            containers = (
                manifest.get("spec", {})
                .get("jobTemplate", {})
                .get("spec", {})
                .get("template", {})
                .get("spec", {})
                .get("containers", [])
            )
        else:
            containers = manifest.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])

        for container in containers:
            image = container.get("image", "")

            # Must have a tag
            if ":" not in image:
                issues.append(f"{kind}/{name} container '{container.get('name')}' uses image without tag: {image}")
            elif image.endswith(":latest"):
                issues.append(f"{kind}/{name} container '{container.get('name')}' uses :latest tag: {image}")

    assert not issues, "Container image issues:\n" + "\n".join(issues)


@requires_tool("kubectl", skip_reason="kubectl CLI not installed - required for kustomization validation")
@pytest.mark.parametrize("overlay_dir", OVERLAYS_TO_TEST)
def test_kustomization_resources_exist(overlay_dir: Path):  # noqa: C901
    """
    Test that all resource files referenced in kustomization.yaml actually exist.

    This catches errors where kustomization.yaml references files that don't exist,
    which would cause kustomize build to fail or silently skip resources.
    """
    kustomization_file = overlay_dir / "kustomization.yaml"

    if not kustomization_file.exists():
        pytest.skip(f"No kustomization.yaml in {overlay_dir.name}")

    with open(kustomization_file) as f:
        kustomization = yaml.safe_load(f)

    missing_files = []

    # Check resources section
    resources = kustomization.get("resources", [])
    for resource in resources:
        # Skip relative paths to base directories
        if resource.startswith("../") or resource.startswith("./"):
            continue

        resource_path = overlay_dir / resource
        if not resource_path.exists():
            missing_files.append(f"resources: {resource}")

    # Check patches section (legacy inline patches are allowed)
    patches = kustomization.get("patches", [])
    for patch in patches:
        if isinstance(patch, dict):
            # Inline patch definition - check if it has a 'path' field
            if "path" in patch:
                patch_path = overlay_dir / patch["path"]
                if not patch_path.exists():
                    missing_files.append(f"patches.path: {patch['path']}")
        elif isinstance(patch, str):
            # String path reference
            patch_path = overlay_dir / patch
            if not patch_path.exists():
                missing_files.append(f"patches: {patch}")

    # Check patchesStrategicMerge (deprecated but still used)
    patches_strategic_merge = kustomization.get("patchesStrategicMerge", [])
    for patch in patches_strategic_merge:
        patch_path = overlay_dir / patch
        if not patch_path.exists():
            missing_files.append(f"patchesStrategicMerge: {patch}")

    # Check patchesJson6902 (deprecated but still used)
    patches_json = kustomization.get("patchesJson6902", [])
    for patch in patches_json:
        if "path" in patch:
            patch_path = overlay_dir / patch["path"]
            if not patch_path.exists():
                missing_files.append(f"patchesJson6902.path: {patch['path']}")

    assert not missing_files, f"kustomization.yaml in {overlay_dir.name} references files that don't exist:\n" + "\n".join(
        f"  - {f}" for f in missing_files
    )


# Codex Finding #2 (P0 Blocker): Cloud overlay ConfigMap generator tests
@requires_tool("kubectl", skip_reason="kubectl CLI not installed - required for kustomize build")
@pytest.mark.parametrize("overlay_dir", CLOUD_OVERLAYS_TO_TEST)
def test_cloud_overlay_builds_successfully(overlay_dir: Path):
    """
    Test that cloud-specific overlays (AWS, GCP, Azure) build without errors.

    Codex Finding #2 (P0): These overlays use configMapGenerator with behavior: replace
    against a non-generated ConfigMap, causing build failures.

    Red phase: This test will fail until ConfigMaps are converted to patches.
    Green phase: After fixing configMapGenerator to use patches, builds should succeed.
    """
    stdout, stderr, returncode = build_kustomize(overlay_dir)

    assert returncode == 0, (
        f"Kustomize build failed for {overlay_dir.name}:\n"
        f"STDERR:\n{stderr}\n"
        f"STDOUT:\n{stdout}\n\n"
        f"Common issue: configMapGenerator with 'behavior: replace' requires "
        f"base ConfigMap to also be generated (not static YAML).\n"
        f"Fix: Convert to strategic merge patch instead of configMapGenerator."
    )


@requires_tool("kubectl", skip_reason="kubectl CLI not installed - required for OTEL config validation")
@pytest.mark.parametrize("overlay_dir", CLOUD_OVERLAYS_TO_TEST)
def test_cloud_overlay_otel_config_present(overlay_dir: Path):
    """
    Test that cloud overlays include OTEL collector configuration.

    Validates that the overlay-specific OTEL configuration is properly applied.
    """
    stdout, stderr, returncode = build_kustomize(overlay_dir)
    assert returncode == 0, f"Build failed: {stderr}"

    manifests = parse_manifests(stdout)

    # Find OTEL collector ConfigMap
    otel_config = None
    for manifest in manifests:
        if manifest.get("kind") == "ConfigMap" and manifest.get("metadata", {}).get("name") == "otel-collector-config":
            otel_config = manifest
            break

    assert otel_config is not None, f"OTEL collector ConfigMap not found in {overlay_dir.name} overlay"

    # Verify ConfigMap has data
    data = otel_config.get("data", {})
    assert data, f"OTEL collector ConfigMap in {overlay_dir.name} has no data"


# Codex Finding #4 (P1): AWS container name mismatch test
@requires_tool("kubectl", skip_reason="kubectl CLI not installed - required for AWS patch validation")
def test_aws_overlay_container_patches_apply():
    """
    Test that AWS overlay patches are applied to the correct container.

    Codex Finding #4 (P1): AWS deployment-patch.yaml references container 'mcp-server'
    but base deployment uses 'mcp-server-langgraph', causing patches to be ignored.

    Red phase: AWS-specific env vars (AWS_REGION, etc.) will be missing from deployment.
    Green phase: After fixing container name, env vars should be present.
    """
    aws_overlay = CLOUD_OVERLAYS_DIR / "aws"
    stdout, stderr, returncode = build_kustomize(aws_overlay)
    assert returncode == 0, f"Build failed: {stderr}"

    manifests = parse_manifests(stdout)

    # Find main deployment
    deployment = None
    for manifest in manifests:
        if manifest.get("kind") == "Deployment":
            name = manifest.get("metadata", {}).get("name")
            # Look for the main app deployment (might have prefix)
            if "mcp-server-langgraph" in name:
                deployment = manifest
                break

    assert deployment is not None, "mcp-server-langgraph Deployment not found in AWS overlay"

    # Get containers
    containers = deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])

    # Find main container
    main_container = None
    for container in containers:
        if container.get("name") == "mcp-server-langgraph":
            main_container = container
            break

    assert main_container is not None, (
        "Container 'mcp-server-langgraph' not found in deployment.\n"
        f"Available containers: {[c.get('name') for c in containers]}"
    )

    # Verify AWS-specific environment variables are present
    env_vars = {env.get("name"): env.get("value") for env in main_container.get("env", [])}

    aws_env_vars = ["AWS_REGION"]
    missing_vars = [var for var in aws_env_vars if var not in env_vars]

    assert not missing_vars, (
        f"AWS-specific environment variables missing from deployment:\n"
        f"Missing: {missing_vars}\n"
        f"Available: {list(env_vars.keys())}\n\n"
        f"This indicates the deployment patch is not being applied.\n"
        f"Check that container name in patch matches base deployment."
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
