"""
Workflow Sharing Integration Tests

Integration tests for workflow sharing endpoints.
Tests the full request/response cycle with FastAPI TestClient.

Endpoints tested:
- GET /workflows/{id}/shares - List shares for a workflow
- POST /workflows/{id}/shares - Add a share to a workflow
- DELETE /workflows/{id}/shares/{user_id} - Remove share
- PUT /workflows/{id}/public - Toggle public visibility
- GET /workflows/shared-with-me - List workflows shared with current user
- GET /workflows/public/{share_link} - Access public workflow by link
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

pytestmark = [
    pytest.mark.integration,
    pytest.mark.api,
]


@pytest.fixture
def mock_workflow_service() -> MagicMock:
    """Create a mock workflow service for testing."""
    service = MagicMock()

    # Mock get_workflow for authorization checks
    service.get_workflow = AsyncMock(
        return_value={
            "id": "wf-123",
            "name": "Test Workflow",
            "user_id": "owner-user",
            "description": "A test workflow",
            "nodes": [],
            "edges": [],
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
    )

    # Mock sharing methods
    service.get_workflow_shares = AsyncMock(
        return_value={
            "shares": [
                {"user_id": "user-1", "email": "alice@example.com", "permission": "edit"},
                {"user_id": "user-2", "email": "bob@example.com", "permission": "view"},
            ],
            "is_public": False,
            "share_link": None,
        }
    )

    service.add_workflow_share = AsyncMock(return_value=True)
    service.remove_workflow_share = AsyncMock(return_value=True)
    service.update_workflow_public = AsyncMock(
        return_value={
            "is_public": True,
            "share_link": "abc123xyz",
        }
    )
    service.list_shared_with_me = AsyncMock(
        return_value=[
            {
                "id": "wf-shared-1",
                "name": "Shared Workflow",
                "description": "Workflow shared with me",
                "permission": "view",
            }
        ]
    )
    service.get_public_workflow = AsyncMock(
        return_value={
            "id": "wf-public-1",
            "name": "Public Workflow",
            "description": "A public workflow",
            "nodes": [],
            "edges": [],
        }
    )

    return service


@pytest.fixture
def mock_current_user() -> dict[str, Any]:
    """Mock authenticated user."""
    return {"sub": "owner-user", "preferred_username": "owner", "email": "owner@example.com"}


@pytest.fixture
def workflow_sharing_app(mock_workflow_service: MagicMock, mock_current_user: dict[str, Any]) -> FastAPI:
    """Create a test FastAPI app with the workflows router."""
    from mcp_server_langgraph.api.v1.workflows import workflows_router

    app = FastAPI()
    app.include_router(workflows_router, prefix="/api/v1")

    # Override dependencies
    from mcp_server_langgraph.api.v1 import workflows
    from mcp_server_langgraph.auth.middleware import get_current_user

    app.dependency_overrides[workflows.get_workflow_service] = lambda: mock_workflow_service
    app.dependency_overrides[get_current_user] = lambda: mock_current_user

    return app


@pytest.fixture
def workflow_sharing_client(workflow_sharing_app: FastAPI) -> TestClient:
    """Create a test client for the workflow sharing app."""
    return TestClient(workflow_sharing_app)


@pytest.mark.xdist_group(name="test_workflow_sharing_integration")
class TestGetWorkflowSharesIntegration:
    """Integration tests for GET /workflows/{id}/shares."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_shares_returns_200_for_owner(
        self, workflow_sharing_client: TestClient, mock_workflow_service: MagicMock
    ) -> None:
        """
        GIVEN an authenticated workflow owner
        WHEN GET request is made to /workflows/{id}/shares
        THEN should return 200 with shares list
        """
        response = workflow_sharing_client.get("/api/v1/workflows/wf-123/shares")

        assert response.status_code == 200
        data = response.json()
        assert "shares" in data
        assert len(data["shares"]) == 2
        assert data["is_public"] is False

    def test_get_shares_includes_share_details(
        self, workflow_sharing_client: TestClient, mock_workflow_service: MagicMock
    ) -> None:
        """
        GIVEN a workflow with shares
        WHEN GET request is made to /workflows/{id}/shares
        THEN each share should include user_id, email, and permission
        """
        response = workflow_sharing_client.get("/api/v1/workflows/wf-123/shares")

        assert response.status_code == 200
        data = response.json()
        share = data["shares"][0]
        assert "user_id" in share
        assert "email" in share
        assert "permission" in share


@pytest.mark.xdist_group(name="test_add_workflow_share_integration")
class TestAddWorkflowShareIntegration:
    """Integration tests for POST /workflows/{id}/shares."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_add_share_returns_201_for_owner(
        self, workflow_sharing_client: TestClient, mock_workflow_service: MagicMock
    ) -> None:
        """
        GIVEN an authenticated workflow owner
        WHEN POST request is made to /workflows/{id}/shares with valid data
        THEN should return 201 Created
        """
        response = workflow_sharing_client.post(
            "/api/v1/workflows/wf-123/shares",
            json={"email": "newuser@example.com", "permission": "view"},
        )

        assert response.status_code == 201
        mock_workflow_service.add_workflow_share.assert_called_once()

    def test_add_share_with_edit_permission(
        self, workflow_sharing_client: TestClient, mock_workflow_service: MagicMock
    ) -> None:
        """
        GIVEN a valid share request with edit permission
        WHEN POST request is made to /workflows/{id}/shares
        THEN should accept the permission level
        """
        response = workflow_sharing_client.post(
            "/api/v1/workflows/wf-123/shares",
            json={"email": "editor@example.com", "permission": "edit"},
        )

        assert response.status_code == 201


@pytest.mark.xdist_group(name="test_remove_workflow_share_integration")
class TestRemoveWorkflowShareIntegration:
    """Integration tests for DELETE /workflows/{id}/shares/{user_id}."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_remove_share_returns_204(self, workflow_sharing_client: TestClient, mock_workflow_service: MagicMock) -> None:
        """
        GIVEN an authenticated workflow owner
        WHEN DELETE request is made to /workflows/{id}/shares/{user_id}
        THEN should return 204 No Content
        """
        response = workflow_sharing_client.delete("/api/v1/workflows/wf-123/shares/user-to-remove")

        assert response.status_code == 204
        mock_workflow_service.remove_workflow_share.assert_called_once_with("wf-123", "user-to-remove")


@pytest.mark.xdist_group(name="test_update_workflow_public_integration")
class TestUpdateWorkflowPublicIntegration:
    """Integration tests for PUT /workflows/{id}/public."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_make_workflow_public(self, workflow_sharing_client: TestClient, mock_workflow_service: MagicMock) -> None:
        """
        GIVEN an authenticated workflow owner
        WHEN PUT request is made to make workflow public
        THEN should return 200 with share_link
        """
        response = workflow_sharing_client.put(
            "/api/v1/workflows/wf-123/public",
            json={"is_public": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_public"] is True
        assert "share_link" in data

    def test_make_workflow_private(self, workflow_sharing_client: TestClient, mock_workflow_service: MagicMock) -> None:
        """
        GIVEN a public workflow
        WHEN PUT request is made to make it private
        THEN should return 200 with cleared share_link
        """
        mock_workflow_service.update_workflow_public = AsyncMock(
            return_value={
                "is_public": False,
                "share_link": None,
            }
        )

        response = workflow_sharing_client.put(
            "/api/v1/workflows/wf-123/public",
            json={"is_public": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_public"] is False


@pytest.mark.xdist_group(name="test_shared_with_me_integration")
class TestSharedWithMeIntegration:
    """Integration tests for GET /workflows/shared-with-me."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_shared_workflows_returns_200(
        self, workflow_sharing_client: TestClient, mock_workflow_service: MagicMock
    ) -> None:
        """
        GIVEN an authenticated user
        WHEN GET request is made to /workflows/shared-with-me
        THEN should return 200 with list of shared workflows
        """
        response = workflow_sharing_client.get("/api/v1/workflows/shared-with-me")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.xdist_group(name="test_public_workflow_access_integration")
class TestPublicWorkflowAccessIntegration:
    """Integration tests for GET /workflows/public/{share_link}."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_access_public_workflow_returns_200(
        self, workflow_sharing_client: TestClient, mock_workflow_service: MagicMock
    ) -> None:
        """
        GIVEN a valid share link
        WHEN GET request is made to /workflows/public/{share_link}
        THEN should return 200 with workflow data
        """
        response = workflow_sharing_client.get("/api/v1/workflows/public/abc123xyz")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "name" in data

    def test_invalid_share_link_returns_404(
        self, workflow_sharing_client: TestClient, mock_workflow_service: MagicMock
    ) -> None:
        """
        GIVEN an invalid share link
        WHEN GET request is made to /workflows/public/{share_link}
        THEN should return 404 Not Found
        """
        mock_workflow_service.get_public_workflow = AsyncMock(return_value=None)

        response = workflow_sharing_client.get("/api/v1/workflows/public/invalid-link")

        assert response.status_code == 404


@pytest.mark.xdist_group(name="test_workflow_sharing_authorization_integration")
class TestWorkflowSharingAuthorizationIntegration:
    """Integration tests for authorization on sharing endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_non_owner_cannot_view_shares(self, mock_workflow_service: MagicMock) -> None:
        """
        GIVEN a user who is not the workflow owner
        WHEN GET request is made to /workflows/{id}/shares
        THEN should return 403 Forbidden
        """
        from mcp_server_langgraph.api.v1.workflows import workflows_router
        from mcp_server_langgraph.api.v1 import workflows
        from mcp_server_langgraph.auth.middleware import get_current_user

        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        # Non-owner user
        non_owner = {"sub": "other-user", "preferred_username": "other"}

        app.dependency_overrides[workflows.get_workflow_service] = lambda: mock_workflow_service
        app.dependency_overrides[get_current_user] = lambda: non_owner

        client = TestClient(app)
        response = client.get("/api/v1/workflows/wf-123/shares")

        assert response.status_code == 403

    def test_non_owner_cannot_add_shares(self, mock_workflow_service: MagicMock) -> None:
        """
        GIVEN a user who is not the workflow owner
        WHEN POST request is made to /workflows/{id}/shares
        THEN should return 403 Forbidden
        """
        from mcp_server_langgraph.api.v1.workflows import workflows_router
        from mcp_server_langgraph.api.v1 import workflows
        from mcp_server_langgraph.auth.middleware import get_current_user

        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        # Non-owner user
        non_owner = {"sub": "other-user", "preferred_username": "other"}

        app.dependency_overrides[workflows.get_workflow_service] = lambda: mock_workflow_service
        app.dependency_overrides[get_current_user] = lambda: non_owner

        client = TestClient(app)
        response = client.post(
            "/api/v1/workflows/wf-123/shares",
            json={"email": "test@example.com", "permission": "view"},
        )

        assert response.status_code == 403
