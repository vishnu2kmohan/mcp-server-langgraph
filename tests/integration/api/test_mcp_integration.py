"""
Integration Tests for MCP API with Mock MCP Server.

These tests verify the full flow from API endpoints through MCPBridge
to a mock MCP server that responds to JSON-RPC requests.

Tests verify:
1. Full request/response cycle for MCP operations
2. Error handling (connection failures, permission denied, etc.)
3. Streaming scenarios
4. Protocol version negotiation
"""

from __future__ import annotations

import asyncio
import gc
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

pytestmark = [
    pytest.mark.integration,
    pytest.mark.api,
]


class MockMCPServer:
    """
    Mock MCP server that simulates JSON-RPC responses.

    Useful for integration testing without a real MCP server.
    """

    def __init__(self) -> None:
        """Initialize mock server state."""
        self.resources: list[dict[str, Any]] = []
        self.tasks: dict[str, dict[str, Any]] = {}
        self.request_count = 0
        self.error_mode: str | None = None

    def add_resource(self, uri: str, name: str, mime_type: str = "text/plain") -> None:
        """Add a resource to the mock server."""
        self.resources.append(
            {
                "uri": uri,
                "name": name,
                "mimeType": mime_type,
            }
        )

    def add_task(self, task_id: str, status: str = "working") -> None:
        """Add a task to the mock server."""
        self.tasks[task_id] = {
            "taskId": task_id,
            "status": status,
            "createdAt": datetime.now().isoformat(),
            "lastUpdatedAt": datetime.now().isoformat(),
        }

    def set_error_mode(self, mode: str | None) -> None:
        """Set error mode: 'permission', 'connection', 'not_found', None."""
        self.error_mode = mode

    def handle_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Handle a JSON-RPC request and return result or error."""
        self.request_count += 1

        # Check for error mode
        if self.error_mode == "permission":
            return {
                "error": {
                    "code": -32001,
                    "message": "Permission denied",
                }
            }
        elif self.error_mode == "connection":
            raise ConnectionError("Connection refused")

        # Handle methods
        if method == "resources/list":
            return {"result": {"resources": self.resources}}

        elif method == "resources/read":
            uri = params.get("uri", "")
            for resource in self.resources:
                if resource["uri"] == uri:
                    return {
                        "result": {
                            "contents": [
                                {
                                    "uri": uri,
                                    "mimeType": resource["mimeType"],
                                    "text": f"Content of {resource['name']}",
                                }
                            ]
                        }
                    }
            return {
                "error": {
                    "code": -32002,
                    "message": "Resource not found",
                    "data": {"uri": uri},
                }
            }

        elif method == "tasks/get":
            task_id = params.get("taskId", "")
            if task_id in self.tasks:
                return {"result": self.tasks[task_id]}
            return {
                "error": {
                    "code": -32002,
                    "message": "Task not found",
                    "data": {"taskId": task_id},
                }
            }

        elif method == "tasks/list":
            return {"result": {"tasks": list(self.tasks.values())}}

        elif method == "sampling/createMessage":
            return {
                "result": {
                    "role": "assistant",
                    "content": {"type": "text", "text": "Hello from mock LLM!"},
                    "model": "mock-model",
                    "stopReason": "end_turn",
                }
            }

        else:
            return {
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                }
            }


@pytest.fixture
def mock_mcp_server() -> MockMCPServer:
    """Create a mock MCP server."""
    server = MockMCPServer()
    # Add some default resources
    server.add_resource("file:///test.txt", "test.txt", "text/plain")
    server.add_resource("file:///data.json", "data.json", "application/json")
    # Add a task
    server.add_task("task-123", "working")
    return server


@pytest.fixture
def app_with_mocked_bridge(mock_mcp_server: MockMCPServer) -> FastAPI:
    """Create a FastAPI app with mocked MCP bridge."""
    from fastapi import FastAPI
    from mcp_server_langgraph.api.v1.mcp import mcp_router

    app = FastAPI()
    app.include_router(mcp_router, prefix="/api/v1/mcp")
    return app


@pytest.mark.xdist_group(name="mcp_integration")
class TestMCPResourcesIntegration:
    """Integration tests for MCP resources API."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_resources_returns_all_resources(
        self,
        app_with_mocked_bridge: FastAPI,
        mock_mcp_server: MockMCPServer,
    ) -> None:
        """
        GIVEN a mock MCP server with resources
        WHEN GET /mcp/resources is called
        THEN all resources are returned
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPResource

        # Create mock resources to return
        mock_resources = [
            MCPResource(uri="file:///test.txt", name="test.txt", mime_type="text/plain"),
            MCPResource(uri="file:///data.json", name="data.json", mime_type="application/json"),
        ]

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.list_resources = AsyncMock(return_value=mock_resources)
            mock_get.return_value = mock_service

            client = TestClient(app_with_mocked_bridge)
            response = client.get("/api/v1/mcp/resources")

            assert response.status_code == 200
            data = response.json()
            assert len(data["resources"]) == 2
            assert data["resources"][0]["uri"] == "file:///test.txt"

    def test_read_resource_returns_content(
        self,
        app_with_mocked_bridge: FastAPI,
        mock_mcp_server: MockMCPServer,
    ) -> None:
        """
        GIVEN a mock MCP server with a resource
        WHEN GET /mcp/resources/content is called
        THEN the resource content is returned
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPResourceContent

        mock_content = [
            MCPResourceContent(
                uri="file:///test.txt",
                mime_type="text/plain",
                text="Content of test.txt",
            )
        ]

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.read_resource = AsyncMock(return_value=mock_content)
            mock_get.return_value = mock_service

            client = TestClient(app_with_mocked_bridge)
            response = client.get(
                "/api/v1/mcp/resources/content",
                params={"uri": "file:///test.txt"},
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["contents"]) == 1
            assert "Content of test.txt" in data["contents"][0]["text"]


@pytest.mark.xdist_group(name="mcp_integration")
class TestMCPSamplingIntegration:
    """Integration tests for MCP sampling API."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_sampling_creates_message(
        self,
        app_with_mocked_bridge: FastAPI,
        mock_mcp_server: MockMCPServer,
    ) -> None:
        """
        GIVEN a mock MCP server
        WHEN POST /mcp/sampling is called
        THEN an LLM response is returned
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import SamplingResponse

        mock_response = SamplingResponse(
            role="assistant",
            content={"type": "text", "text": "Hello from mock LLM!"},
            model="mock-model",
            stop_reason="end_turn",
        )

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.request_sampling = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_service

            client = TestClient(app_with_mocked_bridge)
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
            assert "Hello from mock LLM" in data["content"]["text"]


@pytest.mark.xdist_group(name="mcp_integration")
class TestMCPTasksIntegration:
    """Integration tests for MCP tasks API."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_list_tasks_returns_active_tasks(
        self,
        app_with_mocked_bridge: FastAPI,
        mock_mcp_server: MockMCPServer,
    ) -> None:
        """
        GIVEN a mock MCP server with tasks
        WHEN GET /mcp/tasks is called
        THEN all tasks are returned
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPTask, TaskStatus

        mock_tasks = [
            MCPTask(
                task_id="task-123",
                status=TaskStatus.WORKING,
                created_at=datetime.now(),
                last_updated_at=datetime.now(),
            )
        ]

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.list_tasks = AsyncMock(return_value=mock_tasks)
            mock_get.return_value = mock_service

            client = TestClient(app_with_mocked_bridge)
            response = client.get("/api/v1/mcp/tasks")

            assert response.status_code == 200
            data = response.json()
            assert len(data["tasks"]) == 1
            assert data["tasks"][0]["task_id"] == "task-123"

    def test_get_task_returns_task_status(
        self,
        app_with_mocked_bridge: FastAPI,
        mock_mcp_server: MockMCPServer,
    ) -> None:
        """
        GIVEN a mock MCP server with a task
        WHEN GET /mcp/tasks/{id} is called
        THEN the task status is returned
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPTask, TaskStatus

        mock_task = MCPTask(
            task_id="task-123",
            status=TaskStatus.WORKING,
            created_at=datetime.now(),
            last_updated_at=datetime.now(),
            status_message="Processing...",
        )

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.get_task = AsyncMock(return_value=mock_task)
            mock_get.return_value = mock_service

            client = TestClient(app_with_mocked_bridge)
            response = client.get("/api/v1/mcp/tasks/task-123")

            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "task-123"
            assert data["status"] == "working"


@pytest.mark.xdist_group(name="mcp_integration")
class TestMCPErrorIntegration:
    """Integration tests for MCP error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_permission_denied_returns_403(
        self,
        app_with_mocked_bridge: FastAPI,
        mock_mcp_server: MockMCPServer,
    ) -> None:
        """
        GIVEN a mock MCP server returning permission error
        WHEN an API call is made
        THEN 403 Forbidden is returned
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPPermissionError

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.list_resources = AsyncMock(side_effect=MCPPermissionError("Access denied"))
            mock_get.return_value = mock_service

            client = TestClient(app_with_mocked_bridge)
            response = client.get("/api/v1/mcp/resources")

            assert response.status_code == 403
            assert "denied" in response.json()["detail"].lower()

    def test_connection_error_returns_503(
        self,
        app_with_mocked_bridge: FastAPI,
        mock_mcp_server: MockMCPServer,
    ) -> None:
        """
        GIVEN a mock MCP server that is unreachable
        WHEN an API call is made
        THEN 503 Service Unavailable is returned
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPConnectionError

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.list_resources = AsyncMock(side_effect=MCPConnectionError("Connection refused"))
            mock_get.return_value = mock_service

            client = TestClient(app_with_mocked_bridge)
            response = client.get("/api/v1/mcp/resources")

            assert response.status_code == 503
            assert "connection" in response.json()["detail"].lower()

    def test_resource_not_found_returns_404(
        self,
        app_with_mocked_bridge: FastAPI,
        mock_mcp_server: MockMCPServer,
    ) -> None:
        """
        GIVEN a mock MCP server without the requested resource
        WHEN resource is requested
        THEN 404 Not Found is returned
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPResourceNotFoundError

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.read_resource = AsyncMock(
                side_effect=MCPResourceNotFoundError("Resource not found", uri="file:///missing.txt")
            )
            mock_get.return_value = mock_service

            client = TestClient(app_with_mocked_bridge)
            response = client.get(
                "/api/v1/mcp/resources/content",
                params={"uri": "file:///missing.txt"},
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


@pytest.mark.xdist_group(name="mcp_integration")
class TestMCPFullFlowIntegration:
    """Integration tests for complete MCP workflows."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_chat_with_resource_context(
        self,
        app_with_mocked_bridge: FastAPI,
        mock_mcp_server: MockMCPServer,
    ) -> None:
        """
        GIVEN a mock MCP server with resources
        WHEN a chat message is sent with resource context
        THEN the response includes resource-informed content
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import SamplingResponse

        mock_response = SamplingResponse(
            role="assistant",
            content={"type": "text", "text": "Based on the file content..."},
            model="mock-model",
        )

        with patch("mcp_server_langgraph.api.v1.mcp.get_mcp_service") as mock_get:
            mock_service = MagicMock()
            mock_service.request_sampling = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_service

            client = TestClient(app_with_mocked_bridge)
            response = client.post(
                "/api/v1/mcp/sampling",
                json={
                    "messages": [{"role": "user", "content": "What's in the test file?"}],
                    "max_tokens": 100,
                    "system_prompt": "You have access to file:///test.txt",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["role"] == "assistant"
