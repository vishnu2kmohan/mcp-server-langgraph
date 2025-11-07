"""
Integration tests for GDPR compliance endpoints.

Tests all GDPR endpoints through FastAPI test client to ensure:
1. Authentication works correctly with new dependency injection
2. All endpoints return expected responses
3. GDPR compliance requirements are met
"""

import os
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_auth_user() -> Dict[str, Any]:
    """Mock authenticated user for testing."""
    return {
        "user_id": "user:alice",
        "username": "alice",
        "email": "alice@example.com",
        "roles": ["user", "premium"],
    }


@pytest.fixture
def mock_get_current_user(mock_auth_user):
    """Mock get_current_user dependency."""

    async def _mock_get_current_user():
        return mock_auth_user

    return _mock_get_current_user


@pytest.fixture
def test_app(mock_get_current_user):
    """Create test FastAPI app with mocked auth."""
    # Set environment to development to avoid production guard
    os.environ["ENVIRONMENT"] = "development"
    os.environ["GDPR_STORAGE_BACKEND"] = "memory"

    # Import after setting env vars
    from fastapi import FastAPI

    from mcp_server_langgraph.api.gdpr import router
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(router)

    # Override the dependency
    app.dependency_overrides[get_current_user] = mock_get_current_user

    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture(autouse=True)
async def setup_gdpr_storage():
    """Initialize GDPR storage for tests (using memory backend for speed)."""
    from mcp_server_langgraph.compliance.gdpr.factory import initialize_gdpr_storage, reset_gdpr_storage

    # Initialize with memory backend for fast testing
    await initialize_gdpr_storage(backend="memory")

    yield

    # Reset after test
    reset_gdpr_storage()


@pytest.mark.gdpr
class TestGDPREndpoints:
    """Integration tests for GDPR endpoints."""

    def test_get_user_data_success(self, client, mock_auth_user):
        """Test GET /api/v1/users/me/data returns user data."""
        with patch("mcp_server_langgraph.api.gdpr.DataExportService") as mock_export:
            # Import UserDataExport to create actual Pydantic model
            from mcp_server_langgraph.compliance.gdpr.data_export import UserDataExport

            # Mock the export service to return actual UserDataExport object
            mock_instance = mock_export.return_value
            mock_instance.export_user_data = AsyncMock(
                return_value=UserDataExport(
                    export_id="test-export-123",
                    export_timestamp="2025-10-18T00:00:00Z",
                    user_id=mock_auth_user["user_id"],
                    username=mock_auth_user["username"],
                    email=mock_auth_user.get("email", "alice@example.com"),
                    profile={},
                    sessions=[],
                    conversations=[],
                    preferences={},
                    audit_log=[],
                    consents=[],
                    metadata={},
                )
            )

            response = client.get("/api/v1/users/me/data")

            assert response.status_code == 200
            data = response.json()
            assert "export_id" in data
            assert data["user_id"] == mock_auth_user["user_id"]

    def test_get_user_data_unauthorized(self, test_app):
        """Test GET /api/v1/users/me/data without auth fails."""
        # Create client without dependency override
        from fastapi import FastAPI

        app = FastAPI()
        from mcp_server_langgraph.api.gdpr import router

        app.include_router(router)
        # Don't override dependency
        client = TestClient(app)

        response = client.get("/api/v1/users/me/data")

        # Should return 401 or 403 (depending on implementation)
        assert response.status_code in (401, 403)

    def test_export_user_data_json(self, client, mock_auth_user):
        """Test GET /api/v1/users/me/export?format=json."""
        with patch("mcp_server_langgraph.api.gdpr.DataExportService") as mock_export:
            mock_instance = mock_export.return_value
            mock_instance.export_user_data_portable = AsyncMock(return_value=(b'{"data": "test"}', "application/json"))

            response = client.get("/api/v1/users/me/export?format=json")

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"
            assert "attachment" in response.headers.get("content-disposition", "")

    def test_export_user_data_csv(self, client, mock_auth_user):
        """Test GET /api/v1/users/me/export?format=csv."""
        with patch("mcp_server_langgraph.api.gdpr.DataExportService") as mock_export:
            mock_instance = mock_export.return_value
            mock_instance.export_user_data_portable = AsyncMock(return_value=(b"col1,col2\nval1,val2", "text/csv"))

            response = client.get("/api/v1/users/me/export?format=csv")

            assert response.status_code == 200
            # FastAPI may add charset to content-type
            assert "text/csv" in response.headers["content-type"]

    def test_export_user_data_invalid_format(self, client):
        """Test export with invalid format returns 422."""
        response = client.get("/api/v1/users/me/export?format=xml")

        assert response.status_code == 422  # Validation error

    def test_update_user_profile_success(self, client, mock_auth_user):
        """Test PATCH /api/v1/users/me updates profile."""
        update_data = {"name": "Alice Updated", "email": "alice.updated@example.com"}

        response = client.patch("/api/v1/users/me", json={"profile_update": update_data})

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == mock_auth_user["user_id"]
        assert data["name"] == update_data["name"]
        assert data["email"] == update_data["email"]
        assert "updated_at" in data

    def test_update_user_profile_empty_data(self, client):
        """Test PATCH /api/v1/users/me with no data returns 400."""
        response = client.patch("/api/v1/users/me", json={"profile_update": {}})

        assert response.status_code == 400
        assert "No fields provided" in response.json()["detail"]

    def test_delete_user_account_success(self, client, mock_auth_user):
        """Test DELETE /api/v1/users/me with confirm=true."""
        with patch("mcp_server_langgraph.api.gdpr.DataDeletionService") as mock_deletion:
            mock_instance = mock_deletion.return_value
            mock_instance.delete_user_account = AsyncMock(
                return_value=MagicMock(
                    success=True,
                    deletion_timestamp="2025-10-18T00:00:00Z",
                    deleted_items=10,
                    anonymized_items=2,
                    audit_record_id="audit-123",
                    errors=[],
                )
            )

            response = client.delete("/api/v1/users/me?confirm=true")

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Account deleted successfully"
            assert data["deleted_items"] == 10
            assert data["anonymized_items"] == 2

    def test_delete_user_account_without_confirm(self, client):
        """Test DELETE /api/v1/users/me without confirm returns 400."""
        response = client.delete("/api/v1/users/me")

        assert response.status_code == 422  # Missing required query param

    def test_delete_user_account_confirm_false(self, client):
        """Test DELETE /api/v1/users/me with confirm=false returns 400."""
        response = client.delete("/api/v1/users/me?confirm=false")

        assert response.status_code == 400
        assert "requires confirmation" in response.json()["detail"]

    def test_delete_user_account_failure(self, client, mock_auth_user):
        """Test DELETE /api/v1/users/me handles deletion failures."""
        with patch("mcp_server_langgraph.api.gdpr.DataDeletionService") as mock_deletion:
            mock_instance = mock_deletion.return_value
            mock_instance.delete_user_account = AsyncMock(
                return_value=MagicMock(
                    success=False,
                    errors=["Failed to delete sessions", "Failed to delete conversations"],
                    deleted_items=5,
                    anonymized_items=0,
                )
            )

            response = client.delete("/api/v1/users/me?confirm=true")

            assert response.status_code == 500
            assert "errors" in response.json()["detail"]

    def test_update_consent_success(self, client, mock_auth_user):
        """Test POST /api/v1/users/me/consent."""
        consent_data = {"consent_type": "analytics", "granted": True}

        response = client.post("/api/v1/users/me/consent", json={"consent": consent_data})

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == mock_auth_user["user_id"]
        assert "consents" in data
        assert "analytics" in data["consents"]
        assert data["consents"]["analytics"]["granted"] is True

    def test_update_consent_revoke(self, client, mock_auth_user):
        """Test POST /api/v1/users/me/consent to revoke consent."""
        # First grant
        client.post("/api/v1/users/me/consent", json={"consent": {"consent_type": "marketing", "granted": True}})

        # Then revoke
        response = client.post("/api/v1/users/me/consent", json={"consent": {"consent_type": "marketing", "granted": False}})

        assert response.status_code == 200
        data = response.json()
        assert data["consents"]["marketing"]["granted"] is False

    def test_update_consent_invalid_type(self, client):
        """Test POST /api/v1/users/me/consent with invalid type."""
        response = client.post("/api/v1/users/me/consent", json={"consent": {"consent_type": "invalid", "granted": True}})

        assert response.status_code == 422  # Validation error

    def test_get_consent_status_success(self, client, mock_auth_user):
        """Test GET /api/v1/users/me/consent."""
        # First set some consents
        client.post("/api/v1/users/me/consent", json={"consent": {"consent_type": "analytics", "granted": True}})
        client.post("/api/v1/users/me/consent", json={"consent": {"consent_type": "marketing", "granted": False}})

        response = client.get("/api/v1/users/me/consent")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == mock_auth_user["user_id"]
        assert "analytics" in data["consents"]
        assert "marketing" in data["consents"]

    def test_get_consent_status_empty(self, client, mock_auth_user):
        """Test GET /api/v1/users/me/consent with no consents."""
        response = client.get("/api/v1/users/me/consent")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == mock_auth_user["user_id"]
        # Consents should be empty or have only the user's consents
        assert isinstance(data["consents"], dict)


@pytest.mark.integration
@pytest.mark.gdpr
class TestGDPRProductionGuard:
    """Test production guard for in-memory storage."""

    def test_production_guard_triggers(self):
        """Test that production guard raises error when ENVIRONMENT=production."""
        # Set production environment
        os.environ["ENVIRONMENT"] = "production"
        os.environ["GDPR_STORAGE_BACKEND"] = "memory"

        # Importing should raise RuntimeError
        with pytest.raises(RuntimeError, match="CRITICAL.*in-memory storage"):
            # Force reimport to trigger guard
            import sys

            if "mcp_server_langgraph.api.gdpr" in sys.modules:
                del sys.modules["mcp_server_langgraph.api.gdpr"]

            import mcp_server_langgraph.api.gdpr  # noqa: F401

        # Reset environment
        os.environ["ENVIRONMENT"] = "development"

    def test_production_guard_allows_postgres(self):
        """Test that production guard allows postgres backend."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["GDPR_STORAGE_BACKEND"] = "postgres"

        try:
            # Force reimport
            import sys

            if "mcp_server_langgraph.api.gdpr" in sys.modules:
                del sys.modules["mcp_server_langgraph.api.gdpr"]

            import mcp_server_langgraph.api.gdpr  # noqa: F401

            # Should not raise
        finally:
            os.environ["ENVIRONMENT"] = "development"
            os.environ["GDPR_STORAGE_BACKEND"] = "memory"
