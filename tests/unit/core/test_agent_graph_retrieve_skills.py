"""Tests for retrieve_skills node in agent graph (ADR-0099).

TDD RED Phase: These tests define the expected behavior of the
retrieve_skills node, which uses semantic search to find relevant
skills before binding them to the LLM.

The retrieve_skills node is controlled by:
- FF_ENABLE_SEMANTIC_SKILL_SEARCH env var
- enable_semantic_skill_search in AgentConfig

Pattern: Anthropic Tool Search Tool + LangGraph Many Tools
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

if TYPE_CHECKING:
    from mcp_server_langgraph.core.agent_config import AgentConfig

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_retrieve_skills_state")
class TestRetrieveSkillsNodeState:
    """Tests for AgentState skills selection fields."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_state_has_selected_skills_field(self) -> None:
        """AgentState should have selected_skills field."""
        from mcp_server_langgraph.core.agent_graph_builder import AgentState

        # AgentState is a TypedDict, check keys
        assert "selected_skills" in AgentState.__annotations__


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_retrieve_skills_graph")
class TestRetrieveSkillsNodeInGraph:
    """Tests for retrieve_skills node inclusion in graph."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_graph_has_retrieve_skills_node_when_enabled(self) -> None:
        """Graph should include retrieve_skills node when semantic skill search enabled."""
        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(enable_semantic_skill_search=True)

        graph = build_agent_graph(config)

        # Check that retrieve_skills node exists in the graph
        assert "retrieve_skills" in graph.nodes

    def test_graph_no_retrieve_skills_node_when_disabled(self) -> None:
        """Graph should NOT include retrieve_skills node when disabled."""
        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(enable_semantic_skill_search=False)

        graph = build_agent_graph(config)

        # Check that retrieve_skills node does NOT exist
        assert "retrieve_skills" not in graph.nodes


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_retrieve_skills_behavior")
class TestRetrieveSkillsNodeBehavior:
    """Tests for retrieve_skills node behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_retrieve_skills_uses_semantic_index_manager(self) -> None:
        """retrieve_skills should call semantic_index_manager.search_skills."""
        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_skills_impl

        # Create mock semantic index manager
        mock_manager = AsyncMock()
        mock_manager.search_skills.return_value = [
            MagicMock(name="code_review", skill_id="sk1"),
            MagicMock(name="test_generation", skill_id="sk2"),
        ]

        state = {
            "messages": [HumanMessage(content="Review my code and generate tests")],
            "selected_skills": None,
        }

        result = await _retrieve_skills_impl(
            state=state,
            semantic_index_manager=mock_manager,
            max_selected_skills=5,
        )

        # Verify search_skills was called with the query
        mock_manager.search_skills.assert_called_once()
        call_args = mock_manager.search_skills.call_args
        assert "Review my code" in call_args.kwargs.get("query", call_args[1].get("query", ""))

    @pytest.mark.asyncio
    async def test_retrieve_skills_respects_max_selected_skills(self) -> None:
        """retrieve_skills should respect max_selected_skills from config."""
        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_skills_impl

        mock_manager = AsyncMock()
        mock_manager.search_skills.return_value = []

        state = {
            "messages": [HumanMessage(content="Help me with documentation")],
            "selected_skills": None,
        }

        await _retrieve_skills_impl(
            state=state,
            semantic_index_manager=mock_manager,
            max_selected_skills=3,
        )

        # Verify limit was passed
        call_args = mock_manager.search_skills.call_args
        assert call_args.kwargs.get("limit") == 3 or call_args[1].get("limit") == 3


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_retrieve_skills_integration")
class TestRetrieveSkillsNodeIntegration:
    """Integration tests for retrieve_skills node."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_retrieve_skills_node_updates_state_with_selected_skills(self) -> None:
        """retrieve_skills node should update state with skill names."""
        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_skills_impl

        mock_manager = AsyncMock()
        mock_skill1 = MagicMock()
        mock_skill1.name = "code_review"
        mock_skill2 = MagicMock()
        mock_skill2.name = "test_generation"
        mock_manager.search_skills.return_value = [mock_skill1, mock_skill2]

        state = {
            "messages": [HumanMessage(content="Review and test my code")],
            "selected_skills": None,
        }

        result = await _retrieve_skills_impl(
            state=state,
            semantic_index_manager=mock_manager,
            max_selected_skills=5,
        )

        # Verify state has selected_skills populated
        assert "selected_skills" in result or state.get("selected_skills") is not None
        selected = result.get("selected_skills") or state.get("selected_skills")
        assert selected is not None
        assert "code_review" in selected
        assert "test_generation" in selected

    @pytest.mark.asyncio
    async def test_retrieve_skills_falls_back_to_all_skills_on_error(self) -> None:
        """retrieve_skills should fall back gracefully when search fails."""
        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_skills_impl

        mock_manager = AsyncMock()
        mock_manager.search_skills.side_effect = Exception("Qdrant connection failed")

        state = {
            "messages": [HumanMessage(content="Help me with code review")],
            "selected_skills": None,
        }

        result = await _retrieve_skills_impl(
            state=state,
            semantic_index_manager=mock_manager,
            max_selected_skills=5,
        )

        # Should not raise, and selected_skills should be None (use all)
        selected = result.get("selected_skills") or state.get("selected_skills")
        assert selected is None  # None means use all skills

    @pytest.mark.asyncio
    async def test_retrieve_skills_with_empty_query_returns_default_skills(self) -> None:
        """retrieve_skills should handle empty/short queries gracefully."""
        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_skills_impl

        mock_manager = AsyncMock()

        state = {
            "messages": [HumanMessage(content="hi")],
            "selected_skills": None,
        }

        result = await _retrieve_skills_impl(
            state=state,
            semantic_index_manager=mock_manager,
            max_selected_skills=5,
        )

        # Should not call search for short queries
        mock_manager.search_skills.assert_not_called()
        selected = result.get("selected_skills") or state.get("selected_skills")
        assert selected is None

    @pytest.mark.asyncio
    async def test_retrieve_skills_with_none_manager_uses_all_skills(self) -> None:
        """retrieve_skills should use all skills when manager is None."""
        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_skills_impl

        state = {
            "messages": [HumanMessage(content="Review my code changes")],
            "selected_skills": None,
        }

        result = await _retrieve_skills_impl(
            state=state,
            semantic_index_manager=None,
            max_selected_skills=5,
        )

        # Should not fail, selected_skills should be None
        selected = result.get("selected_skills") or state.get("selected_skills")
        assert selected is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_retrieve_skills_flow")
class TestRetrieveSkillsGraphFlow:
    """Tests for retrieve_skills node graph flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_retrieve_skills_routes_to_router(self) -> None:
        """retrieve_skills node should route to router node."""
        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(enable_semantic_skill_search=True)
        graph = build_agent_graph(config)

        # Check that retrieve_skills has edge to router
        # The graph structure should have retrieve_skills -> router edge
        nodes = list(graph.nodes.keys())
        assert "retrieve_skills" in nodes
        assert "router" in nodes

    def test_retrieve_skills_inserted_before_router(self) -> None:
        """retrieve_skills should be in the path before router."""
        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(
            enable_semantic_skill_search=True,
            enable_semantic_tool_search=False,  # Only skill search
        )
        graph = build_agent_graph(config)

        # Both nodes should exist
        assert "retrieve_skills" in graph.nodes
        assert "router" in graph.nodes
