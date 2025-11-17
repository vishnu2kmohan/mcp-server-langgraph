#!/usr/bin/env python3
"""Fix import issues from memory safety auto-fix.

Fixes:
1. Add 'import pytest' to files using @pytest.mark.xdist_group
2. Move 'import gc' to proper location (top of file, in stdlib section)
"""

import re
import sys
from pathlib import Path


def fix_imports(file_path: Path) -> bool:
    """Fix import issues in a test file.

    Returns:
        True if changes were made, False otherwise
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content
    lines = content.splitlines(keepends=True)

    # Check if file uses @pytest.mark.xdist_group
    uses_pytest_marker = "@pytest.mark.xdist_group" in content
    has_pytest_import = re.search(r"^\s*import\s+pytest\s*$", content, re.MULTILINE)
    has_gc_import = "import gc" in content

    if not uses_pytest_marker or (has_pytest_import and not has_gc_import):
        return False  # Nothing to fix

    # Find module docstring end
    docstring_end = 0
    if lines and lines[0].strip().startswith(('"""', "'''")):
        quote = '"""' if '"""' in lines[0] else "'''"
        if lines[0].count(quote) >= 2:
            docstring_end = 1
        else:
            for i in range(1, len(lines)):
                if quote in lines[i]:
                    docstring_end = i + 1
                    break

    # Remove existing gc import if present
    if has_gc_import:
        lines = [line for line in lines if not re.match(r"^\s*import\s+gc\s*$", line)]

    # Find first import line after docstring
    first_import_idx = None
    for i in range(docstring_end, len(lines)):
        if re.match(r"^\s*(import|from)\s+", lines[i]):
            first_import_idx = i
            break

    # Add both gc and pytest imports at the top of imports section
    if first_import_idx is not None:
        imports_to_add = []
        if has_gc_import or uses_pytest_marker:
            imports_to_add.append("import gc\n")
        if uses_pytest_marker and not has_pytest_import:
            imports_to_add.append("import pytest\n")

        # Insert in reverse order to maintain line numbers
        for imp in reversed(imports_to_add):
            lines.insert(first_import_idx, imp)

    new_content = "".join(lines)

    if new_content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True

    return False


def main() -> int:
    """Main entry point."""
    if len(sys.argv) > 1:
        files_to_fix = [Path(f) for f in sys.argv[1:] if f.endswith(".py")]
    else:
        repo_root = Path(__file__).parent.parent
        files_to_fix = sorted(repo_root.rglob("tests/**/test_*.py"))

    fixed_count = 0
    for file_path in files_to_fix:
        if fix_imports(file_path):
            fixed_count += 1
            try:
                repo_root = Path(__file__).parent.parent
                rel_path = file_path.relative_to(repo_root)
            except (ValueError, NameError):
                rel_path = file_path
            print(f"✓ Fixed imports in {rel_path}")

    print(f"\n✅ Fixed {fixed_count} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
