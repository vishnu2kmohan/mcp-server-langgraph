#!/usr/bin/env python3
"""
Automated script to fix hardcoded IDs in test files.

Replaces hardcoded user IDs like "user:alice" with worker-safe ID helpers like get_user_id("alice").
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def fix_hardcoded_user_ids(content: str, filename: str) -> Tuple[str, int]:
    """
    Fix hardcoded user IDs in test file content.

    Returns:
        Tuple of (fixed_content, num_fixes)
    """
    fixes = 0

    # Common hardcoded user ID patterns
    user_patterns = [
        (r'"user:alice"', 'get_user_id("alice")'),
        (r'"user:bob"', 'get_user_id("bob")'),
        (r'"user:charlie"', 'get_user_id("charlie")'),
        (r'"user:dave"', 'get_user_id("dave")'),
        (r'"user:eve"', 'get_user_id("eve")'),
        (r'"user:frank"', 'get_user_id("frank")'),
        (r'"user:grace"', 'get_user_id("grace")'),
        (r'"user:henry"', 'get_user_id("henry")'),
        (r'"user:iris"', 'get_user_id("iris")'),
        (r'"user:jack"', 'get_user_id("jack")'),
        (r'"user:kate"', 'get_user_id("kate")'),
        (r'"user:liam"', 'get_user_id("liam")'),
        (r'"user:mike"', 'get_user_id("mike")'),
        (r'"user:nina"', 'get_user_id("nina")'),
        (r'"user:oscar"', 'get_user_id("oscar")'),
        (r'"user:paul"', 'get_user_id("paul")'),
        (r'"user:quinn"', 'get_user_id("quinn")'),
        (r'"user:sam"', 'get_user_id("sam")'),
        (r'"user:tina"', 'get_user_id("tina")'),
        (r'"user:uma"', 'get_user_id("uma")'),
        (r'"user:victor"', 'get_user_id("victor")'),
        (r'"user:wendy"', 'get_user_id("wendy")'),
        (r'"user:nobody"', 'get_user_id("nobody")'),
        # Additional patterns from validation failures
        (r'"user:admin"', 'get_user_id("admin")'),
        (r'"user:unknown"', 'get_user_id("unknown")'),
        (r'"user:keycloak_admin"', 'get_user_id("keycloak_admin")'),
        (r'"user:keycloak_alice"', 'get_user_id("keycloak_alice")'),
        (r'"user:keycloak_bob"', 'get_user_id("keycloak_bob")'),
        (r'"user:keycloak_limited"', 'get_user_id("keycloak_limited")'),
        (r'"user:nonexistent"', 'get_user_id("nonexistent")'),
        (r'"user:test"', 'get_user_id("test")'),
        (r'"user:owner"', 'get_user_id("owner")'),
    ]

    for pattern, replacement in user_patterns:
        before = content
        content = re.sub(pattern, replacement, content)
        if content != before:
            fixes += content.count(replacement) - before.count(replacement)

    return content, fixes


def ensure_import(content: str) -> str:
    """Ensure get_user_id import is present."""
    # Check if already imported
    if "from tests.conftest import" in content and "get_user_id" in content:
        return content  # Already has import

    # Check if there's an existing import from tests.conftest
    existing_import_pattern = r"from tests\.conftest import ([^\n]+)"
    match = re.search(existing_import_pattern, content)

    if match:
        # Add to existing import
        existing_imports = match.group(1)
        if "get_user_id" not in existing_imports:
            new_imports = existing_imports.rstrip() + ", get_user_id"
            content = re.sub(existing_import_pattern, f"from tests.conftest import {new_imports}", content)
    else:
        # Add new import after other imports
        # Find the last import line
        lines = content.split("\n")
        last_import_idx = -1
        for idx, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                last_import_idx = idx

        if last_import_idx >= 0:
            lines.insert(last_import_idx + 1, "from tests.conftest import get_user_id")
            content = "\n".join(lines)

    return content


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python fix_hardcoded_ids.py <test_file> [<test_file> ...]")
        return 1

    total_fixes = 0
    files_modified = 0

    for filepath_str in sys.argv[1:]:
        filepath = Path(filepath_str)
        if not filepath.exists():
            print(f"⚠️  File not found: {filepath}")
            continue

        print(f"Processing {filepath}...")

        # Read file
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Fix hardcoded IDs
        fixed_content, num_fixes = fix_hardcoded_user_ids(content, str(filepath))

        if num_fixes > 0:
            # Ensure import is present
            fixed_content = ensure_import(fixed_content)

            # Write back
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(fixed_content)

            print(f"✅ Fixed {num_fixes} hardcoded IDs in {filepath}")
            total_fixes += num_fixes
            files_modified += 1
        else:
            print(f"  No fixes needed")

    if total_fixes > 0:
        print(f"\n✅ Total: Fixed {total_fixes} hardcoded IDs in {files_modified} files")
        return 0
    else:
        print("\n  No hardcoded IDs found")
        return 0


if __name__ == "__main__":
    sys.exit(main())
