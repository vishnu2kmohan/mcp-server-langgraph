"""
Budget Monitor and Alert System

Monitors LLM spending against budgets and triggers alerts when thresholds are exceeded.

Features:
- Budget tracking (daily, weekly, monthly, quarterly)
- Configurable alert thresholds (e.g., 75%, 90%)
- Multi-channel alerts (logging, webhooks, email)
- Budget forecasting
- Automatic budget rollover

Example:
    >>> from mcp_server_langgraph.monitoring.budget_monitor import BudgetMonitor
    >>> monitor = BudgetMonitor()
    >>> await monitor.create_budget(
    ...     name="Development Team Monthly",
    ...     limit_usd=1000.00,
    ...     period="monthly"
    ... )
    >>> await monitor.check_budget("budget_001")
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ==============================================================================
# Configuration
# ==============================================================================

logger = logging.getLogger(__name__)


class BudgetPeriod(str, Enum):
    """Budget period types."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class AlertLevel(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ==============================================================================
# Data Models
# ==============================================================================


class Budget(BaseModel):
    """Budget configuration."""

    id: str = Field(description="Unique budget identifier")
    name: str = Field(description="Budget name")
    limit_usd: Decimal = Field(description="Budget limit in USD", gt=0)
    period: BudgetPeriod = Field(description="Budget period")
    start_date: datetime = Field(description="Budget start date")
    end_date: Optional[datetime] = Field(default=None, description="Budget end date (optional)")
    alert_thresholds: List[Decimal] = Field(
        default=[Decimal("0.75"), Decimal("0.90")],
        description="Alert thresholds as percentages (e.g., 0.75 = 75%)",
    )
    enabled: bool = Field(default=True, description="Whether budget monitoring is enabled")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
        }


class BudgetStatus(BaseModel):
    """Current budget status."""

    budget_id: str
    budget_name: str
    limit_usd: Decimal
    spent_usd: Decimal
    remaining_usd: Decimal
    utilization: Decimal  # Percentage (0-1)
    period_start: datetime
    period_end: datetime
    is_exceeded: bool
    days_remaining: int
    projected_end_of_period_spend: Optional[Decimal] = None

    class Config:
        json_encoders = {Decimal: str, datetime: lambda v: v.isoformat()}


class BudgetAlert(BaseModel):
    """Budget alert notification."""

    alert_id: str
    budget_id: str
    budget_name: str
    level: AlertLevel
    utilization: Decimal
    threshold: Decimal
    message: str
    timestamp: datetime
    acknowledged: bool = False

    class Config:
        json_encoders = {Decimal: str, datetime: lambda v: v.isoformat()}


# ==============================================================================
# Budget Monitor
# ==============================================================================


class BudgetMonitor:
    """
    Monitor LLM spending against budgets and trigger alerts.

    Features:
    - Budget tracking by period
    - Configurable alert thresholds
    - Multi-level alerts (info, warning, critical)
    - Budget forecasting
    """

    def __init__(self) -> None:
        """Initialize budget monitor."""
        self._budgets: Dict[str, Budget] = {}
        self._alerts: List[BudgetAlert] = []
        self._alerted_thresholds: Dict[str, set[Decimal]] = {}  # Track which thresholds have been alerted
        self._lock = asyncio.Lock()

    async def create_budget(
        self,
        id: str,
        name: str,
        limit_usd: Decimal,
        period: BudgetPeriod,
        start_date: Optional[datetime] = None,
        alert_thresholds: Optional[List[Decimal]] = None,
    ) -> Budget:
        """
        Create a new budget.

        Args:
            id: Budget identifier
            name: Budget name
            limit_usd: Budget limit in USD
            period: Budget period
            start_date: Start date (defaults to now)
            alert_thresholds: Alert thresholds (defaults to [0.75, 0.90])

        Returns:
            Created Budget

        Example:
            >>> budget = await monitor.create_budget(
            ...     id="dev_team_monthly",
            ...     name="Development Team - Monthly",
            ...     limit_usd=Decimal("1000.00"),
            ...     period=BudgetPeriod.MONTHLY
            ... )
        """
        if start_date is None:
            start_date = datetime.now(timezone.utc)

        budget = Budget(
            id=id,
            name=name,
            limit_usd=limit_usd,
            period=period,
            start_date=start_date,
            alert_thresholds=alert_thresholds or [Decimal("0.75"), Decimal("0.90")],
        )

        async with self._lock:
            self._budgets[id] = budget
            self._alerted_thresholds[id] = set()

        logger.info(f"Created budget: {name} (${limit_usd} {period})")
        return budget

    async def get_budget(self, budget_id: str) -> Optional[Budget]:
        """Get budget by ID."""
        async with self._lock:
            return self._budgets.get(budget_id)

    async def get_period_spend(self, budget_id: str) -> Decimal:
        """
        Get total spending for current budget period.

        This is a stub that should be connected to CostMetricsCollector.

        Args:
            budget_id: Budget identifier

        Returns:
            Total spend in USD for current period
        """
        # TODO: Connect to CostMetricsCollector to get actual spend
        # For now, return a mock value for testing
        return Decimal("0.00")

    async def get_budget_status(self, budget_id: str) -> Optional[BudgetStatus]:
        """
        Get current budget status.

        Args:
            budget_id: Budget identifier

        Returns:
            BudgetStatus with current utilization and projections
        """
        budget = await self.get_budget(budget_id)
        if not budget:
            return None

        spent = await self.get_period_spend(budget_id)
        remaining = budget.limit_usd - spent
        utilization = spent / budget.limit_usd if budget.limit_usd > 0 else Decimal("0")

        # Calculate period dates
        period_start = budget.start_date
        period_end = self._calculate_period_end(period_start, budget.period)

        # Calculate days remaining
        now = datetime.now(timezone.utc)
        days_remaining = (period_end - now).days

        # Project end-of-period spend
        days_elapsed = (now - period_start).days
        if days_elapsed > 0:
            daily_burn_rate = spent / Decimal(days_elapsed)
            total_period_days = (period_end - period_start).days
            projected_spend = daily_burn_rate * Decimal(total_period_days)
        else:
            projected_spend = None

        return BudgetStatus(
            budget_id=budget.id,
            budget_name=budget.name,
            limit_usd=budget.limit_usd,
            spent_usd=spent,
            remaining_usd=remaining,
            utilization=utilization,
            period_start=period_start,
            period_end=period_end,
            is_exceeded=spent > budget.limit_usd,
            days_remaining=days_remaining,
            projected_end_of_period_spend=projected_spend,
        )

    async def check_budget(self, budget_id: str) -> Optional[BudgetAlert]:
        """
        Check budget and trigger alerts if thresholds exceeded.

        Args:
            budget_id: Budget identifier

        Returns:
            BudgetAlert if threshold exceeded, None otherwise

        Example:
            >>> alert = await monitor.check_budget("dev_team_monthly")
            >>> if alert:
            ...     print(f"Alert: {alert.message}")
        """
        budget = await self.get_budget(budget_id)
        if not budget or not budget.enabled:
            return None

        spent = await self.get_period_spend(budget_id)
        utilization = spent / budget.limit_usd if budget.limit_usd > 0 else Decimal("0")

        # Check each threshold
        for threshold in sorted(budget.alert_thresholds, reverse=True):
            if utilization >= threshold:
                # Check if we've already alerted for this threshold
                async with self._lock:
                    if threshold not in self._alerted_thresholds[budget_id]:
                        # Determine alert level
                        if utilization >= Decimal("0.95"):
                            level = AlertLevel.CRITICAL
                        elif utilization >= Decimal("0.85"):
                            level = AlertLevel.WARNING
                        else:
                            level = AlertLevel.INFO

                        # Create alert
                        alert = await self._create_alert(
                            budget=budget,
                            level=level,
                            utilization=utilization,
                            threshold=threshold,
                        )

                        # Mark threshold as alerted
                        self._alerted_thresholds[budget_id].add(threshold)

                        # Send alert
                        await self.send_alert(
                            level=level.value,
                            message=alert.message,
                            budget_id=budget_id,
                            utilization=float(utilization),
                        )

                        return alert

        return None

    async def _create_alert(
        self,
        budget: Budget,
        level: AlertLevel,
        utilization: Decimal,
        threshold: Decimal,
    ) -> BudgetAlert:
        """Create a budget alert."""
        alert_id = f"alert_{budget.id}_{int(datetime.now(timezone.utc).timestamp())}"

        message = (
            f"Budget '{budget.name}' at {utilization * 100:.1f}% "
            f"(threshold: {threshold * 100:.0f}%, limit: ${budget.limit_usd})"
        )

        alert = BudgetAlert(
            alert_id=alert_id,
            budget_id=budget.id,
            budget_name=budget.name,
            level=level,
            utilization=utilization,
            threshold=threshold,
            message=message,
            timestamp=datetime.now(timezone.utc),
        )

        async with self._lock:
            self._alerts.append(alert)

        return alert

    async def send_alert(
        self,
        level: str,
        message: str,
        budget_id: str,
        utilization: float,
    ) -> None:
        """
        Send budget alert notification.

        This is a stub that can be extended to support multiple channels:
        - Logging (implemented)
        - Email (TODO)
        - Slack/Teams webhooks (TODO)
        - PagerDuty (TODO)

        Args:
            level: Alert level (info, warning, critical)
            message: Alert message
            budget_id: Budget identifier
            utilization: Current utilization percentage
        """
        # Log alert
        log_level = {
            "info": logging.INFO,
            "warning": logging.WARNING,
            "critical": logging.CRITICAL,
        }.get(level, logging.WARNING)

        logger.log(log_level, f"BUDGET ALERT [{level.upper()}]: {message}")

        # TODO: Send email alert
        # TODO: Send webhook notification
        # TODO: Send to PagerDuty/OpsGenie

    def _calculate_period_end(self, start_date: datetime, period: BudgetPeriod) -> datetime:
        """Calculate end date for budget period."""
        if period == BudgetPeriod.DAILY:
            return start_date + timedelta(days=1)
        elif period == BudgetPeriod.WEEKLY:
            return start_date + timedelta(weeks=1)
        elif period == BudgetPeriod.MONTHLY:
            # Add one month (approximate)
            return start_date + timedelta(days=30)
        elif period == BudgetPeriod.QUARTERLY:
            return start_date + timedelta(days=90)
        else:  # BudgetPeriod.YEARLY
            return start_date + timedelta(days=365)

    async def reset_budget(self, budget_id: str) -> None:
        """
        Reset budget for new period.

        Clears alerted thresholds so alerts can trigger again.

        Args:
            budget_id: Budget identifier
        """
        async with self._lock:
            if budget_id in self._alerted_thresholds:
                self._alerted_thresholds[budget_id].clear()

        logger.info(f"Reset budget: {budget_id}")

    async def get_all_budgets(self) -> List[Budget]:
        """Get all budgets."""
        async with self._lock:
            return list(self._budgets.values())

    async def get_alerts(
        self,
        budget_id: Optional[str] = None,
        acknowledged: Optional[bool] = None,
    ) -> List[BudgetAlert]:
        """
        Get budget alerts with optional filtering.

        Args:
            budget_id: Filter by budget (optional)
            acknowledged: Filter by acknowledgment status (optional)

        Returns:
            List of BudgetAlerts
        """
        async with self._lock:
            alerts = self._alerts.copy()

        if budget_id:
            alerts = [a for a in alerts if a.budget_id == budget_id]

        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]

        return alerts


# ==============================================================================
# Singleton Instance
# ==============================================================================

_monitor_instance: Optional[BudgetMonitor] = None


def get_budget_monitor() -> BudgetMonitor:
    """Get or create singleton budget monitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = BudgetMonitor()
    return _monitor_instance
