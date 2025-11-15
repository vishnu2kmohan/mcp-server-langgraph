#!/usr/bin/env python3
"""Comprehensively add timeout parameters to all subprocess.run() calls.

Handles multiple code patterns and formatting styles.
"""

import re
from pathlib import Path
from typing import List, Tuple


def find_subprocess_blocks(content: str) -> List[Tuple[int, int, str]]:
    """Find all subprocess.run() call blocks.

    Returns:
        List of (start_pos, end_pos, block_content)
    """
    blocks = []
    pattern = r"subprocess\.run\s*\("

    for match in re.finditer(pattern, content):
        start = match.start()

        # Find the matching closing paren
        depth = 0
        in_call = False
        end = start

        for i in range(start, len(content)):
            char = content[i]

            if char == "(":
                depth += 1
                in_call = True
            elif char == ")":
                depth -= 1

                if depth == 0 and in_call:
                    end = i + 1
                    break

        if end > start:
            blocks.append((start, end, content[start:end]))

    return blocks


def add_timeout_to_call(call_block: str) -> str:
    """Add timeout=60 to a subprocess.run() call block if missing.

    Returns:
        Modified call block with timeout added
    """
    # Check if timeout already exists
    if re.search(r"\btimeout\s*=", call_block):
        return call_block  # Already has timeout

    # Find where to insert timeout
    # Strategy: Insert after the last keyword argument, before the closing paren

    # First, try to find common insertion points
    insertion_patterns = [
        (r"(text\s*=\s*True)\s*,", r"\1,\n            timeout=60,"),
        (r"(capture_output\s*=\s*True)\s*,", r"\1,\n            timeout=60,"),
        (r"(check\s*=\s*True)\s*,", r"\1,\n            timeout=60,"),
        (r"(cwd\s*=\s*[^,]+)\s*,", r"\1,\n            timeout=60,"),
    ]

    for pattern, replacement in insertion_patterns:
        if re.search(pattern, call_block):
            return re.sub(pattern, replacement, call_block, count=1)

    # Fallback: Add before closing paren
    # Match the last parameter and add timeout after it
    call_block = re.sub(r"(\s*)(\))\s*$", r"\1    timeout=60,\n\1\2", call_block)

    return call_block


def fix_subprocess_timeouts_in_file(file_path: Path) -> int:
    """Add timeout parameters to subprocess.run() calls in a file.

    Returns:
        Number of modifications made
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, IOError):
        return 0

    modifications = 0

    # Find all subprocess.run() blocks
    blocks = find_subprocess_blocks(content)

    # Process blocks in reverse order to preserve positions
    for start, end, block in reversed(blocks):
        new_block = add_timeout_to_call(block)

        if new_block != block:
            content = content[:start] + new_block + content[end:]
            modifications += 1

    if modifications > 0:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    return modifications


def main():
    """Process all test files."""
    tests_dir = Path(__file__).parent.parent / "tests"
    test_files = list(tests_dir.rglob("test_*.py"))

    total_modified_files = 0
    total_modifications = 0

    print(f"Processing {len(test_files)} test files...")

    for test_file in test_files:
        mods = fix_subprocess_timeouts_in_file(test_file)
        if mods > 0:
            total_modified_files += 1
            total_modifications += mods
            print(f"✓ {test_file.relative_to(tests_dir)}: Added {mods} timeout parameter(s)")

    print(f"\nSummary:")
    print(f"  Modified files: {total_modified_files}")
    print(f"  Total timeout parameters added: {total_modifications}")

    return 0


if __name__ == "__main__":
    main()
