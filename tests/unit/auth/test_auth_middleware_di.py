"""
Tests for DI-based auth middleware access (replacing global state).

This test module validates the migration from global middleware state
to FastAPI's native dependency injection pattern.

RED-GREEN-REFACTOR: Start with failing tests to define expected behavior.
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

# Mark as unit test
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="auth_middleware_di")
class TestGetAuthMiddlewareFromRequest:
    """Test get_auth_middleware_from_request dependency."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_returns_auth_middleware_from_app_state(self) -> None:
        """Test that get_auth_middleware_from_request returns auth from app.state."""
        from mcp_server_langgraph.auth.dependencies import get_auth_middleware_from_request

        # Create mock request with app.state.auth_middleware
        mock_auth = MagicMock()
        mock_auth.name = "test_auth_middleware"

        mock_app = MagicMock()
        mock_app.state.auth_middleware = mock_auth

        mock_request = MagicMock()
        mock_request.app = mock_app

        # When we get auth from request
        result = get_auth_middleware_from_request(mock_request)

        # Then we should get the auth middleware
        assert result is mock_auth

    def test_returns_none_when_auth_middleware_not_set(self) -> None:
        """Test that returns None when app.state.auth_middleware is not set."""
        from mcp_server_langgraph.auth.dependencies import get_auth_middleware_from_request

        # Create mock request without auth_middleware in app.state
        mock_app = MagicMock()
        # Remove the auth_middleware attribute
        del mock_app.state.auth_middleware

        mock_request = MagicMock()
        mock_request.app = mock_app

        # When we get auth from request
        result = get_auth_middleware_from_request(mock_request)

        # Then we should get None
        assert result is None

    def test_raises_error_when_none_and_required(self) -> None:
        """Test that require_auth_middleware_from_request raises when auth not set."""
        from mcp_server_langgraph.auth.dependencies import require_auth_middleware_from_request

        # Create mock request without auth_middleware in app.state
        mock_app = MagicMock()
        del mock_app.state.auth_middleware

        mock_request = MagicMock()
        mock_request.app = mock_app

        # When we require auth from request without it being set
        # Then we should get RuntimeError
        with pytest.raises(RuntimeError, match="Auth middleware not initialized"):
            require_auth_middleware_from_request(mock_request)


@pytest.mark.xdist_group(name="auth_middleware_di")
class TestGetCurrentUserDI:
    """Test get_current_user dependency with DI pattern."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_current_user_uses_request_scoped_auth(self) -> None:
        """Test get_current_user uses auth from app.state, not global."""
        from mcp_server_langgraph.auth.dependencies import get_current_user

        # Create mock auth middleware with verify_token
        mock_auth = AsyncMock()  # noqa: async-mock-config
        mock_auth.verify_token = AsyncMock(
            return_value=MagicMock(
                valid=True,
                payload={
                    "sub": "test-user",
                    "preferred_username": "testuser",
                    "email": "test@example.com",
                },
            )
        )

        # Create mock request with auth in app.state
        mock_app = MagicMock()
        mock_app.state.auth_middleware = mock_auth

        mock_request = MagicMock()
        mock_request.app = mock_app
        mock_request.headers = {"Authorization": "Bearer test-token"}
        mock_request.state = MagicMock()
        mock_request.state.user = None  # Not already set

        # Make hasattr return False for user
        delattr(mock_request.state, "user")

        # When we get current user
        user = await get_current_user(mock_request)

        # Then auth.verify_token should have been called
        mock_auth.verify_token.assert_called_once_with("test-token")
        assert user["user_id"] is not None


@pytest.mark.xdist_group(name="auth_middleware_di")
class TestGlobalMiddlewareDeprecation:
    """Test that global middleware functions work with deprecation warning."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_global_functions_still_work_for_backward_compatibility(self) -> None:
        """Test that set_global/get_global functions still work."""
        from mcp_server_langgraph.auth.dependencies import (
            set_global_auth_middleware,
            get_auth_middleware,
            clear_global_auth_middleware,
        )

        # Clear first
        clear_global_auth_middleware()

        # Set global
        mock_auth = MagicMock()
        set_global_auth_middleware(mock_auth)

        # Get global
        result = get_auth_middleware()
        assert result is mock_auth

        # Clear for other tests
        clear_global_auth_middleware()

    def test_get_auth_middleware_raises_when_not_set(self) -> None:
        """Test that get_auth_middleware raises RuntimeError when not initialized."""
        from mcp_server_langgraph.auth.dependencies import (
            get_auth_middleware,
            clear_global_auth_middleware,
        )

        # Clear first
        clear_global_auth_middleware()

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Auth middleware not initialized"):
            get_auth_middleware()
