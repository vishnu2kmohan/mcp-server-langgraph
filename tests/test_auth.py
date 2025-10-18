"""Unit tests for auth.py - Authentication and Authorization"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest

from mcp_server_langgraph.auth.middleware import AuthMiddleware, require_auth, verify_token


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
