"""Tests for MemoryStore with tier-based routing.

TDD: These tests define the contract for hierarchical memory storage
with tier-based persistence routing.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestMemoryStoreBasic:
    """Tests for MemoryStore basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_memory_store_exists(self) -> None:
        """Test MemoryStore class exists."""
        from mcp_server_langgraph.memory.store import MemoryStore

        assert MemoryStore is not None

    def test_memory_store_has_store_method(self) -> None:
        """Test MemoryStore has store method."""
        from mcp_server_langgraph.memory.store import MemoryStore

        store = MemoryStore()
        assert hasattr(store, "store")
        assert callable(store.store)

    def test_memory_store_has_retrieve_method(self) -> None:
        """Test MemoryStore has retrieve method."""
        from mcp_server_langgraph.memory.store import MemoryStore

        store = MemoryStore()
        assert hasattr(store, "retrieve")
        assert callable(store.retrieve)

    def test_memory_store_has_get_relevant_method(self) -> None:
        """Test MemoryStore has get_relevant method for semantic retrieval."""
        from mcp_server_langgraph.memory.store import MemoryStore

        store = MemoryStore()
        assert hasattr(store, "get_relevant")
        assert callable(store.get_relevant)


@pytest.mark.unit
class TestMemoryStoreStorage:
    """Tests for MemoryStore storage operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_store_returns_memory_id(self) -> None:
        """Test store() returns a memory ID."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.memory.store import MemoryStore
        from mcp_server_langgraph.memory.tiers import MemoryTier

        store = MemoryStore()
        memory_id = await store.store(
            content="Test memory",
            tier=MemoryTier.WORKING,
            scope=CapabilityScope.TASK,
        )

        assert memory_id is not None
        assert isinstance(memory_id, str)

    @pytest.mark.asyncio
    async def test_store_with_metadata(self) -> None:
        """Test store() accepts metadata."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.memory.store import MemoryStore
        from mcp_server_langgraph.memory.tiers import MemoryTier

        store = MemoryStore()
        memory_id = await store.store(
            content="Test memory with metadata",
            tier=MemoryTier.WORKING,
            scope=CapabilityScope.TASK,
            metadata={"key": "value"},
        )

        assert memory_id is not None

    @pytest.mark.asyncio
    async def test_retrieve_returns_content(self) -> None:
        """Test retrieve() returns stored content."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.memory.store import MemoryStore
        from mcp_server_langgraph.memory.tiers import MemoryTier

        store = MemoryStore()
        content = "Retrievable memory"
        memory_id = await store.store(
            content=content,
            tier=MemoryTier.WORKING,
            scope=CapabilityScope.TASK,
        )

        result = await store.retrieve(memory_id)
        assert result is not None
        assert result.content == content

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_returns_none(self) -> None:
        """Test retrieve() returns None for nonexistent ID."""
        from mcp_server_langgraph.memory.store import MemoryStore

        store = MemoryStore()
        result = await store.retrieve("nonexistent-id")
        assert result is None


@pytest.mark.unit
class TestMemoryStoreTierRouting:
    """Tests for MemoryStore tier-based routing."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_working_tier_stored_in_memory(self) -> None:
        """Test WORKING tier memories are stored in-memory."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.memory.store import MemoryStore
        from mcp_server_langgraph.memory.tiers import MemoryTier

        store = MemoryStore()
        memory_id = await store.store(
            content="Working memory",
            tier=MemoryTier.WORKING,
            scope=CapabilityScope.TASK,
        )

        # Should be stored in working memory dict
        assert memory_id in store._working_memory

    @pytest.mark.asyncio
    async def test_session_tier_stored_appropriately(self) -> None:
        """Test SESSION tier memories are stored for session."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.memory.store import MemoryStore
        from mcp_server_langgraph.memory.tiers import MemoryTier

        store = MemoryStore()
        memory_id = await store.store(
            content="Session memory",
            tier=MemoryTier.SESSION,
            scope=CapabilityScope.SESSION,
        )

        # Should be stored in session memory
        assert memory_id in store._session_memory


@pytest.mark.unit
class TestMemoryStoreRetrieval:
    """Tests for MemoryStore retrieval operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_relevant_returns_list(self) -> None:
        """Test get_relevant() returns a list of results."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.memory.store import MemoryStore
        from mcp_server_langgraph.memory.tiers import MemoryTier

        store = MemoryStore()

        # Store some memories
        await store.store(
            content="Python programming language",
            tier=MemoryTier.WORKING,
            scope=CapabilityScope.TASK,
        )

        results = await store.get_relevant(
            query="Python",
            scope=CapabilityScope.TASK,
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_relevant_respects_limit(self) -> None:
        """Test get_relevant() respects limit parameter."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.memory.store import MemoryStore
        from mcp_server_langgraph.memory.tiers import MemoryTier

        store = MemoryStore()

        # Store multiple memories
        for i in range(5):
            await store.store(
                content=f"Memory {i} about Python",
                tier=MemoryTier.WORKING,
                scope=CapabilityScope.TASK,
            )

        results = await store.get_relevant(
            query="Python",
            scope=CapabilityScope.TASK,
            limit=2,
        )

        assert len(results) <= 2


@pytest.mark.unit
class TestMemoryStoreSemanticSearch:
    """Tests for MemoryStore vector-based semantic search.

    TDD: These tests define the contract for vector-based memory retrieval.
    When embedding_service is provided, get_relevant uses semantic similarity.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_memory_store_accepts_embedding_service(self) -> None:
        """Test MemoryStore accepts embedding_service parameter."""
        from unittest.mock import MagicMock

        from mcp_server_langgraph.memory.store import MemoryStore

        mock_embeddings = MagicMock()
        store = MemoryStore(embedding_service=mock_embeddings)

        assert store.embedding_service is mock_embeddings

    def test_memory_store_accepts_vector_provider(self) -> None:
        """Test MemoryStore accepts vector_provider parameter."""
        from unittest.mock import MagicMock

        from mcp_server_langgraph.memory.store import MemoryStore

        mock_provider = MagicMock()
        store = MemoryStore(vector_provider=mock_provider)

        assert store.vector_provider is mock_provider

    def test_embedding_service_defaults_to_none(self) -> None:
        """Test embedding_service defaults to None."""
        from mcp_server_langgraph.memory.store import MemoryStore

        store = MemoryStore()
        assert store.embedding_service is None

    @pytest.mark.asyncio
    async def test_store_indexes_memory_when_embedding_service_provided(self) -> None:
        """Test store() indexes memory for semantic search when configured."""
        from unittest.mock import AsyncMock, MagicMock

        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.memory.store import MemoryStore
        from mcp_server_langgraph.memory.tiers import MemoryTier

        mock_embeddings = MagicMock()
        mock_embeddings.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        mock_provider = MagicMock()
        mock_provider.upsert = AsyncMock(return_value=None)

        store = MemoryStore(
            embedding_service=mock_embeddings,
            vector_provider=mock_provider,
        )

        await store.store(
            content="Important memory about Python",
            tier=MemoryTier.DURABLE,
            scope=CapabilityScope.PROJECT,
        )

        # Should have called embed and upsert
        mock_embeddings.embed.assert_called_once()
        mock_provider.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_relevant_uses_vector_search_when_configured(self) -> None:
        """Test get_relevant() uses vector search when embedding_service is provided."""
        from unittest.mock import AsyncMock, MagicMock

        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.memory.store import MemoryStore

        mock_embeddings = MagicMock()
        mock_embeddings.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        mock_provider = MagicMock()
        mock_provider.upsert = AsyncMock(return_value=None)
        mock_provider.search = AsyncMock(
            return_value=[
                {
                    "id": "memory-1",
                    "score": 0.95,
                    "metadata": {
                        "content": "Python is great for ML",
                        "tier": "DURABLE",
                    },
                }
            ]
        )

        store = MemoryStore(
            embedding_service=mock_embeddings,
            vector_provider=mock_provider,
        )

        results = await store.get_relevant(
            query="machine learning",
            scope=CapabilityScope.PROJECT,
            enable_semantic=True,
        )

        # Should have called search
        mock_provider.search.assert_called_once()
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_get_relevant_falls_back_to_keyword_when_not_configured(self) -> None:
        """Test get_relevant() uses keyword matching when no embedding_service."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.memory.store import MemoryStore
        from mcp_server_langgraph.memory.tiers import MemoryTier

        store = MemoryStore()  # No embedding service

        # Store a memory with keyword matching
        await store.store(
            content="Python programming language",
            tier=MemoryTier.WORKING,
            scope=CapabilityScope.TASK,
        )

        # Should still work with keyword fallback
        results = await store.get_relevant(
            query="Python",
            scope=CapabilityScope.TASK,
        )

        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_semantic_search_respects_min_score(self) -> None:
        """Test semantic search filters by min_score."""
        from unittest.mock import AsyncMock, MagicMock

        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.memory.store import MemoryStore

        mock_embeddings = MagicMock()
        mock_embeddings.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        mock_provider = MagicMock()
        mock_provider.search = AsyncMock(return_value=[])

        store = MemoryStore(
            embedding_service=mock_embeddings,
            vector_provider=mock_provider,
        )

        await store.get_relevant(
            query="test query",
            scope=CapabilityScope.PROJECT,
            enable_semantic=True,
            min_score=0.8,
        )

        # Check min_score was passed to search
        call_kwargs = mock_provider.search.call_args.kwargs
        assert call_kwargs.get("min_score") == 0.8
