"""
In-Memory Vector Provider

Testing implementation of VectorSearchProvider.
Uses cosine similarity for vector comparison.

Note: This is for testing only. Production should use
pgvector or Qdrant for scalability and persistence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from mcp_server_langgraph.storage.vectors.base import (
    VectorSearchProvider,
    VectorSearchResult,
)


@dataclass
class StoredVector:
    """Internal representation of a stored vector."""

    id: str
    vector: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score (0-1 for normalized vectors)
    """
    if len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=True))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


class InMemoryVectorProvider(VectorSearchProvider):
    """In-memory vector provider for testing.

    Stores vectors in a dict keyed by (collection, id).
    Uses cosine similarity for search.
    """

    def __init__(self) -> None:
        """Initialize empty vector storage."""
        # Key: (collection, id) -> StoredVector
        self._vectors: dict[tuple[str, str], StoredVector] = {}

    async def upsert(
        self,
        collection: str,
        id: str,
        vector: list[float],
        metadata: dict[str, Any],
    ) -> None:
        """Insert or update a vector with metadata."""
        key = (collection, id)
        self._vectors[key] = StoredVector(id=id, vector=vector, metadata=metadata)

    async def search(
        self,
        collection: str,
        query_vector: list[float],
        limit: int = 10,
        min_score: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Search for similar vectors using cosine similarity."""
        results: list[tuple[float, StoredVector]] = []

        for (coll, _), stored in self._vectors.items():
            if coll != collection:
                continue

            # Apply metadata filters
            if filters:
                if not self._matches_filters(stored.metadata, filters):
                    continue

            # Calculate similarity
            score = _cosine_similarity(query_vector, stored.vector)

            if score >= min_score:
                results.append((score, stored))

        # Sort by score descending
        results.sort(key=lambda x: x[0], reverse=True)

        # Limit and convert to VectorSearchResult
        return [
            VectorSearchResult(
                id=stored.id,
                score=score,
                metadata=stored.metadata.copy(),
            )
            for score, stored in results[:limit]
        ]

    async def delete(self, collection: str, id: str) -> None:
        """Delete a vector by ID."""
        key = (collection, id)
        self._vectors.pop(key, None)

    def _matches_filters(self, metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
        """Check if metadata matches all filters (exact match)."""
        return all(metadata.get(key) == value for key, value in filters.items())

    def clear(self) -> None:
        """Clear all stored vectors (testing utility)."""
        self._vectors.clear()
