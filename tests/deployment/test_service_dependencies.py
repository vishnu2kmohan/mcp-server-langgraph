#!/usr/bin/env python3
"""
Test suite for service dependency validation in init containers.

Ensures that all service names referenced in init containers actually
exist in the deployed manifests. This prevents pods from getting stuck
in Init state waiting for non-existent services.

Critical issue prevented:
- Init containers with 'nc -z <service> <port>' that reference services
  that don't exist, causing "bad address" errors and infinite wait loops.
"""

import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.fixtures.tool_fixtures import requires_tool
from tests.helpers.path_helpers import get_repo_root

# Mark as unit test to ensure it runs in CI
pytestmark = [pytest.mark.unit, pytest.mark.validation]

REPO_ROOT = get_repo_root()
OVERLAYS_DIR = REPO_ROOT / "deployments" / "overlays"
STAGING_GKE_DIR = OVERLAYS_DIR / "preview-gke"


def load_yaml_documents(file_path: Path) -> list[dict[str, Any]]:
    """Load all YAML documents from a file."""
    with open(file_path) as f:
        return list(yaml.safe_load_all(f))


@requires_tool("kustomize")
def build_kustomize_manifests(overlay_dir: Path) -> str:
    """Build Kustomize manifests and return as string."""
    result = subprocess.run(["kubectl", "kustomize", str(overlay_dir)], capture_output=True, text=True, check=True, timeout=60)
    return result.stdout


def parse_kustomize_output(kustomize_output: str) -> list[dict[str, Any]]:
    """Parse Kustomize output into list of manifests."""
    return list(yaml.safe_load_all(kustomize_output))


def extract_services(manifests: list[dict[str, Any]]) -> set[str]:
    """Extract all service names from manifests."""
    services = set()

    for manifest in manifests:
        if not manifest:
            continue

        if manifest.get("kind") == "Service":
            metadata = manifest.get("metadata", {})
            name = metadata.get("name")
            if name:
                services.add(name)

    return services


def extract_init_container_service_refs(manifests: list[dict[str, Any]]) -> dict[str, list[str]]:
    """
    Extract service names referenced in init containers.

    Returns dict mapping deployment name to list of referenced services.
    """
    service_refs = {}

    for manifest in manifests:
        if not manifest:
            continue

        if manifest.get("kind") != "Deployment":
            continue

        deployment_name = manifest.get("metadata", {}).get("name", "unknown")
        init_containers = manifest.get("spec", {}).get("template", {}).get("spec", {}).get("initContainers", [])

        refs = []
        for init_container in init_containers:
            # Look for 'nc -z <service> <port>' pattern in args
            args = init_container.get("args", [])
            for arg in args:
                if isinstance(arg, str) and "nc -z" in arg:
                    # Extract service name from pattern like "nc -z service-name 8080"
                    parts = arg.split()
                    for i, part in enumerate(parts):
                        if part == "-z" and i + 1 < len(parts):
                            service_name = parts[i + 1]
                            refs.append(service_name)

        if refs:
            service_refs[deployment_name] = refs

    return service_refs


def test_staging_gke_overlay_builds():
    """Test that preview-gke overlay builds without errors."""
    try:
        output = build_kustomize_manifests(STAGING_GKE_DIR)
        assert output, "Kustomize build produced empty output"
        assert len(output) > 0, "Kustomize build produced no manifests"
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Kustomize build failed: {e.stderr}")


def test_all_init_container_services_exist():
    """
    Test that all services referenced in init containers actually exist.

    This is a CRITICAL test that prevents the failure mode where init
    containers wait indefinitely for services that don't exist, blocking
    all pod startup.
    """
    # Build manifests
    try:
        kustomize_output = build_kustomize_manifests(STAGING_GKE_DIR)
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Kustomize build failed: {e.stderr}")

    manifests = parse_kustomize_output(kustomize_output)

    # Extract services and init container refs
    services = extract_services(manifests)
    service_refs = extract_init_container_service_refs(manifests)

    # Verify all references exist
    missing_services = {}
    for deployment, refs in service_refs.items():
        missing = [ref for ref in refs if ref not in services]
        if missing:
            missing_services[deployment] = missing

    assert not missing_services, (
        f"Init containers reference services that don't exist:\n"
        f"{yaml.dump(missing_services, default_flow_style=False)}\n"
        f"Available services: {sorted(services)}"
    )


def test_staging_services_have_prefix():
    """Test that staging services have the 'preview-' prefix applied by Kustomize."""
    kustomize_output = build_kustomize_manifests(STAGING_GKE_DIR)
    manifests = parse_kustomize_output(kustomize_output)

    services = extract_services(manifests)

    # Exclude system services and ExternalName services
    app_services = {s for s in services if not s.startswith("preview-mcp-server-langgraph")}

    for service in app_services:
        if service in ["default", "kubernetes"]:  # System services
            continue

        assert service.startswith("preview-"), f"Service '{service}' doesn't have 'preview-' prefix"


def test_init_container_refs_match_staging_prefix():
    """
    Test that init container service refs use staging- prefix.

    This catches the bug where base manifests reference unprefixed service
    names but Kustomize applies a prefix, causing name mismatches.
    """
    kustomize_output = build_kustomize_manifests(STAGING_GKE_DIR)
    manifests = parse_kustomize_output(kustomize_output)

    service_refs = extract_init_container_service_refs(manifests)

    # All refs in staging should start with 'preview-'
    invalid_refs = {}
    for deployment, refs in service_refs.items():
        invalid = [ref for ref in refs if not ref.startswith("preview-")]
        if invalid:
            invalid_refs[deployment] = invalid

    assert not invalid_refs, (
        f"Init containers reference services without 'preview-' prefix:\n"
        f"{yaml.dump(invalid_refs, default_flow_style=False)}\n"
        f"These should be prefixed with 'preview-' to match Kustomize namePrefix"
    )


def test_required_services_exist_in_staging():
    """Test that all required services exist in staging deployment."""
    kustomize_output = build_kustomize_manifests(STAGING_GKE_DIR)
    manifests = parse_kustomize_output(kustomize_output)

    services = extract_services(manifests)

    # Required services for preview (all have preview- prefix from Kustomize)
    required_services = [
        "preview-keycloak",
        "preview-openfga",
        "preview-qdrant",
        "preview-mcp-server-langgraph",
        "preview-redis-session",  # ExternalName to Memorystore
    ]

    missing = [svc for svc in required_services if svc not in services]

    assert not missing, f"Required services missing from staging deployment: {missing}\nAvailable services: {sorted(services)}"


def test_external_name_services_have_endpoints():
    """Test that ExternalName services have valid external endpoints."""
    kustomize_output = build_kustomize_manifests(STAGING_GKE_DIR)
    manifests = parse_kustomize_output(kustomize_output)

    for manifest in manifests:
        if not manifest or manifest.get("kind") != "Service":
            continue

        spec = manifest.get("spec", {})
        if spec.get("type") == "ExternalName":
            external_name = spec.get("externalName")
            service_name = manifest.get("metadata", {}).get("name")

            assert external_name, f"ExternalName service '{service_name}' has no externalName field"

            # Should be an IP address or hostname
            assert external_name and len(external_name) > 0, f"ExternalName service '{service_name}' has empty externalName"


def test_external_name_services_use_dns_not_ip():
    """
    Test that ExternalName services use DNS names, not IP addresses.

    ExternalName services create CNAME records, which require DNS names.
    Using IP addresses in externalName will cause service resolution failures.

    Kubernetes ExternalName service spec requires a fully qualified domain name (FQDN),
    not an IP address. IP addresses should use a headless Service with Endpoints instead.
    """
    import re

    kustomize_output = build_kustomize_manifests(STAGING_GKE_DIR)
    manifests = parse_kustomize_output(kustomize_output)

    # IPv4 pattern - matches standard dotted decimal notation
    ipv4_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")

    # IPv6 pattern - simplified, matches most IPv6 formats
    ipv6_pattern = re.compile(r"^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$")

    invalid_services = []

    for manifest in manifests:
        if not manifest or manifest.get("kind") != "Service":
            continue

        spec = manifest.get("spec", {})
        if spec.get("type") == "ExternalName":
            external_name = spec.get("externalName", "")
            service_name = manifest.get("metadata", {}).get("name")

            # Check if externalName is an IP address
            if ipv4_pattern.match(external_name) or ipv6_pattern.match(external_name):
                invalid_services.append(
                    {"name": service_name, "externalName": external_name, "issue": "IP address used instead of DNS name"}
                )

    assert not invalid_services, (
        f"ExternalName services must use DNS names, not IP addresses:\n"
        f"{yaml.dump(invalid_services, default_flow_style=False)}\n"
        f"Fix: Replace ExternalName service with Headless Service + Endpoints object\n"
        f"or use the actual DNS name of the external service."
    )


def test_deployment_init_containers_timeout():
    """Test that init containers have reasonable timeouts implied by their logic."""
    kustomize_output = build_kustomize_manifests(STAGING_GKE_DIR)
    manifests = parse_kustomize_output(kustomize_output)

    for manifest in manifests:
        if not manifest or manifest.get("kind") != "Deployment":
            continue

        deployment_name = manifest.get("metadata", {}).get("name", "unknown")
        init_containers = manifest.get("spec", {}).get("template", {}).get("spec", {}).get("initContainers", [])

        for init_container in init_containers:
            args = init_container.get("args", [])
            for arg in args:
                if isinstance(arg, str) and "until nc -z" in arg:
                    # Should have a sleep statement to avoid tight loop
                    assert "sleep" in arg, (
                        f"Init container '{init_container.get('name')}' in {deployment_name} "
                        f"has wait loop without sleep, causing CPU spin"
                    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
