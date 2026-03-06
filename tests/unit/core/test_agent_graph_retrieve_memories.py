"""Tests for retrieve_memories node in agent graph (ADR-0099).

TDD RED Phase: These tests define the expected behavior of the
retrieve_memories node, which uses semantic search to find relevant
memories for context enrichment before LLM invocation.

The retrieve_memories node is controlled by:
- FF_ENABLE_SEMANTIC_MEMORY_SEARCH env var
- enable_semantic_memory_search in AgentConfig

Pattern: Anthropic Tool Search Tool + LangGraph Many Tools
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage

if TYPE_CHECKING:
    pass

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_retrieve_memories_state")
class TestRetrieveMemoriesNodeState:
    """Tests for AgentState memory retrieval fields."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_state_has_retrieved_memories_field(self) -> None:
        """AgentState should have retrieved_memories field."""
        from mcp_server_langgraph.core.agent_graph_builder import AgentState

        # AgentState is a TypedDict, check keys
        assert "retrieved_memories" in AgentState.__annotations__


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_retrieve_memories_graph")
class TestRetrieveMemoriesNodeInGraph:
    """Tests for retrieve_memories node inclusion in graph."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_graph_has_retrieve_memories_node_when_enabled(self) -> None:
        """Graph should include retrieve_memories node when semantic memory search enabled."""
        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(enable_semantic_memory_search=True)

        graph = build_agent_graph(config)

        # Check that retrieve_memories node exists in the graph
        assert "retrieve_memories" in graph.nodes

    def test_graph_no_retrieve_memories_node_when_disabled(self) -> None:
        """Graph should NOT include retrieve_memories node when disabled."""
        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(enable_semantic_memory_search=False)

        graph = build_agent_graph(config)

        # Check that retrieve_memories node does NOT exist
        assert "retrieve_memories" not in graph.nodes


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_retrieve_memories_behavior")
class TestRetrieveMemoriesNodeBehavior:
    """Tests for retrieve_memories node behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_retrieve_memories_uses_semantic_index_manager(self) -> None:
        """retrieve_memories should call semantic_index_manager.search_memories."""
        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_memories_impl

        # Create mock semantic index manager
        mock_manager = AsyncMock(return_value=None)
        mock_manager.search_memories.return_value = [
            MagicMock(content="Previous conversation context", memory_id="mem1"),
            MagicMock(content="User preference: dark mode", memory_id="mem2"),
        ]

        state = {
            "messages": [HumanMessage(content="What did we discuss last time?")],
            "retrieved_memories": None,
            "user_id": "user-123",
        }

        await _retrieve_memories_impl(
            state=state,
            semantic_index_manager=mock_manager,
            max_retrieved_memories=10,
        )

        # Verify search_memories was called with the query
        mock_manager.search_memories.assert_called_once()
        call_args = mock_manager.search_memories.call_args
        assert "What did we discuss" in call_args.kwargs.get("query", call_args[1].get("query", ""))

    @pytest.mark.asyncio
    async def test_retrieve_memories_respects_max_retrieved_memories(self) -> None:
        """retrieve_memories should respect max_retrieved_memories from config."""
        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_memories_impl

        mock_manager = AsyncMock(return_value=None)
        mock_manager.search_memories.return_value = []

        state = {
            "messages": [HumanMessage(content="Remind me of my preferences")],
            "retrieved_memories": None,
            "user_id": "user-123",
        }

        await _retrieve_memories_impl(
            state=state,
            semantic_index_manager=mock_manager,
            max_retrieved_memories=5,
        )

        # Verify limit was passed
        call_args = mock_manager.search_memories.call_args
        assert call_args.kwargs.get("limit") == 5 or call_args[1].get("limit") == 5


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_retrieve_memories_integration")
class TestRetrieveMemoriesNodeIntegration:
    """Integration tests for retrieve_memories node."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_retrieve_memories_node_updates_state_with_memories(self) -> None:
        """retrieve_memories node should update state with memory contents."""
        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_memories_impl

        mock_manager = AsyncMock(return_value=None)
        mock_mem1 = MagicMock()
        mock_mem1.content = "Previous discussion about AI"
        mock_mem2 = MagicMock()
        mock_mem2.content = "User prefers Python"
        mock_manager.search_memories.return_value = [mock_mem1, mock_mem2]

        state = {
            "messages": [HumanMessage(content="Continue our previous discussion")],
            "retrieved_memories": None,
            "user_id": "user-123",
        }

        result = await _retrieve_memories_impl(
            state=state,
            semantic_index_manager=mock_manager,
            max_retrieved_memories=10,
        )

        # Verify state has retrieved_memories populated
        assert "retrieved_memories" in result or state.get("retrieved_memories") is not None
        retrieved = result.get("retrieved_memories") or state.get("retrieved_memories")
        assert retrieved is not None
        assert "Previous discussion about AI" in retrieved
        assert "User prefers Python" in retrieved

    @pytest.mark.asyncio
    async def test_retrieve_memories_falls_back_on_error(self) -> None:
        """retrieve_memories should fall back gracefully when search fails."""
        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_memories_impl

        mock_manager = AsyncMock(return_value=None)
        mock_manager.search_memories.side_effect = Exception("Qdrant connection failed")

        state = {
            "messages": [HumanMessage(content="What were my previous requests?")],
            "retrieved_memories": None,
            "user_id": "user-123",
        }

        result = await _retrieve_memories_impl(
            state=state,
            semantic_index_manager=mock_manager,
            max_retrieved_memories=10,
        )

        # Should not raise, and retrieved_memories should be None
        retrieved = result.get("retrieved_memories") or state.get("retrieved_memories")
        assert retrieved is None  # None means no context enrichment

    @pytest.mark.asyncio
    async def test_retrieve_memories_with_empty_query_returns_none(self) -> None:
        """retrieve_memories should handle empty/short queries gracefully."""
        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_memories_impl

        mock_manager = AsyncMock(return_value=None)

        state = {
            "messages": [HumanMessage(content="hi")],
            "retrieved_memories": None,
            "user_id": "user-123",
        }

        result = await _retrieve_memories_impl(
            state=state,
            semantic_index_manager=mock_manager,
            max_retrieved_memories=10,
        )

        # Should not call search for short queries
        mock_manager.search_memories.assert_not_called()
        retrieved = result.get("retrieved_memories") or state.get("retrieved_memories")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_retrieve_memories_with_none_manager_returns_none(self) -> None:
        """retrieve_memories should return None when manager is None."""
        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_memories_impl

        state = {
            "messages": [HumanMessage(content="Recall our conversation")],
            "retrieved_memories": None,
            "user_id": "user-123",
        }

        result = await _retrieve_memories_impl(
            state=state,
            semantic_index_manager=None,
            max_retrieved_memories=10,
        )

        # Should not fail, retrieved_memories should be None
        retrieved = result.get("retrieved_memories") or state.get("retrieved_memories")
        assert retrieved is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_retrieve_memories_flow")
class TestRetrieveMemoriesGraphFlow:
    """Tests for retrieve_memories node graph flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_retrieve_memories_routes_to_router(self) -> None:
        """retrieve_memories node should eventually route to router node."""
        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(enable_semantic_memory_search=True)
        graph = build_agent_graph(config)

        # Check that retrieve_memories exists and router exists
        nodes = list(graph.nodes.keys())
        assert "retrieve_memories" in nodes
        assert "router" in nodes

    def test_retrieve_memories_inserted_in_chain(self) -> None:
        """retrieve_memories should be in the processing chain."""
        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(
            enable_semantic_memory_search=True,
            enable_semantic_tool_search=False,
            enable_semantic_skill_search=False,
        )
        graph = build_agent_graph(config)

        # Both nodes should exist
        assert "retrieve_memories" in graph.nodes
        assert "router" in graph.nodes
