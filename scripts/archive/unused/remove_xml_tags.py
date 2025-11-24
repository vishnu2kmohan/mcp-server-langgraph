#!/usr/bin/env python3
"""Remove stray ```xml tags from MDX files."""

import sys
from pathlib import Path


def fix_file(filepath: Path) -> bool:
    """Fix a single file by removing ```xml tags."""
    try:
        content = filepath.read_text(encoding="utf-8")
        original = content

        # Replace ```xml with just ```
        content = content.replace("```xml\n", "```\n")
        content = content.replace("```xml", "```")

        if content != original:
            filepath.write_text(content, encoding="utf-8")
            return True
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    docs_dir = Path(__file__).parent.parent / "docs"

    mdx_files = list(docs_dir.rglob("*.mdx"))
    mdx_files.extend(docs_dir.rglob("*.md"))

    fixed_count = 0
    for filepath in mdx_files:
        if fix_file(filepath):
            print(f"Fixed: {filepath.relative_to(docs_dir)}")
            fixed_count += 1

    print(f"\nTotal files fixed: {fixed_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
