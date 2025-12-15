"""
Workflow storage layer for the unified Studio frontend.

Provides persistent workflow storage with multiple backends:
- PostgreSQL: Durable persistence for production (ACID guarantees, versioning)
- Redis: Fast workflow storage with optional TTL
- User-scoped workflow retrieval
- Workflow CRUD operations

Example (PostgreSQL - recommended for production):
    from mcp_server_langgraph.storage.workflow import (
        PostgresWorkflowManager,
        create_postgres_engine,
        init_workflow_database,
    )

    engine = await create_postgres_engine("postgresql+asyncpg://user:pass@localhost/db")
    await init_workflow_database(engine)
    manager = PostgresWorkflowManager(engine=engine)

Example (Redis):
    from mcp_server_langgraph.storage.workflow import (
        RedisWorkflowManager,
        create_redis_pool,
    )

    redis_pool = await create_redis_pool("redis://localhost:6379/3")
    manager = RedisWorkflowManager(redis_client=redis_pool)
"""

from .manager import RedisWorkflowManager, create_redis_pool
from .models import StoredWorkflow, WorkflowSummary
from .postgres_execution_manager import (
    ExecutionBase,
    PostgresExecutionHistoryManager,
    WorkflowExecutionModel,
)
from .postgres_manager import (
    PostgresWorkflowManager,
    create_postgres_engine,
    init_workflow_database,
)
from .postgres_models import WorkflowBase, WorkflowModel

__all__ = [
    # Postgres storage (recommended for production)
    "PostgresWorkflowManager",
    "create_postgres_engine",
    "init_workflow_database",
    "WorkflowBase",
    "WorkflowModel",
    # Postgres execution history
    "PostgresExecutionHistoryManager",
    "ExecutionBase",
    "WorkflowExecutionModel",
    # Redis storage
    "RedisWorkflowManager",
    "create_redis_pool",
    # Shared models
    "StoredWorkflow",
    "WorkflowSummary",
]
