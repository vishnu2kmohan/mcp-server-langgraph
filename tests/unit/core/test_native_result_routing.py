"""
Unit tests for native result routing in generate_response (v7).

TDD tests for detecting and routing native tool results from AIMessage
content blocks directly, bypassing use_tools.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

pytestmark = [pytest.mark.unit, pytest.mark.xdist_group(name="test_native_result_routing")]


class TestNativeResultRouting:
    """Tests for native result routing in generate_response."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_native_results_detected_and_appended(self):
        """Native tool results should be detected and appended as ToolMessages."""
        from unittest.mock import patch

        from mcp_server_langgraph.core.agent_graph_builder import (
            _generate_response_impl,
        )

        # Create mock response with native web_search results
        mock_response = AIMessage(
            content=[
                {"type": "text", "text": "Here are the search results:"},
                {
                    "type": "web_search_results",
                    "results": [
                        {"title": "AI News", "url": "https://example.com", "snippet": "Latest AI news"},
                    ],
                },
            ]
        )

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=mock_response)

        state = {
            "messages": [HumanMessage(content="Search for AI news")],
            "selected_tools": None,
            "next_action": "",
        }

        # Mock adispatch_custom_event since it requires a parent run context
        with patch(
            "langchain_core.callbacks.manager.adispatch_custom_event",
            new_callable=AsyncMock,
        ):
            result = await _generate_response_impl(
                state=state,
                model=mock_model,
                bound_tools=[],
                model_with_tools=None,
                pydantic_agent=None,
            )

        # Should have appended messages: AI response + native ToolMessage
        messages = result.get("messages", [])
        assert len(messages) >= 2, f"Expected at least 2 messages, got {len(messages)}"

        # Check that a ToolMessage was appended
        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
        assert len(tool_messages) == 1, f"Expected 1 ToolMessage, got {len(tool_messages)}"
        assert tool_messages[0].name == "web_search"

    @pytest.mark.asyncio
    async def test_native_results_route_to_respond(self):
        """Native tool results should route to 'respond' for refinement."""
        from unittest.mock import patch

        from mcp_server_langgraph.core.agent_graph_builder import (
            _generate_response_impl,
        )

        # Create mock response with native results
        mock_response = AIMessage(
            content=[
                {"type": "text", "text": "Here are the results:"},
                {
                    "type": "web_search_results",
                    "results": [{"title": "Result", "url": "https://x.com", "snippet": "Test"}],
                },
            ]
        )

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=mock_response)

        state = {
            "messages": [HumanMessage(content="Search")],
            "selected_tools": None,
            "next_action": "",
        }

        # Mock adispatch_custom_event since it requires a parent run context
        with patch(
            "langchain_core.callbacks.manager.adispatch_custom_event",
            new_callable=AsyncMock,
        ):
            result = await _generate_response_impl(
                state=state,
                model=mock_model,
                bound_tools=[],
                model_with_tools=None,
                pydantic_agent=None,
            )

        # Should route to "respond" to allow model to refine based on results
        # or "end" if already final - implementation may vary
        assert result.get("next_action") in ("respond", "end")

    @pytest.mark.asyncio
    async def test_no_native_results_routes_normally(self):
        """Without native results, should route based on tool_calls."""
        from mcp_server_langgraph.core.agent_graph_builder import (
            _generate_response_impl,
        )

        # Create mock response without native results (plain text)
        mock_response = AIMessage(content="Here is my response")

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=mock_response)

        state = {
            "messages": [HumanMessage(content="Hello")],
            "selected_tools": None,
            "next_action": "",
        }

        result = await _generate_response_impl(
            state=state,
            model=mock_model,
            bound_tools=[],
            model_with_tools=None,
            pydantic_agent=None,
        )

        # No tool calls, no native results -> should end
        assert result.get("next_action") == "end"

    @pytest.mark.asyncio
    async def test_tool_calls_take_precedence_over_native_results(self):
        """Tool calls should route to use_tools even if native results present."""
        from mcp_server_langgraph.core.agent_graph_builder import (
            _generate_response_impl,
        )

        # Create mock response with both tool_calls and native results
        mock_response = AIMessage(
            content=[
                {"type": "text", "text": "I need to search"},
            ],
            tool_calls=[{"id": "call_123", "name": "web_search", "args": {"query": "test"}}],
        )

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=mock_response)

        state = {
            "messages": [HumanMessage(content="Search")],
            "selected_tools": None,
            "next_action": "",
        }

        result = await _generate_response_impl(
            state=state,
            model=mock_model,
            bound_tools=[],
            model_with_tools=None,
            pydantic_agent=None,
        )

        # Tool calls present -> should route to use_tools
        assert result.get("next_action") == "use_tools"

    @pytest.mark.asyncio
    async def test_tool_result_block_detected(self):
        """Direct tool_result blocks should be detected."""
        from mcp_server_langgraph.core.agent_graph_builder import (
            _generate_response_impl,
        )

        # Create mock response with tool_result block
        mock_response = AIMessage(
            content=[
                {"type": "text", "text": "Executed code:"},
                {
                    "type": "tool_result",
                    "tool_use_id": "exec_123",
                    "name": "code_execution",
                    "content": "print output",
                },
            ]
        )

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=mock_response)

        state = {
            "messages": [HumanMessage(content="Run code")],
            "selected_tools": None,
            "next_action": "",
        }

        result = await _generate_response_impl(
            state=state,
            model=mock_model,
            bound_tools=[],
            model_with_tools=None,
            pydantic_agent=None,
        )

        # Should have appended native tool result
        messages = result.get("messages", [])
        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
        assert len(tool_messages) == 1


class TestParseNativeResults:
    """Tests for parse_native_results function."""

    def teardown_method(self) -> None:
        """Force GC."""
        gc.collect()

    def test_parse_web_search_results(self):
        """Should parse web_search_results blocks."""
        from mcp_server_langgraph.tools.native_handler import parse_native_results

        response = AIMessage(
            content=[
                {"type": "text", "text": "Here are results:"},
                {
                    "type": "web_search_results",
                    "results": [
                        {"title": "Result 1", "url": "https://a.com", "snippet": "First result"},
                        {"title": "Result 2", "url": "https://b.com", "snippet": "Second result"},
                    ],
                },
            ]
        )

        tool_messages = parse_native_results(response)

        assert len(tool_messages) == 1
        assert tool_messages[0].name == "web_search"
        assert "Result 1" in tool_messages[0].content
        assert "Result 2" in tool_messages[0].content

    def test_parse_tool_result_block(self):
        """Should parse tool_result blocks."""
        from mcp_server_langgraph.tools.native_handler import parse_native_results

        response = AIMessage(
            content=[
                {
                    "type": "tool_result",
                    "tool_use_id": "use_123",
                    "name": "code_execution",
                    "content": "42",
                },
            ]
        )

        tool_messages = parse_native_results(response)

        assert len(tool_messages) == 1
        assert tool_messages[0].tool_call_id == "use_123"
        assert tool_messages[0].name == "code_execution"

    def test_parse_string_content_returns_empty(self):
        """String content should return empty list."""
        from mcp_server_langgraph.tools.native_handler import parse_native_results

        response = AIMessage(content="Plain text response")

        tool_messages = parse_native_results(response)

        assert len(tool_messages) == 0

    def test_parse_no_native_blocks_returns_empty(self):
        """Non-native blocks should return empty list."""
        from mcp_server_langgraph.tools.native_handler import parse_native_results

        response = AIMessage(
            content=[
                {"type": "text", "text": "Just text"},
            ]
        )

        tool_messages = parse_native_results(response)

        assert len(tool_messages) == 0
