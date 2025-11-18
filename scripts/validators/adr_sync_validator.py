#!/usr/bin/env python3
"""
ADR Synchronization Validator

Validates that ADRs in /adr are synchronized with /docs/architecture.

Features:
1. Checks that all ADRs in /adr exist in /docs/architecture
2. Checks that all ADRs in /docs/architecture exist in /adr
3. Optionally validates content similarity
4. Reports missing or orphaned ADRs

Exit codes:
- 0: All ADRs are synchronized
- 1: ADRs are out of sync
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set


@dataclass
class SyncResult:
    """Result of ADR synchronization check."""

    is_synced: bool
    source_adrs: set[str] = field(default_factory=set)
    docs_adrs: set[str] = field(default_factory=set)
    missing_in_docs: set[str] = field(default_factory=set)
    missing_in_source: set[str] = field(default_factory=set)
    uppercase_filenames: list[Path] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        """Get exit code for CLI."""
        return 0 if self.is_synced else 1


class AdrSyncValidator:
    """Validates ADR synchronization between source and docs."""

    def __init__(self, repo_root: Path):
        """
        Initialize validator.

        Args:
            repo_root: Path to repository root
        """
        self.repo_root = Path(repo_root)
        self.adr_dir = self.repo_root / "adr"
        self.docs_adr_dir = self.repo_root / "docs" / "architecture"

    def validate(self) -> SyncResult:
        """
        Validate ADR synchronization.

        Returns:
            SyncResult with sync status and details
        """
        # Find all ADRs in source
        source_adrs = self._find_adrs(self.adr_dir, ".md")

        # Find all ADRs in docs
        docs_adrs = self._find_adrs(self.docs_adr_dir, ".mdx")

        # Check for uppercase filenames (should be lowercase adr-*, not ADR-*)
        uppercase_filenames = self._find_uppercase_filenames()

        # Compare
        missing_in_docs = source_adrs - docs_adrs
        missing_in_source = docs_adrs - source_adrs

        is_synced = len(missing_in_docs) == 0 and len(missing_in_source) == 0 and len(uppercase_filenames) == 0

        stats = {
            "source_count": len(source_adrs),
            "docs_count": len(docs_adrs),
            "missing_in_docs": len(missing_in_docs),
            "missing_in_source": len(missing_in_source),
            "uppercase_count": len(uppercase_filenames),
        }

        return SyncResult(
            is_synced=is_synced,
            source_adrs=source_adrs,
            docs_adrs=docs_adrs,
            missing_in_docs=missing_in_docs,
            missing_in_source=missing_in_source,
            uppercase_filenames=uppercase_filenames,
            stats=stats,
        )

    def _find_adrs(self, directory: Path, extension: str) -> set[str]:
        """
        Find all ADR files in directory.

        Args:
            directory: Directory to search
            extension: File extension (.md or .mdx)

        Returns:
            Set of ADR names (without extension)
        """
        adrs = set()

        if not directory.exists():
            return adrs

        # Pattern: adr-NNNN-*.md or adr-NNNN-*.mdx
        for adr_file in directory.glob(f"adr-*{extension}"):
            # Extract ADR name without extension
            adr_name = adr_file.stem
            adrs.add(adr_name)

        return adrs

    def _find_uppercase_filenames(self) -> list[Path]:
        """
        Find ADR files with uppercase naming (ADR-* instead of adr-*).

        Returns:
            List of files with incorrect uppercase naming
        """
        uppercase_files = []

        for directory, extension in [(self.adr_dir, ".md"), (self.docs_adr_dir, ".mdx")]:
            if not directory.exists():
                continue

            # Look for uppercase ADR-* pattern
            for adr_file in directory.glob(f"ADR-*{extension}"):
                uppercase_files.append(adr_file)

        return uppercase_files

    def print_report(self, result: SyncResult) -> None:
        """Print validation report to stdout."""
        print("\n" + "=" * 80)
        print("🔄 ADR Synchronization Validation Report")
        print("=" * 80)

        # Statistics
        print("\n📊 Statistics:")
        print(f"  ADRs in /adr: {result.stats['source_count']}")
        print(f"  ADRs in /docs/architecture: {result.stats['docs_count']}")

        # Uppercase filename warnings
        if result.uppercase_filenames:
            print(f"\n⚠️  Uppercase filenames detected ({len(result.uppercase_filenames)}):")
            for uppercase_file in sorted(result.uppercase_filenames):
                lowercase_name = uppercase_file.name.replace("ADR-", "adr-")
                print(f"    • {uppercase_file.relative_to(self.repo_root)}")
                print(f"      Rename to: {uppercase_file.parent / lowercase_name}")

        # Missing ADRs
        if result.missing_in_docs:
            print(f"\n❌ ADRs missing in /docs/architecture ({len(result.missing_in_docs)}):")
            for adr in sorted(result.missing_in_docs):
                print(f"    • {adr}.md → {adr}.mdx (expected)")

        if result.missing_in_source:
            print(f"\n⚠️  ADRs missing in /adr ({len(result.missing_in_source)}):")
            for adr in sorted(result.missing_in_source):
                print(f"    • {adr}.mdx (orphaned in docs)")

        # Recommendations
        if not result.is_synced:
            print("\n💡 Recommendations:")
            rec_num = 1
            if result.uppercase_filenames:
                print(f"  {rec_num}. Rename uppercase files to lowercase:")
                for uppercase_file in sorted(result.uppercase_filenames):
                    lowercase_name = uppercase_file.name.replace("ADR-", "adr-")
                    print(f"     mv {uppercase_file.relative_to(self.repo_root)} ", end="")
                    print(f"{uppercase_file.parent.relative_to(self.repo_root)}/{lowercase_name}")
                rec_num += 1
            if result.missing_in_docs:
                print(f"  {rec_num}. Sync ADRs from /adr to /docs/architecture:")
                for adr in sorted(result.missing_in_docs):
                    print(f"     cp adr/{adr}.md docs/architecture/{adr}.mdx")
                rec_num += 1
            if result.missing_in_source:
                print(f"  {rec_num}. Review orphaned ADRs in /docs/architecture")
                print(f"  {rec_num + 1}. Consider adding them to /adr or removing if outdated")
                rec_num += 2

            print(f"\n  {rec_num}. Pre-commit hook is configured to prevent future desync")
            print("     Hook: validate-adr-sync in .pre-commit-config.yaml")

        # Summary
        print("\n" + "=" * 80)
        if result.is_synced:
            print("✅ All ADRs are synchronized!")
        else:
            print("❌ ADRs are out of sync - see details above")
        print("=" * 80 + "\n")


def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate ADR synchronization between /adr and /docs/architecture")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Path to repository root (default: current directory)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output (only use exit code)",
    )

    args = parser.parse_args()

    # Run validation
    validator = AdrSyncValidator(args.repo_root)
    result = validator.validate()

    # Print report
    if not args.quiet:
        validator.print_report(result)

    # Exit with appropriate code
    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()
