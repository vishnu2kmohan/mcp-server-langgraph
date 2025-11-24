#!/usr/bin/env python3
"""
Validates that all files in docs/ use .mdx extension.
"""

import sys
from pathlib import Path


def validate_mdx_extensions(files):
    failed = False
    for file_path in files:
        path = Path(file_path)

        # Skip unrelated directories
        if "node_modules" in path.parts or "template" in path.parts:
            continue

        # Check if file is in docs/ (or subdirectory) and has .md extension
        # The pre-commit hook filters for docs/ so we can assume passed files are relevant
        if path.suffix == ".md":
            print(f"Error: File '{file_path}' should use .mdx extension for Mintlify compatibility.")
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    # pre-commit passes files as arguments
    sys.exit(validate_mdx_extensions(sys.argv[1:]))
