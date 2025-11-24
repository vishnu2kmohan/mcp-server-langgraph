#!/usr/bin/env python3
"""Add 'import gc' to all test files that don't have it."""

import re
from pathlib import Path


def add_gc_import(file_path):
    """Add 'import gc' to a test file if not already present."""
    with open(file_path) as f:
        content = f.read()

    # Check if gc is already imported
    if re.search(r"^\s*import\s+gc\s*$", content, re.MULTILINE):
        return False
    if re.search(r"^\s*from\s+.*\s+import\s+.*gc", content, re.MULTILINE):
        return False

    lines = content.splitlines(keepends=True)

    # Find the last import line
    last_import_idx = -1
    for i, line in enumerate(lines):
        if re.match(r"^\s*(import|from)\s+", line):
            last_import_idx = i

    if last_import_idx >= 0:
        # Insert after last import
        lines.insert(last_import_idx + 1, "import gc\n")
    else:
        # No imports found, add at beginning after module docstring
        insert_idx = 0
        if lines and lines[0].strip().startswith('"""'):
            # Skip module docstring
            for i in range(1, len(lines)):
                if '"""' in lines[i]:
                    insert_idx = i + 1
                    break
        lines.insert(insert_idx, "import gc\n")

    with open(file_path, "w") as f:
        f.writelines(lines)

    return True


def main():
    repo_root = Path(__file__).parent.parent
    test_dir = repo_root / "tests"

    fixed_count = 0
    for test_file in test_dir.rglob("test_*.py"):
        if add_gc_import(test_file):
            fixed_count += 1
            print(f"✓ Added import gc to {test_file.relative_to(repo_root)}")

    print(f"\n✅ Added import gc to {fixed_count} file(s)")


if __name__ == "__main__":
    main()
