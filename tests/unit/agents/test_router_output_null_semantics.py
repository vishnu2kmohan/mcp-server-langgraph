"""Tests for RouterOutput null semantics (v35.0 Plan).

Tests that tools_needed and skills_needed:
1. Accept None values
2. Normalize empty lists to None via @model_validator
3. Preserve non-empty lists as-is

This ensures consistent NULL semantics for ExecutionPlan persistence.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestRouterOutputNullSemantics:
    """Test null semantics for RouterOutput tools_needed and skills_needed."""

    def test_tools_needed_accepts_none(self) -> None:
        """Test that tools_needed can be explicitly set to None."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=None,
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
        )

        assert output.tools_needed is None

    def test_skills_needed_accepts_none(self) -> None:
        """Test that skills_needed can be explicitly set to None."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=None,
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
            skills_needed=None,
        )

        assert output.skills_needed is None

    def test_empty_tools_needed_normalized_to_none(self) -> None:
        """Test that empty list for tools_needed is normalized to None.

        v35.0: Empty lists should be normalized to None via @model_validator
        for consistent NULL semantics in database persistence.
        """
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],  # Empty list should become None
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
        )

        assert output.tools_needed is None

    def test_empty_skills_needed_normalized_to_none(self) -> None:
        """Test that empty list for skills_needed is normalized to None.

        v35.0: Empty lists should be normalized to None via @model_validator
        for consistent NULL semantics in database persistence.
        """
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=None,
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
            skills_needed=[],  # Empty list should become None
        )

        assert output.skills_needed is None

    def test_non_empty_tools_needed_preserved(self) -> None:
        """Test that non-empty tools_needed list is preserved."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        tools = ["search", "calculator"]
        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=tools,
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
        )

        assert output.tools_needed == tools

    def test_non_empty_skills_needed_preserved(self) -> None:
        """Test that non-empty skills_needed list is preserved."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        skills = ["code_review", "testing"]
        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=None,
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
            skills_needed=skills,
        )

        assert output.skills_needed == skills

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.unit
class TestDefaultRouterOutputNullSemantics:
    """Test that DEFAULT_ROUTER_OUTPUT uses None for nullable fields."""

    def test_default_router_output_tools_needed_is_none(self) -> None:
        """Test that DEFAULT_ROUTER_OUTPUT.tools_needed is None (not empty list).

        v35.0: Sentinel value is None to indicate "use router suggestion".
        """
        from mcp_server_langgraph.agents.router_agent import DEFAULT_ROUTER_OUTPUT

        assert DEFAULT_ROUTER_OUTPUT.tools_needed is None

    def test_default_router_output_skills_needed_is_none(self) -> None:
        """Test that DEFAULT_ROUTER_OUTPUT.skills_needed is None (not empty list).

        v35.0: Sentinel value is None to indicate "use router suggestion".
        """
        from mcp_server_langgraph.agents.router_agent import DEFAULT_ROUTER_OUTPUT

        assert DEFAULT_ROUTER_OUTPUT.skills_needed is None

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.unit
class TestRouterOutputWithDiscoveryNullSemantics:
    """Test null semantics inherited by RouterOutputWithDiscovery."""

    def test_inherits_null_normalization(self) -> None:
        """Test that RouterOutputWithDiscovery inherits null normalization."""
        from mcp_server_langgraph.agents.router_agent import RouterOutputWithDiscovery

        output = RouterOutputWithDiscovery(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],  # Should normalize to None
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
            skills_needed=[],  # Should normalize to None
        )

        assert output.tools_needed is None
        assert output.skills_needed is None

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.unit
class TestRouterOutputWithTemplatesNullSemantics:
    """Test null semantics inherited by RouterOutputWithTemplates."""

    def test_inherits_null_normalization(self) -> None:
        """Test that RouterOutputWithTemplates inherits null normalization."""
        from mcp_server_langgraph.agents.router_agent import RouterOutputWithTemplates

        output = RouterOutputWithTemplates(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],  # Should normalize to None
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
            skills_needed=[],  # Should normalize to None
        )

        assert output.tools_needed is None
        assert output.skills_needed is None

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.unit
class TestRouterOutputToolPreferenceFields:
    """Test tool_preference and tool_selection_mode fields (v35.0 Phase 2e)."""

    def test_tool_preference_accepts_none(self) -> None:
        """Test that tool_preference accepts None."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=None,
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
            tool_preference=None,
        )

        assert output.tool_preference is None

    def test_tool_preference_accepts_string(self) -> None:
        """Test that tool_preference accepts string values."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=None,
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
            tool_preference="prefer_tools",
        )

        assert output.tool_preference == "prefer_tools"

    def test_tool_selection_mode_accepts_none(self) -> None:
        """Test that tool_selection_mode accepts None."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=None,
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
            tool_selection_mode=None,
        )

        assert output.tool_selection_mode is None

    def test_tool_selection_mode_accepts_valid_values(self) -> None:
        """Test that tool_selection_mode accepts valid literal values."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        for mode in ["auto", "manual", "hybrid"]:
            output = RouterOutput(
                complexity="simple",
                risk="low",
                task_type="chat",
                tools_needed=None,
                suggested_orchestrator="standard",
                critique_rounds=0,
                thinking_budget="none",
                confidence=0.9,
                tool_selection_mode=mode,
            )

            assert output.tool_selection_mode == mode

    def test_default_router_output_has_none_tool_preference(self) -> None:
        """Test that DEFAULT_ROUTER_OUTPUT has None for tool_preference."""
        from mcp_server_langgraph.agents.router_agent import DEFAULT_ROUTER_OUTPUT

        assert DEFAULT_ROUTER_OUTPUT.tool_preference is None

    def test_default_router_output_has_none_tool_selection_mode(self) -> None:
        """Test that DEFAULT_ROUTER_OUTPUT has None for tool_selection_mode."""
        from mcp_server_langgraph.agents.router_agent import DEFAULT_ROUTER_OUTPUT

        assert DEFAULT_ROUTER_OUTPUT.tool_selection_mode is None

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
