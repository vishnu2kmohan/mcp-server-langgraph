"""
Tests for Agents MCP Handler

Tests for agents/orchestrate, agents/status, agents/cancel operations.
Following TDD - these tests define the expected behavior.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    from mcp_server_langgraph.mcp.handlers.agents import AgentsToolHandler


@pytest.mark.unit
@pytest.mark.mcp
@pytest.mark.multi_agent
@pytest.mark.xdist_group(name="mcp_agents_handler")
class TestAgentsToolHandler:
    """Tests for AgentsToolHandler."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handler_class_exists(self) -> None:
        """Test that AgentsToolHandler class exists."""
        from mcp_server_langgraph.mcp.handlers.agents import AgentsToolHandler

        assert AgentsToolHandler is not None

    def test_handler_initialization(self) -> None:
        """Test handler initialization with dependencies."""
        from mcp_server_langgraph.mcp.handlers.agents import AgentsToolHandler

        auth_mock = MagicMock()
        agent_graph_mock = MagicMock()

        handler = AgentsToolHandler(auth=auth_mock, agent_graph=agent_graph_mock)

        assert handler.auth == auth_mock
        assert handler.agent_graph == agent_graph_mock

    @pytest.mark.asyncio
    async def test_handle_decompose_task(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test decomposing a task into subtasks."""
        import sys

        from tests.fixtures.feature_flags_fixtures import MockFeatureFlags

        from mcp_server_langgraph.mcp.handlers.agents import AgentsToolHandler

        # Enable multi-agent orchestration feature flag for this test
        mock_flags = MockFeatureFlags(enable_multi_agent_orchestration=True)
        ff_module = sys.modules["mcp_server_langgraph.core.feature_flags"]
        monkeypatch.setattr(ff_module, "feature_flags", mock_flags)

        auth_mock = MagicMock()
        agent_graph_mock = MagicMock()
        handler = AgentsToolHandler(auth=auth_mock, agent_graph=agent_graph_mock)

        result = await handler.handle_decompose_task(
            arguments={
                "task": "Research quantum computing advances",
                "num_subtasks": 3,
            },
            span=MagicMock(),
            user_id="test-user",
        )

        assert isinstance(result, list)
        assert len(result) == 1
        # Should contain JSON with decomposition

    @pytest.mark.asyncio
    async def test_handle_orchestrate(self) -> None:
        """Test orchestrating a multi-agent task."""
        from mcp_server_langgraph.mcp.handlers.agents import AgentsToolHandler

        auth_mock = MagicMock()
        agent_graph_mock = MagicMock()
        handler = AgentsToolHandler(auth=auth_mock, agent_graph=agent_graph_mock)

        result = await handler.handle_orchestrate(
            arguments={
                "task": "Analyze and summarize this document",
                "strategy": "parallel",
            },
            span=MagicMock(),
            user_id="test-user",
        )

        assert isinstance(result, list)
        assert len(result) >= 1
        # Should contain orchestration result

    @pytest.mark.asyncio
    async def test_handle_orchestrate_feature_flag_disabled(self) -> None:
        """Test orchestration respects feature flag."""
        from mcp_server_langgraph.mcp.handlers.agents import AgentsToolHandler

        auth_mock = MagicMock()
        agent_graph_mock = MagicMock()
        handler = AgentsToolHandler(auth=auth_mock, agent_graph=agent_graph_mock)

        with patch("mcp_server_langgraph.mcp.handlers.agents.feature_flags") as ff_mock:
            ff_mock.enable_multi_agent_orchestration = False

            result = await handler.handle_orchestrate(
                arguments={"task": "Test task"},
                span=MagicMock(),
                user_id="test-user",
            )

            assert isinstance(result, list)
            assert "disabled" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_get_status(self) -> None:
        """Test getting status of an orchestration."""
        from mcp_server_langgraph.mcp.handlers.agents import AgentsToolHandler

        auth_mock = MagicMock()
        agent_graph_mock = MagicMock()
        handler = AgentsToolHandler(auth=auth_mock, agent_graph=agent_graph_mock)

        result = await handler.handle_get_status(
            arguments={"orchestration_id": "test-orch-123"},
            span=MagicMock(),
            user_id="test-user",
        )

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_handle_cancel(self) -> None:
        """Test cancelling an orchestration."""
        from mcp_server_langgraph.mcp.handlers.agents import AgentsToolHandler

        auth_mock = MagicMock()
        agent_graph_mock = MagicMock()
        handler = AgentsToolHandler(auth=auth_mock, agent_graph=agent_graph_mock)

        result = await handler.handle_cancel(
            arguments={"orchestration_id": "test-orch-123"},
            span=MagicMock(),
            user_id="test-user",
        )

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_handle_select_model(self) -> None:
        """Test selecting model for task complexity."""
        from mcp_server_langgraph.mcp.handlers.agents import AgentsToolHandler

        auth_mock = MagicMock()
        agent_graph_mock = MagicMock()
        handler = AgentsToolHandler(auth=auth_mock, agent_graph=agent_graph_mock)

        result = await handler.handle_select_model(
            arguments={"complexity": "complex"},
            span=MagicMock(),
            user_id="test-user",
        )

        assert isinstance(result, list)
        assert len(result) == 1
        # Should contain model recommendation


@pytest.mark.unit
@pytest.mark.mcp
@pytest.mark.multi_agent
@pytest.mark.xdist_group(name="mcp_agents_handler")
class TestAgentsToolHandlerIntegration:
    """Integration tests for AgentsToolHandler."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handler_uses_orchestrator(self) -> None:
        """Test handler integrates with Orchestrator."""
        from mcp_server_langgraph.mcp.handlers.agents import AgentsToolHandler
        from mcp_server_langgraph.agents import Orchestrator

        auth_mock = MagicMock()
        agent_graph_mock = MagicMock()
        orchestrator = Orchestrator()

        handler = AgentsToolHandler(
            auth=auth_mock,
            agent_graph=agent_graph_mock,
            orchestrator=orchestrator,
        )

        assert handler.orchestrator is orchestrator

    @pytest.mark.asyncio
    async def test_handler_uses_model_selector(self) -> None:
        """Test handler integrates with ModelSelector."""
        from mcp_server_langgraph.mcp.handlers.agents import AgentsToolHandler
        from mcp_server_langgraph.agents import ModelSelector

        auth_mock = MagicMock()
        agent_graph_mock = MagicMock()
        selector = ModelSelector()

        handler = AgentsToolHandler(
            auth=auth_mock,
            agent_graph=agent_graph_mock,
            model_selector=selector,
        )

        assert handler.model_selector is selector
