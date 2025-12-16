"""
Tests for MCP Connections Bulk Operations API

TDD: Tests for bulk operations on MCP connections:
- Bulk delete
- Bulk test (health check)
- Bulk status update

Follows memory safety patterns for pytest-xdist.

NOTE: These tests are skipped in xdist parallel mode because the
CachedConnectionRepository import triggers Redis/DB connection attempts
at module level, which can fail when tests run in parallel workers
without infrastructure access.
"""

import gc
import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.storage.models import (
    MCPConnection,
    MCPConnectionCreate,
    MCPConnectionTestResult,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


@pytest.fixture(autouse=True)
def skip_in_xdist_worker():
    """Skip tests in xdist worker environment.

    The CachedConnectionRepository import triggers Redis/DB connection attempts
    at module level, which fail when tests run in parallel workers without
    infrastructure access. This fixture checks at runtime (not import time)
    so the skip works correctly in xdist.
    """
    if os.getenv("PYTEST_XDIST_WORKER") is not None:
        pytest.skip("CachedConnectionRepository import triggers Redis/DB connection in xdist")


# ============================================================================
# Mock Repository and Test Fixtures
# ============================================================================


class MockConnectionRepository:
    """In-memory mock repository for testing bulk operations."""

    def __init__(self) -> None:
        self.connections: dict[str, MCPConnection] = {}
        self.deleted_ids: list[str] = []

    async def create(
        self,
        data: MCPConnectionCreate,
        owner_id: str,
    ) -> MCPConnection:
        """Create a new connection."""
        connection_id = str(uuid4())
        now = datetime.now(UTC)

        connection = MCPConnection(
            id=connection_id,
            name=data.name,
            description=data.description,
            url=data.url,
            auth_type=data.auth_type or "none",
            status="disconnected",
            owner_id=owner_id,
            project_id=data.project_id,
            created_at=now,
            updated_at=now,
        )

        self.connections[connection_id] = connection
        return connection

    async def get(self, connection_id: str) -> MCPConnection | None:
        """Get a connection by ID."""
        return self.connections.get(connection_id)

    async def get_many(self, connection_ids: list[str]) -> list[MCPConnection]:
        """Get multiple connections by their IDs."""
        return [c for cid, c in self.connections.items() if cid in connection_ids]

    async def delete(self, connection_id: str) -> bool:
        """Delete a connection."""
        if connection_id in self.connections:
            del self.connections[connection_id]
            self.deleted_ids.append(connection_id)
            return True
        return False

    async def delete_many(self, connection_ids: list[str]) -> int:
        """Delete multiple connections."""
        count = 0
        for cid in connection_ids:
            if cid in self.connections:
                del self.connections[cid]
                self.deleted_ids.append(cid)
                count += 1
        return count

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
    ) -> None:
        """Update connection status."""
        connection = self.connections.get(connection_id)
        if connection:
            updates = {"status": status, "updated_at": datetime.now(UTC)}
            if server_name is not None:
                updates["server_name"] = server_name
            if server_version is not None:
                updates["server_version"] = server_version
            if tool_count is not None:
                updates["tool_count"] = tool_count
            if last_error is not None:
                updates["last_error"] = last_error
            if status == "connected":
                updates["last_connected_at"] = datetime.now(UTC)
                updates["last_error"] = None
            connection = connection.model_copy(update=updates)
            self.connections[connection_id] = connection


class MockMCPClient:
    """Mock MCP client for connection testing."""

    def __init__(self) -> None:
        self.test_results: dict[str, MCPConnectionTestResult] = {}

    def set_result(self, url: str, success: bool, error: str | None = None):
        """Set the test result for a URL."""
        self.test_results[url] = MCPConnectionTestResult(
            success=success,
            server_name="Mock Server" if success else None,
            server_version="1.0.0" if success else None,
            tool_count=5 if success else 0,
            resource_count=3 if success else 0,
            prompt_count=2 if success else 0,
            error=error,
        )

    async def test_connection(self, url: str, auth_header: str | None = None) -> MCPConnectionTestResult:
        """Test MCP connection."""
        if url in self.test_results:
            return self.test_results[url]
        return MCPConnectionTestResult(
            success=True,
            server_name="Mock MCP Server",
            server_version="1.0.0",
            tool_count=5,
            resource_count=3,
            prompt_count=2,
        )


@pytest.fixture
def mock_repo():
    """Create a mock connection repository."""
    return MockConnectionRepository()


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client."""
    return MockMCPClient()


@pytest.fixture
def app(mock_repo, mock_mcp_client):
    """Create a test FastAPI app with the connections router."""
    # Import here to ensure fresh module state
    from mcp_server_langgraph.api.v1.connections_bulk import bulk_router
    from mcp_server_langgraph.core.dependencies import (
        get_connection_repository,
        get_db_session,
        get_mcp_client,
    )

    app = FastAPI()
    app.include_router(bulk_router)

    # Override dependencies - including get_db_session to prevent any DB connections
    # during xdist parallel runs where global state may be polluted
    app.dependency_overrides[get_connection_repository] = lambda: mock_repo
    app.dependency_overrides[get_mcp_client] = lambda: mock_mcp_client
    app.dependency_overrides[get_db_session] = lambda: None  # Ensure no DB access

    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


# ============================================================================
# Bulk Delete Tests
# ============================================================================


@pytest.mark.xdist_group(name="connections_bulk_api")
class TestBulkDelete:
    """Tests for POST /connections/bulk/delete"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_bulk_delete_success(self, client, mock_repo):
        """Should delete multiple connections."""
        import asyncio

        async def create():
            c1 = await mock_repo.create(
                MCPConnectionCreate(name="Server 1", url="https://s1.example.com"),
                owner_id="user-123",
            )
            c2 = await mock_repo.create(
                MCPConnectionCreate(name="Server 2", url="https://s2.example.com"),
                owner_id="user-123",
            )
            c3 = await mock_repo.create(
                MCPConnectionCreate(name="Server 3", url="https://s3.example.com"),
                owner_id="user-123",
            )
            return [c1.id, c2.id, c3.id]

        ids = asyncio.run(create())

        response = client.post(
            "/connections/bulk/delete",
            json={"connection_ids": ids[:2]},  # Delete first 2
        )

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 2
        assert len(mock_repo.connections) == 1

    def test_bulk_delete_empty_list(self, client):
        """Should return 422 for empty connection_ids."""
        response = client.post(
            "/connections/bulk/delete",
            json={"connection_ids": []},
        )
        assert response.status_code == 422

    def test_bulk_delete_partial_success(self, client, mock_repo):
        """Should handle partial success (some IDs don't exist)."""
        import asyncio

        async def create():
            c1 = await mock_repo.create(
                MCPConnectionCreate(name="Server 1", url="https://s1.example.com"),
                owner_id="user-123",
            )
            return c1.id

        existing_id = asyncio.run(create())

        response = client.post(
            "/connections/bulk/delete",
            json={"connection_ids": [existing_id, "nonexistent-id"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 1
        assert "nonexistent-id" in data["failed_ids"]

    def test_bulk_delete_max_limit(self, client):
        """Should enforce maximum limit on bulk delete."""
        # Try to delete more than allowed (100)
        response = client.post(
            "/connections/bulk/delete",
            json={"connection_ids": [f"id-{i}" for i in range(101)]},
        )
        assert response.status_code == 422


# ============================================================================
# Bulk Test (Health Check) Tests
# ============================================================================


@pytest.mark.xdist_group(name="connections_bulk_api")
class TestBulkTest:
    """Tests for POST /connections/bulk/test"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_bulk_test_success(self, client, mock_repo):
        """Should test multiple connections."""
        import asyncio

        async def create():
            c1 = await mock_repo.create(
                MCPConnectionCreate(name="Server 1", url="https://s1.example.com"),
                owner_id="user-123",
            )
            c2 = await mock_repo.create(
                MCPConnectionCreate(name="Server 2", url="https://s2.example.com"),
                owner_id="user-123",
            )
            return [c1.id, c2.id]

        ids = asyncio.run(create())

        response = client.post(
            "/connections/bulk/test",
            json={"connection_ids": ids},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        assert all(r["success"] for r in data["results"])

    def test_bulk_test_mixed_results(self, client, mock_repo, mock_mcp_client):
        """Should return mixed success/failure results."""
        import asyncio

        async def create():
            c1 = await mock_repo.create(
                MCPConnectionCreate(name="Server 1", url="https://success.example.com"),
                owner_id="user-123",
            )
            c2 = await mock_repo.create(
                MCPConnectionCreate(name="Server 2", url="https://failure.example.com"),
                owner_id="user-123",
            )
            return [c1.id, c2.id]

        ids = asyncio.run(create())

        # Set one to fail
        mock_mcp_client.set_result("https://failure.example.com", False, "Connection refused")

        response = client.post(
            "/connections/bulk/test",
            json={"connection_ids": ids},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        results_by_success = {r["connection_id"]: r["success"] for r in data["results"]}
        assert any(not s for s in results_by_success.values())

    def test_bulk_test_not_found(self, client):
        """Should handle nonexistent connections gracefully."""
        response = client.post(
            "/connections/bulk/test",
            json={"connection_ids": ["nonexistent-1", "nonexistent-2"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 0
        assert len(data["not_found"]) == 2

    def test_bulk_test_empty_list(self, client):
        """Should return 422 for empty connection_ids."""
        response = client.post(
            "/connections/bulk/test",
            json={"connection_ids": []},
        )
        assert response.status_code == 422


# ============================================================================
# Bulk Status Update Tests
# ============================================================================


@pytest.mark.xdist_group(name="connections_bulk_api")
class TestBulkStatusUpdate:
    """Tests for POST /connections/bulk/status"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_bulk_disconnect_with_valid_ids_succeeds(self, client, mock_repo):
        """Should disconnect multiple connections."""
        import asyncio

        async def create():
            c1 = await mock_repo.create(
                MCPConnectionCreate(name="Server 1", url="https://s1.example.com"),
                owner_id="user-123",
            )
            c2 = await mock_repo.create(
                MCPConnectionCreate(name="Server 2", url="https://s2.example.com"),
                owner_id="user-123",
            )
            # Mark as connected
            await mock_repo.update_status(c1.id, "connected")
            await mock_repo.update_status(c2.id, "connected")
            return [c1.id, c2.id]

        ids = asyncio.run(create())

        response = client.post(
            "/connections/bulk/status",
            json={
                "connection_ids": ids,
                "status": "disconnected",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 2

        # Verify status changed
        import asyncio

        connections = asyncio.run(mock_repo.get_many(ids))
        assert all(c.status == "disconnected" for c in connections)

    def test_bulk_status_update_invalid_status(self, client):
        """Should reject invalid status values."""
        response = client.post(
            "/connections/bulk/status",
            json={
                "connection_ids": ["id-1"],
                "status": "invalid_status",
            },
        )
        assert response.status_code == 422
