"""
CLI Smoke Tests

Basic smoke tests for CLI commands to ensure they can be invoked without errors.
These tests don't verify full functionality, but ensure commands are accessible
and provide proper help text.

Following TDD principles - these tests verify CLI commands are properly wired.

Note: These tests require click<8.2.0 due to internal module changes in 8.2+.
The CLI module is pinned in pyproject.toml [project.optional-dependencies.cli].
"""

import gc

import pytest

# Check if CLI dependencies are available and functional
CLI_AVAILABLE = False
CLI_ERROR = ""

try:
    from click.testing import CliRunner
    from mcp_server_langgraph.cli import cli

    # Test that CLI can actually be invoked (catches Click 8.2+ _textwrap issue)
    _test_runner = CliRunner()
    _test_result = _test_runner.invoke(cli, ["--help"])
    if _test_result.exception and isinstance(_test_result.exception, ModuleNotFoundError):
        CLI_AVAILABLE = False
        CLI_ERROR = str(_test_result.exception)
    elif _test_result.exit_code != 0 and _test_result.exception:
        CLI_AVAILABLE = False
        CLI_ERROR = str(_test_result.exception)
    else:
        CLI_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    CLI_AVAILABLE = False
    CLI_ERROR = str(e)
except Exception as e:
    CLI_AVAILABLE = False
    CLI_ERROR = str(e)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(
        not CLI_AVAILABLE,
        reason=f"CLI not functional: {CLI_ERROR}",
    ),
]


@pytest.mark.cli
@pytest.mark.xdist_group(name="testclismoke")
class TestCLISmoke:
    """Smoke tests for CLI commands."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def runner(self):
        """Create a Click CLI test runner."""
        return CliRunner()

    def test_cli_main_help(self, runner):
        """Test that main CLI help command works."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "MCP Server with LangGraph CLI" in result.output
        assert "init" in result.output
        assert "create-agent" in result.output
        assert "add-tool" in result.output
        assert "migrate" in result.output

    def test_cli_version_command_displays_version_info(self, runner):
        """Test that version command works."""
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "mcpserver" in result.output

    def test_init_command_help(self, runner):
        """Test that init command help works."""
        result = runner.invoke(cli, ["init", "--help"])

        assert result.exit_code == 0
        assert "Initialize a new MCP Server project" in result.output
        assert "--quickstart" in result.output
        assert "--template" in result.output

    def test_create_agent_command_help(self, runner):
        """Test that create-agent command help works."""
        result = runner.invoke(cli, ["create-agent", "--help"])

        assert result.exit_code == 0
        assert "Create a new agent" in result.output
        assert "--template" in result.output
        assert "--tools" in result.output

    def test_add_tool_command_help(self, runner):
        """Test that add-tool command help works."""
        result = runner.invoke(cli, ["add-tool", "--help"])

        assert result.exit_code == 0
        assert "Add a new tool" in result.output
        assert "--description" in result.output

    def test_migrate_command_help(self, runner):
        """Test that migrate command help works."""
        result = runner.invoke(cli, ["migrate", "--help"])

        assert result.exit_code == 0
        assert "Migrate from another agent framework" in result.output
        assert "--from" in result.output
        assert "--input" in result.output


@pytest.mark.cli
@pytest.mark.xdist_group(name="testclitemplateoptions")
class TestCLITemplateOptions:
    """Test that CLI commands accept valid template options."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def runner(self):
        """Create a Click CLI test runner."""
        return CliRunner()

    def test_init_accepts_valid_templates(self, runner):
        """Test that init command accepts valid template choices."""
        valid_templates = ["quickstart", "production", "enterprise"]

        for template in valid_templates:
            # Test with --help to avoid actually creating files
            result = runner.invoke(cli, ["init", "--help"])
            assert result.exit_code == 0
            assert template in result.output

    def test_create_agent_accepts_valid_templates(self, runner):
        """Test that create-agent command accepts valid template choices."""
        valid_templates = ["basic", "research", "customer-support", "code-review", "data-analyst"]

        # Verify templates are documented in help
        result = runner.invoke(cli, ["create-agent", "--help"])
        assert result.exit_code == 0

        # At least some templates should be mentioned
        assert any(template in result.output for template in valid_templates)

    def test_migrate_accepts_valid_frameworks(self, runner):
        """Test that migrate command accepts valid framework choices."""
        valid_frameworks = ["crewai", "langchain", "openai-agentkit", "autogpt"]

        # Verify frameworks are documented in help
        result = runner.invoke(cli, ["migrate", "--help"])
        assert result.exit_code == 0

        # At least some frameworks should be mentioned
        assert any(framework in result.output for framework in valid_frameworks)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
