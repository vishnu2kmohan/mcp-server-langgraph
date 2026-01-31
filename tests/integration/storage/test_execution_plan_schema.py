"""
Integration Tests for Execution Plan Schema

Verifies that the execution_plans table has all required columns
including user_id and created_by for GDPR compliance and ownership tracking.

TDD Approach:
- RED: Tests fail if columns are missing
- GREEN: Tests pass after migration adds columns
- REFACTOR: Optimize schema

Phase 2: Fix Embeddings Schema
- Add user_id column to execution_plans for GDPR user filtering
- Add created_by column to execution_plans matching PlanTemplate pattern
"""

import gc

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.schema]


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="testexecutionplanschema")
@pytest.mark.skip_isolation_check  # Uses worker-scoped Postgres schemas for isolation
class TestExecutionPlanSchema:
    """
    Test execution_plans table schema completeness.

    TDD: RED phase - These tests will fail without the schema migration.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_user_id_column_exists(self, postgres_connection_clean):
        """
        TDD RED: Verify user_id column exists in execution_plans.

        user_id is required for:
        - GDPR export (filter by user)
        - GDPR deletion (cascade delete)
        - Multi-tenant access control
        """
        result = await postgres_connection_clean.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'execution_plans'
                AND column_name = 'user_id'
            )
            """
        )
        assert result is True, "user_id column not found in execution_plans. Run migration to add user_id for GDPR compliance."

    async def test_created_by_column_exists(self, postgres_connection_clean):
        """
        TDD RED: Verify created_by column exists in execution_plans.

        created_by is required for:
        - Plan ownership tracking
        - Audit trail consistency with PlanTemplate pattern
        """
        result = await postgres_connection_clean.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'execution_plans'
                AND column_name = 'created_by'
            )
            """
        )
        assert result is True, (
            "created_by column not found in execution_plans. Run migration to add created_by for ownership tracking."
        )

    async def test_description_embedding_is_vector_type(self, postgres_connection_clean):
        """
        TDD RED: Verify description_embedding is proper vector(768) type.

        The embedding column must be vector type (not float array)
        for pgvector similarity search.
        """
        result = await postgres_connection_clean.fetchrow(
            """
            SELECT data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'execution_plans'
            AND column_name = 'description_embedding'
            """
        )
        assert result is not None, "description_embedding column not found"
        assert result["udt_name"] == "vector", (
            f"description_embedding should be vector type, got {result['udt_name']}. "
            "Run migration to convert float array to vector(768)."
        )

    async def test_user_id_has_index(self, postgres_connection_clean):
        """
        TDD RED: Verify user_id column is indexed for GDPR queries.

        Index required for efficient:
        - GDPR export by user
        - GDPR deletion by user
        """
        result = await postgres_connection_clean.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'execution_plans'
                AND indexdef LIKE '%user_id%'
            )
            """
        )
        assert result is True, "user_id index not found in execution_plans. Add index for efficient GDPR queries."

    async def test_embedding_status_columns_exist(self, postgres_connection_clean):
        """
        TDD RED: Verify embedding status tracking columns exist.

        Required for Phase 7.25 self-healing embedding service:
        - embedding_status: pending|processing|completed|failed
        - embedding_error: Error reason if failed
        - embedding_failed_at: Timestamp of last failure
        """
        columns = ["embedding_status", "embedding_error", "embedding_failed_at"]
        for column_name in columns:
            result = await postgres_connection_clean.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'execution_plans'
                    AND column_name = $1
                )
                """,
                column_name,
            )
            assert result is True, (
                f"{column_name} column not found in execution_plans. Run migration to add embedding status tracking columns."
            )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="testplantemplatesschema")
@pytest.mark.skip_isolation_check  # Uses worker-scoped Postgres schemas for isolation
class TestPlanTemplateSchema:
    """
    Test plan_templates table schema completeness.

    Verify embedding status columns for self-healing service.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_embedding_status_columns_exist(self, postgres_connection_clean):
        """
        TDD RED: Verify embedding status tracking columns exist.

        Required for Phase 7.25 self-healing embedding service:
        - embedding_status: pending|processing|completed|failed
        - embedding_error: Error reason if failed
        - embedding_failed_at: Timestamp of last failure
        """
        columns = ["embedding_status", "embedding_error", "embedding_failed_at"]
        for column_name in columns:
            result = await postgres_connection_clean.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'plan_templates'
                    AND column_name = $1
                )
                """,
                column_name,
            )
            assert result is True, (
                f"{column_name} column not found in plan_templates. Run migration to add embedding status tracking columns."
            )

    async def test_description_embedding_is_vector_type(self, postgres_connection_clean):
        """
        TDD RED: Verify description_embedding is proper vector(768) type.
        """
        result = await postgres_connection_clean.fetchrow(
            """
            SELECT data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'plan_templates'
            AND column_name = 'description_embedding'
            """
        )
        assert result is not None, "description_embedding column not found"
        assert result["udt_name"] == "vector", (
            f"description_embedding should be vector type, got {result['udt_name']}. "
            "Run migration to convert float array to vector(768)."
        )
