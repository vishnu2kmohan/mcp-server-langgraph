"""
Redis-backed workflow manager for the unified Studio frontend.

Provides:
- Workflow CRUD operations via Redis
- User-scoped workflow retrieval
- TTL-based automatic cleanup
- Cursor-based pagination for consistent API

Example:
    from mcp_server_langgraph.storage.workflow import (
        RedisWorkflowManager,
        create_redis_pool,
    )

    redis_pool = await create_redis_pool("redis://localhost:6379/3")

    # Create manager
    manager = RedisWorkflowManager(redis_client=redis_pool, ttl_seconds=86400)

    # Create workflow
    workflow = await manager.create_workflow(
        name="My Agent",
        description="A helpful agent",
        nodes=[...],
        edges=[...],
        user_id="user-123",
    )

    # List workflows with cursor pagination
    workflows, next_cursor = await manager.list_workflows(user_id="user-123")
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as redis

from .models import SortOrder, StoredWorkflow, WorkflowSortField, WorkflowSummary

# Redis key prefix for workflows
WORKFLOW_KEY_PREFIX = "workflow:"
USER_WORKFLOW_KEY_PREFIX = "workflow:user:"


async def create_redis_pool(
    redis_url: str,
    max_connections: int = 10,
) -> redis.Redis:
    """
    Create a Redis connection pool for workflow storage.

    Args:
        redis_url: Redis connection URL (e.g., "redis://localhost:6379/3")
        max_connections: Maximum connections in pool

    Returns:
        Configured Redis client with connection pool
    """
    client: redis.Redis = redis.from_url(  # type: ignore[no-untyped-call]
        redis_url,
        max_connections=max_connections,
        decode_responses=True,
    )
    return client


class RedisWorkflowManager:
    """
    Redis-backed workflow manager for studio workflows.

    Stores workflows in Redis with optional TTL expiration.
    Uses separate key patterns for workflow-by-id and user-scoped listings.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        ttl_seconds: int | None = None,
    ) -> None:
        """
        Initialize the workflow manager.

        Args:
            redis_client: Redis client (with connection pool)
            ttl_seconds: Optional TTL for workflows (None = no expiration)
        """
        self._redis = redis_client
        self._ttl = ttl_seconds

    def _workflow_key(self, workflow_id: str) -> str:
        """Generate Redis key for a workflow."""
        return f"{WORKFLOW_KEY_PREFIX}{workflow_id}"

    def _user_workflow_key(self, user_id: str, workflow_id: str) -> str:
        """Generate Redis key for user-scoped workflow."""
        return f"{USER_WORKFLOW_KEY_PREFIX}{user_id}:workflow:{workflow_id}"

    async def create_workflow(
        self,
        name: str,
        description: str = "",
        nodes: list[dict[str, Any]] | None = None,
        edges: list[dict[str, Any]] | None = None,
        user_id: str | None = None,
    ) -> StoredWorkflow:
        """
        Create a new workflow and store it in Redis.

        Args:
            name: Workflow name
            description: Optional description
            nodes: List of node definitions
            edges: List of edge definitions
            user_id: Optional user ID for scoping

        Returns:
            Created workflow
        """
        workflow_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        workflow = StoredWorkflow(
            id=workflow_id,
            name=name,
            description=description,
            nodes=nodes or [],
            edges=edges or [],
            user_id=user_id,
            created_at=now,
            updated_at=now,
        )

        # Store in Redis
        key = self._workflow_key(workflow_id)
        if self._ttl:
            await self._redis.setex(key, self._ttl, workflow.model_dump_json())
        else:
            await self._redis.set(key, workflow.model_dump_json())

        # Also store under user key if user_id provided
        if user_id:
            user_key = self._user_workflow_key(user_id, workflow_id)
            if self._ttl:
                await self._redis.setex(user_key, self._ttl, workflow.model_dump_json())
            else:
                await self._redis.set(user_key, workflow.model_dump_json())

        return workflow

    async def get_workflow(self, workflow_id: str) -> StoredWorkflow | None:
        """
        Retrieve a workflow from Redis.

        Args:
            workflow_id: Workflow ID

        Returns:
            Workflow if found, None otherwise
        """
        key = self._workflow_key(workflow_id)
        data = await self._redis.get(key)

        if not data:
            return None

        return StoredWorkflow.model_validate_json(data)

    async def update_workflow(
        self,
        workflow_id: str,
        name: str | None = None,
        description: str | None = None,
        nodes: list[dict[str, Any]] | None = None,
        edges: list[dict[str, Any]] | None = None,
    ) -> StoredWorkflow | None:
        """
        Update an existing workflow.

        Args:
            workflow_id: Workflow ID
            name: Optional new name
            description: Optional new description
            nodes: Optional new nodes
            edges: Optional new edges

        Returns:
            Updated workflow if found, None otherwise
        """
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            return None

        # Update fields
        if name is not None:
            workflow.name = name
        if description is not None:
            workflow.description = description
        if nodes is not None:
            workflow.nodes = nodes
        if edges is not None:
            workflow.edges = edges

        workflow.updated_at = datetime.now(UTC)

        # Store updated workflow
        key = self._workflow_key(workflow_id)
        if self._ttl:
            await self._redis.setex(key, self._ttl, workflow.model_dump_json())
        else:
            await self._redis.set(key, workflow.model_dump_json())

        # Update user key if applicable
        if workflow.user_id:
            user_key = self._user_workflow_key(workflow.user_id, workflow_id)
            if self._ttl:
                await self._redis.setex(user_key, self._ttl, workflow.model_dump_json())
            else:
                await self._redis.set(user_key, workflow.model_dump_json())

        return workflow

    async def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete a workflow from Redis.

        Args:
            workflow_id: Workflow ID

        Returns:
            True if deleted, False if not found
        """
        # Get workflow first to check user_id
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            return False

        key = self._workflow_key(workflow_id)
        result = await self._redis.delete(key)

        # Also delete user key if applicable
        if workflow.user_id:
            user_key = self._user_workflow_key(workflow.user_id, workflow_id)
            await self._redis.delete(user_key)

        return bool(result > 0)

    async def list_workflows(
        self,
        user_id: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
        search: str | None = None,
        status: str | None = None,
        sort_by: str = WorkflowSortField.UPDATED_AT.value,
        sort_order: str = SortOrder.DESC.value,
    ) -> tuple[list[WorkflowSummary], str | None]:
        """
        List workflows with pagination.

        Note: Redis backend has limited sorting/search capabilities.
        For full FTS and efficient pagination, use PostgresWorkflowManager.

        Args:
            user_id: Optional user ID to filter by
            limit: Maximum number of workflows to return
            cursor: Pagination cursor (Redis scan cursor encoded as string)
            search: Optional search term (client-side filtering in Redis)
            status: Optional status filter (client-side filtering in Redis)
            sort_by: Sort field (client-side sorting in Redis)
            sort_order: Sort order (client-side sorting in Redis)

        Returns:
            Tuple of (workflow summaries, next_cursor)
        """
        pattern = f"{USER_WORKFLOW_KEY_PREFIX}{user_id}:workflow:*" if user_id else f"{WORKFLOW_KEY_PREFIX}*"

        workflows: list[WorkflowSummary] = []
        redis_cursor = int(cursor) if cursor else 0

        # Fetch more than needed to allow for filtering
        fetch_limit = (limit + 1) * 3 if search or status else limit + 1

        while len(workflows) < fetch_limit:
            redis_cursor, keys = await self._redis.scan(cursor=redis_cursor, match=pattern, count=100)

            for key in keys:
                if len(workflows) >= fetch_limit:
                    break
                data = await self._redis.get(key)
                if data:
                    workflow = StoredWorkflow.model_validate_json(data)

                    # Apply status filter if provided
                    if status and workflow.status != status:
                        continue

                    # Apply search filter if provided (client-side)
                    if search:
                        search_lower = search.lower()
                        if search_lower not in workflow.name.lower() and search_lower not in workflow.description.lower():
                            continue

                    summary = WorkflowSummary(
                        id=workflow.id,
                        name=workflow.name,
                        description=workflow.description,
                        node_count=len(workflow.nodes),
                        edge_count=len(workflow.edges),
                        status=workflow.status,
                        created_at=workflow.created_at,
                        updated_at=workflow.updated_at,
                    )
                    workflows.append(summary)

            if redis_cursor == 0:
                break

        # Sort workflows client-side
        reverse = sort_order == SortOrder.DESC.value
        if sort_by == WorkflowSortField.NAME.value:
            workflows.sort(key=lambda w: w.name.lower(), reverse=reverse)
        elif sort_by == WorkflowSortField.CREATED_AT.value:
            workflows.sort(key=lambda w: w.created_at, reverse=reverse)
        else:  # updated_at is default
            workflows.sort(key=lambda w: w.updated_at, reverse=reverse)

        # Apply limit and determine next cursor
        has_more = len(workflows) > limit
        if has_more:
            workflows = workflows[:limit]

        # For Redis, use scan cursor as pagination cursor
        next_cursor = str(redis_cursor) if has_more and redis_cursor != 0 else None

        return workflows, next_cursor

    async def close(self) -> None:
        """Close the Redis connection."""
        await self._redis.close()
