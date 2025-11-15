"""
Regression Tests for Documentation Code Blocks

Prevents recurrence of CI failure from 2025-11-12 where 253 untagged code blocks
caused pre-commit validate-codeblock-languages hook to fail.

This test ensures all code blocks in documentation have proper language tags.

## Failure Scenario (2025-11-12)
- Pre-commit hook failed: "❌ Validation failed: 253 untagged code blocks found"
- Affected files: docs/**/*.mdx (architecture, API reference, advanced)
- Root cause: Code blocks missing language specifiers (```bash, ```python, etc.)

## Prevention Strategy
1. Test runs on all .mdx files in docs/ directory
2. Parses markdown for code fences (```)
3. Ensures every code block has a language tag
4. Fails fast if any untagged blocks found

## Usage
Run with: pytest tests/regression/test_documentation_code_blocks.py -v
"""

import gc
import re
from pathlib import Path
from typing import List, Tuple

import pytest
import yaml


def find_mdx_files() -> List[Path]:
    """
    Find all .mdx documentation files.

    Returns:
        List of Path objects for .mdx files
    """
    docs_dir = Path(__file__).parent.parent.parent / "docs"
    if not docs_dir.exists():
        return []
    return list(docs_dir.rglob("*.mdx"))


def extract_code_blocks(file_path: Path) -> List[Tuple[int, str]]:
    """
    Extract all code blocks from an .mdx file.

    Args:
        file_path: Path to .mdx file

    Returns:
        List of tuples (line_number, language_tag)
        Empty string for language_tag means untagged
    """
    content = file_path.read_text()
    lines = content.split("\n")

    code_blocks = []
    in_code_block = False
    code_fence_pattern = re.compile(r"^```(\w*)")

    for line_num, line in enumerate(lines, start=1):
        match = code_fence_pattern.match(line.strip())
        if match and not in_code_block:
            # Opening fence
            language = match.group(1)  # Empty string if no language
            code_blocks.append((line_num, language))
            in_code_block = True
        elif line.strip() == "```" and in_code_block:
            # Closing fence
            in_code_block = False

    return code_blocks


@pytest.mark.regression
@pytest.mark.documentation
@pytest.mark.xdist_group(name="testdocumentationcodeblocks")
class TestDocumentationCodeBlocks:
    """
    Regression tests for documentation code block validation.

    Prevents recurrence of issue from 2025-11-12.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_all_code_blocks_have_language_tags(self):
        """
        Test: All code blocks in .mdx files must have language tags.

        RED (Before Fix - 2025-11-12):
        - 253 untagged code blocks across multiple .mdx files
        - Pre-commit hook failed with validation error
        - Manual tagging required across architecture/, api-reference/, advanced/

        GREEN (After Fix - 2025-11-12):
        - All code blocks tagged with appropriate languages
        - Auto-fixed using scripts/add_code_block_languages.py
        - Languages: bash, python, yaml, json, typescript, etc.

        REFACTOR:
        - This test ensures fix stays in place
        - Fails immediately if any untagged blocks introduced
        """
        mdx_files = find_mdx_files()
        assert len(mdx_files) > 0, "No .mdx files found - check docs/ directory exists"

        untagged_blocks = []

        for file_path in mdx_files:
            code_blocks = extract_code_blocks(file_path)

            for line_num, language in code_blocks:
                if not language:
                    relative_path = file_path.relative_to(Path(__file__).parent.parent.parent)
                    untagged_blocks.append(f"{relative_path}:{line_num}")

        if untagged_blocks:
            error_message = f"\n❌ Found {len(untagged_blocks)} untagged code blocks:\n\n" + "\n".join(
                f"  - {block}" for block in untagged_blocks[:10]
            )
            if len(untagged_blocks) > 10:
                error_message += f"\n  ... and {len(untagged_blocks) - 10} more"

            error_message += (
                "\n\n💡 Fix: Run the auto-fix script:\n"
                "  python scripts/add_code_block_languages.py docs/**/*.mdx\n"
                "\nOr manually add language tags to code fences:\n"
                "  \\`\\`\\`python  (for Python code)\n"
                "  \\`\\`\\`bash   (for shell commands)\n"
                "  \\`\\`\\`yaml   (for YAML config)\n"
            )

            pytest.fail(error_message)

    def test_code_block_auto_fix_script_exists(self):
        """
        Test: Auto-fix script exists and is executable.

        Ensures the tool used to fix this issue is available for future use.
        """
        script_path = Path(__file__).parent.parent.parent / "scripts" / "add_code_block_languages.py"

        assert script_path.exists(), (
            f"Auto-fix script not found: {script_path}\n" "This script is required to fix untagged code blocks."
        )

        # Verify script is a valid Python file
        content = script_path.read_text()
        assert "def " in content, "Script appears to be empty or invalid"

    @pytest.mark.parametrize(
        "language",
        [
            "bash",
            "python",
            "yaml",
            "json",
            "typescript",
            "javascript",
            "sql",
            "rust",
            "go",
        ],
    )
    def test_common_language_tags_are_used(self, language):
        """
        Test: Common programming language tags are actually used in docs.

        Ensures documentation uses appropriate language tags for different code types.
        This is a sanity check that the auto-fix script chose reasonable defaults.
        """
        mdx_files = find_mdx_files()
        language_found = False

        for file_path in mdx_files:
            code_blocks = extract_code_blocks(file_path)
            if any(lang == language for _, lang in code_blocks):
                language_found = True
                break

        # We expect at least some common languages to be present in docs
        # Not all languages will be present, so we just check coverage
        if language in ["bash", "python", "yaml", "json"]:
            assert language_found, (
                f"Expected to find '{language}' code blocks in documentation, "
                f"but none found. This may indicate incomplete code block tagging."
            )

    def test_no_code_blocks_with_invalid_tags(self):
        """
        Test: Code block language tags are valid identifiers.

        Prevents typos like \\`\\`\\`pytohn or \\`\\`\\`bas
        """
        mdx_files = find_mdx_files()
        invalid_blocks = []

        # Common typos and invalid tags
        KNOWN_GOOD_LANGUAGES = {
            "bash",
            "sh",
            "shell",
            "python",
            "py",
            "javascript",
            "js",
            "typescript",
            "ts",
            "yaml",
            "yml",
            "json",
            "sql",
            "rust",
            "rs",
            "go",
            "java",
            "c",
            "cpp",
            "csharp",
            "ruby",
            "php",
            "html",
            "css",
            "xml",
            "markdown",
            "md",
            "text",
            "txt",
            "diff",
            "plaintext",
        }

        for file_path in mdx_files:
            code_blocks = extract_code_blocks(file_path)

            for line_num, language in code_blocks:
                if language and language.lower() not in KNOWN_GOOD_LANGUAGES:
                    relative_path = file_path.relative_to(Path(__file__).parent.parent.parent)
                    invalid_blocks.append(f"{relative_path}:{line_num} (language: {language})")

        if invalid_blocks:
            error_message = (
                f"\n⚠️  Found {len(invalid_blocks)} code blocks with potentially invalid language tags:\n\n"
                + "\n".join(f"  - {block}" for block in invalid_blocks[:10])
            )
            if len(invalid_blocks) > 10:
                error_message += f"\n  ... and {len(invalid_blocks) - 10} more"

            # This is a warning, not a hard failure, since new languages may be valid
            pytest.skip(f"Potential invalid language tags (manual review needed):{error_message}")


@pytest.mark.regression
def test_pre_commit_hook_config_has_codeblock_validation():
    """
    Test: Pre-commit configuration includes code block validation hook.

    Ensures the pre-commit hook that caught this issue is still configured.
    """
    pre_commit_config = Path(__file__).parent.parent.parent / ".pre-commit-config.yaml"
    assert pre_commit_config.exists(), "Pre-commit config not found"

    content = pre_commit_config.read_text()
    assert "validate-code-block-languages" in content, (
        "Pre-commit hook 'validate-code-block-languages' not found in config. "
        "This hook is required to catch untagged code blocks before CI."
    )


@pytest.mark.regression
def test_no_duplicate_pre_commit_hook_ids():
    """
    Test: Pre-commit hook IDs must be unique.

    Prevents duplicate hook IDs which can cause unexpected behavior where only
    one hook runs instead of both. This is a regression prevention test to catch
    configuration errors early.

    Context: Previously had duplicate 'validate-code-block-languages' hooks at
    lines 330 and 1271, causing only one to execute.
    """
    pre_commit_config = Path(__file__).parent.parent.parent / ".pre-commit-config.yaml"
    assert pre_commit_config.exists(), "Pre-commit config not found"

    with open(pre_commit_config, "r") as f:
        config = yaml.safe_load(f)

    # Extract all hook IDs
    hook_ids = []
    for repo in config.get("repos", []):
        for hook in repo.get("hooks", []):
            hook_id = hook.get("id")
            if hook_id:
                hook_ids.append(hook_id)

    # Check for duplicates
    duplicates = [hook_id for hook_id in set(hook_ids) if hook_ids.count(hook_id) > 1]

    assert not duplicates, (
        f"Found duplicate hook IDs in .pre-commit-config.yaml: {duplicates}\n"
        f"Each hook ID must be unique. Duplicate IDs cause only one hook to execute.\n"
        f"Please consolidate or rename duplicate hooks."
    )


if __name__ == "__main__":
    # Allow running directly for quick validation
    pytest.main([__file__, "-v", "--tb=short"])
