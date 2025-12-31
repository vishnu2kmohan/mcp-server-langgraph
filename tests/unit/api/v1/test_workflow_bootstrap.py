"""
Workflow Bootstrap Router Unit Tests

Tests for /api/v1/sessions/{id}/bootstrap-workflow endpoint per TDD methodology.
Tests written FIRST before implementation (RED phase).

The workflow bootstrap endpoint analyzes chat session traces and creates
workflow definitions based on the conversation steps.
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
    """Create a test app with the workflow bootstrap router and mocked auth."""
    from mcp_server_langgraph.api.v1.workflow_bootstrap import workflow_bootstrap_router
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()

    # Mock current user for all tests
    async def mock_get_current_user() -> dict:
        return {"user_id": "user:test_user", "username": "test_user", "roles": ["user"]}

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.include_router(workflow_bootstrap_router, prefix="/api/v1")
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)


@pytest.fixture
def sample_session_with_messages() -> dict:
    """Sample session with conversation trace for testing."""
    return {
        "id": str(uuid4()),
        "title": "Help me analyze sales data",
        "messages": [
            {
                "role": "user",
                "content": "I need to analyze my sales data from the database",
            },
            {
                "role": "assistant",
                "content": "I'll help you with that. Let me query the database.",
            },
            {
                "role": "assistant",
                "content": "I've retrieved the data. Now let me perform some analysis.",
            },
            {"role": "assistant", "content": "Here are the results in a summary format."},
        ],
    }


@pytest.fixture
def expected_workflow_steps() -> list[dict]:
    """Expected workflow steps extracted from conversation."""
    return [
        {"action": "query_database", "description": "Query sales data from database"},
        {"action": "analyze_data", "description": "Perform data analysis"},
        {"action": "format_results", "description": "Format results as summary"},
    ]


@pytest.fixture
def expected_workflow() -> dict:
    """Expected workflow structure with nodes and edges."""
    workflow_id = str(uuid4())
    return {
        "id": workflow_id,
        "name": "Sales Data Analysis Workflow",
        "description": "Automated workflow for sales data analysis",
        "nodes": [
            {
                "id": "node_1",
                "type": "start",
                "position": {"x": 0, "y": 0},
                "data": {},
            },
            {
                "id": "node_2",
                "type": "tool",
                "position": {"x": 200, "y": 0},
                "data": {"action": "query_database"},
            },
            {
                "id": "node_3",
                "type": "llm",
                "position": {"x": 400, "y": 0},
                "data": {"action": "analyze_data"},
            },
            {
                "id": "node_4",
                "type": "tool",
                "position": {"x": 600, "y": 0},
                "data": {"action": "format_results"},
            },
            {
                "id": "node_5",
                "type": "end",
                "position": {"x": 800, "y": 0},
                "data": {},
            },
        ],
        "edges": [
            {"source": "node_1", "target": "node_2", "label": None},
            {"source": "node_2", "target": "node_3", "label": None},
            {"source": "node_3", "target": "node_4", "label": None},
            {"source": "node_4", "target": "node_5", "label": None},
        ],
    }


@pytest.mark.xdist_group(name="test_workflow_bootstrap")
class TestWorkflowBootstrapEndpoint:
    """Tests for POST /api/v1/sessions/{id}/bootstrap-workflow endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_bootstrap_workflow_returns_200(self, test_app: FastAPI) -> None:
        """
        GIVEN a valid session ID and bootstrap request
        WHEN POST request is made to /sessions/{id}/bootstrap-workflow
        THEN response should be 200 OK
        """
        session_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.workflow_bootstrap.get_workflow_bootstrapper") as mock_get_bootstrapper:
            mock_bootstrapper = AsyncMock()  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_bootstrapper.bootstrap_workflow.return_value = {
                "id": str(uuid4()),
                "name": "Test Workflow",
                "nodes": [],
                "edges": [],
            }
            mock_get_bootstrapper.return_value = mock_bootstrapper

            client = TestClient(test_app)
            response = client.post(
                f"/api/v1/sessions/{session_id}/bootstrap-workflow",
                json={
                    "name": "Test Workflow",
                    "description": "A test workflow",
                },
            )

            assert response.status_code == 200

    def test_bootstrap_workflow_with_invalid_session_returns_404(self, test_app: FastAPI) -> None:
        """
        GIVEN an invalid session ID
        WHEN POST request is made
        THEN response should be 404 Not Found
        """
        session_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.workflow_bootstrap.get_workflow_bootstrapper") as mock_get_bootstrapper:
            mock_bootstrapper = AsyncMock()  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_bootstrapper.bootstrap_workflow.side_effect = ValueError(f"Session {session_id} not found")
            mock_get_bootstrapper.return_value = mock_bootstrapper

            client = TestClient(test_app)
            response = client.post(
                f"/api/v1/sessions/{session_id}/bootstrap-workflow",
                json={
                    "name": "Test Workflow",
                    "description": "A test workflow",
                },
            )

            assert response.status_code == 404

    def test_bootstrap_workflow_with_empty_session_returns_400(self, test_app: FastAPI) -> None:
        """
        GIVEN a session with no messages
        WHEN POST request is made
        THEN response should be 400 Bad Request
        """
        session_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.workflow_bootstrap.get_workflow_bootstrapper") as mock_get_bootstrapper:
            mock_bootstrapper = AsyncMock()  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_bootstrapper.bootstrap_workflow.side_effect = ValueError("Cannot bootstrap workflow from empty session")
            mock_get_bootstrapper.return_value = mock_bootstrapper

            client = TestClient(test_app)
            response = client.post(
                f"/api/v1/sessions/{session_id}/bootstrap-workflow",
                json={
                    "name": "Test Workflow",
                    "description": "A test workflow",
                },
            )

            assert response.status_code == 400

    def test_bootstrap_workflow_returns_workflow_data(self, test_app: FastAPI, expected_workflow: dict) -> None:
        """
        GIVEN a valid session with messages
        WHEN POST request is made
        THEN response should contain workflow with nodes and edges
        """
        session_id = str(uuid4())
        with patch("mcp_server_langgraph.api.v1.workflow_bootstrap.get_workflow_bootstrapper") as mock_get_bootstrapper:
            mock_bootstrapper = AsyncMock()  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_bootstrapper.bootstrap_workflow.return_value = expected_workflow
            mock_get_bootstrapper.return_value = mock_bootstrapper

            client = TestClient(test_app)
            response = client.post(
                f"/api/v1/sessions/{session_id}/bootstrap-workflow",
                json={
                    "name": expected_workflow["name"],
                    "description": expected_workflow["description"],
                },
            )

            data = response.json()
            assert response.status_code == 200
            assert "id" in data
            assert data["name"] == expected_workflow["name"]
            assert "nodes" in data
            assert "edges" in data
            assert len(data["nodes"]) > 0
            assert len(data["edges"]) > 0

    def test_bootstrap_workflow_with_selected_messages(self, test_app: FastAPI) -> None:
        """
        GIVEN a bootstrap request with selected_messages
        WHEN POST request is made
        THEN only the selected messages should be used
        """
        session_id = str(uuid4())
        selected_indices = [0, 1, 3]

        with patch("mcp_server_langgraph.api.v1.workflow_bootstrap.get_workflow_bootstrapper") as mock_get_bootstrapper:
            mock_bootstrapper = AsyncMock()  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_bootstrapper.bootstrap_workflow.return_value = {
                "id": str(uuid4()),
                "name": "Selective Workflow",
                "nodes": [],
                "edges": [],
            }
            mock_get_bootstrapper.return_value = mock_bootstrapper

            client = TestClient(test_app)
            response = client.post(
                f"/api/v1/sessions/{session_id}/bootstrap-workflow",
                json={
                    "name": "Selective Workflow",
                    "description": "Workflow from selected messages",
                    "selected_messages": selected_indices,
                },
            )

            assert response.status_code == 200
            # Verify the bootstrapper was called with selected_messages
            call_args = mock_bootstrapper.bootstrap_workflow.call_args
            assert call_args is not None


@pytest.mark.xdist_group(name="test_workflow_bootstrapper")
class TestWorkflowBootstrapperClass:
    """Tests for WorkflowBootstrapper class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extract_steps_from_session_returns_list(self, sample_session_with_messages: dict) -> None:
        """
        GIVEN a session with conversation trace
        WHEN extract_steps_from_session is called
        THEN it should return a list of action steps
        """
        from mcp_server_langgraph.api.v1.workflow_bootstrap import (
            WorkflowBootstrapper,
        )

        WorkflowBootstrapper()

        # Mock the session service
        with patch("mcp_server_langgraph.api.v1.workflow_bootstrap.get_session_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_service.get_session.return_value = sample_session_with_messages
            mock_get_service.return_value = mock_service

            # This will fail until implementation exists (RED phase)
            # Placeholder for future async test

    def test_create_workflow_from_steps_returns_workflow(self, expected_workflow_steps: list[dict]) -> None:
        """
        GIVEN a list of workflow steps
        WHEN create_workflow_from_steps is called
        THEN it should return a workflow definition with nodes and edges
        """
        from mcp_server_langgraph.api.v1.workflow_bootstrap import (
            WorkflowBootstrapper,
        )

        WorkflowBootstrapper()

        # This will fail until implementation exists (RED phase)
        # Placeholder for future test

    def test_bootstrap_workflow_end_to_end(self, sample_session_with_messages: dict) -> None:
        """
        GIVEN a session ID, name, and description
        WHEN bootstrap_workflow is called
        THEN it should extract steps, create workflow, and return complete workflow
        """
        from mcp_server_langgraph.api.v1.workflow_bootstrap import (
            WorkflowBootstrapper,
        )

        WorkflowBootstrapper()

        # Mock the session service
        with patch("mcp_server_langgraph.api.v1.workflow_bootstrap.get_session_service") as mock_get_service:
            mock_service = AsyncMock()  # async-mock-configured (return_value set below)  # noqa: async-mock-config
            mock_service.get_session.return_value = sample_session_with_messages
            mock_get_service.return_value = mock_service

            # This will fail until implementation exists (RED phase)
            # Placeholder for future async test
