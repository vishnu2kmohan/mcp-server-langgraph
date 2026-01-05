"""Tests for WorkerAgent tool binding capabilities.

TDD: These tests define the contract for WorkerAgent tool binding
from request, user selection, and capability provider.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="worker_agent_tool_binding_basic")
class TestWorkerAgentToolBindingBasic:
    """Tests for WorkerAgent tool binding basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_worker_agent_accepts_capability_provider(self) -> None:
        """Test WorkerAgent can be initialized with capability_provider."""
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent
        from mcp_server_langgraph.capabilities.provider import NullCapabilityProvider

        llm_factory = MagicMock()
        provider = NullCapabilityProvider()

        agent = WorkerAgent(llm_factory=llm_factory, capability_provider=provider)

        assert agent.capability_provider is provider

    def test_worker_agent_capability_provider_defaults_none(self) -> None:
        """Test WorkerAgent capability_provider defaults to None."""
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        llm_factory = MagicMock()

        agent = WorkerAgent(llm_factory=llm_factory)

        assert agent.capability_provider is None

    def test_worker_agent_has_resolve_tools_method(self) -> None:
        """Test WorkerAgent has _resolve_tools method."""
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        llm_factory = MagicMock()
        agent = WorkerAgent(llm_factory=llm_factory)

        assert hasattr(agent, "_resolve_tools")
        assert callable(agent._resolve_tools)

    def test_worker_agent_has_resolve_capabilities_method(self) -> None:
        """Test WorkerAgent has _resolve_capabilities method."""
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        llm_factory = MagicMock()
        agent = WorkerAgent(llm_factory=llm_factory)

        assert hasattr(agent, "_resolve_capabilities")
        assert callable(agent._resolve_capabilities)


@pytest.mark.unit
@pytest.mark.xdist_group(name="worker_agent_tool_resolution")
class TestWorkerAgentToolResolution:
    """Tests for WorkerAgent tool resolution from request."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_resolve_tools_returns_empty_when_no_provider(self) -> None:
        """Test _resolve_tools returns empty list when no provider."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        llm_factory = MagicMock()
        agent = WorkerAgent(llm_factory=llm_factory)
        request = AgentRequest(message="test", tools=["tool1", "tool2"])

        tools = await agent._resolve_tools(request)

        assert tools == []

    @pytest.mark.asyncio
    async def test_resolve_tools_from_capability_provider(self) -> None:
        """Test _resolve_tools retrieves tools from capability provider."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent
        from mcp_server_langgraph.capabilities.provider import ToolSpec
        from mcp_server_langgraph.core.scopes import CapabilityScope

        llm_factory = MagicMock()

        # Mock capability provider
        mock_provider = AsyncMock()  # noqa: async-mock-config
        mock_provider.get_tools = AsyncMock(
            return_value=[
                ToolSpec(name="tool1", description="Tool 1"),
                ToolSpec(name="tool2", description="Tool 2"),
            ]
        )

        agent = WorkerAgent(llm_factory=llm_factory, capability_provider=mock_provider)
        request = AgentRequest(
            message="test",
            tools=["tool1", "tool2"],
            scope=CapabilityScope.TASK,
        )

        tools = await agent._resolve_tools(request)

        assert len(tools) == 2
        assert tools[0].name == "tool1"
        mock_provider.get_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolve_tools_with_user_selection_only(self) -> None:
        """Test _resolve_tools with user_only merge strategy."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent
        from mcp_server_langgraph.capabilities.provider import ToolSpec
        from mcp_server_langgraph.core.scopes import CapabilityScope

        llm_factory = MagicMock()

        mock_provider = AsyncMock()  # noqa: async-mock-config
        mock_provider.get_tools = AsyncMock(
            return_value=[
                ToolSpec(name="user_tool", description="User tool"),
            ]
        )

        agent = WorkerAgent(llm_factory=llm_factory, capability_provider=mock_provider)
        request = AgentRequest(
            message="test",
            tools=["router_tool"],
            user_tool_selection=["user_tool"],
            merge_strategy="user_only",
            scope=CapabilityScope.TASK,
        )

        tools = await agent._resolve_tools(request)

        # Should only have user selected tool
        assert len(tools) == 1
        assert tools[0].name == "user_tool"


@pytest.mark.unit
@pytest.mark.xdist_group(name="worker_agent_merge_strategies")
class TestWorkerAgentMergeStrategies:
    """Tests for WorkerAgent tool merge strategies."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_union_merge_strategy(self) -> None:
        """Test union merge strategy combines router + user tools."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent
        from mcp_server_langgraph.capabilities.provider import ToolSpec
        from mcp_server_langgraph.core.scopes import CapabilityScope

        llm_factory = MagicMock()

        # Provider returns all requested tools
        mock_provider = AsyncMock()  # noqa: async-mock-config
        mock_provider.get_tools = AsyncMock(
            return_value=[
                ToolSpec(name="router_tool", description="Router tool"),
                ToolSpec(name="user_tool", description="User tool"),
            ]
        )

        agent = WorkerAgent(llm_factory=llm_factory, capability_provider=mock_provider)
        request = AgentRequest(
            message="test",
            tools=["router_tool"],
            user_tool_selection=["user_tool"],
            merge_strategy="union",
            scope=CapabilityScope.TASK,
        )

        tools = await agent._resolve_tools(request)

        # Union: both router and user tools
        tool_names = [t.name for t in tools]
        assert "router_tool" in tool_names
        assert "user_tool" in tool_names

    @pytest.mark.asyncio
    async def test_intersection_merge_strategy(self) -> None:
        """Test intersection merge strategy returns only common tools."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent
        from mcp_server_langgraph.capabilities.provider import ToolSpec
        from mcp_server_langgraph.core.scopes import CapabilityScope

        llm_factory = MagicMock()

        mock_provider = AsyncMock()  # noqa: async-mock-config
        mock_provider.get_tools = AsyncMock(
            return_value=[
                ToolSpec(name="common_tool", description="Common tool"),
            ]
        )

        agent = WorkerAgent(llm_factory=llm_factory, capability_provider=mock_provider)
        request = AgentRequest(
            message="test",
            tools=["common_tool", "router_only"],
            user_tool_selection=["common_tool", "user_only"],
            merge_strategy="intersection",
            scope=CapabilityScope.TASK,
        )

        tools = await agent._resolve_tools(request)

        # Intersection: only tools in both lists
        assert len(tools) == 1
        assert tools[0].name == "common_tool"

    @pytest.mark.asyncio
    async def test_router_only_merge_strategy(self) -> None:
        """Test router_only merge strategy ignores user selection."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent
        from mcp_server_langgraph.capabilities.provider import ToolSpec
        from mcp_server_langgraph.core.scopes import CapabilityScope

        llm_factory = MagicMock()

        mock_provider = AsyncMock()  # noqa: async-mock-config
        mock_provider.get_tools = AsyncMock(
            return_value=[
                ToolSpec(name="router_tool", description="Router tool"),
            ]
        )

        agent = WorkerAgent(llm_factory=llm_factory, capability_provider=mock_provider)
        request = AgentRequest(
            message="test",
            tools=["router_tool"],
            user_tool_selection=["user_tool"],
            merge_strategy="router_only",
            scope=CapabilityScope.TASK,
        )

        tools = await agent._resolve_tools(request)

        # Router only: ignore user selection
        assert len(tools) == 1
        assert tools[0].name == "router_tool"


@pytest.mark.unit
@pytest.mark.xdist_group(name="worker_agent_backward_compat")
class TestWorkerAgentBackwardCompatibility:
    """Tests for WorkerAgent backward compatibility without capability provider."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_legacy_run_without_capability_provider(self) -> None:
        """Test WorkerAgent runs without capability_provider (legacy path)."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        # Mock LLM factory response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello, world!"
        mock_response.model = "test-model"

        llm_factory = MagicMock()
        llm_factory.create_completion = AsyncMock(return_value=mock_response)

        agent = WorkerAgent(llm_factory=llm_factory)
        request = AgentRequest(message="test")

        result = await agent.run(request)

        assert result.success is True
        assert result.content == "Hello, world!"

    @pytest.mark.asyncio
    async def test_run_handles_no_tools_gracefully(self) -> None:
        """Test WorkerAgent handles empty tools gracefully."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent
        from mcp_server_langgraph.capabilities.provider import NullCapabilityProvider

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response without tools"
        mock_response.model = "test-model"

        llm_factory = MagicMock()
        llm_factory.create_completion = AsyncMock(return_value=mock_response)

        agent = WorkerAgent(llm_factory=llm_factory, capability_provider=NullCapabilityProvider())
        request = AgentRequest(message="test", tools=[])

        result = await agent.run(request)

        assert result.success is True


@pytest.mark.unit
@pytest.mark.xdist_group(name="worker_agent_resolve_capabilities")
class TestWorkerAgentResolveCapabilities:
    """Tests for WorkerAgent _resolve_capabilities method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_resolve_capabilities_returns_resolved_object(self) -> None:
        """Test _resolve_capabilities returns ResolvedCapabilities."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent
        from mcp_server_langgraph.capabilities.provider import (
            MemoryContext,
            ResolvedCapabilities,
            SkillSpec,
            ToolSpec,
        )
        from mcp_server_langgraph.core.scopes import CapabilityScope

        llm_factory = MagicMock()

        mock_provider = AsyncMock()  # noqa: async-mock-config
        mock_provider.get_tools = AsyncMock(return_value=[ToolSpec(name="tool1", description="Tool 1")])
        mock_provider.get_skills = AsyncMock(return_value=[SkillSpec(name="skill1", description="Skill 1")])
        mock_provider.get_memory = AsyncMock(return_value=MemoryContext())

        agent = WorkerAgent(llm_factory=llm_factory, capability_provider=mock_provider)
        request = AgentRequest(
            message="test",
            tools=["tool1"],
            skills=["skill1"],
            scope=CapabilityScope.TASK,
        )

        capabilities = await agent._resolve_capabilities(request)

        assert isinstance(capabilities, ResolvedCapabilities)
        assert len(capabilities.tools) == 1
        assert len(capabilities.skills) == 1

    @pytest.mark.asyncio
    async def test_resolve_capabilities_empty_when_no_provider(self) -> None:
        """Test _resolve_capabilities returns empty when no provider."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent
        from mcp_server_langgraph.capabilities.provider import ResolvedCapabilities

        llm_factory = MagicMock()
        agent = WorkerAgent(llm_factory=llm_factory)
        request = AgentRequest(message="test")

        capabilities = await agent._resolve_capabilities(request)

        assert isinstance(capabilities, ResolvedCapabilities)
        assert capabilities.tools == []
        assert capabilities.skills == []
