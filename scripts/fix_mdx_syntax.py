#!/usr/bin/env python3
"""
Fix common MDX syntax errors in documentation files.

This script fixes the specific pattern where code blocks are closed with
```LANG instead of just ```, which breaks MDX parsing.

Usage:
    python3 scripts/fix-mdx-syntax.py [--file FILE | --all]
"""

import argparse
import re
from pathlib import Path


def fix_code_block_closings(content: str) -> tuple[str, int]:
    """
    Fix code blocks that are closed with ```LANG instead of ```.

    Args:
        content: The file content to fix

    Returns:
        Tuple of (fixed_content, number_of_fixes)
    """
    lines = content.split("\n")
    fixed_lines = []
    skip_next = False
    fixes = 0

    for i in range(len(lines)):
        if skip_next:
            skip_next = False
            # Add a blank line instead of the malformed ```LANG
            fixed_lines.append("")
            fixes += 1
            continue

        line = lines[i]

        # Pattern 1: ``` followed by ```LANG on next line (standalone, not ```LANG Title)
        if (
            i + 1 < len(lines)
            and line.strip() == "```"
            and re.match(
                r"^```(bash|python|javascript|json|yaml|text|ini|hcl|sql|markdown|typescript|xml|html|dockerfile)$",
                lines[i + 1].strip(),
            )
        ):
            fixed_lines.append(line)
            skip_next = True
            continue

        # Pattern 2: ```LANG right before </CodeGroup>
        if (
            i + 1 < len(lines)
            and re.match(r"^```(bash|python|javascript|json|yaml|text)$", line.strip())
            and lines[i + 1].strip() == "</CodeGroup>"
        ):
            # Replace with just ```
            fixed_lines.append("```")
            fixes += 1
            continue

        # Pattern 3: ```LANG right before MDX tags (<Note>, <Warning>, <ResponseField>, etc.)
        if (
            i + 1 < len(lines)
            and re.match(r"^```(bash|python|javascript|json|yaml|text|ini|hcl)$", line.strip())
            and re.match(
                r"^<(Note|Warning|Tip|Info|Card|Accordion|ResponseField|ParamField|Check|Error)", lines[i + 1].strip()
            )
        ):
            # Replace with just ```
            fixed_lines.append("```")
            fixes += 1
            continue

        # Pattern 4: ```LANG right before markdown text (##, **, -, etc.)
        if (
            i + 1 < len(lines)
            and re.match(r"^```(bash|python|javascript|json|yaml|text|ini|hcl|mermaid)$", line.strip())
            and lines[i + 1].strip()
            and re.match(r"^(\*\*|##|###|####|-|\d+\.|\||>)", lines[i + 1].strip())
        ):
            # Replace with just ```
            fixed_lines.append("```")
            fixes += 1
            continue

        fixed_lines.append(line)

    return "\n".join(fixed_lines), fixes


def fix_file(file_path: Path, dry_run: bool = False) -> tuple[int, list[str]]:
    """
    Fix MDX syntax errors in a file.

    Args:
        file_path: Path to the MDX file
        dry_run: If True, don't write changes

    Returns:
        Tuple of (number_of_fixes, list_of_changes)
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            original_content = f.read()

        fixed_content, fixes = fix_code_block_closings(original_content)

        changes = []
        if fixes > 0:
            changes.append(f"Fixed {fixes} malformed code block closing(s)")

            if not dry_run:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(fixed_content)

        return fixes, changes

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0, []


def main():
    parser = argparse.ArgumentParser(description="Fix MDX syntax errors")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=str, help="Fix a single file")
    group.add_argument("--all", action="store_true", help="Fix all MDX files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed")
    args = parser.parse_args()

    if args.file:
        files = [Path(args.file).resolve()]
    else:
        docs_dir = Path("docs").resolve()
        files = list(docs_dir.rglob("*.mdx"))
        # Exclude templates
        files = [f for f in files if ".mintlify/templates" not in str(f)]

    total_files = 0
    total_fixes = 0

    print(f"{'DRY RUN - ' if args.dry_run else ''}Fixing MDX syntax in {len(files)} files...\n")

    for file_path in sorted(files):
        fixes, changes = fix_file(file_path, dry_run=args.dry_run)

        if fixes > 0:
            total_files += 1
            total_fixes += fixes
            relative_path = file_path.relative_to(Path.cwd())
            print(f"✓ {relative_path}: {fixes} fix(es)")

            for change in changes:
                print(f"  {change}")

    print(f"\n{'Would fix' if args.dry_run else 'Fixed'} {total_fixes} issues in {total_files} files")

    if args.dry_run:
        print("\nRun without --dry-run to apply changes")

    return 0 if total_fixes == 0 else 1


if __name__ == "__main__":
    exit(main())
