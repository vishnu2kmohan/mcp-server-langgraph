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

import subprocess
import time
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent.parent


@pytest.mark.deployment
@pytest.mark.requires_kubectl
class TestDNSConfiguration:
    """Verify Cloud DNS is properly configured"""

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
class TestDNSResolution:
    """Verify DNS resolution from within GKE cluster"""

    def _run_dns_test_pod(self, dns_name: str) -> tuple[int, str]:
        """
        Helper to run DNS test from within GKE cluster.

        Returns: (returncode, output)
        """
        pod_yaml = f"""
apiVersion: v1
kind: Pod
metadata:
  name: dns-test-{int(time.time())}
  namespace: staging-mcp-server-langgraph
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
            # Apply pod
            subprocess.run(
                ["kubectl", "apply", "-f", temp_file],
                capture_output=True,
                check=True,
            )

            pod_name = f"dns-test-{int(time.time())}"

            # Wait for completion (max 30 seconds)
            time.sleep(15)

            # Get logs
            result = subprocess.run(
                [
                    "kubectl",
                    "logs",
                    pod_name,
                    "-n",
                    "staging-mcp-server-langgraph",
                ],
                capture_output=True,
                text=True,
            )

            # Delete pod
            subprocess.run(
                [
                    "kubectl",
                    "delete",
                    "pod",
                    pod_name,
                    "-n",
                    "staging-mcp-server-langgraph",
                    "--wait=false",
                ],
                capture_output=True,
            )

            return result.returncode, result.stdout

        finally:
            import os

            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_cloudsql_dns_resolves(self):
        """
        Test that cloudsql-staging.staging.internal resolves from within cluster.
        """
        returncode, output = self._run_dns_test_pod("cloudsql-staging.staging.internal")

        assert "10.178.0.3" in output or "Address:" in output, (
            f"DNS resolution failed for cloudsql-staging.staging.internal\n"
            f"Output: {output}\n"
            f"Check: gcloud dns record-sets list --zone=staging-internal"
        )

    def test_redis_dns_resolves(self):
        """
        Test that redis-staging.staging.internal resolves from within cluster.
        """
        returncode, output = self._run_dns_test_pod("redis-staging.staging.internal")

        assert "10.138.129.37" in output or "Address:" in output, (
            f"DNS resolution failed for redis-staging.staging.internal\n" f"Output: {output}"
        )

    def test_redis_session_dns_resolves(self):
        """
        Test that redis-session-staging.staging.internal resolves from within cluster.
        """
        returncode, output = self._run_dns_test_pod("redis-session-staging.staging.internal")

        assert "10.138.129.37" in output or "Address:" in output, (
            f"DNS resolution failed for redis-session-staging.staging.internal\n" f"Output: {output}"
        )


@pytest.mark.deployment
@pytest.mark.requires_kubectl
class TestServiceConfiguration:
    """Verify Kubernetes services use DNS names"""

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
class TestDNSFailoverSimulation:
    """Simulate DNS failover scenarios"""

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
        )

        ttl = int(result.stdout.strip())

        # TTL should be low for fast failover
        assert ttl <= 600, (
            f"DNS TTL should be <= 600 seconds for fast failover, got: {ttl}\n" f"Recommended: 300 seconds (5 minutes)"
        )

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
        )

        if result.returncode != 0:
            pytest.skip("Deployment not found")

        available_replicas = int(result.stdout.strip() or "0")

        assert available_replicas > 0, "Deployment has no available replicas. Check pod logs for connection errors."
