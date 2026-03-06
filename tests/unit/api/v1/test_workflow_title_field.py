"""
Workflow Title Field Tests

TDD tests for the workflow title field feature.
The title field provides a human-friendly display name separate from
the programmatic name field. This follows the artifact pattern:
- id: UUID, immutable primary key
- name: Programmatic identifier (for code refs, exports, URL slugs)
- title: Human-friendly display name shown in UI
- description: Longer explanation
"""

import gc
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


class MockWorkflowServiceAdapter:
    """Mock workflow service adapter for testing."""

    def __init__(self) -> None:
        """Initialize with empty storage."""
        self._workflows: dict[str, dict[str, Any]] = {}

    async def list_workflows(
        self,
        cursor: str | None = None,
        limit: int = 20,
        status: str | None = None,
        owner_id: str | None = None,
        search: str | None = None,
        sort_by: str | None = "created_at",
        sort_order: str | None = "desc",
    ) -> tuple[list[dict[str, Any]], str | None]:
        """List workflows with pagination."""
        workflows = list(self._workflows.values())
        return workflows[:limit], None

    async def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    async def create_workflow(self, workflow_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new workflow."""
        from datetime import UTC, datetime

        workflow_id = str(uuid4())
        now = datetime.now(UTC).isoformat()

        workflow = {
            "id": workflow_id,
            "name": workflow_data["name"],
            "title": workflow_data.get("title", workflow_data["name"]),  # Default to name
            "description": workflow_data.get("description", ""),
            "nodes": workflow_data.get("nodes", []),
            "edges": workflow_data.get("edges", []),
            "user_id": workflow_data.get("user_id"),
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        self._workflows[workflow_id] = workflow
        return workflow

    async def update_workflow(self, workflow_id: str, workflow_data: dict[str, Any]) -> dict[str, Any] | None:
        """Update a workflow."""
        from datetime import UTC, datetime

        if workflow_id not in self._workflows:
            return None

        workflow = self._workflows[workflow_id]
        for key, value in workflow_data.items():
            if value is not None:
                workflow[key] = value
        workflow["updated_at"] = datetime.now(UTC).isoformat()
        return workflow

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            return True
        return False


@pytest.fixture
def mock_workflow_service() -> MockWorkflowServiceAdapter:
    """Create a mock workflow service adapter."""
    return MockWorkflowServiceAdapter()


@pytest.fixture
def test_app(mock_workflow_service: MockWorkflowServiceAdapter) -> FastAPI:
    """Create a test app with the workflows router and mocked service."""
    from mcp_server_langgraph.api.v1.workflows import (
        get_workflow_service,
        workflows_router,
    )
    from mcp_server_langgraph.auth.dependencies import (
        get_current_user,
        require_workflow_editor,
        require_workflow_viewer,
    )

    app = FastAPI()
    app.include_router(workflows_router, prefix="/api/v1")
    app.dependency_overrides[get_workflow_service] = lambda: mock_workflow_service

    # Mock authentication - return an admin user (to bypass owner filtering in list)
    mock_user = {
        "sub": "test-user-id",
        "user_id": "test-user-id",
        "username": "testuser",
        "email": "testuser@example.com",
        "roles": ["admin"],
        "realm_access": {"roles": ["admin"]},
    }

    async def _override_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = _override_current_user

    # Override auth dependencies for workflow routes
    async def _mock_viewer():
        return mock_user

    async def _mock_editor():
        return mock_user

    app.dependency_overrides[require_workflow_viewer] = _mock_viewer
    app.dependency_overrides[require_workflow_editor] = _mock_editor

    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)


@pytest.mark.xdist_group(name="test_workflow_title_field")
class TestWorkflowTitleField:
    """Tests for workflow title field (TDD RED phase)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_workflow_with_title_returns_title(self, client: TestClient) -> None:
        """
        GIVEN valid workflow data with title
        WHEN POST request is made
        THEN response should include the title field
        """
        response = client.post(
            "/api/v1/workflows",
            json={
                "name": "data-pipeline-v1",
                "title": "Customer Data Pipeline",
                "description": "ETL pipeline for customer data",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Customer Data Pipeline"
        assert data["name"] == "data-pipeline-v1"

    def test_create_workflow_without_title_uses_name_as_title(self, client: TestClient) -> None:
        """
        GIVEN workflow data without title
        WHEN POST request is made
        THEN title should default to name value
        """
        response = client.post(
            "/api/v1/workflows",
            json={
                "name": "my-workflow",
                "description": "A workflow without explicit title",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "my-workflow"

    def test_update_workflow_title(self, client: TestClient, mock_workflow_service: MockWorkflowServiceAdapter) -> None:
        """
        GIVEN a workflow exists
        WHEN PUT request updates the title
        THEN response should show updated title
        """
        workflow_id = str(uuid4())
        mock_workflow_service._workflows[workflow_id] = {
            "id": workflow_id,
            "name": "original-name",
            "title": "Original Title",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

        response = client.put(
            f"/api/v1/workflows/{workflow_id}",
            json={"title": "Updated Display Title"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Display Title"
        assert data["name"] == "original-name"

    def test_get_workflow_returns_title(self, client: TestClient, mock_workflow_service: MockWorkflowServiceAdapter) -> None:
        """
        GIVEN a workflow with title exists
        WHEN GET request is made
        THEN response should include title field
        """
        workflow_id = str(uuid4())
        mock_workflow_service._workflows[workflow_id] = {
            "id": workflow_id,
            "name": "api-workflow",
            "title": "API Integration Workflow",
            "description": "Handles API calls",
            "nodes": [],
            "edges": [],
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

        response = client.get(f"/api/v1/workflows/{workflow_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "API Integration Workflow"

    def test_list_workflows_includes_title(
        self, client: TestClient, mock_workflow_service: MockWorkflowServiceAdapter
    ) -> None:
        """
        GIVEN workflows with titles exist
        WHEN GET list request is made
        THEN response should include title in each workflow
        """
        mock_workflow_service._workflows["1"] = {
            "id": "1",
            "name": "workflow-1",
            "title": "First Workflow",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        mock_workflow_service._workflows["2"] = {
            "id": "2",
            "name": "workflow-2",
            "title": "Second Workflow",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

        response = client.get("/api/v1/workflows")
        assert response.status_code == 200
        data = response.json()
        titles = [w["title"] for w in data["data"]]
        assert "First Workflow" in titles
        assert "Second Workflow" in titles
