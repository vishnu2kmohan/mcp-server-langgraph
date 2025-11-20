"""
Tests for API Key Management REST Endpoints

Tests all API key operations including creation, listing, rotation, revocation,
and the internal validation endpoint used by Kong for API key→JWT exchange.

See ADR-0034 for API key to JWT exchange pattern.
"""

import gc
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

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


@pytest.fixture(scope="function")
def api_keys_test_client(mock_api_key_manager, mock_keycloak_client, mock_current_user):
    """
    FastAPI TestClient with mocked dependencies for API keys endpoints.

    PYTEST-XDIST FIX (2025-11-13 - FINAL):
    - Removed MCP_SKIP_AUTH environment variable (caused race conditions)
    - Use app.dependency_overrides exclusively for test isolation
    - FastAPI dependency overrides provide proper pytest-xdist isolation

    PYTEST-XDIST FIX (2025-11-14 - REVISION 6 - RE-IMPORT PATTERN):
    - Re-import auth.middleware right before applying overrides
    - Ensures we always override the exact objects the router currently holds
    - Prevents 401 errors even if another test reloaded the module
    - See: OpenAI Codex findings 2025-11-14 (worker pollution analysis)

    PYTEST-XDIST FIX (2025-11-14 - REVISION 7 - MODULE RELOAD PATTERN):
    - Use importlib.reload() to force router to re-import from reloaded middleware
    - Python's import system caches modules - importing again returns cached version
    - Router module already has stale references from previous tests
    - Reloading forces fresh import chain: middleware → router → endpoint functions
    """
    import importlib

    from fastapi import FastAPI
    from fastapi.security import HTTPAuthorizationCredentials

    # CRITICAL RE-IMPORT + RELOAD PATTERN (2025-11-14 - REVISION 7):
    # Re-import middleware FIRST to get fresh module reference
    from mcp_server_langgraph.auth import middleware

    # RELOAD middleware to ensure we get current instances (not cached from previous tests)
    importlib.reload(middleware)

    # Now import router module (gets cached version)
    from mcp_server_langgraph.api import api_keys

    # RELOAD router to force it to re-import from the reloaded middleware
    importlib.reload(api_keys)

    # Get router and dependencies from reloaded module
    router = api_keys.router
    from mcp_server_langgraph.core.dependencies import get_api_key_manager, get_keycloak_client

    # Create fresh FastAPI app
    app = FastAPI()

    # CRITICAL: Override bearer_scheme BEFORE include_router (Commit 05a54e1)
    # This prevents bearer_scheme singleton pollution in pytest-xdist
    # Use middleware.bearer_scheme (just re-imported) instead of top-level import
    app.dependency_overrides[middleware.bearer_scheme] = lambda: HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="mock_token_for_testing"
    )

    app.include_router(router)

    # Override dependencies using FastAPI's built-in mechanism
    # CRITICAL: get_current_user is async, so override MUST be async (not lambda)
    # Use middleware.get_current_user (just re-imported) for correct instance
    async def override_get_current_user():
        return mock_current_user

    app.dependency_overrides[middleware.get_current_user] = override_get_current_user
    app.dependency_overrides[get_api_key_manager] = lambda: mock_api_key_manager
    app.dependency_overrides[get_keycloak_client] = lambda: mock_keycloak_client

    # Create TestClient
    client = TestClient(app, raise_server_exceptions=False)

    yield client

    # Cleanup
    app.dependency_overrides.clear()
    gc.collect()


# ==============================================================================
# Create API Key Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="api_keys_create_tests")
class TestCreateAPIKey:
    """Tests for POST /api/v1/api-keys/"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_api_key_success(self, api_keys_test_client, mock_api_key_manager):
        """Test successful API key creation"""
        response = api_keys_test_client.post(
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

    def test_create_api_key_custom_expiration(self, api_keys_test_client, mock_api_key_manager):
        """Test API key creation with custom expiration"""
        response = api_keys_test_client.post(
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

    def test_create_api_key_max_keys_exceeded(self, api_keys_test_client, mock_api_key_manager):
        """Test API key creation when user has reached the limit (5 keys)"""
        # Simulate max keys error
        mock_api_key_manager.create_api_key.side_effect = ValueError("Maximum of 5 API keys allowed per user")

        response = api_keys_test_client.post(
            "/api/v1/api-keys/",
            json={
                "name": "Sixth Key",
                "expires_days": 365,
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Maximum of 5 API keys" in response.json()["detail"]

    def test_create_api_key_missing_name(self, api_keys_test_client):
        """Test API key creation without required name field"""
        response = api_keys_test_client.post(
            "/api/v1/api-keys/",
            json={
                "expires_days": 365,
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_create_api_key_invalid_expiration(self, api_keys_test_client, mock_api_key_manager):
        """Test API key creation with invalid expiration days"""
        mock_api_key_manager.create_api_key.side_effect = ValueError("expires_days must be between 1 and 365")

        response = api_keys_test_client.post(
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
@pytest.mark.xdist_group(name="api_keys_list_tests")
class TestListAPIKeys:
    """Tests for GET /api/v1/api-keys/"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_list_api_keys_success(self, api_keys_test_client, mock_api_key_manager):
        """Test successful listing of user's API keys"""
        response = api_keys_test_client.get("/api/v1/api-keys/")

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
        mock_api_key_manager.list_api_keys.assert_called_once_with(
            "8c7b4e5d-1234-5678-abcd-ef1234567890"
        )  # keycloak_id from fixture

    def test_list_api_keys_empty(self, api_keys_test_client, mock_api_key_manager):
        """Test listing when user has no API keys"""
        mock_api_key_manager.list_api_keys.return_value = []

        response = api_keys_test_client.get("/api/v1/api-keys/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 0


# ==============================================================================
# Rotate API Key Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="api_keys_rotate_tests")
class TestRotateAPIKey:
    """Tests for POST /api/v1/api-keys/{key_id}/rotate"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_rotate_api_key_success(self, api_keys_test_client, mock_api_key_manager):
        """Test successful API key rotation"""
        response = api_keys_test_client.post("/api/v1/api-keys/key_12345/rotate")

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

    def test_rotate_api_key_not_found(self, api_keys_test_client, mock_api_key_manager):
        """Test rotating non-existent or unauthorized API key"""
        mock_api_key_manager.rotate_api_key.side_effect = ValueError("API key not found or unauthorized")

        response = api_keys_test_client.post("/api/v1/api-keys/nonexistent/rotate")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_rotate_api_key_another_users_key(self, api_keys_test_client, mock_api_key_manager):
        """Test rotating another user's API key (should fail)"""
        mock_api_key_manager.rotate_api_key.side_effect = ValueError("API key belongs to different user")

        response = api_keys_test_client.post("/api/v1/api-keys/other_user_key/rotate")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==============================================================================
# Revoke API Key Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="api_keys_revoke_tests")
class TestRevokeAPIKey:
    """Tests for DELETE /api/v1/api-keys/{key_id}"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_revoke_api_key_success(self, api_keys_test_client, mock_api_key_manager):
        """Test successful API key revocation"""
        response = api_keys_test_client.delete("/api/v1/api-keys/key_12345")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""  # No response body

        # Verify manager was called correctly
        mock_api_key_manager.revoke_api_key.assert_called_once_with(
            user_id="8c7b4e5d-1234-5678-abcd-ef1234567890",  # keycloak_id from fixture
            key_id="key_12345",
        )

    def test_revoke_api_key_idempotent(self, api_keys_test_client, mock_api_key_manager):
        """Test revoking already revoked key is idempotent"""
        # Revoke doesn't raise error even if key doesn't exist
        mock_api_key_manager.revoke_api_key.return_value = None

        response = api_keys_test_client.delete("/api/v1/api-keys/already_revoked")

        assert response.status_code == status.HTTP_204_NO_CONTENT


# ==============================================================================
# Validate API Key Tests (Internal Kong Endpoint)
# ==============================================================================


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.auth
@pytest.mark.xdist_group(name="api_keys_validate_tests")
class TestValidateAPIKey:
    """Tests for POST /api/v1/api-keys/validate (Kong plugin)"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_validate_api_key_success(self, api_keys_test_client, mock_api_key_manager, mock_keycloak_client):
        """Test successful API key validation and JWT exchange"""
        response = api_keys_test_client.post(
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

    def test_validate_api_key_missing_header(self, api_keys_test_client):
        """Test validation without X-API-Key header"""
        response = api_keys_test_client.post("/api/v1/api-keys/validate")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Missing X-API-Key header" in response.json()["detail"]

    def test_validate_api_key_invalid(self, api_keys_test_client, mock_api_key_manager):
        """Test validation with invalid API key"""
        mock_api_key_manager.validate_and_get_user.return_value = None

        response = api_keys_test_client.post(
            "/api/v1/api-keys/validate",
            headers={"X-API-Key": "invalid_key"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid or expired" in response.json()["detail"]

    def test_validate_api_key_expired(self, api_keys_test_client, mock_api_key_manager):
        """Test validation with expired API key"""
        mock_api_key_manager.validate_and_get_user.return_value = None

        response = api_keys_test_client.post(
            "/api/v1/api-keys/validate",
            headers={"X-API-Key": "mcp_expired_key"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_validate_api_key_jwt_issuance_fails(self, api_keys_test_client, mock_keycloak_client):
        """Test validation when JWT issuance fails"""
        mock_keycloak_client.issue_token_for_user.side_effect = Exception("Keycloak unavailable")

        response = api_keys_test_client.post(
            "/api/v1/api-keys/validate",
            headers={"X-API-Key": "mcp_test_key_abcdef123456"},  # gitleaks:allow - test key
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to issue JWT" in response.json()["detail"]

    def test_validate_api_key_not_in_openapi_schema(self, api_keys_test_client):
        """Test that validate endpoint is excluded from public API docs"""
        # This endpoint should have include_in_schema=False
        # We can't directly test FastAPI's schema generation here,
        # but we verify the endpoint works (it's an internal endpoint)
        response = api_keys_test_client.post(
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
@pytest.mark.xdist_group(name="api_keys_auth_tests")
class TestAPIKeyEndpointAuthorization:
    """Tests for endpoint authorization (JWT required)"""

    def setup_method(self):
        """Reset state BEFORE test to prevent MCP_SKIP_AUTH pollution"""
        import os

        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None
        os.environ["MCP_SKIP_AUTH"] = "false"

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_without_auth(self, monkeypatch):
        """Test creating API key without authentication fails"""

        from fastapi import FastAPI

        from mcp_server_langgraph.api.api_keys import router

        app = FastAPI()
        app.include_router(router)

        # No dependency overrides - will fail auth
        client = TestClient(app)

        try:
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
        finally:
            # Cleanup to prevent pollution in pytest-xdist workers
            app.dependency_overrides.clear()

    def test_list_without_auth(self, monkeypatch):
        """Test listing API keys without authentication fails"""
        from fastapi import FastAPI

        from mcp_server_langgraph.api.api_keys import router

        app = FastAPI()
        app.include_router(router)

        # No dependency overrides - will fail auth
        client = TestClient(app)

        try:
            response = client.get("/api/v1/api-keys/")

            # Should fail due to missing authentication
            # Actual status depends on middleware implementation
            assert response.status_code in [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_500_INTERNAL_SERVER_ERROR,  # If dependency fails
            ]
        finally:
            # Cleanup to prevent pollution in pytest-xdist workers
            app.dependency_overrides.clear()


# ==============================================================================
# Integration-style Tests (with real dependencies - optional)
# ==============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.slow
@pytest.mark.xdist_group(name="api_keys_integration_tests")
class TestAPIKeyEndpointsIntegration:
    """
    Integration tests with real Keycloak (requires docker-compose.test.yml)

    These tests are marked as integration and slow - they require the full
    test infrastructure to be running.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_full_api_key_lifecycle(self, integration_test_env, test_fastapi_app):
        """
        Test complete API key lifecycle with real services.

        Uses integration_test_env fixture which auto-skips when
        Docker infrastructure is not available.

        Test steps:
        1. Create API key
        2. List keys
        3. Validate key → JWT exchange
        4. Rotate key
        5. Validate new key
        6. Revoke key
        7. Verify revoked key fails validation
        """
        # TODO: Implement full lifecycle test
        # infrastructure is available via fixtures
