"""Semantic Index Manager for Tool/Skill/Memory Discovery.

Manages semantic indexing and search for tools, skills, and memories
to enable dynamic capability discovery and progressive disclosure.

Follows patterns from:
- Anthropic's Tool Search Tool pattern (defer_loading, 34-64% token savings)
- LangGraph's Many Tools pattern (index embeddings, retrieve_tools node)

Usage:
    from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

    manager = SemanticIndexManager(
        embedder=embeddings_instance,
        qdrant_client=async_qdrant_client,
    )

    # Index tools
    await manager.index_tool(tool_entry)

    # Search for relevant tools
    tools = await manager.search_tools(query="calculate sum", limit=10)

ADR Reference: Plan for semantic tool/skill discovery
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from mcp_server_langgraph.core.scopes import CapabilityScope
from mcp_server_langgraph.observability.telemetry import logger, tracer
from mcp_server_langgraph.tools.semantic_index import (
    MemoryIndexEntry,
    SkillIndexEntry,
    ToolIndexEntry,
)

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from qdrant_client import AsyncQdrantClient


# Constants
DEFAULT_COLLECTION_NAME = "capability_index"
DEFAULT_VECTOR_SIZE = 384  # Common for lightweight models


class SemanticIndexManager:
    """Manages semantic indexing and search for capabilities.

    Provides unified indexing and search for tools, skills, and memories
    using Qdrant vector store with semantic embeddings.

    Attributes:
        embedder: LangChain Embeddings instance for generating embeddings
        qdrant_client: Async Qdrant client for vector storage
        collection_name: Name of the Qdrant collection
        vector_size: Dimension of embedding vectors
    """

    def __init__(
        self,
        embedder: Embeddings,
        qdrant_client: AsyncQdrantClient,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        vector_size: int = DEFAULT_VECTOR_SIZE,
    ) -> None:
        """Initialize SemanticIndexManager.

        Args:
            embedder: LangChain Embeddings instance
            qdrant_client: Async Qdrant client
            collection_name: Name of the Qdrant collection
            vector_size: Dimension of embedding vectors
        """
        self.embedder = embedder
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name
        self.vector_size = vector_size

    async def ensure_collection(self) -> None:
        """Ensure the collection exists, creating if necessary.

        Creates the collection with appropriate vector configuration
        if it doesn't already exist.
        """
        with tracer.start_as_current_span("semantic_index.ensure_collection") as span:
            span.set_attribute("collection_name", self.collection_name)

            try:
                collections = await self.qdrant_client.get_collections()
                existing_names = {c.name for c in collections.collections}

                if self.collection_name not in existing_names:
                    logger.info(f"Creating collection: {self.collection_name}")
                    await self.qdrant_client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(
                            size=self.vector_size,
                            distance=Distance.COSINE,
                        ),
                    )
                    logger.info(f"Collection created: {self.collection_name}")
                else:
                    logger.debug(f"Collection already exists: {self.collection_name}")

            except Exception as e:
                logger.error(f"Failed to ensure collection: {e}")
                raise

    # =========================================================================
    # Tool Indexing and Search
    # =========================================================================

    async def index_tool(self, entry: ToolIndexEntry) -> None:
        """Index a single tool entry.

        Generates embedding if not provided and stores in Qdrant.

        Args:
            entry: ToolIndexEntry to index
        """
        with tracer.start_as_current_span("semantic_index.index_tool") as span:
            span.set_attribute("tool_id", entry.tool_id)
            span.set_attribute("tool_name", entry.name)

            # Generate embedding if not provided
            embedding = entry.embedding
            if embedding is None:
                text_to_embed = f"{entry.name}: {entry.description}"
                embedding = await asyncio.to_thread(self.embedder.embed_query, text_to_embed)

            # Build payload
            payload = entry.to_dict()
            payload["ref_type"] = "tool"

            # Upsert to Qdrant
            point = PointStruct(
                id=entry.tool_id,
                vector=embedding,
                payload=payload,
            )

            await self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=[point],
            )

            logger.debug(f"Indexed tool: {entry.name}")

    async def index_tools_batch(self, entries: list[ToolIndexEntry]) -> None:
        """Index multiple tools efficiently in batch.

        Args:
            entries: List of ToolIndexEntry to index
        """
        with tracer.start_as_current_span("semantic_index.index_tools_batch") as span:
            span.set_attribute("count", len(entries))

            if not entries:
                return

            # Generate embeddings for entries without them
            texts_to_embed = []
            entries_needing_embedding = []

            for entry in entries:
                if entry.embedding is None:
                    texts_to_embed.append(f"{entry.name}: {entry.description}")
                    entries_needing_embedding.append(entry)

            # Batch embed
            if texts_to_embed:
                embeddings = await asyncio.to_thread(self.embedder.embed_documents, texts_to_embed)
                for entry, emb in zip(entries_needing_embedding, embeddings, strict=True):
                    entry.embedding = emb

            # Build points
            points = []
            for entry in entries:
                payload = entry.to_dict()
                payload["ref_type"] = "tool"
                # Embedding is guaranteed to be set after batch embed loop above
                embedding = entry.embedding
                if embedding is None:
                    continue  # Skip entries without embeddings (shouldn't happen)
                points.append(
                    PointStruct(
                        id=entry.tool_id,
                        vector=embedding,
                        payload=payload,
                    )
                )

            # Batch upsert
            await self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points,
            )

            logger.info(f"Batch indexed {len(entries)} tools")

    async def search_tools(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.5,
        category: str | None = None,
        scope: CapabilityScope | None = None,
        tenant_id: str | None = None,
    ) -> list[ToolIndexEntry]:
        """Search for relevant tools using semantic similarity.

        Args:
            query: Search query
            limit: Maximum number of results
            min_score: Minimum similarity score (0-1)
            category: Optional category filter
            scope: Optional scope filter
            tenant_id: Optional tenant ID for multi-tenant isolation

        Returns:
            List of matching ToolIndexEntry sorted by relevance
        """
        with tracer.start_as_current_span("semantic_index.search_tools") as span:
            span.set_attribute("query", query)
            span.set_attribute("limit", limit)

            # Generate query embedding
            query_embedding = await asyncio.to_thread(self.embedder.embed_query, query)

            # Build filter
            must_conditions: list[FieldCondition] = [FieldCondition(key="ref_type", match=MatchValue(value="tool"))]

            if category:
                must_conditions.append(FieldCondition(key="category", match=MatchValue(value=category)))

            if scope:
                must_conditions.append(FieldCondition(key="scope", match=MatchValue(value=str(scope.value))))

            if tenant_id:
                must_conditions.append(FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)))

            query_filter = Filter(must=must_conditions)

            # Search using query_points (qdrant-client >= 1.7)
            response = await self.qdrant_client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                query_filter=query_filter,
                limit=limit,
                score_threshold=min_score,
            )
            results = response.points

            # Convert to ToolIndexEntry
            entries = []
            for result in results:
                payload = result.payload or {}
                entry = ToolIndexEntry(
                    tool_id=payload.get("tool_id", str(result.id)),
                    name=payload.get("name", ""),
                    description=payload.get("description", ""),
                    category=payload.get("category", "other"),
                    scope=CapabilityScope(payload.get("scope", "session")),
                    tenant_id=payload.get("tenant_id"),
                    parameters_summary=payload.get("parameters_summary", ""),
                    token_estimate=payload.get("token_estimate", 0),
                )
                entries.append(entry)

            span.set_attribute("results_count", len(entries))
            return entries

    # =========================================================================
    # Skill Indexing and Search
    # =========================================================================

    async def index_skill(self, entry: SkillIndexEntry) -> None:
        """Index a single skill entry.

        Args:
            entry: SkillIndexEntry to index
        """
        with tracer.start_as_current_span("semantic_index.index_skill") as span:
            span.set_attribute("skill_id", entry.skill_id)
            span.set_attribute("skill_name", entry.name)

            # Generate embedding if not provided
            embedding = entry.embedding
            if embedding is None:
                text_to_embed = f"{entry.name}: {entry.description}"
                embedding = await asyncio.to_thread(self.embedder.embed_query, text_to_embed)

            # Build payload
            payload = entry.to_dict()
            payload["ref_type"] = "skill"

            # Upsert to Qdrant
            point = PointStruct(
                id=entry.skill_id,
                vector=embedding,
                payload=payload,
            )

            await self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=[point],
            )

            logger.debug(f"Indexed skill: {entry.name}")

    async def search_skills(
        self,
        query: str,
        limit: int = 5,
        min_score: float = 0.5,
        category: str | None = None,
        tenant_id: str | None = None,
    ) -> list[SkillIndexEntry]:
        """Search for relevant skills using semantic similarity.

        Args:
            query: Search query
            limit: Maximum number of results
            min_score: Minimum similarity score (0-1)
            category: Optional category filter
            tenant_id: Optional tenant ID for multi-tenant isolation

        Returns:
            List of matching SkillIndexEntry sorted by relevance
        """
        with tracer.start_as_current_span("semantic_index.search_skills") as span:
            span.set_attribute("query", query)
            span.set_attribute("limit", limit)

            # Generate query embedding
            query_embedding = await asyncio.to_thread(self.embedder.embed_query, query)

            # Build filter
            must_conditions: list[FieldCondition] = [FieldCondition(key="ref_type", match=MatchValue(value="skill"))]

            if category:
                must_conditions.append(FieldCondition(key="category", match=MatchValue(value=category)))

            if tenant_id:
                must_conditions.append(FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)))

            query_filter = Filter(must=must_conditions)

            # Search using query_points (qdrant-client >= 1.7)
            response = await self.qdrant_client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                query_filter=query_filter,
                limit=limit,
                score_threshold=min_score,
            )
            results = response.points

            # Convert to SkillIndexEntry
            entries = []
            for result in results:
                payload = result.payload or {}
                entry = SkillIndexEntry(
                    skill_id=payload.get("skill_id", str(result.id)),
                    name=payload.get("name", ""),
                    description=payload.get("description", ""),
                    category=payload.get("category", "other"),
                    scope=CapabilityScope(payload.get("scope", "project")),
                    tenant_id=payload.get("tenant_id"),
                    skill_file_path=payload.get("skill_file_path"),
                    summary=payload.get("summary"),
                    token_estimate=payload.get("token_estimate", 0),
                    tools_needed=payload.get("tools_needed", []),
                )
                entries.append(entry)

            span.set_attribute("results_count", len(entries))
            return entries

    # =========================================================================
    # Memory Indexing and Search
    # =========================================================================

    async def index_memory(self, entry: MemoryIndexEntry) -> None:
        """Index a single memory entry.

        Args:
            entry: MemoryIndexEntry to index
        """
        with tracer.start_as_current_span("semantic_index.index_memory") as span:
            span.set_attribute("memory_id", entry.memory_id)

            # Generate embedding if not provided
            embedding = entry.embedding
            if embedding is None:
                embedding = await asyncio.to_thread(self.embedder.embed_query, entry.content)

            # Build payload
            payload = entry.to_dict()
            payload["ref_type"] = "memory"

            # Upsert to Qdrant
            point = PointStruct(
                id=entry.memory_id,
                vector=embedding,
                payload=payload,
            )

            await self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=[point],
            )

            logger.debug(f"Indexed memory: {entry.memory_id}")

    async def search_memories(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.5,
        memory_type: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        tenant_id: str | None = None,
    ) -> list[MemoryIndexEntry]:
        """Search for relevant memories using semantic similarity.

        Args:
            query: Search query
            limit: Maximum number of results
            min_score: Minimum similarity score (0-1)
            memory_type: Optional memory type filter
            session_id: Optional session ID filter
            user_id: Optional user ID filter
            tenant_id: Optional tenant ID for multi-tenant isolation

        Returns:
            List of matching MemoryIndexEntry sorted by relevance
        """
        with tracer.start_as_current_span("semantic_index.search_memories") as span:
            span.set_attribute("query", query)
            span.set_attribute("limit", limit)

            # Generate query embedding
            query_embedding = await asyncio.to_thread(self.embedder.embed_query, query)

            # Build filter
            must_conditions: list[FieldCondition] = [FieldCondition(key="ref_type", match=MatchValue(value="memory"))]

            if memory_type:
                must_conditions.append(FieldCondition(key="memory_type", match=MatchValue(value=memory_type)))

            if session_id:
                must_conditions.append(FieldCondition(key="session_id", match=MatchValue(value=session_id)))

            if user_id:
                must_conditions.append(FieldCondition(key="user_id", match=MatchValue(value=user_id)))

            if tenant_id:
                must_conditions.append(FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)))

            query_filter = Filter(must=must_conditions)

            # Search using query_points (qdrant-client >= 1.7)
            response = await self.qdrant_client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                query_filter=query_filter,
                limit=limit,
                score_threshold=min_score,
            )
            results = response.points

            # Convert to MemoryIndexEntry
            entries = []
            for result in results:
                payload = result.payload or {}
                entry = MemoryIndexEntry(
                    memory_id=payload.get("memory_id", str(result.id)),
                    content=payload.get("content", ""),
                    memory_type=payload.get("memory_type", "context"),
                    scope=CapabilityScope(payload.get("scope", "session")),
                    session_id=payload.get("session_id"),
                    user_id=payload.get("user_id"),
                    tenant_id=payload.get("tenant_id"),
                    timestamp=payload.get("timestamp"),
                    importance_score=payload.get("importance_score", 0.5),
                )
                entries.append(entry)

            span.set_attribute("results_count", len(entries))
            return entries


__all__ = ["SemanticIndexManager"]
