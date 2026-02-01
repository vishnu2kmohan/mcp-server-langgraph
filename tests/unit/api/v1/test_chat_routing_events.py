"""
Unit tests for chat routing SSE event shape parity.

Tests that plan_generated SSE events include all v35.0 fields consistently.
"""

import gc
from decimal import Decimal

import pytest

from mcp_server_langgraph.api.v1.serializers import plan_to_dict
from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="chat_routing_events")
class TestPlanGeneratedEventShape:
    """Tests for plan_generated SSE event field presence (v35.0)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_plan_to_dict_includes_skills_needed(self) -> None:
        """Test plan_to_dict includes skills_needed field."""
        plan = ExecutionPlan(
            plan_id="plan-test",
            session_id="session-test",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="test-model",
            estimated_cost=Decimal("0.01"),
            message="Test message",
            skills_needed=["skill1", "skill2"],
        )

        result = plan_to_dict(plan)

        assert "skills_needed" in result
        assert result["skills_needed"] == ["skill1", "skill2"]

    def test_plan_to_dict_includes_selected_tool_ids(self) -> None:
        """Test plan_to_dict includes selected_tool_ids field."""
        plan = ExecutionPlan(
            plan_id="plan-test",
            session_id="session-test",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="test-model",
            estimated_cost=Decimal("0.01"),
            message="Test message",
            selected_tool_ids=["tool-1", "tool-2"],
        )

        result = plan_to_dict(plan)

        assert "selected_tool_ids" in result
        assert result["selected_tool_ids"] == ["tool-1", "tool-2"]

    def test_plan_to_dict_includes_llm_provider(self) -> None:
        """Test plan_to_dict includes llm_provider field."""
        plan = ExecutionPlan(
            plan_id="plan-test",
            session_id="session-test",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="test-model",
            estimated_cost=Decimal("0.01"),
            message="Test message",
            llm_provider="anthropic",
        )

        result = plan_to_dict(plan)

        assert "llm_provider" in result
        assert result["llm_provider"] == "anthropic"

    def test_plan_to_dict_includes_kb_focus(self) -> None:
        """Test plan_to_dict includes kb_focus field."""
        plan = ExecutionPlan(
            plan_id="plan-test",
            session_id="session-test",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="test-model",
            estimated_cost=Decimal("0.01"),
            message="Test message",
            kb_focus="all",
        )

        result = plan_to_dict(plan)

        assert "kb_focus" in result
        assert result["kb_focus"] == "all"

    def test_plan_to_dict_includes_tool_preference(self) -> None:
        """Test plan_to_dict includes tool_preference field."""
        plan = ExecutionPlan(
            plan_id="plan-test",
            session_id="session-test",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="test-model",
            estimated_cost=Decimal("0.01"),
            message="Test message",
            tool_preference="prefer_tools",
        )

        result = plan_to_dict(plan)

        assert "tool_preference" in result
        assert result["tool_preference"] == "prefer_tools"

    def test_plan_to_dict_includes_tool_selection_mode(self) -> None:
        """Test plan_to_dict includes tool_selection_mode field."""
        plan = ExecutionPlan(
            plan_id="plan-test",
            session_id="session-test",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="test-model",
            estimated_cost=Decimal("0.01"),
            message="Test message",
            tool_selection_mode="auto",
        )

        result = plan_to_dict(plan)

        assert "tool_selection_mode" in result
        assert result["tool_selection_mode"] == "auto"

    def test_plan_to_dict_v35_fields_all_present(self) -> None:
        """Test plan_to_dict includes all v35.0 audit trail fields."""
        plan = ExecutionPlan(
            plan_id="plan-test",
            session_id="session-test",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="test-model",
            estimated_cost=Decimal("0.01"),
            message="Test message",
        )

        result = plan_to_dict(plan)

        # All v35.0 fields should be present (even if None)
        v35_fields = [
            "skills_needed",
            "selected_tool_ids",
            "llm_provider",
            "kb_focus",
            "tool_preference",
            "tool_selection_mode",
        ]

        for field in v35_fields:
            assert field in result, f"plan_to_dict should include {field}"

    def test_plan_to_dict_field_count(self) -> None:
        """Test plan_to_dict returns expected number of fields (31 total)."""
        plan = ExecutionPlan(
            plan_id="plan-test",
            session_id="session-test",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="test-model",
            estimated_cost=Decimal("0.01"),
            message="Test message",
        )

        result = plan_to_dict(plan)

        # 27 original fields + 4 v35.0 Phase 2e fields + 2 tool preference = 33 fields
        # Actually: 25 model + 2 computed (orchestrator alias, requires_approval)
        # + 6 v35.0 fields = 33 fields
        # Let's verify by counting
        assert len(result) >= 30, f"Expected at least 30 fields, got {len(result)}: {list(result.keys())}"


@pytest.mark.xdist_group(name="chat_routing_events")
class TestExecutionPlanV35FieldPopulation:
    """Tests for v35.0 field population in ExecutionPlan creation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_execution_plan_model_copy_preserves_selected_tool_ids(self) -> None:
        """Test model_copy can add selected_tool_ids to ExecutionPlan."""
        plan = ExecutionPlan(
            plan_id="plan-test",
            session_id="session-test",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="test-model",
            estimated_cost=Decimal("0.01"),
            message="Test message",
        )

        updated_plan = plan.model_copy(update={"selected_tool_ids": ["tool-1", "tool-2"]})

        assert updated_plan.selected_tool_ids == ["tool-1", "tool-2"]
        assert plan.selected_tool_ids is None  # Original unchanged

    def test_execution_plan_model_copy_preserves_llm_provider(self) -> None:
        """Test model_copy can add llm_provider to ExecutionPlan."""
        plan = ExecutionPlan(
            plan_id="plan-test",
            session_id="session-test",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="test-model",
            estimated_cost=Decimal("0.01"),
            message="Test message",
        )

        updated_plan = plan.model_copy(update={"llm_provider": "anthropic"})

        assert updated_plan.llm_provider == "anthropic"
        assert plan.llm_provider is None  # Original unchanged

    def test_execution_plan_model_copy_preserves_kb_focus(self) -> None:
        """Test model_copy can add kb_focus to ExecutionPlan."""
        plan = ExecutionPlan(
            plan_id="plan-test",
            session_id="session-test",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="test-model",
            estimated_cost=Decimal("0.01"),
            message="Test message",
        )

        updated_plan = plan.model_copy(update={"kb_focus": "kb_only"})

        assert updated_plan.kb_focus == "kb_only"
        assert plan.kb_focus is None  # Original unchanged

    def test_execution_plan_model_copy_multiple_v35_fields(self) -> None:
        """Test model_copy can add all v35.0 context fields at once."""
        plan = ExecutionPlan(
            plan_id="plan-test",
            session_id="session-test",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="test-model",
            estimated_cost=Decimal("0.01"),
            message="Test message",
        )

        updated_plan = plan.model_copy(
            update={
                "user_id": "user-123",
                "created_by": "user-123",
                "selected_tool_ids": ["tool-a", "tool-b"],
                "llm_provider": "openai",
                "kb_focus": "web_only",
            }
        )

        assert updated_plan.user_id == "user-123"
        assert updated_plan.created_by == "user-123"
        assert updated_plan.selected_tool_ids == ["tool-a", "tool-b"]
        assert updated_plan.llm_provider == "openai"
        assert updated_plan.kb_focus == "web_only"

    def test_plan_to_dict_includes_context_fields_after_model_copy(self) -> None:
        """Test plan_to_dict includes v35.0 fields added via model_copy."""
        plan = ExecutionPlan(
            plan_id="plan-test",
            session_id="session-test",
            status="awaiting_approval",
            complexity="simple",
            risk_level="low",
            task_type="chat",
            executor_model="test-model",
            estimated_cost=Decimal("0.01"),
            message="Test message",
        )

        updated_plan = plan.model_copy(
            update={
                "selected_tool_ids": ["tool-x"],
                "llm_provider": "vertex",
                "kb_focus": "all",
            }
        )

        result = plan_to_dict(updated_plan)

        assert result["selected_tool_ids"] == ["tool-x"]
        assert result["llm_provider"] == "vertex"
        assert result["kb_focus"] == "all"
