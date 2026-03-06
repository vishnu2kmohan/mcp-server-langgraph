"""Tests for CapabilityProvider protocol.

TDD: These tests define the contract for CapabilityProvider - the core abstraction
that enables composition-based tool/skill awareness for all agents.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
class TestCapabilityProviderProtocol:
    """Tests for CapabilityProvider protocol definition."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_capability_provider_module_exists(self) -> None:
        """Test that capabilities.provider module exists."""
        from mcp_server_langgraph.capabilities import provider

        assert provider is not None

    def test_capability_provider_class_exists(self) -> None:
        """Test that CapabilityProvider class exists."""
        from mcp_server_langgraph.capabilities.provider import CapabilityProvider

        assert CapabilityProvider is not None

    def test_capability_provider_is_protocol(self) -> None:
        """Test CapabilityProvider is a Protocol (typing.Protocol)."""

        from mcp_server_langgraph.capabilities.provider import CapabilityProvider

        # Check it's runtime_checkable (can use isinstance)
        # Protocol classes decorated with @runtime_checkable have __protocol_attrs__
        assert hasattr(CapabilityProvider, "_is_protocol") or hasattr(CapabilityProvider, "__protocol_attrs__")

    def test_capability_provider_has_get_tools_method(self) -> None:
        """Test CapabilityProvider requires get_tools method."""
        from mcp_server_langgraph.capabilities.provider import CapabilityProvider

        # Protocol methods are defined as callable attributes
        assert hasattr(CapabilityProvider, "get_tools")

    def test_capability_provider_has_get_skills_method(self) -> None:
        """Test CapabilityProvider requires get_skills method."""
        from mcp_server_langgraph.capabilities.provider import CapabilityProvider

        assert hasattr(CapabilityProvider, "get_skills")

    def test_capability_provider_has_get_memory_method(self) -> None:
        """Test CapabilityProvider requires get_memory method."""
        from mcp_server_langgraph.capabilities.provider import CapabilityProvider

        assert hasattr(CapabilityProvider, "get_memory")


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
class TestCapabilityProviderTypes:
    """Tests for CapabilityProvider supporting types."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_tool_spec_exists(self) -> None:
        """Test ToolSpec dataclass exists."""
        from mcp_server_langgraph.capabilities.provider import ToolSpec

        assert ToolSpec is not None

    def test_tool_spec_has_name_field(self) -> None:
        """Test ToolSpec has name field."""
        from mcp_server_langgraph.capabilities.provider import ToolSpec

        spec = ToolSpec(name="file_reader", description="Reads files")
        assert spec.name == "file_reader"

    def test_tool_spec_has_description_field(self) -> None:
        """Test ToolSpec has description field."""
        from mcp_server_langgraph.capabilities.provider import ToolSpec

        spec = ToolSpec(name="file_reader", description="Reads files")
        assert spec.description == "Reads files"

    def test_tool_spec_has_optional_schema_field(self) -> None:
        """Test ToolSpec has optional schema field."""
        from mcp_server_langgraph.capabilities.provider import ToolSpec

        spec = ToolSpec(
            name="file_reader",
            description="Reads files",
            schema={"type": "object", "properties": {"path": {"type": "string"}}},
        )
        assert "path" in spec.schema["properties"]

    def test_skill_spec_exists(self) -> None:
        """Test SkillSpec dataclass exists."""
        from mcp_server_langgraph.capabilities.provider import SkillSpec

        assert SkillSpec is not None

    def test_skill_spec_has_name_field(self) -> None:
        """Test SkillSpec has name field."""
        from mcp_server_langgraph.capabilities.provider import SkillSpec

        spec = SkillSpec(name="summarize", description="Summarizes content")
        assert spec.name == "summarize"

    def test_skill_spec_has_description_field(self) -> None:
        """Test SkillSpec has description field."""
        from mcp_server_langgraph.capabilities.provider import SkillSpec

        spec = SkillSpec(name="summarize", description="Summarizes content")
        assert spec.description == "Summarizes content"

    def test_skill_spec_has_optional_category_field(self) -> None:
        """Test SkillSpec has optional category field."""
        from mcp_server_langgraph.capabilities.provider import SkillSpec

        spec = SkillSpec(name="summarize", description="Summarizes content", category="text")
        assert spec.category == "text"

    def test_memory_context_exists(self) -> None:
        """Test MemoryContext dataclass exists."""
        from mcp_server_langgraph.capabilities.provider import MemoryContext

        assert MemoryContext is not None

    def test_memory_context_has_working_memory_field(self) -> None:
        """Test MemoryContext has working_memory field."""
        from mcp_server_langgraph.capabilities.provider import MemoryContext

        ctx = MemoryContext(working_memory={"key": "value"})
        assert ctx.working_memory == {"key": "value"}

    def test_memory_context_has_session_memory_field(self) -> None:
        """Test MemoryContext has session_memory field."""
        from mcp_server_langgraph.capabilities.provider import MemoryContext

        ctx = MemoryContext(session_memory=["item1", "item2"])
        assert ctx.session_memory == ["item1", "item2"]


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
class TestCapabilityProviderImplementation:
    """Tests for implementing CapabilityProvider protocol."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_null_capability_provider_exists(self) -> None:
        """Test NullCapabilityProvider (no-op implementation) exists."""
        from mcp_server_langgraph.capabilities.provider import NullCapabilityProvider

        assert NullCapabilityProvider is not None

    def test_null_provider_implements_protocol(self) -> None:
        """Test NullCapabilityProvider implements CapabilityProvider protocol."""
        from mcp_server_langgraph.capabilities.provider import (
            NullCapabilityProvider,
        )

        provider = NullCapabilityProvider()
        # Check it has the required methods
        assert hasattr(provider, "get_tools")
        assert hasattr(provider, "get_skills")
        assert hasattr(provider, "get_memory")

    @pytest.mark.asyncio
    async def test_null_provider_get_tools_returns_empty(self) -> None:
        """Test NullCapabilityProvider.get_tools returns empty list."""
        from mcp_server_langgraph.capabilities.provider import NullCapabilityProvider
        from mcp_server_langgraph.core.scopes import CapabilityScope

        provider = NullCapabilityProvider()
        tools = await provider.get_tools(CapabilityScope.TASK)
        assert tools == []

    @pytest.mark.asyncio
    async def test_null_provider_get_skills_returns_empty(self) -> None:
        """Test NullCapabilityProvider.get_skills returns empty list."""
        from mcp_server_langgraph.capabilities.provider import NullCapabilityProvider
        from mcp_server_langgraph.core.scopes import CapabilityScope

        provider = NullCapabilityProvider()
        skills = await provider.get_skills(CapabilityScope.TASK)
        assert skills == []

    @pytest.mark.asyncio
    async def test_null_provider_get_memory_returns_empty(self) -> None:
        """Test NullCapabilityProvider.get_memory returns empty context."""
        from mcp_server_langgraph.capabilities.provider import (
            NullCapabilityProvider,
        )
        from mcp_server_langgraph.core.scopes import CapabilityScope

        provider = NullCapabilityProvider()
        memory = await provider.get_memory(CapabilityScope.TASK)
        assert memory.working_memory == {}
        assert memory.session_memory == []


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
class TestResolvedCapabilities:
    """Tests for ResolvedCapabilities dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_resolved_capabilities_exists(self) -> None:
        """Test ResolvedCapabilities dataclass exists."""
        from mcp_server_langgraph.capabilities.provider import ResolvedCapabilities

        assert ResolvedCapabilities is not None

    def test_resolved_capabilities_has_tools_field(self) -> None:
        """Test ResolvedCapabilities has tools field."""
        from mcp_server_langgraph.capabilities.provider import (
            ResolvedCapabilities,
            ToolSpec,
        )

        resolved = ResolvedCapabilities(
            tools=[ToolSpec(name="test", description="test tool")],
            skills=[],
            memory=None,
        )
        assert len(resolved.tools) == 1
        assert resolved.tools[0].name == "test"

    def test_resolved_capabilities_has_skills_field(self) -> None:
        """Test ResolvedCapabilities has skills field."""
        from mcp_server_langgraph.capabilities.provider import (
            ResolvedCapabilities,
            SkillSpec,
        )

        resolved = ResolvedCapabilities(
            tools=[],
            skills=[SkillSpec(name="summarize", description="test skill")],
            memory=None,
        )
        assert len(resolved.skills) == 1
        assert resolved.skills[0].name == "summarize"

    def test_resolved_capabilities_has_memory_field(self) -> None:
        """Test ResolvedCapabilities has memory field."""
        from mcp_server_langgraph.capabilities.provider import (
            MemoryContext,
            ResolvedCapabilities,
        )

        memory = MemoryContext(working_memory={"key": "value"})
        resolved = ResolvedCapabilities(tools=[], skills=[], memory=memory)
        assert resolved.memory is not None
        assert resolved.memory.working_memory == {"key": "value"}

    def test_resolved_capabilities_has_scope_field(self) -> None:
        """Test ResolvedCapabilities has scope field."""
        from mcp_server_langgraph.capabilities.provider import ResolvedCapabilities
        from mcp_server_langgraph.core.scopes import CapabilityScope

        resolved = ResolvedCapabilities(tools=[], skills=[], memory=None, scope=CapabilityScope.PROJECT)
        assert resolved.scope == CapabilityScope.PROJECT

    def test_resolved_capabilities_scope_defaults_to_task(self) -> None:
        """Test ResolvedCapabilities.scope defaults to TASK."""
        from mcp_server_langgraph.capabilities.provider import ResolvedCapabilities
        from mcp_server_langgraph.core.scopes import CapabilityScope

        resolved = ResolvedCapabilities(tools=[], skills=[], memory=None)
        assert resolved.scope == CapabilityScope.TASK
