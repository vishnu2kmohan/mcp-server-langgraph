"""Shared serialization functions for API response models.

This module provides dict conversion functions used across multiple API modules
to avoid circular imports and reduce coupling.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan
    from mcp_server_langgraph.core.models.plan_template import PlanTemplate


def plan_to_dict(plan: ExecutionPlan) -> dict[str, Any]:
    """Convert ExecutionPlan to response dict with all 27 fields.

    Field breakdown:
    - 25 model fields (plan_id through rejection_reason)
    - +1 computed alias: orchestrator (= suggested_orchestrator)
    - +1 computed property: requires_approval

    Args:
        plan: The ExecutionPlan instance to convert

    Returns:
        Dictionary with all 27 fields for API response
    """
    return {
        # Core identification
        "plan_id": plan.plan_id,
        "session_id": plan.session_id,
        "status": plan.status,
        # Classification
        "complexity": plan.complexity,
        "risk_level": plan.risk_level,
        "task_type": plan.task_type,
        # Model configuration
        "executor_model": plan.executor_model,
        "critic_model": plan.critic_model,
        # Cost tracking
        "estimated_cost": str(plan.estimated_cost),
        "actual_cost": str(plan.actual_cost) if plan.actual_cost is not None else None,
        # Content
        "message": plan.message,
        "tools_needed": plan.tools_needed,
        # Approval configuration
        "force_approval": plan.force_approval,
        "confidence": plan.confidence,
        # Orchestrator
        "suggested_orchestrator": plan.suggested_orchestrator,
        "orchestrator": plan.suggested_orchestrator,  # Alias for frontend compatibility
        # Computed property
        "requires_approval": plan.requires_approval,
        # Thinking configuration
        "thinking_budget": plan.thinking_budget,
        "critique_rounds": plan.critique_rounds,
        # Timestamps
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "expires_at": plan.expires_at.isoformat() if plan.expires_at else None,
        "executed_at": plan.executed_at.isoformat() if plan.executed_at else None,
        # Approval/rejection tracking
        "approved_by": plan.approved_by,
        "approved_at": plan.approved_at.isoformat() if plan.approved_at else None,
        "rejected_by": plan.rejected_by,
        "rejected_at": plan.rejected_at.isoformat() if plan.rejected_at else None,
        "rejection_reason": plan.rejection_reason,
        # v35.0: New fields for audit trail and capability tracking
        "skills_needed": plan.skills_needed,
        "selected_tool_ids": plan.selected_tool_ids,
        "llm_provider": plan.llm_provider,
        "kb_focus": plan.kb_focus,
        # v35.0 Phase 2e: Tool preference fields
        "tool_preference": plan.tool_preference,
        "tool_selection_mode": plan.tool_selection_mode,
    }


def plan_to_admin_dict(plan: ExecutionPlan) -> dict[str, Any]:
    """Convert ExecutionPlan to admin response dict with additional fields (v35.0 Phase 2f).

    Extends plan_to_dict with admin-only fields:
    - user_id: User who created the plan (GDPR)
    - created_by: User/system that created the plan
    - embedding_status: Status of embedding generation
    - embedding_error: Error message if embedding failed

    Args:
        plan: The ExecutionPlan instance to convert

    Returns:
        Dictionary with all base fields + 4 admin fields for API response
    """
    base_dict = plan_to_dict(plan)
    admin_fields = {
        "user_id": plan.user_id,
        "created_by": plan.created_by,
        "embedding_status": plan.embedding_status,
        "embedding_error": plan.embedding_error,
    }
    return {**base_dict, **admin_fields}


def template_to_dict(template: PlanTemplate) -> dict[str, Any]:
    """Convert PlanTemplate to response dict with all 12 fields.

    Args:
        template: The PlanTemplate instance to convert

    Returns:
        Dictionary with all 12 fields for API response
    """
    return {
        "template_id": template.template_id,
        "name": template.name,
        "description": template.description,
        "orchestrator": template.orchestrator,
        "thinking_budget": template.thinking_budget,
        "critique_rounds": template.critique_rounds,
        "auto_approve": template.auto_approve,
        "created_by": template.created_by,
        "created_at": template.created_at.isoformat(),
        "use_count": template.use_count,
        "success_rate": template.success_rate,
        "tags": template.tags,
    }
