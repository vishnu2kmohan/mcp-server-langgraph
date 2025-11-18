#!/usr/bin/env python3
"""
Compatibility shim for check_internal_links module.

This module was refactored and archived, but tests still depend on it.
This shim maintains backward compatibility by importing functions from
the archived version.

NOTE: This is a temporary compatibility layer for tests.
New code should use validate_mintlify_docs.py or validate_documentation_links.py

See: scripts/validators/archive/check_internal_links.py.deprecated
"""

import re
from pathlib import Path
from typing import List, Optional


def extract_internal_links(content: str) -> list[str]:
    """
    Extract internal link targets from markdown/MDX content.

    Args:
        content: The file content

    Returns:
        List of internal link targets (relative or absolute paths)
    """
    links = []

    # Pattern 1: [text](path) markdown links
    markdown_links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
    for text, url in markdown_links:
        # Skip external URLs
        if url.startswith(("http://", "https://", "mailto:", "tel:")):
            continue

        # Skip pure anchors
        if url.startswith("#"):
            continue

        # Remove anchor from URL
        url = url.split("#")[0]

        if url:
            links.append(url)

    # Pattern 2: MDX Link components
    mdx_links = re.findall(r'<Link\s+href=["\']([^"\']+)["\']', content)
    for url in mdx_links:
        if not url.startswith(("http://", "https://", "#")):
            links.append(url)

    # Pattern 3: Card/Button href attributes
    component_links = re.findall(r'href=["\']([^"\']+)["\']', content)
    for url in component_links:
        if not url.startswith(("http://", "https://", "mailto:", "#")):
            url_clean = url.split("#")[0]
            if url_clean and url_clean not in links:
                links.append(url_clean)

    return list(set(links))  # Remove duplicates


def resolve_link(source_file: Path, target: str, docs_root: Path | None = None) -> Path | None:
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
        docs_root = Path("docs").resolve()

    try:
        # Absolute path from docs root
        if target.startswith("/"):
            resolved = docs_root / target.lstrip("/")
        else:
            # Relative path from source file
            resolved = (source_file.parent / target).resolve()

        # Try with and without .mdx extension
        if resolved.exists():
            return resolved

        if not resolved.suffix:
            mdx_version = resolved.with_suffix(".mdx")
            if mdx_version.exists():
                return mdx_version

            md_version = resolved.with_suffix(".md")
            if md_version.exists():
                return md_version

        return None

    except Exception:
        return None


def check_internal_links(file_path: Path, docs_root: Path | None = None) -> list[str]:
    """
    Check all internal links in a file.

    Args:
        file_path: Path to the file to check
        docs_root: Root directory for docs

    Returns:
        List of broken link targets
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        links = extract_internal_links(content)

        broken = []
        for link in links:
            resolved = resolve_link(file_path, link, docs_root)
            if resolved is None or not resolved.exists():
                broken.append(link)

        return broken

    except Exception as e:
        print(f"Error checking {file_path}: {e}")
        return []


def validate_file_links(file_path: Path, docs_root: Path | None = None) -> list[str]:
    """
    Validate links in a single file.

    Args:
        file_path: Path to the file to validate
        docs_root: Root directory for docs

    Returns:
        List of broken links found
    """
    return check_internal_links(file_path, docs_root)


def validate_all_links(docs_root: Path) -> int:
    """
    Validate all links in documentation.

    Args:
        docs_root: Root directory of documentation

    Returns:
        Number of broken links found
    """
    broken_count = 0

    for file_path in docs_root.rglob("*.mdx"):
        broken = check_internal_links(file_path, docs_root)
        if broken:
            print(f"\n{file_path.relative_to(docs_root)}:")
            for link in broken:
                print(f"  - Broken link: {link}")
                broken_count += 1

    for file_path in docs_root.rglob("*.md"):
        broken = check_internal_links(file_path, docs_root)
        if broken:
            print(f"\n{file_path.relative_to(docs_root)}:")
            for link in broken:
                print(f"  - Broken link: {link}")
                broken_count += 1

    return broken_count


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Check for broken internal links in documentation")
    parser.add_argument("--file", type=Path, help="Check a single file")
    parser.add_argument("--all", action="store_true", help="Check all documentation files")
    parser.add_argument("--docs-root", type=Path, default=Path("docs"), help="Documentation root directory")

    args = parser.parse_args()

    if args.file:
        broken = check_internal_links(args.file, args.docs_root)
        if broken:
            print(f"Broken links in {args.file}:")
            for link in broken:
                print(f"  - {link}")
            sys.exit(1)
        else:
            print(f"No broken links in {args.file}")
            sys.exit(0)

    elif args.all:
        count = validate_all_links(args.docs_root)
        if count > 0:
            print(f"\nFound {count} broken link(s)")
            sys.exit(1)
        else:
            print("\nNo broken links found!")
            sys.exit(0)

    else:
        parser.print_help()
        sys.exit(1)
