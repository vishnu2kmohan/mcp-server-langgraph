"""
Meta-tests to validate pytest plugin behavior with various CLI modes

TDD Regression Test: Ensures fixture organization plugin doesn't interfere
with informational pytest commands like --version, --markers, --fixtures

References:
- OpenAI Codex finding: Plugin may exit during harmless --collect-only runs
- pytest best practices: Plugins should not block informational commands
"""

import gc
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.xdist_group(name="testpluginclimodeguards")
class TestPluginCLIModeGuards:
    """Validate that pytest plugins don't interfere with CLI informational modes"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_plugin_allows_help_command(self):
        """
        TDD REGRESSION TEST: Ensure plugin doesn't block --help

        GIVEN: Pytest with fixture organization plugin
        WHEN: Running pytest --help
        THEN: Command succeeds without fixture validation errors
        """
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--help"],
            capture_output=True,
            timeout=10,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Should not mention fixture violations
        assert "FIXTURE ORGANIZATION VIOLATIONS" not in result.stdout.decode()
        assert "FIXTURE ORGANIZATION VIOLATIONS" not in result.stderr.decode()
        # Should exit successfully
        assert result.returncode == 0

    @pytest.mark.unit
    def test_plugin_allows_version_command(self):
        """
        TDD REGRESSION TEST: Ensure plugin doesn't block --version

        GIVEN: Pytest with fixture organization plugin
        WHEN: Running pytest --version
        THEN: Command succeeds without fixture validation errors
        """
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            capture_output=True,
            timeout=10,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Should not mention fixture violations
        assert "FIXTURE ORGANIZATION VIOLATIONS" not in result.stdout.decode()
        assert "FIXTURE ORGANIZATION VIOLATIONS" not in result.stderr.decode()
        # Should exit successfully
        assert result.returncode == 0

    @pytest.mark.unit
    def test_plugin_allows_markers_command(self):
        """
        TDD REGRESSION TEST: Ensure plugin doesn't block --markers

        GIVEN: Pytest with fixture organization plugin
        WHEN: Running pytest --markers
        THEN: Command succeeds and shows markers without fixture validation
        """
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--markers"],
            capture_output=True,
            timeout=10,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Should not mention fixture violations
        assert "FIXTURE ORGANIZATION VIOLATIONS" not in result.stdout.decode()
        assert "FIXTURE ORGANIZATION VIOLATIONS" not in result.stderr.decode()
        # Should show markers (contains "@pytest.mark")
        output = result.stdout.decode() + result.stderr.decode()
        assert "@pytest.mark" in output
        # Should exit successfully
        assert result.returncode == 0

    @pytest.mark.unit
    def test_plugin_allows_fixtures_command(self):
        """
        TDD REGRESSION TEST: Ensure plugin doesn't block --fixtures

        GIVEN: Pytest with fixture organization plugin
        WHEN: Running pytest --fixtures
        THEN: Command succeeds and shows fixtures without validation errors
        """
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--fixtures"],
            capture_output=True,
            timeout=90,  # Increased from 30s - pytest_sessionfinish litellm cleanup can be slow
            cwd=Path(__file__).parent.parent.parent,
        )

        # Should not mention fixture violations
        assert "FIXTURE ORGANIZATION VIOLATIONS" not in result.stdout.decode()
        assert "FIXTURE ORGANIZATION VIOLATIONS" not in result.stderr.decode()
        # Should show fixtures
        output = result.stdout.decode() + result.stderr.decode()
        assert "fixtures defined from" in output or "fixture" in output.lower()
        # Should exit successfully
        assert result.returncode == 0

    @pytest.mark.unit
    def test_plugin_allows_collect_only_command(self):
        """
        TDD REGRESSION TEST: Ensure plugin doesn't block --collect-only

        GIVEN: Pytest with fixture organization plugin
        WHEN: Running pytest --collect-only
        THEN: Command succeeds and collects tests without running validation
        """
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "tests/meta/"],
            capture_output=True,
            timeout=90,  # Increased from 10s - pytest collection can trigger litellm cleanup hooks
            cwd=Path(__file__).parent.parent.parent,
        )

        # Should not mention fixture violations
        assert "FIXTURE ORGANIZATION VIOLATIONS" not in result.stdout.decode()
        assert "FIXTURE ORGANIZATION VIOLATIONS" not in result.stderr.decode()
        # Should show collected tests
        output = result.stdout.decode() + result.stderr.decode()
        assert "<Module" in output or "collected" in output.lower()
        # Should exit successfully (or with no tests collected warning)
        assert result.returncode in [0, 5]  # 5 = no tests collected
