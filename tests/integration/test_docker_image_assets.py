"""
Integration tests for Docker test image asset exclusion (ADR-0053 compliance).

Validates that the Docker test image correctly EXCLUDES directories per ADR-0053:
- scripts/ directory must NOT be in Docker image
- deployments/ directory must NOT be in Docker image
- Meta-tests requiring these directories run on the host, not in containers

TDD: Updated to match ADR-0053 policy (meta-tests run on host).

ADR-0053: Docker Image Contents Policy
- Docker image contains: src/, tests/, pyproject.toml
- Docker image excludes: scripts/, deployments/
- Meta-tests requiring excluded directories run on host via @pytest.mark.skipif
"""

import gc
import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.tool_fixtures import requires_tool

pytestmark = pytest.mark.integration


@pytest.mark.xdist_group(name="testdockertestimageassets")
class TestDockerTestImageAssets:
    """Test that Docker test image contains all required assets."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture(scope="function")
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture(scope="function")
    def dockerfile_path(self, project_root):
        """
        Get Dockerfile path.

        Skips if running inside Docker (where docker/ directory isn't available).
        """
        dockerfile = project_root / "docker" / "Dockerfile"
        if not dockerfile.exists():
            pytest.skip(f"Dockerfile not found at {dockerfile} - likely running inside Docker container")
        return dockerfile

    @pytest.mark.integration
    @pytest.mark.skipif(
        os.getenv("TESTING") == "true", reason="Skipped inside Docker - Dockerfile not available in test image"
    )
    def test_dockerfile_excludes_deployments_directory(self, dockerfile_path):
        """
        Test that Dockerfile final-test stage EXCLUDES deployments/ directory per ADR-0053.

        ADR-0053 Policy: deployments/ should NOT be in Docker image.
        Meta-tests requiring deployments/ run on host, not in container.

        GREEN phase: Passes when deployments/ is NOT copied
        RED phase: Fails if deployments/ IS copied (violates ADR-0053)

        Validation: scripts/validate_docker_image_contents.py enforces this at pre-commit.
        """
        with open(dockerfile_path) as f:
            dockerfile_content = f.read()

        # Find the final-test stage
        assert "FROM runtime-slim AS final-test" in dockerfile_content, "Dockerfile must have 'final-test' stage"

        # Extract final-test stage content
        lines = dockerfile_content.split("\n")
        final_test_start = None
        final_test_end = None

        for i, line in enumerate(lines):
            if "FROM runtime-slim AS final-test" in line:
                final_test_start = i
            elif final_test_start is not None and line.strip().startswith("FROM "):
                final_test_end = i
                break

        if final_test_end is None:
            final_test_end = len(lines)

        final_test_stage = "\n".join(lines[final_test_start:final_test_end])

        # Check that deployments/ is NOT copied (ADR-0053 compliance)
        assert not any("COPY deployments/" in line for line in final_test_stage.split("\n")), (
            "❌ ADR-0053 VIOLATION: Dockerfile final-test stage must NOT copy deployments/ directory.\n\n"
            f"Current final-test stage:\n{final_test_stage}\n\n"
            "Per ADR-0053:\n"
            "  - deployments/ must NOT be in Docker image\n"
            "  - Meta-tests requiring deployments/ run on host, not in container\n"
            "  - Use @pytest.mark.skipif(os.getenv('TESTING') == 'true') for host-only tests\n\n"
            "Remove any COPY deployments/ command from final-test stage."
        )

    @pytest.mark.integration
    @pytest.mark.skipif(
        os.getenv("TESTING") == "true", reason="Skipped inside Docker - Dockerfile not available in test image"
    )
    def test_dockerfile_excludes_scripts_directory(self, dockerfile_path):
        """
        Test that Dockerfile final-test stage EXCLUDES scripts/ directory per ADR-0053.

        ADR-0053 Policy: scripts/ should NOT be in Docker image.
        Meta-tests requiring scripts/ run on host, not in container.

        GREEN phase: Passes when scripts/ is NOT copied
        RED phase: Fails if scripts/ IS copied (violates ADR-0053)

        Validation: scripts/validate_docker_image_contents.py enforces this at pre-commit.
        """
        with open(dockerfile_path) as f:
            dockerfile_content = f.read()

        # Find the final-test stage
        lines = dockerfile_content.split("\n")
        final_test_start = None
        final_test_end = None

        for i, line in enumerate(lines):
            if "FROM runtime-slim AS final-test" in line:
                final_test_start = i
            elif final_test_start is not None and line.strip().startswith("FROM "):
                final_test_end = i
                break

        if final_test_end is None:
            final_test_end = len(lines)

        final_test_stage = "\n".join(lines[final_test_start:final_test_end])

        # Check that scripts/ is NOT copied (ADR-0053 compliance)
        assert not any("COPY scripts/" in line for line in final_test_stage.split("\n")), (
            "❌ ADR-0053 VIOLATION: Dockerfile final-test stage must NOT copy scripts/ directory.\n\n"
            f"Current final-test stage:\n{final_test_stage}\n\n"
            "Per ADR-0053:\n"
            "  - scripts/ must NOT be in Docker image\n"
            "  - Meta-tests requiring scripts/ run on host, not in container\n"
            "  - Use @pytest.mark.skipif(os.getenv('TESTING') == 'true') for host-only tests\n\n"
            "Remove any COPY scripts/ command from final-test stage."
        )

    @pytest.mark.integration
    def test_pyproject_pythonpath_includes_scripts(self, project_root):
        """
        Test that pyproject.toml configures PYTHONPATH to include scripts/.

        This validates the configuration is correct (even though it is ineffective
        without the scripts/ directory being copied into the Docker image).
        """
        pyproject_path = project_root / "pyproject.toml"
        assert pyproject_path.exists(), f"pyproject.toml not found at {pyproject_path}"

        with open(pyproject_path) as f:
            pyproject_content = f.read()

        # Check for pythonpath configuration
        assert "pythonpath" in pyproject_content.lower(), "pyproject.toml should configure pythonpath for pytest"

        # Should include "scripts" in pythonpath
        # Pattern: pythonpath = [".", "scripts"]
        assert '"scripts"' in pyproject_content or "'scripts'" in pyproject_content, (
            "pyproject.toml pythonpath should include 'scripts' directory.\n\n"
            "Expected configuration:\n"
            "  [tool.pytest.ini_options]\n"
            '  pythonpath = [".", "scripts"]\n\n'
            "This allows tests to import from scripts/ directory."
        )

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skipif(os.getenv("PYTEST_XDIST_WORKER") is not None, reason="Docker build tests skipped in parallel mode")
    @pytest.mark.skipif(os.getenv("TESTING") == "true", reason="Skipped inside Docker - docker command not available")
    @requires_tool("docker")
    def test_docker_test_image_excludes_deployments_at_runtime(self, project_root):
        """
        Test that built Docker test image correctly EXCLUDES deployments/ at runtime (ADR-0053).

        This is an end-to-end test that builds the test image and verifies
        the directory does NOT exist inside the container.

        GREEN phase: Passes when deployments/ is NOT in Docker image (ADR-0053 compliant)
        RED phase: Fails if deployments/ IS in Docker image (violates ADR-0053)
        """
        dockerfile = project_root / "docker" / "Dockerfile"

        # Build only the final-test stage
        try:
            print("\nBuilding Docker test image (final-test stage)...")
            result = subprocess.run(
                [
                    "docker",
                    "build",
                    "-f",
                    str(dockerfile),
                    "--target",
                    "final-test",
                    "-t",
                    "mcp-server-langgraph:test-asset-check",
                    str(project_root),
                ],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout for build
            )

            assert result.returncode == 0, f"Docker build failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"

            # Run container and check that deployments/ does NOT exist (ADR-0053)
            print("Verifying deployments/ is excluded from container (ADR-0053)...")
            check_result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "mcp-server-langgraph:test-asset-check",
                    "ls",
                    "-la",
                    "/app/deployments",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # ADR-0053: deployments/ should NOT exist in Docker image
            assert check_result.returncode != 0, (
                "❌ ADR-0053 VIOLATION: /app/deployments/ directory FOUND in Docker test image!\n\n"
                f"Directory listing:\n{check_result.stdout}\n\n"
                "Per ADR-0053, deployments/ must NOT be in Docker image.\n"
                "Remove COPY deployments/ command from Dockerfile final-test stage."
            )

            print("✅ PASS: /app/deployments/ correctly excluded from Docker image (ADR-0053 compliant)")

        finally:
            # Cleanup: Remove test image
            subprocess.run(["docker", "rmi", "-f", "mcp-server-langgraph:test-asset-check"], capture_output=True, timeout=60)

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skipif(os.getenv("PYTEST_XDIST_WORKER") is not None, reason="Docker build tests skipped in parallel mode")
    @pytest.mark.skipif(os.getenv("TESTING") == "true", reason="Skipped inside Docker - docker command not available")
    @requires_tool("docker")
    def test_docker_test_image_excludes_scripts_at_runtime(self, project_root):
        """
        Test that built Docker test image correctly EXCLUDES scripts/ at runtime (ADR-0053).

        This is an end-to-end test that builds the test image and verifies
        the directory does NOT exist inside the container.

        GREEN phase: Passes when scripts/ is NOT in Docker image (ADR-0053 compliant)
        RED phase: Fails if scripts/ IS in Docker image (violates ADR-0053)
        """
        dockerfile = project_root / "docker" / "Dockerfile"

        # Build only the final-test stage
        try:
            print("\nBuilding Docker test image (final-test stage)...")
            result = subprocess.run(
                [
                    "docker",
                    "build",
                    "-f",
                    str(dockerfile),
                    "--target",
                    "final-test",
                    "-t",
                    "mcp-server-langgraph:test-asset-check-scripts",
                    str(project_root),
                ],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout for build
            )

            assert result.returncode == 0, f"Docker build failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"

            # Run container and check that scripts/ does NOT exist (ADR-0053)
            print("Verifying scripts/ is excluded from container (ADR-0053)...")
            check_result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "mcp-server-langgraph:test-asset-check-scripts",
                    "ls",
                    "-la",
                    "/app/scripts",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # ADR-0053: scripts/ should NOT exist in Docker image
            assert check_result.returncode != 0, (
                "❌ ADR-0053 VIOLATION: /app/scripts/ directory FOUND in Docker test image!\n\n"
                f"Directory listing:\n{check_result.stdout}\n\n"
                "Per ADR-0053, scripts/ must NOT be in Docker image.\n"
                "Meta-tests requiring scripts/ run on host, not in container.\n"
                "Remove COPY scripts/ command from Dockerfile final-test stage."
            )

            print("✅ PASS: /app/scripts/ correctly excluded from Docker image (ADR-0053 compliant)")

        finally:
            # Cleanup: Remove test image
            subprocess.run(
                ["docker", "rmi", "-f", "mcp-server-langgraph:test-asset-check-scripts"], capture_output=True, timeout=60
            )
