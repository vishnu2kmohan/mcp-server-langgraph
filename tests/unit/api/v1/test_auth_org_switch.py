"""
Tests for Organization Switch Authorization

TDD tests for POST /api/v1/auth/switch-org endpoint.
Verifies that org switch properly validates user membership via OpenFGA.

PYTEST-XDIST FIX: Uses dual mocking strategy for xdist reliability.
"""

import gc
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_auth_org_switch")
class TestOrganizationSwitchAuthorization:
    """Tests for POST /api/v1/auth/switch-org endpoint authorization.

    Verifies that the endpoint validates user membership in target org via OpenFGA.
    """

    def setup_method(self) -> None:
        """Reset singletons before each test to ensure clean state."""
        reset_singleton_dependencies()

    def teardown_method(self) -> None:
        """Force GC and reset singletons to prevent mock accumulation."""
        reset_singleton_dependencies()
        gc.collect()

    def _create_mock_openfga_client(
        self,
        has_permission: bool = True,
        raise_error: Exception | None = None,
    ) -> AsyncMock:
        """Create a mock OpenFGA client."""
        mock_client = AsyncMock()
        if raise_error:
            mock_client.check_permission.side_effect = raise_error
        else:
            mock_client.check_permission.return_value = has_permission
        return mock_client

    def _create_app(
        self,
        mock_openfga_client: AsyncMock | None = None,
        mock_current_user: dict | None = None,
    ) -> FastAPI:
        """Create a FastAPI app with the auth router."""
        from mcp_server_langgraph.api.deps import get_openfga_client
        from mcp_server_langgraph.api.v1.auth import auth_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(auth_router, prefix="/api/v1")

        # Mock OpenFGA client dependency
        if mock_openfga_client:
            app.dependency_overrides[get_openfga_client] = lambda: mock_openfga_client

        # Mock current user authentication
        if mock_current_user:
            app.dependency_overrides[get_current_user] = lambda: mock_current_user

        return app

    def _create_client(
        self,
        mock_openfga_client: AsyncMock | None = None,
        mock_current_user: dict | None = None,
    ) -> TestClient:
        """Create a test client for the auth API."""
        return TestClient(self._create_app(mock_openfga_client, mock_current_user))

    @pytest.mark.asyncio
    async def test_switch_org_with_valid_membership_succeeds(self) -> None:
        """POST /api/v1/auth/switch-org succeeds when user has member relation."""
        mock_openfga = self._create_mock_openfga_client(has_permission=True)
        mock_user = {
            "sub": "user-123",
            "user_id": "user:alice",
            "username": "alice",
            "email": "alice@test.com",
        }

        client = self._create_client(mock_openfga, mock_user)
        response = client.post(
            "/api/v1/auth/switch-org",
            json={"orgId": "org-456"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["org_id"] == "org-456"

        # Verify OpenFGA was called with correct parameters
        mock_openfga.check_permission.assert_called_once()
        call_args = mock_openfga.check_permission.call_args
        assert "user:alice" in str(call_args) or "user-123" in str(call_args)
        assert "organization:org-456" in str(call_args)

    @pytest.mark.asyncio
    async def test_switch_org_without_membership_returns_403(self) -> None:
        """POST /api/v1/auth/switch-org returns 403 when user lacks membership."""
        mock_openfga = self._create_mock_openfga_client(has_permission=False)
        mock_user = {
            "sub": "user-123",
            "user_id": "user:bob",
            "username": "bob",
            "email": "bob@test.com",
        }

        client = self._create_client(mock_openfga, mock_user)
        response = client.post(
            "/api/v1/auth/switch-org",
            json={"orgId": "org-789"},
        )

        assert response.status_code == 403
        data = response.json()
        assert "permission" in data["detail"].lower() or "access" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_switch_org_admin_can_switch(self) -> None:
        """POST /api/v1/auth/switch-org allows admin relation access."""
        # Admin relation should also grant access
        mock_openfga = self._create_mock_openfga_client(has_permission=True)
        mock_user = {
            "sub": "admin-user",
            "user_id": "user:admin",
            "username": "admin",
            "email": "admin@test.com",
            "roles": ["admin"],
        }

        client = self._create_client(mock_openfga, mock_user)
        response = client.post(
            "/api/v1/auth/switch-org",
            json={"orgId": "org-admin-123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_switch_org_logs_audit_event(self) -> None:
        """POST /api/v1/auth/switch-org logs audit trail on successful switch."""
        mock_openfga = self._create_mock_openfga_client(has_permission=True)
        mock_user = {
            "sub": "user-123",
            "user_id": "user:charlie",
            "username": "charlie",
            "email": "charlie@test.com",
        }

        with patch("mcp_server_langgraph.api.v1.auth.logger") as mock_logger:
            client = self._create_client(mock_openfga, mock_user)
            response = client.post(
                "/api/v1/auth/switch-org",
                json={"orgId": "org-audit-test"},
            )

            assert response.status_code == 200

            # Verify audit logging occurred
            assert mock_logger.info.called
            # Check for audit-related log call
            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("org" in call.lower() or "switch" in call.lower() for call in log_calls)

    @pytest.mark.asyncio
    async def test_switch_org_empty_org_id_returns_error(self) -> None:
        """POST /api/v1/auth/switch-org returns 400 or 422 for empty org ID."""
        mock_openfga = self._create_mock_openfga_client(has_permission=True)
        mock_user = {
            "sub": "user-123",
            "user_id": "user:test",
            "username": "test",
        }

        client = self._create_client(mock_openfga, mock_user)
        response = client.post(
            "/api/v1/auth/switch-org",
            json={"orgId": ""},
        )

        # Accept both 400 (explicit check) and 422 (Pydantic validation)
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_switch_org_openfga_unavailable_fails_closed(self) -> None:
        """POST /api/v1/auth/switch-org fails when OpenFGA is unavailable."""
        # Security: Fail closed when auth service is unavailable
        mock_openfga = self._create_mock_openfga_client(raise_error=Exception("OpenFGA connection failed"))
        mock_user = {
            "sub": "user-123",
            "user_id": "user:test",
            "username": "test",
        }

        client = self._create_client(mock_openfga, mock_user)
        response = client.post(
            "/api/v1/auth/switch-org",
            json={"orgId": "org-test"},
        )

        # Should fail closed (503 or 403) - not succeed
        assert response.status_code in [403, 503]
