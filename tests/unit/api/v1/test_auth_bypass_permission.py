"""
Tests for Bypass Permission Check Endpoint.

TDD tests for GET /api/v1/auth/bypass-permission endpoint.
Verifies that bypass permission properly checks bypass_executor relation via OpenFGA.

PYTEST-XDIST FIX: Uses dual mocking strategy for xdist reliability.
"""

import gc
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_auth_bypass_permission")
class TestBypassPermissionCheck:
    """Tests for GET /api/v1/auth/bypass-permission endpoint.

    Verifies that the endpoint checks bypass_executor permission via OpenFGA.
    """

    def setup_method(self) -> None:
        """Reset singletons before each test to ensure clean state."""
        reset_singleton_dependencies()

    def teardown_method(self) -> None:
        """Force GC and reset singletons to prevent mock accumulation."""
        reset_singleton_dependencies()
        gc.collect()

    def _create_mock_openfga_client(
        self,
        has_permission: bool = True,
        raise_error: Exception | None = None,
    ) -> AsyncMock:
        """Create a mock OpenFGA client."""
        mock_client = AsyncMock(return_value=None)  # noqa: async-mock-config
        if raise_error:
            mock_client.check_permission.side_effect = raise_error
        else:
            mock_client.check_permission.return_value = has_permission
        return mock_client

    def _create_app(
        self,
        mock_openfga_client: AsyncMock | None = None,
        mock_current_user: dict | None = None,
    ) -> FastAPI:
        """Create a FastAPI app with the auth router."""
        from mcp_server_langgraph.api.deps import get_openfga_client
        from mcp_server_langgraph.api.v1.auth import auth_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(auth_router, prefix="/api/v1")

        # Mock OpenFGA client dependency
        if mock_openfga_client is not None:
            app.dependency_overrides[get_openfga_client] = lambda: mock_openfga_client
        else:
            # No OpenFGA client - return None
            app.dependency_overrides[get_openfga_client] = lambda: None

        # Mock current user authentication
        if mock_current_user:
            app.dependency_overrides[get_current_user] = lambda: mock_current_user

        return app

    def _create_client(
        self,
        mock_openfga_client: AsyncMock | None = None,
        mock_current_user: dict | None = None,
    ) -> TestClient:
        """Create a test client for the auth API."""
        app = self._create_app(mock_openfga_client, mock_current_user)
        return TestClient(app)

    # =========================================================================
    # Permission Granted Tests
    # =========================================================================

    def test_bypass_permission_granted_for_user_with_permission(self) -> None:
        """GIVEN a user with bypass_executor permission
        WHEN GET /api/v1/auth/bypass-permission is called
        THEN allowed=True is returned.
        """
        mock_openfga = self._create_mock_openfga_client(has_permission=True)
        mock_user = {
            "user_id": "user:alice",
            "preferred_username": "alice",
        }

        client = self._create_client(mock_openfga, mock_user)
        response = client.get("/api/v1/auth/bypass-permission")

        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is True

        # Verify OpenFGA was called with correct args
        mock_openfga.check_permission.assert_called_once_with(
            user="user:alice",
            relation="bypass_executor",
            object="system:global",
            critical=True,
        )

    def test_bypass_permission_granted_for_admin(self) -> None:
        """GIVEN an admin user (admin relation inherits bypass_executor)
        WHEN GET /api/v1/auth/bypass-permission is called
        THEN allowed=True is returned.
        """
        mock_openfga = self._create_mock_openfga_client(has_permission=True)
        mock_user = {
            "user_id": "user:admin",
            "preferred_username": "admin",
        }

        client = self._create_client(mock_openfga, mock_user)
        response = client.get("/api/v1/auth/bypass-permission")

        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is True

    # =========================================================================
    # Permission Denied Tests
    # =========================================================================

    def test_bypass_permission_denied_for_user_without_permission(self) -> None:
        """GIVEN a user without bypass_executor permission
        WHEN GET /api/v1/auth/bypass-permission is called
        THEN allowed=False is returned.
        """
        mock_openfga = self._create_mock_openfga_client(has_permission=False)
        mock_user = {
            "user_id": "user:bob",
            "preferred_username": "bob",
        }

        client = self._create_client(mock_openfga, mock_user)
        response = client.get("/api/v1/auth/bypass-permission")

        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is False

    def test_bypass_permission_denied_when_openfga_not_configured(self) -> None:
        """GIVEN no OpenFGA client is configured
        WHEN GET /api/v1/auth/bypass-permission is called
        THEN allowed=False is returned (fail-closed).
        """
        mock_user = {
            "user_id": "user:alice",
            "preferred_username": "alice",
        }

        # No OpenFGA client - pass None explicitly
        client = self._create_client(None, mock_user)
        response = client.get("/api/v1/auth/bypass-permission")

        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is False

    # =========================================================================
    # User ID Handling Tests
    # =========================================================================

    def test_uses_user_id_directly_without_prefix(self) -> None:
        """GIVEN user_id already has 'user:' prefix
        WHEN GET /api/v1/auth/bypass-permission is called
        THEN the user_id is used as-is without double-prefixing.
        """
        mock_openfga = self._create_mock_openfga_client(has_permission=True)
        mock_user = {
            "user_id": "user:alice",  # Already prefixed
            "preferred_username": "alice",
        }

        client = self._create_client(mock_openfga, mock_user)
        response = client.get("/api/v1/auth/bypass-permission")

        assert response.status_code == 200
        # Verify NO double-prefixing (should be "user:alice", NOT "user:user:alice")
        mock_openfga.check_permission.assert_called_once()
        call_args = mock_openfga.check_permission.call_args
        assert call_args.kwargs["user"] == "user:alice"

    def test_fallback_to_preferred_username_when_user_id_missing(self) -> None:
        """GIVEN user_id is not in current_user but preferred_username is
        WHEN GET /api/v1/auth/bypass-permission is called
        THEN user:preferred_username is used.
        """
        mock_openfga = self._create_mock_openfga_client(has_permission=True)
        mock_user = {
            # No user_id - fall back to preferred_username
            "preferred_username": "carol",
        }

        client = self._create_client(mock_openfga, mock_user)
        response = client.get("/api/v1/auth/bypass-permission")

        assert response.status_code == 200
        mock_openfga.check_permission.assert_called_once()
        call_args = mock_openfga.check_permission.call_args
        assert call_args.kwargs["user"] == "user:carol"

    # =========================================================================
    # Error Handling Tests
    # =========================================================================

    def test_bypass_permission_denied_on_openfga_error(self) -> None:
        """GIVEN OpenFGA raises an error during check
        WHEN GET /api/v1/auth/bypass-permission is called
        THEN the error is propagated (fail-closed behavior).
        """
        mock_openfga = self._create_mock_openfga_client(raise_error=Exception("OpenFGA connection failed"))
        mock_user = {
            "user_id": "user:alice",
            "preferred_username": "alice",
        }

        client = self._create_client(mock_openfga, mock_user)

        # Error should propagate (fail-closed behavior)
        with pytest.raises(Exception, match="OpenFGA connection failed"):
            client.get("/api/v1/auth/bypass-permission")
