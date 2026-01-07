"""
Qdrant Vector Provider

Qdrant implementation of VectorSearchProvider.
Provides scalable vector similarity search using Qdrant vector database.

Features:
- High-performance vector similarity search
- Metadata filtering via Qdrant Filter API
- Collection-based namespacing
- Supports async operations via qdrant-client

Requirements:
- qdrant-client>=1.16.1

Note: This provider is optional. If qdrant dependencies are not
available, the factory will fallback to InMemoryVectorProvider.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol

from mcp_server_langgraph.storage.vectors.base import (
    VectorSearchProvider,
    VectorSearchResult,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class QdrantClientProtocol(Protocol):
    """Protocol for Qdrant client operations (async compatible)."""

    async def upsert(
        self,
        collection_name: str,
        points: list[Any],
        **kwargs: Any,
    ) -> Any:
        """Upsert points to collection."""
        ...

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int,
        query_filter: Any | None = None,
        **kwargs: Any,
    ) -> list[Any]:
        """Search for similar vectors."""
        ...

    async def delete(
        self,
        collection_name: str,
        points_selector: Any,
        **kwargs: Any,
    ) -> Any:
        """Delete points from collection."""
        ...


class QdrantVectorProvider(VectorSearchProvider):
    """Qdrant implementation of VectorSearchProvider.

    Uses Qdrant vector database for scalable similarity search.
    """

    def __init__(
        self,
        client: QdrantClientProtocol,
        vector_size: int = 768,
    ) -> None:
        """Initialize Qdrant provider.

        Args:
            client: Qdrant async client
            vector_size: Dimension of vectors (default: 768 for common embeddings)
        """
        self._client = client
        self._vector_size = vector_size

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
            # Import Qdrant types lazily to allow graceful degradation
            from qdrant_client.models import PointStruct

            point = PointStruct(
                id=id,
                vector=vector,
                payload=metadata,
            )

            await self._client.upsert(
                collection_name=collection,
                points=[point],
            )

            logger.debug(
                "Upserted vector to Qdrant",
                extra={"collection": collection, "id": id},
            )

        except ImportError as e:
            logger.exception("qdrant-client not available: %s", e)
            raise
        except Exception as e:
            logger.exception(
                "Failed to upsert vector to Qdrant",
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
        """Search for similar vectors.

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
            # Build filter if provided
            query_filter = None
            if filters:
                from qdrant_client.models import FieldCondition, Filter, MatchValue

                conditions = [
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value),
                    )
                    for key, value in filters.items()
                ]
                query_filter = Filter(must=conditions)  # type: ignore[arg-type]

            # Search Qdrant
            results = await self._client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=limit,
                query_filter=query_filter,
                score_threshold=min_score if min_score > 0 else None,
            )

            # Convert to VectorSearchResult
            return [
                VectorSearchResult(
                    id=str(hit.id),
                    score=hit.score,
                    metadata=dict(hit.payload) if hit.payload else {},
                )
                for hit in results
            ]

        except ImportError as e:
            logger.exception("qdrant-client not available: %s", e)
            return []
        except Exception as e:
            logger.exception(
                "Failed to search Qdrant",
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
            from qdrant_client.models import PointIdsList

            await self._client.delete(
                collection_name=collection,
                points_selector=PointIdsList(points=[id]),
            )

            logger.debug(
                "Deleted vector from Qdrant",
                extra={"collection": collection, "id": id},
            )

        except ImportError as e:
            logger.exception("qdrant-client not available: %s", e)
            raise
        except Exception as e:
            logger.exception(
                "Failed to delete vector from Qdrant",
                extra={"collection": collection, "id": id, "error": str(e)},
            )
            raise
