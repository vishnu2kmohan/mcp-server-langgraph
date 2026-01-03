"""
Vector Search Provider Base

Abstract base class for vector search providers.
Implementations must support:
- upsert: Insert or update vectors with metadata
- search: Find similar vectors with optional filters
- delete: Remove vectors by ID

Provider implementations:
- InMemoryVectorProvider: For testing
- PgVectorProvider: PostgreSQL pgvector extension
- QdrantProvider: Qdrant vector database
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VectorSearchResult:
    """Result from vector similarity search.

    Attributes:
        id: Unique identifier of the matching document
        score: Similarity score (0-1, higher is more similar)
        metadata: Associated metadata for the document
    """

    id: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorSearchProvider(ABC):
    """Abstract base class for vector search providers.

    Implementations provide vector storage and similarity search
    capabilities with optional metadata filtering.
    """

    @abstractmethod
    async def upsert(
        self,
        collection: str,
        id: str,
        vector: list[float],
        metadata: dict[str, Any],
    ) -> None:
        """Insert or update a vector with metadata.

        If a vector with the same ID exists, it will be replaced.

        Args:
            collection: Collection/namespace name
            id: Unique identifier for the vector
            vector: Vector embedding (list of floats)
            metadata: Key-value metadata to store with the vector
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def delete(self, collection: str, id: str) -> None:
        """Delete a vector by ID.

        Args:
            collection: Collection containing the vector
            id: ID of the vector to delete
        """
        pass
