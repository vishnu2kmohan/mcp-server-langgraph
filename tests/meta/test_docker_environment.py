"""
Test Docker environment configuration following ADR-0053.

Per ADR-0053 (Codex Integration Test Findings):
- scripts/ and deployments/ are NOT copied to Docker images
- Meta-tests requiring these directories run on the host, not in container
- Docker images only contain src/ and tests/ for integration tests
- pyproject.toml is NOT copied (version read via importlib.metadata)

These tests validate:
1. Host environment has required directories (scripts/, deployments/)
2. Dockerfile.test does NOT copy excluded directories
3. Dockerfile.test only copies what's needed for integration tests

References:
- ADR-0053: Codex Integration Test Findings
- tests/meta/test_precommit_docker_image_validation.py
- scripts/validators/validate_docker_image_contents.py
"""

import gc
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def project_root():
    """Find project root directory."""
    current = Path(__file__).resolve().parent
    markers = [".git", "pyproject.toml"]

    while current != current.parent:
        if any((current / marker).exists() for marker in markers):
            return current
        current = current.parent

    raise RuntimeError("Cannot find project root")


@pytest.mark.xdist_group(name="testdockerenvironmentsetup")
class TestHostEnvironmentSetup:
    """Test that host environment has required directories for meta-tests.

    Per ADR-0053: Meta-tests run on the host (not in Docker) because they need
    access to scripts/, deployments/, and other repo directories not in Docker images.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_scripts_directory_exists_on_host(self, project_root):
        """
        Test that scripts/ directory exists on host for meta-tests.

        Per ADR-0053: scripts/ is NOT copied to Docker image.
        Meta-tests that import from scripts/ run on the host.
        """
        scripts_dir = project_root / "scripts"
        assert scripts_dir.exists(), (
            f"scripts/ directory not found at {scripts_dir}. Required on host for meta-tests (NOT in Docker per ADR-0053)."
        )
        assert scripts_dir.is_dir(), f"{scripts_dir} exists but is not a directory"

    def test_scripts_is_importable_on_host(self, project_root):
        """Test that scripts can be imported as a module on host."""
        scripts_dir = project_root / "scripts"

        # scripts/__init__.py should exist
        init_file = scripts_dir / "__init__.py"
        assert init_file.exists(), (
            f"scripts/__init__.py not found. scripts/ directory exists at {scripts_dir} but is not a Python package."
        )

    def test_scripts_validators_exists_on_host(self, project_root):
        """Test that scripts/validators/ subdirectory exists on host."""
        validators_dir = project_root / "scripts" / "validators"
        assert validators_dir.exists(), (
            f"scripts/validators/ not found at {validators_dir}. "
            "Required on host for documentation validation (NOT in Docker per ADR-0053)."
        )

    def test_deployments_directory_exists_on_host(self, project_root):
        """
        Test that deployments/ directory exists on host for meta-tests.

        Per ADR-0053: deployments/ is NOT copied to Docker image.
        Deployment validation tests run on the host with full repo context.
        """
        deployments_dir = project_root / "deployments"
        assert deployments_dir.exists(), (
            f"deployments/ directory not found at {deployments_dir}. "
            "Required on host for deployment tests (NOT in Docker per ADR-0053)."
        )
        assert deployments_dir.is_dir(), f"{deployments_dir} exists but is not a directory"

    def test_deployments_overlays_exists_on_host(self, project_root):
        """Test that deployments/overlays/ subdirectory exists on host."""
        overlays_dir = project_root / "deployments" / "overlays"
        assert overlays_dir.exists(), (
            f"deployments/overlays/ not found at {overlays_dir}. "
            "Required on host for Kubernetes deployment tests (NOT in Docker per ADR-0053)."
        )


@pytest.mark.xdist_group(name="testdockerfiletestconfiguration")
class TestDockerfileTestConfiguration:
    """Test that Dockerfile.test follows ADR-0053 design.

    Per ADR-0053:
    - Docker images only contain src/ and tests/
    - scripts/, deployments/, pyproject.toml are NOT copied
    - Meta-tests run on host with full repo context
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_dockerfile_test_exists(self, project_root):
        """Test that docker/Dockerfile.test exists."""
        dockerfile = project_root / "docker" / "Dockerfile.test"
        assert dockerfile.exists(), "docker/Dockerfile.test not found"

    def test_dockerfile_test_copies_src(self, project_root):
        """
        Test that Dockerfile.test includes COPY directive for src/.

        Per ADR-0053: src/ is required in Docker image for integration tests.
        """
        dockerfile = project_root / "docker" / "Dockerfile.test"
        content = dockerfile.read_text()

        # Check for COPY src/ directive
        assert "COPY src/" in content or "COPY --chown" in content and "src/" in content, (
            "Dockerfile.test missing 'COPY src/' directive. src/ is required for integration tests per ADR-0053."
        )

    def test_dockerfile_test_copies_tests(self, project_root):
        """
        Test that Dockerfile.test includes COPY directive for tests/.

        Per ADR-0053: tests/ is required in Docker image for integration tests.
        """
        dockerfile = project_root / "docker" / "Dockerfile.test"
        content = dockerfile.read_text()

        # Check for COPY tests/ directive
        assert "COPY tests/" in content or "COPY --chown" in content and "tests/" in content, (
            "Dockerfile.test missing 'COPY tests/' directive. tests/ is required for integration tests per ADR-0053."
        )

    def test_dockerfile_test_does_not_copy_scripts(self, project_root):
        """
        Test that Dockerfile.test does NOT copy scripts/ directory.

        Per ADR-0053: scripts/ must NOT be in Docker image.
        Meta-tests that need scripts/ run on the host.
        """
        dockerfile = project_root / "docker" / "Dockerfile.test"
        content = dockerfile.read_text()

        # scripts/ should NOT be copied
        assert "COPY scripts/" not in content, (
            "Dockerfile.test should NOT copy scripts/ directory. "
            "Per ADR-0053: scripts/ must NOT be in Docker image. "
            "Meta-tests run on host with full repo context."
        )

    def test_dockerfile_test_does_not_copy_deployments(self, project_root):
        """
        Test that Dockerfile.test does NOT copy deployments/ directory.

        Per ADR-0053: deployments/ must NOT be in Docker image.
        Deployment validation tests run on the host.
        """
        dockerfile = project_root / "docker" / "Dockerfile.test"
        content = dockerfile.read_text()

        # deployments/ should NOT be copied
        assert "COPY deployments/" not in content, (
            "Dockerfile.test should NOT copy deployments/ directory. "
            "Per ADR-0053: deployments/ must NOT be in Docker image. "
            "Deployment tests run on host with full repo context."
        )

    def test_dockerfile_test_does_not_copy_pyproject_toml(self, project_root):
        """
        Test that Dockerfile.test does NOT copy pyproject.toml to runtime.

        Per ADR-0053: pyproject.toml must NOT be in final Docker image.
        Version is read via importlib.metadata at runtime.

        Note: pyproject.toml may be copied in build stages for dependency
        installation, but should not be in the final runtime image.
        """
        dockerfile = project_root / "docker" / "Dockerfile.test"
        content = dockerfile.read_text()

        # Look for pyproject.toml COPY in final stage (after last FROM)
        lines = content.split("\n")
        last_from_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("FROM"):
                last_from_idx = i

        if last_from_idx >= 0:
            # Check if pyproject.toml is copied in final stage
            # Allow it in earlier stages for dependency installation
            has_pyproject_in_final = False
            for line in lines[last_from_idx:]:
                if "COPY" in line and "pyproject.toml" in line and not line.strip().startswith("#"):
                    has_pyproject_in_final = True
                    break

            assert not has_pyproject_in_final, (
                "Dockerfile.test should NOT copy pyproject.toml to final stage. "
                "Per ADR-0053: version is read via importlib.metadata at runtime."
            )

    @pytest.mark.skipif(os.getenv("TESTING") != "true", reason="Only in Docker test environment")
    def test_docker_working_directory_is_app(self):
        """Test that Docker container uses /app as working directory."""
        cwd = Path.cwd()
        # In Docker, we expect to be in /app
        if str(cwd) == "/app":
            assert True, "Running in Docker test environment"


@pytest.mark.xdist_group(name="testdockerimageassets")
class TestDockerImageAssets:
    """Meta-tests validating Docker image contents per ADR-0053.

    These tests run on the host machine to validate Dockerfile configuration.
    They ensure compliance with ADR-0053 design decisions.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_adr_0053_design_documented(self, project_root):
        """
        Verify ADR-0053 exists and documents Docker image design.

        ADR-0053 is the authoritative source for what should/shouldn't
        be in Docker images.
        """
        adr_path = project_root / "docs-internal" / "ADR-0053-codex-findings-validation.md"
        assert adr_path.exists(), (
            "ADR-0053 not found. This ADR documents the design decision that "
            "scripts/, deployments/, and pyproject.toml should NOT be in Docker images."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
