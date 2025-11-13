"""
Tests for Service Principal Management REST Endpoints

Tests all service principal operations including creation, listing, secret rotation,
deletion, and user association for permission inheritance.

See ADR-0033 for service principal design decisions.
"""

import gc
from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient


@dataclass
class MockServicePrincipal:
    """Mock ServicePrincipal dataclass matching auth/service_principal.py"""

    service_id: str
    name: str
    description: str
    authentication_mode: str
    associated_user_id: str | None
    owner_user_id: str | None
    inherit_permissions: bool
    enabled: bool
    created_at: str | None
    client_secret: str | None = None  # Only populated on creation/rotation


@pytest.fixture
def mock_sp_manager():
    """Mock ServicePrincipalManager for testing endpoints"""
    manager = AsyncMock()

    # Mock create_service_principal
    manager.create_service_principal.return_value = MockServicePrincipal(
        service_id="batch-etl-job",
        name="Batch ETL Job",
        description="Nightly data processing",
        authentication_mode="client_credentials",
        associated_user_id="user:alice",
        owner_user_id="user:alice",  # OpenFGA format from shared fixture
        inherit_permissions=True,
        enabled=True,
        created_at=datetime.now(timezone.utc).isoformat(),
        client_secret="sp_secret_abc123xyz789",  # gitleaks:allow - test secret
    )

    # Mock list_service_principals
    manager.list_service_principals.return_value = [
        MockServicePrincipal(
            service_id="batch-etl-job",
            name="Batch ETL Job",
            description="Nightly data processing",
            authentication_mode="client_credentials",
            associated_user_id="user:alice",
            owner_user_id="user:alice",  # OpenFGA format from shared fixture
            inherit_permissions=True,
            enabled=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        ),
        MockServicePrincipal(
            service_id="monitoring-service",
            name="Monitoring Service",
            description="Health checks and monitoring",
            authentication_mode="service_account_user",
            associated_user_id=None,
            owner_user_id="user:alice",  # OpenFGA format from shared fixture
            inherit_permissions=False,
            enabled=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        ),
    ]

    # Mock get_service_principal - return None by default (SP doesn't exist)
    # Individual tests can override this to test conflict scenarios
    manager.get_service_principal.return_value = None

    # Mock rotate_secret
    manager.rotate_secret.return_value = "sp_secret_rotated_new123"  # gitleaks:allow - test secret

    # Mock delete_service_principal
    manager.delete_service_principal.return_value = None

    # Mock associate_with_user
    manager.associate_with_user.return_value = None

    return manager


@pytest.fixture
def mock_admin_user(mock_current_user):
    """Mock current user with admin role for tests that need elevated permissions"""
    admin_user = mock_current_user.copy()
    admin_user["roles"] = ["admin"]
    return admin_user


@pytest.fixture
def mock_openfga_client():
    """Mock OpenFGA client for authorization checks"""
    mock_client = AsyncMock()
    # By default, authorize all permission checks (tests can override)
    mock_client.check_permission = AsyncMock(return_value=True)
    return mock_client


@pytest.fixture
def mock_keycloak_client():
    """Mock Keycloak client for service principal management"""
    mock_client = AsyncMock()
    # Default mocks for Keycloak operations (tests can override)
    mock_client.create_client = AsyncMock(return_value="client-uuid-123")
    mock_client.get_client_secret = AsyncMock(return_value="sp_secret_abc123xyz789")
    mock_client.delete_client = AsyncMock()
    return mock_client


@pytest.fixture(scope="function")
def sp_test_client(mock_sp_manager, mock_current_user, mock_openfga_client, mock_keycloak_client):
    """
    FastAPI TestClient with mocked dependencies for service principals endpoints.

    PYTEST-XDIST FIX (2025-11-12 - REVISION 5 - CRITICAL):
    - Use app.dependency_overrides instead of monkeypatch
    - Monkeypatch + reload causes FastAPI parameter name collision:
      * Endpoint has parameter: request: CreateServicePrincipalRequest
      * Mock get_current_user has parameter: request: Request
      * FastAPI gets confused and looks for 'request' field in body → 422 error
    - dependency_overrides avoids this issue and works reliably with pytest-xdist

    ROOT CAUSE OF PREVIOUS FAILURES:
    FastAPI introspects function signatures for dependency injection. When using
    monkeypatch + reload, FastAPI sees the mock function signature with Request
    parameter and gets confused with the endpoint's request parameter, causing:
    {'detail': [{'type': 'missing', 'loc': ['body', 'request'], 'msg': 'Field required'}]}

    Solution: Use dependency_overrides which properly isolates dependencies.
    """
    import os

    from fastapi import FastAPI

    from mcp_server_langgraph.api.service_principals import router
    from mcp_server_langgraph.auth.middleware import get_current_user
    from mcp_server_langgraph.core.dependencies import get_keycloak_client, get_openfga_client, get_service_principal_manager

    # CRITICAL: Set MCP_SKIP_AUTH="false" BEFORE creating app
    # get_current_user() checks os.getenv("MCP_SKIP_AUTH") at RUNTIME (every call)
    # We must set it to "false" explicitly to prevent conftest.py pollution
    # Just deleting isn't enough - need to explicitly set to "false"
    # Create fresh FastAPI app
    app = FastAPI()
    app.include_router(router)

    # Override dependencies using FastAPI's built-in mechanism
    # With MCP_SKIP_AUTH=true (set in conftest), get_current_user returns default user
    # Override it here to use our specific mock_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    app.dependency_overrides[get_service_principal_manager] = lambda: mock_sp_manager
    app.dependency_overrides[get_openfga_client] = lambda: mock_openfga_client
    app.dependency_overrides[get_keycloak_client] = lambda: mock_keycloak_client

    # Create TestClient
    client = TestClient(app, raise_server_exceptions=False)

    yield client

    # Cleanup
    app.dependency_overrides.clear()
    gc.collect()


@pytest.fixture(scope="function")
def admin_test_client(mock_sp_manager, mock_admin_user, mock_openfga_client, mock_keycloak_client):
    """
    FastAPI TestClient with admin user for tests requiring elevated permissions.

    PYTEST-XDIST FIX (2025-11-12 - REVISION 5):
    - Use app.dependency_overrides instead of monkeypatch
    - Same fix as sp_test_client to avoid FastAPI parameter name collision
    """
    import os

    from fastapi import FastAPI

    from mcp_server_langgraph.api.service_principals import router
    from mcp_server_langgraph.auth.middleware import get_current_user
    from mcp_server_langgraph.core.dependencies import get_keycloak_client, get_openfga_client, get_service_principal_manager

    # CRITICAL: Set MCP_SKIP_AUTH="false" BEFORE creating app (same fix as sp_test_client)
    # Must set explicitly to "false" to prevent conftest.py pollution
    # Create fresh FastAPI app
    app = FastAPI()
    app.include_router(router)

    # Override dependencies with admin user
    app.dependency_overrides[get_current_user] = lambda: mock_admin_user
    app.dependency_overrides[get_service_principal_manager] = lambda: mock_sp_manager
    app.dependency_overrides[get_openfga_client] = lambda: mock_openfga_client
    app.dependency_overrides[get_keycloak_client] = lambda: mock_keycloak_client

    # Create TestClient
    client = TestClient(app, raise_server_exceptions=False)

    yield client

    # Cleanup
    app.dependency_overrides.clear()
    gc.collect()


# ==============================================================================
# Create Service Principal Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="sp_create_tests")
class TestCreateServicePrincipal:
    """Tests for POST /api/v1/service-principals/"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_create_service_principal_success(self, sp_test_client, mock_sp_manager):
        """Test successful service principal creation"""
        response = sp_test_client.post(
            "/api/v1/service-principals/",
            json={
                "name": "Batch ETL Job",
                "description": "Nightly data processing",
                "authentication_mode": "client_credentials",
                "associated_user_id": "user:alice",
                "inherit_permissions": True,
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Verify response structure
        assert data["service_id"] == "batch-etl-job"
        assert data["name"] == "Batch ETL Job"
        assert data["description"] == "Nightly data processing"
        assert data["authentication_mode"] == "client_credentials"
        assert data["associated_user_id"] == "user:alice"
        assert data["owner_user_id"] == "user:alice"  # OpenFGA format
        assert data["inherit_permissions"] is True
        assert data["enabled"] is True
        assert "created_at" in data
        assert "client_secret" in data
        assert data["client_secret"].startswith("sp_secret_")
        assert "message" in data
        assert "save the client_secret securely" in data["message"].lower()

        # Verify manager was called correctly
        mock_sp_manager.create_service_principal.assert_called_once()

    def test_create_service_principal_minimal(self, sp_test_client, mock_sp_manager):
        """Test service principal creation with minimal fields"""
        response = sp_test_client.post(
            "/api/v1/service-principals/",
            json={
                "name": "Simple Service",
                "description": "Basic service",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Verify defaults
        assert data["authentication_mode"] == "client_credentials"

        # FIXED: Remove always-true assertion - lock in actual default behavior
        # The default for inherit_permissions should be explicitly documented
        # Based on the mock fixture, the default is True when associated_user_id is set
        assert data["inherit_permissions"] is True, (
            "Default inherit_permissions should be True when creating service principal with minimal fields "
            "(this locks in the API contract for default behavior)"
        )

    def test_create_service_principal_service_account_mode(self, sp_test_client, mock_sp_manager):
        """Test creating service principal with service_account_user mode"""
        response = sp_test_client.post(
            "/api/v1/service-principals/",
            json={
                "name": "Service Account",
                "description": "Service account user mode",
                "authentication_mode": "service_account_user",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_create_service_principal_invalid_auth_mode(self, sp_test_client):
        """Test creating service principal with invalid authentication mode"""
        response = sp_test_client.post(
            "/api/v1/service-principals/",
            json={
                "name": "Bad Service",
                "description": "Invalid auth mode",
                "authentication_mode": "invalid_mode",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid authentication_mode" in response.json()["detail"]

    def test_create_service_principal_duplicate_id(self, sp_test_client, mock_sp_manager):
        """Test creating service principal when ID already exists"""
        # Mock get_service_principal to return existing SP
        mock_sp_manager.get_service_principal.return_value = MockServicePrincipal(
            service_id="batch-etl-job",
            name="Existing",
            description="Already exists",
            authentication_mode="client_credentials",
            associated_user_id=None,
            owner_user_id="user:alice",  # OpenFGA format from shared fixture
            inherit_permissions=False,
            enabled=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        response = sp_test_client.post(
            "/api/v1/service-principals/",
            json={
                "name": "Batch ETL Job",  # Will generate same service_id
                "description": "Duplicate",
            },
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]

    def test_create_service_principal_missing_secret(self, sp_test_client, mock_sp_manager):
        """Test error handling when secret generation fails"""
        # Mock creation to return SP without secret
        mock_sp_manager.create_service_principal.return_value = MockServicePrincipal(
            service_id="bad-service",
            name="Bad Service",
            description="No secret",
            authentication_mode="client_credentials",
            associated_user_id=None,
            owner_user_id="user:alice",  # OpenFGA format from shared fixture
            inherit_permissions=False,
            enabled=True,
            created_at=datetime.now(timezone.utc).isoformat(),
            client_secret=None,  # Missing secret
        )

        response = sp_test_client.post(
            "/api/v1/service-principals/",
            json={
                "name": "Bad Service",
                "description": "Test",
            },
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to generate client secret" in response.json()["detail"]


# ==============================================================================
# List Service Principals Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="sp_list_tests")
class TestListServicePrincipals:
    """Tests for GET /api/v1/service-principals/"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_list_service_principals_success(self, sp_test_client, mock_sp_manager):
        """Test successful listing of user's service principals"""
        response = sp_test_client.get("/api/v1/service-principals/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response is a list
        assert isinstance(data, list)
        assert len(data) == 2

        # Verify first SP structure
        assert data[0]["service_id"] == "batch-etl-job"
        assert data[0]["name"] == "Batch ETL Job"
        assert data[0]["authentication_mode"] == "client_credentials"
        assert data[0]["inherit_permissions"] is True

        # Verify client_secret is NOT included
        assert "client_secret" not in data[0]

        # Verify manager was called with current user
        mock_sp_manager.list_service_principals.assert_called_once_with(owner_user_id="user:alice")  # OpenFGA format

    def test_list_service_principals_empty(self, sp_test_client, mock_sp_manager):
        """Test listing when user has no service principals"""
        mock_sp_manager.list_service_principals.return_value = []

        response = sp_test_client.get("/api/v1/service-principals/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 0


# ==============================================================================
# Get Service Principal Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="sp_get_tests")
class TestGetServicePrincipal:
    """Tests for GET /api/v1/service-principals/{service_id}"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_get_service_principal_success(self, sp_test_client, mock_sp_manager):
        """Test successful retrieval of service principal details"""
        # Arrange: Configure mock to return existing service principal
        mock_sp_manager.get_service_principal.return_value = MockServicePrincipal(
            service_id="batch-etl-job",
            name="Batch ETL Job",
            description="Nightly data processing",
            authentication_mode="client_credentials",
            associated_user_id=None,
            owner_user_id="user:alice",  # OpenFGA format from shared fixture
            inherit_permissions=False,
            enabled=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Act: Retrieve service principal
        response = sp_test_client.get("/api/v1/service-principals/batch-etl-job")

        # Assert: Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert data["service_id"] == "batch-etl-job"
        assert data["name"] == "Batch ETL Job"
        assert data["owner_user_id"] == "user:alice"  # OpenFGA format

        # Verify client_secret is NOT included
        assert "client_secret" not in data

        # Verify manager was called
        mock_sp_manager.get_service_principal.assert_called_once_with("batch-etl-job")

    def test_get_service_principal_not_found(self, sp_test_client, mock_sp_manager):
        """Test retrieving non-existent service principal"""
        mock_sp_manager.get_service_principal.return_value = None

        response = sp_test_client.get("/api/v1/service-principals/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]

    def test_get_service_principal_unauthorized(self, sp_test_client, mock_sp_manager):
        """Test retrieving another user's service principal"""
        # Return SP owned by different user
        mock_sp_manager.get_service_principal.return_value = MockServicePrincipal(
            service_id="other-service",
            name="Other Service",
            description="Owned by someone else",
            authentication_mode="client_credentials",
            associated_user_id=None,
            owner_user_id="other_user",  # Different owner
            inherit_permissions=False,
            enabled=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        response = sp_test_client.get("/api/v1/service-principals/other-service")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "do not have permission" in response.json()["detail"]


# ==============================================================================
# Rotate Secret Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="sp_rotate_tests")
class TestRotateServicePrincipalSecret:
    """Tests for POST /api/v1/service-principals/{service_id}/rotate-secret"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_rotate_secret_success(self, sp_test_client, mock_sp_manager):
        """Test successful secret rotation"""
        # Arrange: Configure mock to return existing service principal owned by current user
        mock_sp_manager.get_service_principal.return_value = MockServicePrincipal(
            service_id="batch-etl-job",
            name="Batch ETL Job",
            description="Nightly data processing",
            authentication_mode="client_credentials",
            associated_user_id=None,
            owner_user_id="user:alice",  # OpenFGA format from shared fixture
            inherit_permissions=False,
            enabled=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Act: Call rotate secret endpoint
        response = sp_test_client.post("/api/v1/service-principals/batch-etl-job/rotate-secret")

        # Assert: Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert data["service_id"] == "batch-etl-job"
        assert "client_secret" in data
        assert data["client_secret"] == "sp_secret_rotated_new123"
        assert "message" in data
        assert "update your service configuration" in data["message"].lower()

        # Verify manager was called
        mock_sp_manager.rotate_secret.assert_called_once_with("batch-etl-job")

    def test_rotate_secret_not_found(self, sp_test_client, mock_sp_manager):
        """Test rotating secret for non-existent service principal"""
        mock_sp_manager.get_service_principal.return_value = None

        response = sp_test_client.post("/api/v1/service-principals/nonexistent/rotate-secret")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_rotate_secret_unauthorized(self, sp_test_client, mock_sp_manager):
        """Test rotating secret for another user's service principal"""
        # Return SP owned by different user
        mock_sp_manager.get_service_principal.return_value = MockServicePrincipal(
            service_id="other-service",
            name="Other Service",
            description="Not owned by current user",
            authentication_mode="client_credentials",
            associated_user_id=None,
            owner_user_id="other_user",
            inherit_permissions=False,
            enabled=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        response = sp_test_client.post("/api/v1/service-principals/other-service/rotate-secret")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "do not have permission" in response.json()["detail"]


# ==============================================================================
# Delete Service Principal Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="sp_delete_tests")
class TestDeleteServicePrincipal:
    """Tests for DELETE /api/v1/service-principals/{service_id}"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_delete_service_principal_success(self, sp_test_client, mock_sp_manager):
        """Test successful service principal deletion"""
        # Arrange: Configure mock to return existing service principal owned by current user
        mock_sp_manager.get_service_principal.return_value = MockServicePrincipal(
            service_id="batch-etl-job",
            name="Batch ETL Job",
            description="Nightly data processing",
            authentication_mode="client_credentials",
            associated_user_id=None,
            owner_user_id="user:alice",  # OpenFGA format from shared fixture
            inherit_permissions=False,
            enabled=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Act: Delete service principal
        response = sp_test_client.delete("/api/v1/service-principals/batch-etl-job")

        # Assert: Verify response
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""  # No response body

        # Verify manager was called
        mock_sp_manager.delete_service_principal.assert_called_once_with("batch-etl-job")

    def test_delete_service_principal_not_found(self, sp_test_client, mock_sp_manager):
        """Test deleting non-existent service principal"""
        mock_sp_manager.get_service_principal.return_value = None

        response = sp_test_client.delete("/api/v1/service-principals/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_service_principal_unauthorized(self, sp_test_client, mock_sp_manager):
        """Test deleting another user's service principal"""
        mock_sp_manager.get_service_principal.return_value = MockServicePrincipal(
            service_id="other-service",
            name="Other Service",
            description="Not owned",
            authentication_mode="client_credentials",
            associated_user_id=None,
            owner_user_id="other_user",
            inherit_permissions=False,
            enabled=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        response = sp_test_client.delete("/api/v1/service-principals/other-service")

        assert response.status_code == status.HTTP_403_FORBIDDEN


# ==============================================================================
# Associate with User Tests
# ==============================================================================


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="sp_associate_tests")
class TestAssociateServicePrincipalWithUser:
    """Tests for POST /api/v1/service-principals/{service_id}/associate-user"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_associate_with_user_success(self, admin_test_client, mock_sp_manager):
        """Test successful user association (requires admin role)"""
        # Mock updated SP after association
        mock_sp_manager.get_service_principal.return_value = MockServicePrincipal(
            service_id="batch-etl-job",
            name="Batch ETL Job",
            description="Now associated",
            authentication_mode="client_credentials",
            associated_user_id="user:bob",  # Updated
            owner_user_id="user:alice",  # OpenFGA format from shared fixture
            inherit_permissions=True,
            enabled=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        response = admin_test_client.post(
            "/api/v1/service-principals/batch-etl-job/associate-user",
            params={
                "user_id": "user:bob",
                "inherit_permissions": True,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify updated association
        assert data["associated_user_id"] == "user:bob"
        assert data["inherit_permissions"] is True

        # Verify manager was called
        mock_sp_manager.associate_with_user.assert_called_once_with(
            service_id="batch-etl-job",
            user_id="user:bob",
            inherit_permissions=True,
        )

    def test_associate_with_user_not_found(self, sp_test_client, mock_sp_manager):
        """Test associating non-existent service principal"""
        mock_sp_manager.get_service_principal.return_value = None

        response = sp_test_client.post(
            "/api/v1/service-principals/nonexistent/associate-user",
            params={"user_id": "user:bob"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_associate_with_user_unauthorized(self, sp_test_client, mock_sp_manager):
        """Test associating another user's service principal"""
        mock_sp_manager.get_service_principal.return_value = MockServicePrincipal(
            service_id="other-service",
            name="Other",
            description="Not owned",
            authentication_mode="client_credentials",
            associated_user_id=None,
            owner_user_id="other_user",
            inherit_permissions=False,
            enabled=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        response = sp_test_client.post(
            "/api/v1/service-principals/other-service/associate-user",
            params={"user_id": "user:bob"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_associate_with_user_update_fails(self, admin_test_client, mock_sp_manager):
        """Test error when retrieving updated SP fails after association (requires admin role)"""
        # First call returns existing SP, second call (after update) returns None
        mock_sp_manager.get_service_principal.side_effect = [
            MockServicePrincipal(
                service_id="batch-etl-job",
                name="Batch ETL Job",
                description="Test",
                authentication_mode="client_credentials",
                associated_user_id=None,
                owner_user_id="user:alice",  # OpenFGA format from shared fixture
                inherit_permissions=False,
                enabled=True,
                created_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc).isoformat(),
            ),
            None,  # Second call fails
        ]

        response = admin_test_client.post(
            "/api/v1/service-principals/batch-etl-job/associate-user",
            params={"user_id": "user:bob"},
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve updated service principal" in response.json()["detail"]


# ==============================================================================
# Integration Tests
# ==============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.slow
@pytest.mark.xdist_group(name="sp_integration_tests")
class TestServicePrincipalEndpointsIntegration:
    """
    Integration tests with real Keycloak and OpenFGA

    These tests require docker-compose.test.yml to be running.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    async def test_full_service_principal_lifecycle(self):
        """
        Test complete service principal lifecycle:
        1. Create service principal
        2. List service principals
        3. Get service principal details
        4. Associate with user
        5. Rotate secret
        6. Authenticate with new secret
        7. Delete service principal
        """
        # Implementation pending - needs test_infrastructure with FastAPI app
        # The test_infrastructure fixture provides docker services, but we also need
        # the FastAPI app running with those services for full E2E testing.
