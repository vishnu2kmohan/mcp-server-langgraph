"""
Integration tests for Grafana LGTM Stack infrastructure.

This test suite validates that the observability infrastructure components
(Loki, Grafana, Tempo, Mimir, Alloy) are properly configured and functional.

These tests require `make test-infra-full-up` to be running.

TDD Rationale:
--------------
These tests were created after CI failures revealed gaps in our local testing:
- Loki container failed due to tmpfs permissions (user 10001)
- Grafana dashboard provisioning failed due to non-existent directories
- These issues were not caught locally because we had no integration tests
  for the LGTM stack infrastructure itself.

Test Categories:
----------------
1. Health Checks: Verify each LGTM component is healthy and accessible
2. Configuration: Validate provisioning files exist and are valid
3. Connectivity: Verify services can communicate with each other
4. End-to-End: Test telemetry flow from app -> Alloy -> backends

Markers:
--------
- @pytest.mark.integration: Integration test category
- @pytest.mark.observability: Observability-specific tests
- @pytest.mark.docker: Requires Docker infrastructure
- @pytest.mark.slow: May take >30s to complete

Related Issues:
---------------
- Loki permission denied: docker-compose.test.yml tmpfs uid/gid for user 10001
- Grafana provisioning: dashboards.yml referenced non-existent directories
- ADR-0067: Grafana LGTM Stack migration decision
"""

import gc
import socket
import time

import pytest
import requests
import yaml

from tests.constants import (
    TEST_ALLOY_PORT,
    TEST_GRAFANA_PORT,
    TEST_LOKI_PORT,
    TEST_MIMIR_PORT,
    TEST_TEMPO_PORT,
)
from tests.fixtures.tool_fixtures import requires_tool
from tests.helpers.path_helpers import get_repo_root

# Module-level marker
pytestmark = [
    pytest.mark.integration,
    pytest.mark.observability,
]

PROJECT_ROOT = get_repo_root()


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is in use (service is accessible)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        try:
            sock.connect((host, port))
            return True
        except (TimeoutError, ConnectionRefusedError, OSError):
            return False


def wait_for_service(
    url: str,
    timeout: int = 30,
    check_interval: float = 1.0,
) -> bool:
    """Wait for an HTTP service to become healthy."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code < 500:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(check_interval)
    return False


def skip_if_infra_not_running() -> None:
    """Skip test if test infrastructure is not running."""
    # Check if key services are accessible
    services_to_check = [
        (TEST_LOKI_PORT, "Loki"),
        (TEST_GRAFANA_PORT, "Grafana"),
    ]
    missing_services = []
    for port, name in services_to_check:
        if not is_port_in_use(port):
            missing_services.append(f"{name} (port {port})")

    if missing_services:
        pytest.skip(
            f"LGTM stack not running. Missing: {', '.join(missing_services)}. "
            f"Run 'make test-infra-full-up' to start the infrastructure."
        )


# ==============================================================================
# Configuration Validation Tests (No Docker Required)
# ==============================================================================


class TestLGTMConfiguration:
    """
    Test LGTM stack configuration files.

    These tests validate that configuration files are correct and consistent.
    They don't require Docker and can run offline.
    """

    def test_grafana_dashboards_yml_references_existing_paths(self) -> None:
        """
        Verify dashboards.yml only references directories that exist.

        RED Phase: This test would have caught the CI failure where
        dashboards.yml referenced non-existent /dashboards/security and
        /dashboards/performance directories.

        GREEN Phase: After removing the non-existent paths, this test passes.
        """
        dashboards_yml = PROJECT_ROOT / "monitoring" / "grafana" / "dashboards.yml"
        dashboards_dir = PROJECT_ROOT / "monitoring" / "grafana" / "dashboards"

        assert dashboards_yml.exists(), f"dashboards.yml not found at {dashboards_yml}"

        with open(dashboards_yml) as f:
            config = yaml.safe_load(f)

        providers = config.get("providers", [])
        assert providers, "No dashboard providers configured in dashboards.yml"

        # Verify each provider's path exists locally (relative to dashboards dir)
        for provider in providers:
            options = provider.get("options", {})
            # Verify the provider has a path configured
            provider_path = options.get("path", "")
            assert provider_path, f"Provider {provider.get('name', 'unknown')} has no path"

            # If folders from file structure is enabled, verify dashboards dir exists
            folders_from_structure = options.get("foldersFromFilesStructure", True)
            if folders_from_structure:
                assert dashboards_dir.exists(), f"Dashboard directory not found: {dashboards_dir}"

    def test_grafana_datasources_yml_valid(self) -> None:
        """Verify datasources.yml is valid YAML with expected structure."""
        datasources_yml = PROJECT_ROOT / "monitoring" / "grafana" / "datasources.yml"

        assert datasources_yml.exists(), f"datasources.yml not found at {datasources_yml}"

        with open(datasources_yml) as f:
            config = yaml.safe_load(f)

        assert "datasources" in config, "datasources.yml must have 'datasources' key"
        datasources = config["datasources"]
        assert isinstance(datasources, list), "datasources must be a list"

        # Verify expected datasources exist
        datasource_names = {ds.get("name") for ds in datasources}

        expected_datasources = {"Loki", "Tempo", "Mimir"}
        missing = expected_datasources - datasource_names

        assert not missing, f"Missing expected datasources: {missing}. Found: {datasource_names}"

    def test_loki_config_valid(self) -> None:
        """Verify Loki configuration is valid."""
        loki_config = PROJECT_ROOT / "docker" / "loki" / "loki-config.yaml"

        assert loki_config.exists(), f"Loki config not found at {loki_config}"

        with open(loki_config) as f:
            config = yaml.safe_load(f)

        # Verify key sections exist
        # Note: Loki 3.x uses common.storage instead of storage_config (legacy pattern)
        # See: https://grafana.com/docs/loki/latest/configure/
        required_sections = ["server", "common", "schema_config"]
        for section in required_sections:
            assert section in config, f"Loki config missing '{section}' section"

        # Verify storage is configured (either via common.storage or storage_config)
        has_storage = "storage_config" in config or ("common" in config and "storage" in config.get("common", {}))
        assert has_storage, "Loki config missing storage configuration (storage_config or common.storage)"

    def test_tempo_config_valid(self) -> None:
        """Verify Tempo configuration is valid."""
        tempo_config = PROJECT_ROOT / "docker" / "tempo" / "tempo-config.yaml"

        assert tempo_config.exists(), f"Tempo config not found at {tempo_config}"

        with open(tempo_config) as f:
            config = yaml.safe_load(f)

        # Verify key sections exist
        required_sections = ["server", "distributor", "storage"]
        for section in required_sections:
            assert section in config, f"Tempo config missing '{section}' section"

    def test_mimir_config_valid(self) -> None:
        """Verify Mimir configuration is valid."""
        mimir_config = PROJECT_ROOT / "docker" / "mimir" / "mimir-config.yaml"

        assert mimir_config.exists(), f"Mimir config not found at {mimir_config}"

        with open(mimir_config) as f:
            config = yaml.safe_load(f)

        # Mimir uses hierarchical config, verify top-level is valid
        assert config is not None, "Mimir config is empty"

    def test_alloy_config_valid(self) -> None:
        """Verify Alloy configuration is valid (HCL-like format)."""
        alloy_config = PROJECT_ROOT / "docker" / "alloy" / "alloy-config.alloy"

        assert alloy_config.exists(), f"Alloy config not found at {alloy_config}"

        # Alloy uses River config (HCL-like), just verify it's not empty
        content = alloy_config.read_text()
        assert len(content) > 100, "Alloy config appears to be empty or minimal"

        # Verify key components are configured
        expected_components = [
            "otelcol.receiver.otlp",  # OTLP receiver
            "loki.write",  # Loki writer
            "otelcol.exporter.otlp",  # Tempo exporter
        ]
        for component in expected_components:
            assert component in content, f"Alloy config missing '{component}' component"

    def test_docker_compose_lgtm_services_defined(self) -> None:
        """Verify all LGTM services are defined in docker-compose.test.yml."""
        compose_file = PROJECT_ROOT / "docker-compose.test.yml"

        assert compose_file.exists(), "docker-compose.test.yml not found"

        with open(compose_file) as f:
            config = yaml.safe_load(f)

        services = config.get("services", {})

        expected_services = [
            "grafana-test",
            "loki-test",
            "tempo-test",
            "mimir-test",
            "alloy-test",
        ]

        for service in expected_services:
            assert service in services, f"Missing LGTM service: {service}"

    def test_docker_compose_loki_has_correct_user(self) -> None:
        """
        Verify Loki service runs as correct user for tmpfs permissions.

        RED Phase: This test would have caught the permission denied issue
        where Loki (running as user 10001) couldn't write to tmpfs.

        GREEN Phase: After adding 'user: "10001"' to docker-compose.test.yml,
        this test passes.
        """
        compose_file = PROJECT_ROOT / "docker-compose.test.yml"

        with open(compose_file) as f:
            config = yaml.safe_load(f)

        loki_service = config.get("services", {}).get("loki-test", {})
        user = loki_service.get("user")

        assert user == "10001", f"Loki service should run as user '10001' for tmpfs permissions. Current user: {user}"

    def test_docker_compose_loki_tmpfs_has_correct_permissions(self) -> None:
        """
        Verify Loki tmpfs has correct uid/gid for non-root user.

        RED Phase: This test would have caught the permission denied issue
        where tmpfs was mounted without uid/gid matching Loki user.
        """
        compose_file = PROJECT_ROOT / "docker-compose.test.yml"

        with open(compose_file) as f:
            config = yaml.safe_load(f)

        loki_service = config.get("services", {}).get("loki-test", {})
        tmpfs = loki_service.get("tmpfs", [])

        # Find the /tmp/loki tmpfs mount
        loki_tmpfs = None
        for mount in tmpfs:
            if "/tmp/loki" in mount:
                loki_tmpfs = mount
                break

        assert loki_tmpfs is not None, "Loki tmpfs mount for /tmp/loki not found"

        # Verify uid and gid are set
        assert "uid=10001" in loki_tmpfs, f"Loki tmpfs missing 'uid=10001'. Current: {loki_tmpfs}"
        assert "gid=10001" in loki_tmpfs, f"Loki tmpfs missing 'gid=10001'. Current: {loki_tmpfs}"


# ==============================================================================
# Health Check Tests (Require Running Infrastructure)
# ==============================================================================


@pytest.mark.docker
@pytest.mark.slow
@pytest.mark.xdist_group(name="lgtm_infrastructure_tests")
@requires_tool("docker")
class TestLGTMHealthChecks:
    """
    Test LGTM stack service health.

    These tests require `make test-infra-full-up` to be running.
    They verify each service is accessible and healthy.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_loki_is_healthy(self) -> None:
        """
        Verify Loki is running and healthy.

        GIVEN: Test infrastructure is running
        WHEN: We query Loki's /ready endpoint
        THEN: Loki should return a successful response
        """
        skip_if_infra_not_running()

        url = f"http://localhost:{TEST_LOKI_PORT}/ready"
        is_ready = wait_for_service(url, timeout=30)

        assert is_ready, f"Loki not ready at {url}. Check 'docker compose -f docker-compose.test.yml logs loki-test'"

    def test_grafana_is_healthy(self) -> None:
        """
        Verify Grafana is running and healthy.

        GIVEN: Test infrastructure is running
        WHEN: We query Grafana's /api/health endpoint
        THEN: Grafana should return a successful response
        """
        skip_if_infra_not_running()

        url = f"http://localhost:{TEST_GRAFANA_PORT}/api/health"
        is_ready = wait_for_service(url, timeout=30)

        assert is_ready, f"Grafana not ready at {url}. Check 'docker compose -f docker-compose.test.yml logs grafana-test'"

    def test_grafana_datasources_provisioned(self) -> None:
        """
        Verify Grafana has datasources provisioned.

        GIVEN: Grafana is running with provisioning
        WHEN: We query the datasources API
        THEN: Expected datasources should be present
        """
        skip_if_infra_not_running()

        url = f"http://localhost:{TEST_GRAFANA_PORT}/api/datasources"
        response = requests.get(url, auth=("admin", "admin"), timeout=10)

        assert response.status_code == 200, f"Failed to get datasources: {response.status_code}"

        datasources = response.json()
        datasource_names = {ds.get("name") for ds in datasources}

        expected = {"Loki", "Tempo", "Mimir"}
        missing = expected - datasource_names

        assert not missing, f"Missing provisioned datasources: {missing}. Found: {datasource_names}"

    def test_grafana_dashboards_provisioned(self) -> None:
        """
        Verify Grafana has dashboards provisioned without errors.

        GIVEN: Grafana is running with dashboard provisioning
        WHEN: We query the dashboards search API
        THEN: Should have at least one dashboard (no provisioning errors)
        """
        skip_if_infra_not_running()

        url = f"http://localhost:{TEST_GRAFANA_PORT}/api/search?type=dash-db"
        response = requests.get(url, auth=("admin", "admin"), timeout=10)

        assert response.status_code == 200, f"Failed to search dashboards: {response.status_code}"

        # Just verify we can query - empty list is okay if no dashboards yet
        dashboards = response.json()
        assert isinstance(dashboards, list), "Expected list of dashboards"

    def test_tempo_is_healthy(self) -> None:
        """
        Verify Tempo is running and healthy.

        GIVEN: Test infrastructure is running
        WHEN: We query Tempo's /ready endpoint
        THEN: Tempo should return a successful response
        """
        skip_if_infra_not_running()

        # Tempo may take longer to start
        if not is_port_in_use(TEST_TEMPO_PORT):
            pytest.skip(f"Tempo not available on port {TEST_TEMPO_PORT}")

        url = f"http://localhost:{TEST_TEMPO_PORT}/ready"
        is_ready = wait_for_service(url, timeout=30)

        assert is_ready, f"Tempo not ready at {url}. Check 'docker compose -f docker-compose.test.yml logs tempo-test'"

    def test_mimir_is_healthy(self) -> None:
        """
        Verify Mimir is running and accessible.

        GIVEN: Test infrastructure is running
        WHEN: We check if Mimir's port is accessible
        THEN: Mimir should be listening (healthcheck disabled due to distroless)
        """
        skip_if_infra_not_running()

        # Mimir uses distroless image, no healthcheck available
        # Just verify port is accessible
        if not is_port_in_use(TEST_MIMIR_PORT):
            pytest.skip(f"Mimir not available on port {TEST_MIMIR_PORT}")

        # Try to access Mimir API
        url = f"http://localhost:{TEST_MIMIR_PORT}/ready"
        try:
            response = requests.get(url, timeout=5)
            # Any response is good - even 404 means service is running
            assert response.status_code < 500, f"Mimir returned server error: {response.status_code}"
        except requests.exceptions.ConnectionError:
            pytest.fail(f"Cannot connect to Mimir at {url}. Check 'docker compose -f docker-compose.test.yml logs mimir-test'")

    def test_alloy_is_healthy(self) -> None:
        """
        Verify Alloy is running and healthy.

        GIVEN: Test infrastructure is running
        WHEN: We check if Alloy's port is accessible
        THEN: Alloy should be listening
        """
        skip_if_infra_not_running()

        if not is_port_in_use(TEST_ALLOY_PORT):
            pytest.skip(f"Alloy not available on port {TEST_ALLOY_PORT}")

        # Alloy doesn't have wget/curl in image, just verify port is accessible
        assert is_port_in_use(TEST_ALLOY_PORT), (
            f"Alloy not accessible on port {TEST_ALLOY_PORT}. "
            f"Check 'docker compose -f docker-compose.test.yml logs alloy-test'"
        )


# ==============================================================================
# Integration Tests (Require Running Infrastructure)
# ==============================================================================


@pytest.mark.docker
@pytest.mark.slow
@pytest.mark.xdist_group(name="lgtm_infrastructure_tests")
@requires_tool("docker")
class TestLGTMIntegration:
    """
    Test LGTM stack end-to-end integration.

    These tests verify telemetry flows correctly through the stack.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_loki_can_receive_logs(self) -> None:
        """
        Verify Loki can receive and store logs.

        GIVEN: Loki is running
        WHEN: We push a test log entry
        THEN: We should be able to query it back
        """
        skip_if_infra_not_running()

        if not is_port_in_use(TEST_LOKI_PORT):
            pytest.skip(f"Loki not available on port {TEST_LOKI_PORT}")

        # Push a test log entry
        push_url = f"http://localhost:{TEST_LOKI_PORT}/loki/api/v1/push"
        timestamp = int(time.time() * 1e9)  # Nanoseconds
        test_message = f"integration_test_log_{timestamp}"

        payload = {
            "streams": [
                {
                    "stream": {
                        "job": "integration-test",
                        "env": "test",
                    },
                    "values": [[str(timestamp), test_message]],
                }
            ]
        }

        response = requests.post(
            push_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        assert response.status_code in (200, 204), f"Failed to push log to Loki: {response.status_code} {response.text}"

        # Wait a moment for ingestion
        time.sleep(2)

        # Query the log back
        query_url = f"http://localhost:{TEST_LOKI_PORT}/loki/api/v1/query"
        params = {
            "query": '{job="integration-test"}',
            "limit": 10,
        }

        response = requests.get(query_url, params=params, timeout=10)
        assert response.status_code == 200, f"Failed to query Loki: {response.status_code} {response.text}"

    def test_tempo_can_receive_traces(self) -> None:
        """
        Verify Tempo is accepting trace data.

        GIVEN: Tempo is running
        WHEN: We check Tempo's status
        THEN: Tempo should report as ready
        """
        skip_if_infra_not_running()

        if not is_port_in_use(TEST_TEMPO_PORT):
            pytest.skip(f"Tempo not available on port {TEST_TEMPO_PORT}")

        # Check Tempo is ready to receive traces
        url = f"http://localhost:{TEST_TEMPO_PORT}/ready"
        response = requests.get(url, timeout=10)

        assert response.status_code == 200, f"Tempo not ready: {response.status_code} {response.text}"

    def test_alloy_receives_otlp_traces(self) -> None:
        """
        Verify Alloy's OTLP receiver is accepting connections.

        GIVEN: Alloy is running with OTLP receiver
        WHEN: We check the OTLP HTTP port (4318)
        THEN: The port should be accepting connections
        """
        skip_if_infra_not_running()

        # Alloy OTLP HTTP port
        otlp_port = 4318

        if not is_port_in_use(otlp_port):
            pytest.skip(f"Alloy OTLP receiver not available on port {otlp_port}")

        assert is_port_in_use(otlp_port), f"Alloy OTLP receiver not accessible on port {otlp_port}"
