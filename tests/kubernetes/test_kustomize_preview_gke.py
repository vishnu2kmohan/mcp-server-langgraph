"""
Test suite to validate preview-gke Kustomize configuration correctness.

These tests validate that Kustomize rendered manifests are properly configured
for the preview-gke environment, catching issues before deployment.

Following TDD Red-Green-Refactor:
- RED: These tests should FAIL initially (revealing existing config issues)
- GREEN: After fixing deployment configurations, tests should PASS
- REFACTOR: Improve validation logic and configurations as needed

Issue Context:
- Pod failure: preview-mcp-server-langgraph (CreateContainerConfigError)
  Root cause: Secret name mismatch - deployment refs 'mcp-server-langgraph-secrets'
  but Kustomize creates 'preview-mcp-server-langgraph-secrets' due to namePrefix

- Pod failure: preview-keycloak (CrashLoopBackOff)
  Root cause: EmptyDir volume mounted at /opt/keycloak/lib overwrites JAR files
  causing ClassNotFoundException: io.quarkus.bootstrap.runner.QuarkusEntryPoint
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
PREVIEW_GKE_OVERLAY = PROJECT_ROOT / "deployments" / "overlays" / "preview-gke"


@pytest.mark.unit
@pytest.mark.kubernetes
@pytest.mark.requires_kubectl
@pytest.mark.xdist_group(name="test_kustomize_preview_gke")
class TestKustomizePreviewGKE:
    """Test that preview-gke Kustomize configurations are correct."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def _render_kustomize_manifests(self) -> list[dict[str, Any]]:
        """Render Kustomize manifests and return parsed YAML documents."""
        if not PREVIEW_GKE_OVERLAY.exists():
            pytest.skip(f"Preview GKE overlay not found: {PREVIEW_GKE_OVERLAY}")

        try:
            # Run kubectl kustomize to render manifests
            result = subprocess.run(
                ["kubectl", "kustomize", str(PREVIEW_GKE_OVERLAY)],
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
        except Exception as e:
            pytest.fail(f"Error rendering Kustomize manifests: {e}")

    def _find_resource(self, manifests: list[dict[str, Any]], kind: str, name: str) -> dict[str, Any] | None:
        """Find a specific resource by kind and name in rendered manifests."""
        for manifest in manifests:
            if manifest.get("kind") == kind and manifest.get("metadata", {}).get("name") == name:
                return manifest
        return None

    def _extract_secret_refs_from_env(self, container: dict[str, Any]) -> list[tuple[str, str]]:
        """Extract secret references from container environment variables.

        Returns list of (env_var_name, secret_name) tuples.
        """
        secret_refs = []
        env_vars = container.get("env", [])

        for env in env_vars:
            if "valueFrom" in env:
                secret_key_ref = env["valueFrom"].get("secretKeyRef")
                if secret_key_ref:
                    secret_refs.append((env["name"], secret_key_ref["name"]))

        return secret_refs

    def test_secret_references_use_preview_prefix(self):
        """
        Test that all secret references in preview-gke use 'preview-' prefix.

        RED: Should FAIL - mcp-server-langgraph deployment refs unprefixed secret name
        GREEN: Should PASS - after adding deployment patch to fix secret references

        This test prevents CreateContainerConfigError caused by secret name mismatches.
        """
        manifests = self._render_kustomize_manifests()

        violations = []

        for manifest in manifests:
            kind = manifest.get("kind")
            if kind != "Deployment":
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
                secret_refs = self._extract_secret_refs_from_env(container)

                for env_name, secret_name in secret_refs:
                    # All secrets in preview-gke should have 'preview-' prefix
                    if not secret_name.startswith("preview-"):
                        violations.append(
                            {
                                "deployment": name,
                                "container": container_name,
                                "env_var": env_name,
                                "secret_name": secret_name,
                                "expected_prefix": "preview-",
                                "issue": f"Secret reference '{secret_name}' missing 'preview-' prefix",
                            }
                        )

        if violations:
            error_msg = "\n\nSecret reference violations in preview-gke:\n"
            error_msg += "\nKustomize namePrefix='preview-' doesn't auto-update secretKeyRef!\n"
            error_msg += "All secret references must explicitly use the prefixed name.\n"
            for v in violations:
                error_msg += f"\n  Deployment: {v['deployment']}"
                error_msg += f"\n    Container: {v['container']}"
                error_msg += f"\n    Env Var: {v['env_var']}"
                error_msg += f"\n    Current: {v['secret_name']}"
                error_msg += f"\n    Expected: preview-{v['secret_name']}"
                error_msg += f"\n    Issue: {v['issue']}\n"

            pytest.fail(error_msg)

    def test_keycloak_volume_mounts_dont_override_critical_paths(self):
        """
        Test that Keycloak deployment doesn't mount emptyDir at /opt/keycloak/lib.

        RED: Should FAIL - Keycloak has emptyDir mount at /opt/keycloak/lib
        GREEN: Should PASS - after removing the problematic volume mount

        This test prevents CrashLoopBackOff caused by overwriting Keycloak's JAR files.
        The /opt/keycloak/lib directory contains critical Quarkus runtime JARs that must
        not be replaced with an empty directory.
        """
        manifests = self._render_kustomize_manifests()

        keycloak_deployment = self._find_resource(manifests, "Deployment", "preview-keycloak")

        if not keycloak_deployment:
            pytest.skip("preview-keycloak deployment not found in rendered manifests")

        spec = keycloak_deployment.get("spec", {})
        template = spec.get("template", {})
        pod_spec = template.get("spec", {})

        # Define critical paths that should NEVER have emptyDir mounts
        CRITICAL_PATHS = {
            "/opt/keycloak/lib": "Contains Quarkus runtime JARs",
            "/opt/keycloak/bin": "Contains Keycloak executables",
            "/usr": "System binaries and libraries",
            "/lib": "System libraries",
            "/lib64": "System libraries (64-bit)",
        }

        violations = []

        # Get volumes for reference
        volumes = {v["name"]: v for v in pod_spec.get("volumes", [])}

        # Check all containers
        containers = pod_spec.get("containers", [])
        for container in containers:
            container_name = container.get("name", "unknown")
            volume_mounts = container.get("volumeMounts", [])

            for mount in volume_mounts:
                mount_path = mount.get("mountPath", "")
                volume_name = mount.get("name", "")

                # Check if this mount overrides a critical path
                for critical_path, reason in CRITICAL_PATHS.items():
                    if mount_path == critical_path:
                        volume_config = volumes.get(volume_name, {})

                        # EmptyDir mounts are particularly dangerous
                        if "emptyDir" in volume_config:
                            violations.append(
                                {
                                    "container": container_name,
                                    "mount_path": mount_path,
                                    "volume_name": volume_name,
                                    "volume_type": "emptyDir",
                                    "reason": reason,
                                    "issue": f"EmptyDir mount at {mount_path} overwrites {reason.lower()}",
                                }
                            )

        if violations:
            error_msg = "\n\nCritical path volume mount violations in preview-keycloak:\n"
            error_msg += "\nEmptyDir mounts at critical paths cause container failures!\n"
            for v in violations:
                error_msg += f"\n  Container: {v['container']}"
                error_msg += f"\n    Mount Path: {v['mount_path']}"
                error_msg += f"\n    Volume: {v['volume_name']} ({v['volume_type']})"
                error_msg += f"\n    Why Critical: {v['reason']}"
                error_msg += f"\n    Issue: {v['issue']}\n"
                error_msg += "\n    RECOMMENDED: Remove this volume mount entirely\n"

            pytest.fail(error_msg)

    def test_keycloak_has_required_volume_mounts(self):
        """
        Test that Keycloak has required volume mounts for data and cache.

        This ensures Keycloak can persist data and use temporary directories
        without overwriting critical application files.
        """
        manifests = self._render_kustomize_manifests()

        keycloak_deployment = self._find_resource(manifests, "Deployment", "preview-keycloak")

        if not keycloak_deployment:
            pytest.skip("preview-keycloak deployment not found in rendered manifests")

        spec = keycloak_deployment.get("spec", {})
        template = spec.get("template", {})
        pod_spec = template.get("spec", {})

        # Required mounts (safe paths for emptyDir)
        REQUIRED_MOUNTS = {
            "/opt/keycloak/data": "Keycloak data directory",
            "/tmp": "Temporary files",
            "/var/tmp": "Persistent temporary files",
        }

        containers = pod_spec.get("containers", [])
        keycloak_container = None
        for container in containers:
            if container.get("name") == "keycloak":
                keycloak_container = container
                break

        if not keycloak_container:
            pytest.fail("Keycloak container not found in deployment")

        volume_mounts = keycloak_container.get("volumeMounts", [])
        mounted_paths = {mount["mountPath"] for mount in volume_mounts}

        missing_mounts = []
        for required_path, purpose in REQUIRED_MOUNTS.items():
            if required_path not in mounted_paths:
                missing_mounts.append((required_path, purpose))

        if missing_mounts:
            error_msg = "\n\nMissing required volume mounts in preview-keycloak:\n"
            for path, purpose in missing_mounts:
                error_msg += f"\n  Path: {path}"
                error_msg += f"\n    Purpose: {purpose}\n"

            pytest.fail(error_msg)

    def test_all_deployments_have_valid_images(self):
        """
        Test that all deployments reference valid container images.

        This ensures no placeholder image tags or invalid registries are used.

        Note: "latest" tags are allowed for preview/dev environments (e.g., preview-latest, dev-latest)
        since we force-pull images anyway. Only production should use pinned versions.
        """
        manifests = self._render_kustomize_manifests()

        INVALID_IMAGE_PATTERNS = [
            ":latest",  # Standalone ":latest" not allowed, but "preview-latest" is OK
            "IMAGE_PLACEHOLDER",
            "YOUR_REGISTRY",
            "localhost",  # Should use actual registry
        ]

        # Allowed patterns that contain "latest" but are acceptable
        ALLOWED_LATEST_PATTERNS = [
            "preview-latest",
            "dev-latest",
            "development-latest",
            # TEMPORARY: Allow GCR workaround until GHCR :preview tag is created
            # This will be removed after CI fix is merged and kustomization.yaml
            # is updated to use: newName: ghcr.io/vishnu2kmohan/mcp-server-langgraph, newTag: preview
            # See: https://github.com/vishnu2kmohan/mcp-server-langgraph/pull/XXX
            # TODO: Remove this after switching to GHCR :preview tag
            "gcr.io/vishnu-sandbox-20250310/mcp-server-langgraph:latest",
        ]

        violations = []

        for manifest in manifests:
            if manifest.get("kind") != "Deployment":
                continue

            name = manifest.get("metadata", {}).get("name", "unknown")
            spec = manifest.get("spec", {})
            template = spec.get("template", {})
            pod_spec = template.get("spec", {})

            containers = pod_spec.get("containers", [])
            init_containers = pod_spec.get("initContainers", [])

            for container in containers + init_containers:
                container_name = container.get("name", "unknown")
                image = container.get("image", "")

                # Skip if image uses an allowed latest pattern
                if any(allowed in image for allowed in ALLOWED_LATEST_PATTERNS):
                    continue

                for invalid_pattern in INVALID_IMAGE_PATTERNS:
                    if invalid_pattern in image:
                        violations.append(
                            {
                                "deployment": name,
                                "container": container_name,
                                "image": image,
                                "invalid_pattern": invalid_pattern,
                                "issue": f"Image contains invalid pattern: {invalid_pattern}",
                            }
                        )

        if violations:
            error_msg = "\n\nInvalid container image references:\n"
            for v in violations:
                error_msg += f"\n  Deployment: {v['deployment']}"
                error_msg += f"\n    Container: {v['container']}"
                error_msg += f"\n    Image: {v['image']}"
                error_msg += f"\n    Issue: {v['issue']}\n"

            pytest.fail(error_msg)

    def test_kustomize_renders_without_errors(self):
        """
        Test that Kustomize can render manifests without errors.

        This is a basic smoke test to catch YAML syntax errors,
        invalid references, or missing patches.
        """
        # If we got here, _render_kustomize_manifests() succeeded
        manifests = self._render_kustomize_manifests()

        assert len(manifests) > 0, "No manifests rendered from Kustomize"

        # Verify we have expected core resources
        kinds = {m.get("kind") for m in manifests}

        required_kinds = {"Namespace", "Deployment", "Service", "ConfigMap"}
        missing_kinds = required_kinds - kinds

        if missing_kinds:
            pytest.fail(f"Missing required resource kinds: {missing_kinds}\nFound kinds: {sorted(kinds)}")

    def test_environment_labels_use_preview_not_staging(self):
        """
        Test that all environment labels/annotations use 'preview' not 'staging'.

        RED: Should FAIL initially - kustomization.yaml and namespace.yaml use 'staging'
        GREEN: Should PASS after updating all environment labels to 'preview'

        This ensures consistency after the staging-to-preview rename and prevents
        monitoring/alerting confusion from mixed environment labels.
        """
        manifests = self._render_kustomize_manifests()

        violations = []

        for manifest in manifests:
            kind = manifest.get("kind")
            name = manifest.get("metadata", {}).get("name", "unknown")

            # Check labels
            labels = manifest.get("metadata", {}).get("labels", {})
            if labels.get("environment") == "staging":
                violations.append(f"{kind}/{name}: metadata.labels.environment=staging")

            # Check annotations
            annotations = manifest.get("metadata", {}).get("annotations", {})
            if annotations.get("environment") == "staging":
                violations.append(f"{kind}/{name}: metadata.annotations.environment=staging")

        if violations:
            error_msg = "\n\nFound 'staging' environment labels (should be 'preview'):\n"
            error_msg += "The staging-to-preview rename requires all environment labels to be updated.\n\n"
            for v in violations:
                error_msg += f"  - {v}\n"
            error_msg += "\nFiles to update:\n"
            error_msg += "  - deployments/overlays/preview-gke/kustomization.yaml\n"
            error_msg += "  - deployments/overlays/preview-gke/namespace.yaml\n"
            pytest.fail(error_msg)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
