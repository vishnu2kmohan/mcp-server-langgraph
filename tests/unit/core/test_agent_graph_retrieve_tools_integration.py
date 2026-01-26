"""
Tests for SemanticIndexManager dependency injection in Agent Graph Builder.

TDD RED Phase: These tests verify the dependency injection of SemanticIndexManager
into the retrieve_tools node. They will fail initially and pass after implementation.

Tests cover:
1. build_agent_graph accepts semantic_index_manager parameter
2. retrieve_tools node actually calls search_tools when manager is provided
3. retrieve_tools node populates state["selected_tools"] with tool names
4. Graceful fallback when manager is None or raises error
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_semantic_index_di")
class TestSemanticIndexManagerDependencyInjection:
    """Tests for SemanticIndexManager dependency injection into build_agent_graph."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_build_agent_graph_accepts_semantic_index_manager_parameter(
        self, monkeypatch
    ) -> None:
        """build_agent_graph should accept optional semantic_index_manager parameter."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(
            enable_semantic_tool_search=True,
            enable_verification=False,
            enable_context_compaction=False,
        )

        # Create mock semantic index manager
        mock_semantic_index = AsyncMock(return_value=None)
        mock_semantic_index.search_tools = AsyncMock(return_value=[])

        # Should not raise - parameter should be accepted
        graph = build_agent_graph(
            config=config,
            semantic_index_manager=mock_semantic_index,
        )

        assert graph is not None
        assert "retrieve_tools" in graph.nodes

    @pytest.mark.asyncio
    async def test_build_agent_graph_works_without_semantic_index_manager(
        self, monkeypatch
    ) -> None:
        """build_agent_graph should work when semantic_index_manager is not provided."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(
            enable_semantic_tool_search=True,
            enable_verification=False,
            enable_context_compaction=False,
        )

        # Should work without semantic_index_manager (graceful fallback)
        graph = build_agent_graph(config=config)

        assert graph is not None
        assert "retrieve_tools" in graph.nodes


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_retrieve_tools_calls_manager")
class TestSelectToolsCallsSemanticIndexManager:
    """Tests verifying retrieve_tools actually calls SemanticIndexManager."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_retrieve_tools_calls_search_tools_with_query(
        self, monkeypatch
    ) -> None:
        """retrieve_tools should call semantic_index_manager.search_tools with query."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_tools_impl
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        # Create mock entries
        mock_entries = [
            ToolIndexEntry(
                tool_id="tool-1",
                name="calculator",
                description="Perform calculations",
                category="math",
            ),
            ToolIndexEntry(
                tool_id="tool-2",
                name="search",
                description="Search the web",
                category="search",
            ),
        ]

        # Create mock semantic index manager
        mock_semantic_index = AsyncMock(return_value=None)
        mock_semantic_index.search_tools = AsyncMock(return_value=mock_entries)

        # Create test state with a message
        initial_state = {
            "messages": [HumanMessage(content="Calculate the sum of 2 and 3")],
            "selected_tools": None,
        }

        # Call the helper function directly
        result = await _retrieve_tools_impl(
            state=initial_state,
            semantic_index_manager=mock_semantic_index,
            max_selected_tools=10,
        )

        # Verify search_tools was called
        mock_semantic_index.search_tools.assert_called_once()

        # Verify the query was passed (should contain the message content)
        call_kwargs = mock_semantic_index.search_tools.call_args
        assert call_kwargs is not None
        assert "Calculate the sum of 2 and 3" in call_kwargs.kwargs.get("query", "")

    @pytest.mark.asyncio
    async def test_retrieve_tools_populates_selected_tools_with_names(
        self, monkeypatch
    ) -> None:
        """retrieve_tools should populate state['selected_tools'] with tool names."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_tools_impl
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        # Create mock entries
        mock_entries = [
            ToolIndexEntry(
                tool_id="tool-1",
                name="calculator",
                description="Perform calculations",
                category="math",
            ),
            ToolIndexEntry(
                tool_id="tool-2",
                name="search",
                description="Search the web",
                category="search",
            ),
        ]

        # Create mock semantic index manager
        mock_semantic_index = AsyncMock(return_value=None)
        mock_semantic_index.search_tools = AsyncMock(return_value=mock_entries)

        # Create test state
        initial_state = {
            "messages": [HumanMessage(content="Calculate the sum of numbers")],
            "selected_tools": None,
        }

        # Call the helper function directly
        result = await _retrieve_tools_impl(
            state=initial_state,
            semantic_index_manager=mock_semantic_index,
            max_selected_tools=10,
        )

        # Verify selected_tools contains the tool names
        assert initial_state["selected_tools"] == ["calculator", "search"]

    @pytest.mark.asyncio
    async def test_retrieve_tools_uses_config_max_selected_tools(
        self, monkeypatch
    ) -> None:
        """retrieve_tools should pass max_selected_tools to search_tools."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_tools_impl

        # Create mock semantic index manager
        mock_semantic_index = AsyncMock(return_value=None)
        mock_semantic_index.search_tools = AsyncMock(return_value=[])

        # Create test state
        initial_state = {
            "messages": [HumanMessage(content="Search for Python tutorials")],
            "selected_tools": None,
        }

        # Call the helper function with custom limit
        await _retrieve_tools_impl(
            state=initial_state,
            semantic_index_manager=mock_semantic_index,
            max_selected_tools=5,  # Custom limit
        )

        # Verify limit was passed to search_tools
        mock_semantic_index.search_tools.assert_called_once()
        call_kwargs = mock_semantic_index.search_tools.call_args
        # Should include limit=5
        assert call_kwargs is not None
        assert call_kwargs.kwargs.get("limit") == 5


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_retrieve_tools_fallback")
class TestSelectToolsFallbackBehavior:
    """Tests for graceful fallback behavior in retrieve_tools."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_retrieve_tools_falls_back_when_manager_not_provided(
        self, monkeypatch
    ) -> None:
        """retrieve_tools should use all tools when semantic_index_manager is None."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_tools_impl

        # Create test state
        initial_state = {
            "messages": [HumanMessage(content="Calculate something")],
            "selected_tools": None,
        }

        # Call with no semantic_index_manager
        result = await _retrieve_tools_impl(
            state=initial_state,
            semantic_index_manager=None,
            max_selected_tools=10,
        )

        # Should fall back to None (use all tools)
        assert initial_state["selected_tools"] is None

    @pytest.mark.asyncio
    async def test_retrieve_tools_falls_back_when_search_fails(
        self, monkeypatch
    ) -> None:
        """retrieve_tools should fall back to all tools when search_tools raises."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_tools_impl

        # Create mock that raises an error
        mock_semantic_index = AsyncMock(return_value=None)
        mock_semantic_index.search_tools = AsyncMock(
            side_effect=Exception("Search failed")
        )

        # Create test state
        initial_state = {
            "messages": [HumanMessage(content="Search for something")],
            "selected_tools": None,
        }

        # Should not raise - graceful fallback
        result = await _retrieve_tools_impl(
            state=initial_state,
            semantic_index_manager=mock_semantic_index,
            max_selected_tools=10,
        )

        # Should fall back to None (use all tools) on error
        assert initial_state["selected_tools"] is None

    @pytest.mark.asyncio
    async def test_retrieve_tools_falls_back_when_search_returns_empty(
        self, monkeypatch
    ) -> None:
        """retrieve_tools should fall back when search returns no results."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_tools_impl

        # Create mock that returns empty list
        mock_semantic_index = AsyncMock(return_value=None)
        mock_semantic_index.search_tools = AsyncMock(return_value=[])

        # Create test state
        initial_state = {
            "messages": [HumanMessage(content="Search for something obscure")],
            "selected_tools": None,
        }

        # Call the helper function
        result = await _retrieve_tools_impl(
            state=initial_state,
            semantic_index_manager=mock_semantic_index,
            max_selected_tools=10,
        )

        # Empty list means no specific tools - should use all tools
        assert initial_state["selected_tools"] is None
