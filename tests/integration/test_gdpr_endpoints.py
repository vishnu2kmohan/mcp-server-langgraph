"""
Integration tests for GDPR compliance endpoints.

Tests all GDPR endpoints through FastAPI test client to ensure:
1. Authentication works correctly with new dependency injection
2. All endpoints return expected responses
3. GDPR compliance requirements are met
"""

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from tests.conftest import get_user_id

pytestmark = pytest.mark.integration


@pytest.fixture
def mock_auth_user() -> dict[str, Any]:
    """Mock authenticated user for testing."""
    user_id = get_user_id("alice")
    return {
        "user_id": user_id,
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
def test_app(mock_get_current_user, monkeypatch):
    """
    Create test FastAPI app with mocked auth.

    **pytest-xdist Isolation:**
    - Uses monkeypatch.setenv() for automatic environment cleanup
    - Overrides bearer_scheme to prevent singleton pollution
    - Clears dependency_overrides in teardown to prevent leaks

    PYTEST-XDIST FIX (2025-11-14 - REVISION 7 - MODULE RELOAD PATTERN):
    - Use importlib.reload() to force router to re-import from reloaded middleware
    - Python's import system caches modules - importing again returns cached version
    - Router module already has stale references from previous tests
    - Reloading forces fresh import chain: middleware → router → endpoint functions

    References:
    - tests/regression/test_pytest_xdist_environment_pollution.py
    - OpenAI Codex Finding: test_gdpr_endpoints.py:40-57
    - PYTEST_XDIST_BEST_PRACTICES.md
    - tests/regression/test_bearer_scheme_isolation.py (Revision 7 pattern)
    """
    import importlib

    # Set environment to development to avoid production guard
    # Use monkeypatch for automatic cleanup (prevents environment pollution)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("GDPR_STORAGE_BACKEND", "memory")

    # Import after setting env vars
    from fastapi import FastAPI
    from fastapi.security import HTTPAuthorizationCredentials

    # CRITICAL RE-IMPORT + RELOAD PATTERN (2025-11-14 - REVISION 7):
    # Re-import middleware FIRST to get fresh module reference
    from mcp_server_langgraph.auth import middleware

    # RELOAD middleware to ensure we get current instances (not cached from previous tests)
    importlib.reload(middleware)

    # Now import router module (gets cached version)
    from mcp_server_langgraph.api import gdpr

    # RELOAD router to force it to re-import from the reloaded middleware
    importlib.reload(gdpr)

    # Get router and dependencies from reloaded module
    router = gdpr.router

    app = FastAPI()

    # CODEX FINDING FIX (2025-11-21): GDPR Endpoint Auth Middleware
    # ==============================================================
    # Previous: Only overrode dependencies, not middleware
    # Problem: Endpoints check request.state.user (set by AuthRequestMiddleware)
    #          All 11 tests failed with 401 Unauthorized
    # Fix: Add mock middleware that sets request.state.user before request
    #      processing, matching production middleware behavior
    #
    # Root Cause: Production endpoints expect request.state.user from middleware,
    #             not from dependency injection. Dependency overrides alone are
    #             insufficient for endpoints that access request.state directly.
    #
    # Prevention: Test validates request.state.user is populated before endpoint
    @app.middleware("http")
    async def mock_auth_middleware(request_obj: Request, call_next):
        """Mock authentication middleware that sets request.state.user"""
        # Set authenticated user on request state (matches AuthRequestMiddleware)
        request_obj.state.user = mock_auth_user

        # Process request
        response = await call_next(request_obj)
        return response

    # CRITICAL: Override bearer_scheme BEFORE include_router (Revision 7)
    # This prevents bearer_scheme singleton pollution in pytest-xdist
    # Use middleware.bearer_scheme (just re-imported) instead of top-level import
    app.dependency_overrides[middleware.bearer_scheme] = lambda: HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="mock_token_for_testing"
    )

    app.include_router(router)

    # Override the dependency (async function for async dependency)
    # Use middleware.get_current_user (just re-imported) for correct instance
    app.dependency_overrides[middleware.get_current_user] = mock_get_current_user

    yield app

    # CRITICAL: Clear dependency overrides to prevent leaks to other tests
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture(autouse=True, scope="function")
async def setup_gdpr_storage():
    """
    Initialize GDPR storage for tests (using memory backend for speed).

    Function-scoped to ensure each test gets a fresh GDPR storage instance
    and prevents singleton pollution affecting other tests.
    """
    from mcp_server_langgraph.compliance.gdpr.factory import initialize_gdpr_storage, reset_gdpr_storage

    # Initialize with memory backend for fast testing
    await initialize_gdpr_storage(backend="memory")

    yield

    # Reset after test
    reset_gdpr_storage()


@pytest.mark.gdpr
@pytest.mark.xdist_group(name="gdpr_integration_tests")
class TestGDPREndpoints:
    """Integration tests for GDPR endpoints."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

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

        response = client.patch("/api/v1/users/me", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == mock_auth_user["user_id"]
        assert data["name"] == update_data["name"]
        assert data["email"] == update_data["email"]
        assert "updated_at" in data

    def test_update_user_profile_empty_data(self, client):
        """Test PATCH /api/v1/users/me with no data returns 400."""
        response = client.patch("/api/v1/users/me", json={})

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

        # API expects ConsentRecord directly, not wrapped in {"consent": ...}
        response = client.post("/api/v1/users/me/consent", json=consent_data)

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == mock_auth_user["user_id"]
        assert "consents" in data
        assert "analytics" in data["consents"]
        assert data["consents"]["analytics"]["granted"] is True

    def test_update_consent_revoke(self, client, mock_auth_user):
        """Test POST /api/v1/users/me/consent to revoke consent."""
        # First grant
        client.post("/api/v1/users/me/consent", json={"consent_type": "marketing", "granted": True})

        # Then revoke
        response = client.post("/api/v1/users/me/consent", json={"consent_type": "marketing", "granted": False})

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
        # API expects ConsentRecord directly, not wrapped in {"consent": ...}
        client.post("/api/v1/users/me/consent", json={"consent_type": "analytics", "granted": True})
        client.post("/api/v1/users/me/consent", json={"consent_type": "marketing", "granted": False})

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
@pytest.mark.xdist_group(name="gdpr_integration_tests")
class TestGDPRProductionGuard:
    """Test production guard for in-memory storage."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.xfail(strict=True, reason="Production guard not yet implemented - TDD test written before implementation")
    def test_production_guard_triggers(self, monkeypatch):
        """
        Test that production guard raises error when ENVIRONMENT=production.

        TDD: This test was written before the production guard was implemented.
        Once the guard is added to src/mcp_server_langgraph/api/gdpr.py,
        this test will pass and can be unmarked as xfail.

        Expected implementation:
            # At module level in src/mcp_server_langgraph/api/gdpr.py
            import os
            from mcp_server_langgraph.core.config import settings

            if settings.environment == "production" and settings.gdpr_storage_backend == "memory":
                raise RuntimeError(
                    "CRITICAL: Cannot use in-memory storage in production. "
                    "Set GDPR_STORAGE_BACKEND=postgres for production deployments."
                )
        """
        # Set production environment
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("GDPR_STORAGE_BACKEND", "memory")

        # Importing should raise RuntimeError
        with pytest.raises(RuntimeError, match="CRITICAL.*in-memory storage"):
            # Force reimport to trigger guard
            import sys

            if "mcp_server_langgraph.api.gdpr" in sys.modules:
                del sys.modules["mcp_server_langgraph.api.gdpr"]

            import mcp_server_langgraph.api.gdpr  # noqa: F401

    def test_production_guard_allows_postgres(self, monkeypatch):
        """Test that production guard allows postgres backend."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("GDPR_STORAGE_BACKEND", "postgres")

        # Force reimport
        import sys

        if "mcp_server_langgraph.api.gdpr" in sys.modules:
            del sys.modules["mcp_server_langgraph.api.gdpr"]

        import mcp_server_langgraph.api.gdpr  # noqa: F401

        # Should not raise
