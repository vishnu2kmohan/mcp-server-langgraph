"""
TDD tests for Keycloak login metrics instrumentation.

Verifies that record_login_attempt() is called during authenticate_user().
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.metrics
@pytest.mark.xdist_group(name="keycloak_login_metrics")
class TestKeycloakLoginMetrics:
    """Test Keycloak login metrics instrumentation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_authenticate_user_records_success_metrics(self) -> None:
        """Verify successful login records metrics with correct attributes."""
        from mcp_server_langgraph.auth.keycloak import KeycloakClient, KeycloakConfig

        config = KeycloakConfig(
            server_url="http://localhost:8180",
            realm="test",
            client_id="test-client",
            client_secret="test-secret",
        )
        client = KeycloakClient(config)

        # Mock successful token response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "test-token",
            "refresh_token": "test-refresh",
            "expires_in": 300,
        }
        mock_response.raise_for_status = MagicMock()

        with (
            patch("httpx.AsyncClient") as mock_http,
            patch("mcp_server_langgraph.auth.keycloak.record_login_attempt") as mock_record,
        ):
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await client.authenticate_user("testuser", "testpass")

            # Verify login metrics were recorded
            mock_record.assert_called_once()
            call_args = mock_record.call_args

            # Check provider is "keycloak"
            assert call_args[0][0] == "keycloak" or call_args.kwargs.get("provider") == "keycloak"
            # Check result is "success"
            assert call_args[0][1] == "success" or call_args.kwargs.get("result") == "success"
            # Check duration is a positive number
            duration = call_args[0][2] if len(call_args[0]) > 2 else call_args.kwargs.get("duration_ms")
            assert isinstance(duration, float)
            assert duration >= 0

            # Verify tokens were returned
            assert result["access_token"] == "test-token"

    @pytest.mark.asyncio
    async def test_authenticate_user_records_failure_metrics(self) -> None:
        """Verify failed login records metrics with failure reason."""
        from mcp_server_langgraph.auth.keycloak import KeycloakClient, KeycloakConfig

        config = KeycloakConfig(
            server_url="http://localhost:8180",
            realm="test",
            client_id="test-client",
        )
        client = KeycloakClient(config)

        # Mock 401 error response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"

        with (
            patch("httpx.AsyncClient") as mock_http,
            patch("mcp_server_langgraph.auth.keycloak.record_login_attempt") as mock_record,
        ):
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=mock_response)
            )

            with pytest.raises(httpx.HTTPStatusError):
                await client.authenticate_user("testuser", "wrongpass")

            # Verify failure metrics were recorded
            mock_record.assert_called_once()
            call_args = mock_record.call_args

            # Check provider is "keycloak"
            assert call_args[0][0] == "keycloak" or call_args.kwargs.get("provider") == "keycloak"
            # Check result is "invalid_credentials"
            assert call_args[0][1] == "invalid_credentials" or call_args.kwargs.get("result") == "invalid_credentials"

    @pytest.mark.asyncio
    async def test_authenticate_user_records_error_metrics_on_http_error(self) -> None:
        """Verify HTTP errors record metrics with error reason."""
        from mcp_server_langgraph.auth.keycloak import KeycloakClient, KeycloakConfig

        config = KeycloakConfig(
            server_url="http://localhost:8180",
            realm="test",
            client_id="test-client",
        )
        client = KeycloakClient(config)

        with (
            patch("httpx.AsyncClient") as mock_http,
            patch("mcp_server_langgraph.auth.keycloak.record_login_attempt") as mock_record,
        ):
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )

            with pytest.raises(httpx.HTTPError):
                await client.authenticate_user("testuser", "testpass")

            # Verify error metrics were recorded
            mock_record.assert_called_once()
            call_args = mock_record.call_args

            # Check result is "error"
            assert call_args[0][1] == "error" or call_args.kwargs.get("result") == "error"
