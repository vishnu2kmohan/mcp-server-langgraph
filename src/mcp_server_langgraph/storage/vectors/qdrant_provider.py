"""
Qdrant Vector Provider

Qdrant implementation of VectorSearchProvider.
Provides scalable vector similarity search using Qdrant vector database.

Features:
- High-performance vector similarity search
- Metadata filtering via Qdrant Filter API
- Collection-based namespacing
- Supports async operations via qdrant-client
- Automatic conversion of string IDs to valid UUIDs

Requirements:
- qdrant-client>=1.16.1

Note: This provider is optional. If qdrant dependencies are not
available, the factory will fallback to InMemoryVectorProvider.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any, Protocol

from mcp_server_langgraph.storage.vectors.base import (
    VectorSearchProvider,
    VectorSearchResult,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Namespace UUID for deterministic ID generation
# Using a fixed namespace ensures consistent ID conversion across restarts
QDRANT_ID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def string_to_qdrant_id(id_string: str) -> str:
    """Convert an arbitrary string ID to a valid Qdrant point ID.

    Qdrant requires point IDs to be either:
    - Unsigned 64-bit integers
    - Valid UUID strings

    This function converts arbitrary string IDs to valid UUIDs using
    UUID5 (deterministic, namespace-based hashing). If the input is
    already a valid UUID, it is returned unchanged.

    Args:
        id_string: Arbitrary string identifier

    Returns:
        Valid UUID string for use as Qdrant point ID

    Examples:
        >>> string_to_qdrant_id("skill-001")
        'a1b2c3d4-...'  # Deterministic UUID5 hash

        >>> string_to_qdrant_id("550e8400-e29b-41d4-a716-446655440000")
        '550e8400-e29b-41d4-a716-446655440000'  # Preserved
    """
    # Check if already a valid UUID
    try:
        parsed = uuid.UUID(id_string)
        return str(parsed)
    except (ValueError, AttributeError):
        pass

    # Convert to UUID5 using namespace (deterministic)
    generated = uuid.uuid5(QDRANT_ID_NAMESPACE, id_string)
    return str(generated)


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

    async def query_points(
        self,
        collection_name: str,
        query: list[float],
        limit: int,
        query_filter: Any | None = None,
        score_threshold: float | None = None,
        **kwargs: Any,
    ) -> Any:
        """Query points using vector similarity (qdrant-client >= 1.7 API)."""
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
            id: Unique identifier for the vector (arbitrary string, converted to UUID)
            vector: Vector embedding (list of floats)
            metadata: Key-value metadata to store with the vector

        Note:
            Qdrant requires point IDs to be valid UUIDs or unsigned integers.
            This method automatically converts arbitrary string IDs to UUIDs
            using deterministic UUID5 hashing.
        """
        try:
            # Import Qdrant types lazily to allow graceful degradation
            from qdrant_client.models import PointStruct

            # Convert string ID to valid Qdrant point ID (UUID)
            qdrant_id = string_to_qdrant_id(id)

            # Store original ID in payload for retrieval
            # Use copy to avoid mutating caller's metadata
            payload = {**metadata, "_original_id": id}

            point = PointStruct(
                id=qdrant_id,
                vector=vector,
                payload=payload,
            )

            await self._client.upsert(
                collection_name=collection,
                points=[point],
            )

            logger.debug(
                "Upserted vector to Qdrant",
                extra={"collection": collection, "id": id, "qdrant_id": qdrant_id},
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

            # Search Qdrant using query_points (qdrant-client >= 1.7)
            response = await self._client.query_points(
                collection_name=collection,
                query=query_vector,
                limit=limit,
                query_filter=query_filter,
                score_threshold=min_score if min_score > 0 else None,
            )
            results = response.points

            # Convert to VectorSearchResult
            # Extract original ID from payload if present, otherwise use Qdrant point ID
            search_results = []
            for hit in results:
                payload = dict(hit.payload) if hit.payload else {}
                # Use original ID if stored, otherwise fall back to Qdrant point ID
                original_id = payload.pop("_original_id", str(hit.id))
                search_results.append(
                    VectorSearchResult(
                        id=original_id,
                        score=hit.score,
                        metadata=payload,
                    )
                )
            return search_results

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
            id: ID of the vector to delete (arbitrary string, converted to UUID)

        Note:
            Qdrant requires point IDs to be valid UUIDs or unsigned integers.
            This method automatically converts arbitrary string IDs to UUIDs
            using deterministic UUID5 hashing.
        """
        try:
            from qdrant_client.models import PointIdsList

            # Convert string ID to valid Qdrant point ID (UUID)
            qdrant_id = string_to_qdrant_id(id)

            await self._client.delete(
                collection_name=collection,
                points_selector=PointIdsList(points=[qdrant_id]),
            )

            logger.debug(
                "Deleted vector from Qdrant",
                extra={"collection": collection, "id": id, "qdrant_id": qdrant_id},
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
