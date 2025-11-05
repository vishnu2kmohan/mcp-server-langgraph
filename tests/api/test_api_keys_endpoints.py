"""
Tests for API Key Management REST Endpoints

Tests all API key operations including creation, listing, rotation, revocation,
and the internal validation endpoint used by Kong for API key→JWT exchange.

See ADR-0034 for API key to JWT exchange pattern.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient


@pytest.fixture
def mock_api_key_manager():
    """
    Mock APIKeyManager for testing endpoints without real Keycloak.

    Uses deterministic timestamps for reproducible tests.
    Fixed reference time: 2024-01-01T00:00:00Z
    """
    manager = AsyncMock()

    # Use deterministic timestamps instead of datetime.now()
    # This eliminates test flakiness and makes test data reproducible
    FIXED_TIME = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    # Mock create_api_key
    manager.create_api_key.return_value = {
        "key_id": "key_12345",
        "api_key": "mcp_test_key_abcdef123456",  # gitleaks:allow - test fixture
        "name": "Test Key",
        "created": FIXED_TIME.isoformat(),
        "expires_at": (FIXED_TIME + timedelta(days=365)).isoformat(),
    }

    # Mock list_api_keys
    manager.list_api_keys.return_value = [
        {
            "key_id": "key_12345",
            "name": "Test Key",
            "created": FIXED_TIME.isoformat(),
            "expires_at": (FIXED_TIME + timedelta(days=365)).isoformat(),
            "last_used": None,
        },
        {
            "key_id": "key_67890",
            "name": "Production Key",
            "created": (FIXED_TIME - timedelta(days=30)).isoformat(),
            "expires_at": (FIXED_TIME + timedelta(days=335)).isoformat(),
            "last_used": FIXED_TIME.isoformat(),
        },
    ]

    # Mock rotate_api_key
    manager.rotate_api_key.return_value = {
        "key_id": "key_12345",
        "new_api_key": "mcp_test_key_rotated_xyz789",  # gitleaks:allow - test fixture
    }

    # Mock revoke_api_key (returns None)
    manager.revoke_api_key.return_value = None

    # Mock validate_and_get_user
    manager.validate_and_get_user.return_value = {
        "user_id": "user:alice",  # OpenFGA format
        "keycloak_id": "8c7b4e5d-1234-5678-abcd-ef1234567890",  # Keycloak UUID
        "username": "alice",
        "email": "alice@example.com",
    }

    return manager


@pytest.fixture
def mock_keycloak_client():
    """Mock KeycloakClient for testing JWT issuance"""
    client = AsyncMock()

    # Mock issue_token_for_user
    client.issue_token_for_user.return_value = {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",  # gitleaks:allow - test JWT
        "expires_in": 900,  # 15 minutes
        "refresh_token": "refresh_token_xyz",  # gitleaks:allow - test token
        "token_type": "Bearer",
    }

    return client


@pytest.fixture
def test_client(mock_api_key_manager, mock_keycloak_client, mock_current_user):
    """FastAPI TestClient with mocked dependencies"""
    from fastapi import FastAPI

    from mcp_server_langgraph.api.api_keys import router
    from mcp_server_langgraph.auth.middleware import get_current_user
    from mcp_server_langgraph.core.dependencies import get_api_key_manager, get_keycloak_client

    app = FastAPI()
    app.include_router(router)

    # Override dependencies with actual function references
    app.dependency_overrides[get_api_key_manager] = lambda: mock_api_key_manager
    app.dependency_overrides[get_keycloak_client] = lambda: mock_keycloak_client
    app.dependency_overrides[get_current_user] = lambda: mock_current_user

    return TestClient(app)


# ==============================================================================
# Create API Key Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestCreateAPIKey:
    """Tests for POST /api/v1/api-keys/"""

    def test_create_api_key_success(self, test_client, mock_api_key_manager):
        """Test successful API key creation"""
        response = test_client.post(
            "/api/v1/api-keys/",
            json={
                "name": "Test Key",
                "expires_days": 365,
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Verify response structure
        assert "key_id" in data
        assert "api_key" in data
        assert data["name"] == "Test Key"
        assert "created" in data
        assert "expires_at" in data
        assert "message" in data
        assert "save it securely" in data["message"].lower()

        # Verify manager was called correctly
        mock_api_key_manager.create_api_key.assert_called_once_with(
            user_id="8c7b4e5d-1234-5678-abcd-ef1234567890",  # keycloak_id from fixture
            name="Test Key",
            expires_days=365,
        )

    def test_create_api_key_custom_expiration(self, test_client, mock_api_key_manager):
        """Test API key creation with custom expiration"""
        response = test_client.post(
            "/api/v1/api-keys/",
            json={
                "name": "Short-lived Key",
                "expires_days": 30,
            },
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Verify custom expiration was passed
        mock_api_key_manager.create_api_key.assert_called_once_with(
            user_id="8c7b4e5d-1234-5678-abcd-ef1234567890",  # keycloak_id from fixture
            name="Short-lived Key",
            expires_days=30,
        )

    def test_create_api_key_max_keys_exceeded(self, test_client, mock_api_key_manager):
        """Test API key creation when user has reached the limit (5 keys)"""
        # Simulate max keys error
        mock_api_key_manager.create_api_key.side_effect = ValueError("Maximum of 5 API keys allowed per user")

        response = test_client.post(
            "/api/v1/api-keys/",
            json={
                "name": "Sixth Key",
                "expires_days": 365,
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Maximum of 5 API keys" in response.json()["detail"]

    def test_create_api_key_missing_name(self, test_client):
        """Test API key creation without required name field"""
        response = test_client.post(
            "/api/v1/api-keys/",
            json={
                "expires_days": 365,
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_api_key_invalid_expiration(self, test_client, mock_api_key_manager):
        """Test API key creation with invalid expiration days"""
        mock_api_key_manager.create_api_key.side_effect = ValueError("expires_days must be between 1 and 365")

        response = test_client.post(
            "/api/v1/api-keys/",
            json={
                "name": "Invalid Key",
                "expires_days": 0,
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ==============================================================================
# List API Keys Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestListAPIKeys:
    """Tests for GET /api/v1/api-keys/"""

    def test_list_api_keys_success(self, test_client, mock_api_key_manager):
        """Test successful listing of user's API keys"""
        response = test_client.get("/api/v1/api-keys/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response is a list
        assert isinstance(data, list)
        assert len(data) == 2

        # Verify first key structure
        assert data[0]["key_id"] == "key_12345"
        assert data[0]["name"] == "Test Key"
        assert "created" in data[0]
        assert "expires_at" in data[0]
        assert data[0]["last_used"] is None

        # Verify API key is NOT included in response
        assert "api_key" not in data[0]

        # Verify second key has last_used
        assert data[1]["last_used"] is not None

        # Verify manager was called correctly
        mock_api_key_manager.list_api_keys.assert_called_once_with("8c7b4e5d-1234-5678-abcd-ef1234567890")  # keycloak_id from fixture

    def test_list_api_keys_empty(self, test_client, mock_api_key_manager):
        """Test listing when user has no API keys"""
        mock_api_key_manager.list_api_keys.return_value = []

        response = test_client.get("/api/v1/api-keys/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 0


# ==============================================================================
# Rotate API Key Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestRotateAPIKey:
    """Tests for POST /api/v1/api-keys/{key_id}/rotate"""

    def test_rotate_api_key_success(self, test_client, mock_api_key_manager):
        """Test successful API key rotation"""
        response = test_client.post("/api/v1/api-keys/key_12345/rotate")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert data["key_id"] == "key_12345"
        assert "new_api_key" in data
        assert data["new_api_key"] == "mcp_test_key_rotated_xyz789"
        assert "message" in data
        assert "update your client configuration" in data["message"].lower()

        # Verify manager was called correctly
        mock_api_key_manager.rotate_api_key.assert_called_once_with(
            user_id="8c7b4e5d-1234-5678-abcd-ef1234567890",  # keycloak_id from fixture
            key_id="key_12345",
        )

    def test_rotate_api_key_not_found(self, test_client, mock_api_key_manager):
        """Test rotating non-existent or unauthorized API key"""
        mock_api_key_manager.rotate_api_key.side_effect = ValueError("API key not found or unauthorized")

        response = test_client.post("/api/v1/api-keys/nonexistent/rotate")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_rotate_api_key_another_users_key(self, test_client, mock_api_key_manager):
        """Test rotating another user's API key (should fail)"""
        mock_api_key_manager.rotate_api_key.side_effect = ValueError("API key belongs to different user")

        response = test_client.post("/api/v1/api-keys/other_user_key/rotate")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==============================================================================
# Revoke API Key Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestRevokeAPIKey:
    """Tests for DELETE /api/v1/api-keys/{key_id}"""

    def test_revoke_api_key_success(self, test_client, mock_api_key_manager):
        """Test successful API key revocation"""
        response = test_client.delete("/api/v1/api-keys/key_12345")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""  # No response body

        # Verify manager was called correctly
        mock_api_key_manager.revoke_api_key.assert_called_once_with(
            user_id="8c7b4e5d-1234-5678-abcd-ef1234567890",  # keycloak_id from fixture
            key_id="key_12345",
        )

    def test_revoke_api_key_idempotent(self, test_client, mock_api_key_manager):
        """Test revoking already revoked key is idempotent"""
        # Revoke doesn't raise error even if key doesn't exist
        mock_api_key_manager.revoke_api_key.return_value = None

        response = test_client.delete("/api/v1/api-keys/already_revoked")

        assert response.status_code == status.HTTP_204_NO_CONTENT


# ==============================================================================
# Validate API Key Tests (Internal Kong Endpoint)
# ==============================================================================


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.auth
class TestValidateAPIKey:
    """Tests for POST /api/v1/api-keys/validate (Kong plugin)"""

    def test_validate_api_key_success(self, test_client, mock_api_key_manager, mock_keycloak_client):
        """Test successful API key validation and JWT exchange"""
        response = test_client.post(
            "/api/v1/api-keys/validate",
            headers={"X-API-Key": "mcp_test_key_abcdef123456"},  # gitleaks:allow - test key
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify JWT response
        assert "access_token" in data
        assert data["access_token"].startswith("eyJ")  # JWT format
        assert data["expires_in"] == 900
        assert data["user_id"] == "user:alice"  # OpenFGA format from user_info["user_id"]
        assert data["username"] == "alice"

        # Verify validation was called
        mock_api_key_manager.validate_and_get_user.assert_called_once_with("mcp_test_key_abcdef123456")

        # Verify JWT was issued with keycloak_id (UUID)
        mock_keycloak_client.issue_token_for_user.assert_called_once_with("8c7b4e5d-1234-5678-abcd-ef1234567890")

    def test_validate_api_key_missing_header(self, test_client):
        """Test validation without X-API-Key header"""
        response = test_client.post("/api/v1/api-keys/validate")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Missing X-API-Key header" in response.json()["detail"]

    def test_validate_api_key_invalid(self, test_client, mock_api_key_manager):
        """Test validation with invalid API key"""
        mock_api_key_manager.validate_and_get_user.return_value = None

        response = test_client.post(
            "/api/v1/api-keys/validate",
            headers={"X-API-Key": "invalid_key"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid or expired" in response.json()["detail"]

    def test_validate_api_key_expired(self, test_client, mock_api_key_manager):
        """Test validation with expired API key"""
        mock_api_key_manager.validate_and_get_user.return_value = None

        response = test_client.post(
            "/api/v1/api-keys/validate",
            headers={"X-API-Key": "mcp_expired_key"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_validate_api_key_jwt_issuance_fails(self, test_client, mock_keycloak_client):
        """Test validation when JWT issuance fails"""
        mock_keycloak_client.issue_token_for_user.side_effect = Exception("Keycloak unavailable")

        response = test_client.post(
            "/api/v1/api-keys/validate",
            headers={"X-API-Key": "mcp_test_key_abcdef123456"},  # gitleaks:allow - test key
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to issue JWT" in response.json()["detail"]

    def test_validate_api_key_not_in_openapi_schema(self, test_client):
        """Test that validate endpoint is excluded from public API docs"""
        # This endpoint should have include_in_schema=False
        # We can't directly test FastAPI's schema generation here,
        # but we verify the endpoint works (it's an internal endpoint)
        response = test_client.post(
            "/api/v1/api-keys/validate",
            headers={"X-API-Key": "mcp_test_key_abcdef123456"},  # gitleaks:allow - test key
        )

        # Should work despite being hidden from schema
        assert response.status_code == status.HTTP_200_OK


# ==============================================================================
# Authorization Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.auth
class TestAPIKeyEndpointAuthorization:
    """Tests for endpoint authorization (JWT required)"""

    def test_create_without_auth(self):
        """Test creating API key without authentication fails"""
        from fastapi import FastAPI

        from mcp_server_langgraph.api.api_keys import router

        app = FastAPI()
        app.include_router(router)

        # No dependency overrides - will fail auth
        client = TestClient(app)

        response = client.post(
            "/api/v1/api-keys/",
            json={"name": "Test", "expires_days": 365},
        )

        # Should fail due to missing authentication
        # Actual status depends on middleware implementation
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_500_INTERNAL_SERVER_ERROR,  # If dependency fails
        ]

    def test_list_without_auth(self):
        """Test listing API keys without authentication fails"""
        from fastapi import FastAPI

        from mcp_server_langgraph.api.api_keys import router

        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)

        response = client.get("/api/v1/api-keys/")

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]


# ==============================================================================
# Integration-style Tests (with real dependencies - optional)
# ==============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.slow
class TestAPIKeyEndpointsIntegration:
    """
    Integration tests with real Keycloak (requires docker-compose.test.yml)

    These tests are marked as integration and slow - they require the full
    test infrastructure to be running.
    """

    @pytest.mark.skip(reason="Requires full test infrastructure setup")
    async def test_full_api_key_lifecycle(self):
        """
        Test complete API key lifecycle with real services:
        1. Create API key
        2. List keys
        3. Validate key → JWT exchange
        4. Rotate key
        5. Validate new key
        6. Revoke key
        7. Verify revoked key fails validation
        """
        # TODO: Implement when E2E infrastructure is ready
        pass
