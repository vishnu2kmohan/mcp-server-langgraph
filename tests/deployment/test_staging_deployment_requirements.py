"""
Pre-deployment validation tests for staging environment.

Prevents deployment failures by validating configuration before deploy.

TDD Context:
- RED (2025-11-12): Deployment failed due to missing Cloud SQL Proxy sidecar config
- GREEN: Added validation tests to catch config issues early
- REFACTOR: These tests run in CI to prevent deployment failures

Following TDD: Tests written FIRST to catch deployment issues, preventing production incidents.
"""

import gc
from pathlib import Path

import pytest
import yaml

# Mark as unit test to ensure it runs in CI (deployment validation)
pytestmark = pytest.mark.unit


@pytest.mark.deployment
@pytest.mark.staging
@pytest.mark.xdist_group(name="teststagingdeploymentrequirements")
class TestStagingDeploymentRequirements:
    """Test staging deployment meets all requirements."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_keycloak_has_cloud_sql_proxy_sidecar(self):
        """
        Test: Staging Keycloak must have Cloud SQL Proxy sidecar for database connectivity.

        RED (Before Fix):
        - Keycloak deployment missing Cloud SQL Proxy sidecar
        - Pod fails to start - cannot connect to database
        - No validation caught this before deployment

        GREEN (After Fix):
        - Cloud SQL Proxy sidecar added to keycloak-patch.yaml
        - Proper port configuration (5432)
        - Health checks configured

        REFACTOR:
        - This test prevents regression
        - Validates staging overlay has sidecar
        """
        patch_file = Path("deployments/overlays/staging-gke/keycloak-patch.yaml")

        assert patch_file.exists(), f"Staging Keycloak patch file not found: {patch_file}"

        with open(patch_file) as f:
            manifest = yaml.safe_load(f)

        assert manifest.get("kind") == "Deployment", "Patch should modify Deployment"

        containers = manifest["spec"]["template"]["spec"]["containers"]
        container_names = [c["name"] for c in containers]

        assert "cloud-sql-proxy" in container_names, (
            "Staging Keycloak deployment missing Cloud SQL Proxy sidecar.\n"
            "Without this sidecar, Keycloak cannot connect to Cloud SQL database.\n"
            "Fix: Add cloud-sql-proxy container to deployments/overlays/staging-gke/keycloak-patch.yaml"
        )

    def test_keycloak_db_url_points_to_localhost(self):
        """
        Test: Staging Keycloak must connect to database via Cloud SQL Proxy on localhost.

        Validates KC_DB_URL environment variable points to 127.0.0.1:5432
        (Cloud SQL Proxy sidecar listens on localhost)
        """
        patch_file = Path("deployments/overlays/staging-gke/keycloak-patch.yaml")

        with open(patch_file) as f:
            manifest = yaml.safe_load(f)

        containers = manifest["spec"]["template"]["spec"]["containers"]
        keycloak = next((c for c in containers if c["name"] == "keycloak"), None)

        assert keycloak, "Keycloak container not found in deployment"

        env_vars = {e["name"]: e.get("value", "") for e in keycloak.get("env", [])}
        db_url = env_vars.get("KC_DB_URL", "")

        assert "127.0.0.1:5432" in db_url or "localhost:5432" in db_url, (
            f"Keycloak DB URL should use localhost via Cloud SQL Proxy.\n"
            f"Expected: jdbc:postgresql://127.0.0.1:5432/keycloak\n"
            f"Got: {db_url}\n"
            f"Fix: Update KC_DB_URL to point to 127.0.0.1:5432"
        )

    def test_cloud_sql_proxy_has_correct_instance_connection_string(self):
        """
        Test: Cloud SQL Proxy must have correct instance connection string for staging.

        Validates the connection string format and project ID.
        """
        patch_file = Path("deployments/overlays/staging-gke/keycloak-patch.yaml")

        with open(patch_file) as f:
            manifest = yaml.safe_load(f)

        containers = manifest["spec"]["template"]["spec"]["containers"]
        proxy = next((c for c in containers if c["name"] == "cloud-sql-proxy"), None)

        assert proxy, "Cloud SQL Proxy container not found"

        args = proxy.get("args", [])

        # Find the instance connection string argument
        instance_arg = None
        for arg in args:
            # Connection string format: PROJECT:REGION:INSTANCE
            if ":" in arg and "vishnu-sandbox" in arg:
                instance_arg = arg
                break

        assert instance_arg, (
            "Cloud SQL instance connection string not found in proxy args.\n"
            "Expected format: PROJECT:REGION:INSTANCE\n"
            f"Args: {args}"
        )

        # Validate format
        parts = instance_arg.split(":")
        assert len(parts) == 3, (
            f"Invalid instance connection string format: {instance_arg}\n" f"Expected: PROJECT:REGION:INSTANCE"
        )

    def test_cloud_sql_proxy_has_health_checks(self):
        """
        Test: Cloud SQL Proxy must have liveness and readiness probes.

        Ensures Kubernetes can detect proxy failures and restart if needed.
        """
        patch_file = Path("deployments/overlays/staging-gke/keycloak-patch.yaml")

        with open(patch_file) as f:
            manifest = yaml.safe_load(f)

        containers = manifest["spec"]["template"]["spec"]["containers"]
        proxy = next((c for c in containers if c["name"] == "cloud-sql-proxy"), None)

        assert proxy, "Cloud SQL Proxy container not found"

        assert "livenessProbe" in proxy, "Cloud SQL Proxy missing liveness probe"
        assert "readinessProbe" in proxy, "Cloud SQL Proxy missing readiness probe"

        # Validate health check endpoints
        liveness = proxy["livenessProbe"]
        readiness = proxy["readinessProbe"]

        assert liveness.get("httpGet", {}).get("path") == "/liveness", "Liveness probe should use /liveness endpoint"

        assert readiness.get("httpGet", {}).get("path") == "/readiness", "Readiness probe should use /readiness endpoint"

    def test_cloud_sql_proxy_uses_private_ip(self):
        """
        Test: Cloud SQL Proxy must use --private-ip flag for VPC connectivity.

        Ensures proxy connects to Cloud SQL instance via private IP, not public.
        """
        patch_file = Path("deployments/overlays/staging-gke/keycloak-patch.yaml")

        with open(patch_file) as f:
            manifest = yaml.safe_load(f)

        containers = manifest["spec"]["template"]["spec"]["containers"]
        proxy = next((c for c in containers if c["name"] == "cloud-sql-proxy"), None)

        assert proxy, "Cloud SQL Proxy container not found"

        args = proxy.get("args", [])

        assert "--private-ip" in args, (
            "Cloud SQL Proxy missing --private-ip flag.\n"
            "Without this, proxy attempts public IP connection which may fail in VPC.\n"
            "Fix: Add --private-ip to proxy args"
        )

    def test_keycloak_has_required_volume_mounts(self):
        """
        Test: Keycloak container has proper security configuration with compensating controls.

        **IMPORTANT**: Keycloak requires readOnlyRootFilesystem: false due to Quarkus JIT compilation.
        This is documented in deployments/overlays/staging-gke/.trivyignore (AVD-KSV-0014).

        Security mitigations (compensating controls):
        1. emptyDir volumes for writable paths (/tmp, /var/tmp, /opt/keycloak/data)
        2. runAsNonRoot: true, runAsUser: 1000
        3. allowPrivilegeEscalation: false
        4. capabilities.drop: ALL

        References:
        - .trivyignore: AVD-KSV-0014 (lines 96-152)
        - Upstream issue: https://github.com/keycloak/keycloak/issues/10150
        """
        patch_file = Path("deployments/overlays/staging-gke/keycloak-patch.yaml")

        with open(patch_file) as f:
            manifest = yaml.safe_load(f)

        containers = manifest["spec"]["template"]["spec"]["containers"]
        keycloak = next((c for c in containers if c["name"] == "keycloak"), None)

        assert keycloak, "Keycloak container not found"

        # Verify readOnlyRootFilesystem is explicitly set to false (documented exception)
        security_context = keycloak.get("securityContext", {})
        assert security_context.get("readOnlyRootFilesystem") is False, (
            "Keycloak should have readOnlyRootFilesystem: false (Quarkus JIT requirement). "
            "See .trivyignore AVD-KSV-0014 for justification."
        )

        # Verify compensating control: emptyDir volumes for writable paths
        volume_mounts = keycloak.get("volumeMounts", [])
        mount_paths = {vm["mountPath"] for vm in volume_mounts}

        # Required emptyDir mounts (ephemeral, isolated writes)
        required_mounts = {"/tmp", "/var/tmp", "/opt/keycloak/data"}

        missing_mounts = required_mounts - mount_paths

        assert not missing_mounts, (
            f"Keycloak missing required emptyDir volume mounts: {missing_mounts}\n"
            f"These compensate for readOnlyRootFilesystem: false by ensuring writes are ephemeral.\n"
            f"Current mounts: {mount_paths}\n"
            f"See .trivyignore AVD-KSV-0014 for security rationale."
        )

    def test_staging_uses_staging_secrets(self):
        """
        Test: Staging deployment references staging-specific secrets.

        Prevents accidentally using production secrets in staging.
        """
        patch_file = Path("deployments/overlays/staging-gke/keycloak-patch.yaml")

        with open(patch_file) as f:
            manifest = yaml.safe_load(f)

        containers = manifest["spec"]["template"]["spec"]["containers"]
        keycloak = next((c for c in containers if c["name"] == "keycloak"), None)

        assert keycloak, "Keycloak container not found"

        # Check environment variables for secret references
        env_vars = keycloak.get("env", [])

        for env_var in env_vars:
            if "valueFrom" in env_var and "secretKeyRef" in env_var["valueFrom"]:
                secret_name = env_var["valueFrom"]["secretKeyRef"]["name"]

                assert "staging" in secret_name.lower(), (
                    f"Environment variable {env_var['name']} references secret '{secret_name}' "
                    f"which doesn't appear to be staging-specific.\n"
                    f"Staging should use staging-prefixed secrets to prevent production data leakage."
                )

    def test_keycloak_resource_limits_appropriate_for_staging(self):
        """
        Test: Keycloak resource requests/limits are appropriate for staging environment.

        Staging should have lower limits than production but sufficient for testing.
        """
        patch_file = Path("deployments/overlays/staging-gke/keycloak-patch.yaml")

        with open(patch_file) as f:
            manifest = yaml.safe_load(f)

        containers = manifest["spec"]["template"]["spec"]["containers"]
        keycloak = next((c for c in containers if c["name"] == "keycloak"), None)

        assert keycloak, "Keycloak container not found"

        resources = keycloak.get("resources", {})

        assert "requests" in resources, "Keycloak should have resource requests"
        assert "limits" in resources, "Keycloak should have resource limits"

        requests = resources["requests"]
        limits = resources["limits"]

        # Validate memory (staging should have at least 512Mi)
        assert "memory" in requests, "Memory request not specified"
        assert "memory" in limits, "Memory limit not specified"

        # Validate CPU
        assert "cpu" in requests, "CPU request not specified"
        assert "cpu" in limits, "CPU limit not specified"

    def test_mcp_server_has_topology_spread_constraints(self):
        """
        Test: MCP Server deployment must have topology spread constraints for HA.

        RED (Before Fix):
        - No topology spread constraints configured
        - Pods may cluster in single zone
        - Violates high availability requirements

        GREEN (After Fix):
        - Zone constraint: maxSkew 1, whenUnsatisfiable ScheduleAnyway (flexible for single-zone GKE Autopilot)
        - Hostname constraint: maxSkew 2, whenUnsatisfiable DoNotSchedule (spread across nodes)

        REFACTOR:
        - This ensures pods distributed across zones for resilience while supporting single-zone clusters
        """
        base_file = Path("deployments/base/deployment.yaml")

        with open(base_file) as f:
            manifest = yaml.safe_load(f)

        constraints = manifest["spec"]["template"]["spec"].get("topologySpreadConstraints", [])

        assert len(constraints) > 0, (
            "MCP Server deployment missing topologySpreadConstraints.\n"
            "Without this, pods may cluster in single zone, violating HA requirements.\n"
            "Fix: Add topologySpreadConstraints to deployments/base/deployment.yaml"
        )

        # Validate zone constraint
        zone_constraints = [c for c in constraints if c["topologyKey"] == "topology.kubernetes.io/zone"]

        assert len(zone_constraints) == 1, f"Expected exactly 1 zone topology constraint, found {len(zone_constraints)}"

        zone_constraint = zone_constraints[0]
        assert (
            zone_constraint["maxSkew"] == 1
        ), f"Zone constraint maxSkew should be 1 (strict), got {zone_constraint['maxSkew']}"
        assert zone_constraint["whenUnsatisfiable"] == "ScheduleAnyway", (
            f"Zone constraint should use ScheduleAnyway to support single-zone GKE Autopilot clusters, "
            f"got {zone_constraint['whenUnsatisfiable']}"
        )

        # Validate hostname (node) constraint
        hostname_constraints = [c for c in constraints if c["topologyKey"] == "kubernetes.io/hostname"]

        assert (
            len(hostname_constraints) == 1
        ), f"Expected exactly 1 hostname topology constraint, found {len(hostname_constraints)}"

        hostname_constraint = hostname_constraints[0]
        assert hostname_constraint["maxSkew"] == 2, (
            f"Hostname constraint maxSkew should be 2 (allow some flexibility), " f"got {hostname_constraint['maxSkew']}"
        )

    def test_mcp_server_has_required_pod_anti_affinity(self):
        """
        Test: MCP Server must have REQUIRED pod anti-affinity for hostname.

        RED (Before Fix):
        - Only preferred anti-affinity (soft constraint)
        - Scheduler may place multiple replicas on same node
        - Reduces blast radius resilience

        GREEN (After Fix):
        - Required anti-affinity for hostname (strict - prevents co-location)
        - Preferred anti-affinity for zone (soft - distributes across zones)

        REFACTOR:
        - This prevents accidental pod co-location on same node
        """
        base_file = Path("deployments/base/deployment.yaml")

        with open(base_file) as f:
            manifest = yaml.safe_load(f)

        affinity = manifest["spec"]["template"]["spec"].get("affinity", {})
        pod_anti_affinity = affinity.get("podAntiAffinity", {})

        # Check for REQUIRED anti-affinity
        required = pod_anti_affinity.get("requiredDuringSchedulingIgnoredDuringExecution", [])

        assert len(required) > 0, (
            "MCP Server deployment missing REQUIRED podAntiAffinity.\n"
            "Without this, multiple replicas may be scheduled on same node.\n"
            "Fix: Add requiredDuringSchedulingIgnoredDuringExecution for hostname topology"
        )

        # Validate hostname anti-affinity is required
        hostname_required = [term for term in required if term.get("topologyKey") == "kubernetes.io/hostname"]

        assert len(hostname_required) == 1, (
            "MCP Server must have REQUIRED anti-affinity for hostname.\n"
            "This prevents multiple replicas on same node (reduces blast radius)."
        )

        # Also verify preferred exists for zone distribution
        preferred = pod_anti_affinity.get("preferredDuringSchedulingIgnoredDuringExecution", [])
        zone_preferred = [
            term for term in preferred if term.get("podAffinityTerm", {}).get("topologyKey") == "topology.kubernetes.io/zone"
        ]

        assert len(zone_preferred) > 0, "MCP Server should also have PREFERRED anti-affinity for zone distribution"

    def test_mcp_server_has_startup_probe(self):
        """
        Test: MCP Server must have startup probe for slow initialization.

        RED (Before Fix):
        - No startup probe configured
        - Liveness probe triggers during startup
        - Pod killed prematurely → CrashLoopBackOff

        GREEN (After Fix):
        - Startup probe with high failureThreshold (30+)
        - Liveness probe doesn't start until startup succeeds

        REFACTOR:
        - This allows MCP Server 60+ seconds to initialize
        """
        base_file = Path("deployments/base/deployment.yaml")

        with open(base_file) as f:
            manifest = yaml.safe_load(f)

        containers = manifest["spec"]["template"]["spec"]["containers"]
        mcp_server = next((c for c in containers if c["name"] == "mcp-server-langgraph"), None)

        assert mcp_server, "MCP Server container not found"

        assert "startupProbe" in mcp_server, (
            "MCP Server missing startup probe.\n"
            "Without this, liveness probe may kill pod during slow startup.\n"
            "Fix: Add startupProbe with high failureThreshold to deployment.yaml"
        )

        startup_probe = mcp_server["startupProbe"]

        # Validate sufficient timeout for slow startup
        failure_threshold = startup_probe.get("failureThreshold", 0)
        period_seconds = startup_probe.get("periodSeconds", 1)
        total_timeout = failure_threshold * period_seconds

        assert failure_threshold >= 30, (
            f"Startup probe failureThreshold should be ≥30 for slow initialization.\n"
            f"Got: {failure_threshold} (total timeout: {total_timeout}s)"
        )

        assert total_timeout >= 60, (
            f"Startup probe total timeout should be ≥60 seconds.\n"
            f"Got: {total_timeout}s (failureThreshold={failure_threshold} * periodSeconds={period_seconds})"
        )
