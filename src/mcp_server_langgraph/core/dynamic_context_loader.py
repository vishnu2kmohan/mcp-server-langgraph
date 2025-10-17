"""
Dynamic Context Loading with Qdrant Vector Store

Implements Anthropic's Just-in-Time context loading strategy:
- Semantic search for relevant context
- Progressive discovery patterns
- Lightweight context references
"""

import asyncio
import base64
import time
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Optional, Union

from cryptography.fernet import Fernet
from langchain_core.embeddings import Embeddings
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

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer
from mcp_server_langgraph.utils.response_optimizer import count_tokens


def _create_embeddings(
    provider: str,
    model_name: str,
    google_api_key: Optional[str] = None,
    task_type: Optional[str] = None,
) -> Embeddings:
    """
    Create embeddings instance based on provider.

    Args:
        provider: "google" for Gemini API or "local" for sentence-transformers
        model_name: Model name (e.g., "models/text-embedding-004" or "all-MiniLM-L6-v2")
        google_api_key: Google API key (required for "google" provider)
        task_type: Task type for Google embeddings optimization

    Returns:
        Embeddings instance

    Raises:
        ValueError: If provider is unsupported or required API key is missing
    """
    if provider == "google":
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
        except ImportError:
            raise ImportError(
                "langchain-google-genai is required for Google embeddings. " "Install with: pip install langchain-google-genai"
            )

        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY is required for Google embeddings. " "Set via environment variable or Infisical.")

        # Create Google embeddings with task type optimization
        embeddings = GoogleGenerativeAIEmbeddings(
            model=model_name,
            google_api_key=google_api_key,
            task_type=task_type or "RETRIEVAL_DOCUMENT",
        )

        logger.info(
            "Initialized Google Gemini embeddings",
            extra={"model": model_name, "task_type": task_type},
        )

        return embeddings

    elif provider == "local":
        try:
            from sentence_transformers import SentenceTransformer

            class SentenceTransformerEmbeddings(Embeddings):
                """Wrapper to make SentenceTransformer compatible with LangChain Embeddings interface."""

                def __init__(self, model_name: str):
                    self.model = SentenceTransformer(model_name)

                def embed_documents(self, texts: list[str]) -> list[list[float]]:
                    """Embed multiple documents."""
                    embeddings = self.model.encode(texts)
                    return embeddings.tolist()

                def embed_query(self, text: str) -> list[float]:
                    """Embed a single query."""
                    embedding = self.model.encode(text)
                    return embedding.tolist()

            embeddings = SentenceTransformerEmbeddings(model_name)

            logger.info(
                "Initialized local sentence-transformers embeddings",
                extra={"model": model_name},
            )

            return embeddings

        except ImportError:
            raise ImportError(
                "sentence-transformers is required for local embeddings. " "Install with: pip install sentence-transformers"
            )

    else:
        raise ValueError(f"Unsupported embedding provider: {provider}. " f"Supported providers: 'google', 'local'")


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
        embedding_provider: str | None = None,
        embedding_dimensions: int | None = None,
        cache_size: int | None = None,
    ):
        """
        Initialize dynamic context loader with encryption and retention support.

        Args:
            qdrant_url: Qdrant server URL (defaults to settings.qdrant_url)
            qdrant_port: Qdrant server port (defaults to settings.qdrant_port)
            collection_name: Name of Qdrant collection (defaults to settings.qdrant_collection_name)
            embedding_model: Model name (defaults to settings.embedding_model_name)
            embedding_provider: "google" or "local" (defaults to settings.embedding_provider)
            embedding_dimensions: Embedding dimensions (defaults to settings.embedding_dimensions)
            cache_size: LRU cache size for loaded contexts (defaults to settings.context_cache_size)

        Note:
            For regulated workloads (HIPAA, GDPR, etc.):
            - Set enable_context_encryption=True in settings
            - Configure retention period with context_retention_days
            - For multi-tenant isolation, use enable_multi_tenant_isolation=True

            Migration from sentence-transformers:
            - Existing collections with different dimensions need recreation
            - Google embeddings (768) vs sentence-transformers (384)
        """
        self.qdrant_url = qdrant_url or settings.qdrant_url
        self.qdrant_port = qdrant_port or settings.qdrant_port
        self.collection_name = collection_name or settings.qdrant_collection_name

        # Embedding configuration
        self.embedding_provider = embedding_provider or settings.embedding_provider
        # Support both new and legacy config parameter names
        self.embedding_model_name = embedding_model or settings.embedding_model_name
        self.embedding_dim = embedding_dimensions or settings.embedding_dimensions

        cache_size = cache_size or settings.context_cache_size

        # Security & Compliance configuration
        self.enable_encryption = settings.enable_context_encryption
        self.retention_days = settings.context_retention_days
        self.enable_auto_deletion = settings.enable_auto_deletion

        # Initialize encryption if enabled
        self.cipher: Optional[Fernet] = None
        if self.enable_encryption:
            if not settings.context_encryption_key:
                raise ValueError(
                    "CRITICAL: Context encryption enabled but no encryption key configured. "
                    "Set CONTEXT_ENCRYPTION_KEY environment variable or configure via Infisical."
                )
            # Fernet requires base64-encoded 32-byte key
            try:
                self.cipher = Fernet(settings.context_encryption_key.encode())
            except Exception as e:
                raise ValueError(f"Invalid encryption key format: {e}. Generate with: Fernet.generate_key()")

        # Initialize Qdrant client
        self.client = QdrantClient(host=self.qdrant_url, port=self.qdrant_port)

        # Initialize embeddings
        self.embedder = _create_embeddings(
            provider=self.embedding_provider,
            model_name=self.embedding_model_name,
            google_api_key=settings.google_api_key,
            task_type=settings.embedding_task_type,
        )

        # Create collection if it doesn't exist
        self._ensure_collection_exists()

        # LRU cache for loaded contexts
        self._load_context_cached = lru_cache(maxsize=cache_size)(self._load_context_impl)

        logger.info(
            "DynamicContextLoader initialized",
            extra={
                "qdrant_url": self.qdrant_url,
                "collection": self.collection_name,
                "embedding_provider": self.embedding_provider,
                "embedding_model": self.embedding_model_name,
                "embedding_dim": self.embedding_dim,
                "encryption_enabled": self.enable_encryption,
                "retention_days": self.retention_days,
                "auto_deletion_enabled": self.enable_auto_deletion,
            },
        )

    def _encrypt_content(self, content: str) -> str:
        """
        Encrypt content for storage (encryption-at-rest).

        Args:
            content: Plain text content

        Returns:
            Base64-encoded encrypted content
        """
        if not self.cipher:
            return content

        encrypted_bytes = self.cipher.encrypt(content.encode())
        return base64.b64encode(encrypted_bytes).decode()

    def _decrypt_content(self, encrypted_content: str) -> str:
        """
        Decrypt content from storage.

        Args:
            encrypted_content: Base64-encoded encrypted content

        Returns:
            Decrypted plain text
        """
        if not self.cipher:
            return encrypted_content

        try:
            encrypted_bytes = base64.b64decode(encrypted_content.encode())
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}", exc_info=True)
            raise ValueError(f"Failed to decrypt content: {e}")

    def _calculate_expiry_timestamp(self) -> float:
        """Calculate expiry timestamp based on retention policy."""
        expiry_date = datetime.now(timezone.utc) + timedelta(days=self.retention_days)
        return expiry_date.timestamp()

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
                # Generate embedding using LangChain Embeddings interface
                embedding = await asyncio.to_thread(self.embedder.embed_query, content)

                # Encrypt content if encryption is enabled
                stored_content = self._encrypt_content(content) if self.enable_encryption else content

                # Calculate expiry timestamp for retention
                created_at = datetime.now(timezone.utc).timestamp()
                expires_at = self._calculate_expiry_timestamp()

                # Create point with encryption and retention support
                point = PointStruct(
                    id=ref_id,
                    vector=embedding,  # Already a list from embed_query
                    payload={
                        "ref_id": ref_id,
                        "ref_type": ref_type,
                        "summary": summary,
                        "content": stored_content,  # Encrypted if encryption enabled
                        "token_count": count_tokens(content),
                        "metadata": metadata or {},
                        "created_at": created_at,  # For retention tracking
                        "expires_at": expires_at,  # For auto-deletion
                        "encrypted": self.enable_encryption,  # Flag for decryption
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
                # Generate query embedding using LangChain Embeddings interface
                query_embedding = await asyncio.to_thread(self.embedder.embed_query, query)

                # Build filter
                search_filter = None
                if ref_type_filter:
                    search_filter = Filter(must=[FieldCondition(key="ref_type", match=MatchValue(value=ref_type_filter))])

                # Search Qdrant
                results = await asyncio.to_thread(
                    self.client.search,
                    collection_name=self.collection_name,
                    query_vector=query_embedding,  # Already a list from embed_query
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

            # Decrypt content if it was encrypted
            stored_content = payload["content"]
            is_encrypted = payload.get("encrypted", False)
            content = self._decrypt_content(stored_content) if is_encrypted else stored_content

            loaded = LoadedContext(
                reference=reference,
                content=content,  # Decrypted content
                token_count=payload["token_count"],
                loaded_at=time.time(),
            )

            logger.info(f"Loaded context: {ref_id}", extra={"token_count": loaded.token_count})

            return loaded

        except Exception as e:
            logger.error(f"Failed to load context {ref_id}: {e}", exc_info=True)
            metrics.failed_calls.add(1, {"operation": "load_context", "error": type(e).__name__})
            raise

    async def load_batch(self, references: list[ContextReference], max_tokens: int = 4000) -> list[LoadedContext]:
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
