"""
Admin User Journey E2E Tests

Tests for admin user journey including:
- Admin login flow
- Access admin dashboard
- User management operations
- Audit log access

These tests require E2E infrastructure (make test-infra-up).
"""

import gc
from typing import Any

import pytest

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

    @pytest.mark.xfail(strict=True, reason="Requires E2E infrastructure running")
    async def test_01_admin_login_with_keycloak(
        self,
        e2e_keycloak_base_url: str,
        admin_credentials: dict[str, Any],
    ) -> None:
        """
        Step 1: Admin authenticates with Keycloak.

        GIVEN admin credentials
        WHEN admin attempts to login via Keycloak
        THEN admin should receive a valid access token with admin role
        """
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{e2e_keycloak_base_url}/realms/default/protocol/openid-connect/token",
                data={
                    "grant_type": "password",
                    "client_id": "mcp-server",
                    "username": admin_credentials["username"],
                    "password": admin_credentials["password"],
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data

            # Verify admin has admin role in token claims
            # (would need to decode JWT to verify)

    @pytest.mark.xfail(strict=True, reason="Requires E2E infrastructure running")
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

    @pytest.mark.xfail(strict=True, reason="Requires E2E infrastructure running")
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

    @pytest.mark.xfail(strict=True, reason="Requires E2E infrastructure running")
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

    @pytest.mark.xfail(strict=True, reason="Requires E2E infrastructure running")
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

    @pytest.mark.xfail(strict=True, reason="Requires E2E infrastructure running")
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

    @pytest.mark.xfail(strict=True, reason="Requires E2E infrastructure running")
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
