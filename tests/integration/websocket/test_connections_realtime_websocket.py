"""
Connections Realtime WebSocket Integration Tests.

Integration tests for /api/v1/ws/connections-realtime endpoint.
Tests the full WebSocket flow for real-time MCP connection status updates.

Architecture:
- Uses Starlette TestClient for actual WebSocket connections
- Tests subscription (single/all), health checks, and lifecycle events
- Validates message format and error handling
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime, timedelta
from typing import Any, Generator

import jwt
import pytest
from fastapi import FastAPI, WebSocket
from starlette.testclient import TestClient

from mcp_server_langgraph.websocket.handlers.connections_realtime import (
    ConnectionsRealtimeHandler,
)
from mcp_server_langgraph.websocket.types import WebSocketConfig

pytestmark = [
    pytest.mark.integration,
    pytest.mark.websocket,
    pytest.mark.connections,
]

# Test JWT secret for integration tests
TEST_JWT_SECRET = "integration-test-jwt-secret-for-connections-realtime"


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


class MockConnectionService:
    """Mock connection service for integration tests."""

    def __init__(self) -> None:
        self.connections: dict[str, dict[str, Any]] = {}
        self._setup_test_data()

    def _setup_test_data(self) -> None:
        """Set up test connection data."""
        self.connections = {
            "conn-1": {
                "id": "conn-1",
                "name": "Production Server",
                "url": "https://prod.example.com/mcp",
                "auth_type": "oauth2",
                "status": "connected",
                "server_name": "MCP Production",
                "tool_count": 15,
                "resource_count": 8,
                "prompt_count": 3,
                "last_connected_at": datetime.now(UTC).isoformat(),
            },
            "conn-2": {
                "id": "conn-2",
                "name": "Development Server",
                "url": "https://dev.example.com/mcp",
                "auth_type": "api_key",
                "status": "disconnected",
                "server_name": None,
                "tool_count": 0,
                "resource_count": 0,
                "prompt_count": 0,
                "last_connected_at": None,
            },
            "conn-3": {
                "id": "conn-3",
                "name": "Staging Server",
                "url": "https://staging.example.com/mcp",
                "auth_type": "none",
                "status": "error",
                "server_name": None,
                "tool_count": 0,
                "resource_count": 0,
                "prompt_count": 0,
                "last_connected_at": None,
                "error_message": "Connection refused",
            },
        }

    async def list_connections(self) -> list[dict[str, Any]]:
        """List all connections."""
        return list(self.connections.values())

    async def get_connection(self, connection_id: str) -> dict[str, Any] | None:
        """Get a specific connection by ID."""
        return self.connections.get(connection_id)

    async def get_connection_health(self, connection_id: str) -> dict[str, Any]:
        """Get health status for a connection."""
        conn = self.connections.get(connection_id)
        if not conn:
            return {
                "connection_id": connection_id,
                "healthy": False,
                "error": "Connection not found",
            }
        return {
            "connection_id": connection_id,
            "healthy": conn.get("status") == "connected",
            "status": conn.get("status"),
            "latency_ms": 42 if conn.get("status") == "connected" else None,
            "last_check": datetime.now(UTC).isoformat(),
        }


@pytest.fixture
def mock_connection_service() -> MockConnectionService:
    """Create a mock connection service with test data."""
    return MockConnectionService()


@pytest.fixture
def test_app(mock_connection_service: MockConnectionService) -> FastAPI:
    """Create a test FastAPI app with connections realtime endpoint."""
    app = FastAPI()

    @app.websocket("/api/v1/ws/connections-realtime")
    async def connections_realtime_endpoint(websocket: WebSocket) -> None:
        handler = ConnectionsRealtimeHandler(
            config=WebSocketConfig(
                endpoint_name="connections-realtime-test",
                require_auth=False,  # Disable auth for testing
                rate_limit_per_minute=600,
                message_timeout=30,
            ),
            connection_service=mock_connection_service,
        )
        await handler.run(websocket)

    return app


@pytest.fixture
def test_client(test_app: FastAPI) -> Generator[TestClient, None, None]:
    """Create a test client for the app."""
    with TestClient(test_app) as client:
        yield client


@pytest.mark.xdist_group(name="connections_realtime_websocket")
class TestConnectionsRealtimeWebSocketConnection:
    """Test WebSocket connection lifecycle for connections realtime."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_connection_succeeds(self, test_client: TestClient) -> None:
        """Test that WebSocket connection can be established."""
        with test_client.websocket_connect("/api/v1/ws/connections-realtime?v=1.0.0") as ws:
            # Connection successful, should receive initial connection list
            response = ws.receive_json()
            assert response["type"] == "connection_list"

    def test_websocket_receives_initial_connection_list(self, test_client: TestClient) -> None:
        """Test that client receives connection list on connect."""
        with test_client.websocket_connect("/api/v1/ws/connections-realtime?v=1.0.0") as ws:
            response = ws.receive_json()

            assert response["type"] == "connection_list"
            assert "connections" in response
            assert len(response["connections"]) == 3

            # Verify connection structure
            conn_names = [c["name"] for c in response["connections"]]
            assert "Production Server" in conn_names
            assert "Development Server" in conn_names
            assert "Staging Server" in conn_names


@pytest.mark.xdist_group(name="connections_realtime_websocket")
class TestConnectionsRealtimeSubscription:
    """Test subscription to specific connections."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_subscribe_to_specific_connection(self, test_client: TestClient) -> None:
        """Test subscribing to a specific connection."""
        with test_client.websocket_connect("/api/v1/ws/connections-realtime?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial connection list

            ws.send_json(
                {
                    "type": "subscribe",
                    "id": "test-1",
                    "payload": {"connection_id": "conn-1"},
                }
            )
            response = ws.receive_json()

            assert response["type"] == "connection_status"
            assert response["id"] == "test-1"
            assert response["payload"]["connection"]["id"] == "conn-1"
            assert response["payload"]["connection"]["name"] == "Production Server"

    def test_subscribe_to_nonexistent_connection_returns_error(self, test_client: TestClient) -> None:
        """Test subscribing to nonexistent connection returns error."""
        with test_client.websocket_connect("/api/v1/ws/connections-realtime?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial connection list

            ws.send_json(
                {
                    "type": "subscribe",
                    "id": "test-2",
                    "payload": {"connection_id": "nonexistent"},
                }
            )
            response = ws.receive_json()

            assert response["type"] == "error"
            assert response["id"] == "test-2"
            assert response["payload"]["code"] == "connection_not_found"

    def test_subscribe_missing_connection_id_returns_error(self, test_client: TestClient) -> None:
        """Test subscribing without connection_id returns error."""
        with test_client.websocket_connect("/api/v1/ws/connections-realtime?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial connection list

            ws.send_json(
                {
                    "type": "subscribe",
                    "id": "test-3",
                    "payload": {},
                }
            )
            response = ws.receive_json()

            assert response["type"] == "error"
            assert response["id"] == "test-3"
            assert response["payload"]["code"] == "missing_connection_id"


@pytest.mark.xdist_group(name="connections_realtime_websocket")
class TestConnectionsRealtimeSubscribeAll:
    """Test subscribe_all functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_subscribe_all_succeeds(self, test_client: TestClient) -> None:
        """Test subscribing to all connections."""
        with test_client.websocket_connect("/api/v1/ws/connections-realtime?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial connection list

            ws.send_json(
                {
                    "type": "subscribe_all",
                    "id": "test-4",
                    "payload": {},
                }
            )
            response = ws.receive_json()

            assert response["type"] == "subscribed_all"
            assert response["id"] == "test-4"
            assert response["payload"]["subscribed"] is True


@pytest.mark.xdist_group(name="connections_realtime_websocket")
class TestConnectionsRealtimeUnsubscribe:
    """Test unsubscription functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_unsubscribe_from_connection(self, test_client: TestClient) -> None:
        """Test unsubscribing from a connection."""
        with test_client.websocket_connect("/api/v1/ws/connections-realtime?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial connection list

            # First subscribe
            ws.send_json(
                {
                    "type": "subscribe",
                    "id": "test-5",
                    "payload": {"connection_id": "conn-1"},
                }
            )
            ws.receive_json()  # Consume connection_status

            # Then unsubscribe
            ws.send_json(
                {
                    "type": "unsubscribe",
                    "id": "test-6",
                    "payload": {"connection_id": "conn-1"},
                }
            )
            response = ws.receive_json()

            assert response["type"] == "unsubscribed"
            assert response["id"] == "test-6"
            assert response["payload"]["connection_id"] == "conn-1"


@pytest.mark.xdist_group(name="connections_realtime_websocket")
class TestConnectionsRealtimeHealthCheck:
    """Test health check request functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_request_health_check_for_connected_server(self, test_client: TestClient) -> None:
        """Test health check for connected server."""
        with test_client.websocket_connect("/api/v1/ws/connections-realtime?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial connection list

            ws.send_json(
                {
                    "type": "request_health_check",
                    "id": "test-7",
                    "payload": {"connection_id": "conn-1"},
                }
            )
            response = ws.receive_json()

            assert response["type"] == "health_check_result"
            assert response["id"] == "test-7"
            assert response["payload"]["connection_id"] == "conn-1"
            assert response["payload"]["healthy"] is True
            assert response["payload"]["status"] == "connected"
            assert "latency_ms" in response["payload"]

    def test_request_health_check_for_disconnected_server(self, test_client: TestClient) -> None:
        """Test health check for disconnected server."""
        with test_client.websocket_connect("/api/v1/ws/connections-realtime?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial connection list

            ws.send_json(
                {
                    "type": "request_health_check",
                    "id": "test-8",
                    "payload": {"connection_id": "conn-2"},
                }
            )
            response = ws.receive_json()

            assert response["type"] == "health_check_result"
            assert response["payload"]["connection_id"] == "conn-2"
            assert response["payload"]["healthy"] is False
            assert response["payload"]["status"] == "disconnected"

    def test_request_health_check_for_error_server(self, test_client: TestClient) -> None:
        """Test health check for server in error state."""
        with test_client.websocket_connect("/api/v1/ws/connections-realtime?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial connection list

            ws.send_json(
                {
                    "type": "request_health_check",
                    "id": "test-9",
                    "payload": {"connection_id": "conn-3"},
                }
            )
            response = ws.receive_json()

            assert response["type"] == "health_check_result"
            assert response["payload"]["connection_id"] == "conn-3"
            assert response["payload"]["healthy"] is False
            assert response["payload"]["status"] == "error"

    def test_request_health_check_missing_connection_id_returns_error(self, test_client: TestClient) -> None:
        """Test health check without connection_id returns error."""
        with test_client.websocket_connect("/api/v1/ws/connections-realtime?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial connection list

            ws.send_json(
                {
                    "type": "request_health_check",
                    "id": "test-10",
                    "payload": {},
                }
            )
            response = ws.receive_json()

            assert response["type"] == "error"
            assert response["id"] == "test-10"
            assert response["payload"]["code"] == "missing_connection_id"


@pytest.mark.xdist_group(name="connections_realtime_websocket")
class TestConnectionsRealtimeErrorHandling:
    """Test error handling for connections realtime WebSocket."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_unknown_message_type_returns_error(self, test_client: TestClient) -> None:
        """Test that unknown message type returns error."""
        with test_client.websocket_connect("/api/v1/ws/connections-realtime?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial connection list

            ws.send_json(
                {
                    "type": "invalid_type",
                    "id": "test-11",
                    "payload": {},
                }
            )
            response = ws.receive_json()

            assert response["type"] == "error"
            assert response["id"] == "test-11"
            assert response["payload"]["code"] == "unknown_message_type"


@pytest.mark.xdist_group(name="connections_realtime_websocket")
class TestConnectionsRealtimeMessageFormats:
    """Test message format validation for connections realtime."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_connection_list_message_format(self, test_client: TestClient) -> None:
        """Test connection_list message format matches frontend expectations."""
        # Frontend hook (useConnectionsRealtimeWebSocket) expects:
        # {
        #   type: "connection_list",
        #   connections: [{ id, name, url, auth_type, status, ... }]
        # }
        with test_client.websocket_connect("/api/v1/ws/connections-realtime?v=1.0.0") as ws:
            response = ws.receive_json()

            # Verify structure
            assert response["type"] == "connection_list"
            assert "connections" in response
            assert isinstance(response["connections"], list)

            # Verify connection structure
            if response["connections"]:
                conn = response["connections"][0]
                assert "id" in conn
                assert "name" in conn
                assert "url" in conn
                assert "auth_type" in conn
                assert "status" in conn

    def test_connection_status_message_format(self, test_client: TestClient) -> None:
        """Test connection_status message format."""
        with test_client.websocket_connect("/api/v1/ws/connections-realtime?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial list

            ws.send_json(
                {
                    "type": "subscribe",
                    "id": "format-test",
                    "payload": {"connection_id": "conn-1"},
                }
            )
            response = ws.receive_json()

            # Verify structure
            assert response["type"] == "connection_status"
            assert "payload" in response
            assert "connection" in response["payload"]
            assert "id" in response["payload"]["connection"]

    def test_health_check_result_message_format(self, test_client: TestClient) -> None:
        """Test health_check_result message format."""
        with test_client.websocket_connect("/api/v1/ws/connections-realtime?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial list

            ws.send_json(
                {
                    "type": "request_health_check",
                    "id": "format-test-2",
                    "payload": {"connection_id": "conn-1"},
                }
            )
            response = ws.receive_json()

            # Verify structure
            assert response["type"] == "health_check_result"
            assert "payload" in response
            assert "connection_id" in response["payload"]
            assert "healthy" in response["payload"]
            assert "status" in response["payload"]
            assert "last_check" in response["payload"]

    def test_error_message_format(self, test_client: TestClient) -> None:
        """Test error message format."""
        with test_client.websocket_connect("/api/v1/ws/connections-realtime?v=1.0.0") as ws:
            ws.receive_json()  # Consume initial list

            ws.send_json(
                {
                    "type": "subscribe",
                    "id": "format-test-3",
                    "payload": {},  # Missing connection_id
                }
            )
            response = ws.receive_json()

            assert response["type"] == "error"
            assert "payload" in response
            assert "code" in response["payload"]
            assert "message" in response["payload"]
