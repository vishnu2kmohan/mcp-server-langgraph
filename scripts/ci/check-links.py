#!/usr/bin/env python3
"""
Documentation Link Checker

Validates internal documentation links in Markdown files.
Extracted from .github/workflows/link-checker.yml for maintainability.

Usage:
    python scripts/ci/check-links.py [--root-dir PATH] [--exclude PATTERN ...]

Exit codes:
    0 - All high-priority links valid
    1 - Broken high-priority links found
"""

import re
import argparse
import sys
from pathlib import Path
from collections import defaultdict


def find_broken_links(root_dir, exclude_patterns=None):
    """Find broken internal links in markdown files"""
    if exclude_patterns is None:
        exclude_patterns = ['archive/', 'reports/', 'node_modules/', '.venv/', 'venv/', 'docs/']

    broken_links = []
    root_path = Path(root_dir)

    # Find all markdown files
    md_files = list(root_path.rglob("*.md")) + list(root_path.rglob("*.mdx"))

    for md_file in md_files:
        # Skip excluded directories
        if any(exclude in str(md_file) for exclude in exclude_patterns):
            continue

        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find markdown links [text](path)
            links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)

            for link_text, link_path in links:
                # Skip external links and anchors
                if link_path.startswith(('http://', 'https://', 'mailto:', '#')):
                    continue

                # Skip Mintlify internal navigation links (start with /)
                if link_path.startswith('/') and not link_path.startswith('//'):
                    continue

                # Skip invalid markdown (like **arguments)
                if link_path.startswith('**'):
                    continue

                # Remove anchors
                link_path_no_anchor = link_path.split('#')[0]
                if not link_path_no_anchor:
                    continue

                # Resolve relative path
                if link_path_no_anchor.startswith('/'):
                    target = root_path / link_path_no_anchor.lstrip('/')
                else:
                    target = (md_file.parent / link_path_no_anchor).resolve()

                # Check if target exists
                if not target.exists():
                    broken_links.append({
                        'file': str(md_file.relative_to(root_path)),
                        'link_text': link_text,
                        'link_path': link_path,
                        'line': None  # Could add line number if needed
                    })
        except Exception as e:
            print(f"⚠️  Error processing {md_file}: {e}")

    return broken_links


def categorize_links(broken_links):
    """Categorize broken links by priority"""
    categories = {cat: [] for cat in ['github', 'adr', 'other']}

    for link in broken_links:
        file_path = link['file']
        if file_path.startswith('.github/'):
            categories['github'].append(link)
        elif file_path.startswith('adr/'):
            categories['adr'].append(link)
        else:
            categories['other'].append(link)

    return categories


def main():
    parser = argparse.ArgumentParser(description='Check internal documentation links')
    parser.add_argument('--root-dir', default='.', help='Root directory to search (default: current directory)')
    parser.add_argument('--exclude', nargs='*', default=['archive/', 'reports/', 'docs/'],
                        help='Directories to exclude (default: archive/, reports/, docs/)')

    args = parser.parse_args()

    print("🔍 Checking for broken internal links...")
    print(f"Excluding: {', '.join(args.exclude)} (historical docs and Mintlify navigation)")
    print()

    broken = find_broken_links(args.root_dir, args.exclude)
    categories = categorize_links(broken)
    high_priority = categories['github'] + categories['adr']

    if high_priority:
        print(f"❌ Found {len(high_priority)} HIGH-PRIORITY broken links:")
        print()

        by_file = defaultdict(list)
        for link in high_priority:
            by_file[link['file']].append(link)

        for file, links in sorted(by_file.items())[:10]:
            print(f"📄 {file}:")
            for link in links[:3]:
                print(f"   ❌ [{link['link_text']}]({link['link_path']})")
            print()

        print("Please fix these high-priority broken links before merging.")
        sys.exit(1)
    elif broken:
        print(f"⚠️  Found {len(broken)} low-priority broken links (acceptable)")
        print("✅ All high-priority links (GitHub, ADR, active docs) are valid!")
        print()
        print("Note: Low-priority links can be addressed later.")
        sys.exit(0)
    else:
        print("✅ No broken internal links found!")
        print()
        print("All internal links are valid. Great job! 🎉")
        sys.exit(0)


if __name__ == '__main__':
    main()
