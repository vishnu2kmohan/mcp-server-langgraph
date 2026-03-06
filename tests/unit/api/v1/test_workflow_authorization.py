"""
Workflow Authorization Tests

TDD tests for workflow ownership authorization (Phase 6).

Authorization requirements:
- Only workflow owner can manage shares
- 403 Forbidden for non-owners
- 404 Not Found for non-existent workflows
- 401 Unauthorized for unauthenticated requests
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, status

if TYPE_CHECKING:
    pass

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestRequireWorkflowOwnerDependency:
    """Tests for require_workflow_owner authorization dependency."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_require_workflow_owner_function_exists(self) -> None:
        """require_workflow_owner should be importable from dependencies."""
        from mcp_server_langgraph.auth.dependencies import require_workflow_owner

        assert callable(require_workflow_owner)

    @pytest.mark.asyncio
    async def test_owner_can_access_workflow(self) -> None:
        """Workflow owner should be authorized to access sharing endpoints."""
        # Use the internal helper function for unit testing authorization logic
        from mcp_server_langgraph.api.v1.workflows import _require_workflow_owner_with_service

        # GIVEN a user who owns the workflow
        mock_service = MagicMock()
        mock_service.get_workflow = AsyncMock(
            return_value={
                "id": "wf-123",
                "name": "Test Workflow",
                "user_id": "user-alice",  # Owner
            }
        )
        current_user = {"sub": "user-alice", "preferred_username": "alice"}

        # WHEN checking ownership
        result = await _require_workflow_owner_with_service(
            workflow_id="wf-123",
            current_user=current_user,
            service=mock_service,
        )

        # THEN should return the workflow (no exception)
        assert result["id"] == "wf-123"
        mock_service.get_workflow.assert_called_once_with("wf-123")

    @pytest.mark.asyncio
    async def test_non_owner_gets_403_forbidden(self) -> None:
        """Non-owner should receive 403 Forbidden."""
        from mcp_server_langgraph.api.v1.workflows import _require_workflow_owner_with_service

        # GIVEN a user who does NOT own the workflow
        mock_service = MagicMock()
        mock_service.get_workflow = AsyncMock(
            return_value={
                "id": "wf-123",
                "name": "Test Workflow",
                "user_id": "user-alice",  # Owner is alice
            }
        )
        current_user = {"sub": "user-bob", "preferred_username": "bob"}  # Bob is not owner

        # WHEN checking ownership
        # THEN should raise 403 Forbidden
        with pytest.raises(HTTPException) as exc_info:
            await _require_workflow_owner_with_service(
                workflow_id="wf-123",
                current_user=current_user,
                service=mock_service,
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "not authorized" in exc_info.value.detail.lower() or "owner" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_nonexistent_workflow_gets_404(self) -> None:
        """Non-existent workflow should return 404 Not Found."""
        from mcp_server_langgraph.api.v1.workflows import _require_workflow_owner_with_service

        # GIVEN workflow does not exist
        mock_service = MagicMock()
        mock_service.get_workflow = AsyncMock(return_value=None)
        current_user = {"sub": "user-alice", "preferred_username": "alice"}

        # WHEN checking ownership
        # THEN should raise 404 Not Found
        with pytest.raises(HTTPException) as exc_info:
            await _require_workflow_owner_with_service(
                workflow_id="nonexistent-wf",
                current_user=current_user,
                service=mock_service,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_admin_can_access_any_workflow(self) -> None:
        """Admin users should be able to access any workflow."""
        from mcp_server_langgraph.api.v1.workflows import _require_workflow_owner_with_service

        # GIVEN an admin user who does NOT own the workflow
        mock_service = MagicMock()
        mock_service.get_workflow = AsyncMock(
            return_value={
                "id": "wf-123",
                "name": "Test Workflow",
                "user_id": "user-alice",  # Owner is alice
            }
        )
        current_user = {
            "sub": "user-admin",
            "preferred_username": "admin",
            "roles": ["admin"],  # Admin role
        }

        # WHEN checking ownership
        result = await _require_workflow_owner_with_service(
            workflow_id="wf-123",
            current_user=current_user,
            service=mock_service,
        )

        # THEN admin should have access
        assert result["id"] == "wf-123"

    @pytest.mark.asyncio
    async def test_user_id_extracted_from_sub_claim(self) -> None:
        """User ID should be extracted from 'sub' claim first."""
        from mcp_server_langgraph.api.v1.workflows import _require_workflow_owner_with_service

        # GIVEN user with both sub and preferred_username
        mock_service = MagicMock()
        mock_service.get_workflow = AsyncMock(
            return_value={
                "id": "wf-123",
                "name": "Test Workflow",
                "user_id": "user:alice",  # OpenFGA format
            }
        )
        current_user = {
            "sub": "user:alice",  # Should match
            "preferred_username": "alice-different",  # Different
        }

        # WHEN checking ownership
        result = await _require_workflow_owner_with_service(
            workflow_id="wf-123",
            current_user=current_user,
            service=mock_service,
        )

        # THEN should match on 'sub' claim
        assert result["id"] == "wf-123"

    @pytest.mark.asyncio
    async def test_user_id_fallback_to_preferred_username(self) -> None:
        """User ID should fallback to 'preferred_username' if 'sub' missing."""
        from mcp_server_langgraph.api.v1.workflows import _require_workflow_owner_with_service

        # GIVEN user with only preferred_username
        mock_service = MagicMock()
        mock_service.get_workflow = AsyncMock(
            return_value={
                "id": "wf-123",
                "name": "Test Workflow",
                "user_id": "alice",  # Plain username
            }
        )
        current_user = {
            "preferred_username": "alice",  # Should match
        }

        # WHEN checking ownership
        result = await _require_workflow_owner_with_service(
            workflow_id="wf-123",
            current_user=current_user,
            service=mock_service,
        )

        # THEN should match on 'preferred_username'
        assert result["id"] == "wf-123"


class TestWorkflowSharingEndpointAuthorization:
    """Tests for authorization on workflow sharing endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_service(self) -> MagicMock:
        """Create a mock WorkflowServiceAdapter."""
        service = MagicMock()
        service.get_workflow = AsyncMock(
            return_value={
                "id": "wf-123",
                "name": "Test Workflow",
                "user_id": "user-owner",
            }
        )
        service.get_workflow_shares = AsyncMock(
            return_value={
                "shares": [],
                "is_public": False,
                "share_link": None,
            }
        )
        service.add_workflow_share = AsyncMock(return_value=True)
        service.remove_workflow_share = AsyncMock(return_value=True)
        service.update_workflow_public = AsyncMock(return_value={"is_public": True, "share_link": "abc123"})
        return service

    @pytest.mark.asyncio
    async def test_get_shares_requires_owner(self, mock_service: MagicMock) -> None:
        """GET /workflows/{id}/shares should require ownership."""
        from mcp_server_langgraph.api.v1.workflows import (
            get_workflow_shares_authorized,
        )

        # GIVEN a non-owner
        current_user = {"sub": "user-other", "preferred_username": "other"}

        # WHEN/THEN should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await get_workflow_shares_authorized(
                workflow_id="wf-123",
                current_user=current_user,
                service=mock_service,
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_add_share_requires_owner(self, mock_service: MagicMock) -> None:
        """POST /workflows/{id}/shares should require ownership."""
        from mcp_server_langgraph.api.v1.workflows import (
            AddWorkflowShareRequest,
            add_workflow_share_authorized,
        )

        # GIVEN a non-owner
        current_user = {"sub": "user-other", "preferred_username": "other"}
        request = AddWorkflowShareRequest(email="test@example.com", permission="view")

        # WHEN/THEN should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await add_workflow_share_authorized(
                workflow_id="wf-123",
                request=request,
                current_user=current_user,
                service=mock_service,
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_remove_share_requires_owner(self, mock_service: MagicMock) -> None:
        """DELETE /workflows/{id}/shares/{user_id} should require ownership."""
        from mcp_server_langgraph.api.v1.workflows import (
            remove_workflow_share_authorized,
        )

        # GIVEN a non-owner
        current_user = {"sub": "user-other", "preferred_username": "other"}

        # WHEN/THEN should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await remove_workflow_share_authorized(
                workflow_id="wf-123",
                user_id="user-to-remove",
                current_user=current_user,
                service=mock_service,
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_update_public_requires_owner(self, mock_service: MagicMock) -> None:
        """PUT /workflows/{id}/public should require ownership."""
        from mcp_server_langgraph.api.v1.workflows import (
            UpdateWorkflowPublicRequest,
            update_workflow_public_authorized,
        )

        # GIVEN a non-owner
        current_user = {"sub": "user-other", "preferred_username": "other"}
        request = UpdateWorkflowPublicRequest(is_public=True)

        # WHEN/THEN should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await update_workflow_public_authorized(
                workflow_id="wf-123",
                request=request,
                current_user=current_user,
                service=mock_service,
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_owner_can_get_shares(self, mock_service: MagicMock) -> None:
        """Owner should be able to get shares."""
        from mcp_server_langgraph.api.v1.workflows import (
            get_workflow_shares_authorized,
        )

        # GIVEN the owner
        current_user = {"sub": "user-owner", "preferred_username": "owner"}

        # WHEN getting shares
        result = await get_workflow_shares_authorized(
            workflow_id="wf-123",
            current_user=current_user,
            service=mock_service,
        )

        # THEN should succeed
        assert result.shares == []
        assert result.is_public is False

    @pytest.mark.asyncio
    async def test_owner_can_add_share(self, mock_service: MagicMock) -> None:
        """Owner should be able to add shares."""
        from mcp_server_langgraph.api.v1.workflows import (
            AddWorkflowShareRequest,
            add_workflow_share_authorized,
        )

        # GIVEN the owner
        current_user = {"sub": "user-owner", "preferred_username": "owner"}
        request = AddWorkflowShareRequest(email="test@example.com", permission="view")

        # WHEN adding a share
        result = await add_workflow_share_authorized(
            workflow_id="wf-123",
            request=request,
            current_user=current_user,
            service=mock_service,
        )

        # THEN should succeed
        assert result["status"] == "shared"
        mock_service.add_workflow_share.assert_called_once()
