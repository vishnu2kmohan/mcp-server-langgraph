"""
Tests for Notification WebSocket Streaming.

TDD RED phase: These tests define expected behavior for real-time
notification streaming via WebSocket.

The WebSocket endpoint should:
- Stream notifications in real-time to connected clients
- Send notifications in format: { type: "notification", payload: { type, title, message } }
- Require authentication via JWT token
- Support multiple subscribers (broadcast pattern)
- Handle connection lifecycle properly
"""

import gc
from datetime import UTC, datetime, timedelta
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from fastapi import FastAPI

pytestmark = pytest.mark.api

# Test JWT secret for unit tests
TEST_JWT_SECRET = "test-jwt-secret-for-websocket-unit-tests"


def _make_authenticated_user() -> dict[str, Any]:
    """Create authenticated user for access."""
    return {
        "user_id": "user-001",
        "username": "testuser",
        "email": "user@example.com",
        "roles": ["user"],
    }


def _make_admin_user() -> dict[str, Any]:
    """Create admin user for access."""
    return {
        "user_id": "admin-001",
        "username": "admin",
        "email": "admin@example.com",
        "roles": ["admin"],
    }


@pytest.fixture
def notification_ws_app() -> Generator[tuple[FastAPI, AsyncMock], None, None]:
    """Create test app with mocked notification broadcaster and authenticated user."""
    from mcp_server_langgraph.api.v1.notification_websocket import (
        router,
        set_notification_broadcaster,
    )
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(router, prefix="/ws")

    # Override get_current_user to return authenticated user
    async def get_auth_user() -> dict[str, Any]:
        return _make_authenticated_user()

    app.dependency_overrides[get_current_user] = get_auth_user

    mock_broadcaster = AsyncMock()  # noqa: async-mock-config
    set_notification_broadcaster(mock_broadcaster)

    yield app, mock_broadcaster

    # Cleanup
    set_notification_broadcaster(None)
    app.dependency_overrides.clear()


@pytest.fixture
def notification_ws_app_unauthenticated() -> Generator[tuple[FastAPI, AsyncMock], None, None]:
    """Create test app without authentication."""
    from mcp_server_langgraph.api.v1.notification_websocket import (
        router,
        set_notification_broadcaster,
    )
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(router, prefix="/ws")

    # Override get_current_user to return None (unauthenticated)
    async def get_no_user() -> None:
        return None

    app.dependency_overrides[get_current_user] = get_no_user

    mock_broadcaster = AsyncMock()  # noqa: async-mock-config
    set_notification_broadcaster(mock_broadcaster)

    yield app, mock_broadcaster

    # Cleanup
    set_notification_broadcaster(None)
    app.dependency_overrides.clear()


@pytest.mark.api
@pytest.mark.xdist_group(name="notification_websocket")
class TestNotificationWebSocketEndpoint:
    """Tests for /ws/notifications WebSocket endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_endpoint_exists(self, notification_ws_app: tuple) -> None:
        """
        GIVEN FastAPI app with notification WebSocket router
        WHEN checking routes
        THEN WebSocket endpoint exists at /ws/notifications.
        """
        app, _ = notification_ws_app

        routes = [route.path for route in app.routes]
        assert "/ws/notifications" in routes


@pytest.mark.api
@pytest.mark.xdist_group(name="notification_websocket")
class TestNotificationBroadcaster:
    """Tests for NotificationBroadcaster."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_broadcaster_add_subscriber(self) -> None:
        """
        GIVEN a broadcaster
        WHEN adding a subscriber
        THEN subscriber is registered.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()
        mock_ws = AsyncMock()  # noqa: async-mock-config

        await broadcaster.subscribe(mock_ws)

        assert broadcaster.subscriber_count == 1

    @pytest.mark.asyncio
    async def test_broadcaster_remove_subscriber(self) -> None:
        """
        GIVEN a broadcaster with subscriber
        WHEN removing subscriber
        THEN subscriber is unregistered.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()
        mock_ws = AsyncMock()  # noqa: async-mock-config

        await broadcaster.subscribe(mock_ws)
        await broadcaster.unsubscribe(mock_ws)

        assert broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_broadcaster_broadcast_notification(self) -> None:
        """
        GIVEN subscribers
        WHEN broadcasting notification
        THEN all subscribers receive notification in correct format.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()
        mock_ws1 = AsyncMock()  # noqa: async-mock-config
        mock_ws2 = AsyncMock()  # noqa: async-mock-config

        await broadcaster.subscribe(mock_ws1)
        await broadcaster.subscribe(mock_ws2)

        # Broadcast a notification
        await broadcaster.broadcast(
            notification_type="success",
            title="Session Created",
            message="Your session has been created successfully.",
        )

        # Verify both subscribers received the notification in correct format
        expected_message = {
            "type": "notification",
            "payload": {
                "type": "success",
                "title": "Session Created",
                "message": "Your session has been created successfully.",
            },
        }
        mock_ws1.send_json.assert_called_once_with(expected_message)
        mock_ws2.send_json.assert_called_once_with(expected_message)

    @pytest.mark.asyncio
    async def test_broadcaster_broadcast_with_action(self) -> None:
        """
        GIVEN subscribers
        WHEN broadcasting notification with action
        THEN all subscribers receive notification with action.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()
        mock_ws = AsyncMock()  # noqa: async-mock-config

        await broadcaster.subscribe(mock_ws)

        # Broadcast a notification with action
        await broadcaster.broadcast(
            notification_type="info",
            title="New Workflow Shared",
            message="Alice shared a workflow with you.",
            action={"label": "View Workflow", "url": "/workflows/123"},
        )

        # Verify notification includes action
        expected_message = {
            "type": "notification",
            "payload": {
                "type": "info",
                "title": "New Workflow Shared",
                "message": "Alice shared a workflow with you.",
                "action": {"label": "View Workflow", "url": "/workflows/123"},
            },
        }
        mock_ws.send_json.assert_called_once_with(expected_message)

    @pytest.mark.asyncio
    async def test_broadcaster_handles_disconnected_subscriber(self) -> None:
        """
        GIVEN a subscriber that disconnects
        WHEN broadcasting
        THEN handles error gracefully and removes subscriber.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()
        mock_ws = AsyncMock()  # noqa: async-mock-config
        mock_ws.send_json.side_effect = Exception("Connection closed")

        await broadcaster.subscribe(mock_ws)

        # Should not raise
        await broadcaster.broadcast(
            notification_type="info",
            title="Test",
            message="Test message",
        )

        # Subscriber should be removed after failed send
        assert broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_broadcaster_broadcast_to_specific_user(self) -> None:
        """
        GIVEN multiple subscribers for different users
        WHEN broadcasting to specific user
        THEN only that user's subscribers receive notification.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()
        mock_ws_user1 = AsyncMock()  # noqa: async-mock-config
        mock_ws_user2 = AsyncMock()  # noqa: async-mock-config

        await broadcaster.subscribe(mock_ws_user1, user_id="user-001")
        await broadcaster.subscribe(mock_ws_user2, user_id="user-002")

        # Broadcast to specific user
        await broadcaster.broadcast_to_user(
            user_id="user-001",
            notification_type="warning",
            title="Tier Limit Approaching",
            message="You've used 4/5 sessions.",
        )

        # Only user-001 should receive the notification
        assert mock_ws_user1.send_json.called
        assert not mock_ws_user2.send_json.called


@pytest.mark.api
@pytest.mark.xdist_group(name="notification_websocket")
class TestNotificationTypes:
    """Tests for notification type validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "notification_type",
        ["info", "success", "warning", "error"],
    )
    async def test_valid_notification_types(self, notification_type: str) -> None:
        """
        GIVEN a valid notification type
        WHEN broadcasting
        THEN notification is sent with correct type.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()
        mock_ws = AsyncMock()  # noqa: async-mock-config

        await broadcaster.subscribe(mock_ws)

        await broadcaster.broadcast(
            notification_type=notification_type,
            title="Test",
            message="Test message",
        )

        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["payload"]["type"] == notification_type

    @pytest.mark.asyncio
    async def test_invalid_notification_type_raises(self) -> None:
        """
        GIVEN an invalid notification type
        WHEN broadcasting
        THEN raises ValueError.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()
        mock_ws = AsyncMock()  # noqa: async-mock-config

        await broadcaster.subscribe(mock_ws)

        with pytest.raises(ValueError, match="Invalid notification type"):
            await broadcaster.broadcast(
                notification_type="invalid_type",
                title="Test",
                message="Test message",
            )


@pytest.mark.api
@pytest.mark.xdist_group(name="notification_websocket")
class TestNotificationWebSocketLifecycle:
    """Tests for WebSocket connection lifecycle."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_subscribe_on_connect(self) -> None:
        """
        GIVEN notification WebSocket endpoint
        WHEN client connects
        THEN client is subscribed to broadcaster.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()

        # Simulate connection with configured mock
        mock_ws = AsyncMock()  # noqa: async-mock-config
        mock_ws.send_json.return_value = None
        await broadcaster.subscribe(mock_ws, user_id="user-001")

        assert broadcaster.subscriber_count == 1

    @pytest.mark.asyncio
    async def test_unsubscribe_on_disconnect(self) -> None:
        """
        GIVEN connected client
        WHEN client disconnects
        THEN client is unsubscribed from broadcaster.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()
        mock_ws = AsyncMock()  # noqa: async-mock-config
        mock_ws.send_json.return_value = None

        await broadcaster.subscribe(mock_ws, user_id="user-001")
        await broadcaster.unsubscribe(mock_ws)

        assert broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_get_subscriber_count_by_user(self) -> None:
        """
        GIVEN multiple connections from same user
        WHEN checking subscriber count for user
        THEN returns correct count.
        """
        from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

        broadcaster = NotificationBroadcaster()
        mock_ws1 = AsyncMock()  # noqa: async-mock-config
        mock_ws1.send_json.return_value = None
        mock_ws2 = AsyncMock()  # noqa: async-mock-config
        mock_ws2.send_json.return_value = None
        mock_ws3 = AsyncMock()  # noqa: async-mock-config
        mock_ws3.send_json.return_value = None

        # User 1 has 2 connections, User 2 has 1
        await broadcaster.subscribe(mock_ws1, user_id="user-001")
        await broadcaster.subscribe(mock_ws2, user_id="user-001")
        await broadcaster.subscribe(mock_ws3, user_id="user-002")

        assert broadcaster.get_subscriber_count_for_user("user-001") == 2
        assert broadcaster.get_subscriber_count_for_user("user-002") == 1
        assert broadcaster.get_subscriber_count_for_user("user-003") == 0


def _create_test_jwt(
    user_id: str = "user:alice",
    username: str = "alice",
    roles: list[str] | None = None,
    email: str = "alice@example.com",
    expires_in: int = 3600,
    secret: str = TEST_JWT_SECRET,
) -> str:
    """Create a test JWT token for unit tests."""
    if roles is None:
        roles = ["user"]
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "username": username,
        "email": email,
        "roles": roles,
        "exp": now + timedelta(seconds=expires_in),
        "iat": now,
        "jti": f"{username}_{int(now.timestamp() * 1000)}",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _create_expired_jwt(
    user_id: str = "user:alice",
    username: str = "alice",
    secret: str = TEST_JWT_SECRET,
) -> str:
    """Create an expired JWT token for testing."""
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "username": username,
        "roles": ["user"],
        "exp": now - timedelta(hours=1),  # Expired 1 hour ago
        "iat": now - timedelta(hours=2),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
def mock_auth_middleware():
    """Set up and tear down mock auth middleware for WebSocket tests."""
    from mcp_server_langgraph.auth.middleware import (
        AuthMiddleware,
        set_global_auth_middleware,
    )
    from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider

    # Create InMemoryUserProvider with test secret
    user_provider = InMemoryUserProvider(secret_key=TEST_JWT_SECRET)
    # Add test users (username, password, email, roles)
    user_provider.add_user("alice", "password123", "alice@example.com", ["user", "premium"])
    user_provider.add_user("bob", "password123", "bob@example.com", ["admin"])
    user_provider.add_user("query_user", "password123", "query@example.com", ["user"])
    user_provider.add_user("header_user", "password123", "header@example.com", ["user"])
    user_provider.add_user("keycloak_user", "password123", "keycloak@example.com", ["user", "premium"])

    # Create middleware with the test user provider
    middleware = AuthMiddleware(user_provider=user_provider)
    set_global_auth_middleware(middleware)

    yield middleware

    # Cleanup
    set_global_auth_middleware(None)


@pytest.mark.api
@pytest.mark.xdist_group(name="notification_websocket_auth")
class TestWebSocketJWTAuthentication:
    """Tests for WebSocket JWT authentication via validate_websocket_auth."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_validate_websocket_auth_with_query_param_token(self, mock_auth_middleware) -> None:
        """
        GIVEN a WebSocket with JWT token in query params
        WHEN validating authentication
        THEN returns user data extracted from token.
        """
        from mcp_server_langgraph.api.v1.notification_websocket import (
            validate_websocket_auth,
        )

        token = _create_test_jwt(
            user_id="user:alice",
            username="alice",
            email="alice@example.com",
            roles=["user", "premium"],
        )

        # Create mock WebSocket with token in query params
        mock_ws = MagicMock()
        mock_ws.query_params = {"token": token}
        mock_ws.headers = {}

        user = await validate_websocket_auth(mock_ws)

        assert user is not None
        assert user["user_id"] == "user:alice"
        assert user["username"] == "alice"
        assert "user" in user["roles"]

    @pytest.mark.asyncio
    async def test_validate_websocket_auth_with_authorization_header(self, mock_auth_middleware) -> None:
        """
        GIVEN a WebSocket with Bearer token in Authorization header
        WHEN validating authentication
        THEN returns user data extracted from token.
        """
        from mcp_server_langgraph.api.v1.notification_websocket import (
            validate_websocket_auth,
        )

        token = _create_test_jwt(
            user_id="user:bob",
            username="bob",
            roles=["admin"],
        )

        # Create mock WebSocket with token in header
        mock_ws = MagicMock()
        mock_ws.query_params = {}
        mock_ws.headers = {"Authorization": f"Bearer {token}"}

        user = await validate_websocket_auth(mock_ws)

        assert user is not None
        assert user["user_id"] == "user:bob"
        assert user["username"] == "bob"
        assert "admin" in user["roles"]

    @pytest.mark.asyncio
    async def test_validate_websocket_auth_no_token(self) -> None:
        """
        GIVEN a WebSocket without any token
        WHEN validating authentication
        THEN returns None.
        """
        from mcp_server_langgraph.api.v1.notification_websocket import (
            validate_websocket_auth,
        )

        mock_ws = MagicMock()
        mock_ws.query_params = {}
        mock_ws.headers = {}

        user = await validate_websocket_auth(mock_ws)

        assert user is None

    @pytest.mark.asyncio
    async def test_validate_websocket_auth_expired_token(self, mock_auth_middleware) -> None:
        """
        GIVEN a WebSocket with expired JWT token
        WHEN validating authentication
        THEN returns None (token rejected).
        """
        from mcp_server_langgraph.api.v1.notification_websocket import (
            validate_websocket_auth,
        )

        token = _create_expired_jwt()

        mock_ws = MagicMock()
        mock_ws.query_params = {"token": token}
        mock_ws.headers = {}

        user = await validate_websocket_auth(mock_ws)

        assert user is None

    @pytest.mark.asyncio
    async def test_validate_websocket_auth_invalid_token(self, mock_auth_middleware) -> None:
        """
        GIVEN a WebSocket with invalid JWT token
        WHEN validating authentication
        THEN returns None (token rejected).
        """
        from mcp_server_langgraph.api.v1.notification_websocket import (
            validate_websocket_auth,
        )

        mock_ws = MagicMock()
        mock_ws.query_params = {"token": "invalid.jwt.token"}
        mock_ws.headers = {}

        user = await validate_websocket_auth(mock_ws)

        assert user is None

    @pytest.mark.asyncio
    async def test_validate_websocket_auth_wrong_signature(self, mock_auth_middleware) -> None:
        """
        GIVEN a WebSocket with JWT signed with wrong secret
        WHEN validating authentication
        THEN returns None (signature verification fails).
        """
        from mcp_server_langgraph.api.v1.notification_websocket import (
            validate_websocket_auth,
        )

        # Create token with different secret
        token = _create_test_jwt(secret="wrong-secret-key")

        mock_ws = MagicMock()
        mock_ws.query_params = {"token": token}
        mock_ws.headers = {}

        user = await validate_websocket_auth(mock_ws)

        assert user is None

    @pytest.mark.asyncio
    async def test_validate_websocket_auth_query_param_takes_precedence(self, mock_auth_middleware) -> None:
        """
        GIVEN a WebSocket with token in both query params and header
        WHEN validating authentication
        THEN query param token takes precedence.
        """
        from mcp_server_langgraph.api.v1.notification_websocket import (
            validate_websocket_auth,
        )

        query_token = _create_test_jwt(user_id="user:query_user", username="query_user")
        header_token = _create_test_jwt(user_id="user:header_user", username="header_user")

        mock_ws = MagicMock()
        mock_ws.query_params = {"token": query_token}
        mock_ws.headers = {"Authorization": f"Bearer {header_token}"}

        user = await validate_websocket_auth(mock_ws)

        assert user is not None
        assert user["username"] == "query_user"

    @pytest.mark.asyncio
    async def test_validate_websocket_auth_uses_auth_middleware(self, mock_auth_middleware) -> None:
        """
        GIVEN a WebSocket with valid token
        WHEN validating authentication
        THEN uses AuthMiddleware.verify_token for validation.
        """
        from mcp_server_langgraph.api.v1.notification_websocket import (
            validate_websocket_auth,
        )

        token = _create_test_jwt(user_id="user:alice", username="alice")

        mock_ws = MagicMock()
        mock_ws.query_params = {"token": token}
        mock_ws.headers = {}

        # The function should use AuthMiddleware internally
        user = await validate_websocket_auth(mock_ws)

        # Auth middleware was used, should return valid user
        assert user is not None
        assert user["username"] == "alice"


@pytest.mark.api
@pytest.mark.xdist_group(name="notification_websocket_auth")
class TestWebSocketKeycloakAuthentication:
    """Tests for WebSocket authentication with Keycloak tokens."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_validate_keycloak_token_with_realm_roles(self, mock_auth_middleware) -> None:
        """
        GIVEN a Keycloak token with realm_access roles
        WHEN validating authentication
        THEN extracts roles correctly.
        """
        from mcp_server_langgraph.api.v1.notification_websocket import (
            validate_websocket_auth,
        )

        # Create Keycloak-style token
        now = datetime.now(UTC)
        payload = {
            "sub": "550e8400-e29b-41d4-a716-446655440000",
            "preferred_username": "keycloak_user",
            "email": "keycloak@example.com",
            "realm_access": {"roles": ["user", "premium"]},
            "exp": now + timedelta(hours=1),
            "iat": now,
        }
        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")

        mock_ws = MagicMock()
        mock_ws.query_params = {"token": token}
        mock_ws.headers = {}

        user = await validate_websocket_auth(mock_ws)

        # Should extract user info from Keycloak token format
        assert user is not None
        assert user["username"] == "keycloak_user"
        assert "user" in user["roles"]
        assert "premium" in user["roles"]
