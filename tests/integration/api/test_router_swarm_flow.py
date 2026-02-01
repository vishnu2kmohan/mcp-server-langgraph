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
from unittest.mock import MagicMock

import pytest

from mcp_server_langgraph.agents.router_agent import RouterOutput


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
    """Integration tests for Router → Swarm flow via create_stream().

    NOTE: RouterAgent orchestration is in create_stream(), NOT create_completion().
    These tests validate the selection logic which is properly tested in
    TestOrchestratorSelectionIntegration. Here we add stream-focused tests.

    Key architecture notes:
    - RouterAgent is initialized via ChatServiceImpl._router_agent property
    - feature_flags is imported inside functions (not at module level)
    - SwarmOrchestrator dispatch happens in create_stream() after select_orchestrator()
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_router_agent_select_orchestrator_returns_swarm_for_swarm_request(
        self,
        swarm_router_output: RouterOutput,
    ) -> None:
        """
        GIVEN RouterAgent returns suggested_orchestrator="swarm"
        AND enable_swarm_orchestrator=True
        WHEN select_orchestrator() is called
        THEN OrchestratorSelection has type="asyncio_swarm"
        """
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_feature_flags = MagicMock()
        mock_feature_flags.enable_swarm_orchestrator = True
        mock_feature_flags.enable_langgraph_patterns = False

        mock_llm_factory = MagicMock()
        router = RouterAgent(llm_factory=mock_llm_factory)
        selection = await router.select_orchestrator(
            routing_decision=swarm_router_output,
            feature_flags=mock_feature_flags,
        )

        # Verify swarm selection
        assert selection.orchestrator_type == "asyncio_swarm"
        assert selection.swarm_strategy == "consensus"  # high risk

    @pytest.mark.asyncio
    async def test_router_agent_select_orchestrator_returns_standard_when_swarm_disabled(
        self,
        swarm_router_output: RouterOutput,
    ) -> None:
        """
        GIVEN RouterAgent returns suggested_orchestrator="swarm"
        AND enable_swarm_orchestrator=False
        WHEN select_orchestrator() is called
        THEN OrchestratorSelection has type="standard" (fallback)
        """
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_feature_flags = MagicMock()
        mock_feature_flags.enable_swarm_orchestrator = False
        mock_feature_flags.enable_langgraph_patterns = False

        mock_llm_factory = MagicMock()
        router = RouterAgent(llm_factory=mock_llm_factory)
        selection = await router.select_orchestrator(
            routing_decision=swarm_router_output,
            feature_flags=mock_feature_flags,
        )

        # Verify standard fallback
        assert selection.orchestrator_type == "standard"

    @pytest.mark.asyncio
    async def test_router_agent_select_orchestrator_returns_standard_for_standard_request(
        self,
        standard_router_output: RouterOutput,
    ) -> None:
        """
        GIVEN RouterAgent returns suggested_orchestrator="standard"
        WHEN select_orchestrator() is called
        THEN OrchestratorSelection has type="standard"
        """
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_feature_flags = MagicMock()
        mock_feature_flags.enable_swarm_orchestrator = True
        mock_feature_flags.enable_langgraph_patterns = False

        mock_llm_factory = MagicMock()
        router = RouterAgent(llm_factory=mock_llm_factory)
        selection = await router.select_orchestrator(
            routing_decision=standard_router_output,
            feature_flags=mock_feature_flags,
        )

        # Verify standard selection
        assert selection.orchestrator_type == "standard"

    @pytest.mark.asyncio
    async def test_swarm_selection_includes_complete_metadata(
        self,
        swarm_router_output: RouterOutput,
    ) -> None:
        """
        GIVEN Swarm orchestration is selected
        WHEN OrchestratorSelection is returned
        THEN it includes strategy, worker_count, and context_strategy
        """
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_feature_flags = MagicMock()
        mock_feature_flags.enable_swarm_orchestrator = True
        mock_feature_flags.enable_langgraph_patterns = False

        mock_llm_factory = MagicMock()
        router = RouterAgent(llm_factory=mock_llm_factory)
        selection = await router.select_orchestrator(
            routing_decision=swarm_router_output,
            feature_flags=mock_feature_flags,
        )

        # Verify complete metadata
        assert selection.orchestrator_type == "asyncio_swarm"
        assert selection.swarm_strategy == "consensus"  # high risk → consensus
        assert selection.worker_count == 3
        assert selection.context_strategy == "summarized"  # consensus → summarized
        assert selection.thinking_budget == "deep"  # from router_output


# =============================================================================
# Phase 2 Integration Tests - Orchestrator Selection
# =============================================================================


class TestOrchestratorSelectionIntegration:
    """Integration tests for select_orchestrator() flow (ADR-0105 Phase 2)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_orchestrator_selection_derives_context_strategy_from_risk(
        self,
        swarm_router_output: RouterOutput,
    ) -> None:
        """
        GIVEN RouterAgent returns high risk swarm request
        WHEN select_orchestrator() is called
        THEN context_strategy="summarized" (consensus strategy)
        """
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_feature_flags = MagicMock()
        mock_feature_flags.enable_swarm_orchestrator = True

        mock_llm_factory = MagicMock()
        router = RouterAgent(llm_factory=mock_llm_factory)
        selection = await router.select_orchestrator(
            routing_decision=swarm_router_output,
            feature_flags=mock_feature_flags,
        )

        # High risk → consensus strategy → summarized context
        assert selection.orchestrator_type == "asyncio_swarm"
        assert selection.swarm_strategy == "consensus"
        assert selection.context_strategy == "summarized"

    @pytest.mark.asyncio
    async def test_orchestrator_selection_race_strategy_uses_scoped_context(self) -> None:
        """
        GIVEN RouterAgent returns low risk swarm request
        WHEN select_orchestrator() is called
        THEN context_strategy="scoped" (race strategy)
        """
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        low_risk_output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="swarm",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
        )

        mock_feature_flags = MagicMock()
        mock_feature_flags.enable_swarm_orchestrator = True

        mock_llm_factory = MagicMock()
        router = RouterAgent(llm_factory=mock_llm_factory)
        selection = await router.select_orchestrator(
            routing_decision=low_risk_output,
            feature_flags=mock_feature_flags,
        )

        # Low risk → race strategy → scoped context
        assert selection.orchestrator_type == "asyncio_swarm"
        assert selection.swarm_strategy == "race"
        assert selection.context_strategy == "scoped"

    @pytest.mark.asyncio
    async def test_cascade_strategy_uses_scoped_context(self) -> None:
        """
        GIVEN RouterAgent returns medium risk swarm request
        WHEN select_orchestrator() is called
        THEN context_strategy="scoped" (cascade strategy)
        """
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        medium_risk_output = RouterOutput(
            complexity="complicated",
            risk="medium",
            task_type="analysis",
            tools_needed=["search"],
            suggested_orchestrator="swarm",
            critique_rounds=1,
            thinking_budget="light",
            confidence=0.85,
        )

        mock_feature_flags = MagicMock()
        mock_feature_flags.enable_swarm_orchestrator = True

        mock_llm_factory = MagicMock()
        router = RouterAgent(llm_factory=mock_llm_factory)
        selection = await router.select_orchestrator(
            routing_decision=medium_risk_output,
            feature_flags=mock_feature_flags,
        )

        # Medium risk → cascade strategy → scoped context
        assert selection.orchestrator_type == "asyncio_swarm"
        assert selection.swarm_strategy == "cascade"
        assert selection.context_strategy == "scoped"

    @pytest.mark.asyncio
    async def test_orchestrator_selection_model_validation(
        self,
        swarm_router_output: RouterOutput,
    ) -> None:
        """
        GIVEN OrchestratorSelection is created
        WHEN validated
        THEN all fields have correct types and values
        """
        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection

        # Create a valid selection
        selection = OrchestratorSelection(
            orchestrator_type="asyncio_swarm",
            swarm_strategy="consensus",
            worker_count=3,
            worker_model="vertex_ai/gemini-3-flash-preview",
            thinking_budget="deep",
            context_strategy="summarized",
        )

        # Verify all fields are correct
        assert selection.orchestrator_type == "asyncio_swarm"
        assert selection.swarm_strategy == "consensus"
        assert selection.worker_count == 3
        assert selection.worker_model == "vertex_ai/gemini-3-flash-preview"
        assert selection.thinking_budget == "deep"
        assert selection.context_strategy == "summarized"

        # Verify defaults for standard selection
        standard_selection = OrchestratorSelection(
            orchestrator_type="standard",
            thinking_budget="none",
        )
        assert standard_selection.orchestrator_type == "standard"
        assert standard_selection.swarm_strategy is None
        assert standard_selection.context_strategy == "scoped"  # Default

    @pytest.mark.asyncio
    async def test_standard_orchestrator_does_not_use_swarm(
        self,
        standard_router_output: RouterOutput,
        sample_messages: list[dict[str, Any]],
    ) -> None:
        """
        GIVEN RouterAgent returns standard orchestration
        WHEN select_orchestrator() is called
        THEN orchestrator_type="standard" and no swarm execution
        """
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_feature_flags = MagicMock()
        mock_feature_flags.enable_swarm_orchestrator = True

        mock_llm_factory = MagicMock()
        router = RouterAgent(llm_factory=mock_llm_factory)
        selection = await router.select_orchestrator(
            routing_decision=standard_router_output,
            feature_flags=mock_feature_flags,
        )

        # Standard routing → standard orchestrator type
        assert selection.orchestrator_type == "standard"
        assert selection.swarm_strategy is None
        # context_strategy defaults to "scoped" for standard
        assert selection.context_strategy == "scoped"
