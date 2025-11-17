"""
Integration tests for Kubernetes health probes.

Tests verify that health check endpoints work correctly in a Kubernetes
deployment environment and prevent the production failures discovered in staging.

These tests can run against:
1. Local Kubernetes (kind, minikube)
2. Staging cluster (for validation)
3. CI/CD pipeline (for deployment verification)
"""

import gc
import os
import time

import pytest
import requests

# Skip if not in Kubernetes environment + xdist_group for worker isolation
pytestmark = [
    pytest.mark.skipif(
        os.getenv("KUBERNETES_SERVICE_HOST") is None and os.getenv("TEST_KUBERNETES_PROBES") != "true",
        reason="Requires Kubernetes environment or TEST_KUBERNETES_PROBES=true",
    ),
    pytest.mark.xdist_group(name="integration_kubernetes_health_probes_tests"),
]


def teardown_module():
    """Force GC to prevent mock accumulation in xdist workers"""
    gc.collect()


@pytest.fixture(autouse=True)
def teardown_method_kubernetes_health_probes():
    """Force GC after each teardown_method to prevent mock accumulation in xdist workers"""
    yield
    gc.collect()


@pytest.mark.integration
def test_startup_probe_accessible():
    """
    Test that startup probe endpoint is accessible at /health/startup.

    This prevents the production issue where pods failed startup probes
    due to incorrect path configuration (/health/health/startup).
    """
    # Use localhost if running inside pod, otherwise use port-forward
    base_url = os.getenv("HEALTH_CHECK_URL", "http://localhost:8000")

    response = requests.get(f"{base_url}/health/startup", timeout=5)

    assert response.status_code == 200, f"Startup probe failed with status {response.status_code}"

    data = response.json()
    assert data["status"] == "started", f"Startup probe status incorrect: {data['status']}"
    assert "checks" in data, "Startup probe response missing 'checks'"


@pytest.mark.integration
def test_readiness_probe_accessible():
    """
    Test that readiness probe endpoint is accessible at /health/ready.

    Kubernetes uses this to determine if pod should receive traffic.
    """
    base_url = os.getenv("HEALTH_CHECK_URL", "http://localhost:8000")

    response = requests.get(f"{base_url}/health/ready", timeout=5)

    # May be 200 (ready) or 503 (not ready, dependencies down)
    assert response.status_code in [200, 503], f"Readiness probe failed with status {response.status_code}"

    data = response.json()
    assert "status" in data, "Readiness probe response missing 'status'"
    assert "checks" in data, "Readiness probe response missing 'checks'"


@pytest.mark.integration
def test_liveness_probe_accessible():
    """
    Test that liveness probe endpoint is accessible at /health/live.

    Kubernetes uses this to determine if pod should be restarted.
    """
    base_url = os.getenv("HEALTH_CHECK_URL", "http://localhost:8000")

    response = requests.get(f"{base_url}/health/live", timeout=5)

    assert response.status_code == 200, f"Liveness probe failed with status {response.status_code}"

    data = response.json()
    assert data["status"] == "healthy", f"Liveness probe status incorrect: {data['status']}"


@pytest.mark.integration
def test_root_health_endpoint_accessible():
    """
    Test that root health endpoint is accessible at /health/.

    This is a convenience endpoint that maps to the liveness check.
    """
    base_url = os.getenv("HEALTH_CHECK_URL", "http://localhost:8000")

    response = requests.get(f"{base_url}/health/", timeout=5)

    assert response.status_code == 200, f"Root health endpoint failed with status {response.status_code}"

    data = response.json()
    assert data["status"] == "healthy", f"Root health status incorrect: {data['status']}"


@pytest.mark.integration
def test_double_path_health_endpoints_not_found():
    """
    Test that double-path health endpoints return 404.

    This prevents regression to the bug where routes were defined incorrectly,
    creating paths like /health/health/startup instead of /health/startup.

    CRITICAL: This test failing indicates the FastAPI sub-app mounting bug has returned.
    """
    base_url = os.getenv("HEALTH_CHECK_URL", "http://localhost:8000")

    # These paths should NOT exist
    bad_paths = ["/health/health/startup", "/health/health/ready", "/health/health/live", "/health/health"]

    for path in bad_paths:
        response = requests.get(f"{base_url}{path}", timeout=5)
        assert response.status_code == 404, f"Double-path {path} should return 404, got {response.status_code}"


@pytest.mark.integration
def test_health_probe_response_time():
    """
    Test that health probes respond within acceptable time limits.

    Kubernetes probes have timeoutSeconds configured, and we need to ensure
    our endpoints respond faster than the timeout.

    Current probe timeouts:
    - Startup: 3s
    - Readiness: 5s
    - Liveness: 5s
    """
    base_url = os.getenv("HEALTH_CHECK_URL", "http://localhost:8000")

    endpoints = {
        "/health/startup": 3.0,  # Must respond within 3s
        "/health/ready": 5.0,  # Must respond within 5s
        "/health/live": 5.0,  # Must respond within 5s
    }

    for path, max_time in endpoints.items():
        start = time.time()
        response = requests.get(f"{base_url}{path}", timeout=max_time)
        duration = time.time() - start

        assert response.status_code in [
            200,
            503,
        ], f"{path} returned unexpected status {response.status_code}"
        assert duration < max_time, f"{path} took {duration:.2f}s, exceeds timeout {max_time}s"


@pytest.mark.integration
@pytest.mark.kubernetes
def test_cloud_sql_proxy_health_endpoints():
    """
    Test that Cloud SQL Proxy health endpoints are accessible.

    This prevents the production issue where Cloud SQL Proxy sidecars crashed
    because health check server was not enabled.

    Requires: Cloud SQL Proxy running with --health-check flag
    """
    # Cloud SQL Proxy runs on port 9801 in sidecar
    proxy_url = os.getenv("CLOUD_SQL_PROXY_URL", "http://localhost:9801")

    # Test liveness endpoint
    try:
        response = requests.get(f"{proxy_url}/liveness", timeout=5)
        assert response.status_code == 200, f"Proxy liveness failed with status {response.status_code}"
    except requests.exceptions.ConnectionError:
        pytest.skip("Cloud SQL Proxy not accessible (not running or not in same pod)")

    # Test readiness endpoint
    response = requests.get(f"{proxy_url}/readiness", timeout=5)
    assert response.status_code in [200, 503], f"Proxy readiness failed with status {response.status_code}"


@pytest.mark.integration
@pytest.mark.kubernetes
@pytest.mark.requires_kubectl
def test_kubernetes_probe_paths_match_deployment():
    """
    Verify that actual deployment probe paths match expected values.

    This catches configuration drift between deployment manifests and
    actual endpoint implementations.
    """
    # This test requires kubectl access and is intended for CI/CD validation
    if os.getenv("KUBERNETES_SERVICE_HOST") is None:
        pytest.skip("Not running in Kubernetes cluster")

    # Actual validation would use kubectl to verify probe paths
    # For now, this serves as a placeholder for CI/CD integration
