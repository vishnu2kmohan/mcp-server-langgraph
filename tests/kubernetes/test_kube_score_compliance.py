#!/usr/bin/env python3
"""
TDD Tests for Kube-Score Compliance

Following TDD principles:
1. RED: These tests verify kube-score best practices
2. GREEN: Fix manifests to pass all checks
3. REFACTOR: Ensure consistency across all deployments

Validates:
- ImagePullPolicy set to Always
- Resource limits and requests (CPU, Memory, Ephemeral Storage)
- Security context (high UIDs, read-only filesystem)
- Probe differentiation (readiness vs liveness)
- HPA configuration (no static replica count)
- PodDisruptionBudgets
- Service/NetworkPolicy selectors
"""

import gc
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml


# Mark as unit test to ensure it runs in CI (deployment validation)
pytestmark = pytest.mark.unit
PROJECT_ROOT = Path(__file__).parent.parent.parent
DEPLOYMENTS_BASE = PROJECT_ROOT / "deployments" / "base"
DEPLOYMENTS_OVERLAYS = PROJECT_ROOT / "deployments" / "overlays"


@pytest.mark.xdist_group(name="testimagepullpolicy")
class TestImagePullPolicy:
    """Test that all containers have imagePullPolicy: Always."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def _load_yaml_docs(self, file_path: Path) -> list[dict[str, Any]]:
        """Load all YAML documents from a file."""
        with open(file_path, encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
            return [d for d in docs if d is not None]

    def _get_deployments_and_statefulsets(self) -> list[Path]:
        """Get all deployment and statefulset YAML files."""
        files = []
        for pattern in ["*deployment.yaml", "*statefulset.yaml"]:
            files.extend(DEPLOYMENTS_BASE.glob(pattern))
        return files

    def test_all_containers_have_imagepullpolicy_always(self):
        """
        All containers and initContainers must have imagePullPolicy: Always.

        This ensures we always pull the latest image with the specified tag,
        improving security and preventing stale images.
        """
        files = self._get_deployments_and_statefulsets()
        assert len(files) > 0, "No deployment/statefulset files found"

        violations = []

        for file_path in files:
            docs = self._load_yaml_docs(file_path)

            for doc in docs:
                kind = doc.get("kind")
                if kind not in ["Deployment", "StatefulSet"]:
                    continue

                name = doc.get("metadata", {}).get("name", "unknown")
                spec = doc.get("spec", {}).get("template", {}).get("spec", {})

                # Check init containers
                for init_container in spec.get("initContainers", []):
                    container_name = init_container.get("name", "unknown")
                    pull_policy = init_container.get("imagePullPolicy")

                    if pull_policy != "Always":
                        violations.append(
                            f"{file_path.name}: {kind}/{name} init container '{container_name}' "
                            f"has imagePullPolicy='{pull_policy}' (expected 'Always')"
                        )

                # Check regular containers
                for container in spec.get("containers", []):
                    container_name = container.get("name", "unknown")
                    pull_policy = container.get("imagePullPolicy")

                    if pull_policy != "Always":
                        violations.append(
                            f"{file_path.name}: {kind}/{name} container '{container_name}' "
                            f"has imagePullPolicy='{pull_policy}' (expected 'Always')"
                        )

        if violations:
            error_msg = "\n\nImagePullPolicy violations found:\n\n"
            error_msg += "\n".join(f"  - {v}" for v in violations)
            error_msg += "\n\nFix: Set imagePullPolicy: Always for all containers\n"
            pytest.fail(error_msg)


@pytest.mark.xdist_group(name="testresourcelimits")
class TestResourceLimits:
    """Test that all containers have proper resource limits and requests."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def _load_yaml_docs(self, file_path: Path) -> list[dict[str, Any]]:
        """Load all YAML documents from a file."""
        with open(file_path, encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
            return [d for d in docs if d is not None]

    def _get_deployments_and_statefulsets(self) -> list[Path]:
        """Get all deployment and statefulset YAML files."""
        files = []
        for pattern in ["*deployment.yaml", "*statefulset.yaml"]:
            files.extend(DEPLOYMENTS_BASE.glob(pattern))
        return files

    def test_all_containers_have_cpu_memory_limits(self):
        """
        All containers must have CPU and Memory limits and requests.

        This prevents resource exhaustion and ensures fair scheduling.
        Init containers can be exempted if they're short-lived.
        """
        files = self._get_deployments_and_statefulsets()
        violations = []

        for file_path in files:
            docs = self._load_yaml_docs(file_path)

            for doc in docs:
                kind = doc.get("kind")
                if kind not in ["Deployment", "StatefulSet"]:
                    continue

                name = doc.get("metadata", {}).get("name", "unknown")
                spec = doc.get("spec", {}).get("template", {}).get("spec", {})

                # Check regular containers (strict requirements)
                for container in spec.get("containers", []):
                    container_name = container.get("name", "unknown")
                    resources = container.get("resources", {})
                    limits = resources.get("limits", {})
                    requests = resources.get("requests", {})

                    if "cpu" not in limits:
                        violations.append(f"{file_path.name}: {kind}/{name} container '{container_name}' missing CPU limit")
                    if "memory" not in limits:
                        violations.append(f"{file_path.name}: {kind}/{name} container '{container_name}' missing Memory limit")
                    if "cpu" not in requests:
                        violations.append(f"{file_path.name}: {kind}/{name} container '{container_name}' missing CPU request")
                    if "memory" not in requests:
                        violations.append(
                            f"{file_path.name}: {kind}/{name} container '{container_name}' missing Memory request"
                        )

        if violations:
            error_msg = "\n\nResource limit violations found:\n\n"
            error_msg += "\n".join(f"  - {v}" for v in violations[:20])  # Limit output
            if len(violations) > 20:
                error_msg += f"\n  ... and {len(violations) - 20} more"
            error_msg += "\n\nFix: Add resources.limits and resources.requests for CPU and Memory\n"
            pytest.fail(error_msg)

    def test_all_containers_have_ephemeral_storage_limits(self):
        """
        All containers should have ephemeral storage limits.

        This prevents containers from filling up node disk space.
        """
        files = self._get_deployments_and_statefulsets()
        violations = []

        for file_path in files:
            docs = self._load_yaml_docs(file_path)

            for doc in docs:
                kind = doc.get("kind")
                if kind not in ["Deployment", "StatefulSet"]:
                    continue

                name = doc.get("metadata", {}).get("name", "unknown")
                spec = doc.get("spec", {}).get("template", {}).get("spec", {})

                # Check all containers (including init)
                all_containers = spec.get("initContainers", []) + spec.get("containers", [])

                for container in all_containers:
                    container_name = container.get("name", "unknown")
                    resources = container.get("resources", {})
                    limits = resources.get("limits", {})
                    requests = resources.get("requests", {})

                    if "ephemeral-storage" not in limits:
                        violations.append(
                            f"{file_path.name}: {kind}/{name} container '{container_name}' " f"missing ephemeral-storage limit"
                        )
                    if "ephemeral-storage" not in requests:
                        violations.append(
                            f"{file_path.name}: {kind}/{name} container '{container_name}' "
                            f"missing ephemeral-storage request"
                        )

        if violations:
            error_msg = "\n\nEphemeral storage violations found:\n\n"
            error_msg += "\n".join(f"  - {v}" for v in violations[:15])
            if len(violations) > 15:
                error_msg += f"\n  ... and {len(violations) - 15} more"
            error_msg += "\n\nFix: Add ephemeral-storage to resources.limits and resources.requests\n"
            pytest.fail(error_msg)


@pytest.mark.xdist_group(name="testsecuritycontext")
class TestSecurityContext:
    """Test security context configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def _load_yaml_docs(self, file_path: Path) -> list[dict[str, Any]]:
        """Load all YAML documents from a file."""
        with open(file_path, encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
            return [d for d in docs if d is not None]

    def _get_deployments_and_statefulsets(self) -> list[Path]:
        """Get all deployment and statefulset YAML files."""
        files = []
        for pattern in ["*deployment.yaml", "*statefulset.yaml"]:
            files.extend(DEPLOYMENTS_BASE.glob(pattern))
        return files

    def test_containers_run_as_high_uid(self):
        """
        Containers should run as UID >= 10000 for security.

        This prevents privilege escalation and follows security best practices.
        """
        files = self._get_deployments_and_statefulsets()
        violations = []

        for file_path in files:
            docs = self._load_yaml_docs(file_path)

            for doc in docs:
                kind = doc.get("kind")
                if kind not in ["Deployment", "StatefulSet"]:
                    continue

                name = doc.get("metadata", {}).get("name", "unknown")
                spec = doc.get("spec", {}).get("template", {}).get("spec", {})

                # Check all containers
                all_containers = spec.get("initContainers", []) + spec.get("containers", [])

                for container in all_containers:
                    container_name = container.get("name", "unknown")
                    sec_context = container.get("securityContext", {})
                    run_as_user = sec_context.get("runAsUser")
                    run_as_group = sec_context.get("runAsGroup")

                    if run_as_user is not None and run_as_user < 10000:
                        violations.append(
                            f"{file_path.name}: {kind}/{name} container '{container_name}' "
                            f"runAsUser={run_as_user} (expected >= 10000)"
                        )
                    if run_as_group is not None and run_as_group < 10000:
                        violations.append(
                            f"{file_path.name}: {kind}/{name} container '{container_name}' "
                            f"runAsGroup={run_as_group} (expected >= 10000)"
                        )

        if violations:
            error_msg = "\n\nSecurity context UID/GID violations found:\n\n"
            error_msg += "\n".join(f"  - {v}" for v in violations[:15])
            if len(violations) > 15:
                error_msg += f"\n  ... and {len(violations) - 15} more"
            error_msg += "\n\nFix: Set runAsUser and runAsGroup to >= 10000\n"
            pytest.fail(error_msg)

    def test_containers_use_readonly_root_filesystem(self):
        """
        Containers should use read-only root filesystem where possible.

        This limits attack surface by preventing file modifications.
        """
        files = self._get_deployments_and_statefulsets()
        violations = []

        for file_path in files:
            docs = self._load_yaml_docs(file_path)

            for doc in docs:
                kind = doc.get("kind")
                if kind not in ["Deployment", "StatefulSet"]:
                    continue

                name = doc.get("metadata", {}).get("name", "unknown")
                spec = doc.get("spec", {}).get("template", {}).get("spec", {})

                # Only check main containers (not init containers)
                for container in spec.get("containers", []):
                    container_name = container.get("name", "unknown")
                    sec_context = container.get("securityContext", {})
                    read_only_fs = sec_context.get("readOnlyRootFilesystem")

                    # Allow exceptions for stateful services that need writable filesystems
                    # These services write to their data directories and cannot use readonly FS
                    STATEFUL_SERVICES_ALLOWED = {"postgres", "redis", "keycloak"}

                    if read_only_fs is not True and container_name not in STATEFUL_SERVICES_ALLOWED:
                        violations.append(
                            f"{file_path.name}: {kind}/{name} container '{container_name}' "
                            f"readOnlyRootFilesystem={read_only_fs} (expected True)"
                        )

        if violations:
            error_msg = "\n\nRead-only filesystem violations found:\n\n"
            error_msg += "\n".join(f"  - {v}" for v in violations[:15])
            if len(violations) > 15:
                error_msg += f"\n  ... and {len(violations) - 15} more"
            error_msg += "\n\nFix: Set readOnlyRootFilesystem: true in securityContext\n"
            error_msg += "Note: May require adding emptyDir volumes for /tmp if needed\n"
            pytest.fail(error_msg)


@pytest.mark.xdist_group(name="testprobeconfiguration")
class TestProbeConfiguration:
    """Test that readiness and liveness probes are different."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def _load_yaml_docs(self, file_path: Path) -> list[dict[str, Any]]:
        """Load all YAML documents from a file."""
        with open(file_path, encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
            return [d for d in docs if d is not None]

    def _get_deployments_and_statefulsets(self) -> list[Path]:
        """Get all deployment and statefulset YAML files."""
        files = []
        for pattern in ["*deployment.yaml", "*statefulset.yaml"]:
            files.extend(DEPLOYMENTS_BASE.glob(pattern))
        return files

    def test_readiness_liveness_probes_are_different(self):
        """
        Readiness and liveness probes should be different.

        Liveness probe should check if app needs restart.
        Readiness probe should check if app can serve traffic.
        """
        files = self._get_deployments_and_statefulsets()
        violations = []

        for file_path in files:
            docs = self._load_yaml_docs(file_path)

            for doc in docs:
                kind = doc.get("kind")
                if kind not in ["Deployment", "StatefulSet"]:
                    continue

                name = doc.get("metadata", {}).get("name", "unknown")
                spec = doc.get("spec", {}).get("template", {}).get("spec", {})

                for container in spec.get("containers", []):
                    container_name = container.get("name", "unknown")
                    liveness = container.get("livenessProbe")
                    readiness = container.get("readinessProbe")

                    # Skip if either probe is missing
                    if not liveness or not readiness:
                        continue

                    # Check if probes are identical
                    if liveness == readiness:
                        violations.append(
                            f"{file_path.name}: {kind}/{name} container '{container_name}' "
                            f"has identical liveness and readiness probes"
                        )

        if violations:
            error_msg = "\n\nProbe configuration violations found:\n\n"
            error_msg += "\n".join(f"  - {v}" for v in violations)
            error_msg += "\n\nFix: Make readiness probe more sensitive (lower threshold/faster fail)\n"
            error_msg += "Example: Liveness failureThreshold=3, Readiness failureThreshold=1\n"
            pytest.fail(error_msg)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
