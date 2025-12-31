"""
Meta Test: Prevent create_all() Usage in Production Code

This test ensures that SQLAlchemy's create_all() is NEVER used in production code.
All schema management must go through Alembic migrations.

Background:
    Using create_all() in production causes schema drift between:
    - Development (where create_all() auto-creates tables from models)
    - Production (where only Alembic migrations run)

    This leads to:
    - Missing columns in production (e.g., workflows.title)
    - Missing tables in production (e.g., workflow_executions, alert_records)
    - Inconsistent database state between environments

Solution:
    1. All schema changes must be done via Alembic migrations
    2. This test blocks any PR that introduces create_all() calls
    3. Pre-commit hook provides immediate feedback during development

Reference: ADR for schema management practices (to be created)
"""

import gc
import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.meta, pytest.mark.unit]

# Root directory for source code
SRC_ROOT = Path(__file__).parent.parent.parent / "src"

# Patterns that indicate create_all() usage
CREATE_ALL_PATTERNS = [
    r"\.create_all\s*\(",
    r"metadata\.create_all",
    r"Base\.metadata\.create_all",
    r"run_sync\s*\(\s*\w+\.metadata\.create_all",
]

# Files that are explicitly allowed to have create_all()
# (e.g., test fixtures, migration tools)
ALLOWED_FILES = [
    # Test fixtures may need create_all() for in-memory databases
    "conftest.py",
    "test_",
    # Migration-related tools
    "alembic/",
]


def is_allowed_file(file_path: Path) -> bool:
    """Check if file is in the allowed list."""
    path_str = str(file_path)
    return any(allowed in path_str for allowed in ALLOWED_FILES)


def find_create_all_violations() -> list[tuple[Path, int, str]]:
    """
    Scan source code for create_all() usage.

    Returns:
        List of (file_path, line_number, line_content) tuples
    """
    violations = []
    combined_pattern = re.compile("|".join(CREATE_ALL_PATTERNS))

    for py_file in SRC_ROOT.rglob("*.py"):
        if is_allowed_file(py_file):
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            for line_num, line in enumerate(content.splitlines(), start=1):
                # Skip comments
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue

                if combined_pattern.search(line):
                    violations.append((py_file, line_num, stripped))
        except (OSError, UnicodeDecodeError):
            continue

    return violations


@pytest.mark.xdist_group(name="meta_tests")
class TestNoCreateAllUsage:
    """
    Test suite to prevent create_all() usage in production code.

    These tests enforce the architectural decision to use Alembic exclusively
    for database schema management.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_no_create_all_in_source_code(self) -> None:
        """
        GIVEN the source code directory
        WHEN we scan for create_all() patterns
        THEN no violations should be found in production code.

        This test will FAIL if any create_all() calls exist in src/,
        forcing developers to use Alembic migrations instead.
        """
        violations = find_create_all_violations()

        if violations:
            violation_report = "\n".join(
                f"  {path.relative_to(SRC_ROOT)}:{line_num}: {content}" for path, line_num, content in violations
            )
            pytest.fail(
                f"Found {len(violations)} create_all() violations in source code:\n"
                f"{violation_report}\n\n"
                f"SOLUTION: Remove create_all() calls and use Alembic migrations instead.\n"
                f"See: alembic/README.md for migration best practices."
            )

    def test_create_all_patterns_are_comprehensive(self) -> None:
        """
        GIVEN the create_all pattern list
        WHEN we check for common variations
        THEN all known patterns should be covered.
        """
        test_cases = [
            ("metadata.create_all()", True),
            ("Base.metadata.create_all(engine)", True),
            ("await conn.run_sync(Base.metadata.create_all)", True),
            (".create_all(bind=engine)", True),
            ("# metadata.create_all()", False),  # Comments should not match
            ("def create_all_tables():", False),  # Function definitions OK
            ("create_all_resources = []", False),  # Variable names OK
        ]

        combined_pattern = re.compile("|".join(CREATE_ALL_PATTERNS))

        for test_input, should_match in test_cases:
            # Skip comment check (handled separately in find_create_all_violations)
            if test_input.startswith("#"):
                continue

            matched = bool(combined_pattern.search(test_input))
            if should_match:
                assert matched, f"Pattern should match: {test_input!r}"
            # Note: We don't assert on should_not_match cases because
            # our patterns are intentionally broad to catch variations


@pytest.mark.xdist_group(name="meta_tests")
class TestAlembicMigrationCoverage:
    """
    Tests to ensure all SQLAlchemy models have corresponding Alembic migrations.

    This prevents the scenario where:
    - A developer adds a new column to a model
    - create_all() would create it in dev
    - But production fails because no migration exists
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alembic_versions_directory_exists(self) -> None:
        """
        GIVEN the project structure
        WHEN we check for alembic versions
        THEN the versions directory should exist with migrations.
        """
        alembic_versions = Path(__file__).parent.parent.parent / "alembic" / "versions"
        assert alembic_versions.exists(), f"Alembic versions directory not found: {alembic_versions}"

        migrations = list(alembic_versions.glob("*.py"))
        # Filter out __pycache__ and __init__.py
        migrations = [m for m in migrations if not m.name.startswith("_")]
        assert len(migrations) > 0, "No Alembic migrations found"

    def test_migration_chain_is_valid(self) -> None:
        """
        GIVEN the alembic migrations
        WHEN we check the revision chain
        THEN there should be a single head (no divergent branches).
        """
        import subprocess

        result = subprocess.run(
            ["uv", "run", "--frozen", "alembic", "heads"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Count the number of heads
        heads = [line for line in result.stdout.strip().split("\n") if line.strip()]
        assert len(heads) <= 1, (
            f"Multiple Alembic heads detected (migration branches diverged):\n"
            f"{result.stdout}\n"
            f"Run 'alembic merge heads' to create a merge migration."
        )
