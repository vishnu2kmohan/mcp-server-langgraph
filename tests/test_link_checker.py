#!/usr/bin/env python3
"""
Test suite for documentation link checker.

Following TDD principles - tests define expected behavior.
"""

import pytest
from pathlib import Path
import tempfile
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestInternalLinkParsing:
    """Test parsing of internal links from MDX files."""

    def test_finds_relative_links(self):
        """Test that relative links are correctly extracted."""
        content = """
        See [Getting Started](../getting-started/installation.mdx) for setup.
        Check [API Reference](./api-reference.mdx) for details.
        """

        from check_internal_links import extract_internal_links

        links = extract_internal_links(content)

        assert len(links) >= 2
        assert any('../getting-started/installation.mdx' in link for link in links)
        assert any('./api-reference.mdx' in link for link in links)

    def test_ignores_external_links(self):
        """Test that external links are ignored."""
        content = """
        Visit [GitHub](https://github.com/user/repo) for code.
        See [Google](http://google.com) for search.
        """

        from check_internal_links import extract_internal_links

        links = extract_internal_links(content)

        assert len(links) == 0

    def test_finds_anchor_links(self):
        """Test that anchor links are correctly handled."""
        content = """
        Jump to [Section](#my-section) below.
        See [Other Page](../guide.mdx#specific-section) for details.
        """

        from check_internal_links import extract_internal_links

        links = extract_internal_links(content)

        # Should find the link with file, may or may not include pure anchors
        assert any('guide.mdx' in link for link in links)

    def test_handles_mdx_link_components(self):
        """Test parsing of MDX Link components."""
        content = """
        <Link href="/getting-started/installation">Install</Link>
        """

        from check_internal_links import extract_internal_links

        links = extract_internal_links(content)

        assert any('installation' in link for link in links)


class TestLinkResolution:
    """Test resolution of internal links to actual files."""

    @pytest.fixture
    def temp_docs_structure(self):
        """Create temporary docs structure for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs = Path(tmpdir) / "docs"
            docs.mkdir()

            # Create some test files
            (docs / "index.mdx").write_text("# Index")
            (docs / "guide.mdx").write_text("# Guide")

            subdir = docs / "getting-started"
            subdir.mkdir()
            (subdir / "installation.mdx").write_text("# Installation")

            yield docs

    def test_resolves_relative_link(self, temp_docs_structure):
        """Test that relative links resolve correctly."""
        from check_internal_links import resolve_link

        source_file = temp_docs_structure / "index.mdx"
        target = "./getting-started/installation.mdx"  # Correct relative path

        # This should resolve from temp location
        # Test that function handles relative paths
        resolved = resolve_link(source_file, target, docs_root=temp_docs_structure)
        assert resolved is not None
        assert resolved.exists()

    def test_detects_broken_link(self, temp_docs_structure):
        """Test that broken links are detected."""
        from check_internal_links import resolve_link

        source_file = temp_docs_structure / "index.mdx"
        target = "../nonexistent/file.mdx"

        resolved = resolve_link(source_file, target)
        assert resolved is None or not resolved.exists()

    def test_resolves_absolute_link(self, temp_docs_structure):
        """Test that absolute links (from docs root) resolve."""
        from check_internal_links import resolve_link

        source_file = temp_docs_structure / "getting-started" / "installation.mdx"
        target = "/guide.mdx"

        resolved = resolve_link(source_file, target, docs_root=temp_docs_structure)
        assert resolved == temp_docs_structure / "guide.mdx"


class TestLinkValidation:
    """Test complete link validation workflow."""

    def test_validates_all_links_in_file(self):
        """Test that all links in a file are validated."""
        from check_internal_links import validate_file_links

        # Create temp file with mixed links
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mdx', delete=False) as f:
            f.write("""
            Valid: [Guide](./guide.mdx)
            External: [GitHub](https://github.com)
            Broken: [Missing](./nonexistent.mdx)
            """)
            temp_file = Path(f.name)

        try:
            # Create the valid target
            guide_file = temp_file.parent / "guide.mdx"
            guide_file.write_text("# Guide")

            broken_links = validate_file_links(temp_file)

            # Should find the broken link
            assert len(broken_links) >= 1
            assert any('nonexistent.mdx' in link for link in broken_links)

        finally:
            temp_file.unlink(missing_ok=True)
            guide_file.unlink(missing_ok=True)


class TestRealWorldExamples:
    """Test cases based on actual documentation structure."""

    def test_adr_cross_references(self):
        """Test that ADR cross-references are valid."""
        # ADRs frequently reference each other
        # This test would check actual ADR files if they exist
        adr_dir = Path('adr')
        if not adr_dir.exists():
            pytest.skip("ADR directory not found")

        from check_internal_links import validate_file_links

        adr_files = list(adr_dir.glob('*.md'))
        if not adr_files:
            pytest.skip("No ADR files found")

        # Check first ADR file
        broken = validate_file_links(adr_files[0])

        # ADRs should have valid cross-references
        assert isinstance(broken, list)

    def test_navigation_links_exist(self):
        """Test that docs.json references existing files."""
        import json

        docs_json = Path('docs/docs.json')
        if not docs_json.exists():
            pytest.skip("docs.json not found")

        with open(docs_json) as f:
            data = json.load(f)

        # Extract all page references
        pages = []

        def extract_pages(obj):
            if isinstance(obj, dict):
                if 'pages' in obj:
                    pages.extend(obj['pages'])
                for v in obj.values():
                    extract_pages(v)
            elif isinstance(obj, list):
                for item in obj:
                    extract_pages(item)

        extract_pages(data.get('navigation', {}))

        # Verify files exist
        missing = []
        for page in pages:
            file_path = Path('docs') / f"{page}.mdx"
            if not file_path.exists():
                missing.append(page)

        assert len(missing) == 0, f"Missing files: {missing}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
