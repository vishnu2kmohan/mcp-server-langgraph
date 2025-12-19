#!/usr/bin/env python3
"""
ADR Synchronization Validator.

Validates that Architecture Decision Records (ADRs) are properly synchronized:
1. README.md badge count matches actual ADR file count
2. All ADR .md files have corresponding .mdx files in docs/architecture/
3. No duplicate ADR numbers
4. Report gaps in ADR numbering (informational warning)

Usage:
    python scripts/validators/check_adr_sync.py [--repo-root PATH] [--fix]

Exit codes:
    0: All checks passed
    1: Validation failures found

Examples:
    # Check ADR synchronization
    python scripts/validators/check_adr_sync.py

    # Check with custom repo root
    python scripts/validators/check_adr_sync.py --repo-root /path/to/repo

    # Fix badge count automatically
    python scripts/validators/check_adr_sync.py --fix
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path


def count_adr_files(adr_dir: Path) -> int:
    """
    Count ADR files in adr/ directory.

    Args:
        adr_dir: Path to adr/ directory

    Returns:
        Number of adr-*.md files (excluding README.md)
    """
    if not adr_dir.exists():
        return 0

    adr_files = list(adr_dir.glob("adr-*.md"))
    return len(adr_files)


def get_badge_count(readme_path: Path) -> int | None:
    """
    Extract ADR count from README.md badge.

    Args:
        readme_path: Path to README.md

    Returns:
        Badge count if found, None otherwise
    """
    if not readme_path.exists():
        return None

    content = readme_path.read_text()
    match = re.search(r"ADRs-(\d+)-informational", content)
    if match:
        return int(match.group(1))
    return None


def update_badge_count(readme_path: Path, new_count: int) -> bool:
    """
    Update ADR badge count in README.md.

    Args:
        readme_path: Path to README.md
        new_count: New count to set

    Returns:
        True if updated successfully, False otherwise
    """
    if not readme_path.exists():
        return False

    content = readme_path.read_text()
    updated_content = re.sub(r"ADRs-(\d+)-informational", f"ADRs-{new_count}-informational", content)

    if content != updated_content:
        readme_path.write_text(updated_content)
        return True

    return False


def validate_adr_numbering(adr_dir: Path) -> tuple[list[int], set[int]]:
    """
    Validate ADR numbering for duplicates and gaps.

    Args:
        adr_dir: Path to adr/ directory

    Returns:
        Tuple of (duplicate_numbers, gap_numbers)
    """
    if not adr_dir.exists():
        return [], set()

    adr_numbers = []
    for adr_file in adr_dir.glob("adr-*.md"):
        match = re.match(r"adr-(\d+)-", adr_file.name)
        if match:
            adr_numbers.append(int(match.group(1)))

    # Find duplicates
    counts = Counter(adr_numbers)
    duplicates = [num for num, count in counts.items() if count > 1]

    # Find gaps
    gaps = set()
    if adr_numbers:
        min_num = min(adr_numbers)
        max_num = max(adr_numbers)
        expected_range = set(range(min_num, max_num + 1))
        actual_set = set(adr_numbers)
        gaps = expected_range - actual_set

    return duplicates, gaps


def validate_source_mdx_sync(adr_dir: Path, docs_dir: Path) -> tuple[set[str], set[str]]:
    """
    Validate synchronization between adr/ and docs/architecture/.

    Args:
        adr_dir: Path to adr/ directory
        docs_dir: Path to docs/architecture/ directory

    Returns:
        Tuple of (missing_in_docs, orphaned_in_docs)
    """
    if not adr_dir.exists():
        return set(), set()

    source_adrs = {f.stem for f in adr_dir.glob("adr-*.md")}

    docs_adrs = set()
    if docs_dir.exists():
        docs_adrs = {f.stem for f in docs_dir.glob("adr-*.mdx")}

    missing_in_docs = source_adrs - docs_adrs
    orphaned_in_docs = docs_adrs - source_adrs

    return missing_in_docs, orphaned_in_docs


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate ADR synchronization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      # Validate current repository
  %(prog)s --repo-root /path    # Validate specific repository
  %(prog)s --fix                # Fix badge count automatically

Exit codes:
  0: All checks passed
  1: Validation failures found
""",
    )

    parser.add_argument(
        "--repo-root", type=Path, default=Path.cwd(), help="Repository root directory (default: current directory)"
    )
    parser.add_argument("--fix", action="store_true", help="Automatically fix badge count in README.md")

    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    adr_dir = repo_root / "adr"
    docs_dir = repo_root / "docs" / "architecture"
    readme_path = repo_root / "README.md"

    # Track overall validation status
    all_checks_passed = True

    print("\n" + "=" * 80)
    print("📋 ADR Synchronization Validation")
    print("=" * 80)

    # Check 1: Badge count
    print("\n1️⃣  Badge Count Validation")
    print("-" * 80)

    actual_count = count_adr_files(adr_dir)
    badge_count = get_badge_count(readme_path)

    print(f"   ADR files in adr/: {actual_count}")
    if badge_count is not None:
        print(f"   Badge count in README.md: {badge_count}")

        if actual_count == badge_count:
            print("   ✅ Badge count matches actual ADR count")
        else:
            print(f"   ❌ Badge count mismatch! Expected {actual_count}, got {badge_count}")
            all_checks_passed = False

            if args.fix:
                if update_badge_count(readme_path, actual_count):
                    print(f"   🔧 Fixed: Updated badge count to {actual_count}")
                    all_checks_passed = True  # Fixed, so consider it passed
                else:
                    print("   ❌ Failed to update badge count")
    else:
        print("   ⚠️  No ADR badge found in README.md")
        all_checks_passed = False

    # Check 2: ADR numbering
    print("\n2️⃣  ADR Numbering Validation")
    print("-" * 80)

    duplicates, gaps = validate_adr_numbering(adr_dir)

    if duplicates:
        print(f"   ❌ Duplicate ADR numbers found: {sorted(duplicates)}")
        all_checks_passed = False
    else:
        print("   ✅ No duplicate ADR numbers")

    if gaps:
        print(f"   ⚠️  Gaps in ADR numbering (may be intentional): {sorted(gaps)}")
        # Gaps are informational only, don't fail validation
    else:
        print("   ✅ No gaps in ADR numbering")

    # Check 3: Source/MDX synchronization
    print("\n3️⃣  Source/MDX Synchronization")
    print("-" * 80)

    missing_in_docs, orphaned_in_docs = validate_source_mdx_sync(adr_dir, docs_dir)

    if missing_in_docs:
        print(f"   ❌ ADRs missing in docs/architecture/ ({len(missing_in_docs)}):")
        for adr in sorted(missing_in_docs):
            print(f"      • {adr}.md → {adr}.mdx")
        all_checks_passed = False
    else:
        print("   ✅ All source ADRs have corresponding .mdx files")

    if orphaned_in_docs:
        print(f"   ⚠️  Orphaned ADRs in docs/architecture/ ({len(orphaned_in_docs)}):")
        for adr in sorted(orphaned_in_docs):
            print(f"      • {adr}.mdx (no source .md file)")
        # Orphans are informational only, don't fail validation
    else:
        print("   ✅ No orphaned .mdx files in docs/architecture/")

    # Summary
    print("\n" + "=" * 80)
    if all_checks_passed:
        print("✅ All ADR synchronization checks passed!")
    else:
        print("❌ ADR synchronization validation failed")
        if not args.fix:
            print("\n💡 Tip: Run with --fix to automatically update badge count")
    print("=" * 80 + "\n")

    return 0 if all_checks_passed else 1


if __name__ == "__main__":
    sys.exit(main())
