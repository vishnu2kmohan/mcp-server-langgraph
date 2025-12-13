"""
Workflows Router Unit Tests

Tests for /api/v1/workflows endpoints per TDD methodology.
Tests written FIRST before implementation (RED phase).

The workflows endpoint provides CRUD operations for workflow management.
"""

import gc
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


@pytest.fixture
def test_app() -> FastAPI:
    """Create a test app with the workflows router."""
    from mcp_server_langgraph.api.v1.workflows import workflows_router

    app = FastAPI()
    app.include_router(workflows_router, prefix="/api/v1")
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)


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

    def test_list_workflows_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a request to /api/v1/workflows
        WHEN GET request is made
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.workflows.get_workflow_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_workflows.return_value = ([], None)
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/workflows")

            assert response.status_code == 200

    def test_list_workflows_returns_array(self, test_app: FastAPI) -> None:
        """
        GIVEN workflows exist
        WHEN GET request is made
        THEN response should contain array of workflows
        """
        with patch("mcp_server_langgraph.api.v1.workflows.get_workflow_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_workflows.return_value = (
                [{"id": "1", "name": "Test"}],
                None,
            )
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get("/api/v1/workflows")
            data = response.json()

            assert "data" in data
            assert isinstance(data["data"], list)

    def test_list_workflows_with_pagination(self, test_app: FastAPI) -> None:
        """
        GIVEN pagination parameters
        WHEN GET request is made with cursor and limit
        THEN response should include pagination metadata
        """
        with patch("mcp_server_langgraph.api.v1.workflows.get_workflow_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_workflows.return_value = (
                [{"id": "1", "name": "Test"}],
                "next_cursor_value",
            )
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
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

    def test_get_workflow_returns_200(self, test_app: FastAPI, sample_workflow: dict) -> None:
        """
        GIVEN a workflow exists
        WHEN GET request is made with workflow ID
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.workflows.get_workflow_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_workflow.return_value = sample_workflow
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/workflows/{sample_workflow['id']}")

            assert response.status_code == 200

    def test_get_workflow_returns_workflow_data(self, test_app: FastAPI, sample_workflow: dict) -> None:
        """
        GIVEN a workflow exists
        WHEN GET request is made
        THEN response should contain workflow data
        """
        with patch("mcp_server_langgraph.api.v1.workflows.get_workflow_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_workflow.return_value = sample_workflow
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.get(f"/api/v1/workflows/{sample_workflow['id']}")
            data = response.json()

            assert data["id"] == sample_workflow["id"]
            assert data["name"] == sample_workflow["name"]

    def test_get_workflow_not_found_returns_404(self, test_app: FastAPI) -> None:
        """
        GIVEN a workflow does not exist
        WHEN GET request is made
        THEN response should be 404 Not Found
        """
        with patch("mcp_server_langgraph.api.v1.workflows.get_workflow_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_workflow.return_value = None
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            workflow_id = str(uuid4())
            response = client.get(f"/api/v1/workflows/{workflow_id}")

            assert response.status_code == 404


@pytest.mark.xdist_group(name="test_workflows_router")
class TestWorkflowsCreateEndpoint:
    """Tests for POST /api/v1/workflows endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_workflow_returns_201(self, test_app: FastAPI, sample_workflow: dict) -> None:
        """
        GIVEN valid workflow data
        WHEN POST request is made
        THEN response should be 201 Created
        """
        with patch("mcp_server_langgraph.api.v1.workflows.get_workflow_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.create_workflow.return_value = sample_workflow
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
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

    def test_create_workflow_returns_created_workflow(self, test_app: FastAPI, sample_workflow: dict) -> None:
        """
        GIVEN valid workflow data
        WHEN POST request is made
        THEN response should contain created workflow with ID
        """
        with patch("mcp_server_langgraph.api.v1.workflows.get_workflow_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.create_workflow.return_value = sample_workflow
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
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

    def test_create_workflow_validates_required_fields(self, test_app: FastAPI) -> None:
        """
        GIVEN invalid workflow data (missing required fields)
        WHEN POST request is made
        THEN response should be 422 Unprocessable Entity
        """
        with patch("mcp_server_langgraph.api.v1.workflows.get_workflow_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)  # Not called due to validation failure
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
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

    def test_update_workflow_returns_200(self, test_app: FastAPI, sample_workflow: dict) -> None:
        """
        GIVEN a workflow exists
        WHEN PUT request is made with updated data
        THEN response should be 200 OK
        """
        with patch("mcp_server_langgraph.api.v1.workflows.get_workflow_service") as mock_get_service:
            mock_service = AsyncMock()
            updated_workflow = {**sample_workflow, "name": "Updated Name"}
            mock_service.update_workflow.return_value = updated_workflow
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.put(
                f"/api/v1/workflows/{sample_workflow['id']}",
                json={"name": "Updated Name"},
            )

            assert response.status_code == 200

    def test_update_workflow_not_found_returns_404(self, test_app: FastAPI) -> None:
        """
        GIVEN a workflow does not exist
        WHEN PUT request is made
        THEN response should be 404 Not Found
        """
        with patch("mcp_server_langgraph.api.v1.workflows.get_workflow_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.update_workflow.return_value = None
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
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

    def test_delete_workflow_returns_204(self, test_app: FastAPI, sample_workflow: dict) -> None:
        """
        GIVEN a workflow exists
        WHEN DELETE request is made
        THEN response should be 204 No Content
        """
        with patch("mcp_server_langgraph.api.v1.workflows.get_workflow_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.delete_workflow.return_value = True
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            response = client.delete(f"/api/v1/workflows/{sample_workflow['id']}")

            assert response.status_code == 204

    def test_delete_workflow_not_found_returns_404(self, test_app: FastAPI) -> None:
        """
        GIVEN a workflow does not exist
        WHEN DELETE request is made
        THEN response should be 404 Not Found
        """
        with patch("mcp_server_langgraph.api.v1.workflows.get_workflow_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.delete_workflow.return_value = False
            mock_get_service.return_value = mock_service

            client = TestClient(test_app)
            workflow_id = str(uuid4())
            response = client.delete(f"/api/v1/workflows/{workflow_id}")

            assert response.status_code == 404
