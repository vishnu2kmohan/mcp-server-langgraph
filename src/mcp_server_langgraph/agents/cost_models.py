"""
Cost tracking data models.

Phase 5 of the Multi-Agent Orchestrator Enhancement Plan.

Provides:
- CostRecord: Immutable record of cost for a single LLM call
- BudgetStatus: Enum for budget health states
- CostAlert: Alert generated when budget thresholds are crossed
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class BudgetStatus(Enum):
    """Budget health status levels.

    Used by CostTracker to indicate current budget state.
    """

    OK = "ok"  # Under all alert thresholds
    WARNING = "warning"  # Crossed first threshold (typically 50%)
    CRITICAL = "critical"  # Crossed final threshold (typically 90%)
    EXCEEDED = "exceeded"  # Over 100% of budget limit


@dataclass(frozen=True)
class CostRecord:
    """Immutable record of cost for a single LLM call.

    Captures token usage and associated costs using model pricing
    from the ModelRegistry.

    Attributes:
        model: The model identifier used for the call
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of output/completion tokens
        input_cost: Cost for input tokens in dollars
        output_cost: Cost for output tokens in dollars
        total_cost: Total cost (input + output) in dollars
        task_id: Optional task identifier for correlation
        session_id: Optional session identifier for aggregation
    """

    model: str
    input_tokens: int
    output_tokens: int
    input_cost: Decimal
    output_cost: Decimal
    total_cost: Decimal
    task_id: str | None = None
    session_id: str | None = None


@dataclass
class CostAlert:
    """Alert generated when a budget threshold is crossed.

    Created by CostTracker when session or orchestration costs
    exceed configured alert thresholds.

    Attributes:
        status: Current budget status (WARNING, CRITICAL, EXCEEDED)
        threshold_percentage: The threshold that was crossed (0.0-1.0)
        current_cost: Current accumulated cost in dollars
        limit: The configured budget limit in dollars
        session_id: Session this alert applies to
        message: Optional human-readable alert message
    """

    status: BudgetStatus
    threshold_percentage: float
    current_cost: Decimal
    limit: Decimal
    session_id: str
    message: str = field(default="")

    def __post_init__(self) -> None:
        """Generate default message if not provided."""
        if not self.message:
            pct = self.threshold_percentage * 100
            self.message = (
                f"Session {self.session_id} has reached {pct:.0f}% of budget (${self.current_cost:.4f} / ${self.limit:.2f})"
            )
