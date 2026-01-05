"""SkillSearchTool for semantic skill discovery.

Provides vector-based semantic search for skill discovery:
- Index skills with embeddings
- Search by natural language query
- Filter by scope and minimum score

This integrates with the existing vector infrastructure (Qdrant/pgvector/in-memory)
to enable progressive skill loading based on semantic relevance.

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from mcp_server_langgraph.skills.models import Skill


class EmbeddingServiceProtocol(Protocol):
    """Protocol for embedding services."""

    async def embed(self, text: str) -> list[float]:
        """Embed text into a vector."""
        ...


class VectorProviderProtocol(Protocol):
    """Protocol for vector search providers."""

    async def upsert(
        self,
        *,
        collection: str,
        id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Upsert a vector into the collection."""
        ...

    async def search(
        self,
        *,
        collection: str,
        query_vector: list[float],
        limit: int = 10,
        min_score: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors."""
        ...


@dataclass
class SkillSearchResult:
    """Result from skill search.

    Attributes:
        skill_id: Unique identifier of the skill
        name: Name of the skill
        description: Description of the skill
        score: Similarity score (0-1)
        tags: Optional list of tags
    """

    skill_id: str
    name: str
    description: str
    score: float
    tags: list[str] | None = None


class SkillSearchTool:
    """Semantic skill discovery via vector similarity.

    Uses embeddings to index skills and find semantically similar
    skills based on natural language queries.

    Attributes:
        COLLECTION: Name of the vector collection for skills
        vector_provider: Provider for vector storage and search
        embedding_service: Service for generating embeddings
    """

    COLLECTION: str = "skills"

    def __init__(
        self,
        vector_provider: VectorProviderProtocol,
        embedding_service: EmbeddingServiceProtocol | None = None,
    ) -> None:
        """Initialize the SkillSearchTool.

        Args:
            vector_provider: Provider for vector storage and search
            embedding_service: Optional service for generating embeddings
        """
        self._vector_provider = vector_provider
        self._embedding_service = embedding_service

    @property
    def vector_provider(self) -> VectorProviderProtocol:
        """Get the vector provider."""
        return self._vector_provider

    @property
    def embedding_service(self) -> EmbeddingServiceProtocol | None:
        """Get the embedding service."""
        return self._embedding_service

    async def index_skill(self, skill: Skill, *, skill_id: str) -> None:
        """Index a skill for semantic search.

        Args:
            skill: The skill to index
            skill_id: Unique identifier for the skill
        """
        if self._embedding_service is None:
            raise ValueError("Embedding service required for indexing")

        # Combine name and description for rich embedding
        text = f"{skill.name}: {skill.description}"
        vector = await self._embedding_service.embed(text)

        metadata: dict[str, Any] = {
            "name": skill.name,
            "description": skill.description,
        }
        if skill.tags:
            metadata["tags"] = skill.tags

        await self._vector_provider.upsert(
            collection=self.COLLECTION,
            id=skill_id,
            vector=vector,
            metadata=metadata,
        )

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> list[SkillSearchResult]:
        """Find skills matching a natural language query.

        Args:
            query: Natural language search query
            limit: Maximum number of results to return
            min_score: Minimum similarity score (0-1)

        Returns:
            List of SkillSearchResult ordered by relevance
        """
        if self._embedding_service is None:
            raise ValueError("Embedding service required for search")

        query_vector = await self._embedding_service.embed(query)

        results = await self._vector_provider.search(
            collection=self.COLLECTION,
            query_vector=query_vector,
            limit=limit,
            min_score=min_score,
        )

        return [
            SkillSearchResult(
                skill_id=result.get("id", ""),
                name=result.get("metadata", {}).get("name", ""),
                description=result.get("metadata", {}).get("description", ""),
                score=result.get("score", 0.0),
                tags=result.get("metadata", {}).get("tags"),
            )
            for result in results
        ]
