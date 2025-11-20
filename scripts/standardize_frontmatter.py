#!/usr/bin/env python3
"""
Standardize frontmatter in Mintlify .mdx files.

Standards:
- title: No quotes, Title Case
- description: Single quotes, no ending period
- icon: Single quotes
"""

import re
import sys
from pathlib import Path


def parse_frontmatter(content: str) -> tuple[dict | None, str, str]:
    """
    Parse YAML frontmatter from .mdx content.

    Returns:
        Tuple of (frontmatter_dict, frontmatter_text, body_text)
    """
    # Match frontmatter between --- markers
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
    if not match:
        return None, "", content

    frontmatter_text = match.group(1)
    body_text = match.group(2)

    # Parse frontmatter fields
    frontmatter = {}
    for line in frontmatter_text.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()

    return frontmatter, frontmatter_text, body_text


def unquote(value: str) -> str:
    """Remove quotes from a string if present."""
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def single_quote(value: str) -> str:
    """Add single quotes to a string if it contains special characters."""
    # Remove existing quotes
    value = unquote(value)

    # Check if quotes are needed (contains special chars, colons, etc.)
    if ":" in value or value.startswith("-") or "\n" in value:
        # Escape single quotes in the value
        value = value.replace("'", "''")
        return f"'{value}'"

    # For simple strings, single quotes are still preferred for consistency
    return f"'{value}'"


def standardize_frontmatter(content: str) -> tuple[str, bool]:
    """
    Standardize frontmatter quotes.

    Returns:
        Tuple of (updated_content, was_modified)
    """
    frontmatter, fm_text, body = parse_frontmatter(content)
    if not frontmatter:
        return content, False

    modified = False
    new_lines = []

    for line in fm_text.split("\n"):
        if ":" not in line:
            new_lines.append(line)
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if key == "title":
            # Remove quotes from title, but keep them if title contains colon
            new_value = unquote(value)
            # YAML requires quotes for values containing colons
            if ":" in new_value:
                new_value = f"'{new_value}'"
            if new_value != value:
                modified = True
            new_lines.append(f"{key}: {new_value}")

        elif key == "description":
            # Use single quotes for description
            new_value = single_quote(value)
            if new_value != value:
                modified = True
            new_lines.append(f"{key}: {new_value}")

        elif key == "icon":
            # Use single quotes for icon
            new_value = single_quote(value)
            if new_value != value:
                modified = True
            new_lines.append(f"{key}: {new_value}")

        else:
            # Leave other fields unchanged
            new_lines.append(line)

    if modified:
        new_content = f"---\n{chr(10).join(new_lines)}\n---\n{body}"
        return new_content, True

    return content, False


def process_file(file_path: Path, dry_run: bool = False) -> bool:
    """
    Process a single .mdx file.

    Returns:
        True if file was modified
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        new_content, modified = standardize_frontmatter(content)

        if modified:
            if dry_run:
                print(f"[DRY RUN] Would update: {file_path}")
            else:
                file_path.write_text(new_content, encoding="utf-8")
                print(f"✓ Updated: {file_path}")
            return True

        return False

    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Standardize frontmatter in Mintlify .mdx files")
    parser.add_argument("path", nargs="?", default="docs", help="Path to docs directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without modifying files")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    docs_path = Path(args.path)
    if not docs_path.exists():
        print(f"Error: Path '{docs_path}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Find all .mdx files
    mdx_files = list(docs_path.rglob("*.mdx"))
    if not mdx_files:
        print(f"No .mdx files found in {docs_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(mdx_files)} .mdx files...")
    if args.dry_run:
        print("[DRY RUN MODE - No files will be modified]\n")

    modified_count = 0
    for file_path in sorted(mdx_files):
        if process_file(file_path, args.dry_run):
            modified_count += 1

    print(f"\n{'Would modify' if args.dry_run else 'Modified'}: {modified_count}/{len(mdx_files)} files")

    if args.dry_run and modified_count > 0:
        print("\nRun without --dry-run to apply changes")


if __name__ == "__main__":
    main()
