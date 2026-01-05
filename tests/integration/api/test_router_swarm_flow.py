"""
Integration tests for Router → Swarm Orchestrator Flow.

Tests the complete lifecycle when RouterAgent suggests swarm orchestration:
- RouterAgent classifies request as requiring swarm
- SwarmOrchestrator is instantiated with worker agents
- Swarm executes with configured strategy
- Response includes router_metadata

Reference: ADR-0090 Agent Orchestration Architecture
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.agents.router_agent import RouterOutput
from mcp_server_langgraph.api.v1.chat import ChatServiceImpl


pytestmark = [
    pytest.mark.integration,
    pytest.mark.xdist_group(name="router_swarm_integration"),
]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def swarm_router_output() -> RouterOutput:
    """RouterOutput that suggests swarm orchestration."""
    return RouterOutput(
        complexity="complex",
        risk="high",
        task_type="analysis",
        tools_needed=["data_query", "visualization"],
        suggested_orchestrator="swarm",
        critique_rounds=2,
        thinking_budget="deep",
        confidence=0.92,
    )


@pytest.fixture
def standard_router_output() -> RouterOutput:
    """RouterOutput that suggests standard orchestration (default)."""
    return RouterOutput(
        complexity="simple",
        risk="low",
        task_type="chat",
        tools_needed=[],
        suggested_orchestrator="standard",
        critique_rounds=0,
        thinking_budget="none",
        confidence=0.95,
    )


@pytest.fixture
def sample_messages() -> list[dict[str, Any]]:
    """Sample messages for testing."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Analyze this complex dataset and provide insights."},
    ]


# =============================================================================
# Integration Tests
# =============================================================================


class TestRouterSwarmIntegration:
    """Integration tests for Router → Swarm flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_swarm_orchestrator_invoked_when_router_suggests_swarm(
        self,
        swarm_router_output: RouterOutput,
        sample_messages: list[dict[str, Any]],
    ) -> None:
        """
        GIVEN RouterAgent returns suggested_orchestrator="swarm"
        AND enable_swarm_orchestrator=True
        WHEN create_completion() is called
        THEN SwarmOrchestrator is instantiated and run() is called
        """
        mock_router_agent = MagicMock()
        mock_router_agent.route = AsyncMock(return_value=swarm_router_output)

        mock_agent_result = MagicMock()
        mock_agent_result.content = "Swarm consensus response"

        mock_swarm_instance = MagicMock()
        mock_swarm_instance.run = AsyncMock(return_value=mock_agent_result)

        with (
            patch("mcp_server_langgraph.api.v1.chat.feature_flags") as mock_flags,
            patch("mcp_server_langgraph.api.v1.chat.RouterAgent", return_value=mock_router_agent),
            patch("mcp_server_langgraph.api.v1.chat.SwarmOrchestrator") as mock_swarm_cls,
            patch("mcp_server_langgraph.agents.worker_agent.WorkerAgent"),
            patch("mcp_server_langgraph.api.v1.chat.sanitize_content") as mock_sanitize,
        ):
            mock_flags.enable_router_agent = True
            mock_flags.enable_swarm_orchestrator = True
            mock_swarm_cls.return_value = mock_swarm_instance

            mock_sanitize.return_value = ("Sanitized message", MagicMock(risk_score=0.1))

            service = ChatServiceImpl()
            result = await service.create_completion(
                session_id="test-session",
                messages=sample_messages,
            )

        # Verify SwarmOrchestrator was instantiated
        mock_swarm_cls.assert_called_once()

        # Verify swarm.run() was called
        mock_swarm_instance.run.assert_called_once()

        # Verify response includes router_metadata
        assert "router_metadata" in result
        assert result["router_metadata"]["suggested_orchestrator"] == "swarm"
        assert result["router_metadata"]["complexity"] == "complex"
        assert result["router_metadata"]["risk"] == "high"

    @pytest.mark.asyncio
    async def test_standard_path_when_router_suggests_standard(
        self,
        standard_router_output: RouterOutput,
        sample_messages: list[dict[str, Any]],
    ) -> None:
        """
        GIVEN RouterAgent returns suggested_orchestrator="standard"
        WHEN create_completion() is called
        THEN SwarmOrchestrator is NOT invoked
        """
        mock_router_agent = MagicMock()
        mock_router_agent.route = AsyncMock(return_value=standard_router_output)

        mock_llm_response = MagicMock()
        mock_llm_response.choices = [MagicMock()]
        mock_llm_response.choices[0].message = MagicMock()
        mock_llm_response.choices[0].message.content = "Standard response"
        mock_llm_response.usage = MagicMock()
        mock_llm_response.usage.prompt_tokens = 10
        mock_llm_response.usage.completion_tokens = 20

        with (
            patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion,
            patch("mcp_server_langgraph.api.v1.chat.feature_flags") as mock_flags,
            patch("mcp_server_langgraph.api.v1.chat.RouterAgent", return_value=mock_router_agent),
            patch("mcp_server_langgraph.api.v1.chat.SwarmOrchestrator") as mock_swarm_cls,
            patch("mcp_server_langgraph.api.v1.chat.sanitize_content") as mock_sanitize,
        ):
            mock_flags.enable_router_agent = True
            mock_flags.enable_swarm_orchestrator = True
            mock_acompletion.return_value = mock_llm_response

            mock_sanitize.return_value = ("Sanitized message", MagicMock(risk_score=0.1))

            service = ChatServiceImpl()
            result = await service.create_completion(
                session_id="test-session",
                messages=sample_messages,
            )

        # SwarmOrchestrator should NOT be called for standard routing
        mock_swarm_cls.assert_not_called()

        # Response still includes router_metadata
        assert "router_metadata" in result
        assert result["router_metadata"]["suggested_orchestrator"] == "standard"

    @pytest.mark.asyncio
    async def test_swarm_disabled_falls_back_to_standard(
        self,
        swarm_router_output: RouterOutput,
        sample_messages: list[dict[str, Any]],
    ) -> None:
        """
        GIVEN RouterAgent returns suggested_orchestrator="swarm"
        AND enable_swarm_orchestrator=False
        WHEN create_completion() is called
        THEN SwarmOrchestrator is NOT invoked (falls back to standard)
        """
        mock_router_agent = MagicMock()
        mock_router_agent.route = AsyncMock(return_value=swarm_router_output)

        mock_llm_response = MagicMock()
        mock_llm_response.choices = [MagicMock()]
        mock_llm_response.choices[0].message = MagicMock()
        mock_llm_response.choices[0].message.content = "Fallback response"
        mock_llm_response.usage = MagicMock()
        mock_llm_response.usage.prompt_tokens = 10
        mock_llm_response.usage.completion_tokens = 20

        with (
            patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion,
            patch("mcp_server_langgraph.api.v1.chat.feature_flags") as mock_flags,
            patch("mcp_server_langgraph.api.v1.chat.RouterAgent", return_value=mock_router_agent),
            patch("mcp_server_langgraph.api.v1.chat.SwarmOrchestrator") as mock_swarm_cls,
            patch("mcp_server_langgraph.api.v1.chat.sanitize_content") as mock_sanitize,
        ):
            mock_flags.enable_router_agent = True
            mock_flags.enable_swarm_orchestrator = False  # Swarm disabled
            mock_acompletion.return_value = mock_llm_response

            mock_sanitize.return_value = ("Sanitized message", MagicMock(risk_score=0.1))

            service = ChatServiceImpl()
            result = await service.create_completion(
                session_id="test-session",
                messages=sample_messages,
            )

        # SwarmOrchestrator should NOT be called when flag is disabled
        mock_swarm_cls.assert_not_called()

        # Response still includes router_metadata (swarm was suggested but not used)
        assert "router_metadata" in result
        assert result["router_metadata"]["suggested_orchestrator"] == "swarm"

    @pytest.mark.asyncio
    async def test_swarm_response_includes_correct_metadata(
        self,
        swarm_router_output: RouterOutput,
        sample_messages: list[dict[str, Any]],
    ) -> None:
        """
        GIVEN Swarm orchestration is triggered
        WHEN create_completion() returns
        THEN response includes complete router_metadata
        """
        mock_router_agent = MagicMock()
        mock_router_agent.route = AsyncMock(return_value=swarm_router_output)

        mock_agent_result = MagicMock()
        mock_agent_result.content = "Detailed analysis result"

        mock_swarm_instance = MagicMock()
        mock_swarm_instance.run = AsyncMock(return_value=mock_agent_result)

        with (
            patch("mcp_server_langgraph.api.v1.chat.feature_flags") as mock_flags,
            patch("mcp_server_langgraph.api.v1.chat.RouterAgent", return_value=mock_router_agent),
            patch("mcp_server_langgraph.api.v1.chat.SwarmOrchestrator") as mock_swarm_cls,
            patch("mcp_server_langgraph.agents.worker_agent.WorkerAgent"),
            patch("mcp_server_langgraph.api.v1.chat.sanitize_content") as mock_sanitize,
        ):
            mock_flags.enable_router_agent = True
            mock_flags.enable_swarm_orchestrator = True
            mock_swarm_cls.return_value = mock_swarm_instance

            mock_sanitize.return_value = ("Sanitized message", MagicMock(risk_score=0.1))

            service = ChatServiceImpl()
            result = await service.create_completion(
                session_id="test-session",
                messages=sample_messages,
            )

        # Verify complete router_metadata
        metadata = result["router_metadata"]
        assert metadata["complexity"] == "complex"
        assert metadata["risk"] == "high"
        assert metadata["task_type"] == "analysis"
        assert metadata["suggested_orchestrator"] == "swarm"
        assert metadata["confidence"] == 0.92

        # Verify response content
        assert result["message"]["content"] == "Detailed analysis result"
        assert result["message"]["role"] == "assistant"
