"""
Dynamic Context Loading with Qdrant Vector Store

Implements Anthropic's Just-in-Time context loading strategy:
- Semantic search for relevant context
- Progressive discovery patterns
- Lightweight context references
"""

import asyncio
import time
from functools import lru_cache
from typing import Any

from langchain_core.messages import BaseMessage, SystemMessage
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from sentence_transformers import SentenceTransformer

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer
from mcp_server_langgraph.utils.response_optimizer import count_tokens


class ContextReference(BaseModel):
    """Lightweight reference to context that can be loaded on demand."""

    ref_id: str = Field(description="Unique identifier for this context")
    ref_type: str = Field(description="Type: conversation, document, tool_usage, file")
    summary: str = Field(description="Brief summary for filtering (< 100 chars)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    relevance_score: float | None = Field(default=None, description="Relevance score if from search")


class LoadedContext(BaseModel):
    """Full context loaded from a reference."""

    reference: ContextReference
    content: str = Field(description="Full context content")
    token_count: int = Field(description="Token count of content")
    loaded_at: float = Field(description="Timestamp when loaded")


class DynamicContextLoader:
    """
    Manages just-in-time context loading with semantic search.

    Follows Anthropic's recommendations:
    1. Store lightweight identifiers instead of full context
    2. Load context dynamically when needed
    3. Use semantic search for relevance
    4. Progressive discovery through iterative search
    """

    def __init__(
        self,
        qdrant_url: str | None = None,
        qdrant_port: int | None = None,
        collection_name: str | None = None,
        embedding_model: str | None = None,
        cache_size: int | None = None,
    ):
        """
        Initialize dynamic context loader.

        Args:
            qdrant_url: Qdrant server URL (defaults to settings.qdrant_url)
            qdrant_port: Qdrant server port (defaults to settings.qdrant_port)
            collection_name: Name of Qdrant collection (defaults to settings.qdrant_collection_name)
            embedding_model: SentenceTransformer model name (defaults to settings.embedding_model)
            cache_size: LRU cache size for loaded contexts (defaults to settings.context_cache_size)
        """
        self.qdrant_url = qdrant_url or settings.qdrant_url
        self.qdrant_port = qdrant_port or settings.qdrant_port
        self.collection_name = collection_name or settings.qdrant_collection_name
        self.embedding_model_name = embedding_model or settings.embedding_model
        cache_size = cache_size or settings.context_cache_size

        # Initialize Qdrant client
        self.client = QdrantClient(host=self.qdrant_url, port=self.qdrant_port)

        # Initialize embedding model
        self.embedder = SentenceTransformer(self.embedding_model_name)
        self.embedding_dim = self.embedder.get_sentence_embedding_dimension()

        # Create collection if it doesn't exist
        self._ensure_collection_exists()

        # LRU cache for loaded contexts
        self._load_context_cached = lru_cache(maxsize=cache_size)(self._load_context_impl)

        logger.info(
            "DynamicContextLoader initialized",
            extra={
                "qdrant_url": self.qdrant_url,
                "collection": self.collection_name,
                "embedding_model": self.embedding_model_name,
                "embedding_dim": self.embedding_dim,
            },
        )

    def _ensure_collection_exists(self):
        """Create Qdrant collection if it doesn't exist."""
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.embedding_dim, distance=Distance.COSINE),
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Qdrant collection exists: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to ensure Qdrant collection: {e}", exc_info=True)
            raise

    async def index_context(
        self,
        ref_id: str,
        content: str,
        ref_type: str,
        summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Index context for later retrieval.

        Args:
            ref_id: Unique identifier
            content: Full content to index
            ref_type: Type of context
            summary: Brief summary
            metadata: Additional metadata
        """
        with tracer.start_as_current_span("context.index") as span:
            span.set_attribute("ref_id", ref_id)
            span.set_attribute("ref_type", ref_type)

            try:
                # Generate embedding
                embedding = await asyncio.to_thread(self.embedder.encode, content)

                # Create point
                point = PointStruct(
                    id=ref_id,
                    vector=embedding.tolist(),
                    payload={
                        "ref_id": ref_id,
                        "ref_type": ref_type,
                        "summary": summary,
                        "content": content,  # Store full content for retrieval
                        "token_count": count_tokens(content),
                        "metadata": metadata or {},
                    },
                )

                # Upsert to Qdrant
                await asyncio.to_thread(self.client.upsert, collection_name=self.collection_name, points=[point])

                logger.info(f"Indexed context: {ref_id}", extra={"ref_type": ref_type, "summary": summary})
                metrics.successful_calls.add(1, {"operation": "index_context", "type": ref_type})

            except Exception as e:
                logger.error(f"Failed to index context: {e}", exc_info=True)
                metrics.failed_calls.add(1, {"operation": "index_context", "error": type(e).__name__})
                raise

    async def semantic_search(
        self,
        query: str,
        top_k: int = 5,
        ref_type_filter: str | None = None,
        min_score: float = 0.5,
    ) -> list[ContextReference]:
        """
        Search for relevant context using semantic similarity.

        Implements Anthropic's recommendation for search-focused retrieval.

        Args:
            query: Search query
            top_k: Number of results
            ref_type_filter: Optional filter by ref_type
            min_score: Minimum similarity score (0-1)

        Returns:
            List of context references sorted by relevance
        """
        with tracer.start_as_current_span("context.semantic_search") as span:
            span.set_attribute("query", query)
            span.set_attribute("top_k", top_k)

            try:
                # Generate query embedding
                query_embedding = await asyncio.to_thread(self.embedder.encode, query)

                # Build filter
                search_filter = None
                if ref_type_filter:
                    search_filter = Filter(must=[FieldCondition(key="ref_type", match=MatchValue(value=ref_type_filter))])

                # Search Qdrant
                results = await asyncio.to_thread(
                    self.client.search,
                    collection_name=self.collection_name,
                    query_vector=query_embedding.tolist(),
                    limit=top_k,
                    query_filter=search_filter,
                    score_threshold=min_score,
                )

                # Convert to ContextReferences
                references = []
                for result in results:
                    payload = result.payload
                    ref = ContextReference(
                        ref_id=payload["ref_id"],
                        ref_type=payload["ref_type"],
                        summary=payload["summary"],
                        metadata=payload.get("metadata", {}),
                        relevance_score=result.score,
                    )
                    references.append(ref)

                logger.info(
                    "Semantic search completed",
                    extra={"query": query, "results_found": len(references), "top_k": top_k},
                )

                span.set_attribute("results.count", len(references))
                metrics.successful_calls.add(1, {"operation": "semantic_search"})

                return references

            except Exception as e:
                logger.error(f"Semantic search failed: {e}", exc_info=True)
                metrics.failed_calls.add(1, {"operation": "semantic_search", "error": type(e).__name__})
                return []

    async def progressive_discover(
        self,
        initial_query: str,
        max_iterations: int = 3,
        expansion_keywords: list[str] | None = None,
    ) -> list[ContextReference]:
        """
        Progressive discovery: iteratively refine search based on results.

        Implements Anthropic's "Progressive Disclosure" pattern.

        Args:
            initial_query: Starting search query
            max_iterations: Maximum search iterations
            expansion_keywords: Keywords to expand search

        Returns:
            Aggregated context references from all iterations
        """
        with tracer.start_as_current_span("context.progressive_discover") as span:
            span.set_attribute("initial_query", initial_query)
            span.set_attribute("max_iterations", max_iterations)

            all_references = []
            seen_ids = set()
            current_query = initial_query

            for iteration in range(max_iterations):
                logger.info(f"Progressive discovery iteration {iteration + 1}/{max_iterations}")

                # Search with current query
                results = await self.semantic_search(current_query, top_k=5)

                # Add new results
                for ref in results:
                    if ref.ref_id not in seen_ids:
                        all_references.append(ref)
                        seen_ids.add(ref.ref_id)

                # Stop if no new results
                if not results:
                    logger.info(f"No new results in iteration {iteration + 1}, stopping")
                    break

                # Expand query for next iteration
                if expansion_keywords and iteration < max_iterations - 1:
                    current_query = f"{current_query} {expansion_keywords[iteration]}"

            span.set_attribute("total_references", len(all_references))
            span.set_attribute("iterations_completed", iteration + 1)

            logger.info(
                "Progressive discovery completed",
                extra={"iterations": iteration + 1, "total_references": len(all_references)},
            )

            return all_references

    async def load_context(self, reference: ContextReference) -> LoadedContext:
        """
        Load full context from a reference.

        Uses LRU cache for frequently accessed contexts.

        Args:
            reference: Context reference to load

        Returns:
            Loaded context with full content
        """
        with tracer.start_as_current_span("context.load") as span:
            span.set_attribute("ref_id", reference.ref_id)

            # Use cached implementation
            loaded = await asyncio.to_thread(self._load_context_cached, reference.ref_id)

            span.set_attribute("token_count", loaded.token_count)
            metrics.successful_calls.add(1, {"operation": "load_context", "type": reference.ref_type})

            return loaded

    def _load_context_impl(self, ref_id: str) -> LoadedContext:
        """
        Implementation of context loading (cached).

        Args:
            ref_id: Reference ID to load

        Returns:
            Loaded context
        """
        try:
            # Retrieve from Qdrant
            results = self.client.retrieve(collection_name=self.collection_name, ids=[ref_id])

            if not results:
                raise ValueError(f"Context not found: {ref_id}")

            result = results[0]
            payload = result.payload

            reference = ContextReference(
                ref_id=payload["ref_id"],
                ref_type=payload["ref_type"],
                summary=payload["summary"],
                metadata=payload.get("metadata", {}),
            )

            loaded = LoadedContext(
                reference=reference,
                content=payload["content"],
                token_count=payload["token_count"],
                loaded_at=time.time(),
            )

            logger.info(f"Loaded context: {ref_id}", extra={"token_count": loaded.token_count})

            return loaded

        except Exception as e:
            logger.error(f"Failed to load context {ref_id}: {e}", exc_info=True)
            metrics.failed_calls.add(1, {"operation": "load_context", "error": type(e).__name__})
            raise

    async def load_batch(
        self, references: list[ContextReference], max_tokens: int = 4000
    ) -> list[LoadedContext]:
        """
        Load multiple contexts up to token limit.

        Implements token-aware batching.

        Args:
            references: List of references to load
            max_tokens: Maximum total tokens

        Returns:
            List of loaded contexts within token budget
        """
        with tracer.start_as_current_span("context.load_batch") as span:
            loaded = []
            total_tokens = 0

            for ref in references:
                context = await self.load_context(ref)

                if total_tokens + context.token_count <= max_tokens:
                    loaded.append(context)
                    total_tokens += context.token_count
                else:
                    logger.info(
                        f"Token limit reached, loaded {len(loaded)}/{len(references)} contexts",
                        extra={"total_tokens": total_tokens, "limit": max_tokens},
                    )
                    break

            span.set_attribute("contexts_loaded", len(loaded))
            span.set_attribute("total_tokens", total_tokens)

            return loaded

    def to_messages(self, loaded_contexts: list[LoadedContext]) -> list[BaseMessage]:
        """
        Convert loaded contexts to LangChain messages.

        Args:
            loaded_contexts: List of loaded contexts

        Returns:
            List of SystemMessages containing context
        """
        messages = []

        for ctx in loaded_contexts:
            message = SystemMessage(
                content=f'<context type="{ctx.reference.ref_type}" id="{ctx.reference.ref_id}">\n'
                f"{ctx.content}\n"
                f"</context>"
            )
            messages.append(message)

        return messages


# Convenience functions
async def search_and_load_context(
    query: str,
    loader: DynamicContextLoader | None = None,
    top_k: int = 3,
    max_tokens: int = 2000,
) -> list[LoadedContext]:
    """
    Search for context and load top results within token budget.

    Args:
        query: Search query
        loader: Context loader instance (creates new if None)
        top_k: Number of results to search for
        max_tokens: Maximum tokens to load

    Returns:
        List of loaded contexts
    """
    if loader is None:
        loader = DynamicContextLoader()

    # Search
    references = await loader.semantic_search(query, top_k=top_k)

    # Load within budget
    loaded = await loader.load_batch(references, max_tokens=max_tokens)

    return loaded
