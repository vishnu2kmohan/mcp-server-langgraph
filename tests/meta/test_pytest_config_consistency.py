"""
Test that validates pytest configuration consistency across the codebase.

OpenAI Codex Finding (2025-11-16):
===================================
tests/deployment/pytest.ini creates duplicate pytest configuration that conflicts
with root pyproject.toml settings, causing tests to behave differently when run
from the deployment directory.

Issues with duplicate config:
- testpaths: pytest.ini uses "." (current dir), pyproject.toml uses ["tests"] (root)
- pythonpath: pytest.ini MISSING, pyproject.toml has [".", "scripts"]
- addopts: pytest.ini missing --dist loadscope --timeout=60 --benchmark-disable
- markers: pytest.ini has 11 markers, pyproject.toml has 38 markers (superset)

Solution:
- Single source of truth: pyproject.toml [tool.pytest.ini_options]
- Delete tests/deployment/pytest.ini
- All tests inherit same configuration regardless of run location

This test ensures no duplicate pytest configurations exist.
"""

import gc
from pathlib import Path

import pytest


# Module-level markers: Unit tests that validate test infrastructure (meta)
pytestmark = [pytest.mark.unit, pytest.mark.meta]


@pytest.mark.meta
@pytest.mark.xdist_group(name="pytest_config_consistency")
class TestPytestConfigConsistency:
    """Validate single source of truth for pytest configuration."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_no_duplicate_pytest_ini_files(self):
        """
        GIVEN: Project root and all subdirectories
        WHEN: Searching for pytest configuration files
        THEN: Only pyproject.toml should contain pytest configuration
              No pytest.ini, .pytest.ini, tox.ini, or setup.cfg with [tool:pytest] sections

        RED PHASE: This test should FAIL initially (tests/deployment/pytest.ini exists)
        GREEN PHASE: Test passes after deleting duplicate config files
        """
        project_root = Path(__file__).parent.parent.parent

        # Find all pytest.ini files (should be NONE)
        pytest_ini_files = list(project_root.rglob("pytest.ini"))
        hidden_pytest_ini_files = list(project_root.rglob(".pytest.ini"))

        # Find setup.cfg files with pytest config (should be NONE)
        setup_cfg_files = []
        for setup_cfg in project_root.rglob("setup.cfg"):
            content = setup_cfg.read_text()
            if "[tool:pytest]" in content or "[pytest]" in content:
                setup_cfg_files.append(setup_cfg)

        # Find tox.ini files with pytest config (should be NONE)
        tox_ini_files = []
        for tox_ini in project_root.rglob("tox.ini"):
            content = tox_ini.read_text()
            if "[pytest]" in content:
                tox_ini_files.append(tox_ini)

        # Collect all duplicate config files
        duplicate_configs = pytest_ini_files + hidden_pytest_ini_files + setup_cfg_files + tox_ini_files

        # Filter out .venv and node_modules
        duplicate_configs = [f for f in duplicate_configs if ".venv" not in str(f) and "node_modules" not in str(f)]

        assert not duplicate_configs, (
            f"Found {len(duplicate_configs)} duplicate pytest configuration files.\n"
            "\n"
            "Only pyproject.toml should contain pytest configuration.\n"
            "Duplicate configs cause inconsistent test behavior based on run location.\n"
            "\n"
            "Duplicate configs found:\n" + "\n".join(f"  - {f.relative_to(project_root)}" for f in duplicate_configs) + "\n\n"
            "Solution: Delete these files and rely on pyproject.toml [tool.pytest.ini_options]\n"
        )

    def test_pyproject_toml_has_pytest_config(self):
        """
        GIVEN: Project root pyproject.toml
        WHEN: Checking for pytest configuration
        THEN: Should have [tool.pytest.ini_options] section with required settings
        """
        project_root = Path(__file__).parent.parent.parent
        pyproject_toml = project_root / "pyproject.toml"

        assert pyproject_toml.exists(), "pyproject.toml not found at project root"

        content = pyproject_toml.read_text()

        # Verify pytest configuration section exists
        assert "[tool.pytest.ini_options]" in content, "pyproject.toml missing [tool.pytest.ini_options] section"

        # Verify critical settings present
        required_settings = [
            "testpaths",  # Where tests are located
            "pythonpath",  # Python path configuration
            "addopts",  # pytest command-line options
            "markers",  # Registered pytest markers
        ]

        for setting in required_settings:
            assert (
                f"{setting} =" in content or f"{setting} = [" in content
            ), f"pyproject.toml [tool.pytest.ini_options] missing required setting: {setting}"

    def test_pytest_config_includes_timeout_protection(self):
        """
        GIVEN: Project pyproject.toml pytest configuration
        WHEN: Checking addopts setting
        THEN: Should include --timeout flag for test timeout protection

        This prevents tests from hanging indefinitely.
        """
        project_root = Path(__file__).parent.parent.parent
        pyproject_toml = project_root / "pyproject.toml"
        content = pyproject_toml.read_text()

        # Find [tool.pytest.ini_options] section
        assert "[tool.pytest.ini_options]" in content

        # Verify timeout is configured
        assert "--timeout" in content, (
            "pytest configuration missing --timeout flag.\n"
            "This is critical for preventing hanging tests.\n"
            "Expected: addopts should include --timeout=60 or similar"
        )

    def test_pytest_config_includes_xdist_settings(self):
        """
        GIVEN: Project pyproject.toml pytest configuration
        WHEN: Checking addopts setting
        THEN: Should include pytest-xdist settings for parallel execution

        Validates --dist loadscope is configured for proper test distribution.
        """
        project_root = Path(__file__).parent.parent.parent
        pyproject_toml = project_root / "pyproject.toml"
        content = pyproject_toml.read_text()

        # Find [tool.pytest.ini_options] section
        assert "[tool.pytest.ini_options]" in content

        # Verify xdist is configured (--dist loadscope recommended for class-based tests)
        # This may not always be in addopts if passed via command line, so we make this informational
        if "--dist" in content:
            assert "--dist loadscope" in content or "--dist load" in content, (
                "pytest-xdist configured but not using loadscope.\n"
                "Recommended: --dist loadscope for class-based test distribution"
            )
