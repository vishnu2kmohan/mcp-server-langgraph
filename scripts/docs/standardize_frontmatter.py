#!/usr/bin/env python3
"""
Standardize frontmatter in Mintlify documentation files.

This script fixes common frontmatter issues:
1. Converts double-quoted icons to single quotes
2. Converts unquoted icons to single quotes
3. Adds missing icons to ADR files based on topic mapping
4. Standardizes contentType format

Usage:
    python scripts/docs/standardize_frontmatter.py                    # Dry-run (report only)
    python scripts/docs/standardize_frontmatter.py --fix              # Apply fixes
    python scripts/docs/standardize_frontmatter.py --fix --verbose    # Apply fixes with details

Exit codes:
    0: All files are valid or fixes applied successfully
    1: Issues found (dry-run) or errors during fixing
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Import icon registry from validate_docs
sys.path.insert(0, str(Path(__file__).parent.parent / "validators"))
from validate_docs import (
    get_suggested_adr_icon,
)


@dataclass
class StandardizationResult:
    """Result of frontmatter standardization."""

    files_scanned: int = 0
    files_modified: int = 0
    icons_fixed: int = 0
    icons_added: int = 0
    errors: list[str] = field(default_factory=list)
    changes: list[tuple[Path, str]] = field(default_factory=list)


def fix_icon_quotes(content: str) -> tuple[str, bool]:
    """
    Fix icon quote style in frontmatter.

    Converts:
    - icon: "value" -> icon: 'value'
    - icon: value -> icon: 'value'

    Returns:
        Tuple of (fixed_content, was_modified)
    """
    was_modified = False

    # Match frontmatter block
    match = re.match(r"^(---\n)(.*?)(\n---\n)(.*)$", content, re.DOTALL)
    if not match:
        return content, False

    before = match.group(1)
    frontmatter = match.group(2)
    after_fm = match.group(3)
    body = match.group(4)

    # Fix double-quoted icons: icon: "value" -> icon: 'value'
    double_quote_pattern = r'^(icon:\s*)"([^"]+)"'
    if re.search(double_quote_pattern, frontmatter, re.MULTILINE):
        frontmatter = re.sub(
            double_quote_pattern,
            r"\1'\2'",
            frontmatter,
            flags=re.MULTILINE,
        )
        was_modified = True

    # Fix unquoted icons: icon: value -> icon: 'value'
    # But only if value doesn't start with a quote
    unquoted_pattern = r"^(icon:\s*)([a-z][a-z0-9-]*)\s*$"
    if re.search(unquoted_pattern, frontmatter, re.MULTILINE):
        frontmatter = re.sub(
            unquoted_pattern,
            r"\1'\2'",
            frontmatter,
            flags=re.MULTILINE,
        )
        was_modified = True

    return before + frontmatter + after_fm + body, was_modified


def add_icon_to_adr(content: str, suggested_icon: str) -> tuple[str, bool]:
    """
    Add icon to ADR frontmatter if missing.

    Returns:
        Tuple of (fixed_content, was_modified)
    """
    # Check if icon already exists
    if re.search(r"^icon:", content, re.MULTILINE):
        return content, False

    # Match frontmatter block
    match = re.match(r"^(---\n)(.*?)(\n---\n)(.*)$", content, re.DOTALL)
    if not match:
        return content, False

    before = match.group(1)
    frontmatter = match.group(2)
    after_fm = match.group(3)
    body = match.group(4)

    # Add icon after description line
    lines = frontmatter.split("\n")
    new_lines = []
    icon_added = False

    for line in lines:
        new_lines.append(line)
        # Add icon after description
        if line.startswith("description:") and not icon_added:
            new_lines.append(f"icon: '{suggested_icon}'")
            icon_added = True

    # If no description found, add icon at the end
    if not icon_added:
        new_lines.append(f"icon: '{suggested_icon}'")

    return before + "\n".join(new_lines) + after_fm + body, True


def standardize_file(file_path: Path, fix: bool = False, verbose: bool = False) -> tuple[bool, list[str]]:
    """
    Standardize frontmatter in a single file.

    Args:
        file_path: Path to the .mdx file
        fix: Whether to apply fixes (False = dry-run)
        verbose: Whether to print detailed changes

    Returns:
        Tuple of (was_modified, list of change descriptions)
    """
    changes = []

    try:
        content = file_path.read_text()
        was_modified = False

        # Fix icon quotes
        content, quote_fixed = fix_icon_quotes(content)
        if quote_fixed:
            changes.append("Fixed icon quote style")
            was_modified = True

        # Add icon to ADR files if missing
        is_adr = "architecture" in str(file_path) and file_path.name.startswith("adr-")
        if is_adr:
            suggested_icon = get_suggested_adr_icon(file_path)
            content, icon_added = add_icon_to_adr(content, suggested_icon)
            if icon_added:
                changes.append(f"Added icon: '{suggested_icon}'")
                was_modified = True

        # Write changes if fix mode and content changed
        if fix and was_modified:
            file_path.write_text(content)
            if verbose:
                print(f"  Fixed: {file_path}")
                for change in changes:
                    print(f"    - {change}")

        return was_modified, changes

    except Exception as e:
        return False, [f"Error: {e}"]


def standardize_docs(docs_dir: Path, fix: bool = False, verbose: bool = False) -> StandardizationResult:
    """
    Standardize all MDX files in docs directory.

    Args:
        docs_dir: Path to docs directory
        fix: Whether to apply fixes (False = dry-run)
        verbose: Whether to print detailed changes

    Returns:
        StandardizationResult with statistics
    """
    result = StandardizationResult()

    if not docs_dir.exists():
        result.errors.append(f"Docs directory not found: {docs_dir}")
        return result

    # Find all .mdx files
    mdx_files = list(docs_dir.rglob("*.mdx"))
    result.files_scanned = len(mdx_files)

    for mdx_file in mdx_files:
        was_modified, changes = standardize_file(mdx_file, fix=fix, verbose=verbose)

        if was_modified:
            result.files_modified += 1
            result.changes.append((mdx_file, "; ".join(changes)))

            # Count specific changes
            for change in changes:
                if "quote" in change.lower():
                    result.icons_fixed += 1
                elif "Added icon" in change:
                    result.icons_added += 1

    return result


def print_report(result: StandardizationResult, docs_dir: Path, fix: bool) -> None:
    """Print standardization report."""
    mode = "FIX" if fix else "DRY RUN"
    print(f"\n{'=' * 80}")
    print(f"📝 Frontmatter Standardization Report ({mode})")
    print("=" * 80)

    print("\n📊 Statistics:")
    print(f"  Files scanned: {result.files_scanned}")
    print(f"  Files {'modified' if fix else 'to modify'}: {result.files_modified}")
    print(f"  Icon quotes {'fixed' if fix else 'to fix'}: {result.icons_fixed}")
    print(f"  Icons {'added' if fix else 'to add'}: {result.icons_added}")

    if result.changes:
        print(f"\n{'✅ Changes applied' if fix else '⚠️  Changes needed'}:")
        for file_path, change in result.changes[:30]:
            relative = (
                file_path.relative_to(docs_dir) if docs_dir in file_path.parents or docs_dir == file_path.parent else file_path
            )
            print(f"    {'✅' if fix else '⚠️ '} {relative}: {change}")
        if len(result.changes) > 30:
            print(f"    ... and {len(result.changes) - 30} more")

    if result.errors:
        print("\n❌ Errors:")
        for error in result.errors:
            print(f"    ❌ {error}")

    print("\n" + "=" * 80)
    if fix:
        if result.files_modified > 0:
            print(f"✅ Successfully modified {result.files_modified} files")
        else:
            print("✅ No changes needed - all files are already standardized")
    else:
        if result.files_modified > 0:
            print(f"⚠️  {result.files_modified} files need standardization")
            print("💡 Run with --fix to apply changes")
        else:
            print("✅ All files are already standardized")
    print("=" * 80 + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Standardize frontmatter in Mintlify documentation files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Fixes Applied:
  - Icon quote style: "icon" -> 'icon', icon -> 'icon'
  - Missing ADR icons: Adds contextual icons based on ADR topic

Examples:
  %(prog)s                      # Dry-run - report issues
  %(prog)s --fix                # Apply fixes
  %(prog)s --fix --verbose      # Apply fixes with details
  %(prog)s --docs-dir docs/     # Specify docs directory
""",
    )

    parser.add_argument("--fix", action="store_true", help="Apply fixes (default: dry-run)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed changes")
    parser.add_argument("--docs-dir", type=Path, default=Path("docs"), help="Path to docs directory")

    args = parser.parse_args()

    print(f"\n🔍 Scanning {args.docs_dir}...")

    result = standardize_docs(args.docs_dir, fix=args.fix, verbose=args.verbose)
    print_report(result, args.docs_dir, args.fix)

    # Exit with error if issues found in dry-run mode
    if not args.fix and result.files_modified > 0:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
