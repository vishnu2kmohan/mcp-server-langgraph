"""Tests for Chat Critique Loop Integration.

TDD: These tests verify that the critique loop is properly integrated
into the chat.py create_stream() method, including:
- Feature flag gating
- SSE event emission for critique_status
- Fallback behavior on errors

PYTEST-XDIST FIX: Uses gc.collect() in teardown for memory safety.
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestChatCritiqueIntegration:
    """Tests for critique loop integration in create_stream."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_critique_loop_triggered_when_enabled_and_high_risk(self) -> None:
        """GIVEN critique loop enabled and routing indicates high risk
        WHEN create_stream is called
        THEN CritiqueExecutor is used
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        # Create service with mocked dependencies
        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = AsyncMock(return_value=None)
        service._session_storage.get_messages = AsyncMock(return_value=[])
        service._mcp_bridge = None
        service._langgraph_agent = None
        service._router_agent = AsyncMock(return_value=None)
        service._llm_factory = MagicMock()

        # Mock routing decision with high risk
        mock_routing = MagicMock()
        mock_routing.complexity = "complex"
        mock_routing.risk = "high"
        mock_routing.task_type = "code"
        mock_routing.tools_needed = []
        mock_routing.suggested_orchestrator = "standard"
        mock_routing.critique_rounds = 2
        mock_routing.thinking_budget = "medium"
        mock_routing.confidence = 0.9
        mock_routing.skills_needed = []
        mock_routing.execution_mode = "react"
        mock_routing.routing_rationale = "Complex task"
        mock_routing.tool_preference = None
        mock_routing.tool_selection_mode = None

        service._router_agent.route = AsyncMock(return_value=mock_routing)

        # Mock CritiqueExecutor
        async def mock_critique_execute(*args: Any, **kwargs: Any):
            yield {"type": "executor_response", "round": 0, "content": "Response", "model": "gemini"}
            yield {
                "type": "critique",
                "round": 1,
                "result": MagicMock(approved=True, feedback=None, confidence=0.9),
                "model": "claude",
            }

        mock_critique_executor_class = MagicMock()
        mock_critique_executor_instance = MagicMock()
        mock_critique_executor_instance.execute_with_critique = mock_critique_execute
        mock_critique_executor_class.return_value = mock_critique_executor_instance

        mock_feature_flags = MagicMock()
        mock_feature_flags.enable_critique_loop = True
        mock_feature_flags.critique_cross_vendor = True
        mock_feature_flags.max_critique_rounds = 3
        mock_feature_flags.critique_streaming = True

        # Patch at the module where feature_flags is imported from
        with (
            patch(
                "mcp_server_langgraph.core.feature_flags.feature_flags",
                mock_feature_flags,
            ),
            patch(
                "mcp_server_langgraph.agents.critique_executor.CritiqueExecutor",
                mock_critique_executor_class,
            ),
            patch(
                "mcp_server_langgraph.agents.router_agent.select_executor_critic",
                side_effect=lambda *a, **kw: ("gemini-3-flash", "claude-haiku"),
            ),
        ):
            events = []
            async for event in service.create_stream(
                session_id="test-session",
                messages=[{"role": "user", "content": "Complex task"}],
                enable_routing=True,
            ):
                events.append(event)

        # Should have routing_decision, delta, and critique_status events
        event_types = [list(e.keys())[0] for e in events]
        assert "routing_decision" in event_types
        assert "delta" in event_types or "critique_status" in event_types

    @pytest.mark.asyncio
    async def test_critique_loop_skipped_when_disabled(self) -> None:
        """GIVEN critique loop disabled via feature flag
        WHEN create_stream is called with high-risk routing
        THEN standard streaming is used instead
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = AsyncMock(return_value=None)
        service._session_storage.get_messages = AsyncMock(return_value=[])
        service._mcp_bridge = None
        service._langgraph_agent = None
        service._router_agent = AsyncMock(return_value=None)
        service._llm_factory = MagicMock()

        # Mock routing decision with high risk
        mock_routing = MagicMock()
        mock_routing.complexity = "complex"
        mock_routing.risk = "high"
        mock_routing.critique_rounds = 2
        mock_routing.suggested_orchestrator = "standard"
        mock_routing.task_type = "code"
        mock_routing.tools_needed = []
        mock_routing.thinking_budget = "medium"
        mock_routing.confidence = 0.9
        mock_routing.skills_needed = []
        mock_routing.execution_mode = "react"
        mock_routing.routing_rationale = "Complex task"
        mock_routing.tool_preference = None
        mock_routing.tool_selection_mode = None

        service._router_agent.route = AsyncMock(return_value=mock_routing)

        mock_feature_flags = MagicMock()
        mock_feature_flags.enable_critique_loop = False  # Disabled

        # Mock LLMFactory streaming
        async def mock_stream(*args: Any, **kwargs: Any):
            yield {"delta": {"content": "Standard response"}}

        with (
            patch(
                "mcp_server_langgraph.core.feature_flags.feature_flags",
                mock_feature_flags,
            ),
            patch.object(service, "_stream_via_llm_factory", mock_stream),
        ):
            events = []
            async for event in service.create_stream(
                session_id="test-session",
                messages=[{"role": "user", "content": "Complex task"}],
                enable_routing=True,
            ):
                events.append(event)

        # Should NOT have critique_status events
        event_types = [list(e.keys())[0] for e in events]
        assert "critique_status" not in event_types

    @pytest.mark.asyncio
    async def test_critique_loop_skipped_for_low_risk(self) -> None:
        """GIVEN low-risk routing decision
        WHEN create_stream is called with critique loop enabled
        THEN critique loop is skipped (not worth the latency)
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = AsyncMock(return_value=None)
        service._session_storage.get_messages = AsyncMock(return_value=[])
        service._mcp_bridge = None
        service._langgraph_agent = None
        service._router_agent = AsyncMock(return_value=None)
        service._llm_factory = MagicMock()

        # Mock routing decision with LOW risk
        mock_routing = MagicMock()
        mock_routing.complexity = "simple"
        mock_routing.risk = "low"  # Low risk - skip critique
        mock_routing.critique_rounds = 0
        mock_routing.suggested_orchestrator = "standard"
        mock_routing.task_type = "chat"
        mock_routing.tools_needed = []
        mock_routing.thinking_budget = "none"
        mock_routing.confidence = 0.95
        mock_routing.skills_needed = []
        mock_routing.execution_mode = "direct"
        mock_routing.routing_rationale = "Simple greeting"
        mock_routing.tool_preference = None
        mock_routing.tool_selection_mode = None

        service._router_agent.route = AsyncMock(return_value=mock_routing)

        mock_feature_flags = MagicMock()
        mock_feature_flags.enable_critique_loop = True  # Enabled but should skip

        async def mock_stream(*args: Any, **kwargs: Any):
            yield {"delta": {"content": "Hello!"}}

        with (
            patch(
                "mcp_server_langgraph.core.feature_flags.feature_flags",
                mock_feature_flags,
            ),
            patch.object(service, "_stream_via_llm_factory", mock_stream),
        ):
            events = []
            async for event in service.create_stream(
                session_id="test-session",
                messages=[{"role": "user", "content": "Hello"}],
                enable_routing=True,
            ):
                events.append(event)

        # Should NOT have critique_status events (low risk skipped)
        event_types = [list(e.keys())[0] for e in events]
        assert "critique_status" not in event_types

    @pytest.mark.asyncio
    async def test_critique_status_events_include_model_info(self) -> None:
        """GIVEN critique streaming enabled
        WHEN critique loop executes
        THEN critique_status events include model information for DevTools
        """
        from mcp_server_langgraph.agents.critique_executor import CritiqueResult
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl.__new__(ChatServiceImpl)
        service._session_storage = AsyncMock(return_value=None)
        service._session_storage.get_messages = AsyncMock(return_value=[])
        service._mcp_bridge = None
        service._langgraph_agent = None
        service._router_agent = AsyncMock(return_value=None)
        service._llm_factory = MagicMock()

        mock_routing = MagicMock()
        mock_routing.complexity = "complex"
        mock_routing.risk = "high"
        mock_routing.critique_rounds = 1
        mock_routing.suggested_orchestrator = "standard"
        mock_routing.task_type = "analysis"
        mock_routing.tools_needed = []
        mock_routing.thinking_budget = "deep"
        mock_routing.confidence = 0.85
        mock_routing.skills_needed = []
        mock_routing.execution_mode = "react"
        mock_routing.routing_rationale = "Analysis task"
        mock_routing.tool_preference = None
        mock_routing.tool_selection_mode = None

        service._router_agent.route = AsyncMock(return_value=mock_routing)

        # Mock CritiqueExecutor with model info
        async def mock_critique_execute(*args: Any, **kwargs: Any):
            yield {
                "type": "executor_response",
                "round": 0,
                "content": "Analysis result",
                "model": "vertex_ai/gemini-3-pro-preview",
            }
            yield {
                "type": "critique",
                "round": 1,
                "result": CritiqueResult(approved=True, feedback=None, confidence=0.92),
                "model": "vertex_ai/claude-sonnet-4-5@20250929",
            }

        mock_critique_executor_class = MagicMock()
        mock_critique_executor_instance = MagicMock()
        mock_critique_executor_instance.execute_with_critique = mock_critique_execute
        mock_critique_executor_class.return_value = mock_critique_executor_instance

        mock_feature_flags = MagicMock()
        mock_feature_flags.enable_critique_loop = True
        mock_feature_flags.critique_cross_vendor = True
        mock_feature_flags.max_critique_rounds = 3
        mock_feature_flags.critique_streaming = True

        with (
            patch(
                "mcp_server_langgraph.core.feature_flags.feature_flags",
                mock_feature_flags,
            ),
            patch(
                "mcp_server_langgraph.agents.critique_executor.CritiqueExecutor",
                mock_critique_executor_class,
            ),
            patch(
                "mcp_server_langgraph.agents.router_agent.select_executor_critic",
                side_effect=lambda *a, **kw: ("vertex_ai/gemini-3-pro-preview", "vertex_ai/claude-sonnet-4-5@20250929"),
            ),
        ):
            events = []
            async for event in service.create_stream(
                session_id="test-session",
                messages=[{"role": "user", "content": "Analyze this data"}],
                enable_routing=True,
            ):
                events.append(event)

        # Find critique_status events
        critique_events = [e for e in events if "critique_status" in e]
        assert len(critique_events) >= 1

        # Verify model info is included
        for ce in critique_events:
            status = ce["critique_status"]
            assert "model" in status
            assert "phase" in status
            assert "round" in status
