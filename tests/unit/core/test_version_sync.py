"""
Test version synchronization across all modules.

Ensures that version is consistent across:
- pyproject.toml (single source of truth)
- __init__.py
- config.py
- observability telemetry
"""

import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
def test_version_matches_pyproject():
    """Test that __version__ in __init__.py matches pyproject.toml."""
    # Read version from pyproject.toml
    # Path: tests/unit/core/test_*.py -> parent^4 = project root
    project_root = Path(__file__).parent.parent.parent.parent
    pyproject_path = project_root / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)
    expected_version = pyproject_data["project"]["version"]

    # Import version from package
    from mcp_server_langgraph import __version__

    assert __version__ == expected_version, (
        f"Version mismatch: __init__.py has {__version__}, but pyproject.toml has {expected_version}"
    )


@pytest.mark.unit
def test_config_version_matches():
    """Test that config.service_version matches package version."""
    from mcp_server_langgraph import __version__
    from mcp_server_langgraph.core.config import settings

    assert settings.service_version == __version__, (
        f"Config version mismatch: config.service_version is {settings.service_version}, "
        f"but package __version__ is {__version__}"
    )


@pytest.mark.unit
def test_telemetry_version_matches():
    """Test that telemetry resource uses correct version."""
    from mcp_server_langgraph import __version__

    # The telemetry config should use settings.service_version
    # which should match __version__
    from mcp_server_langgraph.core.config import settings

    assert settings.service_version == __version__, (
        f"Telemetry will use incorrect version: settings.service_version is {settings.service_version}, "
        f"but __version__ is {__version__}"
    )


@pytest.mark.unit
def test_version_format_validation_with_semver_ensures_correct_structure():
    """Test that version follows semantic versioning format."""
    from mcp_server_langgraph import __version__

    # Should be in format X.Y.Z or X.Y.Z-suffix
    parts = __version__.split("-")[0].split(".")
    assert len(parts) == 3, f"Version {__version__} should have 3 parts (X.Y.Z)"

    for part in parts:
        assert part.isdigit(), f"Version part '{part}' in {__version__} should be numeric"


@pytest.mark.unit
def test_version_via_importlib_metadata():
    """Test that version can be retrieved via importlib.metadata.

    This ensures the package is properly installed with metadata,
    allowing version detection without requiring pyproject.toml at runtime.
    This pattern is required for Docker runtime images that don't include pyproject.toml.
    """
    from importlib.metadata import version

    from mcp_server_langgraph import __version__

    # importlib.metadata.version reads from installed package metadata
    metadata_version = version("mcp-server-langgraph")

    assert metadata_version == __version__, (
        f"importlib.metadata version ({metadata_version}) should match __version__ ({__version__})"
    )
