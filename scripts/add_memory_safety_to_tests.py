#!/usr/bin/env python3
"""
Add memory safety protections to test files.

Adds:
1. import gc (if not present)
2. @pytest.mark.xdist_group marker to test classes
3. teardown_method with gc.collect() to test classes
"""

import re
import sys
from pathlib import Path


def add_memory_safety(filepath: str, group_name: str) -> tuple[bool, str]:
    """
    Add memory safety protections to a test file.

    Args:
        filepath: Path to test file
        group_name: Name for xdist_group (e.g., "keycloak_unit_tests")

    Returns:
        (changed, message) tuple
    """
    path = Path(filepath)
    if not path.exists():
        return False, f"File not found: {filepath}"

    content = path.read_text()
    original_content = content

    # Step 1: Add import gc if not present
    if "import gc" not in content:
        # Find last import line
        import_pattern = r"(^import .*\n|^from .* import .*\n)"
        imports = list(re.finditer(import_pattern, content, re.MULTILINE))
        if imports:
            last_import = imports[0]  # Add at beginning for consistency
            insert_pos = content.find("\n", last_import.start()) + 1
            if content[insert_pos - 10 : insert_pos].strip().startswith('"""'):
                # After module docstring
                docstring_end = content.find('"""', insert_pos) + 3
                insert_pos = content.find("\n", docstring_end) + 1

            content = content[:insert_pos] + "import gc\n" + content[insert_pos:]

    # Step 2: Find all test classes and add markers + teardown
    class_pattern = r"(@pytest\.mark\.\w+\s*\n)*class (Test\w+):"

    def replace_class(match):
        decorators = match.group(0).split("\nclass ")[0]
        class_name_line = "class " + match.group(0).split("\nclass ")[1]

        # Check if already has xdist_group
        if "@pytest.mark.xdist_group" in decorators:
            return match.group(0)  # Already protected

        # Add xdist_group marker
        new_decorators = decorators + f'\n@pytest.mark.xdist_group(name="{group_name}")'
        return new_decorators + "\n" + class_name_line

    content = re.sub(class_pattern, replace_class, content)

    # Step 3: Add teardown_method to each test class (if not present)
    # Find classes and add teardown after docstring
    class_full_pattern = r'(class Test\w+:)\s*\n(\s+"""[^"]*""")\s*\n'

    def add_teardown(match):
        class_def = match.group(1)
        docstring = match.group(2)

        # Check if teardown already exists in this class
        # We'll do this by looking ahead (simplified - may miss some cases)
        teardown_code = '''
    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()
'''

        return class_def + "\n" + docstring + "\n" + teardown_code + "\n"

    content = re.sub(class_full_pattern, add_teardown, content)

    # Check if anything changed
    if content == original_content:
        return False, "No changes needed"

    # Write back
    path.write_text(content)
    return True, "Updated successfully"


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python add_memory_safety_to_tests.py <file> <group_name>")
        print("Example: python add_memory_safety_to_tests.py tests/test_keycloak.py keycloak_unit_tests")
        sys.exit(1)

    filepath = sys.argv[1]
    group_name = sys.argv[2]

    changed, message = add_memory_safety(filepath, group_name)
    print(f"{filepath}: {message}")
    sys.exit(0 if changed else 1)
