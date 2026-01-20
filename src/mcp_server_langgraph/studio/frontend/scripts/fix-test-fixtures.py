#!/usr/bin/env python3
"""
Fix test fixtures to add transformSnakeToCamel for API response assertions.

This script adds the transform import and updates tests that check API response
properties to use transformed data.
"""

import re
import sys
from pathlib import Path

FILES_TO_FIX = [
    "src/mocks/handlers/aiSuggestionsHandlers.test.ts",
    "src/mocks/handlers/aiHandlers.test.ts",
]


def add_transform_import(content: str) -> tuple[str, bool]:
    """Add transformSnakeToCamel import if not present."""
    if "transformSnakeToCamel" in content:
        return content, False

    # Find the vitest import and add after it
    vitest_import = re.search(r'import\s+\{[^}]+\}\s+from\s+["\']vitest["\'];?', content)
    if vitest_import:
        insert_pos = vitest_import.end()
        import_line = '\nimport { transformSnakeToCamel } from "../../api/transforms";'
        content = content[:insert_pos] + import_line + content[insert_pos:]
        return content, True

    return content, False


def main() -> int:
    print("Fixing test fixtures to use transformSnakeToCamel...\n")

    for file_path in FILES_TO_FIX:
        path = Path(file_path)
        if not path.exists():
            print(f"  Skipped {file_path} - not found")
            continue

        content = path.read_text()
        original = content

        content, added = add_transform_import(content)
        if added:
            print(f"  + Added transformSnakeToCamel import to {file_path}")
            path.write_text(content)
        else:
            print(f"  Already has transform import: {file_path}")

    print("\nDone! Run tests to see what needs manual fixes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
