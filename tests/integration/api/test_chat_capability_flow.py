"""Integration tests for Chat API capability flow.

Tests the integration of ADR-0092 capability architecture components:
- Router passes tools/skills/execution_mode to worker
- User tool/skill selections are respected
- Merge strategies work correctly

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.integration
@pytest.mark.xdist_group(name="capability_flow_router_output")
class TestCapabilityFlowRouterOutput:
    """Tests for router output capability fields."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_router_output_has_skills_needed(self) -> None:
        """Test RouterOutput includes skills_needed field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="complicated",
            risk="medium",
            task_type="code",
            tools_needed=["file_read", "file_write"],
            suggested_orchestrator="standard",
            critique_rounds=1,
            thinking_budget="light",
            confidence=0.85,
            skills_needed=["code-review", "testing"],
            execution_mode="tool_calling",
            routing_rationale="Code review requires file tools",
        )

        assert output.skills_needed == ["code-review", "testing"]

    def test_router_output_has_execution_mode(self) -> None:
        """Test RouterOutput includes execution_mode field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="complex",
            risk="high",
            task_type="ops",
            tools_needed=["deploy", "monitor"],
            suggested_orchestrator="standard",
            critique_rounds=2,
            thinking_budget="deep",
            confidence=0.75,
            skills_needed=[],
            execution_mode="orchestrator",
            routing_rationale="Complex deployment needs orchestration",
        )

        assert output.execution_mode == "orchestrator"

    def test_router_output_has_routing_rationale(self) -> None:
        """Test RouterOutput includes routing_rationale field."""
        from mcp_server_langgraph.agents.router_agent import RouterOutput

        output = RouterOutput(
            complexity="simple",
            risk="low",
            task_type="chat",
            tools_needed=[],
            suggested_orchestrator="standard",
            critique_rounds=0,
            thinking_budget="none",
            confidence=0.95,
            skills_needed=[],
            execution_mode="pure_llm",
            routing_rationale="Simple question needs no tools",
        )

        assert output.routing_rationale == "Simple question needs no tools"


@pytest.mark.integration
@pytest.mark.xdist_group(name="capability_flow_agent_request")
class TestCapabilityFlowAgentRequest:
    """Tests for AgentRequest capability fields."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_agent_request_has_tools_field(self) -> None:
        """Test AgentRequest includes tools field."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(
            message="Review this code",
            tools=["file_read", "file_write"],
        )

        assert request.tools == ["file_read", "file_write"]

    def test_agent_request_has_skills_field(self) -> None:
        """Test AgentRequest includes skills field."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(
            message="Review this code",
            skills=["code-review", "testing"],
        )

        assert request.skills == ["code-review", "testing"]

    def test_agent_request_has_scope_field(self) -> None:
        """Test AgentRequest includes scope field."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.core.scopes import CapabilityScope

        request = AgentRequest(
            message="Review this code",
            scope=CapabilityScope.PROJECT,
        )

        assert request.scope == CapabilityScope.PROJECT

    def test_agent_request_has_merge_strategy_field(self) -> None:
        """Test AgentRequest includes merge_strategy field."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(
            message="Review this code",
            merge_strategy="user_only",
        )

        assert request.merge_strategy == "user_only"

    def test_agent_request_default_merge_strategy_is_union(self) -> None:
        """Test AgentRequest default merge_strategy is 'union'."""
        from mcp_server_langgraph.agents.base_agent import AgentRequest

        request = AgentRequest(message="Hello")

        assert request.merge_strategy == "union"


@pytest.mark.integration
@pytest.mark.xdist_group(name="capability_flow_scope_resolution")
class TestCapabilityFlowScopeResolution:
    """Tests for capability scope resolution."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_scope_hierarchy_task_overrides_project(self) -> None:
        """Test task scope skills override project scope skills."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.models import Skill

        registry = HierarchicalSkillRegistry()

        # Register same skill at different scopes
        project_skill = Skill(name="code-review", description="Project level")
        task_skill = Skill(name="code-review", description="Task level override")

        registry.register_for_scope(project_skill, CapabilityScope.PROJECT)
        registry.register_for_scope(task_skill, CapabilityScope.TASK)

        # Task scope should return task-level skill
        resolved = registry.get_for_scope("code-review", CapabilityScope.TASK)

        assert resolved is not None
        assert resolved.description == "Task level override"

    def test_scope_resolution_includes_parent_scopes(self) -> None:
        """Test scope resolution includes skills from parent scopes."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.models import Skill

        registry = HierarchicalSkillRegistry()

        # Register skills at different scopes
        project_skill = Skill(name="project-skill", description="From project")
        session_skill = Skill(name="session-skill", description="From session")

        registry.register_for_scope(project_skill, CapabilityScope.PROJECT)
        registry.register_for_scope(session_skill, CapabilityScope.SESSION)

        # Task scope should see both via parent resolution
        all_skills = registry.list_for_scope(CapabilityScope.TASK, include_parent_scopes=True)

        skill_names = [s.name for s in all_skills]
        assert "project-skill" in skill_names
        assert "session-skill" in skill_names


@pytest.mark.integration
@pytest.mark.xdist_group(name="capability_flow_progressive")
class TestCapabilityFlowProgressive:
    """Tests for progressive capability loading."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_progressive_loader_respects_max_skills(self) -> None:
        """Test progressive loader respects max_skills limit."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.skills.progressive_loader import (
            ProgressiveSkillLoader,
        )

        registry = HierarchicalSkillRegistry()

        # Register many skills
        for i in range(10):
            skill = Skill(name=f"skill-{i}", description=f"Skill {i}")
            registry.register_for_scope(skill, CapabilityScope.PROJECT)

        loader = ProgressiveSkillLoader(skill_registry=registry)
        result = await loader.load_for_task(
            task_description="Do everything",
            scope=CapabilityScope.TASK,
            requested_skills=[f"skill-{i}" for i in range(10)],
            max_skills=3,
        )

        assert len(result) <= 3

    @pytest.mark.asyncio
    async def test_progressive_loader_prioritizes_requested_skills(self) -> None:
        """Test progressive loader prioritizes explicitly requested skills."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
        from mcp_server_langgraph.skills.models import Skill
        from mcp_server_langgraph.skills.progressive_loader import (
            ProgressiveSkillLoader,
        )

        registry = HierarchicalSkillRegistry()

        requested = Skill(name="requested-skill", description="Explicitly requested")
        default = Skill(name="default-skill", description="Default", tags=["default"])

        registry.register_for_scope(requested, CapabilityScope.PROJECT)
        registry.register_for_scope(default, CapabilityScope.PROJECT)

        loader = ProgressiveSkillLoader(skill_registry=registry)
        result = await loader.load_for_task(
            task_description="Task",
            scope=CapabilityScope.TASK,
            requested_skills=["requested-skill"],
            include_defaults=True,
            max_skills=1,
        )

        # Requested skill should be first and only one returned
        assert len(result) == 1
        assert result[0].name == "requested-skill"


@pytest.mark.integration
@pytest.mark.xdist_group(name="capability_flow_execution_mode")
class TestCapabilityFlowExecutionMode:
    """Tests for execution mode selection integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_task_analyzer_suggests_execution_mode(self) -> None:
        """Test TaskAnalyzer includes suggested_execution_mode."""
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()

        # Simple task - should suggest pure_llm or tool_calling
        simple_result = analyzer.analyze("What is Python?")
        assert simple_result.suggested_execution_mode in ["pure_llm", "tool_calling"]

        # Complex exploration task - should suggest react
        explore_result = analyzer.analyze("Find all occurrences of the bug")
        assert explore_result.suggested_execution_mode == "react"

    def test_execution_mode_selector_integrates_with_task_analysis(self) -> None:
        """Test ExecutionModeSelector uses TaskAnalysis results."""
        from mcp_server_langgraph.agents.execution_selector import ExecutionModeSelector
        from mcp_server_langgraph.agents.task_analyzer import TaskAnalyzer

        analyzer = TaskAnalyzer()
        selector = ExecutionModeSelector()

        # Analyze a complex task that requires tools
        analysis = analyzer.analyze("Search for files, read them, and deploy the distributed system")

        # Use analysis to select mode
        mode = selector.select(
            task_complexity=analysis.complexity,
            risk_level=analysis.risk_level,
            tool_count=analysis.estimated_tool_count,
            requires_exploration=analysis.requires_exploration,
            requires_multi_step=analysis.requires_multi_step,
            requires_batch_processing=analysis.requires_batch_processing,
        )

        # With tools needed, mode should be one of the tool-using modes
        if analysis.estimated_tool_count > 0:
            assert mode.value in ["orchestrator", "react", "tool_calling", "programmatic"]
        else:
            # No tools = pure_llm is acceptable
            assert mode.value == "pure_llm"


@pytest.mark.integration
@pytest.mark.xdist_group(name="capability_flow_hitl")
class TestCapabilityFlowHITL:
    """Tests for HITL capability integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_reversible_action_integrates_with_history(self) -> None:
        """Test ReversibleAction integrates with ActionHistoryStore."""
        from mcp_server_langgraph.hitl.reversible import (
            ActionHistoryStore,
            ActionState,
            ReversibleAction,
        )

        store = ActionHistoryStore()

        action = ReversibleAction(
            action_id="action-1",
            action_type="file_write",
            description="Write config",
            execute_fn=AsyncMock(return_value={"status": "written"}),
            undo_fn=AsyncMock(return_value={"status": "undone"}),
        )

        store.add(action, session_id="session-123")

        # Execute the action
        await action.execute()
        assert action.state == ActionState.EXECUTED

        # Store should show it as undoable
        undoable = store.get_undoable("session-123")
        assert len(undoable) == 1

        # Undo via store
        await store.undo("action-1")
        assert action.state == ActionState.UNDONE

    @pytest.mark.asyncio
    async def test_human_expert_request_response_flow(self) -> None:
        """Test HumanExpertTool request/response flow."""
        from mcp_server_langgraph.hitl.human_expert import (
            HumanExpertRequest,
            HumanExpertResponse,
            HumanExpertTool,
            RequestStatus,
        )

        tool = HumanExpertTool()

        # Create request
        request = HumanExpertRequest(
            question="Which database should we use?",
            context="Building a new microservice",
            options=["PostgreSQL", "MongoDB", "Redis"],
        )

        request_id = await tool.ask(request, session_id="session-123")
        assert tool.get_status(request_id) == RequestStatus.PENDING

        # Submit response
        response = HumanExpertResponse(
            answer="PostgreSQL for relational data",
            answered_by="architect@example.com",
            selected_option=0,
            confidence=0.9,
        )

        await tool.respond(request_id, response)
        assert tool.get_status(request_id) == RequestStatus.ANSWERED

        # Retrieve response
        stored_response = tool.get_response(request_id)
        assert stored_response is not None
        assert stored_response.selected_option == 0
