"""
Qdrant Vector Service for Artifacts.

Provides vector-based operations for artifacts:
- Embedding generation and indexing
- Semantic search across artifacts
- Similar artifact discovery
- AI-powered recommendations

Features:
- User-scoped vector queries (security)
- Graceful degradation on failures
- Metadata storage for retrieval
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


class EmbedderProtocol(Protocol):
    """Protocol for embedding services."""

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        ...


class QdrantClientProtocol(Protocol):
    """Protocol for Qdrant client operations."""

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

    async def retrieve(
        self,
        collection_name: str,
        ids: list[str],
        with_vectors: bool = True,
        **kwargs: Any,
    ) -> list[Any]:
        """Retrieve points by IDs."""
        ...

    async def delete(
        self,
        collection_name: str,
        points_selector: Any,
        **kwargs: Any,
    ) -> Any:
        """Delete points from collection."""
        ...


class QdrantArtifactVectorService:
    """
    Vector service for artifact semantic operations.

    Uses Qdrant for vector storage and similarity search.
    """

    def __init__(
        self,
        client: QdrantClientProtocol,
        embedder: EmbedderProtocol,
        collection: str = "artifacts",
    ) -> None:
        """
        Initialize vector service.

        Args:
            client: Qdrant client
            embedder: Embedding service
            collection: Qdrant collection name
        """
        self._client = client
        self._embedder = embedder
        self._collection = collection

    async def index(
        self,
        artifact: dict[str, Any],
        user_id: str,
    ) -> bool:
        """
        Index artifact as vector.

        Args:
            artifact: Artifact dictionary with content
            user_id: User ID for filtering

        Returns:
            True if indexed successfully, False otherwise
        """
        artifact_id = artifact.get("id")
        content = artifact.get("content", "")

        try:
            # Generate embedding
            embedding = await self._embedder.embed(content)

            # Prepare payload (metadata)
            payload = {
                "artifact_id": artifact_id,
                "user_id": user_id,
                "title": artifact.get("title", ""),
                "type": artifact.get("type", "code"),
                "content_type": artifact.get("content_type", "code"),
            }

            # Create point for upsert
            point = {
                "id": artifact_id,
                "vector": embedding,
                "payload": payload,
            }

            # Upsert to Qdrant
            await self._client.upsert(
                collection_name=self._collection,
                points=[point],
                payload=payload,
            )

            logger.info(
                "Indexed artifact vector",
                extra={"artifact_id": artifact_id, "user_id": user_id},
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to index artifact vector",
                extra={"artifact_id": artifact_id, "error": str(e)},
            )
            return False

    async def search(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Semantic search for artifacts.

        Args:
            query: Search query
            user_id: User ID (for filtering)
            limit: Max results

        Returns:
            List of search results with scores
        """
        try:
            # Generate query embedding
            query_embedding = await self._embedder.embed(query)

            # Build user filter for security
            user_filter = {"must": [{"key": "user_id", "match": {"value": user_id}}]}

            # Search Qdrant
            results = await self._client.search(
                collection_name=self._collection,
                query_vector=query_embedding,
                limit=limit,
                query_filter=user_filter,
                filter=user_filter,
            )

            # Format results
            return [
                {
                    "artifact_id": result.payload.get("artifact_id"),
                    "title": result.payload.get("title"),
                    "type": result.payload.get("type"),
                    "score": result.score,
                }
                for result in results
            ]

        except Exception as e:
            logger.error(
                "Failed to search artifact vectors",
                extra={"query": query[:50], "error": str(e)},
            )
            return []

    async def find_similar(
        self,
        artifact_id: str,
        user_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Find artifacts similar to a given artifact.

        Args:
            artifact_id: Source artifact ID
            user_id: User ID (for filtering)
            limit: Max results

        Returns:
            List of similar artifacts
        """
        try:
            # Retrieve existing embedding
            points = await self._client.retrieve(
                collection_name=self._collection,
                ids=[artifact_id],
                with_vectors=True,
            )

            if not points:
                logger.warning(
                    "Artifact not found in vector store",
                    extra={"artifact_id": artifact_id},
                )
                return []

            # Use existing embedding for search
            embedding = points[0].vector

            # Build user filter
            user_filter = {"must": [{"key": "user_id", "match": {"value": user_id}}]}

            # Search for similar (request more to filter source)
            results = await self._client.search(
                collection_name=self._collection,
                query_vector=embedding,
                limit=limit + 1,  # Extra to filter source
                query_filter=user_filter,
                filter=user_filter,
            )

            # Exclude source artifact from results
            return [
                {
                    "artifact_id": result.payload.get("artifact_id"),
                    "title": result.payload.get("title"),
                    "type": result.payload.get("type"),
                    "score": result.score,
                }
                for result in results
                if result.payload.get("artifact_id") != artifact_id
            ][:limit]

        except Exception as e:
            logger.error(
                "Failed to find similar artifacts",
                extra={"artifact_id": artifact_id, "error": str(e)},
            )
            return []

    async def delete(self, artifact_id: str) -> bool:
        """
        Delete artifact vector from Qdrant.

        Args:
            artifact_id: Artifact ID

        Returns:
            True if deleted, False otherwise
        """
        try:
            # Delete by point ID
            await self._client.delete(
                collection_name=self._collection,
                points_selector={"points": [artifact_id]},
            )

            logger.info(
                "Deleted artifact vector",
                extra={"artifact_id": artifact_id},
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to delete artifact vector",
                extra={"artifact_id": artifact_id, "error": str(e)},
            )
            return False
