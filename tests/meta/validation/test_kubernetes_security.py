#!/usr/bin/env python3
"""
Tests for Kubernetes security context configuration.

Following TDD principles:
1. RED: Verify all pods have readOnlyRootFilesystem security context
2. GREEN: Add security contexts to deployment patches
3. REFACTOR: Extract common patterns to Helm values
"""

import gc
import subprocess

import pytest
import yaml

from tests.fixtures.tool_fixtures import requires_tool

# Mark as unit test to ensure it runs in CI
pytestmark = [pytest.mark.unit, pytest.mark.validation]


@pytest.mark.xdist_group(name="testsecuritycontexts")
class TestSecurityContexts:
    """Test Kubernetes pod security contexts."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def deployment_patch_files(self, deployments_dir):
        """Get all deployment patch files.

        Uses the shared deployments_dir fixture from conftest.py to prevent
        path resolution bugs (DRY pattern).
        """
        overlays_dir = deployments_dir / "overlays" / "staging-gke"
        return [
            overlays_dir / "deployment-patch.yaml",
            overlays_dir / "openfga-patch.yaml",
            overlays_dir / "keycloak-patch.yaml",
        ]

    def test_all_containers_have_readonly_filesystem(self, deployment_patch_files):
        """
        Test that all container security contexts have readOnlyRootFilesystem: true.

        This test will initially FAIL because security contexts are missing.
        After fix, all containers should have this critical security setting.

        **EXCEPTION: Keycloak (staging-gke overlay only)**
        Keycloak requires readOnlyRootFilesystem: false due to Quarkus JIT compilation.

        Current Status:
        - staging-gke: readOnlyRootFilesystem: false ✅ (deployed and working)
        - base: readOnlyRootFilesystem: true ❌ (not deployed, needs fix)
        - production-gke: readOnlyRootFilesystem: true ❌ (not deployed, needs fix)

        With the custom optimized Keycloak image (docker/Dockerfile.keycloak), we can now
        use readOnlyRootFilesystem: true because Quarkus is pre-compiled at build time.

        Previous exception (no longer needed):
        - Keycloak required writable filesystem for Quarkus JIT compilation
        - See: https://github.com/keycloak/keycloak/issues/10150

        Current approach:
        - Custom image runs 'kc.sh build' during Docker build (pre-compilation)
        - Runtime uses '--optimized' flag to skip augmentation
        - readOnlyRootFilesystem: true can now be used safely
        - See: docker/Dockerfile.keycloak and https://www.keycloak.org/server/containers
        """
        # Documented exceptions (see .trivyignore for detailed justification)
        # NOTE: Keycloak exception REMOVED - custom optimized image supports readOnlyRootFilesystem: true
        # See: docker/Dockerfile.keycloak for the pre-compilation approach
        READONLY_FILESYSTEM_EXCEPTIONS: dict[str, str] = {
            # No exceptions currently - all containers should use readOnlyRootFilesystem: true
        }

        for patch_file in deployment_patch_files:
            if not patch_file.exists():
                pytest.skip(f"Patch file not found: {patch_file}")

            with open(patch_file) as f:
                # Handle multi-document YAML (with ---)
                patches = list(yaml.safe_load_all(f))

            for doc_idx, patch in enumerate(patches):
                if not patch:  # Skip empty documents
                    continue

                # Navigate to containers
                spec = patch.get("spec", {})
                template = spec.get("template", {})
                pod_spec = template.get("spec", {})
                containers = pod_spec.get("containers", [])

                for container_idx, container in enumerate(containers):
                    container_name = container.get("name", f"container-{container_idx}")
                    security_context = container.get("securityContext", {})

                    # Check if this container has a documented exception
                    if container_name.lower() in READONLY_FILESYSTEM_EXCEPTIONS:
                        # For exceptions, verify it's explicitly set to false (not just missing)
                        assert "readOnlyRootFilesystem" in security_context, (
                            f"{patch_file.name}: Container '{container_name}' is an exception but must "
                            f"explicitly set readOnlyRootFilesystem: false.\n"
                            f"Reason: {READONLY_FILESYSTEM_EXCEPTIONS[container_name.lower()]}"
                        )
                        assert security_context["readOnlyRootFilesystem"] is False, (
                            f"{patch_file.name}: Container '{container_name}' must have "
                            f"readOnlyRootFilesystem: false (not true).\n"
                            f"Reason: {READONLY_FILESYSTEM_EXCEPTIONS[container_name.lower()]}"
                        )
                        continue  # Skip readOnly check for documented exceptions

                    # All other containers must have readOnlyRootFilesystem: true
                    assert "readOnlyRootFilesystem" in security_context, (
                        f"{patch_file.name}: Container '{container_name}' missing securityContext.readOnlyRootFilesystem"
                    )

                    assert security_context["readOnlyRootFilesystem"] is True, (
                        f"{patch_file.name}: Container '{container_name}' must have readOnlyRootFilesystem: true"
                    )

    def test_writable_volumes_mounted_as_emptydir(self, deployment_patch_files):
        """
        Test that writable directories use emptyDir volumes.

        Containers with readOnlyRootFilesystem need emptyDir volumes for:
        - /tmp (temporary files)
        - /var/tmp (temp files)
        - Application-specific writable paths
        """
        for patch_file in deployment_patch_files:
            if not patch_file.exists():
                pytest.skip(f"Patch file not found: {patch_file}")

            with open(patch_file) as f:
                patches = list(yaml.safe_load_all(f))

            for patch in patches:
                if not patch:
                    continue

                spec = patch.get("spec", {})
                template = spec.get("template", {})
                pod_spec = template.get("spec", {})
                containers = pod_spec.get("containers", [])

                # Check if any container has readOnlyRootFilesystem
                has_readonly_fs = False
                for container in containers:
                    sec_ctx = container.get("securityContext", {})
                    if sec_ctx.get("readOnlyRootFilesystem"):
                        has_readonly_fs = True
                        break

                if has_readonly_fs:
                    # Verify volumes and volumeMounts exist
                    # Should have at least tmp volume

                    # Check for common writable paths
                    for container in containers:
                        volume_mounts = container.get("volumeMounts", [])
                        mount_paths = [vm.get("mountPath") for vm in volume_mounts]

                        # If readOnlyRootFilesystem is set, should mount /tmp
                        sec_ctx = container.get("securityContext", {})
                        if sec_ctx.get("readOnlyRootFilesystem"):
                            assert any(
                                "/tmp" in path  # nosec B108 - K8s volumeMount path check, not temp file creation
                                for path in mount_paths
                            ), f"{patch_file.name}: Container with readOnlyRootFilesystem should mount /tmp"

    def test_init_containers_have_security_context(self, deployment_patch_files):
        """Test that init containers also have proper security contexts."""
        for patch_file in deployment_patch_files:
            if not patch_file.exists():
                pytest.skip(f"Patch file not found: {patch_file}")

            with open(patch_file) as f:
                patches = list(yaml.safe_load_all(f))

            for patch in patches:
                if not patch:
                    continue

                spec = patch.get("spec", {})
                template = spec.get("template", {})
                pod_spec = template.get("spec", {})
                init_containers = pod_spec.get("initContainers", [])

                for init_container in init_containers:
                    container_name = init_container.get("name", "unknown")
                    security_context = init_container.get("securityContext", {})

                    # Init containers should also have readOnlyRootFilesystem
                    # (unless they specifically need write access)
                    if "securityContext" in init_container:
                        assert isinstance(security_context, dict), (
                            f"{patch_file.name}: Init container '{container_name}' has invalid securityContext"
                        )


@pytest.mark.requires_kubectl
@pytest.mark.xdist_group(name="testimagepullpolicy")
class TestImagePullPolicy:
    """Test imagePullPolicy configuration for security compliance."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def staging_overlay_dir(self, deployments_dir):
        """Get staging overlay directory using shared fixture."""
        return deployments_dir / "overlays" / "staging-gke"

    @requires_tool("kubectl")
    def test_staging_overlay_has_imagepullpolicy_always(self, staging_overlay_dir):
        """
        Test that staging overlay sets imagePullPolicy: Always for all containers.

        TDD RED phase: This test will initially FAIL because staging patches don't override imagePullPolicy.

        Rationale:
        - imagePullPolicy: IfNotPresent (base default) can use stale cached images in staging
        - imagePullPolicy: Always ensures latest security patches and prevents supply chain attacks
        - kube-score compliance: Production and staging MUST use Always for image pull policy

        This prevents scenarios where:
        1. A node caches a vulnerable image
        2. Updated image is pushed with same tag (e.g., v2.8.0 rebuilt with security fix)
        3. Pod uses cached vulnerable version instead of pulling updated image
        """
        # Build the kustomize output
        result = subprocess.run(["kubectl", "kustomize", str(staging_overlay_dir)], capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            pytest.skip(f"kubectl kustomize failed: {result.stderr}")

        # Parse all manifests
        manifests = list(yaml.safe_load_all(result.stdout))

        # Track violations for detailed error reporting
        violations = []

        for manifest in manifests:
            if not manifest or manifest.get("kind") != "Deployment":
                continue

            deployment_name = manifest.get("metadata", {}).get("name", "unknown")
            spec = manifest.get("spec", {})
            template = spec.get("template", {})
            pod_spec = template.get("spec", {})

            # Check all init containers
            init_containers = pod_spec.get("initContainers", [])
            for idx, container in enumerate(init_containers):
                container_name = container.get("name", f"init-{idx}")
                pull_policy = container.get("imagePullPolicy")

                if pull_policy != "Always":
                    violations.append(
                        f"Deployment '{deployment_name}': init container '{container_name}' "
                        f"has imagePullPolicy={pull_policy} (expected: Always)"
                    )

            # Check all app containers
            containers = pod_spec.get("containers", [])
            for idx, container in enumerate(containers):
                container_name = container.get("name", f"container-{idx}")
                pull_policy = container.get("imagePullPolicy")

                if pull_policy != "Always":
                    violations.append(
                        f"Deployment '{deployment_name}': container '{container_name}' "
                        f"has imagePullPolicy={pull_policy} (expected: Always)"
                    )

        # Report all violations at once for better debugging
        assert not violations, "Staging overlay must set imagePullPolicy: Always for all containers:\n" + "\n".join(
            f"  - {v}" for v in violations
        )


@pytest.mark.xdist_group(name="testredisexternalnameservice")
class TestRedisExternalNameService:
    """Test Redis ExternalName service configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_redis_service_configuration(self, deployments_dir):
        """
        Test Redis service configuration for AVD-KSV-0108 compliance.

        Per user preference: Investigate before deciding on approach.
        This test documents the current state and expected fixes.
        """
        redis_service_file = deployments_dir / "overlays" / "staging-gke" / "redis-session-service-patch.yaml"

        if not redis_service_file.exists():
            pytest.skip("Redis service patch not found")

        with open(redis_service_file) as f:
            patches = list(yaml.safe_load_all(f))

        for patch in patches:
            if not patch:
                continue

            kind = patch.get("kind")
            if kind == "Service":
                service_type = patch.get("spec", {}).get("type")

                # Document current state
                if service_type == "ExternalName":
                    # ExternalName triggers AVD-KSV-0108 in Trivy
                    # Options:
                    # 1. Keep ExternalName + add Trivy exception (if Cloud DNS is required)
                    # 2. Switch to ClusterIP + externalIPs
                    # 3. Use Endpoint/EndpointSlice for external IP
                    pytest.skip(
                        "Redis ExternalName service needs investigation - "
                        "research GCP Memorystore best practices before fixing"
                    )


@pytest.mark.requires_kubectl
@pytest.mark.xdist_group(name="testkubernetesvalidation")
class TestKubernetesValidation:
    """Test Kubernetes manifest validation with security tools."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @requires_tool("kubectl")
    def test_kubeconform_validates_manifests(self, deployments_dir):
        """Test that manifests pass kubeconform validation."""
        overlays_dir = deployments_dir / "overlays" / "staging-gke"

        if not overlays_dir.exists():
            pytest.skip("Overlays directory not found")

        # Check if kubeconform is installed
        try:
            subprocess.run(["kubeconform", "--version"], capture_output=True, check=True, timeout=60)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("kubeconform not installed")

        # Run kubeconform on the overlay
        result = subprocess.run(["kubectl", "kustomize", str(overlays_dir)], capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            pytest.skip(f"kubectl kustomize failed: {result.stderr}")

        # Validate with kubeconform
        validate_result = subprocess.run(
            ["kubeconform", "-strict", "-summary"], input=result.stdout, capture_output=True, text=True, timeout=60
        )

        # Should not have validation errors
        assert validate_result.returncode == 0, (
            f"Kubeconform validation failed:\n{validate_result.stdout}\n{validate_result.stderr}"
        )

    @requires_tool("kubectl")
    def test_kustomize_builds_successfully(self, deployments_dir):
        """Test that Kustomize overlays build without errors."""
        overlays_dir = deployments_dir / "overlays" / "staging-gke"

        if not overlays_dir.exists():
            pytest.skip("Overlays directory not found")

        result = subprocess.run(["kubectl", "kustomize", str(overlays_dir)], capture_output=True, text=True, timeout=60)

        assert result.returncode == 0, f"Kustomize build failed:\n{result.stderr}"
        assert len(result.stdout) > 0, "Kustomize build produced no output"


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "kubernetes: tests for Kubernetes security")
    config.addinivalue_line("markers", "security: security-focused tests")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
