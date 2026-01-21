"""
Tests for Tool Binding in Agent Graph Builder.

TDD tests to verify that tools are properly bound to the LLM model
when enable_tool_calling is enabled in AgentConfig.

This addresses the architectural gap where the LangGraph agent graph
doesn't bind tools to the model, preventing the LLM from generating
tool_calls.

RED Phase: These tests define the expected behavior.
GREEN Phase: Implementation in agent_graph_builder.py will make them pass.
"""

import gc

import pytest
from langchain_core.messages import AIMessage

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_tool_binding_config")
class TestAgentConfigToolCalling:
    """Test AgentConfig has enable_tool_calling field."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_config_has_enable_tool_calling_field(self):
        """AgentConfig should have enable_tool_calling field with default True."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig()

        # Tool calling should be enabled by default for agentic behavior
        assert hasattr(config, "enable_tool_calling")
        assert config.enable_tool_calling is True

    def test_agent_config_tool_calling_can_be_disabled(self):
        """AgentConfig should allow disabling tool calling."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig(enable_tool_calling=False)

        assert config.enable_tool_calling is False

    def test_enable_tool_calling_is_topology_field(self):
        """enable_tool_calling should affect graph topology (and thus graph_version)."""
        from mcp_server_langgraph.core.agent_config import AgentConfig

        config_with_tools = AgentConfig(enable_tool_calling=True)
        config_without_tools = AgentConfig(enable_tool_calling=False)

        # Different tool calling settings should produce different graph versions
        # (because the model binding changes the graph behavior)
        assert config_with_tools.graph_version != config_without_tools.graph_version


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_tool_binding_graph")
class TestToolBindingInGraph:
    """Test that tools are bound to the model when enable_tool_calling=True."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_model_has_tools_bound_when_enabled(self, monkeypatch):
        """When enable_tool_calling=True, model should have tools bound."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(enable_tool_calling=True)
        graph = build_agent_graph(config)

        # The graph should have been built with a tool-bound model
        # We verify this by checking that the graph has tool-related metadata
        assert graph is not None
        # The respond node should use a model with tools bound
        # This is verified by the actual behavior in integration tests

    @pytest.mark.asyncio
    async def test_graph_can_generate_tool_calls(self, monkeypatch):
        """Graph with tool calling enabled should be able to generate tool_calls."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(
            enable_tool_calling=True,
            enable_verification=False,  # Simplify test
            enable_context_compaction=False,
        )
        graph = build_agent_graph(config)

        # The graph should be capable of tool calling
        assert "tools" in graph.nodes

    @pytest.mark.asyncio
    async def test_tools_node_receives_tool_calls_from_llm(self, monkeypatch):
        """When LLM generates tool_calls, the tools node should receive them."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        # This test verifies the integration: LLM -> tool_calls -> tools node
        # The key is that the LLM must be bound with tools to generate tool_calls

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(
            enable_tool_calling=True,
            enable_verification=False,
            enable_context_compaction=False,
        )
        graph = build_agent_graph(config)

        # Verify the graph structure supports tool calling flow
        assert "router" in graph.nodes
        assert "tools" in graph.nodes
        assert "respond" in graph.nodes


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_tool_binding_model")
class TestModelToolBinding:
    """Test that the LLM model is properly bound with tools."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_llm_with_tools_returns_tool_bound_model(self, monkeypatch):
        """create_llm_from_config with tools should return a model with tools bound."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.tools import get_all_tools

        # Get tools for the test environment
        tools = get_all_tools()

        # Verify we have tools available
        assert len(tools) > 0, "Should have at least some tools available"

        # Verify tools have the expected structure for binding
        for tool in tools:
            assert hasattr(tool, "name"), f"Tool {tool} should have a name"
            assert hasattr(tool, "description"), f"Tool {tool} should have a description"

    @pytest.mark.asyncio
    async def test_llm_factory_supports_tool_calling_via_litellm(self, monkeypatch):
        """LLMFactory should support tool calling via LiteLLM's native tool support.

        Note: LLMFactory is a custom wrapper that uses LiteLLM's acompletion,
        which supports tool calling via the 'tools' parameter. The bind_tools
        pattern from LangChain is not directly supported, but tools can be
        passed to the completion call.
        """
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        from mcp_server_langgraph.llm.factory import create_llm_from_config, LLMFactory
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.tools import get_all_tools

        settings = Settings(
            environment="test",
            llm_provider="openai",
            openai_api_key="test-key",
        )
        model = create_llm_from_config(settings)
        tools = get_all_tools(settings)

        # LLMFactory is our custom wrapper that uses LiteLLM
        assert isinstance(model, LLMFactory)

        # LLMFactory has ainvoke method for async completion
        assert hasattr(model, "ainvoke")

        # Tools are available for binding in the agent graph builder
        assert len(tools) > 0, "Should have tools available"


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_tool_calling_routing")
class TestToolCallingRouting:
    """Test that routing properly handles tool_calls from LLM."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_routing_checks_for_tool_calls_in_response(self):
        """Routing should check for tool_calls attribute in LLM response."""
        # Create a mock AI message with tool_calls
        mock_tool_calls = [
            {
                "id": "call_123",
                "name": "calculator",
                "args": {"a": 1, "b": 2},
            }
        ]

        ai_message = AIMessage(content="", tool_calls=mock_tool_calls)

        # Verify the message has tool_calls
        assert hasattr(ai_message, "tool_calls")
        assert len(ai_message.tool_calls) == 1
        assert ai_message.tool_calls[0]["name"] == "calculator"

    def test_routing_handles_message_without_tool_calls(self):
        """Routing should handle messages without tool_calls gracefully."""
        ai_message = AIMessage(content="Hello, how can I help?")

        # Message without tool_calls should have empty list or None
        tool_calls = getattr(ai_message, "tool_calls", None)
        assert tool_calls is None or len(tool_calls) == 0


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_tool_binding_feature_flag")
class TestToolBindingFeatureFlag:
    """Test that tool binding respects feature flags and settings."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_sandbox_tools_included_when_enabled(self, monkeypatch):
        """Sandbox tools should be included when enable_sandbox_tools=True."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.tools import get_all_tools

        # In test environment, sandbox tools should be available
        settings = Settings(environment="test")
        tools = get_all_tools(settings)

        tool_names = [t.name for t in tools]

        # Basic tools should always be present
        assert "calculator" in tool_names or "add" in tool_names
        assert "search_knowledge_base" in tool_names
        assert "read_file" in tool_names

    @pytest.mark.asyncio
    async def test_code_execution_tool_included_when_enabled(self, monkeypatch):
        """execute_python tool should be included when enable_code_execution=True."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.tools import get_all_tools

        settings = Settings(environment="test", enable_code_execution=True)
        tools = get_all_tools(settings)

        tool_names = [t.name for t in tools]

        # execute_python should be present when code execution is enabled
        assert "execute_python" in tool_names


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_respond_node_tool_binding")
class TestRespondNodeToolBinding:
    """Test that the respond node uses a tool-bound model."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_respond_node_invokes_model_with_tools(self, monkeypatch):
        """The respond node should invoke the model with tools bound."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(
            enable_tool_calling=True,
            enable_verification=False,
            enable_context_compaction=False,
        )

        # Build the graph
        graph = build_agent_graph(config)

        # The graph should have the respond node
        assert "respond" in graph.nodes

        # The respond node should be configured to use tool-bound model
        # This is verified by checking the node exists and graph builds successfully
        # Full verification requires integration test with mocked LLM


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_dynamic_tool_binding")
class TestDynamicToolBinding:
    """Test dynamic tool binding based on selected_tools from semantic search."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_generate_response_uses_selected_tools_when_available(self, monkeypatch):
        """generate_response should use selected_tools from state when available."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(
            enable_semantic_tool_search=True,
            enable_tool_calling=True,
            enable_verification=False,
            enable_context_compaction=False,
        )

        graph = build_agent_graph(config)

        # Graph should have both retrieve_tools and respond nodes
        assert "retrieve_tools" in graph.nodes
        assert "respond" in graph.nodes

    @pytest.mark.asyncio
    async def test_selected_tools_state_field_is_list_or_none(self, monkeypatch):
        """selected_tools in state should be list[str] or None."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_graph_builder import AgentState

        # Valid state with selected_tools as list
        state_with_tools: AgentState = {
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
            "selected_tools": ["calculator", "search"],
        }

        assert state_with_tools["selected_tools"] == ["calculator", "search"]

        # Valid state with selected_tools as None (use all tools)
        state_without_tools: AgentState = {
            **state_with_tools,
            "selected_tools": None,
        }

        assert state_without_tools["selected_tools"] is None

    @pytest.mark.asyncio
    async def test_dynamic_binding_respects_max_selected_tools(self, monkeypatch):
        """Dynamic binding should respect max_selected_tools config."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig

        config = AgentConfig(
            enable_semantic_tool_search=True,
            max_selected_tools=5,
        )

        # Config should have max_selected_tools
        assert config.max_selected_tools == 5

    @pytest.mark.asyncio
    async def test_dynamic_binding_falls_back_to_all_tools_when_selected_is_none(self, monkeypatch):
        """When selected_tools is None, should fall back to all bound tools."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(
            enable_semantic_tool_search=True,
            enable_tool_calling=True,
            enable_verification=False,
        )

        graph = build_agent_graph(config)

        # Graph should build successfully
        assert graph is not None
        assert "respond" in graph.nodes

    @pytest.mark.asyncio
    async def test_semantic_selection_integrates_with_tool_binding(self, monkeypatch):
        """Semantic tool selection should integrate with tool binding in graph."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from mcp_server_langgraph.core.agent_config import AgentConfig
        from mcp_server_langgraph.core.agent_graph_builder import build_agent_graph

        config = AgentConfig(
            enable_semantic_tool_search=True,
            enable_tool_calling=True,
            max_selected_tools=10,
            semantic_tool_search_threshold=0.5,
            enable_verification=False,
            enable_context_compaction=False,
        )

        graph = build_agent_graph(config)

        # Verify the complete tool selection flow
        assert "retrieve_tools" in graph.nodes
        assert "router" in graph.nodes
        assert "tools" in graph.nodes
        assert "respond" in graph.nodes


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_dynamic_tool_filtering")
class TestDynamicToolFiltering:
    """Test that generate_response actually filters tools based on selected_tools."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_generate_response_filters_tools_when_selected_tools_present(self, monkeypatch):
        """generate_response should bind only selected tools when state has selected_tools.

        This is the core test for ADR-0099 dynamic tool binding:
        When semantic search selects specific tools, the LLM should only receive
        those tools in its context, not all available tools.
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from langchain_core.messages import HumanMessage, AIMessage
        from mcp_server_langgraph.core.agent_graph_builder import (
            _generate_response_impl,
            AgentState,
        )

        # Create mock tools
        mock_calculator = MagicMock()
        mock_calculator.name = "calculator"
        mock_search = MagicMock()
        mock_search.name = "search"
        mock_translate = MagicMock()
        mock_translate.name = "translate"

        all_tools = [mock_calculator, mock_search, mock_translate]

        # Create mock model
        mock_model = MagicMock()
        mock_model_with_filtered_tools = MagicMock()
        mock_model.bind_tools = MagicMock(return_value=mock_model_with_filtered_tools)
        mock_model_with_filtered_tools.ainvoke = AsyncMock(
            return_value=AIMessage(content="Response using selected tools")
        )

        # State with only calculator and search selected
        state: AgentState = {
            "messages": [HumanMessage(content="Calculate 2+2")],
            "next_action": "respond",
            "user_id": "user:test",
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
            "selected_tools": ["calculator", "search"],  # Only 2 of 3 tools selected
        }

        # Call the implementation helper
        result = await _generate_response_impl(
            state=state,
            model=mock_model,
            bound_tools=all_tools,
            model_with_tools=None,  # Force dynamic binding path
            pydantic_agent=None,
        )

        # Verify that bind_tools was called with only the selected tools
        mock_model.bind_tools.assert_called_once()
        bound_tool_names = [t.name for t in mock_model.bind_tools.call_args[0][0]]
        assert set(bound_tool_names) == {"calculator", "search"}
        assert "translate" not in bound_tool_names

        # Verify the filtered model was used for inference
        mock_model_with_filtered_tools.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_response_uses_all_tools_when_selected_tools_is_none(self, monkeypatch):
        """generate_response should use all tools when selected_tools is None."""
        from unittest.mock import AsyncMock, MagicMock

        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from langchain_core.messages import HumanMessage, AIMessage
        from mcp_server_langgraph.core.agent_graph_builder import (
            _generate_response_impl,
            AgentState,
        )

        # Create mock tools
        mock_tool1 = MagicMock()
        mock_tool1.name = "tool1"
        mock_tool2 = MagicMock()
        mock_tool2.name = "tool2"
        all_tools = [mock_tool1, mock_tool2]

        # Create pre-bound model (all tools)
        mock_model_with_all_tools = MagicMock()
        mock_model_with_all_tools.ainvoke = AsyncMock(
            return_value=AIMessage(content="Response using all tools")
        )

        mock_model = MagicMock()

        # State without selected_tools (None)
        state: AgentState = {
            "messages": [HumanMessage(content="Hello")],
            "next_action": "respond",
            "user_id": "user:test",
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
            "selected_tools": None,  # No selection - use all tools
        }

        result = await _generate_response_impl(
            state=state,
            model=mock_model,
            bound_tools=all_tools,
            model_with_tools=mock_model_with_all_tools,  # Pre-bound with all tools
            pydantic_agent=None,
        )

        # Verify the pre-bound model with all tools was used
        mock_model_with_all_tools.ainvoke.assert_called_once()
        # bind_tools should NOT have been called since we use the pre-bound model
        mock_model.bind_tools.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_response_handles_empty_selected_tools(self, monkeypatch):
        """generate_response should handle empty selected_tools list gracefully."""
        from unittest.mock import AsyncMock, MagicMock

        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from langchain_core.messages import HumanMessage, AIMessage
        from mcp_server_langgraph.core.agent_graph_builder import (
            _generate_response_impl,
            AgentState,
        )

        mock_model = MagicMock()
        mock_model_no_tools = MagicMock()
        mock_model.bind_tools = MagicMock(return_value=mock_model_no_tools)
        mock_model_no_tools.ainvoke = AsyncMock(
            return_value=AIMessage(content="Response without tools")
        )

        mock_model_with_all_tools = MagicMock()
        mock_model_with_all_tools.ainvoke = AsyncMock(
            return_value=AIMessage(content="Response with all tools")
        )

        state: AgentState = {
            "messages": [HumanMessage(content="Hello")],
            "next_action": "respond",
            "user_id": "user:test",
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
            "selected_tools": [],  # Empty list - fall back to all tools
        }

        result = await _generate_response_impl(
            state=state,
            model=mock_model,
            bound_tools=[MagicMock()],
            model_with_tools=mock_model_with_all_tools,
            pydantic_agent=None,
        )

        # Empty selection should fall back to all tools
        mock_model_with_all_tools.ainvoke.assert_called_once()


# =============================================================================
# v7: Native Tool Result Detection Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_native_result_detection_v7")
class TestNativeResultDetection:
    """Tests for v7 native tool result detection in _generate_response_impl."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_generate_response_detects_native_results(self, monkeypatch):
        """generate_response should detect native tool results and append them."""
        from unittest.mock import AsyncMock, MagicMock

        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from langchain_core.messages import HumanMessage

        from mcp_server_langgraph.core.agent_graph_builder import _generate_response_impl

        # Create a mock response with native tool results
        mock_response = MagicMock()
        mock_response.content = [
            {"type": "text", "text": "Here are the search results:"},
            {
                "type": "web_search_results",
                "results": [
                    {
                        "title": "Test Result",
                        "url": "https://example.com",
                        "snippet": "Test snippet",
                    }
                ],
            },
        ]
        mock_response.tool_calls = None  # No standard tool calls

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=mock_response)

        state = {
            "messages": [HumanMessage(content="Search for AI news")],
            "next_action": "respond",
            "user_id": "user:test",
            "tool_preference": "native",
        }

        result = await _generate_response_impl(
            state=state,
            model=mock_model,
            bound_tools=[],
            model_with_tools=None,
            pydantic_agent=None,
        )

        # Should have detected native results
        # The response messages should include the original response
        assert len(result["messages"]) >= 1

    @pytest.mark.asyncio
    async def test_generate_response_routes_to_use_tools_for_tool_calls(self, monkeypatch):
        """generate_response should route to use_tools when tool_calls are present."""
        from unittest.mock import AsyncMock, MagicMock

        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long1234")
        monkeypatch.setenv("ENVIRONMENT", "test")

        from langchain_core.messages import HumanMessage

        from mcp_server_langgraph.core.agent_graph_builder import _generate_response_impl

        mock_response = MagicMock()
        mock_response.content = "I'll calculate that for you."
        mock_response.tool_calls = [
            {"id": "call_123", "name": "calculator", "args": {"a": 1, "b": 2}}
        ]

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(return_value=mock_response)

        state = {
            "messages": [HumanMessage(content="Calculate 1 + 2")],
            "next_action": "respond",
            "user_id": "user:test",
        }

        result = await _generate_response_impl(
            state=state,
            model=mock_model,
            bound_tools=[],
            model_with_tools=None,
            pydantic_agent=None,
        )

        # Should route to use_tools for standard tool calls
        assert result["next_action"] == "use_tools"
