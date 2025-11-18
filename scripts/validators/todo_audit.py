#!/usr/bin/env python3
"""
TODO/FIXME/XXX Marker Audit Tool

Audits documentation for TODO, FIXME, and XXX markers to track work items.

Features:
1. Finds all TODO/FIXME/XXX markers in documentation
2. Reports location (file and line number)
3. Generates statistics and reports
4. Helps track outstanding work items

Exit codes:
- 0: Audit completed successfully
- 1: Critical error
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set


@dataclass
class TodoMarker:
    """Represents a TODO/FIXME/XXX marker found in documentation."""

    marker_type: str  # TODO, FIXME, XXX
    file_path: str
    line_number: int
    content: str  # The text after the marker


@dataclass
class AuditResult:
    """Result of TODO/FIXME audit."""

    markers: list[TodoMarker] = field(default_factory=list)
    stats: dict[str, any] = field(default_factory=dict)


class TodoAuditor:
    """Audits documentation for TODO/FIXME/XXX markers."""

    # Patterns to exclude from audit
    EXCLUDE_PATTERNS = [
        ".mintlify/templates/",  # Template files
        "node_modules/",  # Dependencies
        ".git/",  # Git directory
        "__pycache__/",  # Python cache
        ".pytest_cache/",  # Pytest cache
    ]

    # Regex patterns for different marker types
    # Matches: TODO:, FIXME:, XXX with optional surrounding characters
    TODO_PATTERN = re.compile(r"\b(TODO|FIXME):\s*(.+?)$", re.IGNORECASE | re.MULTILINE)
    XXX_PATTERN = re.compile(r"XXX+", re.IGNORECASE)

    def __init__(self, docs_dir: Path):
        """
        Initialize auditor.

        Args:
            docs_dir: Path to docs directory
        """
        self.docs_dir = Path(docs_dir)

    def audit(self) -> AuditResult:
        """
        Run audit to find all TODO/FIXME/XXX markers.

        Returns:
            AuditResult with markers and statistics
        """
        markers: list[TodoMarker] = []
        stats: dict[str, any] = {
            "total_files": 0,
            "total_markers": 0,
            "by_type": {"TODO": 0, "FIXME": 0, "XXX": 0},
        }

        if not self.docs_dir.exists():
            return AuditResult(markers=markers, stats=stats)

        # Find all MDX and MD files
        doc_files = self._find_documentation_files()
        stats["total_files"] = len(doc_files)

        for doc_file in doc_files:
            relative_path = doc_file.relative_to(self.docs_dir)
            file_markers = self._audit_file(doc_file, str(relative_path))
            markers.extend(file_markers)

            # Update type statistics
            for marker in file_markers:
                stats["by_type"][marker.marker_type] += 1

        stats["total_markers"] = len(markers)

        return AuditResult(markers=markers, stats=stats)

    def _find_documentation_files(self) -> set[Path]:
        """Find all documentation files (MDX and MD)."""
        files = set()

        # Find MDX files
        for mdx_path in self.docs_dir.rglob("*.mdx"):
            if self._should_include(mdx_path):
                files.add(mdx_path)

        # Find MD files
        for md_path in self.docs_dir.rglob("*.md"):
            if self._should_include(md_path):
                files.add(md_path)

        return files

    def _should_include(self, file_path: Path) -> bool:
        """Check if file should be included in audit."""
        relative_path = file_path.relative_to(self.docs_dir)
        for pattern in self.EXCLUDE_PATTERNS:
            if pattern in str(relative_path):
                return False
        return True

    def _audit_file(self, file_path: Path, relative_path: str) -> list[TodoMarker]:
        """Audit a single file for markers."""
        markers = []

        try:
            content = file_path.read_text()
        except Exception:
            return markers

        lines = content.split("\n")

        # Find TODO and FIXME markers
        for match in self.TODO_PATTERN.finditer(content):
            marker_type = match.group(1).upper()
            marker_content = match.group(2).strip()

            # Calculate line number
            line_number = content[: match.start()].count("\n") + 1

            markers.append(
                TodoMarker(
                    marker_type=marker_type,
                    file_path=relative_path,
                    line_number=line_number,
                    content=marker_content,
                )
            )

        # Find XXX patterns (placeholders)
        for line_num, line in enumerate(lines, start=1):
            if self.XXX_PATTERN.search(line):
                # Extract context around XXX
                marker_content = line.strip()[:100]

                markers.append(
                    TodoMarker(
                        marker_type="XXX",
                        file_path=relative_path,
                        line_number=line_num,
                        content=marker_content,
                    )
                )

        return markers

    def print_report(self, result: AuditResult) -> None:
        """Print audit report to stdout."""
        print("\n" + "=" * 80)
        print("📋 TODO/FIXME/XXX Marker Audit Report")
        print("=" * 80)

        # Statistics
        print("\n📊 Statistics:")
        print(f"  Total files scanned: {result.stats.get('total_files', 0)}")
        print(f"  Total markers found: {result.stats.get('total_markers', 0)}")
        print(f"\n  By type:")
        for marker_type, count in result.stats.get("by_type", {}).items():
            if count > 0:
                print(f"    {marker_type}: {count}")

        # Markers by file
        if result.markers:
            print(f"\n📝 Markers Found:")

            # Group by file
            by_file: dict[str, list[TodoMarker]] = {}
            for marker in result.markers:
                if marker.file_path not in by_file:
                    by_file[marker.file_path] = []
                by_file[marker.file_path].append(marker)

            # Print grouped by file
            for file_path in sorted(by_file.keys()):
                markers_in_file = by_file[file_path]
                print(f"\n  📄 {file_path} ({len(markers_in_file)} markers):")

                # Sort by line number
                for marker in sorted(markers_in_file, key=lambda m: m.line_number):
                    # Truncate content if too long
                    content = marker.content
                    if len(content) > 70:
                        content = content[:70] + "..."

                    icon = {
                        "TODO": "📌",
                        "FIXME": "🔧",
                        "XXX": "⚠️ ",
                    }.get(marker.marker_type, "•")

                    print(f"    {icon} Line {marker.line_number}: [{marker.marker_type}] {content}")

            print("\n  💡 Recommendations:")
            print("     1. Review each marker and determine if it's still relevant")
            print("     2. Complete or remove TODO items that are done")
            print("     3. Fix FIXME issues or create tracking tickets")
            print("     4. Replace XXX placeholders with realistic values")
            print("     5. Document any intentional TODOs with context")

        # Summary
        print("\n" + "=" * 80)
        if result.stats.get("total_markers", 0) == 0:
            print("✅ No TODO/FIXME/XXX markers found!")
        else:
            print(f"📋 Found {result.stats.get('total_markers', 0)} markers to review")
        print("=" * 80 + "\n")


def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Audit documentation for TODO/FIXME/XXX markers")
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("docs"),
        help="Path to docs directory (default: docs/)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output (only use exit code)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "csv"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()

    # Run audit
    auditor = TodoAuditor(args.docs_dir)
    result = auditor.audit()

    # Print report
    if not args.quiet:
        if args.format == "text":
            auditor.print_report(result)
        elif args.format == "json":
            import json

            output = {
                "stats": result.stats,
                "markers": [
                    {
                        "type": m.marker_type,
                        "file": m.file_path,
                        "line": m.line_number,
                        "content": m.content,
                    }
                    for m in result.markers
                ],
            }
            print(json.dumps(output, indent=2))
        elif args.format == "csv":
            print("Type,File,Line,Content")
            for marker in result.markers:
                # Escape CSV content
                content = marker.content.replace('"', '""')
                print(f'"{marker.marker_type}","{marker.file_path}",{marker.line_number},"{content}"')

    # Exit successfully (audit always succeeds)
    sys.exit(0)


if __name__ == "__main__":
    main()
