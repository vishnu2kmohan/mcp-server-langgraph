"""
PostgresWorkflowShareRepository Integration Tests

Integration tests for PostgreSQL-backed workflow sharing repository.
These tests require a PostgreSQL database connection.

Uses pytest-asyncio and SQLAlchemy async engine for database operations.
"""

from __future__ import annotations

import gc
import uuid
from typing import TYPE_CHECKING, AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

if TYPE_CHECKING:
    from mcp_server_langgraph.storage.workflow.share_repository import (
        PostgresWorkflowShareRepository,
    )

pytestmark = [
    pytest.mark.integration,
    pytest.mark.database,
    pytest.mark.asyncio,
]


# Check if required dependencies are available
try:
    import aiosqlite  # noqa: F401

    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False


@pytest.fixture
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    """
    Create an async SQLAlchemy engine for testing.

    Uses in-memory SQLite for isolated tests without external dependencies.
    For real Postgres tests, configure DATABASE_URL environment variable.
    """
    import os

    database_url = os.environ.get("TEST_DATABASE_URL")

    if database_url is None:
        if not HAS_AIOSQLITE:
            pytest.skip("aiosqlite required for in-memory SQLite tests. Set TEST_DATABASE_URL for Postgres.")
        database_url = "sqlite+aiosqlite:///:memory:"

    engine = create_async_engine(database_url, echo=False)

    # Create tables
    from mcp_server_langgraph.storage.workflow.postgres_models import WorkflowBase

    async with engine.begin() as conn:
        await conn.run_sync(WorkflowBase.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(WorkflowBase.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def repo(async_engine: AsyncEngine) -> PostgresWorkflowShareRepository:
    """Create a PostgresWorkflowShareRepository with the test engine."""
    from mcp_server_langgraph.storage.workflow.share_repository import (
        PostgresWorkflowShareRepository,
    )

    return PostgresWorkflowShareRepository(engine=async_engine)


@pytest.fixture
async def workflow_id(async_engine: AsyncEngine) -> str:
    """Create a test workflow and return its ID."""
    from mcp_server_langgraph.storage.workflow.postgres_models import WorkflowModel

    wf_id = str(uuid.uuid4())

    async with AsyncSession(async_engine) as session:
        async with session.begin():
            workflow = WorkflowModel(
                id=wf_id,
                name="Test Workflow",
                description="A workflow for testing",
                nodes=[],
                edges=[],
                user_id="owner-user",
                status="active",
                is_public=False,
                share_link=None,
            )
            session.add(workflow)

    return wf_id


@pytest.mark.xdist_group(name="test_postgres_share_repo_create")
class TestPostgresShareRepositoryCreate:
    """Integration tests for create_share operation."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory issues in xdist workers."""
        gc.collect()

    async def test_create_share_persists_to_database(
        self,
        repo: PostgresWorkflowShareRepository,
        workflow_id: str,
    ) -> None:
        """
        GIVEN a valid workflow exists
        WHEN create_share is called with valid share data
        THEN the share should be persisted to the database
        """
        from mcp_server_langgraph.storage.workflow.models import WorkflowShare

        # GIVEN
        share = WorkflowShare(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            user_id="test-user",
            email="test@example.com",
            permission="view",
            created_by="owner-user",
        )

        # WHEN
        await repo.create_share(share)

        # THEN
        shares = await repo.get_shares(workflow_id)
        assert len(shares) == 1
        assert shares[0].user_id == "test-user"
        assert shares[0].email == "test@example.com"
        assert shares[0].permission == "view"

    async def test_create_share_upserts_on_duplicate(
        self,
        repo: PostgresWorkflowShareRepository,
        workflow_id: str,
    ) -> None:
        """
        GIVEN a share already exists for workflow+user
        WHEN create_share is called again with different permission
        THEN the existing share should be updated (not duplicated)
        """
        from mcp_server_langgraph.storage.workflow.models import WorkflowShare

        # GIVEN - Create initial share
        share1 = WorkflowShare(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            user_id="test-user",
            email="test@example.com",
            permission="view",
            created_by="owner-user",
        )
        await repo.create_share(share1)

        # WHEN - Update with new permission
        share2 = WorkflowShare(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            user_id="test-user",
            email="test@example.com",
            permission="edit",
            created_by="owner-user",
        )
        await repo.create_share(share2)

        # THEN - Only one share exists with updated permission
        shares = await repo.get_shares(workflow_id)
        assert len(shares) == 1
        assert shares[0].permission == "edit"


@pytest.mark.xdist_group(name="test_postgres_share_repo_get")
class TestPostgresShareRepositoryGet:
    """Integration tests for get_share and get_shares operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory issues in xdist workers."""
        gc.collect()

    async def test_get_shares_returns_all_workflow_shares(
        self,
        repo: PostgresWorkflowShareRepository,
        workflow_id: str,
    ) -> None:
        """
        GIVEN multiple users have shares for a workflow
        WHEN get_shares is called
        THEN all shares for that workflow should be returned
        """
        from mcp_server_langgraph.storage.workflow.models import WorkflowShare

        # GIVEN - Create multiple shares
        for i in range(3):
            share = WorkflowShare(
                id=str(uuid.uuid4()),
                workflow_id=workflow_id,
                user_id=f"user-{i}",
                email=f"user{i}@example.com",
                permission="view",
                created_by="owner-user",
            )
            await repo.create_share(share)

        # WHEN
        shares = await repo.get_shares(workflow_id)

        # THEN
        assert len(shares) == 3
        user_ids = {s.user_id for s in shares}
        assert user_ids == {"user-0", "user-1", "user-2"}

    async def test_get_shares_returns_empty_for_no_shares(
        self,
        repo: PostgresWorkflowShareRepository,
        workflow_id: str,
    ) -> None:
        """
        GIVEN a workflow with no shares
        WHEN get_shares is called
        THEN an empty list should be returned
        """
        # WHEN
        shares = await repo.get_shares(workflow_id)

        # THEN
        assert shares == []

    async def test_get_share_returns_specific_share(
        self,
        repo: PostgresWorkflowShareRepository,
        workflow_id: str,
    ) -> None:
        """
        GIVEN a share exists for a specific workflow+user
        WHEN get_share is called with those IDs
        THEN the specific share should be returned
        """
        from mcp_server_langgraph.storage.workflow.models import WorkflowShare

        # GIVEN
        share = WorkflowShare(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            user_id="target-user",
            email="target@example.com",
            permission="edit",
            created_by="owner-user",
        )
        await repo.create_share(share)

        # WHEN
        result = await repo.get_share(workflow_id, "target-user")

        # THEN
        assert result is not None
        assert result.user_id == "target-user"
        assert result.email == "target@example.com"
        assert result.permission == "edit"

    async def test_get_share_returns_none_if_not_found(
        self,
        repo: PostgresWorkflowShareRepository,
        workflow_id: str,
    ) -> None:
        """
        GIVEN no share exists for the workflow+user
        WHEN get_share is called
        THEN None should be returned
        """
        # WHEN
        result = await repo.get_share(workflow_id, "nonexistent-user")

        # THEN
        assert result is None


@pytest.mark.xdist_group(name="test_postgres_share_repo_delete")
class TestPostgresShareRepositoryDelete:
    """Integration tests for delete_share operation."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory issues in xdist workers."""
        gc.collect()

    async def test_delete_share_removes_from_database(
        self,
        repo: PostgresWorkflowShareRepository,
        workflow_id: str,
    ) -> None:
        """
        GIVEN a share exists
        WHEN delete_share is called
        THEN the share should be removed from the database
        """
        from mcp_server_langgraph.storage.workflow.models import WorkflowShare

        # GIVEN
        share = WorkflowShare(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            user_id="user-to-delete",
            email="delete@example.com",
            permission="view",
            created_by="owner-user",
        )
        await repo.create_share(share)

        # WHEN
        deleted = await repo.delete_share(workflow_id, "user-to-delete")

        # THEN
        assert deleted is True
        result = await repo.get_share(workflow_id, "user-to-delete")
        assert result is None

    async def test_delete_share_returns_false_if_not_found(
        self,
        repo: PostgresWorkflowShareRepository,
        workflow_id: str,
    ) -> None:
        """
        GIVEN no share exists
        WHEN delete_share is called
        THEN False should be returned
        """
        # WHEN
        deleted = await repo.delete_share(workflow_id, "nonexistent-user")

        # THEN
        assert deleted is False


@pytest.mark.xdist_group(name="test_postgres_share_repo_list")
class TestPostgresShareRepositoryList:
    """Integration tests for list_shared_with_user operation."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory issues in xdist workers."""
        gc.collect()

    async def test_list_shared_with_user_returns_workflow_ids(
        self,
        repo: PostgresWorkflowShareRepository,
        async_engine: AsyncEngine,
    ) -> None:
        """
        GIVEN multiple workflows are shared with a user
        WHEN list_shared_with_user is called
        THEN all shared workflow IDs should be returned
        """
        from mcp_server_langgraph.storage.workflow.models import WorkflowShare
        from mcp_server_langgraph.storage.workflow.postgres_models import WorkflowModel

        # GIVEN - Create multiple workflows
        workflow_ids = []
        async with AsyncSession(async_engine) as session:
            async with session.begin():
                for i in range(3):
                    wf_id = str(uuid.uuid4())
                    workflow_ids.append(wf_id)
                    workflow = WorkflowModel(
                        id=wf_id,
                        name=f"Workflow {i}",
                        description="Test",
                        nodes=[],
                        edges=[],
                        user_id="owner-user",
                        status="active",
                    )
                    session.add(workflow)

        # Share all workflows with the same user
        for wf_id in workflow_ids:
            share = WorkflowShare(
                id=str(uuid.uuid4()),
                workflow_id=wf_id,
                user_id="shared-user",
                email="shared@example.com",
                permission="view",
                created_by="owner-user",
            )
            await repo.create_share(share)

        # WHEN
        result = await repo.list_shared_with_user("shared-user")

        # THEN
        assert len(result) == 3
        assert set(result) == set(workflow_ids)

    async def test_list_shared_with_user_returns_empty_if_none(
        self,
        repo: PostgresWorkflowShareRepository,
    ) -> None:
        """
        GIVEN no workflows are shared with the user
        WHEN list_shared_with_user is called
        THEN an empty list should be returned
        """
        # WHEN
        result = await repo.list_shared_with_user("no-shares-user")

        # THEN
        assert result == []


@pytest.mark.xdist_group(name="test_postgres_share_repo_public")
class TestPostgresShareRepositoryPublic:
    """Integration tests for public workflow operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory issues in xdist workers."""
        gc.collect()

    async def test_update_workflow_public_sets_is_public_true(
        self,
        repo: PostgresWorkflowShareRepository,
        workflow_id: str,
    ) -> None:
        """
        GIVEN a private workflow exists
        WHEN update_workflow_public is called with is_public=True
        THEN the workflow should be made public with a share_link
        """
        # WHEN
        result = await repo.update_workflow_public(workflow_id, is_public=True)

        # THEN
        assert result is not None
        assert result["is_public"] is True
        assert result["share_link"] is not None
        assert len(result["share_link"]) > 0

    async def test_update_workflow_public_sets_is_public_false(
        self,
        repo: PostgresWorkflowShareRepository,
        workflow_id: str,
    ) -> None:
        """
        GIVEN a public workflow exists
        WHEN update_workflow_public is called with is_public=False
        THEN the workflow should be made private and share_link cleared
        """
        # GIVEN - Make workflow public first
        await repo.update_workflow_public(workflow_id, is_public=True)

        # WHEN - Make it private
        result = await repo.update_workflow_public(workflow_id, is_public=False)

        # THEN
        assert result is not None
        assert result["is_public"] is False
        assert result["share_link"] is None

    async def test_update_workflow_public_returns_none_for_nonexistent(
        self,
        repo: PostgresWorkflowShareRepository,
    ) -> None:
        """
        GIVEN no workflow exists with the given ID
        WHEN update_workflow_public is called
        THEN None should be returned
        """
        # WHEN
        result = await repo.update_workflow_public("nonexistent-workflow", is_public=True)

        # THEN
        assert result is None

    async def test_get_by_share_link_returns_workflow_id(
        self,
        repo: PostgresWorkflowShareRepository,
        workflow_id: str,
    ) -> None:
        """
        GIVEN a public workflow with a share_link
        WHEN get_by_share_link is called with the link
        THEN the workflow ID should be returned
        """
        # GIVEN
        result = await repo.update_workflow_public(workflow_id, is_public=True)
        share_link = result["share_link"]

        # WHEN
        found_id = await repo.get_by_share_link(share_link)

        # THEN
        assert found_id == workflow_id

    async def test_get_by_share_link_returns_none_for_invalid(
        self,
        repo: PostgresWorkflowShareRepository,
    ) -> None:
        """
        GIVEN no workflow has the given share_link
        WHEN get_by_share_link is called
        THEN None should be returned
        """
        # WHEN
        result = await repo.get_by_share_link("invalid-share-link")

        # THEN
        assert result is None

    async def test_get_by_share_link_returns_none_for_private_workflow(
        self,
        repo: PostgresWorkflowShareRepository,
        workflow_id: str,
    ) -> None:
        """
        GIVEN a workflow that was made public then private
        WHEN get_by_share_link is called with the old link
        THEN None should be returned (link is invalidated)
        """
        # GIVEN - Make public, then private
        result = await repo.update_workflow_public(workflow_id, is_public=True)
        old_link = result["share_link"]
        await repo.update_workflow_public(workflow_id, is_public=False)

        # WHEN
        found_id = await repo.get_by_share_link(old_link)

        # THEN
        assert found_id is None
