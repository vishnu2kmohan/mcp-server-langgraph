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
        mock_provider = AsyncMock(return_value=None)
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

        mock_provider = AsyncMock(return_value=None)
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
        mock_provider = AsyncMock(return_value=None)
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

        mock_provider = AsyncMock(return_value=None)
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

        mock_provider = AsyncMock(return_value=None)
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
class TestWorkerAgentBackwardCompatibility:
    """Tests for WorkerAgent backward compatibility without capability provider."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_legacy_run_without_capability_provider(self) -> None:
        """Test WorkerAgent runs without capability_provider (legacy path)."""
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        # Mock LLM factory response using ainvoke (returns AIMessage)
        mock_response = AIMessage(content="Hello, world!")

        llm_factory = MagicMock()
        llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        agent = WorkerAgent(llm_factory=llm_factory)
        request = AgentRequest(message="test")

        result = await agent.run(request)

        assert result.success is True
        assert result.content == "Hello, world!"

    @pytest.mark.asyncio
    async def test_run_handles_no_tools_gracefully(self) -> None:
        """Test WorkerAgent handles empty tools gracefully."""
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent
        from mcp_server_langgraph.capabilities.provider import NullCapabilityProvider

        # Mock LLM factory response using ainvoke (returns AIMessage)
        mock_response = AIMessage(content="Response without tools")

        llm_factory = MagicMock()
        llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        agent = WorkerAgent(llm_factory=llm_factory, capability_provider=NullCapabilityProvider())
        request = AgentRequest(message="test", tools=[])

        result = await agent.run(request)

        assert result.success is True


@pytest.mark.unit
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

        mock_provider = AsyncMock(return_value=None)
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


@pytest.mark.unit
class TestWorkerAgentRunUsesCapabilities:
    """Tests that run() actually wires and uses resolved capabilities.

    TDD: These tests verify Finding 3.1 - _resolve_capabilities is called
    during run() and the resolved tools are bound to the LLM.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_run_calls_resolve_capabilities_when_provider_set(self) -> None:
        """GIVEN WorkerAgent with capability_provider
        WHEN run() is called with tools in request
        THEN _resolve_capabilities should be called
        """
        from langchain_core.messages import AIMessage
        from unittest.mock import patch

        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent
        from mcp_server_langgraph.capabilities.provider import (
            MemoryContext,
            ToolSpec,
        )
        from mcp_server_langgraph.core.scopes import CapabilityScope

        mock_response = AIMessage(content="Tool response")

        llm_factory = MagicMock()
        llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        mock_provider = AsyncMock(return_value=None)
        mock_provider.get_tools = AsyncMock(return_value=[ToolSpec(name="tool1", description="Tool")])
        mock_provider.get_skills = AsyncMock(return_value=[])
        mock_provider.get_memory = AsyncMock(return_value=MemoryContext())

        agent = WorkerAgent(llm_factory=llm_factory, capability_provider=mock_provider)
        request = AgentRequest(
            message="test",
            tools=["tool1"],
            scope=CapabilityScope.TASK,
        )

        # Spy on _resolve_capabilities
        with patch.object(agent, "_resolve_capabilities", wraps=agent._resolve_capabilities) as spy:
            await agent.run(request)

            # _resolve_capabilities should have been called
            spy.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_run_binds_resolved_tools_to_llm(self) -> None:
        """GIVEN WorkerAgent with capability_provider
        WHEN run() is called with tools
        THEN the LLM should be called with bound tools
        """
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent
        from mcp_server_langgraph.capabilities.provider import (
            MemoryContext,
            ToolSpec,
        )
        from mcp_server_langgraph.core.scopes import CapabilityScope

        mock_response = AIMessage(content="Tool response")

        # Create a proper LLM mock that can bind tools
        llm_factory = MagicMock()
        llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        # Capture if bind_tools was called (or tools passed to ainvoke)
        ainvoke_kwargs_captured = {}

        async def capture_ainvoke(messages, **kwargs):
            ainvoke_kwargs_captured.update(kwargs)
            return mock_response

        llm_factory.ainvoke = capture_ainvoke

        # Create tool spec with callable and schema
        def dummy_tool(x: str) -> str:
            return x

        tool_spec = ToolSpec(
            name="tool1",
            description="Tool",
            callable=dummy_tool,
            schema={"type": "object", "properties": {"x": {"type": "string"}}},
        )

        mock_provider = AsyncMock(return_value=None)
        mock_provider.get_tools = AsyncMock(return_value=[tool_spec])
        mock_provider.get_skills = AsyncMock(return_value=[])
        mock_provider.get_memory = AsyncMock(return_value=MemoryContext())

        agent = WorkerAgent(llm_factory=llm_factory, capability_provider=mock_provider)
        request = AgentRequest(
            message="test",
            tools=["tool1"],
            scope=CapabilityScope.TASK,
        )

        await agent.run(request)

        # Verify that tools were passed to ainvoke
        # Implementation may pass tools as "tools" kwarg or use bind_tools
        assert "tools" in ainvoke_kwargs_captured, "Tools should be passed to LLM ainvoke"

    @pytest.mark.asyncio
    async def test_run_injects_memory_context_into_messages(self) -> None:
        """GIVEN WorkerAgent with capability_provider returning memory
        WHEN run() is called
        THEN memory context should be injected into messages
        """
        from langchain_core.messages import AIMessage, SystemMessage

        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent
        from mcp_server_langgraph.capabilities.provider import (
            MemoryContext,
        )
        from mcp_server_langgraph.core.scopes import CapabilityScope

        mock_response = AIMessage(content="Memory-aware response")

        # Capture messages passed to ainvoke
        messages_captured = []

        async def capture_ainvoke(messages, **kwargs):
            messages_captured.extend(messages)
            return mock_response

        llm_factory = MagicMock()
        llm_factory.ainvoke = capture_ainvoke

        # Memory with relevant context
        memory = MemoryContext(
            relevant_memories=["User prefers Python", "Previous topic was TDD"],
            working_memory={"summary": "Discussing software development"},
        )

        mock_provider = AsyncMock(return_value=None)
        mock_provider.get_tools = AsyncMock(return_value=[])
        mock_provider.get_skills = AsyncMock(return_value=[])
        mock_provider.get_memory = AsyncMock(return_value=memory)

        agent = WorkerAgent(llm_factory=llm_factory, capability_provider=mock_provider)
        request = AgentRequest(
            message="test",
            scope=CapabilityScope.TASK,
        )

        await agent.run(request)

        # Check that memory context was injected as system message
        system_messages = [m for m in messages_captured if isinstance(m, SystemMessage)]
        assert len(system_messages) > 0, "Memory context should be injected as SystemMessage"
        # Verify memory content is in the system message
        memory_content = " ".join(str(m.content) for m in system_messages)
        assert "Python" in memory_content or "TDD" in memory_content, "Memory facts should appear in system message"

    @pytest.mark.asyncio
    async def test_run_skips_capability_resolution_when_no_provider(self) -> None:
        """GIVEN WorkerAgent without capability_provider
        WHEN run() is called
        THEN it should work without calling capability resolution
        """
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent

        mock_response = AIMessage(content="Legacy response")

        llm_factory = MagicMock()
        llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        agent = WorkerAgent(llm_factory=llm_factory)
        request = AgentRequest(message="test")

        result = await agent.run(request)

        # Should succeed in legacy mode
        assert result.success is True
        assert result.content == "Legacy response"

    @pytest.mark.asyncio
    async def test_run_handles_empty_tools_gracefully(self) -> None:
        """GIVEN WorkerAgent with capability_provider returning no tools
        WHEN run() is called
        THEN it should work without binding tools
        """
        from langchain_core.messages import AIMessage

        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent
        from mcp_server_langgraph.capabilities.provider import (
            MemoryContext,
        )
        from mcp_server_langgraph.core.scopes import CapabilityScope

        mock_response = AIMessage(content="No tools response")

        llm_factory = MagicMock()
        llm_factory.ainvoke = AsyncMock(return_value=mock_response)

        mock_provider = AsyncMock(return_value=None)
        mock_provider.get_tools = AsyncMock(return_value=[])
        mock_provider.get_skills = AsyncMock(return_value=[])
        mock_provider.get_memory = AsyncMock(return_value=MemoryContext())

        agent = WorkerAgent(llm_factory=llm_factory, capability_provider=mock_provider)
        request = AgentRequest(
            message="test",
            tools=[],
            scope=CapabilityScope.TASK,
        )

        result = await agent.run(request)

        assert result.success is True
        assert result.content == "No tools response"
