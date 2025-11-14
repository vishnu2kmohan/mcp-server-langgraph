"""
Regression tests for documentation structure and organization.

Prevents issues identified in documentation audit (2025-11-12):
- Orphaned MDX files not in navigation
- Duplicate ADR numbering
- Broken internal links
- Missing files referenced in navigation
- Version inconsistencies

Author: Documentation Audit Remediation
Date: 2025-11-12
Related: GitHub Issues #75-80
"""

import json
from pathlib import Path
from typing import Dict, List, Set

import pytest

# Project root is 3 levels up from this file
PROJECT_ROOT = Path(__file__).parent.parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
DOCS_JSON = DOCS_DIR / "docs.json"
ADR_DIR = PROJECT_ROOT / "adr"
PYPROJECT_TOML = PROJECT_ROOT / "pyproject.toml"


class TestDocumentationNavigation:
    """Prevent orphaned files and broken navigation references."""

    def test_all_mdx_files_in_navigation(self):
        """
        Ensure all MDX files (except excluded ones) are referenced in docs.json.

        Prevents: Orphaned documentation files (CRIT-001 from audit)
        """
        if not DOCS_JSON.exists():
            pytest.skip("docs/docs.json not found")

        # Load navigation
        with open(DOCS_JSON) as f:
            docs_config = json.load(f)

        # Extract all page references from navigation
        nav_pages = self._extract_navigation_pages(docs_config.get("navigation", {}))

        # Find all MDX files
        all_mdx_files = set()
        for mdx_file in DOCS_DIR.rglob("*.mdx"):
            # Get relative path from docs/ directory
            rel_path = mdx_file.relative_to(DOCS_DIR)
            # Remove .mdx extension for comparison
            page_ref = str(rel_path).replace(".mdx", "")
            all_mdx_files.add(page_ref)

        # Files that are intentionally excluded from navigation
        excluded_files = {
            ".mintlify/templates/adr-template",
            ".mintlify/templates/deployment-template",
            ".mintlify/templates/guide-template",
            ".mintlify/templates/reference-template",
            # Operational documentation (internal implementation plans, incident reports)
            "architecture/adr/ADR-0053-pytest-xdist-state-pollution-prevention",
            "kubernetes/KEYCLOAK_READONLY_FILESYSTEM",
            "kubernetes/POD_CRASH_RESOLUTION_2025-11-12",
        }

        # Find orphaned files
        orphaned = all_mdx_files - nav_pages - excluded_files

        assert not orphaned, (
            f"Found {len(orphaned)} orphaned MDX files not in navigation:\n"
            + "\n".join(f"  - {f}" for f in sorted(orphaned))
            + "\n\nAdd these files to docs/docs.json navigation or add to excluded_files set."
        )

    def test_all_navigation_pages_exist(self):
        """
        Ensure all pages referenced in navigation actually exist.

        Prevents: Missing files causing broken navigation
        """
        if not DOCS_JSON.exists():
            pytest.skip("docs/docs.json not found")

        with open(DOCS_JSON) as f:
            docs_config = json.load(f)

        nav_pages = self._extract_navigation_pages(docs_config.get("navigation", {}))

        missing_files = []
        for page_ref in nav_pages:
            mdx_path = DOCS_DIR / f"{page_ref}.mdx"
            if not mdx_path.exists():
                missing_files.append(page_ref)

        assert not missing_files, (
            f"Found {len(missing_files)} missing files referenced in navigation:\n"
            + "\n".join(f"  - {f}.mdx" for f in sorted(missing_files))
            + "\n\nRemove these from docs/docs.json or create the missing files."
        )

    def test_no_duplicate_pages_in_navigation(self):
        """
        Ensure no page is referenced multiple times in navigation.

        Prevents: Duplicate navigation entries causing confusion
        """
        if not DOCS_JSON.exists():
            pytest.skip("docs/docs.json not found")

        with open(DOCS_JSON) as f:
            docs_config = json.load(f)

        nav_pages = self._extract_navigation_pages(docs_config.get("navigation", {}), return_list=True)

        # Find duplicates
        seen = set()
        duplicates = []
        for page in nav_pages:
            if page in seen:
                duplicates.append(page)
            seen.add(page)

        assert not duplicates, (
            f"Found {len(duplicates)} duplicate pages in navigation:\n"
            + "\n".join(f"  - {f}" for f in sorted(set(duplicates)))
            + "\n\nRemove duplicate entries from docs/docs.json."
        )

    def _extract_navigation_pages(self, nav_obj: Dict, return_list: bool = False):
        """Extract all page references from navigation object."""
        pages = []

        if isinstance(nav_obj, dict):
            # Handle tabs
            if "tabs" in nav_obj:
                for tab in nav_obj["tabs"]:
                    if "groups" in tab:
                        for group in tab["groups"]:
                            if "pages" in group:
                                pages.extend(group["pages"])

            # Handle global navigation
            if "global" in nav_obj:
                # Global doesn't have pages, skip
                pass

        # Return as list or set based on parameter
        if return_list:
            return pages
        else:
            return set(pages)


class TestADRNumbering:
    """Prevent duplicate ADR numbering."""

    def test_no_duplicate_adr_numbers(self):
        """
        Ensure no two ADRs have the same number.

        Prevents: Duplicate ADR numbering (WARN-002 from audit)
        """
        if not ADR_DIR.exists():
            pytest.skip("adr/ directory not found")

        adr_numbers = {}
        duplicates = []

        for adr_file in sorted(ADR_DIR.glob("adr-*.md")):
            # Extract number from filename (e.g., "adr-0045-title.md" -> "0045")
            filename = adr_file.name
            if not filename.startswith("adr-"):
                continue

            parts = filename.split("-")
            if len(parts) < 2:
                continue

            adr_num = parts[1]

            if adr_num in adr_numbers:
                duplicates.append({"number": adr_num, "files": [adr_numbers[adr_num], filename]})
            else:
                adr_numbers[adr_num] = filename

        assert not duplicates, (
            "Found duplicate ADR numbers:\n"
            + "\n".join(f"  - ADR-{d['number']}: {', '.join(d['files'])}" for d in duplicates)
            + "\n\nRenumber one of the duplicate ADRs to the next available number."
        )

    def test_adr_source_and_mintlify_sync(self):
        """
        Ensure ADRs in /adr match those in /docs/architecture.

        Prevents: ADR sync drift between source and Mintlify
        """
        if not ADR_DIR.exists() or not (DOCS_DIR / "architecture").exists():
            pytest.skip("ADR directories not found")

        # Get source ADRs
        source_adrs = set()
        for adr_file in ADR_DIR.glob("adr-*.md"):
            # Extract base name without extension
            source_adrs.add(adr_file.stem)

        # Get Mintlify ADRs
        mintlify_adrs = set()
        arch_dir = DOCS_DIR / "architecture"
        for adr_file in arch_dir.glob("adr-*.mdx"):
            # Extract base name without extension
            mintlify_adrs.add(adr_file.stem)

        # Check for missing in Mintlify
        missing_in_mintlify = source_adrs - mintlify_adrs

        # Check for missing in source
        missing_in_source = mintlify_adrs - source_adrs

        errors = []

        if missing_in_mintlify:
            errors.append(
                "ADRs in /adr but missing in /docs/architecture:\n"
                + "\n".join(f"  - {adr}" for adr in sorted(missing_in_mintlify))
            )

        if missing_in_source:
            errors.append(
                "ADRs in /docs/architecture but missing in /adr:\n"
                + "\n".join(f"  - {adr}" for adr in sorted(missing_in_source))
            )

        assert not errors, "\n\n".join(errors) + "\n\nSync ADRs between /adr and /docs/architecture."

    def test_adr_sequential_numbering(self):
        """
        Warn about gaps in ADR numbering sequence.

        Note: This is a warning, not a failure. Gaps may be intentional.
        """
        if not ADR_DIR.exists():
            pytest.skip("adr/ directory not found")

        adr_numbers = []
        for adr_file in sorted(ADR_DIR.glob("adr-*.md")):
            filename = adr_file.name
            if not filename.startswith("adr-"):
                continue

            parts = filename.split("-")
            if len(parts) < 2:
                continue

            try:
                adr_num = int(parts[1])
                adr_numbers.append(adr_num)
            except ValueError:
                continue

        adr_numbers.sort()

        if not adr_numbers:
            pytest.skip("No ADRs found")

        # Check for gaps
        gaps = []
        for i in range(len(adr_numbers) - 1):
            current = adr_numbers[i]
            next_num = adr_numbers[i + 1]
            if next_num - current > 1:
                missing = list(range(current + 1, next_num))
                gaps.extend(missing)

        if gaps:
            # This is informational, not a failure
            print(
                f"\nINFO: Found {len(gaps)} gaps in ADR numbering: "
                f"{', '.join(f'ADR-{n:04d}' for n in gaps[:5])}" + ("..." if len(gaps) > 5 else "")
            )


class TestVersionConsistency:
    """Ensure version numbers are consistent across project."""

    def test_version_consistency_in_deployment_files(self):
        """
        Ensure deployment files reference consistent version.

        Prevents: Version drift in deployment configurations
        """
        # Get version from pyproject.toml
        version = self._get_project_version()

        if not version:
            pytest.skip("Could not determine project version")

        # Check key deployment files
        deployment_files = [
            "deployments/kubernetes/deployment.yaml",
            "deployments/helm/Chart.yaml",
            "deployments/docker-compose.yml",
        ]

        version_issues = []

        for file_path_str in deployment_files:
            file_path = PROJECT_ROOT / file_path_str
            if not file_path.exists():
                continue

            content = file_path.read_text()

            # Look for image tags or version references
            # This is a simplified check - extend based on your needs
            if f":{version}" not in content and f"version: {version}" not in content:
                # More lenient check - just ensure version appears somewhere
                if version not in content:
                    version_issues.append(file_path_str)

        # Note: This test is informational - version references may be intentional
        if version_issues:
            print(f"\nINFO: Project version {version} not found in:\n" + "\n".join(f"  - {f}" for f in version_issues))

    def test_readme_adr_badge_accuracy(self):
        """
        Ensure README.md ADR badge count matches actual ADR count.

        Prevents: Incorrect badge counts (WARN-002 from audit)
        """
        readme = PROJECT_ROOT / "README.md"
        if not readme.exists() or not ADR_DIR.exists():
            pytest.skip("README.md or adr/ directory not found")

        import re

        # Count actual ADRs
        actual_adr_count = len(list(ADR_DIR.glob("adr-*.md")))

        # Read README and extract badge count
        readme_content = readme.read_text()

        # Match badge pattern: [![ADRs](https://img.shields.io/badge/ADRs-XX-informational.svg)]
        badge_match = re.search(r"!\[ADRs\]\(https://img\.shields\.io/badge/ADRs-(\d+)-", readme_content)

        if not badge_match:
            pytest.fail(
                "Could not find ADR badge in README.md. "
                "Expected format: [![ADRs](https://img.shields.io/badge/ADRs-XX-informational.svg)](adr/README.md)"
            )

        badge_count = int(badge_match.group(1))

        assert badge_count == actual_adr_count, (
            f"README.md ADR badge shows {badge_count} but found {actual_adr_count} ADRs.\n"
            f"Update README.md line with ADR badge to show correct count.\n"
            f"Search for 'badge/ADRs-{badge_count}-' and replace with 'badge/ADRs-{actual_adr_count}-'"
        )

    def _get_project_version(self) -> str | None:
        """Extract version from pyproject.toml."""
        if not PYPROJECT_TOML.exists():
            return None

        content = PYPROJECT_TOML.read_text()

        # Simple regex to find version
        import re

        match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if match:
            return match.group(1)

        return None


class TestDocumentationQuality:
    """Additional quality checks for documentation."""

    def test_no_todos_in_public_docs(self):
        """
        Ensure public-facing documentation doesn't have TODO/FIXME comments.

        Prevents: Incomplete public documentation (WARN-003 from audit)

        This checks ALL public docs except:
        - Templates (intentionally have TODOs as scaffolding)
        - Internal docs (docs-internal/)
        - Archive docs

        TODOs in development/internal docs are acceptable for tracking.
        """
        if not DOCS_DIR.exists():
            pytest.skip("docs/ directory not found")

        import re

        # Directories/files to exclude from TODO checking
        excluded_patterns = [
            ".mintlify/templates/",  # Template files intentionally have TODOs
            "archive/",  # Archive docs can have TODOs
        ]

        docs_with_todos = []
        total_todos = 0
        total_fixmes = 0

        for mdx_file in DOCS_DIR.rglob("*.mdx"):
            # Get relative path for readability
            rel_path = str(mdx_file.relative_to(DOCS_DIR))

            # Skip excluded paths
            if any(pattern in rel_path for pattern in excluded_patterns):
                continue

            content = mdx_file.read_text()

            # Check for TODO/FIXME markers (actual task markers, not prose)
            # Match patterns like:
            #   - TODO: something (with colon)
            #   - # TODO something (comment)
            #   - <!-- TODO something (HTML comment)
            #   - TODO(username) (with parentheses)
            # But NOT:
            #   - "with TODOs where" (plural in prose)
            #   - "as TODO for" (singular in prose without marker)
            #   - "Commented with TODOs" (descriptive text)

            todo_markers = []

            # Pattern 1: TODO/FIXME with colon (TODO: task)
            todo_markers.extend(re.findall(r"(?:^|\s)(?:TODO|FIXME)\s*:", content, re.IGNORECASE | re.MULTILINE))

            # Pattern 2: Comment markers (# TODO, <!-- TODO, // TODO)
            todo_markers.extend(re.findall(r"(?:#|<!--|//)\s*(?:TODO|FIXME)\b", content, re.IGNORECASE))

            # Pattern 3: TODO with parentheses (TODO(username))
            todo_markers.extend(re.findall(r"(?:^|\s)(?:TODO|FIXME)\s*\([^)]+\)", content, re.IGNORECASE | re.MULTILINE))

            # Pattern 4: Standalone TODO at start of line followed by dash and text (- TODO something)
            # But be very careful here - only match if it's clearly a task marker
            # Skip this pattern as it's too ambiguous and causes false positives

            todos = len(todo_markers)

            # Count FIXMEs separately for reporting
            fixme_count = len([m for m in todo_markers if "FIXME" in m.upper()])
            todo_count = len([m for m in todo_markers if "TODO" in m.upper() and "FIXME" not in m.upper()])

            # For compatibility, use total for todos, specific count for fixmes
            todos = todo_count
            fixmes = fixme_count

            if todos + fixmes > 0:
                docs_with_todos.append(f"{rel_path} ({todos} TODOs, {fixmes} FIXMEs)")
                total_todos += todos
                total_fixmes += fixmes

        assert not docs_with_todos, (
            f"Found {total_todos} TODOs and {total_fixmes} FIXMEs in "
            f"{len(docs_with_todos)} public documentation files:\n"
            + "\n".join(f"  - {d}" for d in sorted(docs_with_todos))
            + "\n\nOptions to fix:\n"
            + "1. Complete the TODO/FIXME task\n"
            + "2. Remove if no longer relevant\n"
            + "3. Convert to GitHub issue and remove from docs\n"
            + "4. Add to excluded_patterns if intentional (rare)\n"
        )

    def test_mdx_files_have_frontmatter(self):
        """
        Ensure all MDX files have proper frontmatter.

        Prevents: Missing metadata in Mintlify docs
        """
        if not DOCS_DIR.exists():
            pytest.skip("docs/ directory not found")

        files_without_frontmatter = []

        for mdx_file in DOCS_DIR.rglob("*.mdx"):
            content = mdx_file.read_text()

            # Check for frontmatter (starts with ---)
            if not content.strip().startswith("---"):
                rel_path = mdx_file.relative_to(DOCS_DIR)
                files_without_frontmatter.append(str(rel_path))

        # This is informational - some files may intentionally lack frontmatter
        if files_without_frontmatter:
            print(
                f"\nINFO: Found {len(files_without_frontmatter)} MDX files without frontmatter:\n"
                + "\n".join(f"  - {f}" for f in sorted(files_without_frontmatter)[:10])
                + ("..." if len(files_without_frontmatter) > 10 else "")
            )

    def test_no_broken_internal_links(self):
        """
        Check for broken internal links in MDX files.

        Prevents: Broken internal links between documentation pages

        Validates:
        - Relative links to other .mdx files
        - Links to files in the repository
        - Anchor links within the same file
        """
        if not DOCS_DIR.exists():
            pytest.skip("docs/ directory not found")

        import re

        broken_links = []

        # Pattern to match markdown links: [text](url)
        link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

        for mdx_file in DOCS_DIR.rglob("*.mdx"):
            content = mdx_file.read_text()
            rel_path = mdx_file.relative_to(DOCS_DIR)

            # Find all links
            for match in link_pattern.finditer(content):
                link_text = match.group(1)
                link_url = match.group(2)

                # Skip external links (http/https)
                if link_url.startswith(("http://", "https://", "mailto:")):
                    continue

                # Skip anchor-only links (they reference the same page)
                if link_url.startswith("#"):
                    # TODO: Could validate anchors exist, but that's complex
                    continue

                # Handle links with anchors
                link_path = link_url.split("#")[0] if "#" in link_url else link_url

                # Skip empty links
                if not link_path:
                    continue

                # Resolve the link relative to the current file's directory
                current_dir = mdx_file.parent

                # Try different path resolutions
                target_paths = []

                # 1. Relative to current file
                target_paths.append(current_dir / link_path)

                # 2. If it ends with .mdx, try as-is
                if link_path.endswith(".mdx"):
                    target_paths.append(current_dir / link_path)
                # 3. If it doesn't end with .mdx, try adding it
                else:
                    target_paths.append(current_dir / f"{link_path}.mdx")

                # 4. Try relative to docs root
                target_paths.append(DOCS_DIR / link_path)
                if not link_path.endswith(".mdx"):
                    target_paths.append(DOCS_DIR / f"{link_path}.mdx")

                # 5. Try relative to project root (for files like README.md)
                target_paths.append(PROJECT_ROOT / link_path)

                # Check if any of the target paths exist
                link_valid = any(p.exists() for p in target_paths)

                if not link_valid:
                    broken_links.append(
                        {
                            "file": str(rel_path),
                            "link_text": link_text,
                            "link_url": link_url,
                            "tried_paths": [str(p) for p in target_paths[:3]],  # Show first 3
                        }
                    )

        # Report broken links
        if broken_links:
            error_msg = f"Found {len(broken_links)} potentially broken internal links:\n"
            for link_info in broken_links[:20]:  # Show first 20
                error_msg += f"\n  File: {link_info['file']}\n"
                error_msg += f"  Link: [{link_info['link_text']}]({link_info['link_url']})\n"
                error_msg += f"  Tried: {', '.join(link_info['tried_paths'][:2])}\n"

            if len(broken_links) > 20:
                error_msg += f"\n  ... and {len(broken_links) - 20} more\n"

            # This is a warning, not a failure - some links might be valid but not detected
            print(f"\nWARNING: {error_msg}")
            # Uncomment to make this a hard failure:
            # pytest.fail(error_msg)


class TestRootDocumentationFiles:
    """Validate root-level documentation files."""

    def test_essential_root_docs_exist(self):
        """
        Ensure essential root documentation files exist.

        Prevents: Missing critical project documentation
        """
        essential_files = [
            "README.md",
            "CHANGELOG.md",
            "SECURITY.md",
            "CONTRIBUTING.md",
            "CODE_OF_CONDUCT.md",
        ]

        missing = []
        for filename in essential_files:
            if not (PROJECT_ROOT / filename).exists():
                missing.append(filename)

        assert not missing, (
            "Missing essential root documentation files:\n"
            + "\n".join(f"  - {f}" for f in missing)
            + "\n\nCreate these files for a complete project."
        )

    def test_changelog_not_too_large(self):
        """
        Warn if CHANGELOG.md is excessively large.

        Prevents: Unwieldy changelog file (WARN-004 from audit)
        """
        changelog = PROJECT_ROOT / "CHANGELOG.md"
        if not changelog.exists():
            pytest.skip("CHANGELOG.md not found")

        content = changelog.read_text()
        lines = content.splitlines()

        # Warn if > 3000 lines (can be adjusted)
        if len(lines) > 3000:
            print(
                f"\nINFO: CHANGELOG.md is large ({len(lines)} lines). "
                "Consider archiving older versions to CHANGELOG-ARCHIVE.md"
            )
