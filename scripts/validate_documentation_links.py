#!/usr/bin/env python3
"""
Comprehensive documentation link validator.

This script validates all internal links in markdown and mdx files,
categorizes broken links, and generates a detailed report.
"""

import re
import os
import glob
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Set


class DocumentationLinkValidator:
    """Validates links in documentation files."""

    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir).resolve()
        self.broken_links: List[Dict] = []
        self.all_files: Set[Path] = set()
        self.categories = defaultdict(list)

    def find_all_docs(self) -> Set[Path]:
        """Find all markdown and mdx files."""
        files = set()
        for pattern in ["**/*.md", "**/*.mdx"]:
            for file_path in self.root_dir.glob(pattern):
                # Skip node_modules, .git, and virtual environments
                if any(part in file_path.parts for part in [".git", "node_modules", "venv", ".venv", "__pycache__"]):
                    continue
                files.add(file_path)
        return files

    def extract_links(self, file_path: Path) -> List[Tuple[str, str]]:
        """Extract markdown links from a file."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Find markdown links: [text](path)
            link_pattern = r"\[([^\]]+)\]\(([^\)]+)\)"
            links = re.findall(link_pattern, content)
            return links
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return []

    def resolve_link(self, source_file: Path, link_path: str) -> Tuple[Path, bool]:
        """Resolve a link path and check if it exists."""
        # Skip external URLs
        if link_path.startswith(("http://", "https://", "mailto:", "ftp://")):
            return None, True

        # Skip anchors
        if link_path.startswith("#"):
            return None, True

        # Remove anchor from path
        clean_path = link_path.split("#")[0]
        if not clean_path:
            return None, True

        # Resolve relative path
        base_dir = source_file.parent

        # Handle absolute paths from root
        if clean_path.startswith("/"):
            target_path = (self.root_dir / clean_path.lstrip("/")).resolve()
        else:
            target_path = (base_dir / clean_path).resolve()

        # Check if file exists
        exists = target_path.exists()

        return target_path, exists

    def categorize_broken_link(self, source_file: Path, link_path: str, resolved_path: Path):
        """Categorize a broken link by type."""
        category = "other"

        source_str = str(source_file)
        link_lower = link_path.lower()

        # Categorize
        if "compliance" in link_lower:
            category = "missing_compliance_docs"
        elif any(x in link_path for x in ["LITELLM_GUIDE", "README_OPENFGA", "PYDANTIC_AI"]):
            category = "missing_reference_files"
        elif "archive" in source_str or "archive" in link_path:
            category = "archive_issues"
        elif "CHANGELOG" in source_str:
            category = "changelog_references"
        elif link_path.endswith(".md") and "docs/" in str(source_file):
            category = "md_mdx_mismatch"
        elif link_path.startswith("/"):
            category = "absolute_path_issues"
        elif "adr/" in source_str:
            category = "adr_cross_references"

        return category

    def validate_all_links(self):
        """Validate all links in all documentation files."""
        print("Finding all documentation files...")
        self.all_files = self.find_all_docs()
        print(f"Found {len(self.all_files)} documentation files")

        print("\nValidating links...")
        for file_path in sorted(self.all_files):
            links = self.extract_links(file_path)

            for link_text, link_path in links:
                resolved_path, exists = self.resolve_link(file_path, link_path)

                if resolved_path is None:
                    # Skipped (external or anchor)
                    continue

                if not exists:
                    category = self.categorize_broken_link(file_path, link_path, resolved_path)

                    broken_link = {
                        "source_file": str(file_path.relative_to(self.root_dir)),
                        "link_text": link_text,
                        "link_path": link_path,
                        "resolved_path": str(
                            resolved_path.relative_to(self.root_dir)
                            if resolved_path.is_relative_to(self.root_dir)
                            else resolved_path
                        ),
                        "category": category,
                    }

                    self.broken_links.append(broken_link)
                    self.categories[category].append(broken_link)

        print(f"Found {len(self.broken_links)} broken links\n")

    def generate_report(self) -> str:
        """Generate a detailed report of broken links."""
        report_lines = []
        report_lines.append("# Documentation Link Validation Report")
        report_lines.append(f"\nGenerated: {self._get_timestamp()}")
        report_lines.append(f"\n## Summary\n")
        report_lines.append(f"- Total files scanned: {len(self.all_files)}")
        report_lines.append(f"- Total broken links: {len(self.broken_links)}")
        report_lines.append(f"- Categories: {len(self.categories)}")

        # Summary by category
        report_lines.append(f"\n## Broken Links by Category\n")
        for category, links in sorted(self.categories.items(), key=lambda x: len(x[1]), reverse=True):
            report_lines.append(f"### {category.replace('_', ' ').title()} ({len(links)} links)\n")

            # Group by source file
            by_file = defaultdict(list)
            for link in links:
                by_file[link["source_file"]].append(link)

            for source_file, file_links in sorted(by_file.items()):
                report_lines.append(f"**{source_file}**:")
                for link in file_links:
                    report_lines.append(f"- Link: `{link['link_path']}`")
                    report_lines.append(f"  - Text: \"{link['link_text']}\"")
                    report_lines.append(f"  - Resolved to: `{link['resolved_path']}`")
                report_lines.append("")

        # Recommendations
        report_lines.append("\n## Recommendations\n")

        if "missing_compliance_docs" in self.categories:
            report_lines.append("### Compliance Documentation")
            report_lines.append("- Create placeholder compliance docs or remove broken links")
            report_lines.append("- Files: `docs/compliance/gdpr.md`, `docs/compliance/hipaa.md`, `docs/compliance/soc2.md`\n")

        if "missing_reference_files" in self.categories:
            report_lines.append("### Reference Documentation")
            report_lines.append("- Create missing reference files or update links to existing integration docs")
            report_lines.append("- Consider consolidating into `integrations/` or `reference/` directories\n")

        if "md_mdx_mismatch" in self.categories:
            report_lines.append("### Format Mismatches")
            report_lines.append("- Update links to use correct file extensions (.md vs .mdx)")
            report_lines.append("- Consider converting .md files to .mdx for consistency\n")

        if "changelog_references" in self.categories:
            report_lines.append("### CHANGELOG References")
            report_lines.append("- Update CHANGELOG.md to reference existing files in reports/")
            report_lines.append("- Remove references to files that don't exist\n")

        return "\n".join(report_lines)

    def generate_json_report(self) -> str:
        """Generate a JSON report for programmatic processing."""
        report = {
            "timestamp": self._get_timestamp(),
            "summary": {
                "total_files": len(self.all_files),
                "total_broken_links": len(self.broken_links),
                "categories": {cat: len(links) for cat, links in self.categories.items()},
            },
            "broken_links": self.broken_links,
            "by_category": {cat: links for cat, links in self.categories.items()},
        }
        return json.dumps(report, indent=2)

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate documentation links")
    parser.add_argument("--root", default=".", help="Root directory to scan")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")

    args = parser.parse_args()

    validator = DocumentationLinkValidator(args.root)
    validator.validate_all_links()

    if args.json:
        report = validator.generate_json_report()
    else:
        report = validator.generate_report()

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
