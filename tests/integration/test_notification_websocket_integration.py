"""
Notification WebSocket Integration Tests.

Integration tests for real-time notification WebSocket with actual WebSocket connections.
Tests the full notification flow from broadcaster to connected clients.

Architecture:
- Uses Starlette TestClient which runs the ASGI app in a background thread
- The NotificationBroadcaster manages subscriptions with asyncio.Lock
- Tests use careful synchronization to test the real WebSocket flow

For broadcast tests that need to send messages to connected clients:
- The broadcast must happen from within the WebSocket handler's async context
- We use a ping/pong mechanism where the client triggers the broadcast via a message
"""

from __future__ import annotations

import gc
import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Generator

import jwt
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

pytestmark = [
    pytest.mark.integration,
    pytest.mark.api,
    pytest.mark.websocket,
]

# Test JWT secret for integration tests
TEST_JWT_SECRET = "integration-test-jwt-secret-for-websocket"


def _create_test_jwt(
    user_id: str = "user:alice",
    username: str = "alice",
    roles: list[str] | None = None,
    email: str = "alice@example.com",
    expires_in: int = 3600,
    secret: str = TEST_JWT_SECRET,
) -> str:
    """Create a test JWT token for integration tests."""
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


@pytest.fixture
def notification_websocket_app() -> Generator[FastAPI, None, None]:
    """
    Create a test FastAPI app with the notification WebSocket router.

    Includes test-only HTTP endpoints for triggering broadcasts from the same
    async context as the WebSocket connections (solving the threading issue).
    """
    from mcp_server_langgraph.api.v1.notification_websocket import (
        router,
        set_notification_broadcaster,
    )
    from mcp_server_langgraph.auth.middleware import (
        AuthMiddleware,
        set_global_auth_middleware,
    )
    from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider
    from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster

    # Create user provider with test secret
    user_provider = InMemoryUserProvider(secret_key=TEST_JWT_SECRET)
    user_provider.add_user("alice", "password123", "alice@example.com", ["user"])
    user_provider.add_user("bob", "password123", "bob@example.com", ["user"])

    # Create and set auth middleware
    middleware = AuthMiddleware(user_provider=user_provider)
    set_global_auth_middleware(middleware)

    # Create and set broadcaster
    broadcaster = NotificationBroadcaster()
    set_notification_broadcaster(broadcaster)

    app = FastAPI()
    app.include_router(router, prefix="/ws")

    # Store broadcaster on app for test access
    app.state.broadcaster = broadcaster

    # Test-only endpoint to trigger broadcasts from the same async context
    @app.post("/test/broadcast")
    async def trigger_broadcast(
        notification_type: str = "info",
        title: str = "Test",
        message: str = "Test message",
    ) -> dict[str, str]:
        """Trigger a broadcast notification (test-only endpoint)."""
        await broadcaster.broadcast(
            notification_type=notification_type,
            title=title,
            message=message,
        )
        return {"status": "broadcast_sent"}

    @app.post("/test/broadcast-to-user")
    async def trigger_user_broadcast(
        user_id: str,
        notification_type: str = "info",
        title: str = "Test",
        message: str = "Test message",
    ) -> dict[str, str]:
        """Trigger a user-specific broadcast notification (test-only endpoint)."""
        await broadcaster.broadcast_to_user(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
        )
        return {"status": "broadcast_sent", "user_id": user_id}

    yield app

    # Cleanup
    set_notification_broadcaster(None)
    set_global_auth_middleware(None)


@pytest.fixture
def notification_websocket_client(
    notification_websocket_app: FastAPI,
) -> TestClient:
    """Create a test client for the notification WebSocket app."""
    return TestClient(notification_websocket_app)


@pytest.mark.xdist_group(name="test_notification_websocket_integration")
class TestNotificationWebSocketIntegration:
    """Integration tests for notification WebSocket endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_connection_with_valid_token(self, notification_websocket_client: TestClient) -> None:
        """
        GIVEN a valid JWT token
        WHEN connecting to the notification WebSocket
        THEN the connection is established successfully.
        """
        token = _create_test_jwt(user_id="user:alice", username="alice")

        with notification_websocket_client.websocket_connect(f"/ws/notifications?token={token}") as websocket:
            # Connection should be established - just verify we can connect
            # A real notification would be sent asynchronously
            assert websocket is not None

    def test_websocket_connection_without_token_closes(self, notification_websocket_client: TestClient) -> None:
        """
        GIVEN no JWT token
        WHEN connecting to the notification WebSocket
        THEN the connection is closed.
        """
        # Without token, connection should close quickly
        try:
            with notification_websocket_client.websocket_connect("/ws/notifications") as websocket:
                # Try to receive - should get WebSocket close
                try:
                    websocket.receive_json(timeout=1)
                    pytest.fail("Expected WebSocket to close")
                except Exception:
                    pass  # Expected - connection closed
        except Exception:
            pass  # Connection refused is also acceptable

    @pytest.mark.xfail(
        reason="Starlette TestClient creates isolated async contexts per request. "
        "Each TestClient runs the ASGI app in its own event loop, so the broadcaster's "
        "asyncio.Lock and subscriber list aren't shared properly between WebSocket and HTTP contexts. "
        "This test works correctly with a live server (e.g., using uvicorn + websockets client). "
        "The broadcaster logic is verified in unit tests for NotificationBroadcaster.",
        strict=False,
    )
    def test_websocket_receives_broadcast_notification(
        self, notification_websocket_app: FastAPI, notification_websocket_client: TestClient
    ) -> None:
        """
        GIVEN a connected WebSocket client
        WHEN a notification is broadcast via HTTP endpoint
        THEN the client receives the notification.

        Uses a test-only HTTP endpoint to trigger broadcasts. The HTTP call is made
        from a separate thread to allow concurrent WebSocket and HTTP operations.

        NOTE: This test is xfail due to TestClient async isolation. Test against
        a live server for true E2E validation.
        """
        token = _create_test_jwt(user_id="user:alice", username="alice")

        received_messages: list[dict[str, Any]] = []
        connection_ready = threading.Event()
        broadcast_requested = threading.Event()
        message_received = threading.Event()

        def connect_and_receive():
            try:
                with notification_websocket_client.websocket_connect(f"/ws/notifications?token={token}") as websocket:
                    # Signal that connection is ready
                    connection_ready.set()

                    # Wait for main thread to request broadcast
                    broadcast_requested.wait(timeout=3)

                    # Wait for message with timeout
                    try:
                        message = websocket.receive_json(timeout=5)
                        received_messages.append(message)
                        message_received.set()
                    except Exception:
                        pass
            except Exception:
                connection_ready.set()  # Release main thread on error

        def trigger_broadcast():
            """Trigger broadcast from separate thread using fresh TestClient."""
            http_client = TestClient(notification_websocket_app)
            response = http_client.post(
                "/test/broadcast",
                params={
                    "notification_type": "info",
                    "title": "Test Notification",
                    "message": "This is a test notification",
                },
            )
            assert response.status_code == 200

        # Start connection in background thread
        receiver_thread = threading.Thread(target=connect_and_receive)
        receiver_thread.start()

        # Wait for connection to establish
        connection_ready.wait(timeout=3)
        time.sleep(0.5)  # Give time for subscription to complete

        # Signal that we're about to broadcast
        broadcast_requested.set()

        # Give a moment for the receive to start
        time.sleep(0.1)

        # Trigger broadcast from separate thread
        broadcast_thread = threading.Thread(target=trigger_broadcast)
        broadcast_thread.start()
        broadcast_thread.join(timeout=5)

        # Wait for message
        message_received.wait(timeout=3)
        receiver_thread.join(timeout=5)

        # Verify notification was received
        assert len(received_messages) == 1
        msg = received_messages[0]
        assert msg["type"] == "notification"
        assert msg["payload"]["type"] == "info"
        assert msg["payload"]["title"] == "Test Notification"
        assert msg["payload"]["message"] == "This is a test notification"

    @pytest.mark.xfail(
        reason="Starlette TestClient creates isolated async contexts per request. "
        "See test_websocket_receives_broadcast_notification for full explanation. "
        "Test against a live server for true E2E user-specific notification validation.",
        strict=False,
    )
    def test_websocket_user_specific_notification(
        self, notification_websocket_app: FastAPI, notification_websocket_client: TestClient
    ) -> None:
        """
        GIVEN two connected WebSocket clients
        WHEN a notification is broadcast to a specific user via HTTP endpoint
        THEN only that user's client receives the notification.

        Uses a test-only HTTP endpoint to trigger user-specific broadcasts.
        The HTTP call is made from a separate thread.

        NOTE: This test is xfail due to TestClient async isolation.
        """
        alice_token = _create_test_jwt(
            user_id="alice@example.com",
            username="alice",
            email="alice@example.com",
        )
        bob_token = _create_test_jwt(
            user_id="bob@example.com",
            username="bob",
            email="bob@example.com",
        )

        alice_messages: list[dict[str, Any]] = []
        bob_messages: list[dict[str, Any]] = []
        alice_ready = threading.Event()
        bob_ready = threading.Event()
        broadcast_requested = threading.Event()
        alice_done = threading.Event()
        bob_done = threading.Event()

        def alice_connect():
            try:
                with notification_websocket_client.websocket_connect(f"/ws/notifications?token={alice_token}") as websocket:
                    alice_ready.set()
                    # Wait for broadcast signal
                    broadcast_requested.wait(timeout=3)
                    try:
                        message = websocket.receive_json(timeout=5)
                        alice_messages.append(message)
                    except Exception:
                        pass
                    alice_done.set()
            except Exception:
                alice_ready.set()
                alice_done.set()

        def bob_connect():
            try:
                with notification_websocket_client.websocket_connect(f"/ws/notifications?token={bob_token}") as websocket:
                    bob_ready.set()
                    # Wait for broadcast signal
                    broadcast_requested.wait(timeout=3)
                    try:
                        message = websocket.receive_json(timeout=3)
                        bob_messages.append(message)
                    except Exception:
                        pass
                    bob_done.set()
            except Exception:
                bob_ready.set()
                bob_done.set()

        def trigger_broadcast():
            """Trigger user-specific broadcast from separate thread."""
            http_client = TestClient(notification_websocket_app)
            response = http_client.post(
                "/test/broadcast-to-user",
                params={
                    "user_id": "alice@example.com",
                    "notification_type": "success",
                    "title": "Hello Alice",
                    "message": "This is for Alice only",
                },
            )
            assert response.status_code == 200

        # Connect both users
        alice_thread = threading.Thread(target=alice_connect)
        bob_thread = threading.Thread(target=bob_connect)
        alice_thread.start()
        bob_thread.start()

        # Wait for both to connect
        alice_ready.wait(timeout=3)
        bob_ready.wait(timeout=3)
        time.sleep(0.5)  # Wait for subscriptions

        # Signal that we're about to broadcast
        broadcast_requested.set()
        time.sleep(0.1)  # Let receive calls start

        # Trigger broadcast from separate thread
        broadcast_thread = threading.Thread(target=trigger_broadcast)
        broadcast_thread.start()
        broadcast_thread.join(timeout=5)

        # Wait for threads
        alice_done.wait(timeout=5)
        bob_done.wait(timeout=5)
        alice_thread.join(timeout=5)
        bob_thread.join(timeout=5)

        # Alice should have received the notification
        assert len(alice_messages) == 1
        assert alice_messages[0]["payload"]["title"] == "Hello Alice"

        # Bob should not have received the notification
        assert len(bob_messages) == 0

    def test_subscriber_count_increases_on_connect(
        self, notification_websocket_app: FastAPI, notification_websocket_client: TestClient
    ) -> None:
        """
        GIVEN the notification broadcaster
        WHEN a client connects via WebSocket
        THEN the subscriber count increases.
        """
        token = _create_test_jwt(user_id="user:alice", username="alice")
        broadcaster = notification_websocket_app.state.broadcaster

        initial_count = broadcaster.subscriber_count
        connection_ready = threading.Event()

        def connect():
            try:
                with notification_websocket_client.websocket_connect(f"/ws/notifications?token={token}") as _websocket:
                    connection_ready.set()
                    # Keep connection alive briefly
                    time.sleep(1)
            except Exception:
                connection_ready.set()

        thread = threading.Thread(target=connect)
        thread.start()

        connection_ready.wait(timeout=3)
        time.sleep(0.5)  # Wait for subscription

        # Check subscriber count increased
        current_count = broadcaster.subscriber_count
        assert current_count > initial_count

        thread.join(timeout=5)
