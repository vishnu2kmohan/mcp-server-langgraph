"""Tests for STUDIO.md validation CLI command.

TDD: These tests define the contract for the studio validate CLI command
that validates STUDIO.md configuration files.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc
from pathlib import Path

import pytest
from click.testing import CliRunner

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="cli_studio_validate")
class TestStudioValidateCLI:
    """Tests for studio validate CLI command."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_validate_command_exists(self) -> None:
        """Test studio validate command exists."""
        from mcp_server_langgraph.cli.studio import studio_validate

        assert studio_validate is not None

    def test_studio_validate_accepts_path_argument(self) -> None:
        """Test studio validate accepts path argument."""
        from mcp_server_langgraph.cli.studio import studio_validate

        runner = CliRunner()
        result = runner.invoke(studio_validate, ["--help"])

        assert "PATH" in result.output or "path" in result.output.lower()

    def test_studio_validate_reports_missing_file(self) -> None:
        """Test studio validate reports missing file error."""
        from mcp_server_langgraph.cli.studio import studio_validate

        runner = CliRunner()
        result = runner.invoke(studio_validate, ["/nonexistent/STUDIO.md"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "does not exist" in result.output.lower()

    def test_studio_validate_validates_valid_studio_md(self) -> None:
        """Test studio validate succeeds with valid STUDIO.md."""
        from mcp_server_langgraph.cli.studio import studio_validate

        valid_content = """---
name: Test Project
tools:
  enabled:
    - search
    - calculator
---
# Test Project

Project instructions here.
"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("STUDIO.md").write_text(valid_content)
            result = runner.invoke(studio_validate, ["STUDIO.md"])

            assert result.exit_code == 0
            assert "valid" in result.output.lower() or "success" in result.output.lower()

    def test_studio_validate_reports_invalid_yaml(self) -> None:
        """Test studio validate reports invalid YAML error."""
        from mcp_server_langgraph.cli.studio import studio_validate

        invalid_content = """---
name: Test Project
tools: [unclosed bracket
---
# Invalid YAML
"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("STUDIO.md").write_text(invalid_content)
            result = runner.invoke(studio_validate, ["STUDIO.md"])

            assert result.exit_code != 0
            assert "error" in result.output.lower() or "invalid" in result.output.lower()

    def test_studio_validate_shows_config_summary(self) -> None:
        """Test studio validate shows configuration summary."""
        from mcp_server_langgraph.cli.studio import studio_validate

        valid_content = """---
name: Test Project
tools:
  enabled:
    - search
    - calculator
skills:
  enabled:
    - code-review
---
# Test Project
"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("STUDIO.md").write_text(valid_content)
            result = runner.invoke(studio_validate, ["STUDIO.md"])

            assert result.exit_code == 0
            # Should show summary of tools and skills
            assert "2" in result.output  # 2 tools
            assert "1" in result.output  # 1 skill


@pytest.mark.unit
@pytest.mark.xdist_group(name="cli_studio_validate_verbose")
class TestStudioValidateCLIVerbose:
    """Tests for studio validate CLI verbose mode."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_validate_verbose_flag(self) -> None:
        """Test studio validate supports --verbose flag."""
        from mcp_server_langgraph.cli.studio import studio_validate

        runner = CliRunner()
        result = runner.invoke(studio_validate, ["--help"])

        assert "--verbose" in result.output or "-v" in result.output

    def test_studio_validate_verbose_shows_details(self) -> None:
        """Test studio validate --verbose shows detailed output."""
        from mcp_server_langgraph.cli.studio import studio_validate

        valid_content = """---
name: Test Project
tools:
  enabled:
    - search
---
# Test Project
"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("STUDIO.md").write_text(valid_content)
            result = runner.invoke(studio_validate, ["--verbose", "STUDIO.md"])

            assert result.exit_code == 0
            # Verbose should show tool names
            assert "search" in result.output


@pytest.mark.unit
@pytest.mark.xdist_group(name="cli_studio_group")
class TestStudioCLIGroup:
    """Tests for studio CLI command group."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_command_group_exists(self) -> None:
        """Test studio command group exists."""
        from mcp_server_langgraph.cli.studio import studio

        assert studio is not None

    def test_studio_command_group_has_validate(self) -> None:
        """Test studio command group has validate subcommand."""
        from mcp_server_langgraph.cli.studio import studio

        runner = CliRunner()
        result = runner.invoke(studio, ["--help"])

        assert "validate" in result.output
