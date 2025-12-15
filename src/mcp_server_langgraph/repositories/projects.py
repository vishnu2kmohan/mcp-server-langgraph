"""
PostgreSQL Project Repository Implementation

Implements the ProjectRepository interface for persistent project storage
using SQLAlchemy async with PostgreSQL.

Supports the Unified Workspace Paradigm:
    One Project = Session + Workflow + Connections
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mcp_server_langgraph.models.project import (
    ProjectConnectionModel,
    ProjectMemberModel,
    ProjectModel,
    ProjectSessionModel,
    ProjectWorkflowModel,
)
from mcp_server_langgraph.storage.base import ProjectRepository
from mcp_server_langgraph.storage.models import (
    Project,
    ProjectConnection,
    ProjectMember,
    ProjectSessionRef,
    ProjectSummary,
    ProjectWorkflowRef,
)


class PostgresProjectRepository(ProjectRepository):
    """PostgreSQL implementation of ProjectRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with async database session."""
        self._session = session

    def _model_to_entity(self, model: ProjectModel) -> Project:
        """Convert SQLAlchemy model to Pydantic entity."""
        return Project(
            id=str(model.id),
            name=model.name,
            description=model.description or "",
            organization_id=model.organization_id,
            owner_id=model.owner_id,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
            workflows=[
                ProjectWorkflowRef(
                    id=str(w.workflow_id),
                    name=w.workflow_name,
                    added_at=w.added_at,
                )
                for w in model.workflows
            ],
            sessions=[
                ProjectSessionRef(
                    id=str(s.session_id),
                    name=s.session_name,
                    message_count=s.message_count,
                    added_at=s.added_at,
                )
                for s in model.sessions
            ],
            connections=[
                ProjectConnection(
                    id=str(c.id),
                    connection_type=c.connection_type,
                    name=c.connection_name,
                    status=c.status,
                    config=c.config,
                    created_at=c.created_at,
                )
                for c in model.connections
            ],
            members=[
                ProjectMember(
                    user_id=m.user_id,
                    role=m.role,
                    added_at=m.added_at,
                )
                for m in model.members
            ],
        )

    def _model_to_summary(self, model: ProjectModel) -> ProjectSummary:
        """Convert SQLAlchemy model to summary Pydantic model."""
        return ProjectSummary(
            id=str(model.id),
            name=model.name,
            description=model.description or "",
            organization_id=model.organization_id,
            owner_id=model.owner_id,
            status=model.status,
            workflow_count=len(model.workflows) if model.workflows else 0,
            session_count=len(model.sessions) if model.sessions else 0,
            connection_count=len(model.connections) if model.connections else 0,
            member_count=len(model.members) if model.members else 0,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def _get_model(self, project_id: str) -> ProjectModel | None:
        """Get project model by ID with all relationships loaded."""
        stmt = (
            select(ProjectModel)
            .options(
                selectinload(ProjectModel.workflows),
                selectinload(ProjectModel.sessions),
                selectinload(ProjectModel.connections),
                selectinload(ProjectModel.members),
            )
            .where(ProjectModel.id == project_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, entity: Project) -> Project:
        """Create a new project."""
        model = ProjectModel(
            id=entity.id or str(uuid4()),
            name=entity.name,
            description=entity.description or None,
            organization_id=entity.organization_id,
            owner_id=entity.owner_id,
            status=entity.status,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self._session.add(model)
        await self._session.flush()

        # Add owner as a member with 'owner' role
        owner_member = ProjectMemberModel(
            project_id=model.id,
            user_id=entity.owner_id,
            role="owner",
            added_at=datetime.now(UTC),
        )
        self._session.add(owner_member)
        await self._session.flush()

        # Reload with relationships
        project = await self._get_model(str(model.id))
        return self._model_to_entity(project) if project else entity

    async def get(self, entity_id: str) -> Project | None:
        """Get a project by ID with all child resources."""
        model = await self._get_model(entity_id)
        return self._model_to_entity(model) if model else None

    async def update(self, entity_id: str, data: dict[str, Any]) -> Project | None:
        """Update a project. Returns None if not found."""
        model = await self._get_model(entity_id)
        if not model:
            return None

        # Update allowed fields
        if "name" in data and data["name"]:
            model.name = data["name"]
        if "description" in data:
            model.description = data["description"]
        if "status" in data and data["status"]:
            model.status = data["status"]

        model.updated_at = datetime.now(UTC)
        await self._session.flush()

        return self._model_to_entity(model)

    async def delete(self, entity_id: str, cascade: bool = False) -> bool:
        """Delete a project. Cascade is handled by DB foreign keys."""
        model = await self._get_model(entity_id)
        if not model:
            return False

        await self._session.delete(model)
        await self._session.flush()
        return True

    async def list(
        self,
        cursor: str | None = None,
        limit: int = 20,
        owner_id: str | None = None,
        organization_id: str | None = None,
        search: str | None = None,
        sort_by: str | None = "created_at",
        sort_order: str | None = "desc",
        **filters: Any,
    ) -> tuple[list[ProjectSummary], str | None]:
        """
        List projects with pagination, filtering, search, and sorting.

        Uses PostgreSQL Full-Text Search (FTS) for efficient search when available,
        falling back to ILIKE for databases without FTS triggers configured.

        Args:
            cursor: Pagination cursor (project ID)
            limit: Maximum number of projects to return
            owner_id: Filter by owner user ID
            organization_id: Filter by organization ID
            search: Search term (uses FTS on name and description)
            sort_by: Field to sort by (name, created_at, updated_at)
            sort_order: Sort order (asc, desc)
            **filters: Additional filters (status)

        Returns:
            Tuple of (list of project summaries, next_cursor)
        """
        stmt = select(ProjectModel).options(
            selectinload(ProjectModel.workflows),
            selectinload(ProjectModel.sessions),
            selectinload(ProjectModel.connections),
            selectinload(ProjectModel.members),
        )

        # Apply filters
        if owner_id:
            stmt = stmt.where(ProjectModel.owner_id == owner_id)
        if organization_id:
            stmt = stmt.where(ProjectModel.organization_id == organization_id)
        if "status" in filters and filters["status"]:
            stmt = stmt.where(ProjectModel.status == filters["status"])

        # Apply search using Full-Text Search (FTS) for efficiency
        if search:
            # Convert search term to tsquery format
            # plainto_tsquery handles plain text input safely
            search_query = func.plainto_tsquery("english", search)

            # Use FTS if search_vector is populated, fallback to ILIKE
            stmt = stmt.where(
                ProjectModel.search_vector.bool_op("@@")(search_query)
                | ProjectModel.name.ilike(f"%{search}%")
                | ProjectModel.description.ilike(f"%{search}%")
            )

        # Determine sort column
        # Use Any type to allow different column types (str, datetime)
        sort_column: Any = ProjectModel.created_at  # Default
        if sort_by == "name":
            sort_column = ProjectModel.name
        elif sort_by == "updated_at":
            sort_column = ProjectModel.updated_at

        # Apply sorting with tiebreaker on ID for stable pagination
        if sort_order == "asc":
            stmt = stmt.order_by(sort_column.asc(), ProjectModel.id.asc())
        else:
            stmt = stmt.order_by(sort_column.desc(), ProjectModel.id.desc())

        # Cursor-based pagination with composite key support
        if cursor:
            cursor_model = await self._get_model(cursor)
            if cursor_model:
                # Build cursor condition based on sort column and order
                if sort_order == "asc":
                    if sort_by == "name":
                        stmt = stmt.where(
                            (ProjectModel.name > cursor_model.name)
                            | ((ProjectModel.name == cursor_model.name) & (ProjectModel.id > cursor_model.id))
                        )
                    elif sort_by == "updated_at":
                        stmt = stmt.where(
                            (ProjectModel.updated_at > cursor_model.updated_at)
                            | ((ProjectModel.updated_at == cursor_model.updated_at) & (ProjectModel.id > cursor_model.id))
                        )
                    else:  # created_at
                        stmt = stmt.where(
                            (ProjectModel.created_at > cursor_model.created_at)
                            | ((ProjectModel.created_at == cursor_model.created_at) & (ProjectModel.id > cursor_model.id))
                        )
                else:  # desc
                    if sort_by == "name":
                        stmt = stmt.where(
                            (ProjectModel.name < cursor_model.name)
                            | ((ProjectModel.name == cursor_model.name) & (ProjectModel.id < cursor_model.id))
                        )
                    elif sort_by == "updated_at":
                        stmt = stmt.where(
                            (ProjectModel.updated_at < cursor_model.updated_at)
                            | ((ProjectModel.updated_at == cursor_model.updated_at) & (ProjectModel.id < cursor_model.id))
                        )
                    else:  # created_at
                        stmt = stmt.where(
                            (ProjectModel.created_at < cursor_model.created_at)
                            | ((ProjectModel.created_at == cursor_model.created_at) & (ProjectModel.id < cursor_model.id))
                        )

        stmt = stmt.limit(limit + 1)  # Fetch one extra to check for next page

        result = await self._session.execute(stmt)
        models = list(result.scalars().all())

        # Determine next cursor
        next_cursor = None
        if len(models) > limit:
            models = models[:limit]
            next_cursor = str(models[-1].id)

        summaries = [self._model_to_summary(m) for m in models]
        return summaries, next_cursor

    # Child resource management

    async def add_workflow(self, project_id: str, workflow_id: str, workflow_name: str) -> Project | None:
        """Add a workflow to a project."""
        model = await self._get_model(project_id)
        if not model:
            return None

        # Check if already exists
        for w in model.workflows:
            if str(w.workflow_id) == workflow_id:
                return self._model_to_entity(model)

        workflow_ref = ProjectWorkflowModel(
            project_id=project_id,
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            added_at=datetime.now(UTC),
        )
        self._session.add(workflow_ref)
        model.updated_at = datetime.now(UTC)
        await self._session.flush()

        return await self.get(project_id)

    async def remove_workflow(self, project_id: str, workflow_id: str) -> Project | None:
        """Remove a workflow from a project."""
        model = await self._get_model(project_id)
        if not model:
            return None

        for w in model.workflows:
            if str(w.workflow_id) == workflow_id:
                await self._session.delete(w)
                break

        model.updated_at = datetime.now(UTC)
        await self._session.flush()

        return await self.get(project_id)

    async def add_session(self, project_id: str, session_id: str, session_name: str) -> Project | None:
        """Add a session to a project."""
        model = await self._get_model(project_id)
        if not model:
            return None

        # Check if already exists
        for s in model.sessions:
            if str(s.session_id) == session_id:
                return self._model_to_entity(model)

        session_ref = ProjectSessionModel(
            project_id=project_id,
            session_id=session_id,
            session_name=session_name,
            message_count=0,
            added_at=datetime.now(UTC),
        )
        self._session.add(session_ref)
        model.updated_at = datetime.now(UTC)
        await self._session.flush()

        return await self.get(project_id)

    async def remove_session(self, project_id: str, session_id: str) -> Project | None:
        """Remove a session from a project."""
        model = await self._get_model(project_id)
        if not model:
            return None

        for s in model.sessions:
            if str(s.session_id) == session_id:
                await self._session.delete(s)
                break

        model.updated_at = datetime.now(UTC)
        await self._session.flush()

        return await self.get(project_id)

    async def add_connection(self, project_id: str, connection: ProjectConnection) -> Project | None:
        """Add a connection to a project."""
        model = await self._get_model(project_id)
        if not model:
            return None

        conn_model = ProjectConnectionModel(
            id=connection.id or str(uuid4()),
            project_id=project_id,
            connection_type=connection.connection_type,
            connection_name=connection.name,
            status=connection.status,
            config=connection.config,
            created_at=datetime.now(UTC),
        )
        self._session.add(conn_model)
        model.updated_at = datetime.now(UTC)
        await self._session.flush()

        return await self.get(project_id)

    async def remove_connection(self, project_id: str, connection_id: str) -> Project | None:
        """Remove a connection from a project."""
        model = await self._get_model(project_id)
        if not model:
            return None

        for c in model.connections:
            if str(c.id) == connection_id:
                await self._session.delete(c)
                break

        model.updated_at = datetime.now(UTC)
        await self._session.flush()

        return await self.get(project_id)

    # Member management

    async def add_member(self, project_id: str, user_id: str, role: str) -> Project | None:
        """Add a member to a project."""
        model = await self._get_model(project_id)
        if not model:
            return None

        # Check if already exists, update role if so
        for m in model.members:
            if m.user_id == user_id:
                m.role = role
                model.updated_at = datetime.now(UTC)
                await self._session.flush()
                return await self.get(project_id)

        member = ProjectMemberModel(
            project_id=project_id,
            user_id=user_id,
            role=role,
            added_at=datetime.now(UTC),
        )
        self._session.add(member)
        model.updated_at = datetime.now(UTC)
        await self._session.flush()

        return await self.get(project_id)

    async def remove_member(self, project_id: str, user_id: str) -> Project | None:
        """Remove a member from a project."""
        model = await self._get_model(project_id)
        if not model:
            return None

        for m in model.members:
            if m.user_id == user_id:
                # Don't allow removing owner
                if m.role == "owner":
                    return self._model_to_entity(model)
                await self._session.delete(m)
                break

        model.updated_at = datetime.now(UTC)
        await self._session.flush()

        return await self.get(project_id)

    async def get_member_role(self, project_id: str, user_id: str) -> str | None:
        """Get a member's role in a project."""
        model = await self._get_model(project_id)
        if not model:
            return None

        for m in model.members:
            if m.user_id == user_id:
                return m.role

        return None
