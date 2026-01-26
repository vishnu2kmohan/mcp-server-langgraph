"""
Push Notification Analytics Tests.

TDD tests for tracking and analyzing push notification performance.

Features:
- Track delivery success/failure rates
- Monitor user engagement (click-through rates)
- Analyze notification latency
- Generate reports and metrics

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="push_analytics")
class TestDeliveryTracking:
    """Tests for push notification delivery tracking."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_record_delivery_success(self) -> None:
        """Test recording successful push delivery."""
        from mcp_server_langgraph.notifications.push_analytics import (
            PushAnalytics,
            DeliveryEvent,
        )

        mock_store = AsyncMock(return_value=None)
        mock_store.save_event = AsyncMock(return_value=None)

        analytics = PushAnalytics(store=mock_store)
        event = DeliveryEvent(
            notification_id="notif-001",
            user_id="user-001",
            status="delivered",
            timestamp=datetime.now(UTC),
        )

        await analytics.record_delivery(event)

        mock_store.save_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_delivery_failure(self) -> None:
        """Test recording failed push delivery."""
        from mcp_server_langgraph.notifications.push_analytics import (
            PushAnalytics,
            DeliveryEvent,
        )

        mock_store = AsyncMock(return_value=None)
        mock_store.save_event = AsyncMock(return_value=None)

        analytics = PushAnalytics(store=mock_store)
        event = DeliveryEvent(
            notification_id="notif-002",
            user_id="user-002",
            status="failed",
            error_code="expired_subscription",
            timestamp=datetime.now(UTC),
        )

        await analytics.record_delivery(event)

        mock_store.save_event.assert_called_once()
        saved_event = mock_store.save_event.call_args[0][0]
        assert saved_event.status == "failed"
        assert saved_event.error_code == "expired_subscription"


@pytest.mark.unit
@pytest.mark.xdist_group(name="push_analytics")
class TestEngagementTracking:
    """Tests for user engagement tracking."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_record_notification_click(self) -> None:
        """Test recording notification click event."""
        from mcp_server_langgraph.notifications.push_analytics import (
            PushAnalytics,
            EngagementEvent,
        )

        mock_store = AsyncMock(return_value=None)
        mock_store.save_engagement = AsyncMock(return_value=None)

        analytics = PushAnalytics(store=mock_store)
        event = EngagementEvent(
            notification_id="notif-003",
            user_id="user-003",
            action="click",
            timestamp=datetime.now(UTC),
        )

        await analytics.record_engagement(event)

        mock_store.save_engagement.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_notification_dismiss(self) -> None:
        """Test recording notification dismiss event."""
        from mcp_server_langgraph.notifications.push_analytics import (
            PushAnalytics,
            EngagementEvent,
        )

        mock_store = AsyncMock(return_value=None)
        mock_store.save_engagement = AsyncMock(return_value=None)

        analytics = PushAnalytics(store=mock_store)
        event = EngagementEvent(
            notification_id="notif-004",
            user_id="user-004",
            action="dismiss",
            timestamp=datetime.now(UTC),
        )

        await analytics.record_engagement(event)

        mock_store.save_engagement.assert_called_once()


@pytest.mark.unit
@pytest.mark.xdist_group(name="push_analytics")
class TestMetricsCalculation:
    """Tests for analytics metrics calculation."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_calculate_delivery_rate(self) -> None:
        """Test calculating delivery success rate."""
        from mcp_server_langgraph.notifications.push_analytics import (
            PushAnalytics,
            DeliverySummary,
        )

        mock_store = AsyncMock(return_value=None)
        mock_store.get_delivery_stats = AsyncMock(
            return_value={
                "total_sent": 100,
                "delivered": 95,
                "failed": 5,
            }
        )

        analytics = PushAnalytics(store=mock_store)
        summary = await analytics.get_delivery_summary(
            start_time=datetime.now(UTC) - timedelta(hours=24),
            end_time=datetime.now(UTC),
        )

        assert isinstance(summary, DeliverySummary)
        assert summary.total_sent == 100
        assert summary.delivered == 95
        assert summary.delivery_rate == 0.95

    @pytest.mark.asyncio
    async def test_calculate_click_through_rate(self) -> None:
        """Test calculating click-through rate."""
        from mcp_server_langgraph.notifications.push_analytics import (
            PushAnalytics,
            EngagementSummary,
        )

        mock_store = AsyncMock(return_value=None)
        mock_store.get_engagement_stats = AsyncMock(
            return_value={
                "delivered": 100,
                "clicked": 25,
                "dismissed": 50,
                "ignored": 25,
            }
        )

        analytics = PushAnalytics(store=mock_store)
        summary = await analytics.get_engagement_summary(
            start_time=datetime.now(UTC) - timedelta(hours=24),
            end_time=datetime.now(UTC),
        )

        assert isinstance(summary, EngagementSummary)
        assert summary.click_through_rate == 0.25
        assert summary.dismiss_rate == 0.5


@pytest.mark.unit
@pytest.mark.xdist_group(name="push_analytics")
class TestLatencyTracking:
    """Tests for notification latency tracking."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_record_delivery_latency(self) -> None:
        """Test recording delivery latency."""
        from mcp_server_langgraph.notifications.push_analytics import (
            PushAnalytics,
            DeliveryEvent,
        )

        mock_store = AsyncMock(return_value=None)
        mock_store.save_event = AsyncMock(return_value=None)

        analytics = PushAnalytics(store=mock_store)
        event = DeliveryEvent(
            notification_id="notif-005",
            user_id="user-005",
            status="delivered",
            timestamp=datetime.now(UTC),
            latency_ms=150,
        )

        await analytics.record_delivery(event)

        saved_event = mock_store.save_event.call_args[0][0]
        assert saved_event.latency_ms == 150

    @pytest.mark.asyncio
    async def test_calculate_average_latency(self) -> None:
        """Test calculating average delivery latency."""
        from mcp_server_langgraph.notifications.push_analytics import (
            PushAnalytics,
            LatencySummary,
        )

        mock_store = AsyncMock(return_value=None)
        mock_store.get_latency_stats = AsyncMock(
            return_value={
                "avg_latency_ms": 120,
                "p50_latency_ms": 100,
                "p95_latency_ms": 300,
                "p99_latency_ms": 500,
            }
        )

        analytics = PushAnalytics(store=mock_store)
        summary = await analytics.get_latency_summary(
            start_time=datetime.now(UTC) - timedelta(hours=24),
            end_time=datetime.now(UTC),
        )

        assert isinstance(summary, LatencySummary)
        assert summary.avg_latency_ms == 120
        assert summary.p95_latency_ms == 300


@pytest.mark.unit
@pytest.mark.xdist_group(name="push_analytics")
class TestReportGeneration:
    """Tests for analytics report generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_generate_daily_report(self) -> None:
        """Test generating daily analytics report."""
        from mcp_server_langgraph.notifications.push_analytics import (
            PushAnalytics,
            AnalyticsReport,
        )

        mock_store = AsyncMock(return_value=None)
        mock_store.get_delivery_stats = AsyncMock(return_value={"total_sent": 500, "delivered": 480, "failed": 20})
        mock_store.get_engagement_stats = AsyncMock(
            return_value={
                "delivered": 480,
                "clicked": 120,
                "dismissed": 200,
                "ignored": 160,
            }
        )
        mock_store.get_latency_stats = AsyncMock(
            return_value={
                "avg_latency_ms": 100,
                "p50_latency_ms": 80,
                "p95_latency_ms": 250,
                "p99_latency_ms": 400,
            }
        )

        analytics = PushAnalytics(store=mock_store)
        report = await analytics.generate_report(
            start_time=datetime.now(UTC) - timedelta(days=1),
            end_time=datetime.now(UTC),
        )

        assert isinstance(report, AnalyticsReport)
        assert report.delivery.total_sent == 500
        assert report.engagement.click_through_rate == 0.25
        assert report.latency.avg_latency_ms == 100


@pytest.mark.unit
@pytest.mark.xdist_group(name="push_analytics")
class TestAnalyticsModels:
    """Tests for analytics data models."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_delivery_event_model(self) -> None:
        """Test DeliveryEvent model."""
        from mcp_server_langgraph.notifications.push_analytics import (
            DeliveryEvent,
        )

        event = DeliveryEvent(
            notification_id="notif-006",
            user_id="user-006",
            status="delivered",
            timestamp=datetime.now(UTC),
            latency_ms=100,
        )

        assert event.notification_id == "notif-006"
        assert event.status == "delivered"
        assert event.latency_ms == 100

    def test_engagement_event_model(self) -> None:
        """Test EngagementEvent model."""
        from mcp_server_langgraph.notifications.push_analytics import (
            EngagementEvent,
        )

        event = EngagementEvent(
            notification_id="notif-007",
            user_id="user-007",
            action="click",
            timestamp=datetime.now(UTC),
        )

        assert event.notification_id == "notif-007"
        assert event.action == "click"

    def test_delivery_summary_model(self) -> None:
        """Test DeliverySummary model."""
        from mcp_server_langgraph.notifications.push_analytics import (
            DeliverySummary,
        )

        summary = DeliverySummary(
            total_sent=100,
            delivered=95,
            failed=5,
            delivery_rate=0.95,
        )

        assert summary.total_sent == 100
        assert summary.delivery_rate == 0.95

    def test_engagement_summary_model(self) -> None:
        """Test EngagementSummary model."""
        from mcp_server_langgraph.notifications.push_analytics import (
            EngagementSummary,
        )

        summary = EngagementSummary(
            delivered=100,
            clicked=25,
            dismissed=50,
            ignored=25,
            click_through_rate=0.25,
            dismiss_rate=0.5,
        )

        assert summary.click_through_rate == 0.25
        assert summary.dismiss_rate == 0.5

    def test_latency_summary_model(self) -> None:
        """Test LatencySummary model."""
        from mcp_server_langgraph.notifications.push_analytics import (
            LatencySummary,
        )

        summary = LatencySummary(
            avg_latency_ms=100,
            p50_latency_ms=80,
            p95_latency_ms=250,
            p99_latency_ms=400,
        )

        assert summary.avg_latency_ms == 100
        assert summary.p95_latency_ms == 250
