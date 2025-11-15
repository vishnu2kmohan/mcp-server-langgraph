#!/usr/bin/env python3
"""Add timeout=60 to subprocess.run() calls missing timeout parameter.

Simple line-based approach that preserves formatting and comments.
"""

import re
from pathlib import Path


def add_timeout_to_file(file_path: Path) -> int:
    """Add timeout parameter to subprocess.run() calls in a file.

    Returns:
        Number of modifications made
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (UnicodeDecodeError, IOError):
        return 0

    modifications = 0
    in_subprocess_call = False
    call_start_line = -1

    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect start of subprocess.run() call
        if "subprocess.run(" in line:
            in_subprocess_call = True
            call_start_line = i

        # If we're in a subprocess call, look for the closing paren
        if in_subprocess_call:
            # Check if this line or subsequent lines contain timeout=
            remaining_lines = "".join(lines[call_start_line : i + 10])  # Look ahead max 10 lines
            has_timeout = "timeout=" in remaining_lines

            # If we find the closing paren and no timeout, add it
            if ")" in line and "subprocess.run(" not in line:
                if not has_timeout:
                    # Find where to insert timeout
                    # Look for capture_output=True or text=True
                    for j in range(call_start_line, i + 1):
                        if ("capture_output=True," in lines[j] or "text=True," in lines[j]) and "timeout=" not in lines[j]:
                            # Add timeout right after this line
                            indent = len(lines[j]) - len(lines[j].lstrip())
                            lines.insert(j + 1, " " * indent + "timeout=60,\n")
                            modifications += 1
                            i += 1  # Account for inserted line
                            break

                in_subprocess_call = False
                call_start_line = -1

        i += 1

    if modifications > 0:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    return modifications


def main():
    """Process all test files."""
    tests_dir = Path(__file__).parent.parent / "tests"
    test_files = list(tests_dir.rglob("test_*.py"))

    total_modified_files = 0
    total_modifications = 0

    print(f"Processing {len(test_files)} test files...")

    for test_file in test_files:
        mods = add_timeout_to_file(test_file)
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
