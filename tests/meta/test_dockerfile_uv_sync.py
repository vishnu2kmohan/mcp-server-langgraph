"""
Meta-test: Validate Dockerfile uses `uv sync --frozen` for consistency.

This test ensures Docker builds use the same dependency management approach
as local development and CI/CD, preventing subtle dependency differences.

TDD Test (RED phase): These tests will fail until Dockerfiles are updated
to use `uv sync --frozen` instead of `uv export` + `uv pip install`.

References:
- https://docs.astral.sh/uv/guides/integration/docker/
- https://hynek.me/articles/docker-uv/
- ADR: Consistent uv sync usage across environments
"""

import gc
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.meta


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


@pytest.fixture(scope="module")
def main_dockerfile(project_root):
    """Read the main Dockerfile content."""
    dockerfile_path = project_root / "docker" / "Dockerfile"
    return dockerfile_path.read_text()


@pytest.fixture(scope="module")
def test_dockerfile(project_root):
    """Read the test Dockerfile content."""
    dockerfile_path = project_root / "docker" / "Dockerfile.test"
    return dockerfile_path.read_text()


@pytest.mark.xdist_group(name="dockerfile_uv_sync")
class TestDockerfileUvSyncConsistency:
    """Test that Dockerfiles use uv sync --frozen for consistency with local/CI."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_main_dockerfile_uses_uv_sync(self, main_dockerfile):
        """
        Verify main Dockerfile uses 'uv sync' instead of 'uv export' + 'uv pip install'.

        This ensures consistency with local development and CI/CD which use:
            uv sync --frozen --extra dev --extra builder
        """
        # Should NOT use uv export (old approach)
        assert "uv export" not in main_dockerfile, (
            "Dockerfile should NOT use 'uv export'. " "Use 'uv sync --frozen' directly for consistency with local/CI."
        )

        # Should use uv sync
        assert "uv sync" in main_dockerfile, (
            "Dockerfile should use 'uv sync --frozen' for dependency installation. "
            "This ensures consistency with local development and CI/CD."
        )

    def test_main_dockerfile_uses_frozen_flag(self, main_dockerfile):
        """
        Verify main Dockerfile uses --frozen flag with uv sync.

        The --frozen flag ensures the lockfile is used exactly as-is,
        failing if dependencies need resolution.
        """
        # Look for uv sync with --frozen flag
        uv_sync_pattern = re.compile(r"uv\s+sync\s+[^#\n]*--frozen")
        assert uv_sync_pattern.search(main_dockerfile), (
            "Dockerfile should use 'uv sync --frozen' to ensure lockfile is used exactly. "
            "This prevents dependency drift between local and Docker builds."
        )

    def test_main_dockerfile_no_manual_venv(self, main_dockerfile):
        """
        Verify main Dockerfile does not manually create venvs.

        With uv sync, the virtual environment is managed by uv itself
        via UV_PROJECT_ENVIRONMENT or default .venv location.
        """
        # Should NOT manually create venv
        assert "python -m venv" not in main_dockerfile, (
            "Dockerfile should NOT use 'python -m venv'. " "Let uv manage the virtual environment via UV_PROJECT_ENVIRONMENT."
        )

    def test_main_dockerfile_no_uv_pip_install(self, main_dockerfile):
        """
        Verify main Dockerfile does not use 'uv pip install'.

        'uv pip install' bypasses the lockfile resolution. Use 'uv sync' instead.
        """
        assert "uv pip install" not in main_dockerfile, (
            "Dockerfile should NOT use 'uv pip install'. " "Use 'uv sync --frozen' which respects the lockfile."
        )

    def test_main_dockerfile_has_uv_env_vars(self, main_dockerfile):
        """
        Verify main Dockerfile sets recommended UV environment variables.

        Best practices from official uv docs and Hynek Schlawack's guide:
        - UV_COMPILE_BYTECODE=1: Faster startup
        - UV_LINK_MODE=copy: Copy files instead of symlinks
        - UV_PYTHON_DOWNLOADS=never: Use system Python
        """
        assert "UV_COMPILE_BYTECODE" in main_dockerfile, "Dockerfile should set UV_COMPILE_BYTECODE=1 for faster startup."
        assert "UV_LINK_MODE" in main_dockerfile, "Dockerfile should set UV_LINK_MODE=copy for portable builds."

    def test_test_dockerfile_uses_uv_sync(self, test_dockerfile):
        """
        Verify test Dockerfile uses 'uv sync' instead of 'uv export' + 'uv pip install'.
        """
        # Should NOT use uv export
        assert "uv export" not in test_dockerfile, (
            "Dockerfile.test should NOT use 'uv export'. "
            "Use 'uv sync --frozen --extra dev --extra builder' for consistency."
        )

        # Should use uv sync
        assert "uv sync" in test_dockerfile, "Dockerfile.test should use 'uv sync --frozen' for dependency installation."

    def test_test_dockerfile_uses_frozen_flag(self, test_dockerfile):
        """Verify test Dockerfile uses --frozen flag with uv sync."""
        uv_sync_pattern = re.compile(r"uv\s+sync\s+[^#\n]*--frozen")
        assert uv_sync_pattern.search(
            test_dockerfile
        ), "Dockerfile.test should use 'uv sync --frozen' to ensure lockfile is used exactly."

    def test_test_dockerfile_no_uv_pip_install(self, test_dockerfile):
        """Verify test Dockerfile does not use 'uv pip install'."""
        assert "uv pip install" not in test_dockerfile, (
            "Dockerfile.test should NOT use 'uv pip install'. " "Use 'uv sync --frozen' which respects the lockfile."
        )


@pytest.mark.xdist_group(name="dockerfile_uv_sync_extras")
class TestDockerfileUvSyncExtras:
    """Test that Dockerfiles use correct --extra flags for each variant."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_base_variant_has_no_dev_flag(self, main_dockerfile):
        """
        Verify base variant uses --no-dev to exclude development dependencies.

        Production images should not include dev dependencies.
        """
        # Look for build-base stage using --no-dev
        # This is a simplified check - the actual pattern may vary
        assert "--no-dev" in main_dockerfile, "Production variants should use '--no-dev' flag to exclude dev dependencies."

    def test_test_dockerfile_has_dev_extra(self, test_dockerfile):
        """
        Verify test Dockerfile includes --extra dev for test dependencies.

        Test images need dev dependencies for running pytest, etc.
        """
        assert (
            "--extra dev" in test_dockerfile or "--all-extras" in test_dockerfile
        ), "Dockerfile.test should include '--extra dev' for test dependencies."


@pytest.mark.xdist_group(name="dockerfile_uv_sync_paths")
class TestDockerfileUvSyncPaths:
    """Test that Dockerfiles use correct paths with uv sync."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_main_dockerfile_sets_uv_project_environment(self, main_dockerfile):
        """
        Verify Dockerfile sets UV_PROJECT_ENVIRONMENT for consistent venv location.

        This ensures uv sync installs to a predictable location that can be
        copied to the runtime stage.
        """
        assert "UV_PROJECT_ENVIRONMENT" in main_dockerfile, (
            "Dockerfile should set UV_PROJECT_ENVIRONMENT to control venv location. "
            "Recommended: UV_PROJECT_ENVIRONMENT=/app/.venv"
        )

    def test_main_dockerfile_copies_uv_lock(self, main_dockerfile):
        """
        Verify Dockerfile copies uv.lock file before running uv sync.

        uv sync --frozen requires the lockfile to be present.
        """
        # Look for COPY command that includes uv.lock
        assert "uv.lock" in main_dockerfile, "Dockerfile must copy uv.lock file for 'uv sync --frozen' to work."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
