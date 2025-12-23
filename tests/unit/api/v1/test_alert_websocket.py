"""
Alert WebSocket Endpoint Unit Tests.

Tests for the Alert WebSocket handler following TDD methodology.
Tests the WebSocket endpoint that provides real-time alert streaming to Admin users.

Features tested:
- JWT authentication (query param and header)
- Admin role authorization
- Subscribe/unsubscribe to alert stream
- Severity filtering (critical/warning only)
- Alert message format validation
- Ping/pong keepalive
- Connection lifecycle management

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.observability.query.interfaces import (
    Alert,
    AlertSeverity,
    AlertState,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.websocket,
    pytest.mark.alerts,
]


@pytest.mark.xdist_group(name="test_alert_websocket")
class TestAlertWebSocketEndpoint:
    """Tests for Alert WebSocket endpoint existence and configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alert_websocket_router_exists(self) -> None:
        """
        GIVEN the alert websocket module
        WHEN importing the router
        THEN should export alert_websocket_router.
        """
        from mcp_server_langgraph.api.v1.alert_websocket import alert_websocket_router

        assert alert_websocket_router is not None

    def test_websocket_endpoint_exists(self) -> None:
        """
        GIVEN the alert websocket router
        WHEN checking routes
        THEN should have /alerts websocket endpoint.
        """
        from mcp_server_langgraph.api.v1.alert_websocket import alert_websocket_router

        routes = [r for r in alert_websocket_router.routes]
        websocket_routes = [r for r in routes if hasattr(r, "path") and "alerts" in r.path]
        assert len(websocket_routes) > 0, "Should have /alerts websocket route"

    def test_broadcaster_getter_exists(self) -> None:
        """
        GIVEN the alert websocket module
        WHEN importing broadcaster getter
        THEN should export get_alert_broadcaster function.
        """
        from mcp_server_langgraph.api.v1.alert_websocket import get_alert_broadcaster

        assert get_alert_broadcaster is not None
        assert callable(get_alert_broadcaster)

    def test_broadcaster_setter_exists(self) -> None:
        """
        GIVEN the alert websocket module
        WHEN importing broadcaster setter
        THEN should export set_alert_broadcaster function.
        """
        from mcp_server_langgraph.api.v1.alert_websocket import set_alert_broadcaster

        assert set_alert_broadcaster is not None
        assert callable(set_alert_broadcaster)


@pytest.mark.xdist_group(name="test_alert_websocket")
class TestAlertWebSocketAuthentication:
    """Tests for Alert WebSocket authentication."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_validate_websocket_auth_with_query_token(self) -> None:
        """
        GIVEN a WebSocket connection with token in query params
        WHEN validating authentication
        THEN should extract and validate the token.
        """
        from mcp_server_langgraph.api.v1.alert_websocket import (
            validate_alert_websocket_auth,
        )

        mock_websocket = MagicMock()
        mock_websocket.query_params.get.return_value = "valid-jwt-token"
        mock_websocket.headers.get.return_value = ""

        mock_auth_middleware = AsyncMock()
        mock_auth_middleware.verify_token.return_value = MagicMock(
            valid=True,
            payload={
                "sub": "user-123",
                "preferred_username": "admin",
                "email": "admin@example.com",
                "realm_access": {"roles": ["admin"]},
            },
        )
        mock_websocket.app.state.auth_middleware = mock_auth_middleware

        user = await validate_alert_websocket_auth(mock_websocket)

        assert user is not None
        # user_id is formatted as "user:<username>" by extract_user_from_jwt_payload
        assert user.get("user_id") == "user:admin"
        mock_auth_middleware.verify_token.assert_called_once_with("valid-jwt-token")

    @pytest.mark.asyncio
    async def test_validate_websocket_auth_with_header_token(self) -> None:
        """
        GIVEN a WebSocket connection with token in Authorization header
        WHEN validating authentication
        THEN should extract token from Bearer header.
        """
        from mcp_server_langgraph.api.v1.alert_websocket import (
            validate_alert_websocket_auth,
        )

        mock_websocket = MagicMock()
        mock_websocket.query_params.get.return_value = None
        mock_websocket.headers.get.return_value = "Bearer header-jwt-token"

        mock_auth_middleware = AsyncMock()
        mock_auth_middleware.verify_token.return_value = MagicMock(
            valid=True,
            payload={
                "sub": "user-456",
                "preferred_username": "admin2",
                "email": "admin2@example.com",
                "realm_access": {"roles": ["admin"]},
            },
        )
        mock_websocket.app.state.auth_middleware = mock_auth_middleware

        user = await validate_alert_websocket_auth(mock_websocket)

        assert user is not None
        # user_id is formatted as "user:<username>" by extract_user_from_jwt_payload
        assert user.get("user_id") == "user:admin2"
        mock_auth_middleware.verify_token.assert_called_once_with("header-jwt-token")

    @pytest.mark.asyncio
    async def test_validate_websocket_auth_no_token_returns_none(self) -> None:
        """
        GIVEN a WebSocket connection with no token
        WHEN validating authentication
        THEN should return None.
        """
        from mcp_server_langgraph.api.v1.alert_websocket import (
            validate_alert_websocket_auth,
        )

        mock_websocket = MagicMock()
        mock_websocket.query_params.get.return_value = None
        mock_websocket.headers.get.return_value = ""

        user = await validate_alert_websocket_auth(mock_websocket)

        assert user is None

    @pytest.mark.asyncio
    async def test_validate_websocket_auth_invalid_token_returns_none(self) -> None:
        """
        GIVEN a WebSocket connection with invalid token
        WHEN validating authentication
        THEN should return None.
        """
        from mcp_server_langgraph.api.v1.alert_websocket import (
            validate_alert_websocket_auth,
        )

        mock_websocket = MagicMock()
        mock_websocket.query_params.get.return_value = "invalid-token"
        mock_websocket.headers.get.return_value = ""

        mock_auth_middleware = AsyncMock()
        mock_auth_middleware.verify_token.return_value = MagicMock(
            valid=False,
            payload=None,
            error="Invalid token",
        )
        mock_websocket.app.state.auth_middleware = mock_auth_middleware

        user = await validate_alert_websocket_auth(mock_websocket)

        assert user is None

    @pytest.mark.asyncio
    async def test_validate_websocket_auth_query_param_takes_precedence(self) -> None:
        """
        GIVEN a WebSocket with both query param and header token
        WHEN validating authentication
        THEN should use query param token.
        """
        from mcp_server_langgraph.api.v1.alert_websocket import (
            validate_alert_websocket_auth,
        )

        mock_websocket = MagicMock()
        mock_websocket.query_params.get.return_value = "query-token"
        mock_websocket.headers.get.return_value = "Bearer header-token"

        mock_auth_middleware = AsyncMock()
        mock_auth_middleware.verify_token.return_value = MagicMock(
            valid=True,
            payload={
                "sub": "user-query",
                "preferred_username": "admin",
                "email": "admin@example.com",
                "realm_access": {"roles": ["admin"]},
            },
        )
        mock_websocket.app.state.auth_middleware = mock_auth_middleware

        user = await validate_alert_websocket_auth(mock_websocket)

        assert user is not None
        mock_auth_middleware.verify_token.assert_called_once_with("query-token")


@pytest.mark.xdist_group(name="test_alert_websocket")
class TestAlertWebSocketAdminAuthorization:
    """Tests for Alert WebSocket admin-only authorization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_admin_role_required_for_alerts(self) -> None:
        """
        GIVEN a WebSocket connection
        WHEN checking admin authorization
        THEN should require admin role.
        """
        from mcp_server_langgraph.api.v1.alert_websocket import is_admin_user

        # Admin user should pass
        admin_user = {"roles": ["admin"]}
        assert is_admin_user(admin_user) is True

        # Non-admin should fail
        regular_user = {"roles": ["user"]}
        assert is_admin_user(regular_user) is False

        # Empty roles should fail
        no_roles_user = {"roles": []}
        assert is_admin_user(no_roles_user) is False

        # No roles key should fail
        no_roles_key: dict[str, list[str]] = {}
        assert is_admin_user(no_roles_key) is False

    @pytest.mark.asyncio
    async def test_platform_admin_role_also_allowed(self) -> None:
        """
        GIVEN a user with platform_admin role
        WHEN checking admin authorization
        THEN should be allowed.
        """
        from mcp_server_langgraph.api.v1.alert_websocket import is_admin_user

        platform_admin = {"roles": ["platform_admin"]}
        assert is_admin_user(platform_admin) is True


@pytest.mark.xdist_group(name="test_alert_websocket")
class TestAlertBroadcaster:
    """Tests for Alert broadcaster service."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_broadcaster_initialization(self) -> None:
        """
        GIVEN the AlertBroadcaster class
        WHEN creating a new instance
        THEN should initialize with empty subscribers.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        broadcaster = AlertBroadcaster()

        assert broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_broadcaster_subscribe(self) -> None:
        """
        GIVEN an AlertBroadcaster instance
        WHEN subscribing a connection
        THEN should add to subscribers.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        broadcaster = AlertBroadcaster()
        mock_connection = AsyncMock()

        await broadcaster.subscribe(mock_connection, user_id="admin-123")

        assert broadcaster.subscriber_count == 1

    @pytest.mark.asyncio
    async def test_broadcaster_unsubscribe(self) -> None:
        """
        GIVEN an AlertBroadcaster with a subscriber
        WHEN unsubscribing the connection
        THEN should remove from subscribers.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        broadcaster = AlertBroadcaster()
        mock_connection = AsyncMock()

        await broadcaster.subscribe(mock_connection, user_id="admin-123")
        assert broadcaster.subscriber_count == 1

        await broadcaster.unsubscribe(mock_connection)
        assert broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_broadcaster_broadcast_alert(self) -> None:
        """
        GIVEN an AlertBroadcaster with subscribers
        WHEN broadcasting an alert
        THEN should send to all subscribers.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        broadcaster = AlertBroadcaster()
        mock_connection1 = AsyncMock()
        mock_connection2 = AsyncMock()

        await broadcaster.subscribe(mock_connection1, user_id="admin-1")
        await broadcaster.subscribe(mock_connection2, user_id="admin-2")

        alert = Alert(
            alert_id="alert-001",
            name="CircuitBreakerOpen",
            severity=AlertSeverity.CRITICAL,
            state=AlertState.FIRING,
            message="Redis circuit breaker is open",
            labels={"service": "redis"},
            started_at=datetime.now(UTC),
        )

        await broadcaster.broadcast_alert(alert)

        mock_connection1.send_json.assert_called_once()
        mock_connection2.send_json.assert_called_once()

        # Verify message format
        sent_data = mock_connection1.send_json.call_args[0][0]
        assert sent_data["type"] == "alert"
        assert sent_data["payload"]["alert_id"] == "alert-001"
        assert sent_data["payload"]["severity"] == "critical"
        assert sent_data["payload"]["state"] == "firing"

    @pytest.mark.asyncio
    async def test_broadcaster_filters_info_severity(self) -> None:
        """
        GIVEN an AlertBroadcaster
        WHEN broadcasting an info severity alert
        THEN should NOT send (only critical/warning allowed).
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        broadcaster = AlertBroadcaster()
        mock_connection = AsyncMock()

        await broadcaster.subscribe(mock_connection, user_id="admin-1")

        alert = Alert(
            alert_id="alert-info",
            name="InfoAlert",
            severity=AlertSeverity.INFO,
            state=AlertState.FIRING,
            message="Informational message",
        )

        await broadcaster.broadcast_alert(alert)

        mock_connection.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcaster_allows_warning_severity(self) -> None:
        """
        GIVEN an AlertBroadcaster
        WHEN broadcasting a warning severity alert
        THEN should send to subscribers.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        broadcaster = AlertBroadcaster()
        mock_connection = AsyncMock()

        await broadcaster.subscribe(mock_connection, user_id="admin-1")

        alert = Alert(
            alert_id="alert-warn",
            name="WarningAlert",
            severity=AlertSeverity.WARNING,
            state=AlertState.FIRING,
            message="Warning message",
        )

        await broadcaster.broadcast_alert(alert)

        mock_connection.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcaster_allows_critical_severity(self) -> None:
        """
        GIVEN an AlertBroadcaster
        WHEN broadcasting a critical severity alert
        THEN should send to subscribers.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        broadcaster = AlertBroadcaster()
        mock_connection = AsyncMock()

        await broadcaster.subscribe(mock_connection, user_id="admin-1")

        alert = Alert(
            alert_id="alert-crit",
            name="CriticalAlert",
            severity=AlertSeverity.CRITICAL,
            state=AlertState.FIRING,
            message="Critical message",
        )

        await broadcaster.broadcast_alert(alert)

        mock_connection.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcaster_removes_failed_connections(self) -> None:
        """
        GIVEN an AlertBroadcaster with subscribers
        WHEN a connection fails during broadcast
        THEN should remove the failed connection.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        broadcaster = AlertBroadcaster()

        # One good connection, one that will fail
        good_connection = AsyncMock()
        bad_connection = AsyncMock()
        bad_connection.send_json.side_effect = Exception("Connection closed")

        await broadcaster.subscribe(good_connection, user_id="admin-1")
        await broadcaster.subscribe(bad_connection, user_id="admin-2")
        assert broadcaster.subscriber_count == 2

        alert = Alert(
            alert_id="alert-test",
            name="TestAlert",
            severity=AlertSeverity.CRITICAL,
            state=AlertState.FIRING,
            message="Test message",
        )

        await broadcaster.broadcast_alert(alert)

        # Good connection should have received the message
        good_connection.send_json.assert_called_once()

        # Bad connection should be removed
        assert broadcaster.subscriber_count == 1


@pytest.mark.xdist_group(name="test_alert_websocket")
class TestAlertMessageFormat:
    """Tests for Alert message format."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alert_to_websocket_message_format(self) -> None:
        """
        GIVEN an Alert dataclass
        WHEN converting to WebSocket message format
        THEN should produce valid JSON structure.
        """
        from mcp_server_langgraph.alerts.broadcaster import alert_to_message

        alert = Alert(
            alert_id="alert-001",
            name="CircuitBreakerOpen",
            severity=AlertSeverity.CRITICAL,
            state=AlertState.FIRING,
            message="Redis circuit breaker is open",
            labels={"service": "redis", "provider": "infrastructure"},
            annotations={
                "summary": "Circuit breaker opened for Redis",
                "runbook_url": "https://runbooks.example.com/cb-redis",
            },
            started_at=datetime(2025, 12, 20, 10, 30, 0, tzinfo=UTC),
        )

        message = alert_to_message(alert)

        assert message["type"] == "alert"
        assert message["payload"]["alert_id"] == "alert-001"
        assert message["payload"]["name"] == "CircuitBreakerOpen"
        assert message["payload"]["severity"] == "critical"
        assert message["payload"]["state"] == "firing"
        assert message["payload"]["message"] == "Redis circuit breaker is open"
        assert message["payload"]["labels"]["service"] == "redis"
        assert "runbook_url" in message["payload"]["annotations"]
        assert message["payload"]["started_at"] is not None

    def test_alert_to_websocket_message_includes_duration(self) -> None:
        """
        GIVEN an Alert with start and end time
        WHEN converting to WebSocket message
        THEN should include duration_ms.
        """
        from mcp_server_langgraph.alerts.broadcaster import alert_to_message

        start = datetime(2025, 12, 20, 10, 0, 0, tzinfo=UTC)
        end = datetime(2025, 12, 20, 10, 5, 0, tzinfo=UTC)  # 5 minutes later

        alert = Alert(
            alert_id="alert-002",
            name="ResolvedAlert",
            severity=AlertSeverity.WARNING,
            state=AlertState.RESOLVED,
            message="Issue resolved",
            started_at=start,
            ended_at=end,
        )

        message = alert_to_message(alert)

        assert message["payload"]["duration_ms"] == 300000  # 5 minutes in ms


@pytest.mark.xdist_group(name="test_alert_websocket")
class TestAlertWebSocketPingPong:
    """Tests for WebSocket ping/pong keepalive."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_ping_message_receives_pong(self) -> None:
        """
        GIVEN a connected alert WebSocket
        WHEN client sends ping
        THEN should receive pong response.
        """
        from mcp_server_langgraph.api.v1.alert_websocket import handle_client_message

        mock_websocket = AsyncMock()

        result = await handle_client_message(mock_websocket, {"type": "ping"})

        assert result == {"type": "pong"}


@pytest.mark.xdist_group(name="test_alert_websocket")
class TestAlertWebSocketIntegration:
    """Integration-style tests for full WebSocket flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_full_connection_lifecycle(self) -> None:
        """
        GIVEN a valid admin user
        WHEN connecting to alert WebSocket
        THEN should complete full lifecycle: connect -> receive alerts -> disconnect.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        broadcaster = AlertBroadcaster()
        mock_websocket = AsyncMock()

        # Simulate connection lifecycle
        await broadcaster.subscribe(mock_websocket, user_id="admin-123")
        assert broadcaster.subscriber_count == 1

        # Simulate receiving an alert
        alert = Alert(
            alert_id="lifecycle-test",
            name="TestAlert",
            severity=AlertSeverity.CRITICAL,
            state=AlertState.FIRING,
            message="Lifecycle test",
        )
        await broadcaster.broadcast_alert(alert)
        mock_websocket.send_json.assert_called()

        # Disconnect
        await broadcaster.unsubscribe(mock_websocket)
        assert broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_multiple_concurrent_subscribers(self) -> None:
        """
        GIVEN multiple admin connections
        WHEN an alert is broadcast
        THEN all should receive the alert.
        """
        from mcp_server_langgraph.alerts.broadcaster import AlertBroadcaster

        broadcaster = AlertBroadcaster()

        connections = [AsyncMock() for _ in range(5)]
        for i, conn in enumerate(connections):
            await broadcaster.subscribe(conn, user_id=f"admin-{i}")

        assert broadcaster.subscriber_count == 5

        alert = Alert(
            alert_id="multi-test",
            name="MultiTest",
            severity=AlertSeverity.WARNING,
            state=AlertState.FIRING,
            message="Multiple subscribers test",
        )

        await broadcaster.broadcast_alert(alert)

        for conn in connections:
            conn.send_json.assert_called_once()
