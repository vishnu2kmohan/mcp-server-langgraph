"""
Integration Tests for pgvector Extension Availability

Verifies that the pgvector extension is properly installed and available
in the test PostgreSQL database (TimescaleDB 2.17.2-pg16).

TDD Approach:
- RED: Tests fail if pgvector extension not enabled in init script
- GREEN: Tests pass after adding pgvector to init-test-databases.sh
- REFACTOR: Optimize extension loading

Phase 1: pgvector Test Image (Dockerfile.test)
- TimescaleDB 2.17.2-pg16 includes pgvector as bundled extension
- Init script must CREATE EXTENSION vector in agent_studio_test database
"""

import gc

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.pgvector]


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="testpgvectorextension")
@pytest.mark.skip_isolation_check  # Uses worker-scoped Postgres schemas for isolation
class TestPgVectorExtension:
    """
    Test pgvector extension availability in test database.

    TDD: RED phase - These tests will fail without pgvector extension enabled.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_pgvector_extension_available(self, postgres_connection_clean):
        """
        TDD RED: Verify pgvector extension is installed and available.

        This test will fail if pgvector extension is not created in
        docker/postgres/init-test-databases.sh.
        """
        # Query for pgvector extension
        result = await postgres_connection_clean.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
            )
            """
        )
        assert result is True, (
            "pgvector extension not found. Ensure docker/postgres/init-test-databases.sh creates the extension."
        )

    async def test_vector_type_available(self, postgres_connection_clean):
        """
        TDD RED: Verify vector data type is available for use.

        Tests that we can create a table with vector(768) column,
        matching the embedding dimension used by the application.
        """
        from mcp_server_langgraph.core.constants import EMBEDDING_DIM

        # Create a test table with vector column
        await postgres_connection_clean.execute(
            f"""
            CREATE TABLE IF NOT EXISTS test_vector_type (
                id SERIAL PRIMARY KEY,
                embedding vector({EMBEDDING_DIM})
            )
            """
        )

        # Insert a test vector
        test_vector = "[" + ",".join(["0.1"] * EMBEDDING_DIM) + "]"
        await postgres_connection_clean.execute(
            f"""
            INSERT INTO test_vector_type (embedding)
            VALUES ('{test_vector}'::vector)
            """
        )

        # Verify the vector was stored correctly
        result = await postgres_connection_clean.fetchval("SELECT vector_dims(embedding) FROM test_vector_type LIMIT 1")
        assert result == EMBEDDING_DIM, f"Expected vector dimension {EMBEDDING_DIM}, got {result}"

        # Cleanup
        await postgres_connection_clean.execute("DROP TABLE test_vector_type")

    async def test_vector_similarity_search(self, postgres_connection_clean):
        """
        TDD RED: Verify vector similarity search works.

        Tests cosine distance operator (<=> ) for similarity search,
        which is used by plan template semantic search.
        """
        # Create test table with sample vectors
        await postgres_connection_clean.execute(
            """
            CREATE TABLE IF NOT EXISTS test_similarity (
                id SERIAL PRIMARY KEY,
                name TEXT,
                embedding vector(3)
            )
            """
        )

        # Insert sample vectors
        await postgres_connection_clean.execute(
            """
            INSERT INTO test_similarity (name, embedding) VALUES
            ('similar', '[1, 0, 0]'),
            ('different', '[0, 1, 0]'),
            ('orthogonal', '[0, 0, 1]')
            """
        )

        # Search for vectors similar to [1, 0, 0]
        results = await postgres_connection_clean.fetch(
            """
            SELECT name, embedding <=> '[1, 0, 0]' AS distance
            FROM test_similarity
            ORDER BY distance
            LIMIT 3
            """
        )

        # 'similar' should be first (distance 0)
        assert results[0]["name"] == "similar"
        assert results[0]["distance"] == 0.0

        # Cleanup
        await postgres_connection_clean.execute("DROP TABLE test_similarity")

    async def test_ivfflat_index_creation(self, postgres_connection_clean):
        """
        TDD RED: Verify IVFFlat index can be created for vector columns.

        IVFFlat indexes are used for approximate nearest neighbor search
        on execution plan and template embeddings.
        """
        # Create table with vector column
        await postgres_connection_clean.execute(
            """
            CREATE TABLE IF NOT EXISTS test_ivfflat (
                id SERIAL PRIMARY KEY,
                embedding vector(128)
            )
            """
        )

        # Insert enough rows for IVFFlat (requires at least lists^2 rows)
        # Using lists=10, so need at least 100 rows
        for i in range(100):
            vector_vals = [str(float(i % 10) / 10)] * 128
            vector_str = "[" + ",".join(vector_vals) + "]"
            await postgres_connection_clean.execute(f"INSERT INTO test_ivfflat (embedding) VALUES ('{vector_str}'::vector)")

        # Create IVFFlat index with cosine distance
        await postgres_connection_clean.execute(
            """
            CREATE INDEX IF NOT EXISTS test_ivfflat_idx
            ON test_ivfflat
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 10)
            """
        )

        # Verify index was created
        result = await postgres_connection_clean.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM pg_indexes
                WHERE indexname = 'test_ivfflat_idx'
            )
            """
        )
        assert result is True, "IVFFlat index creation failed"

        # Cleanup
        await postgres_connection_clean.execute("DROP TABLE test_ivfflat")
