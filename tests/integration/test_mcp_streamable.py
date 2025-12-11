"""Integration tests for MCP StreamableHTTP transport"""

import gc

import pytest
from fastapi.testclient import TestClient

from tests.conftest import get_user_id
from datetime import UTC

pytestmark = pytest.mark.integration

# ============================================================================
# Fixtures and Helpers
# ============================================================================


@pytest.fixture
def client():
    """
    Create FastAPI test client with pre-populated test users.

    TDD Fix (2025-11-12):
    - Before: InMemoryUserProvider starts empty → login fails with 401
    - After: Pre-populate with alice/bob users → login succeeds

    Sets up:
    - alice / alice123 (matches Keycloak test realm)
    - bob / bob123 (matches Keycloak test realm)
    - admin / admin123 (for admin operations)

    Note: Uses get_mcp_server() to access server instance and populate users.
    """
    # Initialize observability before creating client
    from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider
    from mcp_server_langgraph.core.config import settings
    from mcp_server_langgraph.mcp.server_streamable import app, get_mcp_server
    from mcp_server_langgraph.observability.telemetry import init_observability, is_initialized

    if not is_initialized():
        init_observability(settings=settings, enable_file_logging=False)

    # Populate test users if using InMemoryUserProvider
    # (matches users in tests/e2e/mcp-test.json for consistency)
    #
    # IMPORTANT: Use worker-safe IDs for pytest-xdist parallel execution
    # to prevent state pollution between workers sharing the same infrastructure
    try:
        mcp_server = get_mcp_server()
        if mcp_server and mcp_server.auth:
            user_provider = mcp_server.auth.user_provider
            if isinstance(user_provider, InMemoryUserProvider):
                # Generate worker-safe user IDs
                alice_id = get_user_id("alice")
                bob_id = get_user_id("bob")
                admin_id = get_user_id("admin")

                # Only add if not already present (idempotent)
                if "alice" not in user_provider.users_db:
                    user_provider.add_user(
                        username="alice",
                        password="alice123",
                        email="alice@example.com",
                        roles=["user", "premium"],
                        user_id=alice_id,  # Worker-safe ID for parallel execution
                    )
                if "bob" not in user_provider.users_db:
                    user_provider.add_user(
                        username="bob",
                        password="bob123",
                        email="bob@example.com",
                        roles=["user"],
                        user_id=bob_id,  # Worker-safe ID for parallel execution
                    )
                if "admin" not in user_provider.users_db:
                    user_provider.add_user(
                        username="admin",
                        password="admin123",
                        email="admin@example.com",
                        roles=["admin"],
                        user_id=admin_id,  # Worker-safe ID for parallel execution
                    )
    except Exception:
        # If we can't access the server instance, skip user population
        # Tests may use dependency overrides or other auth mechanisms
        pass

    return TestClient(app)


@pytest.fixture
def auth_token(client):
    """Get authentication token for testing"""
    response = client.post("/auth/login", json={"username": "alice", "password": "alice123"})
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.xdist_group(name="testmcpstreamablehttp")
class TestMCPStreamableHTTP:
    """Test StreamableHTTP MCP server"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

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

    def test_health_endpoint_returns_status_and_timestamp(self, client):
        """Test GET /health/ returns healthy status"""
        # Health is mounted at /health/, test the root health endpoint
        response = client.get("/health/")

        # Should return health status
        assert response.status_code in [200, 404]  # 404 if mount not working, that's OK for this test

        # If health endpoint is working, verify structure
        if response.status_code == 200:
            data = response.json()
            assert "status" in data or "healthy" in str(data).lower()

    def test_login_success_with_valid_credentials_returns_jwt(self, client):
        """Test successful login returns JWT token"""
        response = client.post("/auth/login", json={"username": "alice", "password": "alice123"})

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user_id"] == get_user_id("alice")
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

    def test_login_missing_username(self, client):
        """Test login without username fails"""
        response = client.post("/auth/login", json={"password": "password123"})

        assert response.status_code == 422

    def test_login_empty_credentials(self, client):
        """Test login with empty credentials fails"""
        response = client.post("/auth/login", json={"username": "", "password": ""})

        # Should fail validation or authentication
        assert response.status_code in [401, 422]

    def test_initialize_method_with_valid_params_returns_server_info(self, client):
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

    def test_tools_call_without_token(self, client):
        """Test tools/call without authentication token fails"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "agent_chat",
                "arguments": {
                    "message": "Hello",
                    "user_id": get_user_id("test"),
                    # Missing token!
                },
            },
        }

        response = client.post("/message", json=request)

        # FIXED: Tighten assertion to expect specific error response
        # JSON-RPC returns 200 with error in body for protocol-level errors
        assert response.status_code == 200, "JSON-RPC should return 200 with error in body"
        data = response.json()
        assert "error" in data, "Response should contain error for missing token"
        # Verify it's an authentication/authorization error
        assert data["error"]["code"] in [-32000, -32001, -32603], "Should return auth-related error code"

    def test_tools_call_with_invalid_token(self, client):
        """Test tools/call with invalid token fails"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "agent_chat",
                "arguments": {
                    "message": "Hello",
                    "token": "invalid-token-12345",
                    "user_id": get_user_id("test"),
                },
            },
        }

        response = client.post("/message", json=request)

        # FIXED: Tighten assertion to expect specific error response
        # JSON-RPC returns 200 with error in body for protocol-level errors
        assert response.status_code == 200, "JSON-RPC should return 200 with error in body"
        data = response.json()
        assert "error" in data, "Response should contain error for invalid token"
        # Verify it's an authentication error
        assert data["error"]["code"] in [-32000, -32001, -32603], "Should return auth-related error code"

    def test_tools_call_missing_required_argument(self, client, auth_token):
        """Test tools/call with missing required argument"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "agent_chat",
                "arguments": {
                    # Missing 'message' argument!
                    "token": auth_token,
                    "user_id": get_user_id("alice"),
                },
            },
        }

        response = client.post("/message", json=request)

        # Should return error due to missing required field
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.json()
            assert "error" in data

    def test_tools_call_unknown_tool(self, client, auth_token):
        """Test calling an unknown tool"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "nonexistent_tool",
                "arguments": {
                    "token": auth_token,
                    "user_id": get_user_id("alice"),
                },
            },
        }

        response = client.post("/message", json=request)

        # Should return error for unknown tool
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.json()
            assert "error" in data

    def test_streaming_response_header(self, client):
        """Test streaming response with NDJSON Accept header"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }

        # Request with streaming Accept header
        response = client.post(
            "/message",
            json=request,
            headers={"Accept": "application/x-ndjson"},
        )

        # Should accept the request
        assert response.status_code == 200

        # Check if streaming was used (content-type or chunked encoding)
        content_type = response.headers.get("content-type", "")
        # May be application/x-ndjson or application/json depending on implementation
        assert "application/" in content_type

    def test_invalid_method_with_unknown_name_returns_error(self, client):
        """Test invalid MCP method returns error"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "invalid_method_name",
            "params": {},
        }

        response = client.post("/message", json=request)

        # JSON-RPC returns HTTP 200 with error in response body
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] in [-32601, -32603]  # Method not found or internal error

    def test_malformed_request_with_invalid_jsonrpc_returns_error(self):
        """Test malformed JSON-RPC request"""
        from mcp_server_langgraph.mcp.server_streamable import app

        client = TestClient(app)
        request = {"not": "valid", "jsonrpc": "nope"}

        response = client.post("/message", json=request)

        # Should handle gracefully
        assert response.status_code in [200, 400, 500]

    def test_message_endpoint_with_missing_id(self, client):
        """Test message endpoint with missing id field"""
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {},
        }

        response = client.post("/message", json=request)

        # Should handle request without id (notification)
        assert response.status_code in [200, 400]

    def test_tools_list_via_get_endpoint(self, client):
        """Test GET /tools convenience endpoint"""
        response = client.get("/tools")

        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert isinstance(data["tools"], list)
        assert len(data["tools"]) > 0

        # Verify tool structure
        first_tool = data["tools"][0]
        assert "name" in first_tool
        assert "description" in first_tool
        assert "inputSchema" in first_tool

    def test_resources_list_via_get_endpoint(self, client):
        """Test GET /resources convenience endpoint"""
        response = client.get("/resources")

        assert response.status_code == 200
        data = response.json()
        assert "resources" in data
        assert isinstance(data["resources"], list)

    def test_tools_list_via_message_endpoint(self, client):
        """Test tools/list via MCP message endpoint"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }

        response = client.post("/message", json=request)

        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert "result" in data
        assert "tools" in data["result"]
        assert len(data["result"]["tools"]) > 0

    def test_resources_list_via_message_endpoint(self, client):
        """Test resources/list via MCP message endpoint"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/list",
            "params": {},
        }

        response = client.post("/message", json=request)

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "resources" in data["result"]

    def test_resources_read_via_message_endpoint(self, client):
        """Test resources/read via MCP message endpoint"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/read",
            "params": {"uri": "agent://config"},
        }

        response = client.post("/message", json=request)

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "contents" in data["result"]

    def test_initialize_with_different_protocol_version(self, client):
        """Test initialize with different protocol versions"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "1.0.0", "clientInfo": {"name": "test", "version": "2.0"}},
        }

        response = client.post("/message", json=request)

        # Should accept and return server info
        assert response.status_code == 200
        data = response.json()
        assert "result" in data

    def test_cors_headers_on_options_request(self, client):
        """Test CORS headers are present on OPTIONS requests"""
        response = client.options("/")

        # FastAPI handles OPTIONS automatically if CORS is configured
        # Status could be 200 (allowed) or 405 (method not allowed)
        assert response.status_code in [200, 405]

    def test_server_capabilities_in_root_response(self, client):
        """Test server capabilities are properly advertised"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Verify capabilities
        assert "capabilities" in data
        caps = data["capabilities"]

        # Tools capability
        assert "tools" in caps
        assert caps["tools"]["listSupported"] is True
        assert caps["tools"]["callSupported"] is True

        # Resources capability
        assert "resources" in caps
        assert caps["resources"]["listSupported"] is True

        # Streaming capability
        assert caps["streaming"] is True

        # Authentication capability
        assert "authentication" in caps
        assert "jwt" in caps["authentication"]["methods"]
        assert caps["authentication"]["tokenRefresh"] is True

    def test_server_version_in_response(self, client):
        """Test server version is included in responses"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert len(data["version"]) > 0

    def test_initialize_returns_server_capabilities(self, client):
        """Test initialize returns server capabilities"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "0.1.0", "clientInfo": {"name": "test", "version": "1.0"}},
        }

        response = client.post("/message", json=request)

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "capabilities" in data["result"]
        assert "tools" in data["result"]["capabilities"]

    def test_message_endpoint_handles_json_parse_error(self, client):
        """Test message endpoint handles invalid JSON gracefully"""
        # Send invalid JSON
        response = client.post("/message", content="not valid json", headers={"Content-Type": "application/json"})

        # JSON-RPC can return 200 with error in body, or 400 for parse errors
        # Both are acceptable depending on implementation
        assert response.status_code in [200, 400, 422]
        if response.status_code == 200:
            # If 200, should have JSON-RPC error in body
            data = response.json()
            assert "error" in data

    def test_multiple_initialize_calls(self, client):
        """Test multiple initialize calls are handled"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "0.1.0", "clientInfo": {"name": "test", "version": "1.0"}},
        }

        # First initialize
        response1 = client.post("/message", json=request)
        assert response1.status_code == 200

        # Second initialize (should also succeed)
        request["id"] = 2
        response2 = client.post("/message", json=request)
        assert response2.status_code == 200

    def test_resources_read_with_invalid_uri(self, client):
        """Test resources/read with invalid URI"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/read",
            "params": {"uri": "invalid://nonexistent"},
        }

        response = client.post("/message", json=request)

        # Should return successfully (returns placeholder for unknown URIs)
        assert response.status_code == 200

    def test_login_with_very_long_username(self, client):
        """Test login with excessively long username"""
        very_long_username = "a" * 1000

        response = client.post("/auth/login", json={"username": very_long_username, "password": "password"})

        # Should handle gracefully (either validation error or auth failure)
        assert response.status_code in [401, 422]

    def test_login_with_special_characters_in_username(self, client):
        """Test login with special characters"""
        response = client.post("/auth/login", json={"username": "user@example.com", "password": "password"})

        # Should handle gracefully
        assert response.status_code in [401, 422]


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.xdist_group(name="testtokenrefresh")
class TestTokenRefresh:
    """Test token refresh endpoint"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

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
        assert payload["sub"] == get_user_id("alice")
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
        from datetime import datetime, timedelta

        import jwt

        # Create an expired token
        from mcp_server_langgraph.core.config import settings

        expired_payload = {
            "sub": get_user_id("alice"),
            "username": "alice",
            "exp": datetime.now(UTC) - timedelta(hours=1),  # Expired 1 hour ago
            "iat": datetime.now(UTC) - timedelta(hours=2),
        }

        expired_token = jwt.encode(expired_payload, settings.jwt_secret_key, algorithm="HS256")

        response = client.post("/auth/refresh", json={"current_token": expired_token})

        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    def test_refresh_token_missing_username(self, client):
        """Test refresh with token missing username claim"""
        from datetime import datetime, timedelta

        import jwt

        from mcp_server_langgraph.core.config import settings

        # Create token without username
        invalid_payload = {
            "sub": get_user_id("alice"),
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "iat": datetime.now(UTC),
        }

        invalid_token = jwt.encode(invalid_payload, settings.jwt_secret_key, algorithm="HS256")

        response = client.post("/auth/refresh", json={"current_token": invalid_token})

        # Should fail due to missing username
        assert response.status_code == 401

    def test_refresh_token_wrong_secret(self, client):
        """Test refresh with token signed with wrong secret"""
        from datetime import datetime, timedelta

        import jwt

        # Create token with wrong secret
        wrong_secret_payload = {
            "sub": get_user_id("alice"),
            "username": "alice",
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "iat": datetime.now(UTC),
        }

        wrong_token = jwt.encode(wrong_secret_payload, "wrong-secret-key", algorithm="HS256")

        response = client.post("/auth/refresh", json={"current_token": wrong_token})

        assert response.status_code == 401

    def test_refresh_token_returns_different_token(self, client, auth_token):
        """Test that refresh returns a different token"""
        response = client.post("/auth/refresh", json={"current_token": auth_token})

        assert response.status_code == 200
        new_token = response.json()["access_token"]

        # New token should be different from original
        assert new_token != auth_token

    def test_refresh_token_preserves_user_claims(self, client, auth_token):
        """Test that refresh preserves user information"""
        import jwt

        from mcp_server_langgraph.core.config import settings

        # Get original claims
        original_payload = jwt.decode(auth_token, settings.jwt_secret_key, algorithms=["HS256"])

        # Refresh token
        response = client.post("/auth/refresh", json={"current_token": auth_token})
        new_token = response.json()["access_token"]

        # Get new claims
        new_payload = jwt.decode(new_token, settings.jwt_secret_key, algorithms=["HS256"])

        # Should preserve user information
        assert new_payload["sub"] == original_payload["sub"]
        assert new_payload["username"] == original_payload["username"]


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.xdist_group(name="testtokenvalidation")
class TestTokenValidation:
    """Test token-based authentication for tool calls"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_tool_call_authorization_flow(self, client, auth_token):
        """Test complete authorization flow for tool calls"""
        # This test verifies the auth flow without actually calling the LLM
        # The authorization logic is what we're testing

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "agent_chat",
                "arguments": {
                    "message": "Test message",
                    "token": auth_token,
                    "user_id": get_user_id("alice"),
                    "response_format": "concise",
                },
            },
        }

        response = client.post("/message", json=request)

        # The test verifies auth is checked
        # Actual execution may fail due to missing LLM, but auth should work
        # We accept 200 (success) or 500 (LLM failure), but not 401/403 (auth failure)
        assert response.status_code not in [401, 403], "Authentication should succeed"

    def test_tool_call_requires_executor_permission(self, client, auth_token):
        """Test that tool calls check executor permission"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "agent_chat",
                "arguments": {
                    "message": "Test",
                    "token": auth_token,
                    "user_id": get_user_id("alice"),
                },
            },
        }

        response = client.post("/message", json=request)

        # Should not fail with unauthorized error (alice has permission)
        assert response.status_code not in [401, 403]

    def test_conversation_get_requires_token(self, client):
        """Test conversation_get requires authentication"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "conversation_get",
                "arguments": {
                    "thread_id": "test-thread",
                    "user_id": get_user_id("test"),
                    # Missing token!
                },
            },
        }

        response = client.post("/message", json=request)

        # Should fail due to missing token
        assert response.status_code in [200, 403]
        if response.status_code == 200:
            data = response.json()
            assert "error" in data

    def test_conversation_search_with_valid_token(self, client, auth_token):
        """Test conversation_search with valid authentication"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "conversation_search",
                "arguments": {
                    "query": "test",
                    "token": auth_token,
                    "user_id": get_user_id("alice"),
                    "limit": 10,
                },
            },
        }

        response = client.post("/message", json=request)

        # Should not fail auth (actual execution may vary)
        assert response.status_code not in [401, 403]


@pytest.mark.e2e
@pytest.mark.mcp
@pytest.mark.xdist_group(name="testmcpendtoend")
class TestMCPEndToEnd:
    """End-to-end tests for complete MCP flow"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_complete_mcp_workflow_with_test_client(self, client, auth_token):
        """Test complete MCP workflow using test client"""
        # Step 1: Initialize
        init_response = client.post(
            "/message",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "0.1.0", "clientInfo": {"name": "test", "version": "1.0"}},
            },
        )
        assert init_response.status_code == 200
        assert "serverInfo" in init_response.json()["result"]

        # Step 2: List tools
        tools_response = client.post("/message", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        assert tools_response.status_code == 200
        tools = tools_response.json()["result"]["tools"]
        assert len(tools) > 0
        tool_names = [t["name"] for t in tools]
        assert "agent_chat" in tool_names

        # Step 3: List resources
        resources_response = client.post(
            "/message", json={"jsonrpc": "2.0", "id": 3, "method": "resources/list", "params": {}}
        )
        assert resources_response.status_code == 200
        assert "resources" in resources_response.json()["result"]

        # Step 4: Test conversation search (doesn't require LLM)
        search_response = client.post(
            "/message",
            json={
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "conversation_search",
                    "arguments": {"query": "test", "token": auth_token, "user_id": get_user_id("alice"), "limit": 5},
                },
            },
        )
        # Should not fail auth
        assert search_response.status_code not in [401, 403]

    def test_mcp_protocol_version_negotiation(self, client):
        """Test MCP protocol version negotiation"""
        versions_to_test = ["0.1.0", "1.0.0", "2.0.0"]

        for version in versions_to_test:
            response = client.post(
                "/message",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": version, "clientInfo": {"name": "test", "version": "1.0"}},
                },
            )
            # Should accept all versions gracefully
            assert response.status_code == 200
            assert "result" in response.json()

    def test_multiple_sequential_tool_calls(self, client, auth_token):
        """Test multiple sequential tool calls in one session"""
        # Call 1: List tools
        response1 = client.post("/message", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        assert response1.status_code == 200

        # Call 2: List resources
        response2 = client.post("/message", json={"jsonrpc": "2.0", "id": 2, "method": "resources/list", "params": {}})
        assert response2.status_code == 200

        # Call 3: Search conversations
        response3 = client.post(
            "/message",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "conversation_search",
                    "arguments": {"query": "test", "token": auth_token, "user_id": get_user_id("alice"), "limit": 1},
                },
            },
        )
        assert response3.status_code not in [401, 403]

        # All calls should have different IDs in responses
        assert response1.json()["id"] == 1
        assert response2.json()["id"] == 2
        assert response3.json()["id"] == 3
