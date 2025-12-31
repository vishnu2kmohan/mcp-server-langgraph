"""
Tests for Admin API Key Endpoints

TDD tests for /api/v1/admin/users/{user_id}/api-key endpoints.
Verifies that API key management endpoints properly integrate with APIKeyManager.

PYTEST-XDIST FIX: Uses dual mocking strategy for xdist reliability.
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
@pytest.mark.xdist_group(name="test_admin_api_keys")
class TestAdminApiKeyGetEndpoint:
    """Tests for GET /api/v1/admin/users/{user_id}/api-key endpoint.

    Verifies that the endpoint retrieves API keys from APIKeyManager.
    """

    def setup_method(self) -> None:
        """Reset singletons before each test to ensure clean state."""
        reset_singleton_dependencies()

    def teardown_method(self) -> None:
        """Force GC and reset singletons to prevent mock accumulation."""
        reset_singleton_dependencies()
        gc.collect()

    def _create_mock_user_provider(self, user: UserData | None = None) -> AsyncMock:
        """Create a mock user provider."""
        mock_provider = AsyncMock()  # noqa: async-mock-config
        mock_provider.get_user_by_username.return_value = user
        mock_provider.get_user_by_id.return_value = user
        return mock_provider

    def _create_mock_api_key_manager(self, keys: list[dict] | None = None, raise_error: Exception | None = None) -> AsyncMock:
        """Create a mock API key manager."""
        mock_manager = AsyncMock()  # noqa: async-mock-config
        if raise_error:
            mock_manager.list_api_keys.side_effect = raise_error
        else:
            mock_manager.list_api_keys.return_value = keys or []
        return mock_manager

    def _create_app(
        self,
        mock_provider: AsyncMock | None = None,
        mock_api_key_manager: AsyncMock | None = None,
    ) -> FastAPI:
        """Create a FastAPI app with the admin router."""
        import mcp_server_langgraph.core.dependencies as deps_module
        from mcp_server_langgraph.api.v1.admin import admin_router
        from mcp_server_langgraph.auth.dependencies import require_admin
        from mcp_server_langgraph.core.dependencies import get_user_provider

        app = FastAPI()
        app.include_router(admin_router, prefix="/api/v1")

        if mock_provider:
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

        # Mock API key manager dependency
        if mock_api_key_manager:
            from mcp_server_langgraph.api.deps import get_api_key_manager

            app.dependency_overrides[get_api_key_manager] = lambda: mock_api_key_manager

        return app

    def _create_client(
        self,
        mock_provider: AsyncMock | None = None,
        mock_api_key_manager: AsyncMock | None = None,
    ) -> TestClient:
        """Create a test client for the admin API."""
        return TestClient(self._create_app(mock_provider, mock_api_key_manager))

    @pytest.mark.asyncio
    async def test_get_user_api_key_returns_masked_key_from_keycloak(self) -> None:
        """GET /api/v1/admin/users/{user_id}/api-key retrieves from APIKeyManager."""
        mock_user = UserData(
            user_id="user:alice",
            username="alice",
            email="alice@test.com",
            roles=["user"],
            active=True,
        )
        mock_provider = self._create_mock_user_provider(mock_user)

        # Mock API key manager with existing keys
        mock_keys = [
            {
                "key_id": "abc123",
                "name": "Production Key",
                "created": "2025-01-01T00:00:00Z",
                "expires_at": "2026-01-01T00:00:00Z",
                "last_used": "2025-12-01T00:00:00Z",
            }
        ]
        mock_api_key_manager = self._create_mock_api_key_manager(keys=mock_keys)

        client = self._create_client(mock_provider, mock_api_key_manager)
        response = client.get("/api/v1/admin/users/alice/api-key")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user:alice"
        # Should return masked key format, not the actual key
        assert data["masked_key"] is not None
        assert "****" in data["masked_key"]

        # Verify APIKeyManager was called with correct user_id format
        mock_api_key_manager.list_api_keys.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_api_key_user_not_found_returns_404(self) -> None:
        """GET /api/v1/admin/users/{user_id}/api-key returns 404 for missing user."""
        mock_provider = self._create_mock_user_provider(None)  # No user found
        mock_api_key_manager = self._create_mock_api_key_manager()

        client = self._create_client(mock_provider, mock_api_key_manager)
        response = client.get("/api/v1/admin/users/nonexistent/api-key")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_user_api_key_no_keys_returns_empty(self) -> None:
        """GET /api/v1/admin/users/{user_id}/api-key returns null masked_key when no keys exist."""
        mock_user = UserData(
            user_id="user:bob",
            username="bob",
            email="bob@test.com",
            roles=["user"],
            active=True,
        )
        mock_provider = self._create_mock_user_provider(mock_user)
        mock_api_key_manager = self._create_mock_api_key_manager(keys=[])

        client = self._create_client(mock_provider, mock_api_key_manager)
        response = client.get("/api/v1/admin/users/bob/api-key")

        assert response.status_code == 200
        data = response.json()
        assert data["masked_key"] is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_admin_api_keys")
class TestAdminApiKeyGenerateEndpoint:
    """Tests for POST /api/v1/admin/users/{user_id}/api-key endpoint.

    Verifies that the endpoint creates API keys via APIKeyManager.
    """

    def setup_method(self) -> None:
        """Reset singletons before each test to ensure clean state."""
        reset_singleton_dependencies()

    def teardown_method(self) -> None:
        """Force GC and reset singletons to prevent mock accumulation."""
        reset_singleton_dependencies()
        gc.collect()

    def _create_mock_user_provider(self, user: UserData | None = None) -> AsyncMock:
        """Create a mock user provider."""
        mock_provider = AsyncMock()  # noqa: async-mock-config
        mock_provider.get_user_by_username.return_value = user
        mock_provider.get_user_by_id.return_value = user
        return mock_provider

    def _create_mock_api_key_manager(
        self,
        create_result: dict | None = None,
        raise_error: Exception | None = None,
    ) -> AsyncMock:
        """Create a mock API key manager."""
        mock_manager = AsyncMock()  # noqa: async-mock-config
        if raise_error:
            mock_manager.create_api_key.side_effect = raise_error
        else:
            mock_manager.create_api_key.return_value = create_result or {
                "key_id": "new123",
                "api_key": "mcpkey_live_abc123xyz456",  # gitleaks:allow
                "name": "Admin Generated",
                "created": "2025-12-31T00:00:00Z",
                "expires_at": "2026-12-31T00:00:00Z",
            }
        mock_manager.list_api_keys.return_value = []  # For quota check
        return mock_manager

    def _create_app(
        self,
        mock_provider: AsyncMock | None = None,
        mock_api_key_manager: AsyncMock | None = None,
    ) -> FastAPI:
        """Create a FastAPI app with the admin router."""
        import mcp_server_langgraph.core.dependencies as deps_module
        from mcp_server_langgraph.api.v1.admin import admin_router
        from mcp_server_langgraph.auth.dependencies import require_admin
        from mcp_server_langgraph.core.dependencies import get_user_provider

        app = FastAPI()
        app.include_router(admin_router, prefix="/api/v1")

        if mock_provider:
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

        # Mock API key manager dependency
        if mock_api_key_manager:
            from mcp_server_langgraph.api.deps import get_api_key_manager

            app.dependency_overrides[get_api_key_manager] = lambda: mock_api_key_manager

        return app

    def _create_client(
        self,
        mock_provider: AsyncMock | None = None,
        mock_api_key_manager: AsyncMock | None = None,
    ) -> TestClient:
        """Create a test client for the admin API."""
        return TestClient(self._create_app(mock_provider, mock_api_key_manager))

    @pytest.mark.asyncio
    async def test_generate_user_api_key_stores_hash_in_keycloak(self) -> None:
        """POST /api/v1/admin/users/{user_id}/api-key creates via APIKeyManager."""
        mock_user = UserData(
            user_id="user:alice",
            username="alice",
            email="alice@test.com",
            roles=["user"],
            active=True,
        )
        mock_provider = self._create_mock_user_provider(mock_user)

        # Mock successful key creation
        created_key = {
            "key_id": "new123",
            "api_key": "mcpkey_live_testkey123456789",  # gitleaks:allow
            "name": "Admin Generated",
            "created": "2025-12-31T00:00:00Z",
            "expires_at": "2026-12-31T00:00:00Z",
        }
        mock_api_key_manager = self._create_mock_api_key_manager(create_result=created_key)

        client = self._create_client(mock_provider, mock_api_key_manager)
        response = client.post("/api/v1/admin/users/alice/api-key")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user:alice"
        # Should return the full API key (only time it's shown)
        assert data["api_key"] is not None
        assert data["api_key"].startswith("mcpkey_live_")
        # Should also return masked version
        assert data["masked_key"] is not None

        # Verify APIKeyManager.create_api_key was called
        mock_api_key_manager.create_api_key.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_user_api_key_user_not_found_returns_404(self) -> None:
        """POST /api/v1/admin/users/{user_id}/api-key returns 404 for missing user."""
        mock_provider = self._create_mock_user_provider(None)
        mock_api_key_manager = self._create_mock_api_key_manager()

        client = self._create_client(mock_provider, mock_api_key_manager)
        response = client.post("/api/v1/admin/users/nonexistent/api-key")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_generate_user_api_key_respects_max_quota(self) -> None:
        """POST /api/v1/admin/users/{user_id}/api-key returns 400 when quota exceeded."""
        mock_user = UserData(
            user_id="user:alice",
            username="alice",
            email="alice@test.com",
            roles=["user"],
            active=True,
        )
        mock_provider = self._create_mock_user_provider(mock_user)

        # Mock quota exceeded error
        mock_api_key_manager = self._create_mock_api_key_manager(raise_error=ValueError("Maximum API keys reached (5)"))

        client = self._create_client(mock_provider, mock_api_key_manager)
        response = client.post("/api/v1/admin/users/alice/api-key")

        assert response.status_code == 400
        assert "maximum" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_generate_user_api_key_invalidates_existing_keys(self) -> None:
        """POST /api/v1/admin/users/{user_id}/api-key revokes existing keys first."""
        mock_user = UserData(
            user_id="user:alice",
            username="alice",
            email="alice@test.com",
            roles=["user"],
            active=True,
        )
        mock_provider = self._create_mock_user_provider(mock_user)

        # Mock existing keys
        mock_api_key_manager = AsyncMock()  # noqa: async-mock-config
        mock_api_key_manager.list_api_keys.return_value = [{"key_id": "old123", "name": "Old Key"}]
        mock_api_key_manager.revoke_api_key.return_value = None
        mock_api_key_manager.create_api_key.return_value = {
            "key_id": "new456",
            "api_key": "mcpkey_live_newkey789",  # gitleaks:allow
            "name": "Admin Generated",
            "created": "2025-12-31T00:00:00Z",
            "expires_at": "2026-12-31T00:00:00Z",
        }

        client = self._create_client(mock_provider, mock_api_key_manager)
        response = client.post("/api/v1/admin/users/alice/api-key")

        assert response.status_code == 200
        # Verify old key was revoked before creating new one
        mock_api_key_manager.revoke_api_key.assert_called_once()
        mock_api_key_manager.create_api_key.assert_called_once()
