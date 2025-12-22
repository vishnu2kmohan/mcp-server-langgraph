"""
Push Notification Analytics.

Service for tracking and analyzing push notification performance.

Features:
- Track delivery success/failure rates
- Monitor user engagement (click-through rates)
- Analyze notification latency
- Generate reports and metrics

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class DeliveryEvent:
    """
    Push notification delivery event.

    Attributes:
        notification_id: Unique notification identifier.
        user_id: Target user ID.
        status: Delivery status (delivered, failed).
        timestamp: Event timestamp.
        latency_ms: Delivery latency in milliseconds.
        error_code: Error code for failed deliveries.
    """

    notification_id: str
    user_id: str
    status: str  # "delivered" | "failed"
    timestamp: datetime
    latency_ms: int | None = None
    error_code: str | None = None


@dataclass
class EngagementEvent:
    """
    Push notification engagement event.

    Attributes:
        notification_id: Notification that was engaged with.
        user_id: User who engaged.
        action: Engagement action (click, dismiss, ignore).
        timestamp: Event timestamp.
    """

    notification_id: str
    user_id: str
    action: str  # "click" | "dismiss" | "ignore"
    timestamp: datetime


@dataclass
class DeliverySummary:
    """
    Summary of delivery metrics.

    Attributes:
        total_sent: Total notifications sent.
        delivered: Successfully delivered count.
        failed: Failed delivery count.
        delivery_rate: Success rate (0-1).
    """

    total_sent: int
    delivered: int
    failed: int
    delivery_rate: float


@dataclass
class EngagementSummary:
    """
    Summary of engagement metrics.

    Attributes:
        delivered: Total delivered notifications.
        clicked: Number of clicks.
        dismissed: Number of dismissals.
        ignored: Number of ignored notifications.
        click_through_rate: Click-through rate (0-1).
        dismiss_rate: Dismiss rate (0-1).
    """

    delivered: int
    clicked: int
    dismissed: int
    ignored: int
    click_through_rate: float
    dismiss_rate: float


@dataclass
class LatencySummary:
    """
    Summary of latency metrics.

    Attributes:
        avg_latency_ms: Average latency in milliseconds.
        p50_latency_ms: Median latency.
        p95_latency_ms: 95th percentile latency.
        p99_latency_ms: 99th percentile latency.
    """

    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float


@dataclass
class AnalyticsReport:
    """
    Complete analytics report.

    Attributes:
        start_time: Report start time.
        end_time: Report end time.
        delivery: Delivery metrics summary.
        engagement: Engagement metrics summary.
        latency: Latency metrics summary.
    """

    start_time: datetime
    end_time: datetime
    delivery: DeliverySummary
    engagement: EngagementSummary
    latency: LatencySummary


# =============================================================================
# Storage Protocol
# =============================================================================


class AnalyticsStore(Protocol):
    """Protocol for analytics data storage."""

    async def save_event(self, event: DeliveryEvent) -> None:
        """Save a delivery event."""
        ...

    async def save_engagement(self, event: EngagementEvent) -> None:
        """Save an engagement event."""
        ...

    async def get_delivery_stats(
        self, start_time: datetime, end_time: datetime
    ) -> dict[str, int]:
        """Get delivery statistics for a time range."""
        ...

    async def get_engagement_stats(
        self, start_time: datetime, end_time: datetime
    ) -> dict[str, int]:
        """Get engagement statistics for a time range."""
        ...

    async def get_latency_stats(
        self, start_time: datetime, end_time: datetime
    ) -> dict[str, float]:
        """Get latency statistics for a time range."""
        ...


# =============================================================================
# Push Analytics Service
# =============================================================================


class PushAnalytics:
    """
    Push notification analytics service.

    Tracks delivery, engagement, and latency metrics for push notifications.
    """

    def __init__(self, store: AnalyticsStore) -> None:
        """
        Initialize the analytics service.

        Args:
            store: Storage backend for analytics data.
        """
        self._store = store

    async def record_delivery(self, event: DeliveryEvent) -> None:
        """
        Record a delivery event.

        Args:
            event: The delivery event to record.
        """
        await self._store.save_event(event)
        logger.debug(
            f"Recorded delivery event: {event.notification_id} - {event.status}"
        )

    async def record_engagement(self, event: EngagementEvent) -> None:
        """
        Record an engagement event.

        Args:
            event: The engagement event to record.
        """
        await self._store.save_engagement(event)
        logger.debug(
            f"Recorded engagement: {event.notification_id} - {event.action}"
        )

    async def get_delivery_summary(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> DeliverySummary:
        """
        Get delivery metrics summary for a time range.

        Args:
            start_time: Start of time range.
            end_time: End of time range.

        Returns:
            DeliverySummary with delivery metrics.
        """
        stats = await self._store.get_delivery_stats(start_time, end_time)

        total_sent = stats.get("total_sent", 0)
        delivered = stats.get("delivered", 0)
        failed = stats.get("failed", 0)

        delivery_rate = delivered / total_sent if total_sent > 0 else 0.0

        return DeliverySummary(
            total_sent=total_sent,
            delivered=delivered,
            failed=failed,
            delivery_rate=delivery_rate,
        )

    async def get_engagement_summary(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> EngagementSummary:
        """
        Get engagement metrics summary for a time range.

        Args:
            start_time: Start of time range.
            end_time: End of time range.

        Returns:
            EngagementSummary with engagement metrics.
        """
        stats = await self._store.get_engagement_stats(start_time, end_time)

        delivered = stats.get("delivered", 0)
        clicked = stats.get("clicked", 0)
        dismissed = stats.get("dismissed", 0)
        ignored = stats.get("ignored", 0)

        click_through_rate = clicked / delivered if delivered > 0 else 0.0
        dismiss_rate = dismissed / delivered if delivered > 0 else 0.0

        return EngagementSummary(
            delivered=delivered,
            clicked=clicked,
            dismissed=dismissed,
            ignored=ignored,
            click_through_rate=click_through_rate,
            dismiss_rate=dismiss_rate,
        )

    async def get_latency_summary(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> LatencySummary:
        """
        Get latency metrics summary for a time range.

        Args:
            start_time: Start of time range.
            end_time: End of time range.

        Returns:
            LatencySummary with latency metrics.
        """
        stats = await self._store.get_latency_stats(start_time, end_time)

        return LatencySummary(
            avg_latency_ms=stats.get("avg_latency_ms", 0.0),
            p50_latency_ms=stats.get("p50_latency_ms", 0.0),
            p95_latency_ms=stats.get("p95_latency_ms", 0.0),
            p99_latency_ms=stats.get("p99_latency_ms", 0.0),
        )

    async def generate_report(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> AnalyticsReport:
        """
        Generate a complete analytics report for a time range.

        Args:
            start_time: Start of time range.
            end_time: End of time range.

        Returns:
            AnalyticsReport with all metrics.
        """
        delivery = await self.get_delivery_summary(start_time, end_time)
        engagement = await self.get_engagement_summary(start_time, end_time)
        latency = await self.get_latency_summary(start_time, end_time)

        return AnalyticsReport(
            start_time=start_time,
            end_time=end_time,
            delivery=delivery,
            engagement=engagement,
            latency=latency,
        )
