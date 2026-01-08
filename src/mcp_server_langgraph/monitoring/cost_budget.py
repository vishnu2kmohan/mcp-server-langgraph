"""
Cost Budget Management Module

Provides budget definition, tracking, alerting, anomaly detection,
and forecasting for LLM cost management.

Features:
- Budget definition per organization/project/team/user
- Configurable warning and critical thresholds
- Real-time budget status checking
- Anomaly detection using statistical methods (Z-score)
- Cost forecasting based on usage trends

Architecture (ADR-0026 Cost Tracking Enhancements):
- Budget: Immutable budget configuration
- BudgetStatus: Current status of spend against budget
- BudgetChecker: Checks current spend against budget thresholds
- CostAnomalyDetector: Detects unusual spending patterns
- CostForecaster: Projects end-of-month spend based on trends

Example:
    >>> from mcp_server_langgraph.monitoring.cost_budget import (
    ...     Budget, BudgetChecker, CostAnomalyDetector, CostForecaster
    ... )
    >>> budget = Budget(
    ...     entity_type="organization",
    ...     entity_id="org:acme",
    ...     monthly_limit_usd=Decimal("1000.00"),
    ... )
    >>> checker = BudgetChecker()
    >>> status = await checker.check(budget, current_spend=Decimal("850.00"))
    >>> print(status.status)  # "warning"
"""

import logging
import statistics
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

from mcp_server_langgraph.core.numeric import safe_divide

logger = logging.getLogger(__name__)


# ==============================================================================
# Budget Definition
# ==============================================================================


@dataclass
class Budget:
    """
    Budget configuration for an entity.

    Supports budgets at multiple levels:
    - organization: Company-wide budget
    - project: Per-project budget
    - team: Team-level budget
    - user: Individual user budget

    Attributes:
        entity_type: Type of entity (organization, project, team, user)
        entity_id: Unique identifier for the entity
        monthly_limit_usd: Monthly budget limit in USD
        warning_threshold: Percentage at which to trigger warning (default: 0.80 = 80%)
        critical_threshold: Percentage at which to trigger critical alert (default: 1.0 = 100%)
    """

    entity_type: Literal["organization", "project", "team", "user"]
    entity_id: str
    monthly_limit_usd: Decimal
    warning_threshold: float = 0.80
    critical_threshold: float = 1.0
    name: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        """Validate thresholds."""
        if self.warning_threshold >= self.critical_threshold:
            raise ValueError("warning_threshold must be less than critical_threshold")
        if self.monthly_limit_usd <= Decimal("0"):
            raise ValueError("monthly_limit_usd must be positive")


# ==============================================================================
# Budget Status
# ==============================================================================


@dataclass
class BudgetStatus:
    """
    Current status of spend against a budget.

    Attributes:
        budget: The budget being checked
        current_spend: Current spend amount
        percent_used: Percentage of budget used (0-100+)
        status: Current status (ok, warning, critical, exceeded)
        remaining: Amount remaining in budget
    """

    budget: Budget
    current_spend: Decimal
    percent_used: float
    status: Literal["ok", "warning", "critical", "exceeded"]
    remaining: Decimal

    @property
    def message(self) -> str:
        """Generate a human-readable status message."""
        if self.status == "ok":
            return f"Budget on track: {self.percent_used:.1f}% used, ${self.remaining:.2f} remaining"
        elif self.status == "warning":
            return f"Budget warning: {self.percent_used:.1f}% used, ${self.remaining:.2f} remaining"
        elif self.status == "critical":
            return f"Budget critical: {self.percent_used:.1f}% used, ${self.remaining:.2f} remaining"
        else:  # exceeded
            overspend = abs(self.remaining)
            return f"Budget exceeded: {self.percent_used:.1f}% used, ${overspend:.2f} over budget"


# ==============================================================================
# Budget Checker
# ==============================================================================


class BudgetChecker:
    """
    Checks current spend against budget thresholds.

    Thread-safe and stateless - can be shared across requests.
    """

    async def check(self, budget: Budget, current_spend: Decimal) -> BudgetStatus:
        """
        Check current spend against a budget.

        Args:
            budget: The budget configuration
            current_spend: Current spend amount in USD

        Returns:
            BudgetStatus with current status
        """
        # Use safe_divide to handle zero/invalid budget limits gracefully
        percent_used = safe_divide(float(current_spend), float(budget.monthly_limit_usd)) * 100
        remaining = budget.monthly_limit_usd - current_spend

        # Determine status based on thresholds
        # exceeded: over 100% (more than the limit)
        # critical: at or above critical threshold (default 100%)
        # warning: at or above warning threshold (default 80%)
        # ok: below warning threshold
        if percent_used > 100:
            status = "exceeded"
        elif percent_used >= budget.critical_threshold * 100:
            status = "critical"
        elif percent_used >= budget.warning_threshold * 100:
            status = "warning"
        else:
            status = "ok"

        return BudgetStatus(
            budget=budget,
            current_spend=current_spend,
            percent_used=percent_used,
            status=status,
            remaining=remaining,
        )

    async def check_all(
        self,
        budgets: list[Budget],
        spend_by_entity: dict[str, Decimal],
    ) -> list[BudgetStatus]:
        """
        Check multiple budgets at once.

        Args:
            budgets: List of budgets to check
            spend_by_entity: Dictionary mapping entity_id to current spend

        Returns:
            List of BudgetStatus objects
        """
        results = []
        for budget in budgets:
            spend = spend_by_entity.get(budget.entity_id, Decimal("0"))
            status = await self.check(budget, spend)
            results.append(status)
        return results


# ==============================================================================
# Anomaly Detection
# ==============================================================================


@dataclass
class AnomalyResult:
    """
    Result of anomaly detection.

    Attributes:
        is_anomaly: Whether the current value is anomalous
        severity: Severity if anomaly detected (warning, critical)
        z_score: Z-score of the current value
        mean: Historical mean
        std_dev: Historical standard deviation
        message: Human-readable explanation
    """

    is_anomaly: bool
    severity: Literal["none", "warning", "critical"]
    z_score: float
    mean: Decimal
    std_dev: Decimal
    message: str


class CostAnomalyDetector:
    """
    Detects anomalous spending patterns using statistical methods.

    Uses Z-score (standard deviations from mean) to identify unusual values.
    - Z-score > 2: Warning anomaly
    - Z-score > 3: Critical anomaly
    """

    def __init__(
        self,
        warning_z_score: float = 2.0,
        critical_z_score: float = 3.0,
        min_history_size: int = 3,
    ) -> None:
        """
        Initialize the anomaly detector.

        Args:
            warning_z_score: Z-score threshold for warning (default: 2.0)
            critical_z_score: Z-score threshold for critical (default: 3.0)
            min_history_size: Minimum historical values needed (default: 3)
        """
        self.warning_z_score = warning_z_score
        self.critical_z_score = critical_z_score
        self.min_history_size = min_history_size

    async def detect(
        self,
        current_value: Decimal,
        historical_values: list[Decimal],
    ) -> AnomalyResult:
        """
        Detect if the current value is anomalous compared to history.

        Args:
            current_value: Current value to check
            historical_values: List of historical values

        Returns:
            AnomalyResult with detection details
        """
        # Need enough history for meaningful statistics
        if len(historical_values) < self.min_history_size:
            return AnomalyResult(
                is_anomaly=False,
                severity="none",
                z_score=0.0,
                mean=Decimal("0"),
                std_dev=Decimal("0"),
                message="Insufficient history for anomaly detection",
            )

        # Calculate statistics
        float_values = [float(v) for v in historical_values]
        mean = statistics.mean(float_values)
        std_dev = statistics.stdev(float_values) if len(float_values) > 1 else 0.0

        # Handle case where std_dev is 0 (all values identical)
        if std_dev == 0:
            # If current equals historical, not anomalous
            if float(current_value) == mean:
                return AnomalyResult(
                    is_anomaly=False,
                    severity="none",
                    z_score=0.0,
                    mean=Decimal(str(mean)),
                    std_dev=Decimal("0"),
                    message="Consistent spending pattern",
                )
            # Otherwise, any deviation is anomalous
            return AnomalyResult(
                is_anomaly=True,
                severity="warning",
                z_score=float("inf"),
                mean=Decimal(str(mean)),
                std_dev=Decimal("0"),
                message="Deviation from perfectly consistent spending",
            )

        # Calculate Z-score
        z_score = (float(current_value) - mean) / std_dev

        # Determine severity
        if abs(z_score) >= self.critical_z_score:
            is_anomaly = True
            severity = "critical"
            message = f"Critical anomaly: {z_score:.2f} standard deviations from mean"
        elif abs(z_score) >= self.warning_z_score:
            is_anomaly = True
            severity = "warning"
            message = f"Warning anomaly: {z_score:.2f} standard deviations from mean"
        else:
            is_anomaly = False
            severity = "none"
            message = f"Normal: {z_score:.2f} standard deviations from mean"

        return AnomalyResult(
            is_anomaly=is_anomaly,
            severity=severity,
            z_score=z_score,
            mean=Decimal(str(mean)),
            std_dev=Decimal(str(std_dev)),
            message=message,
        )


# ==============================================================================
# Cost Forecasting
# ==============================================================================


@dataclass
class CostForecast:
    """
    Cost forecast result.

    Attributes:
        projected_total: Projected total spend for the period
        confidence_low: Lower bound of confidence interval
        confidence_high: Upper bound of confidence interval
        trend: Trend direction (increasing, decreasing, stable)
        days_analyzed: Number of days of data analyzed
        message: Human-readable forecast summary
    """

    projected_total: Decimal
    confidence_low: Decimal
    confidence_high: Decimal
    trend: Literal["increasing", "decreasing", "stable"]
    days_analyzed: int
    message: str


class CostForecaster:
    """
    Forecasts end-of-period cost based on usage trends.

    Uses simple linear regression to project costs and estimate
    confidence intervals.
    """

    def __init__(
        self,
        confidence_interval: float = 0.95,
    ) -> None:
        """
        Initialize the forecaster.

        Args:
            confidence_interval: Confidence interval for projections (default: 0.95)
        """
        self.confidence_interval = confidence_interval

    async def forecast_month_end(
        self,
        daily_values: list[Decimal],
        days_in_month: int = 30,
    ) -> CostForecast:
        """
        Forecast end-of-month spend based on daily values.

        Uses linear regression to identify trend and project future spend.

        Args:
            daily_values: List of daily spend values (most recent last)
            days_in_month: Total days in the month

        Returns:
            CostForecast with projection details
        """
        if not daily_values:
            return CostForecast(
                projected_total=Decimal("0"),
                confidence_low=Decimal("0"),
                confidence_high=Decimal("0"),
                trend="stable",
                days_analyzed=0,
                message="No data available for forecasting",
            )

        days_analyzed = len(daily_values)
        days_remaining = days_in_month - days_analyzed

        # Convert to floats for calculation
        float_values = [float(v) for v in daily_values]

        # Calculate current total
        current_total = sum(float_values)

        # Simple linear regression to find trend
        n = len(float_values)
        if n > 1:
            # Calculate slope (trend)
            x = list(range(n))
            x_mean = sum(x) / n
            y_mean = sum(float_values) / n

            numerator = sum((x[i] - x_mean) * (float_values[i] - y_mean) for i in range(n))
            denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

            slope = numerator / denominator if denominator != 0 else 0.0

            # Determine trend direction
            if slope > 0.01 * y_mean:  # More than 1% increase per day
                trend = "increasing"
            elif slope < -0.01 * y_mean:  # More than 1% decrease per day
                trend = "decreasing"
            else:
                trend = "stable"

            # Project future values using trend
            # For remaining days, project using the slope
            last_value = float_values[-1]
            projected_daily = [last_value + slope * (i + 1) for i in range(days_remaining)]
            projected_remaining = sum(max(0, v) for v in projected_daily)  # Don't go negative
        else:
            # Single data point - use simple average
            slope = 0.0
            trend = "stable"
            projected_remaining = float_values[0] * days_remaining

        projected_total = current_total + projected_remaining

        # Calculate confidence interval using standard deviation
        if n > 1:
            std_dev = statistics.stdev(float_values)
            # Confidence interval widens with projection horizon
            margin = std_dev * days_remaining * 0.5  # Simplified margin
        else:
            margin = projected_total * 0.2  # 20% margin with single data point

        confidence_low = max(Decimal("0"), Decimal(str(projected_total - margin)))
        confidence_high = Decimal(str(projected_total + margin))

        # Generate message
        if days_remaining > 0:
            daily_avg = current_total / n
            message = (
                f"Based on {days_analyzed} days of data (avg ${daily_avg:.2f}/day), "
                f"projecting ${projected_total:.2f} by end of month ({trend} trend)"
            )
        else:
            message = f"Month complete: ${projected_total:.2f} total spend"

        return CostForecast(
            projected_total=Decimal(str(round(projected_total, 2))),
            confidence_low=Decimal(str(round(float(confidence_low), 2))),
            confidence_high=Decimal(str(round(float(confidence_high), 2))),
            trend=trend,
            days_analyzed=days_analyzed,
            message=message,
        )


# ==============================================================================
# Budget Alert Broadcasting
# ==============================================================================


class WebSocketConnection:
    """Protocol for WebSocket connections (duck-typed)."""

    async def send_json(self, data: dict[str, Any]) -> None:
        """Send JSON data to the WebSocket."""
        ...


@dataclass
class BudgetSubscriber:
    """A WebSocket subscriber for budget alerts."""

    connection: WebSocketConnection
    user_id: str
    entity_filters: list[str] = field(default_factory=list)


def budget_status_to_message(status: BudgetStatus) -> dict[str, Any]:
    """
    Convert a BudgetStatus to WebSocket message format.

    Args:
        status: The BudgetStatus to convert.

    Returns:
        Dictionary in the expected WebSocket message format.
    """
    return {
        "type": "budget_alert",
        "payload": {
            "entity_type": status.budget.entity_type,
            "entity_id": status.budget.entity_id,
            "status": status.status,
            "percent_used": status.percent_used,
            "current_spend": str(status.current_spend),
            "remaining": str(status.remaining),
            "monthly_limit_usd": str(status.budget.monthly_limit_usd),
            "message": status.message,
        },
    }


class BudgetAlertBroadcaster:
    """
    Broadcasts budget alerts to subscribed WebSocket connections.

    Features:
    - Subscribe/unsubscribe pattern for WebSocket connections
    - Entity-based filtering (org, project, team, user)
    - Push notifications for critical/exceeded budgets
    - Graceful handling of disconnected clients
    - Thread-safe subscriber management

    Message Format:
        {
            "type": "budget_alert",
            "payload": {
                "entity_type": "organization" | "project" | "team" | "user",
                "entity_id": "string",
                "status": "ok" | "warning" | "critical" | "exceeded",
                "percent_used": number,
                "current_spend": "string (decimal)",
                "remaining": "string (decimal)",
                "monthly_limit_usd": "string (decimal)",
                "message": "string"
            }
        }
    """

    def __init__(self, push_sender: Any | None = None) -> None:
        """
        Initialize the broadcaster.

        Args:
            push_sender: Optional push notification sender for critical alerts.
        """
        import asyncio

        self._subscribers: list[BudgetSubscriber] = []
        self._lock = asyncio.Lock()
        self._push_sender = push_sender

    @property
    def subscriber_count(self) -> int:
        """Get the number of active subscribers."""
        return len(self._subscribers)

    def get_subscriber_filters(self, user_id: str) -> list[str]:
        """
        Get the entity filters for a specific user.

        Args:
            user_id: The user ID to check.

        Returns:
            List of entity filters for the user, or empty list if not found.
        """
        for subscriber in self._subscribers:
            if subscriber.user_id == user_id:
                return subscriber.entity_filters
        return []

    async def subscribe(
        self,
        connection: WebSocketConnection,
        user_id: str,
        entity_filters: list[str] | None = None,
    ) -> None:
        """
        Subscribe a WebSocket connection to budget alerts.

        Args:
            connection: The WebSocket connection to subscribe.
            user_id: The user ID.
            entity_filters: Optional list of entity IDs to filter alerts.
                           If empty/None, receives all budget alerts.
        """
        async with self._lock:
            subscriber = BudgetSubscriber(
                connection=connection,
                user_id=user_id,
                entity_filters=entity_filters or [],
            )
            self._subscribers.append(subscriber)
            logger.info(f"Budget subscriber added. User: {user_id}. Total: {self.subscriber_count}")

    async def unsubscribe(self, connection: WebSocketConnection) -> None:
        """
        Unsubscribe a WebSocket connection.

        Args:
            connection: The WebSocket connection to unsubscribe.
        """
        async with self._lock:
            self._subscribers = [s for s in self._subscribers if s.connection != connection]
            logger.info(f"Budget subscriber removed. Total: {self.subscriber_count}")

    async def broadcast_budget_status(self, status: BudgetStatus) -> None:
        """
        Broadcast a budget status to relevant subscribers.

        Filters subscribers based on entity_filters:
        - Subscribers with no filters receive all alerts
        - Subscribers with filters only receive matching alerts

        For critical/exceeded status, also sends push notifications.

        Args:
            status: The BudgetStatus to broadcast.
        """
        # Send push notification for critical/exceeded status
        if self._push_sender and status.status in ("critical", "exceeded"):
            try:
                await self._push_sender.send_budget_alert(status)
                logger.info(f"Sent push notification for budget {status.status}: {status.budget.entity_id}")
            except Exception as e:
                logger.warning(f"Failed to send push notification: {e}")

        if not self._subscribers:
            return

        message = budget_status_to_message(status)
        entity_id = status.budget.entity_id
        failed_connections: list[WebSocketConnection] = []

        async with self._lock:
            for subscriber in self._subscribers:
                # Filter by entity if subscriber has filters
                if subscriber.entity_filters:
                    if entity_id not in subscriber.entity_filters:
                        continue

                try:
                    await subscriber.connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send budget alert to {subscriber.user_id}: {e}")
                    failed_connections.append(subscriber.connection)

            # Remove failed connections
            if failed_connections:
                self._subscribers = [s for s in self._subscribers if s.connection not in failed_connections]
                logger.info(f"Removed {len(failed_connections)} failed subscribers. Remaining: {self.subscriber_count}")


# ==============================================================================
# Module-Level Singleton Accessors
# ==============================================================================

_budget_checker: BudgetChecker | None = None
_anomaly_detector: CostAnomalyDetector | None = None
_forecaster: CostForecaster | None = None
_budget_alert_broadcaster: BudgetAlertBroadcaster | None = None


def get_budget_checker() -> BudgetChecker:
    """Get the singleton BudgetChecker instance."""
    global _budget_checker
    if _budget_checker is None:
        _budget_checker = BudgetChecker()
    return _budget_checker


def get_anomaly_detector() -> CostAnomalyDetector:
    """Get the singleton CostAnomalyDetector instance."""
    global _anomaly_detector
    if _anomaly_detector is None:
        _anomaly_detector = CostAnomalyDetector()
    return _anomaly_detector


def get_forecaster() -> CostForecaster:
    """Get the singleton CostForecaster instance."""
    global _forecaster
    if _forecaster is None:
        _forecaster = CostForecaster()
    return _forecaster


def get_budget_alert_broadcaster() -> BudgetAlertBroadcaster:
    """Get the singleton BudgetAlertBroadcaster instance."""
    global _budget_alert_broadcaster
    if _budget_alert_broadcaster is None:
        _budget_alert_broadcaster = BudgetAlertBroadcaster()
    return _budget_alert_broadcaster
