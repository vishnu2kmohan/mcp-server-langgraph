"""
Workflow Sharing API Tests

TDD tests for workflow sharing endpoints (Phase 6).

Endpoints:
- GET /workflows/{id}/shares - List shares for a workflow
- POST /workflows/{id}/shares - Add a share to a workflow
- DELETE /workflows/{id}/shares/{user_id} - Remove share
- PUT /workflows/{id}/public - Toggle public visibility
- GET /workflows/shared-with-me - List workflows shared with current user
- GET /workflows/public/{share_link} - Access public workflow by link

Requirements:
- Only workflow owner can manage shares
- Shares have permission levels: view, edit, execute
- Public workflows accessible via share_link
- 404 for non-existent workflows
- 403 for non-owners attempting to share
"""

import gc

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import status

from mcp_server_langgraph.api.v1.workflows import workflows_router

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestWorkflowShareModels:
    """Tests for workflow sharing Pydantic models."""

    def test_workflow_share_model_exists(self) -> None:
        """WorkflowShare model should exist with required fields."""
        from mcp_server_langgraph.api.v1.workflows import WorkflowShare

        schema = WorkflowShare.model_json_schema()
        properties = schema.get("properties", {})

        # Required fields
        assert "user_id" in properties
        assert "email" in properties
        assert "permission" in properties

    def test_workflow_share_permission_values(self) -> None:
        """Permission should be constrained to view, edit, execute."""
        from mcp_server_langgraph.api.v1.workflows import WorkflowShare

        # Valid permissions should work
        share = WorkflowShare(user_id="user-1", email="test@example.com", permission="view")
        assert share.permission == "view"

        share = WorkflowShare(user_id="user-1", email="test@example.com", permission="edit")
        assert share.permission == "edit"

        share = WorkflowShare(user_id="user-1", email="test@example.com", permission="execute")
        assert share.permission == "execute"

    def test_workflow_shares_response_model_exists(self) -> None:
        """WorkflowSharesResponse model should exist with required fields."""
        from mcp_server_langgraph.api.v1.workflows import WorkflowSharesResponse

        schema = WorkflowSharesResponse.model_json_schema()
        properties = schema.get("properties", {})

        # Required fields
        assert "shares" in properties
        assert "is_public" in properties
        assert "share_link" in properties

    def test_add_workflow_share_request_model_exists(self) -> None:
        """AddWorkflowShareRequest model should exist."""
        from mcp_server_langgraph.api.v1.workflows import AddWorkflowShareRequest

        schema = AddWorkflowShareRequest.model_json_schema()
        properties = schema.get("properties", {})

        assert "email" in properties
        assert "permission" in properties


class TestGetWorkflowSharesEndpoint:
    """Tests for GET /workflows/{id}/shares endpoint."""

    def test_get_shares_endpoint_exists(self) -> None:
        """GET /workflows/{workflow_id}/shares endpoint should exist."""
        route_paths = [route.path for route in workflows_router.routes]
        assert "/workflows/{workflow_id}/shares" in route_paths

    def test_get_shares_endpoint_method_is_get(self) -> None:
        """The endpoint should accept GET method."""
        for route in workflows_router.routes:
            if hasattr(route, "path") and route.path == "/workflows/{workflow_id}/shares":
                assert "GET" in route.methods
                return
        pytest.fail("GET /workflows/{workflow_id}/shares route not found")


class TestAddWorkflowShareEndpoint:
    """Tests for POST /workflows/{id}/shares endpoint."""

    def test_add_share_endpoint_exists(self) -> None:
        """POST /workflows/{workflow_id}/shares endpoint should exist."""
        route_paths = [route.path for route in workflows_router.routes]
        assert "/workflows/{workflow_id}/shares" in route_paths

    def test_add_share_endpoint_method_is_post(self) -> None:
        """The endpoint should accept POST method."""
        for route in workflows_router.routes:
            if hasattr(route, "path") and route.path == "/workflows/{workflow_id}/shares":
                if "POST" in route.methods:
                    return
        pytest.fail("POST /workflows/{workflow_id}/shares route not found")


class TestRemoveWorkflowShareEndpoint:
    """Tests for DELETE /workflows/{id}/shares/{user_id} endpoint."""

    def test_remove_share_endpoint_exists(self) -> None:
        """DELETE /workflows/{workflow_id}/shares/{user_id} endpoint should exist."""
        route_paths = [route.path for route in workflows_router.routes]
        assert "/workflows/{workflow_id}/shares/{user_id}" in route_paths

    def test_remove_share_endpoint_method_is_delete(self) -> None:
        """The endpoint should accept DELETE method."""
        for route in workflows_router.routes:
            if hasattr(route, "path") and route.path == "/workflows/{workflow_id}/shares/{user_id}":
                assert "DELETE" in route.methods
                return
        pytest.fail("DELETE /workflows/{workflow_id}/shares/{user_id} route not found")

    def test_remove_share_returns_204_status(self) -> None:
        """The endpoint should return 204 No Content on success."""
        for route in workflows_router.routes:
            if hasattr(route, "path") and route.path == "/workflows/{workflow_id}/shares/{user_id}":
                assert route.status_code == status.HTTP_204_NO_CONTENT
                return
        pytest.fail("DELETE /workflows/{workflow_id}/shares/{user_id} route not found")


class TestUpdateWorkflowPublicEndpoint:
    """Tests for PUT /workflows/{id}/public endpoint."""

    def test_update_public_endpoint_exists(self) -> None:
        """PUT /workflows/{workflow_id}/public endpoint should exist."""
        route_paths = [route.path for route in workflows_router.routes]
        assert "/workflows/{workflow_id}/public" in route_paths

    def test_update_public_endpoint_method_is_put(self) -> None:
        """The endpoint should accept PUT method."""
        for route in workflows_router.routes:
            if hasattr(route, "path") and route.path == "/workflows/{workflow_id}/public":
                assert "PUT" in route.methods
                return
        pytest.fail("PUT /workflows/{workflow_id}/public route not found")


class TestSharedWithMeEndpoint:
    """Tests for GET /workflows/shared-with-me endpoint."""

    def test_shared_with_me_endpoint_exists(self) -> None:
        """GET /workflows/shared-with-me endpoint should exist."""
        route_paths = [route.path for route in workflows_router.routes]
        assert "/workflows/shared-with-me" in route_paths

    def test_shared_with_me_endpoint_method_is_get(self) -> None:
        """The endpoint should accept GET method."""
        for route in workflows_router.routes:
            if hasattr(route, "path") and route.path == "/workflows/shared-with-me":
                assert "GET" in route.methods
                return
        pytest.fail("GET /workflows/shared-with-me route not found")


class TestPublicWorkflowAccessEndpoint:
    """Tests for GET /workflows/public/{share_link} endpoint."""

    def test_public_access_endpoint_exists(self) -> None:
        """GET /workflows/public/{share_link} endpoint should exist."""
        route_paths = [route.path for route in workflows_router.routes]
        assert "/workflows/public/{share_link}" in route_paths

    def test_public_access_endpoint_method_is_get(self) -> None:
        """The endpoint should accept GET method."""
        for route in workflows_router.routes:
            if hasattr(route, "path") and route.path == "/workflows/public/{share_link}":
                assert "GET" in route.methods
                return
        pytest.fail("GET /workflows/public/{share_link} route not found")


@pytest.mark.xdist_group(name="test_workflow_sharing_integration")
class TestWorkflowSharingIntegration:
    """Integration-style unit tests for workflow sharing functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_service(self) -> MagicMock:
        """Create a mock WorkflowServiceAdapter with sharing methods."""
        service = MagicMock()
        # Mock get_workflow for authorization check - returns workflow dict owned by mock user
        # Must be a dict since require_workflow_owner calls workflow.get("user_id")
        service.get_workflow = AsyncMock(return_value={"id": "wf-123", "user_id": "owner-123", "name": "Test Workflow"})
        service.get_workflow_shares = AsyncMock(
            return_value={
                "shares": [
                    {"user_id": "user-1", "email": "alice@example.com", "permission": "edit"},
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
                "share_link": "abc123",
            }
        )
        service.list_shared_with_me = AsyncMock(return_value=[])
        service.get_public_workflow = AsyncMock(return_value=None)
        return service

    @pytest.fixture
    def mock_current_user(self) -> dict[str, str]:
        """Create a mock current user for authorization.

        Uses 'sub' as the user ID key (matches _get_user_id implementation).
        """
        return {"sub": "owner-123", "email": "owner@example.com"}

    @pytest.mark.asyncio
    async def test_get_shares_returns_shares_list(self, mock_service: MagicMock, mock_current_user: dict[str, str]) -> None:
        """GET /workflows/{id}/shares should return shares list."""
        from mcp_server_langgraph.api.v1.workflows import get_workflow_shares

        # GIVEN a workflow with shares
        mock_service.get_workflow_shares = AsyncMock(
            return_value={
                "shares": [
                    {"user_id": "user-1", "email": "alice@example.com", "permission": "edit"},
                    {"user_id": "user-2", "email": "bob@example.com", "permission": "view"},
                ],
                "is_public": False,
                "share_link": None,
            }
        )

        # WHEN calling the endpoint handler
        result = await get_workflow_shares(
            workflow_id="wf-123",
            service=mock_service,
            current_user=mock_current_user,
        )

        # THEN should return shares response
        assert len(result.shares) == 2
        assert result.is_public is False
        mock_service.get_workflow_shares.assert_called_once_with("wf-123")

    @pytest.mark.asyncio
    async def test_add_share_calls_service(self, mock_service: MagicMock, mock_current_user: dict[str, str]) -> None:
        """POST /workflows/{id}/shares should add a share."""
        from mcp_server_langgraph.api.v1.workflows import (
            add_workflow_share,
            AddWorkflowShareRequest,
        )

        # GIVEN a share request
        request = AddWorkflowShareRequest(email="test@example.com", permission="edit")

        # WHEN calling the endpoint handler
        await add_workflow_share(
            workflow_id="wf-123",
            request=request,
            service=mock_service,
            current_user=mock_current_user,
        )

        # THEN service should be called
        mock_service.add_workflow_share.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_share_returns_none(self, mock_service: MagicMock, mock_current_user: dict[str, str]) -> None:
        """DELETE /workflows/{id}/shares/{user_id} should return None (204)."""
        from mcp_server_langgraph.api.v1.workflows import remove_workflow_share

        # WHEN calling the endpoint handler
        result = await remove_workflow_share(
            workflow_id="wf-123",
            user_id="user-456",
            service=mock_service,
            current_user=mock_current_user,
        )

        # THEN should return None and call service
        assert result is None
        mock_service.remove_workflow_share.assert_called_once_with("wf-123", "user-456")

    @pytest.mark.asyncio
    async def test_update_public_returns_link(self, mock_service: MagicMock, mock_current_user: dict[str, str]) -> None:
        """PUT /workflows/{id}/public should return share link when made public."""
        from mcp_server_langgraph.api.v1.workflows import (
            update_workflow_public,
            UpdateWorkflowPublicRequest,
        )

        # GIVEN a request to make workflow public
        request = UpdateWorkflowPublicRequest(is_public=True)
        mock_service.update_workflow_public = AsyncMock(
            return_value={
                "is_public": True,
                "share_link": "abc123xyz",
            }
        )

        # WHEN calling the endpoint handler
        result = await update_workflow_public(
            workflow_id="wf-123",
            request=request,
            service=mock_service,
            current_user=mock_current_user,
        )

        # THEN should return public status and link
        assert result["is_public"] is True
        assert result["share_link"] == "abc123xyz"

    @pytest.mark.asyncio
    async def test_workflow_not_found_raises_404(self, mock_service: MagicMock, mock_current_user: dict[str, str]) -> None:
        """Should raise 404 if workflow not found."""
        from fastapi import HTTPException
        from mcp_server_langgraph.api.v1.workflows import get_workflow_shares

        # GIVEN workflow doesn't exist (get_workflow returns None)
        mock_service.get_workflow = AsyncMock(return_value=None)

        # WHEN/THEN should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await get_workflow_shares(
                workflow_id="nonexistent",
                service=mock_service,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
