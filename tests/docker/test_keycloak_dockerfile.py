"""
TDD Tests for Keycloak Optimized Dockerfile.

These tests validate that the Keycloak Dockerfile follows best practices for
building an optimized Keycloak image that doesn't require runtime augmentation.

Issue: Keycloak 26.4+ with Quarkus requires JIT compilation at startup, which
fails in read-only container environments because it tries to modify JAR files.

Solution: Build an optimized image with `kc.sh build` during Docker build time.

Reference: https://www.keycloak.org/server/containers
"""

import gc
from pathlib import Path

import pytest

# Module-level pytest markers for test categorization
pytestmark = [pytest.mark.unit, pytest.mark.docker]


@pytest.fixture(scope="module")
def keycloak_dockerfile_path() -> Path:
    """Path to the Keycloak Dockerfile."""
    return Path(__file__).parent.parent.parent / "docker" / "Dockerfile.keycloak"


@pytest.fixture(scope="module")
def keycloak_dockerfile_content(keycloak_dockerfile_path: Path) -> str:
    """Content of the Keycloak Dockerfile."""
    if not keycloak_dockerfile_path.exists():
        pytest.skip(f"Keycloak Dockerfile not found at {keycloak_dockerfile_path}")
    return keycloak_dockerfile_path.read_text()


@pytest.mark.xdist_group(name="keycloak_dockerfile")
class TestKeycloakDockerfileStructure:
    """Tests for Dockerfile structure and multi-stage build."""

    def teardown_method(self) -> None:
        """Clean up after each test to prevent memory issues in xdist."""
        gc.collect()

    def test_dockerfile_exists_at_expected_path(self, keycloak_dockerfile_path: Path) -> None:
        """Verify Keycloak Dockerfile exists at the expected path."""
        assert keycloak_dockerfile_path.exists(), (
            f"Keycloak Dockerfile should exist at {keycloak_dockerfile_path}. "
            "This is required for building an optimized Keycloak image."
        )

    def test_uses_multistage_build_for_optimization(self, keycloak_dockerfile_content: str) -> None:
        """
        Verify Dockerfile uses multi-stage build.

        Multi-stage builds are required to:
        1. Run kc.sh build in builder stage
        2. Copy optimized artifacts to runtime stage
        3. Keep final image size small
        """
        # Count FROM statements - should have at least 2 for multi-stage
        from_count = keycloak_dockerfile_content.lower().count("from ")
        assert from_count >= 2, (
            f"Dockerfile should use multi-stage build (found {from_count} FROM statements). "
            "First stage builds optimized Keycloak, second stage creates minimal runtime image."
        )

    def test_has_builder_stage_named_correctly(self, keycloak_dockerfile_content: str) -> None:
        """Verify Dockerfile has a named builder stage."""
        assert "as builder" in keycloak_dockerfile_content.lower(), (
            "Dockerfile should have a named 'builder' stage for the build process"
        )

    def test_uses_official_keycloak_base_image(self, keycloak_dockerfile_content: str) -> None:
        """Verify Dockerfile uses official Keycloak image."""
        assert "quay.io/keycloak/keycloak" in keycloak_dockerfile_content, (
            "Dockerfile should use official Keycloak image from quay.io/keycloak/keycloak"
        )


@pytest.mark.xdist_group(name="keycloak_dockerfile")
class TestKeycloakBuildOptimization:
    """Tests for Keycloak build optimization configuration."""

    def teardown_method(self) -> None:
        """Clean up after each test to prevent memory issues in xdist."""
        gc.collect()

    def test_runs_kc_build_command_for_precompilation(self, keycloak_dockerfile_content: str) -> None:
        """
        Verify Dockerfile runs kc.sh build during image build.

        This is the critical step that pre-compiles Quarkus, preventing
        the ReadOnlyFileSystemException at runtime.
        """
        assert "kc.sh build" in keycloak_dockerfile_content, (
            "Dockerfile must run 'kc.sh build' to pre-compile Quarkus. "
            "Without this, Keycloak will fail with ReadOnlyFileSystemException."
        )

    def test_configures_database_type_for_postgres(self, keycloak_dockerfile_content: str) -> None:
        """
        Verify Dockerfile configures database type for build.

        KC_DB must be set at build time for proper optimization.
        """
        assert "KC_DB" in keycloak_dockerfile_content, (
            "Dockerfile should set KC_DB environment variable for database configuration"
        )
        assert "postgres" in keycloak_dockerfile_content.lower(), "Dockerfile should configure PostgreSQL as the database type"

    def test_enables_health_endpoint_at_build_time(self, keycloak_dockerfile_content: str) -> None:
        """Verify Dockerfile enables health endpoints at build time."""
        assert "KC_HEALTH_ENABLED" in keycloak_dockerfile_content, (
            "Dockerfile should set KC_HEALTH_ENABLED=true for Kubernetes probes"
        )

    def test_enables_metrics_endpoint_at_build_time(self, keycloak_dockerfile_content: str) -> None:
        """Verify Dockerfile enables metrics endpoints at build time."""
        assert "KC_METRICS_ENABLED" in keycloak_dockerfile_content, (
            "Dockerfile should set KC_METRICS_ENABLED=true for Prometheus scraping"
        )


@pytest.mark.xdist_group(name="keycloak_dockerfile")
class TestKeycloakRuntimeConfiguration:
    """Tests for runtime configuration in the final image."""

    def teardown_method(self) -> None:
        """Clean up after each test to prevent memory issues in xdist."""
        gc.collect()

    def test_uses_optimized_start_command_flag(self, keycloak_dockerfile_content: str) -> None:
        """
        Verify the final image uses --optimized flag.

        The --optimized flag tells Keycloak to skip runtime augmentation
        and use the pre-built artifacts.
        """
        assert "--optimized" in keycloak_dockerfile_content, (
            "Dockerfile should use 'start --optimized' to skip runtime augmentation. "
            "This is required for the pre-built image to work correctly."
        )

    def test_copies_quarkus_artifacts_to_runtime(self, keycloak_dockerfile_content: str) -> None:
        """
        Verify Dockerfile copies Quarkus build artifacts to runtime stage.

        The /opt/keycloak/lib/quarkus/ directory contains the pre-built artifacts.
        """
        assert "lib/quarkus" in keycloak_dockerfile_content, (
            "Dockerfile should copy /opt/keycloak/lib/quarkus/ from builder stage. "
            "This directory contains the pre-compiled Quarkus artifacts."
        )

    def test_sets_proper_entrypoint_to_kc_script(self, keycloak_dockerfile_content: str) -> None:
        """Verify Dockerfile sets kc.sh as entrypoint."""
        assert "ENTRYPOINT" in keycloak_dockerfile_content, "Dockerfile should set ENTRYPOINT to kc.sh"
        assert "kc.sh" in keycloak_dockerfile_content, "ENTRYPOINT should reference kc.sh"


@pytest.mark.xdist_group(name="keycloak_dockerfile")
class TestKeycloakSecurityBestPractices:
    """Tests for security best practices in the Dockerfile."""

    def teardown_method(self) -> None:
        """Clean up after each test to prevent memory issues in xdist."""
        gc.collect()

    def test_runs_as_non_root_user_in_final_image(self, keycloak_dockerfile_content: str) -> None:
        """
        Verify Dockerfile has explicit USER instruction for non-root.

        Trivy DS002 requires explicit USER instruction to pass security scans.
        Keycloak runs as UID 1000 by default.
        """
        lines = keycloak_dockerfile_content.split("\n")
        user_statements = [line.strip() for line in lines if line.strip().upper().startswith("USER ")]

        # Must have at least one USER statement (Trivy DS002 compliance)
        assert len(user_statements) >= 1, "Dockerfile must have explicit USER instruction for Trivy DS002 compliance"

        # The last USER statement should be non-root (1000 is Keycloak default)
        last_user = user_statements[-1]
        assert "1000" in last_user or "keycloak" in last_user.lower(), (
            f"Dockerfile should run as non-root user (UID 1000). Found: {last_user}"
        )

    def test_has_healthcheck_instruction(self, keycloak_dockerfile_content: str) -> None:
        """
        Verify Dockerfile has HEALTHCHECK instruction.

        Trivy DS026 recommends HEALTHCHECK for container orchestration.
        """
        assert "HEALTHCHECK" in keycloak_dockerfile_content.upper(), (
            "Dockerfile should have HEALTHCHECK instruction for container health monitoring. "
            "Use Keycloak's /health/ready endpoint."
        )

    def test_has_labels_for_image_traceability(self, keycloak_dockerfile_content: str) -> None:
        """Verify Dockerfile has OCI labels for image traceability."""
        assert "LABEL" in keycloak_dockerfile_content.upper(), "Dockerfile should have LABEL statements for OCI image metadata"


@pytest.mark.xdist_group(name="keycloak_dockerfile")
class TestKeycloakImageVersioning:
    """Tests for image version management."""

    def teardown_method(self) -> None:
        """Clean up after each test to prevent memory issues in xdist."""
        gc.collect()

    def test_uses_arg_for_configurable_version(self, keycloak_dockerfile_content: str) -> None:
        """
        Verify Dockerfile uses ARG for Keycloak version.

        This allows the version to be overridden at build time.
        """
        assert "ARG" in keycloak_dockerfile_content.upper(), (
            "Dockerfile should use ARG for configurable values like Keycloak version"
        )

    def test_version_matches_base_deployment_config(self, keycloak_dockerfile_content: str) -> None:
        """
        Verify Dockerfile version matches base deployment.

        The Dockerfile should use the same Keycloak version as specified
        in deployments/base/keycloak-deployment.yaml.
        """
        # Read the base deployment to get the expected version
        base_deployment_path = Path(__file__).parent.parent.parent / "deployments" / "base" / "keycloak-deployment.yaml"

        if base_deployment_path.exists():
            base_content = base_deployment_path.read_text()
            # Extract version from image tag (e.g., keycloak:26.4.2)
            import re

            match = re.search(r"keycloak:(\d+\.\d+\.\d+)", base_content)
            if match:
                expected_version = match.group(1)
                assert expected_version in keycloak_dockerfile_content, (
                    f"Dockerfile should use Keycloak version {expected_version} to match base deployment"
                )
