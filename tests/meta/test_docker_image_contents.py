"""
Meta-test: Validate Docker Image Contents

This test ensures that critical files and directories are copied into the Docker
image, preventing test failures when containerized tests can't access required files.

Related: OpenAI Codex Finding 2025-11-15 - ADR documentation test failed because
adr/ directory was not copied to the Docker test image.
"""

from pathlib import Path

import pytest


@pytest.mark.integration
class TestDockerImageContents:
    """Validate Docker image contains required files and directories"""

    def test_adr_directory_exists(self):
        """
        Verify adr/ directory is present in the Docker image.

        This prevents regression where the test-mcp-startup-validation test failed
        because ADR-0042 was not accessible in the container.

        References:
        - docker/Dockerfile:264 (COPY adr/ ./adr/)
        - tests/integration/test_mcp_startup_validation.py:283-284
        - adr/adr-0042-dependency-injection-configuration-fixes.md
        """
        adr_dir = Path("adr")
        assert adr_dir.exists(), (
            "adr/ directory must be copied to Docker image. " "Update docker/Dockerfile to include: COPY adr/ ./adr/"
        )
        assert adr_dir.is_dir(), "adr/ must be a directory"

    def test_adr_0042_exists(self):
        """
        Verify specific ADR file that tests depend on exists.

        ADR-0042 documents dependency injection configuration fixes and is
        referenced by production readiness tests.
        """
        adr_file = Path("adr/adr-0042-dependency-injection-configuration-fixes.md")
        assert adr_file.exists(), (
            f"ADR file {adr_file} must exist in Docker image. " "Ensure adr/ directory is copied in Dockerfile."
        )
        assert adr_file.is_file(), f"{adr_file} must be a regular file"

    def test_scripts_directory_exists(self):
        """
        Verify scripts/ directory is present for test utilities.

        Scripts are used for OpenFGA setup, validation, and other test infrastructure.
        """
        scripts_dir = Path("scripts")
        assert scripts_dir.exists(), "scripts/ directory must be copied to Docker image. " "Check docker/Dockerfile:263"
        assert scripts_dir.is_dir(), "scripts/ must be a directory"

    def test_deployments_directory_exists(self):
        """
        Verify deployments/ directory is present for deployment validation tests.

        Deployment tests validate Kubernetes manifests, Helm charts, etc.
        """
        deployments_dir = Path("deployments")
        assert deployments_dir.exists(), (
            "deployments/ directory must be copied to Docker image. " "Check docker/Dockerfile:262"
        )
        assert deployments_dir.is_dir(), "deployments/ must be a directory"

    def test_src_directory_exists(self):
        """Verify src/ directory with application code is present"""
        src_dir = Path("src")
        assert src_dir.exists(), "src/ directory must exist in Docker image"
        assert src_dir.is_dir(), "src/ must be a directory"

        # Verify main package is present
        main_package = src_dir / "mcp_server_langgraph"
        assert main_package.exists(), "Main package must exist"
        assert main_package.is_dir(), "Main package must be a directory"

    def test_tests_directory_exists(self):
        """Verify tests/ directory is present for running tests in container"""
        tests_dir = Path("tests")
        assert tests_dir.exists(), "tests/ directory must exist in Docker image"
        assert tests_dir.is_dir(), "tests/ must be a directory"

    def test_pyproject_toml_exists(self):
        """Verify pyproject.toml is present for package metadata and config"""
        pyproject = Path("pyproject.toml")
        assert pyproject.exists(), "pyproject.toml must exist in Docker image"
        assert pyproject.is_file(), "pyproject.toml must be a regular file"

    @pytest.mark.unit
    def test_critical_files_documented(self):
        """
        Document which files/directories MUST be in the Docker image.

        This serves as a checklist for future Dockerfile updates.
        """
        critical_paths = {
            "src/": "Application source code",
            "tests/": "Test suite",
            "pyproject.toml": "Package configuration",
            "adr/": "Architecture Decision Records (required by production readiness tests)",
            "scripts/": "Utility scripts (OpenFGA setup, validation, etc.)",
            "deployments/": "Kubernetes/Helm manifests (required by deployment tests)",
        }

        # This test always passes - it's documentation
        # If a path is missing, other tests will fail with helpful messages
        for path, description in critical_paths.items():
            if Path(path).exists():
                print(f"✓ {path}: {description}")
            else:
                print(f"✗ {path}: {description} [MISSING]")
