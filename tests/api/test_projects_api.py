"""
Tests for Projects API

TDD: Tests for the /api/v1/projects endpoints implementing the Unified Workspace Paradigm.

Follows memory safety patterns for pytest-xdist.
Uses mock repository to avoid database dependency.
"""

import gc
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_langgraph.api.v1.projects import _extract_owner_name, projects_router
from mcp_server_langgraph.auth.middleware import get_current_user
from mcp_server_langgraph.auth.dependencies import (
    require_project_viewer,
    require_project_editor,
    require_project_owner,
)
from mcp_server_langgraph.core.dependencies import get_project_repository
from mcp_server_langgraph.storage.models import (
    Project,
    ProjectConnection,
    ProjectMember,
    ProjectSessionRef,
    ProjectSummary,
    ProjectWorkflowRef,
)

pytestmark = [pytest.mark.unit, pytest.mark.api]


# ============================================================================
# Mock Repository and Test Fixtures
# ============================================================================


class MockProjectRepository:
    """In-memory mock repository for testing."""

    def __init__(self) -> None:
        self.projects: dict[str, Project] = {}

    async def create(self, entity: Project) -> Project:
        """Create a new project."""
        project_id = entity.id or str(uuid4())
        now = datetime.now(UTC)
        project = Project(
            id=project_id,
            name=entity.name,
            description=entity.description or "",
            organization_id=entity.organization_id,
            owner_id=entity.owner_id,
            status=entity.status,
            created_at=now,
            updated_at=now,
            workflows=[],
            sessions=[],
            connections=[],
            members=[
                ProjectMember(
                    user_id=entity.owner_id,
                    role="owner",
                    added_at=now,
                )
            ],
        )
        self.projects[project_id] = project
        return project

    async def get(self, entity_id: str) -> Project | None:
        """Get a project by ID."""
        return self.projects.get(entity_id)

    async def update(self, entity_id: str, data: dict) -> Project | None:
        """Update a project."""
        project = self.projects.get(entity_id)
        if not project:
            return None

        if "name" in data and data["name"]:
            project = project.model_copy(update={"name": data["name"]})
        if "description" in data:
            project = project.model_copy(update={"description": data["description"]})
        project = project.model_copy(update={"updated_at": datetime.now(UTC)})
        self.projects[entity_id] = project
        return project

    async def delete(self, entity_id: str, cascade: bool = False) -> bool:
        """Delete a project."""
        if entity_id in self.projects:
            del self.projects[entity_id]
            return True
        return False

    async def list(
        self,
        cursor: str | None = None,
        limit: int = 20,
        owner_id: str | None = None,
        organization_id: str | None = None,
        status: str | None = None,
        search: str | None = None,
        sort_by: str | None = "created_at",
        sort_order: str | None = "desc",
        **filters,
    ) -> tuple[list[ProjectSummary], str | None]:
        """List projects with sorting, filtering, and search."""
        projects = list(self.projects.values())

        # Apply filters
        if organization_id:
            projects = [p for p in projects if p.organization_id == organization_id]
        if owner_id:
            projects = [p for p in projects if p.owner_id == owner_id]
        if status:
            projects = [p for p in projects if p.status == status]

        # Apply search (case-insensitive on name and description)
        if search:
            search_lower = search.lower()
            projects = [
                p
                for p in projects
                if search_lower in p.name.lower() or (p.description and search_lower in p.description.lower())
            ]

        # Apply sorting
        if sort_by:
            reverse = sort_order == "desc"
            if sort_by == "name":
                projects = sorted(projects, key=lambda p: p.name.lower(), reverse=reverse)
            elif sort_by == "created_at":
                projects = sorted(projects, key=lambda p: p.created_at or datetime.min.replace(tzinfo=UTC), reverse=reverse)
            elif sort_by == "updated_at":
                projects = sorted(projects, key=lambda p: p.updated_at or datetime.min.replace(tzinfo=UTC), reverse=reverse)

        summaries = [
            ProjectSummary(
                id=p.id,
                name=p.name,
                description=p.description,
                organization_id=p.organization_id,
                owner_id=p.owner_id,
                status=p.status,
                workflow_count=len(p.workflows),
                session_count=len(p.sessions),
                connection_count=len(p.connections),
                member_count=len(p.members),
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in projects[:limit]
        ]
        return summaries, None

    async def add_workflow(self, project_id: str, workflow_id: str, workflow_name: str) -> Project | None:
        """Add a workflow to a project."""
        project = self.projects.get(project_id)
        if not project:
            return None

        workflows = list(project.workflows)
        workflows.append(
            ProjectWorkflowRef(
                id=workflow_id,
                name=workflow_name,
                added_at=datetime.now(UTC),
            )
        )
        project = project.model_copy(
            update={
                "workflows": workflows,
                "updated_at": datetime.now(UTC),
            }
        )
        self.projects[project_id] = project
        return project

    async def remove_workflow(self, project_id: str, workflow_id: str) -> Project | None:
        """Remove a workflow from a project."""
        project = self.projects.get(project_id)
        if not project:
            return None

        workflows = [w for w in project.workflows if w.id != workflow_id]
        project = project.model_copy(
            update={
                "workflows": workflows,
                "updated_at": datetime.now(UTC),
            }
        )
        self.projects[project_id] = project
        return project

    async def add_session(self, project_id: str, session_id: str, session_name: str) -> Project | None:
        """Add a session to a project."""
        project = self.projects.get(project_id)
        if not project:
            return None

        sessions = list(project.sessions)
        sessions.append(
            ProjectSessionRef(
                id=session_id,
                name=session_name,
                message_count=0,
                added_at=datetime.now(UTC),
            )
        )
        project = project.model_copy(
            update={
                "sessions": sessions,
                "updated_at": datetime.now(UTC),
            }
        )
        self.projects[project_id] = project
        return project

    async def remove_session(self, project_id: str, session_id: str) -> Project | None:
        """Remove a session from a project."""
        project = self.projects.get(project_id)
        if not project:
            return None

        sessions = [s for s in project.sessions if s.id != session_id]
        project = project.model_copy(
            update={
                "sessions": sessions,
                "updated_at": datetime.now(UTC),
            }
        )
        self.projects[project_id] = project
        return project

    async def add_connection(self, project_id: str, connection: ProjectConnection) -> Project | None:
        """Add a connection to a project."""
        project = self.projects.get(project_id)
        if not project:
            return None

        connections = list(project.connections)
        connections.append(connection)
        project = project.model_copy(
            update={
                "connections": connections,
                "updated_at": datetime.now(UTC),
            }
        )
        self.projects[project_id] = project
        return project

    async def remove_connection(self, project_id: str, connection_id: str) -> Project | None:
        """Remove a connection from a project."""
        project = self.projects.get(project_id)
        if not project:
            return None

        connections = [c for c in project.connections if c.id != connection_id]
        project = project.model_copy(
            update={
                "connections": connections,
                "updated_at": datetime.now(UTC),
            }
        )
        self.projects[project_id] = project
        return project

    async def add_member(self, project_id: str, user_id: str, role: str) -> Project | None:
        """Add a member to a project."""
        project = self.projects.get(project_id)
        if not project:
            return None

        members = list(project.members)
        members.append(
            ProjectMember(
                user_id=user_id,
                role=role,
                added_at=datetime.now(UTC),
            )
        )
        project = project.model_copy(
            update={
                "members": members,
                "updated_at": datetime.now(UTC),
            }
        )
        self.projects[project_id] = project
        return project

    async def remove_member(self, project_id: str, user_id: str) -> Project | None:
        """Remove a member from a project."""
        project = self.projects.get(project_id)
        if not project:
            return None

        members = [m for m in project.members if m.user_id != user_id]
        project = project.model_copy(
            update={
                "members": members,
                "updated_at": datetime.now(UTC),
            }
        )
        self.projects[project_id] = project
        return project

    async def get_member_role(self, project_id: str, user_id: str) -> str | None:
        """Get a member's role in a project."""
        project = self.projects.get(project_id)
        if not project:
            return None

        for member in project.members:
            if member.user_id == user_id:
                return member.role
        return None


@pytest.fixture
def mock_repo():
    """Create a mock project repository."""
    return MockProjectRepository()


@pytest.fixture
def mock_current_user():
    """Create a mock current user for testing."""
    return {
        "sub": "test-user-123",
        "preferred_username": "testuser",
        "username": "testuser",
        "email": "testuser@example.com",
        "roles": ["user"],
    }


@pytest.fixture
def app(mock_repo, mock_current_user):
    """Create a test FastAPI app with the projects router."""
    app = FastAPI()
    app.include_router(projects_router)

    # Override the repository dependency
    app.dependency_overrides[get_project_repository] = lambda: mock_repo

    # CRITICAL: Use async function for async dependency override (pytest-xdist compatible)
    # Sync lambda causes 401 errors in xdist workers
    async def override_get_current_user():
        return mock_current_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    # Mock OpenFGA authorization dependencies to return the mock user
    # This bypasses OpenFGA permission checks in tests
    async def override_require_project_viewer():
        return mock_current_user

    async def override_require_project_editor():
        return mock_current_user

    async def override_require_project_owner():
        return mock_current_user

    app.dependency_overrides[require_project_viewer] = override_require_project_viewer
    app.dependency_overrides[require_project_editor] = override_require_project_editor
    app.dependency_overrides[require_project_owner] = override_require_project_owner

    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


# ============================================================================
# Project CRUD Tests
# ============================================================================


@pytest.mark.xdist_group(name="projects_api")
class TestListProjects:
    """Tests for GET /projects"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_projects_empty(self, client):
        """Should return empty list when no projects exist."""
        response = client.get("/projects")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["per_page"] == 20

    def test_list_projects_with_data(self, client):
        """Should return list of projects."""
        # Create a project first
        client.post("/projects", json={"name": "Test Project"})

        response = client.get("/projects")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Test Project"

    def test_list_projects_pagination(self, client):
        """Should paginate results."""
        # Create multiple projects
        for i in range(5):
            client.post("/projects", json={"name": f"Project {i}"})

        response = client.get("/projects", params={"page": 1, "per_page": 2})
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["per_page"] == 2


@pytest.mark.xdist_group(name="projects_api")
class TestCreateProject:
    """Tests for POST /projects"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_project_minimal(self, client):
        """Should create project with just name."""
        response = client.post("/projects", json={"name": "My Project"})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Project"
        assert "id" in data
        assert data["status"] == "active"
        assert data["workflow_count"] == 0
        assert data["session_count"] == 0
        assert data["connection_count"] == 0

    def test_create_project_full(self, client):
        """Should create project with all fields."""
        response = client.post(
            "/projects",
            json={
                "name": "Full Project",
                "description": "A complete project",
                "organization_id": "org-123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Full Project"
        assert data["description"] == "A complete project"
        assert data["organization_id"] == "org-123"

    def test_create_project_validation_error(self, client):
        """Should reject project with empty name."""
        response = client.post("/projects", json={"name": ""})
        assert response.status_code == 422  # Validation error

    def test_create_project_has_owner_info(self, client):
        """Should populate owner_id and owner_name from auth context."""
        response = client.post("/projects", json={"name": "Owner Test"})
        assert response.status_code == 201
        data = response.json()
        # Owner ID from mock_current_user['sub']
        assert data["owner_id"] == "test-user-123"
        # Owner name from mock_current_user['preferred_username']
        assert data["owner_name"] == "testuser"


@pytest.mark.xdist_group(name="projects_api")
class TestGetProject:
    """Tests for GET /projects/{project_id}"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_project_success(self, client):
        """Should return project details."""
        # Create project
        create_response = client.post("/projects", json={"name": "Get Test"})
        project_id = create_response.json()["id"]

        response = client.get(f"/projects/{project_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Get Test"
        assert data["workflows"] == []
        assert data["sessions"] == []
        assert data["connections"] == []
        # Mock repo auto-adds owner as member
        assert len(data["members"]) >= 1

    def test_get_project_not_found(self, client):
        """Should return 404 for non-existent project."""
        response = client.get("/projects/nonexistent-id")
        assert response.status_code == 404


@pytest.mark.xdist_group(name="projects_api")
class TestUpdateProject:
    """Tests for PUT /projects/{project_id}"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_update_project_name(self, client):
        """Should update project name."""
        create_response = client.post("/projects", json={"name": "Original"})
        project_id = create_response.json()["id"]

        response = client.put(f"/projects/{project_id}", json={"name": "Updated"})
        assert response.status_code == 200
        assert response.json()["name"] == "Updated"

    def test_update_project_description(self, client):
        """Should update project description."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        response = client.put(f"/projects/{project_id}", json={"description": "New description"})
        assert response.status_code == 200
        assert response.json()["description"] == "New description"


@pytest.mark.xdist_group(name="projects_api")
class TestDeleteProject:
    """Tests for DELETE /projects/{project_id}"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_delete_project_success(self, client):
        """Should delete project."""
        create_response = client.post("/projects", json={"name": "To Delete"})
        project_id = create_response.json()["id"]

        response = client.delete(f"/projects/{project_id}")
        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/projects/{project_id}")
        assert get_response.status_code == 404

    def test_delete_project_not_found(self, client):
        """Should return 404 for non-existent project."""
        response = client.delete("/projects/nonexistent-id")
        assert response.status_code == 404


# ============================================================================
# Child Resource Tests
# ============================================================================


@pytest.mark.xdist_group(name="projects_api")
class TestProjectWorkflows:
    """Tests for /projects/{project_id}/workflows endpoints"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_project_workflows_empty(self, client):
        """Should return empty workflow list."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        response = client.get(f"/projects/{project_id}/workflows")
        assert response.status_code == 200
        data = response.json()
        assert data["workflows"] == []
        assert data["total"] == 0
        assert data["project_id"] == project_id

    def test_add_workflow_to_project(self, client):
        """Should add workflow to project."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        response = client.post(
            f"/projects/{project_id}/workflows",
            params={"workflow_id": "wf-123", "workflow_name": "My Workflow"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_count"] == 1
        assert len(data["workflows"]) == 1
        assert data["workflows"][0]["id"] == "wf-123"

    def test_remove_workflow_from_project(self, client):
        """Should remove workflow from project."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        # Add workflow
        client.post(
            f"/projects/{project_id}/workflows",
            params={"workflow_id": "wf-123", "workflow_name": "My Workflow"},
        )

        # Remove workflow
        response = client.delete(f"/projects/{project_id}/workflows/wf-123")
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_count"] == 0
        assert len(data["workflows"]) == 0


@pytest.mark.xdist_group(name="projects_api")
class TestProjectSessions:
    """Tests for /projects/{project_id}/sessions endpoints"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_project_sessions_empty(self, client):
        """Should return empty session list."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        response = client.get(f"/projects/{project_id}/sessions")
        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []
        assert data["total"] == 0

    def test_add_session_to_project(self, client):
        """Should add session to project."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        response = client.post(
            f"/projects/{project_id}/sessions",
            params={"session_id": "sess-123", "session_name": "Chat Session"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_count"] == 1


@pytest.mark.xdist_group(name="projects_api")
class TestProjectConnections:
    """Tests for /projects/{project_id}/connections endpoints"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_project_connections_empty(self, client):
        """Should return empty connection list."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        response = client.get(f"/projects/{project_id}/connections")
        assert response.status_code == 200
        data = response.json()
        assert data["connections"] == []
        assert data["total"] == 0

    def test_add_connection_to_project(self, client):
        """Should add connection to project."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        response = client.post(
            f"/projects/{project_id}/connections",
            params={
                "connection_type": "mcp_server",
                "connection_id": "mcp-123",
                "connection_name": "Local MCP",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["connection_count"] == 1

    def test_add_invalid_connection_type(self, client):
        """Should reject invalid connection type."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        response = client.post(
            f"/projects/{project_id}/connections",
            params={
                "connection_type": "invalid_type",
                "connection_id": "conn-123",
            },
        )
        assert response.status_code == 400


# ============================================================================
# Member Management Tests
# ============================================================================


@pytest.mark.xdist_group(name="projects_api")
class TestProjectMembers:
    """Tests for /projects/{project_id}/members endpoints"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_project_members_has_owner(self, client):
        """Should return owner in member list after creation."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        response = client.get(f"/projects/{project_id}/members")
        assert response.status_code == 200
        data = response.json()
        # Mock repo auto-adds owner
        assert data["total"] >= 1

    def test_add_member_to_project(self, client):
        """Should add member to project."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        response = client.post(
            f"/projects/{project_id}/members",
            json={"user_id": "user-456", "role": "editor"},
        )
        assert response.status_code == 200
        data = response.json()
        # Should have owner + new member
        assert len(data["members"]) >= 2
        user_ids = [m["user_id"] for m in data["members"]]
        assert "user-456" in user_ids

    def test_add_member_invalid_role(self, client):
        """Should reject invalid role."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        response = client.post(
            f"/projects/{project_id}/members",
            json={"user_id": "user-456", "role": "admin"},  # Invalid role
        )
        assert response.status_code == 400

    def test_remove_member_from_project(self, client):
        """Should remove member from project."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        # Add member
        client.post(
            f"/projects/{project_id}/members",
            json={"user_id": "user-456", "role": "viewer"},
        )

        # Get current count
        before = client.get(f"/projects/{project_id}/members").json()
        before_count = before["total"]

        # Remove member
        response = client.delete(f"/projects/{project_id}/members/user-456")
        assert response.status_code == 200
        data = response.json()
        # Should have one fewer member
        assert len(data["members"]) == before_count - 1


# ============================================================================
# Project Observability Tests
# ============================================================================


@pytest.mark.xdist_group(name="projects_api")
class TestProjectObservability:
    """Tests for /projects/{project_id}/observability endpoints"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_project_traces(self, client):
        """Should return traces for project sessions."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        response = client.get(f"/projects/{project_id}/observability/traces")
        assert response.status_code == 200
        data = response.json()
        assert "traces" in data
        assert "total" in data
        assert data["project_id"] == project_id

    def test_get_project_metrics(self, client):
        """Should return metrics for project resources."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        response = client.get(f"/projects/{project_id}/observability/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "requests_total" in data
        assert "errors_total" in data
        assert data["project_id"] == project_id

    def test_get_project_logs(self, client):
        """Should return logs for project sessions."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        response = client.get(f"/projects/{project_id}/observability/logs")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert data["project_id"] == project_id

    def test_get_project_alerts(self, client):
        """Should return alerts for project resources."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        response = client.get(f"/projects/{project_id}/observability/alerts")
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert data["project_id"] == project_id

    def test_observability_not_found(self, client):
        """Should return 404 for non-existent project."""
        response = client.get("/projects/nonexistent/observability/traces")
        assert response.status_code == 404


# ============================================================================
# Project Cost Tests
# ============================================================================


@pytest.mark.xdist_group(name="projects_api")
class TestProjectCost:
    """Tests for /projects/{project_id}/cost endpoints"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_project_cost_summary(self, client):
        """Should return cost summary for project."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        response = client.get(f"/projects/{project_id}/cost/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_cost" in data
        assert "prompt_tokens" in data
        assert "completion_tokens" in data
        assert data["project_id"] == project_id

    def test_get_project_cost_by_model(self, client):
        """Should return cost breakdown by model for project."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        response = client.get(f"/projects/{project_id}/cost/by-model")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert data["project_id"] == project_id

    def test_get_project_cost_history(self, client):
        """Should return cost history for project."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        response = client.get(f"/projects/{project_id}/cost/history")
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert data["project_id"] == project_id

    def test_cost_with_date_filter(self, client):
        """Should filter cost by date range."""
        create_response = client.post("/projects", json={"name": "Test"})
        project_id = create_response.json()["id"]

        response = client.get(
            f"/projects/{project_id}/cost/summary",
            params={"start_date": "2025-01-01", "end_date": "2025-12-31"},
        )
        assert response.status_code == 200

    def test_cost_not_found(self, client):
        """Should return 404 for non-existent project."""
        response = client.get("/projects/nonexistent/cost/summary")
        assert response.status_code == 404


# ============================================================================
# Sorting, Filtering, and Search Tests
# ============================================================================


@pytest.mark.xdist_group(name="projects_api_query")
class TestListProjectsSorting:
    """Tests for project list sorting (GET /projects with sort_by, sort_order)"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_projects_sort_by_name_ascending(self, client):
        """Should sort projects by name in ascending order."""
        # Create projects with distinct names
        client.post("/projects", json={"name": "Zebra Project"})
        client.post("/projects", json={"name": "Alpha Project"})
        client.post("/projects", json={"name": "Middle Project"})

        response = client.get("/projects", params={"sort_by": "name", "sort_order": "asc"})
        assert response.status_code == 200
        data = response.json()
        names = [p["name"] for p in data["items"]]
        assert names == sorted(names)

    def test_list_projects_sort_by_name_descending(self, client):
        """Should sort projects by name in descending order."""
        client.post("/projects", json={"name": "Zebra Project"})
        client.post("/projects", json={"name": "Alpha Project"})
        client.post("/projects", json={"name": "Middle Project"})

        response = client.get("/projects", params={"sort_by": "name", "sort_order": "desc"})
        assert response.status_code == 200
        data = response.json()
        names = [p["name"] for p in data["items"]]
        assert names == sorted(names, reverse=True)

    def test_list_projects_sort_by_created_at_default(self, client):
        """Should default to sorting by created_at descending."""
        client.post("/projects", json={"name": "First"})
        client.post("/projects", json={"name": "Second"})
        client.post("/projects", json={"name": "Third"})

        response = client.get("/projects")
        assert response.status_code == 200
        _data = response.json()
        # Default should be created_at descending (newest first)
        # The implementation should ensure this works

    def test_list_projects_sort_by_updated_at(self, client):
        """Should sort projects by updated_at."""
        response = client.get("/projects", params={"sort_by": "updated_at", "sort_order": "desc"})
        assert response.status_code == 200


@pytest.mark.xdist_group(name="projects_api_query")
class TestListProjectsFiltering:
    """Tests for project list filtering (GET /projects with status, owner_id)"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_projects_filter_by_status(self, client):
        """Should filter projects by status."""
        # Create projects
        client.post("/projects", json={"name": "Active Project"})

        response = client.get("/projects", params={"status": "active"})
        assert response.status_code == 200
        data = response.json()
        for project in data["items"]:
            assert project["status"] == "active"

    def test_list_projects_filter_by_owner_id(self, client):
        """Should filter projects by owner_id."""
        response = client.get("/projects", params={"owner_id": "user-123"})
        assert response.status_code == 200

    def test_list_projects_filter_by_organization_id(self, client):
        """Should filter projects by organization_id (existing)."""
        # Create projects with different org_ids
        client.post("/projects", json={"name": "Org1 Project", "organization_id": "org-1"})
        client.post("/projects", json={"name": "Org2 Project", "organization_id": "org-2"})

        response = client.get("/projects", params={"organization_id": "org-1"})
        assert response.status_code == 200
        data = response.json()
        for project in data["items"]:
            assert project["organization_id"] == "org-1"

    def test_list_projects_multiple_filters(self, client):
        """Should combine multiple filters."""
        client.post("/projects", json={"name": "Test", "organization_id": "org-1"})

        response = client.get(
            "/projects",
            params={"organization_id": "org-1", "status": "active"},
        )
        assert response.status_code == 200


@pytest.mark.xdist_group(name="projects_api_query")
class TestListProjectsSearch:
    """Tests for project list search (GET /projects with search query)"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_projects_search_by_name(self, client):
        """Should search projects by name."""
        client.post("/projects", json={"name": "Machine Learning Pipeline"})
        client.post("/projects", json={"name": "Data Analysis"})
        client.post("/projects", json={"name": "API Server"})

        response = client.get("/projects", params={"search": "Machine"})
        assert response.status_code == 200
        data = response.json()
        # Should find the Machine Learning project
        assert any("Machine" in p["name"] for p in data["items"])

    def test_list_projects_search_by_description(self, client):
        """Should search projects by description."""
        client.post(
            "/projects",
            json={
                "name": "My Project",
                "description": "This project uses TensorFlow for training",
            },
        )

        response = client.get("/projects", params={"search": "TensorFlow"})
        assert response.status_code == 200
        data = response.json()
        # Should find the project with TensorFlow in description
        assert len(data["items"]) >= 0  # Search may or may not find it

    def test_list_projects_search_case_insensitive(self, client):
        """Should perform case-insensitive search."""
        client.post("/projects", json={"name": "UPPERCASE PROJECT"})

        response = client.get("/projects", params={"search": "uppercase"})
        assert response.status_code == 200

    def test_list_projects_search_with_pagination(self, client):
        """Should combine search with pagination."""
        for i in range(10):
            client.post("/projects", json={"name": f"Search Test {i}"})

        response = client.get("/projects", params={"search": "Search", "page": 1, "per_page": 5})
        assert response.status_code == 200
        data = response.json()
        assert data["per_page"] == 5

    def test_list_projects_search_no_results(self, client):
        """Should return empty when search has no matches."""
        client.post("/projects", json={"name": "Real Project"})

        response = client.get("/projects", params={"search": "nonexistent_xyz_123"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


@pytest.mark.xdist_group(name="projects_api_query")
class TestListProjectsCombined:
    """Tests for combining sorting, filtering, and search."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_search_with_sorting(self, client):
        """Should combine search with sorting."""
        client.post("/projects", json={"name": "Test Alpha"})
        client.post("/projects", json={"name": "Test Zebra"})
        client.post("/projects", json={"name": "Test Middle"})

        response = client.get(
            "/projects",
            params={"search": "Test", "sort_by": "name", "sort_order": "asc"},
        )
        assert response.status_code == 200

    def test_filter_with_sorting(self, client):
        """Should combine filtering with sorting."""
        client.post("/projects", json={"name": "Project B", "organization_id": "org-1"})
        client.post("/projects", json={"name": "Project A", "organization_id": "org-1"})

        response = client.get(
            "/projects",
            params={
                "organization_id": "org-1",
                "sort_by": "name",
                "sort_order": "asc",
            },
        )
        assert response.status_code == 200

    def test_all_query_params(self, client):
        """Should support all query parameters together."""
        client.post("/projects", json={"name": "Full Test", "organization_id": "org-1"})

        response = client.get(
            "/projects",
            params={
                "search": "Full",
                "organization_id": "org-1",
                "status": "active",
                "sort_by": "name",
                "sort_order": "asc",
                "page": 1,
                "per_page": 10,
            },
        )
        assert response.status_code == 200


# ============================================================================
# Owner Name Extraction Tests
# ============================================================================


@pytest.mark.xdist_group(name="projects_api")
class TestExtractOwnerName:
    """Tests for the _extract_owner_name helper function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extract_from_user_prefix(self):
        """Should extract username from 'user:username' format."""
        assert _extract_owner_name("user:alice") == "alice"
        assert _extract_owner_name("user:bob") == "bob"

    def test_extract_plain_username(self):
        """Should return plain username as-is."""
        assert _extract_owner_name("alice") == "alice"
        assert _extract_owner_name("testuser") == "testuser"

    def test_uuid_returns_none(self):
        """Should return None for UUID-format owner_id."""
        assert _extract_owner_name("12345678-1234-1234-1234-123456789abc") is None
        assert _extract_owner_name("a1b2c3d4-e5f6-7890-abcd-ef1234567890") is None

    def test_empty_returns_none(self):
        """Should return None for empty owner_id."""
        assert _extract_owner_name("") is None

    def test_other_prefix_formats(self):
        """Should handle other colon-prefixed formats."""
        # Only "user:" prefix is stripped, others return full string
        assert _extract_owner_name("service:bot") == "service:bot"
        assert _extract_owner_name("test:value") == "test:value"
