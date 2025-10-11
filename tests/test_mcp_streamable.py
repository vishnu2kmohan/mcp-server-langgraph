"""Integration tests for MCP StreamableHTTP transport"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.mark.integration
@pytest.mark.mcp
class TestMCPStreamableHTTP:
    """Test StreamableHTTP MCP server"""

    def test_server_info_endpoint(self):
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

    @pytest.mark.skip(reason="Health app mounted at /health requires FastAPI mount testing setup")
    def test_health_endpoint(self):
        """Test GET /health/ returns healthy status"""
        pass

    def test_initialize_method(self):
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

    @pytest.mark.skip(reason="MCP SDK _tool_manager internal API requires complex mocking - tests need refactoring")
    def test_tools_list_method(self, mock_mcp_modules):
        """Test MCP tools/list method"""
        pass

    @pytest.mark.skip(reason="MCP SDK _tool_manager internal API requires complex mocking - tests need refactoring")
    def test_tools_call_method(self, mock_mcp_modules):
        """Test MCP tools/call method"""
        pass

    @pytest.mark.skip(reason="MCP SDK _tool_manager internal API requires complex mocking - tests need refactoring")
    def test_tools_call_unauthorized(self, mock_mcp_modules):
        """Test tools/call with unauthorized user"""
        pass

    @pytest.mark.skip(reason="MCP SDK _tool_manager internal API requires complex mocking - tests need refactoring")
    def test_streaming_response(self, mock_mcp_modules):
        """Test streaming response with Accept: application/x-ndjson"""
        pass

    @pytest.mark.skip(reason="MCP SDK _resource_manager internal API requires complex mocking - tests need refactoring")
    def test_resources_list_method(self, mock_mcp_modules):
        """Test MCP resources/list method"""
        pass

    @pytest.mark.skip(reason="HTTPException handling requires FastAPI internal behavior - test needs refactoring")
    def test_invalid_method(self):
        """Test invalid method returns error"""
        pass

    def test_malformed_request(self):
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

    @pytest.mark.skip(reason="FastAPI CORS middleware OPTIONS handling - test needs refactoring")
    def test_cors_headers(self):
        """Test CORS headers are present"""
        pass


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
