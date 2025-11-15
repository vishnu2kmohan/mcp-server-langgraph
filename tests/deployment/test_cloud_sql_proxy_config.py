#!/usr/bin/env python3
"""
Test suite for Cloud SQL Proxy sidecar configuration validation.

Ensures that Cloud SQL Proxy containers are properly configured with:
1. HTTP admin server port (--http-port=9801) for health checks
2. Correct liveness/readiness probe configuration
3. Required arguments for private IP connectivity

This test prevents the critical failure mode where health check probes
attempt to connect to port 9801 but the proxy doesn't expose it,
causing continuous container restarts.
"""

import gc
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

# Mark as unit test to ensure it runs in CI (deployment validation)
pytestmark = pytest.mark.unit
# Test data
OVERLAYS_DIR = Path(__file__).parent.parent.parent / "deployments" / "overlays"
STAGING_GKE_DIR = OVERLAYS_DIR / "staging-gke"

# Files that should contain Cloud SQL Proxy sidecars
PROXY_PATCH_FILES = [
    STAGING_GKE_DIR / "keycloak-patch.yaml",
    STAGING_GKE_DIR / "openfga-patch.yaml",
]


def load_yaml_file(file_path: Path) -> Dict[str, Any]:
    """Load a YAML file and return parsed content."""
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def find_cloud_sql_proxy_container(manifest: Dict[str, Any]) -> Dict[str, Any] | None:
    """Find the cloud-sql-proxy container in a deployment manifest."""
    if manifest.get("kind") != "Deployment":
        return None

    containers = manifest.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])

    for container in containers:
        if container.get("name") == "cloud-sql-proxy":
            return container

    return None


def test_cloud_sql_proxy_files_exist():
    """Test that expected Cloud SQL Proxy patch files exist."""
    for patch_file in PROXY_PATCH_FILES:
        assert patch_file.exists(), f"Cloud SQL Proxy patch file not found: {patch_file}"


@pytest.mark.parametrize("patch_file", PROXY_PATCH_FILES)
def test_cloud_sql_proxy_http_port_configured(patch_file: Path):
    """
    Test that Cloud SQL Proxy has --http-port=9801 configured.

    This is CRITICAL for health checks to work. Without this flag,
    the proxy doesn't expose the HTTP admin server, causing all
    liveness and readiness probes to fail with "connection refused".
    """
    manifest = load_yaml_file(patch_file)
    proxy_container = find_cloud_sql_proxy_container(manifest)

    assert proxy_container is not None, f"cloud-sql-proxy container not found in {patch_file.name}"

    args = proxy_container.get("args", [])

    # Check for --http-port=9801 flag
    has_http_port = any("--http-port=9801" in arg or arg == "--http-port=9801" for arg in args)

    assert has_http_port, (
        f"Cloud SQL Proxy in {patch_file.name} is missing --http-port=9801 flag. "
        f"This causes health check probes to fail. Current args: {args}"
    )


@pytest.mark.parametrize("patch_file", PROXY_PATCH_FILES)
def test_cloud_sql_proxy_has_required_args(patch_file: Path):
    """Test that Cloud SQL Proxy has all required arguments."""
    manifest = load_yaml_file(patch_file)
    proxy_container = find_cloud_sql_proxy_container(manifest)

    assert proxy_container is not None, f"cloud-sql-proxy container not found in {patch_file.name}"

    args = proxy_container.get("args", [])

    # Required arguments
    required_args = [
        "--structured-logs",
        "--port=5432",
        "--private-ip",
        "--http-port=9801",  # Critical for health checks
        "--health-check",  # Required to enable HTTP health check server
    ]

    for required_arg in required_args:
        has_arg = any(required_arg in arg for arg in args)
        assert has_arg, f"Missing required arg '{required_arg}' in {patch_file.name}"

    # Should have instance connection string
    has_instance = any("vishnu-sandbox-20250310:us-central1:" in arg for arg in args)
    assert has_instance, f"Missing Cloud SQL instance connection string in {patch_file.name}"


@pytest.mark.parametrize("patch_file", PROXY_PATCH_FILES)
def test_cloud_sql_proxy_health_probes_configured(patch_file: Path):
    """Test that Cloud SQL Proxy has liveness and readiness probes configured correctly."""
    manifest = load_yaml_file(patch_file)
    proxy_container = find_cloud_sql_proxy_container(manifest)

    assert proxy_container is not None, f"cloud-sql-proxy container not found in {patch_file.name}"

    # Check liveness probe
    liveness = proxy_container.get("livenessProbe")
    assert liveness is not None, f"Missing livenessProbe in {patch_file.name}"
    assert liveness.get("httpGet", {}).get("port") == 9801, f"Liveness probe must use port 9801 in {patch_file.name}"
    assert (
        liveness.get("httpGet", {}).get("path") == "/liveness"
    ), f"Liveness probe must use /liveness path in {patch_file.name}"

    # Check readiness probe
    readiness = proxy_container.get("readinessProbe")
    assert readiness is not None, f"Missing readinessProbe in {patch_file.name}"
    assert readiness.get("httpGet", {}).get("port") == 9801, f"Readiness probe must use port 9801 in {patch_file.name}"
    assert (
        readiness.get("httpGet", {}).get("path") == "/readiness"
    ), f"Readiness probe must use /readiness path in {patch_file.name}"


@pytest.mark.parametrize("patch_file", PROXY_PATCH_FILES)
def test_cloud_sql_proxy_resource_limits(patch_file: Path):
    """Test that Cloud SQL Proxy has appropriate resource limits."""
    manifest = load_yaml_file(patch_file)
    proxy_container = find_cloud_sql_proxy_container(manifest)

    assert proxy_container is not None, f"cloud-sql-proxy container not found in {patch_file.name}"

    resources = proxy_container.get("resources", {})

    # Should have requests and limits
    assert "requests" in resources, f"Missing resource requests in {patch_file.name}"
    assert "limits" in resources, f"Missing resource limits in {patch_file.name}"

    # Check memory
    assert resources["requests"].get("memory"), f"Missing memory request in {patch_file.name}"
    assert resources["limits"].get("memory"), f"Missing memory limit in {patch_file.name}"

    # Check CPU
    assert resources["requests"].get("cpu"), f"Missing CPU request in {patch_file.name}"
    assert resources["limits"].get("cpu"), f"Missing CPU limit in {patch_file.name}"


@pytest.mark.parametrize("patch_file", PROXY_PATCH_FILES)
def test_cloud_sql_proxy_security_context(patch_file: Path):
    """Test that Cloud SQL Proxy has proper security context."""
    manifest = load_yaml_file(patch_file)
    proxy_container = find_cloud_sql_proxy_container(manifest)

    assert proxy_container is not None, f"cloud-sql-proxy container not found in {patch_file.name}"

    security_context = proxy_container.get("securityContext", {})

    # Security requirements
    assert security_context.get("runAsNonRoot") is True, f"Cloud SQL Proxy must run as non-root in {patch_file.name}"
    assert (
        security_context.get("allowPrivilegeEscalation") is False
    ), f"Cloud SQL Proxy must not allow privilege escalation in {patch_file.name}"
    assert (
        security_context.get("readOnlyRootFilesystem") is True
    ), f"Cloud SQL Proxy must use read-only root filesystem in {patch_file.name}"

    # Should drop all capabilities
    capabilities = security_context.get("capabilities", {})
    assert "ALL" in capabilities.get("drop", []), f"Cloud SQL Proxy must drop all capabilities in {patch_file.name}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
