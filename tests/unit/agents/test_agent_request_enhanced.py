"""Tests for enhanced AgentRequest fields.

TDD: These tests define the contract for the 6 new fields added to AgentRequest
per ADR-0092 Hierarchical Capability Architecture.

New fields:
- tools: list[str] | None - Tools to bind for this request
- skills: list[str] | None - Skills to invoke for this request
- scope: CapabilityScope - Resolution scope for capabilities
- user_tool_selection: list[str] | None - User-specified tools
- user_skill_selection: list[str] | None - User-specified skills
- merge_strategy: str - How to merge router + user selections
"""

from __future__ import annotations

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="agent_request_enhanced")
class TestAgentRequestNewFields:
    """Tests for new AgentRequest fields."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_request_has_tools_field(self) -> None:
        """Test AgentRequest has tools field."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(
            message="Hello",
            tools=["file_reader", "code_search"],
        )

        assert hasattr(request, "tools")
        assert request.tools == ["file_reader", "code_search"]

    def test_agent_request_tools_defaults_to_none(self) -> None:
        """Test tools defaults to None (not empty list)."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(message="Hello")

        assert request.tools is None

    def test_agent_request_has_skills_field(self) -> None:
        """Test AgentRequest has skills field."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(
            message="Hello",
            skills=["summarize", "translate"],
        )

        assert hasattr(request, "skills")
        assert request.skills == ["summarize", "translate"]

    def test_agent_request_skills_defaults_to_none(self) -> None:
        """Test skills defaults to None."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(message="Hello")

        assert request.skills is None

    def test_agent_request_has_scope_field(self) -> None:
        """Test AgentRequest has scope field."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.core.scopes import CapabilityScope

        request = AgentRequest(
            message="Hello",
            scope=CapabilityScope.PROJECT,
        )

        assert hasattr(request, "scope")
        assert request.scope == CapabilityScope.PROJECT

    def test_agent_request_scope_defaults_to_task(self) -> None:
        """Test scope defaults to TASK (highest precedence)."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.core.scopes import CapabilityScope

        request = AgentRequest(message="Hello")

        assert request.scope == CapabilityScope.TASK

    def test_agent_request_has_user_tool_selection_field(self) -> None:
        """Test AgentRequest has user_tool_selection field."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(
            message="Hello",
            user_tool_selection=["web_search"],
        )

        assert hasattr(request, "user_tool_selection")
        assert request.user_tool_selection == ["web_search"]

    def test_agent_request_user_tool_selection_defaults_to_none(self) -> None:
        """Test user_tool_selection defaults to None."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(message="Hello")

        assert request.user_tool_selection is None

    def test_agent_request_has_user_skill_selection_field(self) -> None:
        """Test AgentRequest has user_skill_selection field."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(
            message="Hello",
            user_skill_selection=["code_review"],
        )

        assert hasattr(request, "user_skill_selection")
        assert request.user_skill_selection == ["code_review"]

    def test_agent_request_user_skill_selection_defaults_to_none(self) -> None:
        """Test user_skill_selection defaults to None."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(message="Hello")

        assert request.user_skill_selection is None

    def test_agent_request_has_merge_strategy_field(self) -> None:
        """Test AgentRequest has merge_strategy field."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(
            message="Hello",
            merge_strategy="user_only",
        )

        assert hasattr(request, "merge_strategy")
        assert request.merge_strategy == "user_only"

    def test_agent_request_merge_strategy_defaults_to_union(self) -> None:
        """Test merge_strategy defaults to 'union'."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(message="Hello")

        assert request.merge_strategy == "union"

    def test_agent_request_merge_strategy_valid_values(self) -> None:
        """Test merge_strategy accepts all valid values."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        valid_strategies = ["user_only", "router_only", "union", "intersection"]

        for strategy in valid_strategies:
            request = AgentRequest(message="Hello", merge_strategy=strategy)
            assert request.merge_strategy == strategy


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="agent_request_backward_compat")
class TestAgentRequestBackwardCompatibility:
    """Tests ensuring backward compatibility with existing 7-field usage."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_existing_7_field_creation_still_works(self) -> None:
        """Test creating AgentRequest with only original 7 fields works."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        # This is the existing pattern used throughout the codebase
        request = AgentRequest(
            message="Hello, how are you?",
            context={"session_id": "abc123"},
            thinking_budget="medium",
            max_tokens=1000,
            timeout_seconds=30.0,
            session_id="session123",
            trace_id="trace456",
        )

        # All original fields should work
        assert request.message == "Hello, how are you?"
        assert request.context == {"session_id": "abc123"}
        assert request.thinking_budget == "medium"
        assert request.max_tokens == 1000
        assert request.timeout_seconds == 30.0
        assert request.session_id == "session123"
        assert request.trace_id == "trace456"

    def test_new_fields_have_sensible_defaults(self) -> None:
        """Test new fields default to backward-compatible values."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.core.scopes import CapabilityScope

        request = AgentRequest(message="Hello")

        # New fields should have defaults that don't change behavior
        assert request.tools is None
        assert request.skills is None
        assert request.scope == CapabilityScope.TASK
        assert request.user_tool_selection is None
        assert request.user_skill_selection is None
        assert request.merge_strategy == "union"

    def test_dataclass_fields_count(self) -> None:
        """Test AgentRequest has at least 13 fields (7 original + 6 new)."""
        import dataclasses

        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(message="Hello")
        fields = [f.name for f in dataclasses.fields(request)]

        # Original 7 + 6 new = 13 minimum
        assert len(fields) >= 13

    def test_worker_agent_can_use_request_without_new_fields(self) -> None:
        """Test WorkerAgent works with request that doesn't set new fields."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        # Create request without any new fields (backward compat pattern)
        request = AgentRequest(
            message="Hello",
            thinking_budget="light",
        )

        # Request should be valid and usable
        assert request.message == "Hello"
        assert request.thinking_budget == "light"
        # New fields should have safe defaults
        assert request.tools is None
        assert request.skills is None


@pytest.mark.unit
@pytest.mark.agents
@pytest.mark.orchestrator
@pytest.mark.xdist_group(name="agent_request_full")
class TestAgentRequestFullUsage:
    """Tests for full AgentRequest usage with all fields."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_request_with_all_fields(self) -> None:
        """Test creating AgentRequest with all fields."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.core.scopes import CapabilityScope

        request = AgentRequest(
            # Original 7 fields
            message="Analyze this code",
            context={"file": "main.py"},
            thinking_budget="deep",
            max_tokens=4000,
            timeout_seconds=120.0,
            session_id="sess-001",
            trace_id="trace-001",
            # New 6 fields
            tools=["file_reader", "code_search"],
            skills=["code_analysis", "summarize"],
            scope=CapabilityScope.PROJECT,
            user_tool_selection=["web_search"],
            user_skill_selection=["explain"],
            merge_strategy="union",
        )

        # Verify all fields
        assert request.message == "Analyze this code"
        assert request.tools == ["file_reader", "code_search"]
        assert request.skills == ["code_analysis", "summarize"]
        assert request.scope == CapabilityScope.PROJECT
        assert request.user_tool_selection == ["web_search"]
        assert request.user_skill_selection == ["explain"]
        assert request.merge_strategy == "union"

    def test_agent_request_scope_comparison(self) -> None:
        """Test scope field can be compared with CapabilityScope enum."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.core.scopes import CapabilityScope

        request = AgentRequest(
            message="Hello",
            scope=CapabilityScope.SESSION,
        )

        assert request.scope == CapabilityScope.SESSION
        assert request.scope != CapabilityScope.TASK
        assert request.scope == "session"  # StrEnum comparison
