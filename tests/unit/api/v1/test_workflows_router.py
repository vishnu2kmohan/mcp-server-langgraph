"""
Workflows Router Unit Tests

Tests for /api/v1/workflows endpoints per TDD methodology.
Tests written FIRST before implementation (RED phase).

The workflows endpoint provides CRUD operations for workflow management.
"""

import gc
from collections.abc import Generator
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

        # Apply filters
        if status:
            workflows = [w for w in workflows if w.get("status") == status]
        if owner_id:
            workflows = [w for w in workflows if w.get("user_id") == owner_id]
        if search:
            search_lower = search.lower()
            workflows = [
                w
                for w in workflows
                if search_lower in w.get("name", "").lower() or search_lower in w.get("description", "").lower()
            ]

        # Apply sorting
        if sort_by:
            reverse = sort_order == "desc"
            workflows.sort(key=lambda w: w.get(sort_by, ""), reverse=reverse)

        # Apply pagination
        start_idx = 0
        if cursor:
            try:
                start_idx = int(cursor)
            except ValueError:
                start_idx = 0

        end_idx = start_idx + limit
        result = workflows[start_idx:end_idx]
        next_cursor = str(end_idx) if end_idx < len(workflows) else None

        return result, next_cursor

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
    from mcp_server_langgraph.auth.dependencies import get_current_user

    app = FastAPI()
    app.include_router(workflows_router, prefix="/api/v1")

    # Override the workflow service dependency
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
    app.dependency_overrides[get_current_user] = lambda: mock_user

    return app


@pytest.fixture
def client(test_app: FastAPI, mock_workflow_service: MockWorkflowServiceAdapter) -> Generator[TestClient, None, None]:
    """Create a test client.

    Also depends on mock_workflow_service to ensure pytest injects the same
    instance to both the test_app and tests that need it.
    """
    with TestClient(test_app) as client:
        yield client
    # Clear dependency overrides after test
    test_app.dependency_overrides.clear()


@pytest.fixture
def sample_workflow() -> dict:
    """Sample workflow data for testing."""
    return {
        "id": str(uuid4()),
        "name": "Test Workflow",
        "description": "A test workflow for unit testing",
        "nodes": [
            {"id": "node1", "type": "start", "position": {"x": 0, "y": 0}},
            {"id": "node2", "type": "llm", "position": {"x": 200, "y": 0}},
            {"id": "node3", "type": "end", "position": {"x": 400, "y": 0}},
        ],
        "edges": [
            {"source": "node1", "target": "node2"},
            {"source": "node2", "target": "node3"},
        ],
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }


@pytest.mark.xdist_group(name="test_workflows_router")
class TestWorkflowsListEndpoint:
    """Tests for GET /api/v1/workflows endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_workflows_returns_200(self, client: TestClient) -> None:
        """
        GIVEN a request to /api/v1/workflows
        WHEN GET request is made
        THEN response should be 200 OK
        """
        response = client.get("/api/v1/workflows")
        assert response.status_code == 200

    def test_list_workflows_returns_array(self, client: TestClient, mock_workflow_service: MockWorkflowServiceAdapter) -> None:
        """
        GIVEN workflows exist
        WHEN GET request is made
        THEN response should contain array of workflows
        """
        # Add a workflow to the mock service
        mock_workflow_service._workflows["1"] = {
            "id": "1",
            "name": "Test",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

        response = client.get("/api/v1/workflows")
        data = response.json()

        assert "data" in data
        assert isinstance(data["data"], list)

    def test_list_workflows_with_pagination(
        self, client: TestClient, mock_workflow_service: MockWorkflowServiceAdapter
    ) -> None:
        """
        GIVEN pagination parameters
        WHEN GET request is made with cursor and limit
        THEN response should include pagination metadata
        """
        # Add multiple workflows to test pagination
        for i in range(25):
            mock_workflow_service._workflows[str(i)] = {
                "id": str(i),
                "name": f"Test {i}",
                "description": "",
                "nodes": [],
                "edges": [],
                "status": "active",
                "created_at": f"2025-01-0{(i % 9) + 1}T00:00:00Z",
                "updated_at": f"2025-01-0{(i % 9) + 1}T00:00:00Z",
            }

        response = client.get("/api/v1/workflows?limit=10")
        data = response.json()

        assert "pagination" in data
        assert "has_next" in data["pagination"]


@pytest.mark.xdist_group(name="test_workflows_router")
class TestWorkflowsGetEndpoint:
    """Tests for GET /api/v1/workflows/{id} endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_workflow_returns_200(
        self,
        client: TestClient,
        mock_workflow_service: MockWorkflowServiceAdapter,
        sample_workflow: dict,
    ) -> None:
        """
        GIVEN a workflow exists
        WHEN GET request is made with workflow ID
        THEN response should be 200 OK
        """
        # Add the sample workflow to the mock service
        mock_workflow_service._workflows[sample_workflow["id"]] = sample_workflow

        response = client.get(f"/api/v1/workflows/{sample_workflow['id']}")
        assert response.status_code == 200

    def test_get_workflow_returns_workflow_data(
        self,
        client: TestClient,
        mock_workflow_service: MockWorkflowServiceAdapter,
        sample_workflow: dict,
    ) -> None:
        """
        GIVEN a workflow exists
        WHEN GET request is made
        THEN response should contain workflow data
        """
        mock_workflow_service._workflows[sample_workflow["id"]] = sample_workflow

        response = client.get(f"/api/v1/workflows/{sample_workflow['id']}")
        data = response.json()

        assert data["id"] == sample_workflow["id"]
        assert data["name"] == sample_workflow["name"]

    def test_get_workflow_not_found_returns_404(self, client: TestClient) -> None:
        """
        GIVEN a workflow does not exist
        WHEN GET request is made
        THEN response should be 404 Not Found
        """
        workflow_id = str(uuid4())
        response = client.get(f"/api/v1/workflows/{workflow_id}")
        assert response.status_code == 404


@pytest.mark.xdist_group(name="test_workflows_router")
class TestWorkflowsCreateEndpoint:
    """Tests for POST /api/v1/workflows endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_workflow_returns_201(self, client: TestClient, sample_workflow: dict) -> None:
        """
        GIVEN valid workflow data
        WHEN POST request is made
        THEN response should be 201 Created
        """
        response = client.post(
            "/api/v1/workflows",
            json={
                "name": sample_workflow["name"],
                "description": sample_workflow["description"],
                "nodes": sample_workflow["nodes"],
                "edges": sample_workflow["edges"],
            },
        )
        assert response.status_code == 201

    def test_create_workflow_returns_created_workflow(self, client: TestClient, sample_workflow: dict) -> None:
        """
        GIVEN valid workflow data
        WHEN POST request is made
        THEN response should contain created workflow with ID
        """
        response = client.post(
            "/api/v1/workflows",
            json={
                "name": sample_workflow["name"],
                "description": sample_workflow["description"],
                "nodes": sample_workflow["nodes"],
                "edges": sample_workflow["edges"],
            },
        )
        data = response.json()

        assert "id" in data
        assert data["name"] == sample_workflow["name"]

    def test_create_workflow_validates_required_fields(self, client: TestClient) -> None:
        """
        GIVEN invalid workflow data (missing required fields)
        WHEN POST request is made
        THEN response should be 422 Unprocessable Entity
        """
        response = client.post(
            "/api/v1/workflows",
            json={},  # Missing required 'name' field
        )
        assert response.status_code == 422


@pytest.mark.xdist_group(name="test_workflows_router")
class TestWorkflowsUpdateEndpoint:
    """Tests for PUT /api/v1/workflows/{id} endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_update_workflow_returns_200(
        self,
        client: TestClient,
        mock_workflow_service: MockWorkflowServiceAdapter,
        sample_workflow: dict,
    ) -> None:
        """
        GIVEN a workflow exists
        WHEN PUT request is made with updated data
        THEN response should be 200 OK
        """
        mock_workflow_service._workflows[sample_workflow["id"]] = sample_workflow

        response = client.put(
            f"/api/v1/workflows/{sample_workflow['id']}",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200

    def test_update_workflow_not_found_returns_404(self, client: TestClient) -> None:
        """
        GIVEN a workflow does not exist
        WHEN PUT request is made
        THEN response should be 404 Not Found
        """
        workflow_id = str(uuid4())
        response = client.put(
            f"/api/v1/workflows/{workflow_id}",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 404


@pytest.mark.xdist_group(name="test_workflows_router")
class TestWorkflowsDeleteEndpoint:
    """Tests for DELETE /api/v1/workflows/{id} endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_delete_workflow_returns_204(
        self,
        client: TestClient,
        mock_workflow_service: MockWorkflowServiceAdapter,
        sample_workflow: dict,
    ) -> None:
        """
        GIVEN a workflow exists
        WHEN DELETE request is made
        THEN response should be 204 No Content
        """
        mock_workflow_service._workflows[sample_workflow["id"]] = sample_workflow

        response = client.delete(f"/api/v1/workflows/{sample_workflow['id']}")
        assert response.status_code == 204

    def test_delete_workflow_not_found_returns_404(self, client: TestClient) -> None:
        """
        GIVEN a workflow does not exist
        WHEN DELETE request is made
        THEN response should be 404 Not Found
        """
        workflow_id = str(uuid4())
        response = client.delete(f"/api/v1/workflows/{workflow_id}")
        assert response.status_code == 404


# ============================================================================
# Sorting Tests
# ============================================================================


@pytest.mark.xdist_group(name="test_workflows_router_query")
class TestWorkflowsListSorting:
    """Tests for sorting workflows via GET /api/v1/workflows."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_workflows_sort_by_name_ascending(
        self, client: TestClient, mock_workflow_service: MockWorkflowServiceAdapter
    ) -> None:
        """
        GIVEN workflows exist
        WHEN GET request with sort_by=name and sort_order=asc
        THEN response should be 200 OK with sorted results
        """
        # Add workflows with different names
        mock_workflow_service._workflows["1"] = {
            "id": "1",
            "name": "Zebra Workflow",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        mock_workflow_service._workflows["2"] = {
            "id": "2",
            "name": "Alpha Workflow",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "active",
            "created_at": "2025-01-02T00:00:00Z",
            "updated_at": "2025-01-02T00:00:00Z",
        }

        response = client.get("/api/v1/workflows?sort_by=name&sort_order=asc")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        # Ascending order: Alpha before Zebra
        assert data["data"][0]["name"] == "Alpha Workflow"
        assert data["data"][1]["name"] == "Zebra Workflow"

    def test_list_workflows_sort_by_created_at_descending(
        self, client: TestClient, mock_workflow_service: MockWorkflowServiceAdapter
    ) -> None:
        """
        GIVEN workflows exist
        WHEN GET request with sort_by=created_at and sort_order=desc
        THEN response should show newest first
        """
        mock_workflow_service._workflows["1"] = {
            "id": "1",
            "name": "Old Workflow",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        mock_workflow_service._workflows["2"] = {
            "id": "2",
            "name": "New Workflow",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "active",
            "created_at": "2025-01-10T00:00:00Z",
            "updated_at": "2025-01-10T00:00:00Z",
        }

        response = client.get("/api/v1/workflows?sort_by=created_at&sort_order=desc")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        # Descending order: Newer first
        assert data["data"][0]["name"] == "New Workflow"
        assert data["data"][1]["name"] == "Old Workflow"

    def test_list_workflows_sort_by_updated_at(
        self, client: TestClient, mock_workflow_service: MockWorkflowServiceAdapter
    ) -> None:
        """
        GIVEN workflows exist
        WHEN GET request with sort_by=updated_at
        THEN response should be sorted by updated_at
        """
        mock_workflow_service._workflows["1"] = {
            "id": "1",
            "name": "Test 1",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-05T00:00:00Z",
        }
        mock_workflow_service._workflows["2"] = {
            "id": "2",
            "name": "Test 2",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "active",
            "created_at": "2025-01-02T00:00:00Z",
            "updated_at": "2025-01-03T00:00:00Z",
        }

        response = client.get("/api/v1/workflows?sort_by=updated_at&sort_order=asc")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        # Ascending by updated_at: Test 2 (Jan 3) before Test 1 (Jan 5)
        assert data["data"][0]["name"] == "Test 2"
        assert data["data"][1]["name"] == "Test 1"


# ============================================================================
# Filtering Tests
# ============================================================================


@pytest.mark.xdist_group(name="test_workflows_router_query")
class TestWorkflowsListFiltering:
    """Tests for filtering workflows via GET /api/v1/workflows."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_workflows_filter_by_status(
        self, client: TestClient, mock_workflow_service: MockWorkflowServiceAdapter
    ) -> None:
        """
        GIVEN workflows with different statuses exist
        WHEN GET request with status=published
        THEN only published workflows are returned
        """
        mock_workflow_service._workflows["1"] = {
            "id": "1",
            "name": "Draft Workflow",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "draft",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        mock_workflow_service._workflows["2"] = {
            "id": "2",
            "name": "Published Workflow",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "published",
            "created_at": "2025-01-02T00:00:00Z",
            "updated_at": "2025-01-02T00:00:00Z",
        }

        response = client.get("/api/v1/workflows?status=published")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Published Workflow"

    def test_list_workflows_filter_by_owner_id(
        self, client: TestClient, mock_workflow_service: MockWorkflowServiceAdapter
    ) -> None:
        """
        GIVEN workflows exist for different owners
        WHEN GET request with owner_id filter
        THEN only that owner's workflows are returned
        """
        owner_id = str(uuid4())
        other_owner_id = str(uuid4())

        mock_workflow_service._workflows["1"] = {
            "id": "1",
            "name": "My Workflow",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "active",
            "user_id": owner_id,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        mock_workflow_service._workflows["2"] = {
            "id": "2",
            "name": "Other Workflow",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "active",
            "user_id": other_owner_id,
            "created_at": "2025-01-02T00:00:00Z",
            "updated_at": "2025-01-02T00:00:00Z",
        }

        response = client.get(f"/api/v1/workflows?owner_id={owner_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "My Workflow"

    def test_list_workflows_multiple_filters(
        self, client: TestClient, mock_workflow_service: MockWorkflowServiceAdapter
    ) -> None:
        """
        GIVEN workflows exist
        WHEN GET request with multiple filters
        THEN only workflows matching all filters are returned
        """
        owner_id = str(uuid4())

        mock_workflow_service._workflows["1"] = {
            "id": "1",
            "name": "Draft Mine",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "draft",
            "user_id": owner_id,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        mock_workflow_service._workflows["2"] = {
            "id": "2",
            "name": "Published Mine",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "published",
            "user_id": owner_id,
            "created_at": "2025-01-02T00:00:00Z",
            "updated_at": "2025-01-02T00:00:00Z",
        }
        mock_workflow_service._workflows["3"] = {
            "id": "3",
            "name": "Draft Other",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "draft",
            "user_id": str(uuid4()),
            "created_at": "2025-01-03T00:00:00Z",
            "updated_at": "2025-01-03T00:00:00Z",
        }

        response = client.get(f"/api/v1/workflows?status=draft&owner_id={owner_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Draft Mine"


# ============================================================================
# Search Tests
# ============================================================================


@pytest.mark.xdist_group(name="test_workflows_router_query")
class TestWorkflowsListSearch:
    """Tests for searching workflows via GET /api/v1/workflows."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_workflows_search_by_name(
        self, client: TestClient, mock_workflow_service: MockWorkflowServiceAdapter
    ) -> None:
        """
        GIVEN workflows exist
        WHEN GET request with search parameter
        THEN only matching workflows are returned
        """
        mock_workflow_service._workflows["1"] = {
            "id": "1",
            "name": "Machine Learning Pipeline",
            "description": "An ML workflow",
            "nodes": [],
            "edges": [],
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        mock_workflow_service._workflows["2"] = {
            "id": "2",
            "name": "Data Processing",
            "description": "A data workflow",
            "nodes": [],
            "edges": [],
            "status": "active",
            "created_at": "2025-01-02T00:00:00Z",
            "updated_at": "2025-01-02T00:00:00Z",
        }

        response = client.get("/api/v1/workflows?search=Machine")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Machine Learning Pipeline"

    def test_list_workflows_search_case_insensitive(
        self, client: TestClient, mock_workflow_service: MockWorkflowServiceAdapter
    ) -> None:
        """
        GIVEN workflows exist
        WHEN GET request with lowercase search
        THEN should find workflows case-insensitively
        """
        mock_workflow_service._workflows["1"] = {
            "id": "1",
            "name": "Machine Learning Pipeline",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

        response = client.get("/api/v1/workflows?search=machine")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Machine Learning Pipeline"

    def test_list_workflows_search_with_pagination(
        self, client: TestClient, mock_workflow_service: MockWorkflowServiceAdapter
    ) -> None:
        """
        GIVEN many matching workflows exist
        WHEN GET request with search and pagination
        THEN should return paginated results
        """
        # Add 15 matching workflows
        for i in range(15):
            mock_workflow_service._workflows[str(i)] = {
                "id": str(i),
                "name": f"Test Workflow {i}",
                "description": "A test workflow",
                "nodes": [],
                "edges": [],
                "status": "active",
                "created_at": f"2025-01-{(i % 28) + 1:02d}T00:00:00Z",
                "updated_at": f"2025-01-{(i % 28) + 1:02d}T00:00:00Z",
            }

        response = client.get("/api/v1/workflows?search=test&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 10
        assert data["pagination"]["has_next"] is True

    def test_list_workflows_search_no_results(
        self, client: TestClient, mock_workflow_service: MockWorkflowServiceAdapter
    ) -> None:
        """
        GIVEN no matching workflows
        WHEN GET request with search
        THEN should return empty list
        """
        mock_workflow_service._workflows["1"] = {
            "id": "1",
            "name": "Real Workflow",
            "description": "A real workflow",
            "nodes": [],
            "edges": [],
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

        response = client.get("/api/v1/workflows?search=nonexistent_xyz_123")

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []


# ============================================================================
# Combined Query Tests
# ============================================================================


@pytest.mark.xdist_group(name="test_workflows_router_query")
class TestWorkflowsListCombined:
    """Tests for combining sorting, filtering, and search."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_workflows_search_with_sorting(
        self, client: TestClient, mock_workflow_service: MockWorkflowServiceAdapter
    ) -> None:
        """
        GIVEN workflows exist
        WHEN GET request with search and sorting
        THEN should return search results sorted correctly
        """
        mock_workflow_service._workflows["1"] = {
            "id": "1",
            "name": "Zebra Test",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        mock_workflow_service._workflows["2"] = {
            "id": "2",
            "name": "Alpha Test",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "active",
            "created_at": "2025-01-02T00:00:00Z",
            "updated_at": "2025-01-02T00:00:00Z",
        }
        mock_workflow_service._workflows["3"] = {
            "id": "3",
            "name": "Unrelated Workflow",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "active",
            "created_at": "2025-01-03T00:00:00Z",
            "updated_at": "2025-01-03T00:00:00Z",
        }

        response = client.get("/api/v1/workflows?search=test&sort_by=name&sort_order=asc")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        # Search results sorted by name ascending
        assert data["data"][0]["name"] == "Alpha Test"
        assert data["data"][1]["name"] == "Zebra Test"

    def test_list_workflows_filter_with_sorting(
        self, client: TestClient, mock_workflow_service: MockWorkflowServiceAdapter
    ) -> None:
        """
        GIVEN workflows exist
        WHEN GET request with filters and sorting
        THEN should return filtered results sorted correctly
        """
        mock_workflow_service._workflows["1"] = {
            "id": "1",
            "name": "Old Published",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "published",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        mock_workflow_service._workflows["2"] = {
            "id": "2",
            "name": "New Published",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "published",
            "created_at": "2025-01-10T00:00:00Z",
            "updated_at": "2025-01-10T00:00:00Z",
        }
        mock_workflow_service._workflows["3"] = {
            "id": "3",
            "name": "Draft Workflow",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "draft",
            "created_at": "2025-01-05T00:00:00Z",
            "updated_at": "2025-01-05T00:00:00Z",
        }

        response = client.get("/api/v1/workflows?status=published&sort_by=created_at&sort_order=desc")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        # Published only, sorted by created_at descending
        assert data["data"][0]["name"] == "New Published"
        assert data["data"][1]["name"] == "Old Published"

    def test_list_workflows_all_query_params(
        self, client: TestClient, mock_workflow_service: MockWorkflowServiceAdapter
    ) -> None:
        """
        GIVEN workflows exist
        WHEN GET request with all query parameters
        THEN should return correctly filtered, searched, and sorted results
        """
        owner_id = str(uuid4())
        other_owner_id = str(uuid4())

        # Create test data that exercises all filters
        mock_workflow_service._workflows["1"] = {
            "id": "1",
            "name": "Test Alpha",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "published",
            "user_id": owner_id,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        mock_workflow_service._workflows["2"] = {
            "id": "2",
            "name": "Test Zebra",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "published",
            "user_id": owner_id,
            "created_at": "2025-01-02T00:00:00Z",
            "updated_at": "2025-01-02T00:00:00Z",
        }
        # Should be excluded: wrong owner
        mock_workflow_service._workflows["3"] = {
            "id": "3",
            "name": "Test Other Owner",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "published",
            "user_id": other_owner_id,
            "created_at": "2025-01-03T00:00:00Z",
            "updated_at": "2025-01-03T00:00:00Z",
        }
        # Should be excluded: wrong status
        mock_workflow_service._workflows["4"] = {
            "id": "4",
            "name": "Test Draft",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "draft",
            "user_id": owner_id,
            "created_at": "2025-01-04T00:00:00Z",
            "updated_at": "2025-01-04T00:00:00Z",
        }
        # Should be excluded: doesn't match search
        mock_workflow_service._workflows["5"] = {
            "id": "5",
            "name": "No Match",
            "description": "",
            "nodes": [],
            "edges": [],
            "status": "published",
            "user_id": owner_id,
            "created_at": "2025-01-05T00:00:00Z",
            "updated_at": "2025-01-05T00:00:00Z",
        }

        response = client.get(
            f"/api/v1/workflows?search=test&owner_id={owner_id}&status=published&sort_by=name&sort_order=asc&limit=10"
        )

        assert response.status_code == 200
        data = response.json()
        # Only workflows 1 and 2 match all criteria
        assert len(data["data"]) == 2
        # Sorted by name ascending
        assert data["data"][0]["name"] == "Test Alpha"
        assert data["data"][1]["name"] == "Test Zebra"


@pytest.mark.xdist_group(name="test_workflows_router")
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
