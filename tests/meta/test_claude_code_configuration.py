"""
Test suite for Claude Code configuration validation.

Validates that Claude Code integration follows Anthropic's best practices:
- .claude/settings.json exists and has valid structure
- Slash commands are valid markdown
- CLAUDE.md contains required workflow sections
- .mcp.json is valid JSON
- Templates have required frontmatter

Following TDD: These tests are written FIRST, before configuration exists.
They will FAIL initially (RED phase), then PASS after implementation (GREEN phase).

Regression prevention for Anthropic Claude Code best practices compliance.
See: https://www.anthropic.com/engineering/claude-code-best-practices
"""

import json
import os
from pathlib import Path
from typing import List

import pytest

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = [pytest.mark.unit, pytest.mark.meta]


class TestClaudeCodeConfiguration:
    """Validate Claude Code configuration files exist and are properly structured."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        # Navigate up from tests/meta/ to project root
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def claude_dir(self, project_root: Path) -> Path:
        """Get the .claude directory."""
        return project_root / ".claude"

    @pytest.fixture
    def github_dir(self, project_root: Path) -> Path:
        """Get the .github directory."""
        return project_root / ".github"

    def test_claude_settings_json_exists(self, claude_dir: Path):
        """Test that .claude/settings.json exists."""
        settings_file = claude_dir / "settings.json"
        assert settings_file.exists(), (
            ".claude/settings.json does not exist. " "Create it with allowedTools configuration for WebFetch and Bash."
        )

    def test_claude_settings_json_valid_json(self, claude_dir: Path):
        """Test that .claude/settings.json is valid JSON."""
        settings_file = claude_dir / "settings.json"
        if not settings_file.exists():
            pytest.skip("settings.json does not exist yet (expected in RED phase)")

        with open(settings_file) as f:
            try:
                json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f".claude/settings.json is not valid JSON: {e}")

    def test_claude_settings_has_allowed_tools(self, claude_dir: Path):
        """Test that settings.json has allowedTools configuration."""
        settings_file = claude_dir / "settings.json"
        if not settings_file.exists():
            pytest.skip("settings.json does not exist yet (expected in RED phase)")

        with open(settings_file) as f:
            config = json.load(f)

        assert "allowedTools" in config, "settings.json missing 'allowedTools' key. " "Add WebFetch and Bash tool permissions."

    def test_claude_settings_has_webfetch_domains(self, claude_dir: Path):
        """Test that settings.json has WebFetch allowed_domains."""
        settings_file = claude_dir / "settings.json"
        if not settings_file.exists():
            pytest.skip("settings.json does not exist yet (expected in RED phase)")

        with open(settings_file) as f:
            config = json.load(f)

        if "allowedTools" not in config:
            pytest.skip("allowedTools not configured yet")

        assert "WebFetch" in config["allowedTools"], "settings.json missing WebFetch in allowedTools"

        assert (
            "allowed_domains" in config["allowedTools"]["WebFetch"]
        ), "settings.json missing allowed_domains in WebFetch configuration"

        domains = config["allowedTools"]["WebFetch"]["allowed_domains"]
        assert isinstance(domains, list), "allowed_domains must be a list"
        assert len(domains) > 0, "allowed_domains should not be empty"

        # Check for essential domains
        essential_domains = ["docs.python.org", "github.com", "docs.anthropic.com"]
        for domain in essential_domains:
            assert domain in domains, f"Essential domain '{domain}' missing from allowed_domains"

    def test_mcp_json_exists(self, project_root: Path):
        """Test that .mcp.json exists in project root."""
        mcp_file = project_root / ".mcp.json"
        # This should already exist (validated in previous analysis)
        assert mcp_file.exists(), ".mcp.json should exist in project root"

    def test_mcp_json_valid_structure(self, project_root: Path):
        """Test that .mcp.json has valid structure."""
        mcp_file = project_root / ".mcp.json"
        if not mcp_file.exists():
            pytest.skip(".mcp.json does not exist")

        with open(mcp_file) as f:
            config = json.load(f)

        assert "mcpServers" in config, ".mcp.json missing 'mcpServers' key"
        assert isinstance(config["mcpServers"], dict), "mcpServers must be a dictionary"

    def test_claude_md_exists(self, github_dir: Path):
        """Test that .github/CLAUDE.md exists."""
        claude_md = github_dir / "CLAUDE.md"
        # This should already exist (800+ lines)
        assert claude_md.exists(), ".github/CLAUDE.md should exist"

    def test_claude_md_has_workflow_section(self, github_dir: Path):
        """Test that CLAUDE.md contains Explore→Plan→Code workflow section."""
        claude_md = github_dir / "CLAUDE.md"
        if not claude_md.exists():
            pytest.skip("CLAUDE.md does not exist")

        with open(claude_md) as f:
            content = f.read()

        # Check for workflow section
        assert "Explore → Plan → Code" in content or "Explore->Plan->Code" in content, (
            "CLAUDE.md missing 'Explore → Plan → Code' workflow section. "
            "Add section documenting the recommended 4-phase workflow."
        )

        # Check for phase descriptions
        assert (
            "Phase 1: EXPLORE" in content or "EXPLORE (Research First)" in content
        ), "CLAUDE.md missing EXPLORE phase documentation"

        assert (
            "Phase 2: PLAN" in content or "PLAN (Think Before Acting)" in content
        ), "CLAUDE.md missing PLAN phase documentation"

        assert "Phase 3: CODE" in content or "CODE (TDD Cycle)" in content, "CLAUDE.md missing CODE phase documentation"

        assert (
            "Phase 4: COMMIT" in content or "COMMIT (Automated Validation)" in content
        ), "CLAUDE.md missing COMMIT phase documentation"

    def test_slash_commands_directory_exists(self, claude_dir: Path):
        """Test that .claude/commands/ directory exists."""
        commands_dir = claude_dir / "commands"
        # This should already exist (31+ commands)
        assert commands_dir.exists(), ".claude/commands/ directory should exist"
        assert commands_dir.is_dir(), ".claude/commands/ should be a directory"

    def test_slash_commands_are_markdown(self, claude_dir: Path):
        """Test that all slash commands are .md files."""
        commands_dir = claude_dir / "commands"
        if not commands_dir.exists():
            pytest.skip("commands directory does not exist")

        command_files = list(commands_dir.glob("*.md"))
        assert len(command_files) > 0, "No .md files found in .claude/commands/"

        # All files in commands/ should be .md
        all_files = list(commands_dir.glob("*"))
        non_md_files = [f for f in all_files if f.suffix != ".md" and f.is_file()]

        assert len(non_md_files) == 0, f"Found non-markdown files in .claude/commands/: {non_md_files}"

    def test_new_slash_commands_exist(self, claude_dir: Path):
        """Test that new recommended slash commands exist."""
        commands_dir = claude_dir / "commands"
        if not commands_dir.exists():
            pytest.skip("commands directory does not exist")

        # New commands recommended by Anthropic best practices
        recommended_commands = [
            "tdd.md",
            "explore-codebase.md",
            "plan-feature.md",
            "verify-tests.md",
            "fix-mypy.md",
            "review-pr.md",
        ]

        existing_commands = [f.name for f in commands_dir.glob("*.md")]

        missing_commands = []
        for cmd in recommended_commands:
            if cmd not in existing_commands:
                missing_commands.append(cmd)

        assert len(missing_commands) == 0, (
            f"Missing recommended slash commands: {missing_commands}. " f"Create them in .claude/commands/"
        )

    def test_templates_directory_exists(self, claude_dir: Path):
        """Test that .claude/templates/ directory exists."""
        templates_dir = claude_dir / "templates"
        # This should already exist
        assert templates_dir.exists(), ".claude/templates/ directory should exist"

    def test_templates_are_markdown(self, claude_dir: Path):
        """Test that all templates are .md files."""
        templates_dir = claude_dir / "templates"
        if not templates_dir.exists():
            pytest.skip("templates directory does not exist")

        template_files = list(templates_dir.glob("*.md"))
        # Should have at least a few templates
        assert len(template_files) > 0, "No .md files found in .claude/templates/"

    def test_context_directory_exists(self, claude_dir: Path):
        """Test that .claude/context/ directory exists with key files."""
        context_dir = claude_dir / "context"
        # This should already exist
        assert context_dir.exists(), ".claude/context/ directory should exist"

        # Check for key context files
        key_files = ["testing-patterns.md", "code-patterns.md"]
        for filename in key_files:
            file_path = context_dir / filename
            assert file_path.exists(), f"Missing key context file: {filename} in .claude/context/"

    def test_no_settings_local_in_git(self, claude_dir: Path):
        """Test that settings.local.json is not tracked in git."""
        # This test ensures .gitignore is working correctly
        # settings.local.json should exist but not be committed

        # We can't directly check git status in tests, but we can verify
        # that the .gitignore pattern exists
        gitignore = claude_dir.parent / ".gitignore"

        if not gitignore.exists():
            pytest.skip(".gitignore does not exist")

        with open(gitignore) as f:
            gitignore_content = f.read()

        # Check for settings.local.json or *.local.json pattern
        assert "settings.local.json" in gitignore_content or "*.local.json" in gitignore_content, (
            ".gitignore should contain pattern to exclude settings.local.json " "to prevent committing local configurations"
        )


class TestSlashCommandQuality:
    """Validate slash commands have proper structure and content."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def commands_dir(self, project_root: Path) -> Path:
        """Get the .claude/commands directory."""
        return project_root / ".claude" / "commands"

    @pytest.fixture
    def command_files(self, commands_dir: Path) -> List[Path]:
        """Get all command files."""
        if not commands_dir.exists():
            return []
        return list(commands_dir.glob("*.md"))

    def test_all_commands_have_description(self, command_files: List[Path]):
        """Test that all slash commands have a description."""
        if not command_files:
            pytest.skip("No command files found (expected in RED phase)")

        for cmd_file in command_files:
            with open(cmd_file) as f:
                content = f.read()

            # Each command should have a description (first heading or paragraph)
            assert len(content.strip()) > 0, f"Command {cmd_file.name} is empty"

            # Should have at least a heading
            assert content.startswith("#"), f"Command {cmd_file.name} should start with a markdown heading"


# TDD Validation: Run this test file to verify RED phase
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
