"""
PostgreSQL-backed workflow manager for the unified Studio frontend.

Provides durable persistence for production use-cases:
- ACID guarantees for workflow operations
- Full-text search on workflow names/descriptions using PostgreSQL tsvector
- Cursor-based pagination for stable ordering
- Complex queries for analytics
- Version history support (future)

Optimization Features:
- FTS using plainto_tsquery with ILIKE fallback
- Cursor pagination with composite keys (sort_column + id) for stable ordering
- Composite indices for efficient filtering and sorting

Example:
    from mcp_server_langgraph.storage.workflow import (
        PostgresWorkflowManager,
        create_postgres_engine,
    )

    engine = await create_postgres_engine("postgresql+asyncpg://user:pass@localhost/db")
    manager = PostgresWorkflowManager(engine=engine)

    # Create workflow
    workflow = await manager.create_workflow(
        name="My Agent",
        description="A helpful agent",
        nodes=[...],
        edges=[...],
        user_id="user-123",
    )

    # List with cursor pagination and FTS
    workflows, next_cursor = await manager.list_workflows(
        user_id="user-123",
        search="agent",
        sort_by="updated_at",
        sort_order="desc",
        limit=20,
    )
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .models import (
    SortOrder,
    StoredWorkflow,
    WorkflowSortField,
    WorkflowSummary,
)
from .postgres_models import WorkflowModel, WorkflowVersionModel


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


async def init_workflow_database(engine: AsyncEngine) -> None:
    """
    Initialize the workflow database connection.

    IMPORTANT: This function NO LONGER creates tables via create_all().
    All schema management is handled exclusively by Alembic migrations.

    The workflows table and related schema are created by migrations:
    - d4e5f6g7h8i9: Creates workflows table with FTS
    - j0k1l2m3n4o5: Adds workflow sharing support
    - s9t0u1v2w3x4: Adds workflow title column

    Args:
        engine: SQLAlchemy async engine

    Note:
        Run 'alembic upgrade head' before using this manager.
    """
    # Verify engine is valid by testing connection
    async with engine.begin():
        pass  # Connection test - schema managed by Alembic


class PostgresWorkflowManager:
    """
    PostgreSQL-backed workflow manager for studio workflows.

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
        cursor: str | None = None,
        search: str | None = None,
        status: str | None = None,
        sort_by: str = WorkflowSortField.UPDATED_AT.value,
        sort_order: str = SortOrder.DESC.value,
    ) -> tuple[list[WorkflowSummary], str | None]:
        """
        List workflows with cursor-based pagination and Full-Text Search.

        Uses PostgreSQL FTS with plainto_tsquery for efficient search,
        falling back to ILIKE when search_vector is not populated.

        Cursor pagination uses composite keys (sort_column + id) for
        stable ordering even when multiple records have the same sort value.

        Args:
            user_id: Optional user ID to filter by
            limit: Maximum number of workflows to return
            cursor: Opaque cursor for pagination (from previous response)
            search: Optional search term (uses FTS with ILIKE fallback)
            status: Optional status filter (active, archived, draft)
            sort_by: Field to sort by (name, created_at, updated_at)
            sort_order: Sort direction (asc, desc)

        Returns:
            Tuple of (workflow summaries, next_cursor)
            next_cursor is None if no more results
        """
        async with self._session_maker() as session:
            query = select(WorkflowModel)

            # Filter by user if provided
            if user_id:
                query = query.where(WorkflowModel.user_id == user_id)

            # Filter by status if provided
            if status:
                query = query.where(WorkflowModel.status == status)

            # Apply Full-Text Search with ILIKE fallback
            if search:
                # Try FTS first if search_vector is populated
                fts_condition = WorkflowModel.search_vector.op("@@")(func.plainto_tsquery("english", search))
                # ILIKE fallback for when search_vector is NULL or FTS not configured
                search_term = f"%{search}%"
                ilike_condition = or_(
                    WorkflowModel.name.ilike(search_term),
                    WorkflowModel.description.ilike(search_term),
                )
                # Use FTS when search_vector is not NULL, otherwise ILIKE
                query = query.where(
                    or_(
                        and_(
                            WorkflowModel.search_vector.isnot(None),
                            fts_condition,
                        ),
                        and_(
                            WorkflowModel.search_vector.is_(None),
                            ilike_condition,
                        ),
                    )
                )

            # Validate and get sort column
            sort_field = (
                WorkflowSortField(sort_by) if sort_by in [e.value for e in WorkflowSortField] else WorkflowSortField.UPDATED_AT
            )
            order = SortOrder(sort_order) if sort_order in [e.value for e in SortOrder] else SortOrder.DESC

            # Get the sort column
            sort_column = getattr(WorkflowModel, sort_field.value)

            # Apply cursor-based pagination
            if cursor:
                cursor_data = self._decode_cursor(cursor)
                if cursor_data:
                    sort_value: Any = cursor_data.get("sort_value")
                    cursor_id = cursor_data.get("id")

                    # Handle datetime parsing for timestamp fields
                    if sort_field in (WorkflowSortField.CREATED_AT, WorkflowSortField.UPDATED_AT):
                        if isinstance(sort_value, str):
                            sort_value = datetime.fromisoformat(sort_value)

                    # Cursor condition for stable pagination
                    # For DESC: (sort_column < cursor_value) OR (sort_column = cursor_value AND id < cursor_id)
                    # For ASC: (sort_column > cursor_value) OR (sort_column = cursor_value AND id > cursor_id)
                    if order == SortOrder.DESC:
                        cursor_condition = or_(
                            sort_column < sort_value,
                            and_(sort_column == sort_value, WorkflowModel.id < cursor_id),
                        )
                    else:
                        cursor_condition = or_(
                            sort_column > sort_value,
                            and_(sort_column == sort_value, WorkflowModel.id > cursor_id),
                        )
                    query = query.where(cursor_condition)

            # Apply ordering with id as tiebreaker for stable pagination
            if order == SortOrder.DESC:
                query = query.order_by(sort_column.desc(), WorkflowModel.id.desc())
            else:
                query = query.order_by(sort_column.asc(), WorkflowModel.id.asc())

            # Fetch one extra to check if there are more results
            query = query.limit(limit + 1)

            result = await session.execute(query)
            models = list(result.scalars().all())

            # Determine if there are more results
            has_more = len(models) > limit
            if has_more:
                models = models[:limit]  # Remove the extra record

            # Build workflow summaries
            summaries = [
                WorkflowSummary(
                    id=model.id,
                    name=model.name,
                    description=model.description,
                    node_count=len(model.nodes) if model.nodes else 0,
                    edge_count=len(model.edges) if model.edges else 0,
                    status=model.status,
                    created_at=model.created_at,
                    updated_at=model.updated_at,
                )
                for model in models
            ]

            # Generate next cursor if there are more results
            next_cursor = None
            if has_more and models:
                last_model = models[-1]
                sort_value = getattr(last_model, sort_field.value)
                if isinstance(sort_value, datetime):
                    sort_value = sort_value.isoformat()
                next_cursor = self._encode_cursor(sort_value, last_model.id)

            return summaries, next_cursor

    def _encode_cursor(self, sort_value: Any, id: str) -> str:
        """Encode cursor data as base64 JSON."""
        cursor_data = {"sort_value": sort_value, "id": id}
        return base64.urlsafe_b64encode(json.dumps(cursor_data).encode()).decode()

    def _decode_cursor(self, cursor: str) -> dict[str, Any] | None:
        """Decode cursor from base64 JSON."""
        try:
            decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
            result = json.loads(decoded)
            if isinstance(result, dict):
                return result
            return None
        except (ValueError, json.JSONDecodeError):
            return None

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
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ==========================================================================
    # Version History Methods
    # ==========================================================================

    async def get_workflow_versions(
        self,
        workflow_id: str,
    ) -> list[WorkflowVersionModel]:
        """
        Get version history for a workflow.

        Returns versions ordered by version_number descending (newest first).

        Args:
            workflow_id: ID of the workflow

        Returns:
            List of WorkflowVersionModel objects
        """
        async with self._session_maker() as session:
            result = await session.execute(
                select(WorkflowVersionModel)
                .where(WorkflowVersionModel.workflow_id == workflow_id)
                .order_by(WorkflowVersionModel.version_number.desc())
            )
            return list(result.scalars().all())

    async def restore_workflow_version(
        self,
        workflow_id: str,
        version_id: str,
        user_id: str,
    ) -> StoredWorkflow:
        """
        Restore a workflow to a previous version.

        Creates a new version with the restored state (append-only, no overwrites).

        Args:
            workflow_id: ID of the workflow
            version_id: ID of the version to restore
            user_id: ID of the user performing the restore

        Returns:
            Updated workflow with new version

        Raises:
            ValueError: If workflow or version not found
        """
        async with self._session_maker() as session:
            # 1. Get the workflow
            workflow_result = await session.execute(select(WorkflowModel).where(WorkflowModel.id == workflow_id))
            workflow = workflow_result.scalar_one_or_none()

            if not workflow:
                raise ValueError(f"Workflow not found: {workflow_id}")

            # 2. Get the version to restore
            version_result = await session.execute(select(WorkflowVersionModel).where(WorkflowVersionModel.id == version_id))
            version_to_restore = version_result.scalar_one_or_none()

            if not version_to_restore:
                raise ValueError(f"Version not found: {version_id}")

            # 3. Get the current max version number
            max_version_result = await session.execute(
                select(func.max(WorkflowVersionModel.version_number)).where(WorkflowVersionModel.workflow_id == workflow_id)
            )
            max_version = max_version_result.scalar() or 0

            # 4. Create a new version with the restored state
            new_version = WorkflowVersionModel(
                id=str(uuid.uuid4()),
                workflow_id=workflow_id,
                version_number=max_version + 1,
                graph_json=version_to_restore.graph_json,
                source_text=version_to_restore.source_text,
                commit_message=f"Restored from version {version_to_restore.version_number}",
                created_by=user_id,
                created_at=datetime.now(UTC),
                prompt_version=version_to_restore.prompt_version,
                prompt_hash=version_to_restore.prompt_hash,
                prompt_model=version_to_restore.prompt_model,
            )
            session.add(new_version)

            # 5. Update the workflow with the restored nodes/edges
            graph_json = version_to_restore.graph_json or {}
            workflow.nodes = graph_json.get("nodes", [])
            workflow.edges = graph_json.get("edges", [])
            workflow.head_version_id = new_version.id
            workflow.updated_at = datetime.now(UTC)

            await session.commit()
            await session.refresh(workflow)

            return self._model_to_stored(workflow)
