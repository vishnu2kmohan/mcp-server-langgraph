"""
Unit Tests for PostgresProjectRepository

Tests the project repository implementation for the Unified Workspace Paradigm.
Uses pytest with async support and SQLAlchemy in-memory SQLite for isolation.
"""

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from mcp_server_langgraph.models.project import (
    ProjectMemberModel,
    ProjectModel,
)
from mcp_server_langgraph.repositories.projects import PostgresProjectRepository
from mcp_server_langgraph.storage.models import (
    Project,
    ProjectConnection,
)

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="project_repository")
@pytest.mark.unit
class TestPostgresProjectRepository:
    """Unit tests for PostgresProjectRepository."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        session = AsyncMock()  # async-mock-configured
        session.add = MagicMock()
        session.delete = AsyncMock()  # async-mock-configured
        session.flush = AsyncMock()  # async-mock-configured
        session.execute = AsyncMock()  # async-mock-configured
        return session

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> PostgresProjectRepository:
        """Create a repository instance with mock session."""
        return PostgresProjectRepository(mock_session)

    @pytest.fixture
    def sample_project_model(self) -> ProjectModel:
        """Create a sample project model for testing."""
        project = ProjectModel(
            id=str(uuid4()),
            name="Test Project",
            description="A test project",
            organization_id=None,
            owner_id="user-123",
            status="active",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        # Initialize relationship lists
        project.workflows = []
        project.sessions = []
        project.connections = []
        project.members = [
            ProjectMemberModel(
                project_id=project.id,
                user_id="user-123",
                role="owner",
                added_at=datetime.now(UTC),
            )
        ]
        return project

    @pytest.fixture
    def sample_project_entity(self) -> Project:
        """Create a sample project entity for testing."""
        return Project(
            id=str(uuid4()),
            name="New Project",
            description="A new project",
            organization_id=None,
            owner_id="user-456",
            status="active",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    # =========================================================================
    # CRUD Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_project_success(
        self,
        repository: PostgresProjectRepository,
        mock_session: AsyncMock,
        sample_project_entity: Project,
    ) -> None:
        """Test creating a new project."""
        # GIVEN a project entity to create
        project = sample_project_entity

        # Mock the get after create
        mock_model = MagicMock(spec=ProjectModel)
        mock_model.id = project.id
        mock_model.name = project.name
        mock_model.description = project.description
        mock_model.organization_id = project.organization_id
        mock_model.owner_id = project.owner_id
        mock_model.status = project.status
        mock_model.created_at = project.created_at
        mock_model.updated_at = project.updated_at
        mock_model.workflows = []
        mock_model.sessions = []
        mock_model.connections = []
        mock_model.members = [
            MagicMock(
                user_id=project.owner_id,
                role="owner",
                added_at=datetime.now(UTC),
            )
        ]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        # WHEN creating the project
        result = await repository.create(project)

        # THEN the project is created successfully
        assert result is not None
        assert result.name == project.name
        assert result.owner_id == project.owner_id
        mock_session.add.assert_called()
        mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_get_project_found(
        self,
        repository: PostgresProjectRepository,
        mock_session: AsyncMock,
        sample_project_model: ProjectModel,
    ) -> None:
        """Test getting an existing project."""
        # GIVEN a project exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project_model
        mock_session.execute.return_value = mock_result

        # WHEN getting the project
        result = await repository.get(sample_project_model.id)

        # THEN the project is returned
        assert result is not None
        assert result.id == sample_project_model.id
        assert result.name == sample_project_model.name

    @pytest.mark.asyncio
    async def test_get_project_not_found(
        self,
        repository: PostgresProjectRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting a non-existent project."""
        # GIVEN no project exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # WHEN getting a non-existent project
        result = await repository.get("non-existent-id")

        # THEN None is returned
        assert result is None

    @pytest.mark.asyncio
    async def test_update_project_success(
        self,
        repository: PostgresProjectRepository,
        mock_session: AsyncMock,
        sample_project_model: ProjectModel,
    ) -> None:
        """Test updating a project."""
        # GIVEN a project exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project_model
        mock_session.execute.return_value = mock_result

        # WHEN updating the project
        result = await repository.update(
            sample_project_model.id,
            {"name": "Updated Name", "description": "Updated description"},
        )

        # THEN the project is updated
        assert result is not None
        assert sample_project_model.name == "Updated Name"
        assert sample_project_model.description == "Updated description"
        mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_update_project_not_found(
        self,
        repository: PostgresProjectRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test updating a non-existent project."""
        # GIVEN no project exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # WHEN updating a non-existent project
        result = await repository.update("non-existent-id", {"name": "New Name"})

        # THEN None is returned
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_project_success(
        self,
        repository: PostgresProjectRepository,
        mock_session: AsyncMock,
        sample_project_model: ProjectModel,
    ) -> None:
        """Test deleting a project."""
        # GIVEN a project exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project_model
        mock_session.execute.return_value = mock_result

        # WHEN deleting the project
        result = await repository.delete(sample_project_model.id)

        # THEN the project is deleted
        assert result is True
        mock_session.delete.assert_called_with(sample_project_model)
        mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_delete_project_not_found(
        self,
        repository: PostgresProjectRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test deleting a non-existent project."""
        # GIVEN no project exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # WHEN deleting a non-existent project
        result = await repository.delete("non-existent-id")

        # THEN False is returned
        assert result is False

    # =========================================================================
    # List Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_list_projects_empty(
        self,
        repository: PostgresProjectRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing projects when none exist."""
        # GIVEN no projects exist
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # WHEN listing projects
        summaries, next_cursor = await repository.list()

        # THEN empty list is returned
        assert summaries == []
        assert next_cursor is None

    @pytest.mark.asyncio
    async def test_list_projects_with_results(
        self,
        repository: PostgresProjectRepository,
        mock_session: AsyncMock,
        sample_project_model: ProjectModel,
    ) -> None:
        """Test listing projects with results."""
        # GIVEN projects exist
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_project_model]
        mock_session.execute.return_value = mock_result

        # WHEN listing projects
        summaries, next_cursor = await repository.list()

        # THEN projects are returned
        assert len(summaries) == 1
        assert summaries[0].id == sample_project_model.id
        assert next_cursor is None

    # =========================================================================
    # Child Resource Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_add_workflow_success(
        self,
        repository: PostgresProjectRepository,
        mock_session: AsyncMock,
        sample_project_model: ProjectModel,
    ) -> None:
        """Test adding a workflow to a project."""
        # GIVEN a project exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project_model
        mock_session.execute.return_value = mock_result

        # WHEN adding a workflow
        result = await repository.add_workflow(
            sample_project_model.id,
            str(uuid4()),
            "Test Workflow",
        )

        # THEN the workflow is added
        assert result is not None
        mock_session.add.assert_called()
        mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_add_session_success(
        self,
        repository: PostgresProjectRepository,
        mock_session: AsyncMock,
        sample_project_model: ProjectModel,
    ) -> None:
        """Test adding a session to a project."""
        # GIVEN a project exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project_model
        mock_session.execute.return_value = mock_result

        # WHEN adding a session
        result = await repository.add_session(
            sample_project_model.id,
            str(uuid4()),
            "Test Session",
        )

        # THEN the session is added
        assert result is not None
        mock_session.add.assert_called()
        mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_add_connection_success(
        self,
        repository: PostgresProjectRepository,
        mock_session: AsyncMock,
        sample_project_model: ProjectModel,
    ) -> None:
        """Test adding a connection to a project."""
        # GIVEN a project exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project_model
        mock_session.execute.return_value = mock_result

        connection = ProjectConnection(
            id=str(uuid4()),
            connection_type="mcp_server",
            name="Test MCP",
            status="active",
        )

        # WHEN adding a connection
        result = await repository.add_connection(
            sample_project_model.id,
            connection,
        )

        # THEN the connection is added
        assert result is not None
        mock_session.add.assert_called()
        mock_session.flush.assert_called()

    # =========================================================================
    # Member Management Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_add_member_success(
        self,
        repository: PostgresProjectRepository,
        mock_session: AsyncMock,
        sample_project_model: ProjectModel,
    ) -> None:
        """Test adding a member to a project."""
        # GIVEN a project exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project_model
        mock_session.execute.return_value = mock_result

        # WHEN adding a member
        result = await repository.add_member(
            sample_project_model.id,
            "new-user",
            "editor",
        )

        # THEN the member is added
        assert result is not None
        mock_session.add.assert_called()
        mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_get_member_role_found(
        self,
        repository: PostgresProjectRepository,
        mock_session: AsyncMock,
        sample_project_model: ProjectModel,
    ) -> None:
        """Test getting a member's role."""
        # GIVEN a project with a member exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project_model
        mock_session.execute.return_value = mock_result

        # WHEN getting the member's role
        role = await repository.get_member_role(
            sample_project_model.id,
            "user-123",
        )

        # THEN the role is returned
        assert role == "owner"

    @pytest.mark.asyncio
    async def test_get_member_role_not_member(
        self,
        repository: PostgresProjectRepository,
        mock_session: AsyncMock,
        sample_project_model: ProjectModel,
    ) -> None:
        """Test getting role for non-member."""
        # GIVEN a project exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project_model
        mock_session.execute.return_value = mock_result

        # WHEN getting role for non-member
        role = await repository.get_member_role(
            sample_project_model.id,
            "not-a-member",
        )

        # THEN None is returned
        assert role is None

    # =========================================================================
    # Model Conversion Tests
    # =========================================================================

    def test_model_to_entity_conversion(
        self,
        repository: PostgresProjectRepository,
        sample_project_model: ProjectModel,
    ) -> None:
        """Test converting SQLAlchemy model to Pydantic entity."""
        # GIVEN a project model
        # WHEN converting to entity
        entity = repository._model_to_entity(sample_project_model)

        # THEN the entity has correct values
        assert entity.id == sample_project_model.id
        assert entity.name == sample_project_model.name
        assert entity.owner_id == sample_project_model.owner_id
        assert len(entity.members) == 1
        assert entity.members[0].role == "owner"

    def test_model_to_summary_conversion(
        self,
        repository: PostgresProjectRepository,
        sample_project_model: ProjectModel,
    ) -> None:
        """Test converting SQLAlchemy model to summary."""
        # GIVEN a project model
        # WHEN converting to summary
        summary = repository._model_to_summary(sample_project_model)

        # THEN the summary has correct values
        assert summary.id == sample_project_model.id
        assert summary.name == sample_project_model.name
        assert summary.member_count == 1
        assert summary.workflow_count == 0
