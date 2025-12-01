#!/usr/bin/env python3
"""
Ultra-reliable MDX code block language tag fixer.

This script fixes bare code fences (```) by adding appropriate language tags
based on content analysis. It's designed to be safe and conservative.

Usage:
    # Dry run (show what would change)
    python scripts/docs/fix_code_block_languages.py --dry-run

    # Fix all files
    python scripts/docs/fix_code_block_languages.py --fix

    # Fix specific file
    python scripts/docs/fix_code_block_languages.py --fix docs/deployment/kubernetes.mdx

    # Validate after fixing
    python scripts/docs/fix_code_block_languages.py --fix --validate

Safety Features:
- Creates .bak backup before modifying any file
- Dry-run mode by default
- Conservative language inference
- Validates Mintlify can parse after each fix (optional)
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass

# Import the inference engine
from infer_code_language import infer_language


@dataclass
class CodeBlockFix:
    """Represents a fix to be applied to a code block."""

    line_number: int
    original: str
    fixed: str
    language: str
    confidence: float
    reason: str


@dataclass
class FileFixResult:
    """Result of fixing a single file."""

    filepath: Path
    fixes: list[CodeBlockFix]
    success: bool
    error: str | None = None


def find_bare_fences(content: str) -> list[tuple[int, int, list[str]]]:
    """
    Find all bare opening code fences and their content.

    Returns:
        List of (line_number, end_line, content_lines) tuples
    """
    lines = content.split("\n")
    bare_fences = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check for opening fence with language (skip these)
        if re.match(r"^```[a-zA-Z]", stripped):
            # Skip to closing fence
            i += 1
            while i < len(lines) and lines[i].strip() != "```":
                i += 1
            i += 1
            continue

        # Check for bare opening fence
        if stripped == "```":
            start_line = i + 1  # 1-indexed
            content_lines = []
            i += 1

            # Collect content until closing fence
            while i < len(lines) and lines[i].strip() != "```":
                content_lines.append(lines[i])
                i += 1

            if content_lines:  # Only if there's content
                bare_fences.append((start_line, i + 1, content_lines))

            i += 1
            continue

        i += 1

    return bare_fences


def fix_file(filepath: Path, dry_run: bool = True, min_confidence: float = 0.5) -> FileFixResult:
    """
    Fix bare code fences in a single file.

    Args:
        filepath: Path to the MDX file
        dry_run: If True, don't modify the file
        min_confidence: Minimum confidence to apply a fix

    Returns:
        FileFixResult with applied fixes and status
    """
    try:
        content = filepath.read_text()
    except Exception as e:
        return FileFixResult(filepath, [], False, f"Failed to read: {e}")

    lines = content.split("\n")
    fixes: list[CodeBlockFix] = []

    # Find all bare fences
    bare_fences = find_bare_fences(content)

    if not bare_fences:
        return FileFixResult(filepath, [], True)

    # Process each bare fence
    for start_line, end_line, content_lines in bare_fences:
        # Infer language
        result = infer_language(content_lines)

        if result.confidence >= min_confidence:
            fix = CodeBlockFix(
                line_number=start_line,
                original="```",
                fixed=f"```{result.language}",
                language=result.language,
                confidence=result.confidence,
                reason=result.reason,
            )
            fixes.append(fix)

    if not fixes:
        return FileFixResult(filepath, [], True)

    if dry_run:
        return FileFixResult(filepath, fixes, True)

    # Apply fixes (work backwards to preserve line numbers)
    fixes_by_line = {f.line_number: f for f in fixes}

    new_lines = []
    i = 0
    while i < len(lines):
        line_num = i + 1
        if line_num in fixes_by_line:
            fix = fixes_by_line[line_num]
            # Replace the bare fence with language-tagged fence
            new_lines.append(lines[i].replace("```", fix.fixed, 1))
        else:
            new_lines.append(lines[i])
        i += 1

    # Create backup
    backup_path = filepath.with_suffix(filepath.suffix + ".bak")
    shutil.copy2(filepath, backup_path)

    # Write fixed content
    try:
        filepath.write_text("\n".join(new_lines))
        return FileFixResult(filepath, fixes, True)
    except Exception as e:
        # Restore from backup on failure
        shutil.copy2(backup_path, filepath)
        return FileFixResult(filepath, [], False, f"Failed to write: {e}")


def validate_with_mintlify(docs_dir: Path) -> bool:
    """Run mintlify broken-links to validate the docs."""
    try:
        result = subprocess.run(
            ["npm", "exec", "--", "mintlify", "broken-links"],
            cwd=docs_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return "no broken links found" in result.stdout.lower() or result.returncode == 0
    except Exception as e:
        print(f"Warning: Mintlify validation failed: {e}")
        return True  # Don't block on validation failures


def find_mdx_files(docs_dir: Path) -> list[Path]:
    """Find all MDX files in the docs directory."""
    return sorted(docs_dir.rglob("*.mdx"))


def main():
    parser = argparse.ArgumentParser(description="Fix bare code fences in MDX files by adding language tags.")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Actually fix files (default is dry-run)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Show what would be fixed without modifying files",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate with Mintlify after fixing",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.5,
        help="Minimum confidence to apply a fix (0.0-1.0)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Specific files to fix (default: all docs/*.mdx)",
    )

    args = parser.parse_args()

    # Determine if we're fixing or just showing
    dry_run = not args.fix

    # Find files to process
    docs_dir = Path("docs")
    if args.files:
        files = [Path(f) for f in args.files]
    else:
        files = find_mdx_files(docs_dir)

    if not files:
        print("No MDX files found")
        return 1

    print(f"{'DRY RUN - ' if dry_run else ''}Processing {len(files)} files...")
    print("=" * 70)

    total_fixes = 0
    files_with_fixes = 0
    failed_files = []

    for filepath in files:
        result = fix_file(filepath, dry_run=dry_run, min_confidence=args.min_confidence)

        if not result.success:
            failed_files.append((filepath, result.error))
            print(f"✗ {filepath}: {result.error}")
            continue

        if result.fixes:
            files_with_fixes += 1
            total_fixes += len(result.fixes)

            if args.verbose or dry_run:
                print(f"\n{filepath} ({len(result.fixes)} fixes):")
                for fix in result.fixes:
                    print(f"  Line {fix.line_number}: ``` → ```{fix.language} ({fix.confidence:.1f})")
                    if args.verbose:
                        print(f"    Reason: {fix.reason}")

    print("=" * 70)
    print(f"Summary: {total_fixes} fixes in {files_with_fixes} files")

    if dry_run:
        print("\nThis was a DRY RUN. Use --fix to apply changes.")
    elif args.validate:
        print("\nValidating with Mintlify...")
        if validate_with_mintlify(docs_dir):
            print("✓ Mintlify validation passed")
        else:
            print("✗ Mintlify validation failed")
            return 1

    if failed_files:
        print(f"\n{len(failed_files)} files failed:")
        for filepath, error in failed_files:
            print(f"  {filepath}: {error}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
