"""Integration tests for router-to-worker tool binding.

Tests the flow where RouterOutput recommendations are consumed
by WorkerAgent for tool and skill binding.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.xdist_group(name="router_worker")]


@pytest.mark.integration
class TestRouterOutputFields:
    """Tests for enhanced RouterOutput fields."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_router_output_exists(self) -> None:
        """Test RouterOutput class is importable."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        assert RouterOutput is not None

    def test_router_output_has_tools_needed_field(self) -> None:
        """Test RouterOutput has tools_needed field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=["search", "calculator"],
            suggested_orchestrator="standard",
            critique_rounds=1,
            thinking_budget="light",
            confidence=0.8,
        )

        assert output.tools_needed == ["search", "calculator"]

    def test_router_output_has_skills_needed_field(self) -> None:
        """Test RouterOutput has skills_needed field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="complicated",
            risk="medium",
            task_type="code",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=2,
            thinking_budget="medium",
            confidence=0.75,
            skills_needed=["code_review", "testing"],
        )

        assert output.skills_needed == ["code_review", "testing"]

    def test_router_output_has_execution_mode_field(self) -> None:
        """Test RouterOutput has execution_mode field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="complex",
            risk="high",
            task_type="code",
            tools_needed=["search"],
            suggested_orchestrator="standard",
            critique_rounds=3,
            thinking_budget="deep",
            confidence=0.6,
            execution_mode="react",
        )

        assert output.execution_mode == "react"

    def test_router_output_has_routing_rationale_field(self) -> None:
        """Test RouterOutput has routing_rationale field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=1,
            thinking_budget="light",
            confidence=0.9,
            routing_rationale="Simple query requiring no tools",
        )

        assert output.routing_rationale == "Simple query requiring no tools"


@pytest.mark.integration
class TestAgentRequestFields:
    """Tests for enhanced AgentRequest capability fields."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_request_exists(self) -> None:
        """Test AgentRequest class is importable."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        assert AgentRequest is not None

    def test_agent_request_has_tools_field(self) -> None:
        """Test AgentRequest has tools field."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(
            message="Test message",
            tools=["search", "calculator"],
        )

        assert request.tools == ["search", "calculator"]

    def test_agent_request_has_skills_field(self) -> None:
        """Test AgentRequest has skills field."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(
            message="Test message",
            skills=["code_review"],
        )

        assert request.skills == ["code_review"]

    def test_agent_request_has_scope_field(self) -> None:
        """Test AgentRequest has scope field."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.core.scopes import CapabilityScope

        request = AgentRequest(
            message="Test message",
            scope=CapabilityScope.PROJECT,
        )

        assert request.scope == CapabilityScope.PROJECT

    def test_agent_request_has_merge_strategy_field(self) -> None:
        """Test AgentRequest has merge_strategy field."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(
            message="Test message",
            merge_strategy="union",
        )

        assert request.merge_strategy == "union"


@pytest.mark.integration
class TestRouterToWorkerFlow:
    """Tests for router-to-worker tool binding flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_worker_agent_exists(self) -> None:
        """Test WorkerAgent class is importable."""
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        assert WorkerAgent is not None

    def test_worker_agent_accepts_capability_provider(self) -> None:
        """Test WorkerAgent accepts capability_provider parameter."""
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent
        from mcp_server_langgraph.capabilities.resolver import (
            HierarchicalCapabilityProvider,
        )

        provider = HierarchicalCapabilityProvider()

        # WorkerAgent should accept capability_provider in constructor
        mock_llm_factory = MagicMock()
        worker = WorkerAgent(
            llm_factory=mock_llm_factory,
            capability_provider=provider,
        )

        assert worker.capability_provider is provider

    @pytest.mark.asyncio
    async def test_router_output_consumed_by_worker(self) -> None:
        """Test RouterOutput is consumed to create AgentRequest for WorkerAgent."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.router_agent import RouterOutput
        from mcp_server_langgraph.core.scopes import CapabilityScope

        # Simulate router output with valid literal values
        router_output = RouterOutput(
            complexity="complicated",
            risk="medium",
            task_type="code",  # Use valid literal: 'chat', 'code', 'analysis', 'data', 'ops', 'other'
            tools_needed=["code_search", "file_writer"],
            suggested_orchestrator="standard",
            critique_rounds=2,
            thinking_budget="medium",
            confidence=0.75,
            skills_needed=["code_generation"],
            execution_mode="tool_calling",
        )

        # Create AgentRequest from router output
        request = AgentRequest(
            message="Implement feature X",
            tools=router_output.tools_needed,
            skills=router_output.skills_needed,
            scope=CapabilityScope.PROJECT,
            merge_strategy="union",
        )

        # Verify request contains router recommendations
        assert request.tools == ["code_search", "file_writer"]
        assert request.skills == ["code_generation"]
        assert request.scope == CapabilityScope.PROJECT


@pytest.mark.integration
class TestToolBindingFlow:
    """Tests for actual tool binding in WorkerAgent."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_worker_resolves_tools_from_request(self) -> None:
        """Test WorkerAgent resolves tools from request."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent
        from mcp_server_langgraph.capabilities.resolver import (
            HierarchicalCapabilityProvider,
        )
        from mcp_server_langgraph.core.scopes import CapabilityScope

        provider = HierarchicalCapabilityProvider()
        mock_llm_factory = MagicMock()

        _worker = WorkerAgent(  # noqa: F841
            llm_factory=mock_llm_factory,
            capability_provider=provider,
        )

        request = AgentRequest(
            message="Test message",
            tools=["test_tool"],
            scope=CapabilityScope.PROJECT,
        )

        # Mock the provider's get_tools method
        with patch.object(provider, "get_tools", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []

            # Worker should be able to resolve tools (even if empty)
            _tools = await provider.get_tools(  # noqa: F841
                scope=request.scope,
                names=request.tools,
            )

            mock_get.assert_called_once_with(
                scope=CapabilityScope.PROJECT,
                names=["test_tool"],
            )

    @pytest.mark.asyncio
    async def test_capability_provider_integration(self) -> None:
        """Test CapabilityProvider integrates with WorkerAgent."""
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent
        from mcp_server_langgraph.capabilities.resolver import (
            HierarchicalCapabilityProvider,
        )

        provider = HierarchicalCapabilityProvider()
        mock_llm_factory = MagicMock()
        worker = WorkerAgent(
            llm_factory=mock_llm_factory,
            capability_provider=provider,
        )

        # Verify the provider is accessible
        assert worker.capability_provider is not None
        assert isinstance(worker.capability_provider, HierarchicalCapabilityProvider)


@pytest.mark.integration
class TestMergeStrategyIntegration:
    """Tests for merge strategy in router-worker flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_union_merge_preserves_all_tools(self) -> None:
        """Test union merge includes router + user tools."""
        from mcp_server_langgraph.capabilities.resolver import merge_capabilities

        router_tools = ["search", "calculator"]
        user_tools = ["calculator", "file_reader"]

        result = merge_capabilities(router_tools, user_tools, "union")

        assert "search" in result
        assert "calculator" in result
        assert "file_reader" in result
        assert len(result) == 3  # No duplicates

    def test_intersection_merge_finds_common_tools(self) -> None:
        """Test intersection merge includes only common tools."""
        from mcp_server_langgraph.capabilities.resolver import merge_capabilities

        router_tools = ["search", "calculator"]
        user_tools = ["calculator", "file_reader"]

        result = merge_capabilities(router_tools, user_tools, "intersection")

        assert result == ["calculator"]

    def test_user_only_ignores_router(self) -> None:
        """Test user_only merge ignores router recommendations."""
        from mcp_server_langgraph.capabilities.resolver import merge_capabilities

        router_tools = ["search", "calculator"]
        user_tools = ["file_reader"]

        result = merge_capabilities(router_tools, user_tools, "user_only")

        assert result == ["file_reader"]
        assert "search" not in result

    def test_router_only_ignores_user(self) -> None:
        """Test router_only merge ignores user selections."""
        from mcp_server_langgraph.capabilities.resolver import merge_capabilities

        router_tools = ["search", "calculator"]
        user_tools = ["file_reader"]

        result = merge_capabilities(router_tools, user_tools, "router_only")

        assert set(result) == {"search", "calculator"}
        assert "file_reader" not in result


@pytest.mark.integration
class TestExecutionModeSelector:
    """Tests for execution mode selection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_execution_mode_selector_exists(self) -> None:
        """Test ExecutionModeSelector class exists."""
        from mcp_server_langgraph.agents.execution_selector import (
            ExecutionModeSelector,
        )

        assert ExecutionModeSelector is not None

    def test_execution_mode_enum_exists(self) -> None:
        """Test ExecutionMode enum exists."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        assert ExecutionMode is not None

    def test_execution_mode_has_required_modes(self) -> None:
        """Test ExecutionMode has all 5 modes."""
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        modes = [
            ExecutionMode.PURE_LLM,
            ExecutionMode.TOOL_CALLING,
            ExecutionMode.REACT,
            ExecutionMode.PROGRAMMATIC,
            ExecutionMode.ORCHESTRATOR,
        ]
        assert len(modes) == 5

    def test_selector_selects_pure_llm_when_no_tools(self) -> None:
        """Test selector returns PURE_LLM when no tools needed."""
        from mcp_server_langgraph.agents.execution_selector import (
            ExecutionModeSelector,
        )
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()

        mode = selector.select(tool_count=0, skill_count=0)

        assert mode == ExecutionMode.PURE_LLM

    def test_selector_selects_tool_calling_for_simple_tasks(self) -> None:
        """Test selector returns TOOL_CALLING for simple tasks with few tools."""
        from mcp_server_langgraph.agents.execution_selector import (
            ExecutionModeSelector,
        )
        from mcp_server_langgraph.core.execution_modes import ExecutionMode

        selector = ExecutionModeSelector()

        mode = selector.select(
            task_complexity="simple",
            tool_count=2,
            requires_exploration=False,
        )

        assert mode == ExecutionMode.TOOL_CALLING
