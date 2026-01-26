"""
Tests for agent_graph_builder event dispatch.

TDD: These tests are written FIRST to define the expected behavior
of dynamic_context_loaded event emission in the load_dynamic_context node.

Bug Reference: chat.py:892 handles dynamic_context_loaded event, but
agent_graph_builder.py never dispatches it.

Tests verify:
1. dynamic_context_loaded event is dispatched when context is loaded
2. Event contains refs_count and tokens_loaded data
3. Event is not dispatched when no context is loaded
4. Event is not dispatched when kb_focus is "none"
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


@pytest.mark.xdist_group(name="agent_graph_builder_events")
class TestDynamicContextLoadedEvent:
    """Tests for dynamic_context_loaded event emission."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_event_dispatched_when_context_loaded(self) -> None:
        """GIVEN dynamic context loading returns contexts
        WHEN load_dynamic_context node executes
        THEN dynamic_context_loaded event should be dispatched

        This test uses the extracted _load_dynamic_context_impl function
        which is designed to be testable.
        """
        from langchain_core.messages import HumanMessage

        # Mock the context and context loader
        mock_context = MagicMock()
        mock_context.token_count = 500

        mock_context_loader = MagicMock()
        mock_context_loader.to_messages = MagicMock(return_value=[])

        # Patch search_and_load_context at the module where it's imported
        with (
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader.search_and_load_context",
                new=AsyncMock(return_value=[mock_context]),
            ),
            patch(
                "langchain_core.callbacks.manager.adispatch_custom_event",
                new=AsyncMock(return_value=None),
            ) as mock_dispatch,
        ):
            from mcp_server_langgraph.core.agent_graph_builder import (
                _load_dynamic_context_impl,
            )

            state: dict[str, Any] = {
                "messages": [HumanMessage(content="Tell me about Python")],
                "next_action": "",
                "kb_focus": "all",
            }

            await _load_dynamic_context_impl(
                state=state,
                context_loader=mock_context_loader,
                top_k=3,
                max_tokens=2000,
            )

            # Verify event was dispatched
            mock_dispatch.assert_called_once()
            call_args = mock_dispatch.call_args
            assert call_args[0][0] == "dynamic_context_loaded"
            event_data = call_args[0][1]
            assert "refs_count" in event_data
            assert "tokens_loaded" in event_data
            assert event_data["refs_count"] == 1
            assert event_data["tokens_loaded"] == 500

    @pytest.mark.asyncio
    async def test_event_not_dispatched_when_no_context_loaded(self) -> None:
        """GIVEN dynamic context loading returns empty list
        WHEN load_dynamic_context node executes
        THEN dynamic_context_loaded event should NOT be dispatched
        """
        from langchain_core.messages import HumanMessage

        mock_context_loader = MagicMock()

        with (
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader.search_and_load_context",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "langchain_core.callbacks.manager.adispatch_custom_event",
                new=AsyncMock(return_value=None),
            ) as mock_dispatch,
        ):
            from mcp_server_langgraph.core.agent_graph_builder import (
                _load_dynamic_context_impl,
            )

            state: dict[str, Any] = {
                "messages": [HumanMessage(content="Tell me about Python")],
                "next_action": "",
                "kb_focus": "all",
            }

            await _load_dynamic_context_impl(
                state=state,
                context_loader=mock_context_loader,
                top_k=3,
                max_tokens=2000,
            )

            # Verify event was NOT dispatched
            mock_dispatch.assert_not_called()

    @pytest.mark.asyncio
    async def test_event_not_dispatched_when_kb_focus_none(self) -> None:
        """GIVEN kb_focus is set to 'none'
        WHEN load_dynamic_context node executes
        THEN search should not be called and event should NOT be dispatched
        """
        from langchain_core.messages import HumanMessage

        mock_context_loader = MagicMock()

        with (
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader.search_and_load_context",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "langchain_core.callbacks.manager.adispatch_custom_event",
                new=AsyncMock(return_value=None),
            ) as mock_dispatch,
        ):
            from mcp_server_langgraph.core.agent_graph_builder import (
                _load_dynamic_context_impl,
            )

            state: dict[str, Any] = {
                "messages": [HumanMessage(content="Tell me about Python")],
                "next_action": "",
                "kb_focus": "none",  # KB disabled
            }

            await _load_dynamic_context_impl(
                state=state,
                context_loader=mock_context_loader,
                top_k=3,
                max_tokens=2000,
            )

            # Verify event was NOT dispatched (kb_focus=none skips context loading)
            mock_dispatch.assert_not_called()

    @pytest.mark.asyncio
    async def test_event_contains_correct_token_count(self) -> None:
        """GIVEN multiple contexts loaded with different token counts
        WHEN load_dynamic_context node executes
        THEN event should contain sum of all token counts
        """
        from langchain_core.messages import HumanMessage

        mock_context1 = MagicMock()
        mock_context1.token_count = 300
        mock_context2 = MagicMock()
        mock_context2.token_count = 400
        mock_context3 = MagicMock()
        mock_context3.token_count = 200

        mock_context_loader = MagicMock()
        mock_context_loader.to_messages = MagicMock(return_value=[])

        with (
            patch(
                "mcp_server_langgraph.core.dynamic_context_loader.search_and_load_context",
                new=AsyncMock(return_value=[mock_context1, mock_context2, mock_context3]),
            ),
            patch(
                "langchain_core.callbacks.manager.adispatch_custom_event",
                new=AsyncMock(return_value=None),
            ) as mock_dispatch,
        ):
            from mcp_server_langgraph.core.agent_graph_builder import (
                _load_dynamic_context_impl,
            )

            state: dict[str, Any] = {
                "messages": [HumanMessage(content="Tell me about Python")],
                "next_action": "",
                "kb_focus": "all",
            }

            await _load_dynamic_context_impl(
                state=state,
                context_loader=mock_context_loader,
                top_k=3,
                max_tokens=2000,
            )

            # Verify event data
            call_args = mock_dispatch.call_args
            event_data = call_args[0][1]
            assert event_data["refs_count"] == 3
            assert event_data["tokens_loaded"] == 900  # 300 + 400 + 200
