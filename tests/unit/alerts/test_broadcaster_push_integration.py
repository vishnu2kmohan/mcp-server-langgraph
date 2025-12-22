"""
AlertBroadcaster Push Notification Integration Tests.

TDD tests for the integration between AlertBroadcaster and PushNotificationSender.

Features tested:
- Push notifications sent for critical alerts
- Push notifications NOT sent for non-critical alerts
- Push notifications NOT sent when push_sender is None
- Push notification failures don't break WebSocket broadcast

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.alerts.broadcaster import (
    ALLOWED_SEVERITIES,
    AlertBroadcaster,
    AlertSubscriber,
)
from mcp_server_langgraph.observability.query.interfaces import (
    Alert,
    AlertSeverity,
    AlertState,
)

pytestmark = pytest.mark.unit

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_critical_alert() -> Alert:
    """Create a sample critical alert."""
    return Alert(
        alert_id="alert-critical-001",
        name="HighCPU",
        severity=AlertSeverity.CRITICAL,
        state=AlertState.FIRING,
        message="CPU usage at 95%",
        labels={"service": "api-server", "namespace": "production"},
        annotations={"runbook_url": "https://runbooks.example.com/cpu"},
        started_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_warning_alert() -> Alert:
    """Create a sample warning alert."""
    return Alert(
        alert_id="alert-warning-001",
        name="MemoryPressure",
        severity=AlertSeverity.WARNING,
        state=AlertState.FIRING,
        message="Memory usage at 80%",
        labels={"service": "api-server", "namespace": "production"},
        annotations={},
        started_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_info_alert() -> Alert:
    """Create a sample info alert (should be filtered out)."""
    return Alert(
        alert_id="alert-info-001",
        name="Heartbeat",
        severity=AlertSeverity.INFO,
        state=AlertState.FIRING,
        message="Service is healthy",
        labels={"service": "api-server"},
        annotations={},
        started_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_websocket() -> MagicMock:
    """Create a mock WebSocket connection."""
    ws = MagicMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.fixture
def mock_push_sender() -> AsyncMock:
    """Create a mock push notification sender."""
    sender = AsyncMock()
    sender.send_critical_alert = AsyncMock(return_value=5)  # 5 notifications sent
    return sender


# =============================================================================
# Push Integration Initialization Tests
# =============================================================================


@pytest.mark.xdist_group(name="broadcaster_push")
class TestBroadcasterPushInitialization:
    """Tests for AlertBroadcaster initialization with push sender."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_broadcaster_accepts_push_sender(
        self,
        mock_push_sender: AsyncMock,
    ) -> None:
        """Test that AlertBroadcaster accepts a push_sender parameter."""
        broadcaster = AlertBroadcaster(push_sender=mock_push_sender)
        assert broadcaster._push_sender is mock_push_sender

    def test_broadcaster_works_without_push_sender(self) -> None:
        """Test that AlertBroadcaster works when push_sender is None."""
        broadcaster = AlertBroadcaster()
        assert broadcaster._push_sender is None
        assert broadcaster.subscriber_count == 0


# =============================================================================
# Push Notification for Critical Alerts Tests
# =============================================================================


@pytest.mark.xdist_group(name="broadcaster_push")
class TestBroadcasterPushCriticalAlerts:
    """Tests for push notifications on critical alerts."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_push_sent_for_critical_alert(
        self,
        mock_push_sender: AsyncMock,
        sample_critical_alert: Alert,
    ) -> None:
        """Test that push notification is sent for critical alerts."""
        broadcaster = AlertBroadcaster(push_sender=mock_push_sender)

        await broadcaster.broadcast_alert(sample_critical_alert)

        mock_push_sender.send_critical_alert.assert_called_once_with(
            sample_critical_alert
        )

    @pytest.mark.asyncio
    async def test_push_not_sent_for_warning_alert(
        self,
        mock_push_sender: AsyncMock,
        sample_warning_alert: Alert,
    ) -> None:
        """Test that push notification is NOT sent for warning alerts."""
        broadcaster = AlertBroadcaster(push_sender=mock_push_sender)

        await broadcaster.broadcast_alert(sample_warning_alert)

        # Warning alerts should NOT trigger push notifications
        mock_push_sender.send_critical_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_not_sent_for_info_alert(
        self,
        mock_push_sender: AsyncMock,
        sample_info_alert: Alert,
    ) -> None:
        """Test that push notification is NOT sent for info alerts (filtered out)."""
        broadcaster = AlertBroadcaster(push_sender=mock_push_sender)

        await broadcaster.broadcast_alert(sample_info_alert)

        # Info alerts are filtered before push check
        mock_push_sender.send_critical_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_not_sent_when_push_sender_is_none(
        self,
        sample_critical_alert: Alert,
    ) -> None:
        """Test that broadcast works when push_sender is None."""
        broadcaster = AlertBroadcaster(push_sender=None)

        # Should not raise
        await broadcaster.broadcast_alert(sample_critical_alert)


# =============================================================================
# Push Notification Error Handling Tests
# =============================================================================


@pytest.mark.xdist_group(name="broadcaster_push")
class TestBroadcasterPushErrorHandling:
    """Tests for error handling in push notification integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_push_failure_does_not_break_websocket_broadcast(
        self,
        mock_push_sender: AsyncMock,
        mock_websocket: MagicMock,
        sample_critical_alert: Alert,
    ) -> None:
        """Test that push notification failure doesn't break WebSocket broadcast."""
        mock_push_sender.send_critical_alert.side_effect = Exception("Push failed")
        broadcaster = AlertBroadcaster(push_sender=mock_push_sender)

        # Add a WebSocket subscriber
        await broadcaster.subscribe(mock_websocket, "admin-user-001")

        # Should not raise, WebSocket should still receive the alert
        await broadcaster.broadcast_alert(sample_critical_alert)

        # WebSocket should still receive the alert
        mock_websocket.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_logs_success_count(
        self,
        mock_push_sender: AsyncMock,
        sample_critical_alert: Alert,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that successful push notification logs the count."""
        mock_push_sender.send_critical_alert.return_value = 5
        broadcaster = AlertBroadcaster(push_sender=mock_push_sender)

        import logging

        with caplog.at_level(logging.INFO):
            await broadcaster.broadcast_alert(sample_critical_alert)

        # Check that success was logged
        assert any(
            "push notification" in record.message.lower()
            and "5" in record.message
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_push_logs_failure_as_warning(
        self,
        mock_push_sender: AsyncMock,
        sample_critical_alert: Alert,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that push notification failure is logged as warning."""
        mock_push_sender.send_critical_alert.side_effect = Exception("Network error")
        broadcaster = AlertBroadcaster(push_sender=mock_push_sender)

        import logging

        with caplog.at_level(logging.WARNING):
            await broadcaster.broadcast_alert(sample_critical_alert)

        # Check that failure was logged as warning
        assert any(
            "failed" in record.message.lower()
            and "push" in record.message.lower()
            for record in caplog.records
        )


# =============================================================================
# Push + WebSocket Combined Tests
# =============================================================================


@pytest.mark.xdist_group(name="broadcaster_push")
class TestBroadcasterPushAndWebSocket:
    """Tests for combined push and WebSocket broadcasting."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_both_push_and_websocket_sent_for_critical(
        self,
        mock_push_sender: AsyncMock,
        mock_websocket: MagicMock,
        sample_critical_alert: Alert,
    ) -> None:
        """Test that both push and WebSocket are used for critical alerts."""
        broadcaster = AlertBroadcaster(push_sender=mock_push_sender)
        await broadcaster.subscribe(mock_websocket, "admin-user-001")

        await broadcaster.broadcast_alert(sample_critical_alert)

        # Both should be called
        mock_push_sender.send_critical_alert.assert_called_once()
        mock_websocket.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_sent_even_with_no_websocket_subscribers(
        self,
        mock_push_sender: AsyncMock,
        sample_critical_alert: Alert,
    ) -> None:
        """Test that push notifications work even with no WebSocket subscribers."""
        broadcaster = AlertBroadcaster(push_sender=mock_push_sender)
        # No WebSocket subscribers

        await broadcaster.broadcast_alert(sample_critical_alert)

        # Push should still be sent
        mock_push_sender.send_critical_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_sent_even_when_push_fails(
        self,
        mock_push_sender: AsyncMock,
        mock_websocket: MagicMock,
        sample_critical_alert: Alert,
    ) -> None:
        """Test that WebSocket broadcast works even when push fails."""
        mock_push_sender.send_critical_alert.side_effect = Exception("Push failed")
        broadcaster = AlertBroadcaster(push_sender=mock_push_sender)
        await broadcaster.subscribe(mock_websocket, "admin-user-001")

        await broadcaster.broadcast_alert(sample_critical_alert)

        # WebSocket should still work
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "alert"
        assert call_args["payload"]["alert_id"] == sample_critical_alert.alert_id
