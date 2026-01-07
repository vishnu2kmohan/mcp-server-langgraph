"""
PgVector Provider

PostgreSQL pgvector extension implementation of VectorSearchProvider.
Provides vector similarity search using PostgreSQL's pgvector extension.

Features:
- Uses existing PostgreSQL connection pool
- Cosine similarity search
- Metadata filtering via JSONB
- Collection-based namespacing

Requirements:
- PostgreSQL with pgvector extension enabled
- asyncpg connection pool

Note: This provider is optional. If pgvector dependencies are not
available, the factory will fallback to InMemoryVectorProvider.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Protocol

from mcp_server_langgraph.storage.vectors.base import (
    VectorSearchProvider,
    VectorSearchResult,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ConnectionPoolProtocol(Protocol):
    """Protocol for async connection pool (asyncpg compatible)."""

    def acquire(self) -> Any:
        """Acquire a connection from the pool."""
        ...


class PgVectorProvider(VectorSearchProvider):
    """PostgreSQL pgvector implementation of VectorSearchProvider.

    Uses pgvector extension for vector similarity search.
    Stores vectors in a table with JSONB metadata support.
    """

    def __init__(
        self,
        connection_pool: ConnectionPoolProtocol,
        table_prefix: str = "vector_store",
    ) -> None:
        """Initialize PgVector provider.

        Args:
            connection_pool: asyncpg connection pool
            table_prefix: Prefix for vector storage tables
        """
        self._pool = connection_pool
        self._table_prefix = table_prefix

    def _table_name(self, collection: str) -> str:
        """Get table name for a collection.

        Args:
            collection: Collection name

        Returns:
            Fully qualified table name
        """
        # Sanitize collection name to prevent SQL injection
        safe_collection = "".join(c for c in collection if c.isalnum() or c == "_")
        return f"{self._table_prefix}_{safe_collection}"

    async def _ensure_table(self, collection: str) -> None:
        """Ensure table exists for collection.

        Args:
            collection: Collection name
        """
        table = self._table_name(collection)
        async with self._pool.acquire() as conn:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id TEXT PRIMARY KEY,
                    vector vector,
                    metadata JSONB DEFAULT '{{}}'::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            # Create index for similarity search
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS {table}_vector_idx
                ON {table}
                USING ivfflat (vector vector_cosine_ops)
                WITH (lists = 100)
            """)

    async def upsert(
        self,
        collection: str,
        id: str,
        vector: list[float],
        metadata: dict[str, Any],
    ) -> None:
        """Insert or update a vector with metadata.

        Args:
            collection: Collection/namespace name
            id: Unique identifier for the vector
            vector: Vector embedding (list of floats)
            metadata: Key-value metadata to store with the vector
        """
        try:
            await self._ensure_table(collection)
            table = self._table_name(collection)

            # Convert vector to pgvector format
            vector_str = f"[{','.join(str(v) for v in vector)}]"
            metadata_json = json.dumps(metadata)

            async with self._pool.acquire() as conn:
                # S608: table name comes from internal config, not user input
                await conn.execute(
                    f"""
                    INSERT INTO {table} (id, vector, metadata)
                    VALUES ($1, $2::vector, $3::jsonb)
                    ON CONFLICT (id) DO UPDATE SET
                        vector = EXCLUDED.vector,
                        metadata = EXCLUDED.metadata
                    """,  # noqa: S608
                    id,
                    vector_str,
                    metadata_json,
                )

            logger.debug(
                "Upserted vector",
                extra={"collection": collection, "id": id},
            )

        except Exception as e:
            logger.exception(
                "Failed to upsert vector",
                extra={"collection": collection, "id": id, "error": str(e)},
            )
            raise

    async def search(
        self,
        collection: str,
        query_vector: list[float],
        limit: int = 10,
        min_score: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Search for similar vectors using cosine similarity.

        Args:
            collection: Collection/namespace to search
            query_vector: Query vector for similarity comparison
            limit: Maximum number of results to return
            min_score: Minimum similarity score threshold (0-1)
            filters: Optional metadata filters (exact match)

        Returns:
            List of VectorSearchResult sorted by similarity (descending)
        """
        try:
            table = self._table_name(collection)

            # Build filter clause
            filter_clause = ""
            filter_values: list[Any] = []

            if filters:
                conditions = []
                for key, value in filters.items():
                    filter_values.append(json.dumps(value))
                    param_idx = len(filter_values) + 1
                    conditions.append(f"metadata->>'{key}' = ${param_idx}")
                if conditions:
                    filter_clause = "WHERE " + " AND ".join(conditions)

            # Convert query vector to pgvector format
            vector_str = f"[{','.join(str(v) for v in query_vector)}]"

            # Build query with cosine similarity
            # Note: pgvector uses <=> for cosine distance, we convert to similarity
            # S608: table name comes from internal config, not user input
            query = f"""
                SELECT
                    id,
                    1 - (vector <=> $1::vector) as score,
                    metadata
                FROM {table}
                {filter_clause}
                ORDER BY vector <=> $1::vector
                LIMIT ${2 + len(filter_values)}
            """  # noqa: S608

            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    query,
                    vector_str,
                    *filter_values,
                    limit,
                )

            results = []
            for row in rows:
                score = float(row["score"])
                if score >= min_score:
                    metadata = row["metadata"]
                    if isinstance(metadata, str):
                        metadata = json.loads(metadata)
                    results.append(
                        VectorSearchResult(
                            id=row["id"],
                            score=score,
                            metadata=metadata or {},
                        )
                    )

            return results

        except Exception as e:
            logger.exception(
                "Failed to search vectors",
                extra={"collection": collection, "error": str(e)},
            )
            return []

    async def delete(self, collection: str, id: str) -> None:
        """Delete a vector by ID.

        Args:
            collection: Collection containing the vector
            id: ID of the vector to delete
        """
        try:
            table = self._table_name(collection)

            async with self._pool.acquire() as conn:
                # S608: table name comes from internal config, not user input
                await conn.execute(
                    f"DELETE FROM {table} WHERE id = $1",  # noqa: S608
                    id,
                )

            logger.debug(
                "Deleted vector",
                extra={"collection": collection, "id": id},
            )

        except Exception as e:
            logger.exception(
                "Failed to delete vector",
                extra={"collection": collection, "id": id, "error": str(e)},
            )
            raise
