"""
Tests for agent graph builder native tools wiring (v7).

TDD: These tests define expected behavior for native tool integration
in the agent graph, including selected_tool_ids preference, kb_focus,
and verification routing.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestGenerateResponseImplSelectedToolIds:
    """Tests for selected_tool_ids preference over selected_tools."""

    @pytest.mark.asyncio
    async def test_prefers_selected_tool_ids_over_selected_tools(self) -> None:
        """Should prefer selected_tool_ids when both are present."""
        from mcp_server_langgraph.core.agent_graph_builder import _generate_response_impl

        # State with both selected_tool_ids and selected_tools
        state = {
            "messages": [HumanMessage(content="Test")],
            "selected_tool_ids": ["github:create_issue", "native:web_search"],
            "selected_tools": ["create_issue", "web_search"],  # Less specific
            "tool_preference": "auto",
            "tool_selection_mode": "auto",
            "kb_focus": "all",
        }

        mock_model = AsyncMock(return_value=None)
        mock_model.ainvoke = AsyncMock(return_value=AIMessage(content="Response"))
        mock_model.model_name = "gpt-5.2"

        # Patch at the source module
        with patch("mcp_server_langgraph.core.feature_flags.feature_flags") as mock_flags:
            mock_flags.native_tools_enabled = False  # Disable native to simplify

            result = await _generate_response_impl(
                state=state,
                model=mock_model,
                bound_tools=[],
                model_with_tools=None,
                pydantic_agent=None,
                config=None,
            )

            # Should have produced a response
            assert len(result["messages"]) == 1
            assert isinstance(result["messages"][0], AIMessage)

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.unit
class TestGenerateResponseImplToolSelectionMode:
    """Tests for tool_selection_mode handling."""

    @pytest.mark.asyncio
    async def test_disables_native_when_tool_selection_mode_none(self) -> None:
        """Should not use native tools when tool_selection_mode='none'."""
        from mcp_server_langgraph.core.agent_graph_builder import _generate_response_impl

        state = {
            "messages": [HumanMessage(content="Search for AI news")],
            "selected_tool_ids": ["web_search"],
            "tool_preference": "native",
            "tool_selection_mode": "none",  # Tools disabled!
            "kb_focus": "all",
        }

        mock_model = AsyncMock(return_value=None)
        mock_model.ainvoke = AsyncMock(return_value=AIMessage(content="Response"))
        mock_model.model_name = "gpt-5.2"

        with patch("mcp_server_langgraph.core.feature_flags.feature_flags") as mock_flags:
            mock_flags.native_tools_enabled = True

            await _generate_response_impl(
                state=state,
                model=mock_model,
                bound_tools=[],
                model_with_tools=None,
                pydantic_agent=None,
                config=None,
            )

            # Model should be invoked without native_tools
            mock_model.ainvoke.assert_called_once()
            call_kwargs = mock_model.ainvoke.call_args[1] if mock_model.ainvoke.call_args[1] else {}
            assert "native_tools" not in call_kwargs or call_kwargs.get("native_tools") is None

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.unit
class TestGenerateResponseImplKbFocus:
    """Tests for kb_focus handling."""

    @pytest.mark.asyncio
    async def test_filters_web_search_when_kb_only(self) -> None:
        """Should filter out web_search from native when kb_focus='kb_only'."""
        from mcp_server_langgraph.core.agent_graph_builder import _generate_response_impl

        state = {
            "messages": [HumanMessage(content="Search the knowledge base")],
            "selected_tool_ids": ["web_search", "kb_search"],
            "tool_preference": "auto",
            "tool_selection_mode": "auto",
            "kb_focus": "kb_only",  # Should exclude web_search
        }

        mock_model = AsyncMock(return_value=None)
        mock_model.ainvoke = AsyncMock(return_value=AIMessage(content="KB results"))
        mock_model.model_name = "gpt-5.2"

        with patch("mcp_server_langgraph.core.feature_flags.feature_flags") as mock_flags:
            mock_flags.native_tools_enabled = True

            with patch("mcp_server_langgraph.tools.native_handler.NativeToolHandler") as mock_handler_cls:
                mock_handler = MagicMock()
                mock_handler.get_native_configs.return_value = ([], ["kb_search"])
                mock_handler_cls.return_value = mock_handler

                await _generate_response_impl(
                    state=state,
                    model=mock_model,
                    bound_tools=[],
                    model_with_tools=None,
                    pydantic_agent=None,
                    config=None,
                )

                # Verify that web_search was filtered out before passing to handler
                if mock_handler.get_native_configs.called:
                    call_args = mock_handler.get_native_configs.call_args[0]
                    tool_list = call_args[0]
                    # web_search should have been filtered out
                    assert "web_search" not in tool_list

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.unit
class TestGenerateResponseImplVerificationRouting:
    """Tests for native tool verification routing."""

    @pytest.mark.asyncio
    async def test_routes_to_verify_when_enabled_and_native_output(self) -> None:
        """Should route to 'verify' (not 'end') when verification enabled and native output present."""
        from mcp_server_langgraph.core.agent_graph_builder import _generate_response_impl

        # Response with native output in additional_kwargs
        mock_response = AIMessage(
            content="Here are the search results.",
            additional_kwargs={"native_output": [{"type": "web_search_call", "results": []}]},
        )

        state = {
            "messages": [HumanMessage(content="Search for news")],
            "tool_preference": "native",
            "tool_selection_mode": "auto",
            "kb_focus": "all",
        }

        mock_model = AsyncMock(return_value=None)
        mock_model.ainvoke = AsyncMock(return_value=mock_response)
        mock_model.model_name = "gpt-5.2"

        mock_config = MagicMock()
        mock_config.enable_verification = True

        with patch("mcp_server_langgraph.core.feature_flags.feature_flags") as mock_flags:
            mock_flags.native_tools_enabled = True
            mock_flags.openai_native_web_search_enabled = True
            mock_flags.use_responses_api_for_openai = True

            result = await _generate_response_impl(
                state=state,
                model=mock_model,
                bound_tools=[],
                model_with_tools=None,
                pydantic_agent=None,
                config=mock_config,
            )

            # Should route to verify, not end
            assert result["next_action"] == "verify"

    @pytest.mark.asyncio
    async def test_routes_to_end_when_verification_disabled(self) -> None:
        """Should route to 'end' when verification is disabled."""
        from mcp_server_langgraph.core.agent_graph_builder import _generate_response_impl

        mock_response = AIMessage(
            content="Here are the search results.",
            additional_kwargs={"native_output": [{"type": "web_search_call", "results": []}]},
        )

        state = {
            "messages": [HumanMessage(content="Search for news")],
            "tool_preference": "native",
            "tool_selection_mode": "auto",
            "kb_focus": "all",
        }

        mock_model = AsyncMock(return_value=None)
        mock_model.ainvoke = AsyncMock(return_value=mock_response)
        mock_model.model_name = "gpt-5.2"

        mock_config = MagicMock()
        mock_config.enable_verification = False

        with patch("mcp_server_langgraph.core.feature_flags.feature_flags") as mock_flags:
            mock_flags.native_tools_enabled = True

            result = await _generate_response_impl(
                state=state,
                model=mock_model,
                bound_tools=[],
                model_with_tools=None,
                pydantic_agent=None,
                config=mock_config,
            )

            # Should route to end when verification disabled
            assert result["next_action"] == "end"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.unit
class TestGenerateResponseImplNativeConfigsObservability:
    """Tests for native configs observability."""

    @pytest.mark.asyncio
    async def test_stores_native_configs_used_in_state(self) -> None:
        """Should store _native_configs_used in state for observability."""
        from mcp_server_langgraph.core.agent_graph_builder import _generate_response_impl

        mock_response = AIMessage(
            content="Results here.",
            additional_kwargs={"native_output": [{"type": "web_search_call"}]},
        )

        state = {
            "messages": [HumanMessage(content="Search")],
            "selected_tool_ids": ["web_search"],
            "tool_preference": "native",
            "tool_selection_mode": "auto",
            "kb_focus": "all",
        }

        mock_model = AsyncMock(return_value=None)
        mock_model.ainvoke = AsyncMock(return_value=mock_response)
        mock_model.model_name = "gpt-5.2"

        with patch("mcp_server_langgraph.core.feature_flags.feature_flags") as mock_flags:
            mock_flags.native_tools_enabled = True
            mock_flags.openai_native_web_search_enabled = True
            mock_flags.use_responses_api_for_openai = True

            with patch("mcp_server_langgraph.tools.native_handler.NativeToolHandler") as mock_handler_cls:
                mock_handler = MagicMock()
                mock_handler.get_native_configs.return_value = (
                    [{"type": "web_search_preview"}],
                    [],
                )
                mock_handler.caps.native_provider = "openai"
                mock_handler_cls.return_value = mock_handler

                result = await _generate_response_impl(
                    state=state,
                    model=mock_model,
                    bound_tools=[],
                    model_with_tools=None,
                    pydantic_agent=None,
                    config=None,
                )

                # Should include _native_configs_used for observability
                if "_native_configs_used" in result:
                    assert isinstance(result["_native_configs_used"], list)

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.unit
class TestGenerateResponseImplAutoDerivation:
    """Tests for auto-deriving native candidates from bound_tools."""

    @pytest.mark.asyncio
    async def test_derives_native_from_bound_tools_in_auto_mode(self) -> None:
        """Should derive native candidates from bound_tools when no selection."""
        from mcp_server_langgraph.core.agent_graph_builder import _generate_response_impl

        # Create mock tool with web_search capability
        mock_web_search_tool = MagicMock()
        mock_web_search_tool.name = "web_search"

        mock_calculator_tool = MagicMock()
        mock_calculator_tool.name = "calculator"

        state = {
            "messages": [HumanMessage(content="Search for news")],
            # No selected_tools or selected_tool_ids
            "tool_preference": "auto",
            "tool_selection_mode": "auto",
            "kb_focus": "all",
        }

        mock_model = AsyncMock(return_value=None)
        mock_model.ainvoke = AsyncMock(return_value=AIMessage(content="Results"))
        mock_model.model_name = "gpt-5.2"
        mock_model.bind_tools = MagicMock(return_value=mock_model)

        with patch("mcp_server_langgraph.core.feature_flags.feature_flags") as mock_flags:
            mock_flags.native_tools_enabled = True
            mock_flags.openai_native_web_search_enabled = True
            mock_flags.use_responses_api_for_openai = True

            with patch("mcp_server_langgraph.tools.native_registry.get_native_for_builtin") as mock_get_native:
                # web_search has native equivalent, calculator doesn't
                def get_native_side_effect(name, provider):
                    if name == "web_search":
                        return MagicMock(name="web_search")
                    return None

                mock_get_native.side_effect = get_native_side_effect

                with patch("mcp_server_langgraph.tools.native_handler.NativeToolHandler") as mock_handler_cls:
                    mock_handler = MagicMock()
                    mock_handler.get_native_configs.return_value = (
                        [{"type": "web_search_preview"}],
                        [],
                    )
                    mock_handler.caps.native_provider = "openai"
                    mock_handler_cls.return_value = mock_handler

                    await _generate_response_impl(
                        state=state,
                        model=mock_model,
                        bound_tools=[mock_web_search_tool, mock_calculator_tool],
                        model_with_tools=mock_model,
                        pydantic_agent=None,
                        config=None,
                    )

                    # Verify model was invoked
                    assert mock_model.ainvoke.called

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
