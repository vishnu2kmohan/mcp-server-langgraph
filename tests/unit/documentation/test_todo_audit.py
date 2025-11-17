#!/usr/bin/env python3
"""
Tests for TODO/FIXME Audit Script

Following TDD principles:
1. Test finding TODO/FIXME markers
2. Test categorization
3. Test reporting
4. Test exclusion patterns
"""

import gc
from pathlib import Path

import pytest

from scripts.validators.todo_audit import AuditResult, TodoAuditor, TodoMarker

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testtodoauditor")
class TestTodoAuditor:
    """Test suite for TodoAuditor."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        import gc

        gc.collect()

    @pytest.fixture
    def temp_docs_dir(self, tmp_path):
        """Create temporary docs directory for testing."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        return docs_dir

    def test_empty_directory_has_no_todos(self, temp_docs_dir):
        """Test that empty directory has no TODOs."""
        auditor = TodoAuditor(temp_docs_dir)
        result = auditor.audit()

        assert len(result.markers) == 0
        assert result.stats["total_files"] == 0
        assert result.stats["total_markers"] == 0

    def test_finds_todo_marker(self, temp_docs_dir):
        """Test finding TODO markers."""
        mdx_file = temp_docs_dir / "test.mdx"
        mdx_file.write_text(
            """
# Test Document

TODO: Implement this feature
"""
        )

        auditor = TodoAuditor(temp_docs_dir)
        result = auditor.audit()

        assert len(result.markers) == 1
        assert result.markers[0].marker_type == "TODO"
        assert result.markers[0].file_path == "test.mdx"
        assert "Implement this feature" in result.markers[0].content

    def test_finds_fixme_marker(self, temp_docs_dir):
        """Test finding FIXME markers."""
        mdx_file = temp_docs_dir / "test.mdx"
        mdx_file.write_text(
            """
# Test Document

FIXME: This is broken
"""
        )

        auditor = TodoAuditor(temp_docs_dir)
        result = auditor.audit()

        assert len(result.markers) == 1
        assert result.markers[0].marker_type == "FIXME"
        assert "This is broken" in result.markers[0].content

    def test_finds_xxx_marker(self, temp_docs_dir):
        """Test finding XXX placeholder markers."""
        mdx_file = temp_docs_dir / "test.mdx"
        mdx_file.write_text(
            """
```yaml
store_id: "01HXXXXXXXXX"
```
"""
        )

        auditor = TodoAuditor(temp_docs_dir)
        result = auditor.audit()

        assert len(result.markers) >= 1
        # Should find XXX pattern
        xxx_markers = [m for m in result.markers if m.marker_type == "XXX"]
        assert len(xxx_markers) >= 1

    def test_finds_multiple_markers_in_file(self, temp_docs_dir):
        """Test finding multiple markers in a single file."""
        mdx_file = temp_docs_dir / "test.mdx"
        mdx_file.write_text(
            """
# Test Document

TODO: First item
Some content
FIXME: Second item
More content
TODO: Third item
"""
        )

        auditor = TodoAuditor(temp_docs_dir)
        result = auditor.audit()

        assert len(result.markers) == 3
        todo_count = sum(1 for m in result.markers if m.marker_type == "TODO")
        fixme_count = sum(1 for m in result.markers if m.marker_type == "FIXME")
        assert todo_count == 2
        assert fixme_count == 1

    def test_tracks_line_numbers(self, temp_docs_dir):
        """Test that line numbers are tracked accurately."""
        mdx_file = temp_docs_dir / "test.mdx"
        mdx_file.write_text(
            """Line 1
Line 2
Line 3
TODO: This is on line 4
Line 5
"""
        )

        auditor = TodoAuditor(temp_docs_dir)
        result = auditor.audit()

        assert len(result.markers) == 1
        assert result.markers[0].line_number == 4

    def test_handles_nested_directories(self, temp_docs_dir):
        """Test auditing nested directory structure."""
        nested_dir = temp_docs_dir / "guides" / "advanced"
        nested_dir.mkdir(parents=True)

        mdx_file = nested_dir / "test.mdx"
        mdx_file.write_text("TODO: Nested file task")

        auditor = TodoAuditor(temp_docs_dir)
        result = auditor.audit()

        assert len(result.markers) == 1
        assert "guides/advanced/test.mdx" in result.markers[0].file_path

    def test_excludes_template_files(self, temp_docs_dir):
        """Test that template files are excluded."""
        template_dir = temp_docs_dir / ".mintlify" / "templates"
        template_dir.mkdir(parents=True)

        template_file = template_dir / "template.mdx"
        template_file.write_text("TODO: This should be ignored in templates")

        auditor = TodoAuditor(temp_docs_dir)
        result = auditor.audit()

        # Should not include template files
        assert len(result.markers) == 0

    def test_processes_multiple_files(self, temp_docs_dir):
        """Test processing multiple files."""
        for i in range(3):
            mdx_file = temp_docs_dir / f"file{i}.mdx"
            mdx_file.write_text(f"TODO: Task in file {i}")

        auditor = TodoAuditor(temp_docs_dir)
        result = auditor.audit()

        assert len(result.markers) == 3
        # Should have markers from different files
        unique_files = set(m.file_path for m in result.markers)
        assert len(unique_files) == 3

    def test_statistics_are_accurate(self, temp_docs_dir):
        """Test that statistics are calculated correctly."""
        mdx_file1 = temp_docs_dir / "file1.mdx"
        mdx_file1.write_text(
            """
TODO: Task 1
FIXME: Task 2
"""
        )

        mdx_file2 = temp_docs_dir / "file2.mdx"
        mdx_file2.write_text("TODO: Task 3")

        auditor = TodoAuditor(temp_docs_dir)
        result = auditor.audit()

        assert result.stats["total_files"] == 2
        assert result.stats["total_markers"] == 3
        assert result.stats["by_type"]["TODO"] == 2
        assert result.stats["by_type"]["FIXME"] == 1

    def test_nonexistent_directory(self):
        """Test behavior with nonexistent directory."""
        auditor = TodoAuditor(Path("/nonexistent/path"))
        result = auditor.audit()

        assert len(result.markers) == 0
        assert result.stats["total_files"] == 0

    @pytest.mark.xdist_group(name="validators")
    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""

        gc.collect()


@pytest.mark.xdist_group(name="testtodomarker")
class TestTodoMarker:
    """Test suite for TodoMarker dataclass."""

    def test_marker_attributes(self):
        """Test TodoMarker attributes."""
        marker = TodoMarker(
            marker_type="TODO",
            file_path="test.mdx",
            line_number=42,
            content="Implement feature X",
        )

        assert marker.marker_type == "TODO"
        assert marker.file_path == "test.mdx"
        assert marker.line_number == 42
        assert marker.content == "Implement feature X"

    @pytest.mark.xdist_group(name="validators")
    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""

        gc.collect()


@pytest.mark.xdist_group(name="testauditresult")
class TestAuditResult:
    """Test suite for AuditResult dataclass."""

    def test_audit_result_defaults(self):
        """Test AuditResult default values."""
        result = AuditResult()

        assert result.markers == []
        assert result.stats == {}

    def test_audit_result_with_data(self):
        """Test AuditResult with data."""
        markers = [
            TodoMarker("TODO", "test.mdx", 1, "Task 1"),
            TodoMarker("FIXME", "test.mdx", 2, "Task 2"),
        ]
        stats = {"total_files": 1, "total_markers": 2}

        result = AuditResult(markers=markers, stats=stats)

        assert len(result.markers) == 2
        assert result.stats["total_files"] == 1

    @pytest.mark.xdist_group(name="validators")
    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""

        gc.collect()
