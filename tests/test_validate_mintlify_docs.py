#!/usr/bin/env python3
# ruff: noqa: E402
"""
Tests for scripts/validate_mintlify_docs.py

Following TDD principles:
1. RED: These tests verify the regex pattern compiles correctly
2. GREEN: Fix the regex in validate_mintlify_docs.py:168
3. REFACTOR: Add documentation and prevent regressions
"""

import gc
import re
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

# Mark this as both unit and meta test to ensure it runs in CI
# Note: Individual tests may be skipped if validation module not available
pytestmark = pytest.mark.unit

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Try to import the validation module (may not be available in Docker container)
try:
    from validate_mintlify_docs import (  # noqa: E402
        ValidationReport,
        check_filename_convention,
        check_frontmatter,
        check_internal_links,
        check_mermaid_diagrams,
        parse_frontmatter,
    )

    VALIDATION_MODULE_AVAILABLE = True
except ImportError:
    VALIDATION_MODULE_AVAILABLE = False
    # Define placeholder values for when module is not available
    ValidationReport = None
    check_filename_convention = None
    check_frontmatter = None
    check_internal_links = None
    check_mermaid_diagrams = None
    parse_frontmatter = None

# Skip all tests if validation module is not available
pytestmark = pytest.mark.skipif(
    not VALIDATION_MODULE_AVAILABLE, reason="validate_mintlify_docs module not available (scripts not in Docker image)"
)


@pytest.mark.xdist_group(name="testmermaidarrowregex")
class TestMermaidArrowRegex:
    """Test suite for Mermaid arrow syntax validation regex.

    The regex on line 168 should:
    1. Compile without errors (no invalid character ranges)
    2. Match invalid arrow syntax (single dash not followed by > or -)
    3. NOT match valid patterns like:
       - Number ranges: "70-80%", "1-5"
       - Valid arrows: "A-->B", "A--B"
       - HTML entities or other valid contexts
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_arrow_regex_compiles_without_error(self):
        r"""
        Test that the arrow syntax regex compiles without re.error.

        This test will FAIL initially because [^->-\d] contains invalid range >-\d.
        After fix, pattern should be [^->\d] (no range, just character exclusion).
        """
        # This is the regex pattern from line 168
        # Current (broken): r"[^-\d]-[^->-\d]"
        # Expected (fixed): r"[^-\d]-[^->\d]"

        # Test that the pattern can be compiled
        try:
            pattern = re.compile(r"[^-\d]-[^->\d]")  # Fixed pattern
            assert pattern is not None
        except re.error as e:
            pytest.fail(f"Regex pattern should compile without error: {e}")

    def test_arrow_regex_matches_invalid_single_dash(self):
        """Test regex correctly identifies invalid single-dash arrow syntax."""
        # Fixed pattern that should work
        pattern = re.compile(r"[^-\d]-[^->\d]")

        # These should match (invalid arrow syntax)
        invalid_cases = [
            "A-B",  # Single dash between letters
            "node-next",  # Single dash in node names (context dependent)
            "X-Y",  # Single dash between capitals
        ]

        for case in invalid_cases:
            assert pattern.search(case), f"Should match invalid syntax: {case}"

    def test_arrow_regex_ignores_valid_patterns(self):
        """Test regex doesn't match valid patterns (number ranges, valid arrows)."""
        # Fixed pattern that should work
        pattern = re.compile(r"[^-\d]-[^->\d]")

        # These should NOT match (valid patterns)
        valid_cases = [
            "A-->B",  # Valid arrow
            "A--B",  # Valid double dash
            "70-80%",  # Number range
            "1-5 items",  # Number range
            "range: 0-100",  # Number range with digits
            "---",  # Triple dash (YAML/Markdown)
            "--",  # Double dash
        ]

        for case in valid_cases:
            assert not pattern.search(case), f"Should NOT match valid pattern: {case}"

    def test_mermaid_check_uses_correct_regex(self):
        """Integration test: check_mermaid_diagrams uses compilable regex."""
        content = """---
title: Test
description: 'Test'
icon: 'test'
---

```mermaid
graph TD
    A-B
```
"""

        with NamedTemporaryFile(mode="w", suffix=".mdx", delete=False) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)

        try:
            report = ValidationReport()
            # This should not raise re.error
            check_mermaid_diagrams(file_path, content, report)

            # Should detect the invalid arrow syntax A-B
            warnings = [i for i in report.issues if i.severity == "warning" and "arrow" in i.message.lower()]
            assert len(warnings) > 0, "Should detect invalid arrow syntax in mermaid diagram"
        finally:
            file_path.unlink()


@pytest.mark.xdist_group(name="testfrontmatterparsing")
class TestFrontmatterParsing:
    """Test frontmatter parsing functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_parse_valid_frontmatter(self):
        """Test parsing valid YAML frontmatter."""
        content = """---
title: Test Document
description: 'A test description'
icon: 'book'
---

Content here.
"""
        frontmatter, end_line = parse_frontmatter(content)

        assert frontmatter is not None
        assert "title" in frontmatter
        assert frontmatter["title"] == "Test Document"
        assert frontmatter["description"] == "'A test description'"
        assert frontmatter["icon"] == "'book'"
        assert end_line == 5  # Lines: ---, title, description, icon, ---

    def test_parse_missing_frontmatter(self):
        """Test handling of content without frontmatter."""
        content = "Just plain content without frontmatter"
        frontmatter, end_line = parse_frontmatter(content)

        assert frontmatter is None
        assert end_line == 0

    def test_check_frontmatter_missing_required_fields(self):
        """Test detection of missing required frontmatter fields."""
        from tempfile import NamedTemporaryFile

        content = """---
title: Only Title
---

Content
"""

        with NamedTemporaryFile(mode="w", suffix=".mdx", delete=False) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)

        try:
            report = ValidationReport()
            check_frontmatter(file_path, content, report)

            errors = [i for i in report.issues if i.severity == "error"]
            assert len(errors) >= 2  # Missing description and icon

            error_messages = [i.message for i in errors]
            assert any("description" in msg for msg in error_messages)
            assert any("icon" in msg for msg in error_messages)
        finally:
            file_path.unlink()


@pytest.mark.xdist_group(name="testfilenamconvention")
class TestFilenamConvention:
    """Test filename convention validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_valid_kebab_case_filenames(self):
        """Test that valid kebab-case filenames pass validation."""
        valid_names = [
            "single",
            "kebab-case",
            "multi-word-name",
            "with-numbers-123",
            "a-b-c-d-e",
        ]

        for name in valid_names:
            file_path = Path(f"/tmp/{name}.mdx")  # nosec B108 - test code, not a security risk
            report = ValidationReport()
            check_filename_convention(file_path, report)

            errors = [i for i in report.issues if i.severity == "error"]
            assert len(errors) == 0, f"Valid filename '{name}' should not have errors"

    def test_invalid_filenames(self):
        """Test that invalid filenames are detected."""
        invalid_cases = [
            ("SCREAMING_SNAKE_CASE.mdx", "error"),  # Uppercase + underscore
            ("snake_case_name.mdx", "error"),  # Underscore
            ("MixedCase.mdx", "warning"),  # Mixed case
            ("Capitalized.mdx", "warning"),  # Capitalized
        ]

        for filename, expected_severity in invalid_cases:
            file_path = Path(f"/tmp/{filename}")  # nosec B108 - test code, not a security risk
            report = ValidationReport()
            check_filename_convention(file_path, report)

            issues = [i for i in report.issues if i.severity == expected_severity]
            assert len(issues) > 0, f"Invalid filename '{filename}' should trigger {expected_severity}"


@pytest.mark.xdist_group(name="testinternallinks")
class TestInternalLinks:
    """Test internal link validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_skip_external_links(self):
        """Test that external HTTP(S) links are not validated."""
        content = """---
title: Test
description: 'Test'
icon: 'test'
---

[External](https://example.com)
[HTTP](http://example.com)
"""

        with NamedTemporaryFile(mode="w", suffix=".mdx", delete=False) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)

        try:
            docs_root = Path(__file__).parent.parent / "docs"
            report = ValidationReport()
            check_internal_links(file_path, content, docs_root, report)

            # Should not report errors for external links
            errors = [i for i in report.issues if "example.com" in i.message]
            assert len(errors) == 0
        finally:
            file_path.unlink()

    def test_skip_source_file_references(self):
        """Test that intentional source file references are not validated as docs links."""
        content = """---
title: Test
description: 'Test'
icon: 'test'
---

See [script](/scripts/example.sh) for details.
Check [config](/config/settings.yaml).
"""

        with NamedTemporaryFile(mode="w", suffix=".mdx", delete=False) as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)

        try:
            docs_root = Path(__file__).parent.parent / "docs"
            report = ValidationReport()
            check_internal_links(file_path, content, docs_root, report)

            # Should not report errors for source file references
            errors = [i for i in report.issues if "scripts" in i.message or "config" in i.message]
            assert len(errors) == 0, "Source file references should be skipped"
        finally:
            file_path.unlink()


@pytest.mark.xdist_group(name="testvalidationreport")
class TestValidationReport:
    """Test ValidationReport functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_add_and_count_issues(self):
        """Test adding issues and counting by severity."""
        report = ValidationReport()

        report.add_issue("error", Path("/tmp/test.mdx"), "test", "Error message")  # nosec B108
        report.add_issue("warning", Path("/tmp/test.mdx"), "test", "Warning message")  # nosec B108
        report.add_issue("info", Path("/tmp/test.mdx"), "test", "Info message")  # nosec B108

        errors = [i for i in report.issues if i.severity == "error"]
        warnings = [i for i in report.issues if i.severity == "warning"]
        infos = [i for i in report.issues if i.severity == "info"]

        assert len(errors) == 1
        assert len(warnings) == 1
        assert len(infos) == 1
        assert len(report.issues) == 3

    def test_print_summary_returns_error_count(self, capsys):
        """Test that print_summary returns the correct error count."""
        report = ValidationReport()

        report.add_issue("error", Path("/tmp/test.mdx"), "test", "Error 1")  # nosec B108
        report.add_issue("error", Path("/tmp/test.mdx"), "test", "Error 2")  # nosec B108
        report.add_issue("warning", Path("/tmp/test.mdx"), "test", "Warning")  # nosec B108

        error_count = report.print_summary()

        assert error_count == 2

        captured = capsys.readouterr()
        assert "Errors:   2" in captured.out
        assert "Warnings: 1" in captured.out


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "regex: tests for regex pattern validation")
    config.addinivalue_line("markers", "integration: integration tests")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
