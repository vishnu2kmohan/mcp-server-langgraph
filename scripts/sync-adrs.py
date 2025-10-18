#!/usr/bin/env python3
"""
ADR Sync Script - Automatically convert adr/*.md to docs/architecture/*.mdx

This script maintains synchronization between source ADR files (markdown)
and Mintlify documentation (MDX) by automatically converting and updating
the frontmatter.

Usage:
    python scripts/sync-adrs.py                    # Sync all ADRs
    python scripts/sync-adrs.py --check            # Check for differences
    python scripts/sync-adrs.py --adr 0001         # Sync specific ADR
    python scripts/sync-adrs.py --dry-run          # Preview changes
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class Colors:
    """ANSI color codes"""

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def extract_title_and_date(content: str) -> Tuple[str, str]:
    """
    Extract title and date from ADR content.

    Args:
        content: ADR markdown content

    Returns:
        Tuple of (title, date)
    """
    # Extract title (first # heading)
    title_match = re.search(r"^# (.+)$", content, re.MULTILINE)
    title = title_match.group(1) if title_match else "Unknown ADR"

    # Extract date
    date_match = re.search(r"^Date: (.+)$", content, re.MULTILINE)
    date = date_match.group(1) if date_match else "Unknown"

    return title, date


def generate_frontmatter(title: str, date: str) -> str:
    """
    Generate MDX frontmatter from ADR metadata.

    Args:
        title: ADR title
        date: ADR date

    Returns:
        Formatted frontmatter string
    """
    return f"""---
title: "{title}"
description: "Architecture Decision Record: {title}"
---

"""


def convert_adr_to_mdx(md_content: str) -> str:
    """
    Convert ADR markdown to MDX format with frontmatter.

    Args:
        md_content: Source markdown content

    Returns:
        MDX content with frontmatter
    """
    title, date = extract_title_and_date(md_content)
    frontmatter = generate_frontmatter(title, date)

    return frontmatter + md_content


def sync_adr(adr_number: str, dry_run: bool = False) -> bool:
    """
    Sync a single ADR from source to destination.

    Args:
        adr_number: ADR number (e.g., "0001")
        dry_run: If True, only preview changes

    Returns:
        True if sync was needed, False otherwise
    """
    source_path = Path(f"adr/{adr_number}-*.md")
    source_files = list(Path("adr").glob(f"{adr_number}-*.md"))

    if not source_files:
        print(f"{Colors.RED}✗ ADR {adr_number} not found in adr/{Colors.RESET}")
        return False

    source_file = source_files[0]
    dest_file = Path(f"docs/architecture/adr-{source_file.name.replace('.md', '.mdx')}")

    # Read source
    with open(source_file, "r", encoding="utf-8") as f:
        source_content = f.read()

    # Convert to MDX
    mdx_content = convert_adr_to_mdx(source_content)

    # Check if update needed
    needs_update = True
    if dest_file.exists():
        with open(dest_file, "r", encoding="utf-8") as f:
            existing_content = f.read()

        # Extract body (skip frontmatter) for comparison
        source_body = source_content
        existing_body = re.sub(r"^---\n.*?\n---\n\n", "", existing_content, flags=re.DOTALL)

        if source_body.strip() == existing_body.strip():
            needs_update = False

    if needs_update:
        if dry_run:
            print(f"{Colors.YELLOW}⚠ Would update: {dest_file.name}{Colors.RESET}")
        else:
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_file, "w", encoding="utf-8") as f:
                f.write(mdx_content)
            print(f"{Colors.GREEN}✓ Synced: {source_file.name} → {dest_file.name}{Colors.RESET}")
        return True
    else:
        print(f"{Colors.BLUE}○ Up to date: {dest_file.name}{Colors.RESET}")
        return False


def sync_all_adrs(dry_run: bool = False) -> Dict[str, int]:
    """
    Sync all ADRs from adr/ to docs/architecture/

    Args:
        dry_run: If True, only preview changes

    Returns:
        Dict with counts of synced, skipped, and failed ADRs
    """
    stats = {"synced": 0, "skipped": 0, "failed": 0}

    # Find all ADR files
    adr_files = sorted(Path("adr").glob("*.md"))
    adr_files = [f for f in adr_files if f.name != "README.md"]

    if not adr_files:
        print(f"{Colors.RED}No ADR files found in adr/{Colors.RESET}")
        return stats

    print(f"\n{Colors.BOLD}Syncing {len(adr_files)} ADRs...{Colors.RESET}\n")

    for adr_file in adr_files:
        # Extract ADR number (e.g., "0001" from "0001-llm-multi-provider.md")
        match = re.match(r"(\d{4})-", adr_file.name)
        if not match:
            continue

        adr_number = match.group(1)

        try:
            if sync_adr(adr_number, dry_run):
                stats["synced"] += 1
            else:
                stats["skipped"] += 1
        except Exception as e:
            print(f"{Colors.RED}✗ Failed to sync ADR {adr_number}: {e}{Colors.RESET}")
            stats["failed"] += 1

    return stats


def check_sync_status() -> bool:
    """
    Check if all ADRs are in sync.

    Returns:
        True if all in sync, False otherwise
    """
    print(f"\n{Colors.BOLD}Checking ADR sync status...{Colors.RESET}\n")

    out_of_sync = []

    # Find all ADR files
    adr_files = sorted(Path("adr").glob("*.md"))
    adr_files = [f for f in adr_files if f.name != "README.md"]

    for adr_file in adr_files:
        match = re.match(r"(\d{4})-", adr_file.name)
        if not match:
            continue

        adr_number = match.group(1)
        source_file = adr_file
        dest_file = Path(f"docs/architecture/adr-{source_file.name.replace('.md', '.mdx')}")

        if not dest_file.exists():
            out_of_sync.append((adr_number, "missing"))
            print(f"{Colors.RED}✗ Missing: {dest_file.name}{Colors.RESET}")
            continue

        # Read both files
        with open(source_file, "r", encoding="utf-8") as f:
            source_content = f.read()

        with open(dest_file, "r", encoding="utf-8") as f:
            dest_content = f.read()

        # Extract body for comparison
        dest_body = re.sub(r"^---\n.*?\n---\n\n", "", dest_content, flags=re.DOTALL)

        if source_content.strip() != dest_body.strip():
            out_of_sync.append((adr_number, "different"))
            print(f"{Colors.YELLOW}⚠ Out of sync: {dest_file.name}{Colors.RESET}")
        else:
            print(f"{Colors.GREEN}✓ In sync: {dest_file.name}{Colors.RESET}")

    if out_of_sync:
        print(f"\n{Colors.YELLOW}{len(out_of_sync)} ADR(s) out of sync{Colors.RESET}")
        print(f"\nRun {Colors.BOLD}python scripts/sync-adrs.py{Colors.RESET} to sync")
        return False
    else:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All ADRs are in sync!{Colors.RESET}")
        return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Sync ADR markdown files to Mintlify MDX format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Sync all ADRs
  %(prog)s --check            Check sync status
  %(prog)s --adr 0001         Sync specific ADR
  %(prog)s --dry-run          Preview changes
        """,
    )
    parser.add_argument("--adr", metavar="NUMBER", help="Sync specific ADR by number (e.g., 0001)")
    parser.add_argument("--check", action="store_true", help="Check sync status without making changes")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")

    args = parser.parse_args()

    # Change to repo root
    repo_root = Path(__file__).parent.parent
    import os

    os.chdir(repo_root)

    print(f"\n{Colors.BOLD}{Colors.BLUE}ADR Sync Tool{Colors.RESET}")
    print(f"Source: {Colors.BOLD}adr/*.md{Colors.RESET}")
    print(f"Destination: {Colors.BOLD}docs/architecture/*.mdx{Colors.RESET}")

    if args.check:
        # Check sync status
        in_sync = check_sync_status()
        sys.exit(0 if in_sync else 1)

    elif args.adr:
        # Sync specific ADR
        print(f"\nSyncing ADR {args.adr}...\n")
        success = sync_adr(args.adr, args.dry_run)
        sys.exit(0 if success else 1)

    else:
        # Sync all ADRs
        stats = sync_all_adrs(args.dry_run)

        print(f"\n{Colors.BOLD}Summary:{Colors.RESET}")
        print(f"  {Colors.GREEN}Synced: {stats['synced']}{Colors.RESET}")
        print(f"  {Colors.BLUE}Skipped: {stats['skipped']}{Colors.RESET}")
        print(f"  {Colors.RED}Failed: {stats['failed']}{Colors.RESET}")

        if args.dry_run:
            print(f"\n{Colors.YELLOW}Dry run completed. No files were modified.{Colors.RESET}")
        else:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Sync complete!{Colors.RESET}")

        sys.exit(0 if stats["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
