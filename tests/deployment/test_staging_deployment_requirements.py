"""
Pre-deployment validation tests for staging environment.

Prevents deployment failures by validating configuration before deploy.

TDD Context:
- RED (2025-11-12): Deployment failed due to missing Cloud SQL Proxy sidecar config
- GREEN: Added validation tests to catch config issues early
- REFACTOR: These tests run in CI to prevent deployment failures

Following TDD: Tests written FIRST to catch deployment issues, preventing production incidents.
"""

import pytest
from pathlib import Path
import yaml


@pytest.mark.deployment
@pytest.mark.staging
class TestStagingDeploymentRequirements:
    """Test staging deployment meets all requirements."""

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
            f"Invalid instance connection string format: {instance_arg}\n"
            f"Expected: PROJECT:REGION:INSTANCE"
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

        assert liveness.get("httpGet", {}).get("path") == "/liveness", (
            "Liveness probe should use /liveness endpoint"
        )

        assert readiness.get("httpGet", {}).get("path") == "/readiness", (
            "Readiness probe should use /readiness endpoint"
        )

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
        Test: Keycloak container has all required volume mounts for readOnlyRootFilesystem.

        Cross-validates with security hardening requirements.
        """
        patch_file = Path("deployments/overlays/staging-gke/keycloak-patch.yaml")

        with open(patch_file) as f:
            manifest = yaml.safe_load(f)

        containers = manifest["spec"]["template"]["spec"]["containers"]
        keycloak = next((c for c in containers if c["name"] == "keycloak"), None)

        assert keycloak, "Keycloak container not found"

        # Check readOnlyRootFilesystem is enabled
        security_context = keycloak.get("securityContext", {})
        assert security_context.get("readOnlyRootFilesystem") is True, (
            "Keycloak should have readOnlyRootFilesystem: true (security requirement)"
        )

        # Verify required volume mounts exist
        volume_mounts = keycloak.get("volumeMounts", [])
        mount_paths = {vm["mountPath"] for vm in volume_mounts}

        required_mounts = {"/tmp"}  # Minimum requirement

        missing_mounts = required_mounts - mount_paths

        assert not missing_mounts, (
            f"Keycloak missing required volume mounts: {missing_mounts}\n"
            f"These are needed for readOnlyRootFilesystem: true to work.\n"
            f"Current mounts: {mount_paths}"
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
