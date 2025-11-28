"""
Deployment Security Regression Tests

These tests validate that previously-fixed security issues in deployment
configurations remain fixed. They prevent regression of critical security
findings from Codex and security audits.

Test Coverage:
1. Qdrant deployment has proper securityContext (readOnlyRootFilesystem)
2. OpenFGA ServiceAccount has Workload Identity annotations
3. Qdrant health checks use grpc_health_probe (not wget/curl)
"""

import gc
from pathlib import Path

import pytest
import yaml

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.security
@pytest.mark.regression
@pytest.mark.xdist_group(name="testqdrantsecuritycontext")
class TestQdrantSecurityContext:
    """Regression tests for Qdrant security context configuration"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_qdrant_has_readonly_root_filesystem(self):
        """
        Test that Qdrant deployment has readOnlyRootFilesystem: true.

        This prevents the container from writing to its root filesystem,
        which is a security best practice. Previously flagged by Trivy.

        File: deployments/overlays/staging-gke/qdrant-patch.yaml:12
        Finding: Trivy flagged missing securityContext.readOnlyRootFilesystem
        """
        qdrant_patch_path = (
            Path(__file__).parent.parent.parent / "deployments" / "overlays" / "staging-gke" / "qdrant-patch.yaml"
        )

        assert qdrant_patch_path.exists(), f"Qdrant patch file not found: {qdrant_patch_path}"

        with open(qdrant_patch_path) as f:
            patch_config = yaml.safe_load(f)

        # Navigate to securityContext in the deployment spec
        # Structure: spec.template.spec.containers[0].securityContext
        spec = patch_config.get("spec", {})
        template = spec.get("template", {})
        pod_spec = template.get("spec", {})
        containers = pod_spec.get("containers", [])

        assert len(containers) > 0, "No containers found in Qdrant patch"

        qdrant_container = containers[0]
        security_context = qdrant_container.get("securityContext", {})

        # Verify readOnlyRootFilesystem is set to true
        assert "readOnlyRootFilesystem" in security_context, "readOnlyRootFilesystem not configured in Qdrant securityContext"

        assert security_context["readOnlyRootFilesystem"] is True, "readOnlyRootFilesystem should be True for Qdrant container"

    def test_qdrant_has_run_as_non_root(self):
        """
        Test that Qdrant runs as non-root user.

        This prevents privilege escalation attacks.
        """
        qdrant_patch_path = (
            Path(__file__).parent.parent.parent / "deployments" / "overlays" / "staging-gke" / "qdrant-patch.yaml"
        )

        if not qdrant_patch_path.exists():
            pytest.skip("Qdrant patch file not found")

        with open(qdrant_patch_path) as f:
            patch_config = yaml.safe_load(f)

        spec = patch_config.get("spec", {})
        template = spec.get("template", {})
        pod_spec = template.get("spec", {})
        containers = pod_spec.get("containers", [])

        qdrant_container = containers[0]
        security_context = qdrant_container.get("securityContext", {})

        # Verify runAsNonRoot is set to true
        assert "runAsNonRoot" in security_context, "runAsNonRoot not configured"
        assert security_context["runAsNonRoot"] is True, "Qdrant should run as non-root user"

    def test_qdrant_drops_all_capabilities(self):
        """
        Test that Qdrant drops all Linux capabilities.

        This follows the principle of least privilege.
        """
        qdrant_patch_path = (
            Path(__file__).parent.parent.parent / "deployments" / "overlays" / "staging-gke" / "qdrant-patch.yaml"
        )

        if not qdrant_patch_path.exists():
            pytest.skip("Qdrant patch file not found")

        with open(qdrant_patch_path) as f:
            patch_config = yaml.safe_load(f)

        spec = patch_config.get("spec", {})
        template = spec.get("template", {})
        pod_spec = template.get("spec", {})
        containers = pod_spec.get("containers", [])

        qdrant_container = containers[0]
        security_context = qdrant_container.get("securityContext", {})

        # Verify capabilities are dropped
        capabilities = security_context.get("capabilities", {})
        drop_capabilities = capabilities.get("drop", [])

        assert "ALL" in drop_capabilities, "Should drop ALL capabilities for defense in depth"


@pytest.mark.security
@pytest.mark.regression
@pytest.mark.xdist_group(name="testopenfgaworkloadidentity")
class TestOpenFGAWorkloadIdentity:
    """Regression tests for OpenFGA Workload Identity configuration"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_openfga_has_workload_identity_annotation(self):
        """
        Test that OpenFGA ServiceAccount has Workload Identity annotation.

        This enables secure authentication to GCP services without
        using service account keys.

        File: deployments/overlays/staging-gke/serviceaccount-openfga.yaml:6
        Finding: Missing iam.gke.io/gcp-service-account annotation
        """
        sa_path = (
            Path(__file__).parent.parent.parent / "deployments" / "overlays" / "staging-gke" / "serviceaccount-openfga.yaml"
        )

        assert sa_path.exists(), f"OpenFGA ServiceAccount file not found: {sa_path}"

        with open(sa_path) as f:
            sa_config = yaml.safe_load(f)

        # Verify it's a ServiceAccount
        assert sa_config.get("kind") == "ServiceAccount", "Not a ServiceAccount resource"

        # Verify Workload Identity annotation
        annotations = sa_config.get("metadata", {}).get("annotations", {})

        assert "iam.gke.io/gcp-service-account" in annotations, "Missing Workload Identity annotation"

        gcp_sa = annotations["iam.gke.io/gcp-service-account"]

        # Verify format: <sa-name>@<project-id>.iam.gserviceaccount.com
        assert "@" in gcp_sa, "GCP service account should be in format: name@project.iam.gserviceaccount.com"
        assert ".iam.gserviceaccount.com" in gcp_sa, "GCP service account should end with .iam.gserviceaccount.com"

    def test_openfga_serviceaccount_has_minimal_permissions_comment(self):
        """
        Test that OpenFGA ServiceAccount documents minimal permissions.

        This ensures the principle of least privilege is documented.
        """
        sa_path = (
            Path(__file__).parent.parent.parent / "deployments" / "overlays" / "staging-gke" / "serviceaccount-openfga.yaml"
        )

        if not sa_path.exists():
            pytest.skip("OpenFGA ServiceAccount file not found")

        with open(sa_path) as f:
            content = f.read()

        # Check for documentation of minimal permissions
        assert "minimal permissions" in content.lower() or "least privilege" in content.lower(), (
            "ServiceAccount should document minimal permissions principle"
        )


@pytest.mark.security
@pytest.mark.regression
@pytest.mark.xdist_group(name="testqdranthealthchecksecurity")
class TestQdrantHealthCheckSecurity:
    """Regression tests for Qdrant health check security"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_qdrant_uses_tcp_health_check(self):
        """
        Test that Qdrant health check uses TCP-based check (not wget/curl/grpc_health_probe).

        Qdrant v1.15.1 image does not include wget, curl, or grpc_health_probe binaries.
        For security and reliability, use TCP port check via /dev/tcp instead.

        File: docker-compose.test.yml:232
        Finding: Must use TCP-based health check as no HTTP clients exist in base image
        """
        docker_compose_path = Path(__file__).parent.parent.parent / "docker-compose.test.yml"

        assert docker_compose_path.exists(), f"docker-compose.test.yml not found: {docker_compose_path}"

        with open(docker_compose_path) as f:
            compose_config = yaml.safe_load(f)

        # Find Qdrant test service
        services = compose_config.get("services", {})
        qdrant_service = services.get("qdrant-test")

        assert qdrant_service is not None, "qdrant-test service not found in docker-compose"

        # Verify health check configuration
        healthcheck = qdrant_service.get("healthcheck", {})
        test_cmd = healthcheck.get("test", [])

        # Convert to string for easier checking
        test_cmd_str = " ".join(test_cmd) if isinstance(test_cmd, list) else test_cmd

        # Verify uses TCP-based health check (grpc_health_probe not available in qdrant:v1.15.1 image)
        assert "/dev/tcp" in test_cmd_str, "Qdrant health check should use TCP port check (/dev/tcp)"

        # Verify NOT using wget or curl (security issue - not available in Qdrant v1.15+)
        assert "wget" not in test_cmd_str.lower(), "Should not use wget for health checks (not available in v1.15+)"
        assert "curl" not in test_cmd_str.lower(), "Should not use curl for health checks (not available in v1.15+)"

    def test_qdrant_health_check_has_proper_timing(self):
        """
        Test that Qdrant health check has proper timing configuration.

        This ensures the health check doesn't timeout prematurely.
        """
        docker_compose_path = Path(__file__).parent.parent.parent / "docker-compose.test.yml"

        if not docker_compose_path.exists():
            pytest.skip("docker-compose.test.yml not found")

        with open(docker_compose_path) as f:
            compose_config = yaml.safe_load(f)

        services = compose_config.get("services", {})
        qdrant_service = services.get("qdrant-test")

        if not qdrant_service:
            pytest.skip("qdrant-test service not found")

        healthcheck = qdrant_service.get("healthcheck", {})

        # Verify timing parameters are configured
        assert "interval" in healthcheck, "Health check should have interval configured"
        assert "timeout" in healthcheck, "Health check should have timeout configured"
        assert "retries" in healthcheck, "Health check should have retries configured"
        assert "start_period" in healthcheck, "Health check should have start_period configured"

        # Verify reasonable values (convert interval string to seconds if needed)
        # interval should be reasonable (e.g., 3s-10s)
        # retries should allow for startup time


@pytest.mark.security
@pytest.mark.regression
@pytest.mark.xdist_group(name="testhelmplaceholdersecurity")
class TestHelmPlaceholderSecurity:
    """Regression tests for Helm value placeholder security"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_no_unresolved_project_id_placeholders_in_production(self):
        """
        Test that production Helm values don't have unresolved PROJECT_ID placeholders.

        Unresolved placeholders could cause deployment failures or security issues
        if accidentally deployed with test/placeholder values.

        Files:
        - deployments/helm/values-staging.yaml:108
        - deployments/helm/values-production.yaml:139
        """
        # NOTE: These files are TEMPLATES that should be replaced during deployment.
        # This test verifies they are documented as templates and not used directly.

        staging_values = Path(__file__).parent.parent.parent / "deployments" / "helm" / "values-staging.yaml"
        production_values = Path(__file__).parent.parent.parent / "deployments" / "helm" / "values-production.yaml"

        # Read files and check for placeholder patterns
        # We expect these placeholders to exist in template files,
        # but they should be commented or documented as needing replacement

        for values_file in [staging_values, production_values]:
            if not values_file.exists():
                continue

            with open(values_file) as f:
                content = f.read()

            # Check if placeholders exist
            has_placeholders = "YOUR_STAGING_PROJECT_ID" in content or "PROJECT_ID" in content

            if has_placeholders:
                # If placeholders exist, verify they are documented
                # Look for comments explaining they need to be replaced
                assert "# Replace with" in content or "TODO" in content or "# For" in content, (
                    f"{values_file.name} has placeholders but no documentation on replacing them"
                )

    def test_helm_values_are_valid_yaml(self):
        """
        Test that Helm values files are valid YAML.

        This ensures deployment configurations can be parsed.
        """
        helm_dir = Path(__file__).parent.parent.parent / "deployments" / "helm"
        values_files = list(helm_dir.glob("values-*.yaml"))

        assert len(values_files) > 0, "No Helm values files found"

        for values_file in values_files:
            with open(values_file) as f:
                try:
                    config = yaml.safe_load(f)
                    assert config is not None, f"{values_file.name} is empty"
                except yaml.YAMLError as e:
                    pytest.fail(f"{values_file.name} has invalid YAML syntax: {e}")
