"""
Tests for FastAPI Auth Middleware

Following TDD: These tests are written FIRST, before implementation.
They define the expected behavior of the auth middleware.

The auth middleware should:
1. Extract Bearer tokens from Authorization headers
2. Verify JWT tokens
3. Set request.state.user for authenticated requests
4. Allow public endpoints to pass through
5. Return 401 for invalid/missing tokens on protected endpoints
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from mcp_server_langgraph.auth.middleware import AuthMiddleware, TokenVerification

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="auth_middleware_tests")
class TestAuthRequestMiddleware:
    """Test FastAPI request middleware for auth"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_middleware_extracts_bearer_token_and_sets_request_state(self):
        """
        Middleware should extract Bearer token from headers and set request.state.user
        """
        # Arrange: Create FastAPI app with our auth middleware
        from mcp_server_langgraph.api.auth_request_middleware import AuthRequestMiddleware

        app = FastAPI()

        # Create mock auth middleware
        auth_middleware = MagicMock(spec=AuthMiddleware)
        auth_middleware.verify_token = AsyncMock(
            return_value=TokenVerification(
                valid=True,
                payload={"sub": "user:alice", "username": "alice", "roles": ["user"]},
                error=None,
            )
        )

        # Add auth middleware to app
        app.add_middleware(AuthRequestMiddleware, auth_middleware=auth_middleware)

        # Add test endpoint
        @app.get("/protected")
        async def protected_endpoint(request: Request):
            return {"user": getattr(request.state, "user", None)}

        # Act: Make request with Bearer token
        client = TestClient(app)
        response = client.get("/protected", headers={"Authorization": "Bearer test-token-123"})

        # Assert: request.state.user should be set
        assert response.status_code == 200
        user_data = response.json()["user"]
        assert user_data is not None
        assert user_data["username"] == "alice"
        assert user_data["user_id"] == "user:alice"
        assert "user" in user_data["roles"]

    @pytest.mark.asyncio
    async def test_middleware_handles_missing_token_gracefully(self):
        """
        Middleware should NOT return 401 for missing tokens - let endpoints decide
        """
        # Arrange
        from mcp_server_langgraph.api.auth_request_middleware import AuthRequestMiddleware

        app = FastAPI()
        auth_middleware = MagicMock(spec=AuthMiddleware)
        app.add_middleware(AuthRequestMiddleware, auth_middleware=auth_middleware)

        @app.get("/public")
        async def public_endpoint(request: Request):
            user = getattr(request.state, "user", None)
            return {"user": user, "public": True}

        # Act: Make request without token
        client = TestClient(app)
        response = client.get("/public")

        # Assert: Should allow request through (200), user should be None
        assert response.status_code == 200
        assert response.json()["user"] is None
        assert response.json()["public"] is True

    @pytest.mark.asyncio
    async def test_middleware_handles_invalid_token(self):
        """
        Middleware should NOT set request.state.user for invalid tokens
        """
        # Arrange
        from mcp_server_langgraph.api.auth_request_middleware import AuthRequestMiddleware

        app = FastAPI()
        auth_middleware = MagicMock(spec=AuthMiddleware)
        auth_middleware.verify_token = AsyncMock(
            return_value=TokenVerification(valid=False, payload=None, error="Invalid signature")
        )

        app.add_middleware(AuthRequestMiddleware, auth_middleware=auth_middleware)

        @app.get("/protected")
        async def protected_endpoint(request: Request):
            user = getattr(request.state, "user", None)
            if not user:
                from fastapi import HTTPException

                raise HTTPException(status_code=401, detail="Authentication required")
            return {"user": user}

        # Act: Make request with invalid token
        client = TestClient(app)
        response = client.get("/protected", headers={"Authorization": "Bearer invalid-token"})

        # Assert: request.state.user should not be set, endpoint returns 401
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_middleware_extracts_keycloak_user_info(self):
        """
        Middleware should properly extract Keycloak user information from token
        """
        # Arrange
        from mcp_server_langgraph.api.auth_request_middleware import AuthRequestMiddleware

        app = FastAPI()
        auth_middleware = MagicMock(spec=AuthMiddleware)
        auth_middleware.verify_token = AsyncMock(
            return_value=TokenVerification(
                valid=True,
                payload={
                    "sub": "550e8400-e29b-41d4-a716-446655440000",  # Keycloak UUID
                    "preferred_username": "alice",
                    "email": "alice@example.com",
                    "roles": ["user", "premium"],
                },
                error=None,
            )
        )

        app.add_middleware(AuthRequestMiddleware, auth_middleware=auth_middleware)

        @app.get("/me")
        async def me_endpoint(request: Request):
            return {"user": request.state.user}

        # Act
        client = TestClient(app)
        response = client.get("/me", headers={"Authorization": "Bearer keycloak-token"})

        # Assert: Should extract keycloak_id and username correctly
        assert response.status_code == 200
        user_data = response.json()["user"]
        assert user_data["username"] == "alice"
        assert user_data["keycloak_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert user_data["email"] == "alice@example.com"
        assert user_data["user_id"] == "user:alice"

    @pytest.mark.asyncio
    async def test_middleware_handles_malformed_authorization_header(self):
        """
        Middleware should handle malformed Authorization headers gracefully
        """
        # Arrange
        from mcp_server_langgraph.api.auth_request_middleware import AuthRequestMiddleware

        app = FastAPI()
        auth_middleware = MagicMock(spec=AuthMiddleware)
        app.add_middleware(AuthRequestMiddleware, auth_middleware=auth_middleware)

        @app.get("/test")
        async def test_endpoint(request: Request):
            return {"user": getattr(request.state, "user", None)}

        client = TestClient(app)

        # Act & Assert: Various malformed headers should not crash
        # Missing "Bearer " prefix
        response = client.get("/test", headers={"Authorization": "test-token"})
        assert response.status_code == 200
        assert response.json()["user"] is None

        # Empty token
        response = client.get("/test", headers={"Authorization": "Bearer "})
        assert response.status_code == 200
        assert response.json()["user"] is None

        # Only "Bearer"
        response = client.get("/test", headers={"Authorization": "Bearer"})
        assert response.status_code == 200
        assert response.json()["user"] is None

    @pytest.mark.asyncio
    async def test_middleware_preserves_worker_safe_user_ids(self):
        """
        Middleware should preserve worker-safe user IDs from pytest-xdist
        """
        # Arrange
        from mcp_server_langgraph.api.auth_request_middleware import AuthRequestMiddleware

        app = FastAPI()
        auth_middleware = MagicMock(spec=AuthMiddleware)
        auth_middleware.verify_token = AsyncMock(
            return_value=TokenVerification(
                valid=True,
                payload={
                    "sub": "user:test_gw0_alice",  # Worker-safe ID
                    "username": "alice",
                    "roles": ["user"],
                },
                error=None,
            )
        )

        app.add_middleware(AuthRequestMiddleware, auth_middleware=auth_middleware)

        @app.get("/test")
        async def test_endpoint(request: Request):
            return {"user": request.state.user}

        # Act
        client = TestClient(app)
        response = client.get("/test", headers={"Authorization": "Bearer test-token"})

        # Assert: Worker-safe ID should be preserved
        assert response.status_code == 200
        user_data = response.json()["user"]
        assert user_data["user_id"] == "user:test_gw0_alice"
        assert user_data["username"] == "alice"
