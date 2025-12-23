"""
Token & Cost Budget Tracking.

Phase 5 of the Multi-Agent Orchestrator Enhancement Plan.

Provides:
- CostTracker: Tracks token usage and costs across sessions
- Per-orchestration and session-level budget limits
- Alert generation at configurable thresholds
- Integration with ModelRegistry for accurate pricing

Usage:
    from mcp_server_langgraph.agents.cost_tracker import CostTracker

    tracker = CostTracker()
    record = tracker.track_usage(
        model="claude-opus-4-5-20251101",
        input_tokens=1000,
        output_tokens=500,
        session_id="session-123",
    )
    status = tracker.check_budget("session-123")
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from mcp_server_langgraph.agents.cost_models import (
    BudgetStatus,
    CostAlert,
    CostRecord,
)
from mcp_server_langgraph.agents.metrics import record_cost_usage
from mcp_server_langgraph.agents.model_registry import (
    ModelRegistry,
    get_default_registry,
)
from mcp_server_langgraph.core.feature_flags import feature_flags

if TYPE_CHECKING:
    pass


class CostTracker:
    """Tracks token usage and costs for orchestrations.

    Features:
    - Per-orchestration cost limits
    - Session-level cost accumulation and limits
    - Configurable alert thresholds (50%, 75%, 90%)
    - Integration with ModelRegistry for accurate pricing
    - Prometheus metrics integration

    Usage:
        tracker = CostTracker()

        # Track usage
        record = tracker.track_usage(
            model="claude-opus-4-5-20251101",
            input_tokens=1000,
            output_tokens=500,
            session_id="session-123",
        )

        # Check budget status
        status = tracker.check_budget("session-123")
        if status.status == BudgetStatus.EXCEEDED:
            raise BudgetExceededError(...)
    """

    def __init__(
        self,
        per_orchestration_limit: float | None = None,
        session_limit: float | None = None,
        alert_thresholds: list[float] | None = None,
        model_registry: ModelRegistry | None = None,
    ) -> None:
        """Initialize CostTracker with configurable limits.

        Args:
            per_orchestration_limit: Max cost per orchestration in dollars.
                Defaults to feature_flags.orchestration_cost_limit.
            session_limit: Max cost per session in dollars.
                Defaults to feature_flags.session_cost_limit.
            alert_thresholds: List of percentage thresholds for alerts.
                Defaults to feature_flags.cost_alert_thresholds.
            model_registry: ModelRegistry for pricing lookup.
                Defaults to the global registry.
        """
        self.per_orchestration_limit = Decimal(str(per_orchestration_limit or feature_flags.orchestration_cost_limit))
        self.session_limit = Decimal(str(session_limit or feature_flags.session_cost_limit))
        self.alert_thresholds = sorted(alert_thresholds or feature_flags.cost_alert_thresholds)
        self.model_registry = model_registry or get_default_registry()

        # Internal storage for session costs
        self._session_costs: dict[str, Decimal] = {}

    def track_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        task_id: str | None = None,
        session_id: str | None = None,
    ) -> CostRecord:
        """Track token usage and calculate cost.

        Uses ModelRegistry pricing for accurate cost calculation.
        Accumulates costs for session-level tracking.

        Args:
            model: Model identifier (e.g., "claude-opus-4-5-20251101")
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            task_id: Optional task identifier for correlation
            session_id: Optional session identifier for accumulation

        Returns:
            CostRecord with calculated costs
        """
        # Get pricing from registry (always returns ModelCapabilities with defaults)
        caps = self.model_registry.get(model)

        # Calculate costs using registry pricing (per 1M tokens)
        input_cost = Decimal(str(caps.input_cost_per_1m)) * Decimal(str(input_tokens)) / Decimal("1000000")
        output_cost = Decimal(str(caps.output_cost_per_1m)) * Decimal(str(output_tokens)) / Decimal("1000000")

        total_cost = input_cost + output_cost

        # Create cost record
        record = CostRecord(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            task_id=task_id,
            session_id=session_id,
        )

        # Accumulate session cost
        if session_id:
            if session_id not in self._session_costs:
                self._session_costs[session_id] = Decimal("0")
            self._session_costs[session_id] += total_cost

        # Record Prometheus metrics
        if feature_flags.enable_cost_tracking:
            record_cost_usage(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_cost=float(total_cost),
                session_id=session_id,
            )

        return record

    def get_session_cost(self, session_id: str) -> Decimal:
        """Get accumulated cost for a session.

        Args:
            session_id: Session identifier

        Returns:
            Accumulated cost in dollars, or 0 if session unknown
        """
        return self._session_costs.get(session_id, Decimal("0"))

    def check_budget(self, session_id: str) -> CostAlert:
        """Check budget status for a session.

        Compares current session cost against configured thresholds
        and returns appropriate status.

        Args:
            session_id: Session identifier

        Returns:
            CostAlert with current status and details
        """
        current_cost = self.get_session_cost(session_id)
        limit = self.session_limit

        # Calculate percentage used
        pct_used = float(current_cost / limit) if limit > 0 else 0.0

        # Determine status based on thresholds
        if pct_used >= 1.0:
            status = BudgetStatus.EXCEEDED
            threshold = 1.0
        elif pct_used >= self.alert_thresholds[-1]:  # Highest threshold (e.g., 0.9)
            status = BudgetStatus.CRITICAL
            threshold = self.alert_thresholds[-1]
        elif pct_used >= self.alert_thresholds[0]:  # First threshold (e.g., 0.5)
            status = BudgetStatus.WARNING
            threshold = self.alert_thresholds[0]
        else:
            status = BudgetStatus.OK
            threshold = 0.0

        return CostAlert(
            status=status,
            threshold_percentage=threshold,
            current_cost=current_cost,
            limit=limit,
            session_id=session_id,
        )

    def check_orchestration_budget(self, cost: Decimal) -> CostAlert:
        """Check if a single orchestration exceeds its budget.

        Args:
            cost: Cost of the orchestration in dollars

        Returns:
            CostAlert with OK or EXCEEDED status
        """
        if cost > self.per_orchestration_limit:
            return CostAlert(
                status=BudgetStatus.EXCEEDED,
                threshold_percentage=1.0,
                current_cost=cost,
                limit=self.per_orchestration_limit,
                session_id="orchestration",
                message=f"Orchestration cost ${cost:.4f} exceeds limit ${self.per_orchestration_limit:.2f}",
            )

        return CostAlert(
            status=BudgetStatus.OK,
            threshold_percentage=0.0,
            current_cost=cost,
            limit=self.per_orchestration_limit,
            session_id="orchestration",
        )

    def reset_session(self, session_id: str) -> None:
        """Reset accumulated cost for a session.

        Args:
            session_id: Session identifier to reset
        """
        self._session_costs[session_id] = Decimal("0")

    def reset_all(self) -> None:
        """Reset all session costs."""
        self._session_costs.clear()
