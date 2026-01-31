"""
Plan Template Model

Represents reusable execution plan templates.
Users can save successful plans as templates and reuse them for similar tasks.

Usage:
    from mcp_server_langgraph.core.models.plan_template import PlanTemplate

    template = PlanTemplate(
        template_id="tmpl-123",
        name="Code Review Template",
        description="Template for code review tasks",
        orchestrator="standard",
        thinking_budget="medium",
        critique_rounds=1,
        auto_approve=False,
        created_by="user@example.com",
    )
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Literal

from pydantic import BaseModel, Field


def _now() -> datetime:
    """Get current UTC time."""
    return datetime.now(UTC)


class PlanTemplate(BaseModel):
    """Reusable execution plan template.

    Allows users to save and reuse successful plan configurations.

    Attributes:
        template_id: Unique template identifier
        name: Human-readable template name
        description: Description of when to use this template
        description_embedding: Vector embedding for semantic matching
        orchestrator: Orchestrator pattern to use
        thinking_budget: Extended thinking level
        critique_rounds: Number of critique iterations
        auto_approve: Whether to auto-approve low-risk uses
        created_by: User who created the template
        created_at: When template was created
        use_count: Number of times template has been used
        success_rate: Percentage of successful uses (0-1)
        tags: Labels for filtering and organization
    """

    template_id: str
    name: str = Field(min_length=1, max_length=255)
    # Note: DB column is nullable; allow None to prevent validation errors on NULL rows
    description: str | None = Field(default=None, max_length=2000)

    # Template configuration
    orchestrator: Literal["standard", "swarm", "studio", "ux", "alert"]
    thinking_budget: Literal["none", "light", "medium", "deep"]
    critique_rounds: int = Field(ge=0, le=3)
    auto_approve: bool = False

    # Ownership
    created_by: str
    created_at: datetime = Field(default_factory=_now)

    # Optional embedding for semantic search
    description_embedding: list[float] | None = None

    # Usage metrics
    use_count: int = Field(default=0, ge=0)
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)

    # Organization
    tags: list[str] = Field(default_factory=list)

    # Timestamps
    updated_at: datetime | None = None
    last_used_at: datetime | None = None

    # Embedding status (Phase 7.25: Self-healing embedding service)
    embedding_status: Literal["pending", "processing", "completed", "failed"] = "pending"
    embedding_error: str | None = None
    embedding_failed_at: datetime | None = None

    def record_use(self, success: bool) -> PlanTemplate:
        """Record a template usage and update metrics.

        Args:
            success: Whether the plan execution was successful

        Returns:
            New PlanTemplate with updated metrics
        """
        new_use_count = self.use_count + 1

        # Calculate new success rate
        # Previous successes = use_count * success_rate
        previous_successes = self.use_count * self.success_rate
        new_successes = previous_successes + (1 if success else 0)
        new_success_rate = new_successes / new_use_count

        return self.model_copy(
            update={
                "use_count": new_use_count,
                "success_rate": new_success_rate,
            }
        )
