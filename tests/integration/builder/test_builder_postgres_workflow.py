"""
Integration tests for Postgres-backed workflow storage.

Tests the workflow manager against real PostgreSQL infrastructure:
- Workflow CRUD operations with real Postgres
- User-scoped workflow listing
- Multi-workflow concurrent operations
- Search and pagination support

Requires: PostgreSQL running at TEST_POSTGRES_URL or docker-compose.test.yml

Run with:
    make test-infra-up
    pytest tests/integration/builder/test_builder_postgres_workflow.py -v

References:
- tests/integration/playground/test_playground_postgres_session.py (session pattern)
- src/mcp_server_langgraph/builder/storage/postgres_manager.py (workflow manager)
- tests/integration/builder/test_builder_redis_workflow.py (Redis counterpart)
"""

import asyncio
import gc
import uuid

import pytest

from tests.constants import (
    TEST_POSTGRES_DB,
    TEST_POSTGRES_HOST,
    TEST_POSTGRES_PASSWORD,
    TEST_POSTGRES_PORT,
    TEST_POSTGRES_USER,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.builder,
    pytest.mark.postgres,
    pytest.mark.xdist_group(name="builder_postgres_integration_tests"),
]


@pytest.fixture
def postgres_url() -> str:
    """Get PostgreSQL URL for builder workflows."""
    return f"postgresql+asyncpg://{TEST_POSTGRES_USER}:{TEST_POSTGRES_PASSWORD}@{TEST_POSTGRES_HOST}:{TEST_POSTGRES_PORT}/{TEST_POSTGRES_DB}"


@pytest.fixture
async def postgres_engine(postgres_url: str):
    """Create async SQLAlchemy engine for testing."""
    from mcp_server_langgraph.builder.storage.postgres_manager import (
        create_postgres_engine,
        init_builder_database,
    )

    try:
        engine = await create_postgres_engine(postgres_url, echo=False)
        await init_builder_database(engine)
    except OSError as e:
        pytest.skip(f"PostgreSQL infrastructure not available: {e}")
    except Exception as e:
        # Catch other connection-related errors
        error_msg = str(e)
        if any(pattern in error_msg for pattern in ["Connect call failed", "Connection refused", "Network is unreachable"]):
            pytest.skip(f"PostgreSQL infrastructure not available: {e}")
        raise
    yield engine
    await engine.dispose()


@pytest.fixture
async def workflow_manager(postgres_engine):
    """Create workflow manager with real Postgres."""
    from mcp_server_langgraph.builder.storage.postgres_manager import PostgresWorkflowManager

    manager = PostgresWorkflowManager(engine=postgres_engine)
    yield manager
    await manager.close()


@pytest.fixture
def sample_nodes() -> list[dict]:
    """Sample workflow nodes for testing."""
    return [
        {"id": "node1", "type": "llm", "config": {"model": "gpt-4"}},
        {"id": "node2", "type": "tool", "config": {"tool_name": "search"}},
    ]


@pytest.fixture
def sample_edges() -> list[dict]:
    """Sample workflow edges for testing."""
    return [
        {"from_node": "node1", "to_node": "node2"},
    ]


@pytest.mark.xdist_group(name="builder_postgres_integration_tests")
class TestPostgresWorkflowIntegration:
    """Integration tests for Postgres workflow storage."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_workflow_persists_to_postgres(self, workflow_manager, sample_nodes, sample_edges) -> None:
        """Test that created workflows are actually stored in Postgres."""
        workflow = await workflow_manager.create_workflow(
            name="Integration Test Workflow",
            description="Test workflow for Postgres integration",
            nodes=sample_nodes,
            edges=sample_edges,
            user_id="alice",
        )

        assert workflow is not None
        assert workflow.id is not None
        assert workflow.name == "Integration Test Workflow"
        assert workflow.description == "Test workflow for Postgres integration"
        assert workflow.user_id == "alice"

        # Verify workflow can be retrieved
        retrieved = await workflow_manager.get_workflow(workflow.id)
        assert retrieved is not None
        assert retrieved.id == workflow.id

    @pytest.mark.asyncio
    async def test_get_workflow_retrieves_from_postgres(self, workflow_manager, sample_nodes, sample_edges) -> None:
        """Test retrieving a workflow from Postgres."""
        created = await workflow_manager.create_workflow(
            name="Retrieve Test",
            description="Test retrieval",
            nodes=sample_nodes,
            edges=sample_edges,
            user_id="bob",
        )

        retrieved = await workflow_manager.get_workflow(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Retrieve Test"
        assert retrieved.user_id == "bob"
        assert len(retrieved.nodes) == 2
        assert len(retrieved.edges) == 1

    @pytest.mark.asyncio
    async def test_update_workflow_updates_data(self, workflow_manager, sample_nodes, sample_edges) -> None:
        """Test updating workflow fields."""
        workflow = await workflow_manager.create_workflow(
            name="Original Name",
            description="Original description",
            nodes=sample_nodes,
            edges=sample_edges,
            user_id="charlie",
        )

        # Update the workflow
        updated = await workflow_manager.update_workflow(
            workflow_id=workflow.id,
            name="Updated Name",
            description="Updated description",
        )

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.description == "Updated description"
        assert updated.updated_at > workflow.created_at

        # Verify persisted
        retrieved = await workflow_manager.get_workflow(workflow.id)
        assert retrieved.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_workflow_removes_from_postgres(self, workflow_manager, sample_nodes) -> None:
        """Test that deleted workflows are removed from Postgres."""
        workflow = await workflow_manager.create_workflow(
            name="Delete Test",
            nodes=sample_nodes,
            user_id="dave",
        )

        # Verify exists
        retrieved = await workflow_manager.get_workflow(workflow.id)
        assert retrieved is not None

        result = await workflow_manager.delete_workflow(workflow.id)

        assert result is True

        # Verify deleted
        retrieved = await workflow_manager.get_workflow(workflow.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_workflows_for_user(self, workflow_manager, sample_nodes) -> None:
        """Test listing workflows scoped to a user."""
        user_id = f"user-{uuid.uuid4()}"

        # Create multiple workflows for the user
        workflow1 = await workflow_manager.create_workflow(name="Workflow 1", nodes=sample_nodes, user_id=user_id)
        workflow2 = await workflow_manager.create_workflow(name="Workflow 2", nodes=sample_nodes, user_id=user_id)
        workflow3 = await workflow_manager.create_workflow(name="Workflow 3", nodes=sample_nodes, user_id=user_id)

        # Create workflow for different user
        await workflow_manager.create_workflow(name="Other User", nodes=sample_nodes, user_id="other")

        workflows = await workflow_manager.list_workflows(user_id=user_id)

        assert len(workflows) >= 3
        workflow_ids = {w.id for w in workflows}
        assert workflow1.id in workflow_ids
        assert workflow2.id in workflow_ids
        assert workflow3.id in workflow_ids

    @pytest.mark.asyncio
    async def test_concurrent_workflow_operations(self, workflow_manager, sample_nodes) -> None:
        """Test concurrent workflow operations don't interfere."""
        user_id = f"concurrent-{uuid.uuid4()}"

        # Create workflows concurrently
        tasks = [
            workflow_manager.create_workflow(name=f"Concurrent {i}", nodes=sample_nodes, user_id=user_id) for i in range(5)
        ]
        workflows = await asyncio.gather(*tasks)

        assert len(workflows) == 5
        assert len({w.id for w in workflows}) == 5  # All unique IDs

    @pytest.mark.asyncio
    async def test_workflow_nodes_preserved(self, workflow_manager, sample_nodes, sample_edges) -> None:
        """Test that workflow nodes are preserved in storage."""
        workflow = await workflow_manager.create_workflow(
            name="Node Test",
            nodes=sample_nodes,
            edges=sample_edges,
            user_id="eve",
        )

        retrieved = await workflow_manager.get_workflow(workflow.id)

        assert len(retrieved.nodes) == 2
        assert retrieved.nodes[0]["type"] == "llm"
        assert retrieved.nodes[1]["type"] == "tool"
        assert len(retrieved.edges) == 1
        assert retrieved.edges[0]["from_node"] == "node1"

    @pytest.mark.asyncio
    async def test_search_workflows_by_name(self, workflow_manager, sample_nodes) -> None:
        """Test searching workflows by name (Postgres-specific feature)."""
        user_id = f"search-{uuid.uuid4()}"

        await workflow_manager.create_workflow(name="Alpha Project", nodes=sample_nodes, user_id=user_id)
        await workflow_manager.create_workflow(name="Beta Project", nodes=sample_nodes, user_id=user_id)
        await workflow_manager.create_workflow(name="Gamma Test", nodes=sample_nodes, user_id=user_id)

        # Search for workflows containing "Project"
        workflows = await workflow_manager.list_workflows(user_id=user_id, search="Project")

        assert len(workflows) >= 2
        names = {w.name for w in workflows}
        assert "Alpha Project" in names
        assert "Beta Project" in names

    @pytest.mark.asyncio
    async def test_pagination_support(self, workflow_manager, sample_nodes) -> None:
        """Test pagination of workflow listing (Postgres-specific feature)."""
        user_id = f"pagination-{uuid.uuid4()}"

        # Create 10 workflows
        for i in range(10):
            await workflow_manager.create_workflow(name=f"Page Test {i}", nodes=sample_nodes, user_id=user_id)

        # Get first page
        page1 = await workflow_manager.list_workflows(user_id=user_id, limit=3, offset=0)
        assert len(page1) == 3

        # Get second page
        page2 = await workflow_manager.list_workflows(user_id=user_id, limit=3, offset=3)
        assert len(page2) == 3

        # Pages should have different workflows
        page1_ids = {w.id for w in page1}
        page2_ids = {w.id for w in page2}
        assert page1_ids.isdisjoint(page2_ids)


@pytest.mark.xdist_group(name="builder_postgres_integration_tests")
class TestPostgresWorkflowResilience:
    """Test Postgres connection handling and error cases."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handles_nonexistent_workflow(self, workflow_manager) -> None:
        """Test graceful handling of nonexistent workflows."""
        result = await workflow_manager.get_workflow("nonexistent-workflow-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_workflow_returns_false(self, workflow_manager) -> None:
        """Test deleting nonexistent workflow returns False."""
        result = await workflow_manager.delete_workflow("nonexistent-workflow-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_update_nonexistent_workflow_returns_none(self, workflow_manager) -> None:
        """Test updating nonexistent workflow returns None."""
        result = await workflow_manager.update_workflow(
            workflow_id="nonexistent-workflow-id",
            name="New Name",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_workflow_list_for_new_user(self, workflow_manager) -> None:
        """Test listing workflows for user with no workflows."""
        user_id = f"new-user-{uuid.uuid4()}"
        workflows = await workflow_manager.list_workflows(user_id=user_id)
        assert workflows == []

    @pytest.mark.asyncio
    async def test_workflow_with_no_user_id(self, workflow_manager, sample_nodes) -> None:
        """Test creating workflow without user_id."""
        workflow = await workflow_manager.create_workflow(
            name="No User Workflow",
            nodes=sample_nodes,
            user_id=None,  # No user
        )

        # Can still retrieve
        retrieved = await workflow_manager.get_workflow(workflow.id)
        assert retrieved is not None
        assert retrieved.user_id is None


@pytest.mark.xdist_group(name="builder_postgres_integration_tests")
class TestPostgresWorkflowUpdateOperations:
    """Test various update scenarios for workflows."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_update_workflow_nodes(self, workflow_manager, sample_nodes) -> None:
        """Test updating workflow nodes."""
        workflow = await workflow_manager.create_workflow(
            name="Node Update Test",
            nodes=sample_nodes,
            user_id="frank",
        )

        new_nodes = [
            {"id": "new_node", "type": "router", "config": {"strategy": "round-robin"}},
        ]

        updated = await workflow_manager.update_workflow(
            workflow_id=workflow.id,
            nodes=new_nodes,
        )

        assert updated is not None
        assert len(updated.nodes) == 1
        assert updated.nodes[0]["type"] == "router"

    @pytest.mark.asyncio
    async def test_update_workflow_edges(self, workflow_manager, sample_nodes, sample_edges) -> None:
        """Test updating workflow edges."""
        workflow = await workflow_manager.create_workflow(
            name="Edge Update Test",
            nodes=sample_nodes,
            edges=sample_edges,
            user_id="grace",
        )

        new_edges = [
            {"from_node": "node1", "to_node": "node3"},
            {"from_node": "node3", "to_node": "node2"},
        ]

        updated = await workflow_manager.update_workflow(
            workflow_id=workflow.id,
            edges=new_edges,
        )

        assert updated is not None
        assert len(updated.edges) == 2

    @pytest.mark.asyncio
    async def test_partial_update_preserves_other_fields(self, workflow_manager, sample_nodes, sample_edges) -> None:
        """Test that partial updates preserve unchanged fields."""
        workflow = await workflow_manager.create_workflow(
            name="Partial Update Test",
            description="Original description",
            nodes=sample_nodes,
            edges=sample_edges,
            user_id="henry",
        )

        # Update only name
        updated = await workflow_manager.update_workflow(
            workflow_id=workflow.id,
            name="New Name",
        )

        assert updated is not None
        assert updated.name == "New Name"
        assert updated.description == "Original description"  # Unchanged
        assert len(updated.nodes) == 2  # Unchanged
        assert len(updated.edges) == 1  # Unchanged


@pytest.mark.xdist_group(name="builder_postgres_integration_tests")
class TestPostgresWorkflowAdvancedFeatures:
    """Test advanced Postgres-specific features."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_search_by_description(self, workflow_manager, sample_nodes) -> None:
        """Test searching workflows by description."""
        user_id = f"desc-search-{uuid.uuid4()}"

        await workflow_manager.create_workflow(
            name="Workflow A", description="Agent for customer support", nodes=sample_nodes, user_id=user_id
        )
        await workflow_manager.create_workflow(
            name="Workflow B", description="Agent for sales automation", nodes=sample_nodes, user_id=user_id
        )
        await workflow_manager.create_workflow(
            name="Workflow C", description="Data processing pipeline", nodes=sample_nodes, user_id=user_id
        )

        # Search for "Agent" in description
        workflows = await workflow_manager.list_workflows(user_id=user_id, search="Agent")

        assert len(workflows) >= 2
        descriptions = {w.description for w in workflows}
        assert any("customer support" in d for d in descriptions)
        assert any("sales automation" in d for d in descriptions)

    @pytest.mark.asyncio
    async def test_case_insensitive_search(self, workflow_manager, sample_nodes) -> None:
        """Test case-insensitive search."""
        user_id = f"case-search-{uuid.uuid4()}"

        await workflow_manager.create_workflow(name="MyProject Alpha", nodes=sample_nodes, user_id=user_id)

        # Search with different case
        workflows = await workflow_manager.list_workflows(user_id=user_id, search="myproject")

        assert len(workflows) >= 1
        assert any("MyProject" in w.name for w in workflows)

    @pytest.mark.asyncio
    async def test_workflow_ordering_by_updated_at(self, workflow_manager, sample_nodes) -> None:
        """Test that workflows are ordered by most recently updated."""
        user_id = f"order-{uuid.uuid4()}"

        # Create workflows (w2, w3 needed to populate list but not individually verified)
        w1 = await workflow_manager.create_workflow(name="First", nodes=sample_nodes, user_id=user_id)
        _w2 = await workflow_manager.create_workflow(name="Second", nodes=sample_nodes, user_id=user_id)
        _w3 = await workflow_manager.create_workflow(name="Third", nodes=sample_nodes, user_id=user_id)

        # Update the first workflow to make it most recent
        await workflow_manager.update_workflow(workflow_id=w1.id, name="First Updated")

        workflows = await workflow_manager.list_workflows(user_id=user_id)

        # First updated should be first (most recently updated)
        assert workflows[0].id == w1.id
