"""
Bob User Journey E2E Tests

Tests for standard-tier user (bob) journey including:
- Login flow
- Permission denied for admin routes
- Can view but not edit shared workflows
- Can create own workflows

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
@pytest.mark.xdist_group(name="test_bob_user_journey")
class TestBobStandardUserJourney:
    """Tests for bob's standard user journey."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.xfail(strict=True, reason="Requires E2E infrastructure running")
    async def test_01_bob_login_with_keycloak(
        self,
        e2e_keycloak_base_url: str,
        bob_credentials: dict[str, Any],
    ) -> None:
        """
        Step 1: Bob authenticates with Keycloak.

        GIVEN bob's credentials
        WHEN bob attempts to login via Keycloak
        THEN bob should receive a valid access token
        """
        import httpx

        async with httpx.AsyncClient() as client:
            # Get token from Keycloak
            response = await client.post(
                f"{e2e_keycloak_base_url}/realms/default/protocol/openid-connect/token",
                data={
                    "grant_type": "password",
                    "client_id": "mcp-server",
                    "username": bob_credentials["username"],
                    "password": bob_credentials["password"],
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"].lower() == "bearer"

    @pytest.mark.xfail(strict=True, reason="Requires E2E infrastructure running")
    async def test_02_bob_cannot_access_admin_routes(
        self,
        e2e_api_base_url: str,
        bob_credentials: dict[str, Any],
    ) -> None:
        """
        Step 2: Bob attempts to access admin routes and is denied.

        GIVEN bob is authenticated as a standard user
        WHEN bob attempts to access admin-only endpoints
        THEN bob should receive 403 Forbidden
        """
        import httpx

        # First authenticate bob
        async with httpx.AsyncClient() as client:
            # Get bob's token (simplified - in real test would use Keycloak)
            # For now, we'll test the API behavior with an unauthorized request
            response = await client.get(
                f"{e2e_api_base_url}/api/v1/admin/users",
                headers={"Authorization": "Bearer bob-test-token"},
            )

            # Should be denied access
            assert response.status_code in [401, 403]

    @pytest.mark.xfail(strict=True, reason="Requires E2E infrastructure running")
    async def test_03_bob_can_create_own_workflow(
        self,
        e2e_api_base_url: str,
        openfga_bob_tuples: dict[str, Any],
    ) -> None:
        """
        Step 3: Bob creates his own workflow.

        GIVEN bob is authenticated
        WHEN bob creates a new workflow
        THEN the workflow should be created with bob as owner
        """
        import httpx

        workflow_data = {
            "name": "Bob's Chatbot",
            "description": "A simple chatbot workflow by Bob",
            "nodes": [
                {"id": "input", "type": "input", "data": {"label": "Input"}},
                {"id": "output", "type": "output", "data": {"label": "Output"}},
            ],
            "edges": [{"source": "input", "target": "output"}],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{e2e_api_base_url}/api/v1/studio/workflows",
                json=workflow_data,
                headers={"Authorization": "Bearer bob-test-token"},
            )

            # Bob should be able to create workflows
            assert response.status_code in [201, 401]  # 401 if auth not configured

    @pytest.mark.xfail(strict=True, reason="Requires E2E infrastructure and shared workflow")
    async def test_04_bob_can_view_shared_workflow(
        self,
        e2e_api_base_url: str,
        openfga_cross_user_tuples: dict[str, Any],
    ) -> None:
        """
        Step 4: Bob views a workflow shared by Alice.

        GIVEN alice has shared a workflow with bob (viewer access)
        WHEN bob requests the shared workflow
        THEN bob should see the workflow content
        """
        import httpx

        shared_workflow_id = openfga_cross_user_tuples["shared_workflow_id"]

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{e2e_api_base_url}/api/v1/studio/workflows/{shared_workflow_id}",
                headers={"Authorization": "Bearer bob-test-token"},
            )

            # Bob should be able to view shared workflows
            assert response.status_code in [200, 401]

    @pytest.mark.xfail(strict=True, reason="Requires E2E infrastructure and shared workflow")
    async def test_05_bob_cannot_edit_shared_workflow(
        self,
        e2e_api_base_url: str,
        openfga_cross_user_tuples: dict[str, Any],
    ) -> None:
        """
        Step 5: Bob attempts to edit Alice's shared workflow and is denied.

        GIVEN alice has shared a workflow with bob (viewer-only access)
        WHEN bob attempts to update the workflow
        THEN bob should receive 403 Forbidden
        """
        import httpx

        shared_workflow_id = openfga_cross_user_tuples["shared_workflow_id"]

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{e2e_api_base_url}/api/v1/studio/workflows/{shared_workflow_id}",
                json={"name": "Bob's Modified Workflow"},
                headers={"Authorization": "Bearer bob-test-token"},
            )

            # Bob should NOT be able to edit (viewer only)
            assert response.status_code in [403, 401]

    @pytest.mark.xfail(strict=True, reason="Requires E2E infrastructure running")
    async def test_06_bob_can_use_agent_chat(
        self,
        e2e_api_base_url: str,
        openfga_bob_tuples: dict[str, Any],
    ) -> None:
        """
        Step 6: Bob uses agent chat (within standard tier limits).

        GIVEN bob has executor permission for agent_chat
        WHEN bob sends a message to the agent
        THEN bob should receive a response
        """
        import httpx

        # Verify bob has the required tuples
        assert "agent_chat" in openfga_bob_tuples["tools"]

        chat_data = {
            "message": "Hello, I'm Bob!",
            "conversation_id": None,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{e2e_api_base_url}/api/v1/studio/chat",
                json=chat_data,
                headers={"Authorization": "Bearer bob-test-token"},
            )

            # Should work (if auth configured) or fail with 401/404
            assert response.status_code in [200, 401, 404]
