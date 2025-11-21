"""
Integration tests for External Secrets Operator RBAC configuration on GKE staging.

Tests validate that:
1. GCP service account has proper IAM roles (container.admin)
2. ESO is installed with all required components
3. ESO RBAC resources are created (ClusterRoles, ClusterRoleBindings)
4. ESO can sync secrets from GCP Secret Manager

These are integration tests that require:
- GKE cluster access (kubectl configured)
- GCP credentials with appropriate permissions
- ESO installed on the cluster

Run with: pytest tests/infrastructure/test_external_secrets_rbac.py -v --integration
"""

import gc
import json
import os
import subprocess
from typing import Any

import pytest

pytestmark = pytest.mark.integration


# Helper functions for kubectl commands
def run_kubectl(args: list[str], namespace: str | None = None, check: bool = True) -> dict[str, Any]:
    """
    Run kubectl command and return parsed output.

    Args:
        args: kubectl arguments (e.g., ['get', 'pods'])
        namespace: Optional namespace to use
        check: Whether to raise exception on non-zero exit code

    Returns:
        Dict with 'success', 'output', 'error' keys
    """
    cmd = ["kubectl"] + args
    if namespace:
        cmd.extend(["-n", namespace])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=check, timeout=30)
        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip(),
            "error": result.stderr.strip(),
            "returncode": result.returncode,
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "output": e.stdout.strip() if e.stdout else "",
            "error": e.stderr.strip() if e.stderr else "",
            "returncode": e.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "", "error": "Command timed out", "returncode": -1}


def run_gcloud(args: list[str], check: bool = True) -> dict[str, Any]:
    """
    Run gcloud command and return parsed output.

    Args:
        args: gcloud arguments
        check: Whether to raise exception on non-zero exit code

    Returns:
        Dict with 'success', 'output', 'error' keys
    """
    cmd = ["gcloud"] + args

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=check, timeout=30)
        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip(),
            "error": result.stderr.strip(),
            "returncode": result.returncode,
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "output": e.stdout.strip() if e.stdout else "",
            "error": e.stderr.strip() if e.stderr else "",
            "returncode": e.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "", "error": "Command timed out", "returncode": -1}


# Fixtures
@pytest.fixture(scope="module")
def gcp_project_id() -> str:
    """Get GCP project ID from environment or gcloud config."""
    project_id = os.getenv("GCP_PROJECT_ID")
    if not project_id:
        result = run_gcloud(["config", "get-value", "project"])
        if result["success"]:
            project_id = result["output"]

    if not project_id:
        pytest.skip("GCP_PROJECT_ID not set and gcloud config not available")

    return project_id


@pytest.fixture(scope="module")
def gcp_service_account_email() -> str:
    """Get GCP service account email from environment."""
    sa_email = os.getenv("GCP_SERVICE_ACCOUNT_EMAIL", "github-actions-gke@{project}.iam.gserviceaccount.com")
    if "{project}" in sa_email:
        pytest.skip("GCP_SERVICE_ACCOUNT_EMAIL not configured")
    return sa_email


@pytest.fixture(scope="module")
def kubectl_available() -> bool:
    """Check if kubectl is available and configured."""
    result = run_kubectl(["version", "--client", "-o", "json"], check=False)
    return result["success"]


@pytest.fixture(scope="module")
def gcloud_available() -> bool:
    """Check if gcloud is available and authenticated."""
    result = run_gcloud(["auth", "list", "--format=json"], check=False)
    if not result["success"]:
        return False

    try:
        accounts = json.loads(result["output"])
        return len(accounts) > 0
    except (json.JSONDecodeError, KeyError):
        return False


@pytest.fixture(scope="module")
def eso_installed() -> bool:
    """Check if External Secrets Operator is installed on the cluster."""
    # Check for ESO CRDs as a reliable indicator of ESO installation
    result = run_kubectl(["get", "crd", "externalsecrets.external-secrets.io"], check=False)
    return result["success"]


@pytest.fixture(scope="module")
def skip_if_not_gke(kubectl_available: bool, gcloud_available: bool, eso_installed: bool):
    """Skip tests if not in GKE environment with ESO installed."""
    if not kubectl_available:
        pytest.skip("kubectl not available or not configured")
    if not gcloud_available:
        pytest.skip("gcloud not available or not authenticated")
    if not eso_installed:
        pytest.skip("External Secrets Operator not installed on cluster")


# Test Classes
@pytest.mark.requires_kubectl
@pytest.mark.xdist_group(name="testgcpserviceaccountiam")
class TestGCPServiceAccountIAM:
    """Test GCP service account has proper IAM roles for ESO installation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.integration
    def test_service_account_exists(self, skip_if_not_gke, gcp_project_id: str, gcp_service_account_email: str):
        """Test that the GCP service account exists."""
        result = run_gcloud(
            ["iam", "service-accounts", "describe", gcp_service_account_email, "--project", gcp_project_id, "--format=json"],
            check=False,
        )

        assert result["success"], f"Service account {gcp_service_account_email} not found: {result['error']}"

        sa_info = json.loads(result["output"])
        assert sa_info["email"] == gcp_service_account_email

    @pytest.mark.integration
    def test_service_account_has_container_admin_role(
        self, skip_if_not_gke, gcp_project_id: str, gcp_service_account_email: str
    ):
        """
        Test that service account has roles/container.admin for RBAC creation.

        This is critical for ESO installation as it requires cluster-scoped
        RBAC resource creation (ClusterRoles, ClusterRoleBindings).
        """
        result = run_gcloud(
            [
                "projects",
                "get-iam-policy",
                gcp_project_id,
                "--flatten=bindings[].members",
                f"--filter=bindings.members:serviceAccount:{gcp_service_account_email}",
                "--format=json",
            ]
        )

        assert result["success"], f"Failed to get IAM policy: {result['error']}"

        bindings = json.loads(result["output"])
        roles = [binding["bindings"]["role"] for binding in bindings if "bindings" in binding]

        # Check for container.admin role
        assert "roles/container.admin" in roles, (
            f"Service account missing roles/container.admin. "
            f"Current roles: {roles}. "
            f"This role is required for creating cluster-scoped RBAC resources (ClusterRoles, ClusterRoleBindings)."
        )

    @pytest.mark.integration
    def test_service_account_has_secret_manager_access(
        self, skip_if_not_gke, gcp_project_id: str, gcp_service_account_email: str
    ):
        """
        Test that service account has Secret Manager access for ESO.

        ESO needs to read secrets from GCP Secret Manager.
        """
        result = run_gcloud(
            [
                "projects",
                "get-iam-policy",
                gcp_project_id,
                "--flatten=bindings[].members",
                f"--filter=bindings.members:serviceAccount:{gcp_service_account_email}",
                "--format=json",
            ]
        )

        assert result["success"], f"Failed to get IAM policy: {result['error']}"

        bindings = json.loads(result["output"])
        roles = [binding["bindings"]["role"] for binding in bindings if "bindings" in binding]

        # Check for Secret Manager access (either accessor or admin)
        secret_manager_roles = [role for role in roles if "secretmanager" in role.lower()]

        assert len(secret_manager_roles) > 0, (
            f"Service account missing Secret Manager roles. "
            f"Current roles: {roles}. "
            f"Required: roles/secretmanager.secretAccessor or roles/secretmanager.admin"
        )

    """Test External Secrets Operator namespace and deployments exist."""

    @pytest.mark.integration
    def test_eso_namespace_exists(self, skip_if_not_gke):
        """Test that external-secrets-system namespace exists."""
        result = run_kubectl(["get", "namespace", "external-secrets-system", "-o", "json"], check=False)

        assert result["success"], (
            "Namespace external-secrets-system not found. " "Please run: ./scripts/gcp/setup-staging-infrastructure.sh"
        )

        namespace = json.loads(result["output"])
        assert namespace["metadata"]["name"] == "external-secrets-system"

    @pytest.mark.integration
    def test_eso_controller_deployment_exists(self, skip_if_not_gke):
        """Test that ESO controller deployment exists and is running."""
        result = run_kubectl(
            ["get", "deployment", "external-secrets", "-o", "json"], namespace="external-secrets-system", check=False
        )

        assert result["success"], (
            "ESO controller deployment not found. " "Please run: ./scripts/gcp/setup-staging-infrastructure.sh"
        )

        deployment = json.loads(result["output"])
        assert deployment["metadata"]["name"] == "external-secrets"

        # Check deployment is available
        status = deployment.get("status", {})
        available_replicas = status.get("availableReplicas", 0)
        desired_replicas = status.get("replicas", 0)

        assert (
            available_replicas == desired_replicas
        ), f"ESO controller not fully available: {available_replicas}/{desired_replicas} replicas"

    @pytest.mark.integration
    def test_eso_webhook_deployment_exists(self, skip_if_not_gke):
        """Test that ESO webhook deployment exists and is running."""
        result = run_kubectl(
            ["get", "deployment", "external-secrets-webhook", "-o", "json"], namespace="external-secrets-system", check=False
        )

        assert result["success"], (
            "ESO webhook deployment not found. " "Webhook is required for validating ExternalSecret resources."
        )

        deployment = json.loads(result["output"])
        assert deployment["metadata"]["name"] == "external-secrets-webhook"

        # Check deployment is available
        status = deployment.get("status", {})
        available_replicas = status.get("availableReplicas", 0)
        desired_replicas = status.get("replicas", 0)

        assert (
            available_replicas == desired_replicas
        ), f"ESO webhook not fully available: {available_replicas}/{desired_replicas} replicas"

    @pytest.mark.integration
    def test_eso_cert_controller_deployment_exists(self, skip_if_not_gke):
        """Test that ESO cert-controller deployment exists and is running."""
        result = run_kubectl(
            ["get", "deployment", "external-secrets-cert-controller", "-o", "json"],
            namespace="external-secrets-system",
            check=False,
        )

        assert result["success"], (
            "ESO cert-controller deployment not found. " "Cert-controller is required for managing webhook TLS certificates."
        )

        deployment = json.loads(result["output"])
        assert deployment["metadata"]["name"] == "external-secrets-cert-controller"

        # Check deployment is available
        status = deployment.get("status", {})
        available_replicas = status.get("availableReplicas", 0)
        desired_replicas = status.get("replicas", 0)

        assert (
            available_replicas == desired_replicas
        ), f"ESO cert-controller not fully available: {available_replicas}/{desired_replicas} replicas"


@pytest.mark.requires_kubectl
@pytest.mark.xdist_group(name="testesocrds")
class TestESOCRDs:
    """Test External Secrets Operator CRDs are installed."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.integration
    def test_externalsecret_crd_exists(self, skip_if_not_gke):
        """Test that ExternalSecret CRD exists."""
        result = run_kubectl(["get", "crd", "externalsecrets.external-secrets.io", "-o", "json"], check=False)

        assert result["success"], "ExternalSecret CRD not found"

        crd = json.loads(result["output"])
        assert crd["metadata"]["name"] == "externalsecrets.external-secrets.io"

    @pytest.mark.integration
    def test_secretstore_crd_exists(self, skip_if_not_gke):
        """Test that SecretStore CRD exists."""
        result = run_kubectl(["get", "crd", "secretstores.external-secrets.io", "-o", "json"], check=False)

        assert result["success"], "SecretStore CRD not found"

        crd = json.loads(result["output"])
        assert crd["metadata"]["name"] == "secretstores.external-secrets.io"

    @pytest.mark.integration
    def test_clustersecretstore_crd_exists(self, skip_if_not_gke):
        """Test that ClusterSecretStore CRD exists."""
        result = run_kubectl(["get", "crd", "clustersecretstores.external-secrets.io", "-o", "json"], check=False)

        assert result["success"], "ClusterSecretStore CRD not found"

        crd = json.loads(result["output"])
        assert crd["metadata"]["name"] == "clustersecretstores.external-secrets.io"


@pytest.mark.requires_kubectl
@pytest.mark.xdist_group(name="testesorbacresources")
class TestESORBACResources:
    """Test External Secrets Operator RBAC resources exist (ClusterRoles, ClusterRoleBindings)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.integration
    def test_eso_controller_clusterrole_exists(self, skip_if_not_gke):
        """
        Test that ESO controller ClusterRole exists.

        This requires container.admin to create during installation.
        """
        result = run_kubectl(["get", "clusterrole", "external-secrets-controller", "-o", "json"], check=False)

        assert result["success"], (
            "ESO controller ClusterRole not found. "
            "This indicates RBAC creation failed during installation. "
            "Ensure service account has roles/container.admin."
        )

        clusterrole = json.loads(result["output"])
        assert clusterrole["metadata"]["name"] == "external-secrets-controller"

    @pytest.mark.integration
    def test_eso_webhook_clusterrole_exists(self, skip_if_not_gke):
        """
        Test that ESO webhook ClusterRole exists (if required by ESO version).

        Note: ESO v0.20.x and later may not create a webhook ClusterRole as
        webhooks don't require explicit RBAC permissions. This test checks if
        the webhook deployment exists and only validates the ClusterRole if needed.
        """
        # Check if webhook deployment exists
        webhook_result = run_kubectl(
            ["get", "deployment", "external-secrets-webhook", "-n", "external-secrets-system", "-o", "json"],
            check=False,
        )

        if not webhook_result["success"]:
            pytest.skip("ESO webhook deployment not found - webhook may not be installed")

        # Check for webhook ClusterRole (optional in newer ESO versions)
        result = run_kubectl(["get", "clusterrole", "external-secrets-webhook", "-o", "json"], check=False)

        # If webhook exists but ClusterRole doesn't, this may be expected for newer ESO versions
        if not result["success"]:
            pytest.skip(
                "ESO webhook ClusterRole not found. This is expected for ESO v0.20.x+ "
                "where webhooks don't require explicit RBAC permissions."
            )

        clusterrole = json.loads(result["output"])
        assert clusterrole["metadata"]["name"] == "external-secrets-webhook"

    @pytest.mark.integration
    def test_eso_cert_controller_clusterrole_exists(self, skip_if_not_gke):
        """
        Test that ESO cert-controller ClusterRole exists.

        This requires container.admin to create during installation.
        """
        result = run_kubectl(["get", "clusterrole", "external-secrets-cert-controller", "-o", "json"], check=False)

        assert result["success"], (
            "ESO cert-controller ClusterRole not found. "
            "This indicates RBAC creation failed during installation. "
            "Ensure service account has roles/container.admin."
        )

        clusterrole = json.loads(result["output"])
        assert clusterrole["metadata"]["name"] == "external-secrets-cert-controller"

    @pytest.mark.integration
    def test_eso_controller_clusterrolebinding_exists(self, skip_if_not_gke):
        """Test that ESO controller ClusterRoleBinding exists."""
        result = run_kubectl(["get", "clusterrolebinding", "external-secrets-controller", "-o", "json"], check=False)

        assert result["success"], (
            "ESO controller ClusterRoleBinding not found. " "This indicates RBAC creation failed during installation."
        )

        binding = json.loads(result["output"])
        assert binding["metadata"]["name"] == "external-secrets-controller"
        assert binding["roleRef"]["name"] == "external-secrets-controller"

    @pytest.mark.integration
    def test_eso_webhook_clusterrolebinding_exists(self, skip_if_not_gke):
        """
        Test that ESO webhook ClusterRoleBinding exists (if required by ESO version).

        Note: ESO v0.20.x and later may not create a webhook ClusterRoleBinding as
        webhooks don't require explicit RBAC permissions.
        """
        # Check if webhook deployment exists
        webhook_result = run_kubectl(
            ["get", "deployment", "external-secrets-webhook", "-n", "external-secrets-system", "-o", "json"],
            check=False,
        )

        if not webhook_result["success"]:
            pytest.skip("ESO webhook deployment not found - webhook may not be installed")

        # Check for webhook ClusterRoleBinding (optional in newer ESO versions)
        result = run_kubectl(["get", "clusterrolebinding", "external-secrets-webhook", "-o", "json"], check=False)

        if not result["success"]:
            pytest.skip(
                "ESO webhook ClusterRoleBinding not found. This is expected for ESO v0.20.x+ "
                "where webhooks don't require explicit RBAC permissions."
            )

        binding = json.loads(result["output"])
        assert binding["metadata"]["name"] == "external-secrets-webhook"
        assert binding["roleRef"]["name"] == "external-secrets-webhook"

    @pytest.mark.integration
    def test_eso_cert_controller_clusterrolebinding_exists(self, skip_if_not_gke):
        """Test that ESO cert-controller ClusterRoleBinding exists."""
        result = run_kubectl(["get", "clusterrolebinding", "external-secrets-cert-controller", "-o", "json"], check=False)

        assert result["success"], (
            "ESO cert-controller ClusterRoleBinding not found. " "This indicates RBAC creation failed during installation."
        )

        binding = json.loads(result["output"])
        assert binding["metadata"]["name"] == "external-secrets-cert-controller"
        assert binding["roleRef"]["name"] == "external-secrets-cert-controller"


@pytest.mark.requires_kubectl
@pytest.mark.xdist_group(name="testclustersecretstoreconnectivity")
class TestClusterSecretStoreConnectivity:
    """Test ClusterSecretStore can connect to GCP Secret Manager."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.integration
    def test_clustersecretstore_gcp_exists(self, skip_if_not_gke):
        """Test that ClusterSecretStore for GCP exists."""
        result = run_kubectl(["get", "clustersecretstore", "gcp-secret-manager", "-o", "json"], check=False)

        if not result["success"]:
            pytest.skip(
                "ClusterSecretStore 'gcp-secret-manager' not found. "
                "This may need to be created separately from ESO installation."
            )

        store = json.loads(result["output"])
        assert store["metadata"]["name"] == "gcp-secret-manager"
        assert store["spec"]["provider"]["gcpsm"] is not None

    @pytest.mark.integration
    def test_clustersecretstore_status_valid(self, skip_if_not_gke):
        """Test that ClusterSecretStore status shows valid connection."""
        result = run_kubectl(["get", "clustersecretstore", "gcp-secret-manager", "-o", "json"], check=False)

        if not result["success"]:
            pytest.skip("ClusterSecretStore 'gcp-secret-manager' not found")

        store = json.loads(result["output"])
        status = store.get("status", {})

        # Check conditions
        conditions = status.get("conditions", [])
        ready_condition = next((c for c in conditions if c["type"] == "Ready"), None)

        if ready_condition:
            assert (
                ready_condition["status"] == "True"
            ), f"ClusterSecretStore not ready: {ready_condition.get('message', 'Unknown error')}"


@pytest.mark.requires_kubectl
@pytest.mark.xdist_group(name="testexternalsecretsync")
class TestExternalSecretSync:
    """Test ExternalSecret resources can sync secrets from GCP Secret Manager."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.integration
    def test_externalsecret_resources_exist(self, skip_if_not_gke):
        """Test that ExternalSecret resources exist in the cluster."""
        result = run_kubectl(["get", "externalsecret", "--all-namespaces", "-o", "json"], check=False)

        if not result["success"]:
            pytest.skip("No ExternalSecret resources found in cluster")

        resources = json.loads(result["output"])
        items = resources.get("items", [])

        assert len(items) > 0, "No ExternalSecret resources found"

    @pytest.mark.integration
    def test_externalsecret_sync_status(self, skip_if_not_gke):
        """
        Test that ExternalSecret resources are successfully syncing.

        Checks the status of ExternalSecret resources to ensure they are
        syncing secrets from GCP Secret Manager without errors.
        """
        result = run_kubectl(["get", "externalsecret", "--all-namespaces", "-o", "json"], check=False)

        if not result["success"]:
            pytest.skip("No ExternalSecret resources found in cluster")

        resources = json.loads(result["output"])
        items = resources.get("items", [])

        if len(items) == 0:
            pytest.skip("No ExternalSecret resources to check")

        failed_syncs = []
        for item in items:
            name = item["metadata"]["name"]
            namespace = item["metadata"]["namespace"]
            status = item.get("status", {})
            conditions = status.get("conditions", [])

            # Check Ready condition
            ready_condition = next((c for c in conditions if c["type"] == "Ready"), None)

            if ready_condition and ready_condition["status"] != "True":
                failed_syncs.append(
                    {
                        "name": name,
                        "namespace": namespace,
                        "reason": ready_condition.get("reason", "Unknown"),
                        "message": ready_condition.get("message", "Unknown error"),
                    }
                )

        assert len(failed_syncs) == 0, f"ExternalSecret sync failures: {json.dumps(failed_syncs, indent=2)}"

    @pytest.mark.integration
    def test_synced_secrets_exist(self, skip_if_not_gke):
        """
        Test that secrets synced by ExternalSecret resources exist.

        This validates end-to-end functionality: ESO reads from GCP Secret Manager
        and creates Kubernetes secrets.
        """
        result = run_kubectl(["get", "externalsecret", "--all-namespaces", "-o", "json"], check=False)

        if not result["success"]:
            pytest.skip("No ExternalSecret resources found in cluster")

        resources = json.loads(result["output"])
        items = resources.get("items", [])

        if len(items) == 0:
            pytest.skip("No ExternalSecret resources to check")

        missing_secrets = []
        for item in items:
            name = item["metadata"]["name"]
            namespace = item["metadata"]["namespace"]
            target_secret_name = item["spec"]["target"]["name"]

            # Check if target secret exists
            secret_result = run_kubectl(["get", "secret", target_secret_name, "-o", "json"], namespace=namespace, check=False)

            if not secret_result["success"]:
                missing_secrets.append({"externalsecret": name, "namespace": namespace, "target_secret": target_secret_name})

        assert len(missing_secrets) == 0, (
            f"Missing synced secrets: {json.dumps(missing_secrets, indent=2)}. "
            f"This indicates ESO is not successfully syncing secrets from GCP Secret Manager."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "integration"])
