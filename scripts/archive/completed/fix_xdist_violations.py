#!/usr/bin/env python3
"""
Robust auto-fix for pytest-xdist memory safety violations.

Adds @pytest.mark.xdist_group markers and teardown_method() to all test classes.
Uses regex-based approach for precise code insertion.
"""

import re
import sys
from pathlib import Path


def add_xdist_marker_and_teardown(file_path):
    """Add xdist_group marker and teardown_method to test classes."""
    with open(file_path) as f:
        content = f.read()

    original_content = content
    lines = content.split("\n")

    # Check if gc is imported
    has_gc = re.search(r"^\s*import\s+gc\s*$", content, re.MULTILINE)

    # Find all test classes
    modifications = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Match test class definition
        class_match = re.match(r"^(@pytest\.mark\.\w+\s*)*class\s+(Test\w+)", line)
        if class_match:
            class_name = class_match.group(2)
            group_name = class_name.lower()
            indent = len(line) - len(line.lstrip())

            # Check if xdist_group marker already exists
            has_marker = False
            check_idx = i - 1
            while check_idx >= 0 and (lines[check_idx].strip().startswith("@") or not lines[check_idx].strip()):
                if "xdist_group" in lines[check_idx]:
                    has_marker = True
                    break
                if not lines[check_idx].strip().startswith("@") and lines[check_idx].strip():
                    break
                check_idx -= 1

            # Add xdist_group marker if missing
            if not has_marker:
                marker_line = " " * indent + f'@pytest.mark.xdist_group(name="{group_name}")'
                modifications.append(("insert_before", i, marker_line))

            # Check if teardown_method exists
            has_teardown = False
            j = i + 1
            class_indent = indent
            while j < len(lines):
                next_line = lines[j]
                next_indent = len(next_line) - len(next_line.lstrip())

                # Stop if we've left the class
                if next_line.strip() and next_indent <= class_indent and not next_line.strip().startswith("#"):
                    break

                if re.match(r"^\s*def\s+teardown_method\s*\(", next_line):
                    has_teardown = True
                    break

                j += 1

            # Add teardown_method if missing
            if not has_teardown:
                # Find where to insert (after class definition and any class docstring)
                insert_idx = i + 1

                # Skip empty lines and class docstring
                while insert_idx < len(lines):
                    check_line = lines[insert_idx].strip()
                    if not check_line:
                        insert_idx += 1
                        continue

                    # Check for docstring
                    if check_line.startswith('"""') or check_line.startswith("'''"):
                        # Multi-line docstring
                        if check_line.count('"""') >= 2 or check_line.count("'''") >= 2:
                            # Single line docstring
                            insert_idx += 1
                            break
                        # Find end of docstring
                        quote = '"""' if '"""' in check_line else "'''"
                        insert_idx += 1
                        while insert_idx < len(lines):
                            if quote in lines[insert_idx]:
                                insert_idx += 1
                                break
                            insert_idx += 1
                        break
                    # Not a docstring, insert here
                    break

                # Create teardown_method
                method_indent = " " * (indent + 4)
                teardown_lines = [
                    "",
                    method_indent + "def teardown_method(self) -> None:",
                    method_indent + '    """Force GC to prevent mock accumulation in xdist workers"""',
                    method_indent + "    gc.collect()",
                    "",
                ]

                modifications.append(("insert_at", insert_idx, teardown_lines))

        i += 1

    # Apply modifications in reverse order to maintain line numbers
    for mod_type, idx, data in reversed(modifications):
        if mod_type == "insert_before":
            lines.insert(idx, data)
        elif mod_type == "insert_at":
            for line in reversed(data):
                lines.insert(idx, line)

    content = "\n".join(lines)

    # Add gc import if needed
    if not has_gc and modifications:
        # Find last import line
        import_pattern = r"^(from .+ import .+|import .+)$"
        last_import_idx = -1
        lines = content.split("\n")

        for i, line in enumerate(lines):
            if re.match(import_pattern, line.strip()):
                last_import_idx = i

        if last_import_idx >= 0:
            lines.insert(last_import_idx + 1, "import gc")
            content = "\n".join(lines)

    if content != original_content:
        with open(file_path, "w") as f:
            f.write(content)
        return True

    return False


def main():
    repo_root = Path(__file__).parent.parent
    test_dir = repo_root / "tests"

    if len(sys.argv) > 1:
        files_to_fix = [Path(f) for f in sys.argv[1:] if f.endswith(".py")]
    else:
        files_to_fix = list(test_dir.rglob("test_*.py"))

    fixed_count = 0
    for test_file in sorted(files_to_fix):
        if add_xdist_marker_and_teardown(test_file):
            fixed_count += 1
            try:
                rel_path = test_file.relative_to(repo_root)
            except ValueError:
                rel_path = test_file
            print(f"✓ Fixed {rel_path}")

    print(f"\n✅ Fixed {fixed_count} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
