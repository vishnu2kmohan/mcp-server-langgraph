"""Adapters for connecting SkillSearchTool to shared infrastructure.

These adapters bridge the protocol-based interfaces used by SkillSearchTool
to the concrete implementations in the storage/vectors and core modules.

Adapters:
- VectorProviderAdapter: Wraps VectorSearchProvider to implement VectorProviderProtocol
- EmbeddingServiceAdapter: Wraps LangChain Embeddings to implement EmbeddingServiceProtocol

Factory:
- create_skill_search_tool: Creates SkillSearchTool with configured adapters

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings

    from mcp_server_langgraph.skills.search import SkillSearchTool
    from mcp_server_langgraph.storage.vectors.base import VectorSearchProvider


logger = logging.getLogger(__name__)


class VectorProviderAdapter:
    """Adapts VectorSearchProvider to VectorProviderProtocol.

    This adapter bridges the VectorSearchProvider interface (used by
    storage/vectors/) to the VectorProviderProtocol expected by SkillSearchTool.

    Key differences handled:
    - VectorProviderProtocol.upsert uses keyword-only args and Optional metadata
    - VectorProviderProtocol.search returns list[dict] instead of list[VectorSearchResult]
    """

    def __init__(self, provider: VectorSearchProvider) -> None:
        """Initialize the adapter.

        Args:
            provider: The VectorSearchProvider to wrap
        """
        self._provider = provider

    async def upsert(
        self,
        *,
        collection: str,
        id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Insert or update a vector with metadata.

        Args:
            collection: Collection/namespace name
            id: Unique identifier for the vector
            vector: Vector embedding (list of floats)
            metadata: Optional key-value metadata (defaults to empty dict)
        """
        # VectorSearchProvider requires non-None metadata
        await self._provider.upsert(
            collection=collection,
            id=id,
            vector=vector,
            metadata=metadata if metadata is not None else {},
        )

    async def search(
        self,
        *,
        collection: str,
        query_vector: list[float],
        limit: int = 10,
        min_score: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors.

        Args:
            collection: Collection/namespace to search
            query_vector: Query vector for similarity comparison
            limit: Maximum number of results to return
            min_score: Minimum similarity score threshold (0-1)
            filters: Optional metadata filters (exact match)

        Returns:
            List of dicts with id, score, and metadata keys
        """
        results = await self._provider.search(
            collection=collection,
            query_vector=query_vector,
            limit=limit,
            min_score=min_score,
            filters=filters,
        )

        # Convert VectorSearchResult to dict for VectorProviderProtocol
        return [
            {
                "id": result.id,
                "score": result.score,
                "metadata": result.metadata,
            }
            for result in results
        ]


class EmbeddingServiceAdapter:
    """Adapts LangChain Embeddings to EmbeddingServiceProtocol.

    This adapter bridges LangChain's Embeddings interface to the
    EmbeddingServiceProtocol expected by SkillSearchTool.

    Key differences handled:
    - LangChain embed_query is sync; EmbeddingServiceProtocol.embed is async
    - Uses asyncio.to_thread for non-blocking embedding generation
    """

    def __init__(self, embeddings: Embeddings) -> None:
        """Initialize the adapter.

        Args:
            embeddings: The LangChain Embeddings instance to wrap
        """
        self._embeddings = embeddings

    async def embed(self, text: str) -> list[float]:
        """Embed text into a vector.

        Args:
            text: The text to embed

        Returns:
            Vector embedding as list of floats
        """
        # Run sync method in thread pool to avoid blocking
        return await asyncio.to_thread(self._embeddings.embed_query, text)


def create_skill_search_tool() -> SkillSearchTool | None:
    """Create a SkillSearchTool with configured adapters.

    Creates a SkillSearchTool connected to the shared vector/embedding
    infrastructure based on application settings.

    Returns:
        Configured SkillSearchTool, or None if not configured

    Example:
        tool = create_skill_search_tool()
        if tool:
            results = await tool.search("find code review skill")
    """
    from mcp_server_langgraph.core.config import settings
    from mcp_server_langgraph.core.dynamic_context_loader import _create_embeddings
    from mcp_server_langgraph.skills.search import SkillSearchTool
    from mcp_server_langgraph.storage.vectors.factory import (
        get_vector_provider_from_settings,
    )

    # Check if embeddings are configured
    if not settings.qdrant_url or not settings.embedding_provider:
        logger.debug("SkillSearchTool not configured: missing qdrant_url or embedding_provider")
        return None

    try:
        # Get vector provider from settings
        vector_provider = get_vector_provider_from_settings()
        vector_adapter = VectorProviderAdapter(vector_provider)

        # Create embeddings using shared infrastructure
        embeddings = _create_embeddings(
            provider=settings.embedding_provider,
            model_name=settings.embedding_model_name,
            google_api_key=settings.google_api_key,
            openai_api_key=getattr(settings, "openai_api_key", None),
            huggingface_token=getattr(settings, "huggingface_token", None),
        )
        embedding_adapter = EmbeddingServiceAdapter(embeddings)

        # Create SkillSearchTool with adapters
        tool = SkillSearchTool(
            vector_provider=vector_adapter,
            embedding_service=embedding_adapter,
        )

        logger.info(
            "SkillSearchTool created",
            extra={
                "embedding_provider": settings.embedding_provider,
                "embedding_model": settings.embedding_model_name,
            },
        )

        return tool

    except Exception as e:
        logger.warning(f"Failed to create SkillSearchTool: {e}")
        return None
