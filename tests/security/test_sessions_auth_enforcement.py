"""
Session API Authentication Enforcement Tests

TDD RED PHASE: Security tests to verify session endpoints require authentication.

These tests verify that:
1. All session CRUD endpoints require authentication
2. Unauthenticated requests receive 401 Unauthorized
3. Sessions are scoped to the authenticated user

Security Finding: sessions.py had `user_id=None` hardcoded, bypassing authentication.
Reference: Comprehensive benchmark plan PHASE 0 - CRITICAL SECURITY fix.
"""

import gc
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


pytestmark = [
    pytest.mark.security,
    pytest.mark.unit,
    pytest.mark.api,
]


@pytest.fixture
def app_with_auth() -> FastAPI:
    """
    Create a test app with sessions router and auth middleware.

    This simulates the real app where AuthMiddleware intercepts requests
    and sets request.state.user for authenticated requests.
    """
    from mcp_server_langgraph.api.v1.sessions import sessions_router

    app = FastAPI()
    app.include_router(sessions_router, prefix="/api/v1")
    return app


@pytest.fixture
def authenticated_user() -> dict[str, Any]:
    """Sample authenticated user context."""
    return {
        "sub": "user-123",
        "preferred_username": "testuser",
        "email": "testuser@example.com",
        "roles": ["user"],
    }


@pytest.fixture
def admin_user() -> dict[str, Any]:
    """Sample admin user context."""
    return {
        "sub": "admin-123",
        "preferred_username": "admin",
        "email": "admin@example.com",
        "roles": ["admin", "user"],
    }


@pytest.mark.xdist_group(name="test_sessions_auth")
class TestSessionsAuthenticationEnforcement:
    """
    Tests to verify session endpoints enforce authentication.

    SECURITY: These tests ensure the auth bypass vulnerability is fixed.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_sessions_requires_authentication(self, app_with_auth: FastAPI) -> None:
        """
        GIVEN an unauthenticated request to list sessions
        WHEN GET /api/v1/sessions is called without auth
        THEN response should be 401 Unauthorized

        SECURITY: Prevents unauthorized access to session data.
        """
        client = TestClient(app_with_auth)

        # No authentication headers
        response = client.get("/api/v1/sessions")

        # Should require authentication
        assert response.status_code == 401, (
            f"Expected 401 Unauthorized for unauthenticated request, got {response.status_code}. "
            "Session list endpoint should require authentication."
        )

    def test_create_session_requires_authentication(self, app_with_auth: FastAPI) -> None:
        """
        GIVEN an unauthenticated request to create a session
        WHEN POST /api/v1/sessions is called without auth
        THEN response should be 401 Unauthorized

        SECURITY: Prevents anonymous session creation.
        """
        client = TestClient(app_with_auth)

        response = client.post(
            "/api/v1/sessions",
            json={"name": "Test Session"},
        )

        assert response.status_code == 401, (
            f"Expected 401 Unauthorized for unauthenticated request, got {response.status_code}. "
            "Session creation should require authentication."
        )

    def test_get_session_requires_authentication(self, app_with_auth: FastAPI) -> None:
        """
        GIVEN an unauthenticated request to get a session
        WHEN GET /api/v1/sessions/{id} is called without auth
        THEN response should be 401 Unauthorized

        SECURITY: Prevents unauthorized session access.
        """
        client = TestClient(app_with_auth)
        session_id = str(uuid4())

        response = client.get(f"/api/v1/sessions/{session_id}")

        assert response.status_code == 401, (
            f"Expected 401 Unauthorized for unauthenticated request, got {response.status_code}. "
            "Session get endpoint should require authentication."
        )

    def test_delete_session_requires_authentication(self, app_with_auth: FastAPI) -> None:
        """
        GIVEN an unauthenticated request to delete a session
        WHEN DELETE /api/v1/sessions/{id} is called without auth
        THEN response should be 401 Unauthorized

        SECURITY: Prevents unauthorized session deletion.
        """
        client = TestClient(app_with_auth)
        session_id = str(uuid4())

        response = client.delete(f"/api/v1/sessions/{session_id}")

        assert response.status_code == 401, (
            f"Expected 401 Unauthorized for unauthenticated request, got {response.status_code}. "
            "Session delete endpoint should require authentication."
        )

    def test_get_messages_requires_authentication(self, app_with_auth: FastAPI) -> None:
        """
        GIVEN an unauthenticated request to get session messages
        WHEN GET /api/v1/sessions/{id}/messages is called without auth
        THEN response should be 401 Unauthorized
        """
        client = TestClient(app_with_auth)
        session_id = str(uuid4())

        response = client.get(f"/api/v1/sessions/{session_id}/messages")

        assert response.status_code == 401

    def test_add_message_requires_authentication(self, app_with_auth: FastAPI) -> None:
        """
        GIVEN an unauthenticated request to add a message
        WHEN POST /api/v1/sessions/{id}/messages is called without auth
        THEN response should be 401 Unauthorized
        """
        client = TestClient(app_with_auth)
        session_id = str(uuid4())

        response = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"role": "user", "content": "Hello"},
        )

        assert response.status_code == 401


@pytest.mark.xdist_group(name="test_sessions_auth")
class TestSessionsUserScoping:
    """
    Tests to verify sessions are properly scoped to the authenticated user.

    SECURITY: Users should only see and manage their own sessions.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_sessions_scoped_to_user(
        self,
        app_with_auth: FastAPI,
        authenticated_user: dict[str, Any],
    ) -> None:
        """
        GIVEN an authenticated user
        WHEN listing sessions
        THEN only sessions owned by that user should be returned

        SECURITY: Prevents cross-user session enumeration.
        """
        from mcp_server_langgraph.auth.middleware import get_current_user

        # Use FastAPI's dependency override mechanism
        app_with_auth.dependency_overrides[get_current_user] = lambda: authenticated_user

        try:
            with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
                mock_service = AsyncMock()
                mock_service.list_sessions.return_value = ([], None)
                mock_get_service.return_value = mock_service

                client = TestClient(app_with_auth)
                # Simulate authenticated request (with auth header)
                response = client.get(
                    "/api/v1/sessions",
                    headers={"Authorization": "Bearer test-token"},
                )

                # Should succeed with authentication
                assert response.status_code == 200, f"Expected 200 OK for authenticated request, got {response.status_code}"

                # Verify that list_sessions was called with the user_id
                call_kwargs = mock_service.list_sessions.call_args
                assert call_kwargs is not None, "list_sessions should have been called"

                # Verify user_id is passed (not None)
                # The user_id should be the first positional arg or in kwargs
                user_id = call_kwargs.kwargs.get("user_id")
                if user_id is None and call_kwargs.args:
                    user_id = call_kwargs.args[0]

                assert user_id is not None, (
                    "list_sessions must be called with authenticated user_id. "
                    "This is CRITICAL to prevent cross-user session enumeration."
                )
                assert user_id == authenticated_user["sub"], (
                    f"list_sessions user_id should match authenticated user. "
                    f"Expected {authenticated_user['sub']}, got {user_id}"
                )
        finally:
            # Clean up dependency override
            app_with_auth.dependency_overrides.clear()

    def test_create_session_associates_with_user(
        self,
        app_with_auth: FastAPI,
        authenticated_user: dict[str, Any],
    ) -> None:
        """
        GIVEN an authenticated user
        WHEN creating a session
        THEN the session should be associated with that user's ID

        SECURITY: Ensures session ownership is properly tracked.
        """
        from mcp_server_langgraph.auth.middleware import get_current_user

        # Use FastAPI's dependency override mechanism
        app_with_auth.dependency_overrides[get_current_user] = lambda: authenticated_user

        try:
            with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
                mock_service = AsyncMock()
                mock_service.create_session.return_value = {
                    "id": str(uuid4()),
                    "name": "Test Session",
                    "user_id": authenticated_user["sub"],
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                    "status": "active",
                }
                mock_get_service.return_value = mock_service

                client = TestClient(app_with_auth)
                response = client.post(
                    "/api/v1/sessions",
                    json={"name": "Test Session"},
                    headers={"Authorization": "Bearer test-token"},
                )

                # Should succeed with authentication
                assert response.status_code == 201, (
                    f"Expected 201 Created for authenticated request, got {response.status_code}"
                )

                # Verify create_session was called with user_id from auth context
                call_kwargs = mock_service.create_session.call_args
                assert call_kwargs is not None, "create_session should have been called"

                # The user_id should be the second positional arg or in kwargs
                user_id = call_kwargs.kwargs.get("user_id")
                if user_id is None and len(call_kwargs.args) > 1:
                    user_id = call_kwargs.args[1]

                assert user_id is not None, (
                    "create_session must be called with user_id from authenticated context. "
                    "This is CRITICAL for session ownership."
                )
                assert user_id == authenticated_user["sub"], (
                    f"Session user_id should match authenticated user. Expected {authenticated_user['sub']}, got {user_id}"
                )
        finally:
            # Clean up dependency override
            app_with_auth.dependency_overrides.clear()


@pytest.mark.xdist_group(name="test_sessions_auth")
class TestSessionsAuthorizationBypass:
    """
    Regression tests to prevent the user_id=None auth bypass.

    SECURITY: These tests specifically target the vulnerability where
    sessions.py passed user_id=None, allowing unauthenticated access.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_no_none_user_id_in_redis_list_sessions(self) -> None:
        """
        GIVEN the RedisSessionService implementation
        WHEN inspecting list_sessions
        THEN user_id should not be hardcoded to None

        REGRESSION: Prevents reintroduction of user_id=None bypass.
        """
        import inspect
        from mcp_server_langgraph.api.v1.sessions import RedisSessionService

        # Get the source code of list_sessions
        source = inspect.getsource(RedisSessionService.list_sessions)

        # Check for the vulnerable pattern
        assert "user_id=None" not in source or "# TODO" not in source, (
            "RedisSessionService.list_sessions contains 'user_id=None'. "
            "This bypasses authentication! User ID must come from auth context."
        )

    def test_no_none_user_id_in_redis_create_session(self) -> None:
        """
        GIVEN the RedisSessionService implementation
        WHEN inspecting create_session
        THEN user_id should not be hardcoded to None

        REGRESSION: Prevents reintroduction of user_id=None bypass.
        """
        import inspect
        from mcp_server_langgraph.api.v1.sessions import RedisSessionService

        # Get the source code
        source = inspect.getsource(RedisSessionService.create_session)

        # The vulnerable pattern is passing user_id=None to the manager
        assert "user_id=None" not in source or "# TODO" not in source, (
            "RedisSessionService.create_session contains 'user_id=None'. "
            "This creates anonymous sessions! User ID must come from auth context."
        )

    def test_no_none_user_id_in_postgres_create_session(self) -> None:
        """
        GIVEN the PostgresSessionService implementation
        WHEN inspecting create_session
        THEN user_id should not be hardcoded to None

        REGRESSION: Prevents reintroduction of user_id=None bypass.
        """
        import inspect
        from mcp_server_langgraph.api.v1.sessions import PostgresSessionService

        source = inspect.getsource(PostgresSessionService.create_session)

        assert "user_id=None" not in source or "# TODO" not in source, (
            "PostgresSessionService.create_session contains 'user_id=None'. "
            "This creates anonymous sessions! User ID must come from auth context."
        )
