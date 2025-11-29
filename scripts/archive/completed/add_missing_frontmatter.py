#!/usr/bin/env python3
"""
Add Missing Frontmatter Fields

Automatically adds missing icon and contentType fields to MDX files
based on intelligent defaults derived from file paths and content.

Usage:
    python scripts/add_missing_frontmatter.py [--dry-run]
"""

import re
import sys
from pathlib import Path

# Icon mapping based on directory/file patterns
ICON_MAP = {
    # Top-level categories
    "getting-started": "rocket",
    "guides": "book-open",
    "api-reference": "code",
    "deployment": "server",
    "architecture": "sitemap",
    "security": "shield",
    "compliance": "file-contract",
    "ci-cd": "circle-nodes",
    "reference": "book",
    "comparisons": "scale-balanced",
    "releases": "tag",
    "workflows": "diagram-project",
    # Specific patterns
    "adr-": "file-lines",  # Architecture Decision Records
    "kubernetes": "dharmachakra",
    "monitoring": "chart-line",
    "operations": "gears",
    "advanced": "graduation-cap",
    "platform": "cloud",
    "infrastructure": "server",
    "troubleshooting": "wrench",
    "diagrams": "diagram-project",
    "development": "code",
    # Default
    "_default": "book-open",
}

# ContentType mapping based on directory/file patterns
CONTENT_TYPE_MAP = {
    # Directory-based
    "getting-started": "tutorial",
    "guides": "how-to",
    "api-reference": "reference",
    "deployment": "how-to",
    "architecture": "explanation",
    "security": "explanation",
    "compliance": "reference",
    "ci-cd": "how-to",
    "reference": "reference",
    "comparisons": "explanation",
    "releases": "reference",
    "troubleshooting": "how-to",
    "workflows": "explanation",
    "development": "how-to",
    "diagrams": "reference",
    # Specific patterns
    "adr-": "explanation",  # ADRs are explanations
    "quickstart": "tutorial",
    "overview": "explanation",
    "introduction": "explanation",
    "best-practices": "guide",
    "checklist": "reference",
    "runbook": "how-to",
    "template": "reference",
    # Default
    "_default": "explanation",
}


def get_icon_for_file(file_path: Path) -> str:
    """Determine appropriate icon based on file path."""
    # Check specific patterns first
    for pattern, icon in ICON_MAP.items():
        if pattern == "_default":
            continue
        if pattern in str(file_path).lower():
            return icon

    # Check first directory
    parts = file_path.parts
    if len(parts) > 0:
        first_dir = parts[0]
        if first_dir in ICON_MAP:
            return ICON_MAP[first_dir]

    return ICON_MAP["_default"]


def get_content_type_for_file(file_path: Path) -> str:
    """Determine appropriate contentType based on file path."""
    file_name = file_path.stem.lower()

    # Check for ADR pattern first (highest priority)
    if file_name.startswith("adr-"):
        return "explanation"

    # Check specific filename patterns
    for pattern in ["quickstart", "overview", "introduction", "best-practices", "checklist", "runbook", "template"]:
        if pattern in file_name:
            return CONTENT_TYPE_MAP[pattern]

    # Check directory-based patterns
    parts = list(file_path.parts)
    for part in parts:
        part_lower = part.lower()
        if part_lower in CONTENT_TYPE_MAP and part_lower != "_default":
            return CONTENT_TYPE_MAP[part_lower]

    return CONTENT_TYPE_MAP["_default"]


def parse_frontmatter(content: str) -> tuple[dict[str, str], int, int]:
    """
    Parse YAML frontmatter from MDX content.

    Returns:
        Tuple of (frontmatter_dict, start_pos, end_pos)
    """
    import yaml

    # Match frontmatter between --- markers
    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not match:
        return {}, 0, 0

    frontmatter_text = match.group(1)
    start_pos = 0
    end_pos = match.end()

    try:
        frontmatter = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError:
        frontmatter = {}

    return frontmatter, start_pos, end_pos


def add_missing_fields(file_path: Path, dry_run: bool = False) -> bool:
    """
    Add missing icon and contentType fields to a file.

    Returns:
        True if file was modified
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        frontmatter, start_pos, end_pos = parse_frontmatter(content)

        if not frontmatter:
            print(f"⚠️  Skipping {file_path}: No frontmatter found")
            return False

        # Check what's missing
        needs_icon = "icon" not in frontmatter or not frontmatter.get("icon")
        needs_content_type = "contentType" not in frontmatter or not frontmatter.get("contentType")
        needs_fix_content_type = "contentType" in frontmatter and frontmatter.get("contentType") not in [
            "explanation",
            "reference",
            "tutorial",
            "how-to",
            "guide",
        ]

        if not (needs_icon or needs_content_type or needs_fix_content_type):
            return False

        # Get relative path for better icon/content type detection
        try:
            relative_path = file_path.relative_to(Path("docs"))
        except ValueError:
            relative_path = file_path

        # Add missing fields
        modified = False
        if needs_icon:
            icon = get_icon_for_file(relative_path)
            frontmatter["icon"] = icon
            modified = True
            print(f"  + icon: '{icon}'")

        if needs_content_type or needs_fix_content_type:
            content_type = get_content_type_for_file(relative_path)
            old_type = frontmatter.get("contentType")
            frontmatter["contentType"] = content_type
            modified = True
            if needs_fix_content_type:
                print(f"  ~ contentType: '{old_type}' → '{content_type}'")
            else:
                print(f"  + contentType: '{content_type}'")

        if not modified:
            return False

        # Reconstruct frontmatter
        import yaml

        new_frontmatter_text = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)
        new_content = f"---\n{new_frontmatter_text}---\n" + content[end_pos:]

        if dry_run:
            print(f"[DRY RUN] Would update: {file_path}")
            return True
        else:
            file_path.write_text(new_content, encoding="utf-8")
            print(f"✓ Updated: {file_path}")
            return True

    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Add missing frontmatter fields to MDX files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without modifying files")
    parser.add_argument("--docs-dir", default="docs", help="Path to docs directory (default: docs)")

    args = parser.parse_args()

    docs_path = Path(args.docs_dir)
    if not docs_path.exists():
        print(f"Error: Path '{docs_path}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Find all .mdx files
    mdx_files = list(docs_path.rglob("*.mdx"))
    # Exclude templates
    mdx_files = [f for f in mdx_files if ".mintlify/templates" not in str(f)]

    if not mdx_files:
        print(f"No .mdx files found in {docs_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(mdx_files)} .mdx files...")
    if args.dry_run:
        print("[DRY RUN MODE - No files will be modified]\n")

    modified_count = 0
    for file_path in sorted(mdx_files):
        if add_missing_fields(file_path, args.dry_run):
            modified_count += 1

    print(f"\n{'Would modify' if args.dry_run else 'Modified'}: {modified_count}/{len(mdx_files)} files")

    if args.dry_run and modified_count > 0:
        print("\nRun without --dry-run to apply changes")


if __name__ == "__main__":
    main()
