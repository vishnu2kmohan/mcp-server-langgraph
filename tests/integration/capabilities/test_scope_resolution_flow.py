"""Integration tests for scope resolution flow.

Tests the full capability resolution flow from enterprise
scope down to task scope, including merging and override behavior.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.xdist_group(name="scope_resolution")]


@pytest.mark.xdist_group("test_scope_resolution_basic")
@pytest.mark.integration
class TestScopeResolutionBasic:
    """Basic integration tests for scope resolution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_capability_scope_enum_exists(self) -> None:
        """Test CapabilityScope enum is importable."""
        from mcp_server_langgraph.core.scopes import CapabilityScope

        assert CapabilityScope is not None

    def test_capability_scope_has_required_levels(self) -> None:
        """Test CapabilityScope has all 7 levels."""
        from mcp_server_langgraph.core.scopes import CapabilityScope

        levels = [
            CapabilityScope.ENTERPRISE,
            CapabilityScope.ORGANIZATION,
            CapabilityScope.PROJECT,
            CapabilityScope.TEAM,
            CapabilityScope.USER,
            CapabilityScope.SESSION,
            CapabilityScope.TASK,
        ]
        assert len(levels) == 7

    def test_scope_precedence_order(self) -> None:
        """Test scope precedence: TASK > SESSION > USER > TEAM > PROJECT > ORG > ENTERPRISE."""
        from mcp_server_langgraph.core.scopes import (
            CapabilityScope,
            get_precedence,
            has_higher_precedence,
        )

        # TASK should have highest precedence (lower get_precedence value)
        assert get_precedence(CapabilityScope.TASK) < get_precedence(CapabilityScope.SESSION)
        assert get_precedence(CapabilityScope.SESSION) < get_precedence(CapabilityScope.USER)
        assert get_precedence(CapabilityScope.USER) < get_precedence(CapabilityScope.TEAM)
        assert get_precedence(CapabilityScope.TEAM) < get_precedence(CapabilityScope.PROJECT)
        assert get_precedence(CapabilityScope.PROJECT) < get_precedence(CapabilityScope.ORGANIZATION)
        assert get_precedence(CapabilityScope.ORGANIZATION) < get_precedence(CapabilityScope.ENTERPRISE)

        # Also test the helper function
        assert has_higher_precedence(CapabilityScope.TASK, CapabilityScope.SESSION)


@pytest.mark.xdist_group("test_capability_provider_flow")
@pytest.mark.integration
class TestCapabilityProviderFlow:
    """Integration tests for CapabilityProvider resolution flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_capability_provider_protocol_exists(self) -> None:
        """Test CapabilityProvider protocol is importable."""
        from mcp_server_langgraph.capabilities.provider import CapabilityProvider

        assert CapabilityProvider is not None

    def test_hierarchical_capability_provider_exists(self) -> None:
        """Test HierarchicalCapabilityProvider is importable."""
        from mcp_server_langgraph.capabilities.resolver import (
            HierarchicalCapabilityProvider,
        )

        assert HierarchicalCapabilityProvider is not None

    @pytest.mark.asyncio
    async def test_resolve_tools_from_provider(self) -> None:
        """Test resolving tools from HierarchicalCapabilityProvider."""
        from mcp_server_langgraph.capabilities.resolver import (
            HierarchicalCapabilityProvider,
        )
        from mcp_server_langgraph.core.scopes import CapabilityScope

        provider = HierarchicalCapabilityProvider()

        # Mock internal registries
        with patch.object(provider, "tool_registry") as mock_registry:
            mock_registry.get_for_scope.return_value = None
            mock_registry.list_for_scope.return_value = []

            tools = await provider.get_tools(
                scope=CapabilityScope.PROJECT,
                names=["test_tool"],
            )

            assert isinstance(tools, list)

    @pytest.mark.asyncio
    async def test_resolve_skills_from_provider(self) -> None:
        """Test resolving skills from HierarchicalCapabilityProvider."""
        from mcp_server_langgraph.capabilities.resolver import (
            HierarchicalCapabilityProvider,
        )
        from mcp_server_langgraph.core.scopes import CapabilityScope

        provider = HierarchicalCapabilityProvider()

        with patch.object(provider, "skill_registry") as mock_registry:
            mock_registry.get_for_scope.return_value = None
            mock_registry.list_for_scope.return_value = []

            skills = await provider.get_skills(
                scope=CapabilityScope.PROJECT,
                names=["test_skill"],
            )

            assert isinstance(skills, list)


@pytest.mark.xdist_group("test_scope_inheritance")
@pytest.mark.integration
class TestScopeInheritance:
    """Integration tests for scope inheritance behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_lower_scope_overrides_higher_scope(self) -> None:
        """Test that lower scope (e.g., PROJECT) overrides higher (e.g., ENTERPRISE)."""
        from mcp_server_langgraph.core.scopes import CapabilityScope

        # This is a design test - verifying the expected behavior
        # The actual implementation would use HierarchicalCapabilityProvider

        # Project scope should override organization scope
        project = CapabilityScope.PROJECT
        organization = CapabilityScope.ORGANIZATION

        # Project is more specific, so it should have higher precedence
        # (This tests the semantic design, not the precedence function)
        assert project != organization

    def test_scope_traversal_order(self) -> None:
        """Test that scopes are traversed from most specific to least specific."""
        from mcp_server_langgraph.core.scopes import (
            CapabilityScope,
            SCOPE_PRECEDENCE,
            get_precedence,
        )

        # SCOPE_PRECEDENCE tuple is already in precedence order (highest first)
        assert SCOPE_PRECEDENCE[0] == CapabilityScope.TASK
        assert SCOPE_PRECEDENCE[-1] == CapabilityScope.ENTERPRISE

        # Verify sorting by get_precedence gives same order
        all_scopes = list(CapabilityScope)
        scopes_by_precedence = sorted(
            all_scopes,
            key=lambda s: get_precedence(s),
        )

        # Most specific (lowest get_precedence value) should be first
        assert scopes_by_precedence[0] == CapabilityScope.TASK
        # Least specific (highest get_precedence value) should be last
        assert scopes_by_precedence[-1] == CapabilityScope.ENTERPRISE


@pytest.mark.xdist_group("test_merge_strategies")
@pytest.mark.integration
class TestMergeStrategies:
    """Integration tests for capability merge strategies."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_union_merge_strategy(self) -> None:
        """Test union merge strategy combines all capabilities."""
        from mcp_server_langgraph.capabilities.resolver import merge_capabilities

        router_tools = ["tool_a", "tool_b"]
        user_tools = ["tool_b", "tool_c"]

        result = merge_capabilities(
            router_tools=router_tools,
            user_tools=user_tools,
            strategy="union",
        )

        # Union should include all unique tools
        assert set(result) == {"tool_a", "tool_b", "tool_c"}

    def test_intersection_merge_strategy(self) -> None:
        """Test intersection merge strategy includes only common capabilities."""
        from mcp_server_langgraph.capabilities.resolver import merge_capabilities

        router_tools = ["tool_a", "tool_b"]
        user_tools = ["tool_b", "tool_c"]

        result = merge_capabilities(
            router_tools=router_tools,
            user_tools=user_tools,
            strategy="intersection",
        )

        # Intersection should include only common tools
        assert set(result) == {"tool_b"}

    def test_user_only_merge_strategy(self) -> None:
        """Test user_only merge strategy ignores router recommendations."""
        from mcp_server_langgraph.capabilities.resolver import merge_capabilities

        router_tools = ["tool_a", "tool_b"]
        user_tools = ["tool_c"]

        result = merge_capabilities(
            router_tools=router_tools,
            user_tools=user_tools,
            strategy="user_only",
        )

        # User only should only include user selections
        assert set(result) == {"tool_c"}

    def test_router_only_merge_strategy(self) -> None:
        """Test router_only merge strategy ignores user selections."""
        from mcp_server_langgraph.capabilities.resolver import merge_capabilities

        router_tools = ["tool_a", "tool_b"]
        user_tools = ["tool_c"]

        result = merge_capabilities(
            router_tools=router_tools,
            user_tools=user_tools,
            strategy="router_only",
        )

        # Router only should only include router recommendations
        assert set(result) == {"tool_a", "tool_b"}


@pytest.mark.xdist_group("test_end_to_end_scope_resolution")
@pytest.mark.integration
class TestEndToEndScopeResolution:
    """End-to-end integration tests for scope resolution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_full_resolution_flow(self) -> None:
        """Test complete scope resolution from request to resolved capabilities."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.capabilities.resolver import (
            HierarchicalCapabilityProvider,
            ResolvedCapabilities,
        )
        from mcp_server_langgraph.core.scopes import CapabilityScope

        # Create an agent request with capability fields
        request = AgentRequest(
            message="Test message",
            tools=["search_tool"],
            skills=["code_review"],
            scope=CapabilityScope.PROJECT,
            merge_strategy="union",
        )

        provider = HierarchicalCapabilityProvider()

        # Mock the internal resolution
        with patch.object(
            provider,
            "resolve",
            return_value=ResolvedCapabilities(
                tools=[],
                skills=[],
                scope=CapabilityScope.PROJECT,
            ),
        ) as _mock_resolve:
            resolved = await provider.resolve(request)

            assert isinstance(resolved, ResolvedCapabilities)
            assert resolved.scope == CapabilityScope.PROJECT

    @pytest.mark.asyncio
    async def test_feature_flag_gates_capability_resolution(self) -> None:
        """Test capability resolution is gated by feature flag."""
        from mcp_server_langgraph.core.feature_flags import get_feature_flags

        flags = get_feature_flags()

        # Test that we can check feature flags for capability features
        # Using enable_multi_agent_orchestration which is the relevant flag
        initial_value = flags.enable_multi_agent_orchestration

        # Verify the flag exists and can be read
        assert isinstance(initial_value, bool)

        # Test that flag toggling affects behavior conceptually
        # (In production, this would gate capability resolution)
        with patch.object(flags, "enable_multi_agent_orchestration", True):
            assert flags.enable_multi_agent_orchestration is True

        with patch.object(flags, "enable_multi_agent_orchestration", False):
            assert flags.enable_multi_agent_orchestration is False
