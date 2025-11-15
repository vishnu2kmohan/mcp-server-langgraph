"""
Integration tests for Docker test image asset completeness.

Validates that the Docker test image contains all required directories
and files needed for tests to run successfully.

TDD: Written BEFORE fixing Docker image (RED phase).

Codex Findings:
- docker/Dockerfile:257-259 - Test image missing deployments/ directory
- docker/Dockerfile:257-259 - Test image missing scripts/ directory
- Import failures in test_pod_deployment_regression.py:28
- Import failures in test_mdx_validation.py:18
- Import failures in test_codeblock_autofixer.py:15
"""

import gc
import os
import subprocess
from pathlib import Path

import pytest


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
    def test_dockerfile_copies_deployments_directory(self, dockerfile_path):
        """
        Test that Dockerfile final-test stage copies deployments/ directory.

        RED phase: Will fail if deployments/ is NOT copied
        GREEN phase: Will pass after adding COPY deployments/ ./deployments/

        Codex Finding: test_pod_deployment_regression.py:28 fails because
        it expects /app/deployments/overlays/ but directory is not copied.
        """
        with open(dockerfile_path, "r") as f:
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

        # Check that deployments/ is copied
        assert any("COPY deployments/" in line for line in final_test_stage.split("\n")), (
            "RED: Dockerfile final-test stage must copy deployments/ directory.\n\n"
            f"Current final-test stage:\n{final_test_stage}\n\n"
            "Required: COPY deployments/ ./deployments/\n\n"
            "Why: test_pod_deployment_regression.py:28 expects:\n"
            "  OVERLAYS_DIR = REPO_ROOT / 'deployments' / 'overlays'\n"
            "Without this copy, tests will fail with:\n"
            "  FileNotFoundError: [Errno 2] No such file or directory: '/app/deployments/overlays'"
        )

    @pytest.mark.integration
    @pytest.mark.skipif(
        os.getenv("TESTING") == "true", reason="Skipped inside Docker - Dockerfile not available in test image"
    )
    def test_dockerfile_copies_scripts_directory(self, dockerfile_path):
        """
        Test that Dockerfile final-test stage copies scripts/ directory.

        RED phase: Will fail if scripts/ is NOT copied
        GREEN phase: Will pass after adding COPY scripts/ ./scripts/

        Codex Findings:
        - test_mdx_validation.py:18 imports from scripts.fix_mdx_syntax
        - test_codeblock_autofixer.py:15 imports from scripts.validators.codeblock_autofixer
        """
        with open(dockerfile_path, "r") as f:
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

        # Check that scripts/ is copied
        assert any("COPY scripts/" in line for line in final_test_stage.split("\n")), (
            "RED: Dockerfile final-test stage must copy scripts/ directory.\n\n"
            f"Current final-test stage:\n{final_test_stage}\n\n"
            "Required: COPY scripts/ ./scripts/\n\n"
            "Why: Multiple tests import from scripts/:\n"
            "  - test_mdx_validation.py:18 -> from fix_mdx_syntax import ...\n"
            "  - test_codeblock_autofixer.py:15 -> from scripts.validators.codeblock_autofixer import ...\n"
            "Without this copy, tests will fail with:\n"
            "  ModuleNotFoundError: No module named 'scripts' or 'fix_mdx_syntax'"
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

        with open(pyproject_path, "r") as f:
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
    def test_docker_test_image_contains_deployments_at_runtime(self, project_root):
        """
        Test that built Docker test image actually contains deployments/ at runtime.

        This is an end-to-end test that builds the test image and verifies
        the directory exists inside the container.

        RED phase: Will fail if deployments/ is not copied
        GREEN phase: Will pass after fixing Dockerfile
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

            assert result.returncode == 0, f"Docker build failed:\n" f"stdout: {result.stdout}\n" f"stderr: {result.stderr}"

            # Run container and check if deployments/ exists
            print("Checking if deployments/ exists in container...")
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

            assert check_result.returncode == 0, (
                "RED: /app/deployments/ directory NOT found in Docker test image.\n\n"
                f"Error output:\n{check_result.stderr}\n\n"
                "This means the Dockerfile is not copying deployments/ directory.\n"
                "Add to final-test stage: COPY deployments/ ./deployments/"
            )

            print(f"PASS: /app/deployments/ exists in Docker image:\n{check_result.stdout}")

        finally:
            # Cleanup: Remove test image
            subprocess.run(
                ["docker", "rmi", "-f", "mcp-server-langgraph:test-asset-check"],
                capture_output=True,
            )

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skipif(os.getenv("PYTEST_XDIST_WORKER") is not None, reason="Docker build tests skipped in parallel mode")
    @pytest.mark.skipif(os.getenv("TESTING") == "true", reason="Skipped inside Docker - docker command not available")
    def test_docker_test_image_contains_scripts_at_runtime(self, project_root):
        """
        Test that built Docker test image actually contains scripts/ at runtime.

        This is an end-to-end test that builds the test image and verifies
        the directory exists inside the container.

        RED phase: Will fail if scripts/ is not copied
        GREEN phase: Will pass after fixing Dockerfile
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

            assert result.returncode == 0, f"Docker build failed:\n" f"stdout: {result.stdout}\n" f"stderr: {result.stderr}"

            # Run container and check if scripts/ exists and contains expected files
            print("Checking if scripts/ exists in container...")
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

            assert check_result.returncode == 0, (
                "RED: /app/scripts/ directory NOT found in Docker test image.\n\n"
                f"Error output:\n{check_result.stderr}\n\n"
                "This means the Dockerfile is not copying scripts/ directory.\n"
                "Add to final-test stage: COPY scripts/ ./scripts/"
            )

            # Verify specific files needed by tests exist
            required_files = [
                "/app/scripts/fix_mdx_syntax.py",
                "/app/scripts/validators/codeblock_autofixer.py",
            ]

            for file_path in required_files:
                file_check = subprocess.run(
                    [
                        "docker",
                        "run",
                        "--rm",
                        "mcp-server-langgraph:test-asset-check-scripts",
                        "test",
                        "-f",
                        file_path,
                    ],
                    capture_output=True,
                    timeout=10,
                )

                assert file_check.returncode == 0, (
                    f"RED: Required file {file_path} NOT found in Docker image.\n"
                    "This file is imported by tests and must be present."
                )

            print(f"PASS: /app/scripts/ exists in Docker image:\n{check_result.stdout}")

        finally:
            # Cleanup: Remove test image
            subprocess.run(
                ["docker", "rmi", "-f", "mcp-server-langgraph:test-asset-check-scripts"],
                capture_output=True,
            )
