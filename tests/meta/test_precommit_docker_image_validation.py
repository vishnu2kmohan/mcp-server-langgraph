"""
Meta-tests for pre-commit hook: validate-docker-image-contents

Tests ensure the Docker image validation hook works correctly
and prevents regression of Codex findings related to Docker image contents.

TDD Cycle: RED → GREEN → REFACTOR

Reference: ADR-0053 Future Work - Pre-commit hook: validate-docker-image-contents
"""

import gc
import subprocess
import tempfile
from pathlib import Path

import pytest

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testdockerimagevalidationhook")
class TestDockerImageValidationHook:
    """Test suite for validate_docker_image_contents.py pre-commit hook"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_hook_script_exists(self):
        """
        Validate that the validation script exists.

        GIVEN: The scripts directory
        WHEN: Checking for validate_docker_image_contents.py
        THEN: The script should exist and be executable
        """
        script_path = Path(__file__).parent.parent.parent / "scripts" / "validators" / "validate_docker_image_contents.py"
        assert script_path.exists(), f"Hook script not found: {script_path}"
        assert script_path.is_file(), "Hook script must be a file"

    def test_hook_validates_required_directories_copied(self):
        """
        Validate hook passes when required directories are copied.

        GIVEN: A Dockerfile with required COPY commands for src/, tests/, pyproject.toml
        WHEN: Running the validation hook
        THEN: Hook should exit with code 0 (success)
        """
        # Create temp Dockerfile with correct COPY statements
        dockerfile_content = """
# Multi-stage Dockerfile

FROM python:3.12-slim AS runtime-slim
# ... other commands ...

FROM runtime-slim AS final-test
WORKDIR /app

# Required COPY commands (correct design)
COPY src/ ./src/
COPY tests/ ./tests/
COPY pyproject.toml ./

# Integration tests only need src/, tests/, pyproject.toml
# Meta-tests and deployment tests run on host with full repo

CMD ["pytest", "-m", "integration"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".dockerfile", delete=False) as f:
            f.write(dockerfile_content)
            temp_file = Path(f.name)

        try:
            # Run validation script
            result = subprocess.run(
                ["python", "scripts/validators/validate_docker_image_contents.py", str(temp_file)],
                capture_output=True,
                text=True,
                timeout=60,
            )

            assert result.returncode == 0, f"Hook should pass with required directories. stderr: {result.stderr}"
        finally:
            temp_file.unlink()

    def test_hook_fails_when_src_directory_missing(self):
        """
        Validate hook fails when src/ directory is not copied.

        GIVEN: A Dockerfile missing COPY src/ command
        WHEN: Running the validation hook
        THEN: Hook should exit with code 1 (failure)
        """
        dockerfile_content = """
FROM python:3.12-slim AS final-test
WORKDIR /app

# Missing: COPY src/ ./src/
COPY tests/ ./tests/
COPY pyproject.toml ./

CMD ["pytest"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".dockerfile", delete=False) as f:
            f.write(dockerfile_content)
            temp_file = Path(f.name)

        try:
            result = subprocess.run(
                ["python", "scripts/validators/validate_docker_image_contents.py", str(temp_file)],
                capture_output=True,
                text=True,
                timeout=60,
            )

            assert result.returncode == 1, "Hook should fail when src/ directory missing"
            assert "src/" in result.stderr.lower() or "source" in result.stdout.lower()
        finally:
            temp_file.unlink()

    def test_hook_fails_when_tests_directory_missing(self):
        """
        Validate hook fails when tests/ directory is not copied.

        GIVEN: A Dockerfile missing COPY tests/ command
        WHEN: Running the validation hook
        THEN: Hook should exit with code 1 (failure)
        """
        dockerfile_content = """
FROM python:3.12-slim AS final-test
WORKDIR /app

COPY src/ ./src/
# Missing: COPY tests/ ./tests/
COPY pyproject.toml ./

CMD ["pytest"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".dockerfile", delete=False) as f:
            f.write(dockerfile_content)
            temp_file = Path(f.name)

        try:
            result = subprocess.run(
                ["python", "scripts/validators/validate_docker_image_contents.py", str(temp_file)],
                capture_output=True,
                text=True,
                timeout=60,
            )

            assert result.returncode == 1, "Hook should fail when tests/ directory missing"
            assert "tests/" in result.stderr.lower() or "test" in result.stdout.lower()
        finally:
            temp_file.unlink()

    def test_hook_fails_when_pyproject_toml_missing(self):
        """
        Validate hook fails when pyproject.toml is not copied.

        GIVEN: A Dockerfile missing COPY pyproject.toml command
        WHEN: Running the validation hook
        THEN: Hook should exit with code 1 (failure)
        """
        dockerfile_content = """
FROM python:3.12-slim AS final-test
WORKDIR /app

COPY src/ ./src/
COPY tests/ ./tests/
# Missing: COPY pyproject.toml ./

CMD ["pytest"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".dockerfile", delete=False) as f:
            f.write(dockerfile_content)
            temp_file = Path(f.name)

        try:
            result = subprocess.run(
                ["python", "scripts/validators/validate_docker_image_contents.py", str(temp_file)],
                capture_output=True,
                text=True,
                timeout=60,
            )

            assert result.returncode == 1, "Hook should fail when pyproject.toml missing"
            assert "pyproject" in result.stderr.lower() or "toml" in result.stdout.lower()
        finally:
            temp_file.unlink()

    def test_hook_validates_scripts_not_copied(self):
        """
        Validate hook ensures scripts/ is NOT copied (correct design).

        GIVEN: A Dockerfile with COPY scripts/ command
        WHEN: Running the validation hook
        THEN: Hook should warn or fail (scripts/ should only be on host)
        """
        dockerfile_content = """
FROM python:3.12-slim AS final-test
WORKDIR /app

COPY src/ ./src/
COPY tests/ ./tests/
COPY pyproject.toml ./
COPY scripts/ ./scripts/  # ❌ WRONG: scripts/ should not be in Docker image

CMD ["pytest"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".dockerfile", delete=False) as f:
            f.write(dockerfile_content)
            temp_file = Path(f.name)

        try:
            result = subprocess.run(
                ["python", "scripts/validators/validate_docker_image_contents.py", str(temp_file)],
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Hook should warn about scripts/ being copied
            assert result.returncode == 1 or "scripts/" in result.stderr.lower() or "scripts/" in result.stdout.lower(), (
                "Hook should warn about scripts/ directory being copied"
            )
        finally:
            temp_file.unlink()

    def test_hook_validates_deployments_not_copied(self):
        """
        Validate hook ensures deployments/ is NOT copied (correct design).

        GIVEN: A Dockerfile with COPY deployments/ command
        WHEN: Running the validation hook
        THEN: Hook should warn or fail (deployments/ should only be on host)
        """
        dockerfile_content = """
FROM python:3.12-slim AS final-test
WORKDIR /app

COPY src/ ./src/
COPY tests/ ./tests/
COPY pyproject.toml ./
COPY deployments/ ./deployments/  # ❌ WRONG: deployments/ should not be in Docker image

CMD ["pytest"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".dockerfile", delete=False) as f:
            f.write(dockerfile_content)
            temp_file = Path(f.name)

        try:
            result = subprocess.run(
                ["python", "scripts/validators/validate_docker_image_contents.py", str(temp_file)],
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Hook should warn about deployments/ being copied
            assert (
                result.returncode == 1 or "deployments/" in result.stderr.lower() or "deployments/" in result.stdout.lower()
            ), "Hook should warn about deployments/ directory being copied"
        finally:
            temp_file.unlink()

    def test_hook_validates_correct_stage(self):
        """
        Validate hook checks COPY commands in the correct Dockerfile stage.

        GIVEN: A Dockerfile with final-test stage
        WHEN: Running the validation hook
        THEN: Hook should validate COPY commands in final-test stage only
        """
        dockerfile_content = """
FROM python:3.12-slim AS base
WORKDIR /app
# Base stage can copy anything

FROM base AS runtime-slim
# Runtime can copy anything

FROM runtime-slim AS final-test
WORKDIR /app

# Only these COPY commands matter for integration tests
COPY src/ ./src/
COPY tests/ ./tests/
COPY pyproject.toml ./

CMD ["pytest", "-m", "integration"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".dockerfile", delete=False) as f:
            f.write(dockerfile_content)
            temp_file = Path(f.name)

        try:
            result = subprocess.run(
                ["python", "scripts/validators/validate_docker_image_contents.py", str(temp_file)],
                capture_output=True,
                text=True,
                timeout=60,
            )

            assert result.returncode == 0, f"Hook should validate final-test stage correctly. stderr: {result.stderr}"
        finally:
            temp_file.unlink()

    def test_hook_with_production_dockerfile(self):
        """
        Validate hook works with the actual Dockerfile.

        GIVEN: The actual docker/Dockerfile file
        WHEN: Running the validation hook
        THEN: Hook should pass (design is correct per ADR-0053)
        """
        dockerfile = Path(__file__).parent.parent.parent / "docker" / "Dockerfile"

        assert dockerfile.exists(), "Dockerfile not found"

        result = subprocess.run(
            ["python", "scripts/validators/validate_docker_image_contents.py", str(dockerfile)],
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0, (
            f"Hook should pass with production Dockerfile. "
            f"Per ADR-0053, integration tests only need src/, tests/, pyproject.toml. "
            f"stderr: {result.stderr}\nstdout: {result.stdout}"
        )
