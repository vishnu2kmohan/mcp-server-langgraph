#!/usr/bin/env python3
"""
Migrate MSW handlers to use apiJsonResponse for snake_case API responses.

This script:
1. Adds import for apiJsonResponse utility
2. Replaces HttpResponse.json() calls with apiJsonResponse()
3. Excludes error responses (which already use snake_case)

Usage: python scripts/migrate-msw-to-snake-case.py [--dry-run]
"""

import re
import sys
from pathlib import Path

# MSW handler files to migrate (from audit report)
MSW_HANDLER_FILES = [
    "src/mocks/handlers/canvasHandlers.ts",
    "src/mocks/handlers/mcpHandlers.ts",
]

# Import statement to add
API_RESPONSE_IMPORT = 'import { apiJsonResponse, apiErrorResponse } from "../utils/apiResponse";'


def migrate_file(filepath: Path, dry_run: bool = False) -> tuple[int, list[str]]:
    """Migrate a single file. Returns (changes_count, change_descriptions)."""
    if not filepath.exists():
        return 0, ["  Skipped: file not found"]

    content = filepath.read_text()
    original = content
    changes = []

    # Check if already migrated
    if "apiJsonResponse" in content:
        return 0, ["  Already migrated"]

    # Add import after existing msw import
    msw_import_pattern = r'(import\s+\{[^}]*\}\s+from\s+["\']msw["\'];?)'
    if re.search(msw_import_pattern, content):
        # Add our import after the msw import
        content = re.sub(
            msw_import_pattern,
            r"\1\n" + API_RESPONSE_IMPORT,
            content,
            count=1,
        )
        changes.append("  + Added apiJsonResponse import")

    # Replace HttpResponse.json calls that return data objects
    # Exclude error responses (status >= 400)
    # Pattern[str]: HttpResponse.json(something, { status: 4xx or 5xx })

    # First, let's find all HttpResponse.json calls
    # We need to be careful not to replace error responses

    # Simple replacement for non-error cases
    # Match[str] HttpResponse.json(data) or HttpResponse.json(data, { status: 200/201 })
    def replace_json_call(match):
        full_match = match.group(0)
        # Check if this is an error response
        if "status: 4" in full_match or "status: 5" in full_match:
            # This is an error response, use apiErrorResponse instead
            return full_match.replace("HttpResponse.json", "HttpResponse.json")  # Keep as-is for now
        return full_match.replace("HttpResponse.json", "apiJsonResponse")

    # Pattern[str] for HttpResponse.json calls
    # This is tricky because we need to match balanced parentheses
    # Simplified approach: replace HttpResponse.json( with apiJsonResponse(
    # and let developers fix edge cases

    # Replace simple cases: HttpResponse.json(expr)
    simple_pattern = r"HttpResponse\.json\("
    content, count = re.subn(simple_pattern, "apiJsonResponse(", content)

    if count > 0:
        changes.append(f"  + Replaced {count} HttpResponse.json() calls")

    # Now we need to handle error responses specially
    # Find lines with status: 4xx or 5xx and revert them
    lines = content.split("\n")
    reverted = 0
    for i, line in enumerate(lines):
        if "apiJsonResponse(" in line and ("status: 4" in line or "status: 5" in line):
            lines[i] = line.replace("apiJsonResponse(", "apiErrorResponse(")
            reverted += 1

    if reverted > 0:
        content = "\n".join(lines)
        changes.append(f"  + Converted {reverted} error responses to apiErrorResponse()")

    # Remove HttpResponse from import if no longer used
    if "HttpResponse" in content:
        # Check if HttpResponse is still used anywhere (besides the import)
        uses = len(re.findall(r"HttpResponse\s*\.", content))
        if uses == 0:
            # Remove HttpResponse from import
            content = re.sub(r",?\s*HttpResponse\s*,?", "", content)
            content = re.sub(r"\{\s*,", "{", content)  # Clean up {, ...
            content = re.sub(r",\s*\}", "}", content)  # Clean up ..., }
            changes.append("  - Removed unused HttpResponse import")

    if content != original:
        if not dry_run:
            filepath.write_text(content)
        return len(changes), changes

    return 0, []


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    mode = "[DRY RUN] " if dry_run else ""

    print(f"{mode}Migrating MSW handlers to use apiJsonResponse...\n")

    total_files = 0
    total_changes = 0

    for file_path in MSW_HANDLER_FILES:
        path = Path(file_path)
        print(f"Processing: {file_path}")
        count, changes = migrate_file(path, dry_run)

        if count > 0:
            total_files += 1
            total_changes += count
            for change in changes:
                print(change)
        elif changes:
            for change in changes:
                print(change)
        else:
            print("  No changes needed")

    print(f"\n{'=' * 60}")
    print(f"{mode}SUMMARY: {total_changes} changes in {total_files} files")
    print("=" * 60)

    if total_changes > 0 and not dry_run:
        print("\nRun tests to verify:")
        print("  npm test -- --run src/mocks/handlers/")

    return 0


if __name__ == "__main__":
    sys.exit(main())
