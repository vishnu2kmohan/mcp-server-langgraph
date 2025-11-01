#!/usr/bin/env python3
"""
Fix mismatched code fence closures in MDX files.

Code fences should open with ```lang and close with just ```.
This script finds and fixes cases where closing fences incorrectly have language identifiers.
"""

import glob
import re
import sys


def fix_code_fences(filepath):
    """Fix code fence closures in a single file."""
    with open(filepath, "r") as f:
        lines = f.readlines()

    modified = False
    in_code_block = False
    code_block_lang = None
    fixed_lines = []

    for i, line in enumerate(lines, 1):
        # Check for code fence opening
        match_open = re.match(r"^(\s*)```(\w+)", line)
        if match_open and not in_code_block:
            in_code_block = True
            code_block_lang = match_open.group(2)
            fixed_lines.append(line)
            continue

        # Check for code fence closing
        match_close = re.match(r"^(\s*)```(\w+)?(\s*)$", line)
        if match_close and in_code_block:
            closing_lang = match_close.group(2)
            if closing_lang and closing_lang != code_block_lang:
                # Fix: remove the language identifier from closing fence
                indent = match_close.group(1)
                trailing = match_close.group(3)
                fixed_line = f"{indent}```{trailing}\n"
                fixed_lines.append(fixed_line)
                modified = True
                print(f"  Line {i}: Fixed '{line.rstrip()}' -> '{fixed_line.rstrip()}'")
            else:
                fixed_lines.append(line)
            in_code_block = False
            code_block_lang = None
            continue

        fixed_lines.append(line)

    if modified:
        with open(filepath, "w") as f:
            f.writelines(fixed_lines)
        return True
    return False


def main():
    # Find all MDX files
    files = glob.glob("docs/**/*.mdx", recursive=True)

    fixed_count = 0
    total_files = 0

    for filepath in sorted(files):
        if fix_code_fences(filepath):
            print(f"✓ Fixed: {filepath}")
            fixed_count += 1
            total_files += 1
        else:
            total_files += 1

    print(f"\n{'=' * 60}")
    print(f"Summary: Fixed {fixed_count} out of {total_files} files")
    print(f"{'=' * 60}")

    return 0 if fixed_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
