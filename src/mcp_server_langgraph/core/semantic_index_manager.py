"""Semantic Index Manager for Tool/Skill/Memory Discovery.

Manages semantic indexing and search for tools, skills, and memories
to enable dynamic capability discovery and progressive disclosure.

Follows patterns from:
- Anthropic's Tool Search Tool pattern (defer_loading, 34-64% token savings)
- LangGraph's Many Tools pattern (index embeddings, retrieve_tools node)

Authorization:
- Uses OpenFGA for fine-grained access control (ADR-0068, ADR-0099)
- tool_index: viewer relation required for search
- skill_index: viewer relation required for search
- memory_index: owner relation for own memories, admin for others

Usage:
    from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

    manager = SemanticIndexManager(
        embedder=embeddings_instance,
        qdrant_client=async_qdrant_client,
    )

    # Index tools
    await manager.index_tool(tool_entry)

    # Search for relevant tools (with authorization)
    tools = await manager.search_tools(
        query="calculate sum",
        user_id="user:alice",
        limit=10,
    )

ADR Reference: ADR-0099 Semantic Tool Selection, ADR-0068 OpenFGA ReBAC
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import TYPE_CHECKING, Any

from cachetools import TTLCache

from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from mcp_server_langgraph.core.dependencies import get_openfga_client
from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.core.scopes import CapabilityScope
from mcp_server_langgraph.observability.telemetry import logger, tracer
from mcp_server_langgraph.storage.vectors.qdrant_provider import string_to_qdrant_id
from mcp_server_langgraph.tools.semantic_index import (
    MemoryIndexEntry,
    SkillIndexEntry,
    ToolIndexEntry,
)

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from qdrant_client import AsyncQdrantClient

    from mcp_server_langgraph.core.cache import CacheService
    from mcp_server_langgraph.core.config import Settings


# Constants
DEFAULT_COLLECTION_NAME = "capability_index"
DEFAULT_VECTOR_SIZE = 384  # Common for lightweight models
DEFAULT_AUTH_CACHE_TTL_SECONDS = 60  # Cache authorization results for 60 seconds
DEFAULT_AUTH_CACHE_MAXSIZE = 1000  # Maximum number of cached authorization entries

# Query result cache settings
DEFAULT_QUERY_CACHE_TTL_SECONDS = 300  # Cache query results for 5 minutes
DEFAULT_QUERY_CACHE_MAXSIZE = 500  # Maximum number of cached query results

# Embedding cache settings (embeddings are deterministic, cache longer)
DEFAULT_EMBEDDING_CACHE_TTL_SECONDS = 3600  # Cache embeddings for 1 hour
DEFAULT_EMBEDDING_CACHE_MAXSIZE = 1000  # Maximum number of cached embeddings

# Decision trace collection for context graphs (ADR-0101)
DECISION_TRACE_COLLECTION = "decision_traces"

# =============================================================================
# Prometheus Metrics for Authorization Cache
# =============================================================================

# Lazy-load prometheus_client to handle missing dependency
_prometheus_available: bool | None = None
_semantic_auth_cache_total: Any = None
_semantic_auth_cache_size: Any = None
_semantic_cache_warming_duration: Any = None
_semantic_tool_search_duration: Any = None
_semantic_tool_search_results: Any = None
_semantic_cache_operations: Any = None


def _init_semantic_auth_metrics() -> bool:
    """Initialize Prometheus auth cache metrics lazily."""
    global _prometheus_available
    global _semantic_auth_cache_total
    global _semantic_auth_cache_size
    global _semantic_cache_warming_duration
    global _semantic_tool_search_duration
    global _semantic_tool_search_results
    global _semantic_cache_operations

    if _prometheus_available is not None:
        return _prometheus_available

    try:
        from prometheus_client import Counter, Gauge, Histogram

        _semantic_auth_cache_total = Counter(
            "semantic_auth_cache_total",
            "Semantic index authorization cache operations (hit/miss)",
            ["result", "resource_type"],  # result: hit, miss; resource_type: tool_index, skill_index, memory_index
        )

        _semantic_auth_cache_size = Gauge(
            "semantic_auth_cache_size",
            "Current number of entries in the semantic index authorization cache",
        )

        _semantic_cache_warming_duration = Histogram(
            "semantic_cache_warming_duration_seconds",
            "Duration of cache warming operations in seconds",
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )

        _semantic_tool_search_duration = Histogram(
            "semantic_tool_search_duration_seconds",
            "Duration of semantic tool search operations in seconds",
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        )

        _semantic_tool_search_results = Histogram(
            "semantic_tool_search_results_count",
            "Number of tools returned by semantic search",
            buckets=(0, 1, 2, 5, 10, 20, 50, 100),
        )

        _semantic_cache_operations = Counter(
            "semantic_cache_operations_total",
            "Semantic index cache operations (hit/miss) by cache type",
            ["cache_type", "result"],  # cache_type: query, embedding; result: hit, miss
        )

        _prometheus_available = True
        return True

    except ImportError:
        _prometheus_available = False
        return False


# Initialize on module load
_init_semantic_auth_metrics()


def emit_auth_cache_metric(*, result: str, resource_type: str) -> None:
    """
    Emit a Prometheus counter metric for authorization cache operations.

    Args:
        result: Cache operation result ("hit" or "miss")
        resource_type: Resource type being accessed (e.g., "tool_index", "skill_index")
    """
    if not _prometheus_available:
        return

    try:
        if _semantic_auth_cache_total is not None:
            _semantic_auth_cache_total.labels(result=result, resource_type=resource_type).inc()
    except Exception as e:
        logger.debug("Semantic auth cache metric recording failed: %s", e)


def update_cache_size_gauge(*, size: int) -> None:
    """
    Update the Prometheus gauge for cache size.

    Args:
        size: Current number of entries in the cache
    """
    if not _prometheus_available:
        return

    try:
        if _semantic_auth_cache_size is not None:
            _semantic_auth_cache_size.set(size)
    except Exception as e:
        logger.debug("Semantic auth cache size gauge update failed: %s", e)


def record_cache_warming_duration(*, duration_seconds: float, entries_count: int) -> None:
    """
    Record cache warming duration in Prometheus histogram.

    Args:
        duration_seconds: Duration of the cache warming operation
        entries_count: Number of entries that were warmed
    """
    if not _prometheus_available:
        return

    try:
        if _semantic_cache_warming_duration is not None:
            _semantic_cache_warming_duration.observe(duration_seconds)
    except Exception as e:
        logger.debug("Semantic cache warming duration recording failed: %s", e)


def emit_tool_search_metric(
    *,
    duration_seconds: float,
    results_count: int,
    cache_hit: bool,
    user_id: str,
) -> None:
    """
    Emit Prometheus metrics for a tool search operation.

    Args:
        duration_seconds: Time taken for the search operation
        results_count: Number of tools returned
        cache_hit: Whether the result came from cache
        user_id: User who performed the search (for debugging, not stored in metric)
    """
    if not _prometheus_available:
        return

    try:
        if _semantic_tool_search_duration is not None:
            _semantic_tool_search_duration.observe(duration_seconds)
        if _semantic_tool_search_results is not None:
            _semantic_tool_search_results.observe(results_count)
    except Exception as e:
        logger.debug("Semantic tool search metric recording failed: %s", e)


def emit_cache_hit_metric(*, cache_type: str, result: str) -> None:
    """
    Emit a Prometheus counter metric for cache operations.

    Args:
        cache_type: Type of cache ("query", "embedding")
        result: Cache operation result ("hit" or "miss")
    """
    if not _prometheus_available:
        return

    try:
        if _semantic_cache_operations is not None:
            _semantic_cache_operations.labels(cache_type=cache_type, result=result).inc()
    except Exception as e:
        logger.debug("Semantic cache operation metric recording failed: %s", e)


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
        auth_cache_ttl_seconds: float = DEFAULT_AUTH_CACHE_TTL_SECONDS,
        auth_cache_maxsize: int = DEFAULT_AUTH_CACHE_MAXSIZE,
        query_cache_ttl_seconds: float = DEFAULT_QUERY_CACHE_TTL_SECONDS,
        query_cache_maxsize: int = DEFAULT_QUERY_CACHE_MAXSIZE,
        embedding_cache_ttl_seconds: float = DEFAULT_EMBEDDING_CACHE_TTL_SECONDS,
        embedding_cache_maxsize: int = DEFAULT_EMBEDDING_CACHE_MAXSIZE,
        cache_service: CacheService | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initialize SemanticIndexManager.

        Args:
            embedder: LangChain Embeddings instance
            qdrant_client: Async Qdrant client
            collection_name: Name of the Qdrant collection
            vector_size: Dimension of embedding vectors
            auth_cache_ttl_seconds: TTL for authorization cache in seconds.
                                    Set to 0 to disable caching. Default: 60s.
            auth_cache_maxsize: Maximum number of cached authorization entries.
                               Uses LRU eviction when limit is reached. Default: 1000.
            query_cache_ttl_seconds: TTL for query result cache in seconds.
                                     Set to 0 to disable caching. Default: 300s.
            query_cache_maxsize: Maximum number of cached query results.
                                Uses LRU eviction when limit is reached. Default: 500.
            embedding_cache_ttl_seconds: TTL for embedding cache in seconds.
                                         Set to 0 to disable caching. Default: 3600s (1 hour).
            embedding_cache_maxsize: Maximum number of cached embeddings.
                                    Uses LRU eviction when limit is reached. Default: 1000.
            cache_service: Optional CacheService for distributed (Redis) caching.
                          When provided, enables L1+L2 caching for cache sharing
                          across instances in distributed deployments.
            settings: Optional Settings instance for environment detection.
                     Uses get_settings() if None. Pass explicit settings for testing.
        """
        self.embedder = embedder
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.auth_cache_ttl_seconds = auth_cache_ttl_seconds
        self.auth_cache_maxsize = auth_cache_maxsize
        self.query_cache_ttl_seconds = query_cache_ttl_seconds
        self.query_cache_maxsize = query_cache_maxsize
        self.embedding_cache_ttl_seconds = embedding_cache_ttl_seconds
        self.embedding_cache_maxsize = embedding_cache_maxsize
        self.cache_service = cache_service
        self._settings = settings

        # Authorization cache using TTLCache for automatic expiration and LRU eviction
        # Only positive (True) results are cached for security
        if auth_cache_ttl_seconds > 0:
            self._auth_cache: TTLCache[str, bool] = TTLCache(
                maxsize=auth_cache_maxsize,
                ttl=auth_cache_ttl_seconds,
            )
        else:
            # Disabled cache - use empty TTLCache with 0 TTL that expires immediately
            self._auth_cache = TTLCache(maxsize=1, ttl=0.001)

        # Query result cache using TTLCache for automatic expiration
        if query_cache_ttl_seconds > 0:
            self._query_cache: TTLCache[str, list[Any]] = TTLCache(
                maxsize=query_cache_maxsize,
                ttl=query_cache_ttl_seconds,
            )
        else:
            # Disabled cache
            self._query_cache = TTLCache(maxsize=1, ttl=0.001)

        # Embedding cache using TTLCache (embeddings are deterministic)
        if embedding_cache_ttl_seconds > 0:
            self._embedding_cache: TTLCache[str, list[float]] = TTLCache(
                maxsize=embedding_cache_maxsize,
                ttl=embedding_cache_ttl_seconds,
            )
        else:
            # Disabled cache
            self._embedding_cache = TTLCache(maxsize=1, ttl=0.001)

        # Cache statistics counters
        self._cache_hits = 0
        self._cache_misses = 0
        self._query_cache_hits = 0
        self._query_cache_misses = 0
        self._embedding_cache_hits = 0
        self._embedding_cache_misses = 0

    def clear_auth_cache(self) -> None:
        """Clear all cached authorization results.

        Use this method when authorization tuples have changed
        and you need to force fresh permission checks.
        """
        self._auth_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        logger.debug("Authorization cache cleared")

    def clear_query_cache(self) -> None:
        """Clear all cached query results.

        Use this method when indexed data has changed
        and you need to force fresh queries.
        """
        self._query_cache.clear()
        self._query_cache_hits = 0
        self._query_cache_misses = 0
        logger.debug("Query cache cleared")

    def clear_embedding_cache(self) -> None:
        """Clear all cached embeddings.

        Use this method when the embedding model has changed
        and you need to regenerate embeddings.
        """
        self._embedding_cache.clear()
        self._embedding_cache_hits = 0
        self._embedding_cache_misses = 0
        logger.debug("Embedding cache cleared")

    def _make_embedding_cache_key(self, text: str) -> str:
        """Generate a cache key for an embedding based on text hash.

        Args:
            text: Text to embed

        Returns:
            Cache key string containing a hash of the text
        """
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"emb:{text_hash}"

    def _make_query_cache_key(
        self,
        query: str,
        search_type: str,
        user_id: str,
        limit: int,
        **kwargs: Any,
    ) -> str:
        """Generate a cache key for a query.

        Args:
            query: Search query string
            search_type: Type of search (tools, skills, memories)
            user_id: User identifier
            limit: Maximum number of results
            **kwargs: Additional parameters to include in key

        Returns:
            Cache key string
        """
        # Include all relevant parameters in the key
        key_parts = [
            f"q:{query}",
            f"t:{search_type}",
            f"u:{user_id}",
            f"l:{limit}",
        ]
        # Add any additional kwargs to the key
        for k, v in sorted(kwargs.items()):
            if v is not None:
                key_parts.append(f"{k}:{v}")
        return "|".join(key_parts)

    def get_cache_stats(self) -> dict[str, int | float | bool]:
        """Return cache statistics for monitoring.

        Returns:
            Dictionary with cache statistics including:
            - hits: Number of cache hits
            - misses: Number of cache misses
            - size: Current number of cached entries
            - maxsize: Maximum cache size
            - ttl_seconds: Cache TTL in seconds
            - hit_rate: Cache hit rate (0.0-1.0)
            - distributed: Whether distributed (Redis) caching is enabled
        """
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0.0

        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "size": len(self._auth_cache),
            "maxsize": self.auth_cache_maxsize,
            "ttl_seconds": self.auth_cache_ttl_seconds,
            "hit_rate": hit_rate,
            "distributed": self.cache_service is not None,
        }

    def get_query_cache_stats(self) -> dict[str, int | float]:
        """Return query cache statistics for monitoring.

        Returns:
            Dictionary with query cache statistics including:
            - hits: Number of cache hits
            - misses: Number of cache misses
            - size: Current number of cached entries
            - maxsize: Maximum cache size
            - ttl_seconds: Cache TTL in seconds
            - hit_rate: Cache hit rate (0.0-1.0)
        """
        total = self._query_cache_hits + self._query_cache_misses
        hit_rate = self._query_cache_hits / total if total > 0 else 0.0

        return {
            "hits": self._query_cache_hits,
            "misses": self._query_cache_misses,
            "size": len(self._query_cache),
            "maxsize": self.query_cache_maxsize,
            "ttl_seconds": self.query_cache_ttl_seconds,
            "hit_rate": hit_rate,
        }

    def get_embedding_cache_stats(self) -> dict[str, int | float]:
        """Return embedding cache statistics for monitoring.

        Returns:
            Dictionary with embedding cache statistics including:
            - hits: Number of cache hits
            - misses: Number of cache misses
            - size: Current number of cached entries
            - maxsize: Maximum cache size
            - ttl_seconds: Cache TTL in seconds
            - hit_rate: Cache hit rate (0.0-1.0)
        """
        total = self._embedding_cache_hits + self._embedding_cache_misses
        hit_rate = self._embedding_cache_hits / total if total > 0 else 0.0

        return {
            "hits": self._embedding_cache_hits,
            "misses": self._embedding_cache_misses,
            "size": len(self._embedding_cache),
            "maxsize": self.embedding_cache_maxsize,
            "ttl_seconds": self.embedding_cache_ttl_seconds,
            "hit_rate": hit_rate,
        }

    async def warm_cache(
        self,
        entries: list[dict[str, str]],
    ) -> int:
        """Pre-warm the authorization cache with known user/resource combinations.

        Use this method during application startup to pre-populate the cache
        with commonly accessed authorization entries, reducing first-request
        latency for known service principals and frequently accessed resources.

        Each entry should be a dictionary with:
        - user_id: User identifier (e.g., "user:service-account")
        - relation: Relation to check (e.g., "viewer", "admin")
        - object_type: Object type (e.g., "tool_index", "skill_index")
        - object_id: (optional) Object ID (defaults to "default")

        Args:
            entries: List of authorization entries to warm

        Returns:
            Number of entries successfully warmed (authorized and cached)

        Example:
            entries_to_warm = [
                {"user_id": "user:service", "relation": "viewer", "object_type": "tool_index"},
                {"user_id": "user:admin", "relation": "admin", "object_type": "skill_index"},
            ]
            warmed = await manager.warm_cache(entries_to_warm)
            logger.info(f"Warmed {warmed} cache entries")
        """
        import time

        if not entries:
            return 0

        start_time = time.monotonic()
        warmed_count = 0
        for entry in entries:
            user_id = entry.get("user_id", "")
            relation = entry.get("relation", "")
            object_type = entry.get("object_type", "")
            object_id = entry.get("object_id", "default")

            if not user_id or not relation or not object_type:
                logger.warning(f"Skipping invalid cache warming entry: {entry}")
                continue

            try:
                # _check_authorization will cache positive results
                authorized = await self._check_authorization(
                    user_id=user_id,
                    relation=relation,
                    object_type=object_type,
                    object_id=object_id,
                )
                if authorized:
                    warmed_count += 1
            except Exception as e:
                logger.debug(f"Cache warming failed for entry {entry}: {e}")

        duration = time.monotonic() - start_time
        record_cache_warming_duration(duration_seconds=duration, entries_count=warmed_count)
        logger.info(f"Cache warming complete: {warmed_count}/{len(entries)} entries warmed in {duration:.3f}s")
        return warmed_count

    async def _check_authorization(
        self,
        user_id: str,
        relation: str,
        object_type: str,
        object_id: str = "default",
    ) -> bool:
        """Check if user has permission on an object.

        Implements fail-closed authorization - returns False on any error.
        Caches positive (True) results for performance. When cache_service is
        provided, uses distributed (Redis) caching via CacheService for sharing
        across instances. Otherwise, uses local TTLCache.

        Denied results are NOT cached for security (allows immediate access
        when granted).

        Args:
            user_id: User identifier (e.g., "user:alice")
            relation: Relation to check (e.g., "viewer", "admin")
            object_type: Object type (e.g., "tool_index", "skill_index")
            object_id: Object ID (default: "default")

        Returns:
            True if authorized, False otherwise (fail-closed)
        """
        # Generate cache key (local format)
        local_cache_key = f"{user_id}:{relation}:{object_type}:{object_id}"
        # Distributed cache key uses auth_permission prefix for CacheService TTL config
        distributed_cache_key = f"auth_permission:{local_cache_key}"

        # Check cache - use CacheService if available, otherwise local TTLCache
        if self.cache_service is not None:
            # Distributed mode: use CacheService (L1+L2)
            cached = await self.cache_service.aget(distributed_cache_key)
            if cached is True:
                self._cache_hits += 1
                emit_auth_cache_metric(result="hit", resource_type=object_type)
                logger.debug(f"Authorization cache hit (distributed) for {local_cache_key}")
                return True
        elif self.auth_cache_ttl_seconds > 0 and local_cache_key in self._auth_cache:
            # Local mode: use TTLCache
            self._cache_hits += 1
            emit_auth_cache_metric(result="hit", resource_type=object_type)
            logger.debug(f"Authorization cache hit for {local_cache_key}")
            return True

        # Cache miss - need to check OpenFGA
        self._cache_misses += 1
        emit_auth_cache_metric(result="miss", resource_type=object_type)

        try:
            openfga_client = get_openfga_client()
            if openfga_client is None:
                logger.warning("OpenFGA client not available, denying access")
                return False

            # Check permission
            result = await openfga_client.check_permission(
                user=user_id,
                relation=relation,
                object=f"{object_type}:{object_id}",
            )

            # Cache only positive results (security: don't cache denials)
            if result:
                if self.cache_service is not None:
                    # Distributed mode: use CacheService
                    await self.cache_service.aset(distributed_cache_key, True)
                    logger.debug(f"Authorization cached (distributed) for {local_cache_key}")
                elif self.auth_cache_ttl_seconds > 0:
                    # Local mode: use TTLCache
                    self._auth_cache[local_cache_key] = True
                    update_cache_size_gauge(size=len(self._auth_cache))
                    logger.debug(f"Authorization cached for {local_cache_key}")

            return result

        except Exception as e:
            # Fail-closed: deny access on any error
            logger.error(f"Authorization check failed: {e}")
            return False

    async def _check_tenant_membership(
        self,
        user_id: str,
        tenant_id: str,
    ) -> bool:
        """Check if user is a member of the specified tenant/organization.

        In development mode (environment == "development"), membership is bypassed.
        All other environments (test, staging, production) are fail-closed.

        Args:
            user_id: User identifier (e.g., "user:alice")
            tenant_id: Tenant/organization identifier (e.g., "organization:acme")

        Returns:
            True if user is a member, False otherwise
        """
        from mcp_server_langgraph.core.environment import is_developer_mode

        if is_developer_mode(self._settings):
            logger.debug(f"Dev mode: bypassing tenant membership check for {user_id}")
            return True

        try:
            openfga_client = get_openfga_client()
            if openfga_client is None:
                logger.warning("OpenFGA client not available, denying tenant access")
                return False

            # Check member relation on organization
            result = await openfga_client.check_permission(
                user=user_id,
                relation="member",
                object=tenant_id,
            )
            return result

        except Exception as e:
            logger.error(f"Tenant membership check failed: {e}")
            return False

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
            # Store original ID for retrieval (Qdrant ID may be converted UUID)
            payload["_original_id"] = entry.tool_id

            # Convert string ID to valid Qdrant point ID (UUID)
            qdrant_id = string_to_qdrant_id(entry.tool_id)

            # Upsert to Qdrant
            point = PointStruct(
                id=qdrant_id,
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
                # Store original ID for retrieval (Qdrant ID may be converted UUID)
                payload["_original_id"] = entry.tool_id
                # Embedding is guaranteed to be set after batch embed loop above
                embedding = entry.embedding
                if embedding is None:
                    continue  # Skip entries without embeddings (shouldn't happen)
                # Convert string ID to valid Qdrant point ID (UUID)
                qdrant_id = string_to_qdrant_id(entry.tool_id)
                points.append(
                    PointStruct(
                        id=qdrant_id,
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
        user_id: str,
        limit: int = 10,
        min_score: float = 0.5,
        category: str | None = None,
        scope: CapabilityScope | None = None,
        tenant_id: str | None = None,
    ) -> list[ToolIndexEntry]:
        """Search for relevant tools using semantic similarity.

        Requires authorization: user_id must have 'viewer' relation on tool_index.
        If tenant_id is specified, user must also be a member of that organization.

        Args:
            query: Search query
            user_id: User identifier for authorization (e.g., "user:alice")
            limit: Maximum number of results
            min_score: Minimum similarity score (0-1)
            category: Optional category filter
            scope: Optional scope filter
            tenant_id: Optional tenant ID for multi-tenant isolation

        Returns:
            List of matching ToolIndexEntry sorted by relevance
            Empty list if authorization fails (fail-closed)
        """
        import time

        with tracer.start_as_current_span("semantic_index.search_tools") as span:
            start_time = time.monotonic()
            span.set_attribute("query", query)
            span.set_attribute("user_id", user_id)
            span.set_attribute("limit", limit)

            # Authorization check: user must have viewer access to tool_index
            authorized = await self._check_authorization(
                user_id=user_id,
                relation="viewer",
                object_type="tool_index",
            )
            if not authorized:
                logger.warning(f"User {user_id} denied access to tool_index")
                span.set_attribute("authorized", False)
                return []

            # Tenant membership check if tenant_id is specified
            if tenant_id:
                is_member = await self._check_tenant_membership(user_id, tenant_id)
                if not is_member:
                    logger.warning(f"User {user_id} not member of tenant {tenant_id}")
                    span.set_attribute("tenant_authorized", False)
                    return []

            span.set_attribute("authorized", True)

            # Check query cache (after authorization to prevent cache leaks)
            cache_key = self._make_query_cache_key(
                query=query,
                search_type="tools",
                user_id=user_id,
                limit=limit,
                category=category,
                scope=str(scope.value) if scope else None,
                tenant_id=tenant_id,
            )
            if self.query_cache_ttl_seconds > 0 and cache_key in self._query_cache:
                self._query_cache_hits += 1
                cached_results: list[ToolIndexEntry] = self._query_cache[cache_key]
                span.set_attribute("cache_hit", True)
                span.set_attribute("results_count", len(cached_results))
                logger.debug(f"Query cache hit for tools search: {cache_key}")
                emit_cache_hit_metric(cache_type="query", result="hit")
                # Emit search metric with cache hit
                duration = time.monotonic() - start_time
                emit_tool_search_metric(
                    duration_seconds=duration,
                    results_count=len(cached_results),
                    cache_hit=True,
                    user_id=user_id,
                )
                return cached_results

            self._query_cache_misses += 1
            emit_cache_hit_metric(cache_type="query", result="miss")

            # Generate query embedding (with caching)
            embedding_cache_key = self._make_embedding_cache_key(query)
            if self.embedding_cache_ttl_seconds > 0 and embedding_cache_key in self._embedding_cache:
                self._embedding_cache_hits += 1
                query_embedding = self._embedding_cache[embedding_cache_key]
                logger.debug(f"Embedding cache hit for query: {embedding_cache_key}")
                emit_cache_hit_metric(cache_type="embedding", result="hit")
            else:
                self._embedding_cache_misses += 1
                emit_cache_hit_metric(cache_type="embedding", result="miss")
                query_embedding = await asyncio.to_thread(self.embedder.embed_query, query)
                # Cache the embedding
                if self.embedding_cache_ttl_seconds > 0:
                    self._embedding_cache[embedding_cache_key] = query_embedding
                    logger.debug(f"Embedding cached for query: {embedding_cache_key}")

            # Build filter
            # NOTE: Using untyped list to satisfy qdrant_client Filter's union type requirements
            must_conditions = [FieldCondition(key="ref_type", match=MatchValue(value="tool"))]

            if category:
                must_conditions.append(FieldCondition(key="category", match=MatchValue(value=category)))

            if scope:
                must_conditions.append(FieldCondition(key="scope", match=MatchValue(value=str(scope.value))))

            if tenant_id:
                must_conditions.append(FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)))

            query_filter = Filter(must=must_conditions)  # type: ignore[arg-type]

            # Search using query_points (qdrant-client >= 1.7)
            response = await self.qdrant_client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                query_filter=query_filter,
                limit=limit,
                score_threshold=min_score,
            )
            results = response.points

            # Convert to ToolIndexEntry using shared wrapper (v26)
            # Uses reconstruct_tools_from_payloads() for validation and logging
            from mcp_server_langgraph.tools.semantic_index import (
                reconstruct_tools_from_payloads,
            )

            entries = reconstruct_tools_from_payloads(results, logger)

            # Cache the results
            if self.query_cache_ttl_seconds > 0:
                self._query_cache[cache_key] = entries
                logger.debug(f"Query cache stored for tools search: {cache_key}")

            # Emit search metric
            duration = time.monotonic() - start_time
            emit_tool_search_metric(
                duration_seconds=duration,
                results_count=len(entries),
                cache_hit=False,
                user_id=user_id,
            )

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
            # Store original ID for retrieval (Qdrant ID may be converted UUID)
            payload["_original_id"] = entry.skill_id

            # Convert string ID to valid Qdrant point ID (UUID)
            qdrant_id = string_to_qdrant_id(entry.skill_id)

            # Upsert to Qdrant
            point = PointStruct(
                id=qdrant_id,
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
        user_id: str,
        limit: int = 5,
        min_score: float = 0.5,
        category: str | None = None,
        tenant_id: str | None = None,
    ) -> list[SkillIndexEntry]:
        """Search for relevant skills using semantic similarity.

        Requires authorization: user_id must have 'viewer' relation on skill_index.

        Args:
            query: Search query
            user_id: User identifier for authorization (e.g., "user:alice")
            limit: Maximum number of results
            min_score: Minimum similarity score (0-1)
            category: Optional category filter
            tenant_id: Optional tenant ID for multi-tenant isolation

        Returns:
            List of matching SkillIndexEntry sorted by relevance
            Empty list if authorization fails (fail-closed)
        """
        with tracer.start_as_current_span("semantic_index.search_skills") as span:
            span.set_attribute("query", query)
            span.set_attribute("user_id", user_id)
            span.set_attribute("limit", limit)

            # Authorization check: user must have viewer access to skill_index
            authorized = await self._check_authorization(
                user_id=user_id,
                relation="viewer",
                object_type="skill_index",
            )
            if not authorized:
                logger.warning(f"User {user_id} denied access to skill_index")
                span.set_attribute("authorized", False)
                return []

            span.set_attribute("authorized", True)

            # Generate query embedding
            query_embedding = await asyncio.to_thread(self.embedder.embed_query, query)

            # Build filter
            # NOTE: Using untyped list to satisfy qdrant_client Filter's union type requirements
            must_conditions = [FieldCondition(key="ref_type", match=MatchValue(value="skill"))]

            if category:
                must_conditions.append(FieldCondition(key="category", match=MatchValue(value=category)))

            if tenant_id:
                must_conditions.append(FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)))

            query_filter = Filter(must=must_conditions)  # type: ignore[arg-type]

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
            # Store original ID for retrieval (Qdrant ID may be converted UUID)
            payload["_original_id"] = entry.memory_id

            # Convert string ID to valid Qdrant point ID (UUID)
            qdrant_id = string_to_qdrant_id(entry.memory_id)

            # Upsert to Qdrant
            point = PointStruct(
                id=qdrant_id,
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
        current_user_id: str,
        search_user_id: str,
        limit: int = 10,
        min_score: float = 0.5,
        memory_type: str | None = None,
        session_id: str | None = None,
        tenant_id: str | None = None,
    ) -> list[MemoryIndexEntry]:
        """Search for relevant memories using semantic similarity.

        Authorization:
        - Users can always search their own memories (current_user_id == search_user_id)
        - To search another user's memories, must have 'admin' relation on their memory_index
        - This protects user privacy while allowing admin access for debugging

        Args:
            query: Search query
            current_user_id: User making the request (e.g., "user:alice")
            search_user_id: User whose memories to search (e.g., "user:alice" or "user:bob")
            limit: Maximum number of results
            min_score: Minimum similarity score (0-1)
            memory_type: Optional memory type filter
            session_id: Optional session ID filter
            tenant_id: Optional tenant ID for multi-tenant isolation

        Returns:
            List of matching MemoryIndexEntry sorted by relevance
            Empty list if authorization fails (fail-closed)
        """
        with tracer.start_as_current_span("semantic_index.search_memories") as span:
            span.set_attribute("query", query)
            span.set_attribute("current_user_id", current_user_id)
            span.set_attribute("search_user_id", search_user_id)
            span.set_attribute("limit", limit)

            # Extract username from user_id (e.g., "user:alice" -> "alice")
            search_username = search_user_id.split(":")[-1] if ":" in search_user_id else search_user_id

            # Authorization check for memory access
            # Users can access their own memories, or must have admin access to others
            if current_user_id == search_user_id:
                # Accessing own memories - check viewer permission
                authorized = await self._check_authorization(
                    user_id=current_user_id,
                    relation="viewer",
                    object_type="memory_index",
                    object_id=search_username,
                )
            else:
                # Accessing another user's memories - need admin permission
                authorized = await self._check_authorization(
                    user_id=current_user_id,
                    relation="admin",
                    object_type="memory_index",
                    object_id=search_username,
                )

            if not authorized:
                logger.warning(f"User {current_user_id} denied access to memory_index:{search_username}")
                span.set_attribute("authorized", False)
                return []

            span.set_attribute("authorized", True)

            # Generate query embedding
            query_embedding = await asyncio.to_thread(self.embedder.embed_query, query)

            # Build filter
            # NOTE: Using untyped list to satisfy qdrant_client Filter's union type requirements
            must_conditions = [FieldCondition(key="ref_type", match=MatchValue(value="memory"))]

            if memory_type:
                must_conditions.append(FieldCondition(key="memory_type", match=MatchValue(value=memory_type)))

            if session_id:
                must_conditions.append(FieldCondition(key="session_id", match=MatchValue(value=session_id)))

            # Always filter by the search_user_id to ensure we only get that user's memories
            must_conditions.append(FieldCondition(key="user_id", match=MatchValue(value=search_user_id)))

            if tenant_id:
                must_conditions.append(FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)))

            query_filter = Filter(must=must_conditions)  # type: ignore[arg-type]

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

    # =========================================================================
    # Decision Trace Indexing and Precedent Search (ADR-0101 Context Graphs)
    # =========================================================================

    async def ensure_decision_collection(self) -> None:
        """Create decision traces collection if it doesn't exist.

        Only creates the collection if FF_ENABLE_PRECEDENT_SEARCH is true.
        The collection uses the same vector configuration as the main capability index.
        """
        if not feature_flags.enable_precedent_search:
            logger.debug("Precedent search disabled, skipping collection creation")
            return

        with tracer.start_as_current_span("semantic_index.ensure_decision_collection") as span:
            span.set_attribute("collection_name", DECISION_TRACE_COLLECTION)

            try:
                collections = await self.qdrant_client.get_collections()
                existing_names = {c.name for c in collections.collections}

                if DECISION_TRACE_COLLECTION not in existing_names:
                    logger.info(f"Creating collection: {DECISION_TRACE_COLLECTION}")
                    await self.qdrant_client.create_collection(
                        collection_name=DECISION_TRACE_COLLECTION,
                        vectors_config=VectorParams(
                            size=self.vector_size,
                            distance=Distance.COSINE,
                        ),
                    )
                    logger.info(f"Decision traces collection created: {DECISION_TRACE_COLLECTION}")
                else:
                    logger.debug(f"Decision traces collection already exists: {DECISION_TRACE_COLLECTION}")

            except Exception as e:
                logger.error(f"Failed to ensure decision traces collection: {e}")
                raise

    async def index_decision(
        self,
        trace_id: str,
        embedding_text: str,
        metadata: dict[str, Any],
    ) -> None:
        """Index a decision trace for precedent search.

        Creates an embedding from the embedding_text (typically query + rationale)
        and stores it in Qdrant for semantic similarity search.

        Args:
            trace_id: Unique identifier for the decision trace
            embedding_text: Text to embed (e.g., query + rationale)
            metadata: Additional metadata for filtering (decision_type, outcome, etc.)
        """
        if not feature_flags.enable_precedent_search:
            return

        with tracer.start_as_current_span("semantic_index.index_decision") as span:
            span.set_attribute("trace_id", trace_id)

            # Generate embedding
            embedding = await asyncio.to_thread(self.embedder.embed_query, embedding_text)

            # Build payload with metadata
            payload = {
                "trace_id": trace_id,
                "decision_type": metadata.get("decision_type"),
                "outcome": metadata.get("outcome"),
                "session_id": metadata.get("session_id"),
                "user_id": metadata.get("user_id"),
                "organization_id": metadata.get("organization_id"),
                # Store original ID for retrieval (Qdrant ID may be converted UUID)
                "_original_id": trace_id,
            }

            # Convert string ID to valid Qdrant point ID (UUID)
            qdrant_id = string_to_qdrant_id(trace_id)

            # Upsert to Qdrant
            point = PointStruct(
                id=qdrant_id,
                vector=embedding,
                payload=payload,
            )

            await self.qdrant_client.upsert(
                collection_name=DECISION_TRACE_COLLECTION,
                points=[point],
            )

            logger.debug(f"Indexed decision trace: {trace_id}")

    async def search_precedents(
        self,
        query: str,
        user_id: str,
        organization_id: str,
        limit: int = 10,
        min_score: float | None = None,
        decision_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar past decisions (precedents).

        Uses semantic similarity to find decisions that match the query.
        Filters by organization_id to ensure tenant isolation.

        Args:
            query: Search query (typically the current user query)
            user_id: User making the request
            organization_id: Organization for tenant isolation
            limit: Maximum number of results
            min_score: Minimum similarity score (defaults to feature flag value)
            decision_type: Optional filter by decision type

        Returns:
            List of dicts with trace_id, score, and decision_type
        """
        if not feature_flags.enable_precedent_search:
            return []

        with tracer.start_as_current_span("semantic_index.search_precedents") as span:
            span.set_attribute("query", query)
            span.set_attribute("user_id", user_id)
            span.set_attribute("organization_id", organization_id)
            span.set_attribute("limit", limit)

            # Use feature flag default if not specified
            if min_score is None:
                min_score = feature_flags.precedent_search_min_score

            # Generate query embedding
            query_embedding = await asyncio.to_thread(self.embedder.embed_query, query)

            # Build filter - always filter by organization for tenant isolation
            must_conditions = [
                FieldCondition(key="organization_id", match=MatchValue(value=organization_id)),
            ]

            if decision_type:
                must_conditions.append(FieldCondition(key="decision_type", match=MatchValue(value=decision_type)))

            query_filter = Filter(must=must_conditions)  # type: ignore[arg-type]

            # Search using query_points (qdrant-client >= 1.7)
            response = await self.qdrant_client.query_points(
                collection_name=DECISION_TRACE_COLLECTION,
                query=query_embedding,
                query_filter=query_filter,
                limit=limit,
                score_threshold=min_score,
            )
            results = response.points

            # Convert to list of dicts
            output = []
            for r in results:
                payload = r.payload or {}
                output.append(
                    {
                        "trace_id": payload.get("trace_id", str(r.id)),
                        "score": r.score,
                        "decision_type": payload.get("decision_type"),
                    }
                )

            span.set_attribute("results_count", len(output))
            return output


__all__ = [
    "SemanticIndexManager",
    "DECISION_TRACE_COLLECTION",
    "emit_auth_cache_metric",
    "emit_cache_hit_metric",
    "emit_tool_search_metric",
    "update_cache_size_gauge",
    "record_cache_warming_duration",
]
