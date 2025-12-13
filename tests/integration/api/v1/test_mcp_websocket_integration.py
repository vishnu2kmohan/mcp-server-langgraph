"""
MCP WebSocket Integration Tests

Integration tests for MCP WebSocket handler with real WebSocket connections.
Tests the full request/response cycle over WebSocket.
"""

from __future__ import annotations

import gc

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

pytestmark = [
    pytest.mark.integration,
    pytest.mark.api,
    pytest.mark.websocket,
]


@pytest.fixture
def mcp_websocket_app() -> FastAPI:
    """Create a test FastAPI app with the MCP WebSocket router."""
    from mcp_server_langgraph.api.v1.mcp_websocket import mcp_websocket_router

    app = FastAPI()
    app.include_router(mcp_websocket_router, prefix="/api/v1")
    return app


@pytest.fixture
def mcp_websocket_client(mcp_websocket_app: FastAPI) -> TestClient:
    """Create a test client for the MCP WebSocket app."""
    return TestClient(mcp_websocket_app)


@pytest.mark.xdist_group(name="test_mcp_websocket_integration")
class TestMCPWebSocketIntegration:
    """Integration tests for MCP WebSocket endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_initialize_handshake(self, mcp_websocket_client: TestClient) -> None:
        """
        GIVEN a WebSocket connection to the MCP endpoint
        WHEN sending an initialize message
        THEN should receive a proper initialize response.
        """
        with mcp_websocket_client.websocket_connect("/api/v1/mcp/ws") as websocket:
            # Send initialize request
            websocket.send_json(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "test-client", "version": "1.0.0"},
                    },
                }
            )

            # Receive response
            response = websocket.receive_json()

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 1
            assert "result" in response
            assert response["result"]["protocolVersion"] == "2025-11-25"
            assert "serverInfo" in response["result"]
            assert "capabilities" in response["result"]

    def test_websocket_tools_list(self, mcp_websocket_client: TestClient) -> None:
        """
        GIVEN an initialized WebSocket connection
        WHEN sending a tools/list message
        THEN should receive list of available tools.
        """
        with mcp_websocket_client.websocket_connect("/api/v1/mcp/ws") as websocket:
            # Send tools/list request
            websocket.send_json(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {},
                }
            )

            response = websocket.receive_json()

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 2
            assert "result" in response
            assert "tools" in response["result"]
            assert isinstance(response["result"]["tools"], list)
            assert len(response["result"]["tools"]) > 0

    def test_websocket_resources_list(self, mcp_websocket_client: TestClient) -> None:
        """
        GIVEN an initialized WebSocket connection
        WHEN sending a resources/list message
        THEN should receive list of available resources.
        """
        with mcp_websocket_client.websocket_connect("/api/v1/mcp/ws") as websocket:
            websocket.send_json(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "resources/list",
                    "params": {},
                }
            )

            response = websocket.receive_json()

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 3
            assert "result" in response
            assert "resources" in response["result"]

    def test_websocket_prompts_list(self, mcp_websocket_client: TestClient) -> None:
        """
        GIVEN an initialized WebSocket connection
        WHEN sending a prompts/list message
        THEN should receive list of available prompts.
        """
        with mcp_websocket_client.websocket_connect("/api/v1/mcp/ws") as websocket:
            websocket.send_json(
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "prompts/list",
                    "params": {},
                }
            )

            response = websocket.receive_json()

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 4
            assert "result" in response
            assert "prompts" in response["result"]

    def test_websocket_prompts_get(self, mcp_websocket_client: TestClient) -> None:
        """
        GIVEN an initialized WebSocket connection
        WHEN sending a prompts/get message
        THEN should receive prompt messages.
        """
        with mcp_websocket_client.websocket_connect("/api/v1/mcp/ws") as websocket:
            websocket.send_json(
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "prompts/get",
                    "params": {
                        "name": "code_review",
                        "arguments": {"code": "print('hello')", "language": "python"},
                    },
                }
            )

            response = websocket.receive_json()

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 5
            assert "result" in response
            assert "messages" in response["result"]
            assert len(response["result"]["messages"]) > 0

    def test_websocket_unknown_method(self, mcp_websocket_client: TestClient) -> None:
        """
        GIVEN a WebSocket connection
        WHEN sending an unknown method
        THEN should receive method not found error.
        """
        with mcp_websocket_client.websocket_connect("/api/v1/mcp/ws") as websocket:
            websocket.send_json(
                {
                    "jsonrpc": "2.0",
                    "id": 6,
                    "method": "unknown/method",
                    "params": {},
                }
            )

            response = websocket.receive_json()

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 6
            assert "error" in response
            assert response["error"]["code"] == -32601

    def test_websocket_invalid_json(self, mcp_websocket_client: TestClient) -> None:
        """
        GIVEN a WebSocket connection
        WHEN sending invalid JSON
        THEN should receive parse error.
        """
        with mcp_websocket_client.websocket_connect("/api/v1/mcp/ws") as websocket:
            # Send invalid JSON as text
            websocket.send_text("not valid json {")

            response = websocket.receive_json()

            assert response["jsonrpc"] == "2.0"
            assert "error" in response
            assert response["error"]["code"] == -32700

    def test_websocket_multiple_requests(self, mcp_websocket_client: TestClient) -> None:
        """
        GIVEN a WebSocket connection
        WHEN sending multiple requests in sequence
        THEN should receive correct responses for each.
        """
        with mcp_websocket_client.websocket_connect("/api/v1/mcp/ws") as websocket:
            # First request
            websocket.send_json(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": "2025-11-25", "capabilities": {}},
                }
            )
            response1 = websocket.receive_json()
            assert response1["id"] == 1
            assert "result" in response1

            # Second request
            websocket.send_json(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {},
                }
            )
            response2 = websocket.receive_json()
            assert response2["id"] == 2
            assert "tools" in response2["result"]

            # Third request
            websocket.send_json(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "prompts/list",
                    "params": {},
                }
            )
            response3 = websocket.receive_json()
            assert response3["id"] == 3
            assert "prompts" in response3["result"]


@pytest.mark.xdist_group(name="test_mcp_websocket_integration")
class TestMCPWebSocketWithSessionId:
    """Integration tests for MCP WebSocket with explicit session ID."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_with_session_id(self, mcp_websocket_client: TestClient) -> None:
        """
        GIVEN a WebSocket connection with explicit session ID
        WHEN sending a message
        THEN should receive proper response.
        """
        session_id = "test-session-123"
        with mcp_websocket_client.websocket_connect(f"/api/v1/mcp/ws/{session_id}") as websocket:
            websocket.send_json(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": "2025-11-25", "capabilities": {}},
                }
            )

            response = websocket.receive_json()

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 1
            assert "result" in response


@pytest.mark.xdist_group(name="test_mcp_websocket_integration")
class TestMCPWebSocketToolsCalls:
    """Integration tests for MCP WebSocket tools/call."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_tools_call(self, mcp_websocket_client: TestClient) -> None:
        """
        GIVEN a WebSocket connection
        WHEN calling a tool
        THEN should execute and return result.
        """
        with mcp_websocket_client.websocket_connect("/api/v1/mcp/ws") as websocket:
            websocket.send_json(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "langgraph-run",
                        "arguments": {"query": "Hello, world!"},
                    },
                }
            )

            response = websocket.receive_json()

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 1
            assert "result" in response
            assert "content" in response["result"]

    def test_websocket_resources_read(self, mcp_websocket_client: TestClient) -> None:
        """
        GIVEN a WebSocket connection
        WHEN reading a resource
        THEN should return resource content.
        """
        with mcp_websocket_client.websocket_connect("/api/v1/mcp/ws") as websocket:
            websocket.send_json(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "resources/read",
                    "params": {"uri": "config://test/resource"},
                }
            )

            response = websocket.receive_json()

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 1
            assert "result" in response
            assert "contents" in response["result"]
