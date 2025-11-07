"""Comprehensive tests for UserProvider implementations

Tests InMemoryUserProvider, KeycloakUserProvider, and the factory function.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest

from mcp_server_langgraph.auth.keycloak import KeycloakClient, KeycloakConfig, KeycloakUser
from mcp_server_langgraph.auth.user_provider import (
    InMemoryUserProvider,
    KeycloakUserProvider,
    UserProvider,
    create_user_provider,
)

# Fixtures


@pytest.fixture
def inmemory_provider_with_users():
    """Create InMemoryUserProvider with test users (post Finding #2 fix)"""
    provider = InMemoryUserProvider(secret_key="test-secret", use_password_hashing=False)

    # Explicitly add test users (no hard-coded defaults as of Finding #2 fix)
    provider.add_user("alice", "alice123", "alice@acme.com", ["user", "premium"])
    provider.add_user("bob", "bob123", "bob@acme.com", ["user"])
    provider.add_user("admin", "admin123", "admin@acme.com", ["admin"])

    return provider


@pytest.fixture
def keycloak_config():
    """Sample Keycloak configuration"""
    return KeycloakConfig(
        server_url="http://localhost:8180",
        realm="test-realm",
        client_id="test-client",
        client_secret="test-secret",
        admin_username="admin",
        admin_password="admin-password",
    )


@pytest.fixture
def keycloak_user():
    """Sample Keycloak user"""
    return KeycloakUser(
        id="user-id-123",
        username="alice",
        email="alice@acme.com",
        first_name="Alice",
        last_name="Smith",
        enabled=True,
        email_verified=True,
        realm_roles=["user", "premium"],
        client_roles={"test-client": ["executor"]},
        groups=["/acme"],
    )


# InMemoryUserProvider Tests


@pytest.mark.unit
@pytest.mark.auth
class TestInMemoryUserProvider:
    """Test InMemoryUserProvider implementation"""

    def test_initialization(self):
        """Test provider initialization (post Finding #2 fix: no default users)"""
        provider = InMemoryUserProvider(secret_key="test-secret", use_password_hashing=False)

        assert provider.secret_key == "test-secret"
        # After Finding #2 fix: No hard-coded default users (CWE-798 remediation)
        assert len(provider.users_db) == 0  # Empty by default (secure)
        assert "alice" not in provider.users_db
        assert "bob" not in provider.users_db
        assert "admin" not in provider.users_db

    @pytest.mark.asyncio
    async def test_authenticate_success(self, inmemory_provider_with_users):
        """Test successful authentication"""
        provider = inmemory_provider_with_users  # Use fixture
        result = await provider.authenticate("alice", "alice123")

        assert result.authorized is True
        assert result.username == "alice"
        assert result.user_id == "user:alice"
        assert result.email == "alice@acme.com"
        assert "premium" in result.roles

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, inmemory_provider_with_users):
        """Test authentication with non-existent user"""
        provider = inmemory_provider_with_users  # Use fixture
        result = await provider.authenticate("nonexistent", "password")

        assert result.authorized is False
        assert result.reason == "invalid_credentials"  # Changed from user_not_found for security

    @pytest.mark.asyncio
    async def test_authenticate_inactive_user(self, inmemory_provider_with_users):
        """Test authentication with inactive user"""
        provider = inmemory_provider_with_users  # Use fixture
        provider.users_db["alice"]["active"] = False

        result = await provider.authenticate("alice", "alice123")

        assert result.authorized is False
        assert result.reason == "account_inactive"

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, inmemory_provider_with_users):
        """Test getting user by ID"""
        provider = inmemory_provider_with_users  # Use fixture
        user = await provider.get_user_by_id("user:alice")

        assert user is not None
        assert user.username == "alice"
        assert user.email == "alice@acme.com"

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, inmemory_provider_with_users):
        """Test getting non-existent user by ID"""
        provider = inmemory_provider_with_users  # Use fixture
        user = await provider.get_user_by_id("user:nonexistent")

        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_username(self, inmemory_provider_with_users):
        """Test getting user by username"""
        provider = inmemory_provider_with_users  # Use fixture
        user = await provider.get_user_by_username("bob")

        assert user is not None
        assert user.username == "bob"
        assert user.user_id == "user:bob"
        assert "user" in user.roles

    @pytest.mark.asyncio
    async def test_get_user_by_username_not_found(self, inmemory_provider_with_users):
        """Test getting non-existent user by username"""
        provider = inmemory_provider_with_users  # Use fixture
        user = await provider.get_user_by_username("nonexistent")

        assert user is None

    @pytest.mark.asyncio
    async def test_list_users(self, inmemory_provider_with_users):
        """Test listing all users"""
        provider = inmemory_provider_with_users  # Use fixture
        users = await provider.list_users()

        assert len(users) == 3
        usernames = [u.username for u in users]
        assert "alice" in usernames
        assert "bob" in usernames
        assert "admin" in usernames

    def test_create_token_success(self, inmemory_provider_with_users):
        """Test creating JWT token"""
        provider = inmemory_provider_with_users
        token = provider.create_token("alice", expires_in=3600)

        assert token is not None
        assert isinstance(token, str)

        # Verify token contents
        payload = jwt.decode(token, provider.secret_key, algorithms=["HS256"])
        assert payload["sub"] == "user:alice"
        assert payload["username"] == "alice"
        assert payload["email"] == "alice@acme.com"
        assert "premium" in payload["roles"]

    def test_create_token_user_not_found(self, inmemory_provider_with_users):
        """Test creating token for non-existent user"""
        provider = inmemory_provider_with_users  # Use fixture

        with pytest.raises(ValueError, match="User not found"):
            provider.create_token("nonexistent")

    def test_create_token_expiration(self, inmemory_provider_with_users):
        """Test token expiration is set correctly"""
        provider = inmemory_provider_with_users
        token = provider.create_token("alice", expires_in=7200)

        payload = jwt.decode(token, provider.secret_key, algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], timezone.utc)

        time_diff = (exp - iat).total_seconds()
        assert 7190 <= time_diff <= 7210  # Allow small time drift

    @pytest.mark.asyncio
    async def test_verify_token_success(self, inmemory_provider_with_users):
        """Test successful token verification"""
        provider = inmemory_provider_with_users
        token = provider.create_token("alice")

        result = await provider.verify_token(token)

        assert result.valid is True
        assert result.payload is not None
        assert result.payload["username"] == "alice"

    @pytest.mark.asyncio
    async def test_verify_token_expired(self, inmemory_provider_with_users):
        """Test verification of expired token"""
        provider = inmemory_provider_with_users

        # Create expired token
        payload = {
            "sub": "user:alice",
            "username": "alice",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        expired_token = jwt.encode(payload, provider.secret_key, algorithm="HS256")

        result = await provider.verify_token(expired_token)

        assert result.valid is False
        assert result.error == "Token expired"

    @pytest.mark.asyncio
    async def test_verify_token_invalid(self, inmemory_provider_with_users):
        """Test verification of invalid token"""
        provider = inmemory_provider_with_users

        result = await provider.verify_token("invalid.token.here")

        assert result.valid is False
        assert result.error == "Invalid token"

    @pytest.mark.asyncio
    async def test_verify_token_wrong_secret(self, inmemory_provider_with_users):
        """Test verification with wrong secret"""
        provider1 = inmemory_provider_with_users
        token = provider1.create_token("alice")

        provider2 = InMemoryUserProvider(secret_key="different-secret", use_password_hashing=False)
        provider2.add_user("alice", "password", "alice@test.com", ["user"])
        result = await provider2.verify_token(token)

        assert result.valid is False
        assert result.error == "Invalid token"


# KeycloakUserProvider Tests


@pytest.mark.unit
@pytest.mark.auth
class TestKeycloakUserProvider:
    """Test KeycloakUserProvider implementation"""

    def test_initialization(self, keycloak_config):
        """Test provider initialization"""
        provider = KeycloakUserProvider(config=keycloak_config)

        assert provider.config == keycloak_config
        assert provider.client is not None
        assert provider.openfga_client is None
        assert provider.sync_on_login is True

    def test_initialization_with_openfga(self, keycloak_config):
        """Test initialization with OpenFGA client"""
        mock_openfga = AsyncMock()
        provider = KeycloakUserProvider(config=keycloak_config, openfga_client=mock_openfga, sync_on_login=False)

        assert provider.openfga_client == mock_openfga
        assert provider.sync_on_login is False

    @pytest.mark.asyncio
    async def test_authenticate_success(self, keycloak_config, keycloak_user):
        """Test successful authentication"""
        provider = KeycloakUserProvider(config=keycloak_config, sync_on_login=False)

        tokens = {
            "access_token": "access-token-123",
            "refresh_token": "refresh-token-456",
            "expires_in": 300,
        }

        userinfo = {
            "sub": "user-id-123",
            "preferred_username": "alice",
            "email": "alice@acme.com",
        }

        with patch.object(provider.client, "authenticate_user", return_value=tokens):
            with patch.object(provider.client, "get_userinfo", return_value=userinfo):
                with patch.object(provider.client, "get_user_by_username", return_value=keycloak_user):
                    result = await provider.authenticate("alice", "password123")

                    assert result.authorized is True
                    assert result.username == "alice"
                    assert result.user_id == "user:alice"
                    assert result.email == "alice@acme.com"
                    assert "premium" in result.roles
                    assert result.access_token == "access-token-123"
                    assert result.refresh_token == "refresh-token-456"

    @pytest.mark.asyncio
    async def test_authenticate_no_password(self, keycloak_config):
        """Test authentication without password"""
        provider = KeycloakUserProvider(config=keycloak_config)

        result = await provider.authenticate("alice", password=None)

        assert result.authorized is False
        assert result.reason == "password_required"

    @pytest.mark.asyncio
    async def test_authenticate_with_openfga_sync(self, keycloak_config, keycloak_user):
        """Test authentication with OpenFGA synchronization"""
        mock_openfga = AsyncMock()
        mock_openfga.write_tuples = AsyncMock()

        provider = KeycloakUserProvider(config=keycloak_config, openfga_client=mock_openfga, sync_on_login=True)

        tokens = {"access_token": "token", "expires_in": 300}
        userinfo = {"sub": "user-id-123", "preferred_username": "alice"}

        with patch.object(provider.client, "authenticate_user", return_value=tokens):
            with patch.object(provider.client, "get_userinfo", return_value=userinfo):
                with patch.object(provider.client, "get_user_by_username", return_value=keycloak_user):
                    result = await provider.authenticate("alice", "password123")

                    assert result.authorized is True
                    # Verify OpenFGA sync was called
                    mock_openfga.write_tuples.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_openfga_sync_failure(self, keycloak_config, keycloak_user):
        """Test authentication continues even if OpenFGA sync fails"""
        mock_openfga = AsyncMock()
        mock_openfga.write_tuples.side_effect = Exception("OpenFGA error")

        provider = KeycloakUserProvider(config=keycloak_config, openfga_client=mock_openfga, sync_on_login=True)

        tokens = {"access_token": "token", "expires_in": 300}
        userinfo = {"sub": "user-id-123", "preferred_username": "alice"}

        with patch.object(provider.client, "authenticate_user", return_value=tokens):
            with patch.object(provider.client, "get_userinfo", return_value=userinfo):
                with patch.object(provider.client, "get_user_by_username", return_value=keycloak_user):
                    # Should succeed despite OpenFGA error
                    result = await provider.authenticate("alice", "password123")
                    assert result.authorized is True

    @pytest.mark.asyncio
    async def test_authenticate_keycloak_error(self, keycloak_config):
        """Test authentication handles Keycloak errors"""
        provider = KeycloakUserProvider(config=keycloak_config)

        with patch.object(provider.client, "authenticate_user", side_effect=Exception("Keycloak error")):
            result = await provider.authenticate("alice", "password123")

            assert result.authorized is False
            assert result.reason == "authentication_failed"
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, keycloak_config, keycloak_user):
        """Test getting user by ID"""
        provider = KeycloakUserProvider(config=keycloak_config)

        with patch.object(provider.client, "get_user_by_username", return_value=keycloak_user):
            user = await provider.get_user_by_id("user:alice")

            assert user is not None
            assert user.username == "alice"
            assert user.email == "alice@acme.com"

    @pytest.mark.asyncio
    async def test_get_user_by_username(self, keycloak_config, keycloak_user):
        """Test getting user by username"""
        provider = KeycloakUserProvider(config=keycloak_config)

        with patch.object(provider.client, "get_user_by_username", return_value=keycloak_user):
            user = await provider.get_user_by_username("alice")

            assert user is not None
            assert user.username == "alice"
            assert user.user_id == "user:alice"
            assert user.email == "alice@acme.com"
            assert "premium" in user.roles
            # Note: first_name, last_name, groups not in UserData model
            # These were from KeycloakUser, not returned in UserData

    @pytest.mark.asyncio
    async def test_get_user_by_username_not_found(self, keycloak_config):
        """Test getting non-existent user"""
        provider = KeycloakUserProvider(config=keycloak_config)

        with patch.object(provider.client, "get_user_by_username", return_value=None):
            user = await provider.get_user_by_username("nonexistent")

            assert user is None

    @pytest.mark.asyncio
    async def test_get_user_error_handling(self, keycloak_config):
        """Test error handling when fetching user"""
        provider = KeycloakUserProvider(config=keycloak_config)

        with patch.object(provider.client, "get_user_by_username", side_effect=Exception("Keycloak error")):
            user = await provider.get_user_by_username("alice")

            assert user is None

    @pytest.mark.asyncio
    async def test_verify_token_success(self, keycloak_config):
        """Test successful token verification"""
        provider = KeycloakUserProvider(config=keycloak_config)

        payload = {
            "sub": "user-id-123",
            "preferred_username": "alice",
            "email": "alice@acme.com",
        }

        with patch.object(provider.client, "verify_token", return_value=payload):
            result = await provider.verify_token("valid-token")

            assert result.valid is True
            assert result.payload == payload

    @pytest.mark.asyncio
    async def test_verify_token_invalid(self, keycloak_config):
        """Test verification of invalid token"""
        provider = KeycloakUserProvider(config=keycloak_config)

        with patch.object(provider.client, "verify_token", side_effect=Exception("Invalid token")):
            result = await provider.verify_token("invalid-token")

            assert result.valid is False
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, keycloak_config):
        """Test successful token refresh"""
        provider = KeycloakUserProvider(config=keycloak_config)

        new_tokens = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 300,
        }

        with patch.object(provider.client, "refresh_token", return_value=new_tokens):
            result = await provider.refresh_token("old-refresh-token")

            assert result["success"] is True
            assert result["tokens"] == new_tokens

    @pytest.mark.asyncio
    async def test_refresh_token_failure(self, keycloak_config):
        """Test token refresh failure"""
        provider = KeycloakUserProvider(config=keycloak_config)

        with patch.object(provider.client, "refresh_token", side_effect=Exception("Refresh failed")):
            result = await provider.refresh_token("invalid-refresh-token")

            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_list_users_not_implemented(self, keycloak_config):
        """Test list_users returns empty list (not implemented)"""
        provider = KeycloakUserProvider(config=keycloak_config)

        users = await provider.list_users()

        assert users == []


# Factory Function Tests


@pytest.mark.unit
@pytest.mark.auth
class TestCreateUserProvider:
    """Test create_user_provider factory function"""

    def test_create_inmemory_provider(self):
        """Test creating InMemoryUserProvider"""
        provider = create_user_provider(provider_type="inmemory", secret_key="test-secret")

        assert isinstance(provider, InMemoryUserProvider)
        assert provider.secret_key == "test-secret"

    def test_create_inmemory_provider_default(self):
        """Test creating InMemoryUserProvider with defaults"""
        provider = create_user_provider()

        assert isinstance(provider, InMemoryUserProvider)

    def test_create_keycloak_provider(self, keycloak_config):
        """Test creating KeycloakUserProvider"""
        provider = create_user_provider(provider_type="keycloak", keycloak_config=keycloak_config)

        assert isinstance(provider, KeycloakUserProvider)
        assert provider.config == keycloak_config

    def test_create_keycloak_provider_with_openfga(self, keycloak_config):
        """Test creating KeycloakUserProvider with OpenFGA client"""
        mock_openfga = AsyncMock()

        provider = create_user_provider(provider_type="keycloak", keycloak_config=keycloak_config, openfga_client=mock_openfga)

        assert isinstance(provider, KeycloakUserProvider)
        assert provider.openfga_client == mock_openfga

    def test_create_keycloak_provider_missing_config(self):
        """Test creating KeycloakUserProvider without config fails"""
        with pytest.raises(ValueError, match="keycloak_config required"):
            create_user_provider(provider_type="keycloak")

    def test_create_provider_unknown_type(self):
        """Test creating provider with unknown type"""
        with pytest.raises(ValueError, match="Unknown provider type"):
            create_user_provider(provider_type="unknown")

    def test_create_provider_case_insensitive(self):
        """Test provider type is case-insensitive"""
        provider = create_user_provider(provider_type="InMemory")

        assert isinstance(provider, InMemoryUserProvider)


# UserProvider Interface Tests


@pytest.mark.unit
@pytest.mark.auth
class TestUserProviderInterface:
    """Test UserProvider abstract interface"""

    def test_cannot_instantiate_abstract_class(self):
        """Test UserProvider cannot be instantiated directly"""
        with pytest.raises(TypeError):
            UserProvider()

    @pytest.mark.asyncio
    async def test_inmemory_implements_interface(self):
        """Test InMemoryUserProvider implements all abstract methods"""
        provider = inmemory_provider_with_users  # Use fixture

        # Test all abstract methods are implemented
        assert callable(provider.authenticate)
        assert callable(provider.get_user_by_id)
        assert callable(provider.get_user_by_username)
        assert callable(provider.verify_token)
        assert callable(provider.list_users)

        # Test they work
        result = await provider.authenticate("alice", "alice123")
        assert result.authorized is True

        user = await provider.get_user_by_username("alice")
        assert user is not None

    @pytest.mark.asyncio
    async def test_keycloak_implements_interface(self, keycloak_config):
        """Test KeycloakUserProvider implements all abstract methods"""
        provider = KeycloakUserProvider(config=keycloak_config)

        # Test all abstract methods are implemented
        assert callable(provider.authenticate)
        assert callable(provider.get_user_by_id)
        assert callable(provider.get_user_by_username)
        assert callable(provider.verify_token)
        assert callable(provider.list_users)
