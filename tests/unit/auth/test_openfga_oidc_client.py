"""
Unit tests for OpenFGA OIDC Client.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that:
1. OpenFGAClient reads OIDC configuration from environment variables
2. OIDC token acquisition implements OAuth 2.0 client credentials grant correctly
3. Token caching works as expected (30-second buffer before expiration)
4. Token refresh happens automatically when cached token is near expiration
5. Error handling for failed token acquisition
6. Fallback to preshared key when OIDC is not configured

Reference: RFC 6749 Section 4.4 - Client Credentials Grant
"""

import gc
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig
from mcp_server_langgraph.core.exceptions import OpenFGAError

# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
    pytest.mark.openfga,
    pytest.mark.oidc,
]


@pytest.mark.xdist_group(name="test_openfga_oidc_client")
class TestOpenFGAConfigOIDC:
    """Test OpenFGAConfig with OIDC fields."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_openfga_config_accepts_oidc_fields(self):
        """
        GIVEN: OIDC configuration parameters
        WHEN: Creating OpenFGAConfig
        THEN: Should accept and store OIDC fields

        User Journey: Configuration validation for OIDC setup
        """
        config = OpenFGAConfig(
            api_url="http://localhost:8080",
            store_id="test-store",
            model_id="test-model",
            oidc_client_id="openfga-server",
            oidc_client_secret="test-secret",
            oidc_issuer="http://keycloak:8080/authn/realms/default",
        )

        assert config.oidc_client_id == "openfga-server"
        assert config.oidc_client_secret == "test-secret"
        assert config.oidc_issuer == "http://keycloak:8080/authn/realms/default"

    def test_openfga_config_preshared_key_marked_deprecated(self):
        """
        GIVEN: OpenFGAConfig with preshared key
        WHEN: Checking field description
        THEN: Should indicate deprecation in favor of OIDC

        User Journey: Migration guidance from preshared key to OIDC
        """
        # Verify field description in schema
        schema = OpenFGAConfig.model_json_schema()
        preshared_field = schema["properties"]["preshared_key"]

        assert "DEPRECATED" in preshared_field["description"]
        assert "OIDC" in preshared_field["description"]


@pytest.mark.xdist_group(name="test_openfga_oidc_client")
class TestOpenFGAClientOIDCInitialization:
    """Test OpenFGAClient initialization with OIDC config."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_client_reads_oidc_from_config(self):
        """
        GIVEN: OpenFGAConfig with OIDC credentials
        WHEN: Creating OpenFGAClient
        THEN: Should store OIDC configuration

        User Journey: Programmatic OIDC configuration
        """
        config = OpenFGAConfig(
            api_url="http://localhost:8080",
            oidc_client_id="test-client",
            oidc_client_secret="test-secret",
            oidc_issuer="http://keycloak/realms/default",
        )

        client = OpenFGAClient(config=config)

        assert client.oidc_client_id == "test-client"
        assert client.oidc_client_secret == "test-secret"
        assert client.oidc_issuer == "http://keycloak/realms/default"

    def test_client_reads_oidc_from_parameters(self):
        """
        GIVEN: OIDC parameters passed to constructor
        WHEN: Creating OpenFGAClient
        THEN: Should construct config and store OIDC settings

        User Journey: Direct parameter-based configuration
        """
        client = OpenFGAClient(
            api_url="http://localhost:8080",
            oidc_client_id="test-client",
            oidc_client_secret="test-secret",
            oidc_issuer="http://keycloak/realms/default",
        )

        assert client.oidc_client_id == "test-client"
        assert client.oidc_client_secret == "test-secret"
        assert client.oidc_issuer == "http://keycloak/realms/default"

    @patch.dict(
        "os.environ",
        {
            "OPENFGA_OIDC_CLIENT_ID": "env-client",
            "OPENFGA_OIDC_CLIENT_SECRET": "env-secret",
            "KEYCLOAK_SERVER_URL": "http://keycloak/authn",
            "KEYCLOAK_REALM": "default",
        },
    )
    def test_client_reads_oidc_from_environment_variables(self):
        """
        GIVEN: OIDC configuration in environment variables
        WHEN: Creating OpenFGAClient without explicit config
        THEN: Should read from environment and construct issuer URL

        User Journey: 12-factor config from environment
        """
        client = OpenFGAClient(api_url="http://localhost:8080")

        assert client.oidc_client_id == "env-client"
        assert client.oidc_client_secret == "env-secret"
        # Issuer should be auto-constructed from KEYCLOAK_SERVER_URL + realm
        assert client.oidc_issuer == "http://keycloak/authn/realms/default"

    def test_client_initializes_token_cache_as_none(self):
        """
        GIVEN: New OpenFGAClient with OIDC config
        WHEN: Checking initial state
        THEN: Token cache should be empty

        User Journey: Clean initial state before first token acquisition
        """
        client = OpenFGAClient(
            api_url="http://localhost:8080",
            oidc_client_id="test-client",
            oidc_client_secret="test-secret",
            oidc_issuer="http://keycloak/realms/default",
        )

        assert client._oidc_access_token is None
        assert client._oidc_token_expires_at is None


@pytest.mark.xdist_group(name="test_openfga_oidc_client")
class TestOpenFGAClientOIDCTokenAcquisition:
    """Test OIDC token acquisition logic."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_oidc_token_returns_none_when_not_configured(self):
        """
        GIVEN: OpenFGAClient without OIDC configuration
        WHEN: Calling _get_oidc_access_token()
        THEN: Should return None without making HTTP requests

        User Journey: Graceful degradation when OIDC not configured
        """
        client = OpenFGAClient(api_url="http://localhost:8080")

        token = await client._get_oidc_access_token()

        assert token is None

    @pytest.mark.asyncio
    async def test_get_oidc_token_implements_client_credentials_grant(self):
        """
        GIVEN: OpenFGAClient with OIDC config
        WHEN: Requesting access token
        THEN: Should use OAuth 2.0 client credentials grant (RFC 6749 4.4)

        User Journey: Standard OAuth 2.0 token acquisition
        """
        client = OpenFGAClient(
            api_url="http://localhost:8080",
            oidc_client_id="test-client",
            oidc_client_secret="test-secret",
            oidc_issuer="http://keycloak/realms/default",
        )

        # Mock httpx.AsyncClient.post
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "mock-access-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            token = await client._get_oidc_access_token()

            # Verify correct token endpoint URL
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "http://keycloak/realms/default/protocol/openid-connect/token"

            # Verify client credentials grant parameters
            data = call_args[1]["data"]
            assert data["grant_type"] == "client_credentials"
            assert data["client_id"] == "test-client"
            assert data["client_secret"] == "test-secret"

            # Verify token returned
            assert token == "mock-access-token"

    @pytest.mark.asyncio
    async def test_get_oidc_token_caches_token_and_expiry(self):
        """
        GIVEN: Successful token acquisition
        WHEN: Token is obtained
        THEN: Should cache token and expiration time

        User Journey: Efficient token reuse reduces Keycloak load
        """
        client = OpenFGAClient(
            api_url="http://localhost:8080",
            oidc_client_id="test-client",
            oidc_client_secret="test-secret",
            oidc_issuer="http://keycloak/realms/default",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "cached-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            current_time = time.time()
            with patch("time.time", return_value=current_time):
                _token = await client._get_oidc_access_token()

            # Verify token cached (_token captured for debugging, main assertion is on client state)
            assert client._oidc_access_token == "cached-token"
            # Verify expiry cached (current_time + expires_in)
            assert client._oidc_token_expires_at == current_time + 3600

    @pytest.mark.asyncio
    async def test_get_oidc_token_reuses_cached_token(self):
        """
        GIVEN: Valid cached token (not near expiration)
        WHEN: Requesting token again
        THEN: Should return cached token without making HTTP request

        User Journey: Token reuse prevents unnecessary Keycloak calls
        """
        client = OpenFGAClient(
            api_url="http://localhost:8080",
            oidc_client_id="test-client",
            oidc_client_secret="test-secret",
            oidc_issuer="http://keycloak/realms/default",
        )

        # Set cached token that won't expire for another hour
        client._oidc_access_token = "cached-token"
        client._oidc_token_expires_at = time.time() + 3600

        with patch("httpx.AsyncClient") as mock_client_class:
            token = await client._get_oidc_access_token()

            # Should NOT make HTTP request (client not instantiated)
            mock_client_class.assert_not_called()

            # Should return cached token
            assert token == "cached-token"

    @pytest.mark.asyncio
    async def test_get_oidc_token_refreshes_near_expiry(self):
        """
        GIVEN: Cached token that expires in less than 30 seconds
        WHEN: Requesting token
        THEN: Should refresh token (30-second buffer for clock skew)

        User Journey: Proactive refresh prevents authentication failures
        """
        client = OpenFGAClient(
            api_url="http://localhost:8080",
            oidc_client_id="test-client",
            oidc_client_secret="test-secret",
            oidc_issuer="http://keycloak/realms/default",
        )

        # Set cached token that expires in 20 seconds (within 30s buffer)
        client._oidc_access_token = "old-token"
        client._oidc_token_expires_at = time.time() + 20

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "refreshed-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            token = await client._get_oidc_access_token()

            # Should make HTTP request to refresh
            mock_client.post.assert_called_once()

            # Should return new token
            assert token == "refreshed-token"
            assert client._oidc_access_token == "refreshed-token"

    @pytest.mark.asyncio
    async def test_get_oidc_token_raises_error_on_http_failure(self):
        """
        GIVEN: Keycloak returns HTTP error
        WHEN: Requesting token
        THEN: Should raise OpenFGAError with details

        User Journey: Clear error messaging for authentication failures
        """
        client = OpenFGAClient(
            api_url="http://localhost:8080",
            oidc_client_id="test-client",
            oidc_client_secret="test-secret",
            oidc_issuer="http://keycloak/realms/default",
        )

        # Mock HTTP error response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid client credentials"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=MagicMock(), response=mock_response
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(OpenFGAError) as exc_info:
                await client._get_oidc_access_token()

            assert "Failed to obtain OIDC access token: HTTP 401" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_oidc_token_raises_error_when_no_access_token_in_response(self):
        """
        GIVEN: Keycloak response missing access_token field
        WHEN: Processing token response
        THEN: Should raise OpenFGAError

        User Journey: Validation of token endpoint response
        """
        client = OpenFGAClient(
            api_url="http://localhost:8080",
            oidc_client_id="test-client",
            oidc_client_secret="test-secret",
            oidc_issuer="http://keycloak/realms/default",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            # Missing access_token field
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(OpenFGAError) as exc_info:
                await client._get_oidc_access_token()

            assert "No access_token in Keycloak token response" in str(exc_info.value)


@pytest.mark.xdist_group(name="test_openfga_oidc_client")
class TestOpenFGAClientAuthenticationPriority:
    """Test authentication method priority (OIDC > preshared key > none)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_prefers_oidc_over_preshared_key(self):
        """
        GIVEN: Both OIDC and preshared key configured
        WHEN: Initializing OpenFGA client
        THEN: Should use OIDC authentication

        User Journey: Migration path - OIDC takes precedence
        """
        client = OpenFGAClient(
            api_url="http://localhost:8080",
            store_id="test-store",
            model_id="test-model",
            oidc_client_id="test-client",
            oidc_client_secret="test-secret",
            oidc_issuer="http://keycloak/realms/default",
            preshared_key="should-not-be-used",
        )

        # Mock OIDC token acquisition
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "oidc-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await client._ensure_initialized()

            # Should have obtained OIDC token
            assert client._oidc_access_token == "oidc-token"

            # Verify client was initialized with OIDC credentials
            # Note: OpenFGA SDK client doesn't expose credentials directly, but we can verify
            # the token was cached, which means OIDC was used
            assert client._initialized is True
            assert client._oidc_token_expires_at is not None
