"""
PostgreSQL-backed workflow manager for the Visual Workflow Builder.

Provides durable persistence for production use-cases:
- ACID guarantees for workflow operations
- Full-text search on workflow names/descriptions
- Complex queries for analytics
- Version history support (future)

Example:
    from mcp_server_langgraph.builder.storage import (
        PostgresWorkflowManager,
        create_postgres_engine,
    )

    engine = await create_postgres_engine("postgresql+asyncpg://user:pass@localhost/workflows")
    manager = PostgresWorkflowManager(engine=engine)

    # Create workflow
    workflow = await manager.create_workflow(
        name="My Agent",
        description="A helpful agent",
        nodes=[...],
        edges=[...],
        user_id="user-123",
    )
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .models import StoredWorkflow, WorkflowSummary
from .postgres_models import BuilderBase, WorkflowModel


async def create_postgres_engine(
    database_url: str,
    echo: bool = False,
    pool_size: int = 10,
) -> AsyncEngine:
    """
    Create an async SQLAlchemy engine for workflow storage.

    Args:
        database_url: PostgreSQL connection URL (must use asyncpg driver)
                     Example: postgresql+asyncpg://user:pass@localhost/workflows
        echo: Whether to echo SQL statements (for debugging)
        pool_size: Connection pool size

    Returns:
        Configured AsyncEngine
    """
    engine = create_async_engine(
        database_url,
        echo=echo,
        pool_size=pool_size,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    return engine


async def init_builder_database(engine: AsyncEngine) -> None:
    """
    Initialize the builder database schema.

    Creates all tables defined in BuilderBase if they don't exist.

    Args:
        engine: SQLAlchemy async engine
    """
    async with engine.begin() as conn:
        await conn.run_sync(BuilderBase.metadata.create_all)


class PostgresWorkflowManager:
    """
    PostgreSQL-backed workflow manager for builder workflows.

    Provides durable storage with ACID guarantees for production use.
    """

    def __init__(
        self,
        engine: AsyncEngine,
    ) -> None:
        """
        Initialize the workflow manager.

        Args:
            engine: SQLAlchemy async engine
        """
        self._engine = engine
        self._session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    async def create_workflow(
        self,
        name: str,
        description: str = "",
        nodes: list[dict[str, Any]] | None = None,
        edges: list[dict[str, Any]] | None = None,
        user_id: str | None = None,
    ) -> StoredWorkflow:
        """
        Create a new workflow and store it in PostgreSQL.

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

        workflow_model = WorkflowModel(
            id=workflow_id,
            name=name,
            description=description,
            nodes=nodes or [],
            edges=edges or [],
            user_id=user_id,
            created_at=now,
            updated_at=now,
        )

        async with self._session_maker() as session:
            session.add(workflow_model)
            await session.commit()
            await session.refresh(workflow_model)

        return self._model_to_stored(workflow_model)

    async def get_workflow(self, workflow_id: str) -> StoredWorkflow | None:
        """
        Retrieve a workflow from PostgreSQL.

        Args:
            workflow_id: Workflow ID

        Returns:
            Workflow if found, None otherwise
        """
        async with self._session_maker() as session:
            result = await session.execute(select(WorkflowModel).where(WorkflowModel.id == workflow_id))
            model = result.scalar_one_or_none()

            if not model:
                return None

            return self._model_to_stored(model)

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
        async with self._session_maker() as session:
            result = await session.execute(select(WorkflowModel).where(WorkflowModel.id == workflow_id))
            model = result.scalar_one_or_none()

            if not model:
                return None

            # Update fields
            if name is not None:
                model.name = name
            if description is not None:
                model.description = description
            if nodes is not None:
                model.nodes = nodes
            if edges is not None:
                model.edges = edges

            model.updated_at = datetime.now(UTC)

            await session.commit()
            await session.refresh(model)

            return self._model_to_stored(model)

    async def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete a workflow from PostgreSQL.

        Args:
            workflow_id: Workflow ID

        Returns:
            True if deleted, False if not found
        """
        async with self._session_maker() as session:
            result = await session.execute(select(WorkflowModel).where(WorkflowModel.id == workflow_id))
            model = result.scalar_one_or_none()

            if not model:
                return False

            await session.delete(model)
            await session.commit()

            return True

    async def list_workflows(
        self,
        user_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
        search: str | None = None,
    ) -> list[WorkflowSummary]:
        """
        List workflows, optionally filtered by user and search term.

        Args:
            user_id: Optional user ID to filter by
            limit: Maximum number of workflows to return
            offset: Number of workflows to skip
            search: Optional search term for name/description

        Returns:
            List of workflow summaries
        """
        async with self._session_maker() as session:
            query = select(WorkflowModel)

            # Filter by user if provided
            if user_id:
                query = query.where(WorkflowModel.user_id == user_id)

            # Search by name/description if provided
            if search:
                search_term = f"%{search}%"
                query = query.where((WorkflowModel.name.ilike(search_term)) | (WorkflowModel.description.ilike(search_term)))

            # Order by most recently updated
            query = query.order_by(WorkflowModel.updated_at.desc())

            # Apply pagination
            query = query.limit(limit).offset(offset)

            result = await session.execute(query)
            models = result.scalars().all()

            return [
                WorkflowSummary(
                    id=model.id,
                    name=model.name,
                    description=model.description,
                    node_count=len(model.nodes) if model.nodes else 0,
                    edge_count=len(model.edges) if model.edges else 0,
                    created_at=model.created_at,
                    updated_at=model.updated_at,
                )
                for model in models
            ]

    async def close(self) -> None:
        """Close the database engine."""
        await self._engine.dispose()

    def _model_to_stored(self, model: WorkflowModel) -> StoredWorkflow:
        """Convert SQLAlchemy model to Pydantic model."""
        return StoredWorkflow(
            id=model.id,
            name=model.name,
            description=model.description,
            nodes=model.nodes if model.nodes else [],
            edges=model.edges if model.edges else [],
            user_id=model.user_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
