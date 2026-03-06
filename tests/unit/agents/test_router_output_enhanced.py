"""Tests for enhanced RouterOutput fields.

TDD: These tests define the contract for the 3 new fields added to RouterOutput
per ADR-0092 Hierarchical Capability Architecture.

New fields:
- skills_needed: list[str] - Skills the router recommends for the task
- execution_mode: Literal[...] - Execution mode selection
- routing_rationale: str - Explanation for routing decision
"""

from __future__ import annotations

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
class TestRouterOutputNewFields:
    """Tests for new RouterOutput fields."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_router_output_has_skills_needed_field(self) -> None:
        """Test RouterOutput has skills_needed field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
            skills_needed=["summarize", "translate"],
        )

        assert hasattr(output, "skills_needed")
        assert output.skills_needed == ["summarize", "translate"]

    def test_router_output_skills_needed_defaults_to_empty(self) -> None:
        """Test skills_needed defaults to empty list."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
        )

        assert output.skills_needed == []

    def test_router_output_has_execution_mode_field(self) -> None:
        """Test RouterOutput has execution_mode field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="complicated",
            risk="medium",
            task_type="code",
            tools_needed=["file_reader"],
            suggested_orchestrator="standard",
            critique_rounds=1,
            thinking_budget="medium",
            confidence=0.8,
            execution_mode="react",
        )

        assert hasattr(output, "execution_mode")
        assert output.execution_mode == "react"

    def test_router_output_execution_mode_defaults_to_tool_calling(self) -> None:
        """Test execution_mode defaults to 'tool_calling' for backward compat."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
        )

        assert output.execution_mode == "tool_calling"

    def test_router_output_execution_mode_valid_values(self) -> None:
        """Test execution_mode accepts all 5 valid values."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        valid_modes = ["pure_llm", "tool_calling", "react", "programmatic", "orchestrator"]

        for mode in valid_modes:
            output = RouterOutput(
                complexity="simple",
                risk="low",
                task_type="chat",
                tools_needed=[],
                suggested_orchestrator="standard",
                critique_rounds=0,
                thinking_budget="none",
                confidence=0.9,
                execution_mode=mode,
            )
            assert output.execution_mode == mode

    def test_router_output_has_routing_rationale_field(self) -> None:
        """Test RouterOutput has routing_rationale field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="complex",
            risk="high",
            task_type="ops",
            tools_needed=["deploy", "rollback"],
            suggested_orchestrator="swarm",
            critique_rounds=2,
            thinking_budget="deep",
            confidence=0.7,
            routing_rationale="High-risk deployment operation requires swarm orchestrator with multiple validation rounds.",
        )

        assert hasattr(output, "routing_rationale")
        assert "High-risk" in output.routing_rationale

    def test_router_output_routing_rationale_defaults_to_empty(self) -> None:
        """Test routing_rationale defaults to empty string."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
        )

        assert output.routing_rationale == ""


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
class TestRouterOutputBackwardCompatibility:
    """Tests ensuring backward compatibility with existing 8-field usage."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_existing_8_field_creation_still_works(self) -> None:
        """Test creating RouterOutput with only original 8 fields works."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        # This is the existing pattern used throughout the codebase
        output = RouterOutput(
            complexity="complicated",
            risk="medium",
            task_type="code",
            tools_needed=["file_reader", "code_search"],
            suggested_orchestrator="standard",
            critique_rounds=1,
            thinking_budget="light",
            confidence=0.85,
        )

        # All original fields should work
        assert output.complexity == "complicated"
        assert output.risk == "medium"
        assert output.task_type == "code"
        assert output.tools_needed == ["file_reader", "code_search"]
        assert output.suggested_orchestrator == "standard"
        assert output.critique_rounds == 1
        assert output.thinking_budget == "light"
        assert output.confidence == 0.85

    def test_new_fields_have_sensible_defaults(self) -> None:
        """Test new fields default to backward-compatible values."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
        )

        # New fields should have defaults that match current behavior
        assert output.skills_needed == []
        assert output.execution_mode == "tool_calling"
        assert output.routing_rationale == ""

    def test_default_router_output_includes_new_fields(self) -> None:
        """Test DEFAULT_ROUTER_OUTPUT constant includes new field defaults."""
        from mcp_server_langgraph.agents.router_agent import DEFAULT_ROUTER_OUTPUT

        # New fields should be present with defaults
        assert hasattr(DEFAULT_ROUTER_OUTPUT, "skills_needed")
        assert hasattr(DEFAULT_ROUTER_OUTPUT, "execution_mode")
        assert hasattr(DEFAULT_ROUTER_OUTPUT, "routing_rationale")

        # Defaults should be backward-compatible
        assert DEFAULT_ROUTER_OUTPUT.skills_needed == []
        assert DEFAULT_ROUTER_OUTPUT.execution_mode == "tool_calling"
        assert DEFAULT_ROUTER_OUTPUT.routing_rationale == ""

    def test_router_output_model_dump_includes_new_fields(self) -> None:
        """Test model_dump includes new fields for API serialization."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
        )

        dumped = output.model_dump()

        assert "skills_needed" in dumped
        assert "execution_mode" in dumped
        assert "routing_rationale" in dumped

    def test_router_output_extra_fields_ignored(self) -> None:
        """Test RouterOutput ignores unknown fields for forward compatibility."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        # This should not raise even with unknown fields
        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.9,
            # Unknown field that should be ignored
            unknown_future_field="some_value",
        )

        assert output.complexity == "simple"
        # Unknown field should not be stored
        assert not hasattr(output, "unknown_future_field")


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
class TestRouterOutputJsonParsing:
    """Tests for RouterOutput JSON parsing with new fields."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_parse_json_with_new_fields(self) -> None:
        """Test parsing JSON that includes new fields."""
        import json

        from mcp_server_langgraph.agents.router_agent import RouterOutput

        json_str = json.dumps(
            {
                "complexity": "complicated",
                "risk": "medium",
                "task_type": "analysis",
                "tools_needed": ["data_query"],
                "suggested_orchestrator": "standard",
                "critique_rounds": 1,
                "thinking_budget": "medium",
                "confidence": 0.8,
                "skills_needed": ["data_analysis", "visualization"],
                "execution_mode": "react",
                "routing_rationale": "Complex data analysis requires exploration",
            }
        )

        output = RouterOutput.model_validate_json(json_str)

        assert output.skills_needed == ["data_analysis", "visualization"]
        assert output.execution_mode == "react"
        assert output.routing_rationale == "Complex data analysis requires exploration"

    def test_parse_json_without_new_fields(self) -> None:
        """Test parsing legacy JSON without new fields uses defaults."""
        import json

        from mcp_server_langgraph.agents.router_agent import RouterOutput

        # Legacy JSON without new fields
        json_str = json.dumps(
            {
                "complexity": "simple",
                "risk": "low",
                "task_type": "chat",
                "tools_needed": [],
                "suggested_orchestrator": "standard",
                "critique_rounds": 0,
                "thinking_budget": "none",
                "confidence": 0.95,
            }
        )

        output = RouterOutput.model_validate_json(json_str)

        # Should use defaults
        assert output.skills_needed == []
        assert output.execution_mode == "tool_calling"
        assert output.routing_rationale == ""
