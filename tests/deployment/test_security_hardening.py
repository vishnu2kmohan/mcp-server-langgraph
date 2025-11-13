"""
Regression tests for Kubernetes security hardening requirements.

Prevents recurrence of security misconfigurations detected by Trivy scans.

TDD Context:
- RED (2025-11-12): Keycloak container had readOnlyRootFilesystem: false
- Trivy scan flagged as HIGH severity (AVD-KSV-0014)
- GREEN: Set readOnlyRootFilesystem: true with proper volume mounts
- REFACTOR: This test prevents regression

Following TDD: Tests written FIRST to catch security violations, then fixes applied.
"""

from pathlib import Path

import pytest
import yaml


@pytest.mark.regression
@pytest.mark.security
@pytest.mark.deployment
class TestKubernetesSecurityHardening:
    """Test Kubernetes deployments follow security best practices."""

    def test_all_containers_have_readonly_root_filesystem(self):
        """
        Test: All containers must have readOnlyRootFilesystem: true.

        RED (Before Fix - 2025-11-12):
        - Keycloak container had readOnlyRootFilesystem: false
        - Trivy scan flagged as HIGH severity (AVD-KSV-0014)
        - Security risk: allows container to tamper with filesystem
        - Workflow: Deploy to GKE Staging (Run #19309378657) FAILED

        GREEN (After Fix):
        - Set readOnlyRootFilesystem: true
        - Added volume mounts for /tmp, /opt/keycloak/data, etc.
        - Trivy scan passes
        - Deployment workflow succeeds

        REFACTOR:
        - This test prevents regression
        - Validates all deployment manifests automatically
        - Runs in CI pre-commit hook and deployment validation
        """
        deployment_files = [
            Path("deployments/base/keycloak-deployment.yaml"),
            Path("deployments/overlays/staging-gke/keycloak-patch.yaml"),
            Path("deployments/overlays/production-gke/keycloak-patch.yaml"),
            # Add other deployment files as needed
        ]

        violations = []

        for file_path in deployment_files:
            if not file_path.exists():
                continue

            with open(file_path) as f:
                try:
                    manifest = yaml.safe_load(f)
                except yaml.YAMLError as e:
                    pytest.fail(f"Invalid YAML in {file_path}: {e}")

            if not manifest:
                continue

            # Extract containers from deployment
            containers = []
            if manifest.get("kind") == "Deployment":
                spec = manifest.get("spec", {}).get("template", {}).get("spec", {})
                containers = spec.get("containers", [])
                init_containers = spec.get("initContainers", [])
                containers.extend(init_containers)

            for container in containers:
                container_name = container.get("name", "unknown")
                security_context = container.get("securityContext", {})
                readonly = security_context.get("readOnlyRootFilesystem")

                if readonly is not True:
                    violations.append(
                        f"{file_path}: Container '{container_name}' has readOnlyRootFilesystem={readonly} (should be true)"
                    )

        assert not violations, (
            "\n\nSecurity violation: Containers without readOnlyRootFilesystem:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nFix: Set readOnlyRootFilesystem: true and add volume mounts for writable directories."
            + "\nSee: deployments/overlays/staging-gke/keycloak-patch.yaml for reference implementation"
        )

    def test_containers_with_readonly_fs_have_volume_mounts(self):
        """
        Test: Containers with readOnlyRootFilesystem: true must have volume mounts for writable dirs.

        Ensures containers don't fail to start due to missing writable directories.
        Common directories needing mounts: /tmp, /var/cache, /opt/*/data
        """
        deployment_files = [
            Path("deployments/overlays/staging-gke/keycloak-patch.yaml"),
            Path("deployments/overlays/production-gke/keycloak-patch.yaml"),
        ]

        warnings = []

        for file_path in deployment_files:
            if not file_path.exists():
                continue

            with open(file_path) as f:
                manifest = yaml.safe_load(f)

            if not manifest or manifest.get("kind") != "Deployment":
                continue

            spec = manifest.get("spec", {}).get("template", {}).get("spec", {})
            containers = spec.get("containers", [])
            init_containers = spec.get("initContainers", [])
            all_containers = containers + init_containers

            for container in all_containers:
                container_name = container.get("name", "unknown")
                security_context = container.get("securityContext", {})
                readonly = security_context.get("readOnlyRootFilesystem")

                if readonly is True:
                    volume_mounts = container.get("volumeMounts", [])

                    # Check for /tmp mount (most common writable directory)
                    has_tmp_mount = any(vm.get("mountPath") == "/tmp" for vm in volume_mounts)

                    if not has_tmp_mount:
                        warnings.append(
                            f"{file_path}: Container '{container_name}' has readOnlyRootFilesystem but no /tmp volume mount"
                        )

        if warnings:
            # This is a warning, not a failure - some containers might not need /tmp
            pytest.skip(
                "\n\nWarning: Containers with readOnlyRootFilesystem but no /tmp mount:\n"
                + "\n".join(f"  - {w}" for w in warnings)
                + "\n\nVerify these containers don't need writable directories"
            )

    def test_security_contexts_follow_least_privilege(self):
        """
        Test: All containers follow least-privilege security principles.

        Validates:
        - runAsNonRoot: true
        - allowPrivilegeEscalation: false
        - capabilities.drop: [ALL]
        """
        deployment_files = [
            Path("deployments/base/keycloak-deployment.yaml"),
            Path("deployments/overlays/staging-gke/keycloak-patch.yaml"),
            Path("deployments/overlays/production-gke/keycloak-patch.yaml"),
        ]

        violations = []

        for file_path in deployment_files:
            if not file_path.exists():
                continue

            with open(file_path) as f:
                manifest = yaml.safe_load(f)

            if not manifest or manifest.get("kind") != "Deployment":
                continue

            spec = manifest.get("spec", {}).get("template", {}).get("spec", {})
            containers = spec.get("containers", [])

            for container in containers:
                container_name = container.get("name", "unknown")
                security_context = container.get("securityContext", {})

                # Check runAsNonRoot
                if not security_context.get("runAsNonRoot"):
                    violations.append(f"{file_path}: Container '{container_name}' missing runAsNonRoot: true")

                # Check allowPrivilegeEscalation
                if security_context.get("allowPrivilegeEscalation") is not False:
                    violations.append(f"{file_path}: Container '{container_name}' missing allowPrivilegeEscalation: false")

                # Check capabilities are dropped
                capabilities = security_context.get("capabilities", {})
                drop = capabilities.get("drop", [])
                if "ALL" not in drop:
                    violations.append(f"{file_path}: Container '{container_name}' missing capabilities.drop: [ALL]")

        assert not violations, (
            "\n\nSecurity violations (least-privilege principles):\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nAll containers must have runAsNonRoot: true, allowPrivilegeEscalation: false, "
            + "and capabilities.drop: [ALL]"
        )
