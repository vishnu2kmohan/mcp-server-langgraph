"""
Deployment Validation: Keycloak readOnlyRootFilesystem Configuration

Tests that Keycloak deployment correctly uses `readOnlyRootFilesystem: false` across
all environments (base, staging, production) to support Quarkus JIT compilation.

Context:
- Keycloak uses Quarkus framework which performs JIT compilation at runtime
- JIT compilation requires write access to filesystem (cannot use readOnlyRootFilesystem: true)
- Native images (GraalVM) not officially supported by Keycloak (verified via WebSearch 2025-11-20)
- See deployments/base/.trivyignore (AVD-KSV-0014) for full security justification

Test Coverage:
1. Base deployment has readOnlyRootFilesystem: false in securityContext
2. Production overlay has readOnlyRootFilesystem: false in securityContext
3. Staging overlay has readOnlyRootFilesystem: false in securityContext (if exists)
4. All deployments have comprehensive inline documentation explaining why
5. All deployments have proper security mitigations (emptyDir volumes, runAsNonRoot, etc.)

References:
- ADR-0056: Database Architecture and Naming Convention
- GitHub issue #10150: Keycloak/Quarkus readOnlyRootFilesystem incompatibility
- deployments/base/.trivyignore: AVD-KSV-0014 suppression documentation
"""

import gc
import subprocess
from pathlib import Path

import pytest
import yaml

# Mark as integration test (requires kubectl/kustomize tools)
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def repo_root() -> Path:
    """
    Get repository root directory using marker file search.

    Uses marker files (.git, pyproject.toml) instead of hardcoded .parents[N]
    to prevent path calculation errors when files are moved.
    """
    current = Path(__file__).resolve().parent
    markers = [".git", "pyproject.toml"]

    while current != current.parent:
        if any((current / marker).exists() for marker in markers):
            return current
        current = current.parent

    raise RuntimeError("Cannot find project root - no .git or pyproject.toml found")


@pytest.fixture(scope="module")
def deployments_dir(repo_root: Path) -> Path:
    """Get deployments directory"""
    return repo_root / "deployments"


@pytest.fixture(scope="module")
def base_manifest(deployments_dir: Path) -> dict:
    """Render base Kustomize manifest"""
    result = subprocess.run(
        ["kubectl", "kustomize", str(deployments_dir / "base")],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return list(yaml.safe_load_all(result.stdout))


@pytest.fixture(scope="module")
def staging_manifest(deployments_dir: Path) -> dict:
    """Render staging-gke Kustomize manifest"""
    staging_dir = deployments_dir / "overlays" / "staging-gke"
    if not staging_dir.exists():
        pytest.skip("Staging overlay not found")

    result = subprocess.run(
        ["kubectl", "kustomize", str(staging_dir)],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return list(yaml.safe_load_all(result.stdout))


@pytest.fixture(scope="module")
def production_manifest(deployments_dir: Path) -> dict:
    """Render production-gke Kustomize manifest"""
    prod_dir = deployments_dir / "overlays" / "production-gke"
    if not prod_dir.exists():
        pytest.skip("Production overlay not found")

    result = subprocess.run(
        ["kubectl", "kustomize", str(prod_dir)],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return list(yaml.safe_load_all(result.stdout))


def find_keycloak_deployment(manifest: list[dict]) -> dict | None:
    """Find Keycloak deployment in manifest"""
    for doc in manifest:
        if not doc:
            continue
        if doc.get("kind") == "Deployment" and "keycloak" in doc.get("metadata", {}).get("name", "").lower():
            return doc
    return None


def get_keycloak_container_security_context(deployment: dict) -> dict | None:
    """Extract Keycloak container securityContext from deployment"""
    if not deployment:
        return None

    containers = deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])

    for container in containers:
        if container.get("name") == "keycloak":
            return container.get("securityContext")
    return None


@pytest.mark.deployment
@pytest.mark.kubernetes
@pytest.mark.xdist_group(name="keycloak_deployment_tests")
class TestKeycloakReadOnlyFilesystemConfiguration:
    """Test Keycloak readOnlyRootFilesystem configuration across all environments"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_base_keycloak_has_readonly_filesystem_false(self, base_manifest: list[dict]) -> None:
        """
        GIVEN base Kustomize deployment
        WHEN Keycloak deployment is rendered
        THEN Keycloak container securityContext.readOnlyRootFilesystem should be false
        """
        deployment = find_keycloak_deployment(base_manifest)
        assert deployment is not None, "Keycloak deployment not found in base manifest"

        security_context = get_keycloak_container_security_context(deployment)
        assert security_context is not None, "Keycloak container securityContext not found"

        assert (
            "readOnlyRootFilesystem" in security_context
        ), "readOnlyRootFilesystem not explicitly set in Keycloak securityContext"
        assert security_context["readOnlyRootFilesystem"] is False, (
            "Expected readOnlyRootFilesystem: false for Quarkus JIT compilation. "
            "See deployments/base/.trivyignore (AVD-KSV-0014) for justification."
        )

    def test_production_keycloak_has_readonly_filesystem_false(self, production_manifest: list[dict]) -> None:
        """
        GIVEN production-gke Kustomize deployment
        WHEN Keycloak deployment is rendered
        THEN Keycloak container securityContext.readOnlyRootFilesystem should be false
        """
        deployment = find_keycloak_deployment(production_manifest)
        assert deployment is not None, "Keycloak deployment not found in production manifest"

        security_context = get_keycloak_container_security_context(deployment)
        assert security_context is not None, "Keycloak container securityContext not found"

        assert (
            "readOnlyRootFilesystem" in security_context
        ), "readOnlyRootFilesystem not explicitly set in Keycloak securityContext"
        assert security_context["readOnlyRootFilesystem"] is False, (
            "Expected readOnlyRootFilesystem: false for Quarkus JIT compilation. "
            "See deployments/base/.trivyignore (AVD-KSV-0014) for justification."
        )

    def test_staging_keycloak_has_readonly_filesystem_false(self, staging_manifest: list[dict]) -> None:
        """
        GIVEN staging-gke Kustomize deployment
        WHEN Keycloak deployment is rendered
        THEN Keycloak container securityContext.readOnlyRootFilesystem should be false
        """
        deployment = find_keycloak_deployment(staging_manifest)
        assert deployment is not None, "Keycloak deployment not found in staging manifest"

        security_context = get_keycloak_container_security_context(deployment)
        assert security_context is not None, "Keycloak container securityContext not found"

        assert (
            "readOnlyRootFilesystem" in security_context
        ), "readOnlyRootFilesystem not explicitly set in Keycloak securityContext"
        assert security_context["readOnlyRootFilesystem"] is False, (
            "Expected readOnlyRootFilesystem: false for Quarkus JIT compilation. "
            "See deployments/base/.trivyignore (AVD-KSV-0014) for justification."
        )

    def test_base_keycloak_has_security_mitigations(self, base_manifest: list[dict]) -> None:
        """
        GIVEN base Kustomize deployment with readOnlyRootFilesystem: false
        WHEN validating security mitigations
        THEN Keycloak must have compensating security controls:
          - runAsNonRoot: true
          - allowPrivilegeEscalation: false
          - capabilities.drop: ALL
          - emptyDir volumes for writable paths
        """
        deployment = find_keycloak_deployment(base_manifest)
        assert deployment is not None

        security_context = get_keycloak_container_security_context(deployment)
        assert security_context is not None

        # Verify security mitigations
        assert security_context.get("runAsNonRoot") is True, "Keycloak must run as non-root user"
        assert security_context.get("allowPrivilegeEscalation") is False, "Keycloak must not allow privilege escalation"
        assert "ALL" in security_context.get("capabilities", {}).get("drop", []), "Keycloak must drop all Linux capabilities"
        assert security_context.get("runAsUser") == 10000, "Keycloak must run as UID 10000 (non-root)"

        # Verify emptyDir volumes exist for writable paths
        volumes = deployment.get("spec", {}).get("template", {}).get("spec", {}).get("volumes", [])
        volume_names = {vol.get("name") for vol in volumes}
        # Base uses "work-dir", overlays may use "keycloak-data"
        required_volumes = {"tmp"}
        workdir_volumes = {"work-dir", "keycloak-data"}

        assert required_volumes.issubset(volume_names), (
            f"Missing required emptyDir volumes. Expected {required_volumes}, "
            f"found {volume_names.intersection(required_volumes)}"
        )
        assert len(volume_names.intersection(workdir_volumes)) > 0, (
            f"Missing work directory volume. Expected one of {workdir_volumes}, "
            f"found {volume_names.intersection(workdir_volumes)}"
        )

    def test_production_keycloak_has_security_mitigations(self, production_manifest: list[dict]) -> None:
        """
        GIVEN production-gke deployment with readOnlyRootFilesystem: false
        WHEN validating security mitigations
        THEN Keycloak must have compensating security controls
        """
        deployment = find_keycloak_deployment(production_manifest)
        assert deployment is not None

        security_context = get_keycloak_container_security_context(deployment)
        assert security_context is not None

        assert security_context.get("runAsNonRoot") is True
        assert security_context.get("allowPrivilegeEscalation") is False
        assert "ALL" in security_context.get("capabilities", {}).get("drop", [])
        assert security_context.get("runAsUser") == 10000

    def test_staging_keycloak_has_security_mitigations(self, staging_manifest: list[dict]) -> None:
        """
        GIVEN staging-gke deployment with readOnlyRootFilesystem: false
        WHEN validating security mitigations
        THEN Keycloak must have compensating security controls
        """
        deployment = find_keycloak_deployment(staging_manifest)
        assert deployment is not None

        security_context = get_keycloak_container_security_context(deployment)
        assert security_context is not None

        assert security_context.get("runAsNonRoot") is True
        assert security_context.get("allowPrivilegeEscalation") is False
        assert "ALL" in security_context.get("capabilities", {}).get("drop", [])
        assert security_context.get("runAsUser") == 10000


@pytest.mark.deployment
@pytest.mark.security
@pytest.mark.xdist_group(name="keycloak_deployment_tests")
class TestKeycloakReadOnlyFilesystemDocumentation:
    """Test that readOnlyRootFilesystem: false is properly documented"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_base_deployment_has_inline_comments(self, deployments_dir: Path) -> None:
        """
        GIVEN base/keycloak-deployment.yaml
        WHEN reading file contents
        THEN inline comments should explain why readOnlyRootFilesystem: false
        AND reference GitHub issue #10150
        AND reference .trivyignore AVD-KSV-0014
        """
        keycloak_deployment = deployments_dir / "base" / "keycloak-deployment.yaml"
        assert keycloak_deployment.exists(), "Base Keycloak deployment file not found"

        content = keycloak_deployment.read_text()

        # Check for comprehensive inline documentation
        assert "readonlyrootfilesystem: false" in content.lower(), "readOnlyRootFilesystem: false not found in base deployment"
        assert "quarkus" in content.lower(), "Inline comment should mention Quarkus as the reason"
        assert "jit compilation" in content.lower(), "Inline comment should explain JIT compilation requirement"
        assert "#10150" in content or "10150" in content, "Inline comment should reference GitHub issue #10150"
        assert (
            "trivyignore" in content.lower() or "avd-ksv-0014" in content.lower()
        ), "Inline comment should reference .trivyignore AVD-KSV-0014"

    def test_production_overlay_has_inline_comments(self, deployments_dir: Path) -> None:
        """
        GIVEN overlays/production-gke/keycloak-patch.yaml
        WHEN reading file contents
        THEN inline comments should explain why readOnlyRootFilesystem: false
        """
        keycloak_patch = deployments_dir / "overlays" / "production-gke" / "keycloak-patch.yaml"
        if not keycloak_patch.exists():
            pytest.skip("Production Keycloak patch not found")

        content = keycloak_patch.read_text()

        assert "readonlyrootfilesystem: false" in content.lower()
        assert "quarkus" in content.lower()
        assert "jit compilation" in content.lower()
        # Production patch should reference base .trivyignore for full justification
        assert "trivyignore" in content.lower() or "avd-ksv-0014" in content.lower()

    def test_trivy_ignore_file_exists_and_documents_decision(self, deployments_dir: Path) -> None:
        """
        GIVEN deployments/base/.trivyignore
        WHEN reading file contents
        THEN AVD-KSV-0014 should be suppressed with comprehensive justification
        AND justification should reference WebSearch research findings
        AND justification should list compensating security controls
        """
        trivyignore = deployments_dir / "base" / ".trivyignore"
        assert trivyignore.exists(), (
            "deployments/base/.trivyignore not found. "
            "This file documents the security exception for readOnlyRootFilesystem: false"
        )

        content = trivyignore.read_text()

        # Check AVD-KSV-0014 suppression exists
        assert "AVD-KSV-0014" in content, "AVD-KSV-0014 (readOnlyRootFilesystem) not suppressed in .trivyignore"

        # Check comprehensive justification
        assert "quarkus" in content.lower(), "Trivy suppression should explain Quarkus JIT requirement"
        assert (
            "native image" in content.lower() or "graalvm" in content.lower()
        ), "Trivy suppression should mention native image alternative not supported"
        assert "emptydir" in content.lower(), "Trivy suppression should document emptyDir volume mitigation"
        assert (
            "runasnonroot" in content.lower() or "run as non-root" in content.lower()
        ), "Trivy suppression should document runAsNonRoot mitigation"
        assert "capabilities" in content.lower(), "Trivy suppression should document capabilities.drop: ALL mitigation"
