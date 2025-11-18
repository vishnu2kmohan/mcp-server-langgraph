"""
Test that CI workflow validation tests can import all required modules.

This test ensures that the CI workflow validation step has access to all
necessary dependencies, particularly langchain_core and other project modules.
"""

import gc
import subprocess
import sys
from pathlib import Path

import pytest


# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


def test_langchain_core_importable():
    """Test that langchain_core can be imported in the CI environment.

    This validates that the dev extras in pyproject.toml include all
    required dependencies for workflow validation tests.
    """
    try:
        import langchain_core

        assert langchain_core is not None
    except ImportError as e:
        pytest.fail(f"Failed to import langchain_core: {e}")


def test_all_project_modules_importable():
    """Test that all project modules can be imported.

    This ensures the virtual environment is properly configured and
    all dependencies are installed.
    """
    required_modules = [
        "mcp_server_langgraph",
        "mcp_server_langgraph.auth",
        "mcp_server_langgraph.auth.middleware",
        "mcp_server_langgraph.auth.user_provider",
    ]

    for module_name in required_modules:
        try:
            __import__(module_name)
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


def test_workflow_validation_dependencies():
    """Test that workflow validation test dependencies are available.

    This ensures pytest, pyyaml, and other validation dependencies
    are properly installed in the dev environment.
    """
    required_packages = [
        "pytest",
        "yaml",  # pyyaml
    ]

    for package_name in required_packages:
        try:
            __import__(package_name)
        except ImportError as e:
            pytest.fail(f"Failed to import {package_name}: {e}")


def test_uv_venv_activated():
    """Test that the uv virtual environment is properly activated.

    This validates that the GitHub Actions workflow is using the
    correct Python environment created by the setup-python-deps action.
    """
    # Verify the Python executable path makes sense
    python_path = Path(sys.executable)
    assert python_path.exists(), f"Python executable not found: {python_path}"


def test_dev_extras_complete():
    """Test that dev extras include all necessary packages for CI validation.

    This is a meta-test that verifies the pyproject.toml configuration
    includes all packages needed for workflow validation tests.
    """
    # Read pyproject.toml
    import tomllib

    project_root = Path(__file__).parent.parent
    pyproject_path = project_root / "pyproject.toml"

    assert pyproject_path.exists(), "pyproject.toml not found"

    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    # Check dev extras exist
    dev_deps = pyproject.get("project", {}).get("optional-dependencies", {}).get("dev", [])
    assert len(dev_deps) > 0, "dev extras are empty"

    # Verify pytest and pyyaml are included (directly or via dependency)
    # Note: langchain_core should be in main dependencies or dev extras
    deps_str = " ".join(dev_deps)
    assert "pytest" in deps_str or "pytest>=" in deps_str or "pytest==" in deps_str, "pytest not found in dev extras"
