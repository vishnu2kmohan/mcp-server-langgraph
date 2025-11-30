"""Comprehensive tests for Keycloak integration

Tests KeycloakClient, TokenValidator, and role synchronization.
Uses mocking to avoid requiring live Keycloak instance.
"""

import gc
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.helpers.async_mock_helpers import configured_async_mock

httpx = pytest.importorskip("httpx", reason="httpx required for Keycloak tests")
import jwt  # noqa: E402
from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from jwt.algorithms import RSAAlgorithm  # noqa: E402

from mcp_server_langgraph.auth.keycloak import (  # noqa: E402
    KeycloakClient,
    KeycloakConfig,
    KeycloakUser,
    TokenValidator,
    sync_user_to_openfga,
)
from tests.conftest import get_user_id  # noqa: E402

pytestmark = pytest.mark.unit


@pytest.fixture
def keycloak_config():
    """Sample Keycloak configuration"""
    return KeycloakConfig(
        server_url="http://localhost:9082",
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
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return (private_pem, public_pem)


@pytest.fixture
def jwks_response(rsa_keypair):
    """Mock JWKS response from Keycloak"""
    _, public_pem = rsa_keypair
    public_key = serialization.load_pem_public_key(public_pem)
    jwk = RSAAlgorithm.to_jwk(public_key, as_dict=True)
    return {"keys": [{**jwk, "kid": "test-key-id", "alg": "RS256", "use": "sig"}]}


@pytest.fixture
def keycloak_user():
    """Sample Keycloak user"""
    return KeycloakUser(
        id="550e8400-e29b-41d4-a716-446655440000",
        username=get_user_id("alice").split(":")[-1],  # Worker-safe: "test_gw0_alice"
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


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.xdist_group(name="keycloak_unit_tests")
class TestKeycloakConfig:
    """Test KeycloakConfig model"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_realm_url_construction_with_base_url_returns_correct_endpoint(self, keycloak_config):
        """Test realm URL construction"""
        assert keycloak_config.realm_url == "http://localhost:9082/realms/test-realm"

    def test_admin_url_construction_with_realm_name_returns_correct_endpoint(self, keycloak_config):
        """Test admin API URL construction"""
        assert keycloak_config.admin_url == "http://localhost:9082/admin/realms/test-realm"

    def test_token_endpoint_construction_with_realm_returns_openid_connect_url(self, keycloak_config):
        """Test token endpoint URL"""
        assert keycloak_config.token_endpoint == "http://localhost:9082/realms/test-realm/protocol/openid-connect/token"

    def test_userinfo_endpoint_construction_with_realm_returns_openid_connect_url(self, keycloak_config):
        """Test userinfo endpoint URL"""
        assert keycloak_config.userinfo_endpoint == "http://localhost:9082/realms/test-realm/protocol/openid-connect/userinfo"

    def test_jwks_uri_construction_with_realm_returns_certificate_endpoint(self, keycloak_config):
        """Test JWKS URI"""
        assert keycloak_config.jwks_uri == "http://localhost:9082/realms/test-realm/protocol/openid-connect/certs"

    def test_well_known_url(self, keycloak_config):
        """Test OpenID configuration URL"""
        assert keycloak_config.well_known_url == "http://localhost:9082/realms/test-realm/.well-known/openid-configuration"


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.xdist_group(name="keycloak_unit_tests")
class TestKeycloakUser:
    """Test KeycloakUser model"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_user_id_property(self, keycloak_user):
        """Test user_id property formats correctly"""
        assert keycloak_user.user_id == get_user_id("alice")

    def test_full_name_with_both_names(self, keycloak_user):
        """Test full_name with first and last name"""
        assert keycloak_user.full_name == "Alice Smith"

    def test_full_name_with_first_name_only(self):
        """Test full_name with only first name"""
        user = KeycloakUser(id="test-id", username="bob", first_name="Bob", last_name=None)
        assert user.full_name == "Bob"

    def test_full_name_fallback_to_username(self):
        """Test full_name falls back to username"""
        user = KeycloakUser(id="test-id", username="charlie", first_name=None, last_name=None)
        assert user.full_name == "charlie"


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.xdist_group(name="keycloak_unit_tests")
class TestTokenValidator:
    """Test TokenValidator class"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

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
            jwks1 = await validator.get_jwks()
            jwks2 = await validator.get_jwks()
            assert jwks1 == jwks2
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
            await validator.get_jwks()
            await validator.get_jwks(force_refresh=True)
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
        payload = {
            "sub": "user-id-123",
            "preferred_username": "alice",
            "email": "alice@acme.com",
            "aud": "test-client",
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "iat": datetime.now(UTC),
        }
        private_key = serialization.load_pem_private_key(private_pem, password=None)
        token = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test-key-id"})
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = jwks_response
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            decoded = await validator.verify_token(token)
            assert decoded["sub"] == "user-id-123"
            assert decoded["preferred_username"] == "alice"
            assert decoded["aud"] == "test-client"

    @pytest.mark.asyncio
    async def test_verify_token_expired(self, keycloak_config, rsa_keypair, jwks_response):
        """Test expired token verification fails"""
        private_pem, _ = rsa_keypair
        validator = TokenValidator(keycloak_config)
        payload = {
            "sub": "user-id-123",
            "aud": "test-client",
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "iat": datetime.now(UTC) - timedelta(hours=2),
        }
        private_key = serialization.load_pem_private_key(private_pem, password=None)
        token = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test-key-id"})
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
        token = jwt.encode({"sub": "test"}, "secret", algorithm="HS256")
        with pytest.raises(jwt.InvalidTokenError, match="missing 'kid'"):
            await validator.verify_token(token)

    @pytest.mark.asyncio
    async def test_verify_token_key_not_found(self, keycloak_config, rsa_keypair):
        """Test token with unknown kid triggers JWKS refresh"""
        private_pem, _ = rsa_keypair
        validator = TokenValidator(keycloak_config)
        payload = {"sub": "user-id-123", "aud": "test-client", "exp": datetime.now(UTC) + timedelta(hours=1)}
        private_key = serialization.load_pem_private_key(private_pem, password=None)
        token = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "unknown-kid"})
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"keys": []}
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            with pytest.raises(jwt.InvalidTokenError, match="Public key not found"):
                await validator.verify_token(token)
            assert mock_client.return_value.__aenter__.return_value.get.call_count == 2


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.xdist_group(name="keycloak_unit_tests")
class TestKeycloakClient:
    """Test KeycloakClient class"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

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
        new_tokens = {"access_token": "new-access-token", "refresh_token": "new-refresh-token", "expires_in": 300}
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
        userinfo = {"sub": "user-id-123", "preferred_username": "alice", "email": "alice@acme.com", "email_verified": True}
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
        admin_token_response = {"access_token": "admin-token-123", "expires_in": 300}
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
        admin_token_response = {"access_token": "admin-token-123", "expires_in": 300}
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = admin_token_response
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            token1 = await client.get_admin_token()
            token2 = await client.get_admin_token()
            assert token1 == token2
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
        with patch.object(client, "get_admin_token", return_value="admin-token"):
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
                mock_response.json.return_value = []
                mock_response.raise_for_status = MagicMock()
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
                user = await client.get_user_by_username("nonexistent")
                assert user is None


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.xdist_group(name="keycloak_unit_tests")
class TestRoleSynchronization:
    """Test sync_user_to_openfga function"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_sync_admin_role(self, keycloak_user):
        """Test syncing user with admin role"""
        keycloak_user.realm_roles = ["admin"]
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.write_tuples = configured_async_mock(return_value=None)
        await sync_user_to_openfga(keycloak_user, mock_openfga)
        calls = mock_openfga.write_tuples.call_args[0][0]
        admin_tuples = [t for t in calls if t["relation"] == "admin"]
        assert len(admin_tuples) == 1
        assert admin_tuples[0]["object"] == "system:global"

    @pytest.mark.asyncio
    async def test_sync_group_memberships(self, keycloak_user):
        """Test syncing group memberships"""
        keycloak_user.groups = ["/acme", "/acme/engineering"]
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.write_tuples = configured_async_mock(return_value=None)
        await sync_user_to_openfga(keycloak_user, mock_openfga)
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
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.write_tuples = configured_async_mock(return_value=None)
        await sync_user_to_openfga(keycloak_user, mock_openfga)
        calls = mock_openfga.write_tuples.call_args[0][0]
        premium_tuples = [t for t in calls if t["object"] == "role:premium"]
        assert len(premium_tuples) == 1

    @pytest.mark.asyncio
    async def test_sync_no_roles(self):
        """Test syncing user with no special roles"""
        user = KeycloakUser(id="test-id", username="bob", realm_roles=[], client_roles={}, groups=[])
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.write_tuples = configured_async_mock(return_value=None)
        await sync_user_to_openfga(user, mock_openfga)
        mock_openfga.write_tuples.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_error_handling(self, keycloak_user):
        """Test error handling during sync"""
        mock_openfga = configured_async_mock(return_value=None)
        mock_openfga.write_tuples.side_effect = Exception("OpenFGA error")
        with pytest.raises(Exception, match="OpenFGA error"):
            await sync_user_to_openfga(keycloak_user, mock_openfga)


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.xdist_group(name="keycloak_unit_tests")
class TestKeycloakPrivateMethods:
    """Test private helper methods for comprehensive coverage"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_user_realm_roles_success(self, keycloak_config):
        """Test retrieving user's realm roles"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = [{"name": "admin"}, {"name": "user"}]
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            roles = await client._get_user_realm_roles("user-id-123", "admin-token")
            assert roles == ["admin", "user"]

    @pytest.mark.asyncio
    async def test_get_user_realm_roles_http_error(self, keycloak_config):
        """Test realm roles retrieval handles HTTP errors"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Error", request=MagicMock(), response=MagicMock()
            )
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            roles = await client._get_user_realm_roles("user-id-123", "admin-token")
            assert roles == []

    @pytest.mark.asyncio
    async def test_get_user_client_roles_success(self, keycloak_config):
        """Test retrieving user's client roles"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            clients_response = MagicMock()
            clients_response.json.return_value = [
                {"id": "client-uuid", "clientId": "test-client"},
                {"id": "other-uuid", "clientId": "other-client"},
            ]
            clients_response.raise_for_status = MagicMock()
            roles_response = MagicMock()
            roles_response.status_code = 200
            roles_response.json.return_value = [{"name": "executor"}, {"name": "viewer"}]

            async def mock_get(url, headers):
                if "clients" in url and "role-mappings" not in url:
                    return clients_response
                else:
                    return roles_response

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=mock_get)
            client_roles = await client._get_user_client_roles("user-id-123", "admin-token")
            assert "test-client" in client_roles
            assert client_roles["test-client"] == ["executor", "viewer"]

    @pytest.mark.asyncio
    async def test_get_user_client_roles_http_error(self, keycloak_config):
        """Test client roles retrieval handles HTTP errors"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Error", request=MagicMock(), response=MagicMock()
            )
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            client_roles = await client._get_user_client_roles("user-id-123", "admin-token")
            assert client_roles == {}

    @pytest.mark.asyncio
    async def test_get_user_groups_success(self, keycloak_config):
        """Test retrieving user's group memberships"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = [
                {"path": "/acme", "name": "acme"},
                {"path": "/acme/engineering", "name": "engineering"},
            ]
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            groups = await client._get_user_groups("user-id-123", "admin-token")
            assert groups == ["/acme", "/acme/engineering"]

    @pytest.mark.asyncio
    async def test_get_user_groups_http_error(self, keycloak_config):
        """Test groups retrieval handles HTTP errors"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Error", request=MagicMock(), response=MagicMock()
            )
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            groups = await client._get_user_groups("user-id-123", "admin-token")
            assert groups == []


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.xdist_group(name="keycloak_unit_tests")
class TestTokenValidatorErrorPaths:
    """Test error paths in TokenValidator for higher coverage"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_verify_token_generic_exception(self, keycloak_config, rsa_keypair, jwks_response):
        """Test generic exception handling during token verification"""
        private_pem, _ = rsa_keypair
        validator = TokenValidator(keycloak_config)
        payload = {
            "sub": "user-id-123",
            "preferred_username": "alice",
            "aud": "test-client",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        }
        private_key = serialization.load_pem_private_key(private_pem, password=None)
        token = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test-key-id"})
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.side_effect = Exception("Network error")
            with pytest.raises(Exception, match="Network error"):
                await validator.verify_token(token)


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.xdist_group(name="keycloak_unit_tests")
class TestKeycloakAdminClientManagement:
    """
    Test Keycloak Admin API client management methods.

    These tests follow TDD principles - RED phase.
    Tests written BEFORE implementation to ensure proper behavior.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_client_success(self, keycloak_config):
        """
        Test creating a Keycloak client via Admin API.

        RED: This test will FAIL initially because create_client raises NotImplementedError.
        """
        client = KeycloakClient(keycloak_config)
        client_config = {
            "clientId": "test-service-principal",
            "name": "Test Service Principal",
            "description": "Service account for testing",
            "enabled": True,
            "serviceAccountsEnabled": True,
            "standardFlowEnabled": False,
            "directAccessGrantsEnabled": False,
            "implicitFlowEnabled": False,
            "publicClient": False,
            "clientAuthenticatorType": "client-secret",
            "secret": "test-secret-123",
            "attributes": {
                "associatedUserId": get_user_id("alice"),
                "inheritPermissions": "true",
                "owner": get_user_id("alice"),
            },
        }
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123", "expires_in": 300}
            mock_token_response.raise_for_status = MagicMock()
            mock_create_response = MagicMock()
            mock_create_response.status_code = 201
            mock_create_response.headers = {
                "Location": "http://localhost:9082/admin/realms/test-realm/clients/client-uuid-123"
            }
            mock_create_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(side_effect=[mock_token_response, mock_create_response])
            mock_client.return_value.__aenter__.return_value = mock_async_client
            client_id = await client.create_client(client_config)
            assert client_id == "client-uuid-123"
            assert mock_async_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_create_client_http_error(self, keycloak_config):
        """Test create_client handles HTTP errors gracefully"""
        client = KeycloakClient(keycloak_config)
        client_config = {"clientId": "duplicate-client", "name": "Duplicate Client"}
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123", "expires_in": 300}
            mock_token_response.raise_for_status = MagicMock()
            mock_create_response = MagicMock()
            mock_create_response.status_code = 409
            mock_create_response.text = "Client already exists"
            mock_create_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Conflict", request=MagicMock(), response=mock_create_response
            )
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(side_effect=[mock_token_response, mock_create_response])
            mock_client.return_value.__aenter__.return_value = mock_async_client
            with pytest.raises(httpx.HTTPStatusError):
                await client.create_client(client_config)

    @pytest.mark.asyncio
    async def test_delete_client_success(self, keycloak_config):
        """Test deleting a Keycloak client via Admin API"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123", "expires_in": 300}
            mock_token_response.raise_for_status = MagicMock()
            mock_delete_response = MagicMock()
            mock_delete_response.status_code = 204
            mock_delete_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.delete = AsyncMock(return_value=mock_delete_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            await client.delete_client("client-uuid-123")
            mock_async_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_client_not_found(self, keycloak_config):
        """Test delete_client handles 404 Not Found"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123", "expires_in": 300}
            mock_token_response.raise_for_status = MagicMock()
            mock_delete_response = MagicMock()
            mock_delete_response.status_code = 404
            mock_delete_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=mock_delete_response
            )
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.delete = AsyncMock(return_value=mock_delete_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            with pytest.raises(httpx.HTTPStatusError):
                await client.delete_client("nonexistent-client")


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.xdist_group(name="keycloak_unit_tests")
class TestKeycloakAdminUserManagement:
    """Test Keycloak Admin API user management methods"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_user_success(self, keycloak_config):
        """Test creating a Keycloak user via Admin API"""
        client = KeycloakClient(keycloak_config)
        user_config = {
            "username": "svc_batch_job",
            "enabled": True,
            "email": "svc-batch-job@example.com",
            "emailVerified": True,
            "attributes": {
                "serviceAccount": "true",
                "associatedUserId": get_user_id("alice"),
                "inheritPermissions": "true",
                "owner": get_user_id("alice"),
            },
        }
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123", "expires_in": 300}
            mock_token_response.raise_for_status = MagicMock()
            mock_create_response = MagicMock()
            mock_create_response.status_code = 201
            mock_create_response.headers = {"Location": "http://localhost:9082/admin/realms/test-realm/users/user-uuid-456"}
            mock_create_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(side_effect=[mock_token_response, mock_create_response])
            mock_client.return_value.__aenter__.return_value = mock_async_client
            user_id = await client.create_user(user_config)
            assert user_id == "user-uuid-456"

    @pytest.mark.asyncio
    async def test_delete_user_success(self, keycloak_config):
        """Test deleting a Keycloak user via Admin API"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123", "expires_in": 300}
            mock_token_response.raise_for_status = MagicMock()
            mock_delete_response = MagicMock()
            mock_delete_response.status_code = 204
            mock_delete_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.delete = AsyncMock(return_value=mock_delete_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            await client.delete_user("user-uuid-456")
            mock_async_client.delete.assert_called_once()


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.xdist_group(name="keycloak_unit_tests")
class TestKeycloakUserAttributes:
    """Test Keycloak user attribute management (for API keys)"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_user_attributes_success(self, keycloak_config):
        """Test retrieving user attributes via Admin API"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123", "expires_in": 300}
            mock_token_response.raise_for_status = MagicMock()
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = {
                "id": "user-uuid-789",
                "username": "alice",
                "attributes": {
                    "apiKeys": ["key:abc123:hash1", "key:def456:hash2"],
                    "apiKey_abc123_name": "Production Key",
                    "apiKey_def456_name": "Development Key",
                },
            }
            mock_get_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.get = AsyncMock(return_value=mock_get_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            attributes = await client.get_user_attributes("user-uuid-789")
            assert "apiKeys" in attributes
            assert len(attributes["apiKeys"]) == 2
            assert "apiKey_abc123_name" in attributes

    @pytest.mark.asyncio
    async def test_update_user_attributes_success(self, keycloak_config):
        """Test updating user attributes via Admin API"""
        client = KeycloakClient(keycloak_config)
        new_attributes = {
            "apiKeys": ["key:abc123:hash1", "key:def456:hash2", "key:ghi789:hash3"],
            "apiKey_ghi789_name": "Staging Key",
            "apiKey_ghi789_created": "2025-11-02T12:00:00",
        }
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123", "expires_in": 300}
            mock_token_response.raise_for_status = MagicMock()
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = {
                "id": "user-uuid-789",
                "username": "alice",
                "email": "alice@example.com",
                "enabled": True,
                "attributes": {"apiKeys": ["key:abc123:hash1", "key:def456:hash2"]},
            }
            mock_get_response.raise_for_status = MagicMock()
            mock_put_response = MagicMock()
            mock_put_response.status_code = 204
            mock_put_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.get = AsyncMock(return_value=mock_get_response)
            mock_async_client.put = AsyncMock(return_value=mock_put_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            await client.update_user_attributes("user-uuid-789", new_attributes)
            mock_async_client.put.assert_called_once()
            call_args = mock_async_client.put.call_args
            assert "attributes" in call_args.kwargs["json"]
            assert call_args.kwargs["json"]["attributes"] == new_attributes


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.scim
@pytest.mark.xdist_group(name="keycloak_unit_tests")
class TestKeycloakSCIMUserMethods:
    """
    Test SCIM 2.0 user management methods (TDD RED phase).

    These tests are written FIRST to define expected behavior.
    All tests will FAIL initially because methods raise NotImplementedError.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_update_user_success(self, keycloak_config):
        """Test updating a user via Admin API"""
        client = KeycloakClient(keycloak_config)
        user_config = {
            "username": "alice",
            "email": "alice.updated@example.com",
            "firstName": "Alice",
            "lastName": "Johnson",
            "enabled": True,
            "attributes": {"department": ["engineering"], "title": ["Senior Engineer"]},
        }
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123", "expires_in": 300}
            mock_token_response.raise_for_status = MagicMock()
            mock_put_response = MagicMock()
            mock_put_response.status_code = 204
            mock_put_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.put = AsyncMock(return_value=mock_put_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            await client.update_user("user-uuid-123", user_config)
            mock_async_client.put.assert_called_once()
            call_args = mock_async_client.put.call_args
            assert "admin/realms/test-realm/users/user-uuid-123" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_update_user_http_error(self, keycloak_config):
        """Test update_user handles HTTP errors"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123", "expires_in": 300}
            mock_token_response.raise_for_status = MagicMock()
            mock_put_response = MagicMock()
            mock_put_response.status_code = 404
            mock_put_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=mock_put_response
            )
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.put = AsyncMock(return_value=mock_put_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            with pytest.raises(httpx.HTTPStatusError):
                await client.update_user("nonexistent-user", {})

    @pytest.mark.asyncio
    async def test_set_user_password_success(self, keycloak_config):
        """Test setting user password via Admin API"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123", "expires_in": 300}
            mock_token_response.raise_for_status = MagicMock()
            mock_put_response = MagicMock()
            mock_put_response.status_code = 204
            mock_put_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.put = AsyncMock(return_value=mock_put_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            await client.set_user_password("user-uuid-123", "newSecurePass123!", temporary=False)
            mock_async_client.put.assert_called_once()
            call_args = mock_async_client.put.call_args
            assert "reset-password" in call_args.args[0]
            assert call_args.kwargs["json"]["value"] == "newSecurePass123!"
            assert call_args.kwargs["json"]["temporary"] is False

    @pytest.mark.asyncio
    async def test_set_user_password_temporary(self, keycloak_config):
        """Test setting temporary user password"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_put_response = MagicMock()
            mock_put_response.status_code = 204
            mock_put_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.put = AsyncMock(return_value=mock_put_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            await client.set_user_password("user-uuid-123", "tempPass", temporary=True)
            call_args = mock_async_client.put.call_args
            assert call_args.kwargs["json"]["temporary"] is True

    @pytest.mark.asyncio
    async def test_get_user_success(self, keycloak_config):
        """Test getting user by ID via Admin API"""
        client = KeycloakClient(keycloak_config)
        user_data = {
            "id": "user-uuid-123",
            "username": "alice",
            "email": "alice@example.com",
            "firstName": "Alice",
            "lastName": "Smith",
            "enabled": True,
            "emailVerified": True,
            "attributes": {"department": ["engineering"]},
        }
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = user_data
            mock_get_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.get = AsyncMock(return_value=mock_get_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            user = await client.get_user("user-uuid-123")
            assert user is not None
            assert user["id"] == "user-uuid-123"
            assert user["username"] == "alice"
            assert user["email"] == "alice@example.com"

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, keycloak_config):
        """Test get_user returns None for non-existent user"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_get_response = MagicMock()
            mock_get_response.status_code = 404
            mock_get_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=mock_get_response
            )
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.get = AsyncMock(return_value=mock_get_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            user = await client.get_user("nonexistent-user")
            assert user is None

    @pytest.mark.asyncio
    async def test_search_users_success(self, keycloak_config):
        """Test searching users via Admin API"""
        client = KeycloakClient(keycloak_config)
        users_data = [
            {"id": "user-1", "username": "alice", "email": "alice@example.com", "enabled": True},
            {"id": "user-2", "username": "alice.smith", "email": "alice.smith@example.com", "enabled": True},
        ]
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = users_data
            mock_get_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.get = AsyncMock(return_value=mock_get_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            users = await client.search_users(query={"username": "alice"}, first=0, max=100)
            assert len(users) == 2
            assert users[0]["username"] == "alice"
            call_args = mock_async_client.get.call_args
            assert "params" in call_args.kwargs
            assert call_args.kwargs["params"]["first"] == 0
            assert call_args.kwargs["params"]["max"] == 100

    @pytest.mark.asyncio
    async def test_search_users_with_email_filter(self, keycloak_config):
        """Test searching users by email"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = []
            mock_get_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.get = AsyncMock(return_value=mock_get_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            await client.search_users(query={"email": "alice@example.com"})
            call_args = mock_async_client.get.call_args
            assert call_args.kwargs["params"]["email"] == "alice@example.com"

    @pytest.mark.asyncio
    async def test_get_users_success(self, keycloak_config):
        """Test getting all users via Admin API"""
        client = KeycloakClient(keycloak_config)
        users_data = [
            {"id": "user-1", "username": "alice"},
            {"id": "user-2", "username": "bob"},
            {"id": "user-3", "username": "charlie"},
        ]
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = users_data
            mock_get_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.get = AsyncMock(return_value=mock_get_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            users = await client.get_users()
            assert len(users) == 3
            assert users[0]["username"] == "alice"


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.scim
@pytest.mark.xdist_group(name="keycloak_unit_tests")
class TestKeycloakSCIMGroupMethods:
    """Test SCIM 2.0 group management methods (TDD RED phase)"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_group_success(self, keycloak_config):
        """Test creating a group via Admin API"""
        client = KeycloakClient(keycloak_config)
        group_config = {"name": "engineering", "path": "/engineering", "attributes": {"description": ["Engineering team"]}}
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_post_response = MagicMock()
            mock_post_response.status_code = 201
            mock_post_response.headers = {"Location": "http://localhost:9082/admin/realms/test-realm/groups/group-uuid-789"}
            mock_post_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(side_effect=[mock_token_response, mock_post_response])
            mock_client.return_value.__aenter__.return_value = mock_async_client
            group_id = await client.create_group(group_config)
            assert group_id == "group-uuid-789"
            assert mock_async_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_create_group_http_error(self, keycloak_config):
        """Test create_group handles HTTP errors"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_post_response = MagicMock()
            mock_post_response.status_code = 409
            mock_post_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Conflict", request=MagicMock(), response=mock_post_response
            )
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(side_effect=[mock_token_response, mock_post_response])
            mock_client.return_value.__aenter__.return_value = mock_async_client
            with pytest.raises(httpx.HTTPStatusError):
                await client.create_group({"name": "duplicate-group"})

    @pytest.mark.asyncio
    async def test_get_group_success(self, keycloak_config):
        """Test getting group by ID via Admin API"""
        client = KeycloakClient(keycloak_config)
        group_data = {
            "id": "group-uuid-789",
            "name": "engineering",
            "path": "/engineering",
            "attributes": {"description": ["Engineering team"]},
            "subGroups": [],
        }
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = group_data
            mock_get_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.get = AsyncMock(return_value=mock_get_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            group = await client.get_group("group-uuid-789")
            assert group is not None
            assert group["id"] == "group-uuid-789"
            assert group["name"] == "engineering"

    @pytest.mark.asyncio
    async def test_get_group_not_found(self, keycloak_config):
        """Test get_group returns None for non-existent group"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_get_response = MagicMock()
            mock_get_response.status_code = 404
            mock_get_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=mock_get_response
            )
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.get = AsyncMock(return_value=mock_get_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            group = await client.get_group("nonexistent-group")
            assert group is None

    @pytest.mark.asyncio
    async def test_get_group_members_success(self, keycloak_config):
        """Test getting group members via Admin API"""
        client = KeycloakClient(keycloak_config)
        members_data = [
            {"id": "user-1", "username": "alice", "email": "alice@example.com"},
            {"id": "user-2", "username": "bob", "email": "bob@example.com"},
        ]
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = members_data
            mock_get_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.get = AsyncMock(return_value=mock_get_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            members = await client.get_group_members("group-uuid-789")
            assert len(members) == 2
            assert members[0]["username"] == "alice"
            assert members[1]["username"] == "bob"

    @pytest.mark.asyncio
    async def test_get_group_members_empty(self, keycloak_config):
        """Test getting members of empty group"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = []
            mock_get_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.get = AsyncMock(return_value=mock_get_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            members = await client.get_group_members("empty-group")
            assert members == []

    @pytest.mark.asyncio
    async def test_add_user_to_group_success(self, keycloak_config):
        """Test adding user to group via Admin API"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_put_response = MagicMock()
            mock_put_response.status_code = 204
            mock_put_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.put = AsyncMock(return_value=mock_put_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            await client.add_user_to_group("user-uuid-123", "group-uuid-789")
            mock_async_client.put.assert_called_once()
            call_args = mock_async_client.put.call_args
            assert "user-uuid-123" in call_args.args[0]
            assert "group-uuid-789" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_add_user_to_group_http_error(self, keycloak_config):
        """Test add_user_to_group handles HTTP errors"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_put_response = MagicMock()
            mock_put_response.status_code = 404
            mock_put_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=mock_put_response
            )
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.put = AsyncMock(return_value=mock_put_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            with pytest.raises(httpx.HTTPStatusError):
                await client.add_user_to_group("nonexistent-user", "nonexistent-group")


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.scim
@pytest.mark.xdist_group(name="keycloak_unit_tests")
class TestKeycloakSCIMClientMethods:
    """Test SCIM 2.0 client/service principal methods (TDD RED phase)"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_update_client_attributes_success(self, keycloak_config):
        """Test updating client attributes via Admin API"""
        client = KeycloakClient(keycloak_config)
        attributes = {"owner": get_user_id("alice"), "environment": "production"}
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = {"id": "client-uuid-456", "clientId": "test-service", "attributes": {}}
            mock_get_response.raise_for_status = MagicMock()
            mock_put_response = MagicMock()
            mock_put_response.status_code = 204
            mock_put_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.get = AsyncMock(return_value=mock_get_response)
            mock_async_client.put = AsyncMock(return_value=mock_put_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            await client.update_client_attributes("client-uuid-456", attributes)
            mock_async_client.put.assert_called_once()
            call_args = mock_async_client.put.call_args
            assert call_args.kwargs["json"]["attributes"] == attributes

    @pytest.mark.asyncio
    async def test_update_client_secret_success(self, keycloak_config):
        """Test updating client secret via Admin API"""
        client = KeycloakClient(keycloak_config)
        new_secret = "new-super-secret-123"
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_post_response = MagicMock()
            mock_post_response.status_code = 200
            mock_post_response.json.return_value = {"type": "secret", "value": new_secret}
            mock_post_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(side_effect=[mock_token_response, mock_post_response])
            mock_client.return_value.__aenter__.return_value = mock_async_client
            await client.update_client_secret("client-uuid-456", new_secret)
            assert mock_async_client.post.call_count == 2
            call_args = mock_async_client.post.call_args
            assert "client-secret" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_get_clients_success(self, keycloak_config):
        """Test getting all clients via Admin API"""
        client = KeycloakClient(keycloak_config)
        clients_data = [
            {"id": "client-1", "clientId": "service-a", "enabled": True},
            {"id": "client-2", "clientId": "service-b", "enabled": True},
        ]
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = clients_data
            mock_get_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.get = AsyncMock(return_value=mock_get_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            clients = await client.get_clients()
            assert len(clients) == 2
            assert clients[0]["clientId"] == "service-a"

    @pytest.mark.asyncio
    async def test_get_clients_with_query(self, keycloak_config):
        """Test getting clients with query filter"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = []
            mock_get_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.get = AsyncMock(return_value=mock_get_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            await client.get_clients(query={"clientId": "service-a"})
            call_args = mock_async_client.get.call_args
            assert "params" in call_args.kwargs
            assert call_args.kwargs["params"]["clientId"] == "service-a"

    @pytest.mark.asyncio
    async def test_get_client_success(self, keycloak_config):
        """Test getting client by ID via Admin API"""
        client = KeycloakClient(keycloak_config)
        client_data = {
            "id": "client-uuid-456",
            "clientId": "test-service",
            "enabled": True,
            "serviceAccountsEnabled": True,
            "attributes": {"owner": get_user_id("alice")},
        }
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = client_data
            mock_get_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.get = AsyncMock(return_value=mock_get_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            client_result = await client.get_client("client-uuid-456")
            assert client_result is not None
            assert client_result["id"] == "client-uuid-456"
            assert client_result["clientId"] == "test-service"

    @pytest.mark.asyncio
    async def test_get_client_not_found(self, keycloak_config):
        """Test get_client returns None for non-existent client"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_get_response = MagicMock()
            mock_get_response.status_code = 404
            mock_get_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=mock_get_response
            )
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(return_value=mock_token_response)
            mock_async_client.get = AsyncMock(return_value=mock_get_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            client_result = await client.get_client("nonexistent-client")
            assert client_result is None


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.xdist_group(name="keycloak_unit_tests")
class TestKeycloakTokenIssuance:
    """Test Keycloak token issuance methods for API key → JWT exchange (TDD RED phase)"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_issue_token_for_user_success(self, keycloak_config):
        """Test issuing JWT token for user (for API key exchange)"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_issue_response = MagicMock()
            mock_issue_response.json.return_value = {
                "access_token": "user-access-token-xyz",
                "refresh_token": "user-refresh-token-abc",
                "expires_in": 300,
                "token_type": "Bearer",
            }
            mock_issue_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(side_effect=[mock_token_response, mock_issue_response])
            mock_client.return_value.__aenter__.return_value = mock_async_client
            tokens = await client.issue_token_for_user("user-uuid-123")
            assert tokens["access_token"] == "user-access-token-xyz"
            assert tokens["refresh_token"] == "user-refresh-token-abc"
            assert tokens["expires_in"] == 300
            assert mock_async_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_issue_token_for_user_with_client_id(self, keycloak_config):
        """Test issuing token with specific client_id"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_issue_response = MagicMock()
            mock_issue_response.json.return_value = {"access_token": "user-token", "expires_in": 300}
            mock_issue_response.raise_for_status = MagicMock()
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(side_effect=[mock_token_response, mock_issue_response])
            mock_client.return_value.__aenter__.return_value = mock_async_client
            tokens = await client.issue_token_for_user(
                "user-uuid-123", requested_token_type="urn:ietf:params:oauth:token-type:access_token"
            )
            assert tokens["access_token"] == "user-token"
            call_args = mock_async_client.post.call_args_list[1]
            assert "data" in call_args.kwargs
            assert call_args.kwargs["data"]["requested_token_type"] == "urn:ietf:params:oauth:token-type:access_token"

    @pytest.mark.asyncio
    async def test_issue_token_for_user_http_error(self, keycloak_config):
        """Test issue_token_for_user handles HTTP errors"""
        client = KeycloakClient(keycloak_config)
        with patch("httpx.AsyncClient") as mock_client:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "admin-token-123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_issue_response = MagicMock()
            mock_issue_response.status_code = 403
            mock_issue_response.text = "Forbidden: Impersonation not allowed"
            mock_issue_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Forbidden", request=MagicMock(), response=mock_issue_response
            )
            mock_async_client = configured_async_mock(return_value=None)
            mock_async_client.post = AsyncMock(side_effect=[mock_token_response, mock_issue_response])
            mock_client.return_value.__aenter__.return_value = mock_async_client
            with pytest.raises(httpx.HTTPStatusError):
                await client.issue_token_for_user("user-uuid-123")
