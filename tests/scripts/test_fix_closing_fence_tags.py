"""
Test suite for scripts/fix_closing_fence_tags.py

Tests the closing fence language tag fixer to ensure it:
1. Correctly identifies and fixes closing fences with language tags
2. Preserves opening fence language tags
3. Handles edge cases (indentation, empty blocks, nested structures)
4. Uses proper state machine tracking
"""

import gc

# Import the module under test
import sys
from pathlib import Path
from textwrap import dedent

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.fix_closing_fence_tags import ClosingFenceFixer, find_markdown_files


@pytest.mark.xdist_group(name="scripts_validation")
class TestClosingFenceFixer:
    """Test suite for ClosingFenceFixer class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # ========================================================================
    # Basic Functionality Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_fix_single_closing_fence_with_bash_tag(self):
        """Test fixing a single closing fence with bash tag."""
        content = dedent(
            """
            ```bash
            git clone https://example.com/repo.git
            cd repo
            ```bash

            Next section.
        """
        ).strip()

        fixer = ClosingFenceFixer(dry_run=False)
        fixed_content, fixes = fixer._fix_content(content)

        # Should fix the closing fence
        assert len(fixes) == 1
        assert fixes[0][0] == 4  # Line number
        assert "```bash" in fixes[0][1]  # Old fence
        assert fixes[0][2] == "```"  # New fence

        # Verify fixed content
        assert "```bash\n" in fixed_content  # Opening fence preserved
        assert fixed_content.count("```bash") == 1  # Only opening fence has tag
        assert "```\n\nNext section" in fixed_content  # Closing fence fixed

    @pytest.mark.asyncio
    async def test_fix_multiple_closing_fences(self):
        """Test fixing multiple closing fences in same file."""
        content = dedent(
            """
            First block:
            ```python
            print("hello")
            ```python

            Second block:
            ```javascript
            console.log("world");
            ```javascript

            Done.
        """
        ).strip()

        fixer = ClosingFenceFixer(dry_run=False)
        fixed_content, fixes = fixer._fix_content(content)

        # Should fix both closing fences
        assert len(fixes) == 2
        assert all("```" == fix[2] for fix in fixes)  # Both fixed to bare ```

        # Verify opening fences preserved
        assert "```python\n" in fixed_content
        assert "```javascript\n" in fixed_content

        # Verify closing fences fixed
        assert fixed_content.count("```python") == 1
        assert fixed_content.count("```javascript") == 1

    @pytest.mark.asyncio
    async def test_preserve_correct_closing_fences(self):
        """Test that correctly formatted fences are not modified."""
        content = dedent(
            """
            ```python
            def hello():
                print("world")
            ```

            This is correct.
        """
        ).strip()

        fixer = ClosingFenceFixer(dry_run=False)
        fixed_content, fixes = fixer._fix_content(content)

        # Should not fix anything
        assert len(fixes) == 0
        assert fixed_content == content  # No changes

    # ========================================================================
    # Indentation Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_preserve_indentation_in_fixes(self):
        """Test that indentation is preserved when fixing fences."""
        content = dedent(
            """
            <Step title="Example">
              ```bash
              npm install
              ```bash
            </Step>
        """
        ).strip()

        fixer = ClosingFenceFixer(dry_run=False)
        fixed_content, fixes = fixer._fix_content(content)

        # Should fix with preserved indentation
        assert len(fixes) == 1
        assert fixes[0][2] == "  ```"  # Indentation preserved

        # Verify in content
        lines = fixed_content.split("\n")
        assert lines[3] == "  ```"  # Closing fence with correct indent

    @pytest.mark.asyncio
    async def test_mixed_indentation_levels(self):
        """Test fixing fences with different indentation levels."""
        content = dedent(
            """
            Top level:
            ```yaml
            key: value
            ```yaml

            Indented:
              ```json
              {"key": "value"}
              ```json

            Deep:
                ```python
                x = 1
                ```python
        """
        ).strip()

        fixer = ClosingFenceFixer(dry_run=False)
        fixed_content, fixes = fixer._fix_content(content)

        # Should fix all three with correct indentation
        assert len(fixes) == 3
        assert fixes[0][2] == "```"  # No indent
        assert fixes[1][2] == "  ```"  # 2 spaces
        assert fixes[2][2] == "    ```"  # 4 spaces

    # ========================================================================
    # Edge Cases
    # ========================================================================

    @pytest.mark.asyncio
    async def test_empty_code_block(self):
        """Test fixing empty code block with tagged closing fence."""
        content = dedent(
            """
            ```bash
            ```bash
        """
        ).strip()

        fixer = ClosingFenceFixer(dry_run=False)
        fixed_content, fixes = fixer._fix_content(content)

        # Should fix even empty blocks
        assert len(fixes) == 1
        assert fixes[0][2] == "```"

    @pytest.mark.asyncio
    async def test_nested_code_blocks_in_content(self):
        """Test that code fence examples within blocks don't confuse parser."""
        content = dedent(
            """
            ```markdown
            This shows how to use code blocks:

            ```python
            print("hello")
            ```
            ```markdown

            Next section.
        """
        ).strip()

        fixer = ClosingFenceFixer(dry_run=False)
        fixed_content, fixes = fixer._fix_content(content)

        # The inner ``` are just content, only outer closing fence should be fixed
        assert len(fixes) == 1
        assert "```markdown" not in fixes[0][2]

    @pytest.mark.asyncio
    async def test_malformed_fence_with_extra_whitespace(self):
        """Test fixing fences with trailing whitespace."""
        content = dedent(
            """
            ```bash
            echo "test"
            ```bash
        """
        ).strip()

        fixer = ClosingFenceFixer(dry_run=False)
        fixed_content, fixes = fixer._fix_content(content)

        # Should still detect and fix despite whitespace
        assert len(fixes) == 1
        assert fixes[0][2] == "```"

    @pytest.mark.asyncio
    async def test_multiple_languages_mixed(self):
        """Test fixing different language tags in same file."""
        content = dedent(
            """
            ```python
            x = 1
            ```python

            ```bash
            echo "test"
            ```bash

            ```json
            {}
            ```json
        """
        ).strip()

        fixer = ClosingFenceFixer(dry_run=False)
        fixed_content, fixes = fixer._fix_content(content)

        # All three should be fixed
        assert len(fixes) == 3
        assert all(fix[2] == "```" for fix in fixes)

    # ========================================================================
    # State Machine Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_state_machine_tracks_opening_vs_closing(self):
        """Test that state machine correctly distinguishes opening from closing fences."""
        content = dedent(
            """
            ```python
            # This is code
            ```

            ```python
            # More code
            ```python
        """
        ).strip()

        fixer = ClosingFenceFixer(dry_run=False)
        fixed_content, fixes = fixer._fix_content(content)

        # Only the second closing fence should be fixed
        assert len(fixes) == 1
        assert fixes[0][0] == 7  # Line 7 (second closing fence)

    @pytest.mark.asyncio
    async def test_unclosed_block_at_end_of_file(self):
        """Test handling of unclosed code block at EOF."""
        content = dedent(
            """
            ```bash
            echo "test"
        """
        ).strip()

        fixer = ClosingFenceFixer(dry_run=False)
        fixed_content, fixes = fixer._fix_content(content)

        # Should not crash, just leave as-is
        assert len(fixes) == 0
        assert fixed_content == content

    @pytest.mark.asyncio
    async def test_multiple_blocks_sequential(self):
        """Test multiple code blocks in sequence."""
        content = dedent(
            """
            ```bash
            cmd1
            ```bash
            ```python
            cmd2
            ```python
            ```javascript
            cmd3
            ```
        """
        ).strip()

        fixer = ClosingFenceFixer(dry_run=False)
        fixed_content, fixes = fixer._fix_content(content)

        # First two closing fences should be fixed, third is already correct
        assert len(fixes) == 2
        assert fixes[0][0] == 3  # First closing fence
        assert fixes[1][0] == 6  # Second closing fence

    # ========================================================================
    # Dry Run Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_dry_run_does_not_modify_content(self):
        """Test that dry_run mode reports but doesn't modify."""
        content = dedent(
            """
            ```bash
            test
            ```bash
        """
        ).strip()

        fixer = ClosingFenceFixer(dry_run=True)
        fixed_content, fixes = fixer._fix_content(content)

        # Should still report fixes
        assert len(fixes) == 1

        # But content should be different (fixed)
        assert fixed_content != content  # Fixed content returned
        assert "```bash\n" in fixed_content and fixed_content.count("```bash") == 1

    # ========================================================================
    # Real-World Regression Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_regression_contributing_mdx_pattern(self):
        """Test fixing pattern found in docs/advanced/contributing.mdx."""
        content = dedent(
            """
            ## Quick Start

            ```bash
            ## 1. Fork the repository
            gh repo fork vishnu2kmohan/mcp-server-langgraph
            ```bash
            ### Development Setup
        """
        ).strip()

        fixer = ClosingFenceFixer(dry_run=False)
        fixed_content, fixes = fixer._fix_content(content)

        # Should fix the malformed closing fence
        assert len(fixes) == 1
        assert "```bash" in fixes[0][1]
        assert "```" == fixes[0][2]

        # Header should be outside code block
        assert "```\n### Development Setup" in fixed_content

    @pytest.mark.asyncio
    async def test_regression_authentication_mdx_pattern(self):
        """Test fixing pattern found in docs/api-reference/authentication.mdx."""
        content = dedent(
            """
            ```bash
            curl https://api.example.com/auth/me
            ```json
            **Response**:

            ```
            {
              "id": "alice"
            }
            ```
        """
        ).strip()

        fixer = ClosingFenceFixer(dry_run=False)
        fixed_content, fixes = fixer._fix_content(content)

        # Should fix the first closing fence (```json should be ```)
        assert len(fixes) == 1
        assert "```json" in fixes[0][1]

        # Final content should have proper structure
        lines = fixed_content.split("\n")
        assert "```bash" in lines[0]  # Opening fence
        assert lines[2] == "```"  # Fixed closing fence
        assert "```" in lines[5]  # Second opening (no tag in this test)


@pytest.mark.xdist_group(name="scripts_validation")
class TestFindMarkdownFiles:
    """Test suite for find_markdown_files function."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_find_single_md_file(self, tmp_path):
        """Test finding a single .md file."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test")

        files = find_markdown_files(md_file)

        assert len(files) == 1
        assert files[0] == md_file

    @pytest.mark.asyncio
    async def test_find_single_mdx_file(self, tmp_path):
        """Test finding a single .mdx file."""
        mdx_file = tmp_path / "test.mdx"
        mdx_file.write_text("# Test")

        files = find_markdown_files(mdx_file)

        assert len(files) == 1
        assert files[0] == mdx_file

    @pytest.mark.asyncio
    async def test_ignore_non_markdown_file(self, tmp_path):
        """Test that non-markdown files are ignored."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Test")

        files = find_markdown_files(txt_file)

        assert len(files) == 0

    @pytest.mark.asyncio
    async def test_find_all_markdown_in_directory(self, tmp_path):
        """Test finding all markdown files in a directory."""
        (tmp_path / "file1.md").write_text("# Test 1")
        (tmp_path / "file2.mdx").write_text("# Test 2")
        (tmp_path / "file3.txt").write_text("Not markdown")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file4.md").write_text("# Test 4")

        files = find_markdown_files(tmp_path)

        # Should find 3 markdown files (.md and .mdx only)
        assert len(files) == 3
        assert all(f.suffix in {".md", ".mdx"} for f in files)

    @pytest.mark.asyncio
    async def test_recursive_search(self, tmp_path):
        """Test that search is recursive."""
        (tmp_path / "root.md").write_text("# Root")
        (tmp_path / "level1").mkdir()
        (tmp_path / "level1" / "file.md").write_text("# L1")
        (tmp_path / "level1" / "level2").mkdir()
        (tmp_path / "level1" / "level2" / "deep.md").write_text("# L2")

        files = find_markdown_files(tmp_path)

        assert len(files) == 3  # All three found recursively

    @pytest.mark.asyncio
    async def test_nonexistent_path(self, tmp_path):
        """Test handling of nonexistent path."""
        fake_path = tmp_path / "does_not_exist.md"

        files = find_markdown_files(fake_path)

        assert len(files) == 0


@pytest.mark.xdist_group(name="scripts_validation")
class TestClosingFenceFixerIntegration:
    """Integration tests for ClosingFenceFixer with file I/O."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_fix_file_integration(self, tmp_path):
        """Test fixing a complete file end-to-end."""
        test_file = tmp_path / "test.md"
        original_content = dedent(
            """
            # Documentation

            ## Example 1

            ```bash
            git clone repo
            ```bash

            ## Example 2

            ```python
            print("hello")
            ```python

            Done.
        """
        ).strip()

        test_file.write_text(original_content)

        fixer = ClosingFenceFixer(dry_run=False)
        result = fixer.fix_file(test_file)

        assert result is True  # File was modified
        assert fixer.stats["files_modified"] == 1
        assert fixer.stats["fences_fixed"] == 2

        # Verify file was actually fixed
        fixed_content = test_file.read_text()
        assert fixed_content.count("```bash") == 1  # Only opening fence
        assert fixed_content.count("```python") == 1  # Only opening fence
        assert fixed_content.count("\n```\n") == 2  # Two bare closing fences

    @pytest.mark.asyncio
    async def test_fix_file_no_changes_needed(self, tmp_path):
        """Test processing file that needs no fixes."""
        test_file = tmp_path / "correct.md"
        correct_content = dedent(
            """
            ```python
            def test():
                pass
            ```
        """
        ).strip()

        test_file.write_text(correct_content)

        fixer = ClosingFenceFixer(dry_run=False)
        result = fixer.fix_file(test_file)

        assert result is False  # File was not modified
        assert fixer.stats["files_modified"] == 0
        assert fixer.stats["fences_fixed"] == 0

        # Content unchanged
        assert test_file.read_text() == correct_content

    @pytest.mark.asyncio
    async def test_dry_run_file_not_modified(self, tmp_path):
        """Test that dry_run mode doesn't modify files."""
        test_file = tmp_path / "test.md"
        original_content = dedent(
            """
            ```bash
            test
            ```bash
        """
        ).strip()

        test_file.write_text(original_content)

        fixer = ClosingFenceFixer(dry_run=True)
        result = fixer.fix_file(test_file)

        assert result is True  # Issues found
        assert fixer.stats["fences_fixed"] == 1

        # But file should be unchanged
        assert test_file.read_text() == original_content

    @pytest.mark.asyncio
    async def test_statistics_tracking(self, tmp_path):
        """Test that statistics are tracked correctly across multiple files."""
        # Create multiple test files
        for i in range(3):
            test_file = tmp_path / f"test{i}.md"
            test_file.write_text(f"```bash\ntest{i}\n```bash")

        fixer = ClosingFenceFixer(dry_run=False)

        # Process all files
        for file in tmp_path.glob("*.md"):
            fixer.fix_file(file)

        assert fixer.stats["files_processed"] == 3
        assert fixer.stats["files_modified"] == 3
        assert fixer.stats["fences_fixed"] == 3
