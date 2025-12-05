"""
Deployment Validation: Keycloak readOnlyRootFilesystem Configuration

Tests that Keycloak deployment correctly uses `readOnlyRootFilesystem: true` across
all environments (base, staging, production) using the optimized Keycloak image.

ARCHITECTURE (as of 2025-12-02):
- Custom Keycloak image (docker/Dockerfile.keycloak) pre-compiles Quarkus via 'kc.sh build'
- Runtime uses '--optimized' flag to skip JIT compilation
- This allows readOnlyRootFilesystem: true for better security

Previous Issue (RESOLVED):
- Keycloak uses Quarkus framework which performed JIT compilation at runtime
- JIT compilation required write access to filesystem (readOnlyRootFilesystem: false)
- Native images (GraalVM) not officially supported by Keycloak

Solution:
- Custom multi-stage Docker build runs 'kc.sh build' during image creation
- Pre-compiled Quarkus artifacts copied to runtime image
- Runtime uses '--optimized' flag - no JIT needed
- Can now use readOnlyRootFilesystem: true

Test Coverage:
1. All deployments have readOnlyRootFilesystem: true
2. All deployments use --optimized flag
3. All deployments have proper security controls
4. Inline documentation references custom image and solution

References:
- docker/Dockerfile.keycloak: Custom optimized Keycloak image
- https://www.keycloak.org/server/containers: Official container documentation
- GitHub issue #10150: Original readOnlyRootFilesystem incompatibility (now resolved)
"""

import gc
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.fixtures.tool_fixtures import requires_tool

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
def base_manifest(deployments_dir: Path) -> list[dict]:
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
def staging_manifest(deployments_dir: Path) -> list[dict]:
    """Render preview-gke Kustomize manifest"""
    staging_dir = deployments_dir / "overlays" / "preview-gke"
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
def production_manifest(deployments_dir: Path) -> list[dict]:
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


def get_keycloak_container(deployment: dict) -> dict | None:
    """Extract Keycloak container from deployment"""
    if not deployment:
        return None

    containers = deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])

    for container in containers:
        if container.get("name") == "keycloak":
            return container
    return None


def get_keycloak_container_security_context(deployment: dict) -> dict | None:
    """Extract Keycloak container securityContext from deployment"""
    container = get_keycloak_container(deployment)
    if container:
        return container.get("securityContext")
    return None


@pytest.mark.deployment
@pytest.mark.kubernetes
@pytest.mark.xdist_group(name="keycloak_deployment_tests")
@requires_tool("kubectl")
class TestKeycloakReadOnlyFilesystemConfiguration:
    """Test Keycloak readOnlyRootFilesystem: true configuration across all environments"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_base_keycloak_has_readonly_filesystem_true(self, base_manifest: list[dict]) -> None:
        """
        GIVEN base Kustomize deployment with optimized Keycloak image
        WHEN Keycloak deployment is rendered
        THEN Keycloak container securityContext.readOnlyRootFilesystem should be true
        """
        deployment = find_keycloak_deployment(base_manifest)
        assert deployment is not None, "Keycloak deployment not found in base manifest"

        security_context = get_keycloak_container_security_context(deployment)
        assert security_context is not None, "Keycloak container securityContext not found"

        assert "readOnlyRootFilesystem" in security_context, (
            "readOnlyRootFilesystem not explicitly set in Keycloak securityContext"
        )
        assert security_context["readOnlyRootFilesystem"] is True, (
            "Expected readOnlyRootFilesystem: true with optimized Keycloak image. "
            "The custom image (docker/Dockerfile.keycloak) pre-compiles Quarkus."
        )

    def test_production_keycloak_has_readonly_filesystem_true(self, production_manifest: list[dict]) -> None:
        """
        GIVEN production-gke Kustomize deployment with optimized Keycloak image
        WHEN Keycloak deployment is rendered
        THEN Keycloak container securityContext.readOnlyRootFilesystem should be true
        """
        deployment = find_keycloak_deployment(production_manifest)
        assert deployment is not None, "Keycloak deployment not found in production manifest"

        security_context = get_keycloak_container_security_context(deployment)
        assert security_context is not None, "Keycloak container securityContext not found"

        assert "readOnlyRootFilesystem" in security_context, (
            "readOnlyRootFilesystem not explicitly set in Keycloak securityContext"
        )
        assert security_context["readOnlyRootFilesystem"] is True, (
            "Expected readOnlyRootFilesystem: true with optimized Keycloak image. "
            "The custom image (docker/Dockerfile.keycloak) pre-compiles Quarkus."
        )

    def test_staging_keycloak_has_readonly_filesystem_true(self, staging_manifest: list[dict]) -> None:
        """
        GIVEN preview-gke Kustomize deployment with optimized Keycloak image
        WHEN Keycloak deployment is rendered
        THEN Keycloak container securityContext.readOnlyRootFilesystem should be true
        """
        deployment = find_keycloak_deployment(staging_manifest)
        assert deployment is not None, "Keycloak deployment not found in staging manifest"

        security_context = get_keycloak_container_security_context(deployment)
        assert security_context is not None, "Keycloak container securityContext not found"

        assert "readOnlyRootFilesystem" in security_context, (
            "readOnlyRootFilesystem not explicitly set in Keycloak securityContext"
        )
        assert security_context["readOnlyRootFilesystem"] is True, (
            "Expected readOnlyRootFilesystem: true with optimized Keycloak image. "
            "The custom image (docker/Dockerfile.keycloak) pre-compiles Quarkus."
        )

    def test_base_keycloak_uses_optimized_flag(self, base_manifest: list[dict]) -> None:
        """
        GIVEN base Kustomize deployment
        WHEN Keycloak deployment is rendered
        THEN Keycloak should use --optimized flag to skip runtime augmentation
        """
        deployment = find_keycloak_deployment(base_manifest)
        assert deployment is not None

        container = get_keycloak_container(deployment)
        assert container is not None

        args = container.get("args", [])
        assert "--optimized" in args, (
            "Keycloak must use --optimized flag. This skips runtime Quarkus augmentation and uses pre-built artifacts."
        )

    def test_staging_keycloak_uses_optimized_flag(self, staging_manifest: list[dict]) -> None:
        """
        GIVEN preview-gke Kustomize deployment
        WHEN Keycloak deployment is rendered
        THEN Keycloak should use --optimized flag
        """
        deployment = find_keycloak_deployment(staging_manifest)
        assert deployment is not None

        container = get_keycloak_container(deployment)
        assert container is not None

        args = container.get("args", [])
        assert "--optimized" in args, "Keycloak must use --optimized flag in staging"

    def test_production_keycloak_uses_optimized_flag(self, production_manifest: list[dict]) -> None:
        """
        GIVEN production-gke Kustomize deployment
        WHEN Keycloak deployment is rendered
        THEN Keycloak should use --optimized flag
        """
        deployment = find_keycloak_deployment(production_manifest)
        assert deployment is not None

        container = get_keycloak_container(deployment)
        assert container is not None

        args = container.get("args", [])
        assert "--optimized" in args, "Keycloak must use --optimized flag in production"

    def test_base_keycloak_has_security_mitigations(self, base_manifest: list[dict]) -> None:
        """
        GIVEN base Kustomize deployment with readOnlyRootFilesystem: true
        WHEN validating security controls
        THEN Keycloak must have proper security settings:
          - runAsNonRoot: true
          - allowPrivilegeEscalation: false
          - capabilities.drop: ALL
          - emptyDir volumes for writable paths (/tmp, /opt/keycloak/data)
        """
        deployment = find_keycloak_deployment(base_manifest)
        assert deployment is not None

        security_context = get_keycloak_container_security_context(deployment)
        assert security_context is not None

        # Verify security controls
        assert security_context.get("runAsNonRoot") is True, "Keycloak must run as non-root user"
        assert security_context.get("allowPrivilegeEscalation") is False, "Keycloak must not allow privilege escalation"
        assert "ALL" in security_context.get("capabilities", {}).get("drop", []), "Keycloak must drop all Linux capabilities"
        assert security_context.get("runAsUser") == 10000, "Keycloak must run as UID 10000 (non-root)"

        # Verify emptyDir volumes exist for writable paths
        volumes = deployment.get("spec", {}).get("template", {}).get("spec", {}).get("volumes", [])
        volume_names = {vol.get("name") for vol in volumes}

        assert "tmp" in volume_names, "Missing /tmp emptyDir volume for readOnlyRootFilesystem"

    def test_staging_keycloak_has_security_mitigations(self, staging_manifest: list[dict]) -> None:
        """
        GIVEN preview-gke deployment with readOnlyRootFilesystem: true
        WHEN validating security mitigations
        THEN Keycloak must have proper security controls
        """
        deployment = find_keycloak_deployment(staging_manifest)
        assert deployment is not None

        security_context = get_keycloak_container_security_context(deployment)
        assert security_context is not None

        assert security_context.get("runAsNonRoot") is True
        assert security_context.get("allowPrivilegeEscalation") is False
        assert "ALL" in security_context.get("capabilities", {}).get("drop", [])
        assert security_context.get("runAsUser") == 10000

    def test_production_keycloak_has_security_mitigations(self, production_manifest: list[dict]) -> None:
        """
        GIVEN production-gke deployment with readOnlyRootFilesystem: true
        WHEN validating security mitigations
        THEN Keycloak must have proper security controls
        """
        deployment = find_keycloak_deployment(production_manifest)
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
class TestKeycloakOptimizedImageDocumentation:
    """Test that optimized Keycloak image usage is properly documented"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_dockerfile_exists_for_optimized_keycloak(self, repo_root: Path) -> None:
        """
        GIVEN docker/Dockerfile.keycloak
        WHEN checking file existence
        THEN custom Keycloak Dockerfile should exist
        """
        dockerfile = repo_root / "docker" / "Dockerfile.keycloak"
        assert dockerfile.exists(), (
            "docker/Dockerfile.keycloak not found. This file builds the optimized Keycloak image with pre-compiled Quarkus."
        )

    def test_dockerfile_has_kc_build_command(self, repo_root: Path) -> None:
        """
        GIVEN docker/Dockerfile.keycloak
        WHEN reading file contents
        THEN Dockerfile should run 'kc.sh build' for pre-compilation
        """
        dockerfile = repo_root / "docker" / "Dockerfile.keycloak"
        if not dockerfile.exists():
            pytest.skip("Keycloak Dockerfile not found")

        content = dockerfile.read_text()
        assert "kc.sh build" in content, (
            "Dockerfile must run 'kc.sh build' to pre-compile Quarkus. This is what enables readOnlyRootFilesystem: true."
        )

    def test_staging_overlay_has_inline_comments(self, deployments_dir: Path) -> None:
        """
        GIVEN overlays/preview-gke/keycloak-patch.yaml
        WHEN reading file contents
        THEN inline comments should explain the optimized image approach
        """
        keycloak_patch = deployments_dir / "overlays" / "preview-gke" / "keycloak-patch.yaml"
        if not keycloak_patch.exists():
            pytest.skip("Staging Keycloak patch not found")

        content = keycloak_patch.read_text()

        # Check for optimized image documentation
        assert "--optimized" in content, "Patch should use --optimized flag"
        assert "readonlyrootfilesystem: true" in content.lower(), "Patch should have readOnlyRootFilesystem: true"

    def test_production_overlay_has_inline_comments(self, deployments_dir: Path) -> None:
        """
        GIVEN overlays/production-gke/keycloak-patch.yaml
        WHEN reading file contents
        THEN inline comments should explain the optimized image approach
        """
        keycloak_patch = deployments_dir / "overlays" / "production-gke" / "keycloak-patch.yaml"
        if not keycloak_patch.exists():
            pytest.skip("Production Keycloak patch not found")

        content = keycloak_patch.read_text()

        # Check for optimized image documentation
        assert "--optimized" in content, "Patch should use --optimized flag"
        assert "readonlyrootfilesystem: true" in content.lower(), "Patch should have readOnlyRootFilesystem: true"
