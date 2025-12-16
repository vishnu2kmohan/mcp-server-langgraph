"""
Tests for Connection Health WebSocket Endpoint

TDD: Tests for real-time connection health monitoring via WebSocket.
Follows memory safety patterns for pytest-xdist.

Features tested:
- WebSocket connection establishment
- Health status broadcasting
- Individual connection health updates
- Heartbeat/ping-pong mechanism
- Graceful disconnection handling

XDIST SKIP NOTE:
================
These tests are skipped in pytest-xdist when infrastructure is unavailable.
The router imports trigger singleton creation (cache, database session) that
attempt infrastructure connections. In xdist mode without infrastructure,
this causes OSError: [Errno 111] Connect call failed.

The tests pass in isolation (`pytest tests/api/test_connection_health_websocket.py`).
Skip applies only when:
1. Running in xdist (PYTEST_XDIST_WORKER is set)
2. PostgreSQL not available on port 5432
"""

import gc
import os
import socket
from datetime import UTC, datetime
from uuid import uuid4

import pytest


def _check_infrastructure_for_xdist_skip() -> bool:
    """Check if we should skip this module due to xdist infrastructure constraints.

    Returns True if:
    1. Running in xdist (PYTEST_XDIST_WORKER is set)
    2. PostgreSQL not available on default port 5432

    In xdist mode, router imports trigger singleton creation that attempts
    infrastructure connections, causing failures when infrastructure is unavailable.
    """
    worker_id = os.environ.get("PYTEST_XDIST_WORKER")
    if worker_id is None:
        return False

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex(("127.0.0.1", 5432))
        sock.close()
        return result != 0
    except Exception:
        return True


if _check_infrastructure_for_xdist_skip():
    pytest.skip(
        "Skipping in xdist: infrastructure unavailable on default ports. "
        "Router imports trigger singleton creation that attempts infrastructure "
        "connections. Test passes in isolation.",
        allow_module_level=True,
    )


from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.storage.models import (
    MCPConnection,
    MCPConnectionSummary,
    OAuth2Config,
)

pytestmark = [pytest.mark.unit, pytest.mark.api, pytest.mark.websocket]


# NOTE: Auth and database singletons are reset by the central
# reset_dependency_singletons fixture in tests/conftest.py


# ============================================================================
# Mock Repository
# ============================================================================


class MockConnectionRepository:
    """In-memory mock repository for testing."""

    def __init__(self) -> None:
        self.connections: dict[str, MCPConnection] = {}

    async def list(
        self,
        owner_id: str | None = None,
        cursor: str | None = None,
        limit: int = 50,
        search: str | None = None,
        status: str | None = None,
        auth_type: str | None = None,
        project_id: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[MCPConnectionSummary], str | None]:
        """List all connections as summaries."""
        summaries = [
            MCPConnectionSummary(
                id=c.id,
                name=c.name,
                url=c.url,
                transport=getattr(c, "transport", "streamable_http"),
                auth_type=c.auth_type,
                status=c.status,
                server_name=c.server_name,
                tool_count=c.tool_count or 0,
                resource_count=c.resource_count or 0,
                prompt_count=c.prompt_count or 0,
                created_at=c.created_at,
            )
            for c in self.connections.values()
        ]
        return summaries, None

    async def get(self, connection_id: str) -> MCPConnection | None:
        """Get a connection by ID."""
        return self.connections.get(connection_id)

    async def update_status(
        self,
        connection_id: str,
        status: str,
        server_name: str | None = None,
        server_version: str | None = None,
        tool_count: int | None = None,
        resource_count: int | None = None,
        prompt_count: int | None = None,
        last_error: str | None = None,
    ) -> MCPConnection | None:
        """Update connection status."""
        connection = self.connections.get(connection_id)
        if connection:
            self.connections[connection_id] = MCPConnection(**{**connection.model_dump(), "status": status})
        return self.connections.get(connection_id)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_repo() -> MockConnectionRepository:
    """Create a mock repository with sample connections."""
    repo = MockConnectionRepository()

    # Add some test connections
    now = datetime.now(UTC)
    connections = [
        MCPConnection(
            id=str(uuid4()),
            name="GitHub MCP",
            description="GitHub integration",
            url="https://github-mcp.example.com",
            auth_type="oauth2",
            oauth2_config=OAuth2Config(
                client_id="github-client",
                scopes=["repo", "user"],
            ),
            status="connected",
            server_name="github-mcp-server",
            server_version="1.0.0",
            tool_count=5,
            resource_count=3,
            prompt_count=2,
            owner_id="user-123",
            created_at=now,
            updated_at=now,
        ),
        MCPConnection(
            id=str(uuid4()),
            name="Slack MCP",
            description="Slack integration",
            url="https://slack-mcp.example.com",
            auth_type="api_key",
            status="disconnected",
            owner_id="user-123",
            created_at=now,
            updated_at=now,
        ),
        MCPConnection(
            id=str(uuid4()),
            name="Local MCP",
            description="Local development server",
            url="http://localhost:3000",
            auth_type="none",
            status="error",
            last_error="Connection refused",
            owner_id="user-123",
            created_at=now,
            updated_at=now,
        ),
    ]

    for conn in connections:
        repo.connections[conn.id] = conn

    return repo


@pytest.fixture
def app(mock_repo: MockConnectionRepository) -> FastAPI:
    """Create a test FastAPI app with the health WebSocket endpoint."""
    from mcp_server_langgraph.api.v1.connection_health_ws import (
        connection_health_router,
    )
    from mcp_server_langgraph.auth.middleware import get_current_user
    from mcp_server_langgraph.core.dependencies import get_connection_repository

    test_app = FastAPI()

    # Override dependencies using async functions (required for xdist safety)
    async def get_mock_repo():
        return mock_repo

    async def get_mock_user():
        return {
            "user_id": "user-123",
            "sub": "user-123",
            "username": "testuser",
            "email": "test@example.com",
            "roles": ["user"],
        }

    test_app.dependency_overrides[get_connection_repository] = get_mock_repo
    test_app.dependency_overrides[get_current_user] = get_mock_user

    test_app.include_router(connection_health_router, prefix="/api/v1")

    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


# ============================================================================
# WebSocket Connection Tests
# ============================================================================


@pytest.mark.xdist_group(name="connection_health_ws")
class TestWebSocketConnection:
    """Tests for WebSocket connection establishment."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_connect_success(self, client: TestClient) -> None:
        """Should successfully establish WebSocket connection."""
        with client.websocket_connect("/api/v1/connections/health/ws") as websocket:
            # Should receive initial status message
            data = websocket.receive_json()
            assert data["type"] == "connection_status"
            assert "connections" in data
            assert isinstance(data["connections"], list)

    def test_websocket_receives_initial_status(self, client: TestClient, mock_repo: MockConnectionRepository) -> None:
        """Should receive all connection statuses on connect."""
        with client.websocket_connect("/api/v1/connections/health/ws") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connection_status"
            assert len(data["connections"]) == 3

            # Verify connection data structure
            conn = data["connections"][0]
            assert "id" in conn
            assert "name" in conn
            assert "status" in conn
            assert "url" in conn

    def test_websocket_status_includes_health_metrics(self, client: TestClient) -> None:
        """Should include health metrics in status."""
        with client.websocket_connect("/api/v1/connections/health/ws") as websocket:
            data = websocket.receive_json()

            # Find a connected connection
            connected = next((c for c in data["connections"] if c["status"] == "connected"), None)
            assert connected is not None
            assert "tool_count" in connected
            assert "server_name" in connected


# ============================================================================
# Health Update Broadcasting Tests
# ============================================================================


@pytest.mark.xdist_group(name="connection_health_ws")
class TestHealthBroadcasting:
    """Tests for health status broadcasting."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_heartbeat_returns_pong_on_ping(self, client: TestClient) -> None:
        """Should receive pong response when sending ping."""
        with client.websocket_connect("/api/v1/connections/health/ws") as websocket:
            # Receive initial status
            websocket.receive_json()

            # Send ping, expect pong
            websocket.send_json({"type": "ping"})
            data = websocket.receive_json()
            assert data["type"] == "pong"

    def test_can_request_refresh(self, client: TestClient) -> None:
        """Should refresh status when requested."""
        with client.websocket_connect("/api/v1/connections/health/ws") as websocket:
            # Receive initial status
            websocket.receive_json()

            # Request refresh
            websocket.send_json({"type": "refresh"})
            data = websocket.receive_json()
            assert data["type"] == "connection_status"

    def test_can_subscribe_to_specific_connection(self, client: TestClient, mock_repo: MockConnectionRepository) -> None:
        """Should allow subscribing to specific connection updates."""
        conn_id = list(mock_repo.connections.keys())[0]

        with client.websocket_connect("/api/v1/connections/health/ws") as websocket:
            # Receive initial status
            websocket.receive_json()

            # Subscribe to specific connection
            websocket.send_json({"type": "subscribe", "connection_id": conn_id})
            data = websocket.receive_json()
            assert data["type"] == "subscribed"
            assert data["connection_id"] == conn_id


# ============================================================================
# Connection Health Check Tests
# ============================================================================


@pytest.mark.xdist_group(name="connection_health_ws")
class TestConnectionHealthCheck:
    """Tests for individual connection health checks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_request_health_check(self, client: TestClient, mock_repo: MockConnectionRepository) -> None:
        """Should trigger health check for specific connection."""
        conn_id = list(mock_repo.connections.keys())[0]

        with client.websocket_connect("/api/v1/connections/health/ws") as websocket:
            # Receive initial status
            websocket.receive_json()

            # Request health check
            websocket.send_json({"type": "check_health", "connection_id": conn_id})
            data = websocket.receive_json()
            assert data["type"] in ["health_check_started", "health_check_result"]

    def test_health_check_unknown_connection(self, client: TestClient) -> None:
        """Should handle unknown connection gracefully."""
        with client.websocket_connect("/api/v1/connections/health/ws") as websocket:
            # Receive initial status
            websocket.receive_json()

            # Request health check for unknown connection
            websocket.send_json({"type": "check_health", "connection_id": "unknown-id"})
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "not found" in data["message"].lower()


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.xdist_group(name="connection_health_ws")
class TestErrorHandling:
    """Tests for error handling in WebSocket communication."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_handles_invalid_json(self, client: TestClient) -> None:
        """Should handle invalid JSON gracefully."""
        with client.websocket_connect("/api/v1/connections/health/ws") as websocket:
            # Receive initial status
            websocket.receive_json()

            # Send invalid message (not JSON-RPC format)
            websocket.send_text("not valid json")
            data = websocket.receive_json()
            assert data["type"] == "error"

    def test_handles_unknown_message_type(self, client: TestClient) -> None:
        """Should handle unknown message types."""
        with client.websocket_connect("/api/v1/connections/health/ws") as websocket:
            # Receive initial status
            websocket.receive_json()

            # Send unknown message type
            websocket.send_json({"type": "unknown_action"})
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "unknown" in data["message"].lower()


# ============================================================================
# Connection Status Summary Tests
# ============================================================================


@pytest.mark.xdist_group(name="connection_health_ws")
class TestConnectionStatusSummary:
    """Tests for connection status summary endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_health_summary(self, client: TestClient) -> None:
        """Should return aggregated health summary via REST endpoint."""
        response = client.get("/api/v1/connections/health/summary")
        assert response.status_code == 200

        data = response.json()
        assert "total" in data
        assert "connected" in data
        assert "disconnected" in data
        assert "error" in data
        assert data["total"] == 3
        assert data["connected"] == 1
        assert data["disconnected"] == 1
        assert data["error"] == 1

    def test_health_summary_includes_last_check(self, client: TestClient) -> None:
        """Should include timestamp of last health check."""
        response = client.get("/api/v1/connections/health/summary")
        assert response.status_code == 200

        data = response.json()
        assert "last_check" in data
