"""
Unit tests for Keycloak client resilience patterns.

TDD Cycle: RED -> GREEN -> REFACTOR

These tests verify that:
1. TokenValidator retries JWKS fetch on transient connection failures
2. Circuit breaker trips after threshold failures
3. Connection pooling uses shared HTTP client manager
4. Timeout enforcement works correctly

Reference: ADR-0026 - Resilience Patterns
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_langgraph.auth.keycloak import KeycloakConfig, TokenValidator

# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
    pytest.mark.keycloak,
    pytest.mark.resilience,
]


@pytest.fixture
def keycloak_config():
    """Sample Keycloak configuration for resilience tests."""
    return KeycloakConfig(
        server_url="http://keycloak:8080",
        realm="test-realm",
        client_id="test-client",
        client_secret="test-secret",
        verify_ssl=False,
        timeout=10,
    )


@pytest.fixture
def mock_jwks_response():
    """Mock successful JWKS response."""
    return {
        "keys": [
            {
                "kid": "test-key-id",
                "kty": "RSA",
                "alg": "RS256",
                "use": "sig",
                "n": "test-n-value",
                "e": "AQAB",
            }
        ]
    }


@pytest.mark.xdist_group(name="keycloak_resilience_tests")
class TestTokenValidatorRetryLogic:
    """Test retry logic for JWKS fetch operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_jwks_retries_on_connect_error(self, keycloak_config, mock_jwks_response):
        """
        GIVEN: TokenValidator configured with Keycloak
        WHEN: JWKS fetch fails twice with connection error, then succeeds
        THEN: Should retry and eventually return JWKS

        User Journey: Startup resilience when Keycloak is still initializing
        """
        validator = TokenValidator(keycloak_config)

        # Track call attempts
        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("Connection refused")
            # Third attempt succeeds
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = mock_jwks_response
            response.raise_for_status = MagicMock()
            return response

        with patch("mcp_server_langgraph.auth.keycloak.get_http_client_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_manager.get_client = AsyncMock(return_value=mock_client)
            mock_get_manager.return_value = mock_manager

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                jwks = await validator.get_jwks()

                # Should have made 3 attempts
                assert call_count == 3

                # Should have slept between retries
                assert mock_sleep.call_count == 2

                # Should return JWKS from successful attempt
                assert jwks == mock_jwks_response

    @pytest.mark.asyncio
    async def test_get_jwks_raises_after_max_retries(self, keycloak_config):
        """
        GIVEN: TokenValidator configured with Keycloak
        WHEN: All JWKS fetch attempts fail with connection error
        THEN: Should raise after exhausting retries

        User Journey: Clear failure when Keycloak is truly unreachable
        """
        validator = TokenValidator(keycloak_config)

        async def mock_get_always_fails(*args, **kwargs):
            raise httpx.ConnectError("Connection refused")

        with patch("mcp_server_langgraph.auth.keycloak.get_http_client_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_client = AsyncMock()
            mock_client.get = mock_get_always_fails
            mock_manager.get_client = AsyncMock(return_value=mock_client)
            mock_get_manager.return_value = mock_manager

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(httpx.ConnectError):
                    await validator.get_jwks()

    @pytest.mark.asyncio
    async def test_get_jwks_does_not_retry_on_http_error(self, keycloak_config):
        """
        GIVEN: TokenValidator configured with Keycloak
        WHEN: JWKS endpoint returns HTTP 404
        THEN: Should NOT retry (HTTP errors are not transient)

        User Journey: Fast failure for configuration errors
        """
        validator = TokenValidator(keycloak_config)

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            response = MagicMock()
            response.status_code = 404
            response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404 Not Found", request=MagicMock(), response=response
            )
            return response

        with patch("mcp_server_langgraph.auth.keycloak.get_http_client_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_manager.get_client = AsyncMock(return_value=mock_client)
            mock_get_manager.return_value = mock_manager

            with pytest.raises(httpx.HTTPStatusError):
                await validator.get_jwks()

            # Should only attempt once (no retry for HTTP errors)
            assert call_count == 1


@pytest.mark.xdist_group(name="keycloak_resilience_tests")
class TestTokenValidatorCircuitBreaker:
    """Test circuit breaker for Keycloak operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_threshold_failures(self, keycloak_config):
        """
        GIVEN: TokenValidator with circuit breaker
        WHEN: JWKS fetch fails repeatedly (exceeds threshold)
        THEN: Circuit breaker should open and fail fast

        User Journey: Prevent cascade failures when Keycloak is down
        """
        import pybreaker
        from mcp_server_langgraph.resilience.circuit_breaker import (
            reset_circuit_breaker,
        )

        # Reset circuit breaker state before test
        reset_circuit_breaker("keycloak")

        validator = TokenValidator(keycloak_config)

        async def mock_get_always_fails(*args, **kwargs):
            raise httpx.ConnectError("Connection refused")

        with patch("mcp_server_langgraph.auth.keycloak.get_http_client_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_client = AsyncMock()
            mock_client.get = mock_get_always_fails
            mock_manager.get_client = AsyncMock(return_value=mock_client)
            mock_get_manager.return_value = mock_manager

            with patch("asyncio.sleep", new_callable=AsyncMock):
                # Trigger enough failures to open the circuit breaker
                # Each get_jwks() call exhausts 3 retries before failing
                # Circuit breaker fail_max=5, so we need 5 failures to trip it
                # After 5 failed calls, the circuit should be open
                for _ in range(6):
                    try:
                        await validator.get_jwks()
                    except (httpx.ConnectError, pybreaker.CircuitBreakerError):
                        pass

                # Next call should fail fast with CircuitBreakerError
                with pytest.raises(pybreaker.CircuitBreakerError):
                    await validator.get_jwks()


@pytest.mark.xdist_group(name="keycloak_resilience_tests")
class TestTokenValidatorConnectionPooling:
    """Test that TokenValidator uses shared HTTP client."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_uses_shared_http_client_manager(self, keycloak_config, mock_jwks_response):
        """
        GIVEN: TokenValidator configured with Keycloak
        WHEN: Making multiple JWKS requests
        THEN: Should reuse the shared HTTP client (not create new ones)

        User Journey: Connection pooling for performance
        """
        validator = TokenValidator(keycloak_config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_jwks_response
        mock_response.raise_for_status = MagicMock()

        with patch("mcp_server_langgraph.auth.keycloak.get_http_client_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_manager.get_client = AsyncMock(return_value=mock_client)
            mock_get_manager.return_value = mock_manager

            # Make multiple requests
            await validator.get_jwks(force_refresh=True)
            await validator.get_jwks(force_refresh=True)
            await validator.get_jwks(force_refresh=True)

            # Should have called get_client() to get shared client
            assert mock_manager.get_client.call_count == 3


@pytest.mark.xdist_group(name="keycloak_resilience_tests")
class TestTokenValidatorTimeout:
    """Test timeout enforcement for Keycloak operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_jwks_fetch_respects_timeout(self, keycloak_config):
        """
        GIVEN: TokenValidator with timeout configuration
        WHEN: JWKS fetch takes too long
        THEN: Should timeout and raise appropriate error

        User Journey: Prevent hanging on slow Keycloak

        Note: Timeout is enforced by the HTTP client manager's timeout settings.
        The HttpClientManager uses connect=5s, read=30s, write=30s by default.
        This test verifies that httpx.TimeoutException is handled properly.
        """
        validator = TokenValidator(keycloak_config)

        async def mock_slow_get(*args, **kwargs):
            # Simulate timeout by raising TimeoutException
            raise httpx.TimeoutException("Request timed out")

        with patch("mcp_server_langgraph.auth.keycloak.get_http_client_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_client = AsyncMock()
            mock_client.get = mock_slow_get
            mock_manager.get_client = AsyncMock(return_value=mock_client)
            mock_get_manager.return_value = mock_manager

            # Should timeout and raise httpx.TimeoutException
            # The timeout is enforced by the HTTP client, not by asyncio.wait_for
            with pytest.raises(httpx.TimeoutException):
                await validator.get_jwks()
