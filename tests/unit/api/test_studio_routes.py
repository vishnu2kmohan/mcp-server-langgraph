"""
Studio API Routes Tests

TDD tests for Studio API endpoints including workflows, suggestions, and templates.
Following GIVEN/WHEN/THEN pattern.
"""

import gc
from typing import Any

import pytest
from fastapi import FastAPI, Request
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
def mock_workflow_service():
    """Create a mock workflow service that simulates in-memory storage."""
    from datetime import UTC, datetime
    from unittest.mock import AsyncMock, MagicMock

    # In-memory storage for testing
    _workflows: dict[str, dict[str, Any]] = {}
    _counter = 0

    async def mock_create_workflow(workflow_data: dict[str, Any]) -> dict[str, Any]:
        nonlocal _counter
        _counter += 1
        workflow_id = f"workflow-{_counter}"
        now = datetime.now(UTC).isoformat()
        workflow = {
            "id": workflow_id,
            "name": workflow_data["name"],
            "description": workflow_data.get("description", ""),
            "nodes": workflow_data.get("nodes", []),
            "edges": workflow_data.get("edges", []),
            "user_id": workflow_data.get("user_id"),
            "created_at": now,
            "updated_at": now,
            "status": "active",
        }
        _workflows[workflow_id] = workflow
        return workflow

    async def mock_get_workflow(workflow_id: str) -> dict[str, Any] | None:
        return _workflows.get(workflow_id)

    async def mock_update_workflow(workflow_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        if workflow_id not in _workflows:
            return None
        workflow = _workflows[workflow_id]
        workflow.update(updates)
        workflow["updated_at"] = datetime.now(UTC).isoformat()
        return workflow

    async def mock_delete_workflow(workflow_id: str) -> bool:
        if workflow_id not in _workflows:
            return False
        del _workflows[workflow_id]
        return True

    async def mock_list_workflows(owner_id: str) -> tuple[list[dict[str, Any]], str | None]:
        user_workflows = [w for w in _workflows.values() if w.get("user_id") == owner_id]
        return user_workflows, None

    # Create mock service
    service = MagicMock()
    service.create_workflow = AsyncMock(side_effect=mock_create_workflow)
    service.get_workflow = AsyncMock(side_effect=mock_get_workflow)
    service.update_workflow = AsyncMock(side_effect=mock_update_workflow)
    service.delete_workflow = AsyncMock(side_effect=mock_delete_workflow)
    service.list_workflows = AsyncMock(side_effect=mock_list_workflows)

    return service


@pytest.fixture
def client(mock_current_user: dict[str, Any], mock_workflow_service: Any) -> TestClient:
    """Create test client with mocked authentication and workflow service.

    Creates a fresh FastAPI app with studio router and auth middleware for each test.
    This ensures proper isolation in pytest-xdist parallel execution.

    Uses HTTP middleware to set request.state.user, which get_current_user
    checks before attempting token validation. This approach is more reliable
    than dependency_overrides in xdist workers.
    """
    from mcp_server_langgraph.api.studio import router as studio_router
    from mcp_server_langgraph.api.v1.workflows import get_workflow_service

    # Create fresh app for this test
    app = FastAPI()

    # Override workflow service dependency
    app.dependency_overrides[get_workflow_service] = lambda: mock_workflow_service

    # Add middleware to inject test user into request.state
    # This middleware runs BEFORE route handlers, and get_current_user
    # checks request.state.user first (auth/middleware.py:852-854)
    @app.middleware("http")
    async def inject_test_user(request: Request, call_next):  # type: ignore[no-untyped-def]
        """Inject test user into request state for authentication bypass."""
        request.state.user = mock_current_user
        response = await call_next(request)
        return response

    # Include router AFTER middleware
    app.include_router(studio_router)

    # Use context manager for proper cleanup
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_studio_routes")
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


# NOTE: AI suggestions tests have been moved to tests/api/test_ai_node_config_api.py
# The endpoint /api/v1/studio/suggestions was consolidated into /api/v1/ai/suggestions
# as part of the unified AI API. See TestAISuggestions class in that file for
# comprehensive testing of the suggestions endpoint (40+ tests).


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_studio_routes")
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
@pytest.mark.xdist_group(name="test_studio_routes")
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
        from datetime import UTC, datetime
        from unittest.mock import AsyncMock, MagicMock

        from mcp_server_langgraph.api.studio import router as studio_router
        from mcp_server_langgraph.api.v1.workflows import get_workflow_service

        # Shared in-memory storage for both apps
        _workflows: dict[str, dict[str, Any]] = {}
        _counter = [0]  # Use list to allow nonlocal modification

        async def mock_create_workflow(workflow_data: dict[str, Any]) -> dict[str, Any]:
            _counter[0] += 1
            workflow_id = f"workflow-{_counter[0]}"
            now = datetime.now(UTC).isoformat()
            workflow = {
                "id": workflow_id,
                "name": workflow_data["name"],
                "description": workflow_data.get("description", ""),
                "nodes": workflow_data.get("nodes", []),
                "edges": workflow_data.get("edges", []),
                "user_id": workflow_data.get("user_id"),
                "created_at": now,
                "updated_at": now,
                "status": "active",
            }
            _workflows[workflow_id] = workflow
            return workflow

        async def mock_get_workflow(workflow_id: str) -> dict[str, Any] | None:
            return _workflows.get(workflow_id)

        # Create shared mock service
        shared_service = MagicMock()
        shared_service.create_workflow = AsyncMock(side_effect=mock_create_workflow)
        shared_service.get_workflow = AsyncMock(side_effect=mock_get_workflow)

        # Bob's user info
        bob_user = {**mock_current_user, "keycloak_id": "bob-uuid-456", "user_id": "bob"}

        # Create app for bob to create the workflow
        app_bob = FastAPI()
        app_bob.dependency_overrides[get_workflow_service] = lambda: shared_service

        @app_bob.middleware("http")
        async def inject_bob_user(request: Request, call_next):  # type: ignore[no-untyped-def]
            request.state.user = bob_user
            return await call_next(request)

        app_bob.include_router(studio_router)

        with TestClient(app_bob) as client_as_bob:
            create_response = client_as_bob.post("/api/v1/studio/workflows", json=mock_workflow_data)
            workflow_id = create_response.json()["id"]

        # Create separate app for alice
        app_alice = FastAPI()
        app_alice.dependency_overrides[get_workflow_service] = lambda: shared_service

        @app_alice.middleware("http")
        async def inject_alice_user(request: Request, call_next):  # type: ignore[no-untyped-def]
            request.state.user = mock_current_user
            return await call_next(request)

        app_alice.include_router(studio_router)

        with TestClient(app_alice) as client_as_alice:
            response = client_as_alice.get(f"/api/v1/studio/workflows/{workflow_id}")

        # Should return 403 (access denied) - the studio.py get_workflow checks owner
        assert response.status_code == 403
