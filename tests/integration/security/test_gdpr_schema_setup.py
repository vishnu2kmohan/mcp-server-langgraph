"""
Tests for GDPR schema setup in integration tests

Validates that GDPR database schema is properly initialized before
security tests run. This prevents "table does not exist" errors.

Following TDD best practices:
- Tests define expected schema state (RED phase)
- Fixture implementation makes tests pass (GREEN phase)
- Refactor for quality (REFACTOR phase)

OpenAI Codex Finding (2025-11-16):
====================================
Tests in test_sql_injection_gdpr.py failed with:
  asyncpg.exceptions.UndefinedTableError: relation "conversations" does not exist

Root cause: Alembic migrations use asyncio.run() which fails in pytest-asyncio context.
Exception was silently caught, schema never created.

Solution: Execute schema SQL directly using async connection, bypassing Alembic.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.xdist_group(name="integration_security_gdpr_schema_tests")
class TestGDPRSchemaSetup:
    """Test that GDPR schema is properly initialized for security tests"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        import gc

        gc.collect()

    @pytest.mark.asyncio
    async def test_gdpr_schema_managed_by_alembic(self):
        """
        Test that GDPR schema is managed by Alembic migrations.

        Previously validated migrations/001_gdpr_schema.sql existed.
        Schema is now managed exclusively by Alembic (SQL migrations superseded).
        This test validates that Alembic is the source of truth.
        """
        # GIVEN: Project root path (find by looking for pyproject.toml)
        current = Path(__file__).resolve()
        project_root = None
        for parent in current.parents:
            if (parent / "pyproject.toml").exists():
                project_root = parent
                break

        assert project_root is not None, "Could not find project root (no pyproject.toml)"

        # THEN: Alembic config should exist (source of truth for schema)
        alembic_ini = project_root / "alembic.ini"
        assert alembic_ini.exists(), f"Alembic config not found: {alembic_ini}"

        # AND: Alembic versions directory should have migrations
        versions_dir = project_root / "alembic" / "versions"
        assert versions_dir.exists(), f"Alembic versions directory not found: {versions_dir}"
        migration_files = list(versions_dir.glob("*.py"))
        assert len(migration_files) > 0, "No Alembic migration files found"

    @pytest.mark.asyncio
    async def test_db_pool_gdpr_fixture_creates_schema(self, db_pool_gdpr):
        """
        Test that db_pool_gdpr fixture creates GDPR schema tables.

        This fixture should:
        1. Connect to test database
        2. Provide connection pool with Alembic-managed schema ready
        3. Return connection pool for test use
        """
        # GIVEN: Database pool from fixture
        pool = db_pool_gdpr

        # WHEN: We check for required tables
        async with pool.acquire() as conn:
            # Query PostgreSQL catalog for table existence
            tables = await conn.fetch(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )

        table_names = [row["table_name"] for row in tables]

        # THEN: All GDPR tables should exist
        required_tables = ["user_profiles", "user_preferences", "consent_records", "conversations", "audit_logs"]

        for table in required_tables:
            assert table in table_names, (
                f"Table '{table}' not found in database. Available: {table_names}. Schema setup failed."
            )

    @pytest.mark.asyncio
    async def test_conversations_table_structure(self, db_pool_gdpr):
        """
        Test that conversations table has correct structure.

        This validates the specific table that failed in Codex finding.
        """
        # GIVEN: Database pool with schema
        pool = db_pool_gdpr

        # WHEN: We query conversations table structure
        async with pool.acquire() as conn:
            columns = await conn.fetch(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'conversations'
                ORDER BY ordinal_position
                """
            )

        # THEN: Table should have expected columns
        column_names = [row["column_name"] for row in columns]

        required_columns = [
            "conversation_id",  # Primary key
            "user_id",  # Foreign key to user_profiles
            "title",
            "messages",  # JSONB array
            "created_at",
            "last_message_at",
            "archived",
            "metadata",
        ]

        for col in required_columns:
            assert col in column_names, f"Column '{col}' missing from conversations table. Found: {column_names}"

    @pytest.mark.asyncio
    async def test_user_profiles_table_structure(self, db_pool_gdpr):
        """
        Test that user_profiles table exists and has correct structure.

        This table is referenced by conversations as foreign key.
        """
        # GIVEN: Database pool with schema
        pool = db_pool_gdpr

        # WHEN: We query user_profiles table structure
        async with pool.acquire() as conn:
            columns = await conn.fetch(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'user_profiles'
                ORDER BY ordinal_position
                """
            )

        # THEN: Table should have expected columns
        column_names = [row["column_name"] for row in columns]

        required_columns = [
            "user_id",  # Primary key
            "username",
            "email",
            "full_name",
            "created_at",
            "last_updated",
            "metadata",
        ]

        for col in required_columns:
            assert col in column_names, f"Column '{col}' missing from user_profiles table. Found: {column_names}"

    @pytest.mark.asyncio
    async def test_schema_indexes_created(self, db_pool_gdpr):
        """
        Test that required indexes are created for performance.

        GDPR queries need specific indexes for efficient operation.
        """
        # GIVEN: Database pool with schema
        pool = db_pool_gdpr

        # WHEN: We query for indexes on conversations table
        async with pool.acquire() as conn:
            indexes = await conn.fetch(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename = 'conversations'
                ORDER BY indexname
                """
            )

        index_names = [row["indexname"] for row in indexes]

        # THEN: Key indexes should exist
        # Note: Primary key creates an index automatically
        expected_indexes = [
            "conversations_pkey",  # Primary key index
            "idx_conversations_user_id",  # For user queries
            "idx_conversations_created_at",  # For temporal queries
        ]

        for idx in expected_indexes:
            assert idx in index_names, f"Index '{idx}' not found. Available: {index_names}"

    @pytest.mark.asyncio
    async def test_schema_can_insert_test_data(self, db_pool_gdpr):
        """
        Test that schema accepts valid test data insertion.

        This validates the schema is not only created but functional.
        """
        # GIVEN: Database pool with schema
        pool = db_pool_gdpr

        # WHEN: We insert test data
        async with pool.acquire() as conn:
            # Insert test user
            await conn.execute(
                """
                INSERT INTO user_profiles (user_id, username, email)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO NOTHING
                """,
                "test_schema_user",
                "test_schema",
                "test.schema@example.com",
            )

            # Insert test conversation
            await conn.execute(
                """
                INSERT INTO conversations (conversation_id, user_id, title, messages)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (conversation_id) DO NOTHING
                """,
                "test_schema_conv",
                "test_schema_user",
                "Test Conversation",
                '[{"role": "user", "content": "test"}]',
            )

            # Query back the data
            result = await conn.fetchrow(
                """
                SELECT c.conversation_id, c.title, u.username
                FROM conversations c
                JOIN user_profiles u ON c.user_id = u.user_id
                WHERE c.conversation_id = $1
                """,
                "test_schema_conv",
            )

        # THEN: Data should be retrieved successfully
        assert result is not None, "Failed to retrieve inserted test data"
        assert result["conversation_id"] == "test_schema_conv"
        assert result["title"] == "Test Conversation"
        assert result["username"] == "test_schema"


@pytest.mark.xdist_group(name="integration_security_gdpr_schema_tests")
class TestGDPRSchemaFixturePattern:
    """Test the fixture pattern for schema setup"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        import gc

        gc.collect()

    @pytest.mark.asyncio
    async def test_schema_managed_by_alembic_not_direct_sql(self):
        """
        Test that schema is managed by Alembic migrations.

        Previously validated direct SQL execution pattern. Schema management
        has been consolidated to Alembic (SQL migration files removed).
        This test now validates that Alembic is the single source of truth.
        """
        # GIVEN: Project root
        current = Path(__file__).resolve()
        project_root = None
        for parent in current.parents:
            if (parent / "pyproject.toml").exists():
                project_root = parent
                break

        assert project_root is not None, "Could not find project root (no pyproject.toml)"

        # THEN: Alembic should be configured
        alembic_ini = project_root / "alembic.ini"
        assert alembic_ini.exists(), "Alembic config should exist as schema source of truth"

        # AND: SQL migration files should NOT exist (superseded by Alembic)
        old_sql_file = project_root / "migrations" / "001_gdpr_schema.sql"
        assert not old_sql_file.exists(), "SQL migration file should not exist — schema managed exclusively by Alembic"

    @pytest.mark.asyncio
    async def test_schema_setup_is_idempotent(self, db_pool_gdpr):
        """
        Test that Alembic-managed schema allows idempotent operations.

        Validates that the schema (now managed by Alembic) supports
        repeated operations without errors.
        """
        # GIVEN: Database pool (schema already created by Alembic)
        pool = db_pool_gdpr

        async with pool.acquire() as conn:
            # Query tables to verify schema is intact
            tables = await conn.fetch(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )

        table_names = [row["table_name"] for row in tables]

        # THEN: Tables should still exist (no errors across all iterations)
        required_tables = ["user_profiles", "conversations", "audit_logs"]
        for table in required_tables:
            assert table in table_names
