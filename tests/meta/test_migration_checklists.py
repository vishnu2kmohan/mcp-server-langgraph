"""
Test suite for migration checklist validation.

Validates that migration checklists exist and are properly structured:
- .github/checklists/ directory exists
- Required checklists are present
- Checklists have proper markdown structure
- Items are actionable and testable
- Progress tracking sections exist

Following TDD: These tests are written FIRST, before checklists exist.
They will FAIL initially (RED phase), then PASS after implementation (GREEN phase).

Regression prevention for Anthropic Claude Code best practices (large task checklists).
See: https://www.anthropic.com/engineering/claude-code-best-practices
"""

import gc
from pathlib import Path

import pytest

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="migration_checklists")
class TestMigrationChecklists:
    """Validate migration checklists exist and have proper structure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def checklists_dir(self, project_root: Path) -> Path:
        """Get the .github/checklists directory."""
        return project_root / ".github" / "checklists"

    def test_checklists_directory_exists(self, checklists_dir: Path):
        """Test that .github/checklists/ directory exists."""
        assert checklists_dir.exists(), (
            ".github/checklists/ directory does not exist. Create it to store migration and large task checklists."
        )

        assert checklists_dir.is_dir(), ".github/checklists/ exists but is not a directory"

    def test_required_checklists_exist(self, checklists_dir: Path):
        """Test that all required checklists are present."""
        if not checklists_dir.exists():
            pytest.skip("checklists directory does not exist yet (expected in RED phase)")

        required_checklists = [
            "TYPE_SAFETY_MIGRATION.md",
            "SECURITY_AUDIT_CHECKLIST.md",
            "REFACTORING_CHECKLIST.md",
            "PERFORMANCE_OPTIMIZATION.md",
            "DEPENDENCY_UPDATE.md",
        ]

        missing_checklists = []
        for checklist in required_checklists:
            checklist_path = checklists_dir / checklist
            if not checklist_path.exists():
                missing_checklists.append(checklist)

        assert len(missing_checklists) == 0, (
            f"Missing required checklists: {missing_checklists}. Create them in .github/checklists/"
        )

    def test_checklists_are_markdown(self, checklists_dir: Path):
        """Test that all checklists are markdown files."""
        if not checklists_dir.exists():
            pytest.skip("checklists directory does not exist yet")

        checklist_files = list(checklists_dir.glob("*"))

        if len(checklist_files) == 0:
            pytest.skip("No checklist files found yet")

        # All files should be .md
        non_md_files = [f for f in checklist_files if f.suffix != ".md" and f.is_file()]

        assert len(non_md_files) == 0, f"Found non-markdown files in .github/checklists/: {non_md_files}"

    def test_type_safety_checklist_structure(self, checklists_dir: Path):
        """Test that TYPE_SAFETY_MIGRATION.md has proper structure."""
        checklist_path = checklists_dir / "TYPE_SAFETY_MIGRATION.md"

        if not checklist_path.exists():
            pytest.skip("TYPE_SAFETY_MIGRATION.md does not exist yet")

        with open(checklist_path) as f:
            content = f.read()

        # Check for required sections
        required_sections = [
            "## Goal",
            "## Current Status",
            "## Phase 1:",
            "## Phase 2:",
            "## Progress Tracking",
        ]

        missing_sections = []
        for section in required_sections:
            # Use case-insensitive search for flexibility
            if section.lower() not in content.lower():
                missing_sections.append(section)

        assert len(missing_sections) == 0, f"TYPE_SAFETY_MIGRATION.md missing required sections: {missing_sections}"

        # Check that it mentions MyPy (since it's about type safety)
        assert "mypy" in content.lower(), "TYPE_SAFETY_MIGRATION.md should mention MyPy (type checker)"

    def test_checklists_have_task_items(self, checklists_dir: Path):
        """Test that checklists contain task items (- [ ] format)."""
        if not checklists_dir.exists():
            pytest.skip("checklists directory does not exist yet")

        checklist_files = list(checklists_dir.glob("*.md"))

        if len(checklist_files) == 0:
            pytest.skip("No checklist files found yet")

        checklists_without_tasks = []

        for checklist in checklist_files:
            with open(checklist) as f:
                content = f.read()

            # Check for markdown task list syntax
            has_tasks = "- [ ]" in content or "- [x]" in content

            if not has_tasks:
                checklists_without_tasks.append(checklist.name)

        assert len(checklists_without_tasks) == 0, (
            f"Checklists without task items (- [ ]): {checklists_without_tasks}. Checklists should have actionable task items."
        )

    def test_checklists_are_not_empty(self, checklists_dir: Path):
        """Test that checklists have substantial content (> 200 chars)."""
        if not checklists_dir.exists():
            pytest.skip("checklists directory does not exist yet")

        checklist_files = list(checklists_dir.glob("*.md"))

        if len(checklist_files) == 0:
            pytest.skip("No checklist files found yet")

        empty_checklists = []

        for checklist in checklist_files:
            with open(checklist) as f:
                content = f.read()

            # Check minimum content length (200 chars is very minimal)
            if len(content.strip()) < 200:
                empty_checklists.append(checklist.name)

        assert len(empty_checklists) == 0, (
            f"Checklists with insufficient content (< 200 chars): {empty_checklists}. "
            f"Checklists should have comprehensive content."
        )


@pytest.mark.xdist_group(name="meta_migration_checklists")
class TestTypeSafetyChecklist:
    """Specific validation for TYPE_SAFETY_MIGRATION.md."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        import gc

        gc.collect()

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def type_safety_checklist(self, project_root: Path) -> Path:
        """Get the TYPE_SAFETY_MIGRATION.md file."""
        return project_root / ".github" / "checklists" / "TYPE_SAFETY_MIGRATION.md"

    def test_mentions_145_errors(self, type_safety_checklist: Path):
        """Test that checklist mentions the 145+ MyPy errors baseline."""
        if not type_safety_checklist.exists():
            pytest.skip("TYPE_SAFETY_MIGRATION.md does not exist yet")

        with open(type_safety_checklist) as f:
            content = f.read()

        # Should mention the specific number of errors to fix
        has_error_count = "145" in content or "145+" in content

        assert has_error_count, "TYPE_SAFETY_MIGRATION.md should mention the baseline of 145+ errors that need to be fixed."

    def test_has_phase_structure(self, type_safety_checklist: Path):
        """Test that checklist has multi-phase breakdown."""
        if not type_safety_checklist.exists():
            pytest.skip("TYPE_SAFETY_MIGRATION.md does not exist yet")

        with open(type_safety_checklist) as f:
            content = f.read()

        # Should have multiple phases for incremental work
        phase_count = content.lower().count("## phase")

        assert phase_count >= 3, (
            f"TYPE_SAFETY_MIGRATION.md should have at least 3 phases "
            f"(found {phase_count}). Large migrations should be broken into "
            f"manageable phases."
        )

    def test_references_mypy_commands(self, type_safety_checklist: Path):
        """Test that checklist includes MyPy commands for verification."""
        if not type_safety_checklist.exists():
            pytest.skip("TYPE_SAFETY_MIGRATION.md does not exist yet")

        with open(type_safety_checklist) as f:
            content = f.read()

        # Should include mypy command examples
        has_mypy_command = "mypy src/" in content or "`mypy" in content

        assert has_mypy_command, "TYPE_SAFETY_MIGRATION.md should include mypy command examples for validating progress."


# TDD Validation: Run this test file to verify RED phase
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
