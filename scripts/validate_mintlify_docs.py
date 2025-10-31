#!/usr/bin/env python3
"""
Validate Mintlify documentation for completeness and consistency.

Checks:
- Frontmatter completeness (title, description, icon)
- Frontmatter formatting (quotes, case)
- Mermaid diagram syntax
- Internal link validity
- Icon consistency within categories
- Filename conventions (kebab-case)
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ValidationIssue:
    """Represents a validation issue."""

    severity: str  # 'error', 'warning', 'info'
    file_path: Path
    line_number: Optional[int]
    category: str
    message: str


@dataclass
class ValidationReport:
    """Aggregates validation results."""

    issues: List[ValidationIssue] = field(default_factory=list)

    def add_issue(self, severity: str, file_path: Path, category: str, message: str, line_number: Optional[int] = None):
        """Add a validation issue."""
        self.issues.append(
            ValidationIssue(
                severity=severity, file_path=file_path, line_number=line_number, category=category, message=message
            )
        )

    def print_summary(self):
        """Print validation summary."""
        errors = [i for i in self.issues if i.severity == "error"]
        warnings = [i for i in self.issues if i.severity == "warning"]
        infos = [i for i in self.issues if i.severity == "info"]

        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        print(f"Total Issues: {len(self.issues)}")
        print(f"  Errors:   {len(errors)}")
        print(f"  Warnings: {len(warnings)}")
        print(f"  Info:     {len(infos)}")
        print("=" * 80)

        if errors:
            print("\n❌ ERRORS:")
            self._print_issues(errors)

        if warnings:
            print("\n⚠️  WARNINGS:")
            self._print_issues(warnings)

        if infos:
            print("\n💡 INFO:")
            self._print_issues(infos)

        if not self.issues:
            print("\n✅ All validation checks passed!")

        return len(errors)

    def _print_issues(self, issues: List[ValidationIssue]):
        """Print a list of issues grouped by category."""
        by_category = {}
        for issue in issues:
            by_category.setdefault(issue.category, []).append(issue)

        for category, cat_issues in sorted(by_category.items()):
            print(f"\n  [{category}]")
            for issue in cat_issues:
                loc = f"{issue.file_path}"
                if issue.line_number:
                    loc += f":{issue.line_number}"
                print(f"    {loc}")
                print(f"      {issue.message}")


def parse_frontmatter(content: str) -> Tuple[Optional[Dict], int]:
    """
    Parse YAML frontmatter from .mdx content.

    Returns:
        Tuple of (frontmatter_dict, frontmatter_end_line)
    """
    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not match:
        return None, 0

    frontmatter_text = match.group(1)
    frontmatter_lines = frontmatter_text.split("\n")
    end_line = len(frontmatter_lines) + 2  # +2 for the --- markers

    frontmatter = {}
    for line_no, line in enumerate(frontmatter_lines, start=2):  # Start at line 2 (after first ---)
        if ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()

    return frontmatter, end_line


def check_frontmatter(file_path: Path, content: str, report: ValidationReport):
    """Check frontmatter completeness and formatting."""
    frontmatter, fm_end = parse_frontmatter(content)

    if not frontmatter:
        report.add_issue("error", file_path, "frontmatter", "Missing frontmatter (must start with ---)")
        return

    # Check required fields
    required_fields = ["title", "description", "icon"]
    for field_name in required_fields:
        if field_name not in frontmatter:
            report.add_issue("error", file_path, "frontmatter", f"Missing required field: {field_name}")

    # Check title formatting (should not have quotes)
    if "title" in frontmatter:
        title = frontmatter["title"]
        if (title.startswith('"') and title.endswith('"')) or (title.startswith("'") and title.endswith("'")):
            report.add_issue("warning", file_path, "frontmatter", f"Title should not have quotes: {title}", line_number=2)

    # Check description formatting (should have single quotes)
    if "description" in frontmatter:
        desc = frontmatter["description"]
        if not ((desc.startswith("'") and desc.endswith("'"))):
            report.add_issue(
                "warning", file_path, "frontmatter", f"Description should use single quotes: {desc}", line_number=3
            )

    # Check icon formatting (should have single quotes)
    if "icon" in frontmatter:
        icon = frontmatter["icon"]
        if not ((icon.startswith("'") and icon.endswith("'"))):
            report.add_issue("warning", file_path, "frontmatter", f"Icon should use single quotes: {icon}", line_number=4)


def check_mermaid_diagrams(file_path: Path, content: str, report: ValidationReport):
    """Check Mermaid diagram syntax."""
    # Find all mermaid code blocks
    mermaid_pattern = r"```mermaid\n(.*?)\n```"
    matches = re.finditer(mermaid_pattern, content, re.DOTALL)

    for match in matches:
        diagram = match.group(1)
        line_number = content[: match.start()].count("\n") + 1

        # Check for common syntax errors
        # Note: This is basic validation. Full Mermaid parsing would require the mermaid library

        # Check for invalid arrow syntax (single dash should be followed by > or -)
        if re.search(r"[^-]-[^->-]", diagram):
            report.add_issue("warning", file_path, "mermaid", "Possible invalid arrow syntax (use --> or --)", line_number)

        # Check for unclosed quotes
        single_quotes = diagram.count("'")
        double_quotes = diagram.count('"')
        if single_quotes % 2 != 0:
            report.add_issue("warning", file_path, "mermaid", "Unclosed single quote in diagram", line_number)
        if double_quotes % 2 != 0:
            report.add_issue("warning", file_path, "mermaid", "Unclosed double quote in diagram", line_number)


def check_internal_links(file_path: Path, content: str, docs_root: Path, report: ValidationReport):
    """Check internal link validity."""
    # Match Mintlify-style links: [text](/path/to/doc) or [text](path/to/doc)
    link_pattern = r"\[([^\]]+)\]\((/[^\)]+)\)"
    matches = re.finditer(link_pattern, content)

    for match in matches:
        link_path = match.group(2)
        line_number = content[: match.start()].count("\n") + 1

        # Skip external links
        if link_path.startswith("http://") or link_path.startswith("https://"):
            continue

        # Skip anchors
        if "#" in link_path:
            link_path = link_path.split("#")[0]
            if not link_path:  # Just an anchor
                continue

        # Skip intentional source file references (outside docs/)
        source_patterns = ["/scripts/", "/config/", "/deployments/", "/api/", "/.env"]
        if any(pattern in link_path for pattern in source_patterns):
            continue  # Intentional reference to source code/config

        # Convert link to file path
        # Mintlify links omit .mdx extension
        if link_path.startswith("/"):
            link_path = link_path[1:]  # Remove leading /

        target_path = docs_root / f"{link_path}.mdx"

        # Also check without .mdx (might be a directory or external reference)
        alt_target = docs_root / link_path

        if not target_path.exists() and not alt_target.exists():
            report.add_issue("error", file_path, "links", f"Broken link: {link_path} (target not found)", line_number)


def check_filename_convention(file_path: Path, report: ValidationReport):
    """Check filename follows kebab-case convention."""
    filename = file_path.stem  # Filename without extension

    # Single-word lowercase is OK
    if filename.islower() and "-" not in filename and "_" not in filename:
        return

    # Check for SCREAMING_SNAKE_CASE or other non-kebab-case
    if "_" in filename or filename.isupper():
        report.add_issue("error", file_path, "filename", f"Filename should use kebab-case: {filename}")
    elif not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", filename):
        # Check if it's mostly kebab-case but has some issues
        if not filename.islower():
            report.add_issue("warning", file_path, "filename", f"Filename should be lowercase kebab-case: {filename}")


def check_icon_consistency(docs_root: Path, report: ValidationReport):
    """Check icon consistency within categories."""
    category_icons = {}

    # Define expected icon patterns
    expected_icons = {
        "architecture": "file-lines",  # ADRs should use file-lines
        "releases": "tag",  # All releases should use tag
    }

    for mdx_file in docs_root.rglob("*.mdx"):
        content = mdx_file.read_text(encoding="utf-8")
        frontmatter, _ = parse_frontmatter(content)

        if not frontmatter or "icon" not in frontmatter:
            continue

        icon = frontmatter["icon"].strip("'\"")

        # Determine category from path
        relative_path = mdx_file.relative_to(docs_root)
        category = relative_path.parts[0] if len(relative_path.parts) > 1 else "root"

        category_icons.setdefault(category, []).append((mdx_file, icon))

    # Check for inconsistencies
    for category, expected_icon in expected_icons.items():
        if category in category_icons:
            for file_path, icon in category_icons[category]:
                if icon != expected_icon:
                    report.add_issue(
                        "warning",
                        file_path,
                        "icon-consistency",
                        f"Expected icon '{expected_icon}' for {category}, found '{icon}'",
                    )


def validate_file(file_path: Path, docs_root: Path, report: ValidationReport):
    """Validate a single .mdx file."""
    try:
        content = file_path.read_text(encoding="utf-8")

        # Run all checks
        check_frontmatter(file_path, content, report)
        check_mermaid_diagrams(file_path, content, report)
        check_internal_links(file_path, content, docs_root, report)
        check_filename_convention(file_path, report)

    except Exception as e:
        report.add_issue("error", file_path, "file-read", f"Error reading file: {e}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate Mintlify documentation")
    parser.add_argument("path", nargs="?", default="docs", help="Path to docs directory (default: docs)")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    parser.add_argument("--file", type=str, help="Validate a single file instead of entire directory")

    args = parser.parse_args()

    docs_path = Path(args.path)
    if not docs_path.exists():
        print(f"Error: Path '{docs_path}' does not exist", file=sys.stderr)
        sys.exit(1)

    report = ValidationReport()

    if args.file:
        # Validate single file
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File '{file_path}' does not exist", file=sys.stderr)
            sys.exit(1)
        print(f"Validating {file_path}...")
        validate_file(file_path, docs_path, report)
    else:
        # Validate all .mdx files (excluding templates)
        mdx_files = [f for f in docs_path.rglob("*.mdx") if ".mintlify/templates" not in str(f)]
        print(f"Validating {len(mdx_files)} .mdx files...")

        for file_path in sorted(mdx_files):
            validate_file(file_path, docs_path, report)

        # Check icon consistency across all files
        check_icon_consistency(docs_path, report)

    # Print summary
    error_count = report.print_summary()

    # Exit code
    if error_count > 0:
        sys.exit(1)
    elif args.strict and any(i.severity == "warning" for i in report.issues):
        print("\n❌ Warnings treated as errors in strict mode")
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
