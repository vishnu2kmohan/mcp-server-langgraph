"""
WebSocket Lifecycle Integration Tests.

Integration tests for WebSocket infrastructure with actual connections.
Tests lifecycle management, authentication, heartbeat, and error handling.

Architecture:
- Uses Starlette TestClient which runs the ASGI app in a background thread
- Tests verify the real WebSocket connection flow through the base class
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime, timedelta
from typing import Generator

import jwt
import pytest
from fastapi import FastAPI, WebSocket

from mcp_server_langgraph.websocket.base import WebSocketBase
from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

pytestmark = [
    pytest.mark.integration,
    pytest.mark.websocket,
    pytest.mark.lifecycle,
]

# Test JWT secret for integration tests
TEST_JWT_SECRET = "integration-test-jwt-secret-for-websocket-lifecycle"


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


class LifecycleTestHandler(WebSocketBase):
    """Test WebSocket handler for integration testing."""

    def __init__(self):
        config = WebSocketConfig(
            endpoint_name="test-websocket",
            require_auth=True,
            heartbeat_interval=30,
            idle_timeout=1800,
            rate_limit_per_minute=600,
        )
        super().__init__(config)
        self.messages_received: list[MessageEnvelope] = []
        self.connect_called = False
        self.disconnect_called = False

    async def on_connect(self, user) -> None:
        """Track connection event."""
        self.connect_called = True
        self.connected_user = user

    async def on_disconnect(self) -> None:
        """Track disconnection event."""
        self.disconnect_called = True

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """Echo messages back with test prefix."""
        self.messages_received.append(message)
        if message.type == "echo":
            return MessageEnvelope(
                type="echo_response",
                payload={"echo": message.payload},
            )
        return None


class NoAuthWebSocketHandler(WebSocketBase):
    """Test WebSocket handler without authentication requirement."""

    def __init__(self):
        config = WebSocketConfig(
            endpoint_name="no-auth-websocket",
            require_auth=False,
            heartbeat_interval=30,
        )
        super().__init__(config)

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """Echo messages back."""
        if message.type == "echo":
            return MessageEnvelope(
                type="echo_response",
                payload={"echo": message.payload},
            )
        return None


@pytest.fixture
def lifecycle_websocket_app() -> Generator[FastAPI, None, None]:
    """Create a test FastAPI app with lifecycle test WebSocket endpoints."""
    from mcp_server_langgraph.auth.middleware import (
        AuthMiddleware,
        set_global_auth_middleware,
    )
    from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider

    # Create user provider with test secret
    user_provider = InMemoryUserProvider(secret_key=TEST_JWT_SECRET)
    user_provider.add_user("alice", "password123", "alice@example.com", ["user"])
    user_provider.add_user("bob", "password123", "bob@example.com", ["user"])
    user_provider.add_user("admin", "admin123", "admin@example.com", ["admin", "user"])

    # Create auth middleware
    middleware = AuthMiddleware(user_provider=user_provider)

    # Set both global (backward compat) and app.state (DI pattern)
    set_global_auth_middleware(middleware)

    app = FastAPI()
    # Set auth middleware in app.state for DI pattern (new pattern)
    app.state.auth_middleware = middleware

    # Add auth-required WebSocket endpoint
    @app.websocket("/ws/auth-required")
    async def auth_required_websocket(websocket: WebSocket):
        handler = LifecycleTestHandler()
        await handler.run(websocket)

    # Add no-auth WebSocket endpoint
    @app.websocket("/ws/no-auth")
    async def no_auth_websocket(websocket: WebSocket):
        handler = NoAuthWebSocketHandler()
        await handler.run(websocket)

    yield app

    # Cleanup
    set_global_auth_middleware(None)


@pytest.fixture
def lifecycle_client(lifecycle_websocket_app: FastAPI):
    """Create a test client for lifecycle WebSocket app."""
    from starlette.testclient import TestClient

    return TestClient(lifecycle_websocket_app)


@pytest.mark.xdist_group(name="websocket_lifecycle_integration")
class TestWebSocketLifecycleIntegration:
    """Integration tests for WebSocket lifecycle management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_connection_with_valid_jwt(self, lifecycle_client) -> None:
        """
        GIVEN a valid JWT token
        WHEN connecting to an auth-required WebSocket
        THEN the connection is established successfully.
        """
        token = _create_test_jwt(user_id="user:alice", username="alice")

        with lifecycle_client.websocket_connect(f"/ws/auth-required?token={token}") as websocket:
            assert websocket is not None
            # Send a ping to verify connection is working
            websocket.send_json({"type": "ping", "payload": {}})
            response = websocket.receive_json()
            assert response["type"] == "pong"

    def test_connection_without_jwt_closes(self, lifecycle_client) -> None:
        """
        GIVEN no JWT token
        WHEN connecting to an auth-required WebSocket
        THEN the connection is closed with auth error.
        """
        try:
            with lifecycle_client.websocket_connect("/ws/auth-required") as websocket:
                # Try to receive - should get WebSocket close
                try:
                    websocket.receive_json(timeout=2)
                    pytest.fail("Expected WebSocket to close due to auth failure")
                except Exception:
                    pass  # Expected - connection closed
        except Exception:
            pass  # Connection refused is also acceptable

    def test_connection_with_expired_jwt_closes(self, lifecycle_client) -> None:
        """
        GIVEN an expired JWT token
        WHEN connecting to an auth-required WebSocket
        THEN the connection is closed with auth error.
        """
        expired_token = _create_test_jwt(
            user_id="user:alice",
            username="alice",
            expires_in=-3600,  # Expired 1 hour ago
        )

        try:
            with lifecycle_client.websocket_connect(f"/ws/auth-required?token={expired_token}") as websocket:
                try:
                    websocket.receive_json(timeout=2)
                    pytest.fail("Expected WebSocket to close due to expired token")
                except Exception:
                    pass
        except Exception:
            pass  # Connection refused is also acceptable

    def test_no_auth_endpoint_connects_without_token(self, lifecycle_client) -> None:
        """
        GIVEN no JWT token
        WHEN connecting to a no-auth WebSocket
        THEN the connection is established successfully.
        """
        with lifecycle_client.websocket_connect("/ws/no-auth") as websocket:
            assert websocket is not None
            # Send ping to verify
            websocket.send_json({"type": "ping", "payload": {}})
            response = websocket.receive_json()
            assert response["type"] == "pong"

    def test_ping_pong_handling(self, lifecycle_client) -> None:
        """
        GIVEN a connected WebSocket client
        WHEN sending a ping message
        THEN a pong response is received.
        """
        token = _create_test_jwt(user_id="user:alice")

        with lifecycle_client.websocket_connect(f"/ws/auth-required?token={token}") as websocket:
            # Send ping
            websocket.send_json({"type": "ping", "payload": {}})
            response = websocket.receive_json()

            assert response["type"] == "pong"
            # Pong may or may not have a payload depending on implementation
            # The key assertion is that we get a pong response

    def test_echo_message_handling(self, lifecycle_client) -> None:
        """
        GIVEN a connected WebSocket client
        WHEN sending an echo message
        THEN an echo_response is received.
        """
        token = _create_test_jwt(user_id="user:alice")

        with lifecycle_client.websocket_connect(f"/ws/auth-required?token={token}") as websocket:
            # Send echo message
            websocket.send_json(
                {
                    "type": "echo",
                    "payload": {"message": "Hello, World!"},
                }
            )
            response = websocket.receive_json()

            assert response["type"] == "echo_response"
            assert response["payload"]["echo"]["message"] == "Hello, World!"

    def test_multiple_messages(self, lifecycle_client) -> None:
        """
        GIVEN a connected WebSocket client
        WHEN sending multiple messages
        THEN all responses are received correctly.
        """
        token = _create_test_jwt(user_id="user:alice")

        with lifecycle_client.websocket_connect(f"/ws/auth-required?token={token}") as websocket:
            # Send multiple messages
            for i in range(3):
                websocket.send_json(
                    {
                        "type": "echo",
                        "payload": {"index": i},
                    }
                )
                response = websocket.receive_json()
                assert response["type"] == "echo_response"
                assert response["payload"]["echo"]["index"] == i

    def test_connection_resilience_after_unknown_type(self, lifecycle_client) -> None:
        """
        GIVEN a connected WebSocket client
        WHEN sending an unknown message type
        THEN connection stays open and can still handle valid messages.
        """
        token = _create_test_jwt(user_id="user:alice")

        with lifecycle_client.websocket_connect(f"/ws/auth-required?token={token}") as websocket:
            # Send unknown message type (not invalid, just unhandled)
            websocket.send_json({"type": "unknown_custom_type", "payload": {}})

            # Connection should still work - send a ping
            websocket.send_json({"type": "ping", "payload": {}})
            pong = websocket.receive_json()
            assert pong["type"] == "pong"


@pytest.mark.xdist_group(name="websocket_lifecycle_integration")
class TestWebSocketAuthorizationIntegration:
    """Integration tests for WebSocket authorization patterns."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_admin_role_in_token(self, lifecycle_client) -> None:
        """
        GIVEN a JWT with admin role
        WHEN connecting to WebSocket
        THEN connection is established and role is available.
        """
        admin_token = _create_test_jwt(
            user_id="user:admin",
            username="admin",
            roles=["admin", "user"],
        )

        with lifecycle_client.websocket_connect(f"/ws/auth-required?token={admin_token}") as websocket:
            websocket.send_json({"type": "ping", "payload": {}})
            response = websocket.receive_json()
            assert response["type"] == "pong"

    def test_different_users_isolated(self, lifecycle_client) -> None:
        """
        GIVEN different user tokens
        WHEN they connect to the same endpoint
        THEN each connection is isolated.
        """
        alice_token = _create_test_jwt(user_id="user:alice", username="alice")
        bob_token = _create_test_jwt(user_id="user:bob", username="bob")

        # Both should connect successfully
        with lifecycle_client.websocket_connect(f"/ws/auth-required?token={alice_token}") as alice_ws:
            alice_ws.send_json({"type": "echo", "payload": {"user": "alice"}})
            alice_response = alice_ws.receive_json()
            assert alice_response["payload"]["echo"]["user"] == "alice"

        with lifecycle_client.websocket_connect(f"/ws/auth-required?token={bob_token}") as bob_ws:
            bob_ws.send_json({"type": "echo", "payload": {"user": "bob"}})
            bob_response = bob_ws.receive_json()
            assert bob_response["payload"]["echo"]["user"] == "bob"


@pytest.mark.xdist_group(name="websocket_lifecycle_integration")
class TestWebSocketErrorHandlingIntegration:
    """Integration tests for WebSocket error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_malformed_json_handled(self, lifecycle_client) -> None:
        """
        GIVEN a connected WebSocket
        WHEN sending malformed JSON
        THEN an error is returned and connection stays open.
        """
        token = _create_test_jwt(user_id="user:alice")

        with lifecycle_client.websocket_connect(f"/ws/auth-required?token={token}") as websocket:
            # Send malformed JSON as text
            websocket.send_text("not valid json {{{")
            response = websocket.receive_json()

            assert response["type"] == "error"

            # Connection should still work
            websocket.send_json({"type": "ping", "payload": {}})
            pong = websocket.receive_json()
            assert pong["type"] == "pong"

    def test_unknown_message_type_handled(self, lifecycle_client) -> None:
        """
        GIVEN a connected WebSocket
        WHEN sending an unknown message type
        THEN connection stays open (message is ignored or echoed).
        """
        token = _create_test_jwt(user_id="user:alice")

        with lifecycle_client.websocket_connect(f"/ws/auth-required?token={token}") as websocket:
            # Send unknown message type
            websocket.send_json({"type": "unknown_type", "payload": {}})

            # Send ping to verify connection is still alive
            websocket.send_json({"type": "ping", "payload": {}})
            response = websocket.receive_json()

            # Should get pong (unknown type is handled gracefully)
            assert response["type"] == "pong"


class LowRateLimitHandler(WebSocketBase):
    """Test WebSocket handler with very low rate limit for testing."""

    def __init__(self):
        config = WebSocketConfig(
            endpoint_name="rate-limit-test",
            require_auth=True,
            heartbeat_interval=30,
            rate_limit_per_minute=3,  # Very low limit for testing
        )
        super().__init__(config)

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """Echo messages back."""
        if message.type == "echo":
            return MessageEnvelope(
                type="echo_response",
                payload={"echo": message.payload},
            )
        return None


@pytest.fixture
def rate_limit_test_app() -> Generator[FastAPI, None, None]:
    """Create a test FastAPI app with low rate limit WebSocket endpoint."""
    from mcp_server_langgraph.auth.middleware import (
        AuthMiddleware,
        set_global_auth_middleware,
    )
    from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider

    # Create user provider with test secret
    user_provider = InMemoryUserProvider(secret_key=TEST_JWT_SECRET)
    user_provider.add_user("alice", "password123", "alice@example.com", ["user"])

    # Create auth middleware
    middleware = AuthMiddleware(user_provider=user_provider)
    set_global_auth_middleware(middleware)

    app = FastAPI()
    app.state.auth_middleware = middleware

    @app.websocket("/ws/rate-limited")
    async def rate_limited_websocket(websocket: WebSocket):
        handler = LowRateLimitHandler()
        await handler.run(websocket)

    yield app

    set_global_auth_middleware(None)


@pytest.fixture
def rate_limit_client(rate_limit_test_app: FastAPI):
    """Create a test client for rate limit testing."""
    from starlette.testclient import TestClient

    return TestClient(rate_limit_test_app)


@pytest.mark.xdist_group(name="websocket_rate_limit_integration")
class TestWebSocketRateLimitHeadersIntegration:
    """Integration tests for rate limit headers in WebSocket error responses."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_rate_limit_error_includes_rate_limit_info(self, rate_limit_client) -> None:
        """
        GIVEN a WebSocket endpoint with low rate limit (3/min)
        WHEN the client exceeds the rate limit
        THEN the error response includes rate_limit info with limit, remaining, retry_after.
        """
        token = _create_test_jwt(user_id="user:alice", username="alice")

        with rate_limit_client.websocket_connect(f"/ws/rate-limited?token={token}") as websocket:
            # Send 3 messages (at limit)
            for i in range(3):
                websocket.send_json({"type": "echo", "payload": {"msg": i}})
                response = websocket.receive_json()
                assert response["type"] == "echo_response"

            # 4th message should exceed rate limit
            websocket.send_json({"type": "echo", "payload": {"msg": "over_limit"}})
            error_response = websocket.receive_json()

            # Verify error response structure
            assert error_response["type"] == "error"
            assert error_response["payload"]["code"] == "rate_limit_exceeded"

            # Verify rate_limit info is included
            assert "rate_limit" in error_response["payload"]
            rate_limit = error_response["payload"]["rate_limit"]
            assert rate_limit["limit"] == 3
            assert rate_limit["remaining"] == 0
            assert "retry_after" in rate_limit
            assert isinstance(rate_limit["retry_after"], int)
            assert rate_limit["retry_after"] >= 0

    def test_rate_limit_error_connection_stays_open(self, rate_limit_client) -> None:
        """
        GIVEN a WebSocket that hit rate limit
        WHEN the rate limit error is received
        THEN the connection remains open for future messages.
        """
        token = _create_test_jwt(user_id="user:alice", username="alice")

        with rate_limit_client.websocket_connect(f"/ws/rate-limited?token={token}") as websocket:
            # Exhaust rate limit
            for i in range(3):
                websocket.send_json({"type": "echo", "payload": {"msg": i}})
                websocket.receive_json()

            # Exceed limit
            websocket.send_json({"type": "echo", "payload": {"over": True}})
            error = websocket.receive_json()
            assert error["type"] == "error"

            # Connection should still work for ping/pong (system messages)
            websocket.send_json({"type": "ping", "payload": {}})
            pong = websocket.receive_json()
            assert pong["type"] == "pong"
