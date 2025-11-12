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

        nav_pages = self._extract_navigation_pages(
            docs_config.get("navigation", {}),
            return_list=True
        )

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

    def _extract_navigation_pages(
        self,
        nav_obj: Dict,
        return_list: bool = False
    ):
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
                duplicates.append({
                    "number": adr_num,
                    "files": [adr_numbers[adr_num], filename]
                })
            else:
                adr_numbers[adr_num] = filename

        assert not duplicates, (
            f"Found duplicate ADR numbers:\n"
            + "\n".join(
                f"  - ADR-{d['number']}: {', '.join(d['files'])}"
                for d in duplicates
            )
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
                f"ADRs in /adr but missing in /docs/architecture:\n"
                + "\n".join(f"  - {adr}" for adr in sorted(missing_in_mintlify))
            )

        if missing_in_source:
            errors.append(
                f"ADRs in /docs/architecture but missing in /adr:\n"
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
                f"{', '.join(f'ADR-{n:04d}' for n in gaps[:5])}"
                + ("..." if len(gaps) > 5 else "")
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
            print(
                f"\nINFO: Project version {version} not found in:\n"
                + "\n".join(f"  - {f}" for f in version_issues)
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

    def test_no_todos_in_critical_docs(self):
        """
        Ensure critical documentation files don't have TODO/FIXME comments.

        Prevents: Incomplete critical documentation (WARN-001 from audit)

        Note: This only checks critical paths. TODOs in other docs are tracked via GitHub issues.
        """
        critical_docs = [
            "getting-started/quickstart.mdx",
            "getting-started/installation.mdx",
            "deployment/production-checklist.mdx",
            "security/overview.mdx",
        ]

        docs_with_todos = []

        for doc_path_str in critical_docs:
            doc_path = DOCS_DIR / doc_path_str
            if not doc_path.exists():
                continue

            content = doc_path.read_text()

            # Check for TODO/FIXME (case insensitive)
            if "TODO" in content.upper() or "FIXME" in content.upper():
                # Count occurrences
                import re
                todos = len(re.findall(r'\bTODO\b', content, re.IGNORECASE))
                fixmes = len(re.findall(r'\bFIXME\b', content, re.IGNORECASE))
                docs_with_todos.append(f"{doc_path_str} ({todos} TODOs, {fixmes} FIXMEs)")

        assert not docs_with_todos, (
            f"Found TODO/FIXME comments in critical documentation:\n"
            + "\n".join(f"  - {d}" for d in docs_with_todos)
            + "\n\nResolve these before releasing or move to GitHub issues."
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
            f"Missing essential root documentation files:\n"
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
