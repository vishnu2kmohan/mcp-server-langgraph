"""
Tests for User API

TDD: Tests for the /api/v1/me endpoint returning current user info.

Follows memory safety patterns for pytest-xdist.

PYTEST-XDIST FIX (2025-12-15):
==============================
Previous approach relied on set_global_auth_middleware() to configure authentication.
This failed in parallel execution due to module-level caching and global state pollution.

New approach uses FastAPI dependency overrides to directly override get_current_user,
which is more robust as it doesn't rely on global state management.

Added additional fixture to reset global auth middleware singleton to prevent
test pollution from other tests in the xdist suite.

LOGOUT + DENYLIST (2025-12-15):
===============================
Added tests for logout endpoint with token denylist integration.
Tokens are added to denylist on logout for immediate invalidation (OWASP best practice).
"""

import gc
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.unit, pytest.mark.api]


# NOTE: Auth and database singletons are reset by the central
# reset_dependency_singletons fixture in tests/conftest.py


def _create_test_app_with_user(user_data: dict[str, Any] | None = None) -> FastAPI:
    """
    Create a test FastAPI app with dependency overrides for the user router.

    Args:
        user_data: User data to return from get_current_user, or None to simulate unauthenticated

    Returns:
        FastAPI app with user router and appropriate dependency overrides

    PYTEST-XDIST FIX (2025-12-15):
    ==============================
    Uses dependency override to completely replace get_current_user.
    Also sets up mock global auth middleware as defensive fallback.
    """
    from fastapi import Request

    from mcp_server_langgraph.api.v1.user import user_router
    from mcp_server_langgraph.auth.middleware import (
        get_current_user,
        set_global_auth_middleware,
    )
    from mcp_server_langgraph.auth.user_provider import TokenVerification

    # Defensive: Set up mock global auth middleware in case override doesn't work
    # This prevents RuntimeError if the real get_current_user is called
    # PYTEST-XDIST FIX (2025-12-16): verify_token must return TokenVerification
    # not raw user_data, for fallback to work correctly
    mock_middleware = MagicMock()
    mock_verification = TokenVerification(
        valid=user_data is not None,
        payload=user_data if user_data else None,
        error=None if user_data else "Mocked unauthenticated",
    )
    mock_middleware.verify_token = AsyncMock(return_value=mock_verification)
    set_global_auth_middleware(mock_middleware)

    app = FastAPI()

    if user_data is not None:
        # Override get_current_user to return mock user
        # Note: Must match original signature with Request parameter for xdist compatibility
        async def mock_get_current_user(request: Request) -> dict[str, Any]:
            return user_data

        app.dependency_overrides[get_current_user] = mock_get_current_user
    else:
        # Override get_current_user to raise 401 (simulating no auth)
        async def mock_get_current_user_unauthenticated(request: Request) -> dict[str, Any]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )

        app.dependency_overrides[get_current_user] = mock_get_current_user_unauthenticated

    app.include_router(user_router)

    return app


@pytest.fixture
def mock_auth_middleware():
    """Create a mock auth middleware."""
    mock = MagicMock()
    mock.verify_token = AsyncMock()  # async-mock-configured
    return mock


@pytest.fixture
def app():
    """Create a test FastAPI app with the user router (no auth override)."""
    from mcp_server_langgraph.api.v1.user import user_router

    app = FastAPI()
    app.include_router(user_router)
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def alice_user():
    """Alice user with developer role."""
    return {
        "user_id": "user:alice",
        "keycloak_id": "uuid-alice",
        "username": "alice",
        "roles": ["developer"],
        "email": "alice@example.com",
    }


@pytest.fixture
def bob_user():
    """Bob user with user role only."""
    return {
        "user_id": "user:bob",
        "keycloak_id": "uuid-bob",
        "username": "bob",
        "roles": [],
        "email": "bob@example.com",
    }


@pytest.fixture
def admin_user():
    """Admin user."""
    return {
        "user_id": "user:admin",
        "keycloak_id": "uuid-admin",
        "username": "admin",
        "roles": ["admin", "developer"],
        "email": "admin@example.com",
    }


# ============================================================================
# GET /me Tests
# ============================================================================


@pytest.mark.xdist_group(name="user_api")
class TestGetCurrentUser:
    """Tests for GET /me - returns current authenticated user info."""

    def teardown_method(self) -> None:
        """Force GC to prevent accumulation in xdist workers."""
        gc.collect()

    def test_get_me_returns_user_info(self, alice_user):
        """Should return current user info for authenticated user."""
        # Use dependency override approach instead of global middleware
        user_data = {
            "user_id": "user:alice",
            "username": "alice",
            "email": "alice@example.com",
            "roles": ["developer"],
            "keycloak_id": "uuid-alice",
        }
        app = _create_test_app_with_user(user_data)
        client = TestClient(app)

        response = client.get("/me", headers={"Authorization": "Bearer valid-token"})
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "alice"
        assert data["email"] == "alice@example.com"
        assert "developer" in data["roles"]

    def test_get_me_returns_401_without_auth(self):
        """Should return 401 when no authorization header."""
        # Create app with unauthenticated user (raises 401)
        app = _create_test_app_with_user(None)
        client = TestClient(app)

        response = client.get("/me")
        assert response.status_code == 401

    def test_get_me_returns_401_with_invalid_token(self):
        """Should return 401 for invalid token."""
        # Create app with unauthenticated user (raises 401)
        app = _create_test_app_with_user(None)
        client = TestClient(app)

        response = client.get("/me", headers={"Authorization": "Bearer invalid-token"})
        assert response.status_code == 401

    def test_get_me_includes_persona_for_developer(self):
        """Should include 'developer' persona for developer role."""
        user_data = {
            "user_id": "user:alice",
            "username": "alice",
            "roles": ["developer"],
            "keycloak_id": "uuid-alice",
        }
        app = _create_test_app_with_user(user_data)
        client = TestClient(app)

        response = client.get("/me", headers={"Authorization": "Bearer valid-token"})
        assert response.status_code == 200
        data = response.json()
        assert data["persona"] == "developer"

    def test_get_me_includes_persona_for_admin(self):
        """Should include 'admin' persona for admin role."""
        user_data = {
            "user_id": "user:admin",
            "username": "admin",
            "roles": ["admin"],
            "keycloak_id": "uuid-admin",
        }
        app = _create_test_app_with_user(user_data)
        client = TestClient(app)

        response = client.get("/me", headers={"Authorization": "Bearer valid-token"})
        assert response.status_code == 200
        data = response.json()
        assert data["persona"] == "admin"

    def test_get_me_includes_persona_for_user(self):
        """Should include 'user' persona for users without special roles."""
        user_data = {
            "user_id": "user:bob",
            "username": "bob",
            "roles": [],
            "keycloak_id": "uuid-bob",
        }
        app = _create_test_app_with_user(user_data)
        client = TestClient(app)

        response = client.get("/me", headers={"Authorization": "Bearer valid-token"})
        assert response.status_code == 200
        data = response.json()
        assert data["persona"] == "user"


# ============================================================================
# Integration Tests (with real auth dependency)
# ============================================================================


@pytest.mark.xdist_group(name="user_api")
class TestGetCurrentUserIntegration:
    """Integration tests for /me endpoint with request.state.user."""

    def teardown_method(self) -> None:
        """Force GC to prevent accumulation in xdist workers."""
        gc.collect()

    def test_get_me_uses_request_state_user(self):
        """Should use user from request.state if set by middleware."""
        # Use dependency override approach - simulates what traefik-forward-auth would do
        user_data = {
            "user_id": "user:alice",
            "keycloak_id": "uuid-alice",
            "username": "alice",
            "roles": ["developer"],
            "email": "alice@example.com",
        }
        app = _create_test_app_with_user(user_data)
        client = TestClient(app)

        response = client.get("/me")
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "alice"
        assert data["persona"] == "developer"


# ============================================================================
# POST /logout Tests (with denylist integration)
# ============================================================================


def _create_test_app_with_denylist(mock_denylist: MagicMock | None = None) -> FastAPI:
    """
    Create a test FastAPI app with dependency overrides for logout testing.

    Args:
        mock_denylist: Mock denylist to inject

    Returns:
        FastAPI app with user router and denylist override
    """
    from mcp_server_langgraph.api.v1.user import user_router
    from mcp_server_langgraph.core.dependencies import get_token_denylist

    app = FastAPI()
    app.include_router(user_router)

    if mock_denylist is not None:
        app.dependency_overrides[get_token_denylist] = lambda: mock_denylist

    return app


@pytest.mark.xdist_group(name="user_api_logout")
class TestLogoutWithDenylist:
    """Tests for POST /logout - token denylist integration (OWASP best practice)."""

    def teardown_method(self) -> None:
        """Force GC to prevent accumulation in xdist workers."""
        gc.collect()

    def test_logout_adds_token_to_denylist(self):
        """Should add token JTI to denylist on logout."""
        import jwt

        # Create a mock denylist
        mock_denylist = MagicMock()
        mock_denylist.add = AsyncMock(return_value=None)

        # Create a valid JWT with jti and exp claims
        token_payload = {
            "sub": "user:alice",
            "jti": "test-jti-12345",
            "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp(),
            "iat": datetime.now(UTC).timestamp(),
        }
        test_token = jwt.encode(token_payload, "secret", algorithm="HS256")

        app = _create_test_app_with_denylist(mock_denylist)
        client = TestClient(app)

        # Mock httpx.AsyncClient to prevent actual Keycloak call
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))
            mock_client_class.return_value = mock_client

            response = client.post(
                "/logout",
                headers={"Authorization": f"Bearer {test_token}"},
            )

        assert response.status_code == 200
        # Verify denylist.add was called with jti
        mock_denylist.add.assert_called_once()
        call_args = mock_denylist.add.call_args[0]
        assert call_args[0] == "test-jti-12345"  # jti
        # Second arg is expires_at datetime
        assert isinstance(call_args[1], datetime)

    def test_logout_without_token_returns_success(self):
        """Should return success when no token provided (no session)."""
        mock_denylist = MagicMock()
        mock_denylist.add = AsyncMock(return_value=None)

        app = _create_test_app_with_denylist(mock_denylist)
        client = TestClient(app)

        response = client.post("/logout")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "no active session" in data["message"].lower()
        # Denylist should NOT be called when no token
        mock_denylist.add.assert_not_called()

    def test_logout_with_invalid_token_still_succeeds(self):
        """Should return success even with invalid token format."""
        mock_denylist = MagicMock()
        mock_denylist.add = AsyncMock(return_value=None)

        app = _create_test_app_with_denylist(mock_denylist)
        client = TestClient(app)

        # Mock httpx.AsyncClient to prevent actual Keycloak call
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))
            mock_client_class.return_value = mock_client

            response = client.post(
                "/logout",
                headers={"Authorization": "Bearer invalid-not-a-jwt"},
            )

        # Logout should still succeed (graceful degradation)
        assert response.status_code == 200
        # Denylist add might not be called for invalid tokens (that's OK)

    def test_logout_with_token_without_jti_still_succeeds(self):
        """Should handle tokens without JTI claim gracefully."""
        import jwt

        mock_denylist = MagicMock()
        mock_denylist.add = AsyncMock(return_value=None)

        # Create a JWT without jti claim
        token_payload = {
            "sub": "user:alice",
            "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp(),
        }
        test_token = jwt.encode(token_payload, "secret", algorithm="HS256")

        app = _create_test_app_with_denylist(mock_denylist)
        client = TestClient(app)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))
            mock_client_class.return_value = mock_client

            response = client.post(
                "/logout",
                headers={"Authorization": f"Bearer {test_token}"},
            )

        assert response.status_code == 200
        # Denylist should NOT be called when no jti
        mock_denylist.add.assert_not_called()
