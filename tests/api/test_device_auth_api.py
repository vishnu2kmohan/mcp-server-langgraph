"""
Tests for Device Authorization Grant API endpoints (RFC 8628).

Provides headless/CLI authentication without user interaction on the client device.
The user authenticates via a browser on another device (e.g., phone, laptop).

TDD Tests - Written FIRST before implementation.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.unit, pytest.mark.api, pytest.mark.auth]


def _create_test_app() -> FastAPI:
    """Create a test FastAPI app with the auth router."""
    from mcp_server_langgraph.api.v1.auth import auth_router

    app = FastAPI()
    app.include_router(auth_router)
    return app


@pytest.fixture
def app():
    """Create test app with auth router."""
    return _create_test_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_device_code_response():
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
def mock_token_response():
    """Mock successful token response."""
    return {
        "access_token": "test-access-token-xyz789",
        "refresh_token": "test-refresh-token-uvw456",
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "openid profile email",
    }


@pytest.mark.xdist_group(name="device_auth_api")
class TestDeviceAuthRequestEndpoint:
    """Test GET /auth/device - Request device code."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_device_auth_request_returns_device_code(self, client, mock_device_code_response):
        """
        GIVEN: Device authorization endpoint is available
        WHEN: GET /auth/device is called
        THEN: Should return device_code, user_code, and verification_uri
        """
        with patch("mcp_server_langgraph.api.v1.auth.DeviceAuthClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.request_device_code = AsyncMock(return_value=mock_device_code_response)
            MockClient.return_value = mock_instance

            response = client.get("/auth/device")

            assert response.status_code == 200
            data = response.json()
            assert "device_code" in data
            assert "user_code" in data
            assert "verification_uri" in data
            assert data["user_code"] == "ABCD-EFGH"

    def test_device_auth_request_includes_expires_in(self, client, mock_device_code_response):
        """
        GIVEN: Device authorization endpoint is available
        WHEN: GET /auth/device is called
        THEN: Response should include expires_in for code validity period
        """
        with patch("mcp_server_langgraph.api.v1.auth.DeviceAuthClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.request_device_code = AsyncMock(return_value=mock_device_code_response)
            MockClient.return_value = mock_instance

            response = client.get("/auth/device")

            assert response.status_code == 200
            data = response.json()
            assert "expires_in" in data
            assert data["expires_in"] == 600

    def test_device_auth_request_includes_verification_uri_complete(self, client, mock_device_code_response):
        """
        GIVEN: Device authorization endpoint is available
        WHEN: GET /auth/device is called
        THEN: Response should include verification_uri_complete for QR codes
        """
        with patch("mcp_server_langgraph.api.v1.auth.DeviceAuthClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.request_device_code = AsyncMock(return_value=mock_device_code_response)
            MockClient.return_value = mock_instance

            response = client.get("/auth/device")

            assert response.status_code == 200
            data = response.json()
            assert "verification_uri_complete" in data
            assert "user_code=ABCD-EFGH" in data["verification_uri_complete"]


@pytest.mark.xdist_group(name="device_auth_api")
class TestDeviceAuthTokenEndpoint:
    """Test POST /auth/device/token - Poll for token."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_device_token_returns_tokens_on_success(self, client, mock_token_response):
        """
        GIVEN: User has completed authentication
        WHEN: POST /auth/device/token is called with device_code
        THEN: Should return access_token and refresh_token
        """
        with patch("mcp_server_langgraph.api.v1.auth.DeviceAuthClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.poll_for_token = AsyncMock(return_value=mock_token_response)
            MockClient.return_value = mock_instance

            response = client.post(
                "/auth/device/token",
                json={"device_code": "test-device-code-abc123"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "Bearer"

    def test_device_token_returns_pending_when_user_not_authorized(self, client):
        """
        GIVEN: User has not yet completed authentication
        WHEN: POST /auth/device/token is called
        THEN: Should return 400 with authorization_pending error
        """
        from mcp_server_langgraph.auth.device_auth import AuthorizationPending

        with patch("mcp_server_langgraph.api.v1.auth.DeviceAuthClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.poll_for_token = AsyncMock(side_effect=AuthorizationPending())
            MockClient.return_value = mock_instance

            response = client.post(
                "/auth/device/token",
                json={"device_code": "test-device-code-abc123"},
            )

            assert response.status_code == 400
            data = response.json()
            assert data.get("error") == "authorization_pending"

    def test_device_token_returns_slow_down_when_polling_too_fast(self, client):
        """
        GIVEN: Client is polling too frequently
        WHEN: POST /auth/device/token is called
        THEN: Should return 400 with slow_down error
        """
        from mcp_server_langgraph.auth.device_auth import SlowDown

        with patch("mcp_server_langgraph.api.v1.auth.DeviceAuthClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.poll_for_token = AsyncMock(side_effect=SlowDown())
            MockClient.return_value = mock_instance

            response = client.post(
                "/auth/device/token",
                json={"device_code": "test-device-code-abc123"},
            )

            assert response.status_code == 400
            data = response.json()
            assert data.get("error") == "slow_down"

    def test_device_token_returns_expired_when_device_code_expired(self, client):
        """
        GIVEN: Device code has expired
        WHEN: POST /auth/device/token is called
        THEN: Should return 400 with expired_token error
        """
        from mcp_server_langgraph.auth.device_auth import ExpiredToken

        with patch("mcp_server_langgraph.api.v1.auth.DeviceAuthClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.poll_for_token = AsyncMock(side_effect=ExpiredToken())
            MockClient.return_value = mock_instance

            response = client.post(
                "/auth/device/token",
                json={"device_code": "test-device-code-abc123"},
            )

            assert response.status_code == 400
            data = response.json()
            assert data.get("error") == "expired_token"

    def test_device_token_returns_access_denied_when_user_denies(self, client):
        """
        GIVEN: User denied authorization
        WHEN: POST /auth/device/token is called
        THEN: Should return 400 with access_denied error
        """
        from mcp_server_langgraph.auth.device_auth import AccessDenied

        with patch("mcp_server_langgraph.api.v1.auth.DeviceAuthClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.poll_for_token = AsyncMock(side_effect=AccessDenied())
            MockClient.return_value = mock_instance

            response = client.post(
                "/auth/device/token",
                json={"device_code": "test-device-code-abc123"},
            )

            assert response.status_code == 400
            data = response.json()
            assert data.get("error") == "access_denied"

    def test_device_token_requires_device_code(self, client):
        """
        GIVEN: Device token endpoint
        WHEN: POST /auth/device/token is called without device_code
        THEN: Should return 422 validation error
        """
        response = client.post("/auth/device/token", json={})

        assert response.status_code == 422
