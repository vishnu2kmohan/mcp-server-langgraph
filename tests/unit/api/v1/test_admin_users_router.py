"""
Tests for Admin Users Router

TDD tests for /api/v1/admin/users endpoints.
Provides CRUD operations for user management by administrators.

PYTEST-XDIST FIX (2025-12-16): Reset singleton dependencies before each test
to prevent state pollution from xdist workers that may have created real
providers before the test's dependency_overrides take effect.
"""

import gc
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.auth.user_provider import UserData
from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_admin_users_router")
class TestAdminUsersListEndpoint:
    """Tests for GET /api/v1/admin/users endpoint.

    PYTEST-XDIST FIX (2025-12-16): Uses dual mocking strategy for xdist reliability:
    1. Reset singletons to clear any cached providers from other tests
    2. Set _user_provider singleton directly to bypass get_user_provider() call entirely
    3. Also set dependency_overrides as a safety net

    This ensures the mock is used regardless of how FastAPI resolves the dependency.
    """

    def setup_method(self) -> None:
        """Reset singletons before each test to ensure clean state."""
        reset_singleton_dependencies()

    def teardown_method(self) -> None:
        """Force GC and reset singletons to prevent mock accumulation."""
        reset_singleton_dependencies()
        gc.collect()

    def _create_mock_user_provider(self, users: list[UserData] | None = None) -> AsyncMock:
        """Create a mock user provider."""
        mock_provider = AsyncMock(return_value=None)  # async-mock-configured  # noqa: async-mock-config
        mock_provider.list_users.return_value = users or []
        return mock_provider

    def _create_app(self, mock_provider: AsyncMock | None = None) -> FastAPI:
        """Create a FastAPI app with the admin router.

        Uses dual mocking strategy for xdist reliability:
        1. Sets _user_provider singleton directly in dependencies module
        2. Sets dependency_overrides as a safety net

        AUTH UPDATE (2025-12-29):
        ========================
        Admin endpoints now require authentication via require_admin dependency.
        We mock this to return an admin user for testing.
        """
        import mcp_server_langgraph.core.dependencies as deps_module
        from mcp_server_langgraph.api.v1.admin import admin_router
        from mcp_server_langgraph.auth.dependencies import require_admin
        from mcp_server_langgraph.core.dependencies import get_user_provider

        app = FastAPI()
        app.include_router(admin_router, prefix="/api/v1")

        if mock_provider:
            # Strategy 1: Set the singleton directly (bypasses get_user_provider logic)
            deps_module._user_provider = mock_provider
            # Strategy 2: Also set dependency override as safety net
            app.dependency_overrides[get_user_provider] = lambda: mock_provider

        # Mock admin authentication - return a mock admin user
        mock_admin_user = {
            "sub": "admin-user-id",
            "user_id": "admin-user-id",
            "username": "admin",
            "roles": ["admin"],
            "realm_access": {"roles": ["admin"]},
        }
        app.dependency_overrides[require_admin] = lambda: mock_admin_user

        return app

    def _create_client(self, mock_provider: AsyncMock | None = None) -> TestClient:
        """Create a test client for the admin API."""
        return TestClient(self._create_app(mock_provider))

    @pytest.mark.asyncio
    async def test_list_users_returns_200(self) -> None:
        """GET /api/v1/admin/users should return 200."""
        mock_provider = self._create_mock_user_provider([])
        client = self._create_client(mock_provider)
        response = client.get("/api/v1/admin/users")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_users_returns_all_users(self) -> None:
        """GET /api/v1/admin/users should return all users."""
        mock_users = [
            UserData(user_id="user:alice", username="alice", email="alice@test.com", roles=["admin"], active=True),
            UserData(user_id="user:bob", username="bob", email="bob@test.com", roles=["user"], active=True),
        ]
        mock_provider = self._create_mock_user_provider(mock_users)
        client = self._create_client(mock_provider)
        response = client.get("/api/v1/admin/users")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2
        assert data["items"][0]["username"] == "alice"
        assert data["items"][1]["username"] == "bob"

    @pytest.mark.asyncio
    async def test_list_users_with_search_filter(self) -> None:
        """GET /api/v1/admin/users?search=alice should filter by search."""
        mock_users = [
            UserData(user_id="user:alice", username="alice", email="alice@test.com", roles=["admin"], active=True),
        ]
        mock_provider = self._create_mock_user_provider(mock_users)
        client = self._create_client(mock_provider)
        response = client.get("/api/v1/admin/users?search=alice")

        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_admin_users_router")
class TestAdminUserGetEndpoint:
    """Tests for GET /api/v1/admin/users/{user_id} endpoint."""

    def setup_method(self) -> None:
        """Reset singletons before each test to ensure clean state."""
        reset_singleton_dependencies()

    def teardown_method(self) -> None:
        """Force GC and reset singletons to prevent mock accumulation."""
        reset_singleton_dependencies()
        gc.collect()

    def _create_mock_user_provider(self, user: UserData | None = None) -> AsyncMock:
        """Create a mock user provider."""
        mock_provider = AsyncMock(return_value=None)  # async-mock-configured  # noqa: async-mock-config
        mock_provider.get_user_by_id.return_value = user
        mock_provider.get_user_by_username.return_value = user
        return mock_provider

    def _create_app(self, mock_provider: AsyncMock | None = None) -> FastAPI:
        """Create a FastAPI app with the admin router."""
        import mcp_server_langgraph.core.dependencies as deps_module
        from mcp_server_langgraph.api.v1.admin import admin_router
        from mcp_server_langgraph.auth.dependencies import require_admin
        from mcp_server_langgraph.core.dependencies import get_user_provider

        app = FastAPI()
        app.include_router(admin_router, prefix="/api/v1")

        if mock_provider:
            # Dual mocking strategy for xdist reliability
            deps_module._user_provider = mock_provider
            app.dependency_overrides[get_user_provider] = lambda: mock_provider

        # Mock admin authentication
        mock_admin_user = {
            "sub": "admin-user-id",
            "user_id": "admin-user-id",
            "username": "admin",
            "roles": ["admin"],
            "realm_access": {"roles": ["admin"]},
        }
        app.dependency_overrides[require_admin] = lambda: mock_admin_user

        return app

    def _create_client(self, mock_provider: AsyncMock | None = None) -> TestClient:
        """Create a test client for the admin API."""
        return TestClient(self._create_app(mock_provider))

    @pytest.mark.asyncio
    async def test_get_user_returns_200(self) -> None:
        """GET /api/v1/admin/users/{user_id} should return 200 for existing user."""
        mock_user = UserData(user_id="user:alice", username="alice", email="alice@test.com", roles=["admin"], active=True)
        mock_provider = self._create_mock_user_provider(mock_user)
        client = self._create_client(mock_provider)
        response = client.get("/api/v1/admin/users/alice")

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "alice"
        assert data["email"] == "alice@test.com"

    @pytest.mark.asyncio
    async def test_get_user_returns_404_for_nonexistent(self) -> None:
        """GET /api/v1/admin/users/{user_id} should return 404 for nonexistent user."""
        mock_provider = self._create_mock_user_provider(None)
        client = self._create_client(mock_provider)
        response = client.get("/api/v1/admin/users/nonexistent")

        assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_admin_users_router")
class TestAdminUserCreateEndpoint:
    """Tests for POST /api/v1/admin/users endpoint."""

    def setup_method(self) -> None:
        """Reset singletons before each test to ensure clean state."""
        reset_singleton_dependencies()

    def teardown_method(self) -> None:
        """Force GC and reset singletons to prevent mock accumulation."""
        reset_singleton_dependencies()
        gc.collect()

    def _create_mock_user_provider(self, created_user: UserData | None = None) -> AsyncMock:
        """Create a mock user provider."""
        mock_provider = AsyncMock(return_value=None)  # async-mock-configured  # noqa: async-mock-config
        mock_provider.create_user = AsyncMock(return_value=created_user)
        mock_provider.get_user_by_username = AsyncMock(return_value=None)  # User doesn't exist yet
        return mock_provider

    def _create_app(self, mock_provider: AsyncMock | None = None) -> FastAPI:
        """Create a FastAPI app with the admin router.

        AUTH UPDATE (2025-12-29):
        ========================
        Admin endpoints now require authentication via require_admin dependency.
        We mock this to return an admin user for testing.
        """
        import mcp_server_langgraph.core.dependencies as deps_module
        from mcp_server_langgraph.api.v1.admin import admin_router
        from mcp_server_langgraph.auth.dependencies import require_admin
        from mcp_server_langgraph.core.dependencies import get_user_provider

        app = FastAPI()
        app.include_router(admin_router, prefix="/api/v1")

        if mock_provider:
            # Dual mocking strategy for xdist reliability
            deps_module._user_provider = mock_provider
            app.dependency_overrides[get_user_provider] = lambda: mock_provider

        # Mock admin authentication
        mock_admin_user = {
            "sub": "admin-user-id",
            "user_id": "admin-user-id",
            "username": "admin",
            "roles": ["admin"],
            "realm_access": {"roles": ["admin"]},
        }
        app.dependency_overrides[require_admin] = lambda: mock_admin_user

        return app

    def _create_client(self, mock_provider: AsyncMock | None = None) -> TestClient:
        """Create a test client for the admin API."""
        return TestClient(self._create_app(mock_provider))

    @pytest.mark.asyncio
    async def test_create_user_returns_201(self) -> None:
        """POST /api/v1/admin/users should return 201 on success."""
        created_user = UserData(
            user_id="user:newuser", username="newuser", email="newuser@test.com", roles=["user"], active=True
        )
        mock_provider = self._create_mock_user_provider(created_user)
        client = self._create_client(mock_provider)

        response = client.post(
            "/api/v1/admin/users",
            json={"username": "newuser", "email": "newuser@test.com", "password": "password123", "roles": ["user"]},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@test.com"

    @pytest.mark.asyncio
    async def test_create_user_returns_400_missing_fields(self) -> None:
        """POST /api/v1/admin/users should return 422 for missing required fields."""
        mock_provider = self._create_mock_user_provider()
        client = self._create_client(mock_provider)

        response = client.post("/api/v1/admin/users", json={"username": "newuser"})  # Missing email, password

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_user_returns_409_duplicate(self) -> None:
        """POST /api/v1/admin/users should return 409 for duplicate username."""
        existing_user = UserData(
            user_id="user:existing", username="existing", email="existing@test.com", roles=["user"], active=True
        )
        mock_provider = self._create_mock_user_provider()
        mock_provider.get_user_by_username = AsyncMock(return_value=existing_user)
        client = self._create_client(mock_provider)

        response = client.post(
            "/api/v1/admin/users",
            json={"username": "existing", "email": "new@test.com", "password": "password123", "roles": ["user"]},
        )

        assert response.status_code == 409


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_admin_users_router")
class TestAdminUserUpdateEndpoint:
    """Tests for PUT /api/v1/admin/users/{user_id} endpoint."""

    def setup_method(self) -> None:
        """Reset singletons before each test to ensure clean state."""
        reset_singleton_dependencies()

    def teardown_method(self) -> None:
        """Force GC and reset singletons to prevent mock accumulation."""
        reset_singleton_dependencies()
        gc.collect()

    def _create_mock_user_provider(self, existing_user: UserData | None = None) -> AsyncMock:
        """Create a mock user provider."""
        mock_provider = AsyncMock(return_value=None)  # async-mock-configured  # noqa: async-mock-config
        mock_provider.get_user_by_username = AsyncMock(return_value=existing_user)
        mock_provider.get_user_by_id = AsyncMock(return_value=existing_user)
        mock_provider.update_user = AsyncMock(return_value=existing_user)
        return mock_provider

    def _create_app(self, mock_provider: AsyncMock | None = None) -> FastAPI:
        """Create a FastAPI app with the admin router.

        AUTH UPDATE (2025-12-29):
        ========================
        Admin endpoints now require authentication via require_admin dependency.
        We mock this to return an admin user for testing.
        """
        import mcp_server_langgraph.core.dependencies as deps_module
        from mcp_server_langgraph.api.v1.admin import admin_router
        from mcp_server_langgraph.auth.dependencies import require_admin
        from mcp_server_langgraph.core.dependencies import get_user_provider

        app = FastAPI()
        app.include_router(admin_router, prefix="/api/v1")

        if mock_provider:
            # Dual mocking strategy for xdist reliability
            deps_module._user_provider = mock_provider
            app.dependency_overrides[get_user_provider] = lambda: mock_provider

        # Mock admin authentication
        mock_admin_user = {
            "sub": "admin-user-id",
            "user_id": "admin-user-id",
            "username": "admin",
            "roles": ["admin"],
            "realm_access": {"roles": ["admin"]},
        }
        app.dependency_overrides[require_admin] = lambda: mock_admin_user

        return app

    def _create_client(self, mock_provider: AsyncMock | None = None) -> TestClient:
        """Create a test client for the admin API."""
        return TestClient(self._create_app(mock_provider))

    @pytest.mark.asyncio
    async def test_update_user_returns_200(self) -> None:
        """PUT /api/v1/admin/users/{user_id} should return 200 on success."""
        existing_user = UserData(user_id="user:alice", username="alice", email="alice@test.com", roles=["user"], active=True)
        mock_provider = self._create_mock_user_provider(existing_user)
        client = self._create_client(mock_provider)

        response = client.put("/api/v1/admin/users/alice", json={"email": "alice.new@test.com", "roles": ["admin"]})

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_user_returns_404_nonexistent(self) -> None:
        """PUT /api/v1/admin/users/{user_id} should return 404 for nonexistent user."""
        mock_provider = self._create_mock_user_provider(None)
        client = self._create_client(mock_provider)

        response = client.put("/api/v1/admin/users/nonexistent", json={"email": "new@test.com"})

        assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_admin_users_router")
class TestAdminUserDeleteEndpoint:
    """Tests for DELETE /api/v1/admin/users/{user_id} endpoint."""

    def setup_method(self) -> None:
        """Reset singletons before each test to ensure clean state."""
        reset_singleton_dependencies()

    def teardown_method(self) -> None:
        """Force GC and reset singletons to prevent mock accumulation."""
        reset_singleton_dependencies()
        gc.collect()

    def _create_mock_user_provider(self, existing_user: UserData | None = None) -> AsyncMock:
        """Create a mock user provider."""
        mock_provider = AsyncMock(return_value=None)  # async-mock-configured  # noqa: async-mock-config
        mock_provider.get_user_by_username = AsyncMock(return_value=existing_user)
        mock_provider.get_user_by_id = AsyncMock(return_value=existing_user)
        mock_provider.delete_user = AsyncMock(return_value=True)
        return mock_provider

    def _create_app(self, mock_provider: AsyncMock | None = None) -> FastAPI:
        """Create a FastAPI app with the admin router.

        AUTH UPDATE (2025-12-29):
        ========================
        Admin endpoints now require authentication via require_admin dependency.
        We mock this to return an admin user for testing.
        """
        import mcp_server_langgraph.core.dependencies as deps_module
        from mcp_server_langgraph.api.v1.admin import admin_router
        from mcp_server_langgraph.auth.dependencies import require_admin
        from mcp_server_langgraph.core.dependencies import get_user_provider

        app = FastAPI()
        app.include_router(admin_router, prefix="/api/v1")

        if mock_provider:
            # Dual mocking strategy for xdist reliability
            deps_module._user_provider = mock_provider
            app.dependency_overrides[get_user_provider] = lambda: mock_provider

        # Mock admin authentication
        mock_admin_user = {
            "sub": "admin-user-id",
            "user_id": "admin-user-id",
            "username": "admin",
            "roles": ["admin"],
            "realm_access": {"roles": ["admin"]},
        }
        app.dependency_overrides[require_admin] = lambda: mock_admin_user

        return app

    def _create_client(self, mock_provider: AsyncMock | None = None) -> TestClient:
        """Create a test client for the admin API."""
        return TestClient(self._create_app(mock_provider))

    @pytest.mark.asyncio
    async def test_delete_user_returns_204(self) -> None:
        """DELETE /api/v1/admin/users/{user_id} should return 204 on success."""
        existing_user = UserData(user_id="user:alice", username="alice", email="alice@test.com", roles=["user"], active=True)
        mock_provider = self._create_mock_user_provider(existing_user)
        client = self._create_client(mock_provider)

        response = client.delete("/api/v1/admin/users/alice")

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_user_returns_404_nonexistent(self) -> None:
        """DELETE /api/v1/admin/users/{user_id} should return 404 for nonexistent user."""
        mock_provider = self._create_mock_user_provider(None)
        client = self._create_client(mock_provider)

        response = client.delete("/api/v1/admin/users/nonexistent")

        assert response.status_code == 404
