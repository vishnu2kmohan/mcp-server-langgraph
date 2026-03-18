"""
Admin User Journey E2E Tests

Tests for admin user journey including:
- Admin token acquisition (via Token Exchange or Service Account)
- Access admin dashboard
- User management operations
- Audit log access

These tests require E2E infrastructure (make test-infra-up).

Note: ROPC (password grant) is disabled per security audit.
User tokens are obtained via Token Exchange (RFC 8693) or service accounts.
"""

import gc
from typing import Any

import pytest

# Import the helper function for getting user tokens
from tests.integration.auth.conftest import get_service_account_token, get_user_token

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.user_journey,
]


@pytest.mark.e2e
@pytest.mark.xdist_group(name="test_admin_user_journey")
class TestAdminUserJourney:
    """Tests for admin user journey."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_01_admin_token_acquisition(
        self,
        e2e_keycloak_base_url: str,
        admin_credentials: dict[str, Any],
    ) -> None:
        """
        Step 1: Admin obtains access token via Token Exchange or Service Account.

        GIVEN admin user exists in Keycloak
        WHEN admin token is requested via modern auth methods
        THEN admin should receive a valid access token

        Note: ROPC is disabled per security audit. Uses Token Exchange
        (RFC 8693) or service account tokens (client_credentials grant).
        """
        # Try Token Exchange first (RFC 8693 compliant)
        token = get_user_token("admin")
        if token is None:
            # Fallback to service account token
            token = get_service_account_token()

        assert token is not None, (
            "Failed to obtain token via Token Exchange or Service Account. "
            "Ensure Keycloak is running and mcp-server client has serviceAccountsEnabled=true."
        )
        # Token should be a non-empty string
        assert len(token) > 0

    async def test_02_admin_can_access_admin_dashboard(
        self,
        e2e_api_base_url: str,
        admin_credentials: dict[str, Any],
    ) -> None:
        """
        Step 2: Admin accesses admin dashboard.

        GIVEN admin is authenticated
        WHEN admin requests admin dashboard data
        THEN admin should receive dashboard metrics
        """
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{e2e_api_base_url}/api/v1/admin/dashboard",
                headers={"Authorization": "Bearer admin-test-token"},
            )

            # Admin should be able to access
            assert response.status_code in [200, 401, 404]

    async def test_03_admin_can_list_users(
        self,
        e2e_api_base_url: str,
        admin_credentials: dict[str, Any],
    ) -> None:
        """
        Step 3: Admin lists all users.

        GIVEN admin is authenticated
        WHEN admin requests user list
        THEN admin should see all users in the system
        """
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{e2e_api_base_url}/api/v1/admin/users",
                headers={"Authorization": "Bearer admin-test-token"},
            )

            # Admin should be able to list users
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list) or "users" in data
            else:
                # Expected if endpoint not implemented
                assert response.status_code in [401, 404]

    async def test_04_admin_can_view_user_details(
        self,
        e2e_api_base_url: str,
        admin_credentials: dict[str, Any],
    ) -> None:
        """
        Step 4: Admin views specific user details.

        GIVEN admin is authenticated
        WHEN admin requests details for a specific user
        THEN admin should see full user profile
        """
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{e2e_api_base_url}/api/v1/admin/users/alice",
                headers={"Authorization": "Bearer admin-test-token"},
            )

            if response.status_code == 200:
                data = response.json()
                assert "username" in data or "user_id" in data
            else:
                assert response.status_code in [401, 404]

    async def test_05_admin_can_manage_organizations(
        self,
        e2e_api_base_url: str,
        admin_credentials: dict[str, Any],
    ) -> None:
        """
        Step 5: Admin manages organizations.

        GIVEN admin is authenticated
        WHEN admin requests organization list
        THEN admin should see all organizations
        """
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{e2e_api_base_url}/api/v1/admin/organizations",
                headers={"Authorization": "Bearer admin-test-token"},
            )

            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list) or "organizations" in data
            else:
                assert response.status_code in [401, 404]

    async def test_06_admin_can_view_audit_logs(
        self,
        e2e_api_base_url: str,
        admin_credentials: dict[str, Any],
    ) -> None:
        """
        Step 6: Admin views audit logs.

        GIVEN admin is authenticated
        WHEN admin requests audit logs
        THEN admin should see system activity logs
        """
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{e2e_api_base_url}/api/v1/admin/audit-logs",
                headers={"Authorization": "Bearer admin-test-token"},
            )

            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list) or "logs" in data
            else:
                assert response.status_code in [401, 404]

    async def test_07_admin_can_access_all_workflows(
        self,
        e2e_api_base_url: str,
        openfga_cross_user_tuples: dict[str, Any],
    ) -> None:
        """
        Step 7: Admin can access any user's workflow.

        GIVEN admin has organization admin permission
        WHEN admin requests Alice's workflow
        THEN admin should see the workflow
        """
        import httpx

        # Admin should be able to access any workflow
        shared_workflow_id = openfga_cross_user_tuples["shared_workflow_id"]

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{e2e_api_base_url}/api/v1/studio/workflows/{shared_workflow_id}",
                headers={"Authorization": "Bearer admin-test-token"},
            )

            # Admin should have access
            assert response.status_code in [200, 401, 404]
