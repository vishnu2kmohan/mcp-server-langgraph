"""
Meta-test: Validate Docker Image Contents

This test ensures that critical files and directories are copied into the Docker
image, preventing test failures when containerized tests can't access required files.

Related: OpenAI Codex Finding 2025-11-15 - ADR documentation test failed because
adr/ directory was not copied to the Docker test image.

NOTE: Per ADR-0053, scripts/ and deployments/ are NOT copied to Docker images.
Meta-tests requiring those directories run on the host, not in containers.
"""

import gc
from pathlib import Path

import pytest

pytestmark = pytest.mark.meta


@pytest.mark.xdist_group(name="docker_image_contents")
class TestDockerImageContents:
    """Meta-test validating Docker image contains required files and directories.

    This test runs on the host machine to validate that the repository structure
    matches what Docker images expect. It validates the source files exist in
    the repository, which are then copied into Docker images during build.

    NOTE: This test validates the repository structure, not the actual Docker
    image contents. The Dockerfile COPY commands determine what goes into images.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_adr_directory_exists(self):
        """
        Verify adr/ directory is present for Docker image builds.

        This prevents regression where the test-mcp-startup-validation test failed
        because ADR-0042 was not accessible in the container.

        References:
        - docker/Dockerfile:267 (COPY adr/ ./adr/)
        - tests/integration/test_mcp_startup_validation.py:283-284
        - adr/adr-0042-dependency-injection-configuration-fixes.md
        """
        adr_dir = Path("adr")
        assert adr_dir.exists(), (
            "adr/ directory must exist for Docker image builds. See docker/Dockerfile for COPY adr/ ./adr/"
        )
        assert adr_dir.is_dir(), "adr/ must be a directory"

    def test_adr_0042_exists(self):
        """
        Verify specific ADR file that tests depend on exists.

        ADR-0042 documents dependency injection configuration fixes and is
        referenced by production readiness tests.
        """
        adr_file = Path("adr/adr-0042-dependency-injection-configuration-fixes.md")
        assert adr_file.exists(), f"ADR file {adr_file} must exist. This file is referenced by production readiness tests."
        assert adr_file.is_file(), f"{adr_file} must be a regular file"

    def test_src_directory_exists(self):
        """Verify src/ directory with application code is present"""
        src_dir = Path("src")
        assert src_dir.exists(), "src/ directory must exist for Docker image builds"
        assert src_dir.is_dir(), "src/ must be a directory"

        # Verify main package is present
        main_package = src_dir / "mcp_server_langgraph"
        assert main_package.exists(), "Main package must exist"
        assert main_package.is_dir(), "Main package must be a directory"

    def test_tests_directory_exists(self):
        """Verify tests/ directory is present for running tests in container"""
        tests_dir = Path("tests")
        assert tests_dir.exists(), "tests/ directory must exist for Docker image builds"
        assert tests_dir.is_dir(), "tests/ must be a directory"

    def test_pyproject_toml_exists(self):
        """Verify pyproject.toml is present for package metadata and config"""
        pyproject = Path("pyproject.toml")
        assert pyproject.exists(), "pyproject.toml must exist for Docker image builds"
        assert pyproject.is_file(), "pyproject.toml must be a regular file"

    def test_alembic_directory_exists(self):
        """Verify alembic/ directory is present for database migrations"""
        alembic_dir = Path("alembic")
        assert alembic_dir.exists(), (
            "alembic/ directory must exist for Docker image builds. Required by alembic-migrate-test service."
        )
        assert alembic_dir.is_dir(), "alembic/ must be a directory"

    def test_alembic_ini_exists(self):
        """Verify alembic.ini is present for migration configuration"""
        alembic_ini = Path("alembic.ini")
        assert alembic_ini.exists(), (
            "alembic.ini must exist for Docker image builds. Required by alembic-migrate-test service."
        )
        assert alembic_ini.is_file(), "alembic.ini must be a regular file"

    @pytest.mark.meta
    def test_critical_docker_files_documented(self):
        """
        Document which files/directories MUST be in Docker images.

        This serves as a checklist for future Dockerfile updates.

        NOTE: Per ADR-0053, scripts/ and deployments/ are NOT copied to Docker
        images. Meta-tests requiring those directories run on the host.
        """
        # Files that ARE copied to Docker images
        docker_image_paths = {
            "src/": "Application source code",
            "tests/": "Test suite (test variant only)",
            "pyproject.toml": "Package configuration",
            "adr/": "Architecture Decision Records (main Dockerfile only)",
            "alembic/": "Database migrations",
            "alembic.ini": "Alembic configuration",
        }

        # Files that exist in repo but are NOT copied to Docker images (per ADR-0053)
        host_only_paths = {
            "scripts/": "Utility scripts (run on host, not in Docker)",
            "deployments/": "K8s manifests (run on host, not in Docker)",
        }

        print("\n=== Files COPIED to Docker images ===")
        for path, description in docker_image_paths.items():
            status = "✓" if Path(path).exists() else "✗"
            print(f"{status} {path}: {description}")

        print("\n=== Files NOT copied to Docker (per ADR-0053) ===")
        for path, description in host_only_paths.items():
            status = "✓" if Path(path).exists() else "✗"
            print(f"{status} {path}: {description}")
