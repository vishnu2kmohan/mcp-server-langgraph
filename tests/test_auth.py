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
from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider, KeycloakUserProvider, UserData


@pytest.fixture
def auth_middleware_with_users():
    """Create AuthMiddleware with test users and fallback enabled for testing"""
    from mcp_server_langgraph.core.config import Settings

    # Create settings with fallback enabled for testing (Finding #1 security fix compatibility)
    settings = Settings(
        allow_auth_fallback=True,  # Enable fallback for tests
        environment="development",  # Development environment (not production)
    )

    # Pass secret_key to user provider to match middleware secret (for token creation/verification)
    user_provider = InMemoryUserProvider(
        secret_key="test-key", use_password_hashing=False  # Must match AuthMiddleware secret for token tests
    )

    # Add test users explicitly (no more hard-coded defaults as of Finding #2 fix)
    user_provider.add_user(username="alice", password="alice123", email="alice@acme.com", roles=["user", "premium"])
    user_provider.add_user(username="bob", password="bob123", email="bob@acme.com", roles=["user"])
    user_provider.add_user(username="admin", password="admin123", email="admin@acme.com", roles=["admin"])

    return AuthMiddleware(
        secret_key="test-key",
        user_provider=user_provider,
        settings=settings,  # Pass settings for fallback control (Finding #1)
    )


@pytest.mark.auth
@pytest.mark.unit
class TestAuthMiddleware:
    """Test AuthMiddleware class"""

    def test_init(self, auth_middleware_with_users):
        """Test AuthMiddleware initialization"""
        auth = auth_middleware_with_users
        assert auth.secret_key == "test-key"
        assert auth.openfga is None
        assert len(auth.users_db) == 3
        assert "alice" in auth.users_db
        assert "bob" in auth.users_db
        assert "admin" in auth.users_db

    @pytest.mark.asyncio
    async def test_authenticate_success(self, auth_middleware_with_users):
        """Test successful user authentication with password"""
        auth = auth_middleware_with_users
        result = await auth.authenticate("alice", "alice123")

        assert result.authorized is True
        assert result.username == "alice"
        assert result.user_id == "user:alice"
        assert result.email == "alice@acme.com"
        assert "premium" in result.roles

    @pytest.mark.asyncio
    async def test_authenticate_missing_password(self, auth_middleware_with_users):
        """Test authentication without password fails"""
        auth = auth_middleware_with_users
        result = await auth.authenticate("alice")

        assert result.authorized is False
        assert result.reason == "password_required"

    @pytest.mark.asyncio
    async def test_authenticate_invalid_password(self, auth_middleware_with_users):
        """Test authentication with wrong password fails"""
        auth = auth_middleware_with_users
        result = await auth.authenticate("alice", "wrongpassword")

        assert result.authorized is False
        assert result.reason == "invalid_credentials"

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, auth_middleware_with_users):
        """Test authentication with non-existent user"""
        auth = auth_middleware_with_users
        result = await auth.authenticate("nonexistent", "anypassword")

        assert result.authorized is False
        assert result.reason == "invalid_credentials"  # Same error as invalid password (security)

    @pytest.mark.asyncio
    async def test_authenticate_inactive_user(self, auth_middleware_with_users):
        """Test authentication with inactive user"""
        auth = auth_middleware_with_users
        auth.users_db["alice"]["active"] = False

        result = await auth.authenticate("alice", "alice123")

        assert result.authorized is False
        assert result.reason == "account_inactive"

    @pytest.mark.asyncio
    async def test_authorize_with_openfga_success(self, auth_middleware_with_users):
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
    async def test_authorize_fallback_admin_access(self, auth_middleware_with_users):
        """Test fallback authorization grants admin full access"""
        auth = auth_middleware_with_users  # No OpenFGA client
        result = await auth.authorize(user_id="user:admin", relation="executor", resource="tool:chat")

        assert result is True

    @pytest.mark.asyncio
    async def test_authorize_fallback_premium_user(self, auth_middleware_with_users):
        """Test fallback authorization for premium user"""
        auth = auth_middleware_with_users
        result = await auth.authorize(user_id="user:alice", relation="executor", resource="tool:chat")

        assert result is True

    @pytest.mark.asyncio
    async def test_authorize_fallback_standard_user(self, auth_middleware_with_users):
        """Test fallback authorization for standard user"""
        auth = auth_middleware_with_users
        result = await auth.authorize(user_id="user:bob", relation="executor", resource="tool:chat")

        assert result is True

    @pytest.mark.asyncio
    async def test_authorize_fallback_viewer_access(self, auth_middleware_with_users):
        """Test fallback authorization for viewer relation on default conversation"""
        auth = auth_middleware_with_users
        # Users can view the default conversation
        result = await auth.authorize(user_id="user:alice", relation="viewer", resource="conversation:default")

        assert result is True

    @pytest.mark.asyncio
    async def test_authorize_fallback_editor_access_default(self, auth_middleware_with_users):
        """Test fallback authorization for editor relation on default conversation"""
        auth = auth_middleware_with_users
        # Users should be able to edit the default conversation
        result = await auth.authorize(user_id="user:alice", relation="editor", resource="conversation:default")

        assert result is True

    @pytest.mark.asyncio
    async def test_authorize_fallback_editor_access_owned(self, auth_middleware_with_users):
        """Test fallback authorization allows access to user-owned conversations"""
        auth = auth_middleware_with_users
        # Alice should be able to access conversation:alice_thread1
        result = await auth.authorize(user_id="user:alice", relation="editor", resource="conversation:alice_thread1")

        assert result is True

    @pytest.mark.asyncio
    async def test_authorize_fallback_editor_access_denied_other_user(self, auth_middleware_with_users):
        """
        Test fallback authorization DENIES access to conversations owned by other users.

        SECURITY: This is a critical regression test. The old fallback logic granted
        access to ANY conversation:* resource. This test ensures users can only access
        their own conversations.
        """
        auth = auth_middleware_with_users
        # Alice should NOT be able to access conversation:bob_thread1
        result = await auth.authorize(user_id="user:alice", relation="editor", resource="conversation:bob_thread1")

        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_fallback_viewer_access_denied_other_user(self, auth_middleware_with_users):
        """Test fallback authorization DENIES viewer access to other users' conversations"""
        auth = auth_middleware_with_users
        # Bob should NOT be able to view conversation:alice_private
        result = await auth.authorize(user_id="user:bob", relation="viewer", resource="conversation:alice_private")

        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_fallback_unknown_user(self, auth_middleware_with_users):
        """Test fallback authorization denies unknown user"""
        auth = auth_middleware_with_users
        result = await auth.authorize(user_id="user:unknown", relation="executor", resource="tool:chat")

        assert result is False

    @pytest.mark.asyncio
    async def test_list_accessible_resources_success(self, auth_middleware_with_users):
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
    async def test_list_accessible_resources_no_openfga(self, auth_middleware_with_users):
        """Test listing resources without OpenFGA returns empty list (post Finding #1 fix)"""
        auth = auth_middleware_with_users  # No OpenFGA

        resources = await auth.list_accessible_resources(user_id="user:alice", relation="executor", resource_type="tool")

        # After Finding #1 fix: Without OpenFGA, resource listing returns empty list
        # This is secure fail-closed behavior when authorization infrastructure is unavailable
        assert isinstance(resources, list)
        assert len(resources) == 0  # Empty without OpenFGA (secure behavior)

    @pytest.mark.asyncio
    async def test_list_accessible_resources_error(self, auth_middleware_with_users):
        """Test listing resources handles OpenFGA errors"""
        mock_openfga = AsyncMock()
        mock_openfga.list_objects.side_effect = Exception("OpenFGA error")

        auth = AuthMiddleware(openfga_client=mock_openfga)
        resources = await auth.list_accessible_resources(user_id="user:alice", relation="executor", resource_type="tool")

        assert resources == []

    def test_create_token_success(self, auth_middleware_with_users):
        """Test JWT token creation"""
        auth = auth_middleware_with_users
        token = auth.create_token("alice", expires_in=3600)

        assert token is not None
        assert isinstance(token, str)

        # Verify token contents
        payload = jwt.decode(token, "test-key", algorithms=["HS256"])
        assert payload["sub"] == "user:alice"
        assert payload["username"] == "alice"
        assert payload["email"] == "alice@acme.com"
        assert "premium" in payload["roles"]

    def test_create_token_expiration(self, auth_middleware_with_users):
        """Test JWT token expiration is set correctly"""
        auth = auth_middleware_with_users
        token = auth.create_token("alice", expires_in=7200)

        payload = jwt.decode(token, "test-key", algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], timezone.utc)

        time_diff = (exp - iat).total_seconds()
        assert 7190 <= time_diff <= 7210  # Allow small time drift

    def test_create_token_user_not_found(self, auth_middleware_with_users):
        """Test token creation fails for non-existent user"""
        auth = auth_middleware_with_users

        with pytest.raises(ValueError, match="User not found"):
            auth.create_token("nonexistent")

    @pytest.mark.asyncio
    async def test_verify_token_success(self, auth_middleware_with_users):
        """Test successful token verification"""
        auth = auth_middleware_with_users
        token = auth.create_token("alice", expires_in=3600)

        result = await auth.verify_token(token)

        assert result.valid is True
        assert result.payload is not None
        assert result.payload["username"] == "alice"

    @pytest.mark.asyncio
    async def test_verify_token_expired(self, auth_middleware_with_users):
        """Test verification of expired token"""
        auth = auth_middleware_with_users

        # Create token with past expiration
        payload = {
            "sub": "user:alice",
            "username": "alice",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        expired_token = jwt.encode(payload, "test-key", algorithm="HS256")  # Use same secret as fixture

        result = await auth.verify_token(expired_token)

        assert result.valid is False
        assert result.error == "Token expired"

    @pytest.mark.asyncio
    async def test_verify_token_invalid(self, auth_middleware_with_users):
        """Test verification of invalid token"""
        auth = auth_middleware_with_users

        result = await auth.verify_token("invalid.token.here")

        assert result.valid is False
        assert result.error == "Invalid token"

    @pytest.mark.asyncio
    async def test_verify_token_wrong_secret(self, auth_middleware_with_users):
        """Test verification with wrong secret key"""
        # Use fixture to create token
        auth1 = auth_middleware_with_users
        token = auth1.create_token("alice")

        # Create different middleware with different secret
        user_provider2 = InMemoryUserProvider(use_password_hashing=False)
        user_provider2.add_user("alice", "password", "alice@test.com", ["user"])
        auth2 = AuthMiddleware(secret_key="different-secret", user_provider=user_provider2)
        result = await auth2.verify_token(token)

        assert result.valid is False
        assert result.error == "Invalid token"


@pytest.mark.unit
@pytest.mark.auth
class TestRequireAuthDecorator:
    """Test require_auth decorator"""

    @pytest.mark.asyncio
    async def test_require_auth_success(self, auth_middleware_with_users):
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
        expired_token = jwt.encode(payload, "test-key", algorithm="HS256")

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
        token = jwt.encode(payload, "test-key", algorithm="HS256")

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


@pytest.mark.unit
@pytest.mark.auth
class TestAuthFallbackWithExternalProviders:
    """
    Test authorization fallback logic with external providers (Keycloak, etc.)

    SECURITY: This addresses the critical bug where Keycloak users were denied
    all access when OpenFGA was down, because the fallback logic only checked
    InMemoryUserProvider's users_db (which is empty for Keycloak).

    The fix ensures fallback authorization queries the user provider for roles
    instead of relying on in-memory user database.
    """

    @pytest.mark.asyncio
    async def test_authorize_fallback_keycloak_admin_user(self, auth_middleware_with_users):
        """
        Test fallback authorization grants admin access for Keycloak users.

        REGRESSION TEST: Previously failed because users_db was empty for Keycloak.
        """
        # Mock Keycloak provider
        mock_keycloak = AsyncMock(spec=KeycloakUserProvider)

        # Mock get_user_by_username to return admin user
        admin_user = UserData(
            user_id="user:keycloak_admin",
            username="keycloak_admin",
            email="admin@keycloak.com",
            roles=["admin", "user"],
            active=True,
        )
        mock_keycloak.get_user_by_username.return_value = admin_user

        # Create AuthMiddleware with Keycloak provider (no OpenFGA)
        auth = AuthMiddleware(user_provider=mock_keycloak)

        # Test: Admin should have access to everything
        result = await auth.authorize(user_id="user:keycloak_admin", relation="executor", resource="tool:chat")

        assert result is True
        mock_keycloak.get_user_by_username.assert_called_once_with("keycloak_admin")

    @pytest.mark.asyncio
    async def test_authorize_fallback_keycloak_premium_user(self, auth_middleware_with_users):
        """
        Test fallback authorization for Keycloak premium user.

        REGRESSION TEST: Previously denied access because users_db was empty.
        """
        # Mock Keycloak provider
        mock_keycloak = AsyncMock(spec=KeycloakUserProvider)

        # Mock get_user_by_username to return premium user
        premium_user = UserData(
            user_id="user:keycloak_alice",
            username="keycloak_alice",
            email="alice@keycloak.com",
            roles=["user", "premium"],
            active=True,
        )
        mock_keycloak.get_user_by_username.return_value = premium_user

        # Create AuthMiddleware with Keycloak provider (no OpenFGA)
        auth = AuthMiddleware(user_provider=mock_keycloak)

        # Test: Premium user should have executor access to tools
        result = await auth.authorize(user_id="user:keycloak_alice", relation="executor", resource="tool:chat")

        assert result is True
        mock_keycloak.get_user_by_username.assert_called_once_with("keycloak_alice")

    @pytest.mark.asyncio
    async def test_authorize_fallback_keycloak_standard_user(self, auth_middleware_with_users):
        """Test fallback authorization for Keycloak standard user."""
        # Mock Keycloak provider
        mock_keycloak = AsyncMock(spec=KeycloakUserProvider)

        # Mock get_user_by_username to return standard user
        standard_user = UserData(
            user_id="user:keycloak_bob",
            username="keycloak_bob",
            email="bob@keycloak.com",
            roles=["user"],  # Standard user role
            active=True,
        )
        mock_keycloak.get_user_by_username.return_value = standard_user

        # Create AuthMiddleware with Keycloak provider (no OpenFGA)
        auth = AuthMiddleware(user_provider=mock_keycloak)

        # Test: Standard user should have executor access to tools
        result = await auth.authorize(user_id="user:keycloak_bob", relation="executor", resource="tool:chat")

        assert result is True

    @pytest.mark.asyncio
    async def test_authorize_fallback_keycloak_user_not_found(self, auth_middleware_with_users):
        """
        Test fallback authorization denies access for non-existent Keycloak user.

        REGRESSION TEST: Previously failed with same denial, but now logs correctly.
        """
        # Mock Keycloak provider
        mock_keycloak = AsyncMock(spec=KeycloakUserProvider)

        # Mock get_user_by_username to return None (user not found)
        mock_keycloak.get_user_by_username.return_value = None

        # Create AuthMiddleware with Keycloak provider (no OpenFGA)
        auth = AuthMiddleware(user_provider=mock_keycloak)

        # Test: Non-existent user should be denied
        result = await auth.authorize(user_id="user:nonexistent", relation="executor", resource="tool:chat")

        assert result is False
        mock_keycloak.get_user_by_username.assert_called_once_with("nonexistent")

    @pytest.mark.asyncio
    async def test_authorize_fallback_keycloak_provider_error(self, auth_middleware_with_users):
        """
        Test fallback authorization fails closed when provider lookup fails.

        SECURITY: When we can't verify user roles, deny access (fail closed).
        """
        # Mock Keycloak provider
        mock_keycloak = AsyncMock(spec=KeycloakUserProvider)

        # Mock get_user_by_username to raise exception (provider error)
        mock_keycloak.get_user_by_username.side_effect = Exception("Keycloak connection error")

        # Create AuthMiddleware with Keycloak provider (no OpenFGA)
        auth = AuthMiddleware(user_provider=mock_keycloak)

        # Test: Provider error should deny access (fail closed)
        result = await auth.authorize(user_id="user:alice", relation="executor", resource="tool:chat")

        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_fallback_keycloak_conversation_ownership(self, auth_middleware_with_users):
        """
        Test fallback authorization respects conversation ownership for Keycloak users.

        SECURITY: Users should only access their own conversations in fallback mode.
        """
        # Mock Keycloak provider
        mock_keycloak = AsyncMock(spec=KeycloakUserProvider)

        # Mock get_user_by_username to return user
        user = UserData(
            user_id="user:keycloak_alice", username="keycloak_alice", email="alice@keycloak.com", roles=["user"], active=True
        )
        mock_keycloak.get_user_by_username.return_value = user

        # Create AuthMiddleware with Keycloak provider (no OpenFGA)
        auth = AuthMiddleware(user_provider=mock_keycloak)

        # Test 1: User can access their own conversation
        result = await auth.authorize(
            user_id="user:keycloak_alice", relation="viewer", resource="conversation:keycloak_alice_thread1"
        )
        assert result is True

        # Test 2: User can access default conversation
        result = await auth.authorize(user_id="user:keycloak_alice", relation="viewer", resource="conversation:default")
        assert result is True

        # Test 3: User CANNOT access another user's conversation
        result = await auth.authorize(
            user_id="user:keycloak_alice", relation="viewer", resource="conversation:keycloak_bob_private"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_fallback_keycloak_user_without_required_role(self, auth_middleware_with_users):
        """Test fallback authorization denies access when user lacks required role."""
        # Mock Keycloak provider
        mock_keycloak = AsyncMock(spec=KeycloakUserProvider)

        # Mock get_user_by_username to return user WITHOUT user/premium roles
        limited_user = UserData(
            user_id="user:keycloak_limited",
            username="keycloak_limited",
            email="limited@keycloak.com",
            roles=["viewer"],  # Only viewer role, no user/premium
            active=True,
        )
        mock_keycloak.get_user_by_username.return_value = limited_user

        # Create AuthMiddleware with Keycloak provider (no OpenFGA)
        auth = AuthMiddleware(user_provider=mock_keycloak)

        # Test: User without user/premium role should be denied executor access
        result = await auth.authorize(user_id="user:keycloak_limited", relation="executor", resource="tool:chat")

        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_inmemory_provider_still_works(self):
        """
        Test that InMemoryUserProvider fallback still works (fast path).

        REGRESSION TEST: Ensure the fix didn't break existing InMemory behavior.
        """
        # Create AuthMiddleware with InMemoryUserProvider (default, no OpenFGA)
        auth = AuthMiddleware(secret_key="test-secret")

        # Test: InMemory admin user should have access
        result = await auth.authorize(user_id="user:admin", relation="executor", resource="tool:chat")
        assert result is True

        # Test: InMemory premium user should have access
        result = await auth.authorize(user_id="user:alice", relation="executor", resource="tool:chat")
        assert result is True

        # Test: InMemory unknown user should be denied
        result = await auth.authorize(user_id="user:unknown", relation="executor", resource="tool:chat")
        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_openfga_takes_precedence_over_fallback(self):
        """
        Test that OpenFGA is used when available (fallback only when OpenFGA down).

        SECURITY: Fallback should ONLY be used when OpenFGA is unavailable.
        """
        # Mock Keycloak provider
        mock_keycloak = AsyncMock(spec=KeycloakUserProvider)
        mock_keycloak.get_user_by_username.return_value = UserData(
            user_id="user:alice", username="alice", email="alice@keycloak.com", roles=["user"], active=True
        )

        # Mock OpenFGA client
        mock_openfga = AsyncMock()
        mock_openfga.check_permission.return_value = True

        # Create AuthMiddleware with BOTH Keycloak AND OpenFGA
        auth = AuthMiddleware(user_provider=mock_keycloak, openfga_client=mock_openfga)

        # Test: Should use OpenFGA, NOT fallback
        result = await auth.authorize(user_id="user:alice", relation="executor", resource="tool:chat")

        # Assert: OpenFGA was called
        assert result is True
        mock_openfga.check_permission.assert_called_once()

        # Assert: Keycloak provider was NOT called (because OpenFGA worked)
        mock_keycloak.get_user_by_username.assert_not_called()
