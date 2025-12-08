"""
Builder Storage Module.

Provides Redis-backed workflow storage with:
- Workflow CRUD operations
- User-scoped workflow retrieval
- TTL-based expiration for cleanup

Example:
    from mcp_server_langgraph.builder.storage import (
        RedisWorkflowManager,
        create_redis_pool,
    )

    redis_pool = await create_redis_pool("redis://localhost:6379/3")
    manager = RedisWorkflowManager(redis_client=redis_pool)
"""

from .manager import RedisWorkflowManager, create_redis_pool
from .models import StoredWorkflow, WorkflowSummary
from .postgres_manager import PostgresWorkflowManager, create_postgres_engine, init_builder_database
from .postgres_models import BuilderBase, WorkflowModel

__all__ = [
    # Redis storage
    "RedisWorkflowManager",
    "create_redis_pool",
    # Postgres storage
    "PostgresWorkflowManager",
    "create_postgres_engine",
    "init_builder_database",
    "BuilderBase",
    "WorkflowModel",
    # Shared models
    "StoredWorkflow",
    "WorkflowSummary",
]
