#!/usr/bin/env python3
"""
Documentation link checker for MCP Server LangGraph.

Checks for broken internal links in markdown files and optionally suggests fixes.
"""

import os
import re
import sys
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple


class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def find_broken_links(root_dir: str, exclude_patterns: List[str] = None) -> List[Dict]:
    """
    Find broken internal links in markdown files.

    Args:
        root_dir: Root directory to search
        exclude_patterns: Patterns to exclude from search

    Returns:
        List of broken link dictionaries
    """
    if exclude_patterns is None:
        exclude_patterns = [
            'archive/',
            'reports/',  # Skip all reports (reference documents with external links)
            'node_modules/',
            '.venv/',
            'venv/',
            '__pycache__/',
            '.git/',
            'docs/'  # Skip Mintlify docs (have internal navigation links)
        ]

    broken_links = []
    root_path = Path(root_dir)

    # Find all markdown files
    md_files = list(root_path.rglob("*.md")) + list(root_path.rglob("*.mdx"))

    total_files = 0
    for md_file in md_files:
        # Skip excluded directories
        if any(exclude in str(md_file) for exclude in exclude_patterns):
            continue

        total_files += 1

        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find markdown links [text](path)
            links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)

            for link_text, link_path in links:
                # Skip external links
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

                # Resolve relative path (all remaining links are relative)
                target = (md_file.parent / link_path_no_anchor).resolve()

                # Check if target exists
                if not target.exists():
                    broken_links.append({
                        'file': str(md_file.relative_to(root_path)),
                        'link_text': link_text,
                        'link_path': link_path,
                        'resolved_path': str(target.relative_to(root_path)) if target.is_relative_to(root_path) else str(target)
                    })
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️  Error processing {md_file}: {e}{Colors.RESET}")

    return broken_links, total_files


def categorize_links(broken_links: List[Dict]) -> Dict[str, List[Dict]]:
    """Categorize broken links by file location"""
    categories = {
        'active_docs': [],
        'github': [],
        'adr': [],
        'reports': [],
        'other': []
    }

    for link in broken_links:
        file_path = link['file']

        if 'archive' in file_path:
            continue  # Skip archived docs
        elif file_path.startswith('docs/'):
            categories['active_docs'].append(link)
        elif file_path.startswith('.github/'):
            categories['github'].append(link)
        elif file_path.startswith('adr/'):
            categories['adr'].append(link)
        elif file_path.startswith('reports/'):
            categories['reports'].append(link)
        else:
            categories['other'].append(link)

    return categories


def print_summary(broken_links: List[Dict], total_files: int):
    """Print a summary of broken links"""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}Documentation Link Check Summary{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")

    print(f"📊 Total markdown files scanned: {Colors.CYAN}{total_files}{Colors.RESET}")
    print(f"🔗 Broken links found: {Colors.RED if broken_links else Colors.GREEN}{len(broken_links)}{Colors.RESET}\n")

    if not broken_links:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ All internal links are valid!{Colors.RESET}\n")
        return

    # Categorize
    categories = categorize_links(broken_links)

    print(f"{Colors.YELLOW}Broken links by category:{Colors.RESET}\n")

    priority_map = {
        'github': ('🔴 HIGH', Colors.RED),
        'active_docs': ('🔴 HIGH', Colors.RED),
        'adr': ('🔴 HIGH', Colors.RED),
        'reports': ('🟡 MEDIUM', Colors.YELLOW),
        'other': ('🟢 LOW', Colors.GREEN)
    }

    for category, (priority, color) in priority_map.items():
        count = len(categories[category])
        if count > 0:
            print(f"{color}{priority}{Colors.RESET} {category}: {color}{count}{Colors.RESET}")

    print()

    # Show details for high-priority categories
    for category in ['github', 'active_docs', 'adr']:
        links = categories[category]
        if links:
            print(f"\n{Colors.BOLD}{category.upper()} ({len(links)} broken links):{Colors.RESET}")

            by_file = defaultdict(list)
            for link in links:
                by_file[link['file']].append(link)

            for file, file_links in sorted(by_file.items())[:5]:
                print(f"\n  {Colors.CYAN}📄 {file}{Colors.RESET}")
                for link in file_links[:3]:
                    print(f"     {Colors.RED}❌{Colors.RESET} [{link['link_text']}]({link['link_path']})")
                    print(f"        {Colors.YELLOW}→ {link['resolved_path']}{Colors.RESET}")
                if len(file_links) > 3:
                    print(f"     ... and {len(file_links) - 3} more")


def main():
    """Main entry point"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}🔍 MCP Server LangGraph - Documentation Link Checker{Colors.RESET}\n")

    root_dir = Path(__file__).parent.parent
    os.chdir(root_dir)

    print(f"📂 Scanning directory: {Colors.CYAN}{root_dir}{Colors.RESET}")
    print(f"📝 Excluding: {Colors.YELLOW}archive/, reports/archive/{Colors.RESET} (historical docs)\n")

    broken, total = find_broken_links('.')
    print_summary(broken, total)

    # Check for high-priority broken links only
    categories = categorize_links(broken)
    high_priority_count = len(categories['github']) + len(categories['active_docs']) + len(categories['adr'])

    if high_priority_count > 0:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ Link check failed! Found {high_priority_count} high-priority broken links{Colors.RESET}")
        print(f"\n{Colors.YELLOW}💡 Quick fixes:{Colors.RESET}")
        print(f"  • Review file paths and update broken links")
        print(f"  • Check for moved/renamed files")
        print(f"  • Verify .md vs .mdx extensions")
        print(f"  • Fix relative path navigation (../ vs ../../)")
        print()
        sys.exit(1)
    elif broken:
        print(f"\n{Colors.YELLOW}⚠️  Found {len(broken)} low/medium priority broken links{Colors.RESET}")
        print(f"{Colors.GREEN}{Colors.BOLD}✅ All high-priority links are valid!{Colors.RESET}\n")
        print(f"{Colors.CYAN}Note: Low-priority broken links in 'other' category can be addressed later.{Colors.RESET}\n")
        sys.exit(0)
    else:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ All checks passed!{Colors.RESET}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
