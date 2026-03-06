"""
Tests for WorkerAgent migration to ainvoke.

TDD: These tests are written FIRST to define the expected behavior
of WorkerAgent using LLMFactory.ainvoke() instead of create_completion().

Bug Reference: WorkerAgent calls llm_factory.create_completion() but
LLMFactory only provides ainvoke() and astream().

Tests verify:
1. WorkerAgent.run() correctly uses ainvoke()
2. WorkerAgent.run() correctly parses AIMessage.content
3. WorkerAgent handles ainvoke errors gracefully
4. WorkerAgent passes correct messages to ainvoke()
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


class TestWorkerAgentAInvoke:
    """Test suite for WorkerAgent using ainvoke API."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_run_uses_ainvoke_not_create_completion(self) -> None:
        """GIVEN a WorkerAgent with mock llm_factory
        WHEN run() is called
        THEN it should call ainvoke() not create_completion()

        This test verifies the migration from create_completion to ainvoke.
        """
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        mock_llm_factory = MagicMock()

        # Mock ainvoke to return an AIMessage (correct API)
        mock_response = AIMessage(content="Hello! I'm doing well.")
        mock_llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        # create_completion should NOT be called
        mock_llm_factory.create_completion = AsyncMock(return_value=None)

        agent = WorkerAgent(llm_factory=mock_llm_factory)
        request = AgentRequest(message="Hello, how are you?")
        await agent.run(request)

        # Verify ainvoke was called
        mock_llm_factory.ainvoke.assert_called_once()

        # Verify create_completion was NOT called
        mock_llm_factory.create_completion.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_parses_aimessage_content(self) -> None:
        """GIVEN an ainvoke response with text in AIMessage.content
        WHEN run() parses the response
        THEN it should correctly extract the content for AgentResult
        """
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        mock_llm_factory = MagicMock()
        mock_response = AIMessage(content="This is the LLM response content.")
        mock_llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        agent = WorkerAgent(llm_factory=mock_llm_factory)
        request = AgentRequest(message="Tell me something")
        result = await agent.run(request)

        assert result.success is True
        assert result.content == "This is the LLM response content."

    @pytest.mark.asyncio
    async def test_run_passes_human_message_to_ainvoke(self) -> None:
        """GIVEN a WorkerAgent
        WHEN run() is called with a request
        THEN it should pass a HumanMessage to ainvoke()
        """
        from langchain_core.messages import HumanMessage

        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        mock_llm_factory = MagicMock()
        mock_response = AIMessage(content="Response")
        mock_llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        agent = WorkerAgent(llm_factory=mock_llm_factory)
        request = AgentRequest(message="Hello")
        await agent.run(request)

        # Get the messages passed to ainvoke
        call_args = mock_llm_factory.ainvoke.call_args
        messages = call_args[0][0]  # First positional arg

        # Should have at least one HumanMessage
        assert len(messages) >= 1
        assert isinstance(messages[-1], HumanMessage)
        assert messages[-1].content == "Hello"

    @pytest.mark.asyncio
    async def test_run_handles_ainvoke_exception(self) -> None:
        """GIVEN ainvoke raises an exception
        WHEN run() is called
        THEN it should return AgentResult with success=False and error message
        """
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        mock_llm_factory = MagicMock()
        mock_llm_factory.ainvoke = AsyncMock(side_effect=Exception("LLM unavailable"))

        agent = WorkerAgent(llm_factory=mock_llm_factory)
        request = AgentRequest(message="Hello")
        result = await agent.run(request)

        # Should return error result
        assert result.success is False
        assert "LLM unavailable" in result.error

    @pytest.mark.asyncio
    async def test_run_handles_empty_aimessage_content(self) -> None:
        """GIVEN ainvoke returns AIMessage with empty content
        WHEN run() parses the response
        THEN it should return AgentResult with empty content but success=True
        """
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        mock_llm_factory = MagicMock()
        mock_response = AIMessage(content="")
        mock_llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        agent = WorkerAgent(llm_factory=mock_llm_factory)
        request = AgentRequest(message="Hello")
        result = await agent.run(request)

        # Empty content is valid
        assert result.success is True
        assert result.content == ""

    @pytest.mark.asyncio
    async def test_run_passes_model_id_to_ainvoke(self) -> None:
        """GIVEN a WorkerAgent with custom model_id
        WHEN run() is called
        THEN it should pass model to ainvoke kwargs
        """
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        mock_llm_factory = MagicMock()
        mock_response = AIMessage(content="Response")
        mock_llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        agent = WorkerAgent(llm_factory=mock_llm_factory, model_id="gpt-4-turbo")
        request = AgentRequest(message="Hello")
        await agent.run(request)

        # Verify model was passed in kwargs
        call_kwargs = mock_llm_factory.ainvoke.call_args[1]
        assert call_kwargs.get("model") == "gpt-4-turbo"

    @pytest.mark.asyncio
    async def test_run_passes_max_tokens_to_ainvoke(self) -> None:
        """GIVEN a WorkerAgent with max_tokens in request
        WHEN run() is called
        THEN it should pass max_tokens to ainvoke kwargs
        """
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        mock_llm_factory = MagicMock()
        mock_response = AIMessage(content="Response")
        mock_llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        agent = WorkerAgent(llm_factory=mock_llm_factory)
        request = AgentRequest(message="Hello", max_tokens=100)
        await agent.run(request)

        # Verify max_tokens was passed in kwargs
        call_kwargs = mock_llm_factory.ainvoke.call_args[1]
        assert call_kwargs.get("max_tokens") == 100

    @pytest.mark.asyncio
    async def test_run_handles_timeout(self) -> None:
        """GIVEN ainvoke takes longer than timeout
        WHEN run() is called
        THEN it should return AgentResult with timeout error
        """
        import asyncio

        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        mock_llm_factory = MagicMock()

        async def slow_response(*args, **kwargs):
            await asyncio.sleep(10)  # noqa: sleep-duration - intentionally long for timeout test
            return AIMessage(content="Too late")

        mock_llm_factory.ainvoke = AsyncMock(side_effect=slow_response)

        agent = WorkerAgent(llm_factory=mock_llm_factory)
        request = AgentRequest(message="Hello", timeout_seconds=0.1)
        result = await agent.run(request)

        # Should return timeout error
        assert result.success is False
        assert "Timeout" in result.error or "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_run_handles_cancellation(self) -> None:
        """GIVEN cancel_event is set before execution
        WHEN run() is called
        THEN it should return cancelled AgentResult immediately
        """
        import asyncio

        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        mock_llm_factory = MagicMock()
        mock_response = AIMessage(content="Should not reach")
        mock_llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        agent = WorkerAgent(llm_factory=mock_llm_factory)
        request = AgentRequest(message="Hello")

        # Set cancel event before execution
        cancel_event = asyncio.Event()
        cancel_event.set()

        result = await agent.run(request, cancel_event=cancel_event)

        # Should return cancelled result
        assert result.success is False
        assert "Cancelled" in result.error

        # ainvoke should NOT have been called
        mock_llm_factory.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_extracts_model_from_response_metadata(self) -> None:
        """GIVEN ainvoke returns AIMessage with response_metadata
        WHEN run() parses the response
        THEN it should extract model_used from response metadata
        """
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        mock_llm_factory = MagicMock()
        mock_response = AIMessage(
            content="Response",
            response_metadata={"model": "gpt-4-turbo-preview"},
        )
        mock_llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        agent = WorkerAgent(llm_factory=mock_llm_factory)
        request = AgentRequest(message="Hello")
        result = await agent.run(request)

        assert result.success is True
        # Model should be extracted from response metadata or fallback to agent's model_id
        assert result.model_used is not None
