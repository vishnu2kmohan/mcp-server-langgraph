#!/usr/bin/env python3
"""
Validate SQL migration files use idempotent patterns.

CODEX FINDING REGRESSION PREVENTION (2025-11-20):
Ensures SQL migrations use DROP IF EXISTS for triggers since PostgreSQL
doesn't support CREATE TRIGGER IF NOT EXISTS.

This hook prevents regression of DuplicateObjectError when migrations run multiple times.

References:
- migrations/001_gdpr_schema.sql:198,215 - DROP TRIGGER IF EXISTS pattern
- tests/integration/security/test_gdpr_schema_setup.py::test_schema_setup_is_idempotent
"""

import re
import sys
from pathlib import Path


def check_trigger_idempotency(file_path: Path) -> list[str]:
    """
    Check if SQL file uses idempotent trigger creation.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    content = file_path.read_text()
    lines = content.split("\n")

    # Find all CREATE TRIGGER statements
    for i, line in enumerate(lines, 1):
        # Match CREATE TRIGGER (case-insensitive, allowing whitespace)
        # Exclude CREATE TRIGGER IF (which would be invalid syntax anyway)
        if re.search(r"\bCREATE\s+TRIGGER\s+(?!IF\b)", line, re.IGNORECASE):
            trigger_match = re.search(r"\bCREATE\s+TRIGGER\s+(\w+)", line, re.IGNORECASE)
            if trigger_match:
                trigger_name = trigger_match.group(1)

                # Check if there's a DROP TRIGGER IF EXISTS before this CREATE
                # Look back up to 5 lines
                found_drop = False
                for j in range(max(0, i - 5), i):
                    if re.search(rf"\bDROP\s+TRIGGER\s+IF\s+EXISTS\s+{trigger_name}\b", lines[j], re.IGNORECASE):
                        found_drop = True
                        break

                if not found_drop:
                    errors.append(
                        f"{file_path.name}:{i}: CREATE TRIGGER {trigger_name} without preceding DROP TRIGGER IF EXISTS\n"
                        f"  PostgreSQL doesn't support CREATE TRIGGER IF NOT EXISTS.\n"
                        f"  Use this idempotent pattern:\n"
                        f"    DROP TRIGGER IF EXISTS {trigger_name} ON <table_name>;\n"
                        f"    CREATE TRIGGER {trigger_name} ...\n"
                    )

    return errors


def main(files: list[str] | None = None) -> int:
    """
    Validate migration files for idempotency.

    Args:
        files: List of file paths to check (defaults to migrations/*.sql)

    Returns:
        0 if all files are valid, 1 if errors found
    """
    project_root = Path(__file__).parent.parent
    migrations_dir = project_root / "migrations"

    if files:
        # Check specific files passed as arguments
        sql_files = [Path(f) for f in files if f.endswith(".sql")]
    else:
        # Check all SQL files in migrations/
        if not migrations_dir.exists():
            print(f"ℹ️  No migrations directory found at {migrations_dir}")
            return 0
        sql_files = list(migrations_dir.glob("*.sql"))

    if not sql_files:
        print("ℹ️  No SQL migration files to validate")
        return 0

    all_errors = []

    for sql_file in sql_files:
        errors = check_trigger_idempotency(sql_file)
        all_errors.extend(errors)

    if all_errors:
        print("❌ Migration idempotency validation failed:\n")
        for error in all_errors:
            print(error)
        print("\n📖 References:")
        print("   - Codex Finding: DuplicateObjectError on migration replay")
        print("   - PostgreSQL doesn't support CREATE TRIGGER IF NOT EXISTS")
        print("   - Solution: DROP TRIGGER IF EXISTS before CREATE TRIGGER")
        return 1

    print(f"✅ All {len(sql_files)} migration file(s) use idempotent patterns")
    return 0


if __name__ == "__main__":
    # Allow passing files as arguments (for pre-commit)
    files = sys.argv[1:] if len(sys.argv) > 1 else None
    sys.exit(main(files))
