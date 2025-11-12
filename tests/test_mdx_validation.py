#!/usr/bin/env python3
"""
Test suite for MDX validation scripts.

This test suite follows TDD principles to ensure MDX syntax errors
are caught and fixed correctly, preventing regressions.
"""

import pytest
import tempfile
from pathlib import Path
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from fix_mdx_syntax import fix_code_block_closings


class TestCodeBlockClosingFixes:
    """Test fixes for malformed code block closings."""

    def test_fixes_duplicate_lang_after_closing(self):
        """Test Pattern 1: ``` followed by ```bash on next line."""
        content = """```bash
echo "hello"
```
```bash
Some text here
"""
        fixed, count = fix_code_block_closings(content)
        assert count == 1
        # The duplicate ```bash should be removed and replaced with blank line
        assert "```\n\nSome text here" in fixed
        assert fixed.count("```bash") == 1  # Only the original remains

    def test_fixes_lang_before_code_group_closing(self):
        """Test Pattern 2: ```bash before </CodeGroup>."""
        content = """<CodeGroup>
```bash
echo "test"
```bash
</CodeGroup>"""
        fixed, count = fix_code_block_closings(content)
        assert count == 1
        assert "```\n</CodeGroup>" in fixed
        assert "```bash\n</CodeGroup>" not in fixed

    def test_fixes_lang_before_mdx_tags(self):
        """Test Pattern 3: ```bash before <Note> or other MDX tags."""
        content = """```bash
echo "test"
```bash
<Note>
This is a note
</Note>"""
        fixed, count = fix_code_block_closings(content)
        assert count == 1
        assert "```\n<Note>" in fixed
        assert "```bash\n<Note>" not in fixed

    def test_multiple_patterns_in_one_file(self):
        """Test fixing multiple patterns in a single file."""
        content = """```bash
echo "test1"
```
```python
print("test2")

<CodeGroup>
```bash
echo "test3"
```json
</CodeGroup>

```yaml
key: value
```bash
<Warning>
Test warning
</Warning>"""
        fixed, count = fix_code_block_closings(content)
        assert count >= 2  # At least the duplicates should be fixed

    def test_preserves_valid_code_blocks(self):
        """Test that valid code blocks are not modified."""
        content = """```bash
echo "hello"
```

```python
print("world")
```

<CodeGroup>
```javascript JavaScript
console.log("test");
```
</CodeGroup>"""
        fixed, count = fix_code_block_closings(content)
        assert count == 0
        assert fixed == content

    def test_handles_empty_content(self):
        """Test handling of empty content."""
        content = ""
        fixed, count = fix_code_block_closings(content)
        assert count == 0
        assert fixed == content

    def test_handles_no_code_blocks(self):
        """Test handling of content with no code blocks."""
        content = """# Hello World

This is some markdown without code blocks.

<Note>
Just a note
</Note>"""
        fixed, count = fix_code_block_closings(content)
        assert count == 0
        assert fixed == content

    def test_all_supported_languages(self):
        """Test that all supported languages are handled."""
        languages = ['bash', 'python', 'javascript', 'json', 'yaml', 'text', 'ini', 'hcl']

        for lang in languages:
            content = f"""```{lang}
test content
```
```{lang}
<Note>Test</Note>"""
            fixed, count = fix_code_block_closings(content)
            assert count == 1, f"Failed to fix {lang} pattern"
            assert f"```{lang}\n<Note>" not in fixed


class TestRealWorldExamples:
    """Test cases based on actual errors found in the documentation."""

    def test_api_keys_pattern(self):
        """Test the pattern found in api-keys.mdx."""
        content = """<CodeGroup>
```bash cURL
curl -X POST https://api.example.com
```
```python
```python Python
import httpx
```
</CodeGroup>"""
        fixed, count = fix_code_block_closings(content)
        assert count >= 1
        # The duplicate ```python should be removed
        assert "```\n\n```python Python" in fixed or "```python Python" in fixed
        # Should not have duplicate pattern
        lines = fixed.split('\n')
        consecutive_python = any(
            lines[i].strip() == '```' and
            lines[i+1].strip() == '```python'
            for i in range(len(lines)-1)
        )
        assert not consecutive_python, "Should not have ```\\n```python pattern"

    def test_authentication_pattern(self):
        """Test the pattern found in authentication.mdx."""
        content = """{
  "token": "abc123"
}
```bash
**Status Codes**:"""
        fixed, count = fix_code_block_closings(content)
        assert count == 1
        # Pattern 4 should fix ```bash before markdown text
        assert "```\n**Status Codes**:" in fixed or "```bash\n**Status Codes**:" not in fixed

    def test_response_field_pattern(self):
        """Test pattern with ResponseField tags."""
        content = """```json
{
  "error": "not_found"
}
```
</ResponseField>"""
        fixed, count = fix_code_block_closings(content)
        # This specific pattern might not be caught if ``` is already correct
        # But we should ensure it doesn't break valid structure
        assert "```\n</ResponseField>" in fixed

    def test_nested_mdx_components(self):
        """Test code blocks inside nested MDX components."""
        content = """<AccordionGroup>
  <Accordion title="Test">
    ```bash
    echo "test"
    ```bash
    <Note>Important</Note>
  </Accordion>
</AccordionGroup>"""
        fixed, count = fix_code_block_closings(content)
        assert count == 1
        assert "```bash\n    <Note>" not in fixed


class TestEdgeCases:
    """Test edge cases and potential issues."""

    def test_code_block_with_title(self):
        """Test that labeled code blocks are preserved."""
        content = """```bash Install Dependencies
npm install
```

```python Run Script
python script.py
```"""
        fixed, count = fix_code_block_closings(content)
        assert count == 0
        assert fixed == content

    def test_inline_code_not_affected(self):
        """Test that inline code is not affected."""
        content = """Use `npm install` to install dependencies.

The `<=` operator compares values.

Run ```bash echo "test"``` inline."""
        fixed, count = fix_code_block_closings(content)
        # Should not modify inline code
        assert "`npm install`" in fixed
        assert "`<=`" in fixed

    def test_multiline_code_block_content(self):
        """Test code blocks with multiple lines are preserved."""
        content = """```bash
#!/bin/bash
echo "Line 1"
echo "Line 2"
echo "Line 3"
```

Next section"""
        fixed, count = fix_code_block_closings(content)
        assert count == 0
        assert "Line 1" in fixed
        assert "Line 2" in fixed
        assert "Line 3" in fixed


@pytest.fixture
def temp_mdx_file():
    """Create a temporary MDX file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mdx', delete=False) as f:
        yield Path(f.name)
    Path(f.name).unlink(missing_ok=True)


class TestFileOperations:
    """Test file reading and writing operations."""

    def test_can_read_and_write_file(self, temp_mdx_file):
        """Test basic file I/O."""
        content = """```bash
echo "test"
```
```bash
<Note>Test</Note>"""

        temp_mdx_file.write_text(content)

        # Import fix_file function
        from fix_mdx_syntax import fix_file

        fixes, changes = fix_file(temp_mdx_file, dry_run=False)

        assert fixes > 0

        # Read back and verify
        fixed_content = temp_mdx_file.read_text()
        assert "```bash\n<Note>" not in fixed_content

    def test_dry_run_does_not_modify_file(self, temp_mdx_file):
        """Test that dry run doesn't modify files."""
        content = """```bash
test
```
```bash
<Note>Test</Note>"""

        temp_mdx_file.write_text(content)
        original_content = temp_mdx_file.read_text()

        from fix_mdx_syntax import fix_file

        fixes, changes = fix_file(temp_mdx_file, dry_run=True)

        assert fixes > 0
        assert temp_mdx_file.read_text() == original_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
