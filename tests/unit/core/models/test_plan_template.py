"""
Tests for PlanTemplate Model

TDD: These tests define the contract for reusable execution plan templates.
"""

from __future__ import annotations

import gc
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


@pytest.mark.xdist_group(name="plan_template_model")
class TestPlanTemplateModel:
    """Tests for PlanTemplate model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_plan_template_exists(self) -> None:
        """Test that PlanTemplate model exists."""
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate

        assert PlanTemplate is not None

    def test_plan_template_has_required_fields(self) -> None:
        """Test PlanTemplate has all required fields."""
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate

        template = PlanTemplate(
            template_id="tmpl-123",
            name="Code Review Template",
            description="Template for code review tasks",
            orchestrator="standard",
            thinking_budget="medium",
            critique_rounds=1,
            auto_approve=False,
            created_by="user-456",
        )

        assert template.template_id == "tmpl-123"
        assert template.name == "Code Review Template"
        assert template.description == "Template for code review tasks"
        assert template.orchestrator == "standard"
        assert template.thinking_budget == "medium"
        assert template.critique_rounds == 1
        assert template.auto_approve is False
        assert template.created_by == "user-456"

    def test_plan_template_has_optional_embedding(self) -> None:
        """Test PlanTemplate has optional embedding field."""
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate

        template = PlanTemplate(
            template_id="tmpl-123",
            name="Test",
            description="Test desc",
            orchestrator="standard",
            thinking_budget="none",
            critique_rounds=0,
            auto_approve=True,
            created_by="user-123",
            description_embedding=[0.1, 0.2, 0.3],
        )

        assert template.description_embedding == [0.1, 0.2, 0.3]

    def test_plan_template_embedding_defaults_to_none(self) -> None:
        """Test description_embedding defaults to None."""
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate

        template = PlanTemplate(
            template_id="tmpl-123",
            name="Test",
            description="Test desc",
            orchestrator="standard",
            thinking_budget="none",
            critique_rounds=0,
            auto_approve=True,
            created_by="user-123",
        )

        assert template.description_embedding is None

    def test_plan_template_has_timestamps(self) -> None:
        """Test PlanTemplate has created_at timestamp."""
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate

        template = PlanTemplate(
            template_id="tmpl-123",
            name="Test",
            description="Test desc",
            orchestrator="standard",
            thinking_budget="none",
            critique_rounds=0,
            auto_approve=True,
            created_by="user-123",
        )

        assert template.created_at is not None
        assert isinstance(template.created_at, datetime)

    def test_plan_template_has_usage_metrics(self) -> None:
        """Test PlanTemplate has use_count and success_rate."""
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate

        template = PlanTemplate(
            template_id="tmpl-123",
            name="Test",
            description="Test desc",
            orchestrator="standard",
            thinking_budget="none",
            critique_rounds=0,
            auto_approve=True,
            created_by="user-123",
            use_count=10,
            success_rate=0.85,
        )

        assert template.use_count == 10
        assert template.success_rate == 0.85

    def test_plan_template_usage_metrics_default_to_zero(self) -> None:
        """Test use_count and success_rate default to 0."""
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate

        template = PlanTemplate(
            template_id="tmpl-123",
            name="Test",
            description="Test desc",
            orchestrator="standard",
            thinking_budget="none",
            critique_rounds=0,
            auto_approve=True,
            created_by="user-123",
        )

        assert template.use_count == 0
        assert template.success_rate == 0.0

    def test_plan_template_has_tags(self) -> None:
        """Test PlanTemplate has tags list."""
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate

        template = PlanTemplate(
            template_id="tmpl-123",
            name="Test",
            description="Test desc",
            orchestrator="standard",
            thinking_budget="none",
            critique_rounds=0,
            auto_approve=True,
            created_by="user-123",
            tags=["code", "review", "python"],
        )

        assert template.tags == ["code", "review", "python"]

    def test_plan_template_tags_defaults_to_empty(self) -> None:
        """Test tags defaults to empty list."""
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate

        template = PlanTemplate(
            template_id="tmpl-123",
            name="Test",
            description="Test desc",
            orchestrator="standard",
            thinking_budget="none",
            critique_rounds=0,
            auto_approve=True,
            created_by="user-123",
        )

        assert template.tags == []

    def test_plan_template_validates_orchestrator(self) -> None:
        """Test PlanTemplate validates orchestrator values."""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.models.plan_template import PlanTemplate

        with pytest.raises(ValidationError):
            PlanTemplate(
                template_id="tmpl-123",
                name="Test",
                description="Test desc",
                orchestrator="invalid_orchestrator",  # Invalid
                thinking_budget="none",
                critique_rounds=0,
                auto_approve=True,
                created_by="user-123",
            )

    def test_plan_template_validates_thinking_budget(self) -> None:
        """Test PlanTemplate validates thinking_budget values."""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.models.plan_template import PlanTemplate

        with pytest.raises(ValidationError):
            PlanTemplate(
                template_id="tmpl-123",
                name="Test",
                description="Test desc",
                orchestrator="standard",
                thinking_budget="invalid_budget",  # Invalid
                critique_rounds=0,
                auto_approve=True,
                created_by="user-123",
            )

    def test_plan_template_validates_critique_rounds(self) -> None:
        """Test PlanTemplate validates critique_rounds (0-3)."""
        from pydantic import ValidationError

        from mcp_server_langgraph.core.models.plan_template import PlanTemplate

        with pytest.raises(ValidationError):
            PlanTemplate(
                template_id="tmpl-123",
                name="Test",
                description="Test desc",
                orchestrator="standard",
                thinking_budget="none",
                critique_rounds=5,  # Invalid - max is 3
                auto_approve=True,
                created_by="user-123",
            )


@pytest.mark.xdist_group(name="plan_template_methods")
class TestPlanTemplateMethods:
    """Tests for PlanTemplate methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_plan_template_record_use(self) -> None:
        """Test recording template usage updates metrics."""
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate

        template = PlanTemplate(
            template_id="tmpl-123",
            name="Test",
            description="Test desc",
            orchestrator="standard",
            thinking_budget="none",
            critique_rounds=0,
            auto_approve=True,
            created_by="user-123",
            use_count=5,
            success_rate=0.8,  # 4 out of 5 successful
        )

        updated = template.record_use(success=True)

        assert updated.use_count == 6
        # New success rate: 5 successes out of 6 uses
        assert updated.success_rate == pytest.approx(5 / 6, rel=0.01)

    def test_plan_template_record_use_failure(self) -> None:
        """Test recording failed usage updates metrics."""
        from mcp_server_langgraph.core.models.plan_template import PlanTemplate

        template = PlanTemplate(
            template_id="tmpl-123",
            name="Test",
            description="Test desc",
            orchestrator="standard",
            thinking_budget="none",
            critique_rounds=0,
            auto_approve=True,
            created_by="user-123",
            use_count=5,
            success_rate=0.8,  # 4 out of 5 successful
        )

        updated = template.record_use(success=False)

        assert updated.use_count == 6
        # Same 4 successes out of 6 uses now
        assert updated.success_rate == pytest.approx(4 / 6, rel=0.01)
