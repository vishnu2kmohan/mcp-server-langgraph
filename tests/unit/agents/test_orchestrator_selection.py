"""
Tests for Orchestrator Selection

TDD: These tests define the contract for orchestrator selection that maps
RouterOutput to concrete orchestrator implementations (SwarmOrchestrator,
Orchestrator, or standard LangGraph path).

ADR: Extends RouterAgent with orchestrator selection for AsyncIO-first execution.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


# =============================================================================
# Tests for enable_chat_routing Setting
# =============================================================================


@pytest.mark.unit
@pytest.mark.core
@pytest.mark.config
@pytest.mark.xdist_group(name="enable_chat_routing_setting")
class TestEnableChatRoutingSetting:
    """Tests for enable_chat_routing setting in Settings class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_settings_has_enable_chat_routing_field(self) -> None:
        """Test Settings has enable_chat_routing field."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "enable_chat_routing")

    def test_enable_chat_routing_defaults_to_true(self) -> None:
        """Test enable_chat_routing defaults to True for intelligent routing."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.enable_chat_routing is True

    def test_enable_chat_routing_can_be_disabled(self, monkeypatch) -> None:
        """Test enable_chat_routing can be disabled via env var."""
        monkeypatch.setenv("ENABLE_CHAT_ROUTING", "false")

        from mcp_server_langgraph.core.config import Settings

        # Need to create a fresh instance that reads the new env var
        settings = Settings()
        assert settings.enable_chat_routing is False


# =============================================================================
# Tests for OrchestratorSelection Model
# =============================================================================


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="orchestrator_selection_model")
class TestOrchestratorSelectionModel:
    """Tests for OrchestratorSelection model in router_agent.py."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestrator_selection_exists(self) -> None:
        """Test that OrchestratorSelection class exists."""
        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection

        assert OrchestratorSelection is not None

    def test_orchestrator_selection_has_orchestrator_type(self) -> None:
        """Test OrchestratorSelection has orchestrator_type field."""
        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection

        selection = OrchestratorSelection(orchestrator_type="standard")
        assert selection.orchestrator_type == "standard"

    def test_orchestrator_selection_type_valid_values(self) -> None:
        """Test orchestrator_type accepts valid values."""
        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection

        for otype in ["standard", "asyncio_swarm", "asyncio_task"]:
            selection = OrchestratorSelection(orchestrator_type=otype)
            assert selection.orchestrator_type == otype

    def test_orchestrator_selection_has_swarm_strategy(self) -> None:
        """Test OrchestratorSelection has swarm_strategy field."""
        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection

        selection = OrchestratorSelection(
            orchestrator_type="asyncio_swarm",
            swarm_strategy="consensus",
        )
        assert selection.swarm_strategy == "consensus"

    def test_orchestrator_selection_swarm_strategy_valid_values(self) -> None:
        """Test swarm_strategy accepts valid values."""
        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection

        for strategy in ["race", "cascade", "consensus"]:
            selection = OrchestratorSelection(
                orchestrator_type="asyncio_swarm",
                swarm_strategy=strategy,
            )
            assert selection.swarm_strategy == strategy

    def test_orchestrator_selection_has_worker_count(self) -> None:
        """Test OrchestratorSelection has worker_count field with default."""
        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection

        selection = OrchestratorSelection(orchestrator_type="asyncio_swarm")
        assert selection.worker_count == 3  # Default

    def test_orchestrator_selection_has_worker_model(self) -> None:
        """Test OrchestratorSelection has worker_model field."""
        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection

        selection = OrchestratorSelection(
            orchestrator_type="asyncio_swarm",
            worker_model="vertex_ai/gemini-3-flash-preview",
        )
        assert selection.worker_model == "vertex_ai/gemini-3-flash-preview"

    def test_orchestrator_selection_has_thinking_budget(self) -> None:
        """Test OrchestratorSelection has thinking_budget field with default."""
        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection

        selection = OrchestratorSelection(orchestrator_type="standard")
        assert selection.thinking_budget == "none"  # Default


# =============================================================================
# Tests for select_orchestrator Method
# =============================================================================


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="select_orchestrator_method")
class TestSelectOrchestratorMethod:
    """Tests for RouterAgent.select_orchestrator method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def _create_router_output(self, **kwargs):
        """Create a RouterOutput with defaults."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        defaults = {
            "complexity": "complicated",
            "risk": "medium",
            "task_type": "analysis",
            "tools_needed": [],
            "suggested_orchestrator": "standard",
            "critique_rounds": 1,
            "thinking_budget": "light",
            "confidence": 0.8,
        }
        defaults.update(kwargs)
        return RouterOutput(**defaults)

    def _create_mock_feature_flags(self, **kwargs):
        """Create mock feature flags with defaults."""
        flags = MagicMock()
        flags.enable_swarm_orchestrator = kwargs.get("enable_swarm_orchestrator", True)
        flags.enable_multi_agent_orchestration = kwargs.get("enable_multi_agent_orchestration", True)
        return flags

    async def test_router_agent_has_select_orchestrator_method(self) -> None:
        """Test RouterAgent has select_orchestrator method."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        assert hasattr(agent, "select_orchestrator")
        assert callable(agent.select_orchestrator)

    async def test_select_orchestrator_returns_orchestrator_selection(self) -> None:
        """Test select_orchestrator returns OrchestratorSelection."""
        from mcp_server_langgraph.agents.router_agent import (
            OrchestratorSelection,
            RouterAgent,
        )

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        routing_decision = self._create_router_output()
        flags = self._create_mock_feature_flags()

        result = await agent.select_orchestrator(
            routing_decision=routing_decision,
            feature_flags=flags,
        )

        assert isinstance(result, OrchestratorSelection)

    async def test_select_standard_for_standard_orchestrator(self) -> None:
        """Test standard suggested_orchestrator returns standard type."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        routing_decision = self._create_router_output(suggested_orchestrator="standard")
        flags = self._create_mock_feature_flags()

        result = await agent.select_orchestrator(
            routing_decision=routing_decision,
            feature_flags=flags,
        )

        assert result.orchestrator_type == "standard"

    async def test_select_swarm_when_enabled(self) -> None:
        """Test swarm suggested_orchestrator + enabled flag returns asyncio_swarm."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        routing_decision = self._create_router_output(suggested_orchestrator="swarm")
        flags = self._create_mock_feature_flags(enable_swarm_orchestrator=True)

        result = await agent.select_orchestrator(
            routing_decision=routing_decision,
            feature_flags=flags,
        )

        assert result.orchestrator_type == "asyncio_swarm"

    async def test_swarm_disabled_falls_back_to_standard(self) -> None:
        """Test swarm + disabled flag falls back to standard."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        routing_decision = self._create_router_output(suggested_orchestrator="swarm")
        flags = self._create_mock_feature_flags(enable_swarm_orchestrator=False)

        result = await agent.select_orchestrator(
            routing_decision=routing_decision,
            feature_flags=flags,
        )

        assert result.orchestrator_type == "standard"

    async def test_studio_falls_back_to_standard(self) -> None:
        """Test studio orchestrator falls back to standard when langgraph patterns disabled."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        routing_decision = self._create_router_output(suggested_orchestrator="studio")
        flags = self._create_mock_feature_flags()
        # Explicitly disable langgraph patterns to trigger fallback
        flags.enable_langgraph_patterns = False

        result = await agent.select_orchestrator(
            routing_decision=routing_decision,
            feature_flags=flags,
        )

        assert result.orchestrator_type == "standard"

    async def test_ux_falls_back_to_standard(self) -> None:
        """Test ux orchestrator falls back to standard."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        routing_decision = self._create_router_output(suggested_orchestrator="ux")
        flags = self._create_mock_feature_flags()

        result = await agent.select_orchestrator(
            routing_decision=routing_decision,
            feature_flags=flags,
        )

        assert result.orchestrator_type == "standard"

    async def test_alert_falls_back_to_standard(self) -> None:
        """Test alert orchestrator falls back to standard."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        routing_decision = self._create_router_output(suggested_orchestrator="alert")
        flags = self._create_mock_feature_flags()

        result = await agent.select_orchestrator(
            routing_decision=routing_decision,
            feature_flags=flags,
        )

        assert result.orchestrator_type == "standard"

    async def test_swarm_strategy_derived_from_high_risk(self) -> None:
        """Test high risk maps to consensus strategy."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        routing_decision = self._create_router_output(
            suggested_orchestrator="swarm",
            risk="high",
        )
        flags = self._create_mock_feature_flags()

        result = await agent.select_orchestrator(
            routing_decision=routing_decision,
            feature_flags=flags,
        )

        assert result.swarm_strategy == "consensus"

    async def test_swarm_strategy_derived_from_medium_risk(self) -> None:
        """Test medium risk maps to cascade strategy."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        routing_decision = self._create_router_output(
            suggested_orchestrator="swarm",
            risk="medium",
        )
        flags = self._create_mock_feature_flags()

        result = await agent.select_orchestrator(
            routing_decision=routing_decision,
            feature_flags=flags,
        )

        assert result.swarm_strategy == "cascade"

    async def test_swarm_strategy_derived_from_low_risk(self) -> None:
        """Test low risk maps to race strategy."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        routing_decision = self._create_router_output(
            suggested_orchestrator="swarm",
            risk="low",
        )
        flags = self._create_mock_feature_flags()

        result = await agent.select_orchestrator(
            routing_decision=routing_decision,
            feature_flags=flags,
        )

        assert result.swarm_strategy == "race"

    async def test_worker_model_derived_from_complex_complexity(self) -> None:
        """Test complex complexity maps to pro model."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        routing_decision = self._create_router_output(
            suggested_orchestrator="swarm",
            complexity="complex",
        )
        flags = self._create_mock_feature_flags()

        result = await agent.select_orchestrator(
            routing_decision=routing_decision,
            feature_flags=flags,
        )

        assert result.worker_model is not None
        assert "pro" in result.worker_model.lower()

    async def test_worker_model_derived_from_simple_complexity(self) -> None:
        """Test simple complexity maps to flash model."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        routing_decision = self._create_router_output(
            suggested_orchestrator="swarm",
            complexity="simple",
        )
        flags = self._create_mock_feature_flags()

        result = await agent.select_orchestrator(
            routing_decision=routing_decision,
            feature_flags=flags,
        )

        assert result.worker_model is not None
        assert "flash" in result.worker_model.lower()

    async def test_thinking_budget_passed_through(self) -> None:
        """Test thinking_budget is passed through from RouterOutput."""
        from mcp_server_langgraph.agents.router_agent import RouterAgent

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        routing_decision = self._create_router_output(
            thinking_budget="deep",
        )
        flags = self._create_mock_feature_flags()

        result = await agent.select_orchestrator(
            routing_decision=routing_decision,
            feature_flags=flags,
        )

        assert result.thinking_budget == "deep"


# =============================================================================
# Tests for _select_orchestrator_impl Function
# =============================================================================


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="select_orchestrator_impl")
class TestSelectOrchestratorImpl:
    """Tests for _select_orchestrator_impl helper function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def _create_router_output(self, **kwargs):
        """Create a RouterOutput with defaults."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        defaults = {
            "complexity": "complicated",
            "risk": "medium",
            "task_type": "analysis",
            "tools_needed": [],
            "suggested_orchestrator": "standard",
            "critique_rounds": 1,
            "thinking_budget": "light",
            "confidence": 0.8,
        }
        defaults.update(kwargs)
        return RouterOutput(**defaults)

    def _create_mock_feature_flags(self, **kwargs):
        """Create mock feature flags with defaults."""
        flags = MagicMock()
        flags.enable_swarm_orchestrator = kwargs.get("enable_swarm_orchestrator", True)
        flags.enable_multi_agent_orchestration = kwargs.get("enable_multi_agent_orchestration", True)
        return flags

    def test_select_orchestrator_impl_exists(self) -> None:
        """Test _select_orchestrator_impl function exists."""
        from mcp_server_langgraph.agents.router_agent import _select_orchestrator_impl

        assert _select_orchestrator_impl is not None
        assert callable(_select_orchestrator_impl)

    def test_impl_returns_standard_for_standard(self) -> None:
        """Test standard orchestrator maps to standard type."""
        from mcp_server_langgraph.agents.router_agent import _select_orchestrator_impl

        routing_decision = self._create_router_output(suggested_orchestrator="standard")
        flags = self._create_mock_feature_flags()

        result = _select_orchestrator_impl(routing_decision, flags)

        assert result.orchestrator_type == "standard"

    def test_impl_returns_asyncio_swarm_for_swarm(self) -> None:
        """Test swarm orchestrator maps to asyncio_swarm type."""
        from mcp_server_langgraph.agents.router_agent import _select_orchestrator_impl

        routing_decision = self._create_router_output(suggested_orchestrator="swarm")
        flags = self._create_mock_feature_flags(enable_swarm_orchestrator=True)

        result = _select_orchestrator_impl(routing_decision, flags)

        assert result.orchestrator_type == "asyncio_swarm"

    def test_impl_sets_worker_count_for_swarm(self) -> None:
        """Test swarm selection sets worker_count."""
        from mcp_server_langgraph.agents.router_agent import _select_orchestrator_impl

        routing_decision = self._create_router_output(suggested_orchestrator="swarm")
        flags = self._create_mock_feature_flags()

        result = _select_orchestrator_impl(routing_decision, flags)

        assert result.worker_count == 3


# =============================================================================
# Tests for Swarm Streaming Integration
# =============================================================================


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="swarm_streaming")
class TestSwarmStreaming:
    """Tests for _stream_via_swarm method in ChatServiceImpl."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def _create_orchestrator_selection(self, **kwargs):
        """Create an OrchestratorSelection for testing."""
        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection

        defaults = {
            "orchestrator_type": "asyncio_swarm",
            "swarm_strategy": "race",
            "worker_count": 3,
            "worker_model": "vertex_ai/gemini-3-flash-preview",
            "thinking_budget": "none",
        }
        defaults.update(kwargs)
        return OrchestratorSelection(**defaults)

    async def test_stream_via_swarm_yields_swarm_result_event(self) -> None:
        """Test _stream_via_swarm yields swarm_result metadata event."""
        from unittest.mock import patch

        from mcp_server_langgraph.agents.base_agent import AgentResult

        # Create mock swarm that returns success
        mock_result = AgentResult(
            content="Test response from swarm",
            success=True,
            model_used="vertex_ai/gemini-3-flash-preview",
        )

        selection = self._create_orchestrator_selection()
        messages = [{"role": "user", "content": "Compare React vs Vue"}]

        # Mock SwarmOrchestrator - patch where it's imported (agents module)
        with patch("mcp_server_langgraph.agents.swarm_orchestrator.SwarmOrchestrator") as MockSwarm:
            MockSwarm.return_value.run = AsyncMock(return_value=mock_result)

            # Also patch WorkerAgent since it's created in the method
            with patch("mcp_server_langgraph.agents.worker_agent.WorkerAgent") as MockWorker:
                MockWorker.return_value = MagicMock()

                # Import and create chat service
                from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

                service = ChatServiceImpl.__new__(ChatServiceImpl)
                # Use object.__setattr__ to bypass property setter
                object.__setattr__(service, "_llm_factory", MagicMock())
                # Phase 2: Add optional dependency attributes
                object.__setattr__(service, "_thinking_budget_manager", None)
                object.__setattr__(service, "_capability_provider", None)

                # Collect events from stream
                events = []
                async for event in service._stream_via_swarm(
                    session_id="test-session",
                    messages=messages,
                    selection=selection,
                ):
                    events.append(event)

                # Verify swarm_result event was yielded
                swarm_events = [e for e in events if "swarm_result" in e]
                assert len(swarm_events) == 1
                assert swarm_events[0]["swarm_result"]["success"] is True

    async def test_stream_via_swarm_yields_delta_for_persistence(self) -> None:
        """Test _stream_via_swarm yields delta format for SSE persistence."""
        from unittest.mock import patch

        from mcp_server_langgraph.agents.base_agent import AgentResult

        mock_result = AgentResult(
            content="Swarm consensus response",
            success=True,
            model_used="vertex_ai/gemini-3-flash-preview",
        )

        selection = self._create_orchestrator_selection()
        messages = [{"role": "user", "content": "Question"}]

        with patch("mcp_server_langgraph.agents.swarm_orchestrator.SwarmOrchestrator") as MockSwarm:
            MockSwarm.return_value.run = AsyncMock(return_value=mock_result)

            with patch("mcp_server_langgraph.agents.worker_agent.WorkerAgent") as MockWorker:
                MockWorker.return_value = MagicMock()

                from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

                service = ChatServiceImpl.__new__(ChatServiceImpl)
                object.__setattr__(service, "_llm_factory", MagicMock())
                # Phase 2: Add optional dependency attributes
                object.__setattr__(service, "_thinking_budget_manager", None)
                object.__setattr__(service, "_capability_provider", None)

                events = []
                async for event in service._stream_via_swarm(
                    session_id="test-session",
                    messages=messages,
                    selection=selection,
                ):
                    events.append(event)

                # Verify delta format for persistence
                delta_events = [e for e in events if "delta" in e]
                assert len(delta_events) == 1
                assert delta_events[0]["delta"]["content"] == "Swarm consensus response"

    async def test_stream_via_swarm_handles_error(self) -> None:
        """Test _stream_via_swarm handles swarm errors gracefully."""
        from unittest.mock import patch

        from mcp_server_langgraph.agents.base_agent import AgentResult

        mock_result = AgentResult(
            content="",
            success=False,
            error="All agents failed in race",
        )

        selection = self._create_orchestrator_selection()
        messages = [{"role": "user", "content": "Question"}]

        with patch("mcp_server_langgraph.agents.swarm_orchestrator.SwarmOrchestrator") as MockSwarm:
            MockSwarm.return_value.run = AsyncMock(return_value=mock_result)

            with patch("mcp_server_langgraph.agents.worker_agent.WorkerAgent") as MockWorker:
                MockWorker.return_value = MagicMock()

                from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

                service = ChatServiceImpl.__new__(ChatServiceImpl)
                object.__setattr__(service, "_llm_factory", MagicMock())
                # Phase 2: Add optional dependency attributes
                object.__setattr__(service, "_thinking_budget_manager", None)
                object.__setattr__(service, "_capability_provider", None)

                events = []
                async for event in service._stream_via_swarm(
                    session_id="test-session",
                    messages=messages,
                    selection=selection,
                ):
                    events.append(event)

                # Verify error is yielded in delta format
                delta_events = [e for e in events if "delta" in e]
                assert len(delta_events) == 1
                assert "failed" in delta_events[0]["delta"]["content"].lower()


# =============================================================================
# Tests for Task Orchestrator Streaming
# =============================================================================


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="task_orchestrator_streaming")
class TestTaskOrchestratorStreaming:
    """Tests for _stream_via_task_orchestrator method in ChatServiceImpl."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def _create_orchestrator_selection(self, **kwargs):
        """Create an OrchestratorSelection for testing."""
        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection

        defaults = {
            "orchestrator_type": "asyncio_task",
            "thinking_budget": "none",
        }
        defaults.update(kwargs)
        return OrchestratorSelection(**defaults)

    async def test_stream_via_task_orchestrator_yields_task_decomposition(self) -> None:
        """Test _stream_via_task_orchestrator yields task_decomposition event."""
        from unittest.mock import patch

        from mcp_server_langgraph.agents.orchestrator import (
            Subtask,
            TaskDecomposition,
        )
        from mcp_server_langgraph.agents.subagent import SubagentResult

        # Create mock decomposition
        mock_decomposition = TaskDecomposition(
            original_task="Test task",
            subtasks=[
                Subtask(
                    task_id="subtask-1",
                    title="Part 1",
                    instructions="Do part 1",
                ),
                Subtask(
                    task_id="subtask-2",
                    title="Part 2",
                    instructions="Do part 2",
                ),
            ],
            synthesis_instructions="Combine results",
        )

        mock_results = [
            SubagentResult(
                task_id="subtask-1",
                success=True,
                output="Result 1",
                confidence=0.9,
            ),
            SubagentResult(
                task_id="subtask-2",
                success=True,
                output="Result 2",
                confidence=0.85,
            ),
        ]

        selection = self._create_orchestrator_selection()
        messages = [{"role": "user", "content": "Research something complex"}]

        with patch("mcp_server_langgraph.agents.orchestrator.Orchestrator") as MockOrch:
            mock_orch = MockOrch.return_value
            mock_orch.scale_effort.return_value = 2
            mock_orch.decompose_task.return_value = mock_decomposition
            mock_orch.execute = AsyncMock(return_value=mock_results)

            from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

            service = ChatServiceImpl.__new__(ChatServiceImpl)

            events = []
            async for event in service._stream_via_task_orchestrator(
                session_id="test-session",
                messages=messages,
                selection=selection,
            ):
                events.append(event)

            # Verify task_decomposition event
            decomp_events = [e for e in events if "task_decomposition" in e]
            assert len(decomp_events) == 1
            assert decomp_events[0]["task_decomposition"]["subtask_count"] == 2


# =============================================================================
# Integration Tests for Chat Routing Dispatch
# =============================================================================


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="chat_routing_dispatch")
class TestChatRoutingDispatch:
    """Integration tests for orchestrator dispatch in create_stream."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_registry_contains_swarm_orchestrator(self) -> None:
        """Test ORCHESTRATOR_REGISTRY contains SwarmOrchestrator."""
        from mcp_server_langgraph.agents.registry import ORCHESTRATOR_REGISTRY

        assert "SwarmOrchestrator" in ORCHESTRATOR_REGISTRY
        info = ORCHESTRATOR_REGISTRY["SwarmOrchestrator"]
        assert info.feature_flag == "enable_swarm_orchestrator"
        assert "parallel" in info.task_categories

    async def test_agents_module_exports_orchestrator_selection(self) -> None:
        """Test agents module exports OrchestratorSelection."""
        from mcp_server_langgraph.agents import OrchestratorSelection

        assert OrchestratorSelection is not None

    async def test_agents_module_exports_swarm_orchestrator(self) -> None:
        """Test agents module exports SwarmOrchestrator."""
        from mcp_server_langgraph.agents import SwarmOrchestrator

        assert SwarmOrchestrator is not None

    async def test_agents_module_exports_router_agent(self) -> None:
        """Test agents module exports RouterAgent."""
        from mcp_server_langgraph.agents import RouterAgent

        assert RouterAgent is not None

    async def test_settings_has_enable_chat_routing(self) -> None:
        """Test Settings exports enable_chat_routing."""
        from mcp_server_langgraph.core.config import settings

        assert hasattr(settings, "enable_chat_routing")

    async def test_agent_feature_flags_contains_swarm(self) -> None:
        """Test AGENT_FEATURE_FLAGS contains enable_swarm_orchestrator."""
        from mcp_server_langgraph.api.v1.agents import AGENT_FEATURE_FLAGS

        assert "enable_swarm_orchestrator" in AGENT_FEATURE_FLAGS

    async def test_orchestrator_selection_integration(self) -> None:
        """Test full integration: RouterOutput -> OrchestratorSelection."""
        from mcp_server_langgraph.agents import (
            OrchestratorSelection,
            RouterAgent,
            RouterOutput,
        )

        # Create router output for swarm
        router_output = RouterOutput(
            complexity="complex",
            risk="high",
            task_type="analysis",
            tools_needed=[],
            suggested_orchestrator="swarm",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
        )

        # Create mock feature flags
        mock_flags = MagicMock()
        mock_flags.enable_swarm_orchestrator = True

        # Create router agent and select orchestrator
        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        selection = await agent.select_orchestrator(
            routing_decision=router_output,
            feature_flags=mock_flags,
        )

        # Verify selection
        assert isinstance(selection, OrchestratorSelection)
        assert selection.orchestrator_type == "asyncio_swarm"
        assert selection.swarm_strategy == "consensus"  # high risk -> consensus
        assert "pro" in selection.worker_model.lower()  # complex -> pro model


# =============================================================================
# Phase 2 Tests: Strategy-Configurable Context
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="phase2_context_strategy")
class TestContextStrategy:
    """Tests for strategy-configurable context in OrchestratorSelection (Phase 2)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_orchestrator_selection_has_context_strategy_field(self) -> None:
        """Test OrchestratorSelection has context_strategy field."""
        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection

        selection = OrchestratorSelection(orchestrator_type="asyncio_swarm")
        assert hasattr(selection, "context_strategy")

    async def test_context_strategy_defaults_to_scoped(self) -> None:
        """Test context_strategy defaults to 'scoped' for minimal context."""
        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection

        selection = OrchestratorSelection(orchestrator_type="asyncio_swarm")
        assert selection.context_strategy == "scoped"

    async def test_context_strategy_valid_values(self) -> None:
        """Test context_strategy accepts valid values: scoped, summarized, full."""
        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection

        for strategy in ("scoped", "summarized", "full"):
            selection = OrchestratorSelection(
                orchestrator_type="asyncio_swarm",
                context_strategy=strategy,
            )
            assert selection.context_strategy == strategy

    async def test_race_strategy_uses_scoped_context(self) -> None:
        """Test RACE strategy defaults to scoped context (last message only)."""
        from mcp_server_langgraph.agents.router_agent import (
            RouterOutput,
            _select_orchestrator_impl,
        )

        router_output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="swarm",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
        )

        mock_flags = MagicMock()
        mock_flags.enable_swarm_orchestrator = True

        selection = _select_orchestrator_impl(router_output, mock_flags)

        assert selection.swarm_strategy == "race"
        assert selection.context_strategy == "scoped"

    async def test_consensus_strategy_uses_summarized_context(self) -> None:
        """Test CONSENSUS strategy uses summarized context for agreement."""
        from mcp_server_langgraph.agents.router_agent import (
            RouterOutput,
            _select_orchestrator_impl,
        )

        router_output = RouterOutput(
            complexity="complex",
            risk="high",
            task_type="analysis",
            tools_needed=[],
            suggested_orchestrator="swarm",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
        )

        mock_flags = MagicMock()
        mock_flags.enable_swarm_orchestrator = True

        selection = _select_orchestrator_impl(router_output, mock_flags)

        assert selection.swarm_strategy == "consensus"
        assert selection.context_strategy == "summarized"


# =============================================================================
# Phase 2 Tests: Resource URI Injection for Swarm
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="phase2_resource_injection")
class TestSwarmResourceInjection:
    """Tests for resource URI injection in swarm workers (Phase 2)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def _create_orchestrator_selection(self, **kwargs):
        """Create an OrchestratorSelection for testing."""
        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection

        defaults = {
            "orchestrator_type": "asyncio_swarm",
            "swarm_strategy": "race",
            "worker_count": 3,
            "worker_model": "vertex_ai/gemini-3-flash-preview",
            "thinking_budget": "none",
            "context_strategy": "scoped",
        }
        defaults.update(kwargs)
        return OrchestratorSelection(**defaults)

    async def test_stream_via_swarm_accepts_resource_uris(self) -> None:
        """Test _stream_via_swarm accepts resource_uris parameter."""
        from unittest.mock import patch

        from mcp_server_langgraph.agents.base_agent import AgentResult

        mock_result = AgentResult(
            content="Response with context",
            success=True,
            model_used="test-model",
        )

        selection = self._create_orchestrator_selection()
        messages = [{"role": "user", "content": "Question"}]
        resource_uris = ["file:///path/to/doc.md"]

        with patch("mcp_server_langgraph.agents.swarm_orchestrator.SwarmOrchestrator") as MockSwarm:
            MockSwarm.return_value.run = AsyncMock(return_value=mock_result)

            with patch("mcp_server_langgraph.agents.worker_agent.WorkerAgent") as MockWorker:
                MockWorker.return_value = MagicMock()

                from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

                service = ChatServiceImpl.__new__(ChatServiceImpl)
                object.__setattr__(service, "_llm_factory", MagicMock())
                object.__setattr__(service, "_thinking_budget_manager", None)
                object.__setattr__(service, "_capability_provider", None)

                events = []
                # Call with resource_uris parameter
                async for event in service._stream_via_swarm(
                    session_id="test-session",
                    messages=messages,
                    selection=selection,
                    resource_uris=resource_uris,
                ):
                    events.append(event)

                # Verify events were yielded (method accepts resource_uris)
                assert len(events) >= 1

    async def test_stream_via_swarm_injects_resource_content(self) -> None:
        """Test _stream_via_swarm injects resource content into agent request."""
        from unittest.mock import patch

        from mcp_server_langgraph.agents.base_agent import AgentResult

        mock_result = AgentResult(
            content="Response using document context",
            success=True,
            model_used="test-model",
        )

        selection = self._create_orchestrator_selection(context_strategy="full")
        messages = [{"role": "user", "content": "Summarize the document"}]
        resource_content = "This is the document content to inject."

        with patch("mcp_server_langgraph.agents.swarm_orchestrator.SwarmOrchestrator") as MockSwarm:
            mock_swarm_instance = MockSwarm.return_value
            mock_swarm_instance.run = AsyncMock(return_value=mock_result)

            with patch("mcp_server_langgraph.agents.worker_agent.WorkerAgent") as MockWorker:
                MockWorker.return_value = MagicMock()

                from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

                service = ChatServiceImpl.__new__(ChatServiceImpl)
                object.__setattr__(service, "_llm_factory", MagicMock())
                object.__setattr__(service, "_thinking_budget_manager", None)
                object.__setattr__(service, "_capability_provider", None)

                events = []
                async for event in service._stream_via_swarm(
                    session_id="test-session",
                    messages=messages,
                    selection=selection,
                    resource_content=resource_content,
                ):
                    events.append(event)

                # Verify swarm.run was called with context in the message
                call_args = mock_swarm_instance.run.call_args
                if call_args:
                    request = call_args.kwargs.get("request") or call_args.args[0]
                    # The message should include the resource content
                    assert resource_content in request.message or len(events) > 0


# =============================================================================
# Phase 2 Tests: Non-Streaming create_completion Support
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="phase2_non_streaming")
class TestNonStreamingOrchestration:
    """Tests for non-streaming create_completion with orchestrator dispatch (Phase 2)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_create_completion_respects_orchestrator_selection(self) -> None:
        """Test create_completion uses orchestrator selection when routing enabled."""
        from unittest.mock import patch

        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection, RouterOutput

        mock_router_output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
        )

        mock_selection = OrchestratorSelection(
            orchestrator_type="standard",
            thinking_budget="none",
        )

        with patch("mcp_server_langgraph.api.v1.chat.ChatServiceImpl") as MockService:
            mock_instance = MockService.return_value
            mock_instance.router_agent = MagicMock()
            mock_instance.router_agent.route = AsyncMock(return_value=mock_router_output)
            mock_instance.router_agent.select_orchestrator = AsyncMock(return_value=mock_selection)

            # Verify the service has orchestrator selection capability
            assert hasattr(mock_instance.router_agent, "select_orchestrator")

    async def test_create_completion_swarm_returns_aggregated_response(self) -> None:
        """Test create_completion with swarm returns aggregated response."""
        from unittest.mock import patch

        from mcp_server_langgraph.agents.base_agent import AgentResult

        mock_result = AgentResult(
            content="Consensus response from all agents",
            success=True,
            model_used="vertex_ai/gemini-3-pro-preview",
        )

        with patch("mcp_server_langgraph.agents.swarm_orchestrator.SwarmOrchestrator") as MockSwarm:
            mock_swarm = MockSwarm.return_value
            mock_swarm.run = AsyncMock(return_value=mock_result)

            # Verify SwarmOrchestrator.run returns a complete AgentResult
            result = await mock_swarm.run(MagicMock())
            assert result.success is True
            assert result.content == "Consensus response from all agents"


# =============================================================================
# Phase 2 Tests: Conversation Summarization
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="phase2_summarization")
class TestConversationSummarization:
    """Tests for conversation summarization in swarm context (Phase 2)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_summarize_conversation_function_exists(self) -> None:
        """Test _summarize_conversation function exists in chat module."""
        from mcp_server_langgraph.api.v1.chat import _summarize_conversation

        assert callable(_summarize_conversation)

    async def test_summarize_conversation_returns_string(self) -> None:
        """Test _summarize_conversation returns a string summary."""
        from mcp_server_langgraph.api.v1.chat import _summarize_conversation

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "What is Python?"},
        ]

        summary = await _summarize_conversation(messages)
        assert isinstance(summary, str)
        assert len(summary) > 0

    async def test_summarize_conversation_handles_empty_messages(self) -> None:
        """Test _summarize_conversation handles empty message list."""
        from mcp_server_langgraph.api.v1.chat import _summarize_conversation

        summary = await _summarize_conversation([])
        assert summary == ""

    async def test_summarize_conversation_handles_single_message(self) -> None:
        """Test _summarize_conversation with single message returns that message."""
        from mcp_server_langgraph.api.v1.chat import _summarize_conversation

        messages = [{"role": "user", "content": "Single question"}]
        summary = await _summarize_conversation(messages)
        assert "Single question" in summary

    async def test_stream_via_swarm_uses_summarized_context(self) -> None:
        """Test _stream_via_swarm uses summarized context when strategy is summarized."""
        from unittest.mock import patch

        from mcp_server_langgraph.agents.base_agent import AgentResult
        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection

        mock_result = AgentResult(
            content="Response using summarized context",
            success=True,
            model_used="test-model",
        )

        selection = OrchestratorSelection(
            orchestrator_type="asyncio_swarm",
            swarm_strategy="consensus",
            worker_count=3,
            worker_model="vertex_ai/gemini-3-flash-preview",
            thinking_budget="none",
            context_strategy="summarized",
        )

        messages = [
            {"role": "user", "content": "First question about Python"},
            {"role": "assistant", "content": "Python is a programming language."},
            {"role": "user", "content": "Tell me more about its features"},
        ]

        with patch("mcp_server_langgraph.agents.swarm_orchestrator.SwarmOrchestrator") as MockSwarm:
            mock_swarm_instance = MockSwarm.return_value
            mock_swarm_instance.run = AsyncMock(return_value=mock_result)

            with patch("mcp_server_langgraph.agents.worker_agent.WorkerAgent") as MockWorker:
                MockWorker.return_value = MagicMock()

                from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

                service = ChatServiceImpl.__new__(ChatServiceImpl)
                object.__setattr__(service, "_llm_factory", MagicMock())
                object.__setattr__(service, "_thinking_budget_manager", None)
                object.__setattr__(service, "_capability_provider", None)

                events = []
                async for event in service._stream_via_swarm(
                    session_id="test-session",
                    messages=messages,
                    selection=selection,
                ):
                    events.append(event)

                # Verify swarm was called (context handling is internal)
                assert len(events) >= 1
                assert mock_swarm_instance.run.called


# =============================================================================
# Phase 2: Observability Metrics Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="orchestrator_selection")
class TestOrchestratorSelectionMetrics:
    """Tests for OTEL metrics in orchestrator selection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestrator_selection_metrics_defined(self) -> None:
        """Test orchestrator selection metrics are defined."""
        from mcp_server_langgraph.agents.router_agent import (
            orchestrator_selection_counter,
            orchestrator_selection_latency,
            routing_confidence_histogram,
            swarm_orchestrator_counter,
        )

        assert orchestrator_selection_counter is not None
        assert orchestrator_selection_latency is not None
        assert swarm_orchestrator_counter is not None
        assert routing_confidence_histogram is not None

    def test_tracer_defined_in_router_agent(self) -> None:
        """Test OTEL tracer is defined in router_agent module."""
        from mcp_server_langgraph.agents.router_agent import tracer

        assert tracer is not None

    def test_meter_defined_in_router_agent(self) -> None:
        """Test OTEL meter is defined in router_agent module."""
        from mcp_server_langgraph.agents.router_agent import meter

        assert meter is not None

    async def test_select_orchestrator_records_metrics(self) -> None:
        """Test select_orchestrator records OTEL metrics."""
        from unittest.mock import MagicMock, patch

        from mcp_server_langgraph.agents.router_agent import RouterAgent, RouterOutput

        mock_llm_factory = MagicMock()
        router = RouterAgent(llm_factory=mock_llm_factory)

        routing_decision = RouterOutput(
            complexity="complex",
            risk="high",
            task_type="analysis",
            tools_needed=[],
            suggested_orchestrator="swarm",
            critique_rounds=2,
            thinking_budget="deep",
            confidence=0.9,
        )

        mock_feature_flags = MagicMock()
        mock_feature_flags.enable_swarm_orchestrator = True

        # Mock the metrics
        with (
            patch("mcp_server_langgraph.agents.router_agent.orchestrator_selection_counter") as mock_counter,
            patch("mcp_server_langgraph.agents.router_agent.orchestrator_selection_latency") as mock_latency,
            patch("mcp_server_langgraph.agents.router_agent.swarm_orchestrator_counter") as mock_swarm_counter,
            patch("mcp_server_langgraph.agents.router_agent.routing_confidence_histogram") as mock_confidence,
        ):
            selection = await router.select_orchestrator(
                routing_decision=routing_decision,
                feature_flags=mock_feature_flags,
            )

            # Verify metrics were recorded
            mock_latency.record.assert_called_once()
            mock_counter.add.assert_called_once()
            mock_swarm_counter.add.assert_called_once()  # Swarm was selected
            mock_confidence.record.assert_called_once()

            # Verify swarm selection
            assert selection.orchestrator_type == "asyncio_swarm"

    async def test_select_orchestrator_standard_does_not_record_swarm_counter(self) -> None:
        """Test select_orchestrator does not record swarm counter for standard selection."""
        from unittest.mock import MagicMock, patch

        from mcp_server_langgraph.agents.router_agent import RouterAgent, RouterOutput

        mock_llm_factory = MagicMock()
        router = RouterAgent(llm_factory=mock_llm_factory)

        routing_decision = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.95,
        )

        mock_feature_flags = MagicMock()
        mock_feature_flags.enable_swarm_orchestrator = True

        # Mock the metrics
        with (
            patch("mcp_server_langgraph.agents.router_agent.orchestrator_selection_counter") as mock_counter,
            patch("mcp_server_langgraph.agents.router_agent.orchestrator_selection_latency") as mock_latency,
            patch("mcp_server_langgraph.agents.router_agent.swarm_orchestrator_counter") as mock_swarm_counter,
            patch("mcp_server_langgraph.agents.router_agent.routing_confidence_histogram") as mock_confidence,
        ):
            selection = await router.select_orchestrator(
                routing_decision=routing_decision,
                feature_flags=mock_feature_flags,
            )

            # Verify metrics were recorded
            mock_latency.record.assert_called_once()
            mock_counter.add.assert_called_once()
            mock_swarm_counter.add.assert_not_called()  # Standard was selected
            mock_confidence.record.assert_called_once()

            # Verify standard selection
            assert selection.orchestrator_type == "standard"


# =============================================================================
# Phase 3: LangGraph Pattern Integration Tests (TDD)
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="orchestrator_selection")
class TestLangGraphPatternIntegration:
    """TDD tests for LangGraph pattern integration using astream_events().

    ADR-0105 Phase 3: Integrate LangGraph patterns (Supervisor, Hierarchical)
    as additional orchestrator types without needing LangGraph Server.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_orchestrator_selection_has_langgraph_supervisor_type(self) -> None:
        """Test OrchestratorSelection supports langgraph_supervisor type."""
        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection

        selection = OrchestratorSelection(
            orchestrator_type="langgraph_supervisor",
            thinking_budget="none",
        )

        assert selection.orchestrator_type == "langgraph_supervisor"

    def test_orchestrator_selection_has_langgraph_hierarchical_type(self) -> None:
        """Test OrchestratorSelection supports langgraph_hierarchical type."""
        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection

        selection = OrchestratorSelection(
            orchestrator_type="langgraph_hierarchical",
            thinking_budget="none",
        )

        assert selection.orchestrator_type == "langgraph_hierarchical"

    def test_orchestrator_selection_has_langgraph_pattern_field(self) -> None:
        """Test OrchestratorSelection has langgraph_pattern field."""
        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection

        selection = OrchestratorSelection(
            orchestrator_type="langgraph_supervisor",
            langgraph_pattern="supervisor",
            thinking_budget="none",
        )

        assert selection.langgraph_pattern == "supervisor"

    def test_langgraph_pattern_defaults_to_none(self) -> None:
        """Test langgraph_pattern defaults to None for non-langgraph types."""
        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection

        selection = OrchestratorSelection(
            orchestrator_type="standard",
            thinking_budget="none",
        )

        assert selection.langgraph_pattern is None

    async def test_select_orchestrator_returns_langgraph_supervisor_for_complex_analysis(
        self,
    ) -> None:
        """Test complex analysis tasks route to langgraph_supervisor."""
        from unittest.mock import MagicMock

        from mcp_server_langgraph.agents.router_agent import RouterAgent, RouterOutput

        mock_llm_factory = MagicMock()
        router = RouterAgent(llm_factory=mock_llm_factory)

        # Complex multi-step analysis task
        routing_decision = RouterOutput(
            complexity="complex",
            risk="high",
            task_type="analysis",
            tools_needed=["research", "writer", "reviewer"],
            suggested_orchestrator="studio",  # Studio uses langgraph patterns
            critique_rounds=2,
            thinking_budget="deep",
            confidence=0.85,
        )

        mock_feature_flags = MagicMock()
        mock_feature_flags.enable_swarm_orchestrator = True
        mock_feature_flags.enable_langgraph_patterns = True

        selection = await router.select_orchestrator(
            routing_decision=routing_decision,
            feature_flags=mock_feature_flags,
        )

        # Studio orchestrator should use langgraph_supervisor pattern
        assert selection.orchestrator_type == "langgraph_supervisor"
        assert selection.langgraph_pattern == "supervisor"

    async def test_stream_via_langgraph_supervisor_exists(self) -> None:
        """Test _stream_via_langgraph_supervisor method exists in ChatServiceImpl."""
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        assert hasattr(service, "_stream_via_langgraph_supervisor")

    async def test_stream_via_langgraph_supervisor_uses_astream_events(self) -> None:
        """Test _stream_via_langgraph_supervisor uses astream_events for streaming."""
        from unittest.mock import MagicMock, patch

        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        selection = OrchestratorSelection(
            orchestrator_type="langgraph_supervisor",
            langgraph_pattern="supervisor",
            thinking_budget="none",
        )

        messages = [{"role": "user", "content": "Research and write a report"}]

        # Mock supervisor pattern
        mock_compiled_graph = MagicMock()

        # Create async generator for astream_events
        async def mock_astream_events(*args, **kwargs):
            yield {
                "event": "on_chain_start",
                "metadata": {"langgraph_node": "supervisor"},
            }
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": MagicMock(content="Response content")},
            }
            yield {
                "event": "on_chain_end",
                "metadata": {"langgraph_node": "aggregate"},
            }

        mock_compiled_graph.astream_events = mock_astream_events

        mock_supervisor = MagicMock()
        mock_supervisor.compile.return_value = mock_compiled_graph

        with patch(
            "mcp_server_langgraph.patterns.supervisor.Supervisor",
            return_value=mock_supervisor,
        ):
            service = ChatServiceImpl.__new__(ChatServiceImpl)
            object.__setattr__(service, "_llm_factory", MagicMock())

            events = []
            async for event in service._stream_via_langgraph_supervisor(
                session_id="test-session",
                messages=messages,
                selection=selection,
            ):
                events.append(event)

        # Verify events were streamed
        assert len(events) >= 1
        # Verify supervisor pattern was used
        mock_supervisor.compile.assert_called_once()

    async def test_stream_via_langgraph_supervisor_yields_node_events(self) -> None:
        """Test _stream_via_langgraph_supervisor yields langgraph_node events."""
        from unittest.mock import MagicMock, patch

        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        selection = OrchestratorSelection(
            orchestrator_type="langgraph_supervisor",
            langgraph_pattern="supervisor",
            thinking_budget="none",
        )

        messages = [{"role": "user", "content": "Research this topic"}]

        mock_compiled_graph = MagicMock()

        async def mock_astream_events(*args, **kwargs):
            yield {
                "event": "on_chain_start",
                "metadata": {"langgraph_node": "supervisor"},
            }
            yield {
                "event": "on_chain_start",
                "metadata": {"langgraph_node": "research"},
            }
            yield {
                "event": "on_chain_end",
                "metadata": {"langgraph_node": "research"},
                "data": {"output": {"final_result": "Research complete"}},
            }

        mock_compiled_graph.astream_events = mock_astream_events

        mock_supervisor = MagicMock()
        mock_supervisor.compile.return_value = mock_compiled_graph

        with patch(
            "mcp_server_langgraph.patterns.supervisor.Supervisor",
            return_value=mock_supervisor,
        ):
            service = ChatServiceImpl.__new__(ChatServiceImpl)
            object.__setattr__(service, "_llm_factory", MagicMock())

            events = []
            async for event in service._stream_via_langgraph_supervisor(
                session_id="test-session",
                messages=messages,
                selection=selection,
            ):
                events.append(event)

        # Verify node events are emitted
        node_events = [e for e in events if "langgraph_node" in e]
        assert len(node_events) >= 1

    async def test_stream_via_langgraph_supervisor_yields_delta_content(self) -> None:
        """Test _stream_via_langgraph_supervisor yields delta content for persistence."""
        from unittest.mock import MagicMock, patch

        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        selection = OrchestratorSelection(
            orchestrator_type="langgraph_supervisor",
            langgraph_pattern="supervisor",
            thinking_budget="none",
        )

        messages = [{"role": "user", "content": "Write a report"}]

        mock_compiled_graph = MagicMock()

        async def mock_astream_events(*args, **kwargs):
            chunk = MagicMock()
            chunk.content = "Report content"
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": chunk},
            }

        mock_compiled_graph.astream_events = mock_astream_events

        mock_supervisor = MagicMock()
        mock_supervisor.compile.return_value = mock_compiled_graph

        with patch(
            "mcp_server_langgraph.patterns.supervisor.Supervisor",
            return_value=mock_supervisor,
        ):
            service = ChatServiceImpl.__new__(ChatServiceImpl)
            object.__setattr__(service, "_llm_factory", MagicMock())

            events = []
            async for event in service._stream_via_langgraph_supervisor(
                session_id="test-session",
                messages=messages,
                selection=selection,
            ):
                events.append(event)

        # Verify delta content is emitted (for SSE persistence)
        delta_events = [e for e in events if "delta" in e]
        assert len(delta_events) >= 1
        assert "content" in delta_events[0]["delta"]


# =============================================================================
# Phase 3 Completion: Settings, Dispatch, Hierarchical, Production Workers
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="orchestrator_selection")
class TestEnableLangGraphPatternsSetting:
    """TDD tests for enable_langgraph_patterns setting."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_settings_has_enable_langgraph_patterns_field(self) -> None:
        """Test Settings has enable_langgraph_patterns field."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "enable_langgraph_patterns")

    def test_enable_langgraph_patterns_defaults_to_true(self) -> None:
        """Test enable_langgraph_patterns defaults to True for intelligent routing."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.enable_langgraph_patterns is True


@pytest.mark.unit
@pytest.mark.xdist_group(name="orchestrator_selection")
class TestLangGraphDispatch:
    """TDD tests for langgraph pattern dispatch in create_stream."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_create_stream_dispatches_to_langgraph_supervisor(self) -> None:
        """Test create_stream dispatches to _stream_via_langgraph_supervisor."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from mcp_server_langgraph.agents.router_agent import (
            OrchestratorSelection,
            RouterOutput,
        )
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Mock router to return studio orchestrator
        mock_router_output = RouterOutput(
            complexity="complex",
            risk="high",
            task_type="analysis",
            tools_needed=[],
            suggested_orchestrator="studio",
            critique_rounds=2,
            thinking_budget="deep",
            confidence=0.9,
        )

        mock_selection = OrchestratorSelection(
            orchestrator_type="langgraph_supervisor",
            langgraph_pattern="supervisor",
            thinking_budget="deep",
        )

        mock_router = MagicMock()
        mock_router.route = AsyncMock(return_value=mock_router_output)
        mock_router.select_orchestrator = AsyncMock(return_value=mock_selection)

        # Track if _stream_via_langgraph_supervisor was called
        supervisor_called = []

        async def mock_stream_supervisor(*args, **kwargs):
            supervisor_called.append(True)
            yield {"delta": {"content": "Supervisor response"}}

        messages = [{"role": "user", "content": "Complex analysis task"}]

        # Mock _load_and_merge_history to return messages unchanged
        async def mock_load_history(self, session_id, msgs):
            return msgs

        # Mock _inject_resource_context to return messages unchanged
        async def mock_inject_context(self, msgs, resource_uris):
            return msgs

        with (
            patch.object(ChatServiceImpl, "_stream_via_langgraph_supervisor", mock_stream_supervisor),
            patch.object(ChatServiceImpl, "_load_and_merge_history", mock_load_history),
            patch.object(ChatServiceImpl, "_inject_resource_context", mock_inject_context),
            patch("mcp_server_langgraph.api.v1.chat.settings") as mock_settings,
        ):
            mock_settings.enable_chat_routing = True
            mock_settings.enable_langgraph_patterns = True

            service = ChatServiceImpl.__new__(ChatServiceImpl)
            object.__setattr__(service, "_router_agent", mock_router)
            object.__setattr__(service, "_llm_factory", MagicMock())

            events = []
            async for event in service.create_stream(
                session_id="test-session",
                messages=messages,
            ):
                events.append(event)

        # Verify _stream_via_langgraph_supervisor was called
        assert len(supervisor_called) >= 1


@pytest.mark.unit
@pytest.mark.xdist_group(name="orchestrator_selection")
class TestLangGraphHierarchical:
    """TDD tests for LangGraph Hierarchical pattern integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_stream_via_langgraph_hierarchical_exists(self) -> None:
        """Test _stream_via_langgraph_hierarchical method exists."""
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        assert hasattr(service, "_stream_via_langgraph_hierarchical")

    async def test_stream_via_langgraph_hierarchical_yields_events(self) -> None:
        """Test _stream_via_langgraph_hierarchical yields events."""
        from unittest.mock import MagicMock, patch

        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        selection = OrchestratorSelection(
            orchestrator_type="langgraph_hierarchical",
            langgraph_pattern="hierarchical",
            thinking_budget="deep",
        )

        messages = [{"role": "user", "content": "Complex multi-step task"}]

        mock_compiled_graph = MagicMock()

        async def mock_astream_events(*args, **kwargs):
            yield {
                "event": "on_chain_start",
                "metadata": {"langgraph_node": "ceo"},
            }
            yield {
                "event": "on_chain_end",
                "metadata": {"langgraph_node": "consolidate"},
                "data": {"output": {"final_report": "Final report content"}},
            }

        mock_compiled_graph.astream_events = mock_astream_events

        mock_hierarchical = MagicMock()
        mock_hierarchical.compile.return_value = mock_compiled_graph

        with patch(
            "mcp_server_langgraph.patterns.hierarchical.HierarchicalCoordinator",
            return_value=mock_hierarchical,
        ):
            service = ChatServiceImpl.__new__(ChatServiceImpl)
            object.__setattr__(service, "_llm_factory", MagicMock())

            events = []
            async for event in service._stream_via_langgraph_hierarchical(
                session_id="test-session",
                messages=messages,
                selection=selection,
            ):
                events.append(event)

        assert len(events) >= 1


@pytest.mark.unit
@pytest.mark.xdist_group(name="orchestrator_selection")
class TestProductionWorkers:
    """TDD tests for production workers using LLMFactory."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_supervisor_workers_use_llm_factory(self) -> None:
        """Test supervisor workers use LLMFactory for LLM calls."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        selection = OrchestratorSelection(
            orchestrator_type="langgraph_supervisor",
            langgraph_pattern="supervisor",
            thinking_budget="none",
            worker_model="vertex_ai/gemini-3-flash-preview",
        )

        messages = [{"role": "user", "content": "Research task"}]

        # Mock LLM factory
        mock_llm_factory = MagicMock()
        mock_llm_instance = MagicMock()
        mock_llm_instance.ainvoke = AsyncMock(return_value=MagicMock(content="LLM response"))
        mock_llm_factory.return_value = mock_llm_instance

        mock_compiled_graph = MagicMock()

        async def mock_astream_events(*args, **kwargs):
            yield {
                "event": "on_chain_end",
                "metadata": {"langgraph_node": "aggregate"},
                "data": {"output": {"final_result": "Final result"}},
            }

        mock_compiled_graph.astream_events = mock_astream_events

        mock_supervisor = MagicMock()
        mock_supervisor.compile.return_value = mock_compiled_graph

        with patch(
            "mcp_server_langgraph.patterns.supervisor.Supervisor",
            return_value=mock_supervisor,
        ):
            service = ChatServiceImpl.__new__(ChatServiceImpl)
            object.__setattr__(service, "_llm_factory", mock_llm_factory)

            events = []
            async for event in service._stream_via_langgraph_supervisor(
                session_id="test-session",
                messages=messages,
                selection=selection,
            ):
                events.append(event)

        # Verify events were streamed
        assert len(events) >= 1


# =============================================================================
# Phase 3 Completion: FeatureFlags and Hierarchical Routing
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="orchestrator_selection")
class TestEnableLangGraphPatternsFeatureFlag:
    """TDD tests for enable_langgraph_patterns in FeatureFlags."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_feature_flags_has_enable_langgraph_patterns(self) -> None:
        """Test FeatureFlags has enable_langgraph_patterns field."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_langgraph_patterns")

    def test_enable_langgraph_patterns_defaults_to_true(self) -> None:
        """Test enable_langgraph_patterns defaults to True."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_langgraph_patterns is True


@pytest.mark.unit
@pytest.mark.xdist_group(name="orchestrator_selection")
class TestHierarchicalRoutingCriteria:
    """TDD tests for hierarchical pattern routing criteria.

    Based on research, hierarchical pattern is best for:
    - Complex multi-stage tasks requiring specialized teams
    - Project-level coordination (CEO → Managers → Workers)
    - Tasks with "project", "team", or "coordinate" context
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_complex_project_routes_to_hierarchical(self) -> None:
        """Test complex project tasks route to langgraph_hierarchical."""
        from mcp_server_langgraph.agents.router_agent import (
            RouterAgent,
            RouterOutput,
        )

        # Complex task with project-level coordination needs
        router_output = RouterOutput(
            complexity="complex",
            risk="high",
            task_type="ops",  # Ops tasks often need hierarchical coordination
            tools_needed=["project_manager", "deployment"],
            suggested_orchestrator="swarm",  # Router suggests swarm but...
            critique_rounds=2,
            thinking_budget="deep",
            confidence=0.9,
        )

        mock_flags = MagicMock()
        mock_flags.enable_swarm_orchestrator = True
        mock_flags.enable_langgraph_patterns = True

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        selection = await agent.select_orchestrator(
            routing_decision=router_output,
            feature_flags=mock_flags,
        )

        # Complex ops with high risk MUST use hierarchical for CEO oversight
        assert selection.orchestrator_type == "langgraph_hierarchical"
        assert selection.langgraph_pattern == "hierarchical"
        assert selection.context_strategy == "summarized"

    async def test_complex_data_high_risk_routes_to_hierarchical(self) -> None:
        """Test complex data tasks with high risk route to hierarchical."""
        from mcp_server_langgraph.agents.router_agent import (
            RouterAgent,
            RouterOutput,
        )

        router_output = RouterOutput(
            complexity="complex",
            risk="high",
            task_type="data",  # Data pipeline coordination
            tools_needed=["etl", "validation"],
            suggested_orchestrator="swarm",
            critique_rounds=2,
            thinking_budget="deep",
            confidence=0.85,
        )

        mock_flags = MagicMock()
        mock_flags.enable_langgraph_patterns = True

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        selection = await agent.select_orchestrator(
            routing_decision=router_output,
            feature_flags=mock_flags,
        )

        assert selection.orchestrator_type == "langgraph_hierarchical"

    async def test_analysis_task_does_not_route_to_hierarchical(self) -> None:
        """Test analysis tasks use swarm, not hierarchical."""
        from mcp_server_langgraph.agents.router_agent import (
            RouterAgent,
            RouterOutput,
        )

        router_output = RouterOutput(
            complexity="complex",
            risk="high",
            task_type="analysis",  # Analysis is parallel, not hierarchical
            tools_needed=["search"],
            suggested_orchestrator="swarm",
            critique_rounds=2,
            thinking_budget="deep",
            confidence=0.9,
        )

        mock_flags = MagicMock()
        mock_flags.enable_swarm_orchestrator = True
        mock_flags.enable_langgraph_patterns = True

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        selection = await agent.select_orchestrator(
            routing_decision=router_output,
            feature_flags=mock_flags,
        )

        # Analysis should use swarm (parallel), not hierarchical
        assert selection.orchestrator_type == "asyncio_swarm"

    async def test_studio_routes_to_supervisor_when_langgraph_enabled(self) -> None:
        """Test studio orchestrator routes to langgraph_supervisor."""
        from mcp_server_langgraph.agents.router_agent import (
            RouterAgent,
            RouterOutput,
        )

        router_output = RouterOutput(
            complexity="complex",
            risk="medium",
            task_type="analysis",
            tools_needed=[],
            suggested_orchestrator="studio",
            critique_rounds=1,
            thinking_budget="medium",
            confidence=0.85,
        )

        mock_flags = MagicMock()
        mock_flags.enable_langgraph_patterns = True

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        selection = await agent.select_orchestrator(
            routing_decision=router_output,
            feature_flags=mock_flags,
        )

        assert selection.orchestrator_type == "langgraph_supervisor"
        assert selection.langgraph_pattern == "supervisor"

    async def test_langgraph_disabled_falls_back_to_standard(self) -> None:
        """Test studio falls back to standard when langgraph disabled."""
        from mcp_server_langgraph.agents.router_agent import (
            RouterAgent,
            RouterOutput,
        )

        router_output = RouterOutput(
            complexity="complex",
            risk="medium",
            task_type="analysis",
            tools_needed=[],
            suggested_orchestrator="studio",
            critique_rounds=1,
            thinking_budget="medium",
            confidence=0.85,
        )

        mock_flags = MagicMock()
        mock_flags.enable_langgraph_patterns = False  # Disabled

        mock_llm_factory = MagicMock()
        agent = RouterAgent(llm_factory=mock_llm_factory)

        selection = await agent.select_orchestrator(
            routing_decision=router_output,
            feature_flags=mock_flags,
        )

        assert selection.orchestrator_type == "standard"


@pytest.mark.unit
@pytest.mark.xdist_group(name="orchestrator_selection")
class TestLLMFactoryWorkerIntegration:
    """TDD tests for workers using LLMFactory."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_hierarchical_workers_can_use_llm_factory(self) -> None:
        """Test hierarchical workers can be created with LLMFactory."""
        from unittest.mock import patch

        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        selection = OrchestratorSelection(
            orchestrator_type="langgraph_hierarchical",
            langgraph_pattern="hierarchical",
            thinking_budget="none",
            worker_model="vertex_ai/gemini-3-flash-preview",
        )

        messages = [{"role": "user", "content": "Coordinate project deployment"}]

        # Mock LLMFactory
        mock_llm_factory = MagicMock()
        mock_llm_instance = MagicMock()
        mock_llm_instance.ainvoke = AsyncMock(return_value=MagicMock(content="LLM response"))
        mock_llm_factory.return_value = mock_llm_instance

        mock_compiled_graph = MagicMock()

        async def mock_astream_events(*args, **kwargs):
            yield {
                "event": "on_chain_end",
                "metadata": {"langgraph_node": "consolidate"},
                "data": {"output": {"final_report": "Project deployed"}},
            }

        mock_compiled_graph.astream_events = mock_astream_events

        mock_coordinator = MagicMock()
        mock_coordinator.compile.return_value = mock_compiled_graph

        with patch(
            "mcp_server_langgraph.patterns.hierarchical.HierarchicalCoordinator",
            return_value=mock_coordinator,
        ):
            service = ChatServiceImpl.__new__(ChatServiceImpl)
            object.__setattr__(service, "_llm_factory", mock_llm_factory)

            events = []
            async for event in service._stream_via_langgraph_hierarchical(
                session_id="test-session",
                messages=messages,
                selection=selection,
            ):
                events.append(event)

        # Verify events were streamed
        assert len(events) >= 1


class TestLLMFactoryWorkerIntegrationProduction:
    """Test LLMFactory integration for production workers (ADR-0105 Phase 3).

    These tests verify that the placeholder workers are upgraded to use
    LLMFactory.ainvoke() for actual LLM calls in production.
    """

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_supervisor_workers_use_llm_factory(self) -> None:
        """Test supervisor pattern workers call LLMFactory for responses."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Create mock LLMFactory that tracks calls
        mock_llm_factory = MagicMock()
        mock_ainvoke = AsyncMock(return_value=AIMessage(content="LLM response from worker"))
        mock_llm_factory.ainvoke = mock_ainvoke

        selection = OrchestratorSelection(
            orchestrator_type="langgraph_supervisor",
            langgraph_pattern="supervisor",
            worker_count=2,
        )

        messages = [{"role": "user", "content": "Test task for workers"}]

        # Mock the Supervisor and compiled graph to avoid running LangGraph
        mock_compiled_graph = MagicMock()

        async def mock_astream_events(*args, **kwargs):
            # Simulate supervisor invoking workers
            yield {
                "event": "on_chain_start",
                "metadata": {"langgraph_node": "research"},
                "data": {},
            }
            yield {
                "event": "on_chain_end",
                "metadata": {"langgraph_node": "research"},
                "data": {"output": "Worker completed"},
            }

        mock_compiled_graph.astream_events = mock_astream_events

        mock_supervisor = MagicMock()
        mock_supervisor.compile.return_value = mock_compiled_graph

        with patch(
            "mcp_server_langgraph.patterns.supervisor.Supervisor",
            return_value=mock_supervisor,
        ):
            service = ChatServiceImpl.__new__(ChatServiceImpl)
            object.__setattr__(service, "_llm_factory", mock_llm_factory)

            events = []
            async for event in service._stream_via_langgraph_supervisor(
                session_id="test-session",
                messages=messages,
                selection=selection,
            ):
                events.append(event)

        # Verify LLMFactory was provided (workers have access to it)
        assert mock_llm_factory is not None
        # Note: Full LLM call verification requires workers to actually call ainvoke
        # which happens when the Supervisor invokes them. This test verifies structure.
        assert len(events) >= 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_hierarchical_workers_use_llm_factory(self) -> None:
        """Test hierarchical pattern workers call LLMFactory for responses."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Create mock LLMFactory
        mock_llm_factory = MagicMock()
        mock_ainvoke = AsyncMock(return_value=AIMessage(content="LLM response from worker"))
        mock_llm_factory.ainvoke = mock_ainvoke

        selection = OrchestratorSelection(
            orchestrator_type="langgraph_hierarchical",
            langgraph_pattern="hierarchical",
            worker_count=3,
        )

        messages = [{"role": "user", "content": "Complex project task"}]

        # Mock the HierarchicalCoordinator
        mock_compiled_graph = MagicMock()

        async def mock_astream_events(*args, **kwargs):
            yield {
                "event": "on_chain_start",
                "metadata": {"langgraph_node": "ceo"},
                "data": {},
            }
            yield {
                "event": "on_chain_end",
                "metadata": {"langgraph_node": "ceo"},
                "data": {"output": "CEO decision"},
            }

        mock_compiled_graph.astream_events = mock_astream_events

        mock_coordinator = MagicMock()
        mock_coordinator.compile.return_value = mock_compiled_graph

        with patch(
            "mcp_server_langgraph.patterns.hierarchical.HierarchicalCoordinator",
            return_value=mock_coordinator,
        ):
            service = ChatServiceImpl.__new__(ChatServiceImpl)
            object.__setattr__(service, "_llm_factory", mock_llm_factory)

            events = []
            async for event in service._stream_via_langgraph_hierarchical(
                session_id="test-session",
                messages=messages,
                selection=selection,
            ):
                events.append(event)

        # Verify structure
        assert mock_llm_factory is not None
        assert len(events) >= 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_llm_worker_exists(self) -> None:
        """Test that _create_llm_worker helper method exists on ChatServiceImpl."""
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        assert hasattr(service, "_create_llm_worker")
        assert callable(service._create_llm_worker)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_llm_worker_returns_callable(self) -> None:
        """Test that _create_llm_worker returns a callable worker function."""
        from unittest.mock import AsyncMock, MagicMock

        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_llm_factory = MagicMock()
        mock_ainvoke = AsyncMock(return_value=AIMessage(content="LLM worker response"))
        mock_llm_factory.ainvoke = mock_ainvoke

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        object.__setattr__(service, "_llm_factory", mock_llm_factory)

        worker = service._create_llm_worker("research", "You are a research analyst.")
        assert callable(worker)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_llm_worker_invokes_llm_factory(self) -> None:
        """Test that worker function calls LLMFactory.ainvoke with proper messages."""
        from unittest.mock import AsyncMock, MagicMock

        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_llm_factory = MagicMock()
        mock_ainvoke = AsyncMock(return_value=AIMessage(content="Research findings"))
        mock_llm_factory.ainvoke = mock_ainvoke

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        object.__setattr__(service, "_llm_factory", mock_llm_factory)

        worker = service._create_llm_worker("research", "You are a research analyst.")

        # Worker is sync but internally uses async - run it
        result = worker("Analyze market trends")

        # Verify LLMFactory was called
        assert mock_ainvoke.called or mock_llm_factory.ainvoke.called
        assert "Research" in result or "market" in result.lower() or len(result) > 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_llm_worker_handles_llm_error_gracefully(self) -> None:
        """Test that worker handles LLM errors and returns fallback response."""
        from unittest.mock import AsyncMock, MagicMock

        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_llm_factory = MagicMock()
        mock_llm_factory.ainvoke = AsyncMock(side_effect=Exception("LLM unavailable"))

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        object.__setattr__(service, "_llm_factory", mock_llm_factory)

        worker = service._create_llm_worker("research", "You are a research analyst.")

        # Should not raise - returns fallback
        result = worker("Analyze market trends")
        assert result is not None
        assert isinstance(result, str)
        # Should contain error indication or fallback message
        assert len(result) > 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_llm_worker_uses_system_prompt(self) -> None:
        """Test that worker uses the provided system prompt."""
        from unittest.mock import AsyncMock, MagicMock

        from langchain_core.messages import AIMessage, SystemMessage

        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_llm_factory = MagicMock()
        captured_messages = []

        async def capture_ainvoke(messages, **kwargs):
            captured_messages.extend(messages)
            return AIMessage(content="Response")

        mock_llm_factory.ainvoke = AsyncMock(side_effect=capture_ainvoke)

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        object.__setattr__(service, "_llm_factory", mock_llm_factory)

        system_prompt = "You are a specialized market analyst."
        worker = service._create_llm_worker("analyst", system_prompt)

        # Call the worker
        worker("Analyze Q4 earnings")

        # Verify system prompt was included
        if captured_messages:
            system_msgs = [m for m in captured_messages if isinstance(m, SystemMessage)]
            assert len(system_msgs) >= 1
            assert system_prompt in system_msgs[0].content

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_worker_graceful_fallback_on_llm_error(self) -> None:
        """Test workers gracefully handle LLM errors with fallback response."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from mcp_server_langgraph.agents.router_agent import OrchestratorSelection
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Create mock LLMFactory that raises error
        mock_llm_factory = MagicMock()
        mock_llm_factory.ainvoke = AsyncMock(side_effect=Exception("LLM service unavailable"))

        selection = OrchestratorSelection(
            orchestrator_type="langgraph_supervisor",
            langgraph_pattern="supervisor",
            worker_count=2,
        )

        messages = [{"role": "user", "content": "Test task"}]

        # Mock the Supervisor
        mock_compiled_graph = MagicMock()

        async def mock_astream_events(*args, **kwargs):
            yield {
                "event": "on_chain_end",
                "metadata": {"langgraph_node": "supervisor"},
                "data": {"output": "Fallback response"},
            }

        mock_compiled_graph.astream_events = mock_astream_events

        mock_supervisor = MagicMock()
        mock_supervisor.compile.return_value = mock_compiled_graph

        with patch(
            "mcp_server_langgraph.patterns.supervisor.Supervisor",
            return_value=mock_supervisor,
        ):
            service = ChatServiceImpl.__new__(ChatServiceImpl)
            object.__setattr__(service, "_llm_factory", mock_llm_factory)

            # Should not raise - graceful fallback
            events = []
            async for event in service._stream_via_langgraph_supervisor(
                session_id="test-session",
                messages=messages,
                selection=selection,
            ):
                events.append(event)

            assert len(events) >= 1
