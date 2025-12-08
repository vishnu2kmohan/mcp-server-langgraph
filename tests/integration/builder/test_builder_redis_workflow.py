"""
Integration tests for Redis-backed workflow storage.

Tests the workflow manager against real Redis infrastructure:
- Workflow CRUD operations with real Redis
- TTL expiration behavior
- User-scoped workflow listing
- Multi-workflow concurrent operations
- Connection recovery

Requires: Redis running at TEST_REDIS_URL or docker-compose.test.yml

Run with:
    make test-infra-up
    pytest tests/integration/builder/test_builder_redis_workflow.py -v

References:
- tests/integration/playground/test_playground_redis_session.py (session pattern)
- src/mcp_server_langgraph/builder/storage/manager.py (workflow manager)
- tests/constants.py:TEST_REDIS_BUILDER_DB (DB index 3)
"""

import asyncio
import gc
import uuid

import pytest

from tests.constants import TEST_REDIS_BUILDER_DB, TEST_REDIS_PORT

pytestmark = [
    pytest.mark.integration,
    pytest.mark.builder,
    pytest.mark.redis,
    pytest.mark.xdist_group(name="builder_redis_integration_tests"),
]


@pytest.fixture
def redis_url() -> str:
    """Get Redis URL for builder workflows."""
    return f"redis://localhost:{TEST_REDIS_PORT}/{TEST_REDIS_BUILDER_DB}"


@pytest.fixture
async def redis_client(redis_url: str):
    """Create Redis client for testing."""
    import redis.asyncio as redis

    client = redis.from_url(redis_url, decode_responses=True)
    yield client
    # Clean up test keys
    async for key in client.scan_iter("builder:*"):
        await client.delete(key)
    await client.aclose()


@pytest.fixture
async def workflow_manager(redis_client):
    """Create workflow manager with real Redis."""
    from mcp_server_langgraph.builder.storage.manager import RedisWorkflowManager

    manager = RedisWorkflowManager(redis_client=redis_client, ttl_seconds=60)
    return manager


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


@pytest.mark.xdist_group(name="builder_redis_integration_tests")
class TestRedisWorkflowIntegration:
    """Integration tests for Redis workflow storage."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_workflow_persists_to_redis(self, workflow_manager, redis_client, sample_nodes, sample_edges) -> None:
        """Test that created workflows are actually stored in Redis."""
        workflow = await workflow_manager.create_workflow(
            name="Integration Test Workflow",
            description="Test workflow for Redis integration",
            nodes=sample_nodes,
            edges=sample_edges,
            user_id="alice",
        )

        # Verify workflow exists in Redis
        key = f"builder:workflow:{workflow.id}"
        data = await redis_client.get(key)

        assert data is not None
        assert "Integration Test Workflow" in data
        assert workflow.id in data

    @pytest.mark.asyncio
    async def test_get_workflow_retrieves_from_redis(self, workflow_manager, sample_nodes, sample_edges) -> None:
        """Test retrieving a workflow from Redis."""
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
    async def test_workflow_ttl_is_set(self, workflow_manager, redis_client, sample_nodes) -> None:
        """Test that workflow TTL is properly set in Redis."""
        workflow = await workflow_manager.create_workflow(
            name="TTL Test",
            nodes=sample_nodes,
            user_id="charlie",
        )

        key = f"builder:workflow:{workflow.id}"
        ttl = await redis_client.ttl(key)

        # TTL should be set (60 seconds in fixture, allow some margin)
        assert ttl > 0
        assert ttl <= 60

    @pytest.mark.asyncio
    async def test_update_workflow_updates_data(self, workflow_manager, sample_nodes, sample_edges) -> None:
        """Test updating workflow fields."""
        workflow = await workflow_manager.create_workflow(
            name="Original Name",
            description="Original description",
            nodes=sample_nodes,
            edges=sample_edges,
            user_id="dave",
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
    async def test_delete_workflow_removes_from_redis(self, workflow_manager, redis_client, sample_nodes) -> None:
        """Test that deleted workflows are removed from Redis."""
        workflow = await workflow_manager.create_workflow(
            name="Delete Test",
            nodes=sample_nodes,
            user_id="eve",
        )

        key = f"builder:workflow:{workflow.id}"
        assert await redis_client.exists(key)

        result = await workflow_manager.delete_workflow(workflow.id)

        assert result is True
        assert not await redis_client.exists(key)

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

        assert len(workflows) == 3
        workflow_ids = {w.id for w in workflows}
        assert workflow1.id in workflow_ids
        assert workflow2.id in workflow_ids
        assert workflow3.id in workflow_ids

    @pytest.mark.asyncio
    async def test_update_workflow_refreshes_ttl(self, workflow_manager, redis_client, sample_nodes) -> None:
        """Test that updating a workflow refreshes its TTL."""
        workflow = await workflow_manager.create_workflow(
            name="TTL Refresh Test",
            nodes=sample_nodes,
            user_id="frank",
        )

        key = f"builder:workflow:{workflow.id}"
        initial_ttl = await redis_client.ttl(key)

        # Wait a bit
        await asyncio.sleep(2)

        # Update workflow
        await workflow_manager.update_workflow(workflow.id, name="Updated Name")

        new_ttl = await redis_client.ttl(key)

        # TTL should be refreshed (close to initial)
        assert new_ttl >= initial_ttl - 3  # Allow 3 second margin

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
            user_id="grace",
        )

        retrieved = await workflow_manager.get_workflow(workflow.id)

        assert len(retrieved.nodes) == 2
        assert retrieved.nodes[0]["type"] == "llm"
        assert retrieved.nodes[1]["type"] == "tool"
        assert len(retrieved.edges) == 1
        assert retrieved.edges[0]["from_node"] == "node1"

    @pytest.mark.asyncio
    async def test_workflow_user_key_created(self, workflow_manager, redis_client, sample_nodes) -> None:
        """Test that user-scoped key is created for user workflows."""
        user_id = "henry"
        workflow = await workflow_manager.create_workflow(
            name="User Key Test",
            nodes=sample_nodes,
            user_id=user_id,
        )

        # Check user-scoped key exists
        user_key = f"builder:user:{user_id}:workflow:{workflow.id}"
        data = await redis_client.get(user_key)

        assert data is not None
        assert "User Key Test" in data


@pytest.mark.xdist_group(name="builder_redis_integration_tests")
class TestRedisWorkflowResilience:
    """Test Redis connection handling and recovery."""

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
    async def test_workflow_with_no_user_id(self, workflow_manager, redis_client, sample_nodes) -> None:
        """Test creating workflow without user_id."""
        workflow = await workflow_manager.create_workflow(
            name="No User Workflow",
            nodes=sample_nodes,
            user_id=None,  # No user
        )

        # Should still persist to main key
        key = f"builder:workflow:{workflow.id}"
        assert await redis_client.exists(key)

        # Can still retrieve
        retrieved = await workflow_manager.get_workflow(workflow.id)
        assert retrieved is not None
        assert retrieved.user_id is None


@pytest.mark.xdist_group(name="builder_redis_integration_tests")
class TestRedisWorkflowUpdateOperations:
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
            user_id="ivy",
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
            user_id="jack",
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
            user_id="kate",
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
