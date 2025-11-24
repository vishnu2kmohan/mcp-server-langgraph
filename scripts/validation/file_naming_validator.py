#!/usr/bin/env python3
"""
Validates documentation file naming conventions.
"""

import sys
import re
import argparse
from pathlib import Path


def validate_file_naming(files):
    failed = False

    for file_path in files:
        path = Path(file_path)
        if "node_modules" in path.parts or "template" in path.parts:
            continue

        stem = path.stem

        # Skip special files like README, LICENSE, CONTRIBUTING etc if they are in root docs/
        # But the policy says "All .mdx files must be lowercase".
        # Usually README.md is allowed to be uppercase.
        # But let's stick to the description: "All .mdx files must be lowercase"

        if path.suffix == ".mdx":
            if any(c.isupper() for c in stem):
                print(f"Error: File '{file_path}' contains uppercase letters. Use kebab-case.")
                failed = True

            if "_" in stem:
                print(f"Error: File '{file_path}' contains underscores. Use kebab-case (hyphens).")
                failed = True

            if " " in stem:
                print(f"Error: File '{file_path}' contains spaces. Use kebab-case.")
                failed = True

        # Also description says "No .md files in docs/ directory".
        # That is covered by mdx_extension_validator, but we can check here too if we want.
        # But this script is named file_naming_validator.

    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", help="Path to check", required=False)
    parser.add_argument("files", nargs="*", help="Files to check")
    args = parser.parse_args()

    sys.exit(validate_file_naming(args.files))
