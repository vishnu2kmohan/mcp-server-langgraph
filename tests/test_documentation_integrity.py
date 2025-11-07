"""
Test documentation integrity to prevent broken docs, missing files, and sync issues.

This test suite validates:
1. ADR synchronization between adr/ and docs/architecture/
2. docs.json validity and referenced files exist
3. No HTML comments in MDX files (use JSX comments instead)
4. Mermaid diagrams are properly formatted
5. All navigation links point to existing files
"""

import json
import re
from pathlib import Path
from typing import List, Set

import pytest

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class TestADRSynchronization:
    """Verify ADRs are synced between source (adr/) and Mintlify docs (docs/architecture/)."""

    def test_adr_count_matches(self):
        """Test that the number of ADRs in adr/ matches docs/architecture/."""
        adr_source = list((PROJECT_ROOT / "adr").glob("adr-*.md"))
        adr_docs = list((PROJECT_ROOT / "docs" / "architecture").glob("adr-*.mdx"))

        assert len(adr_source) == len(adr_docs), (
            f"ADR count mismatch: {len(adr_source)} in adr/ " f"but {len(adr_docs)} in docs/architecture/"
        )

    def test_all_source_adrs_have_mdx_versions(self):
        """Test that every ADR in adr/ has a corresponding .mdx file in docs/architecture/."""
        adr_source_dir = PROJECT_ROOT / "adr"
        adr_docs_dir = PROJECT_ROOT / "docs" / "architecture"

        source_adrs = {f.stem for f in adr_source_dir.glob("adr-*.md")}
        docs_adrs = {f.stem for f in adr_docs_dir.glob("adr-*.mdx")}

        missing_in_docs = source_adrs - docs_adrs
        assert not missing_in_docs, f"ADRs in adr/ missing from docs/architecture/: {sorted(missing_in_docs)}"

    def test_no_orphaned_adr_mdx_files(self):
        """Test that there are no orphaned .mdx ADR files without source .md files."""
        adr_source_dir = PROJECT_ROOT / "adr"
        adr_docs_dir = PROJECT_ROOT / "docs" / "architecture"

        source_adrs = {f.stem for f in adr_source_dir.glob("adr-*.md")}
        docs_adrs = {f.stem for f in adr_docs_dir.glob("adr-*.mdx")}

        orphaned_in_docs = docs_adrs - source_adrs
        assert not orphaned_in_docs, f"Orphaned ADR .mdx files in docs/architecture/: {sorted(orphaned_in_docs)}"


class TestDocsJsonIntegrity:
    """Verify docs.json is valid and all referenced files exist."""

    def test_docs_json_is_valid_json(self):
        """Test that docs.json is valid JSON."""
        docs_json_path = PROJECT_ROOT / "docs" / "docs.json"
        assert docs_json_path.exists(), "docs/docs.json not found"

        with open(docs_json_path, "r") as f:
            data = json.load(f)  # Will raise JSONDecodeError if invalid

        assert isinstance(data, dict), "docs.json must be a JSON object"
        assert "navigation" in data, "docs.json must have 'navigation' key"

    def test_all_navigation_files_exist(self):
        """Test that all files referenced in docs.json navigation exist."""
        docs_json_path = PROJECT_ROOT / "docs" / "docs.json"
        docs_dir = PROJECT_ROOT / "docs"

        with open(docs_json_path, "r") as f:
            data = json.load(f)

        # Extract all page references from navigation
        pages = self._extract_all_pages(data["navigation"])

        missing_files = []
        for page in pages:
            # Skip external URLs
            if page.startswith("http"):
                continue

            # Check if file exists with .mdx extension
            file_path = docs_dir / f"{page}.mdx"
            if not file_path.exists():
                missing_files.append(page)

        assert not missing_files, "Files referenced in docs.json but not found:\n" + "\n".join(
            f"  - {f}.mdx" for f in sorted(missing_files)
        )

    def _extract_all_pages(self, navigation: dict) -> List[str]:
        """Recursively extract all page references from navigation structure."""
        pages = []

        if isinstance(navigation, dict):
            # Check for tabs
            if "tabs" in navigation:
                for tab in navigation["tabs"]:
                    if "groups" in tab:
                        for group in tab["groups"]:
                            if "pages" in group:
                                pages.extend(group["pages"])
            # Check for pages at current level
            if "pages" in navigation:
                pages.extend(navigation["pages"])
            # Check for groups at current level
            if "groups" in navigation:
                for group in navigation["groups"]:
                    if "pages" in group:
                        pages.extend(group["pages"])
        elif isinstance(navigation, list):
            for item in navigation:
                pages.extend(self._extract_all_pages(item))

        return pages


class TestMDXSyntax:
    """Verify MDX files use correct syntax and don't have common errors."""

    def test_no_html_comments_in_mdx_files(self):
        """Test that MDX files don't use HTML comments (use JSX comments instead)."""
        docs_dir = PROJECT_ROOT / "docs"
        mdx_files = list(docs_dir.glob("**/*.mdx"))

        files_with_html_comments = []
        for mdx_file in mdx_files:
            # Skip template files
            if ".mintlify/templates" in str(mdx_file):
                continue

            content = mdx_file.read_text()

            # Remove code blocks to avoid false positives (HTML in code examples is fine)
            content_no_code = re.sub(r"```.*?```", "", content, flags=re.DOTALL)

            # Check for HTML comments outside of code blocks
            if re.search(r"<!--", content_no_code):
                files_with_html_comments.append(mdx_file.relative_to(PROJECT_ROOT))

        assert (
            not files_with_html_comments
        ), "MDX files with HTML comments outside code blocks (use {/* */} instead):\n" + "\n".join(
            f"  - {f}" for f in sorted(files_with_html_comments)
        )

    def test_jsx_comments_are_properly_closed(self):
        """Test that JSX comments in MDX files are properly opened and closed."""
        docs_dir = PROJECT_ROOT / "docs"
        mdx_files = list(docs_dir.glob("**/*.mdx"))

        files_with_unclosed_comments = []
        for mdx_file in mdx_files:
            # Skip template files
            if ".mintlify/templates" in str(mdx_file):
                continue

            content = mdx_file.read_text()

            # Count opening and closing JSX comment markers
            opening_count = content.count("{/*")
            closing_count = content.count("*/}")

            if opening_count != closing_count:
                files_with_unclosed_comments.append(
                    f"{mdx_file.relative_to(PROJECT_ROOT)} " + f"(open: {opening_count}, close: {closing_count})"
                )

        assert not files_with_unclosed_comments, "MDX files with unclosed JSX comments:\n" + "\n".join(
            f"  - {f}" for f in sorted(files_with_unclosed_comments)
        )

    def test_no_unescaped_comparison_operators(self):
        """Test that comparison operators < and > are properly escaped in MDX."""
        docs_dir = PROJECT_ROOT / "docs"
        mdx_files = list(docs_dir.glob("**/*.mdx"))

        # Pattern to detect unescaped < or > outside of code blocks and HTML tags
        # This is a simplified check - Mintlify parser will catch more cases
        problematic_files = []

        for mdx_file in mdx_files:
            # Skip template files
            if ".mintlify/templates" in str(mdx_file):
                continue

            content = mdx_file.read_text()

            # Remove code blocks to avoid false positives
            content_no_code = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
            content_no_code = re.sub(r"`[^`]+`", "", content_no_code)

            # Look for patterns like "< " or " <" followed by a digit (e.g., "<15")
            # or "> " or " >" followed by a digit (e.g., ">95")
            if re.search(r"[^<]\s*<\s*\d", content_no_code) or re.search(r"\s*>\s*\d", content_no_code):
                problematic_files.append(mdx_file.relative_to(PROJECT_ROOT))

        # This is a lenient check - we're not failing on this, just warning
        if problematic_files:
            pytest.skip(
                "Potential unescaped comparison operators (use &lt; or &gt;):\n"
                + "\n".join(f"  - {f}" for f in sorted(problematic_files))
            )


class TestArchitectureOverview:
    """Verify architecture overview is up to date with actual ADR count."""

    def test_architecture_overview_adr_count_is_current(self):
        """Test that architecture/overview.mdx has the correct ADR count."""
        overview_path = PROJECT_ROOT / "docs" / "architecture" / "overview.mdx"
        adr_source_dir = PROJECT_ROOT / "adr"

        # Count actual ADRs
        actual_adr_count = len(list(adr_source_dir.glob("adr-*.md")))

        # Read overview file
        content = overview_path.read_text()

        # Find the ADR count statement
        match = re.search(r"We maintain \*\*(\d+) ADRs\*\*", content)
        assert match, "Could not find 'We maintain **X ADRs**' in architecture/overview.mdx"

        documented_count = int(match.group(1))

        assert documented_count == actual_adr_count, (
            f"Architecture overview shows {documented_count} ADRs " f"but there are actually {actual_adr_count} ADRs in adr/"
        )


class TestMermaidDiagrams:
    """Verify Mermaid diagrams are properly formatted."""

    def test_all_mermaid_diagrams_have_closing_markers(self):
        """Test that all Mermaid diagram code blocks are properly closed."""
        docs_dir = PROJECT_ROOT / "docs"
        mdx_files = list(docs_dir.glob("**/*.mdx"))

        files_with_unclosed_mermaid = []
        for mdx_file in mdx_files:
            content = mdx_file.read_text()

            # Count opening and closing mermaid markers
            opening_count = len(re.findall(r"```mermaid", content))
            # Count closing ``` that follow mermaid blocks
            closing_count = len(re.findall(r"```mermaid.*?```", content, flags=re.DOTALL))

            if opening_count != closing_count:
                files_with_unclosed_mermaid.append(
                    f"{mdx_file.relative_to(PROJECT_ROOT)} " + f"(open: {opening_count}, closed: {closing_count})"
                )

        assert not files_with_unclosed_mermaid, "MDX files with unclosed Mermaid diagrams:\n" + "\n".join(
            f"  - {f}" for f in sorted(files_with_unclosed_mermaid)
        )


class TestDocumentationCompleteness:
    """Verify documentation is complete and up to date."""

    def test_no_suspiciously_small_documentation_files(self):
        """Test that there are no suspiciously small (<15 lines) MDX files."""
        docs_dir = PROJECT_ROOT / "docs"
        mdx_files = list(docs_dir.glob("**/*.mdx"))

        small_files = []
        for mdx_file in mdx_files:
            # Skip template files
            if ".mintlify/templates" in str(mdx_file):
                continue

            line_count = len(mdx_file.read_text().splitlines())
            if line_count < 15:
                small_files.append(f"{mdx_file.relative_to(PROJECT_ROOT)} ({line_count} lines)")

        assert not small_files, "Suspiciously small MDX files (potential stubs):\n" + "\n".join(
            f"  - {f}" for f in sorted(small_files)
        )

    def test_monitoring_subdirectories_have_readmes(self):
        """Test that monitoring subdirectories have README.md files."""
        monitoring_dir = PROJECT_ROOT / "monitoring"

        # Define subdirectories that should have READMEs
        required_readmes = {
            "gcp/README.md": "GCP monitoring configuration",
            "otel-collector/README.md": "OpenTelemetry collector configuration",
        }

        missing_readmes = []
        for readme_path, description in required_readmes.items():
            full_path = monitoring_dir / readme_path
            if not full_path.exists():
                missing_readmes.append(f"{readme_path} ({description})")

        assert not missing_readmes, "Missing README files in monitoring subdirectories:\n" + "\n".join(
            f"  - {f}" for f in sorted(missing_readmes)
        )

    def test_monitoring_readmes_are_comprehensive(self):
        """Test that monitoring READMEs are comprehensive (>50 lines)."""
        monitoring_dir = PROJECT_ROOT / "monitoring"

        readmes_to_check = [
            monitoring_dir / "gcp" / "README.md",
            monitoring_dir / "otel-collector" / "README.md",
        ]

        inadequate_readmes = []
        for readme_path in readmes_to_check:
            if not readme_path.exists():
                continue  # Skip if doesn't exist (caught by other test)

            line_count = len(readme_path.read_text().splitlines())
            if line_count < 50:
                inadequate_readmes.append(f"{readme_path.relative_to(PROJECT_ROOT)} ({line_count} lines, minimum 50)")

        assert (
            not inadequate_readmes
        ), "Monitoring READMEs are too brief (should explain setup, usage, troubleshooting):\n" + "\n".join(
            f"  - {f}" for f in sorted(inadequate_readmes)
        )
