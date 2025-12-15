"""
Tests for MCP REST Router.

TDD: These tests define the expected behavior of the MCP router,
which exposes MCP 2025-11-25 protocol features via REST endpoints.

Endpoints tested:
- GET  /api/v1/mcp/resources              - List available resources
- GET  /api/v1/mcp/resources/{uri}        - Read a resource
- POST /api/v1/mcp/sampling               - Request LLM completion
- POST /api/v1/mcp/elicitation            - Request user input (form)
- POST /api/v1/mcp/elicitation/url        - Request user URL action
- GET  /api/v1/mcp/tasks                  - List active tasks
- GET  /api/v1/mcp/tasks/{id}             - Get task status
- POST /api/v1/mcp/tasks/{id}/cancel      - Cancel task
"""

from __future__ import annotations

import gc
from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


@pytest.fixture
def app_with_mcp_router() -> FastAPI:
    """Create a FastAPI app with the MCP router mounted."""
    from fastapi import FastAPI

    from mcp_server_langgraph.api.v1.mcp import mcp_router

    app = FastAPI()
    app.include_router(mcp_router, prefix="/api/v1/mcp")
    return app


@pytest.fixture
def client(app_with_mcp_router: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app_with_mcp_router)


@pytest.mark.xdist_group(name="mcp_router")
class TestMCPRouterResources:
    """Test suite for MCP router resource endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_resources_returns_resources(self, client: TestClient) -> None:
        """GIVEN an MCP router with configured bridge
        WHEN GET /resources is called
        THEN it returns a list of resources
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPResource

        mock_resources = [
            MCPResource(
                uri="file:///test.txt",
                name="test.txt",
                title="Test File",
                mime_type="text/plain",
            ),
            MCPResource(
                uri="file:///data.json",
                name="data.json",
                mime_type="application/json",
            ),
        ]

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.list_resources = AsyncMock(return_value=mock_resources)
            mock_get.return_value = mock_service

            response = client.get("/api/v1/mcp/resources")

        assert response.status_code == 200
        data = response.json()
        assert len(data["resources"]) == 2
        assert data["resources"][0]["uri"] == "file:///test.txt"
        assert data["resources"][0]["name"] == "test.txt"

    def test_list_resources_returns_empty_when_not_configured(self, client: TestClient) -> None:
        """GIVEN no MCP bridge configured
        WHEN GET /resources is called
        THEN it returns empty list with warning
        """
        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.list_resources = AsyncMock(return_value=[])
            mock_get.return_value = mock_service

            response = client.get("/api/v1/mcp/resources")

        assert response.status_code == 200
        assert response.json()["resources"] == []

    def test_read_resource_returns_content(self, client: TestClient) -> None:
        """GIVEN an MCP router
        WHEN GET /resources/{uri} is called
        THEN it returns the resource content
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPResourceContent

        mock_content = [
            MCPResourceContent(
                uri="file:///test.txt",
                mime_type="text/plain",
                text="Hello, World!",
            )
        ]

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.read_resource = AsyncMock(return_value=mock_content)
            mock_get.return_value = mock_service

            # URI is passed as query param (encoded)
            response = client.get(
                "/api/v1/mcp/resources/content",
                params={"uri": "file:///test.txt"},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["contents"]) == 1
        assert data["contents"][0]["text"] == "Hello, World!"

    def test_read_resource_returns_404_for_not_found(self, client: TestClient) -> None:
        """GIVEN a non-existent resource
        WHEN GET /resources/{uri} is called
        THEN it returns 404
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPResourceNotFoundError

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.read_resource = AsyncMock(
                side_effect=MCPResourceNotFoundError("Not found", uri="file:///missing.txt")
            )
            mock_get.return_value = mock_service

            response = client.get(
                "/api/v1/mcp/resources/content",
                params={"uri": "file:///missing.txt"},
            )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.xdist_group(name="mcp_router")
class TestMCPRouterSampling:
    """Test suite for MCP router sampling endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_sampling_creates_message(self, client: TestClient) -> None:
        """GIVEN an MCP router
        WHEN POST /sampling is called
        THEN it creates a sampling message
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import SamplingResponse

        mock_response = SamplingResponse(
            role="assistant",
            content={"type": "text", "text": "Hello from LLM!"},
            model="claude-3-sonnet",
            stop_reason="end_turn",
        )

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.request_sampling = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_service

            response = client.post(
                "/api/v1/mcp/sampling",
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 100,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "assistant"
        assert data["model"] == "claude-3-sonnet"

    def test_sampling_with_model_preferences(self, client: TestClient) -> None:
        """GIVEN sampling request with model preferences
        WHEN POST /sampling is called
        THEN it passes preferences to the service
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import SamplingResponse

        mock_response = SamplingResponse(
            role="assistant",
            content={"type": "text", "text": "Response"},
            model="gpt-4",
        )

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.request_sampling = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_service

            response = client.post(
                "/api/v1/mcp/sampling",
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 100,
                    "model_hints": ["gpt-4", "claude-3-sonnet"],
                    "intelligence_priority": 0.9,
                    "speed_priority": 0.1,
                },
            )

        assert response.status_code == 200
        mock_service.request_sampling.assert_called_once()
        call_kwargs = mock_service.request_sampling.call_args.kwargs
        assert call_kwargs["model_hints"] == ["gpt-4", "claude-3-sonnet"]
        assert call_kwargs["intelligence_priority"] == 0.9


@pytest.mark.xdist_group(name="mcp_router")
class TestMCPRouterElicitation:
    """Test suite for MCP router elicitation endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_elicitation_form_returns_response(self, client: TestClient) -> None:
        """GIVEN an MCP router
        WHEN POST /elicitation is called with form mode
        THEN it returns the elicitation response
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import (
            ElicitationResponse,
            ElicitationAction,
        )

        mock_response = ElicitationResponse(
            action=ElicitationAction.ACCEPT,
            content={"username": "alice", "email": "alice@example.com"},
        )

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.request_user_input = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_service

            response = client.post(
                "/api/v1/mcp/elicitation",
                json={
                    "message": "Please provide your details",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "username": {"type": "string"},
                            "email": {"type": "string"},
                        },
                    },
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "accept"
        assert data["content"]["username"] == "alice"

    def test_elicitation_url_returns_response(self, client: TestClient) -> None:
        """GIVEN an MCP router
        WHEN POST /elicitation/url is called
        THEN it returns the URL elicitation response
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import (
            ElicitationResponse,
            ElicitationAction,
        )

        mock_response = ElicitationResponse(
            action=ElicitationAction.ACCEPT,
            content=None,
        )

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.request_user_url_action = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_service

            response = client.post(
                "/api/v1/mcp/elicitation/url",
                json={
                    "message": "Please authenticate",
                    "url": "https://oauth.example.com/authorize",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "accept"


@pytest.mark.xdist_group(name="mcp_router")
class TestMCPRouterTasks:
    """Test suite for MCP router task endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_tasks_returns_tasks(self, client: TestClient) -> None:
        """GIVEN an MCP router
        WHEN GET /tasks is called
        THEN it returns a list of tasks
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPTask, TaskStatus

        mock_tasks = [
            MCPTask(
                task_id="task-1",
                status=TaskStatus.WORKING,
                created_at=datetime.now(),
                last_updated_at=datetime.now(),
                status_message="Processing...",
            ),
            MCPTask(
                task_id="task-2",
                status=TaskStatus.COMPLETED,
                created_at=datetime.now(),
                last_updated_at=datetime.now(),
            ),
        ]

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.list_tasks = AsyncMock(return_value=mock_tasks)
            mock_get.return_value = mock_service

            response = client.get("/api/v1/mcp/tasks")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 2
        assert data["tasks"][0]["task_id"] == "task-1"
        assert data["tasks"][0]["status"] == "working"

    def test_get_task_returns_task_status(self, client: TestClient) -> None:
        """GIVEN an MCP router
        WHEN GET /tasks/{id} is called
        THEN it returns the task status
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPTask, TaskStatus

        mock_task = MCPTask(
            task_id="task-123",
            status=TaskStatus.WORKING,
            created_at=datetime.now(),
            last_updated_at=datetime.now(),
            status_message="Step 2 of 5",
            poll_interval=1000,
        )

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.get_task = AsyncMock(return_value=mock_task)
            mock_get.return_value = mock_service

            response = client.get("/api/v1/mcp/tasks/task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task-123"
        assert data["status"] == "working"
        assert data["status_message"] == "Step 2 of 5"

    def test_get_task_returns_404_for_not_found(self, client: TestClient) -> None:
        """GIVEN a non-existent task
        WHEN GET /tasks/{id} is called
        THEN it returns 404
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPTaskNotFoundError

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.get_task = AsyncMock(side_effect=MCPTaskNotFoundError("Task not found", task_id="task-999"))
            mock_get.return_value = mock_service

            response = client.get("/api/v1/mcp/tasks/task-999")

        assert response.status_code == 404

    def test_cancel_task_returns_cancelled_status(self, client: TestClient) -> None:
        """GIVEN an MCP router
        WHEN POST /tasks/{id}/cancel is called
        THEN it returns the cancelled task
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPTask, TaskStatus

        mock_task = MCPTask(
            task_id="task-123",
            status=TaskStatus.CANCELLED,
            created_at=datetime.now(),
            last_updated_at=datetime.now(),
        )

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.cancel_task = AsyncMock(return_value=mock_task)
            mock_get.return_value = mock_service

            response = client.post("/api/v1/mcp/tasks/task-123/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"


@pytest.mark.xdist_group(name="mcp_router")
class TestMCPRouterErrorHandling:
    """Test suite for MCP router error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_permission_error_returns_403(self, client: TestClient) -> None:
        """GIVEN a permission denied error
        WHEN any endpoint is called
        THEN it returns 403
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPPermissionError

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.list_resources = AsyncMock(side_effect=MCPPermissionError("Access denied"))
            mock_get.return_value = mock_service

            response = client.get("/api/v1/mcp/resources")

        assert response.status_code == 403
        assert "denied" in response.json()["detail"].lower()

    def test_connection_error_returns_503(self, client: TestClient) -> None:
        """GIVEN a connection error
        WHEN any endpoint is called
        THEN it returns 503
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPConnectionError

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.list_resources = AsyncMock(side_effect=MCPConnectionError("Connection refused"))
            mock_get.return_value = mock_service

            response = client.get("/api/v1/mcp/resources")

        assert response.status_code == 503
        assert "connection" in response.json()["detail"].lower()

    def test_elicitation_required_returns_428(self, client: TestClient) -> None:
        """GIVEN an elicitation required error
        WHEN an endpoint is called
        THEN it returns 428 with elicitation details
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPElicitationRequiredError

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.request_sampling = AsyncMock(
                side_effect=MCPElicitationRequiredError(
                    "User input required",
                    elicitations=[{"type": "form", "schema": {"type": "object"}}],
                )
            )
            mock_get.return_value = mock_service

            response = client.post(
                "/api/v1/mcp/sampling",
                json={"messages": [{"role": "user", "content": "Hello"}]},
            )

        assert response.status_code == 428
        data = response.json()
        # FastAPI HTTPException wraps the dict in "detail"
        assert "detail" in data
        assert "elicitations" in data["detail"]
        assert len(data["detail"]["elicitations"]) == 1
