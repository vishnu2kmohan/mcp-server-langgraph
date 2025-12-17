"""
WorkflowShareRepository Unit Tests

TDD tests for workflow sharing storage layer (Phase 6).

Repository operations:
- create_share: Add a share to a workflow
- get_shares: Get all shares for a workflow
- get_share: Get a specific share by workflow_id + user_id
- delete_share: Remove a share from a workflow
- list_shared_with_user: List workflows shared with a user
- update_workflow_public: Toggle is_public and generate share_link
- get_by_share_link: Get workflow by public share link
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from mcp_server_langgraph.storage.workflow.share_repository import (
        InMemoryWorkflowShareRepository,
    )

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestWorkflowShareModels:
    """Tests for WorkflowShare storage models."""

    def test_workflow_share_model_exists(self) -> None:
        """WorkflowShare model should exist with required fields."""
        from mcp_server_langgraph.storage.workflow.models import WorkflowShare

        # Verify it's a Pydantic model with expected fields
        schema = WorkflowShare.model_json_schema()
        properties = schema.get("properties", {})

        assert "id" in properties
        assert "workflow_id" in properties
        assert "user_id" in properties
        assert "email" in properties
        assert "permission" in properties
        assert "created_at" in properties
        assert "created_by" in properties

    def test_workflow_share_permission_enum_exists(self) -> None:
        """SharePermission enum should define valid permission levels."""
        from mcp_server_langgraph.storage.workflow.models import SharePermission

        assert SharePermission.VIEW.value == "view"
        assert SharePermission.EDIT.value == "edit"
        assert SharePermission.EXECUTE.value == "execute"

    def test_workflow_share_model_defaults(self) -> None:
        """WorkflowShare should have sensible defaults."""
        from mcp_server_langgraph.storage.workflow.models import WorkflowShare

        share = WorkflowShare(
            id="share-1",
            workflow_id="wf-1",
            user_id="user-1",
            email="test@example.com",
            permission="view",
            created_by="owner-1",
        )

        assert share.id == "share-1"
        assert share.permission == "view"
        assert share.created_at is not None


class TestWorkflowShareSQLAlchemyModel:
    """Tests for WorkflowShareModel SQLAlchemy model."""

    def test_workflow_share_sqlalchemy_model_exists(self) -> None:
        """WorkflowShareModel should be a SQLAlchemy model."""
        from mcp_server_langgraph.storage.workflow.postgres_models import (
            WorkflowShareModel,
        )

        assert WorkflowShareModel.__tablename__ == "workflow_shares"

    def test_workflow_share_sqlalchemy_model_columns(self) -> None:
        """WorkflowShareModel should have all required columns."""
        from mcp_server_langgraph.storage.workflow.postgres_models import (
            WorkflowShareModel,
        )

        columns = {c.name for c in WorkflowShareModel.__table__.columns}

        assert "id" in columns
        assert "workflow_id" in columns
        assert "user_id" in columns
        assert "email" in columns
        assert "permission" in columns
        assert "created_at" in columns
        assert "created_by" in columns


class TestWorkflowModelSharingFields:
    """Tests for sharing fields on WorkflowModel."""

    def test_workflow_model_has_is_public_column(self) -> None:
        """WorkflowModel should have is_public column."""
        from mcp_server_langgraph.storage.workflow.postgres_models import (
            WorkflowModel,
        )

        columns = {c.name for c in WorkflowModel.__table__.columns}
        assert "is_public" in columns

    def test_workflow_model_has_share_link_column(self) -> None:
        """WorkflowModel should have share_link column."""
        from mcp_server_langgraph.storage.workflow.postgres_models import (
            WorkflowModel,
        )

        columns = {c.name for c in WorkflowModel.__table__.columns}
        assert "share_link" in columns


class TestInMemoryWorkflowShareRepository:
    """Tests for InMemoryWorkflowShareRepository."""

    @pytest.fixture
    def repo(self) -> InMemoryWorkflowShareRepository:
        """Create a fresh in-memory repository."""
        from mcp_server_langgraph.storage.workflow.share_repository import (
            InMemoryWorkflowShareRepository,
        )

        return InMemoryWorkflowShareRepository()

    @pytest.mark.asyncio
    async def test_create_share_stores_share(self, repo: InMemoryWorkflowShareRepository) -> None:
        """create_share should store the share."""
        from mcp_server_langgraph.storage.workflow.models import WorkflowShare

        # GIVEN a share to create
        share = WorkflowShare(
            id=str(uuid.uuid4()),
            workflow_id="wf-1",
            user_id="user-1",
            email="alice@example.com",
            permission="edit",
            created_by="owner-1",
        )

        # WHEN creating the share
        await repo.create_share(share)

        # THEN it should be retrievable
        shares = await repo.get_shares("wf-1")
        assert len(shares) == 1
        assert shares[0].user_id == "user-1"
        assert shares[0].permission == "edit"

    @pytest.mark.asyncio
    async def test_get_shares_returns_all_shares_for_workflow(self, repo: InMemoryWorkflowShareRepository) -> None:
        """get_shares should return all shares for a workflow."""
        from mcp_server_langgraph.storage.workflow.models import WorkflowShare

        # GIVEN multiple shares for a workflow
        for i in range(3):
            share = WorkflowShare(
                id=str(uuid.uuid4()),
                workflow_id="wf-1",
                user_id=f"user-{i}",
                email=f"user{i}@example.com",
                permission="view",
                created_by="owner-1",
            )
            await repo.create_share(share)

        # WHEN getting shares
        shares = await repo.get_shares("wf-1")

        # THEN all shares should be returned
        assert len(shares) == 3

    @pytest.mark.asyncio
    async def test_get_shares_returns_empty_for_no_shares(self, repo: InMemoryWorkflowShareRepository) -> None:
        """get_shares should return empty list if no shares exist."""
        # GIVEN no shares exist

        # WHEN getting shares
        shares = await repo.get_shares("nonexistent-wf")

        # THEN should return empty list
        assert shares == []

    @pytest.mark.asyncio
    async def test_get_share_returns_specific_share(self, repo: InMemoryWorkflowShareRepository) -> None:
        """get_share should return a specific share by workflow_id and user_id."""
        from mcp_server_langgraph.storage.workflow.models import WorkflowShare

        # GIVEN a share exists
        share = WorkflowShare(
            id=str(uuid.uuid4()),
            workflow_id="wf-1",
            user_id="user-1",
            email="alice@example.com",
            permission="edit",
            created_by="owner-1",
        )
        await repo.create_share(share)

        # WHEN getting the specific share
        result = await repo.get_share("wf-1", "user-1")

        # THEN should return the share
        assert result is not None
        assert result.user_id == "user-1"
        assert result.email == "alice@example.com"

    @pytest.mark.asyncio
    async def test_get_share_returns_none_if_not_found(self, repo: InMemoryWorkflowShareRepository) -> None:
        """get_share should return None if share doesn't exist."""
        # GIVEN no share exists

        # WHEN getting a nonexistent share
        result = await repo.get_share("wf-1", "nonexistent-user")

        # THEN should return None
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_share_removes_share(self, repo: InMemoryWorkflowShareRepository) -> None:
        """delete_share should remove the share."""
        from mcp_server_langgraph.storage.workflow.models import WorkflowShare

        # GIVEN a share exists
        share = WorkflowShare(
            id=str(uuid.uuid4()),
            workflow_id="wf-1",
            user_id="user-1",
            email="alice@example.com",
            permission="edit",
            created_by="owner-1",
        )
        await repo.create_share(share)

        # WHEN deleting the share
        deleted = await repo.delete_share("wf-1", "user-1")

        # THEN should return True and share should be gone
        assert deleted is True
        shares = await repo.get_shares("wf-1")
        assert len(shares) == 0

    @pytest.mark.asyncio
    async def test_delete_share_returns_false_if_not_found(self, repo: InMemoryWorkflowShareRepository) -> None:
        """delete_share should return False if share doesn't exist."""
        # GIVEN no share exists

        # WHEN deleting a nonexistent share
        deleted = await repo.delete_share("wf-1", "nonexistent-user")

        # THEN should return False
        assert deleted is False

    @pytest.mark.asyncio
    async def test_list_shared_with_user_returns_workflows(self, repo: InMemoryWorkflowShareRepository) -> None:
        """list_shared_with_user should return workflows shared with a user."""
        from mcp_server_langgraph.storage.workflow.models import WorkflowShare

        # GIVEN multiple workflows shared with the same user
        for i in range(2):
            share = WorkflowShare(
                id=str(uuid.uuid4()),
                workflow_id=f"wf-{i}",
                user_id="user-1",
                email="alice@example.com",
                permission="view",
                created_by="owner-1",
            )
            await repo.create_share(share)

        # WHEN listing workflows shared with the user
        workflow_ids = await repo.list_shared_with_user("user-1")

        # THEN should return the workflow IDs
        assert len(workflow_ids) == 2
        assert "wf-0" in workflow_ids
        assert "wf-1" in workflow_ids

    @pytest.mark.asyncio
    async def test_create_share_updates_existing_permission(self, repo: InMemoryWorkflowShareRepository) -> None:
        """create_share should update permission if share already exists."""
        from mcp_server_langgraph.storage.workflow.models import WorkflowShare

        # GIVEN an existing share
        share1 = WorkflowShare(
            id=str(uuid.uuid4()),
            workflow_id="wf-1",
            user_id="user-1",
            email="alice@example.com",
            permission="view",
            created_by="owner-1",
        )
        await repo.create_share(share1)

        # WHEN creating a share with same workflow/user but different permission
        share2 = WorkflowShare(
            id=str(uuid.uuid4()),
            workflow_id="wf-1",
            user_id="user-1",
            email="alice@example.com",
            permission="edit",  # Changed from 'view'
            created_by="owner-1",
        )
        await repo.create_share(share2)

        # THEN should update existing share (not create duplicate)
        shares = await repo.get_shares("wf-1")
        assert len(shares) == 1
        assert shares[0].permission == "edit"


class TestPublicWorkflowOperations:
    """Tests for public workflow visibility operations."""

    @pytest.fixture
    def repo(self) -> InMemoryWorkflowShareRepository:
        """Create a fresh in-memory repository."""
        from mcp_server_langgraph.storage.workflow.share_repository import (
            InMemoryWorkflowShareRepository,
        )

        return InMemoryWorkflowShareRepository()

    @pytest.mark.asyncio
    async def test_update_workflow_public_sets_is_public(self, repo: InMemoryWorkflowShareRepository) -> None:
        """update_workflow_public should set is_public flag."""
        # GIVEN a workflow exists (mock workflow_id validation)
        repo._workflows["wf-1"] = {"is_public": False, "share_link": None}

        # WHEN making it public
        result = await repo.update_workflow_public("wf-1", is_public=True)

        # THEN should return updated state
        assert result is not None
        assert result["is_public"] is True
        assert result["share_link"] is not None

    @pytest.mark.asyncio
    async def test_update_workflow_public_generates_share_link(self, repo: InMemoryWorkflowShareRepository) -> None:
        """update_workflow_public should generate share_link when made public."""
        # GIVEN a workflow exists
        repo._workflows["wf-1"] = {"is_public": False, "share_link": None}

        # WHEN making it public
        result = await repo.update_workflow_public("wf-1", is_public=True)

        # THEN share_link should be generated
        assert result["share_link"] is not None
        assert len(result["share_link"]) > 0

    @pytest.mark.asyncio
    async def test_update_workflow_public_clears_share_link_when_private(self, repo: InMemoryWorkflowShareRepository) -> None:
        """update_workflow_public should clear share_link when made private."""
        # GIVEN a public workflow
        repo._workflows["wf-1"] = {"is_public": True, "share_link": "abc123"}

        # WHEN making it private
        result = await repo.update_workflow_public("wf-1", is_public=False)

        # THEN share_link should be None
        assert result["is_public"] is False
        assert result["share_link"] is None

    @pytest.mark.asyncio
    async def test_update_workflow_public_returns_none_if_not_found(self, repo: InMemoryWorkflowShareRepository) -> None:
        """update_workflow_public should return None if workflow doesn't exist."""
        # GIVEN no workflow exists

        # WHEN trying to update a nonexistent workflow
        result = await repo.update_workflow_public("nonexistent", is_public=True)

        # THEN should return None
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_share_link_returns_workflow_id(self, repo: InMemoryWorkflowShareRepository) -> None:
        """get_by_share_link should return workflow_id for valid link."""
        # GIVEN a public workflow with share_link
        repo._workflows["wf-1"] = {"is_public": True, "share_link": "secret-link-123"}
        repo._share_links["secret-link-123"] = "wf-1"

        # WHEN getting by share link
        workflow_id = await repo.get_by_share_link("secret-link-123")

        # THEN should return workflow_id
        assert workflow_id == "wf-1"

    @pytest.mark.asyncio
    async def test_get_by_share_link_returns_none_for_invalid_link(self, repo: InMemoryWorkflowShareRepository) -> None:
        """get_by_share_link should return None for invalid link."""
        # GIVEN no share link exists

        # WHEN getting by invalid link
        workflow_id = await repo.get_by_share_link("invalid-link")

        # THEN should return None
        assert workflow_id is None


class TestWorkflowShareRepositoryProtocol:
    """Tests for WorkflowShareRepositoryProtocol interface."""

    def test_protocol_defines_required_methods(self) -> None:
        """WorkflowShareRepositoryProtocol should define all required methods."""
        from mcp_server_langgraph.storage.workflow.share_repository import (
            WorkflowShareRepositoryProtocol,
        )

        # Check that protocol defines the expected method signatures
        # (typing.runtime_checkable + hasattr checks)
        assert hasattr(WorkflowShareRepositoryProtocol, "create_share")
        assert hasattr(WorkflowShareRepositoryProtocol, "get_shares")
        assert hasattr(WorkflowShareRepositoryProtocol, "get_share")
        assert hasattr(WorkflowShareRepositoryProtocol, "delete_share")
        assert hasattr(WorkflowShareRepositoryProtocol, "list_shared_with_user")
        assert hasattr(WorkflowShareRepositoryProtocol, "update_workflow_public")
        assert hasattr(WorkflowShareRepositoryProtocol, "get_by_share_link")
