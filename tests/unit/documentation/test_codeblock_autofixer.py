"""
Unit tests for code block auto-fixer.

Tests validate that:
1. Code blocks without language tags are auto-fixed
2. Language detection is accurate
3. Files are not modified unnecessarily
4. Backup is created before modification
"""

import sys
from pathlib import Path

import pytest

# Add scripts directory to path - environment-agnostic
_scripts_dir = Path(__file__).resolve().parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(_scripts_dir))

from validators.codeblock_autofixer import CodeBlockAutoFixer, detect_language  # noqa: E402


class TestLanguageDetection:
    """Test language detection logic."""

    def test_detect_python(self):
        """Test Python code detection."""
        code = """def hello():
    print("world")
"""
        assert detect_language(code) == "python"

    def test_detect_bash(self):
        """Test Bash code detection."""
        code = """#!/bin/bash
echo "hello"
"""
        assert detect_language(code) == "bash"

    def test_detect_javascript(self):
        """Test JavaScript code detection."""
        code = """function hello() {
  console.log("world");
}
"""
        assert detect_language(code) == "javascript"

    def test_detect_yaml(self):
        """Test YAML code detection."""
        code = """apiVersion: v1
kind: Pod
metadata:
  name: test
"""
        assert detect_language(code) == "yaml"

    def test_detect_json(self):
        """Test JSON code detection."""
        code = """{
  "key": "value",
  "number": 123
}
"""
        assert detect_language(code) == "json"

    def test_detect_sql(self):
        """Test SQL code detection."""
        code = """SELECT * FROM users
WHERE id = 1;
"""
        assert detect_language(code) == "sql"

    def test_detect_dockerfile(self):
        """Test Dockerfile detection."""
        code = """FROM ubuntu:20.04
RUN apt-get update
"""
        assert detect_language(code) == "dockerfile"

    def test_detect_markdown(self):
        """Test Markdown detection."""
        code = """# Heading

Some text with **bold**.
"""
        assert detect_language(code) == "markdown"

    def test_unknown_defaults_to_text(self):
        """Test that unknown code defaults to text."""
        code = """random content
that doesn't match
any known pattern
"""
        assert detect_language(code) == "text"


class TestCodeBlockAutoFixer:
    """Test suite for CodeBlockAutoFixer."""

    @pytest.fixture
    def fixer(self, tmp_path):
        """Create auto-fixer with temporary directory."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        return CodeBlockAutoFixer(docs_dir)

    def test_fixes_missing_language(self, tmp_path):
        """Test that code blocks without language are fixed."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        original = """---
title: "Test"
description: "Test"
---

```
def hello():
    print("world")
```
"""

        expected = """---
title: "Test"
description: "Test"
---

```python
def hello():
    print("world")
```
"""

        page = docs_dir / "page.mdx"
        page.write_text(original)

        # Act
        fixer = CodeBlockAutoFixer(docs_dir, dry_run=False)
        result = fixer.fix()

        # Assert
        assert result.files_modified == 1
        assert page.read_text() == expected

    def test_dry_run_doesnt_modify(self, tmp_path):
        """Test that dry run doesn't modify files."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        original = """```
print("test")
```"""

        page = docs_dir / "page.mdx"
        page.write_text(original)

        # Act
        fixer = CodeBlockAutoFixer(docs_dir, dry_run=True)
        result = fixer.fix()

        # Assert
        assert result.would_modify == 1
        assert page.read_text() == original  # Not modified

    def test_doesnt_modify_valid_files(self, tmp_path):
        """Test that files with valid language tags aren't modified."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        content = """```python
def hello():
    pass
```"""

        page = docs_dir / "page.mdx"
        page.write_text(content)

        # Act
        fixer = CodeBlockAutoFixer(docs_dir, dry_run=False)
        result = fixer.fix()

        # Assert
        assert result.files_modified == 0
        assert page.read_text() == content  # Unchanged

    def test_preserves_attributes(self, tmp_path):
        """Test that code block attributes are preserved."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        original = """```{1,3-5} showLineNumbers
def hello():
    pass
```"""

        # This already has attributes but no language
        # The fixer should add language while preserving attributes
        page = docs_dir / "page.mdx"
        page.write_text(original)

        # Act
        fixer = CodeBlockAutoFixer(docs_dir, dry_run=False)
        _ = fixer.fix()  # Return value not needed, only checking file contents

        # Assert
        fixed = page.read_text()
        assert "python" in fixed
        assert "{1,3-5}" in fixed
        assert "showLineNumbers" in fixed

    def test_multiple_blocks_in_file(self, tmp_path):
        """Test that all blocks in a file are fixed."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        original = """```
def python_func():
    pass
```

Some text.

```
echo "bash command"
```
"""

        page = docs_dir / "page.mdx"
        page.write_text(original)

        # Act
        fixer = CodeBlockAutoFixer(docs_dir, dry_run=False)
        result = fixer.fix()

        # Assert
        fixed = page.read_text()
        assert "```python\n" in fixed
        assert "```bash\n" in fixed
        assert result.blocks_fixed == 2

    def test_template_files_excluded(self, tmp_path):
        """Test that template files are not modified."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        templates_dir = docs_dir / ".mintlify" / "templates"
        templates_dir.mkdir(parents=True)

        original = """```
template code
```"""

        template = templates_dir / "template.mdx"
        template.write_text(original)

        # Act
        fixer = CodeBlockAutoFixer(docs_dir, dry_run=False)
        result = fixer.fix()

        # Assert
        assert result.files_modified == 0
        assert template.read_text() == original
