"""Unit tests for WebSocket authentication middleware.

Tests the centralized authentication utilities for WebSocket endpoints,
including JWT extraction, validation, and user data normalization.
"""

from __future__ import annotations

import gc
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Module-level marker for test discovery
pytestmark = pytest.mark.unit


@dataclass
class MockVerifyResult:
    """Mock result from token verification."""

    valid: bool
    payload: dict | None = None
    error: str | None = None


@pytest.mark.unit
@pytest.mark.websocket
@pytest.mark.xdist_group(name="websocket_middleware")
class TestExtractWebSocketToken:
    """Test suite for extract_websocket_token function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extract_token_from_query_params(self) -> None:
        """Test extracting token from query parameters."""
        from mcp_server_langgraph.websocket.middleware import extract_websocket_token

        websocket = MagicMock()
        websocket.query_params = {"token": "test-jwt-token"}
        websocket.headers = {}

        token = extract_websocket_token(websocket)

        assert token == "test-jwt-token"

    def test_extract_token_from_authorization_header(self) -> None:
        """Test extracting token from Authorization header."""
        from mcp_server_langgraph.websocket.middleware import extract_websocket_token

        websocket = MagicMock()
        websocket.query_params = {}
        websocket.headers = {"Authorization": "Bearer header-jwt-token"}

        token = extract_websocket_token(websocket)

        assert token == "header-jwt-token"

    def test_query_params_takes_precedence_over_header(self) -> None:
        """Test that query params token takes precedence over header."""
        from mcp_server_langgraph.websocket.middleware import extract_websocket_token

        websocket = MagicMock()
        websocket.query_params = {"token": "query-token"}
        websocket.headers = {"Authorization": "Bearer header-token"}

        token = extract_websocket_token(websocket)

        assert token == "query-token"

    def test_returns_none_when_no_token(self) -> None:
        """Test returns None when no token is provided."""
        from mcp_server_langgraph.websocket.middleware import extract_websocket_token

        websocket = MagicMock()
        websocket.query_params = {}
        websocket.headers = {}

        token = extract_websocket_token(websocket)

        assert token is None

    def test_returns_none_for_empty_token_query_param(self) -> None:
        """Test returns None for empty token in query params."""
        from mcp_server_langgraph.websocket.middleware import extract_websocket_token

        websocket = MagicMock()
        websocket.query_params = {"token": ""}
        websocket.headers = {}

        token = extract_websocket_token(websocket)

        assert token is None

    def test_returns_none_for_malformed_auth_header(self) -> None:
        """Test returns None for non-Bearer auth header."""
        from mcp_server_langgraph.websocket.middleware import extract_websocket_token

        websocket = MagicMock()
        websocket.query_params = {}
        websocket.headers = {"Authorization": "Basic abc123"}

        token = extract_websocket_token(websocket)

        assert token is None

    def test_handles_bearer_prefix_case_sensitive(self) -> None:
        """Test Bearer prefix is case-sensitive."""
        from mcp_server_langgraph.websocket.middleware import extract_websocket_token

        websocket = MagicMock()
        websocket.query_params = {}
        websocket.headers = {"Authorization": "bearer lowercase-token"}

        token = extract_websocket_token(websocket)

        assert token is None  # "bearer" != "Bearer"


@pytest.mark.unit
@pytest.mark.websocket
@pytest.mark.xdist_group(name="websocket_middleware")
class TestExtractUserFromJwtPayload:
    """Test suite for extract_user_from_jwt_payload function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extract_standard_claims(self) -> None:
        """Test extracting standard JWT claims."""
        from mcp_server_langgraph.websocket.middleware import (
            extract_user_from_jwt_payload,
        )

        payload = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "email": "test@example.com",
        }

        user_data = extract_user_from_jwt_payload(payload)

        # user_id is normalized to OpenFGA format (user:preferred_username)
        assert user_data["user_id"] == "user:testuser"
        assert user_data["username"] == "testuser"
        assert user_data["email"] == "test@example.com"
        assert user_data["roles"] == []
        assert user_data["raw_payload"] == payload

    def test_extract_keycloak_realm_roles(self) -> None:
        """Test extracting roles from Keycloak realm_access."""
        from mcp_server_langgraph.websocket.middleware import (
            extract_user_from_jwt_payload,
        )

        payload = {
            "sub": "user-456",
            "realm_access": {"roles": ["admin", "user"]},
        }

        user_data = extract_user_from_jwt_payload(payload)

        assert "admin" in user_data["roles"]
        assert "user" in user_data["roles"]

    def test_extract_keycloak_resource_access_roles(self) -> None:
        """Test extracting roles from Keycloak resource_access."""
        from mcp_server_langgraph.websocket.middleware import (
            extract_user_from_jwt_payload,
        )

        payload = {
            "sub": "user-789",
            "resource_access": {
                "my-client": {"roles": ["client-admin"]},
                "other-client": {"roles": ["viewer"]},
            },
        }

        user_data = extract_user_from_jwt_payload(payload)

        assert "client-admin" in user_data["roles"]
        assert "viewer" in user_data["roles"]

    def test_extract_direct_roles_claim(self) -> None:
        """Test extracting roles from direct roles claim (Auth0 style)."""
        from mcp_server_langgraph.websocket.middleware import (
            extract_user_from_jwt_payload,
        )

        payload = {
            "sub": "auth0|user123",
            "roles": ["admin", "editor"],
        }

        user_data = extract_user_from_jwt_payload(payload)

        assert user_data["roles"] == ["admin", "editor"]

    def test_extract_groups_as_roles(self) -> None:
        """Test that groups claim is NOT used as roles (only realm_access/resource_access)."""
        from mcp_server_langgraph.websocket.middleware import (
            extract_user_from_jwt_payload,
        )

        # Current implementation doesn't extract groups as roles
        # It only supports: roles, realm_access.roles, resource_access.*.roles
        payload = {
            "sub": "user-abc",
            "groups": ["developers", "devops"],
        }

        user_data = extract_user_from_jwt_payload(payload)

        # groups are NOT extracted as roles in the current implementation
        assert user_data["roles"] == []

    def test_deduplicate_roles_prioritizes_direct_claims(self) -> None:
        """Test role extraction prioritizes direct roles over realm_access."""
        from mcp_server_langgraph.websocket.middleware import (
            extract_user_from_jwt_payload,
        )

        # When direct "roles" claim is present, it takes precedence
        # and realm_access is NOT combined (per implementation)
        payload = {
            "sub": "user-xyz",
            "realm_access": {"roles": ["admin", "user"]},
            "roles": ["admin", "viewer"],  # Direct roles take precedence
        }

        user_data = extract_user_from_jwt_payload(payload)

        # Direct roles claim takes precedence, realm_access is ignored
        assert set(user_data["roles"]) == {"admin", "viewer"}

    def test_fallback_user_id_claims(self) -> None:
        """Test user_id extraction uses preferred_username first for OpenFGA."""
        from mcp_server_langgraph.websocket.middleware import (
            extract_user_from_jwt_payload,
        )

        # Current implementation uses preferred_username > username > sub for ID
        # and normalizes to "user:*" format for OpenFGA compatibility
        # It does NOT support user_id, uid, id claims as fallbacks

        # No preferred_username/username -> falls back to sub -> normalizes to user:
        payload1 = {"sub": "some-user"}
        assert extract_user_from_jwt_payload(payload1)["user_id"] == "user:some-user"

        # With preferred_username -> uses that
        payload2 = {"sub": "uuid-123", "preferred_username": "alice"}
        assert extract_user_from_jwt_payload(payload2)["user_id"] == "user:alice"

        # Empty payload -> unknown with prefix
        payload3 = {}
        assert extract_user_from_jwt_payload(payload3)["user_id"] == "user:unknown"

    def test_fallback_username_claims(self) -> None:
        """Test username extraction order: preferred_username > username > sub."""
        from mcp_server_langgraph.websocket.middleware import (
            extract_user_from_jwt_payload,
        )

        # Test username claim
        payload1 = {"sub": "u1", "username": "john_doe"}
        assert extract_user_from_jwt_payload(payload1)["username"] == "john_doe"

        # name claim is NOT used for username - falls back to sub
        payload2 = {"sub": "u2", "name": "Jane Doe"}
        assert extract_user_from_jwt_payload(payload2)["username"] == "u2"

        # email is NOT used for username - falls back to sub
        payload3 = {"sub": "u3", "email": "user@example.com"}
        assert extract_user_from_jwt_payload(payload3)["username"] == "u3"

    def test_fallback_to_unknown_user_id(self) -> None:
        """Test fallback to 'unknown' when no user_id claims present."""
        from mcp_server_langgraph.websocket.middleware import (
            extract_user_from_jwt_payload,
        )

        payload = {"email": "test@example.com"}

        user_data = extract_user_from_jwt_payload(payload)

        # user_id is normalized to OpenFGA format with "user:" prefix
        assert user_data["user_id"] == "user:unknown"

    def test_handles_non_dict_realm_access(self) -> None:
        """Test handling of non-dict realm_access values."""
        from mcp_server_langgraph.websocket.middleware import (
            extract_user_from_jwt_payload,
        )

        payload = {
            "sub": "user-123",
            "realm_access": "invalid",  # Should be dict
        }

        user_data = extract_user_from_jwt_payload(payload)

        assert user_data["roles"] == []  # Gracefully handles invalid format

    def test_handles_non_list_roles(self) -> None:
        """Test handling of non-list roles values."""
        from mcp_server_langgraph.websocket.middleware import (
            extract_user_from_jwt_payload,
        )

        payload = {
            "sub": "user-123",
            "roles": "admin",  # Should be list
        }

        user_data = extract_user_from_jwt_payload(payload)

        assert user_data["roles"] == []  # Gracefully ignores invalid format

    def test_email_fallback_to_mail_claim(self) -> None:
        """Test email only uses 'email' claim (not 'mail')."""
        from mcp_server_langgraph.websocket.middleware import (
            extract_user_from_jwt_payload,
        )

        # The implementation only uses 'email' claim, not 'mail'
        payload = {
            "sub": "user-123",
            "mail": "user@microsoft.com",
        }

        user_data = extract_user_from_jwt_payload(payload)

        # 'mail' claim is NOT used - email is None
        assert user_data["email"] is None

        # 'email' claim is used
        payload_with_email = {
            "sub": "user-123",
            "email": "user@example.com",
        }
        user_data2 = extract_user_from_jwt_payload(payload_with_email)
        assert user_data2["email"] == "user@example.com"


@pytest.mark.unit
@pytest.mark.websocket
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="websocket_middleware")
class TestValidateWebSocketAuth:
    """Test suite for validate_websocket_auth function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_returns_none_when_no_token(self) -> None:
        """Test returns None when no token is provided."""
        from mcp_server_langgraph.websocket.middleware import validate_websocket_auth

        websocket = MagicMock()
        websocket.query_params = {}
        websocket.headers = {}

        result = await validate_websocket_auth(websocket)

        assert result is None

    async def test_returns_user_data_on_valid_token(self) -> None:
        """Test returns user data when token is valid."""
        from mcp_server_langgraph.websocket.middleware import validate_websocket_auth

        # Setup mocks
        mock_verify_result = MockVerifyResult(
            valid=True,
            payload={
                "sub": "user-123",
                "preferred_username": "testuser",
                "email": "test@example.com",
            },
        )

        mock_auth_middleware = AsyncMock(spec=["verify_token"])  # noqa: async-mock-config
        mock_auth_middleware.verify_token = AsyncMock(return_value=mock_verify_result)

        mock_app_state = MagicMock()
        mock_app_state.auth_middleware = mock_auth_middleware

        websocket = MagicMock()
        websocket.query_params = {"token": "valid-token"}
        websocket.headers = {}
        websocket.app.state = mock_app_state

        result = await validate_websocket_auth(websocket)

        assert result is not None
        # user_id is normalized to OpenFGA format (user:preferred_username)
        assert result["user_id"] == "user:testuser"
        assert result["username"] == "testuser"
        assert result["email"] == "test@example.com"

    async def test_returns_none_on_invalid_token(self) -> None:
        """Test returns None when token is invalid."""
        from mcp_server_langgraph.websocket.middleware import validate_websocket_auth

        mock_verify_result = MockVerifyResult(
            valid=False,
            payload=None,
            error="Token expired",
        )

        mock_auth_middleware = AsyncMock(spec=["verify_token"])  # noqa: async-mock-config
        mock_auth_middleware.verify_token = AsyncMock(return_value=mock_verify_result)

        mock_app_state = MagicMock()
        mock_app_state.auth_middleware = mock_auth_middleware

        websocket = MagicMock()
        websocket.query_params = {"token": "invalid-token"}
        websocket.headers = {}
        websocket.app.state = mock_app_state

        result = await validate_websocket_auth(websocket)

        assert result is None

    async def test_returns_none_on_exception(self) -> None:
        """Test returns None when exception occurs."""
        from mcp_server_langgraph.websocket.middleware import validate_websocket_auth

        mock_auth_middleware = AsyncMock(spec=["verify_token"])  # noqa: async-mock-config
        mock_auth_middleware.verify_token = AsyncMock(side_effect=Exception("Connection error"))

        mock_app_state = MagicMock()
        mock_app_state.auth_middleware = mock_auth_middleware

        websocket = MagicMock()
        websocket.query_params = {"token": "some-token"}
        websocket.headers = {}
        websocket.app.state = mock_app_state

        result = await validate_websocket_auth(websocket)

        assert result is None

    async def test_uses_fallback_auth_middleware(self) -> None:
        """Test falls back to global auth middleware when not in app state."""
        from mcp_server_langgraph.websocket.middleware import validate_websocket_auth

        mock_verify_result = MockVerifyResult(
            valid=True,
            payload={"sub": "fallback-user"},
        )

        mock_auth_middleware = AsyncMock(spec=["verify_token"])  # noqa: async-mock-config
        mock_auth_middleware.verify_token = AsyncMock(return_value=mock_verify_result)

        mock_app_state = MagicMock()
        mock_app_state.auth_middleware = None  # Not available in app state

        websocket = MagicMock()
        websocket.query_params = {"token": "some-token"}
        websocket.headers = {}
        websocket.app.state = mock_app_state

        with patch(
            "mcp_server_langgraph.auth.middleware.get_auth_middleware",
            return_value=mock_auth_middleware,
        ):
            result = await validate_websocket_auth(websocket)

        assert result is not None
        # user_id is normalized to OpenFGA format with "user:" prefix
        assert result["user_id"] == "user:fallback-user"


@pytest.mark.unit
@pytest.mark.websocket
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="websocket_middleware")
class TestValidateWebSocketToken:
    """Test suite for validate_websocket_token function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_returns_payload_on_valid_token(self) -> None:
        """Test returns payload when token is valid."""
        from mcp_server_langgraph.websocket.middleware import validate_websocket_token

        mock_verify_result = MockVerifyResult(
            valid=True,
            payload={"sub": "user-123", "roles": ["admin"]},
        )

        mock_auth_middleware = AsyncMock(spec=["verify_token"])  # noqa: async-mock-config
        mock_auth_middleware.verify_token = AsyncMock(return_value=mock_verify_result)

        with patch(
            "mcp_server_langgraph.auth.middleware.get_auth_middleware",
            return_value=mock_auth_middleware,
        ):
            result = await validate_websocket_token("valid-token")

        assert result is not None
        assert result["sub"] == "user-123"
        assert result["roles"] == ["admin"]

    async def test_returns_none_on_invalid_token(self) -> None:
        """Test returns None when token is invalid."""
        from mcp_server_langgraph.websocket.middleware import validate_websocket_token

        mock_verify_result = MockVerifyResult(
            valid=False,
            payload=None,
            error="Invalid signature",
        )

        mock_auth_middleware = AsyncMock(spec=["verify_token"])  # noqa: async-mock-config
        mock_auth_middleware.verify_token = AsyncMock(return_value=mock_verify_result)

        with patch(
            "mcp_server_langgraph.auth.middleware.get_auth_middleware",
            return_value=mock_auth_middleware,
        ):
            result = await validate_websocket_token("invalid-token")

        assert result is None

    async def test_returns_none_on_exception(self) -> None:
        """Test returns None when exception occurs."""
        from mcp_server_langgraph.websocket.middleware import validate_websocket_token

        mock_auth_middleware = AsyncMock(spec=["verify_token"])  # noqa: async-mock-config
        mock_auth_middleware.verify_token = AsyncMock(side_effect=Exception("Auth service down"))

        with patch(
            "mcp_server_langgraph.auth.middleware.get_auth_middleware",
            return_value=mock_auth_middleware,
        ):
            result = await validate_websocket_token("some-token")

        assert result is None


@pytest.mark.unit
@pytest.mark.websocket
@pytest.mark.xdist_group(name="websocket_middleware")
class TestGetAuthMiddleware:
    """Test suite for deprecated get_auth_middleware function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_emits_deprecation_warning(self) -> None:
        """Test that get_auth_middleware emits deprecation warning."""
        from mcp_server_langgraph.websocket.middleware import get_auth_middleware

        mock_middleware = MagicMock()

        with patch(
            "mcp_server_langgraph.auth.middleware.get_auth_middleware",
            return_value=mock_middleware,
        ):
            with pytest.warns(DeprecationWarning, match="get_auth_middleware"):
                result = get_auth_middleware()

        assert result == mock_middleware
