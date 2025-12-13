"""
Studio API Routes Tests

TDD tests for Studio API endpoints including workflows, suggestions, and templates.
Following GIVEN/WHEN/THEN pattern.
"""

import gc
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_current_user() -> dict[str, Any]:
    """Mock authenticated user."""
    return {
        "user_id": "alice",
        "keycloak_id": "alice-uuid-123",
        "username": "alice",
        "email": "alice@example.com",
        "roles": ["user", "developer"],
    }


@pytest.fixture
def mock_workflow_data() -> dict[str, Any]:
    """Mock workflow request data."""
    return {
        "name": "Test Workflow",
        "description": "A test workflow",
        "nodes": [
            {"id": "input", "type": "input", "data": {"label": "Input"}},
            {"id": "llm", "type": "llm", "data": {"model": "gpt-4"}},
            {"id": "output", "type": "output", "data": {"label": "Output"}},
        ],
        "edges": [
            {"source": "input", "target": "llm"},
            {"source": "llm", "target": "output"},
        ],
    }


@pytest.fixture
def client(mock_current_user: dict[str, Any]) -> TestClient:
    """Create test client with mocked authentication.

    Creates a fresh FastAPI app with studio router and auth override for each test.
    This ensures proper isolation in pytest-xdist parallel execution.
    """
    from mcp_server_langgraph.api.studio import WorkflowService, router as studio_router
    from mcp_server_langgraph.auth.middleware import get_current_user

    # Clear in-memory storage before each test
    WorkflowService._workflows.clear()
    WorkflowService._counter = 0

    # Create fresh app for this test
    app = FastAPI()
    app.include_router(studio_router)

    # Override authentication dependency
    async def mock_get_current_user() -> dict[str, Any]:
        return mock_current_user

    app.dependency_overrides[get_current_user] = mock_get_current_user

    # Use context manager for proper cleanup
    with TestClient(app) as test_client:
        yield test_client

    # Clean up dependency overrides
    app.dependency_overrides.clear()


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_studio_routes_workflows")
class TestWorkflowCRUD:
    """Tests for workflow CRUD endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_workflow_returns_201(self, client: TestClient, mock_workflow_data: dict[str, Any]) -> None:
        """GIVEN valid workflow data
        WHEN POST /api/v1/studio/workflows
        THEN should return 201 Created with workflow data
        """
        response = client.post("/api/v1/studio/workflows", json=mock_workflow_data)

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "workflow-1"
        assert data["name"] == "Test Workflow"
        assert data["owner_id"] == "alice-uuid-123"

    def test_get_workflow_returns_workflow(self, client: TestClient, mock_workflow_data: dict[str, Any]) -> None:
        """GIVEN existing workflow ID
        WHEN GET /api/v1/studio/workflows/{id}
        THEN should return workflow data
        """
        # First create a workflow
        create_response = client.post("/api/v1/studio/workflows", json=mock_workflow_data)
        workflow_id = create_response.json()["id"]

        response = client.get(f"/api/v1/studio/workflows/{workflow_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == workflow_id
        assert data["name"] == "Test Workflow"

    def test_get_workflow_returns_404_when_not_found(self, client: TestClient) -> None:
        """GIVEN non-existent workflow ID
        WHEN GET /api/v1/studio/workflows/{id}
        THEN should return 404 Not Found
        """
        response = client.get("/api/v1/studio/workflows/nonexistent")

        assert response.status_code == 404

    def test_update_workflow_returns_updated(self, client: TestClient, mock_workflow_data: dict[str, Any]) -> None:
        """GIVEN existing workflow ID and update data
        WHEN PUT /api/v1/studio/workflows/{id}
        THEN should return updated workflow
        """
        # First create a workflow
        create_response = client.post("/api/v1/studio/workflows", json=mock_workflow_data)
        workflow_id = create_response.json()["id"]

        update_data = {"name": "Updated Workflow", "description": "Updated description"}
        response = client.put(f"/api/v1/studio/workflows/{workflow_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Workflow"
        assert data["description"] == "Updated description"

    def test_delete_workflow_returns_204(self, client: TestClient, mock_workflow_data: dict[str, Any]) -> None:
        """GIVEN existing workflow ID
        WHEN DELETE /api/v1/studio/workflows/{id}
        THEN should return 204 No Content
        """
        # First create a workflow
        create_response = client.post("/api/v1/studio/workflows", json=mock_workflow_data)
        workflow_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/studio/workflows/{workflow_id}")

        assert response.status_code == 204

        # Verify it's deleted
        get_response = client.get(f"/api/v1/studio/workflows/{workflow_id}")
        assert get_response.status_code == 404

    def test_list_workflows_returns_list(self, client: TestClient, mock_workflow_data: dict[str, Any]) -> None:
        """GIVEN authenticated user with workflows
        WHEN GET /api/v1/studio/workflows
        THEN should return list of workflows
        """
        # Create a workflow first
        client.post("/api/v1/studio/workflows", json=mock_workflow_data)

        response = client.get("/api/v1/studio/workflows")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_studio_routes_suggestions")
class TestAISuggestions:
    """Tests for AI suggestion endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_suggestions_returns_suggestions(self, client: TestClient, mock_workflow_data: dict[str, Any]) -> None:
        """GIVEN workflow data
        WHEN POST /api/v1/studio/suggestions
        THEN should return AI suggestions
        """
        request_data = {
            "workflow": {
                "nodes": mock_workflow_data["nodes"],
                "edges": mock_workflow_data["edges"],
            },
            "max_suggestions": 5,
        }

        response = client.post("/api/v1/studio/suggestions", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        # The AI should return suggestions for a workflow with nodes
        assert isinstance(data["suggestions"], list)

    def test_get_suggestions_validates_workflow(self, client: TestClient) -> None:
        """GIVEN invalid workflow data
        WHEN POST /api/v1/studio/suggestions
        THEN should return 422 Unprocessable Entity
        """
        request_data = {"workflow": {}, "max_suggestions": -1}  # Invalid max_suggestions

        response = client.post("/api/v1/studio/suggestions", json=request_data)

        assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_studio_routes_templates")
class TestTemplateEndpoints:
    """Tests for template endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_templates_returns_all_templates(self, client: TestClient) -> None:
        """GIVEN request for templates
        WHEN GET /api/v1/studio/templates
        THEN should return list of available templates
        """
        response = client.get("/api/v1/studio/templates")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 5  # At least 5 built-in templates

    def test_recommend_templates_returns_matches(self, client: TestClient) -> None:
        """GIVEN description of desired workflow
        WHEN POST /api/v1/studio/templates/recommend
        THEN should return matching templates with similarity scores
        """
        request_data = {"description": "Build a chatbot with RAG", "top_k": 3}

        response = client.post("/api/v1/studio/templates/recommend", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert len(data["recommendations"]) <= 3
        # RAG chatbot should be in top results
        ids = [r["id"] for r in data["recommendations"]]
        assert "chatbot-rag" in ids or "chatbot-basic" in ids

    def test_recommend_templates_validates_top_k(self, client: TestClient) -> None:
        """GIVEN invalid top_k value
        WHEN POST /api/v1/studio/templates/recommend
        THEN should return 422 Unprocessable Entity
        """
        request_data = {"description": "Build something", "top_k": 0}  # Invalid

        response = client.post("/api/v1/studio/templates/recommend", json=request_data)

        assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_studio_routes_auth")
class TestAuthorizationEnforcement:
    """Tests for authorization enforcement on studio routes."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_unauthenticated_request_returns_error(self) -> None:
        """GIVEN no authentication
        WHEN accessing protected endpoint
        THEN should return error status
        """
        from mcp_server_langgraph.api.studio import router as studio_router

        app = FastAPI()
        app.include_router(studio_router)
        # No dependency override - requires real auth

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/studio/workflows")

        # Should fail authentication (401, 403, or 500 if deps not configured)
        assert response.status_code in [401, 403, 500]

    def test_user_cannot_access_other_users_workflows(
        self,
        mock_current_user: dict[str, Any],
        mock_workflow_data: dict[str, Any],
    ) -> None:
        """GIVEN workflow owned by different user
        WHEN requesting workflow
        THEN should return 403 Forbidden or 404 Not Found
        """
        from mcp_server_langgraph.api.studio import WorkflowService, router as studio_router

        # Clear storage
        WorkflowService._workflows.clear()
        WorkflowService._counter = 0

        app = FastAPI()
        app.include_router(studio_router)

        # Create workflow as bob
        bob_user = {**mock_current_user, "keycloak_id": "bob-uuid-456", "user_id": "bob"}

        from mcp_server_langgraph.auth.middleware import get_current_user

        app.dependency_overrides[get_current_user] = lambda: bob_user

        client_as_bob = TestClient(app)
        create_response = client_as_bob.post("/api/v1/studio/workflows", json=mock_workflow_data)
        workflow_id = create_response.json()["id"]

        # Now try to access as alice
        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        client_as_alice = TestClient(app)

        response = client_as_alice.get(f"/api/v1/studio/workflows/{workflow_id}")

        # Should return 403 (access denied)
        assert response.status_code == 403
