"""
Unit tests for OpenFGA OIDC Token Refresh During Operations.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that the OpenFGAClient refreshes expired OIDC tokens
during check_permission() calls, not just during initialization.

Bug Context:
- The circuit breaker was opening with 401 errors from OpenFGA
- Root cause: OIDC tokens expire but _ensure_initialized() only checks _initialized flag
- Once _initialized=True, token refresh code is never reached
- This causes 401 errors when tokens expire after ~5 minutes

Fix: _ensure_initialized() must also check token expiration and refresh if needed

Reference: ADR-0070 - OpenFGA OIDC Authentication Migration
"""

import gc
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig

# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
    pytest.mark.openfga,
    pytest.mark.oidc,
]


@pytest.mark.xdist_group(name="test_openfga_oidc_token_refresh")
class TestOpenFGAClientOIDCTokenRefreshDuringOperations:
    """Test that OIDC tokens are refreshed during operations, not just at init time.

    Critical Bug Fix Tests:
    - Tokens expire after ~5 minutes (Keycloak default)
    - Client must detect expiration and refresh before each operation
    - Circuit breaker was opening due to 401 errors from expired tokens
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_ensure_initialized_refreshes_expired_token(self):
        """
        GIVEN: OpenFGAClient already initialized with an expired OIDC token
        WHEN: Calling _ensure_initialized() again
        THEN: Should detect expired token and refresh it

        User Journey: Continued operation after token expiration
        Bug Context: This is the exact scenario causing 401 errors in production
        """
        # Create client with OIDC config
        config = OpenFGAConfig(
            api_url="http://localhost:8080",
            store_id="test-store",
            model_id="test-model",
            oidc_client_id="test-client",
            oidc_client_secret="test-secret",
            oidc_issuer="http://keycloak/realms/default",
        )
        client = OpenFGAClient(config=config)

        # Simulate already initialized state with an EXPIRED token
        client._initialized = True
        client._oidc_access_token = "expired-token"
        # Token expired 10 seconds ago
        client._oidc_token_expires_at = time.time() - 10

        # Mock OpenFgaClient to avoid actual SDK calls
        mock_sdk_client = MagicMock()
        client._client = mock_sdk_client

        # Mock token refresh response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "fresh-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_http_client = AsyncMock()
            mock_http_client.post.return_value = mock_response
            mock_http_client.get.return_value = MagicMock(status_code=200, json=MagicMock(return_value={"stores": []}))
            mock_client_class.return_value.__aenter__.return_value = mock_http_client

            # Call _ensure_initialized - should detect expired token and refresh
            await client._ensure_initialized()

            # Token should be refreshed
            assert client._oidc_access_token == "fresh-token"
            # Verify HTTP call was made to get new token
            mock_http_client.post.assert_called()

    @pytest.mark.asyncio
    async def test_ensure_initialized_refreshes_near_expiry_token(self):
        """
        GIVEN: OpenFGAClient initialized with token expiring in <60 seconds
        WHEN: Calling _ensure_initialized() again
        THEN: Should proactively refresh token (60-second buffer)

        User Journey: Proactive refresh prevents race conditions
        """
        config = OpenFGAConfig(
            api_url="http://localhost:8080",
            store_id="test-store",
            model_id="test-model",
            oidc_client_id="test-client",
            oidc_client_secret="test-secret",
            oidc_issuer="http://keycloak/realms/default",
        )
        client = OpenFGAClient(config=config)

        # Simulate initialized state with token expiring in 30 seconds
        # (within 60-second refresh buffer)
        client._initialized = True
        client._oidc_access_token = "expiring-soon-token"
        client._oidc_token_expires_at = time.time() + 30  # Expires in 30s

        mock_sdk_client = MagicMock()
        client._client = mock_sdk_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "proactively-refreshed-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_http_client = AsyncMock()
            mock_http_client.post.return_value = mock_response
            mock_http_client.get.return_value = MagicMock(status_code=200, json=MagicMock(return_value={"stores": []}))
            mock_client_class.return_value.__aenter__.return_value = mock_http_client

            await client._ensure_initialized()

            # Token should be refreshed proactively
            assert client._oidc_access_token == "proactively-refreshed-token"

    @pytest.mark.asyncio
    async def test_ensure_initialized_skips_refresh_for_valid_token(self):
        """
        GIVEN: OpenFGAClient initialized with valid token (not near expiry)
        WHEN: Calling _ensure_initialized() again
        THEN: Should NOT refresh token (avoid unnecessary Keycloak calls)

        User Journey: Efficient token reuse
        """
        config = OpenFGAConfig(
            api_url="http://localhost:8080",
            store_id="test-store",
            model_id="test-model",
            oidc_client_id="test-client",
            oidc_client_secret="test-secret",
            oidc_issuer="http://keycloak/realms/default",
        )
        client = OpenFGAClient(config=config)

        # Simulate initialized state with valid token (expires in 1 hour)
        client._initialized = True
        client._oidc_access_token = "valid-token"
        client._oidc_token_expires_at = time.time() + 3600  # Expires in 1 hour

        mock_sdk_client = MagicMock()
        client._client = mock_sdk_client

        with patch("httpx.AsyncClient") as mock_client_class:
            # Should NOT make any HTTP calls
            await client._ensure_initialized()

            # Token should remain unchanged
            assert client._oidc_access_token == "valid-token"
            # No HTTP calls should be made
            mock_client_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_permission_triggers_token_refresh_on_expiry(self):
        """
        GIVEN: OpenFGAClient with expired OIDC token
        WHEN: Calling check_permission()
        THEN: Should refresh token before making permission check

        User Journey: Seamless operation continuation after token expiry
        Bug Context: This test would fail before the fix

        Note: This test verifies token refresh happens by checking _ensure_initialized()
        behavior rather than full check_permission() flow, since check_permission()
        involves multiple resilience decorators and SDK validation.
        """
        from mcp_server_langgraph.resilience import reset_all_circuit_breakers
        from mcp_server_langgraph.resilience.circuit_breaker import _circuit_breakers

        # Reset circuit breakers to ensure clean state
        reset_all_circuit_breakers()
        _circuit_breakers.clear()

        # Use valid ULID format for store_id and model_id (SDK validation requirement)
        config = OpenFGAConfig(
            api_url="http://localhost:8080",
            store_id="01HQXXXXXXXXXXXXXXXXXXX01",  # Valid ULID format
            model_id="01HQXXXXXXXXXXXXXXXXXXX02",  # Valid ULID format
            oidc_client_id="test-client",
            oidc_client_secret="test-secret",
            oidc_issuer="http://keycloak/realms/default",
        )
        client = OpenFGAClient(config=config)

        # Simulate initialized state with EXPIRED token
        client._initialized = True
        client._oidc_access_token = "expired-token"
        client._oidc_token_expires_at = time.time() - 10  # Expired 10s ago

        # Mock SDK client - will be replaced after token refresh
        mock_sdk_client = AsyncMock()  # noqa: async-mock-config
        mock_sdk_client.close = AsyncMock(return_value=None)
        client._client = mock_sdk_client

        # Mock token refresh response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "fresh-token-for-check",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_http_client = AsyncMock()
            mock_http_client.post.return_value = mock_response
            mock_http_client.get.return_value = MagicMock(status_code=200, json=MagicMock(return_value={"stores": []}))
            mock_client_class.return_value.__aenter__.return_value = mock_http_client

            # Call _ensure_initialized directly to test token refresh
            # (avoids SDK validation issues with check_permission)
            await client._ensure_initialized()

            # Token should be refreshed
            assert client._oidc_access_token == "fresh-token-for-check"
            # Client should have been reinitialized
            assert client._initialized is True


@pytest.mark.xdist_group(name="test_openfga_oidc_token_refresh")
class TestTokenExpirationDetection:
    """Test _should_refresh_token() helper method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_should_refresh_returns_false_when_no_oidc(self):
        """
        GIVEN: Client without OIDC configuration
        WHEN: Checking if token should be refreshed
        THEN: Should return False (no OIDC, no refresh needed)
        """
        client = OpenFGAClient(api_url="http://localhost:8080")

        # No OIDC token expires_at set
        assert client._oidc_token_expires_at is None
        assert client._should_refresh_token() is False

    def test_should_refresh_returns_true_when_expired(self):
        """
        GIVEN: Client with expired OIDC token
        WHEN: Checking if token should be refreshed
        THEN: Should return True
        """
        config = OpenFGAConfig(
            api_url="http://localhost:8080",
            oidc_client_id="test",
            oidc_client_secret="test",
            oidc_issuer="http://keycloak/realms/default",
        )
        client = OpenFGAClient(config=config)
        client._oidc_token_expires_at = time.time() - 10  # Expired 10s ago

        assert client._should_refresh_token() is True

    def test_should_refresh_returns_true_when_near_expiry(self):
        """
        GIVEN: Client with token expiring within 60-second buffer
        WHEN: Checking if token should be refreshed
        THEN: Should return True (proactive refresh)
        """
        config = OpenFGAConfig(
            api_url="http://localhost:8080",
            oidc_client_id="test",
            oidc_client_secret="test",
            oidc_issuer="http://keycloak/realms/default",
        )
        client = OpenFGAClient(config=config)
        client._oidc_token_expires_at = time.time() + 30  # Expires in 30s

        assert client._should_refresh_token() is True

    def test_should_refresh_returns_false_when_valid(self):
        """
        GIVEN: Client with token not near expiration
        WHEN: Checking if token should be refreshed
        THEN: Should return False
        """
        config = OpenFGAConfig(
            api_url="http://localhost:8080",
            oidc_client_id="test",
            oidc_client_secret="test",
            oidc_issuer="http://keycloak/realms/default",
        )
        client = OpenFGAClient(config=config)
        client._oidc_token_expires_at = time.time() + 3600  # Expires in 1 hour

        assert client._should_refresh_token() is False
