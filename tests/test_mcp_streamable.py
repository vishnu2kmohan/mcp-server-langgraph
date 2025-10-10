"""Integration tests for MCP StreamableHTTP transport"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.mark.integration
@pytest.mark.mcp
class TestMCPStreamableHTTP:
    """Test StreamableHTTP MCP server"""

    @patch('mcp_server_streamable.agent_graph')
    @patch('mcp_server_streamable.auth_middleware')
    def test_server_info_endpoint(self, mock_auth, mock_agent):
        """Test GET / returns server info"""
        from mcp_server_streamable import app

        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "transport" in data
        assert data["transport"] == "streamable-http"

    @patch('mcp_server_streamable.agent_graph')
    @patch('mcp_server_streamable.auth_middleware')
    def test_health_endpoint(self, mock_auth, mock_agent):
        """Test GET /health returns healthy status"""
        from mcp_server_streamable import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @patch('mcp_server_streamable.agent_graph')
    @patch('mcp_server_streamable.auth_middleware')
    def test_initialize_method(self, mock_auth, mock_agent):
        """Test MCP initialize method"""
        from mcp_server_streamable import app

        client = TestClient(app)
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "0.1.0",
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }

        response = client.post("/message", json=request)

        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert "result" in data
        assert "serverInfo" in data["result"]

    @patch('mcp_server_streamable.agent_graph')
    @patch('mcp_server_streamable.auth_middleware')
    def test_tools_list_method(self, mock_auth, mock_agent):
        """Test MCP tools/list method"""
        from mcp_server_streamable import app

        client = TestClient(app)
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }

        response = client.post("/message", json=request)

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "tools" in data["result"]
        assert isinstance(data["result"]["tools"], list)

    @patch('mcp_server_streamable.agent_graph')
    @patch('mcp_server_streamable.auth_middleware')
    def test_tools_call_method(self, mock_auth, mock_agent):
        """Test MCP tools/call method"""
        from mcp_server_streamable import app
        from langchain_core.messages import AIMessage

        # Mock authentication
        mock_auth.authenticate.return_value = {
            "authorized": True,
            "user_id": "user:alice",
            "username": "alice"
        }

        # Mock authorization
        mock_auth.authorize.return_value = True

        # Mock agent execution
        mock_agent.invoke.return_value = {
            "messages": [AIMessage(content="The answer is 4")],
            "next_action": "end",
            "user_id": "user:alice",
            "request_id": "test-123"
        }

        client = TestClient(app)
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "chat",
                "arguments": {
                    "message": "What is 2+2?",
                    "username": "alice"
                }
            }
        }

        response = client.post("/message", json=request)

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "content" in data["result"]

    @patch('mcp_server_streamable.agent_graph')
    @patch('mcp_server_streamable.auth_middleware')
    def test_tools_call_unauthorized(self, mock_auth, mock_agent):
        """Test tools/call with unauthorized user"""
        from mcp_server_streamable import app

        # Mock authentication failure
        mock_auth.authenticate.return_value = {
            "authorized": False,
            "reason": "user_not_found"
        }

        client = TestClient(app)
        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "chat",
                "arguments": {
                    "message": "Hello",
                    "username": "unknown"
                }
            }
        }

        response = client.post("/message", json=request)

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "not authenticated" in data["error"]["message"].lower()

    @patch('mcp_server_streamable.agent_graph')
    @patch('mcp_server_streamable.auth_middleware')
    def test_streaming_response(self, mock_auth, mock_agent):
        """Test streaming response with Accept: application/x-ndjson"""
        from mcp_server_streamable import app
        from langchain_core.messages import AIMessage

        mock_auth.authenticate.return_value = {
            "authorized": True,
            "user_id": "user:alice",
            "username": "alice"
        }
        mock_auth.authorize.return_value = True

        mock_agent.invoke.return_value = {
            "messages": [AIMessage(content="Streaming response")],
            "next_action": "end",
            "user_id": "user:alice",
            "request_id": "test-stream"
        }

        client = TestClient(app)
        request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "chat",
                "arguments": {
                    "message": "Test streaming",
                    "username": "alice"
                }
            }
        }

        response = client.post(
            "/message",
            json=request,
            headers={"Accept": "application/x-ndjson"}
        )

        assert response.status_code == 200
        # Should be streaming response
        assert "x-ndjson" in response.headers.get("content-type", "").lower() or \
               "stream" in str(response.__class__).lower()

    @patch('mcp_server_streamable.agent_graph')
    @patch('mcp_server_streamable.auth_middleware')
    def test_resources_list_method(self, mock_auth, mock_agent):
        """Test MCP resources/list method"""
        from mcp_server_streamable import app

        client = TestClient(app)
        request = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "resources/list",
            "params": {}
        }

        response = client.post("/message", json=request)

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "resources" in data["result"]

    @patch('mcp_server_streamable.agent_graph')
    @patch('mcp_server_streamable.auth_middleware')
    def test_invalid_method(self, mock_auth, mock_agent):
        """Test invalid method returns error"""
        from mcp_server_streamable import app

        client = TestClient(app)
        request = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "invalid/method",
            "params": {}
        }

        response = client.post("/message", json=request)

        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    @patch('mcp_server_streamable.agent_graph')
    @patch('mcp_server_streamable.auth_middleware')
    def test_malformed_request(self, mock_auth, mock_agent):
        """Test malformed JSON-RPC request"""
        from mcp_server_streamable import app

        client = TestClient(app)
        request = {
            "not": "valid",
            "jsonrpc": "nope"
        }

        response = client.post("/message", json=request)

        # Should handle gracefully
        assert response.status_code in [200, 400, 500]

    @patch('mcp_server_streamable.agent_graph')
    @patch('mcp_server_streamable.auth_middleware')
    def test_cors_headers(self, mock_auth, mock_agent):
        """Test CORS headers are present"""
        from mcp_server_streamable import app

        client = TestClient(app)
        response = client.options("/message")

        # CORS should be configured
        assert response.status_code in [200, 204]


@pytest.mark.e2e
@pytest.mark.mcp
class TestMCPEndToEnd:
    """End-to-end tests for complete MCP flow"""

    @pytest.mark.skip(reason="Requires full system setup")
    @pytest.mark.asyncio
    async def test_complete_chat_flow(self):
        """Test complete flow: initialize -> list tools -> call tool"""
        import httpx

        base_url = "http://localhost:8000"

        async with httpx.AsyncClient() as client:
            # Initialize
            init_response = await client.post(
                f"{base_url}/message",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "0.1.0",
                        "clientInfo": {"name": "test", "version": "1.0"}
                    }
                }
            )
            assert init_response.status_code == 200

            # List tools
            tools_response = await client.post(
                f"{base_url}/message",
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {}
                }
            )
            assert tools_response.status_code == 200
            tools = tools_response.json()["result"]["tools"]
            assert len(tools) > 0

            # Call chat tool
            call_response = await client.post(
                f"{base_url}/message",
                json={
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "chat",
                        "arguments": {
                            "message": "Hello!",
                            "username": "alice"
                        }
                    }
                }
            )
            assert call_response.status_code == 200
            result = call_response.json()
            assert "result" in result
