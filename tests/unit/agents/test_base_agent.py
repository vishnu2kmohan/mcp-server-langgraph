"""
Tests for BaseAgent, AgentRequest, AgentResult

TDD: These tests define the contract for the base agent abstraction layer.
This layer sits between orchestrators and LLM providers.
"""

from __future__ import annotations

import asyncio
import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
class TestAgentRequest:
    """Tests for AgentRequest dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_request_exists(self) -> None:
        """Test that AgentRequest class exists."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        assert AgentRequest is not None

    def test_agent_request_has_message_field(self) -> None:
        """Test AgentRequest has message field."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(message="Hello, how are you?")

        assert request.message == "Hello, how are you?"

    def test_agent_request_has_context_field(self) -> None:
        """Test AgentRequest has context field defaulting to empty dict."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(message="Hello")

        assert hasattr(request, "context")
        assert request.context == {}

    def test_agent_request_context_can_be_set(self) -> None:
        """Test AgentRequest context can be provided."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        context = {"session_id": "abc123", "user_id": "user1"}
        request = AgentRequest(message="Hello", context=context)

        assert request.context == context

    def test_agent_request_has_thinking_budget_field(self) -> None:
        """Test AgentRequest has thinking_budget field."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(message="Hello", thinking_budget="medium")

        assert hasattr(request, "thinking_budget")
        assert request.thinking_budget == "medium"

    def test_agent_request_thinking_budget_defaults_to_none(self) -> None:
        """Test thinking_budget defaults to 'none'."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(message="Hello")

        assert request.thinking_budget == "none"

    def test_agent_request_thinking_budget_valid_values(self) -> None:
        """Test thinking_budget accepts valid values."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        for budget in ["none", "light", "medium", "deep"]:
            request = AgentRequest(message="Hello", thinking_budget=budget)
            assert request.thinking_budget == budget

    def test_agent_request_has_max_tokens_field(self) -> None:
        """Test AgentRequest has max_tokens field."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(message="Hello", max_tokens=1000)

        assert hasattr(request, "max_tokens")
        assert request.max_tokens == 1000

    def test_agent_request_max_tokens_defaults_to_none(self) -> None:
        """Test max_tokens defaults to None."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(message="Hello")

        assert request.max_tokens is None

    def test_agent_request_has_timeout_seconds_field(self) -> None:
        """Test AgentRequest has timeout_seconds field."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(message="Hello", timeout_seconds=30.0)

        assert hasattr(request, "timeout_seconds")
        assert request.timeout_seconds == 30.0

    def test_agent_request_timeout_defaults_to_60(self) -> None:
        """Test timeout_seconds defaults to 60.0."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(message="Hello")

        assert request.timeout_seconds == 60.0

    def test_agent_request_has_session_id_field(self) -> None:
        """Test AgentRequest has session_id field."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(message="Hello", session_id="session123")

        assert request.session_id == "session123"

    def test_agent_request_has_trace_id_field(self) -> None:
        """Test AgentRequest has trace_id field."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(message="Hello", trace_id="trace456")

        assert request.trace_id == "trace456"


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
class TestAgentResult:
    """Tests for AgentResult dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_result_exists(self) -> None:
        """Test that AgentResult class exists."""
        from mcp_server_langgraph.agents.base_agent import AgentResult

        assert AgentResult is not None

    def test_agent_result_has_content_field(self) -> None:
        """Test AgentResult has content field."""
        from mcp_server_langgraph.agents.base_agent import AgentResult

        result = AgentResult(content="Hello, I'm doing well!", success=True)

        assert result.content == "Hello, I'm doing well!"

    def test_agent_result_has_success_field(self) -> None:
        """Test AgentResult has success field."""
        from mcp_server_langgraph.agents.base_agent import AgentResult

        result = AgentResult(content="Result", success=True)

        assert result.success is True

    def test_agent_result_has_error_field(self) -> None:
        """Test AgentResult has error field for failure cases."""
        from mcp_server_langgraph.agents.base_agent import AgentResult

        result = AgentResult(content="", success=False, error="Timeout exceeded")

        assert result.error == "Timeout exceeded"

    def test_agent_result_error_defaults_to_none(self) -> None:
        """Test error defaults to None."""
        from mcp_server_langgraph.agents.base_agent import AgentResult

        result = AgentResult(content="OK", success=True)

        assert result.error is None

    def test_agent_result_has_thinking_content_field(self) -> None:
        """Test AgentResult has thinking_content for extended thinking."""
        from mcp_server_langgraph.agents.base_agent import AgentResult

        result = AgentResult(
            content="Result",
            success=True,
            thinking_content="Let me analyze this...",
        )

        assert result.thinking_content == "Let me analyze this..."

    def test_agent_result_thinking_content_defaults_to_none(self) -> None:
        """Test thinking_content defaults to None."""
        from mcp_server_langgraph.agents.base_agent import AgentResult

        result = AgentResult(content="Result", success=True)

        assert result.thinking_content is None

    def test_agent_result_has_thinking_tokens_field(self) -> None:
        """Test AgentResult has thinking_tokens field."""
        from mcp_server_langgraph.agents.base_agent import AgentResult

        result = AgentResult(content="Result", success=True, thinking_tokens=1500)

        assert result.thinking_tokens == 1500

    def test_agent_result_thinking_tokens_defaults_to_zero(self) -> None:
        """Test thinking_tokens defaults to 0."""
        from mcp_server_langgraph.agents.base_agent import AgentResult

        result = AgentResult(content="Result", success=True)

        assert result.thinking_tokens == 0

    def test_agent_result_has_model_used_field(self) -> None:
        """Test AgentResult has model_used field."""
        from mcp_server_langgraph.agents.base_agent import AgentResult

        result = AgentResult(
            content="Result",
            success=True,
            model_used="claude-opus-4-5-20251101",
        )

        assert result.model_used == "claude-opus-4-5-20251101"

    def test_agent_result_model_used_defaults_to_empty(self) -> None:
        """Test model_used defaults to empty string."""
        from mcp_server_langgraph.agents.base_agent import AgentResult

        result = AgentResult(content="Result", success=True)

        assert result.model_used == ""


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
class TestBaseAgent:
    """Tests for BaseAgent abstract class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_base_agent_exists(self) -> None:
        """Test that BaseAgent class exists."""
        from mcp_server_langgraph.agents.base_agent import BaseAgent

        assert BaseAgent is not None

    def test_base_agent_is_abstract(self) -> None:
        """Test BaseAgent cannot be instantiated directly."""
        from abc import ABC

        from mcp_server_langgraph.agents.base_agent import BaseAgent

        assert issubclass(BaseAgent, ABC)

    def test_base_agent_has_run_method(self) -> None:
        """Test BaseAgent has abstract run method."""
        from mcp_server_langgraph.agents.base_agent import BaseAgent

        assert hasattr(BaseAgent, "run")

    def test_base_agent_run_is_abstract(self) -> None:
        """Test BaseAgent.run is an abstract method."""

        from mcp_server_langgraph.agents.base_agent import BaseAgent

        # Check that run is an abstract method
        assert hasattr(BaseAgent.run, "__isabstractmethod__")
        assert BaseAgent.run.__isabstractmethod__ is True

    def test_base_agent_run_signature(self) -> None:
        """Test BaseAgent.run has correct signature."""
        import inspect

        from mcp_server_langgraph.agents.base_agent import BaseAgent

        sig = inspect.signature(BaseAgent.run)
        params = list(sig.parameters.keys())

        # Should have self, request, and optional cancel_event
        assert "self" in params
        assert "request" in params
        assert "cancel_event" in params


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
class TestWorkerAgent:
    """Tests for WorkerAgent concrete implementation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_worker_agent_exists(self) -> None:
        """Test that WorkerAgent class exists."""
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        assert WorkerAgent is not None

    def test_worker_agent_is_base_agent(self) -> None:
        """Test WorkerAgent inherits from BaseAgent."""
        from mcp_server_langgraph.agents.base_agent import BaseAgent
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        assert issubclass(WorkerAgent, BaseAgent)

    def test_worker_agent_requires_llm_factory(self) -> None:
        """Test WorkerAgent requires LLMFactory in constructor."""
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        mock_llm_factory = MagicMock()

        agent = WorkerAgent(llm_factory=mock_llm_factory)

        assert agent.llm_factory == mock_llm_factory

    def test_worker_agent_accepts_thinking_budget_manager(self) -> None:
        """Test WorkerAgent accepts optional ThinkingBudgetManager."""
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        mock_llm_factory = MagicMock()
        mock_budget_manager = MagicMock()

        agent = WorkerAgent(
            llm_factory=mock_llm_factory,
            thinking_budget_manager=mock_budget_manager,
        )

        assert agent.thinking_budget_manager == mock_budget_manager

    def test_worker_agent_accepts_model_id(self) -> None:
        """Test WorkerAgent accepts optional model_id override."""
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        mock_llm_factory = MagicMock()

        agent = WorkerAgent(
            llm_factory=mock_llm_factory,
            model_id="claude-opus-4-5-20251101",
        )

        assert agent.model_id == "claude-opus-4-5-20251101"


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.asyncio
class TestWorkerAgentRun:
    """Tests for WorkerAgent.run execution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_worker_agent_run_returns_agent_result(self) -> None:
        """Test WorkerAgent.run returns AgentResult."""
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.base_agent import AgentRequest, AgentResult
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        mock_llm_factory = MagicMock()
        # WorkerAgent now uses ainvoke which returns AIMessage
        mock_llm_factory.ainvoke = AsyncMock(
            return_value=AIMessage(
                content="Response",
                response_metadata={"model": "claude-opus-4-5-20251101"},
            )
        )

        agent = WorkerAgent(llm_factory=mock_llm_factory)
        request = AgentRequest(message="Hello")

        result = await agent.run(request)

        assert isinstance(result, AgentResult)

    async def test_worker_agent_run_sets_content(self) -> None:
        """Test WorkerAgent.run sets content from LLM response."""
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        mock_llm_factory = MagicMock()
        # WorkerAgent now uses ainvoke which returns AIMessage
        mock_llm_factory.ainvoke = AsyncMock(
            return_value=AIMessage(
                content="I'm doing great!",
                response_metadata={"model": "claude-opus-4-5-20251101"},
            )
        )

        agent = WorkerAgent(llm_factory=mock_llm_factory)
        request = AgentRequest(message="How are you?")

        result = await agent.run(request)

        assert result.content == "I'm doing great!"
        assert result.success is True

    async def test_worker_agent_run_handles_cancel_event(self) -> None:
        """Test WorkerAgent.run respects cancel_event."""
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        mock_llm_factory = MagicMock()
        # WorkerAgent now uses ainvoke which returns AIMessage
        mock_llm_factory.ainvoke = AsyncMock(
            return_value=AIMessage(
                content="Response",
                response_metadata={"model": "claude-opus-4-5-20251101"},
            )
        )

        agent = WorkerAgent(llm_factory=mock_llm_factory)
        request = AgentRequest(message="Hello")

        # Create already-set cancel event
        cancel_event = asyncio.Event()
        cancel_event.set()

        result = await agent.run(request, cancel_event=cancel_event)

        # Should return early with cancellation
        assert result.success is False
        assert "cancel" in result.error.lower()

    async def test_worker_agent_run_handles_error(self) -> None:
        """Test WorkerAgent.run handles LLM errors gracefully."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        mock_llm_factory = MagicMock()
        # WorkerAgent now uses ainvoke
        mock_llm_factory.ainvoke = AsyncMock(side_effect=Exception("LLM Error"))

        agent = WorkerAgent(llm_factory=mock_llm_factory)
        request = AgentRequest(message="Hello")

        result = await agent.run(request)

        assert result.success is False
        assert result.error is not None
        assert "LLM Error" in result.error

    async def test_worker_agent_run_sets_model_used(self) -> None:
        """Test WorkerAgent.run sets model_used in result."""
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        mock_llm_factory = MagicMock()
        # WorkerAgent now uses ainvoke which returns AIMessage
        mock_llm_factory.ainvoke = AsyncMock(
            return_value=AIMessage(
                content="Response",
                response_metadata={"model": "claude-opus-4-5-20251101"},
            )
        )

        agent = WorkerAgent(llm_factory=mock_llm_factory)
        request = AgentRequest(message="Hello")

        result = await agent.run(request)

        assert result.model_used == "claude-opus-4-5-20251101"
