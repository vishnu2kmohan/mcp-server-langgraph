"""Comprehensive tests for Keycloak integration

Tests KeycloakClient, TokenValidator, and role synchronization.
Uses mocking to avoid requiring live Keycloak instance.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from jwt.algorithms import RSAAlgorithm

from mcp_server_langgraph.auth.keycloak import (
    KeycloakClient,
    KeycloakConfig,
    KeycloakUser,
    TokenValidator,
    sync_user_to_openfga,
)


# Fixtures

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
        verify_ssl=False,
        timeout=10,
    )


@pytest.fixture
def rsa_keypair():
    """Generate RSA keypair for JWT signing"""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    # Serialize for JWT library
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return private_pem, public_pem


@pytest.fixture
def jwks_response(rsa_keypair):
    """Mock JWKS response from Keycloak"""
    _, public_pem = rsa_keypair

    # Convert public key to JWK format
    public_key = serialization.load_pem_public_key(public_pem)
    jwk = RSAAlgorithm.to_jwk(public_key, as_dict=True)

    return {
        "keys": [
            {
                **jwk,
                "kid": "test-key-id",
                "alg": "RS256",
                "use": "sig",
            }
        ]
    }


@pytest.fixture
def keycloak_user():
    """Sample Keycloak user"""
    return KeycloakUser(
        id="550e8400-e29b-41d4-a716-446655440000",
        username="alice",
        email="alice@acme.com",
        first_name="Alice",
        last_name="Smith",
        enabled=True,
        email_verified=True,
        realm_roles=["user", "premium"],
        client_roles={"test-client": ["executor"]},
        groups=["/acme", "/acme/engineering"],
        attributes={"department": ["engineering"]},
    )


# KeycloakConfig Tests

@pytest.mark.unit
@pytest.mark.auth
class TestKeycloakConfig:
    """Test KeycloakConfig model"""

    def test_realm_url(self, keycloak_config):
        """Test realm URL construction"""
        assert keycloak_config.realm_url == "http://localhost:8180/realms/test-realm"

    def test_admin_url(self, keycloak_config):
        """Test admin API URL construction"""
        assert keycloak_config.admin_url == "http://localhost:8180/admin/realms/test-realm"

    def test_token_endpoint(self, keycloak_config):
        """Test token endpoint URL"""
        assert keycloak_config.token_endpoint == "http://localhost:8180/realms/test-realm/protocol/openid-connect/token"

    def test_userinfo_endpoint(self, keycloak_config):
        """Test userinfo endpoint URL"""
        assert keycloak_config.userinfo_endpoint == "http://localhost:8180/realms/test-realm/protocol/openid-connect/userinfo"

    def test_jwks_uri(self, keycloak_config):
        """Test JWKS URI"""
        assert keycloak_config.jwks_uri == "http://localhost:8180/realms/test-realm/protocol/openid-connect/certs"

    def test_well_known_url(self, keycloak_config):
        """Test OpenID configuration URL"""
        assert keycloak_config.well_known_url == "http://localhost:8180/realms/test-realm/.well-known/openid-configuration"


# KeycloakUser Tests

@pytest.mark.unit
@pytest.mark.auth
class TestKeycloakUser:
    """Test KeycloakUser model"""

    def test_user_id_property(self, keycloak_user):
        """Test user_id property formats correctly"""
        assert keycloak_user.user_id == "user:alice"

    def test_full_name_with_both_names(self, keycloak_user):
        """Test full_name with first and last name"""
        assert keycloak_user.full_name == "Alice Smith"

    def test_full_name_with_first_name_only(self):
        """Test full_name with only first name"""
        user = KeycloakUser(
            id="test-id",
            username="bob",
            first_name="Bob",
            last_name=None,
        )
        assert user.full_name == "Bob"

    def test_full_name_fallback_to_username(self):
        """Test full_name falls back to username"""
        user = KeycloakUser(
            id="test-id",
            username="charlie",
            first_name=None,
            last_name=None,
        )
        assert user.full_name == "charlie"


# TokenValidator Tests

@pytest.mark.unit
@pytest.mark.auth
class TestTokenValidator:
    """Test TokenValidator class"""

    @pytest.mark.asyncio
    async def test_get_jwks_success(self, keycloak_config, jwks_response):
        """Test successful JWKS retrieval"""
        validator = TokenValidator(keycloak_config)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = jwks_response
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            jwks = await validator.get_jwks()

            assert "keys" in jwks
            assert len(jwks["keys"]) == 1
            assert jwks["keys"][0]["kid"] == "test-key-id"

    @pytest.mark.asyncio
    async def test_get_jwks_caching(self, keycloak_config, jwks_response):
        """Test JWKS caching works"""
        validator = TokenValidator(keycloak_config)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = jwks_response
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            # First call - should fetch
            jwks1 = await validator.get_jwks()
            # Second call - should use cache
            jwks2 = await validator.get_jwks()

            assert jwks1 == jwks2
            # Only one HTTP call should be made
            assert mock_client.return_value.__aenter__.return_value.get.call_count == 1

    @pytest.mark.asyncio
    async def test_get_jwks_force_refresh(self, keycloak_config, jwks_response):
        """Test forced JWKS refresh"""
        validator = TokenValidator(keycloak_config)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = jwks_response
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            # First call
            await validator.get_jwks()
            # Force refresh
            await validator.get_jwks(force_refresh=True)

            # Two HTTP calls should be made
            assert mock_client.return_value.__aenter__.return_value.get.call_count == 2

    @pytest.mark.asyncio
    async def test_get_jwks_http_error(self, keycloak_config):
        """Test JWKS retrieval handles HTTP errors"""
        validator = TokenValidator(keycloak_config)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Error", request=MagicMock(), response=MagicMock()
            )

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            with pytest.raises(httpx.HTTPStatusError):
                await validator.get_jwks()

    @pytest.mark.asyncio
    async def test_verify_token_success(self, keycloak_config, rsa_keypair, jwks_response):
        """Test successful token verification"""
        private_pem, _ = rsa_keypair
        validator = TokenValidator(keycloak_config)

        # Create a valid token
        payload = {
            "sub": "user-id-123",
            "preferred_username": "alice",
            "email": "alice@acme.com",
            "aud": "test-client",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
        }

        private_key = serialization.load_pem_private_key(private_pem, password=None)
        token = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test-key-id"})

        # Mock JWKS response
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = jwks_response
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            # Verify token
            decoded = await validator.verify_token(token)

            assert decoded["sub"] == "user-id-123"
            assert decoded["preferred_username"] == "alice"
            assert decoded["aud"] == "test-client"

    @pytest.mark.asyncio
    async def test_verify_token_expired(self, keycloak_config, rsa_keypair, jwks_response):
        """Test expired token verification fails"""
        private_pem, _ = rsa_keypair
        validator = TokenValidator(keycloak_config)

        # Create expired token
        payload = {
            "sub": "user-id-123",
            "aud": "test-client",
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
            "iat": datetime.utcnow() - timedelta(hours=2),
        }

        private_key = serialization.load_pem_private_key(private_pem, password=None)
        token = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test-key-id"})

        # Mock JWKS response
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = jwks_response
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            with pytest.raises(jwt.ExpiredSignatureError):
                await validator.verify_token(token)

    @pytest.mark.asyncio
    async def test_verify_token_missing_kid(self, keycloak_config):
        """Test token without kid in header fails"""
        validator = TokenValidator(keycloak_config)

        # Create token without kid
        token = jwt.encode({"sub": "test"}, "secret", algorithm="HS256")

        with pytest.raises(jwt.InvalidTokenError, match="missing 'kid'"):
            await validator.verify_token(token)

    @pytest.mark.asyncio
    async def test_verify_token_key_not_found(self, keycloak_config, rsa_keypair):
        """Test token with unknown kid triggers JWKS refresh"""
        private_pem, _ = rsa_keypair
        validator = TokenValidator(keycloak_config)

        # Create token with unknown kid
        payload = {
            "sub": "user-id-123",
            "aud": "test-client",
            "exp": datetime.utcnow() + timedelta(hours=1),
        }

        private_key = serialization.load_pem_private_key(private_pem, password=None)
        token = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "unknown-kid"})

        # Mock JWKS response with no matching key
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"keys": []}
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            with pytest.raises(jwt.InvalidTokenError, match="Public key not found"):
                await validator.verify_token(token)

            # Should have tried twice (initial + refresh)
            assert mock_client.return_value.__aenter__.return_value.get.call_count == 2


# KeycloakClient Tests

@pytest.mark.unit
@pytest.mark.auth
class TestKeycloakClient:
    """Test KeycloakClient class"""

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, keycloak_config):
        """Test successful user authentication"""
        client = KeycloakClient(keycloak_config)

        token_response = {
            "access_token": "access-token-123",
            "refresh_token": "refresh-token-456",
            "expires_in": 300,
            "token_type": "Bearer",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = token_response
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            tokens = await client.authenticate_user("alice", "password123")

            assert tokens["access_token"] == "access-token-123"
            assert tokens["refresh_token"] == "refresh-token-456"
            assert tokens["expires_in"] == 300

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_credentials(self, keycloak_config):
        """Test authentication with invalid credentials"""
        client = KeycloakClient(keycloak_config)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Invalid credentials"
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Unauthorized", request=MagicMock(), response=mock_response
            )

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(httpx.HTTPStatusError):
                await client.authenticate_user("alice", "wrong-password")

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, keycloak_config):
        """Test successful token refresh"""
        client = KeycloakClient(keycloak_config)

        new_tokens = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 300,
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = new_tokens
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            tokens = await client.refresh_token("old-refresh-token")

            assert tokens["access_token"] == "new-access-token"

    @pytest.mark.asyncio
    async def test_get_userinfo_success(self, keycloak_config):
        """Test getting user info"""
        client = KeycloakClient(keycloak_config)

        userinfo = {
            "sub": "user-id-123",
            "preferred_username": "alice",
            "email": "alice@acme.com",
            "email_verified": True,
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = userinfo
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            info = await client.get_userinfo("access-token-123")

            assert info["sub"] == "user-id-123"
            assert info["preferred_username"] == "alice"

    @pytest.mark.asyncio
    async def test_get_admin_token_success(self, keycloak_config):
        """Test getting admin token"""
        client = KeycloakClient(keycloak_config)

        admin_token_response = {
            "access_token": "admin-token-123",
            "expires_in": 300,
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = admin_token_response
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            token = await client.get_admin_token()

            assert token == "admin-token-123"

    @pytest.mark.asyncio
    async def test_get_admin_token_caching(self, keycloak_config):
        """Test admin token caching"""
        client = KeycloakClient(keycloak_config)

        admin_token_response = {
            "access_token": "admin-token-123",
            "expires_in": 300,
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = admin_token_response
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            # First call
            token1 = await client.get_admin_token()
            # Second call should use cache
            token2 = await client.get_admin_token()

            assert token1 == token2
            # Only one HTTP call
            assert mock_client.return_value.__aenter__.return_value.post.call_count == 1

    @pytest.mark.asyncio
    async def test_get_user_by_username_success(self, keycloak_config):
        """Test getting user by username"""
        client = KeycloakClient(keycloak_config)

        user_data = {
            "id": "user-id-123",
            "username": "alice",
            "email": "alice@acme.com",
            "firstName": "Alice",
            "lastName": "Smith",
            "enabled": True,
            "emailVerified": True,
        }

        with patch.object(client, "get_admin_token", return_value="admin-token") as mock_admin:
            with patch.object(client, "_get_user_realm_roles", return_value=["user", "premium"]):
                with patch.object(client, "_get_user_client_roles", return_value={"test-client": ["executor"]}):
                    with patch.object(client, "_get_user_groups", return_value=["/acme"]):
                        with patch("httpx.AsyncClient") as mock_client:
                            mock_response = MagicMock()
                            mock_response.json.return_value = [user_data]
                            mock_response.raise_for_status = MagicMock()

                            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

                            user = await client.get_user_by_username("alice")

                            assert user is not None
                            assert user.username == "alice"
                            assert user.email == "alice@acme.com"
                            assert "premium" in user.realm_roles
                            assert "/acme" in user.groups

    @pytest.mark.asyncio
    async def test_get_user_by_username_not_found(self, keycloak_config):
        """Test getting non-existent user"""
        client = KeycloakClient(keycloak_config)

        with patch.object(client, "get_admin_token", return_value="admin-token"):
            with patch("httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.json.return_value = []  # No users found
                mock_response.raise_for_status = MagicMock()

                mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

                user = await client.get_user_by_username("nonexistent")

                assert user is None


# Role Synchronization Tests

@pytest.mark.unit
@pytest.mark.auth
class TestRoleSynchronization:
    """Test sync_user_to_openfga function"""

    @pytest.mark.asyncio
    async def test_sync_admin_role(self, keycloak_user):
        """Test syncing user with admin role"""
        keycloak_user.realm_roles = ["admin"]

        mock_openfga = AsyncMock()
        mock_openfga.write_tuples = AsyncMock()

        await sync_user_to_openfga(keycloak_user, mock_openfga)

        # Should have admin tuple
        calls = mock_openfga.write_tuples.call_args[0][0]
        admin_tuples = [t for t in calls if t["relation"] == "admin"]
        assert len(admin_tuples) == 1
        assert admin_tuples[0]["object"] == "system:global"

    @pytest.mark.asyncio
    async def test_sync_group_memberships(self, keycloak_user):
        """Test syncing group memberships"""
        keycloak_user.groups = ["/acme", "/acme/engineering"]

        mock_openfga = AsyncMock()
        mock_openfga.write_tuples = AsyncMock()

        await sync_user_to_openfga(keycloak_user, mock_openfga)

        # Should have organization memberships
        calls = mock_openfga.write_tuples.call_args[0][0]
        org_tuples = [t for t in calls if t["relation"] == "member"]
        assert len(org_tuples) == 2

        org_names = [t["object"] for t in org_tuples]
        assert "organization:acme" in org_names
        assert "organization:engineering" in org_names

    @pytest.mark.asyncio
    async def test_sync_premium_role(self, keycloak_user):
        """Test syncing premium role"""
        keycloak_user.realm_roles = ["premium"]

        mock_openfga = AsyncMock()
        mock_openfga.write_tuples = AsyncMock()

        await sync_user_to_openfga(keycloak_user, mock_openfga)

        # Should have premium role tuple
        calls = mock_openfga.write_tuples.call_args[0][0]
        premium_tuples = [t for t in calls if t["object"] == "role:premium"]
        assert len(premium_tuples) == 1

    @pytest.mark.asyncio
    async def test_sync_no_roles(self):
        """Test syncing user with no special roles"""
        user = KeycloakUser(
            id="test-id",
            username="bob",
            realm_roles=[],
            client_roles={},
            groups=[],
        )

        mock_openfga = AsyncMock()
        mock_openfga.write_tuples = AsyncMock()

        await sync_user_to_openfga(user, mock_openfga)

        # Should not call write_tuples for empty list
        mock_openfga.write_tuples.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_error_handling(self, keycloak_user):
        """Test error handling during sync"""
        mock_openfga = AsyncMock()
        mock_openfga.write_tuples.side_effect = Exception("OpenFGA error")

        with pytest.raises(Exception, match="OpenFGA error"):
            await sync_user_to_openfga(keycloak_user, mock_openfga)
