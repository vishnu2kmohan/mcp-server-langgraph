"""
Risk-Aware Bypass Manager.

Uses existing ExecutionPlan.complexity (simple/complicated/complex)
and ExecutionPlan.risk_level (low/medium/high) for auto-approval decisions.

CRITICAL: SANDBOX_REQUIRED_TOOLS presence ESCALATES risk level, not just adds factors.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from mcp_server_langgraph.api.v1.tools import SANDBOX_REQUIRED_TOOLS
from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan
from mcp_server_langgraph.execution.bypass_prometheus_metrics import (
    record_estimated_cost,
    record_tool_escalation,
)
from mcp_server_langgraph.execution.cost_estimator import estimate_execution_cost


RiskLevel = Literal["low", "medium", "high"]
Complexity = Literal["simple", "complicated", "complex"]

# Risk level ordering for escalation
RISK_ORDER: dict[str, int] = {"low": 0, "medium": 1, "high": 2}
RISK_FROM_ORDER: dict[int, RiskLevel] = {0: "low", 1: "medium", 2: "high"}

# Tool-specific risk escalation (uses ACTUAL tool names from api/v1/tools.py:82)
TOOL_RISK_ESCALATION: dict[str, RiskLevel] = {
    "execute_bash": "high",
    "execute_python": "medium",
    "edit_file": "medium",
    "write_file": "medium",
    "keyboard_type": "medium",  # Computer use
    "capture_screenshot": "low",  # Not screenshot!
}


@dataclass
class BypassDecision:
    """Result of bypass mode decision."""

    auto_approved: bool
    requires_user_approval: bool
    risk_level: RiskLevel  # Effective risk (may be escalated)
    original_risk_level: RiskLevel  # From ExecutionPlan
    complexity: Complexity
    risk_factors: list[str]
    estimated_cost: Decimal  # Estimated execution cost in USD


class BypassManager:
    """Manages risk-aware bypass mode decisions."""

    # Auto-approve matrix: (risk_level, complexity) -> auto_approve
    AUTO_APPROVE_MATRIX: dict[tuple[str, str], bool] = {
        ("low", "simple"): True,
        ("low", "complicated"): True,
        ("low", "complex"): False,
        ("medium", "simple"): True,
        ("medium", "complicated"): False,
        ("medium", "complex"): False,
        ("high", "simple"): False,
        ("high", "complicated"): False,
        ("high", "complex"): False,
    }

    def evaluate_plan(self, plan: ExecutionPlan) -> BypassDecision:
        """
        Evaluate an ExecutionPlan for bypass mode auto-approval.

        Uses existing plan.complexity and plan.risk_level.
        CRITICAL: SANDBOX_REQUIRED_TOOLS presence ESCALATES risk level.

        Args:
            plan: The ExecutionPlan to evaluate.

        Returns:
            BypassDecision with auto_approved, risk_level, and risk_factors.
        """
        risk_factors: list[str] = []
        original_risk: RiskLevel = plan.risk_level
        effective_risk_order = RISK_ORDER[original_risk]

        # Check for sandbox-required tools - ESCALATE risk level
        sandbox_tools = set(plan.tools_needed or []) & SANDBOX_REQUIRED_TOOLS
        if sandbox_tools:
            risk_factors.append(f"Sandbox-required tools: {', '.join(sorted(sandbox_tools))}")

            # Escalate based on most dangerous tool
            for tool in sandbox_tools:
                tool_risk = TOOL_RISK_ESCALATION.get(tool)
                if tool_risk:
                    tool_risk_order = RISK_ORDER[tool_risk]
                    if tool_risk_order > effective_risk_order:
                        # Record Prometheus metric for the escalation
                        from_level = RISK_FROM_ORDER[effective_risk_order]
                        record_tool_escalation(
                            tool=tool,
                            from_level=from_level,
                            to_level=tool_risk,
                        )
                        effective_risk_order = tool_risk_order
                        risk_factors.append(f"Risk escalated to {tool_risk} due to {tool}")

        effective_risk: RiskLevel = RISK_FROM_ORDER[effective_risk_order]

        # Determine auto-approval from matrix using EFFECTIVE risk
        complexity: Complexity = plan.complexity
        auto_approve = self.AUTO_APPROVE_MATRIX.get((effective_risk, complexity), False)

        # Calculate estimated execution cost
        estimated_cost = self._estimate_cost(plan)

        # Record cost as Prometheus metric
        if estimated_cost > Decimal("0"):
            record_estimated_cost(
                cost=estimated_cost,
                complexity=complexity,
                risk_level=effective_risk,
            )

        return BypassDecision(
            auto_approved=auto_approve,
            requires_user_approval=not auto_approve,
            risk_level=effective_risk,
            original_risk_level=original_risk,
            complexity=complexity,
            risk_factors=risk_factors,
            estimated_cost=estimated_cost,
        )

    def _estimate_cost(self, plan: ExecutionPlan) -> Decimal:
        """
        Estimate execution cost for a plan.

        Uses the cost_estimator module with graceful fallback on failure.

        Args:
            plan: The ExecutionPlan to estimate cost for.

        Returns:
            Estimated cost in USD as Decimal. Returns Decimal("0") on failure.
        """
        try:
            return estimate_execution_cost(
                model=plan.executor_model,
                task_type=plan.task_type,
                complexity=plan.complexity,
                thinking_budget=plan.thinking_budget or "none",
            )
        except Exception:
            # Don't fail the evaluation if cost estimation fails
            return Decimal("0")
