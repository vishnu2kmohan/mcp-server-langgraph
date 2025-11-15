"""
Test suite for slash command validation.

Validates that slash commands in .claude/commands/ are properly structured:
- Commands have descriptions
- Commands use valid markdown syntax
- No duplicate command names
- Commands reference existing make targets
- New recommended commands exist

Following TDD: These tests are written FIRST, before new commands exist.
They will FAIL initially (RED phase), then PASS after implementation (GREEN phase).

Regression prevention for Anthropic Claude Code slash commands best practices.
See: https://www.anthropic.com/engineering/claude-code-best-practices
"""

import gc
import re
from pathlib import Path
from typing import Dict, List, Set

import pytest

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = [pytest.mark.unit, pytest.mark.meta]


@pytest.mark.xdist_group(name="slash_commands")
class TestSlashCommands:
    """Validate slash commands are properly structured."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

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
            pytest.skip("commands directory does not exist (should exist already)")
        return list(commands_dir.glob("*.md"))

    @pytest.fixture
    def makefile(self, project_root: Path) -> Path:
        """Get the Makefile."""
        return project_root / "Makefile"

    def test_all_commands_have_heading(self, command_files: List[Path]):
        """Test that all slash commands start with a markdown heading."""
        if not command_files:
            pytest.skip("No command files found")

        commands_without_heading = []

        for cmd_file in command_files:
            with open(cmd_file) as f:
                content = f.read().strip()

            if not content.startswith("#"):
                commands_without_heading.append(cmd_file.name)

        assert len(commands_without_heading) == 0, (
            f"Commands without markdown heading: {commands_without_heading}. " f"Each command should start with # Title"
        )

    def test_all_commands_have_substantial_content(self, command_files: List[Path]):
        """Test that all commands have substantial content (> 100 chars)."""
        if not command_files:
            pytest.skip("No command files found")

        short_commands = []

        for cmd_file in command_files:
            with open(cmd_file) as f:
                content = f.read().strip()

            # Minimum 100 characters (very low bar)
            if len(content) < 100:
                short_commands.append(cmd_file.name)

        assert len(short_commands) == 0, (
            f"Commands with insufficient content (< 100 chars): {short_commands}. "
            f"Commands should have clear descriptions and instructions."
        )

    def test_no_duplicate_command_names(self, command_files: List[Path]):
        """Test that there are no duplicate command names."""
        if not command_files:
            pytest.skip("No command files found")

        command_names = [f.stem for f in command_files]  # filename without .md

        duplicates = []
        seen = set()
        for name in command_names:
            if name in seen:
                duplicates.append(name)
            seen.add(name)

        assert len(duplicates) == 0, f"Duplicate command names found: {duplicates}"

    def test_make_targets_referenced_exist(self, command_files: List[Path], makefile: Path):
        """Test that make targets referenced in commands actually exist."""
        if not command_files:
            pytest.skip("No command files found")

        if not makefile.exists():
            pytest.skip("Makefile does not exist")

        # Extract all make targets from Makefile
        with open(makefile) as f:
            makefile_content = f.read()

        # Find all make targets (lines starting with target_name:)
        make_target_pattern = re.compile(r"^([a-z][a-z0-9-]*):.*$", re.MULTILINE)
        make_targets = set(make_target_pattern.findall(makefile_content))

        # Find all make commands in slash commands
        invalid_references = []

        for cmd_file in command_files:
            with open(cmd_file) as f:
                content = f.read()

            # Find make commands (e.g., "make test", "make test-unit")
            make_commands = re.findall(r"make\s+([a-z][a-z0-9-]+)", content)

            for target in make_commands:
                if target not in make_targets:
                    invalid_references.append((cmd_file.name, target))

        assert len(invalid_references) == 0, (
            f"Commands reference non-existent make targets: {invalid_references}. "
            f"Update commands or add missing targets to Makefile."
        )

    def test_commands_use_valid_bash_syntax(self, command_files: List[Path]):
        """Test that bash code blocks in commands have valid syntax."""
        if not command_files:
            pytest.skip("No command files found")

        # This is a basic check - just ensure bash blocks are properly closed
        unclosed_code_blocks = []

        for cmd_file in command_files:
            with open(cmd_file) as f:
                content = f.read()

            # Count code block delimiters
            triple_backticks = content.count("```")

            # Should be even (opening and closing)
            if triple_backticks % 2 != 0:
                unclosed_code_blocks.append(cmd_file.name)

        assert len(unclosed_code_blocks) == 0, (
            f"Commands with unclosed code blocks: {unclosed_code_blocks}. " f"Ensure all ``` blocks are properly closed."
        )

    def test_new_recommended_commands_exist(self, commands_dir: Path):
        """Test that new recommended commands exist."""
        if not commands_dir.exists():
            pytest.skip("commands directory does not exist")

        # New commands recommended by Anthropic best practices
        new_commands = {
            "tdd.md": "Start TDD workflow for a feature",
            "explore-codebase.md": "Guided codebase exploration",
            "plan-feature.md": "Feature planning with ultrathink",
            "verify-tests.md": "Run and verify all tests pass",
            "fix-mypy.md": "Systematic MyPy error fixing",
            "review-pr.md": "Comprehensive PR review checklist",
        }

        missing_commands = []

        for cmd_name, description in new_commands.items():
            cmd_path = commands_dir / cmd_name
            if not cmd_path.exists():
                missing_commands.append(f"{cmd_name} ({description})")

        assert len(missing_commands) == 0, (
            f"Missing recommended commands: {missing_commands}. " f"Create them in .claude/commands/"
        )

    def test_commands_have_consistent_format(self, command_files: List[Path]):
        """Test that commands follow a consistent format."""
        if not command_files:
            pytest.skip("No command files found")

        # Commands should have:
        # 1. Title (# heading)
        # 2. Description (paragraph)
        # 3. Instructions or code blocks

        inconsistent_commands = []

        for cmd_file in command_files:
            with open(cmd_file) as f:
                lines = f.readlines()

            if len(lines) < 3:  # Too short to have title + description
                inconsistent_commands.append(f"{cmd_file.name} (too short)")
                continue

            # First line should be heading
            if not lines[0].strip().startswith("#"):
                inconsistent_commands.append(f"{cmd_file.name} (no heading)")

        # This is informational, not a hard failure
        if inconsistent_commands:
            print(f"\nWARNING: Some commands may have inconsistent format: " f"{inconsistent_commands}")

    def test_tdd_command_references_red_green_refactor(self, commands_dir: Path):
        """Test that tdd.md command explains RED-GREEN-REFACTOR cycle."""
        tdd_command = commands_dir / "tdd.md"

        if not tdd_command.exists():
            pytest.skip("tdd.md does not exist yet (expected in RED phase)")

        with open(tdd_command) as f:
            content = f.read().lower()

        # Should mention the TDD cycle phases
        assert "red" in content, "tdd.md should mention RED phase"
        assert "green" in content, "tdd.md should mention GREEN phase"
        assert "refactor" in content, "tdd.md should mention REFACTOR phase"

        # Should mention writing tests first
        assert "test" in content and "first" in content, "tdd.md should emphasize writing tests FIRST"

    def test_verify_tests_command_runs_all_test_types(self, commands_dir: Path):
        """Test that verify-tests.md runs all test types."""
        verify_command = commands_dir / "verify-tests.md"

        if not verify_command.exists():
            pytest.skip("verify-tests.md does not exist yet (expected in RED phase)")

        with open(verify_command) as f:
            content = f.read()

        # Should include multiple test types
        test_types = ["unit", "integration", "property"]

        missing_types = []
        for test_type in test_types:
            if test_type not in content.lower():
                missing_types.append(test_type)

        assert len(missing_types) == 0, f"verify-tests.md should run {missing_types} tests"

    def test_commands_avoid_dangerous_operations(self, command_files: List[Path]):
        """Test that commands don't include dangerous operations."""
        if not command_files:
            pytest.skip("No command files found")

        dangerous_patterns = [
            r"rm\s+-rf\s+/",
            r"dd\s+if=",
            r"mkfs",
            r"chmod\s+777",
            r"curl.*\|\s*bash",
            r"wget.*\|\s*sh",
        ]

        dangerous_commands = []

        for cmd_file in command_files:
            with open(cmd_file) as f:
                content = f.read()

            for pattern in dangerous_patterns:
                if re.search(pattern, content):
                    dangerous_commands.append((cmd_file.name, pattern))

        assert len(dangerous_commands) == 0, (
            f"Commands contain dangerous operations: {dangerous_commands}. " f"Remove or add safety guards."
        )


@pytest.mark.xdist_group(name="meta_slash_commands")
class TestCommandDocumentation:
    """Validate command documentation quality."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        import gc

        gc.collect()

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def claude_md(self, project_root: Path) -> Path:
        """Get the .github/CLAUDE.md file."""
        return project_root / ".github" / "CLAUDE.md"

    def test_claude_md_documents_slash_commands(self, claude_md: Path):
        """Test that CLAUDE.md documents the slash command system."""
        if not claude_md.exists():
            pytest.skip("CLAUDE.md does not exist")

        with open(claude_md) as f:
            content = f.read()

        # Should mention slash commands
        has_slash_commands_section = (
            "slash command" in content.lower() or "/command" in content or ".claude/commands" in content
        )

        assert has_slash_commands_section, (
            "CLAUDE.md should document the slash command system. "
            "Add a section explaining available commands and how to use them."
        )


# TDD Validation: Run this test file to verify RED phase
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
