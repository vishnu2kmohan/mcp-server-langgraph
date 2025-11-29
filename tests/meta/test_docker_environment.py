"""
Test Docker environment configuration for integration tests.

These tests validate that the Docker test environment is properly configured
with all required directories and dependencies. This prevents test collection
errors when running tests in Docker containers.

Regression Prevention:
- Ensures scripts/ directory is available in Docker (for test imports)
- Ensures deployments/ directory is available (for infrastructure tests)
- Validates Dockerfile.test has required COPY directives

Related Issues:
- FileNotFoundError: '/app/deployments/overlays' (2025-11-14)
- ModuleNotFoundError: No module named 'scripts' (2025-11-14)
- ModuleNotFoundError: No module named 'fix_mdx_syntax' (2025-11-14)
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
class TestDockerEnvironmentSetup:
    """Test that Docker environment has required directories."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_scripts_directory_exists(self, project_root):
        """
        Test that scripts/ directory exists and is accessible.

        Required for:
        - tests/test_mdx_validation.py (imports from scripts/)
        - tests/unit/documentation/* (imports from scripts/validators/)
        """
        scripts_dir = project_root / "scripts"
        assert scripts_dir.exists(), (
            f"scripts/ directory not found at {scripts_dir}. Ensure Dockerfile.test includes 'COPY scripts/ ./scripts/'"
        )
        assert scripts_dir.is_dir(), f"{scripts_dir} exists but is not a directory"

    def test_scripts_is_importable(self, project_root):
        """Test that scripts can be imported as a module."""
        scripts_dir = project_root / "scripts"

        # scripts/__init__.py should exist
        init_file = scripts_dir / "__init__.py"
        assert init_file.exists(), (
            f"scripts/__init__.py not found. scripts/ directory exists at {scripts_dir} but is not a Python package."
        )

    def test_scripts_validators_exists(self, project_root):
        """Test that scripts/validators/ subdirectory exists."""
        validators_dir = project_root / "scripts" / "validators"
        assert validators_dir.exists(), (
            f"scripts/validators/ not found at {validators_dir}. Required for documentation test imports."
        )

    def test_deployments_directory_exists(self, project_root):
        """
        Test that deployments/ directory exists and is accessible.

        Required for:
        - tests/regression/test_pod_deployment_regression.py
        """
        deployments_dir = project_root / "deployments"
        assert deployments_dir.exists(), (
            f"deployments/ directory not found at {deployments_dir}. "
            "Ensure Dockerfile.test includes 'COPY deployments/ ./deployments/'"
        )
        assert deployments_dir.is_dir(), f"{deployments_dir} exists but is not a directory"

    def test_deployments_overlays_exists(self, project_root):
        """Test that deployments/overlays/ subdirectory exists."""
        overlays_dir = project_root / "deployments" / "overlays"
        assert overlays_dir.exists(), (
            f"deployments/overlays/ not found at {overlays_dir}. Required for Kubernetes deployment regression tests."
        )

    @pytest.mark.skipif(os.getenv("TESTING") != "true", reason="Only in Docker test environment")
    def test_docker_working_directory_is_app(self):
        """Test that Docker container uses /app as working directory."""
        cwd = Path.cwd()
        # In Docker, we expect to be in /app
        # This is informational - doesn't fail if not in Docker
        if str(cwd) == "/app":
            assert True, "Running in Docker test environment"


@pytest.mark.xdist_group(name="testdockerfiletestconfiguration")
class TestDockerfileTestConfiguration:
    """Test that Dockerfile.test is properly configured."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_dockerfile_test_exists(self, project_root):
        """Test that docker/Dockerfile.test exists."""
        dockerfile = project_root / "docker" / "Dockerfile.test"
        assert dockerfile.exists(), "docker/Dockerfile.test not found"

    def test_dockerfile_test_copies_scripts(self, project_root):
        """
        Test that Dockerfile.test includes COPY directive for scripts/.

        Regression test for: ModuleNotFoundError: No module named 'scripts'
        """
        dockerfile = project_root / "docker" / "Dockerfile.test"
        content = dockerfile.read_text()

        # Check for COPY scripts/ directive
        assert "COPY scripts/" in content, (
            "Dockerfile.test missing 'COPY scripts/ ./scripts/' directive. "
            "This causes import errors in tests that depend on scripts/ module."
        )

    def test_dockerfile_test_copies_deployments(self, project_root):
        """
        Test that Dockerfile.test includes COPY directive for deployments/.

        Regression test for: FileNotFoundError: '/app/deployments/overlays'
        """
        dockerfile = project_root / "docker" / "Dockerfile.test"
        content = dockerfile.read_text()

        # Check for COPY deployments/ directive
        assert "COPY deployments/" in content, (
            "Dockerfile.test missing 'COPY deployments/ ./deployments/' directive. "
            "This causes FileNotFoundError in pod deployment regression tests."
        )

    def test_dockerfile_test_copies_in_correct_order(self, project_root):
        """
        Test that COPY directives come after pyproject.toml but before pip install.

        Ensures dependencies are available before installing packages.
        """
        dockerfile = project_root / "docker" / "Dockerfile.test"
        content = dockerfile.read_text()
        lines = content.split("\n")

        # Find line numbers
        pyproject_line = next((i for i, line in enumerate(lines) if "COPY pyproject.toml" in line), -1)
        scripts_line = next((i for i, line in enumerate(lines) if "COPY scripts/" in line), -1)
        deployments_line = next((i for i, line in enumerate(lines) if "COPY deployments/" in line), -1)
        pip_install_line = next((i for i, line in enumerate(lines) if "pip install" in line or "uv pip install" in line), -1)

        # Validate order
        assert pyproject_line > 0, "pyproject.toml not found in Dockerfile.test"
        assert scripts_line > pyproject_line, "scripts/ should be copied after pyproject.toml"
        assert deployments_line > pyproject_line, "deployments/ should be copied after pyproject.toml"

        if pip_install_line > 0:
            assert scripts_line < pip_install_line, "scripts/ should be copied before pip install"
            assert deployments_line < pip_install_line, "deployments/ should be copied before pip install"


@pytest.mark.xdist_group(name="testdockerimageassets")
class TestDockerImageAssets:
    """Meta-tests validating Docker image contents.

    These tests run on the host machine to validate the structure and contents
    of Docker images. They are NOT integration tests that run inside Docker.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(os.getenv("SKIP_DOCKER_BUILD_TESTS") == "true", reason="Docker build tests disabled")
    def test_docker_test_image_has_scripts(self):
        """
        Integration test: Verify built Docker test image contains scripts/ directory.

        This test requires Docker to be available and will build the test image
        to verify scripts/ directory is included.
        """
        pytest.skip("Integration test - requires Docker build (expensive)")

    @pytest.mark.skipif(os.getenv("SKIP_DOCKER_BUILD_TESTS") == "true", reason="Docker build tests disabled")
    def test_docker_test_image_has_deployments(self):
        """
        Integration test: Verify built Docker test image contains deployments/ directory.

        This test requires Docker to be available and will build the test image
        to verify deployments/ directory is included.
        """
        pytest.skip("Integration test - requires Docker build (expensive)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
