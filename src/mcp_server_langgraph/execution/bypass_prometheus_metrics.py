"""
Prometheus metrics for bypass mode.

Metrics track bypass mode usage patterns for Grafana dashboards:
- Activation/approval/rejection counts
- Tool escalation tracking
- Permission check outcomes
- Cost estimation recording
- Mode switching behavior
- Active sessions by mode

Uses lazy-loading pattern to handle missing prometheus_client gracefully.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Literal, Optional

if TYPE_CHECKING:
    from prometheus_client import Counter, Gauge

# Lazy-loaded metrics - initialized on first use
_metrics_available: bool | None = None

# Metric instances (initialized lazily)
_bypass_activations_total: Optional["Counter"] = None
_bypass_approvals_total: Optional["Counter"] = None
_bypass_rejections_total: Optional["Counter"] = None
_bypass_tool_escalations_total: Optional["Counter"] = None
_bypass_permission_checks_total: Optional["Counter"] = None
_bypass_plan_estimated_cost: Optional["Gauge"] = None
_bypass_mode_changes_total: Optional["Counter"] = None
_bypass_active_sessions: Optional["Gauge"] = None


def _init_metrics() -> bool:
    """
    Initialize Prometheus metrics lazily.

    Returns True if metrics are available, False otherwise.
    """
    global _metrics_available
    global _bypass_activations_total
    global _bypass_approvals_total
    global _bypass_rejections_total
    global _bypass_tool_escalations_total
    global _bypass_permission_checks_total
    global _bypass_plan_estimated_cost
    global _bypass_mode_changes_total
    global _bypass_active_sessions

    if _metrics_available is not None:
        return _metrics_available

    try:
        from prometheus_client import Counter, Gauge

        _bypass_activations_total = Counter(
            "bypass_activations_total",
            "Total bypass mode activations",
            ["user"],
        )

        _bypass_approvals_total = Counter(
            "bypass_approvals_total",
            "Total bypass mode plan approvals",
            ["approval_type", "risk_level", "complexity"],
        )

        _bypass_rejections_total = Counter(
            "bypass_rejections_total",
            "Total bypass mode plan rejections",
            ["risk_level", "complexity"],
        )

        _bypass_tool_escalations_total = Counter(
            "bypass_tool_escalations_total",
            "Total tool risk escalations in bypass mode",
            ["tool", "from_level", "to_level"],
        )

        _bypass_permission_checks_total = Counter(
            "bypass_permission_checks_total",
            "Total bypass permission check outcomes",
            ["result"],
        )

        _bypass_plan_estimated_cost = Gauge(
            "bypass_plan_estimated_cost",
            "Estimated cost of bypass mode plans",
            ["complexity", "risk_level"],
        )

        _bypass_mode_changes_total = Counter(
            "bypass_mode_changes_total",
            "Total execution mode changes",
            ["from_mode", "to_mode", "trigger"],
        )

        _bypass_active_sessions = Gauge(
            "bypass_active_sessions",
            "Number of active sessions by execution mode",
            ["mode"],
        )

        _metrics_available = True
    except ImportError:
        _metrics_available = False

    return _metrics_available


def record_bypass_activation(user: str) -> None:
    """
    Record a bypass mode activation.

    Args:
        user: Username or user ID who activated bypass mode
    """
    if _init_metrics() and _bypass_activations_total is not None:
        _bypass_activations_total.labels(user=user).inc()


def record_bypass_approval(
    approval_type: Literal["auto", "user"],
    risk_level: Literal["low", "medium", "high"],
    complexity: Literal["simple", "complicated", "complex"],
) -> None:
    """
    Record a bypass mode plan approval.

    Args:
        approval_type: "auto" for auto-approved, "user" for user-approved
        risk_level: Risk level of the plan
        complexity: Complexity level of the plan
    """
    if _init_metrics() and _bypass_approvals_total is not None:
        _bypass_approvals_total.labels(
            approval_type=approval_type,
            risk_level=risk_level,
            complexity=complexity,
        ).inc()


def record_bypass_rejection(
    risk_level: Literal["low", "medium", "high"],
    complexity: Literal["simple", "complicated", "complex"],
) -> None:
    """
    Record a bypass mode plan rejection.

    Args:
        risk_level: Risk level of the rejected plan
        complexity: Complexity level of the rejected plan
    """
    if _init_metrics() and _bypass_rejections_total is not None:
        _bypass_rejections_total.labels(
            risk_level=risk_level,
            complexity=complexity,
        ).inc()


def record_tool_escalation(
    tool: str,
    from_level: Literal["low", "medium", "high"],
    to_level: Literal["low", "medium", "high"],
) -> None:
    """
    Record a tool-based risk escalation.

    Args:
        tool: Tool name that caused escalation
        from_level: Original risk level
        to_level: Escalated risk level
    """
    if _init_metrics() and _bypass_tool_escalations_total is not None:
        _bypass_tool_escalations_total.labels(
            tool=tool,
            from_level=from_level,
            to_level=to_level,
        ).inc()


def record_permission_check(result: Literal["granted", "denied"]) -> None:
    """
    Record a bypass permission check outcome.

    Args:
        result: "granted" or "denied"
    """
    if _init_metrics() and _bypass_permission_checks_total is not None:
        _bypass_permission_checks_total.labels(result=result).inc()


def record_estimated_cost(
    cost: Decimal,
    complexity: Literal["simple", "complicated", "complex"],
    risk_level: Literal["low", "medium", "high"],
) -> None:
    """
    Record estimated cost for a bypass mode plan.

    Args:
        cost: Estimated cost as Decimal
        complexity: Complexity level
        risk_level: Risk level
    """
    if _init_metrics() and _bypass_plan_estimated_cost is not None:
        _bypass_plan_estimated_cost.labels(
            complexity=complexity,
            risk_level=risk_level,
        ).set(float(cost))


def record_mode_change(
    from_mode: str,
    to_mode: str,
    trigger: Literal["keyboard", "click", "api"],
) -> None:
    """
    Record an execution mode change.

    Args:
        from_mode: Previous execution mode
        to_mode: New execution mode
        trigger: How the change was triggered
    """
    if _init_metrics() and _bypass_mode_changes_total is not None:
        _bypass_mode_changes_total.labels(
            from_mode=from_mode,
            to_mode=to_mode,
            trigger=trigger,
        ).inc()


def set_active_sessions_by_mode(mode: str, count: int) -> None:
    """
    Set the number of active sessions for a mode.

    Args:
        mode: Execution mode (default, plan, auto_accept, bypass)
        count: Number of active sessions
    """
    if _init_metrics() and _bypass_active_sessions is not None:
        _bypass_active_sessions.labels(mode=mode).set(count)


def increment_active_session(mode: str) -> None:
    """
    Increment active session count for a mode.

    Args:
        mode: Execution mode
    """
    if _init_metrics() and _bypass_active_sessions is not None:
        _bypass_active_sessions.labels(mode=mode).inc()


def decrement_active_session(mode: str) -> None:
    """
    Decrement active session count for a mode.

    Args:
        mode: Execution mode
    """
    if _init_metrics() and _bypass_active_sessions is not None:
        _bypass_active_sessions.labels(mode=mode).dec()
