#!/usr/bin/env python3
"""
Check version consistency across documentation.

Ensures that version references in documentation match the current project version
from pyproject.toml. Helps prevent confusion from outdated version examples.

Usage:
    python3 scripts/check_version_consistency.py [--fix]

Exit codes:
    0: All versions consistent or only historical references
    1: Inconsistencies found
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Backport for <3.11


def get_current_version() -> str:
    """Get current version from pyproject.toml."""
    try:
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
            return data["project"]["version"]
    except Exception as e:
        print(f"Error reading version from pyproject.toml: {e}")
        sys.exit(1)


def find_version_references(file_path: Path, current_version: str) -> list[tuple[int, str, str]]:
    """
    Find version references in a file.

    Args:
        file_path: Path to the file to check
        current_version: Current project version

    Returns:
        List of (line_number, found_version, context) tuples for outdated versions
    """
    outdated = []

    # Files that should have historical versions
    historical_files = [
        "releases/",
        "CHANGELOG.md",
        "adr-0018-semantic-versioning-strategy",  # Shows version progression examples
    ]

    # Skip historical files
    if any(hist in str(file_path) for hist in historical_files):
        return []

    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            # Match version patterns: v2.X.X, 2.X.X, version: 2.X.X, etc.
            # But skip inline code, URLs, and comments
            if re.search(r"^\s*#", line) or "```" in line:
                continue

            # Find version patterns
            patterns = [
                r"v(\d+\.\d+\.\d+)",
                r'version[:\s]+["\']?(\d+\.\d+\.\d+)',
                r"@(\d+\.\d+\.\d+)",
                r"\s(\d+\.\d+\.\d+)\s",
            ]

            for pattern in patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    found_version = match.group(1)

                    # Skip if it matches current version
                    if found_version == current_version:
                        continue

                    # Skip obviously non-project versions (e.g., dependency versions, years)
                    if found_version.startswith(("1.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")):
                        continue

                    # Skip if it's clearly a dependency version
                    if "python" in line.lower() or "node" in line.lower():
                        continue

                    # Skip dates (e.g., 2025.11.12)
                    if int(found_version.split(".")[0]) > 10:
                        continue

                    context = line.strip()[:80]
                    outdated.append((i, found_version, context))

    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return outdated


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Check version consistency in documentation")
    parser.add_argument("--fix", action="store_true", help="Automatically fix version references")
    args = parser.parse_args()

    current_version = get_current_version()
    print(f"Current version: {current_version}\n")

    docs_dir = Path("docs").resolve()
    if not docs_dir.exists():
        print("Error: docs/ directory not found")
        sys.exit(1)

    mdx_files = list(docs_dir.rglob("*.mdx"))
    md_files = [f.resolve() for f in Path().glob("*.md")]
    all_files = mdx_files + md_files

    issues: dict[Path, list[tuple[int, str, str]]] = {}

    for file_path in all_files:
        outdated = find_version_references(file_path, current_version)
        if outdated:
            issues[file_path] = outdated

    if not issues:
        print("✅ All version references are consistent!")
        return 0

    print(f"Found version inconsistencies in {len(issues)} files:\n")

    total_issues = 0
    cwd = Path.cwd()
    for file_path, file_issues in sorted(issues.items()):
        try:
            relative_path = file_path.relative_to(cwd)
        except ValueError:
            relative_path = file_path
        print(f"📄 {relative_path}")
        for line_num, version, context in file_issues[:5]:  # Show first 5
            print(f"   Line {line_num}: v{version} → should be v{current_version}")
            print(f"   Context: {context}")
            total_issues += 1

        if len(file_issues) > 5:
            print(f"   ... and {len(file_issues) - 5} more")

        print()

    print(f"\n📊 Summary: {total_issues} outdated version references in {len(issues)} files")
    print(f"\n💡 Tip: Review each reference to determine if it should be updated.")
    print(f"   Some references (examples, historical) may be intentionally older.")

    if args.fix:
        print("\n⚠️  Auto-fix not implemented yet. Manual review recommended.")

    return 1


if __name__ == "__main__":
    sys.exit(main())
