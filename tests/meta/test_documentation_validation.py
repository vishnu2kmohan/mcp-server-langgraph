"""
Documentation Validation Tests

These tests ensure documentation quality and prevent common documentation errors:
- MDX parsing errors (unescaped < characters)
- Broken internal links
- Invalid frontmatter
- ADR numbering consistency
- Template file exclusions

Following TDD principles to prevent regression of documentation issues.
"""

import gc
import json
import re

import pytest
from tests.helpers.path_helpers import get_repo_root

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
pytestmark = pytest.mark.unit
# Base paths
REPO_ROOT = get_repo_root()
DOCS_DIR = REPO_ROOT / "docs"
ADR_DIR = REPO_ROOT / "adr"


@pytest.mark.xdist_group(name="testmdxparsing")
class TestMDXParsing:
    """Test MDX files for parsing errors"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_no_unescaped_less_than_digits(self):
        """
        Prevent MDX parsing errors from unescaped < followed by digits.

        Common patterns like <100ms or <2min must be escaped with backticks.
        This prevents MDX from interpreting them as HTML tags.

        Regression test for: mintlify dev parsing errors found on 2025-11-06
        """
        mdx_files = list(DOCS_DIR.glob("**/*.mdx"))
        errors = []

        for mdx_file in mdx_files:
            # Skip template files
            if ".mintlify/templates" in str(mdx_file):
                continue

            content = mdx_file.read_text()

            # Find unescaped <digit patterns (not inside backticks or code blocks)
            # Pattern: < followed by digit, not preceded by backtick or &lt;
            lines = content.split("\n")
            in_code_block = False

            for line_num, line in enumerate(lines, 1):
                # Track fenced code blocks
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue

                # Skip lines inside code blocks or indented code blocks
                if in_code_block or line.startswith("    "):
                    continue

                # Find <digit patterns that are NOT:
                # - Inside backticks: `<100ms`
                # - HTML entities: &lt;100ms
                # - Inside code spans
                matches = re.finditer(r"(?<!`)(?<!&lt;)<(\d+)", line)
                for match in matches:
                    # Check if inside backticks
                    before = line[: match.start()]
                    if before.count("`") % 2 == 0:  # Not inside backticks
                        errors.append(
                            f"{mdx_file.relative_to(REPO_ROOT)}:{line_num} "
                            f"Unescaped '<{match.group(1)}' - wrap in backticks: `<{match.group(1)}`"
                        )

        assert not errors, (
            "Found unescaped <digit patterns that will cause MDX parsing errors:\n"
            + "\n".join(errors)
            + "\n\nFix by wrapping in backticks, e.g., `<100ms` or `<2min`"
        )

    def test_no_unescaped_email_addresses(self):
        """
        Prevent MDX parsing errors from email addresses with < >.

        Email addresses like <email@example.com> must be escaped.
        """
        mdx_files = list(DOCS_DIR.glob("**/*.mdx"))
        md_files = list(DOCS_DIR.glob("**/*.md"))
        all_files = mdx_files + md_files
        errors = []

        for doc_file in all_files:
            # Skip template files
            if ".mintlify/templates" in str(doc_file):
                continue

            content = doc_file.read_text()
            lines = content.split("\n")

            for line_num, line in enumerate(lines, 1):
                # Find <email@domain> patterns not inside backticks
                matches = re.finditer(r"(?<!`)(?<!&lt;)<([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})>", line)
                for match in matches:
                    before = line[: match.start()]
                    if before.count("`") % 2 == 0:  # Not inside backticks
                        errors.append(
                            f"{doc_file.relative_to(REPO_ROOT)}:{line_num} "
                            f"Unescaped email '<{match.group(1)}>' - wrap in backticks: `<{match.group(1)}>`"
                        )

        assert not errors, "Found unescaped email addresses that will cause MDX parsing errors:\n" + "\n".join(errors)


@pytest.mark.xdist_group(name="testmintlifynavigation")
class TestMintlifyNavigation:
    """Test Mintlify navigation configuration"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_docs_json_valid(self):
        """Validate docs.json is valid JSON"""
        docs_json = DOCS_DIR / "docs.json"
        assert docs_json.exists(), "docs/docs.json not found"

        with open(docs_json) as f:
            config = json.load(f)

        # Mintlify uses 'navigation' with 'tabs' structure
        assert "navigation" in config, "docs.json missing 'navigation' key"
        assert "tabs" in config["navigation"], "navigation missing 'tabs' key"
        assert isinstance(config["navigation"]["tabs"], list), "tabs must be a list"

    def test_all_navigation_files_exist(self):
        """Verify all files referenced in docs.json navigation exist"""
        docs_json = DOCS_DIR / "docs.json"
        with open(docs_json) as f:
            config = json.load(f)

        missing_files = []

        def check_navigation(nav_items, parent_path=""):
            for item in nav_items:
                if isinstance(item, dict):
                    # Check groups
                    if "pages" in item:
                        check_navigation(item["pages"], parent_path)
                    # Check tabs
                    elif "groups" in item:
                        for group in item["groups"]:
                            if "pages" in group:
                                check_navigation(group["pages"], parent_path)
                elif isinstance(item, str):
                    # Check if file exists
                    file_path = DOCS_DIR / f"{item}.mdx"
                    if not file_path.exists():
                        # Try .md extension
                        file_path = DOCS_DIR / f"{item}.md"
                    if not file_path.exists():
                        missing_files.append(item)

        # Mintlify structure: {'navigation': {'tabs': [...], 'global': {...}}}
        if "navigation" in config and "tabs" in config["navigation"]:
            check_navigation(config["navigation"]["tabs"])

        assert not missing_files, "Missing files referenced in docs.json navigation:\n" + "\n".join(
            f"  - {f}" for f in missing_files
        )

    def test_no_orphaned_documentation_files(self):
        """Warn about documentation files not in navigation (excluding templates)"""
        docs_json = DOCS_DIR / "docs.json"
        with open(docs_json) as f:
            config = json.load(f)

        # Collect all referenced files
        referenced_files = set()

        def collect_references(nav_items):
            for item in nav_items:
                if isinstance(item, dict):
                    if "pages" in item:
                        collect_references(item["pages"])
                    elif "groups" in item:
                        for group in item["groups"]:
                            if "pages" in group:
                                collect_references(group["pages"])
                elif isinstance(item, str):
                    referenced_files.add(item)

        # Mintlify structure uses 'navigation' with 'tabs'
        if "navigation" in config and "tabs" in config["navigation"]:
            collect_references(config["navigation"]["tabs"])

        # Find all actual .mdx and .md files
        actual_files = []
        for ext in ["*.mdx", "*.md"]:
            for f in DOCS_DIR.glob(f"**/{ext}"):
                # Skip templates and special files
                rel_path = f.relative_to(DOCS_DIR)
                if (
                    ".mintlify/templates" not in str(rel_path)
                    and not str(rel_path).startswith(".")
                    and str(rel_path) != "README.md"
                ):
                    # Convert to navigation format (remove extension)
                    nav_path = str(rel_path).replace(".mdx", "").replace(".md", "")
                    actual_files.append(nav_path)

        orphaned = set(actual_files) - referenced_files

        # This is a warning, not a failure - some files may intentionally not be in nav
        if orphaned:
            print("\nWarning: Files not in navigation (may be intentional):")
            for f in sorted(orphaned):
                print(f"  - {f}")


@pytest.mark.xdist_group(name="testadrconsistency")
class TestADRConsistency:
    """Test Architecture Decision Records consistency"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_adr_numbering_sequential(self):
        """Verify ADR numbers are sequential and unique"""
        adr_files = list(ADR_DIR.glob("adr-*.md"))

        # Extract ADR numbers
        adr_numbers = []
        for adr_file in adr_files:
            match = re.match(r"adr-(\d+)-.*\.md", adr_file.name)
            if match:
                adr_numbers.append(int(match.group(1)))

        # Check for duplicates
        duplicates = [num for num in adr_numbers if adr_numbers.count(num) > 1]
        assert not duplicates, f"Duplicate ADR numbers found: {sorted(set(duplicates))}\nEach ADR must have a unique number."

        # Check for gaps (allowing some intentional gaps)
        adr_numbers.sort()
        if adr_numbers:
            max_num = max(adr_numbers)
            expected_range = set(range(1, max_num + 1))
            actual_set = set(adr_numbers)
            gaps = expected_range - actual_set

            # Allow up to 3 gaps (for deprecated/removed ADRs)
            if len(gaps) > 3:
                print(f"\nWarning: Found {len(gaps)} gaps in ADR numbering: {sorted(gaps)}")

    def test_adr_sync_between_directories(self):
        """Verify ADRs in adr/ have corresponding .mdx files in docs/architecture/"""
        adr_source_files = {f.stem: f for f in ADR_DIR.glob("adr-*.md")}
        adr_docs_files = {f.stem: f for f in (DOCS_DIR / "architecture").glob("adr-*.mdx")}

        missing_in_docs = set(adr_source_files.keys()) - set(adr_docs_files.keys())

        # Allow some ADRs to be source-only (templates, drafts)
        if missing_in_docs:
            print(f"\nWarning: {len(missing_in_docs)} ADRs in adr/ not synced to docs/architecture/:")
            for adr in sorted(missing_in_docs):
                print(f"  - {adr}")


@pytest.mark.xdist_group(name="testfrontmatter")
class TestFrontmatter:
    """Test MDX frontmatter consistency"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_mdx_files_have_frontmatter(self):
        """Verify all MDX files (except templates and operational docs) have valid frontmatter"""
        mdx_files = list(DOCS_DIR.glob("**/*.mdx"))
        missing_frontmatter = []

        # Operational documentation files excluded from frontmatter requirement
        # These are internal implementation plans and incident reports, not user-facing docs
        excluded_operational_docs = {
            "kubernetes/KEYCLOAK_READONLY_FILESYSTEM.mdx",
            "kubernetes/POD_CRASH_RESOLUTION_2025-11-12.mdx",
        }

        for mdx_file in mdx_files:
            # Skip templates
            if ".mintlify/templates" in str(mdx_file):
                continue

            # Skip operational documentation files
            relative_path = str(mdx_file.relative_to(DOCS_DIR))
            if relative_path in excluded_operational_docs:
                continue

            content = mdx_file.read_text()

            # Check for frontmatter (starts with ---)
            if not content.strip().startswith("---"):
                missing_frontmatter.append(mdx_file.relative_to(REPO_ROOT))

        assert not missing_frontmatter, "MDX files missing frontmatter:\n" + "\n".join(f"  - {f}" for f in missing_frontmatter)

    def test_frontmatter_required_fields(self):
        """Verify frontmatter contains required fields"""
        mdx_files = list(DOCS_DIR.glob("**/*.mdx"))
        required_fields = ["title"]
        errors = []

        for mdx_file in mdx_files:
            # Skip templates
            if ".mintlify/templates" in str(mdx_file):
                continue

            content = mdx_file.read_text()

            # Extract frontmatter
            if content.strip().startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = parts[1]

                    # Check for required fields
                    for field in required_fields:
                        if f"{field}:" not in frontmatter and f"{field} :" not in frontmatter:
                            errors.append(f"{mdx_file.relative_to(REPO_ROOT)} missing '{field}' in frontmatter")

        assert not errors, "Frontmatter validation errors:\n" + "\n".join(f"  - {e}" for e in errors)


@pytest.mark.xdist_group(name="testlinkintegrity")
class TestLinkIntegrity:
    """Test internal link integrity"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_no_broken_internal_links_to_docs(self):
        """
        Detect broken internal links within documentation.

        This is a basic check - full link validation should use mintlify broken-links
        """
        mdx_files = list(DOCS_DIR.glob("**/*.mdx"))
        md_files = list(DOCS_DIR.glob("**/*.md"))
        all_files = mdx_files + md_files

        # Build list of valid paths
        valid_paths = set()
        for doc_file in all_files:
            rel_path = doc_file.relative_to(DOCS_DIR)
            # Add both with and without extension
            valid_paths.add("/" + str(rel_path).replace(".mdx", "").replace(".md", ""))
            valid_paths.add(str(rel_path))

        potential_issues = []

        for doc_file in all_files:
            # Skip templates
            if ".mintlify/templates" in str(doc_file):
                continue

            content = doc_file.read_text()

            # Find internal links like [text](/path/to/doc)
            internal_links = re.findall(r"\[([^\]]+)\]\((/[^\)]+)\)", content)

            for link_text, link_path in internal_links:
                # Remove anchors
                clean_path = link_path.split("#")[0]

                # Skip external URLs
                if clean_path.startswith("http"):
                    continue

                # Check if path exists
                if clean_path and clean_path not in valid_paths:
                    # Check if it's a valid file path
                    file_exists = (
                        (DOCS_DIR / clean_path.lstrip("/")).exists()
                        or (DOCS_DIR / (clean_path.lstrip("/") + ".mdx")).exists()
                        or (DOCS_DIR / (clean_path.lstrip("/") + ".md")).exists()
                    )

                    if not file_exists:
                        potential_issues.append(f"{doc_file.relative_to(REPO_ROOT)}: Link to '{clean_path}' may be broken")

        # This is a warning, not a failure - some links may be valid but not detected
        if potential_issues:
            print("\nWarning: Potential broken internal links (verify with 'mintlify broken-links'):")
            for issue in potential_issues[:10]:  # Show first 10
                print(f"  - {issue}")
            if len(potential_issues) > 10:
                print(f"  ... and {len(potential_issues) - 10} more")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
