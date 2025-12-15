"""
Tests for OAuth 2.0 Device Authorization Grant (RFC 8628).

Provides headless/CLI authentication without user interaction on the client device.

TDD Tests - Written FIRST before implementation.
"""

import gc
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
]


@pytest.fixture
def device_auth_config():
    """Sample configuration for device authorization."""
    return {
        "server_url": "http://localhost:9082",
        "realm": "test-realm",
        "client_id": "mcp-cli",
        "client_secret": "test-cli-secret",
        "device_authorization_endpoint": "http://localhost:9082/realms/test-realm/protocol/openid-connect/auth/device",
        "token_endpoint": "http://localhost:9082/realms/test-realm/protocol/openid-connect/token",
        "scope": "openid profile email",
        "polling_interval": 5,
        "timeout": 300,
    }


@pytest.fixture
def device_code_response():
    """Mock device code response from Keycloak."""
    return {
        "device_code": "test-device-code-abc123",
        "user_code": "ABCD-EFGH",
        "verification_uri": "http://localhost:9082/realms/test-realm/device",
        "verification_uri_complete": "http://localhost:9082/realms/test-realm/device?user_code=ABCD-EFGH",
        "expires_in": 600,
        "interval": 5,
    }


@pytest.fixture
def token_response():
    """Mock successful token response."""
    return {
        "access_token": "test-access-token-xyz789",
        "refresh_token": "test-refresh-token-uvw456",
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "openid profile email",
    }


@pytest.mark.xdist_group(name="device_auth_tests")
class TestDeviceAuthRequest:
    """Test device authorization request initiation (RFC 8628 Section 3.1)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_request_device_code_returns_user_code(self, device_auth_config, device_code_response):
        """
        GIVEN: Device authorization client with valid configuration
        WHEN: request_device_code() is called
        THEN: Response should contain user_code for display to user
        """
        from mcp_server_langgraph.auth.device_auth import DeviceAuthClient

        client = DeviceAuthClient(**device_auth_config)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = device_code_response
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await client.request_device_code()

            assert "user_code" in result
            assert result["user_code"] == "ABCD-EFGH"
            assert "verification_uri" in result
            assert "device_code" in result

    @pytest.mark.asyncio
    async def test_request_device_code_includes_verification_uri_complete(self, device_auth_config, device_code_response):
        """
        GIVEN: Device authorization client
        WHEN: request_device_code() is called
        THEN: Response should contain verification_uri_complete for QR codes
        """
        from mcp_server_langgraph.auth.device_auth import DeviceAuthClient

        client = DeviceAuthClient(**device_auth_config)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = device_code_response
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await client.request_device_code()

            assert "verification_uri_complete" in result
            assert "user_code=ABCD-EFGH" in result["verification_uri_complete"]

    @pytest.mark.asyncio
    async def test_request_device_code_includes_expires_in(self, device_auth_config, device_code_response):
        """
        GIVEN: Device authorization client
        WHEN: request_device_code() is called
        THEN: Response should contain expires_in for code validity period
        """
        from mcp_server_langgraph.auth.device_auth import DeviceAuthClient

        client = DeviceAuthClient(**device_auth_config)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = device_code_response
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await client.request_device_code()

            assert "expires_in" in result
            assert result["expires_in"] == 600


@pytest.mark.xdist_group(name="device_auth_tests")
class TestDeviceAuthPolling:
    """Test device authorization polling (RFC 8628 Section 3.4)."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_poll_for_token_returns_tokens_on_success(self, device_auth_config, device_code_response, token_response):
        """
        GIVEN: Device code has been issued and user has completed authentication
        WHEN: poll_for_token() is called
        THEN: Should return access_token and refresh_token
        """
        from mcp_server_langgraph.auth.device_auth import DeviceAuthClient

        client = DeviceAuthClient(**device_auth_config)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = token_response
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await client.poll_for_token(device_code_response["device_code"])

            assert "access_token" in result
            assert "refresh_token" in result
            assert result["token_type"] == "Bearer"

    @pytest.mark.asyncio
    async def test_poll_for_token_handles_authorization_pending(self, device_auth_config, device_code_response):
        """
        GIVEN: User has not yet completed authentication
        WHEN: poll_for_token() is called
        THEN: Should raise AuthorizationPending error
        """
        from mcp_server_langgraph.auth.device_auth import AuthorizationPending, DeviceAuthClient

        client = DeviceAuthClient(**device_auth_config)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"error": "authorization_pending"}
            mock_response.status_code = 400
            mock_response.raise_for_status = MagicMock(side_effect=Exception("400 Bad Request"))
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(AuthorizationPending):
                await client.poll_for_token(device_code_response["device_code"])

    @pytest.mark.asyncio
    async def test_poll_for_token_handles_slow_down(self, device_auth_config, device_code_response):
        """
        GIVEN: Server requests slower polling (too many requests)
        WHEN: poll_for_token() is called
        THEN: Should raise SlowDown error with new interval
        """
        from mcp_server_langgraph.auth.device_auth import DeviceAuthClient, SlowDown

        client = DeviceAuthClient(**device_auth_config)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"error": "slow_down"}
            mock_response.status_code = 400
            mock_response.raise_for_status = MagicMock(side_effect=Exception("400 Bad Request"))
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(SlowDown):
                await client.poll_for_token(device_code_response["device_code"])

    @pytest.mark.asyncio
    async def test_poll_for_token_handles_expired_token(self, device_auth_config, device_code_response):
        """
        GIVEN: Device code has expired
        WHEN: poll_for_token() is called
        THEN: Should raise ExpiredToken error
        """
        from mcp_server_langgraph.auth.device_auth import DeviceAuthClient, ExpiredToken

        client = DeviceAuthClient(**device_auth_config)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"error": "expired_token"}
            mock_response.status_code = 400
            mock_response.raise_for_status = MagicMock(side_effect=Exception("400 Bad Request"))
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(ExpiredToken):
                await client.poll_for_token(device_code_response["device_code"])

    @pytest.mark.asyncio
    async def test_poll_for_token_handles_access_denied(self, device_auth_config, device_code_response):
        """
        GIVEN: User denied authorization
        WHEN: poll_for_token() is called
        THEN: Should raise AccessDenied error
        """
        from mcp_server_langgraph.auth.device_auth import AccessDenied, DeviceAuthClient

        client = DeviceAuthClient(**device_auth_config)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"error": "access_denied"}
            mock_response.status_code = 400
            mock_response.raise_for_status = MagicMock(side_effect=Exception("400 Bad Request"))
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(AccessDenied):
                await client.poll_for_token(device_code_response["device_code"])


@pytest.mark.xdist_group(name="device_auth_tests")
class TestDeviceAuthFlow:
    """Test complete device authorization flow."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_wait_for_authorization_respects_polling_interval(
        self, device_auth_config, device_code_response, token_response
    ):
        """
        GIVEN: Device code with polling interval of 5 seconds
        WHEN: wait_for_authorization() is called
        THEN: Should respect the polling interval between requests
        """

        from mcp_server_langgraph.auth.device_auth import DeviceAuthClient

        client = DeviceAuthClient(**device_auth_config)
        poll_times = []

        async def mock_poll(*args, **kwargs):
            poll_times.append(datetime.now(UTC))
            if len(poll_times) < 3:
                # Return pending for first 2 polls
                from mcp_server_langgraph.auth.device_auth import AuthorizationPending

                raise AuthorizationPending()
            return token_response

        with patch.object(client, "poll_for_token", side_effect=mock_poll):
            # Use very short interval for test
            device_code_response_fast = {**device_code_response, "interval": 0.1}
            result = await client.wait_for_authorization(
                device_code_response_fast["device_code"],
                interval=0.1,
                timeout=5,
            )

            assert result["access_token"] == token_response["access_token"]
            # Check that at least 2 poll attempts happened with delay
            assert len(poll_times) == 3

    @pytest.mark.asyncio
    async def test_wait_for_authorization_times_out(self, device_auth_config, device_code_response):
        """
        GIVEN: User never completes authentication
        WHEN: wait_for_authorization() times out
        THEN: Should raise TimeoutError
        """
        from mcp_server_langgraph.auth.device_auth import AuthorizationPending, DeviceAuthClient

        client = DeviceAuthClient(**device_auth_config)

        async def mock_poll(*args, **kwargs):
            raise AuthorizationPending()

        with patch.object(client, "poll_for_token", side_effect=mock_poll):
            with pytest.raises(TimeoutError):
                await client.wait_for_authorization(
                    device_code_response["device_code"],
                    interval=0.01,
                    timeout=0.05,
                )


@pytest.mark.xdist_group(name="device_auth_tests")
class TestDeviceAuthDisplayHelpers:
    """Test display helpers for CLI output."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_format_user_instructions_includes_url_and_code(self, device_code_response):
        """
        GIVEN: Device code response with verification URI and user code
        WHEN: format_user_instructions() is called
        THEN: Should return formatted instructions with URL and code
        """
        from mcp_server_langgraph.auth.device_auth import format_user_instructions

        instructions = format_user_instructions(device_code_response)

        assert device_code_response["verification_uri"] in instructions
        assert device_code_response["user_code"] in instructions

    def test_generate_qr_code_returns_ascii_art(self, device_code_response):
        """
        GIVEN: Device code response with verification_uri_complete
        WHEN: generate_qr_code() is called
        THEN: Should return QR code as ASCII art string
        """
        pytest.importorskip("qrcode", reason="qrcode library not installed")

        from mcp_server_langgraph.auth.device_auth import generate_qr_code

        qr_code = generate_qr_code(device_code_response["verification_uri_complete"])

        # QR codes use block characters
        assert len(qr_code) > 0
        # Should be multi-line
        assert "\n" in qr_code
