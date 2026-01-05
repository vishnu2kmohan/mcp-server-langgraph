"""Tests for MemoryProgressiveLoader.

TDD: These tests define the contract for progressive loading
of memory context with tier-aware retrieval.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc
from datetime import datetime, UTC
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="memory_loader_basic")
class TestMemoryProgressiveLoaderBasic:
    """Tests for MemoryProgressiveLoader basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_memory_loader_exists(self) -> None:
        """Test MemoryProgressiveLoader class exists."""
        from mcp_server_langgraph.context.memory_loader import (
            MemoryProgressiveLoader,
        )

        assert MemoryProgressiveLoader is not None

    def test_memory_loader_has_load_method(self) -> None:
        """Test MemoryProgressiveLoader has load method."""
        from mcp_server_langgraph.context.memory_loader import (
            MemoryProgressiveLoader,
        )

        loader = MemoryProgressiveLoader()

        assert hasattr(loader, "load")

    def test_memory_loader_accepts_max_memories(self) -> None:
        """Test MemoryProgressiveLoader accepts max_memories parameter."""
        from mcp_server_langgraph.context.memory_loader import (
            MemoryProgressiveLoader,
        )

        loader = MemoryProgressiveLoader(max_memories=50)

        assert loader.max_memories == 50

    def test_memory_loader_accepts_max_tokens(self) -> None:
        """Test MemoryProgressiveLoader accepts max_tokens parameter."""
        from mcp_server_langgraph.context.memory_loader import (
            MemoryProgressiveLoader,
        )

        loader = MemoryProgressiveLoader(max_tokens=4000)

        assert loader.max_tokens == 4000


@pytest.mark.unit
@pytest.mark.xdist_group(name="memory_entry")
class TestMemoryEntry:
    """Tests for MemoryEntry dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_memory_entry_exists(self) -> None:
        """Test MemoryEntry dataclass exists."""
        from mcp_server_langgraph.context.memory_loader import MemoryEntry

        assert MemoryEntry is not None

    def test_memory_entry_has_id(self) -> None:
        """Test MemoryEntry has id field."""
        from mcp_server_langgraph.context.memory_loader import MemoryEntry

        entry = MemoryEntry(
            id="memory-123",
            content="Remember this",
            tier="session",
        )

        assert entry.id == "memory-123"

    def test_memory_entry_has_content(self) -> None:
        """Test MemoryEntry has content field."""
        from mcp_server_langgraph.context.memory_loader import MemoryEntry

        entry = MemoryEntry(
            id="memory-123",
            content="Important information",
            tier="session",
        )

        assert entry.content == "Important information"

    def test_memory_entry_has_tier(self) -> None:
        """Test MemoryEntry has tier field."""
        from mcp_server_langgraph.context.memory_loader import MemoryEntry

        entry = MemoryEntry(
            id="memory-123",
            content="Test",
            tier="durable",
        )

        assert entry.tier == "durable"

    def test_memory_entry_has_optional_relevance_score(self) -> None:
        """Test MemoryEntry has optional relevance_score field."""
        from mcp_server_langgraph.context.memory_loader import MemoryEntry

        entry = MemoryEntry(
            id="memory-123",
            content="Test",
            tier="session",
            relevance_score=0.85,
        )

        assert entry.relevance_score == 0.85

    def test_memory_entry_has_optional_created_at(self) -> None:
        """Test MemoryEntry has optional created_at field."""
        from mcp_server_langgraph.context.memory_loader import MemoryEntry

        now = datetime.now(UTC)
        entry = MemoryEntry(
            id="memory-123",
            content="Test",
            tier="session",
            created_at=now,
        )

        assert entry.created_at == now

    def test_memory_entry_has_optional_metadata(self) -> None:
        """Test MemoryEntry has optional metadata field."""
        from mcp_server_langgraph.context.memory_loader import MemoryEntry

        entry = MemoryEntry(
            id="memory-123",
            content="Test",
            tier="session",
            metadata={"source": "conversation"},
        )

        assert entry.metadata == {"source": "conversation"}


@pytest.mark.unit
@pytest.mark.xdist_group(name="loaded_memory")
class TestLoadedMemory:
    """Tests for LoadedMemory dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_loaded_memory_exists(self) -> None:
        """Test LoadedMemory dataclass exists."""
        from mcp_server_langgraph.context.memory_loader import LoadedMemory

        assert LoadedMemory is not None

    def test_loaded_memory_has_entries(self) -> None:
        """Test LoadedMemory has entries field."""
        from mcp_server_langgraph.context.memory_loader import (
            LoadedMemory,
            MemoryEntry,
        )

        entry = MemoryEntry(
            id="memory-123",
            content="Test",
            tier="session",
        )
        context = LoadedMemory(
            entries=[entry],
            total_tokens=100,
            was_truncated=False,
        )

        assert len(context.entries) == 1
        assert context.entries[0] is entry

    def test_loaded_memory_has_total_tokens(self) -> None:
        """Test LoadedMemory has total_tokens field."""
        from mcp_server_langgraph.context.memory_loader import LoadedMemory

        context = LoadedMemory(
            entries=[],
            total_tokens=500,
            was_truncated=False,
        )

        assert context.total_tokens == 500

    def test_loaded_memory_has_was_truncated(self) -> None:
        """Test LoadedMemory has was_truncated field."""
        from mcp_server_langgraph.context.memory_loader import LoadedMemory

        context = LoadedMemory(
            entries=[],
            total_tokens=500,
            was_truncated=True,
        )

        assert context.was_truncated is True

    def test_loaded_memory_has_tiers_loaded(self) -> None:
        """Test LoadedMemory has tiers_loaded field."""
        from mcp_server_langgraph.context.memory_loader import LoadedMemory

        context = LoadedMemory(
            entries=[],
            total_tokens=500,
            was_truncated=False,
            tiers_loaded=["working", "session"],
        )

        assert context.tiers_loaded == ["working", "session"]


@pytest.mark.unit
@pytest.mark.xdist_group(name="memory_loader_tiers")
class TestMemoryProgressiveLoaderTiers:
    """Tests for MemoryProgressiveLoader tier handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_default_tier_priority(self) -> None:
        """Test default tier priority order."""
        from mcp_server_langgraph.context.memory_loader import (
            MemoryProgressiveLoader,
        )

        loader = MemoryProgressiveLoader()

        # Working > Session > Durable > Artifact
        assert loader.tier_priority[0] == "working"
        assert "session" in loader.tier_priority
        assert "durable" in loader.tier_priority

    def test_custom_tier_priority(self) -> None:
        """Test custom tier priority can be provided."""
        from mcp_server_langgraph.context.memory_loader import (
            MemoryProgressiveLoader,
        )

        custom = ["durable", "session", "working"]
        loader = MemoryProgressiveLoader(tier_priority=custom)

        assert loader.tier_priority == custom


@pytest.mark.unit
@pytest.mark.xdist_group(name="memory_loader_load")
class TestMemoryProgressiveLoaderLoad:
    """Tests for MemoryProgressiveLoader.load() method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_load_returns_loaded_memory(self) -> None:
        """Test load() returns LoadedMemory."""
        from mcp_server_langgraph.context.memory_loader import (
            LoadedMemory,
            MemoryProgressiveLoader,
        )

        loader = MemoryProgressiveLoader()

        # Mock memory retrieval
        with patch.object(loader, "_retrieve_from_tier", return_value=[]):
            result = await loader.load(query="Find auth info", session_id="sess-123")

        assert isinstance(result, LoadedMemory)

    @pytest.mark.asyncio
    async def test_load_uses_query_for_relevance(self) -> None:
        """Test load() uses query to filter/score memories."""
        from mcp_server_langgraph.context.memory_loader import (
            MemoryEntry,
            MemoryProgressiveLoader,
        )

        loader = MemoryProgressiveLoader()

        test_entries = [
            MemoryEntry(id="1", content="Auth credentials", tier="session"),
            MemoryEntry(id="2", content="Random data", tier="session"),
        ]

        # Only return entries for session tier, empty for others
        def mock_retrieve(tier: str, session_id: str) -> list[MemoryEntry]:
            if tier == "session":
                return test_entries
            return []

        with patch.object(loader, "_retrieve_from_tier", side_effect=mock_retrieve):
            with patch.object(loader, "_score_relevance", side_effect=[0.9, 0.2]) as mock_score:
                await loader.load(query="authentication", session_id="sess-123")

        # Should have called score_relevance for each entry
        assert mock_score.call_count == 2

    @pytest.mark.asyncio
    async def test_load_respects_max_memories(self) -> None:
        """Test load() respects max_memories limit."""
        from mcp_server_langgraph.context.memory_loader import (
            MemoryEntry,
            MemoryProgressiveLoader,
        )

        loader = MemoryProgressiveLoader(max_memories=2)

        # Create many test entries
        test_entries = [MemoryEntry(id=f"{i}", content=f"Memory {i}", tier="session") for i in range(10)]

        with patch.object(loader, "_retrieve_from_tier", return_value=test_entries):
            with patch.object(loader, "_score_relevance", return_value=0.5):
                result = await loader.load(query="test", session_id="sess-123")

        assert len(result.entries) <= 2

    @pytest.mark.asyncio
    async def test_load_respects_max_tokens(self) -> None:
        """Test load() respects max_tokens limit."""
        from mcp_server_langgraph.context.memory_loader import (
            MemoryEntry,
            MemoryProgressiveLoader,
        )

        loader = MemoryProgressiveLoader(max_tokens=100)

        # Create entries with known content size
        test_entries = [MemoryEntry(id=f"{i}", content="x" * 200, tier="session") for i in range(5)]

        with patch.object(loader, "_retrieve_from_tier", return_value=test_entries):
            with patch.object(loader, "_score_relevance", return_value=0.5):
                result = await loader.load(query="test", session_id="sess-123")

        # Should truncate based on token limit
        assert result.was_truncated is True

    @pytest.mark.asyncio
    async def test_load_sorts_by_relevance(self) -> None:
        """Test load() returns entries sorted by relevance."""
        from mcp_server_langgraph.context.memory_loader import (
            MemoryEntry,
            MemoryProgressiveLoader,
        )

        loader = MemoryProgressiveLoader(max_memories=10)

        test_entries = [
            MemoryEntry(id="low", content="Low relevance", tier="session"),
            MemoryEntry(id="high", content="High relevance", tier="session"),
        ]

        def mock_score(entry: MemoryEntry, query: str) -> float:
            if "high" in entry.content.lower():
                return 0.9
            return 0.1

        with patch.object(loader, "_retrieve_from_tier", return_value=test_entries):
            with patch.object(loader, "_score_relevance", side_effect=mock_score):
                result = await loader.load(query="test", session_id="sess-123")

        # Entries should be sorted by relevance
        if len(result.entries) >= 2:
            assert result.entries[0].relevance_score >= result.entries[1].relevance_score

    @pytest.mark.asyncio
    async def test_load_includes_tiers_loaded(self) -> None:
        """Test load() includes which tiers were loaded."""
        from mcp_server_langgraph.context.memory_loader import (
            MemoryEntry,
            MemoryProgressiveLoader,
        )

        loader = MemoryProgressiveLoader()

        def mock_retrieve(tier: str, session_id: str) -> list[MemoryEntry]:
            if tier == "working":
                return [MemoryEntry(id="1", content="Working", tier="working")]
            elif tier == "session":
                return [MemoryEntry(id="2", content="Session", tier="session")]
            return []

        with patch.object(loader, "_retrieve_from_tier", side_effect=mock_retrieve):
            with patch.object(loader, "_score_relevance", return_value=0.5):
                result = await loader.load(query="test", session_id="sess-123")

        assert "working" in result.tiers_loaded
        assert "session" in result.tiers_loaded


@pytest.mark.unit
@pytest.mark.xdist_group(name="memory_loader_scope")
class TestMemoryProgressiveLoaderScope:
    """Tests for MemoryProgressiveLoader scope handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_accepts_scope_parameter(self) -> None:
        """Test MemoryProgressiveLoader accepts scope parameter."""
        from mcp_server_langgraph.context.memory_loader import (
            MemoryProgressiveLoader,
        )
        from mcp_server_langgraph.core.scopes import CapabilityScope

        loader = MemoryProgressiveLoader(scope=CapabilityScope.PROJECT)

        assert loader.scope == CapabilityScope.PROJECT

    def test_default_scope_is_session(self) -> None:
        """Test default scope is SESSION."""
        from mcp_server_langgraph.context.memory_loader import (
            MemoryProgressiveLoader,
        )
        from mcp_server_langgraph.core.scopes import CapabilityScope

        loader = MemoryProgressiveLoader()

        assert loader.scope == CapabilityScope.SESSION
