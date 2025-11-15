"""
Unit tests for code block language validator.

Tests validate that:
1. All code blocks have language identifiers
2. Language tags are valid/recognized
3. Inline code is ignored (only fenced code blocks validated)
4. Template files are excluded
"""

import gc
import sys
from pathlib import Path

import pytest

# Add scripts directory to path - environment-agnostic
_scripts_dir = Path(__file__).resolve().parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(_scripts_dir))


from validators.codeblock_validator import CodeBlockError, CodeBlockValidator, MissingLanguageError  # noqa: E402

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testcodeblockvalidator")
class TestCodeBlockValidator:
    """Test suite for CodeBlockValidator."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def validator(self, tmp_path):
        """Create validator with temporary directory."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        return CodeBlockValidator(docs_dir)

    def test_valid_code_blocks_pass(self, tmp_path):
        """Test that code blocks with language tags pass."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "page.mdx").write_text(
            """---
title: "Test"
description: "Test"
---

```python
def hello():
    print("Hello")
```

```bash
echo "test"
```
"""
        )

        # Act
        validator = CodeBlockValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid
        assert len(result.errors) == 0
        assert result.stats["total_code_blocks"] == 2
        assert result.stats["blocks_without_language"] == 0

    def test_missing_language_detected(self, tmp_path):
        """Test that code blocks without language tags are detected."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "page.mdx").write_text(
            """---
title: "Test"
description: "Test"
---

```
code without language
```
"""
        )

        # Act
        validator = CodeBlockValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        assert len(result.errors) == 1
        assert isinstance(result.errors[0], MissingLanguageError)

    def test_inline_code_ignored(self, tmp_path):
        """Test that inline code (backticks) is ignored."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "page.mdx").write_text(
            """---
title: "Test"
description: "Test"
---

Use `inline code` here and `another` there.

```python
def test():
    pass
```
"""
        )

        # Act
        validator = CodeBlockValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid
        assert result.stats["total_code_blocks"] == 1  # Only fenced block

    def test_multiple_code_blocks_in_file(self, tmp_path):
        """Test that all code blocks in a file are validated."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "page.mdx").write_text(
            """---
title: "Test"
description: "Test"
---

```python
# Valid
```

```
# Missing language
```

```bash
# Valid
```

```
# Another missing
```
"""
        )

        # Act
        validator = CodeBlockValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        assert len(result.errors) == 2  # Two blocks without language
        assert result.stats["total_code_blocks"] == 4
        assert result.stats["blocks_without_language"] == 2

    def test_template_files_excluded(self, tmp_path):
        """Test that template files are excluded from validation."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        templates_dir = docs_dir / ".mintlify" / "templates"
        templates_dir.mkdir(parents=True)

        (templates_dir / "template.mdx").write_text(
            """---
title: "Template"
---

```
template code without language
```
"""
        )

        # Act
        validator = CodeBlockValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid  # Templates excluded
        assert result.stats["total_files"] == 0

    def test_common_languages_recognized(self, tmp_path):
        """Test that common programming languages are recognized."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "page.mdx").write_text(
            """---
title: "Test"
description: "Test"
---

```python
# Python
```

```javascript
// JavaScript
```

```typescript
// TypeScript
```

```bash
# Bash
```

```yaml
# YAML
```

```json
{}
```

```dockerfile
FROM ubuntu
```

```sql
SELECT * FROM users;
```
"""
        )

        # Act
        validator = CodeBlockValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid
        assert result.stats["total_code_blocks"] == 8

    def test_indented_code_blocks(self, tmp_path):
        """Test that indented code blocks in lists are detected."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "page.mdx").write_text(
            """---
title: "Test"
description: "Test"
---

Steps:
1. First step
   ```python
   def test():
       pass
   ```

2. Second step
   ```
   code without language
   ```
"""
        )

        # Act
        validator = CodeBlockValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        assert len(result.errors) == 1

    def test_statistics_accurate(self, tmp_path):
        """Test that statistics are accurately collected."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "page1.mdx").write_text(
            """---
title: "Page 1"
description: "Test"
---

```python
valid
```
"""
        )

        (docs_dir / "page2.mdx").write_text(
            """---
title: "Page 2"
description: "Test"
---

```
missing
```

```bash
valid
```
"""
        )

        # Act
        validator = CodeBlockValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.stats["total_files"] == 2
        assert result.stats["total_code_blocks"] == 3
        assert result.stats["blocks_without_language"] == 1

    def test_nested_code_blocks_in_callouts(self, tmp_path):
        """Test code blocks inside MDX callouts/notes."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "page.mdx").write_text(
            """---
title: "Test"
description: "Test"
---

<Note>
```python
code in note
```
</Note>

<Warning>
```
missing language in warning
```
</Warning>
"""
        )

        # Act
        validator = CodeBlockValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        assert len(result.errors) == 1

    def test_code_blocks_with_attributes(self, tmp_path):
        """Test code blocks with additional attributes."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "page.mdx").write_text(
            """---
title: "Test"
description: "Test"
---

```python {1,3-5}
# Python with line highlighting
```

```bash showLineNumbers
# Bash with line numbers
```

```json title="config.json"
{}
```
"""
        )

        # Act
        validator = CodeBlockValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert result.is_valid
        assert result.stats["total_code_blocks"] == 3

    def test_error_includes_line_number(self, tmp_path):
        """Test that errors include approximate line numbers."""
        # Arrange
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "page.mdx").write_text(
            """---
title: "Test"
description: "Test"
---

# Heading

Some text here.

```
code without language on line 11
```
"""
        )

        # Act
        validator = CodeBlockValidator(docs_dir)
        result = validator.validate()

        # Assert
        assert not result.is_valid
        assert len(result.errors) == 1
        error = result.errors[0]
        assert hasattr(error, "line_number")
        assert error.line_number > 0
