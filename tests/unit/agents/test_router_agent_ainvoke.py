"""
Tests for RouterAgent migration to ainvoke.

TDD: These tests are written FIRST to define the expected behavior
of RouterAgent using LLMFactory.ainvoke() instead of create_completion().

Bug Reference: RouterAgent calls llm_factory.create_completion() but
LLMFactory only provides ainvoke() and astream().

Tests verify:
1. RouterAgent.route() correctly uses ainvoke()
2. RouterAgent.route() correctly parses AIMessage.content
3. RouterAgent handles ainvoke errors gracefully
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


class TestRouterAgentAInvoke:
    """Test suite for RouterAgent using ainvoke API."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_route_uses_ainvoke_not_create_completion(self) -> None:
        """GIVEN a RouterAgent with mock llm_factory
        WHEN route() is called
        THEN it should call ainvoke() not create_completion()

        This test verifies the migration from create_completion to ainvoke.
        """
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()

        # Mock ainvoke to return an AIMessage (correct API)
        mock_response = AIMessage(
            content='{"complexity": "simple", "risk": "low", "task_type": "chat", "tools_needed": [], "suggested_orchestrator": "standard", "critique_rounds": 0, "thinking_budget": "none", "confidence": 0.9}'
        )
        mock_llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        # create_completion should NOT be called
        mock_llm_factory.create_completion = AsyncMock(return_value=None)

        agent = RouterAgent(llm_factory=mock_llm_factory)
        await agent.route(message="Hello")

        # Verify ainvoke was called
        mock_llm_factory.ainvoke.assert_called_once()

        # Verify create_completion was NOT called
        mock_llm_factory.create_completion.assert_not_called()

    @pytest.mark.asyncio
    async def test_route_parses_aimessage_content(self) -> None:
        """GIVEN an ainvoke response with JSON in AIMessage.content
        WHEN route() parses the response
        THEN it should correctly extract the RouterOutput fields
        """
        from mcp_server_langgraph.agents.router_agent import RouterAgent, RouterOutput

        mock_llm_factory = MagicMock()
        mock_response = AIMessage(
            content='{"complexity": "complicated", "risk": "medium", "task_type": "code", "tools_needed": ["read_file"], "suggested_orchestrator": "swarm", "critique_rounds": 2, "thinking_budget": "medium", "confidence": 0.85}'
        )
        mock_llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        agent = RouterAgent(llm_factory=mock_llm_factory)
        result = await agent.route(message="Analyze this complex codebase")

        assert isinstance(result, RouterOutput)
        assert result.complexity == "complicated"
        assert result.risk == "medium"
        assert result.task_type == "code"
        assert "read_file" in result.tools_needed
        assert result.suggested_orchestrator == "swarm"
        assert result.critique_rounds == 2
        assert result.thinking_budget == "medium"
        assert result.confidence == 0.85

    @pytest.mark.asyncio
    async def test_route_passes_messages_to_ainvoke(self) -> None:
        """GIVEN a RouterAgent
        WHEN route() is called with a message
        THEN it should pass LangChain messages to ainvoke()
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()
        mock_response = AIMessage(
            content='{"complexity": "simple", "risk": "low", "task_type": "chat", "tools_needed": [], "suggested_orchestrator": "standard", "critique_rounds": 0, "thinking_budget": "none", "confidence": 0.9}'
        )
        mock_llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        agent = RouterAgent(llm_factory=mock_llm_factory)
        await agent.route(message="Hello")

        # Get the messages passed to ainvoke
        call_args = mock_llm_factory.ainvoke.call_args
        messages = call_args[0][0]  # First positional arg

        # Should have system message and user message
        assert len(messages) >= 2
        assert isinstance(messages[0], SystemMessage)
        assert isinstance(messages[-1], HumanMessage)
        assert messages[-1].content == "Hello"

    @pytest.mark.asyncio
    async def test_route_handles_ainvoke_exception(self) -> None:
        """GIVEN ainvoke raises an exception
        WHEN route() is called
        THEN it should return DEFAULT_ROUTER_OUTPUT gracefully
        """
        from mcp_server_langgraph.agents.router_agent import DEFAULT_ROUTER_OUTPUT, RouterAgent

        mock_llm_factory = MagicMock()
        mock_llm_factory.ainvoke = AsyncMock(side_effect=Exception("LLM unavailable"))

        agent = RouterAgent(llm_factory=mock_llm_factory)
        result = await agent.route(message="Hello")

        # Should return default output on error
        assert result == DEFAULT_ROUTER_OUTPUT

    @pytest.mark.asyncio
    async def test_route_handles_invalid_json_from_ainvoke(self) -> None:
        """GIVEN ainvoke returns invalid JSON in AIMessage.content
        WHEN route() parses the response
        THEN it should return DEFAULT_ROUTER_OUTPUT gracefully
        """
        from mcp_server_langgraph.agents.router_agent import DEFAULT_ROUTER_OUTPUT, RouterAgent

        mock_llm_factory = MagicMock()
        mock_response = AIMessage(content="This is not valid JSON")
        mock_llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        agent = RouterAgent(llm_factory=mock_llm_factory)
        result = await agent.route(message="Hello")

        # Should return default output on parse error
        assert result == DEFAULT_ROUTER_OUTPUT

    @pytest.mark.asyncio
    async def test_route_passes_model_id_to_ainvoke(self) -> None:
        """GIVEN a RouterAgent with custom model_id
        WHEN route() is called
        THEN it should pass model to ainvoke kwargs
        """
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()
        mock_response = AIMessage(
            content='{"complexity": "simple", "risk": "low", "task_type": "chat", "tools_needed": [], "suggested_orchestrator": "standard", "critique_rounds": 0, "thinking_budget": "none", "confidence": 0.9}'
        )
        mock_llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        agent = RouterAgent(llm_factory=mock_llm_factory, model_id="gpt-4-turbo")
        await agent.route(message="Hello")

        # Verify model was passed in kwargs
        call_kwargs = mock_llm_factory.ainvoke.call_args[1]
        assert call_kwargs.get("model") == "gpt-4-turbo"

    @pytest.mark.asyncio
    async def test_route_handles_empty_aimessage_content(self) -> None:
        """GIVEN ainvoke returns AIMessage with empty content
        WHEN route() parses the response
        THEN it should return DEFAULT_ROUTER_OUTPUT gracefully
        """
        from mcp_server_langgraph.agents.router_agent import DEFAULT_ROUTER_OUTPUT, RouterAgent

        mock_llm_factory = MagicMock()
        mock_response = AIMessage(content="")
        mock_llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        agent = RouterAgent(llm_factory=mock_llm_factory)
        result = await agent.route(message="Hello")

        # Should return default output on empty content
        assert result == DEFAULT_ROUTER_OUTPUT

    @pytest.mark.asyncio
    async def test_route_handles_none_aimessage_content(self) -> None:
        """GIVEN ainvoke returns AIMessage with None content
        WHEN route() parses the response
        THEN it should return DEFAULT_ROUTER_OUTPUT gracefully
        """
        from mcp_server_langgraph.agents.router_agent import DEFAULT_ROUTER_OUTPUT, RouterAgent

        mock_llm_factory = MagicMock()
        mock_response = AIMessage(content="")  # AIMessage doesn't allow None, use empty
        mock_response.content = None  # Force None for edge case
        mock_llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        agent = RouterAgent(llm_factory=mock_llm_factory)
        result = await agent.route(message="Hello")

        # Should return default output on None content
        assert result == DEFAULT_ROUTER_OUTPUT
