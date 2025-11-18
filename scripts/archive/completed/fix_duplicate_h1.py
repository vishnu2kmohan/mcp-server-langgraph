#!/usr/bin/env python3
"""
Remove duplicate H1 headings from MDX files.

Mintlify renders the frontmatter title as an H1, so any additional # Heading
in the content creates duplicate H1s which is bad for SEO and accessibility.

This script:
1. Reads frontmatter title
2. Finds the first H1 in content that matches or is similar to title
3. Removes that H1
4. Converts remaining H1s to H2s and adjusts hierarchy
"""

import re
import sys
from pathlib import Path
from typing import Optional, Tuple


def extract_frontmatter_title(content: str) -> str | None:
    """Extract title from frontmatter."""
    match = re.search(r'^---\s*\ntitle:\s*["\']?(.+?)["\']?\s*\n', content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def remove_duplicate_h1(file_path: Path) -> tuple[int, int]:
    """Remove duplicate H1 heading that matches frontmatter title.

    Returns:
        Tuple of (h1_count_before, h1_count_after)
    """
    content = file_path.read_text()

    # Extract frontmatter title
    title = extract_frontmatter_title(content)
    if not title:
        return (0, 0)

    # Count H1s before
    h1_pattern = r"^#\s+(.+)$"
    h1_matches_before = re.findall(h1_pattern, content, re.MULTILINE)
    h1_count_before = len(h1_matches_before)

    if h1_count_before == 0:
        return (0, 0)

    # Find frontmatter block
    frontmatter_match = re.search(r"^(---\s*\n.*?\n---\s*\n)", content, re.DOTALL | re.MULTILINE)
    if not frontmatter_match:
        return (h1_count_before, h1_count_before)

    frontmatter_end = frontmatter_match.end()
    before_content = content[:frontmatter_end]
    after_content = content[frontmatter_end:]

    # Find the first H1 after frontmatter
    first_h1_match = re.search(h1_pattern, after_content, re.MULTILINE)

    if first_h1_match:
        first_h1_text = first_h1_match.group(1).strip()

        # Check if it matches title (exact or similar)
        title_lower = title.lower().strip()
        h1_lower = first_h1_text.lower().strip()

        # Remove if exact match or H1 is a substring/superset of title
        if title_lower == h1_lower or title_lower in h1_lower or h1_lower in title_lower:
            # Remove the first H1 and any blank lines after it
            after_content = re.sub(
                r"^#\s+" + re.escape(first_h1_text) + r"\s*\n+", "", after_content, count=1, flags=re.MULTILINE
            )

    # Convert remaining H1s to H2s and adjust hierarchy
    # H1 → H2, H2 → H3, H3 → H4, H4 → H5, H5 → H6
    def adjust_heading(match):
        level = len(match.group(1))
        heading_text = match.group(2)
        new_level = min(level + 1, 6)
        return "#" * new_level + " " + heading_text

    after_content = re.sub(r"^(#{1,5})\s+(.+)$", adjust_heading, after_content, flags=re.MULTILINE)

    new_content = before_content + after_content

    # Count H1s after (should be 0)
    h1_count_after = len(re.findall(h1_pattern, new_content, re.MULTILINE))

    if new_content != content:
        file_path.write_text(new_content)
        return (h1_count_before, h1_count_after)

    return (h1_count_before, h1_count_before)


def main():
    """Main function to process all MDX files."""
    if len(sys.argv) < 2:
        print("Usage: python fix_duplicate_h1.py <directory>")
        sys.exit(1)

    directory = Path(sys.argv[1])

    if not directory.exists():
        print(f"Error: Directory {directory} does not exist")
        sys.exit(1)

    mdx_files = list(directory.rglob("*.mdx"))

    if not mdx_files:
        print(f"No MDX files found in {directory}")
        return

    print(f"Processing {len(mdx_files)} MDX files in {directory}...")

    total_modified = 0
    total_h1s_before = 0
    total_h1s_after = 0

    for file_path in sorted(mdx_files):
        before, after = remove_duplicate_h1(file_path)

        if before > 0:
            total_h1s_before += before
            total_h1s_after += after

            if before != after:
                total_modified += 1
                removed = before - after
                print(
                    f"  ✓ {file_path.relative_to(directory)}: {before} H1s → {after} H1s ({removed} removed, headings adjusted)"
                )

    print(f"\nSummary:")
    print(f"  Files processed: {len(mdx_files)}")
    print(f"  Files modified: {total_modified}")
    print(f"  H1s before: {total_h1s_before}")
    print(f"  H1s after: {total_h1s_after}")
    print(f"  H1s removed: {total_h1s_before - total_h1s_after}")


if __name__ == "__main__":
    main()
