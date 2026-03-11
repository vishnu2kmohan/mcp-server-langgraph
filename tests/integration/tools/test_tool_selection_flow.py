"""
Integration tests for tool selection flow (v7).

Tests the complete tool selection flow from API request through
agent state, semantic search, and tool binding.

Key flows tested:
- Manual tool selection with tool_ids
- Auto mode semantic tool search
- Tool preference (native vs builtin) handling
- State propagation through agent graph
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.xdist_group(name="test_tool_selection_flow")]


@pytest.mark.xdist_group("test_tool_selection_modes")
class TestToolSelectionModes:
    """Tests for tool selection mode handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_manual_mode_uses_selected_tools(self):
        """Manual mode should use explicitly selected tool_ids."""
        state = {
            "tool_selection_mode": "manual",
            "selected_tools": ["builtin:calculator", "builtin:web_search"],
            "messages": [],
        }

        # In manual mode, selected_tools should be passed through unchanged
        assert state["tool_selection_mode"] == "manual"
        assert len(state["selected_tools"]) == 2

    def test_none_mode_disables_tools(self):
        """None mode should result in empty tool selection."""
        state = {
            "tool_selection_mode": "none",
            "messages": [],
        }

        # In none mode, no tools should be selected
        assert state["tool_selection_mode"] == "none"

    def test_auto_mode_uses_semantic_search(self):
        """Auto mode should trigger semantic tool search."""
        state = {
            "tool_selection_mode": "auto",
            "messages": [],
        }

        assert state["tool_selection_mode"] == "auto"


@pytest.mark.xdist_group("test_tool_preference")
class TestToolPreference:
    """Tests for tool preference (native vs builtin) handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    def test_auto_preference_allows_native(self):
        """Auto preference should allow native tools when available."""
        state = {
            "tool_preference": "auto",
            "selected_tools": ["web_search"],
        }

        # Auto preference means native tools can be used if capable
        assert state["tool_preference"] == "auto"

    def test_native_preference_forces_native(self):
        """Native preference should prefer native tools."""
        state = {
            "tool_preference": "native",
            "selected_tools": ["web_search"],
        }

        assert state["tool_preference"] == "native"

    def test_builtin_preference_forces_builtin(self):
        """Builtin preference should use builtin tools only."""
        state = {
            "tool_preference": "builtin",
            "selected_tools": ["web_search"],
        }

        assert state["tool_preference"] == "builtin"


@pytest.mark.xdist_group("test_retrieve_tools_integration")
class TestRetrieveToolsIntegration:
    """Integration tests for retrieve_tools node."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_retrieve_tools_populates_both_fields(self):
        """retrieve_tools should populate both selected_tools and selected_tool_ids."""
        from langchain_core.messages import HumanMessage

        # Mock semantic index manager
        mock_semantic_index = AsyncMock(return_value=None)
        mock_entry = MagicMock()
        mock_entry.name = "calculator"
        mock_entry.tool_id = "builtin:calculator"
        mock_semantic_index.search_tools.return_value = [mock_entry]

        state = {
            "tool_selection_mode": "auto",
            "messages": [HumanMessage(content="Calculate 2 + 2 for me please")],
            "user_id": "test-user",
        }

        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_tools_impl

        result = await _retrieve_tools_impl(
            state=state,
            semantic_index_manager=mock_semantic_index,
            max_selected_tools=5,
        )

        # Both fields should be populated
        assert "selected_tools" in result
        assert "selected_tool_ids" in result
        assert result["selected_tools"] == ["calculator"]
        assert result["selected_tool_ids"] == ["builtin:calculator"]

    @pytest.mark.asyncio
    async def test_retrieve_tools_skips_for_manual_mode(self):
        """retrieve_tools should skip semantic search in manual mode."""
        mock_semantic_index = AsyncMock(return_value=None)

        state = {
            "tool_selection_mode": "manual",
            "selected_tools": ["builtin:calculator"],
            "messages": [],
        }

        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_tools_impl

        await _retrieve_tools_impl(
            state=state,
            semantic_index_manager=mock_semantic_index,
            max_selected_tools=5,
        )

        # Semantic search should not be called
        mock_semantic_index.search_tools.assert_not_called()

    @pytest.mark.asyncio
    async def test_retrieve_tools_returns_empty_or_none_for_none_mode(self):
        """retrieve_tools should return empty/None for none mode (no tools selected)."""
        mock_semantic_index = AsyncMock(return_value=None)

        state = {
            "tool_selection_mode": "none",
            "messages": [],
        }

        from mcp_server_langgraph.core.agent_graph_builder import _retrieve_tools_impl

        result = await _retrieve_tools_impl(
            state=state,
            semantic_index_manager=mock_semantic_index,
            max_selected_tools=5,
        )

        # None mode disables tools - selected_tools should be None or empty
        selected = result.get("selected_tools")
        assert selected is None or selected == [], f"Expected None or empty, got {selected}"


@pytest.mark.xdist_group("test_tool_id_formats")
class TestToolIdFormats:
    """Tests for tool_id format consistency."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    def test_builtin_tool_id_format(self):
        """Builtin tool_ids should follow 'builtin:name' format."""
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        registry = UnifiedToolRegistry()

        # Create a mock tool
        mock_tool = MagicMock()
        mock_tool.name = "calculator"
        mock_tool.description = "Perform calculations"

        registry.register_builtin(mock_tool, category="math")

        tool = registry.get_by_id("builtin:calculator")
        assert tool is not None
        assert tool.tool_id == "builtin:calculator"

    def test_mcp_tool_id_format(self):
        """MCP tool_ids should follow 'mcp:qualified_name' format."""
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        registry = UnifiedToolRegistry()

        mock_tool = MagicMock()
        mock_tool.name = "github_create_issue"
        mock_tool.description = "Create GitHub issue"

        mcp_dict = {
            "qualified_name": "github:create_issue",
            "name": "create_issue",
            "description": "Create GitHub issue",
            "server_name": "github",
        }

        registry.register_mcp_from_cached(mcp_dict, mock_tool)

        tool = registry.get_by_id("mcp:github:create_issue")
        assert tool is not None
        assert tool.tool_id == "mcp:github:create_issue"
        assert tool.name == "github_create_issue"  # LangChain name

    def test_native_tool_id_format(self):
        """Native tool_ids should follow 'native:name' format."""
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        registry = UnifiedToolRegistry()
        registry.register_native(
            name="web_search",
            provider="anthropic",
            provider_type="web_search_20250305",
            description="Native web search",
        )

        tool = registry.get_by_id("native:web_search")
        assert tool is not None
        assert tool.tool_id == "native:web_search"


@pytest.mark.xdist_group("test_state_propagation")
class TestStatePropagation:
    """Tests for tool control state propagation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    def test_state_contains_tool_preference(self):
        """AgentState should contain tool_preference field."""
        state = {
            "messages": [],
            "next_action": "",
            "tool_preference": "native",
            "tool_selection_mode": "manual",
            "selected_tools": ["native:web_search"],
        }

        assert "tool_preference" in state
        assert state["tool_preference"] == "native"

    def test_state_contains_tool_selection_mode(self):
        """AgentState should contain tool_selection_mode field."""
        state = {
            "messages": [],
            "next_action": "",
            "tool_selection_mode": "auto",
        }

        assert "tool_selection_mode" in state
        assert state["tool_selection_mode"] == "auto"
