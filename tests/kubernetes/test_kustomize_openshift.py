"""
Test suite to validate OpenShift Kustomize overlay configuration correctness.

These tests validate that Kustomize rendered manifests are properly configured
for OpenShift environments with restricted-v2 SCC compatibility.

Following TDD Red-Green-Refactor:
- RED: Tests define expected OpenShift security context requirements
- GREEN: After creating the overlay with proper patches, tests should PASS
- REFACTOR: Improve validation logic and configurations as needed

OpenShift Security Context Constraints (SCC):
- restricted-v2 SCC is the default for all namespaces
- Containers run with arbitrary UIDs assigned by OpenShift
- All processes must belong to GID 0 (root group) for file access
- Dockerfiles use g=u permissions pattern (group gets user permissions)

References:
- https://developers.redhat.com/blog/2020/10/26/adapting-docker-and-kubernetes-containers-to-run-on-red-hat-openshift-container-platform
- https://docs.openshift.com/container-platform/latest/authentication/managing-security-context-constraints.html
"""

import gc
import subprocess
from typing import Any

import pytest
import yaml

from tests.helpers.path_helpers import get_repo_root

pytestmark = pytest.mark.deployment

# Define project root relative to test file
PROJECT_ROOT = get_repo_root()
OPENSHIFT_OVERLAY = PROJECT_ROOT / "deployments" / "overlays" / "openshift"


@pytest.mark.unit
@pytest.mark.kubernetes
@pytest.mark.requires_kubectl
@pytest.mark.xdist_group(name="test_kustomize_openshift")
class TestKustomizeOpenShift:
    """Test that OpenShift Kustomize configurations are correct for restricted-v2 SCC."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def _render_kustomize_manifests(self) -> list[dict[str, Any]]:
        """Render Kustomize manifests and return parsed YAML documents."""
        if not OPENSHIFT_OVERLAY.exists():
            pytest.skip(f"OpenShift overlay not found: {OPENSHIFT_OVERLAY}")

        try:
            # Run kubectl kustomize to render manifests
            result = subprocess.run(
                ["kubectl", "kustomize", str(OPENSHIFT_OVERLAY)],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )

            # Parse all YAML documents
            manifests = list(yaml.safe_load_all(result.stdout))
            # Filter out None documents (empty YAML docs)
            return [m for m in manifests if m is not None]

        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to render Kustomize manifests: {e.stderr}")
        except subprocess.TimeoutExpired:
            pytest.fail("Kustomize rendering timed out after 30 seconds")
        except FileNotFoundError:
            pytest.skip("kubectl not found - skipping Kustomize tests")
        except Exception as e:
            pytest.fail(f"Error rendering Kustomize manifests: {e}")

    def _find_resource(self, manifests: list[dict[str, Any]], kind: str, name: str) -> dict[str, Any] | None:
        """Find a specific resource by kind and name in rendered manifests."""
        for manifest in manifests:
            if manifest.get("kind") == kind and manifest.get("metadata", {}).get("name") == name:
                return manifest
        return None

    def _find_resources_by_kind(self, manifests: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
        """Find all resources of a specific kind."""
        return [m for m in manifests if m.get("kind") == kind]

    def test_kustomize_renders_without_errors(self):
        """
        Test that Kustomize can render OpenShift manifests without errors.

        This is a basic smoke test to catch YAML syntax errors,
        invalid references, or missing patches.
        """
        manifests = self._render_kustomize_manifests()

        assert len(manifests) > 0, "No manifests rendered from Kustomize"

        # Verify we have expected core resources
        kinds = {m.get("kind") for m in manifests}

        required_kinds = {"Namespace", "Deployment", "Service", "ConfigMap"}
        missing_kinds = required_kinds - kinds

        if missing_kinds:
            pytest.fail(f"Missing required resource kinds: {missing_kinds}\nFound kinds: {sorted(kinds)}")

    def test_openshift_environment_labels(self):
        """
        Test that all resources have OpenShift-specific labels.

        The OpenShift overlay should add:
        - environment: openshift
        - platform: openshift
        - scc: restricted-v2
        """
        manifests = self._render_kustomize_manifests()

        violations = []

        for manifest in manifests:
            kind = manifest.get("kind")
            name = manifest.get("metadata", {}).get("name", "unknown")
            labels = manifest.get("metadata", {}).get("labels", {})

            # Check for OpenShift-specific labels
            if labels.get("environment") != "openshift":
                violations.append(
                    f"{kind}/{name}: missing or incorrect environment label "
                    f"(expected 'openshift', got '{labels.get('environment')}')"
                )

            if labels.get("platform") != "openshift":
                violations.append(
                    f"{kind}/{name}: missing or incorrect platform label "
                    f"(expected 'openshift', got '{labels.get('platform')}')"
                )

            if labels.get("scc") != "restricted-v2":
                violations.append(
                    f"{kind}/{name}: missing or incorrect scc label (expected 'restricted-v2', got '{labels.get('scc')}')"
                )

        if violations:
            error_msg = "\n\nOpenShift label violations:\n"
            error_msg += "The OpenShift overlay should add proper environment labels.\n\n"
            for v in violations[:10]:  # Limit output to first 10
                error_msg += f"  - {v}\n"
            if len(violations) > 10:
                error_msg += f"  ... and {len(violations) - 10} more violations\n"
            pytest.fail(error_msg)

    def test_pod_security_context_uses_gid_zero(self):
        """
        Test that all pod-level securityContext uses runAsGroup: 0 and fsGroup: 0.

        OpenShift restricted-v2 SCC requires:
        - runAsNonRoot: true
        - runAsGroup: 0 (root group for g=u permissions)
        - fsGroup: 0 (root group for volume ownership)
        - runAsUser should be OMITTED to allow OpenShift to assign arbitrary UID
        """
        manifests = self._render_kustomize_manifests()

        violations = []

        for manifest in manifests:
            kind = manifest.get("kind")
            if kind not in ("Deployment", "StatefulSet"):
                continue

            name = manifest.get("metadata", {}).get("name", "unknown")
            spec = manifest.get("spec", {})
            template = spec.get("template", {})
            pod_spec = template.get("spec", {})
            security_context = pod_spec.get("securityContext", {})

            # Check runAsNonRoot
            if security_context.get("runAsNonRoot") is not True:
                violations.append(f"{kind}/{name}: pod securityContext.runAsNonRoot should be true")

            # Check runAsGroup is 0 (root group for file access)
            run_as_group = security_context.get("runAsGroup")
            if run_as_group != 0:
                violations.append(f"{kind}/{name}: pod securityContext.runAsGroup should be 0 (got {run_as_group})")

            # Check fsGroup is 0 (root group for volume ownership)
            fs_group = security_context.get("fsGroup")
            if fs_group != 0:
                violations.append(f"{kind}/{name}: pod securityContext.fsGroup should be 0 (got {fs_group})")

        if violations:
            error_msg = "\n\nOpenShift pod security context violations:\n"
            error_msg += "The restricted-v2 SCC requires GID 0 for file access.\n\n"
            for v in violations:
                error_msg += f"  - {v}\n"
            pytest.fail(error_msg)

    def test_container_security_context_uses_gid_zero(self):
        """
        Test that all container-level securityContext uses runAsGroup: 0.

        Each container should have:
        - runAsNonRoot: true
        - runAsGroup: 0 (root group)
        - allowPrivilegeEscalation: false
        - capabilities.drop: [ALL]
        """
        manifests = self._render_kustomize_manifests()

        violations = []

        for manifest in manifests:
            kind = manifest.get("kind")
            if kind not in ("Deployment", "StatefulSet"):
                continue

            name = manifest.get("metadata", {}).get("name", "unknown")
            spec = manifest.get("spec", {})
            template = spec.get("template", {})
            pod_spec = template.get("spec", {})

            # Check all containers (including init containers)
            containers = pod_spec.get("containers", [])
            init_containers = pod_spec.get("initContainers", [])

            for container in containers + init_containers:
                container_name = container.get("name", "unknown")
                security_context = container.get("securityContext", {})

                # Check runAsNonRoot
                if security_context.get("runAsNonRoot") is not True:
                    violations.append(f"{kind}/{name}/{container_name}: container securityContext.runAsNonRoot should be true")

                # Check runAsGroup is 0
                run_as_group = security_context.get("runAsGroup")
                if run_as_group != 0:
                    violations.append(
                        f"{kind}/{name}/{container_name}: "
                        f"container securityContext.runAsGroup should be 0 (got {run_as_group})"
                    )

                # Check allowPrivilegeEscalation is false
                if security_context.get("allowPrivilegeEscalation") is not False:
                    violations.append(
                        f"{kind}/{name}/{container_name}: container securityContext.allowPrivilegeEscalation should be false"
                    )

                # Check capabilities.drop includes ALL
                capabilities = security_context.get("capabilities", {})
                drop_caps = capabilities.get("drop", [])
                if "ALL" not in drop_caps:
                    violations.append(
                        f"{kind}/{name}/{container_name}: container securityContext.capabilities.drop should include 'ALL'"
                    )

        if violations:
            error_msg = "\n\nOpenShift container security context violations:\n"
            error_msg += "All containers must use GID 0 and drop all capabilities.\n\n"
            for v in violations[:20]:  # Limit output
                error_msg += f"  - {v}\n"
            if len(violations) > 20:
                error_msg += f"  ... and {len(violations) - 20} more violations\n"
            pytest.fail(error_msg)

    def test_no_explicit_run_as_user_in_containers(self):
        """
        Test that containers do NOT have explicit runAsUser set.

        OpenShift assigns arbitrary UIDs to containers for security.
        Setting an explicit runAsUser would conflict with this mechanism.
        The pod-level runAsUser should also be omitted.
        """
        manifests = self._render_kustomize_manifests()

        violations = []

        for manifest in manifests:
            kind = manifest.get("kind")
            if kind not in ("Deployment", "StatefulSet"):
                continue

            name = manifest.get("metadata", {}).get("name", "unknown")
            spec = manifest.get("spec", {})
            template = spec.get("template", {})
            pod_spec = template.get("spec", {})

            # Note: Pod-level runAsUser should ideally be omitted too,
            # but we focus on container-level as that's where it matters most

            # Check containers
            containers = pod_spec.get("containers", [])
            init_containers = pod_spec.get("initContainers", [])

            for container in containers + init_containers:
                container_name = container.get("name", "unknown")
                security_context = container.get("securityContext", {})

                # Check that runAsUser is NOT set (OpenShift assigns arbitrary UID)
                if "runAsUser" in security_context:
                    violations.append(
                        f"{kind}/{name}/{container_name}: "
                        f"has explicit runAsUser={security_context['runAsUser']} "
                        "(should be omitted for OpenShift arbitrary UID)"
                    )

        if violations:
            error_msg = "\n\nExplicit runAsUser violations (should be omitted for OpenShift):\n"
            error_msg += "OpenShift assigns arbitrary UIDs - do not set runAsUser explicitly.\n\n"
            for v in violations:
                error_msg += f"  - {v}\n"
            pytest.fail(error_msg)

    def test_keycloak_deployment_has_jvm_settings(self):
        """
        Test that Keycloak deployment includes JAVA_OPTS_APPEND environment variable.

        This prevents OOM issues during startup by setting explicit JVM heap limits.
        Matches docker-compose.test.yml pattern for dev/prod parity.
        """
        manifests = self._render_kustomize_manifests()

        keycloak_deployment = self._find_resource(manifests, "Deployment", "keycloak")

        if not keycloak_deployment:
            pytest.skip("keycloak deployment not found in rendered manifests")

        spec = keycloak_deployment.get("spec", {})
        template = spec.get("template", {})
        pod_spec = template.get("spec", {})

        containers = pod_spec.get("containers", [])
        keycloak_container = None
        for container in containers:
            if container.get("name") == "keycloak":
                keycloak_container = container
                break

        if not keycloak_container:
            pytest.fail("Keycloak container not found in deployment")

        env_vars = keycloak_container.get("env", [])
        java_opts_env = None
        for env in env_vars:
            if env.get("name") == "JAVA_OPTS_APPEND":
                java_opts_env = env
                break

        if not java_opts_env:
            pytest.fail(
                "Keycloak deployment missing JAVA_OPTS_APPEND environment variable.\n"
                "This is required to prevent OOM during startup.\n"
                "Expected: JAVA_OPTS_APPEND with -Xms, -Xmx, and -XX:MaxMetaspaceSize"
            )

        value = java_opts_env.get("value", "")

        # Verify key JVM settings are present
        required_settings = ["-Xms", "-Xmx", "-XX:MaxMetaspaceSize"]
        missing_settings = [s for s in required_settings if s not in value]

        if missing_settings:
            pytest.fail(f"Keycloak JAVA_OPTS_APPEND missing required JVM settings: {missing_settings}\nCurrent value: {value}")

    def test_qdrant_deployment_has_recovery_mode(self):
        """
        Test that Qdrant deployment includes QDRANT_ALLOW_RECOVERY_MODE=true.

        This matches docker-compose.test.yml configuration for dev/prod parity.
        """
        manifests = self._render_kustomize_manifests()

        qdrant_deployment = self._find_resource(manifests, "Deployment", "qdrant")

        if not qdrant_deployment:
            pytest.skip("qdrant deployment not found in rendered manifests")

        spec = qdrant_deployment.get("spec", {})
        template = spec.get("template", {})
        pod_spec = template.get("spec", {})

        containers = pod_spec.get("containers", [])
        qdrant_container = None
        for container in containers:
            if container.get("name") == "qdrant":
                qdrant_container = container
                break

        if not qdrant_container:
            pytest.fail("Qdrant container not found in deployment")

        env_vars = qdrant_container.get("env", [])
        recovery_mode_env = None
        for env in env_vars:
            if env.get("name") == "QDRANT_ALLOW_RECOVERY_MODE":
                recovery_mode_env = env
                break

        if not recovery_mode_env:
            pytest.fail(
                "Qdrant deployment missing QDRANT_ALLOW_RECOVERY_MODE environment variable.\n"
                "Expected: QDRANT_ALLOW_RECOVERY_MODE=true"
            )

        value = recovery_mode_env.get("value", "")
        if value.lower() != "true":
            pytest.fail(f"Qdrant QDRANT_ALLOW_RECOVERY_MODE should be 'true', got '{value}'")

    def test_all_deployments_have_seccomp_profile(self):
        """
        Test that all Deployments and StatefulSets have seccompProfile: RuntimeDefault.

        This is required for OpenShift security compliance.
        """
        manifests = self._render_kustomize_manifests()

        violations = []

        for manifest in manifests:
            kind = manifest.get("kind")
            if kind not in ("Deployment", "StatefulSet"):
                continue

            name = manifest.get("metadata", {}).get("name", "unknown")
            spec = manifest.get("spec", {})
            template = spec.get("template", {})
            pod_spec = template.get("spec", {})
            security_context = pod_spec.get("securityContext", {})

            seccomp_profile = security_context.get("seccompProfile", {})
            profile_type = seccomp_profile.get("type")

            if profile_type != "RuntimeDefault":
                violations.append(f"{kind}/{name}: seccompProfile.type should be 'RuntimeDefault' (got '{profile_type}')")

        if violations:
            error_msg = "\n\nSeccomp profile violations:\n"
            error_msg += "All workloads should use seccompProfile.type: RuntimeDefault\n\n"
            for v in violations:
                error_msg += f"  - {v}\n"
            pytest.fail(error_msg)

    def test_overlay_includes_all_expected_patches(self):
        """
        Test that the OpenShift overlay kustomization.yaml includes all expected patches.

        This ensures no services are missed when creating the overlay.
        """
        kustomization_path = OPENSHIFT_OVERLAY / "kustomization.yaml"

        if not kustomization_path.exists():
            pytest.fail(f"OpenShift kustomization.yaml not found: {kustomization_path}")

        with open(kustomization_path) as f:
            kustomization = yaml.safe_load(f)

        patches = kustomization.get("patches", [])
        patch_files = [p.get("path", "") for p in patches]

        # Expected patch files for all services
        expected_patches = {
            "mcp-server-patch.yaml",
            "keycloak-patch.yaml",
            "openfga-patch.yaml",
            "qdrant-patch.yaml",
            "postgres-patch.yaml",
            "redis-patch.yaml",
            "otel-collector-patch.yaml",
        }

        missing_patches = expected_patches - set(patch_files)

        if missing_patches:
            pytest.fail(
                f"OpenShift kustomization.yaml missing expected patches:\n"
                f"  Missing: {missing_patches}\n"
                f"  Found: {set(patch_files)}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
