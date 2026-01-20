"""
Tests for MCP Connections API

TDD: Tests for the /api/v1/connections endpoints implementing MCP server
connection management with OAuth2 and API Key authentication.

Follows memory safety patterns for pytest-xdist.
Uses mock repository to avoid database dependency.
"""

import gc
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.storage.models import (
    MCPConnection,
    MCPConnectionCreate,
    MCPConnectionSummary,
    MCPConnectionTestResult,
    MCPConnectionUpdate,
    OAuth2Config,
)

pytestmark = [pytest.mark.unit, pytest.mark.api]


# ============================================================================
# Mock Repository and Test Fixtures
# ============================================================================


class MockConnectionRepository:
    """In-memory mock repository for testing."""

    def __init__(self) -> None:
        self.connections: dict[str, MCPConnection] = {}
        self.api_keys: dict[str, str] = {}
        self.oauth2_states: dict[str, dict] = {}
        self.oauth2_tokens: dict[str, str] = {}

    async def create(
        self,
        data: MCPConnectionCreate,
        owner_id: str,
    ) -> MCPConnection:
        """Create a new connection."""
        connection_id = str(uuid4())
        now = datetime.now(UTC)

        oauth2_config = None
        if data.auth_type == "oauth2":
            oauth2_config = OAuth2Config(
                client_id=data.oauth2_client_id,
                scopes=data.oauth2_scopes or [],
            )

        connection = MCPConnection(
            id=connection_id,
            name=data.name,
            description=data.description,
            url=data.url,
            auth_type=data.auth_type,
            oauth2_config=oauth2_config,
            status="disconnected",
            owner_id=owner_id,
            project_id=data.project_id,
            created_at=now,
            updated_at=now,
        )

        self.connections[connection_id] = connection

        # Store API key if provided
        if data.auth_type == "api_key" and data.api_key:
            self.api_keys[connection_id] = data.api_key

        return connection

    async def get(self, connection_id: str) -> MCPConnection | None:
        """Get a connection by ID."""
        return self.connections.get(connection_id)

    async def update(
        self,
        connection_id: str,
        data: MCPConnectionUpdate,
    ) -> MCPConnection | None:
        """Update a connection."""
        connection = self.connections.get(connection_id)
        if not connection:
            return None

        updates = {}
        if data.name is not None:
            updates["name"] = data.name
        if data.description is not None:
            updates["description"] = data.description
        if data.url is not None:
            updates["url"] = data.url
        updates["updated_at"] = datetime.now(UTC)

        connection = connection.model_copy(update=updates)
        self.connections[connection_id] = connection
        return connection

    async def delete(self, connection_id: str) -> bool:
        """Delete a connection."""
        if connection_id in self.connections:
            del self.connections[connection_id]
            self.api_keys.pop(connection_id, None)
            self.oauth2_tokens.pop(connection_id, None)
            return True
        return False

    async def list(
        self,
        owner_id: str,
        cursor: str | None = None,
        limit: int = 20,
        search: str | None = None,
        status: str | None = None,
        auth_type: str | None = None,
        project_id: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[MCPConnectionSummary], str | None]:
        """List connections with filtering."""
        connections = list(self.connections.values())

        # Filter by owner
        connections = [c for c in connections if c.owner_id == owner_id]

        # Apply filters
        if status:
            connections = [c for c in connections if c.status == status]
        if auth_type:
            connections = [c for c in connections if c.auth_type == auth_type]
        if project_id:
            connections = [c for c in connections if c.project_id == project_id]
        if search:
            search_lower = search.lower()
            connections = [
                c
                for c in connections
                if search_lower in c.name.lower() or (c.description and search_lower in c.description.lower())
            ]

        # Sort
        reverse = sort_order == "desc"
        connections.sort(key=lambda c: getattr(c, sort_by, c.created_at), reverse=reverse)

        # Limit
        summaries = [c.to_summary() for c in connections[:limit]]
        return summaries, None

    async def store_api_key(self, connection_id: str, api_key: str) -> None:
        """Store API key."""
        self.api_keys[connection_id] = api_key

    async def get_api_key(self, connection_id: str) -> str | None:
        """Get API key."""
        return self.api_keys.get(connection_id)

    async def create_oauth2_state(
        self,
        connection_id: str,
        state: str,
        code_verifier: str,
        redirect_uri: str,
        popup: bool = False,
    ) -> None:
        """Create OAuth2 state."""
        self.oauth2_states[state] = {
            "connection_id": connection_id,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
            "popup": popup,
        }

    async def get_and_delete_oauth2_state(self, state: str) -> dict | None:
        """Get and delete OAuth2 state."""
        return self.oauth2_states.pop(state, None)

    async def store_oauth2_tokens(
        self,
        connection_id: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: datetime | None,
    ) -> None:
        """Store OAuth2 tokens."""
        self.oauth2_tokens[connection_id] = access_token

    async def get_oauth2_access_token(self, connection_id: str) -> str | None:
        """Get OAuth2 access token."""
        return self.oauth2_tokens.get(connection_id)

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
            if resource_count is not None:
                updates["resource_count"] = resource_count
            if prompt_count is not None:
                updates["prompt_count"] = prompt_count
            if last_error is not None:
                updates["last_error"] = last_error
            if status == "connected":
                updates["last_connected_at"] = datetime.now(UTC)
                updates["last_error"] = None
            connection = connection.model_copy(update=updates)
            self.connections[connection_id] = connection


class MockOAuth2Service:
    """Mock OAuth2 service for testing."""

    async def discover_metadata(self, url: str) -> dict:
        """Discover OAuth2 metadata."""
        return {
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
        }

    def generate_code_verifier(self) -> str:
        """Generate PKCE code verifier."""
        return "a" * 64

    def generate_code_challenge(self, verifier: str) -> str:
        """Generate PKCE code challenge."""
        return "challenge-" + verifier[:16]

    def build_authorization_url(
        self,
        authorization_endpoint: str,
        client_id: str,
        redirect_uri: str,
        scope: str,
        state: str,
        code_challenge: str,
    ) -> str:
        """Build authorization URL."""
        return f"{authorization_endpoint}?client_id={client_id}&state={state}"

    async def exchange_code(
        self,
        token_endpoint: str,
        client_id: str,
        client_secret: str | None,
        code: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> dict:
        """Exchange code for tokens."""
        return {
            "access_token": "mock-access-token",
            "refresh_token": "mock-refresh-token",
            "expires_in": 3600,
        }


class MockMCPClient:
    """Mock MCP client for connection testing."""

    async def test_connection(self, url: str, auth_header: str | None = None) -> MCPConnectionTestResult:
        """Test MCP connection."""
        return MCPConnectionTestResult(
            success=True,
            server_name="Mock MCP Server",
            server_version="1.0.0",
            tool_count=5,
            resource_count=3,
            prompt_count=2,
        )


class MockAuditLogRepository:
    """Mock audit log repository for testing."""

    async def log_event(
        self,
        event_type: str,
        resource_type: str,
        resource_id: str,
        actor_id: str,
        action: str,
        details: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Log an audit event (no-op for testing)."""
        pass


@pytest.fixture
def mock_repo():
    """Create a mock connection repository."""
    return MockConnectionRepository()


@pytest.fixture
def mock_oauth2_service():
    """Create a mock OAuth2 service."""
    return MockOAuth2Service()


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client."""
    return MockMCPClient()


@pytest.fixture
def mock_audit_repo():
    """Create a mock audit log repository."""
    return MockAuditLogRepository()


@pytest.fixture
def app(mock_repo, mock_oauth2_service, mock_mcp_client, mock_audit_repo, monkeypatch):
    """Create a test FastAPI app with the connections router."""

    # Mock rate limit decorators to be no-ops for unit tests
    # Rate limiting is tested separately in tests/middleware/test_rate_limiter.py
    def noop_decorator(func):
        """No-op decorator that just returns the function unchanged."""
        return func

    import mcp_server_langgraph.middleware.rate_limiter as rate_limiter_module

    monkeypatch.setattr(rate_limiter_module, "rate_limit_for_oauth2_start", noop_decorator)
    monkeypatch.setattr(rate_limiter_module, "rate_limit_for_oauth2_callback", noop_decorator)

    # Force reimport of connections module to use mocked decorators
    import importlib

    import mcp_server_langgraph.api.v1.connections as connections_module

    importlib.reload(connections_module)

    from mcp_server_langgraph.core.dependencies import (
        get_audit_log_repository,
        get_connection_repository,
        get_mcp_client,
        get_oauth2_service,
    )

    app = FastAPI()

    app.include_router(connections_module.connections_router)

    # Override dependencies using async functions (required for xdist safety)
    async def get_mock_repo():
        return mock_repo

    async def get_mock_oauth2():
        return mock_oauth2_service

    async def get_mock_mcp():
        return mock_mcp_client

    async def get_mock_audit():
        return mock_audit_repo

    app.dependency_overrides[get_connection_repository] = get_mock_repo
    app.dependency_overrides[get_oauth2_service] = get_mock_oauth2
    app.dependency_overrides[get_mcp_client] = get_mock_mcp
    app.dependency_overrides[get_audit_log_repository] = get_mock_audit

    # Mock authentication and authorization dependencies
    from mcp_server_langgraph.auth.dependencies import (
        get_current_user,
        require_connection_owner,
        require_connection_viewer,
    )

    # Use "user-123" to match test data created in tests (e.g., owner_id="user-123")
    mock_user = {
        "sub": "user-123",
        "preferred_username": "testuser",
        "username": "testuser",
        "email": "testuser@example.com",
        "roles": ["user"],
    }

    async def override_get_current_user():
        return mock_user

    async def override_require_connection_viewer():
        return mock_user

    async def override_require_connection_owner():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[require_connection_viewer] = override_require_connection_viewer
    app.dependency_overrides[require_connection_owner] = override_require_connection_owner

    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


# ============================================================================
# Connection CRUD Tests
# ============================================================================


@pytest.mark.xdist_group(name="connections_api")
class TestListConnections:
    """Tests for GET /connections"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_connections_empty(self, client):
        """Should return empty list when no connections exist."""
        response = client.get("/connections")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_connections_with_data(self, client, mock_repo):
        """Should return list of connections."""
        # Create test connections
        import asyncio

        async def create_connections():
            await mock_repo.create(
                MCPConnectionCreate(name="Server 1", url="https://mcp1.example.com"),
                owner_id="user-123",
            )
            await mock_repo.create(
                MCPConnectionCreate(name="Server 2", url="https://mcp2.example.com"),
                owner_id="user-123",
            )

        asyncio.run(create_connections())

        response = client.get("/connections", headers={"X-User-ID": "user-123"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

    def test_list_connections_filter_by_status(self, client, mock_repo):
        """Should filter connections by status."""
        response = client.get("/connections?status=connected")
        assert response.status_code == 200


@pytest.mark.xdist_group(name="connections_api")
class TestCreateConnection:
    """Tests for POST /connections"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_connection_no_auth(self, client):
        """Should create connection without authentication."""
        response = client.post(
            "/connections",
            json={
                "name": "Test Server",
                "url": "https://mcp.example.com",
                "auth_type": "none",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Server"
        assert data["url"] == "https://mcp.example.com"
        assert data["auth_type"] == "none"
        assert data["status"] == "disconnected"

    def test_create_connection_with_api_key(self, client):
        """Should create connection with API key authentication."""
        response = client.post(
            "/connections",
            json={
                "name": "API Key Server",
                "url": "https://mcp.example.com",
                "auth_type": "api_key",
                "api_key": "test-api-key-123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["auth_type"] == "api_key"

    def test_create_connection_with_oauth2(self, client):
        """Should create connection with OAuth2 authentication."""
        response = client.post(
            "/connections",
            json={
                "name": "OAuth2 Server",
                "url": "https://mcp.example.com",
                "auth_type": "oauth2",
                "oauth2_client_id": "client-123",
                "oauth2_scopes": ["read", "write"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["auth_type"] == "oauth2"

    def test_create_connection_validates_required_fields(self, client):
        """Should validate required fields."""
        response = client.post(
            "/connections",
            json={
                "url": "https://mcp.example.com",
                # Missing name
            },
        )
        assert response.status_code == 422  # Validation error


@pytest.mark.xdist_group(name="connections_api")
class TestGetConnection:
    """Tests for GET /connections/{id}"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_connection_exists(self, client, mock_repo):
        """Should return connection details."""
        import asyncio

        async def create():
            return await mock_repo.create(
                MCPConnectionCreate(name="Test Server", url="https://mcp.example.com"),
                owner_id="user-123",
            )

        connection = asyncio.run(create())

        response = client.get(f"/connections/{connection.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == connection.id
        assert data["name"] == "Test Server"

    def test_get_connection_not_found(self, client):
        """Should return 404 for nonexistent connection."""
        response = client.get("/connections/nonexistent-id")
        assert response.status_code == 404


@pytest.mark.xdist_group(name="connections_api")
class TestUpdateConnection:
    """Tests for PUT /connections/{id}"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_update_connection_with_valid_data_succeeds(self, client, mock_repo):
        """Should update connection fields."""
        import asyncio

        async def create():
            return await mock_repo.create(
                MCPConnectionCreate(name="Old Name", url="https://mcp.example.com"),
                owner_id="user-123",
            )

        connection = asyncio.run(create())

        response = client.put(
            f"/connections/{connection.id}",
            json={"name": "New Name", "description": "Updated description"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["description"] == "Updated description"

    def test_update_connection_not_found(self, client):
        """Should return 404 for nonexistent connection."""
        response = client.put(
            "/connections/nonexistent-id",
            json={"name": "New Name"},
        )
        assert response.status_code == 404


@pytest.mark.xdist_group(name="connections_api")
class TestDeleteConnection:
    """Tests for DELETE /connections/{id}"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_delete_connection_with_valid_id_succeeds(self, client, mock_repo):
        """Should delete connection."""
        import asyncio

        async def create():
            return await mock_repo.create(
                MCPConnectionCreate(name="Test Server", url="https://mcp.example.com"),
                owner_id="user-123",
            )

        connection = asyncio.run(create())

        response = client.delete(f"/connections/{connection.id}")
        assert response.status_code == 204

        # Verify deletion
        response = client.get(f"/connections/{connection.id}")
        assert response.status_code == 404

    def test_delete_connection_not_found(self, client):
        """Should return 404 for nonexistent connection."""
        response = client.delete("/connections/nonexistent-id")
        assert response.status_code == 404


@pytest.mark.xdist_group(name="connections_api")
class TestTestConnection:
    """Tests for POST /connections/{id}/test"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_test_connection_success(self, client, mock_repo):
        """Should test connection and return server info."""
        import asyncio

        async def create():
            return await mock_repo.create(
                MCPConnectionCreate(name="Test Server", url="https://mcp.example.com"),
                owner_id="user-123",
            )

        connection = asyncio.run(create())

        response = client.post(f"/connections/{connection.id}/test")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["server_name"] == "Mock MCP Server"
        assert data["tool_count"] == 5

    def test_test_connection_not_found(self, client):
        """Should return 404 for nonexistent connection."""
        response = client.post("/connections/nonexistent-id/test")
        assert response.status_code == 404


@pytest.mark.xdist_group(name="connections_api")
class TestOAuth2Flow:
    """Tests for OAuth2 flow endpoints"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_start_oauth2_flow(self, client, mock_repo):
        """Should start OAuth2 authorization flow."""
        import asyncio

        async def create():
            return await mock_repo.create(
                MCPConnectionCreate(
                    name="OAuth2 Server",
                    url="https://mcp.example.com",
                    auth_type="oauth2",
                    oauth2_client_id="client-123",
                ),
                owner_id="user-123",
            )

        connection = asyncio.run(create())

        response = client.post(f"/connections/{connection.id}/oauth/start")
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data

    def test_start_oauth2_flow_wrong_auth_type(self, client, mock_repo):
        """Should return 400 for non-OAuth2 connection."""
        import asyncio

        async def create():
            return await mock_repo.create(
                MCPConnectionCreate(
                    name="API Key Server",
                    url="https://mcp.example.com",
                    auth_type="api_key",
                ),
                owner_id="user-123",
            )

        connection = asyncio.run(create())

        response = client.post(f"/connections/{connection.id}/oauth/start")
        assert response.status_code == 400

    def test_oauth2_callback_stateless_success(self, client, mock_repo, mock_oauth2_service):
        """Should complete OAuth2 callback via stateless endpoint."""
        import asyncio

        async def setup():
            # Create OAuth2 connection
            connection = await mock_repo.create(
                MCPConnectionCreate(
                    name="OAuth2 Server",
                    url="https://mcp.example.com",
                    auth_type="oauth2",
                    oauth2_client_id="client-123",
                ),
                owner_id="user-123",
            )
            # Store OAuth2 state (simulating what /oauth/start does)
            await mock_repo.create_oauth2_state(
                connection.id,
                "test-state-123",
                "test-code-verifier",
                "https://app.example.com/oauth/callback",
            )
            return connection

        connection = asyncio.run(setup())

        # Call the stateless callback endpoint
        response = client.post(
            "/connections/oauth/callback",
            json={
                "code": "auth-code-from-provider",
                "state": "test-state-123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["connection_id"] == connection.id

    def test_oauth2_callback_stateless_invalid_state(self, client):
        """Should return 400 for invalid/expired state."""
        response = client.post(
            "/connections/oauth/callback",
            json={
                "code": "auth-code-from-provider",
                "state": "invalid-state-xxx",
            },
        )
        assert response.status_code == 400
        assert "Invalid or expired" in response.json()["detail"]

    def test_oauth2_callback_stateless_missing_code(self, client):
        """Should return 422 when code is missing."""
        response = client.post(
            "/connections/oauth/callback",
            json={
                "state": "test-state-123",
            },
        )
        assert response.status_code == 422

    def test_oauth2_callback_stateless_missing_state(self, client):
        """Should return 422 when state is missing."""
        response = client.post(
            "/connections/oauth/callback",
            json={
                "code": "auth-code-from-provider",
            },
        )
        assert response.status_code == 422


@pytest.mark.xdist_group(name="connections_api")
class TestConnectionFiltering:
    """Tests for connection filtering and search"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_filter_by_auth_type(self, client, mock_repo):
        """Should filter by authentication type."""
        import asyncio

        async def create():
            await mock_repo.create(
                MCPConnectionCreate(
                    name="OAuth Server",
                    url="https://oauth.example.com",
                    auth_type="oauth2",
                    oauth2_client_id="client-1",
                ),
                owner_id="user-123",
            )
            await mock_repo.create(
                MCPConnectionCreate(
                    name="API Key Server",
                    url="https://api.example.com",
                    auth_type="api_key",
                ),
                owner_id="user-123",
            )

        asyncio.run(create())

        response = client.get("/connections?auth_type=oauth2", headers={"X-User-ID": "user-123"})
        assert response.status_code == 200
        data = response.json()
        assert all(c["auth_type"] == "oauth2" for c in data["items"])

    def test_search_connections_by_name_filters_correctly(self, client, mock_repo):
        """Should search connections by name."""
        import asyncio

        async def create():
            await mock_repo.create(
                MCPConnectionCreate(name="Production Server", url="https://prod.example.com"),
                owner_id="user-123",
            )
            await mock_repo.create(
                MCPConnectionCreate(name="Development Server", url="https://dev.example.com"),
                owner_id="user-123",
            )

        asyncio.run(create())

        response = client.get("/connections?search=production", headers={"X-User-ID": "user-123"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert "Production" in data["items"][0]["name"]


@pytest.mark.xdist_group(name="connections_api")
class TestConnectionSorting:
    """Tests for connection sorting functionality"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_sort_by_name_asc(self, client, mock_repo):
        """Should sort connections by name ascending."""
        import asyncio

        async def create():
            await mock_repo.create(
                MCPConnectionCreate(name="Zebra Server", url="https://z.example.com"),
                owner_id="user-123",
            )
            await mock_repo.create(
                MCPConnectionCreate(name="Alpha Server", url="https://a.example.com"),
                owner_id="user-123",
            )
            await mock_repo.create(
                MCPConnectionCreate(name="Beta Server", url="https://b.example.com"),
                owner_id="user-123",
            )

        asyncio.run(create())

        response = client.get(
            "/connections?sort_by=name&sort_order=asc",
            headers={"X-User-ID": "user-123"},
        )
        assert response.status_code == 200
        data = response.json()
        names = [item["name"] for item in data["items"]]
        assert names == ["Alpha Server", "Beta Server", "Zebra Server"]

    def test_sort_by_name_desc(self, client, mock_repo):
        """Should sort connections by name descending."""
        import asyncio

        async def create():
            await mock_repo.create(
                MCPConnectionCreate(name="Alpha Server", url="https://a.example.com"),
                owner_id="user-123",
            )
            await mock_repo.create(
                MCPConnectionCreate(name="Zebra Server", url="https://z.example.com"),
                owner_id="user-123",
            )

        asyncio.run(create())

        response = client.get(
            "/connections?sort_by=name&sort_order=desc",
            headers={"X-User-ID": "user-123"},
        )
        assert response.status_code == 200
        data = response.json()
        names = [item["name"] for item in data["items"]]
        assert names == ["Zebra Server", "Alpha Server"]

    def test_sort_by_created_at_desc(self, client, mock_repo):
        """Should sort connections by created_at descending (default)."""
        import asyncio
        import time

        async def create():
            await mock_repo.create(
                MCPConnectionCreate(name="First Server", url="https://first.example.com"),
                owner_id="user-123",
            )
            # Small delay to ensure different timestamps
            time.sleep(0.01)
            await mock_repo.create(
                MCPConnectionCreate(name="Second Server", url="https://second.example.com"),
                owner_id="user-123",
            )

        asyncio.run(create())

        response = client.get(
            "/connections?sort_by=created_at&sort_order=desc",
            headers={"X-User-ID": "user-123"},
        )
        assert response.status_code == 200
        data = response.json()
        names = [item["name"] for item in data["items"]]
        assert names[0] == "Second Server"  # Most recent first

    def test_sort_by_status(self, client, mock_repo):
        """Should sort connections by status."""
        import asyncio

        async def create():
            _ = await mock_repo.create(
                MCPConnectionCreate(name="Disconnected Server", url="https://dc.example.com"),
                owner_id="user-123",
            )
            conn2 = await mock_repo.create(
                MCPConnectionCreate(name="Connected Server", url="https://c.example.com"),
                owner_id="user-123",
            )
            # Update conn2 to connected status
            await mock_repo.update_status(conn2.id, "connected")

        asyncio.run(create())

        response = client.get(
            "/connections?sort_by=status&sort_order=asc",
            headers={"X-User-ID": "user-123"},
        )
        assert response.status_code == 200
        data = response.json()
        statuses = [item["status"] for item in data["items"]]
        assert statuses == sorted(statuses)

    def test_default_sort_created_at_desc(self, client, mock_repo):
        """Should default to sorting by created_at descending."""
        import asyncio
        import time

        async def create():
            await mock_repo.create(
                MCPConnectionCreate(name="Old Server", url="https://old.example.com"),
                owner_id="user-123",
            )
            time.sleep(0.01)
            await mock_repo.create(
                MCPConnectionCreate(name="New Server", url="https://new.example.com"),
                owner_id="user-123",
            )

        asyncio.run(create())

        # No sort parameters - should default to created_at desc
        response = client.get("/connections", headers={"X-User-ID": "user-123"})
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["name"] == "New Server"

    def test_invalid_sort_by_rejected(self, client):
        """Should reject invalid sort_by values."""
        response = client.get("/connections?sort_by=invalid_field")
        assert response.status_code == 422  # Validation error

    def test_invalid_sort_order_rejected(self, client):
        """Should reject invalid sort_order values."""
        response = client.get("/connections?sort_order=invalid")
        assert response.status_code == 422  # Validation error


@pytest.mark.xdist_group(name="connections_api")
class TestConnectionPagination:
    """Tests for connection pagination functionality"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_limit_parameter_restricts_result_count(self, client, mock_repo):
        """Should limit number of returned connections."""
        import asyncio

        async def create():
            for i in range(10):
                await mock_repo.create(
                    MCPConnectionCreate(name=f"Server {i}", url=f"https://s{i}.example.com"),
                    owner_id="user-123",
                )

        asyncio.run(create())

        response = client.get("/connections?limit=5", headers={"X-User-ID": "user-123"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5

    def test_limit_min_value(self, client):
        """Should enforce minimum limit of 1."""
        response = client.get("/connections?limit=0")
        assert response.status_code == 422  # Validation error

    def test_limit_max_value(self, client):
        """Should enforce maximum limit of 100."""
        response = client.get("/connections?limit=101")
        assert response.status_code == 422  # Validation error

    def test_default_limit_returns_twenty_results(self, client, mock_repo):
        """Should use default limit of 20."""
        import asyncio

        async def create():
            for i in range(30):
                await mock_repo.create(
                    MCPConnectionCreate(name=f"Server {i}", url=f"https://s{i}.example.com"),
                    owner_id="user-123",
                )

        asyncio.run(create())

        response = client.get("/connections", headers={"X-User-ID": "user-123"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 20  # Default limit


@pytest.mark.xdist_group(name="connections_api")
class TestConnectionSearchValidation:
    """Tests for search parameter validation"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_search_min_length(self, client):
        """Should reject empty search string (min_length=1)."""
        response = client.get("/connections?search=")
        # Empty search should be rejected with validation error
        assert response.status_code == 422  # Validation error

    def test_search_case_insensitive(self, client, mock_repo):
        """Should perform case-insensitive search."""
        import asyncio

        async def create():
            await mock_repo.create(
                MCPConnectionCreate(name="UPPERCASE Server", url="https://upper.example.com"),
                owner_id="user-123",
            )

        asyncio.run(create())

        response = client.get("/connections?search=uppercase", headers={"X-User-ID": "user-123"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

    def test_search_in_description(self, client, mock_repo):
        """Should search in description field."""
        import asyncio

        async def create():
            await mock_repo.create(
                MCPConnectionCreate(
                    name="My Server",
                    description="Production environment server",
                    url="https://prod.example.com",
                ),
                owner_id="user-123",
            )

        asyncio.run(create())

        response = client.get(
            "/connections?search=production",
            headers={"X-User-ID": "user-123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
