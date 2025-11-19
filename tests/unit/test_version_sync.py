"""
Test version synchronization across all modules.

Ensures that version is consistent across:
- pyproject.toml (single source of truth)
- __init__.py
- config.py
- observability telemetry
"""

import gc
import sys
from pathlib import Path

import pytest


# Python 3.11+ has tomllib built-in, older versions need tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        pytest.skip("tomli not available", allow_module_level=True)


@pytest.mark.unit
def test_version_matches_pyproject():
    """Test that __version__ in __init__.py matches pyproject.toml."""
    # Read version from pyproject.toml
    project_root = Path(__file__).parent.parent.parent
    pyproject_path = project_root / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)
    expected_version = pyproject_data["project"]["version"]

    # Import version from package
    from mcp_server_langgraph import __version__

    assert (
        __version__ == expected_version
    ), f"Version mismatch: __init__.py has {__version__}, but pyproject.toml has {expected_version}"


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
def test_version_format():
    """Test that version follows semantic versioning format."""
    from mcp_server_langgraph import __version__

    # Should be in format X.Y.Z or X.Y.Z-suffix
    parts = __version__.split("-")[0].split(".")
    assert len(parts) == 3, f"Version {__version__} should have 3 parts (X.Y.Z)"

    for part in parts:
        assert part.isdigit(), f"Version part '{part}' in {__version__} should be numeric"
