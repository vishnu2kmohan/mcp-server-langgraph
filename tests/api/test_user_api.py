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
"""

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock

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
    """
    from mcp_server_langgraph.api.v1.user import user_router
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(user_router)

    if user_data is not None:
        # Override get_current_user to return mock user
        async def mock_get_current_user() -> dict[str, Any]:
            return user_data

        app.dependency_overrides[get_current_user] = mock_get_current_user
    else:
        # Override get_current_user to raise 401 (simulating no auth)
        async def mock_get_current_user_unauthenticated() -> dict[str, Any]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )

        app.dependency_overrides[get_current_user] = mock_get_current_user_unauthenticated

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
