"""
Unit tests for AlertBroadcaster core functionality.

Tests subscribe/unsubscribe, severity filtering, message conversion,
and broadcasting to multiple subscribers.

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from mcp_server_langgraph.alerts.broadcaster import (
    ALLOWED_SEVERITIES,
    AlertBroadcaster,
    AlertSubscriber,
    alert_to_message,
)
from mcp_server_langgraph.observability.query.interfaces import (
    Alert,
    AlertSeverity,
    AlertState,
)

pytestmark = pytest.mark.unit

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_websocket() -> AsyncMock:
    """Create a mock WebSocket connection."""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.fixture
def mock_push_sender() -> AsyncMock:
    """Create a mock PushNotificationSender."""
    sender = AsyncMock()
    sender.send_critical_alert = AsyncMock(return_value=5)
    return sender


@pytest.fixture
def broadcaster() -> AlertBroadcaster:
    """Create a broadcaster without push sender."""
    return AlertBroadcaster()


@pytest.fixture
def broadcaster_with_push(mock_push_sender: AsyncMock) -> AlertBroadcaster:
    """Create a broadcaster with push sender."""
    return AlertBroadcaster(push_sender=mock_push_sender)


@pytest.fixture
def sample_critical_alert() -> Alert:
    """Create a sample critical alert."""
    return Alert(
        alert_id="alert-001",
        name="HighCPUUsage",
        severity=AlertSeverity.CRITICAL,
        state=AlertState.FIRING,
        message="CPU usage exceeded 95%",
        labels={"service": "api-gateway", "instance": "pod-1"},
        annotations={"summary": "High CPU detected"},
        started_at=datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
        ended_at=None,
        generator_url="http://alertmanager/alert/001",
    )


@pytest.fixture
def sample_warning_alert() -> Alert:
    """Create a sample warning alert."""
    return Alert(
        alert_id="alert-002",
        name="MemoryPressure",
        severity=AlertSeverity.WARNING,
        state=AlertState.FIRING,
        message="Memory usage at 80%",
        labels={"service": "worker", "instance": "pod-2"},
        annotations={"summary": "Memory pressure detected"},
        started_at=datetime(2025, 1, 15, 11, 0, 0, tzinfo=UTC),
        ended_at=None,
        generator_url=None,
    )


@pytest.fixture
def sample_info_alert() -> Alert:
    """Create a sample info alert (should be filtered)."""
    return Alert(
        alert_id="alert-003",
        name="DeploymentComplete",
        severity=AlertSeverity.INFO,
        state=AlertState.RESOLVED,
        message="Deployment completed successfully",
        labels={"service": "api-gateway"},
        annotations={},
        started_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
        ended_at=datetime(2025, 1, 15, 12, 5, 0, tzinfo=UTC),
        generator_url=None,
    )


# =============================================================================
# Test: ALLOWED_SEVERITIES Constant
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="broadcaster_core")
class TestAllowedSeverities:
    """Test the ALLOWED_SEVERITIES constant."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_allowed_severities_contains_critical(self) -> None:
        """GIVEN ALLOWED_SEVERITIES WHEN checked THEN contains CRITICAL."""
        assert AlertSeverity.CRITICAL in ALLOWED_SEVERITIES

    def test_allowed_severities_contains_warning(self) -> None:
        """GIVEN ALLOWED_SEVERITIES WHEN checked THEN contains WARNING."""
        assert AlertSeverity.WARNING in ALLOWED_SEVERITIES

    def test_allowed_severities_excludes_info(self) -> None:
        """GIVEN ALLOWED_SEVERITIES WHEN checked THEN excludes INFO."""
        assert AlertSeverity.INFO not in ALLOWED_SEVERITIES

    def test_allowed_severities_excludes_error(self) -> None:
        """GIVEN ALLOWED_SEVERITIES WHEN checked THEN excludes ERROR."""
        assert AlertSeverity.ERROR not in ALLOWED_SEVERITIES

    def test_allowed_severities_count(self) -> None:
        """GIVEN ALLOWED_SEVERITIES WHEN counted THEN has exactly 2 items."""
        assert len(ALLOWED_SEVERITIES) == 2


# =============================================================================
# Test: alert_to_message Function
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="broadcaster_core")
class TestAlertToMessage:
    """Test the alert_to_message conversion function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alert_to_message_type(self, sample_critical_alert: Alert) -> None:
        """GIVEN an alert WHEN converted THEN message type is 'alert'."""
        message = alert_to_message(sample_critical_alert)
        assert message["type"] == "alert"

    def test_alert_to_message_has_payload(self, sample_critical_alert: Alert) -> None:
        """GIVEN an alert WHEN converted THEN has payload key."""
        message = alert_to_message(sample_critical_alert)
        assert "payload" in message

    def test_alert_to_message_payload_alert_id(self, sample_critical_alert: Alert) -> None:
        """GIVEN an alert WHEN converted THEN payload has alert_id."""
        message = alert_to_message(sample_critical_alert)
        assert message["payload"]["alert_id"] == "alert-001"

    def test_alert_to_message_payload_name(self, sample_critical_alert: Alert) -> None:
        """GIVEN an alert WHEN converted THEN payload has name."""
        message = alert_to_message(sample_critical_alert)
        assert message["payload"]["name"] == "HighCPUUsage"

    def test_alert_to_message_payload_severity(self, sample_critical_alert: Alert) -> None:
        """GIVEN an alert WHEN converted THEN payload has severity value."""
        message = alert_to_message(sample_critical_alert)
        assert message["payload"]["severity"] == "critical"

    def test_alert_to_message_payload_state(self, sample_critical_alert: Alert) -> None:
        """GIVEN an alert WHEN converted THEN payload has state value."""
        message = alert_to_message(sample_critical_alert)
        assert message["payload"]["state"] == "firing"

    def test_alert_to_message_payload_message(self, sample_critical_alert: Alert) -> None:
        """GIVEN an alert WHEN converted THEN payload has message."""
        message = alert_to_message(sample_critical_alert)
        assert message["payload"]["message"] == "CPU usage exceeded 95%"

    def test_alert_to_message_payload_labels(self, sample_critical_alert: Alert) -> None:
        """GIVEN an alert WHEN converted THEN payload has labels."""
        message = alert_to_message(sample_critical_alert)
        assert message["payload"]["labels"] == {
            "service": "api-gateway",
            "instance": "pod-1",
        }

    def test_alert_to_message_payload_annotations(self, sample_critical_alert: Alert) -> None:
        """GIVEN an alert WHEN converted THEN payload has annotations."""
        message = alert_to_message(sample_critical_alert)
        assert message["payload"]["annotations"] == {"summary": "High CPU detected"}

    def test_alert_to_message_payload_started_at(self, sample_critical_alert: Alert) -> None:
        """GIVEN an alert WHEN converted THEN payload has started_at ISO format."""
        message = alert_to_message(sample_critical_alert)
        assert message["payload"]["started_at"] == "2025-01-15T10:00:00+00:00"

    def test_alert_to_message_payload_ended_at_none(self, sample_critical_alert: Alert) -> None:
        """GIVEN an alert with no end WHEN converted THEN ended_at is None."""
        message = alert_to_message(sample_critical_alert)
        assert message["payload"]["ended_at"] is None

    def test_alert_to_message_payload_ended_at_set(self, sample_info_alert: Alert) -> None:
        """GIVEN a resolved alert WHEN converted THEN ended_at is set."""
        message = alert_to_message(sample_info_alert)
        assert message["payload"]["ended_at"] == "2025-01-15T12:05:00+00:00"

    def test_alert_to_message_payload_duration_ms(self, sample_info_alert: Alert) -> None:
        """GIVEN a resolved alert WHEN converted THEN duration_ms is set."""
        message = alert_to_message(sample_info_alert)
        # 5 minute duration (12:00 to 12:05) = 300000ms
        assert message["payload"]["duration_ms"] == pytest.approx(300000.0)

    def test_alert_to_message_payload_generator_url(self, sample_critical_alert: Alert) -> None:
        """GIVEN an alert with generator URL WHEN converted THEN URL is set."""
        message = alert_to_message(sample_critical_alert)
        assert message["payload"]["generator_url"] == "http://alertmanager/alert/001"

    def test_alert_to_message_payload_generator_url_none(self, sample_warning_alert: Alert) -> None:
        """GIVEN an alert without generator URL WHEN converted THEN URL is None."""
        message = alert_to_message(sample_warning_alert)
        assert message["payload"]["generator_url"] is None


# =============================================================================
# Test: AlertSubscriber Dataclass
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="broadcaster_core")
class TestAlertSubscriber:
    """Test the AlertSubscriber dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alert_subscriber_creation(self, mock_websocket: AsyncMock) -> None:
        """GIVEN connection and user_id WHEN creating subscriber THEN created."""
        subscriber = AlertSubscriber(
            connection=mock_websocket,
            user_id="admin@example.com",
        )
        assert subscriber.connection == mock_websocket
        assert subscriber.user_id == "admin@example.com"


# =============================================================================
# Test: AlertBroadcaster Subscribe/Unsubscribe
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="broadcaster_core")
class TestAlertBroadcasterSubscription:
    """Test AlertBroadcaster subscribe/unsubscribe functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_initial_subscriber_count_zero(self, broadcaster: AlertBroadcaster) -> None:
        """GIVEN new broadcaster WHEN checked THEN subscriber count is 0."""
        assert broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_subscribe_increments_count(self, broadcaster: AlertBroadcaster, mock_websocket: AsyncMock) -> None:
        """GIVEN broadcaster WHEN subscribing THEN count increments."""
        await broadcaster.subscribe(mock_websocket, "admin@example.com")
        assert broadcaster.subscriber_count == 1

    @pytest.mark.asyncio
    async def test_subscribe_multiple_connections(self, broadcaster: AlertBroadcaster) -> None:
        """GIVEN broadcaster WHEN subscribing multiple THEN count reflects all."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        await broadcaster.subscribe(ws1, "admin1@example.com")
        await broadcaster.subscribe(ws2, "admin2@example.com")
        await broadcaster.subscribe(ws3, "admin3@example.com")

        assert broadcaster.subscriber_count == 3

    @pytest.mark.asyncio
    async def test_unsubscribe_decrements_count(self, broadcaster: AlertBroadcaster, mock_websocket: AsyncMock) -> None:
        """GIVEN subscribed connection WHEN unsubscribing THEN count decrements."""
        await broadcaster.subscribe(mock_websocket, "admin@example.com")
        assert broadcaster.subscriber_count == 1

        await broadcaster.unsubscribe(mock_websocket)
        assert broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_connection(self, broadcaster: AlertBroadcaster, mock_websocket: AsyncMock) -> None:
        """GIVEN broadcaster WHEN unsubscribing unknown connection THEN no error."""
        # Should not raise any exception
        await broadcaster.unsubscribe(mock_websocket)
        assert broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_get_subscriber_count_for_user(self, broadcaster: AlertBroadcaster) -> None:
        """GIVEN broadcaster with subscriptions WHEN queried for user THEN correct count."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        await broadcaster.subscribe(ws1, "admin@example.com")
        await broadcaster.subscribe(ws2, "admin@example.com")
        await broadcaster.subscribe(ws3, "other@example.com")

        assert broadcaster.get_subscriber_count_for_user("admin@example.com") == 2
        assert broadcaster.get_subscriber_count_for_user("other@example.com") == 1
        assert broadcaster.get_subscriber_count_for_user("nobody@example.com") == 0


# =============================================================================
# Test: AlertBroadcaster Severity Filtering
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="broadcaster_core")
class TestAlertBroadcasterSeverityFiltering:
    """Test AlertBroadcaster severity filtering behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcast_critical_alert_sent(
        self,
        broadcaster: AlertBroadcaster,
        mock_websocket: AsyncMock,
        sample_critical_alert: Alert,
    ) -> None:
        """GIVEN critical alert WHEN broadcasting THEN sent to subscribers."""
        await broadcaster.subscribe(mock_websocket, "admin@example.com")
        await broadcaster.broadcast_alert(sample_critical_alert)

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "alert"
        assert call_args["payload"]["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_broadcast_warning_alert_sent(
        self,
        broadcaster: AlertBroadcaster,
        mock_websocket: AsyncMock,
        sample_warning_alert: Alert,
    ) -> None:
        """GIVEN warning alert WHEN broadcasting THEN sent to subscribers."""
        await broadcaster.subscribe(mock_websocket, "admin@example.com")
        await broadcaster.broadcast_alert(sample_warning_alert)

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["payload"]["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_broadcast_info_alert_filtered(
        self,
        broadcaster: AlertBroadcaster,
        mock_websocket: AsyncMock,
        sample_info_alert: Alert,
    ) -> None:
        """GIVEN info alert WHEN broadcasting THEN NOT sent (filtered)."""
        await broadcaster.subscribe(mock_websocket, "admin@example.com")
        await broadcaster.broadcast_alert(sample_info_alert)

        mock_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_error_alert_filtered(self, broadcaster: AlertBroadcaster, mock_websocket: AsyncMock) -> None:
        """GIVEN error severity alert WHEN broadcasting THEN NOT sent (filtered)."""
        error_alert = Alert(
            alert_id="alert-004",
            name="ErrorAlert",
            severity=AlertSeverity.ERROR,
            state=AlertState.FIRING,
            message="An error occurred",
            labels={},
            annotations={},
            started_at=datetime.now(UTC),
            ended_at=None,
            generator_url=None,
        )

        await broadcaster.subscribe(mock_websocket, "admin@example.com")
        await broadcaster.broadcast_alert(error_alert)

        mock_websocket.send_json.assert_not_called()


# =============================================================================
# Test: AlertBroadcaster broadcast_alert Multiple Subscribers
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="broadcaster_core")
class TestAlertBroadcasterMultipleSubscribers:
    """Test AlertBroadcaster broadcasting to multiple subscribers."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_subscribers(
        self, broadcaster: AlertBroadcaster, sample_critical_alert: Alert
    ) -> None:
        """GIVEN multiple subscribers WHEN broadcasting THEN all receive alert."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        await broadcaster.subscribe(ws1, "admin1@example.com")
        await broadcaster.subscribe(ws2, "admin2@example.com")
        await broadcaster.subscribe(ws3, "admin3@example.com")

        await broadcaster.broadcast_alert(sample_critical_alert)

        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()
        ws3.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_no_subscribers_no_error(
        self, broadcaster: AlertBroadcaster, sample_critical_alert: Alert
    ) -> None:
        """GIVEN no subscribers WHEN broadcasting THEN no error."""
        # Should not raise any exception
        await broadcaster.broadcast_alert(sample_critical_alert)


# =============================================================================
# Test: AlertBroadcaster Failed Connection Cleanup
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="broadcaster_core")
class TestAlertBroadcasterFailedConnections:
    """Test AlertBroadcaster cleanup of failed connections."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_failed_connection_removed(self, broadcaster: AlertBroadcaster, sample_critical_alert: Alert) -> None:
        """GIVEN failed connection WHEN broadcasting THEN removed from subscribers."""
        ws_good = AsyncMock()
        ws_bad = AsyncMock()
        ws_bad.send_json.side_effect = Exception("Connection closed")

        await broadcaster.subscribe(ws_good, "good@example.com")
        await broadcaster.subscribe(ws_bad, "bad@example.com")
        assert broadcaster.subscriber_count == 2

        await broadcaster.broadcast_alert(sample_critical_alert)

        # Failed connection should be removed
        assert broadcaster.subscriber_count == 1

    @pytest.mark.asyncio
    async def test_good_connections_unaffected_by_bad(
        self, broadcaster: AlertBroadcaster, sample_critical_alert: Alert
    ) -> None:
        """GIVEN mix of good/bad connections WHEN broadcasting THEN good ones work."""
        ws_good1 = AsyncMock()
        ws_bad = AsyncMock()
        ws_good2 = AsyncMock()
        ws_bad.send_json.side_effect = Exception("Connection closed")

        await broadcaster.subscribe(ws_good1, "good1@example.com")
        await broadcaster.subscribe(ws_bad, "bad@example.com")
        await broadcaster.subscribe(ws_good2, "good2@example.com")

        await broadcaster.broadcast_alert(sample_critical_alert)

        # Good connections should have received the alert
        ws_good1.send_json.assert_called_once()
        ws_good2.send_json.assert_called_once()


# =============================================================================
# Test: AlertBroadcaster broadcast_alert_update
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="broadcaster_core")
class TestAlertBroadcasterAlertUpdate:
    """Test AlertBroadcaster broadcast_alert_update functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcast_alert_update_includes_update_type(
        self,
        broadcaster: AlertBroadcaster,
        mock_websocket: AsyncMock,
        sample_critical_alert: Alert,
    ) -> None:
        """GIVEN alert update WHEN broadcasting THEN message has update_type."""
        await broadcaster.subscribe(mock_websocket, "admin@example.com")
        await broadcaster.broadcast_alert_update(sample_critical_alert, "resolved")

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["update_type"] == "resolved"

    @pytest.mark.asyncio
    async def test_broadcast_alert_update_default_type(
        self,
        broadcaster: AlertBroadcaster,
        mock_websocket: AsyncMock,
        sample_critical_alert: Alert,
    ) -> None:
        """GIVEN alert update without type WHEN broadcasting THEN default is 'update'."""
        await broadcaster.subscribe(mock_websocket, "admin@example.com")
        await broadcaster.broadcast_alert_update(sample_critical_alert)

        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["update_type"] == "update"

    @pytest.mark.asyncio
    async def test_broadcast_alert_update_severity_filtered(
        self,
        broadcaster: AlertBroadcaster,
        mock_websocket: AsyncMock,
        sample_info_alert: Alert,
    ) -> None:
        """GIVEN info alert update WHEN broadcasting THEN filtered out."""
        await broadcaster.subscribe(mock_websocket, "admin@example.com")
        await broadcaster.broadcast_alert_update(sample_info_alert, "resolved")

        mock_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_alert_update_removes_failed(
        self, broadcaster: AlertBroadcaster, sample_critical_alert: Alert
    ) -> None:
        """GIVEN failed connection WHEN broadcasting update THEN removed."""
        ws_good = AsyncMock()
        ws_bad = AsyncMock()
        ws_bad.send_json.side_effect = Exception("Connection closed")

        await broadcaster.subscribe(ws_good, "good@example.com")
        await broadcaster.subscribe(ws_bad, "bad@example.com")
        assert broadcaster.subscriber_count == 2

        await broadcaster.broadcast_alert_update(sample_critical_alert, "silenced")

        assert broadcaster.subscriber_count == 1


# =============================================================================
# Test: AlertBroadcaster Push Notification Integration
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="broadcaster_core")
class TestAlertBroadcasterPushIntegration:
    """Test AlertBroadcaster push notification integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_critical_alert_triggers_push(
        self,
        broadcaster_with_push: AlertBroadcaster,
        mock_push_sender: AsyncMock,
        sample_critical_alert: Alert,
    ) -> None:
        """GIVEN critical alert with push sender WHEN broadcasting THEN push sent."""
        await broadcaster_with_push.broadcast_alert(sample_critical_alert)

        mock_push_sender.send_critical_alert.assert_called_once_with(sample_critical_alert)

    @pytest.mark.asyncio
    async def test_warning_alert_no_push(
        self,
        broadcaster_with_push: AlertBroadcaster,
        mock_push_sender: AsyncMock,
        sample_warning_alert: Alert,
    ) -> None:
        """GIVEN warning alert with push sender WHEN broadcasting THEN no push."""
        await broadcaster_with_push.broadcast_alert(sample_warning_alert)

        mock_push_sender.send_critical_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_failure_does_not_block_websocket(
        self,
        broadcaster_with_push: AlertBroadcaster,
        mock_push_sender: AsyncMock,
        mock_websocket: AsyncMock,
        sample_critical_alert: Alert,
    ) -> None:
        """GIVEN push failure WHEN broadcasting THEN WebSocket still works."""
        mock_push_sender.send_critical_alert.side_effect = Exception("Push failed")

        await broadcaster_with_push.subscribe(mock_websocket, "admin@example.com")
        await broadcaster_with_push.broadcast_alert(sample_critical_alert)

        # WebSocket should still receive the alert
        mock_websocket.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_push_sender_no_error(self, broadcaster: AlertBroadcaster, sample_critical_alert: Alert) -> None:
        """GIVEN no push sender WHEN broadcasting critical THEN no error."""
        # Should not raise any exception
        await broadcaster.broadcast_alert(sample_critical_alert)


# =============================================================================
# Test: AlertBroadcaster AlertRouter Integration
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="broadcaster_router_integration")
class TestAlertBroadcasterRouterIntegration:
    """Test AlertBroadcaster integration with AlertRouter."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcaster_with_router_routes_alert(
        self,
        mock_websocket: AsyncMock,
        sample_critical_alert: Alert,
    ) -> None:
        """GIVEN broadcaster with router WHEN broadcasting THEN alert is routed."""
        from mcp_server_langgraph.alerts.routing import AlertRouter, RoutingResult

        mock_router = AsyncMock(spec=AlertRouter)
        mock_router.route_async = AsyncMock(
            return_value=RoutingResult(
                tenant_id="tenant-1",
                routed=True,
                target_tenants=["tenant-1"],
                subscribed_users=["admin@example.com"],
                notification_channels={"admin@example.com": ["push", "email"]},
            )
        )

        broadcaster = AlertBroadcaster(router=mock_router)
        await broadcaster.subscribe(mock_websocket, "admin@example.com")
        await broadcaster.broadcast_alert(sample_critical_alert)

        # Router should have been called
        mock_router.route_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcaster_with_router_filters_by_subscription(
        self,
        sample_critical_alert: Alert,
    ) -> None:
        """GIVEN router with subscriptions WHEN broadcasting THEN only subscribed users receive."""
        from mcp_server_langgraph.alerts.routing import AlertRouter, RoutingResult

        mock_router = AsyncMock(spec=AlertRouter)
        mock_router.route_async = AsyncMock(
            return_value=RoutingResult(
                tenant_id="tenant-1",
                routed=True,
                target_tenants=["tenant-1"],
                subscribed_users=["subscribed@example.com"],  # Only this user subscribed
                notification_channels={},
            )
        )

        broadcaster = AlertBroadcaster(router=mock_router)

        ws_subscribed = AsyncMock()
        ws_not_subscribed = AsyncMock()

        await broadcaster.subscribe(ws_subscribed, "subscribed@example.com")
        await broadcaster.subscribe(ws_not_subscribed, "not-subscribed@example.com")

        await broadcaster.broadcast_alert(sample_critical_alert)

        # Only subscribed user should receive
        ws_subscribed.send_json.assert_called_once()
        ws_not_subscribed.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcaster_with_router_respects_filtered_alerts(
        self,
        mock_websocket: AsyncMock,
        sample_critical_alert: Alert,
    ) -> None:
        """GIVEN router that filters alert WHEN broadcasting THEN alert not sent."""
        from mcp_server_langgraph.alerts.routing import AlertRouter, RoutingResult

        mock_router = AsyncMock(spec=AlertRouter)
        mock_router.route_async = AsyncMock(
            return_value=RoutingResult(
                tenant_id="tenant-1",
                routed=False,  # Alert was filtered by routing rules
                filtered=True,
                target_tenants=[],
            )
        )

        broadcaster = AlertBroadcaster(router=mock_router)
        await broadcaster.subscribe(mock_websocket, "admin@example.com")
        await broadcaster.broadcast_alert(sample_critical_alert)

        # Alert should not be sent due to routing filter
        mock_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcaster_without_router_broadcasts_to_all(
        self,
        sample_critical_alert: Alert,
    ) -> None:
        """GIVEN broadcaster without router WHEN broadcasting THEN all subscribers receive."""
        broadcaster = AlertBroadcaster()  # No router

        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await broadcaster.subscribe(ws1, "admin1@example.com")
        await broadcaster.subscribe(ws2, "admin2@example.com")

        await broadcaster.broadcast_alert(sample_critical_alert)

        # Both should receive (no filtering without router)
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcaster_router_failure_falls_back_to_all(
        self,
        sample_critical_alert: Alert,
    ) -> None:
        """GIVEN router that fails WHEN broadcasting THEN falls back to all subscribers."""
        from mcp_server_langgraph.alerts.routing import AlertRouter

        mock_router = AsyncMock(spec=AlertRouter)
        mock_router.route_async = AsyncMock(side_effect=Exception("Router error"))

        broadcaster = AlertBroadcaster(router=mock_router)

        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await broadcaster.subscribe(ws1, "admin1@example.com")
        await broadcaster.subscribe(ws2, "admin2@example.com")

        await broadcaster.broadcast_alert(sample_critical_alert)

        # Both should receive (fallback behavior)
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcaster_includes_routing_metadata_in_message(
        self,
        mock_websocket: AsyncMock,
        sample_critical_alert: Alert,
    ) -> None:
        """GIVEN routing result WHEN broadcasting THEN message includes routing metadata."""
        from mcp_server_langgraph.alerts.routing import AlertRouter, RoutingResult

        mock_router = AsyncMock(spec=AlertRouter)
        mock_router.route_async = AsyncMock(
            return_value=RoutingResult(
                tenant_id="tenant-1",
                routed=True,
                target_tenants=["tenant-1", "tenant-2"],
                subscribed_users=["admin@example.com"],
                notification_channels={"admin@example.com": ["push"]},
            )
        )

        broadcaster = AlertBroadcaster(router=mock_router)
        await broadcaster.subscribe(mock_websocket, "admin@example.com")
        await broadcaster.broadcast_alert(sample_critical_alert)

        call_args = mock_websocket.send_json.call_args[0][0]
        # Check that routing metadata is included
        assert "routing" in call_args or call_args["payload"].get("tenant_id") is not None


# =============================================================================
# Test Alert Model Consistency (started_at handling)
# =============================================================================


@pytest.mark.xdist_group(name="test_broadcaster_started_at")
class TestAlertStartedAtConsistency:
    """Tests for handling optional started_at in Alert models.

    Ensures that conversions from DB models (where started_at is optional)
    to routing/correlation models (where started_at is required) handle
    None values gracefully by providing sensible defaults.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_convert_to_routing_alert_with_none_started_at(self) -> None:
        """
        GIVEN an Alert with started_at=None
        WHEN converted to RoutingAlert
        THEN started_at should have a sensible default (not None)
        """
        alert = Alert(
            alert_id="alert-123",
            name="Test Alert",
            severity=AlertSeverity.WARNING,
            state=AlertState.FIRING,
            labels={"service": "test"},
            message="Test message",
            started_at=None,  # Explicitly None
        )

        broadcaster = AlertBroadcaster()
        routing_alert = broadcaster._convert_to_routing_alert(alert)

        # started_at should be a datetime, not None
        assert routing_alert.started_at is not None
        assert isinstance(routing_alert.started_at, datetime)

    def test_convert_to_routing_alert_preserves_started_at(self) -> None:
        """
        GIVEN an Alert with a valid started_at
        WHEN converted to RoutingAlert
        THEN started_at should be preserved
        """
        original_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        alert = Alert(
            alert_id="alert-123",
            name="Test Alert",
            severity=AlertSeverity.CRITICAL,
            state=AlertState.FIRING,
            labels={"service": "test"},
            message="Critical message",
            started_at=original_time,
        )

        broadcaster = AlertBroadcaster()
        routing_alert = broadcaster._convert_to_routing_alert(alert)

        assert routing_alert.started_at == original_time
