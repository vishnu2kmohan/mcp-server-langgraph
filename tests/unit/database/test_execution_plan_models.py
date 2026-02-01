"""
Unit tests for ExecutionPlanModel SQLAlchemy model.

Tests v35.0 field additions to the model.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_execution_plan_model")
class TestExecutionPlanModelV35Fields:
    """Test ExecutionPlanModel v35.0 field additions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_execution_plan_model_has_skills_needed(self) -> None:
        """Test ExecutionPlanModel has skills_needed column."""
        from mcp_server_langgraph.database.execution_plan_models import (
            ExecutionPlanModel,
        )

        column_names = [col.name for col in ExecutionPlanModel.__table__.columns]
        assert "skills_needed" in column_names, "ExecutionPlanModel should have skills_needed column"

    def test_execution_plan_model_has_selected_tool_ids(self) -> None:
        """Test ExecutionPlanModel has selected_tool_ids column."""
        from mcp_server_langgraph.database.execution_plan_models import (
            ExecutionPlanModel,
        )

        column_names = [col.name for col in ExecutionPlanModel.__table__.columns]
        assert "selected_tool_ids" in column_names, "ExecutionPlanModel should have selected_tool_ids column"

    def test_execution_plan_model_has_llm_provider(self) -> None:
        """Test ExecutionPlanModel has llm_provider column."""
        from mcp_server_langgraph.database.execution_plan_models import (
            ExecutionPlanModel,
        )

        column_names = [col.name for col in ExecutionPlanModel.__table__.columns]
        assert "llm_provider" in column_names, "ExecutionPlanModel should have llm_provider column"

    def test_execution_plan_model_has_kb_focus(self) -> None:
        """Test ExecutionPlanModel has kb_focus column."""
        from mcp_server_langgraph.database.execution_plan_models import (
            ExecutionPlanModel,
        )

        column_names = [col.name for col in ExecutionPlanModel.__table__.columns]
        assert "kb_focus" in column_names, "ExecutionPlanModel should have kb_focus column"

    def test_execution_plan_model_has_tool_preference(self) -> None:
        """Test ExecutionPlanModel has tool_preference column."""
        from mcp_server_langgraph.database.execution_plan_models import (
            ExecutionPlanModel,
        )

        column_names = [col.name for col in ExecutionPlanModel.__table__.columns]
        assert "tool_preference" in column_names, "ExecutionPlanModel should have tool_preference column"

    def test_execution_plan_model_has_tool_selection_mode(self) -> None:
        """Test ExecutionPlanModel has tool_selection_mode column."""
        from mcp_server_langgraph.database.execution_plan_models import (
            ExecutionPlanModel,
        )

        column_names = [col.name for col in ExecutionPlanModel.__table__.columns]
        assert "tool_selection_mode" in column_names, "ExecutionPlanModel should have tool_selection_mode column"
