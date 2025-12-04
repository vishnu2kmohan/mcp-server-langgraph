#!/usr/bin/env python3
"""
Test suite for GKE Autopilot resource compliance.

Validates that all containers (including init containers) in GKE deployments
meet the minimum resource requirements enforced by GKE Autopilot LimitRanges.

TDD Context:
- RED: Tests fail when containers have resources below GKE Autopilot minimums
- GREEN: After fixing resources, tests pass
- REFACTOR: Update validator and base configs for consistency
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

# GKE Autopilot minimum resource requirements (per LimitRange)
GKE_AUTOPILOT_MIN_MEMORY_MI = 128  # MiB
GKE_AUTOPILOT_MIN_EPHEMERAL_STORAGE_MI = 100  # MiB
GKE_AUTOPILOT_MIN_CPU_M = 100  # millicores

# Overlays that deploy to GKE Autopilot
GKE_AUTOPILOT_OVERLAYS = [
    REPO_ROOT / "deployments" / "overlays" / "staging-gke",
    REPO_ROOT / "deployments" / "overlays" / "production-gke",
]


def parse_memory_to_mi(mem_str: str | None) -> float:
    """Parse memory string to MiB."""
    if not mem_str:
        return 0.0

    units = {
        "Ki": 1 / 1024,
        "Mi": 1,
        "Gi": 1024,
        "Ti": 1024 * 1024,
    }

    for unit, multiplier in units.items():
        if mem_str.endswith(unit):
            return float(mem_str[: -len(unit)]) * multiplier

    # Assume bytes if no unit
    return float(mem_str) / (1024 * 1024)


def parse_cpu_to_millicores(cpu_str: str | None) -> float:
    """Parse CPU string to millicores."""
    if not cpu_str:
        return 0.0
    if cpu_str.endswith("m"):
        return float(cpu_str[:-1])
    return float(cpu_str) * 1000


def render_kustomize_manifests(overlay_path) -> list[dict[str, Any]]:
    """Render Kustomize manifests and return parsed YAML documents."""
    if not overlay_path.exists():
        pytest.skip(f"Overlay not found: {overlay_path}")

    result = subprocess.run(
        ["kubectl", "kustomize", str(overlay_path)],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    manifests = list(yaml.safe_load_all(result.stdout))
    return [m for m in manifests if m is not None]


def find_deployments(manifests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find all Deployment resources in manifests."""
    return [m for m in manifests if m.get("kind") == "Deployment"]


def get_all_containers(deployment: dict[str, Any]) -> list[tuple[str, str, dict]]:
    """
    Get all containers (regular + init) from a deployment.

    Returns list of (deployment_name, container_name, container_spec) tuples.
    """
    containers = []
    deployment_name = deployment.get("metadata", {}).get("name", "unknown")
    spec = deployment.get("spec", {}).get("template", {}).get("spec", {})

    # Regular containers
    for container in spec.get("containers", []):
        containers.append((deployment_name, container.get("name", "unknown"), container))

    # Init containers
    for container in spec.get("initContainers", []):
        containers.append((deployment_name, f"init:{container.get('name', 'unknown')}", container))

    return containers


@pytest.mark.xdist_group(name="test_gke_autopilot_resources")
class TestGKEAutopilotResourceCompliance:
    """Test that all containers meet GKE Autopilot minimum resource requirements."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @requires_tool("kubectl", skip_reason="kubectl CLI not installed - required for kustomize build")
    @pytest.mark.parametrize("overlay_path", GKE_AUTOPILOT_OVERLAYS)
    def test_all_containers_meet_minimum_memory_request(self, overlay_path) -> None:
        """
        Test that all containers have memory requests >= 128Mi.

        GKE Autopilot LimitRange enforces minimum 128Mi memory per container.
        """
        manifests = render_kustomize_manifests(overlay_path)
        deployments = find_deployments(manifests)

        violations = []

        for deployment in deployments:
            for dep_name, container_name, container in get_all_containers(deployment):
                resources = container.get("resources", {})
                requests = resources.get("requests", {})
                memory_request = requests.get("memory")

                if memory_request:
                    memory_mi = parse_memory_to_mi(memory_request)
                    if memory_mi < GKE_AUTOPILOT_MIN_MEMORY_MI:
                        violations.append(
                            {
                                "deployment": dep_name,
                                "container": container_name,
                                "memory_request": memory_request,
                                "memory_mi": memory_mi,
                                "minimum_required": f"{GKE_AUTOPILOT_MIN_MEMORY_MI}Mi",
                            }
                        )

        if violations:
            overlay_name = overlay_path.name
            error_msg = f"\n\n[{overlay_name}] Containers with memory below {GKE_AUTOPILOT_MIN_MEMORY_MI}Mi:\n"
            for v in violations:
                error_msg += f"\n  {v['deployment']}/{v['container']}: {v['memory_request']} ({v['memory_mi']:.0f}Mi < {GKE_AUTOPILOT_MIN_MEMORY_MI}Mi)"
            error_msg += "\n\nGKE Autopilot LimitRange enforces minimum 128Mi memory per container."
            pytest.fail(error_msg)

    @requires_tool("kubectl", skip_reason="kubectl CLI not installed - required for kustomize build")
    @pytest.mark.parametrize("overlay_path", GKE_AUTOPILOT_OVERLAYS)
    def test_all_containers_meet_minimum_ephemeral_storage_request(self, overlay_path) -> None:
        """
        Test that all containers have ephemeral-storage requests >= 100Mi.

        GKE Autopilot LimitRange enforces minimum 100Mi ephemeral-storage per container.
        """
        manifests = render_kustomize_manifests(overlay_path)
        deployments = find_deployments(manifests)

        violations = []

        for deployment in deployments:
            for dep_name, container_name, container in get_all_containers(deployment):
                resources = container.get("resources", {})
                requests = resources.get("requests", {})
                storage_request = requests.get("ephemeral-storage")

                if storage_request:
                    storage_mi = parse_memory_to_mi(storage_request)
                    if storage_mi < GKE_AUTOPILOT_MIN_EPHEMERAL_STORAGE_MI:
                        violations.append(
                            {
                                "deployment": dep_name,
                                "container": container_name,
                                "storage_request": storage_request,
                                "storage_mi": storage_mi,
                                "minimum_required": f"{GKE_AUTOPILOT_MIN_EPHEMERAL_STORAGE_MI}Mi",
                            }
                        )

        if violations:
            overlay_name = overlay_path.name
            error_msg = (
                f"\n\n[{overlay_name}] Containers with ephemeral-storage below {GKE_AUTOPILOT_MIN_EPHEMERAL_STORAGE_MI}Mi:\n"
            )
            for v in violations:
                error_msg += f"\n  {v['deployment']}/{v['container']}: {v['storage_request']} ({v['storage_mi']:.0f}Mi < {GKE_AUTOPILOT_MIN_EPHEMERAL_STORAGE_MI}Mi)"
            error_msg += "\n\nGKE Autopilot LimitRange enforces minimum 100Mi ephemeral-storage per container."
            pytest.fail(error_msg)

    @requires_tool("kubectl", skip_reason="kubectl CLI not installed - required for kustomize build")
    @pytest.mark.parametrize("overlay_path", GKE_AUTOPILOT_OVERLAYS)
    def test_init_containers_have_compliant_resources(self, overlay_path) -> None:
        """
        Test that init containers specifically have GKE Autopilot-compliant resources.

        Init containers often have reduced resources but must still meet minimums.
        """
        manifests = render_kustomize_manifests(overlay_path)
        deployments = find_deployments(manifests)

        violations = []

        for deployment in deployments:
            deployment_name = deployment.get("metadata", {}).get("name", "unknown")
            spec = deployment.get("spec", {}).get("template", {}).get("spec", {})

            for container in spec.get("initContainers", []):
                container_name = container.get("name", "unknown")
                resources = container.get("resources", {})
                requests = resources.get("requests", {})

                memory = requests.get("memory")
                storage = requests.get("ephemeral-storage")

                issues = []

                if memory:
                    memory_mi = parse_memory_to_mi(memory)
                    if memory_mi < GKE_AUTOPILOT_MIN_MEMORY_MI:
                        issues.append(f"memory {memory} < {GKE_AUTOPILOT_MIN_MEMORY_MI}Mi")

                if storage:
                    storage_mi = parse_memory_to_mi(storage)
                    if storage_mi < GKE_AUTOPILOT_MIN_EPHEMERAL_STORAGE_MI:
                        issues.append(f"ephemeral-storage {storage} < {GKE_AUTOPILOT_MIN_EPHEMERAL_STORAGE_MI}Mi")

                if issues:
                    violations.append(
                        {
                            "deployment": deployment_name,
                            "init_container": container_name,
                            "issues": issues,
                        }
                    )

        if violations:
            overlay_name = overlay_path.name
            error_msg = f"\n\n[{overlay_name}] Init containers with non-compliant resources:\n"
            for v in violations:
                error_msg += f"\n  {v['deployment']}/{v['init_container']}:"
                for issue in v["issues"]:
                    error_msg += f"\n    - {issue}"
            error_msg += "\n\nInit containers must meet GKE Autopilot LimitRange minimums."
            pytest.fail(error_msg)
