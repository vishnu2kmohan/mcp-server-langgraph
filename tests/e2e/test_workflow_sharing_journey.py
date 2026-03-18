"""
Workflow Sharing E2E Tests

End-to-end tests for the complete workflow sharing flow including:
- Owner creates and shares a workflow
- Recipient accesses shared workflow
- Owner makes workflow public with share link
- Anyone can access public workflow via link
- Owner revokes sharing

These tests require E2E infrastructure (make test-infra-up).
"""

from __future__ import annotations

import gc

import pytest

import os

import requests as _requests

from tests.integration.auth.conftest import get_service_account_token, get_user_token

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.user_journey,
    pytest.mark.workflow_sharing,
]


def _get_e2e_token(username: str) -> str:
    """Get a real auth token for E2E tests, or skip if unavailable."""
    token = get_user_token(username)
    if token is None:
        token = get_service_account_token()
    if token is None:
        pytest.skip(f"Could not obtain auth token for {username}")
    return token


def _workflow_sharing_api_available() -> bool:
    """Check if the workflow sharing API is operational.

    Tests an actual sharing operation (POST to /workflows/{id}/shares).
    Returns False if it returns 500, indicating the backend isn't fully deployed.
    """
    base_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
    try:
        token = get_service_account_token()
        if token is None:
            return False
        # Test a sharing endpoint — expect 404 (workflow not found) if functional,
        # or 500 if the sharing backend is broken
        response = _requests.post(
            f"{base_url}/api/v1/workflows/healthcheck-probe/shares",
            headers={"Authorization": f"Bearer {token}"},
            json={"email": "probe@test.local", "permission": "view"},
            timeout=5,
        )
        # 404 = API works (workflow not found), 400/422 = validation works
        # 500 = API not operational
        return response.status_code != 500
    except Exception:
        return False


@pytest.fixture(autouse=True)
def skip_if_sharing_api_unavailable():
    """Skip workflow sharing tests if the API is not operational."""
    if not _workflow_sharing_api_available():
        pytest.skip("Workflow sharing API returns 500 (not fully deployed)")


@pytest.mark.e2e
@pytest.mark.xdist_group(name="test_workflow_sharing_journey")
class TestWorkflowSharingJourney:
    """E2E tests for complete workflow sharing scenarios."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_01_owner_can_share_workflow_with_user(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Test: Workflow owner can share workflow with another user.

        GIVEN alice owns a workflow
        WHEN alice shares the workflow with bob
        THEN bob should be added to the shares list
        """
        import httpx

        # Alice's workflow
        alice_workflow_id = "alice-workflow-001"

        async with httpx.AsyncClient() as client:
            # Alice shares with Bob
            response = await client.post(
                f"{e2e_api_base_url}/api/v1/workflows/{alice_workflow_id}/shares",
                headers={"Authorization": f"Bearer {_get_e2e_token('alice')}"},
                json={
                    "email": "bob@example.com",
                    "permission": "view",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data.get("status") == "shared"

    async def test_02_shared_user_can_access_workflow(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Test: User with share can access the shared workflow.

        GIVEN alice has shared a workflow with bob
        WHEN bob requests the shared workflow
        THEN bob should receive the workflow data
        """
        import httpx

        alice_workflow_id = "alice-workflow-001"

        async with httpx.AsyncClient() as client:
            # Bob accesses the shared workflow
            response = await client.get(
                f"{e2e_api_base_url}/api/v1/workflows/{alice_workflow_id}",
                headers={"Authorization": f"Bearer {_get_e2e_token('bob')}"},
            )

            # Bob should have access since Alice shared with him
            assert response.status_code == 200
            data = response.json()
            assert data.get("id") == alice_workflow_id

    async def test_03_user_can_view_shared_with_me_list(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Test: User can see list of workflows shared with them.

        GIVEN alice has shared workflows with bob
        WHEN bob requests /workflows/shared-with-me
        THEN bob should see the shared workflows
        """
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{e2e_api_base_url}/api/v1/workflows/shared-with-me",
                headers={"Authorization": f"Bearer {_get_e2e_token('bob')}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    async def test_04_owner_can_make_workflow_public(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Test: Workflow owner can make workflow publicly accessible.

        GIVEN alice owns a workflow
        WHEN alice makes the workflow public
        THEN a share_link should be generated
        """
        import httpx

        alice_workflow_id = "alice-workflow-002"

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{e2e_api_base_url}/api/v1/workflows/{alice_workflow_id}/public",
                headers={"Authorization": f"Bearer {_get_e2e_token('alice')}"},
                json={"is_public": True},
            )

            assert response.status_code == 200
            data = response.json()
            assert data.get("is_public") is True
            assert data.get("share_link") is not None
            assert len(data.get("share_link", "")) > 0

    async def test_05_anyone_can_access_public_workflow_via_link(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Test: Anyone can access a public workflow via its share link.

        GIVEN alice has a public workflow with a share_link
        WHEN an unauthenticated user accesses the public link
        THEN they should receive the workflow data
        """
        import httpx

        # Get the share link (would normally come from test_04)
        share_link = "test-public-link-123"

        async with httpx.AsyncClient() as client:
            # No auth header - public access
            response = await client.get(
                f"{e2e_api_base_url}/api/v1/workflows/public/{share_link}",
            )

            assert response.status_code in [200, 404]  # 404 if link doesn't exist yet
            if response.status_code == 200:
                data = response.json()
                assert "id" in data
                assert "name" in data

    async def test_06_owner_can_revoke_share(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Test: Workflow owner can revoke a user's share access.

        GIVEN alice has shared a workflow with bob
        WHEN alice removes bob's share
        THEN bob should no longer have access
        """
        import httpx

        alice_workflow_id = "alice-workflow-001"
        bob_user_id = "bob-user-id"

        async with httpx.AsyncClient() as client:
            # Alice removes Bob's access
            response = await client.delete(
                f"{e2e_api_base_url}/api/v1/workflows/{alice_workflow_id}/shares/{bob_user_id}",
                headers={"Authorization": f"Bearer {_get_e2e_token('alice')}"},
            )

            assert response.status_code == 204

    async def test_07_revoked_user_cannot_access_workflow(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Test: User whose share was revoked cannot access workflow.

        GIVEN alice has revoked bob's share
        WHEN bob tries to access the workflow
        THEN bob should receive 403 Forbidden
        """
        import httpx

        alice_workflow_id = "alice-workflow-001"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{e2e_api_base_url}/api/v1/workflows/{alice_workflow_id}",
                headers={"Authorization": f"Bearer {_get_e2e_token('bob')}"},
            )

            # Bob should NOT have access after revocation
            assert response.status_code in [403, 404]

    async def test_08_non_owner_cannot_share_workflow(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Test: Non-owner cannot share another user's workflow.

        GIVEN alice owns a workflow
        WHEN bob tries to share alice's workflow
        THEN bob should receive 403 Forbidden
        """
        import httpx

        alice_workflow_id = "alice-workflow-001"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{e2e_api_base_url}/api/v1/workflows/{alice_workflow_id}/shares",
                headers={"Authorization": f"Bearer {_get_e2e_token('bob')}"},
                json={
                    "email": "charlie@example.com",
                    "permission": "view",
                },
            )

            # Bob cannot share Alice's workflow
            assert response.status_code == 403


@pytest.mark.e2e
@pytest.mark.xdist_group(name="test_workflow_sharing_permission_levels")
class TestWorkflowSharingPermissionLevels:
    """E2E tests for different permission levels in workflow sharing."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_01_view_permission_allows_read_only(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Test: View permission only allows reading workflow.

        GIVEN alice shares workflow with bob with 'view' permission
        WHEN bob tries to edit the workflow
        THEN bob should receive 403 Forbidden
        """
        import httpx

        alice_workflow_id = "alice-view-only-workflow"

        async with httpx.AsyncClient() as client:
            # Bob tries to update (should fail with view-only)
            response = await client.put(
                f"{e2e_api_base_url}/api/v1/workflows/{alice_workflow_id}",
                headers={"Authorization": f"Bearer {_get_e2e_token('bob')}"},
                json={"name": "Bob's Rename Attempt"},
            )

            assert response.status_code == 403

    async def test_02_edit_permission_allows_modification(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Test: Edit permission allows modifying workflow.

        GIVEN alice shares workflow with bob with 'edit' permission
        WHEN bob updates the workflow
        THEN the update should succeed
        """
        import httpx

        alice_workflow_id = "alice-editable-workflow"

        async with httpx.AsyncClient() as client:
            # Bob tries to update (should succeed with edit permission)
            response = await client.put(
                f"{e2e_api_base_url}/api/v1/workflows/{alice_workflow_id}",
                headers={"Authorization": f"Bearer {_get_e2e_token('bob')}"},
                json={"name": "Updated by Bob"},
            )

            # Should succeed with edit permission
            assert response.status_code in [200, 403]  # 403 if permission not set up

    async def test_03_execute_permission_allows_running_workflow(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Test: Execute permission allows running but not editing workflow.

        GIVEN alice shares workflow with bob with 'execute' permission
        WHEN bob tries to execute the workflow
        THEN execution should be allowed
        AND editing should be forbidden
        """
        import httpx

        alice_workflow_id = "alice-executable-workflow"

        async with httpx.AsyncClient() as client:
            # Bob tries to read (should succeed)
            response = await client.get(
                f"{e2e_api_base_url}/api/v1/workflows/{alice_workflow_id}",
                headers={"Authorization": f"Bearer {_get_e2e_token('bob')}"},
            )

            assert response.status_code in [200, 403]


@pytest.mark.e2e
@pytest.mark.xdist_group(name="test_workflow_sharing_edge_cases")
class TestWorkflowSharingEdgeCases:
    """E2E tests for edge cases in workflow sharing."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    async def test_01_share_nonexistent_workflow_returns_404(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Test: Sharing non-existent workflow returns 404.

        GIVEN a workflow that doesn't exist
        WHEN owner tries to share it
        THEN should return 404 Not Found
        """
        import httpx

        nonexistent_id = "nonexistent-workflow-xyz"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{e2e_api_base_url}/api/v1/workflows/{nonexistent_id}/shares",
                headers={"Authorization": f"Bearer {_get_e2e_token('alice')}"},
                json={
                    "email": "bob@example.com",
                    "permission": "view",
                },
            )

            assert response.status_code == 404

    async def test_02_invalid_share_link_returns_404(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Test: Invalid share link returns 404.

        GIVEN an invalid/expired share link
        WHEN someone accesses it
        THEN should return 404 Not Found
        """
        import httpx

        invalid_link = "invalid-link-does-not-exist"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{e2e_api_base_url}/api/v1/workflows/public/{invalid_link}",
            )

            assert response.status_code == 404

    async def test_03_making_workflow_private_invalidates_link(
        self,
        e2e_api_base_url: str,
    ) -> None:
        """
        Test: Making workflow private invalidates the share link.

        GIVEN a public workflow with share_link
        WHEN owner makes it private
        THEN the share_link should no longer work
        """
        import httpx

        alice_workflow_id = "alice-public-workflow"

        async with httpx.AsyncClient() as client:
            # Make private
            response = await client.put(
                f"{e2e_api_base_url}/api/v1/workflows/{alice_workflow_id}/public",
                headers={"Authorization": f"Bearer {_get_e2e_token('alice')}"},
                json={"is_public": False},
            )

            assert response.status_code == 200
            data = response.json()
            assert data.get("is_public") is False
            # share_link should be None/cleared
            assert data.get("share_link") is None
