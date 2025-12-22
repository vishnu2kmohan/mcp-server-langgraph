"""
WebSocket Authentication Middleware Tests.

Tests for the centralized WebSocket authentication utilities:
- extract_websocket_token: JWT extraction from query params or headers
- validate_websocket_auth: Full authentication flow
- extract_user_from_jwt_payload: JWT claim normalization
- validate_websocket_token: Token validation
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.websocket.middleware import (
    extract_user_from_jwt_payload,
    extract_websocket_token,
    validate_websocket_auth,
    validate_websocket_token,
)


pytestmark = [pytest.mark.unit, pytest.mark.websocket, pytest.mark.auth]


@pytest.mark.xdist_group(name="websocket_middleware")
class TestExtractWebSocketToken:
    """Tests for extract_websocket_token function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extracts_token_from_query_param(self) -> None:
        """Token from query param should be extracted."""
        mock_ws = MagicMock()
        mock_ws.query_params = {"token": "jwt-from-query"}
        mock_ws.headers = {}

        result = extract_websocket_token(mock_ws)

        assert result == "jwt-from-query"

    def test_extracts_token_from_authorization_header(self) -> None:
        """Token from Authorization header should be extracted."""
        mock_ws = MagicMock()
        mock_ws.query_params = {}
        mock_ws.headers = {"Authorization": "Bearer jwt-from-header"}

        result = extract_websocket_token(mock_ws)

        assert result == "jwt-from-header"

    def test_query_param_takes_precedence_over_header(self) -> None:
        """Query param token should take precedence over header."""
        mock_ws = MagicMock()
        mock_ws.query_params = {"token": "query-token"}
        mock_ws.headers = {"Authorization": "Bearer header-token"}

        result = extract_websocket_token(mock_ws)

        assert result == "query-token"

    def test_returns_none_when_no_token(self) -> None:
        """Should return None when no token is provided."""
        mock_ws = MagicMock()
        mock_ws.query_params = {}
        mock_ws.headers = {}

        result = extract_websocket_token(mock_ws)

        assert result is None

    def test_returns_none_for_non_bearer_auth_header(self) -> None:
        """Should return None for non-Bearer authorization."""
        mock_ws = MagicMock()
        mock_ws.query_params = {}
        mock_ws.headers = {"Authorization": "Basic sometoken"}

        result = extract_websocket_token(mock_ws)

        assert result is None

    def test_returns_none_for_empty_query_token(self) -> None:
        """Should return None for empty query token."""
        mock_ws = MagicMock()
        mock_ws.query_params = {"token": ""}
        mock_ws.headers = {}

        result = extract_websocket_token(mock_ws)

        assert result is None

    def test_handles_missing_headers_attribute(self) -> None:
        """Should handle websocket with get() returning None."""
        mock_ws = MagicMock()
        mock_ws.query_params = MagicMock()
        mock_ws.query_params.get = MagicMock(return_value=None)
        mock_ws.headers = MagicMock()
        mock_ws.headers.get = MagicMock(return_value="")

        result = extract_websocket_token(mock_ws)

        assert result is None


@pytest.mark.xdist_group(name="websocket_middleware")
class TestExtractUserFromJwtPayload:
    """Tests for extract_user_from_jwt_payload function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extracts_user_id_from_sub_claim(self) -> None:
        """User ID should be extracted from sub claim."""
        payload = {"sub": "user-123"}

        result = extract_user_from_jwt_payload(payload)

        assert result["user_id"] == "user-123"

    def test_extracts_user_id_from_user_id_claim(self) -> None:
        """User ID should fall back to user_id claim."""
        payload = {"user_id": "user-456"}

        result = extract_user_from_jwt_payload(payload)

        assert result["user_id"] == "user-456"

    def test_extracts_user_id_from_uid_claim(self) -> None:
        """User ID should fall back to uid claim."""
        payload = {"uid": "user-789"}

        result = extract_user_from_jwt_payload(payload)

        assert result["user_id"] == "user-789"

    def test_extracts_user_id_from_id_claim(self) -> None:
        """User ID should fall back to id claim."""
        payload = {"id": "user-abc"}

        result = extract_user_from_jwt_payload(payload)

        assert result["user_id"] == "user-abc"

    def test_user_id_defaults_to_unknown(self) -> None:
        """User ID should default to 'unknown' when missing."""
        payload: dict[str, Any] = {}

        result = extract_user_from_jwt_payload(payload)

        assert result["user_id"] == "unknown"

    def test_extracts_username_from_preferred_username(self) -> None:
        """Username should be extracted from preferred_username claim."""
        payload = {"sub": "123", "preferred_username": "alice"}

        result = extract_user_from_jwt_payload(payload)

        assert result["username"] == "alice"

    def test_extracts_username_from_username_claim(self) -> None:
        """Username should fall back to username claim."""
        payload = {"sub": "123", "username": "bob"}

        result = extract_user_from_jwt_payload(payload)

        assert result["username"] == "bob"

    def test_extracts_username_from_name_claim(self) -> None:
        """Username should fall back to name claim."""
        payload = {"sub": "123", "name": "Charlie"}

        result = extract_user_from_jwt_payload(payload)

        assert result["username"] == "Charlie"

    def test_extracts_username_from_email_local_part(self) -> None:
        """Username should fall back to email local part."""
        payload = {"sub": "123", "email": "dave@example.com"}

        result = extract_user_from_jwt_payload(payload)

        assert result["username"] == "dave"

    def test_username_falls_back_to_user_id(self) -> None:
        """Username should fall back to user_id when nothing else available."""
        payload = {"sub": "123"}

        result = extract_user_from_jwt_payload(payload)

        assert result["username"] == "123"

    def test_extracts_email(self) -> None:
        """Email should be extracted from email claim."""
        payload = {"sub": "123", "email": "test@example.com"}

        result = extract_user_from_jwt_payload(payload)

        assert result["email"] == "test@example.com"

    def test_extracts_email_from_mail_claim(self) -> None:
        """Email should fall back to mail claim (LDAP-style)."""
        payload = {"sub": "123", "mail": "test@company.com"}

        result = extract_user_from_jwt_payload(payload)

        assert result["email"] == "test@company.com"

    def test_email_defaults_to_empty(self) -> None:
        """Email should default to empty string when missing."""
        payload = {"sub": "123"}

        result = extract_user_from_jwt_payload(payload)

        assert result["email"] == ""

    def test_extracts_keycloak_realm_roles(self) -> None:
        """Roles should be extracted from Keycloak realm_access.roles."""
        payload = {
            "sub": "123",
            "realm_access": {"roles": ["admin", "user"]},
        }

        result = extract_user_from_jwt_payload(payload)

        assert "admin" in result["roles"]
        assert "user" in result["roles"]

    def test_extracts_keycloak_resource_roles(self) -> None:
        """Roles should be extracted from Keycloak resource_access."""
        payload = {
            "sub": "123",
            "resource_access": {
                "client-a": {"roles": ["role-a"]},
                "client-b": {"roles": ["role-b"]},
            },
        }

        result = extract_user_from_jwt_payload(payload)

        assert "role-a" in result["roles"]
        assert "role-b" in result["roles"]

    def test_extracts_direct_roles_claim(self) -> None:
        """Roles should be extracted from direct roles claim (Auth0-style)."""
        payload = {
            "sub": "123",
            "roles": ["viewer", "editor"],
        }

        result = extract_user_from_jwt_payload(payload)

        assert "viewer" in result["roles"]
        assert "editor" in result["roles"]

    def test_extracts_groups_as_roles(self) -> None:
        """Groups should be extracted and treated as roles."""
        payload = {
            "sub": "123",
            "groups": ["developers", "admins"],
        }

        result = extract_user_from_jwt_payload(payload)

        assert "developers" in result["roles"]
        assert "admins" in result["roles"]

    def test_deduplicates_roles(self) -> None:
        """Duplicate roles should be removed while preserving order."""
        payload = {
            "sub": "123",
            "realm_access": {"roles": ["admin", "user"]},
            "roles": ["user", "admin", "viewer"],
        }

        result = extract_user_from_jwt_payload(payload)

        # Should have exactly 3 unique roles
        assert len(result["roles"]) == 3
        # First occurrence should be preserved
        assert result["roles"].index("admin") < result["roles"].index("viewer")

    def test_includes_raw_payload(self) -> None:
        """Raw payload should be included in result."""
        payload = {"sub": "123", "custom_claim": "value"}

        result = extract_user_from_jwt_payload(payload)

        assert result["raw_payload"] == payload
        assert result["raw_payload"]["custom_claim"] == "value"

    def test_handles_malformed_realm_access(self) -> None:
        """Should handle malformed realm_access gracefully."""
        payload = {
            "sub": "123",
            "realm_access": "not-a-dict",
        }

        result = extract_user_from_jwt_payload(payload)

        assert result["roles"] == []

    def test_handles_malformed_resource_access(self) -> None:
        """Should handle malformed resource_access gracefully."""
        payload = {
            "sub": "123",
            "resource_access": "not-a-dict",
        }

        result = extract_user_from_jwt_payload(payload)

        assert result["roles"] == []

    def test_handles_malformed_roles(self) -> None:
        """Should handle malformed roles claim gracefully."""
        payload = {
            "sub": "123",
            "roles": "not-a-list",
        }

        result = extract_user_from_jwt_payload(payload)

        assert result["roles"] == []

    def test_handles_malformed_groups(self) -> None:
        """Should handle malformed groups claim gracefully."""
        payload = {
            "sub": "123",
            "groups": {"nested": "object"},
        }

        result = extract_user_from_jwt_payload(payload)

        assert result["roles"] == []


@pytest.mark.xdist_group(name="websocket_middleware")
class TestValidateWebSocketAuth:
    """Tests for validate_websocket_auth function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_returns_none_when_no_token(self) -> None:
        """Should return None when no token is provided."""
        mock_ws = MagicMock()
        mock_ws.query_params = {}
        mock_ws.headers = {}
        mock_ws.app = MagicMock()
        mock_ws.app.state = MagicMock()
        mock_ws.app.state.auth_middleware = None

        result = await validate_websocket_auth(mock_ws)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_user_data_for_valid_token(self) -> None:
        """Should return user data for valid token."""
        mock_ws = MagicMock()
        mock_ws.query_params = {"token": "valid-token"}
        mock_ws.headers = {}

        mock_auth = AsyncMock()
        mock_auth.verify_token = AsyncMock(
            return_value=MagicMock(
                valid=True,
                payload={
                    "sub": "user-123",
                    "preferred_username": "testuser",
                    "email": "test@example.com",
                    "realm_access": {"roles": ["user"]},
                },
                error=None,
            )
        )
        mock_ws.app = MagicMock()
        mock_ws.app.state = MagicMock()
        mock_ws.app.state.auth_middleware = mock_auth

        result = await validate_websocket_auth(mock_ws)

        assert result is not None
        assert result["user_id"] == "user-123"
        assert result["username"] == "testuser"
        assert result["email"] == "test@example.com"
        assert "user" in result["roles"]

    @pytest.mark.asyncio
    async def test_returns_none_for_invalid_token(self) -> None:
        """Should return None for invalid token."""
        mock_ws = MagicMock()
        mock_ws.query_params = {"token": "invalid-token"}
        mock_ws.headers = {}

        mock_auth = AsyncMock()
        mock_auth.verify_token = AsyncMock(
            return_value=MagicMock(
                valid=False,
                payload=None,
                error="Token expired",
            )
        )
        mock_ws.app = MagicMock()
        mock_ws.app.state = MagicMock()
        mock_ws.app.state.auth_middleware = mock_auth

        result = await validate_websocket_auth(mock_ws)

        assert result is None

    @pytest.mark.asyncio
    async def test_falls_back_to_global_auth_middleware(self) -> None:
        """Should fall back to global auth middleware when not in app state."""
        mock_ws = MagicMock()
        mock_ws.query_params = {"token": "valid-token"}
        mock_ws.headers = {}
        mock_ws.app = MagicMock()
        mock_ws.app.state = MagicMock()
        mock_ws.app.state.auth_middleware = None

        mock_global_auth = AsyncMock()
        mock_global_auth.verify_token = AsyncMock(
            return_value=MagicMock(
                valid=True,
                payload={
                    "sub": "global-user",
                },
                error=None,
            )
        )

        with patch(
            "mcp_server_langgraph.auth.middleware.get_auth_middleware",
            return_value=mock_global_auth,
        ):
            result = await validate_websocket_auth(mock_ws)

        assert result is not None
        assert result["user_id"] == "global-user"

    @pytest.mark.asyncio
    async def test_returns_none_on_verification_exception(self) -> None:
        """Should return None when verification raises exception."""
        mock_ws = MagicMock()
        mock_ws.query_params = {"token": "valid-token"}
        mock_ws.headers = {}

        mock_auth = AsyncMock()
        mock_auth.verify_token = AsyncMock(side_effect=Exception("Network error"))
        mock_ws.app = MagicMock()
        mock_ws.app.state = MagicMock()
        mock_ws.app.state.auth_middleware = mock_auth

        result = await validate_websocket_auth(mock_ws)

        assert result is None


@pytest.mark.xdist_group(name="websocket_middleware")
class TestValidateWebSocketToken:
    """Tests for validate_websocket_token function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_returns_payload_for_valid_token(self) -> None:
        """Should return payload for valid token."""
        mock_auth = AsyncMock()
        mock_auth.verify_token = AsyncMock(
            return_value=MagicMock(
                valid=True,
                payload={"sub": "user-123", "exp": 9999999999},
                error=None,
            )
        )

        with patch(
            "mcp_server_langgraph.auth.middleware.get_auth_middleware",
            return_value=mock_auth,
        ):
            result = await validate_websocket_token("valid-token")

        assert result is not None
        assert result["sub"] == "user-123"

    @pytest.mark.asyncio
    async def test_returns_none_for_invalid_token(self) -> None:
        """Should return None for invalid token."""
        mock_auth = AsyncMock()
        mock_auth.verify_token = AsyncMock(
            return_value=MagicMock(
                valid=False,
                payload=None,
                error="Invalid signature",
            )
        )

        with patch(
            "mcp_server_langgraph.auth.middleware.get_auth_middleware",
            return_value=mock_auth,
        ):
            result = await validate_websocket_token("invalid-token")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self) -> None:
        """Should return None when verification raises exception."""
        mock_auth = AsyncMock()
        mock_auth.verify_token = AsyncMock(side_effect=Exception("Auth service down"))

        with patch(
            "mcp_server_langgraph.auth.middleware.get_auth_middleware",
            return_value=mock_auth,
        ):
            result = await validate_websocket_token("some-token")

        assert result is None


@pytest.mark.xdist_group(name="websocket_middleware")
class TestDeprecatedGetAuthMiddleware:
    """Tests for deprecated get_auth_middleware function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_emits_deprecation_warning(self) -> None:
        """Should emit deprecation warning when called."""
        from mcp_server_langgraph.websocket.middleware import get_auth_middleware

        with patch(
            "mcp_server_langgraph.auth.middleware.get_auth_middleware",
            return_value=MagicMock(),
        ):
            with pytest.warns(DeprecationWarning, match="get_auth_middleware"):
                get_auth_middleware()
