"""Tests for HierarchicalCapabilityProvider.

TDD: These tests define the contract for the hierarchical capability
provider that resolves tools, skills, and memory based on scope.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="hierarchical_provider_basic")
class TestHierarchicalCapabilityProviderBasic:
    """Tests for HierarchicalCapabilityProvider basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_hierarchical_provider_exists(self) -> None:
        """Test HierarchicalCapabilityProvider class exists."""
        from mcp_server_langgraph.capabilities.resolver import (
            HierarchicalCapabilityProvider,
        )

        assert HierarchicalCapabilityProvider is not None

    def test_hierarchical_provider_implements_protocol(self) -> None:
        """Test HierarchicalCapabilityProvider implements CapabilityProvider protocol."""
        from mcp_server_langgraph.capabilities.provider import CapabilityProvider
        from mcp_server_langgraph.capabilities.resolver import (
            HierarchicalCapabilityProvider,
        )

        provider = HierarchicalCapabilityProvider()
        assert isinstance(provider, CapabilityProvider)

    def test_hierarchical_provider_accepts_tool_registry(self) -> None:
        """Test HierarchicalCapabilityProvider accepts tool_registry parameter."""
        from mcp_server_langgraph.capabilities.resolver import (
            HierarchicalCapabilityProvider,
        )
        from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry

        tool_registry = HierarchicalToolRegistry()
        provider = HierarchicalCapabilityProvider(tool_registry=tool_registry)

        assert provider.tool_registry is tool_registry

    def test_hierarchical_provider_accepts_skill_registry(self) -> None:
        """Test HierarchicalCapabilityProvider accepts skill_registry parameter."""
        from mcp_server_langgraph.capabilities.resolver import (
            HierarchicalCapabilityProvider,
        )
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry

        skill_registry = HierarchicalSkillRegistry()
        provider = HierarchicalCapabilityProvider(skill_registry=skill_registry)

        assert provider.skill_registry is skill_registry

    def test_hierarchical_provider_accepts_memory_store(self) -> None:
        """Test HierarchicalCapabilityProvider accepts memory_store parameter."""
        from mcp_server_langgraph.capabilities.resolver import (
            HierarchicalCapabilityProvider,
        )
        from mcp_server_langgraph.memory.store import MemoryStore

        memory_store = MemoryStore()
        provider = HierarchicalCapabilityProvider(memory_store=memory_store)

        assert provider.memory_store is memory_store


@pytest.mark.unit
@pytest.mark.xdist_group(name="hierarchical_provider_tools")
class TestHierarchicalCapabilityProviderTools:
    """Tests for HierarchicalCapabilityProvider tool resolution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_tools_returns_list(self) -> None:
        """Test get_tools returns a list."""
        from mcp_server_langgraph.capabilities.resolver import (
            HierarchicalCapabilityProvider,
        )
        from mcp_server_langgraph.core.scopes import CapabilityScope

        provider = HierarchicalCapabilityProvider()
        tools = await provider.get_tools(CapabilityScope.TASK)

        assert isinstance(tools, list)

    @pytest.mark.asyncio
    async def test_get_tools_resolves_from_registry(self) -> None:
        """Test get_tools resolves tools from registry."""
        from mcp_server_langgraph.capabilities.provider import ToolSpec
        from mcp_server_langgraph.capabilities.resolver import (
            HierarchicalCapabilityProvider,
        )
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry

        tool_registry = HierarchicalToolRegistry()
        tool = ToolSpec(name="test-tool", description="Test tool")
        tool_registry.register_for_scope(tool, CapabilityScope.PROJECT)

        provider = HierarchicalCapabilityProvider(tool_registry=tool_registry)
        tools = await provider.get_tools(CapabilityScope.TASK, names=["test-tool"])

        assert len(tools) == 1
        assert tools[0].name == "test-tool"

    @pytest.mark.asyncio
    async def test_get_tools_filters_by_names(self) -> None:
        """Test get_tools filters by tool names."""
        from mcp_server_langgraph.capabilities.provider import ToolSpec
        from mcp_server_langgraph.capabilities.resolver import (
            HierarchicalCapabilityProvider,
        )
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry

        tool_registry = HierarchicalToolRegistry()
        tool1 = ToolSpec(name="tool-1", description="Tool 1")
        tool2 = ToolSpec(name="tool-2", description="Tool 2")
        tool_registry.register_for_scope(tool1, CapabilityScope.PROJECT)
        tool_registry.register_for_scope(tool2, CapabilityScope.PROJECT)

        provider = HierarchicalCapabilityProvider(tool_registry=tool_registry)
        tools = await provider.get_tools(CapabilityScope.TASK, names=["tool-1"])

        assert len(tools) == 1
        assert tools[0].name == "tool-1"


@pytest.mark.unit
@pytest.mark.xdist_group(name="hierarchical_provider_skills")
class TestHierarchicalCapabilityProviderSkills:
    """Tests for HierarchicalCapabilityProvider skill resolution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_skills_returns_list(self) -> None:
        """Test get_skills returns a list."""
        from mcp_server_langgraph.capabilities.resolver import (
            HierarchicalCapabilityProvider,
        )
        from mcp_server_langgraph.core.scopes import CapabilityScope

        provider = HierarchicalCapabilityProvider()
        skills = await provider.get_skills(CapabilityScope.TASK)

        assert isinstance(skills, list)

    @pytest.mark.asyncio
    async def test_get_skills_resolves_from_registry(self) -> None:
        """Test get_skills resolves skills from registry."""
        from mcp_server_langgraph.capabilities.resolver import (
            HierarchicalCapabilityProvider,
        )
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.models import Skill

        skill_registry = HierarchicalSkillRegistry()
        skill = Skill(name="test-skill", description="Test skill", instructions="Do X")
        skill_registry.register_for_scope(skill, CapabilityScope.PROJECT)

        provider = HierarchicalCapabilityProvider(skill_registry=skill_registry)
        skills = await provider.get_skills(CapabilityScope.TASK, names=["test-skill"])

        assert len(skills) == 1
        assert skills[0].name == "test-skill"


@pytest.mark.unit
@pytest.mark.xdist_group(name="hierarchical_provider_memory")
class TestHierarchicalCapabilityProviderMemory:
    """Tests for HierarchicalCapabilityProvider memory resolution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_memory_returns_context(self) -> None:
        """Test get_memory returns MemoryContext."""
        from mcp_server_langgraph.capabilities.provider import MemoryContext
        from mcp_server_langgraph.capabilities.resolver import (
            HierarchicalCapabilityProvider,
        )
        from mcp_server_langgraph.core.scopes import CapabilityScope

        provider = HierarchicalCapabilityProvider()
        memory = await provider.get_memory(CapabilityScope.TASK)

        assert isinstance(memory, MemoryContext)

    @pytest.mark.asyncio
    async def test_get_memory_retrieves_relevant(self) -> None:
        """Test get_memory retrieves relevant memories."""
        from mcp_server_langgraph.capabilities.resolver import (
            HierarchicalCapabilityProvider,
        )
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.memory.store import MemoryStore
        from mcp_server_langgraph.memory.tiers import MemoryTier

        memory_store = MemoryStore()
        # Store a memory
        await memory_store.store(
            content="Python programming",
            tier=MemoryTier.WORKING,
            scope=CapabilityScope.TASK,
        )

        provider = HierarchicalCapabilityProvider(memory_store=memory_store)
        memory = await provider.get_memory(CapabilityScope.TASK, query="Python")

        # Should have relevant memories
        assert len(memory.relevant_memories) > 0
