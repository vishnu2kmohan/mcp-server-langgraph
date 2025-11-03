"""Unit tests for auth.py - Authentication and Authorization"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials

from mcp_server_langgraph.auth.middleware import (
    AuthMiddleware,
    get_current_user,
    require_auth,
    set_global_auth_middleware,
    verify_token,
)


@pytest.mark.unit
@pytest.mark.auth
class TestAuthMiddleware:
    """Test AuthMiddleware class"""

    def test_init(self):
        """Test AuthMiddleware initialization"""
        auth = AuthMiddleware(secret_key="test-key")
        assert auth.secret_key == "test-key"
        assert auth.openfga is None
        assert len(auth.users_db) == 3
        assert "alice" in auth.users_db
        assert "bob" in auth.users_db
        assert "admin" in auth.users_db

    @pytest.mark.asyncio
    async def test_authenticate_success(self):
        """Test successful user authentication with password"""
        auth = AuthMiddleware()
        result = await auth.authenticate("alice", "alice123")

        assert result.authorized is True
        assert result.username == "alice"
        assert result.user_id == "user:alice"
        assert result.email == "alice@acme.com"
        assert "premium" in result.roles

    @pytest.mark.asyncio
    async def test_authenticate_missing_password(self):
        """Test authentication without password fails"""
        auth = AuthMiddleware()
        result = await auth.authenticate("alice")

        assert result.authorized is False
        assert result.reason == "password_required"

    @pytest.mark.asyncio
    async def test_authenticate_invalid_password(self):
        """Test authentication with wrong password fails"""
        auth = AuthMiddleware()
        result = await auth.authenticate("alice", "wrongpassword")

        assert result.authorized is False
        assert result.reason == "invalid_credentials"

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self):
        """Test authentication with non-existent user"""
        auth = AuthMiddleware()
        result = await auth.authenticate("nonexistent", "anypassword")

        assert result.authorized is False
        assert result.reason == "invalid_credentials"  # Same error as invalid password (security)

    @pytest.mark.asyncio
    async def test_authenticate_inactive_user(self):
        """Test authentication with inactive user"""
        auth = AuthMiddleware()
        auth.users_db["alice"]["active"] = False

        result = await auth.authenticate("alice", "alice123")

        assert result.authorized is False
        assert result.reason == "account_inactive"

    @pytest.mark.asyncio
    async def test_authorize_with_openfga_success(self):
        """Test authorization with OpenFGA returns True"""
        mock_openfga = AsyncMock()
        mock_openfga.check_permission.return_value = True

        auth = AuthMiddleware(openfga_client=mock_openfga)
        result = await auth.authorize(user_id="user:alice", relation="executor", resource="tool:chat")

        assert result is True
        mock_openfga.check_permission.assert_called_once_with(
            user="user:alice", relation="executor", object="tool:chat", context=None
        )

    @pytest.mark.asyncio
    async def test_authorize_with_openfga_denied(self):
        """Test authorization with OpenFGA returns False"""
        mock_openfga = AsyncMock()
        mock_openfga.check_permission.return_value = False

        auth = AuthMiddleware(openfga_client=mock_openfga)
        result = await auth.authorize(user_id="user:bob", relation="admin", resource="organization:acme")

        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_with_openfga_error(self):
        """Test authorization fails closed on OpenFGA error"""
        mock_openfga = AsyncMock()
        mock_openfga.check_permission.side_effect = Exception("OpenFGA connection error")

        auth = AuthMiddleware(openfga_client=mock_openfga)
        result = await auth.authorize(user_id="user:alice", relation="executor", resource="tool:chat")

        # Should fail closed (deny access)
        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_fallback_admin_access(self):
        """Test fallback authorization grants admin full access"""
        auth = AuthMiddleware()  # No OpenFGA client
        result = await auth.authorize(user_id="user:admin", relation="executor", resource="tool:chat")

        assert result is True

    @pytest.mark.asyncio
    async def test_authorize_fallback_premium_user(self):
        """Test fallback authorization for premium user"""
        auth = AuthMiddleware()
        result = await auth.authorize(user_id="user:alice", relation="executor", resource="tool:chat")

        assert result is True

    @pytest.mark.asyncio
    async def test_authorize_fallback_standard_user(self):
        """Test fallback authorization for standard user"""
        auth = AuthMiddleware()
        result = await auth.authorize(user_id="user:bob", relation="executor", resource="tool:chat")

        assert result is True

    @pytest.mark.asyncio
    async def test_authorize_fallback_viewer_access(self):
        """Test fallback authorization for viewer relation on default conversation"""
        auth = AuthMiddleware()
        # Users can view the default conversation
        result = await auth.authorize(user_id="user:alice", relation="viewer", resource="conversation:default")

        assert result is True

    @pytest.mark.asyncio
    async def test_authorize_fallback_editor_access_default(self):
        """Test fallback authorization for editor relation on default conversation"""
        auth = AuthMiddleware()
        # Users should be able to edit the default conversation
        result = await auth.authorize(user_id="user:alice", relation="editor", resource="conversation:default")

        assert result is True

    @pytest.mark.asyncio
    async def test_authorize_fallback_editor_access_owned(self):
        """Test fallback authorization allows access to user-owned conversations"""
        auth = AuthMiddleware()
        # Alice should be able to access conversation:alice_thread1
        result = await auth.authorize(user_id="user:alice", relation="editor", resource="conversation:alice_thread1")

        assert result is True

    @pytest.mark.asyncio
    async def test_authorize_fallback_editor_access_denied_other_user(self):
        """
        Test fallback authorization DENIES access to conversations owned by other users.

        SECURITY: This is a critical regression test. The old fallback logic granted
        access to ANY conversation:* resource. This test ensures users can only access
        their own conversations.
        """
        auth = AuthMiddleware()
        # Alice should NOT be able to access conversation:bob_thread1
        result = await auth.authorize(user_id="user:alice", relation="editor", resource="conversation:bob_thread1")

        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_fallback_viewer_access_denied_other_user(self):
        """Test fallback authorization DENIES viewer access to other users' conversations"""
        auth = AuthMiddleware()
        # Bob should NOT be able to view conversation:alice_private
        result = await auth.authorize(user_id="user:bob", relation="viewer", resource="conversation:alice_private")

        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_fallback_unknown_user(self):
        """Test fallback authorization denies unknown user"""
        auth = AuthMiddleware()
        result = await auth.authorize(user_id="user:unknown", relation="executor", resource="tool:chat")

        assert result is False

    @pytest.mark.asyncio
    async def test_list_accessible_resources_success(self):
        """Test listing accessible resources with OpenFGA"""
        mock_openfga = AsyncMock()
        mock_openfga.list_objects.return_value = ["tool:chat", "tool:search"]

        auth = AuthMiddleware(openfga_client=mock_openfga)
        resources = await auth.list_accessible_resources(user_id="user:alice", relation="executor", resource_type="tool")

        assert len(resources) == 2
        assert "tool:chat" in resources
        assert "tool:search" in resources
        mock_openfga.list_objects.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_accessible_resources_no_openfga(self):
        """Test listing resources without OpenFGA returns mock resources in development mode"""
        auth = AuthMiddleware()  # No OpenFGA
        resources = await auth.list_accessible_resources(user_id="user:alice", relation="executor", resource_type="tool")

        # In development mode (default in tests), returns mock resources for better developer experience
        # This allows the MCP server to function without requiring OpenFGA infrastructure
        assert isinstance(resources, list)
        assert len(resources) == 3
        assert "tool:agent_chat" in resources
        assert "tool:conversation_get" in resources
        assert "tool:conversation_search" in resources

    @pytest.mark.asyncio
    async def test_list_accessible_resources_error(self):
        """Test listing resources handles OpenFGA errors"""
        mock_openfga = AsyncMock()
        mock_openfga.list_objects.side_effect = Exception("OpenFGA error")

        auth = AuthMiddleware(openfga_client=mock_openfga)
        resources = await auth.list_accessible_resources(user_id="user:alice", relation="executor", resource_type="tool")

        assert resources == []

    def test_create_token_success(self):
        """Test JWT token creation"""
        auth = AuthMiddleware(secret_key="test-secret")
        token = auth.create_token("alice", expires_in=3600)

        assert token is not None
        assert isinstance(token, str)

        # Verify token contents
        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert payload["sub"] == "user:alice"
        assert payload["username"] == "alice"
        assert payload["email"] == "alice@acme.com"
        assert "premium" in payload["roles"]

    def test_create_token_expiration(self):
        """Test JWT token expiration is set correctly"""
        auth = AuthMiddleware(secret_key="test-secret")
        token = auth.create_token("alice", expires_in=7200)

        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], timezone.utc)

        time_diff = (exp - iat).total_seconds()
        assert 7190 <= time_diff <= 7210  # Allow small time drift

    def test_create_token_user_not_found(self):
        """Test token creation fails for non-existent user"""
        auth = AuthMiddleware()

        with pytest.raises(ValueError, match="User not found"):
            auth.create_token("nonexistent")

    @pytest.mark.asyncio
    async def test_verify_token_success(self):
        """Test successful token verification"""
        auth = AuthMiddleware(secret_key="test-secret")
        token = auth.create_token("alice", expires_in=3600)

        result = await auth.verify_token(token)

        assert result.valid is True
        assert result.payload is not None
        assert result.payload["username"] == "alice"

    @pytest.mark.asyncio
    async def test_verify_token_expired(self):
        """Test verification of expired token"""
        auth = AuthMiddleware(secret_key="test-secret")

        # Create token with past expiration
        payload = {
            "sub": "user:alice",
            "username": "alice",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        expired_token = jwt.encode(payload, "test-secret", algorithm="HS256")

        result = await auth.verify_token(expired_token)

        assert result.valid is False
        assert result.error == "Token expired"

    @pytest.mark.asyncio
    async def test_verify_token_invalid(self):
        """Test verification of invalid token"""
        auth = AuthMiddleware(secret_key="test-secret")

        result = await auth.verify_token("invalid.token.here")

        assert result.valid is False
        assert result.error == "Invalid token"

    @pytest.mark.asyncio
    async def test_verify_token_wrong_secret(self):
        """Test verification with wrong secret key"""
        auth1 = AuthMiddleware(secret_key="secret-1")
        token = auth1.create_token("alice")

        auth2 = AuthMiddleware(secret_key="secret-2")
        result = await auth2.verify_token(token)

        assert result.valid is False
        assert result.error == "Invalid token"


@pytest.mark.unit
@pytest.mark.auth
class TestRequireAuthDecorator:
    """Test require_auth decorator"""

    @pytest.mark.asyncio
    async def test_require_auth_success(self):
        """Test decorator allows authorized request"""

        @require_auth()
        async def protected_function(username: str = None, password: str = None, user_id: str = None):
            return f"Success for {user_id}"

        result = await protected_function(username="alice", password="alice123")
        assert "user:alice" in result

    @pytest.mark.asyncio
    async def test_require_auth_no_credentials(self):
        """Test decorator blocks request without credentials"""

        @require_auth()
        async def protected_function(username: str = None, user_id: str = None):
            return "Success"

        with pytest.raises(PermissionError, match="Authentication required"):
            await protected_function()

    @pytest.mark.asyncio
    async def test_require_auth_invalid_user(self):
        """Test decorator blocks invalid user"""

        @require_auth()
        async def protected_function(username: str = None, user_id: str = None):
            return "Success"

        with pytest.raises(PermissionError, match="Authentication failed"):
            await protected_function(username="nonexistent")

    @pytest.mark.asyncio
    async def test_require_auth_with_authorization(self):
        """Test decorator with authorization check"""
        mock_openfga = AsyncMock()
        mock_openfga.check_permission.return_value = True

        @require_auth(relation="executor", resource="tool:chat", openfga_client=mock_openfga)
        async def protected_function(username: str = None, password: str = None, user_id: str = None):
            return f"Success for {user_id}"

        result = await protected_function(username="alice", password="alice123")
        assert "user:alice" in result

    @pytest.mark.asyncio
    async def test_require_auth_authorization_denied(self):
        """Test decorator blocks unauthorized request"""
        mock_openfga = AsyncMock()
        mock_openfga.check_permission.return_value = False

        @require_auth(relation="admin", resource="organization:acme", openfga_client=mock_openfga)
        async def protected_function(username: str = None, password: str = None, user_id: str = None):
            return "Success"

        with pytest.raises(PermissionError, match="Not authorized"):
            await protected_function(username="bob", password="bob123")


@pytest.mark.unit
@pytest.mark.auth
class TestStandaloneVerifyToken:
    """Test standalone verify_token function"""

    @pytest.mark.asyncio
    async def test_standalone_verify_token_success(self):
        """Test standalone token verification succeeds"""
        auth = AuthMiddleware(secret_key="test-secret")
        token = auth.create_token("alice")

        result = await verify_token(token, secret_key="test-secret")

        assert result.valid is True
        assert result.payload["username"] == "alice"

    @pytest.mark.asyncio
    async def test_standalone_verify_token_default_secret(self):
        """Test standalone verification with default secret"""
        # Use explicit secret so both AuthMiddleware and verify_token use the same key
        secret = "your-secret-key-change-in-production"
        auth = AuthMiddleware(secret_key=secret)
        token = auth.create_token("alice")

        result = await verify_token(token)  # Uses same default secret

        assert result.valid is True

    @pytest.mark.asyncio
    async def test_standalone_verify_token_invalid(self):
        """Test standalone verification of invalid token"""
        result = await verify_token("invalid.token", secret_key="test-secret")

        assert result.valid is False


@pytest.mark.unit
@pytest.mark.auth
class TestGetCurrentUser:
    """Test get_current_user FastAPI dependency for bearer token authentication"""

    @pytest.mark.asyncio
    async def test_get_current_user_with_valid_bearer_token(self):
        """
        Test get_current_user authenticates with valid JWT bearer token.

        SECURITY: This is a critical test to ensure bearer token authentication works.
        Without proper dependency injection, bearer tokens are never validated.
        """
        # Setup: Create auth middleware and valid token
        auth = AuthMiddleware(secret_key="test-secret")
        set_global_auth_middleware(auth)
        token = auth.create_token("alice", expires_in=3600)

        # Create mock request and credentials
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.user = None  # No user in request state

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        # Act: Call get_current_user with bearer token
        user = await get_current_user(request, credentials)

        # Assert: User should be authenticated
        assert user is not None
        assert user["username"] == "alice"
        assert user["user_id"] == "user:alice"
        assert "premium" in user["roles"]
        assert user["email"] == "alice@acme.com"

    @pytest.mark.asyncio
    async def test_get_current_user_with_invalid_bearer_token(self):
        """Test get_current_user rejects invalid JWT bearer token"""
        from fastapi import HTTPException

        # Setup
        auth = AuthMiddleware(secret_key="test-secret")
        set_global_auth_middleware(auth)

        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.user = None

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.jwt.token")

        # Act & Assert: Should raise 401 Unauthorized
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request, credentials)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_with_expired_bearer_token(self):
        """Test get_current_user rejects expired JWT bearer token"""
        from fastapi import HTTPException

        # Setup: Create expired token
        auth = AuthMiddleware(secret_key="test-secret")
        set_global_auth_middleware(auth)

        payload = {
            "sub": "user:alice",
            "username": "alice",
            "email": "alice@acme.com",
            "roles": ["premium"],
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        expired_token = jwt.encode(payload, "test-secret", algorithm="HS256")

        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.user = None

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=expired_token)

        # Act & Assert: Should raise 401 Unauthorized
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request, credentials)

        assert exc_info.value.status_code == 401
        assert "Token expired" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_without_credentials_raises_401(self):
        """Test get_current_user requires authentication when no credentials provided"""
        from fastapi import HTTPException

        # Setup
        auth = AuthMiddleware(secret_key="test-secret")
        set_global_auth_middleware(auth)

        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.user = None

        # Act & Assert: Should raise 401 when no credentials
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request, credentials=None)

        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_uses_request_state_if_set(self):
        """Test get_current_user returns user from request.state if already authenticated"""
        # Setup
        auth = AuthMiddleware(secret_key="test-secret")
        set_global_auth_middleware(auth)

        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.user = {"user_id": "user:bob", "username": "bob", "roles": ["standard"], "email": "bob@acme.com"}

        # Act: Call without credentials (should use request.state.user)
        user = await get_current_user(request, credentials=None)

        # Assert: Should return cached user from request state
        assert user["username"] == "bob"
        assert user["user_id"] == "user:bob"

    @pytest.mark.asyncio
    async def test_get_current_user_prefers_preferred_username_over_sub(self):
        """
        Test get_current_user uses preferred_username instead of sub for Keycloak compatibility.

        SECURITY: Keycloak JWTs use UUID in 'sub' field, but OpenFGA tuples use 'user:username'.
        We must extract 'preferred_username' to ensure authorization works correctly.
        """
        # Setup: Create Keycloak-style JWT with UUID in sub and username in preferred_username
        auth = AuthMiddleware(secret_key="test-secret")
        set_global_auth_middleware(auth)

        keycloak_payload = {
            "sub": "f47ac10b-58cc-4372-a567-0e02b2c3d479",  # Keycloak UUID
            "preferred_username": "alice",  # Actual username
            "email": "alice@acme.com",
            "roles": ["premium"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }
        keycloak_token = jwt.encode(keycloak_payload, "test-secret", algorithm="HS256")

        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.user = None

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=keycloak_token)

        # Act: Call get_current_user with Keycloak JWT
        user = await get_current_user(request, credentials)

        # Assert: Should use preferred_username, NOT sub UUID
        assert user["username"] == "alice"  # From preferred_username
        assert user["user_id"] == "user:alice"  # Format for OpenFGA
        assert "uuid" not in user["user_id"].lower()  # Should NOT contain UUID
        assert "f47ac10b" not in user["user_id"]  # Should NOT contain UUID

    @pytest.mark.asyncio
    async def test_get_current_user_falls_back_to_sub_if_no_preferred_username(self):
        """
        Test get_current_user falls back to sub if preferred_username is missing.

        This handles legacy JWTs or non-Keycloak identity providers.
        """
        # Setup: Create JWT without preferred_username
        auth = AuthMiddleware(secret_key="test-secret")
        set_global_auth_middleware(auth)

        legacy_payload = {
            "sub": "user:charlie",  # Already in user:username format
            "email": "charlie@acme.com",
            "roles": ["standard"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }
        legacy_token = jwt.encode(legacy_payload, "test-secret", algorithm="HS256")

        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.user = None

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=legacy_token)

        # Act: Call get_current_user with legacy JWT
        user = await get_current_user(request, credentials)

        # Assert: Should fall back to sub
        assert user["username"] == "charlie"
        assert user["user_id"] == "user:charlie"

    @pytest.mark.asyncio
    async def test_get_current_user_normalizes_username_format(self):
        """
        Test get_current_user normalizes user_id to 'user:username' format for OpenFGA.

        This ensures consistent format regardless of JWT structure.
        """
        # Setup: Create JWT with plain username in preferred_username
        auth = AuthMiddleware(secret_key="test-secret")
        set_global_auth_middleware(auth)

        payload = {
            "sub": "12345",  # Some numeric ID
            "preferred_username": "dave",  # Plain username (no prefix)
            "email": "dave@acme.com",
            "roles": ["admin"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }
        token = jwt.encode(payload, "test-secret", algorithm="HS256")

        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.user = None

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        # Act: Call get_current_user
        user = await get_current_user(request, credentials)

        # Assert: user_id should be normalized to user:username format
        assert user["username"] == "dave"
        assert user["user_id"] == "user:dave"  # Normalized format
        assert user["user_id"].startswith("user:")  # Always has prefix
