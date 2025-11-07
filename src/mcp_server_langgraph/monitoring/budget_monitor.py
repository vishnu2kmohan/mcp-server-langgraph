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
import smtplib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

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

    def __init__(
        self,
        cost_collector: Optional["CostMetricsCollector"] = None,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        email_from: Optional[str] = None,
        email_to: Optional[List[str]] = None,
        webhook_url: Optional[str] = None,
    ) -> None:
        """
        Initialize budget monitor.

        Args:
            cost_collector: CostMetricsCollector instance for querying actual spend.
            smtp_host: SMTP server hostname for email alerts
            smtp_port: SMTP server port (default: 587)
            smtp_username: SMTP authentication username
            smtp_password: SMTP authentication password
            email_from: From email address for alerts
            email_to: List of recipient email addresses
            webhook_url: Webhook URL for POST notifications
        """
        from mcp_server_langgraph.monitoring.cost_tracker import CostMetricsCollector

        self._budgets: Dict[str, Budget] = {}
        self._alerts: List[BudgetAlert] = []
        self._alerted_thresholds: Dict[str, set[Decimal]] = {}
        self._lock = asyncio.Lock()
        self._cost_collector = cost_collector or CostMetricsCollector()

        # Alert transport configuration
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_username = smtp_username
        self._smtp_password = smtp_password
        self._email_from = email_from
        self._email_to = email_to or []
        self._webhook_url = webhook_url

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

        Queries CostMetricsCollector for actual spending within the current period.

        Args:
            budget_id: Budget identifier

        Returns:
            Total spend in USD for current period
        """
        async with self._lock:
            budget = self._budgets.get(budget_id)

        if not budget:
            return Decimal("0.00")

        # Calculate current period boundaries
        now = datetime.now(timezone.utc)
        period_start, period_end = self._calculate_period_boundaries(budget, now)

        # Get all records from cost collector (using "day" but we'll filter manually)
        all_records = await self._cost_collector.get_records(period="day")

        # Filter records by budget period
        period_records = [record for record in all_records if period_start <= record.timestamp <= period_end]

        # Sum costs
        total_cost = sum(
            (record.estimated_cost_usd for record in period_records),
            Decimal("0.00"),
        )

        logger.debug(
            f"Budget {budget_id}: {len(period_records)} records in period "
            f"{period_start} to {period_end}, total cost: ${total_cost}"
        )

        return total_cost

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
        Send budget alert notification via multiple channels.

        Supports:
        - Logging (always enabled)
        - Email via SMTP (if configured)
        - Generic webhooks for Slack/Teams/custom (if configured)

        Args:
            level: Alert level (info, warning, critical)
            message: Alert message
            budget_id: Budget identifier
            utilization: Current utilization percentage
        """
        # 1. Log alert (always enabled)
        log_level = {
            "info": logging.INFO,
            "warning": logging.WARNING,
            "critical": logging.CRITICAL,
        }.get(level, logging.WARNING)

        logger.log(log_level, f"BUDGET ALERT [{level.upper()}]: {message}")

        # 2. Send email alert (if configured)
        if self._smtp_host and self._email_from and self._email_to:
            try:
                await self._send_email_alert(level, message, budget_id, utilization)
            except Exception as e:
                logger.error(f"Failed to send email alert: {e}")

        # 3. Send webhook notification (if configured)
        if self._webhook_url:
            try:
                await self._send_webhook_alert(level, message, budget_id, utilization)
            except Exception as e:
                logger.error(f"Failed to send webhook alert: {e}")

    async def _send_email_alert(self, level: str, message: str, budget_id: str, utilization: float) -> None:
        """Send email alert via SMTP."""
        subject = f"[{level.upper()}] Budget Alert: {budget_id}"

        # Create HTML email body
        html_body = f"""
        <html>
          <body>
            <h2 style="color: {'red' if level == 'critical' else 'orange'};">Budget Alert</h2>
            <p><strong>Level:</strong> {level.upper()}</p>
            <p><strong>Budget ID:</strong> {budget_id}</p>
            <p><strong>Utilization:</strong> {utilization:.1f}%</p>
            <p><strong>Message:</strong> {message}</p>
            <p><strong>Timestamp:</strong> {datetime.now(timezone.utc).isoformat()}</p>
          </body>
        </html>
        """

        # Create plain text fallback
        text_body = f"""
Budget Alert [{level.upper()}]

Budget ID: {budget_id}
Utilization: {utilization:.1f}%
Message: {message}
Timestamp: {datetime.now(timezone.utc).isoformat()}
        """

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._email_from
        msg["To"] = ", ".join(self._email_to)

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        # Send email (run in thread pool to avoid blocking)
        await asyncio.to_thread(self._send_smtp, msg)

        logger.info(f"Email alert sent to {len(self._email_to)} recipients")

    def _send_smtp(self, msg: MIMEMultipart) -> None:
        """Send SMTP message (blocking, meant to be called via to_thread)."""
        with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
            server.starttls()
            if self._smtp_username and self._smtp_password:
                server.login(self._smtp_username, self._smtp_password)
            server.send_message(msg)

    async def _send_webhook_alert(self, level: str, message: str, budget_id: str, utilization: float) -> None:
        """Send webhook notification via HTTP POST."""
        payload = {
            "alert_type": "budget",
            "level": level,
            "budget_id": budget_id,
            "message": message,
            "utilization": utilization,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10.0,
            )
            response.raise_for_status()

        logger.info(f"Webhook alert sent to {self._webhook_url}")

    def _calculate_period_boundaries(self, budget: Budget, current_time: datetime) -> tuple[datetime, datetime]:
        """
        Calculate the start and end boundaries for the current budget period.

        For recurring periods, this calculates which period we're currently in
        based on the budget start date.

        Args:
            budget: Budget configuration
            current_time: Current timestamp

        Returns:
            Tuple of (period_start, period_end)
        """
        budget.start_date

        if budget.period == BudgetPeriod.DAILY:
            # Find current day boundary
            period_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1)
        elif budget.period == BudgetPeriod.WEEKLY:
            # Find current week boundary (Monday-Sunday)
            days_since_monday = current_time.weekday()
            period_start = (current_time - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            period_end = period_start + timedelta(weeks=1)
        elif budget.period == BudgetPeriod.MONTHLY:
            # Find current month boundary
            period_start = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Next month's first day
            if current_time.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1)
        elif budget.period == BudgetPeriod.QUARTERLY:
            # Find current quarter boundary
            quarter_month = ((current_time.month - 1) // 3) * 3 + 1
            period_start = current_time.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=90)
        else:  # BudgetPeriod.YEARLY
            # Find current year boundary
            period_start = current_time.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start.replace(year=period_start.year + 1)

        return period_start, period_end

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
