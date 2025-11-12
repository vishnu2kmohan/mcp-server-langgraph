#!/usr/bin/env python3
"""
Check for broken internal links in documentation.

Validates that internal links in MDX and MD files point to existing files.
Helps prevent broken documentation cross-references.

Usage:
    python3 scripts/check_internal_links.py [--file FILE | --all]

Exit codes:
    0: No broken links
    1: Broken links found
"""

import re
import sys
import argparse
from pathlib import Path
from typing import List, Optional, Set
from urllib.parse import urlparse


def extract_internal_links(content: str) -> List[str]:
    """
    Extract internal link targets from markdown/MDX content.

    Args:
        content: The file content

    Returns:
        List of internal link targets (relative or absolute paths)
    """
    links = []

    # Pattern 1: [text](path) markdown links
    markdown_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
    for text, url in markdown_links:
        # Skip external URLs
        if url.startswith(('http://', 'https://', 'mailto:', 'tel:')):
            continue

        # Skip pure anchors
        if url.startswith('#'):
            continue

        # Remove anchor from URL
        url = url.split('#')[0]

        if url:
            links.append(url)

    # Pattern 2: MDX Link components
    mdx_links = re.findall(r'<Link\s+href=["\']([^"\']+)["\']', content)
    for url in mdx_links:
        if not url.startswith(('http://', 'https://', '#')):
            links.append(url)

    # Pattern 3: Card/Button href attributes
    component_links = re.findall(r'href=["\']([^"\']+)["\']', content)
    for url in component_links:
        if not url.startswith(('http://', 'https://', 'mailto:', '#')):
            url_clean = url.split('#')[0]
            if url_clean and url_clean not in links:
                links.append(url_clean)

    return list(set(links))  # Remove duplicates


def resolve_link(source_file: Path, target: str, docs_root: Optional[Path] = None) -> Optional[Path]:
    """
    Resolve a link target to an absolute path.

    Args:
        source_file: The source file containing the link
        target: The link target (relative or absolute)
        docs_root: Root directory for absolute paths (default: docs/)

    Returns:
        Resolved Path or None if cannot be resolved
    """
    if docs_root is None:
        docs_root = Path('docs').resolve()

    try:
        # Absolute path from docs root
        if target.startswith('/'):
            resolved = docs_root / target.lstrip('/')
        else:
            # Relative path from source file
            resolved = (source_file.parent / target).resolve()

        # Try with and without .mdx extension
        if resolved.exists():
            return resolved

        if not resolved.suffix:
            mdx_version = resolved.with_suffix('.mdx')
            if mdx_version.exists():
                return mdx_version

            md_version = resolved.with_suffix('.md')
            if md_version.exists():
                return md_version

        return None

    except Exception:
        return None


def validate_file_links(file_path: Path, docs_root: Optional[Path] = None) -> List[str]:
    """
    Validate all internal links in a file.

    Args:
        file_path: Path to the file to validate
        docs_root: Root directory for docs

    Returns:
        List of broken link targets
    """
    broken_links = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        links = extract_internal_links(content)

        for link in links:
            resolved = resolve_link(file_path, link, docs_root)
            if resolved is None or not resolved.exists():
                broken_links.append(link)

    except Exception as e:
        print(f"Error validating {file_path}: {e}")

    return broken_links


def main():
    parser = argparse.ArgumentParser(description='Check internal documentation links')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--file', type=str, help='Check a single file')
    group.add_argument('--all', action='store_true', help='Check all documentation files')
    args = parser.parse_args()

    if not args.file and not args.all:
        parser.error("Either --file or --all must be specified")

    if args.file:
        files = [Path(args.file).resolve()]
    else:
        # Check all markdown and MDX files
        md_files = list(Path('.').rglob('*.md'))
        mdx_files = list(Path('docs').rglob('*.mdx')) if Path('docs').exists() else []
        files = md_files + mdx_files
        # Exclude node_modules, .venv, etc.
        files = [f for f in files if 'node_modules' not in str(f) and '.venv' not in str(f)]

    print(f"Checking {len(files)} files for broken internal links...\n")

    total_broken = 0
    files_with_issues = 0

    for file_path in sorted(files):
        broken = validate_file_links(file_path)

        if broken:
            files_with_issues += 1
            total_broken += len(broken)

            relative_path = file_path.relative_to(Path.cwd())
            print(f"❌ {relative_path}")
            for link in broken:
                print(f"   Broken: {link}")
            print()

    if total_broken == 0:
        print("✅ No broken internal links found!")
        return 0
    else:
        print(f"\n📊 Summary: {total_broken} broken links in {files_with_issues} files")
        return 1


if __name__ == "__main__":
    sys.exit(main())
