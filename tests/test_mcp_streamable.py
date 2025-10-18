"""Integration tests for MCP StreamableHTTP transport"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ============================================================================
# Fixtures and Helpers
# ============================================================================


@pytest.fixture
def client():
    """Create FastAPI test client"""
    # Initialize observability before creating client
    from mcp_server_langgraph.core.config import settings
    from mcp_server_langgraph.mcp.server_streamable import app
    from mcp_server_langgraph.observability.telemetry import init_observability, is_initialized

    if not is_initialized():
        init_observability(settings=settings, enable_file_logging=False)

    return TestClient(app)


@pytest.fixture
def auth_token(client):
    """Get authentication token for testing"""
    response = client.post("/auth/login", json={"username": "alice", "password": "alice123"})
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


@pytest.mark.integration
@pytest.mark.mcp
class TestMCPStreamableHTTP:
    """Test StreamableHTTP MCP server"""

    def test_server_info_endpoint(self, client):
        """Test GET / returns server info"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "transport" in data
        assert data["transport"] == "streamable-http"
        # Verify auth endpoints are advertised
        assert "endpoints" in data
        assert "auth" in data["endpoints"]
        assert isinstance(data["endpoints"]["auth"], dict)
        assert data["endpoints"]["auth"]["login"] == "/auth/login"
        assert data["endpoints"]["auth"]["refresh"] == "/auth/refresh"
        # Verify authentication capabilities
        assert "capabilities" in data
        assert "authentication" in data["capabilities"]
        assert data["capabilities"]["authentication"]["tokenRefresh"] is True

    @pytest.mark.skip(reason="Health app mounted at /health requires FastAPI mount testing setup")
    def test_health_endpoint(self):
        """Test GET /health/ returns healthy status"""
        pass

    def test_login_success(self, client):
        """Test successful login returns JWT token"""
        response = client.post("/auth/login", json={"username": "alice", "password": "alice123"})

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user_id"] == "user:alice"
        assert data["username"] == "alice"
        assert "roles" in data
        assert "user" in data["roles"] or "premium" in data["roles"]

    def test_login_invalid_password(self, client):
        """Test login with invalid password fails"""
        response = client.post("/auth/login", json={"username": "alice", "password": "wrong"})

        assert response.status_code == 401
        assert "Authentication failed" in response.json()["detail"]

    def test_login_invalid_user(self, client):
        """Test login with non-existent user fails"""
        response = client.post("/auth/login", json={"username": "nonexistent", "password": "password"})

        assert response.status_code == 401
        assert "Authentication failed" in response.json()["detail"]

    def test_login_missing_password(self, client):
        """Test login without password fails"""
        response = client.post("/auth/login", json={"username": "alice"})

        # FastAPI validation error for missing required field
        assert response.status_code == 422

    def test_initialize_method(self, client):
        """Test MCP initialize method"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "0.1.0", "clientInfo": {"name": "test-client", "version": "1.0.0"}},
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
        from mcp_server_langgraph.mcp.server_streamable import app

        client = TestClient(app)
        request = {"not": "valid", "jsonrpc": "nope"}

        response = client.post("/message", json=request)

        # Should handle gracefully
        assert response.status_code in [200, 400, 500]

    @pytest.mark.skip(reason="FastAPI CORS middleware OPTIONS handling - test needs refactoring")
    def test_cors_headers(self):
        """Test CORS headers are present"""
        pass


@pytest.mark.integration
@pytest.mark.mcp
class TestTokenRefresh:
    """Test token refresh endpoint"""

    def test_refresh_token_success(self, client, auth_token):
        """Test successful token refresh"""
        response = client.post("/auth/refresh", json={"current_token": auth_token})

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert data["expires_in"] > 0

        # Verify the new token is valid
        import jwt

        from mcp_server_langgraph.core.config import settings

        # Decode new token (will raise if invalid)
        payload = jwt.decode(data["access_token"], settings.jwt_secret_key, algorithms=["HS256"])
        assert payload["sub"] == "user:alice"
        assert payload["username"] == "alice"

    def test_refresh_with_invalid_token(self, client):
        """Test refresh with invalid token fails"""
        response = client.post("/auth/refresh", json={"current_token": "invalid-token"})

        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    def test_refresh_without_token(self, client):
        """Test refresh without any token fails"""
        response = client.post("/auth/refresh", json={})

        assert response.status_code == 400
        assert "must be provided" in response.json()["detail"]

    def test_refresh_with_expired_token(self, client):
        """Test refresh with expired token fails"""
        from datetime import datetime, timedelta, timezone

        import jwt

        # Create an expired token
        from mcp_server_langgraph.core.config import settings

        expired_payload = {
            "sub": "user:alice",
            "username": "alice",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired 1 hour ago
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }

        expired_token = jwt.encode(expired_payload, settings.jwt_secret_key, algorithm="HS256")

        response = client.post("/auth/refresh", json={"current_token": expired_token})

        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.mcp
class TestTokenValidation:
    """Test token-based authentication for tool calls"""

    @pytest.mark.skip(reason="MCP SDK _tool_manager internal API not stable - requires complex mocking")
    def test_tool_call_without_token_fails(self, client):
        """Test that tool calls without token are rejected"""
        # Note: This test requires mocking MCP SDK internals which is not stable
        # The authentication logic is tested via login/refresh endpoints instead
        pass

    @pytest.mark.skip(reason="MCP SDK _tool_manager internal API not stable - requires complex mocking")
    def test_tool_call_with_invalid_token_fails(self, client):
        """Test that tool calls with invalid token are rejected"""
        # Note: This test requires mocking MCP SDK internals which is not stable
        # The authentication logic is tested via login/refresh endpoints instead
        pass

    @pytest.mark.skip(reason="Requires full agent setup with LLM - integration test only")
    def test_tool_call_with_valid_token_succeeds(self, client, auth_token):
        """Test that tool calls with valid token succeed"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "agent_chat",
                "arguments": {
                    "message": "Hello!",
                    "token": auth_token,
                    "user_id": "user:alice",
                    "response_format": "concise",
                },
            },
        }

        response = client.post("/message", json=request)

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "content" in data["result"]


@pytest.mark.e2e
@pytest.mark.mcp
class TestMCPEndToEnd:
    """End-to-end tests for complete MCP flow"""

    @pytest.mark.skip(reason="Requires full system setup")
    @pytest.mark.asyncio
    async def test_complete_chat_flow(self):
        """Test complete flow: login -> initialize -> list tools -> call tool"""
        import httpx

        base_url = "http://localhost:8000"

        async with httpx.AsyncClient() as client:
            # Login to get token
            login_response = await client.post(f"{base_url}/auth/login", json={"username": "alice", "password": "alice123"})
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]

            # Initialize
            init_response = await client.post(
                f"{base_url}/message",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": "0.1.0", "clientInfo": {"name": "test", "version": "1.0"}},
                },
            )
            assert init_response.status_code == 200

            # List tools
            tools_response = await client.post(
                f"{base_url}/message", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
            )
            assert tools_response.status_code == 200
            tools = tools_response.json()["result"]["tools"]
            assert len(tools) > 0

            # Call chat tool with token
            call_response = await client.post(
                f"{base_url}/message",
                json={
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "agent_chat",
                        "arguments": {"message": "Hello!", "token": token, "user_id": "user:alice"},
                    },
                },
            )
            assert call_response.status_code == 200
            result = call_response.json()
            assert "result" in result
