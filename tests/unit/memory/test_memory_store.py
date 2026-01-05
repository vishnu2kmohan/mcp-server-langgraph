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
@pytest.mark.xdist_group(name="memory_store_basic")
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
@pytest.mark.xdist_group(name="memory_store_storage")
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
@pytest.mark.xdist_group(name="memory_store_tiers")
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
@pytest.mark.xdist_group(name="memory_store_retrieval")
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
