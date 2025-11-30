"""Unit tests for auth.py - Authentication and Authorization"""

import gc
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import jwt
import pytest
from fastapi import Request

from mcp_server_langgraph.auth.middleware import (
    AuthMiddleware,
    get_current_user,
    require_auth,
    set_global_auth_middleware,
    verify_token,
)
from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider, KeycloakUserProvider, UserData
from tests.conftest import get_user_id
from tests.helpers.async_mock_helpers import configured_async_mock

pytestmark = pytest.mark.unit


@pytest.fixture
def auth_middleware_with_users():
    """Create AuthMiddleware with test users and fallback enabled for testing"""
    from mcp_server_langgraph.core.config import Settings

    settings = Settings(allow_auth_fallback=True, environment="development")
    user_provider = InMemoryUserProvider(secret_key="test-key", use_password_hashing=False)
    user_provider.add_user(
        username="alice",
        password="alice123",
        email="alice@acme.com",
        roles=["user", "premium"],
        user_id=get_user_id("alice"),
    )
    user_provider.add_user(username="bob", password="bob123", email="bob@acme.com", roles=["user"], user_id=get_user_id("bob"))
    user_provider.add_user(
        username="admin", password="admin123", email="admin@acme.com", roles=["admin"], user_id=get_user_id("admin")
    )
    return AuthMiddleware(secret_key="test-key", user_provider=user_provider, settings=settings)


@pytest.mark.auth
@pytest.mark.unit
@pytest.mark.xdist_group(name="auth_middleware_tests")
class TestAuthMiddleware:
    """Test AuthMiddleware class"""

    def setup_method(self):
        """
        Setup clean state BEFORE each test.

        CRITICAL: Reset global state BEFORE test starts to prevent pollution from previous tests.
        This is essential because tests/api/conftest.py sets MCP_SKIP_AUTH=true globally,
        which causes get_current_user() to return hardcoded username="test" instead of validating tokens.
        """
        import os

        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None
        os.environ["MCP_SKIP_AUTH"] = "false"

    def teardown_method(self):
        """
        Force GC to prevent mock accumulation in xdist workers.

        CRITICAL: Reset global state to prevent test pollution.
        Without this, tests running in parallel (-n auto) will interfere with each other
        because they share global variables and environment variables across the worker process.
        """
        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None
        import os

        if "MCP_SKIP_AUTH" in os.environ:
            del os.environ["MCP_SKIP_AUTH"]
        gc.collect()

    def test_auth_middleware_initialization_with_users_creates_expected_config(self, auth_middleware_with_users):
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
        assert result.user_id == get_user_id("alice")
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
        assert result.reason == "invalid_credentials"

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
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.check_permission.return_value = True
        auth = AuthMiddleware(openfga_client=mock_openfga)
        result = await auth.authorize(user_id=get_user_id("alice"), relation="executor", resource="tool:chat")
        assert result is True
        mock_openfga.check_permission.assert_called_once_with(
            user=get_user_id("alice"), relation="executor", object="tool:chat", context=None
        )

    @pytest.mark.asyncio
    async def test_authorize_with_openfga_denied(self):
        """Test authorization with OpenFGA returns False"""
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.check_permission.return_value = False
        auth = AuthMiddleware(openfga_client=mock_openfga)
        result = await auth.authorize(user_id=get_user_id("bob"), relation="admin", resource="organization:acme")
        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_with_openfga_error(self):
        """Test authorization fails closed on OpenFGA error"""
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.check_permission.side_effect = Exception("OpenFGA connection error")
        auth = AuthMiddleware(openfga_client=mock_openfga)
        result = await auth.authorize(user_id=get_user_id("alice"), relation="executor", resource="tool:chat")
        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_fallback_admin_access(self, auth_middleware_with_users):
        """Test fallback authorization grants admin full access"""
        auth = auth_middleware_with_users
        result = await auth.authorize(user_id=get_user_id("admin"), relation="executor", resource="tool:chat")
        assert result is True

    @pytest.mark.asyncio
    async def test_authorize_fallback_premium_user(self, auth_middleware_with_users):
        """Test fallback authorization for premium user"""
        auth = auth_middleware_with_users
        result = await auth.authorize(user_id=get_user_id("alice"), relation="executor", resource="tool:chat")
        assert result is True

    @pytest.mark.asyncio
    async def test_authorize_fallback_standard_user(self, auth_middleware_with_users):
        """Test fallback authorization for standard user"""
        auth = auth_middleware_with_users
        result = await auth.authorize(user_id=get_user_id("bob"), relation="executor", resource="tool:chat")
        assert result is True

    @pytest.mark.asyncio
    async def test_authorize_fallback_viewer_access(self, auth_middleware_with_users):
        """Test fallback authorization for viewer relation on default conversation"""
        auth = auth_middleware_with_users
        result = await auth.authorize(user_id=get_user_id("alice"), relation="viewer", resource="conversation:default")
        assert result is True

    @pytest.mark.asyncio
    async def test_authorize_fallback_editor_access_default(self, auth_middleware_with_users):
        """Test fallback authorization for editor relation on default conversation"""
        auth = auth_middleware_with_users
        result = await auth.authorize(user_id=get_user_id("alice"), relation="editor", resource="conversation:default")
        assert result is True

    @pytest.mark.asyncio
    async def test_authorize_fallback_editor_access_owned(self, auth_middleware_with_users):
        """Test fallback authorization allows access to user-owned conversations"""
        auth = auth_middleware_with_users
        result = await auth.authorize(user_id=get_user_id("alice"), relation="editor", resource="conversation:alice_thread1")
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
        result = await auth.authorize(user_id=get_user_id("alice"), relation="editor", resource="conversation:bob_thread1")
        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_fallback_viewer_access_denied_other_user(self, auth_middleware_with_users):
        """Test fallback authorization DENIES viewer access to other users' conversations"""
        auth = auth_middleware_with_users
        result = await auth.authorize(user_id=get_user_id("bob"), relation="viewer", resource="conversation:alice_private")
        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_fallback_unknown_user(self, auth_middleware_with_users):
        """Test fallback authorization denies unknown user"""
        auth = auth_middleware_with_users
        result = await auth.authorize(user_id=get_user_id("unknown"), relation="executor", resource="tool:chat")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_accessible_resources_success(self, auth_middleware_with_users):
        """Test listing accessible resources with OpenFGA"""
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.list_objects.return_value = ["tool:chat", "tool:search"]
        auth = AuthMiddleware(openfga_client=mock_openfga)
        resources = await auth.list_accessible_resources(
            user_id=get_user_id("alice"), relation="executor", resource_type="tool"
        )
        assert len(resources) == 2
        assert "tool:chat" in resources
        assert "tool:search" in resources
        mock_openfga.list_objects.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_accessible_resources_no_openfga(self, auth_middleware_with_users):
        """Test listing resources without OpenFGA returns empty list (post Finding #1 fix)"""
        auth = auth_middleware_with_users
        resources = await auth.list_accessible_resources(
            user_id=get_user_id("alice"), relation="executor", resource_type="tool"
        )
        assert isinstance(resources, list)
        assert len(resources) == 0

    @pytest.mark.asyncio
    async def test_list_accessible_resources_error(self, auth_middleware_with_users):
        """Test listing resources handles OpenFGA errors"""
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.list_objects.side_effect = Exception("OpenFGA error")
        auth = AuthMiddleware(openfga_client=mock_openfga)
        resources = await auth.list_accessible_resources(
            user_id=get_user_id("alice"), relation="executor", resource_type="tool"
        )
        assert resources == []

    def test_create_token_success(self, auth_middleware_with_users):
        """Test JWT token creation"""
        auth = auth_middleware_with_users
        token = auth.create_token("alice", expires_in=3600)
        assert token is not None
        assert isinstance(token, str)
        payload = jwt.decode(token, "test-key", algorithms=["HS256"])
        assert payload["sub"] == get_user_id("alice")
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
        assert 7190 <= time_diff <= 7210

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
        payload = {
            "sub": get_user_id("alice"),
            "username": "alice",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        expired_token = jwt.encode(payload, "test-key", algorithm="HS256")
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
        auth1 = auth_middleware_with_users
        token = auth1.create_token("alice")
        user_provider2 = InMemoryUserProvider(use_password_hashing=False)
        user_provider2.add_user("alice", "password", "alice@test.com", ["user"], user_id=get_user_id("alice"))
        auth2 = AuthMiddleware(secret_key="different-secret", user_provider=user_provider2)
        result = await auth2.verify_token(token)
        assert result.valid is False
        assert result.error == "Invalid token"


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.xdist_group(name="auth_middleware_tests")
class TestRequireAuthDecorator:
    """Test require_auth decorator"""

    def setup_method(self):
        """
        Setup clean state BEFORE each test.

        CRITICAL: Reset global state BEFORE test starts to prevent pollution from previous tests.
        This is essential because tests/api/conftest.py sets MCP_SKIP_AUTH=true globally,
        which causes get_current_user() to return hardcoded username="test" instead of validating tokens.
        """
        import os

        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None
        os.environ["MCP_SKIP_AUTH"] = "false"

    def teardown_method(self):
        """
        Force GC to prevent mock accumulation in xdist workers.

        CRITICAL: Reset global state to prevent test pollution.
        Without this, tests running in parallel (-n auto) will interfere with each other
        because they share global variables and environment variables across the worker process.
        """
        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None
        import os

        if "MCP_SKIP_AUTH" in os.environ:
            del os.environ["MCP_SKIP_AUTH"]
        gc.collect()

    @pytest.mark.asyncio
    async def test_require_auth_success(self, auth_middleware_with_users):
        """Test decorator allows authorized request"""

        @require_auth(auth_middleware=auth_middleware_with_users)
        async def protected_function(username: str = None, password: str = None, user_id: str = None):
            return f"Success for {user_id}"

        result = await protected_function(username="alice", password="alice123")
        assert get_user_id("alice") in result

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
    async def test_require_auth_with_authorization(self, auth_middleware_with_users):
        """Test decorator with authorization check"""
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.check_permission.return_value = True

        @require_auth(
            relation="executor", resource="tool:chat", openfga_client=mock_openfga, auth_middleware=auth_middleware_with_users
        )
        async def protected_function(username: str = None, password: str = None, user_id: str = None):
            return f"Success for {user_id}"

        result = await protected_function(username="alice", password="alice123")
        assert get_user_id("alice") in result

    @pytest.mark.asyncio
    async def test_require_auth_authorization_denied(self, auth_middleware_with_users):
        """Test decorator blocks unauthorized request"""
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.check_permission.return_value = False

        @require_auth(
            relation="admin",
            resource="organization:acme",
            openfga_client=mock_openfga,
            auth_middleware=auth_middleware_with_users,
        )
        async def protected_function(username: str = None, password: str = None, user_id: str = None):
            return "Success"

        with pytest.raises(PermissionError, match="Not authorized"):
            await protected_function(username="bob", password="bob123")


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.xdist_group(name="auth_middleware_tests")
class TestStandaloneVerifyToken:
    """Test standalone verify_token function"""

    def setup_method(self):
        """
        Setup clean state BEFORE each test.

        CRITICAL: Reset global state BEFORE test starts to prevent pollution from previous tests.
        This is essential because tests/api/conftest.py sets MCP_SKIP_AUTH=true globally,
        which causes get_current_user() to return hardcoded username="test" instead of validating tokens.
        """
        import os

        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None
        os.environ["MCP_SKIP_AUTH"] = "false"

    def teardown_method(self):
        """
        Force GC to prevent mock accumulation in xdist workers.

        CRITICAL: Reset global state to prevent test pollution.
        Without this, tests running in parallel (-n auto) will interfere with each other
        because they share global variables and environment variables across the worker process.
        """
        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None
        import os

        if "MCP_SKIP_AUTH" in os.environ:
            del os.environ["MCP_SKIP_AUTH"]
        gc.collect()

    @pytest.mark.asyncio
    async def test_standalone_verify_token_success(self, auth_middleware_with_users):
        """Test standalone token verification succeeds"""
        token = auth_middleware_with_users.create_token("alice")
        result = await verify_token(token, secret_key="test-key")
        assert result.valid is True
        assert result.payload["username"] == "alice"

    @pytest.mark.asyncio
    async def test_standalone_verify_token_default_secret(self):
        """Test standalone verification with default secret"""
        secret = "your-secret-key-change-in-production"
        user_provider = InMemoryUserProvider(secret_key=secret, use_password_hashing=False)
        user_provider.add_user(
            username="alice", password="alice123", email="alice@test.com", roles=["user"], user_id=get_user_id("alice")
        )
        auth = AuthMiddleware(secret_key=secret, user_provider=user_provider)
        token = auth.create_token("alice")
        result = await verify_token(token)
        assert result.valid is True

    @pytest.mark.asyncio
    async def test_standalone_verify_token_invalid(self):
        """Test standalone verification of invalid token"""
        result = await verify_token("invalid.token", secret_key="test-secret")
        assert result.valid is False


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.xdist_group(name="auth_middleware_tests")
class TestGetCurrentUser:
    """Test get_current_user FastAPI dependency for bearer token authentication"""

    def setup_method(self):
        """
        Setup clean state BEFORE each test.

        CRITICAL: Reset global state BEFORE test starts to prevent pollution from previous tests.
        This is essential because tests/api/conftest.py sets MCP_SKIP_AUTH=true globally,
        which causes get_current_user() to return hardcoded username="test" instead of validating tokens.
        """
        import os

        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None
        os.environ["MCP_SKIP_AUTH"] = "false"

    def teardown_method(self):
        """
        Force GC to prevent mock accumulation in xdist workers.

        CRITICAL: Reset global state to prevent test pollution.
        Without this, tests running in parallel (-n auto) will interfere with each other
        because they share global variables and environment variables across the worker process.
        """
        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None
        import os

        if "MCP_SKIP_AUTH" in os.environ:
            del os.environ["MCP_SKIP_AUTH"]
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_current_user_with_valid_bearer_token(self):
        """
        Test get_current_user authenticates with valid JWT bearer token.

        SECURITY: This is a critical test to ensure bearer token authentication works.
        Without proper dependency injection, bearer tokens are never validated.
        """
        user_provider = InMemoryUserProvider(secret_key="test-secret", use_password_hashing=False)
        user_provider.add_user(
            username="alice",
            password="alice123",
            email="alice@acme.com",
            roles=["user", "premium"],
            user_id=get_user_id("alice"),
        )
        auth = AuthMiddleware(secret_key="test-secret", user_provider=user_provider)
        set_global_auth_middleware(auth)
        token = auth.create_token("alice", expires_in=3600)
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.user = None
        request.headers = {"Authorization": f"Bearer {token}"}
        user = await get_current_user(request)
        assert user is not None
        assert user["username"] == "alice"
        assert user["user_id"] == get_user_id("alice")
        assert "premium" in user["roles"]
        assert user["email"] == "alice@acme.com"

    @pytest.mark.asyncio
    async def test_get_current_user_with_invalid_bearer_token(self):
        """Test get_current_user rejects invalid JWT bearer token"""
        from fastapi import HTTPException

        auth = AuthMiddleware(secret_key="test-secret")
        set_global_auth_middleware(auth)
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.user = None
        request.headers = {"Authorization": "Bearer invalid.jwt.token"}
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request)
        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_with_expired_bearer_token(self):
        """Test get_current_user rejects expired JWT bearer token"""
        from fastapi import HTTPException

        user_provider = InMemoryUserProvider(secret_key="test-secret", use_password_hashing=False)
        user_provider.add_user(
            username="alice", password="alice123", email="alice@acme.com", roles=["premium"], user_id=get_user_id("alice")
        )
        auth = AuthMiddleware(secret_key="test-secret", user_provider=user_provider)
        set_global_auth_middleware(auth)
        payload = {
            "sub": get_user_id("alice"),
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
        request.headers = {"Authorization": f"Bearer {expired_token}"}
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request)
        assert exc_info.value.status_code == 401
        assert "Token expired" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_without_credentials_raises_401(self):
        """Test get_current_user requires authentication when no credentials provided"""
        from fastapi import HTTPException

        auth = AuthMiddleware(secret_key="test-secret")
        set_global_auth_middleware(auth)
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.user = None
        request.headers = {}
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request)
        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_uses_request_state_if_set(self):
        """Test get_current_user returns user from request.state if already authenticated"""
        auth = AuthMiddleware(secret_key="test-secret")
        set_global_auth_middleware(auth)
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.user = {"user_id": get_user_id("bob"), "username": "bob", "roles": ["standard"], "email": "bob@acme.com"}
        request.headers = {}
        user = await get_current_user(request)
        assert user["username"] == "bob"
        assert user["user_id"] == get_user_id("bob")

    @pytest.mark.asyncio
    async def test_get_current_user_prefers_preferred_username_over_sub(self):
        """
        Test get_current_user uses preferred_username instead of sub for Keycloak compatibility.

        SECURITY: Keycloak JWTs use UUID in 'sub' field, but OpenFGA tuples use user:username format.
        We must extract 'preferred_username' to ensure authorization works correctly.
        """
        auth = AuthMiddleware(secret_key="test-secret")
        set_global_auth_middleware(auth)
        keycloak_payload = {
            "sub": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "preferred_username": "alice",
            "email": "alice@acme.com",
            "roles": ["premium"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }
        keycloak_token = jwt.encode(keycloak_payload, "test-secret", algorithm="HS256")
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.user = None
        request.headers = {"Authorization": f"Bearer {keycloak_token}"}
        user = await get_current_user(request)
        assert user["username"] == "alice"
        # Keycloak JWTs normalize to clean user:username format (no worker-safe IDs)
        expected_user_id = f"user:{user['username']}"
        assert user["user_id"] == expected_user_id
        assert "uuid" not in user["user_id"].lower()
        assert "f47ac10b" not in user["user_id"]

    @pytest.mark.asyncio
    async def test_get_current_user_falls_back_to_sub_if_no_preferred_username(self):
        """
        Test get_current_user falls back to sub if preferred_username is missing.

        This handles legacy JWTs or non-Keycloak identity providers.
        """
        auth = AuthMiddleware(secret_key="test-secret")
        set_global_auth_middleware(auth)
        legacy_payload = {
            "sub": get_user_id("charlie"),
            "email": "charlie@acme.com",
            "roles": ["standard"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }
        legacy_token = jwt.encode(legacy_payload, "test-secret", algorithm="HS256")
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.user = None
        request.headers = {"Authorization": f"Bearer {legacy_token}"}
        user = await get_current_user(request)
        assert user["username"] == "charlie"
        assert user["user_id"] == get_user_id("charlie")

    @pytest.mark.asyncio
    async def test_get_current_user_normalizes_username_format(self):
        """
        Test get_current_user normalizes user_id to user:username format for OpenFGA.

        This ensures consistent format regardless of JWT structure.
        """
        user_provider = InMemoryUserProvider(secret_key="test-secret", use_password_hashing=False)
        user_provider.add_user(
            username="dave", password="dave123", email="dave@acme.com", roles=["admin"], user_id=get_user_id("dave")
        )
        auth = AuthMiddleware(secret_key="test-secret", user_provider=user_provider)
        set_global_auth_middleware(auth)
        payload = {
            "sub": "12345",
            "preferred_username": "dave",
            "email": "dave@acme.com",
            "roles": ["admin"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }
        token = jwt.encode(payload, "test-secret", algorithm="HS256")
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.user = None
        request.headers = {"Authorization": f"Bearer {token}"}
        user = await get_current_user(request)
        assert user["username"] == "dave"
        # Manually created JWTs normalize to clean user:username format (no worker-safe IDs)
        expected_user_id = f"user:{user['username']}"
        assert user["user_id"] == expected_user_id
        assert user["user_id"].startswith("user:")


@pytest.fixture
def test_settings_with_fallback():
    """Create test settings with fallback enabled for external provider tests"""
    from mcp_server_langgraph.core.config import Settings

    return Settings(allow_auth_fallback=True, environment="development")


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.xdist_group(name="auth_middleware_tests")
class TestAuthFallbackWithExternalProviders:
    """
    Test authorization fallback logic with external providers (Keycloak, etc.)

    SECURITY: This addresses the critical bug where Keycloak users were denied
    all access when OpenFGA was down, because the fallback logic only checked
    InMemoryUserProvider's users_db (which is empty for Keycloak).

    The fix ensures fallback authorization queries the user provider for roles
    instead of relying on in-memory user database.
    """

    def setup_method(self):
        """
        Setup clean state BEFORE each test.

        CRITICAL: Reset global state BEFORE test starts to prevent pollution from previous tests.
        This is essential because tests/api/conftest.py sets MCP_SKIP_AUTH=true globally,
        which causes get_current_user() to return hardcoded username="test" instead of validating tokens.
        """
        import os

        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None
        os.environ["MCP_SKIP_AUTH"] = "false"

    def teardown_method(self):
        """
        Force GC to prevent mock accumulation in xdist workers.

        CRITICAL: Reset global state to prevent test pollution.
        Without this, tests running in parallel (-n auto) will interfere with each other
        because they share global variables and environment variables across the worker process.
        """
        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None
        import os

        if "MCP_SKIP_AUTH" in os.environ:
            del os.environ["MCP_SKIP_AUTH"]
        gc.collect()

    @pytest.mark.asyncio
    async def test_authorize_fallback_keycloak_admin_user(self, test_settings_with_fallback):
        """
        Test fallback authorization grants admin access for Keycloak users.

        REGRESSION TEST: Previously failed because users_db was empty for Keycloak.
        """
        mock_keycloak = configured_async_mock(return_value=None, spec=KeycloakUserProvider)
        admin_user = UserData(
            user_id=get_user_id("keycloak_admin"),
            username="keycloak_admin",
            email="admin@keycloak.com",
            roles=["admin", "user"],
            active=True,
        )
        mock_keycloak.get_user_by_username.return_value = admin_user
        auth = AuthMiddleware(user_provider=mock_keycloak, settings=test_settings_with_fallback)
        result = await auth.authorize(user_id=get_user_id("keycloak_admin"), relation="executor", resource="tool:chat")
        assert result is True
        mock_keycloak.get_user_by_username.assert_called_once_with("keycloak_admin")

    @pytest.mark.asyncio
    async def test_authorize_fallback_keycloak_premium_user(self, test_settings_with_fallback):
        """
        Test fallback authorization for Keycloak premium user.

        REGRESSION TEST: Previously denied access because users_db was empty.
        """
        mock_keycloak = configured_async_mock(return_value=None, spec=KeycloakUserProvider)
        premium_user = UserData(
            user_id=get_user_id("keycloak_alice"),
            username="keycloak_alice",
            email="alice@keycloak.com",
            roles=["user", "premium"],
            active=True,
        )
        mock_keycloak.get_user_by_username.return_value = premium_user
        auth = AuthMiddleware(user_provider=mock_keycloak, settings=test_settings_with_fallback)
        result = await auth.authorize(user_id=get_user_id("keycloak_alice"), relation="executor", resource="tool:chat")
        assert result is True
        mock_keycloak.get_user_by_username.assert_called_once_with("keycloak_alice")

    @pytest.mark.asyncio
    async def test_authorize_fallback_keycloak_standard_user(self, test_settings_with_fallback):
        """Test fallback authorization for Keycloak standard user."""
        mock_keycloak = configured_async_mock(return_value=None, spec=KeycloakUserProvider)
        standard_user = UserData(
            user_id=get_user_id("keycloak_bob"), username="keycloak_bob", email="bob@keycloak.com", roles=["user"], active=True
        )
        mock_keycloak.get_user_by_username.return_value = standard_user
        auth = AuthMiddleware(user_provider=mock_keycloak, settings=test_settings_with_fallback)
        result = await auth.authorize(user_id=get_user_id("keycloak_bob"), relation="executor", resource="tool:chat")
        assert result is True

    @pytest.mark.asyncio
    async def test_authorize_fallback_keycloak_user_not_found(self, test_settings_with_fallback):
        """
        Test fallback authorization denies access for non-existent Keycloak user.

        REGRESSION TEST: Previously failed with same denial, but now logs correctly.
        """
        mock_keycloak = configured_async_mock(return_value=None, spec=KeycloakUserProvider)
        mock_keycloak.get_user_by_username.return_value = None
        auth = AuthMiddleware(user_provider=mock_keycloak, settings=test_settings_with_fallback)
        result = await auth.authorize(user_id=get_user_id("nonexistent"), relation="executor", resource="tool:chat")
        assert result is False
        mock_keycloak.get_user_by_username.assert_called_once_with("nonexistent")

    @pytest.mark.asyncio
    async def test_authorize_fallback_keycloak_provider_error(self, test_settings_with_fallback):
        """
        Test fallback authorization fails closed when provider lookup fails.

        SECURITY: When we can't verify user roles, deny access (fail closed).
        """
        mock_keycloak = configured_async_mock(return_value=None, spec=KeycloakUserProvider)
        mock_keycloak.get_user_by_username.side_effect = Exception("Keycloak connection error")
        auth = AuthMiddleware(user_provider=mock_keycloak, settings=test_settings_with_fallback)
        result = await auth.authorize(user_id=get_user_id("alice"), relation="executor", resource="tool:chat")
        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_fallback_keycloak_conversation_ownership(self, test_settings_with_fallback):
        """
        Test fallback authorization respects conversation ownership for Keycloak users.

        SECURITY: Users should only access their own conversations in fallback mode.
        """
        mock_keycloak = configured_async_mock(return_value=None, spec=KeycloakUserProvider)
        user = UserData(
            user_id=get_user_id("keycloak_alice"),
            username="keycloak_alice",
            email="alice@keycloak.com",
            roles=["user"],
            active=True,
        )
        mock_keycloak.get_user_by_username.return_value = user
        auth = AuthMiddleware(user_provider=mock_keycloak, settings=test_settings_with_fallback)
        result = await auth.authorize(
            user_id=get_user_id("keycloak_alice"), relation="viewer", resource="conversation:keycloak_alice_thread1"
        )
        assert result is True
        result = await auth.authorize(
            user_id=get_user_id("keycloak_alice"), relation="viewer", resource="conversation:default"
        )
        assert result is True
        result = await auth.authorize(
            user_id=get_user_id("keycloak_alice"), relation="viewer", resource="conversation:keycloak_bob_private"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_fallback_keycloak_user_without_required_role(self, test_settings_with_fallback):
        """Test fallback authorization denies access when user lacks required role."""
        mock_keycloak = configured_async_mock(return_value=None, spec=KeycloakUserProvider)
        limited_user = UserData(
            user_id=get_user_id("keycloak_limited"),
            username="keycloak_limited",
            email="limited@keycloak.com",
            roles=["viewer"],
            active=True,
        )
        mock_keycloak.get_user_by_username.return_value = limited_user
        auth = AuthMiddleware(user_provider=mock_keycloak, settings=test_settings_with_fallback)
        result = await auth.authorize(user_id=get_user_id("keycloak_limited"), relation="executor", resource="tool:chat")
        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_inmemory_provider_still_works(self, test_settings_with_fallback):
        """
        Test that InMemoryUserProvider fallback still works (fast path).

        REGRESSION TEST: Ensure the fix didn't break existing InMemory behavior.
        """
        user_provider = InMemoryUserProvider(secret_key="test-secret", use_password_hashing=False)
        user_provider.add_user(
            username="admin", password="admin123", email="admin@test.com", roles=["admin"], user_id=get_user_id("admin")
        )
        user_provider.add_user(
            username="alice",
            password="alice123",
            email="alice@test.com",
            roles=["user", "premium"],
            user_id=get_user_id("alice"),
        )
        auth = AuthMiddleware(secret_key="test-secret", user_provider=user_provider, settings=test_settings_with_fallback)
        result = await auth.authorize(user_id=get_user_id("admin"), relation="executor", resource="tool:chat")
        assert result is True
        result = await auth.authorize(user_id=get_user_id("alice"), relation="executor", resource="tool:chat")
        assert result is True
        result = await auth.authorize(user_id=get_user_id("unknown"), relation="executor", resource="tool:chat")
        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_openfga_takes_precedence_over_fallback(self):
        """
        Test that OpenFGA is used when available (fallback only when OpenFGA down).

        SECURITY: Fallback should ONLY be used when OpenFGA is unavailable.
        """
        mock_keycloak = configured_async_mock(return_value=None, spec=KeycloakUserProvider)
        mock_keycloak.get_user_by_username.return_value = UserData(
            user_id=get_user_id("alice"), username="alice", email="alice@keycloak.com", roles=["user"], active=True
        )
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.check_permission.return_value = True
        auth = AuthMiddleware(user_provider=mock_keycloak, openfga_client=mock_openfga)
        result = await auth.authorize(user_id=get_user_id("alice"), relation="executor", resource="tool:chat")
        assert result is True
        mock_openfga.check_permission.assert_called_once()
        mock_keycloak.get_user_by_username.assert_not_called()


@pytest.mark.xdist_group(name="auth_middleware_production_tests")
class TestAuthMiddlewareProductionControls:
    """
    CRITICAL P0: Test production environment security controls

    In production, fallback should be disabled to prevent security bypasses
    """

    def setup_method(self):
        """
        Setup clean state BEFORE each test.

        CRITICAL: Reset global state BEFORE test starts to prevent pollution from previous tests.
        This is essential because tests/api/conftest.py sets MCP_SKIP_AUTH=true globally,
        which causes get_current_user() to return hardcoded username="test" instead of validating tokens.
        """
        import os

        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None
        os.environ["MCP_SKIP_AUTH"] = "false"

    def teardown_method(self):
        """
        Force GC to prevent mock accumulation in xdist workers.

        CRITICAL: Reset global state to prevent test pollution.
        Without this, tests running in parallel (-n auto) will interfere with each other
        because they share global variables and environment variables across the worker process.
        """
        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None
        import os

        if "MCP_SKIP_AUTH" in os.environ:
            del os.environ["MCP_SKIP_AUTH"]
        gc.collect()

    @pytest.mark.asyncio
    async def test_authorize_fallback_disabled_in_production(self):
        """
        SECURITY P0: authorize() should NOT use fallback in production

        CWE-863: Incorrect Authorization
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings(
            environment="production", allow_auth_fallback=False, auth_provider="keycloak", gdpr_storage_backend="postgres"
        )
        mock_provider = configured_async_mock(return_value=None, spec=KeycloakUserProvider)
        auth = AuthMiddleware(secret_key="prod-key", user_provider=mock_provider, settings=settings, openfga_client=None)
        result = await auth.authorize(user_id=get_user_id("alice"), relation="viewer", resource="document:sensitive")
        assert result is False
