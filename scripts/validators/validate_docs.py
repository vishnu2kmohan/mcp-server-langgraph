#!/usr/bin/env python3
"""
Consolidated Documentation Validator for Pre-commit Hooks.

This script consolidates 6 documentation validation hooks into a single tool:
1. MDX extension validation (docs/ must use .mdx, not .md)
2. File naming conventions (kebab-case)
3. Frontmatter quote standardization
4. ADR synchronization (adr/ <-> docs/architecture/)
5. Documentation integrity tests
6. Documentation structure tests

Usage:
    python scripts/validators/validate_docs.py --all
    python scripts/validators/validate_docs.py --mdx --docs-dir docs/
    python scripts/validators/validate_docs.py --adr --repo-root .
    python scripts/validators/validate_docs.py --tests --dry-run

Exit codes:
    0: All validations passed
    1: Validation failures found
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


# =============================================================================
# MDX Extension Validation
# =============================================================================


@dataclass
class MDXValidationResult:
    """Result of MDX extension and naming validation."""

    is_valid: bool = True
    md_files: list[Path] = field(default_factory=list)
    invalid_names: list[tuple[Path, str]] = field(default_factory=list)
    frontmatter_issues: list[tuple[Path, str]] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)


# Conventional files allowed to have UPPERCASE names
CONVENTIONAL_FILES = {
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "LICENSE.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "TESTING.md",
    "ROADMAP.md",
    "MIGRATION.md",
}

# Patterns to exclude from validation
EXCLUDE_PATTERNS = [
    ".mintlify/",
    "node_modules/",
    ".git/",
    "__pycache__/",
    ".pytest_cache/",
    "venv/",
    ".venv/",
]


def is_kebab_case(filename: str) -> bool:
    """Check if filename follows kebab-case convention."""
    stem = Path(filename).stem

    if not stem:
        return False

    # Hidden files are allowed
    if stem.startswith("."):
        return True

    # No leading or trailing hyphens
    if stem.startswith("-") or stem.endswith("-"):
        return False

    # Kebab-case: lowercase letters, numbers, and hyphens
    pattern = r"^[a-z0-9]+(-[a-z0-9]+)*$"
    return bool(re.match(pattern, stem))


def to_kebab_case(filename: str) -> str:
    """Convert filename to kebab-case suggestion."""
    stem = Path(filename).stem
    extension = Path(filename).suffix

    suggested = stem.replace("_", "-").lower()
    suggested = re.sub(r"-+", "-", suggested).strip("-")

    return f"{suggested}{extension}"


def parse_frontmatter(content: str) -> tuple[dict | None, str, str]:
    """Parse YAML frontmatter from .mdx content."""
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
    if not match:
        return None, "", content

    frontmatter_text = match.group(1)
    body_text = match.group(2)

    frontmatter = {}
    for line in frontmatter_text.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()

    return frontmatter, frontmatter_text, body_text


def validate_mdx_files(docs_dir: Path, quiet: bool = False) -> MDXValidationResult:
    """
    Validate MDX files in docs directory.

    Checks:
    1. All files use .mdx extension (not .md)
    2. Filenames follow kebab-case convention
    3. Frontmatter uses consistent quote style
    """
    result = MDXValidationResult()
    result.stats = {"total_files": 0, "md_files": 0, "invalid_names": 0, "frontmatter_issues": 0}

    if not docs_dir.exists():
        return result

    # Find all .mdx and .md files
    mdx_files = list(docs_dir.rglob("*.mdx"))
    md_files = list(docs_dir.rglob("*.md"))

    # Filter out excluded patterns
    def should_include(file_path: Path) -> bool:
        relative_path = str(file_path.relative_to(docs_dir))
        return not any(pattern in relative_path for pattern in EXCLUDE_PATTERNS)

    mdx_files = [f for f in mdx_files if should_include(f)]
    md_files = [f for f in md_files if should_include(f)]

    result.stats["total_files"] = len(mdx_files) + len(md_files)

    # Check for .md files (invalid in docs/)
    for md_file in md_files:
        result.md_files.append(md_file)
        result.stats["md_files"] += 1
        result.is_valid = False

    # Check MDX files
    for mdx_file in mdx_files:
        filename = mdx_file.name

        # Check naming convention
        if not is_kebab_case(filename):
            suggested = to_kebab_case(filename)
            result.invalid_names.append((mdx_file, suggested))
            result.stats["invalid_names"] += 1
            result.is_valid = False

        # Check frontmatter (optional, just warnings in dry-run mode)
        try:
            content = mdx_file.read_text()
            frontmatter, fm_text, _ = parse_frontmatter(content)

            if frontmatter:
                # Check for inconsistent quoting
                for line in fm_text.split("\n"):
                    if ":" not in line:
                        continue
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()

                    # description and icon should use single quotes
                    if key in ("description", "icon") and value.startswith('"'):
                        result.frontmatter_issues.append((mdx_file, f"{key} uses double quotes (should use single quotes)"))
                        result.stats["frontmatter_issues"] += 1
        except Exception:
            pass

    return result


def print_mdx_report(result: MDXValidationResult, docs_dir: Path) -> None:
    """Print MDX validation report."""
    print("\n" + "=" * 80)
    print("📝 MDX Extension & Naming Validation Report")
    print("=" * 80)

    print("\n📊 Statistics:")
    print(f"  Total files scanned: {result.stats.get('total_files', 0)}")
    print(f"  Invalid .md files: {result.stats.get('md_files', 0)}")
    print(f"  Invalid filenames: {result.stats.get('invalid_names', 0)}")
    print(f"  Frontmatter issues: {result.stats.get('frontmatter_issues', 0)}")

    if result.md_files:
        print("\n❌ .md files found in docs/ (should be .mdx):")
        for md_file in result.md_files:
            print(f"    ❌ {md_file.relative_to(docs_dir)}")
        print("  💡 Solution: Convert .md files to .mdx")

    if result.invalid_names:
        print("\n❌ Invalid filenames (should be kebab-case):")
        for file_path, suggested in result.invalid_names:
            print(f"    ❌ {file_path.relative_to(docs_dir)} → {suggested}")

    if result.frontmatter_issues:
        print("\n⚠️  Frontmatter issues (warnings):")
        for file_path, issue in result.frontmatter_issues[:10]:
            print(f"    ⚠️  {file_path.relative_to(docs_dir)}: {issue}")
        if len(result.frontmatter_issues) > 10:
            print(f"    ... and {len(result.frontmatter_issues) - 10} more")

    print("\n" + "=" * 80)
    if result.is_valid:
        print("✅ All MDX files are valid!")
    else:
        print("❌ MDX validation failed")
    print("=" * 80 + "\n")


# =============================================================================
# ADR Synchronization Validation
# =============================================================================


@dataclass
class ADRValidationResult:
    """Result of ADR synchronization validation."""

    is_synced: bool = True
    source_adrs: set[str] = field(default_factory=set)
    docs_adrs: set[str] = field(default_factory=set)
    missing_in_docs: set[str] = field(default_factory=set)
    missing_in_source: set[str] = field(default_factory=set)
    uppercase_filenames: list[Path] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)


def validate_adr_sync(repo_root: Path, quiet: bool = False) -> ADRValidationResult:
    """
    Validate ADR synchronization between /adr and /docs/architecture.

    Checks:
    1. All ADRs in /adr have corresponding .mdx in /docs/architecture
    2. No orphaned ADRs in /docs/architecture
    3. No uppercase ADR-* filenames (should be adr-*)
    """
    result = ADRValidationResult()

    adr_dir = repo_root / "adr"
    docs_adr_dir = repo_root / "docs" / "architecture"

    # Find source ADRs (.md files)
    if adr_dir.exists():
        for adr_file in adr_dir.glob("adr-*.md"):
            result.source_adrs.add(adr_file.stem)

        # Check for uppercase ADR-* files
        for adr_file in adr_dir.glob("ADR-*.md"):
            result.uppercase_filenames.append(adr_file)

    # Find docs ADRs (.mdx files)
    if docs_adr_dir.exists():
        for adr_file in docs_adr_dir.glob("adr-*.mdx"):
            result.docs_adrs.add(adr_file.stem)

        # Check for uppercase ADR-* files
        for adr_file in docs_adr_dir.glob("ADR-*.mdx"):
            result.uppercase_filenames.append(adr_file)

    # Compare
    result.missing_in_docs = result.source_adrs - result.docs_adrs
    result.missing_in_source = result.docs_adrs - result.source_adrs

    result.is_synced = (
        len(result.missing_in_docs) == 0 and len(result.missing_in_source) == 0 and len(result.uppercase_filenames) == 0
    )

    result.stats = {
        "source_count": len(result.source_adrs),
        "docs_count": len(result.docs_adrs),
        "missing_in_docs": len(result.missing_in_docs),
        "missing_in_source": len(result.missing_in_source),
        "uppercase_count": len(result.uppercase_filenames),
    }

    return result


def print_adr_report(result: ADRValidationResult, repo_root: Path) -> None:
    """Print ADR synchronization report."""
    print("\n" + "=" * 80)
    print("🔄 ADR Synchronization Validation Report")
    print("=" * 80)

    print("\n📊 Statistics:")
    print(f"  ADRs in /adr: {result.stats['source_count']}")
    print(f"  ADRs in /docs/architecture: {result.stats['docs_count']}")

    if result.uppercase_filenames:
        print(f"\n⚠️  Uppercase filenames detected ({len(result.uppercase_filenames)}):")
        for f in sorted(result.uppercase_filenames):
            lowercase_name = f.name.replace("ADR-", "adr-")
            print(f"    • {f.relative_to(repo_root)} → {lowercase_name}")

    if result.missing_in_docs:
        print(f"\n❌ ADRs missing in /docs/architecture ({len(result.missing_in_docs)}):")
        for adr in sorted(result.missing_in_docs):
            print(f"    • {adr}.md → {adr}.mdx")

    if result.missing_in_source:
        print("\n⚠️  ADRs missing in /adr (orphaned in docs):")
        for adr in sorted(result.missing_in_source):
            print(f"    • {adr}.mdx")

    print("\n" + "=" * 80)
    if result.is_synced:
        print("✅ All ADRs are synchronized!")
    else:
        print("❌ ADRs are out of sync")
    print("=" * 80 + "\n")


# =============================================================================
# Documentation Tests Validation
# =============================================================================


def run_doc_tests(repo_root: Path, dry_run: bool = False) -> int:
    """
    Run documentation validation pytest tests.

    Tests:
    - tests/meta/validation/test_documentation_integrity.py
    - tests/regression/test_documentation_structure.py
    - tests/meta/validation/test_mdx_validation.py
    """
    test_files = [
        "tests/meta/validation/test_documentation_integrity.py",
        "tests/regression/test_documentation_structure.py",
        "tests/meta/validation/test_mdx_validation.py",
    ]

    existing_tests = [repo_root / t for t in test_files if (repo_root / t).exists()]

    if dry_run:
        print("\n" + "=" * 80)
        print("🧪 Documentation Tests (DRY RUN)")
        print("=" * 80)
        print("\nWould run pytest on:")
        for test_file in existing_tests:
            print(f"  • {test_file.relative_to(repo_root)}")
        print("=" * 80 + "\n")
        return 0

    if not existing_tests:
        print("⚠️  No documentation test files found")
        return 0

    print("\n" + "=" * 80)
    print("🧪 Running Documentation Tests")
    print("=" * 80 + "\n")

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "--tb=short",
    ] + [str(t) for t in existing_tests]

    result = subprocess.run(cmd, cwd=repo_root)
    return result.returncode


# =============================================================================
# Main Entry Point
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consolidated documentation validator for pre-commit hooks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Validation Types:
  --mdx       Validate MDX extension, file naming, frontmatter
  --adr       Validate ADR synchronization (adr/ <-> docs/architecture/)
  --tests     Run documentation validation pytest tests
  --all       Run all validations

Examples:
  %(prog)s --all                           # Run all validations
  %(prog)s --mdx --docs-dir docs/          # Validate MDX files only
  %(prog)s --adr --repo-root .             # Validate ADR sync only
  %(prog)s --tests --dry-run               # Show what tests would run
""",
    )

    parser.add_argument("--mdx", action="store_true", help="Validate MDX files (extension, naming, frontmatter)")
    parser.add_argument("--adr", action="store_true", help="Validate ADR synchronization")
    parser.add_argument("--tests", action="store_true", help="Run documentation validation tests")
    parser.add_argument("--all", action="store_true", help="Run all validations")
    parser.add_argument("--docs-dir", type=Path, default=Path("docs"), help="Path to docs directory")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Path to repository root")
    parser.add_argument("--quiet", action="store_true", help="Suppress output (only use exit code)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be validated without running")

    args = parser.parse_args()

    # Default to --all if no specific validation type specified
    if not any([args.mdx, args.adr, args.tests, args.all]):
        args.all = True

    exit_code = 0

    # MDX validation
    if args.mdx or args.all:
        if args.dry_run:
            print(f"[DRY RUN] Would validate MDX files in {args.docs_dir}")
        else:
            result = validate_mdx_files(args.docs_dir, args.quiet)
            if not args.quiet:
                print_mdx_report(result, args.docs_dir)
            if not result.is_valid:
                exit_code = 1

    # ADR validation
    if args.adr or args.all:
        if args.dry_run:
            print(f"[DRY RUN] Would validate ADR sync in {args.repo_root}")
        else:
            result = validate_adr_sync(args.repo_root, args.quiet)
            if not args.quiet:
                print_adr_report(result, args.repo_root)
            if not result.is_synced:
                exit_code = 1

    # Tests validation
    if args.tests or args.all:
        test_exit = run_doc_tests(args.repo_root, args.dry_run)
        if test_exit != 0:
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
