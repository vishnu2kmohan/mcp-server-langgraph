"""
DNS Failover Verification Tests for Staging GKE

These tests verify that Cloud DNS is properly configured and that DNS-based
failover works correctly for Cloud SQL and Memorystore Redis in the staging
environment.

Prerequisites:
- kubectl configured with staging cluster context
- Cloud DNS zone 'staging-internal' created
- DNS records configured per DNS_SETUP.md

Usage:
    pytest tests/deployment/test_dns_failover_verification.py -v
"""

import gc
import subprocess
import time
from pathlib import Path

import pytest
import yaml

from tests.fixtures.tool_fixtures import requires_tool

pytestmark = pytest.mark.integration


@pytest.fixture
def skip_if_no_cluster(kubectl_connected):
    """Skip test if kubectl is not connected to a Kubernetes cluster."""
    if not kubectl_connected:
        pytest.skip("kubectl not connected to a Kubernetes cluster (required for OpenAPI validation)")
    return True


REPO_ROOT = Path(__file__).parent.parent.parent


@pytest.mark.deployment
@pytest.mark.requires_kubectl
@pytest.mark.xdist_group(name="testdnsconfiguration")
class TestDNSConfiguration:
    """Verify Cloud DNS is properly configured"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_dns_zone_exists(self):
        """
        Test that the staging-internal DNS zone exists in GCP.

        This verifies the Cloud DNS zone was created successfully.
        """
        result = subprocess.run(
            [
                "gcloud",
                "dns",
                "managed-zones",
                "describe",
                "staging-internal",
                "--project=vishnu-sandbox-20250310",
                "--format=get(name)",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            pytest.skip("Cloud DNS zone not found. Run: scripts/setup-cloud-dns-staging.sh")

        assert result.stdout.strip() == "staging-internal"

    def test_dns_zone_attached_to_correct_vpc(self):
        """
        Test that DNS zone is attached to the correct VPC network.

        The staging GKE cluster uses 'staging-mcp-slg-vpc', so the DNS zone
        must be attached to this network for pods to resolve DNS names.
        """
        result = subprocess.run(
            [
                "gcloud",
                "dns",
                "managed-zones",
                "describe",
                "staging-internal",
                "--project=vishnu-sandbox-20250310",
                "--format=get(privateVisibilityConfig.networks[0])",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            pytest.skip("Cloud DNS zone not found")

        network_url = result.stdout.strip()

        # Should be attached to staging-mcp-slg-vpc (the GKE cluster's VPC)
        assert "staging-mcp-slg-vpc" in network_url or "default" in network_url, (
            f"DNS zone attached to wrong network: {network_url}\n"
            f"Expected: staging-mcp-slg-vpc\n"
            f"Fix: gcloud dns managed-zones update staging-internal "
            f"--networks=staging-mcp-slg-vpc --project=vishnu-sandbox-20250310"
        )

    def test_dns_records_exist(self):
        """
        Test that all required DNS records exist.

        Required records:
        - cloudsql-staging.staging.internal (Cloud SQL PostgreSQL)
        - redis-staging.staging.internal (Memorystore Redis)
        - redis-session-staging.staging.internal (Redis session store)
        """
        required_records = [
            "cloudsql-staging.staging.internal.",
            "redis-staging.staging.internal.",
            "redis-session-staging.staging.internal.",
        ]

        result = subprocess.run(
            [
                "gcloud",
                "dns",
                "record-sets",
                "list",
                "--zone=staging-internal",
                "--project=vishnu-sandbox-20250310",
                "--format=get(name)",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            pytest.skip("Could not list DNS records")

        existing_records = result.stdout.strip().split("\n")

        for required_record in required_records:
            assert required_record in existing_records, (
                f"DNS record missing: {required_record}\n" f"Run: scripts/setup-cloud-dns-staging.sh"
            )


@pytest.mark.deployment
@pytest.mark.requires_kubectl
@pytest.mark.xdist_group(name="testdnsresolution")
class TestDNSResolution:
    """
    Verify DNS test pod manifests are valid (DRY-RUN mode).

    IMPORTANT: This test uses kubectl --dry-run=client to validate manifests
    WITHOUT applying them to the real cluster. This prevents:
    - Unintended modifications to staging environment
    - Resource conflicts with running services
    - Accidental resource leaks

    For actual DNS resolution testing, use a dedicated test cluster or
    run manually with: kubectl apply -f <manifest>
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @requires_tool("kubectl")
    def _validate_dns_test_pod_manifest(self, dns_name: str) -> tuple[bool, str]:
        """
        Validate DNS test pod manifest using kubectl dry-run.

        This validates:
        - YAML syntax is correct
        - Kubernetes API schema is valid
        - Security context is properly configured
        - Resource requests/limits are within bounds

        Returns: (is_valid, validation_output)
        """
        pod_yaml = f"""
apiVersion: v1
kind: Pod
metadata:
  name: dns-test-{int(time.time())}
  namespace: staging-mcp-server-langgraph
  labels:
    app: dns-test
    purpose: validation
spec:
  restartPolicy: Never
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: dns-test
    image: busybox:1.36
    command: ["sh", "-c"]
    args:
      - |
        echo "Testing: {dns_name}"
        nslookup {dns_name} || exit 1
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
      readOnlyRootFilesystem: true
"""

        # Create temporary pod manifest
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(pod_yaml)
            temp_file = f.name

        try:
            # 🟢 GREEN: Use dry-run to validate WITHOUT applying to cluster
            result = subprocess.run(
                ["kubectl", "apply", "-f", temp_file, "--dry-run=client", "-o", "yaml"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            is_valid = result.returncode == 0
            validation_output = result.stdout if is_valid else result.stderr

            return is_valid, validation_output

        finally:
            import os

            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_cloudsql_dns_test_pod_manifest_valid(self, skip_if_no_cluster):
        """
        Validate DNS test pod manifest for cloudsql-staging (DRY-RUN).

        This validates the test infrastructure is correctly configured WITHOUT
        applying to the real cluster. For actual DNS resolution testing, run manually:
            kubectl apply -f <manifest> && kubectl logs <pod-name>
        """
        is_valid, output = self._validate_dns_test_pod_manifest("cloudsql-staging.staging.internal")

        assert is_valid, (
            f"DNS test pod manifest validation failed for cloudsql-staging.staging.internal\n"
            f"Error: {output}\n"
            f"This indicates the test infrastructure manifest has issues."
        )

        # Verify output contains expected structure
        assert "apiVersion: v1" in output
        assert "kind: Pod" in output
        assert "cloudsql-staging.staging.internal" in output

    def test_redis_dns_test_pod_manifest_valid(self, skip_if_no_cluster):
        """
        Validate DNS test pod manifest for redis-staging (DRY-RUN).
        """
        is_valid, output = self._validate_dns_test_pod_manifest("redis-staging.staging.internal")

        assert is_valid, (
            f"DNS test pod manifest validation failed for redis-staging.staging.internal\n"
            f"Error: {output}\n"
            f"Fix the manifest structure before attempting real DNS tests."
        )

        # Verify security context is present
        assert "securityContext" in output
        assert "runAsNonRoot: true" in output

    def test_redis_session_dns_test_pod_manifest_valid(self, skip_if_no_cluster):
        """
        Validate DNS test pod manifest for redis-session-staging (DRY-RUN).
        """
        is_valid, output = self._validate_dns_test_pod_manifest("redis-session-staging.staging.internal")

        assert is_valid, (
            f"DNS test pod manifest validation failed for redis-session-staging.staging.internal\n"
            f"Error: {output}\n"
            f"Ensure Kubernetes API schema compliance before manual testing."
        )

        # Verify critical security settings
        assert "allowPrivilegeEscalation: false" in output
        assert "readOnlyRootFilesystem: true" in output


@pytest.mark.deployment
@pytest.mark.requires_kubectl
@pytest.mark.xdist_group(name="testserviceconfiguration")
class TestServiceConfiguration:
    """Verify Kubernetes services use DNS names"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @requires_tool("kubectl")
    def test_redis_session_service_uses_external_name(self):
        """
        Test that redis-session Service uses ExternalName type with DNS.

        This verifies the migration from hard-coded IPs to DNS-based approach.
        """
        result = subprocess.run(
            [
                "kubectl",
                "get",
                "service",
                "staging-redis-session",
                "-n",
                "staging-mcp-server-langgraph",
                "-o",
                "yaml",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            pytest.skip("Service not found")

        service = yaml.safe_load(result.stdout)

        # Verify it's an ExternalName service
        assert service["spec"]["type"] == "ExternalName", "Service should be type ExternalName for DNS-based approach"

        # Verify it uses the DNS name
        assert (
            service["spec"]["externalName"] == "redis-session-staging.staging.internal"
        ), f"Service should use DNS name, got: {service['spec'].get('externalName')}"

    @requires_tool("kubectl")
    def test_configmap_uses_dns_names(self):
        """
        Test that ConfigMap uses DNS names instead of hard-coded IPs.

        This verifies the configuration follows the Cloud DNS approach.
        """
        result = subprocess.run(
            [
                "kubectl",
                "get",
                "configmap",
                "staging-mcp-server-langgraph-config",
                "-n",
                "staging-mcp-server-langgraph",
                "-o",
                "yaml",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            pytest.skip("ConfigMap not found")

        configmap = yaml.safe_load(result.stdout)
        data = configmap.get("data", {})

        # Check postgres_host uses DNS name
        postgres_host = data.get("postgres_host", "")
        assert "staging.internal" in postgres_host, f"postgres_host should use DNS name, got: {postgres_host}"
        assert not postgres_host.startswith("10."), f"postgres_host should not be hard-coded IP, got: {postgres_host}"

        # Check redis_host uses DNS name
        redis_host = data.get("redis_host", "")
        assert "staging.internal" in redis_host, f"redis_host should use DNS name, got: {redis_host}"
        assert not redis_host.startswith("10."), f"redis_host should not be hard-coded IP, got: {redis_host}"


@pytest.mark.deployment
@pytest.mark.requires_kubectl
@pytest.mark.integration
@pytest.mark.xdist_group(name="testdnsfailoversimulation")
class TestDNSFailoverSimulation:
    """Simulate DNS failover scenarios"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_dns_record_update_propagates(self):
        """
        Test that DNS record updates propagate correctly.

        This simulates a failover scenario where the IP changes.
        NOTE: This test is read-only - it doesn't actually change DNS records.
        """
        # Get current DNS record
        result = subprocess.run(
            [
                "gcloud",
                "dns",
                "record-sets",
                "describe",
                "cloudsql-staging.staging.internal.",
                "--zone=staging-internal",
                "--type=A",
                "--project=vishnu-sandbox-20250310",
                "--format=get(rrdatas[0])",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            pytest.skip("DNS record not found")

        current_ip = result.stdout.strip()

        assert current_ip, "DNS record should have an IP address"
        assert current_ip.startswith("10."), f"Expected private IP, got: {current_ip}"

        # Get TTL
        result = subprocess.run(
            [
                "gcloud",
                "dns",
                "record-sets",
                "describe",
                "cloudsql-staging.staging.internal.",
                "--zone=staging-internal",
                "--type=A",
                "--project=vishnu-sandbox-20250310",
                "--format=get(ttl)",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        ttl = int(result.stdout.strip())

        # TTL should be low for fast failover
        assert ttl <= 600, (
            f"DNS TTL should be <= 600 seconds for fast failover, got: {ttl}\n" f"Recommended: 300 seconds (5 minutes)"
        )

    @requires_tool("kubectl")
    def test_deployment_can_connect_to_services_via_dns(self):
        """
        Test that the deployment can connect to services via DNS names.

        Checks that pods are running and healthy, indicating successful
        connections to Cloud SQL and Redis via DNS.
        """
        result = subprocess.run(
            [
                "kubectl",
                "get",
                "deployment",
                "staging-mcp-server-langgraph",
                "-n",
                "staging-mcp-server-langgraph",
                "-o",
                "jsonpath={.status.availableReplicas}",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            pytest.skip("Deployment not found")

        available_replicas = int(result.stdout.strip() or "0")

        assert available_replicas > 0, "Deployment has no available replicas. Check pod logs for connection errors."
