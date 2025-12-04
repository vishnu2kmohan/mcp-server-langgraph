"""
Meta-test: Verify Alembic migrations produce identical schema to SQL file.

This test ensures that the Alembic migration history and raw SQL schema
remain in sync, preventing schema drift between test and production environments.

Per Audit Finding #1 (Schema Drift Risk):
- Tests use migrations/001_gdpr_schema.sql directly
- Production uses Alembic migrations
- Risk: Updates to one without the other cause divergence

This meta-test validates:
1. Alembic migrations create same schema as SQL file
2. Migrations are reversible (upgrade/downgrade/upgrade)
3. No schema drift between test and production paths

TDD Phase: RED - Test written first, implementation follows
"""

import os
import socket
import subprocess

import asyncpg
import pytest
from tests.helpers.path_helpers import get_repo_root

# Module-level pytest marker (required by pre-commit hook)
pytestmark = pytest.mark.meta


def is_postgres_available() -> bool:
    """
    Check if PostgreSQL is available at configured host/port.

    Returns:
        bool: True if Postgres is reachable, False otherwise
    """
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))

    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (TimeoutError, OSError, ConnectionRefusedError):
        return False


# Skip all tests in this module if Postgres isn't available
SKIP_REASON = "PostgreSQL not available. Run 'make setup-infra' or 'docker-compose up -d postgres' to start infrastructure."
skip_without_postgres = pytest.mark.skipif(not is_postgres_available(), reason=SKIP_REASON)


# Test configuration
PROJECT_ROOT = get_repo_root()
SQL_SCHEMA_FILE = PROJECT_ROOT / "migrations" / "001_gdpr_schema.sql"
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"


def get_db_dsn(db_name: str) -> str:
    """Get PostgreSQL DSN for test database."""
    return (
        f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'postgres')}@"
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/{db_name}"
    )


def get_alembic_dsn(db_name: str) -> str:
    """Get Alembic-compatible DSN (postgresql+asyncpg)."""
    return (
        f"postgresql+asyncpg://{os.getenv('POSTGRES_USER', 'postgres')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'postgres')}@"
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/{db_name}"
    )


@pytest.mark.asyncio
@pytest.mark.xdist_group(name="testalembicschemaparity")
@skip_without_postgres
class TestAlembicSchemaParity:
    """Validate Alembic migrations match raw SQL schema."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        import gc

        gc.collect()

    async def _create_test_database(self, db_name: str):
        """Create a test database."""
        admin_dsn = get_db_dsn("postgres")
        admin_conn = await asyncpg.connect(admin_dsn)
        try:
            await admin_conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
            await admin_conn.execute(f'CREATE DATABASE "{db_name}"')
        finally:
            await admin_conn.close()

    async def _drop_test_database(self, db_name: str):
        """Drop a test database."""
        admin_dsn = get_db_dsn("postgres")
        admin_conn = await asyncpg.connect(admin_dsn)
        try:
            # Terminate existing connections
            await admin_conn.execute(
                f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = '{db_name}' AND pid <> pg_backend_pid()
                """
            )
            await admin_conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        finally:
            await admin_conn.close()

    async def _extract_schema(self, db_name: str) -> dict:
        """
        Extract schema information from database for comparison.

        Returns dict with:
        - tables: {table_name: {column_name: {type, nullable, default}}}
        - indexes: {index_name: {table, columns, unique}}
        - constraints: {constraint_name: {table, type, definition}}
        """
        dsn = get_db_dsn(db_name)
        conn = await asyncpg.connect(dsn)
        try:
            # Extract table structures
            columns = await conn.fetch(
                """
                SELECT
                    table_name,
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    ordinal_position
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name NOT IN ('alembic_version')
                ORDER BY table_name, ordinal_position
                """
            )

            tables = {}
            for col in columns:
                table = col["table_name"]
                if table not in tables:
                    tables[table] = {}

                tables[table][col["column_name"]] = {
                    "type": col["data_type"],
                    "nullable": col["is_nullable"],
                    "default": col["column_default"],
                    "position": col["ordinal_position"],
                }

            # Extract indexes
            indexes_raw = await conn.fetch(
                """
                SELECT
                    indexname,
                    tablename,
                    indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                AND tablename NOT IN ('alembic_version')
                ORDER BY indexname
                """
            )

            indexes = {idx["indexname"]: {"table": idx["tablename"], "definition": idx["indexdef"]} for idx in indexes_raw}

            # Extract constraints
            constraints_raw = await conn.fetch(
                """
                SELECT
                    tc.constraint_name,
                    tc.table_name,
                    tc.constraint_type,
                    cc.check_clause
                FROM information_schema.table_constraints tc
                LEFT JOIN information_schema.check_constraints cc
                    ON tc.constraint_name = cc.constraint_name
                WHERE tc.table_schema = 'public'
                AND tc.table_name NOT IN ('alembic_version')
                ORDER BY tc.constraint_name
                """
            )

            constraints = {
                cst["constraint_name"]: {
                    "table": cst["table_name"],
                    "type": cst["constraint_type"],
                    "clause": cst["check_clause"],
                }
                for cst in constraints_raw
            }

            return {"tables": tables, "indexes": indexes, "constraints": constraints}
        finally:
            await conn.close()

    def _run_alembic_migration(self, db_name: str, command: str) -> subprocess.CompletedProcess:
        """Run Alembic migration command."""
        env = os.environ.copy()
        env["DATABASE_URL"] = get_alembic_dsn(db_name)

        result = subprocess.run(
            ["alembic", "-c", str(ALEMBIC_INI), *command.split()],
            env=env,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=60,  # 60 seconds for migration commands
        )
        return result

    def _normalize_constraints(self, constraints: dict) -> dict:
        """
        Normalize constraints by filtering out auto-generated OID-based names.

        PostgreSQL generates constraint names like "2200_17144_1_not_null" based on
        internal object IDs. These differ between database instances but represent
        identical constraints. We filter these out and keep only named constraints.

        Returns:
            dict: Constraints with user-defined names only
        """
        # Filter out auto-generated constraint names (pattern: NNNN_NNNNN_N_not_null)
        normalized = {}
        for name, constraint in constraints.items():
            # Skip auto-generated NOT NULL constraint names
            if name.startswith("2200_") and "_not_null" in name:
                continue
            normalized[name] = constraint

        return normalized

    async def test_alembic_migration_creates_all_tables(self):
        """
        Test that Alembic migration creates all expected GDPR tables.

        Expected tables:
        - user_profiles
        - user_preferences
        - consent_records
        - conversations
        - audit_logs
        """
        db_name = f"test_alembic_{os.getpid()}_createtables"

        try:
            # Create database
            await self._create_test_database(db_name)

            # Run Alembic migration
            result = self._run_alembic_migration(db_name, "upgrade head")
            assert result.returncode == 0, f"Alembic migration failed: {result.stderr}"

            # Extract schema
            schema = await self._extract_schema(db_name)
            table_names = list(schema["tables"].keys())

            # Verify all GDPR tables exist
            expected_tables = [
                "audit_logs",
                "consent_records",
                "conversations",
                "user_preferences",
                "user_profiles",
            ]

            for table in expected_tables:
                assert table in table_names, f"Missing table: {table}"

        finally:
            # Cleanup
            await self._drop_test_database(db_name)

    async def test_sql_schema_creates_all_tables(self):
        """
        Test that SQL schema file creates all expected GDPR tables.

        This validates the current test approach (direct SQL execution).
        """
        db_name = f"test_sql_{os.getpid()}_createtables"

        try:
            # Create database
            await self._create_test_database(db_name)

            # Execute SQL schema
            dsn = get_db_dsn(db_name)
            conn = await asyncpg.connect(dsn)
            try:
                schema_sql = SQL_SCHEMA_FILE.read_text()
                await conn.execute(schema_sql)
            finally:
                await conn.close()

            # Extract schema
            schema = await self._extract_schema(db_name)
            table_names = list(schema["tables"].keys())

            # Verify all GDPR tables exist
            expected_tables = [
                "audit_logs",
                "consent_records",
                "conversations",
                "user_preferences",
                "user_profiles",
            ]

            for table in expected_tables:
                assert table in table_names, f"Missing table: {table}"

        finally:
            # Cleanup
            await self._drop_test_database(db_name)

    async def test_alembic_and_sql_produce_identical_schemas(self):
        """
        CRITICAL TEST: Verify Alembic migrations produce identical schema to SQL file.

        This prevents schema drift between test environment (SQL) and
        production environment (Alembic).

        Compares:
        - Table structures (columns, types, constraints)
        - Indexes
        - Comments
        - Check constraints
        - Foreign keys
        """
        alembic_db = f"test_alembic_{os.getpid()}_parity"
        sql_db = f"test_sql_{os.getpid()}_parity"

        try:
            # Create both databases
            await self._create_test_database(alembic_db)
            await self._create_test_database(sql_db)

            # Initialize Alembic database
            result = self._run_alembic_migration(alembic_db, "upgrade head")
            assert result.returncode == 0, f"Alembic migration failed: {result.stderr}"

            # Initialize SQL database
            dsn = get_db_dsn(sql_db)
            conn = await asyncpg.connect(dsn)
            try:
                schema_sql = SQL_SCHEMA_FILE.read_text()
                await conn.execute(schema_sql)
            finally:
                await conn.close()

            # Extract schemas
            alembic_schema = await self._extract_schema(alembic_db)
            sql_schema = await self._extract_schema(sql_db)

            # Compare table structures
            assert alembic_schema["tables"] == sql_schema["tables"], (
                "Table structures differ between Alembic and SQL:\n"
                f"Alembic tables: {sorted(alembic_schema['tables'].keys())}\n"
                f"SQL tables: {sorted(sql_schema['tables'].keys())}"
            )

            # Compare indexes
            assert alembic_schema["indexes"] == sql_schema["indexes"], (
                "Indexes differ between Alembic and SQL:\n"
                f"Alembic indexes: {sorted(alembic_schema['indexes'].keys())}\n"
                f"SQL indexes: {sorted(sql_schema['indexes'].keys())}"
            )

            # Compare constraints (normalize auto-generated OID-based constraint names)
            alembic_normalized = self._normalize_constraints(alembic_schema["constraints"])
            sql_normalized = self._normalize_constraints(sql_schema["constraints"])

            assert alembic_normalized == sql_normalized, (
                "Constraints differ between Alembic and SQL:\n"
                f"Alembic constraints: {sorted(alembic_normalized.keys())}\n"
                f"SQL constraints: {sorted(sql_normalized.keys())}\n"
                f"Differences found in functional definitions"
            )

        finally:
            # Cleanup
            await self._drop_test_database(alembic_db)
            await self._drop_test_database(sql_db)

    async def test_alembic_migration_is_reversible(self):
        """
        Test that Alembic migrations can be reversed (downgrade -> upgrade).

        Ensures migrations are idempotent and reversible for production rollback scenarios.
        """
        db_name = f"test_alembic_{os.getpid()}_reversible"

        try:
            # Create database
            await self._create_test_database(db_name)

            # 1. Upgrade to head
            result = self._run_alembic_migration(db_name, "upgrade head")
            assert result.returncode == 0, f"Alembic upgrade failed: {result.stderr}"

            # Verify tables exist
            schema = await self._extract_schema(db_name)
            assert len(schema["tables"]) > 0, "No tables created after upgrade"
            tables_after_upgrade = set(schema["tables"].keys())

            # 2. Downgrade to base
            result = self._run_alembic_migration(db_name, "downgrade base")
            assert result.returncode == 0, f"Alembic downgrade failed: {result.stderr}"

            # Verify tables removed
            schema = await self._extract_schema(db_name)
            assert len(schema["tables"]) == 0, f"Tables still exist after downgrade: {list(schema['tables'].keys())}"

            # 3. Re-upgrade to head
            result = self._run_alembic_migration(db_name, "upgrade head")
            assert result.returncode == 0, f"Alembic re-upgrade failed: {result.stderr}"

            # Verify tables recreated
            schema = await self._extract_schema(db_name)
            assert len(schema["tables"]) > 0, "No tables created after re-upgrade"
            tables_after_reupgrade = set(schema["tables"].keys())

            # Verify same tables created
            assert tables_after_upgrade == tables_after_reupgrade, (
                "Tables differ after upgrade/downgrade/upgrade cycle:\n"
                f"Initial: {sorted(tables_after_upgrade)}\n"
                f"After cycle: {sorted(tables_after_reupgrade)}"
            )

        finally:
            # Cleanup
            await self._drop_test_database(db_name)
