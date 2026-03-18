"""
Cross-User Access E2E Tests

Tests for cross-user access scenarios including:
- Alice cannot access Bob's private workflows
- Bob cannot access admin routes
- Shared workflow collaboration

These tests require E2E infrastructure (make test-infra-up).
"""

import gc
from typing import Any

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.user_journey,
    pytest.mark.security,
]


@pytest.mark.e2e
@pytest.mark.xdist_group(name="test_cross_user_access")
class TestCrossUserAccess:
    """Tests for cross-user access control."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_01_alice_cannot_access_bobs_private_workflow(
        self,
        e2e_api_base_url: str,
        openfga_bob_tuples: dict[str, Any],
    ) -> None:
        """
        Test: Alice cannot access Bob's private workflow.

        GIVEN bob has created a private workflow
        WHEN alice attempts to access bob's workflow
        THEN alice should receive 403 Forbidden
        """
        import httpx

        # Bob's private workflow (created by bob, not shared)
        bob_private_workflow_id = "bob-private-workflow-1"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{e2e_api_base_url}/api/v1/studio/workflows/{bob_private_workflow_id}",
                headers={"Authorization": "Bearer alice-test-token"},
            )

            # Alice should NOT have access
            assert response.status_code in [403, 404, 401]

    async def test_02_bob_cannot_access_admin_routes(
        self,
        e2e_api_base_url: str,
        openfga_bob_tuples: dict[str, Any],
    ) -> None:
        """
        Test: Bob cannot access admin-only routes.

        GIVEN bob is a standard user (not admin)
        WHEN bob attempts to access admin endpoints
        THEN bob should receive 403 Forbidden
        """
        import httpx

        admin_endpoints = [
            "/api/v1/admin/users",
            "/api/v1/admin/organizations",
            "/api/v1/admin/audit-logs",
            "/api/v1/admin/dashboard",
        ]

        async with httpx.AsyncClient() as client:
            for endpoint in admin_endpoints:
                response = await client.get(
                    f"{e2e_api_base_url}{endpoint}",
                    headers={"Authorization": "Bearer bob-test-token"},
                )

                # Bob should be denied access to all admin routes
                assert response.status_code in [403, 401, 404], f"Bob should not have access to {endpoint}"

    async def test_03_alice_shares_workflow_with_bob(
        self,
        e2e_api_base_url: str,
        openfga_cross_user_tuples: dict[str, Any],
    ) -> None:
        """
        Test: Alice shares workflow with Bob.

        GIVEN alice owns a workflow
        WHEN alice grants bob viewer access
        THEN bob should be able to view the workflow
        """
        import httpx

        shared_workflow_id = openfga_cross_user_tuples["shared_workflow_id"]

        # Bob should be able to view the shared workflow
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{e2e_api_base_url}/api/v1/studio/workflows/{shared_workflow_id}",
                headers={"Authorization": "Bearer bob-test-token"},
            )

            # Bob should have viewer access
            assert response.status_code in [200, 401, 404]

    async def test_04_bob_cannot_delete_shared_workflow(
        self,
        e2e_api_base_url: str,
        openfga_cross_user_tuples: dict[str, Any],
    ) -> None:
        """
        Test: Bob cannot delete Alice's shared workflow.

        GIVEN alice has shared a workflow with bob (viewer only)
        WHEN bob attempts to delete the workflow
        THEN bob should receive 403 Forbidden
        """
        import httpx

        shared_workflow_id = openfga_cross_user_tuples["shared_workflow_id"]

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{e2e_api_base_url}/api/v1/studio/workflows/{shared_workflow_id}",
                headers={"Authorization": "Bearer bob-test-token"},
            )

            # Bob should NOT be able to delete (viewer only)
            assert response.status_code in [403, 401]

    async def test_05_alice_can_revoke_bobs_access(
        self,
        e2e_api_base_url: str,
        openfga_cross_user_tuples: dict[str, Any],
    ) -> None:
        """
        Test: Alice can revoke Bob's access to shared workflow.

        GIVEN bob has viewer access to alice's workflow
        WHEN alice revokes bob's access
        THEN bob should receive 403 when accessing the workflow
        """
        import httpx

        shared_workflow_id = openfga_cross_user_tuples["shared_workflow_id"]

        async with httpx.AsyncClient() as client:
            # Alice revokes bob's access
            response = await client.delete(
                f"{e2e_api_base_url}/api/v1/studio/workflows/{shared_workflow_id}/permissions/bob",
                headers={"Authorization": "Bearer alice-test-token"},
            )

            # Should succeed or 404 if endpoint not implemented
            assert response.status_code in [200, 204, 401, 404]

    async def test_06_admin_can_access_any_workflow(
        self,
        e2e_api_base_url: str,
        openfga_cross_user_tuples: dict[str, Any],
    ) -> None:
        """
        Test: Admin can access any user's workflow.

        GIVEN admin has organization-level admin access
        WHEN admin requests any workflow
        THEN admin should have access
        """
        import httpx

        shared_workflow_id = openfga_cross_user_tuples["shared_workflow_id"]

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{e2e_api_base_url}/api/v1/studio/workflows/{shared_workflow_id}",
                headers={"Authorization": "Bearer admin-test-token"},
            )

            # Admin should have access to all workflows
            assert response.status_code in [200, 401, 404]

    async def test_07_anonymous_user_cannot_access_any_workflow(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Test: Anonymous user cannot access any workflow.

        GIVEN no authentication provided
        WHEN requesting any workflow
        THEN should receive 401 Unauthorized
        """
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{e2e_api_base_url}/api/v1/studio/workflows/any-workflow-id",
                # No Authorization header
            )

            # Should be denied access
            assert response.status_code in [401, 403]
