#!/usr/bin/env python3
"""
Update all script path references to new consolidated locations.

After scripts were reorganized into subdirectories (validators/, dev/, ci/, etc.),
many documentation files and workflows still reference old paths.

This script updates all references to match new locations.

Usage:
    python scripts/dev/update_script_path_references.py
    python scripts/dev/update_script_path_references.py --dry-run
"""

import argparse
from pathlib import Path

# Mapping of old paths to new paths
SCRIPT_MOVES = {
    "scripts/measure_hook_performance.py": "scripts/dev/measure_hook_performance.py",
    "scripts/generate_openapi.py": "scripts/dev/generate_openapi.py",
    "scripts/check_version_consistency.py": "scripts/validators/check_version_consistency.py",
    "scripts/validate_pre_push_hook.py": "scripts/validators/validate_pre_push_hook.py",
}

# Files to update (discovered from grep audit)
FILES_TO_UPDATE = [
    # measure_hook_performance.py references
    ".claude/memory/pre-commit-hooks-catalog.md",
    ".github/CLAUDE.md",
    ".github/CONTRIBUTING.md",
    "CONTRIBUTING.md",
    "docs-internal/CODEX_FINDINGS_REMEDIATION_SUMMARY.md",
    "docs-internal/HOOKS_COMPLETE_AUDIT_SUMMARY.md",
    # generate_openapi.py references
    ".github/copilot-instructions.md",
    # check_version_consistency.py references (CRITICAL: includes CI workflow)
    ".github/workflows/docs-validation.yaml",
    "docs-internal/VALIDATION_IMPLEMENTATION_SUMMARY.md",
    "docs-internal/VALIDATION_INFRASTRUCTURE.md",
]


def update_file(file_path: Path, dry_run: bool = False) -> int:
    """
    Update script path references in a single file.

    Args:
        file_path: Path to file to update
        dry_run: If True, don't write changes

    Returns:
        Number of replacements made
    """
    if not file_path.exists():
        print(f"⚠️  Skipping {file_path} (does not exist)")
        return 0

    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    total_replacements = 0

    # Apply all path replacements
    for old_path, new_path in SCRIPT_MOVES.items():
        # Count replacements
        count = content.count(old_path)
        if count > 0:
            content = content.replace(old_path, new_path)
            total_replacements += count
            print(f"  ✓ Replaced {count}x: {old_path} → {new_path}")

    if total_replacements > 0:
        if not dry_run:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ Updated {file_path} ({total_replacements} replacements)")
        else:
            print(f"🔍 Would update {file_path} ({total_replacements} replacements)")

    return total_replacements


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Update script path references")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent.parent
    total = 0

    print("=== Script Path Reference Update ===\n")
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified\n")

    for file_path_str in FILES_TO_UPDATE:
        file_path = repo_root / file_path_str
        replacements = update_file(file_path, dry_run=args.dry_run)
        total += replacements

    print(
        f"\n{'Would update' if args.dry_run else 'Updated'} {len([f for f in FILES_TO_UPDATE if (repo_root / f).exists()])} files with {total} total replacements"
    )

    if total > 0 and not args.dry_run:
        print("\n✓ Script path references updated successfully!")
        print("  Run 'git diff' to review changes")
        print("  Run 'git add -A && git commit' to commit changes")
    elif total == 0:
        print("\n✓ No script path references need updating")


if __name__ == "__main__":
    main()
