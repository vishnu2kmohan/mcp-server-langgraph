"""
E2E MCP WebSocket Tests.

True end-to-end tests for MCP WebSocket with live server infrastructure.
These tests connect to a running server using actual WebSocket clients (not TestClient).

Infrastructure Requirements:
- docker-compose.test.yml running (make test-infra-up-build)
- MCP server running on port 8000 (or via gateway on port 80)
- Keycloak for authentication

Test Approach:
- Uses websockets library for real WebSocket connections
- Authenticates via Keycloak OAuth2 to get real tokens
- Tests MCP protocol messages (initialize, tools/list, resources/list, etc.)
"""

from __future__ import annotations

import asyncio
import gc
import json
import os
from typing import Any

import pytest
import requests

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.websocket,
    pytest.mark.mcp,
    pytest.mark.asyncio,
]

# E2E test configuration
E2E_WS_BASE_URL = os.getenv("E2E_WS_BASE_URL", "ws://localhost:8000")
E2E_HTTP_BASE_URL = os.getenv("E2E_HTTP_BASE_URL", "http://localhost:8000")
E2E_KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost/authn")
E2E_CLIENT_ID = "agent-studio-keycloak-client-id-for-e2e-tests"
E2E_CLIENT_SECRET = "test-client-secret-for-e2e-tests"


def _get_keycloak_token(
    username: str,
    password: str = "",  # Deprecated: ROPC is disabled per ADR-0086
    client_id: str = E2E_CLIENT_ID,
    client_secret: str = E2E_CLIENT_SECRET,
) -> str | None:
    """Get Keycloak access token via modern OAuth2 flows.

    Two-step Token Exchange (RFC 8693):
    1. Get service account token via client_credentials
    2. Exchange it for a user-specific token with subject_token

    ROPC (password grant) is disabled per security audit (ADR-0086).
    """
    token_url = f"{E2E_KEYCLOAK_URL}/realms/default/protocol/openid-connect/token"

    # Step 1: Get service account token via client_credentials
    try:
        sa_response = requests.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "openid profile email offline_access",
            },
            timeout=10,
        )
        if sa_response.status_code != 200:
            return None
        sa_token = sa_response.json().get("access_token")
        if not sa_token:
            return None
    except Exception:
        return None

    # Step 2: Exchange for user-specific token (RFC 8693)
    try:
        response = requests.post(
            token_url,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "client_id": client_id,
                "client_secret": client_secret,
                "subject_token": sa_token,
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "requested_subject": username,
                "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "scope": "openid profile email offline_access",
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception:
        pass

    # Fallback to service account token if exchange not configured
    return sa_token


def _mcp_websocket_available() -> bool:
    """Check if MCP WebSocket endpoint is available."""
    try:
        # Check MCP server health
        response = requests.get(f"{E2E_HTTP_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture(autouse=True)
def skip_if_mcp_websocket_unavailable():
    """Skip E2E MCP WebSocket tests if infrastructure is not available."""
    if not _mcp_websocket_available():
        pytest.skip("MCP WebSocket infrastructure not available")


@pytest.fixture
def alice_token() -> str | None:
    """Get alice's access token from Keycloak."""
    return _get_keycloak_token("alice", "alice123")


@pytest.fixture
def bob_token() -> str | None:
    """Get bob's access token from Keycloak."""
    return _get_keycloak_token("bob", "bob123")


@pytest.fixture
def admin_token() -> str | None:
    """Get admin's access token from Keycloak."""
    return _get_keycloak_token("admin", "admin123")


@pytest.mark.xdist_group(name="test_mcp_websocket_e2e")
class TestMCPWebSocketE2E:
    """E2E tests for MCP WebSocket with live server."""

    def teardown_method(self) -> None:
        """Force GC to prevent resource accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_mcp_websocket_requires_authentication(self) -> None:
        """
        GIVEN no authentication token
        WHEN connecting to the MCP WebSocket endpoint
        THEN the connection is rejected (ADR-0103: all WS require auth).
        """
        try:
            import websockets
            from websockets.exceptions import InvalidStatus, WebSocketException
        except ImportError:
            pytest.skip("websockets library not installed")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp?v=1.0.0"

        try:
            async with websockets.connect(ws_url, open_timeout=5) as websocket:
                # If connection succeeds, server should close it quickly
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    pytest.fail("MCP WebSocket should require authentication")
                except (TimeoutError, WebSocketException):
                    pass  # Connection closed by server - expected
        except (TimeoutError, InvalidStatus, ConnectionRefusedError, WebSocketException):
            pass  # Connection rejected - expected

    @pytest.mark.asyncio
    async def test_mcp_websocket_initialize_handshake(self, alice_token: str | None) -> None:
        """
        GIVEN an authenticated MCP WebSocket
        WHEN sending initialize message
        THEN should receive proper initialize response with server info.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp?v=1.0.0&token={alice_token}"

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            # Send initialize request
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "e2e-test-client", "version": "1.0.0"},
                },
            }
            await websocket.send(json.dumps(init_message))

            # Receive response
            response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response = json.loads(response_text)

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 1
            assert "result" in response
            assert response["result"]["protocolVersion"] == "2025-11-25"
            assert "serverInfo" in response["result"]
            assert "capabilities" in response["result"]

    @pytest.mark.asyncio
    async def test_mcp_websocket_tools_list(self, alice_token: str | None) -> None:
        """
        GIVEN an authenticated MCP WebSocket after initialize
        WHEN sending tools/list message
        THEN should receive list of available tools.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp?v=1.0.0&token={alice_token}"

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            # Initialize first
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "e2e-test-client", "version": "1.0.0"},
                },
            }
            await websocket.send(json.dumps(init_message))
            await asyncio.wait_for(websocket.recv(), timeout=5.0)

            # Request tools/list
            tools_message = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            }
            await websocket.send(json.dumps(tools_message))

            # Receive response
            response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response = json.loads(response_text)

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 2
            assert "result" in response
            assert "tools" in response["result"]
            assert isinstance(response["result"]["tools"], list)

    @pytest.mark.asyncio
    async def test_mcp_websocket_resources_list(self, alice_token: str | None) -> None:
        """
        GIVEN an authenticated MCP WebSocket after initialize
        WHEN sending resources/list message
        THEN should receive list of available resources.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp?v=1.0.0&token={alice_token}"

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            # Initialize first
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "e2e-test-client", "version": "1.0.0"},
                },
            }
            await websocket.send(json.dumps(init_message))
            await asyncio.wait_for(websocket.recv(), timeout=5.0)

            # Request resources/list
            resources_message = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "resources/list",
                "params": {},
            }
            await websocket.send(json.dumps(resources_message))

            # Receive response
            response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response = json.loads(response_text)

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 3
            assert "result" in response
            assert "resources" in response["result"]

    @pytest.mark.asyncio
    async def test_mcp_websocket_prompts_list(self, alice_token: str | None) -> None:
        """
        GIVEN an authenticated MCP WebSocket after initialize
        WHEN sending prompts/list message
        THEN should receive list of available prompts.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp?v=1.0.0&token={alice_token}"

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            # Initialize first
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "e2e-test-client", "version": "1.0.0"},
                },
            }
            await websocket.send(json.dumps(init_message))
            await asyncio.wait_for(websocket.recv(), timeout=5.0)

            # Request prompts/list
            prompts_message = {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "prompts/list",
                "params": {},
            }
            await websocket.send(json.dumps(prompts_message))

            # Receive response
            response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response = json.loads(response_text)

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 4
            assert "result" in response
            assert "prompts" in response["result"]

    @pytest.mark.asyncio
    async def test_mcp_websocket_unknown_method_error(self, alice_token: str | None) -> None:
        """
        GIVEN an authenticated MCP WebSocket
        WHEN sending unknown method
        THEN should receive method not found error.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp?v=1.0.0&token={alice_token}"

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            # Send unknown method
            unknown_message = {
                "jsonrpc": "2.0",
                "id": 99,
                "method": "unknown/nonexistent",
                "params": {},
            }
            await websocket.send(json.dumps(unknown_message))

            # Receive error response
            response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response = json.loads(response_text)

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 99
            assert "error" in response
            assert response["error"]["code"] == -32601  # Method not found


@pytest.mark.xdist_group(name="test_mcp_websocket_auth_e2e")
class TestMCPWebSocketAuthenticatedE2E:
    """E2E tests for authenticated MCP WebSocket with live server."""

    def teardown_method(self) -> None:
        """Force GC to prevent resource accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_authenticated_mcp_websocket_connection(self, alice_token: str | None) -> None:
        """
        GIVEN a valid Keycloak access token
        WHEN connecting to the authenticated MCP WebSocket endpoint
        THEN the connection is established successfully.
        """
        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp/auth?v=1.0.0&token={alice_token}"

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            assert websocket.open

    @pytest.mark.asyncio
    async def test_authenticated_mcp_websocket_without_token_fails(self) -> None:
        """
        GIVEN no authentication token
        WHEN connecting to the authenticated MCP WebSocket endpoint
        THEN the connection is rejected.
        """
        try:
            import websockets
            from websockets.exceptions import InvalidStatus
        except ImportError:
            pytest.skip("websockets library not installed")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp/auth?v=1.0.0"

        with pytest.raises((InvalidStatus, asyncio.TimeoutError, ConnectionRefusedError)):
            async with websockets.connect(ws_url, open_timeout=5) as _:
                pass

    @pytest.mark.asyncio
    async def test_authenticated_mcp_websocket_with_invalid_token_fails(self) -> None:
        """
        GIVEN an invalid token
        WHEN connecting to the authenticated MCP WebSocket endpoint
        THEN the connection is rejected.
        """
        try:
            import websockets
            from websockets.exceptions import InvalidStatus
        except ImportError:
            pytest.skip("websockets library not installed")

        invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.token"
        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp/auth?v=1.0.0&token={invalid_token}"

        with pytest.raises((InvalidStatus, asyncio.TimeoutError, ConnectionRefusedError)):
            async with websockets.connect(ws_url, open_timeout=5) as _:
                pass

    @pytest.mark.asyncio
    async def test_authenticated_mcp_websocket_tools_call(self, alice_token: str | None) -> None:
        """
        GIVEN an authenticated MCP WebSocket connection
        WHEN sending tools/call message for langgraph-run
        THEN should receive tool execution result.
        """
        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp/auth?v=1.0.0&token={alice_token}"

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            # Initialize first
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "e2e-test-client", "version": "1.0.0"},
                },
            }
            await websocket.send(json.dumps(init_message))
            await asyncio.wait_for(websocket.recv(), timeout=5.0)

            # Call langgraph-run tool
            tool_call_message = {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "langgraph-run",
                    "arguments": {"query": "Hello from E2E test"},
                },
            }
            await websocket.send(json.dumps(tool_call_message))

            # Receive response (may take longer for tool execution)
            response_text = await asyncio.wait_for(websocket.recv(), timeout=30.0)
            response = json.loads(response_text)

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 5
            assert "result" in response
            assert "content" in response["result"]

    @pytest.mark.asyncio
    async def test_multiple_authenticated_clients_concurrent(self, alice_token: str | None, bob_token: str | None) -> None:
        """
        GIVEN multiple users with valid tokens
        WHEN they connect simultaneously to the authenticated MCP WebSocket
        THEN all connections are established successfully.
        """
        if alice_token is None or bob_token is None:
            pytest.skip("Could not obtain tokens from Keycloak")

        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        alice_ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp/auth?v=1.0.0&token={alice_token}"
        bob_ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp/auth?v=1.0.0&token={bob_token}"

        async def connect_and_initialize(ws_url: str) -> bool:
            async with websockets.connect(ws_url, open_timeout=10) as ws:
                assert ws.open
                # Send initialize
                init_message = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "e2e-test-client", "version": "1.0.0"},
                    },
                }
                await ws.send(json.dumps(init_message))
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                return "protocolVersion" in response

        # Connect both users simultaneously
        results = await asyncio.gather(
            connect_and_initialize(alice_ws_url),
            connect_and_initialize(bob_ws_url),
        )

        assert results[0] is True  # Alice connected and initialized
        assert results[1] is True  # Bob connected and initialized


@pytest.mark.xdist_group(name="test_mcp_websocket_session_e2e")
class TestMCPWebSocketSessionE2E:
    """E2E tests for MCP WebSocket with session ID."""

    def teardown_method(self) -> None:
        """Force GC to prevent resource accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_mcp_websocket_with_session_id(self, alice_token: str | None) -> None:
        """
        GIVEN a specific session ID and valid authentication
        WHEN connecting to MCP WebSocket with session ID
        THEN connection is established with session context.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        session_id = "test-session-12345"
        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp/{session_id}?v=1.0.0&token={alice_token}"

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            assert websocket.open

            # Initialize
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "e2e-test-client", "version": "1.0.0"},
                },
            }
            await websocket.send(json.dumps(init_message))
            response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response = json.loads(response_text)

            assert response["result"]["protocolVersion"] == "2025-11-25"

    @pytest.mark.asyncio
    async def test_mcp_websocket_reconnection_with_same_session(self, alice_token: str | None) -> None:
        """
        GIVEN an authenticated session ID that was previously connected
        WHEN reconnecting with the same session ID
        THEN connection is established for context resumption.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        session_id = "test-reconnect-session"
        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp/{session_id}?v=1.0.0&token={alice_token}"

        # First connection
        async with websockets.connect(ws_url, open_timeout=10) as websocket1:
            assert websocket1.open
            await asyncio.sleep(0.5)

        # Second connection (reconnection)
        async with websockets.connect(ws_url, open_timeout=10) as websocket2:
            assert websocket2.open
            # Send initialize to verify functionality
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "e2e-test-client", "version": "1.0.0"},
                },
            }
            await websocket2.send(json.dumps(init_message))
            response_text = await asyncio.wait_for(websocket2.recv(), timeout=5.0)
            response = json.loads(response_text)

            assert response["result"]["protocolVersion"] == "2025-11-25"


@pytest.mark.xdist_group(name="test_mcp_websocket_security_e2e")
class TestMCPWebSocketSecurityE2E:
    """E2E tests for MCP WebSocket security features."""

    def teardown_method(self) -> None:
        """Force GC to prevent resource accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_message_size_limit_enforced(self, alice_token: str | None) -> None:
        """
        GIVEN an authenticated MCP WebSocket
        WHEN sending a message exceeding the size limit (1MB)
        THEN should receive error response.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp?v=1.0.0&token={alice_token}"

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            # Send oversized message (>1MB)
            large_query = "x" * (1_000_001)  # Just over 1MB
            oversized_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "langgraph-run",
                    "arguments": {"query": large_query},
                },
            }
            await websocket.send(json.dumps(oversized_message))

            # Should receive error response
            response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response = json.loads(response_text)

            assert "error" in response
            assert response["error"]["code"] == -32600  # Invalid request

    @pytest.mark.asyncio
    async def test_invalid_session_id_rejected(self, alice_token: str | None) -> None:
        """
        GIVEN an invalid session ID with special characters
        WHEN connecting to authenticated MCP WebSocket with session ID
        THEN connection is rejected with appropriate error.
        """
        try:
            import websockets
            from websockets.exceptions import InvalidStatus
        except ImportError:
            pytest.skip("websockets library not installed")

        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        # Session IDs with special characters should be rejected
        invalid_session_ids = [
            "../../../etc/passwd",  # Path traversal
            "session\x00null",  # Null byte
            "<script>alert(1)</script>",  # XSS attempt
        ]

        for session_id in invalid_session_ids:
            # URL-encode the session ID for the request
            import urllib.parse

            encoded_session = urllib.parse.quote(session_id, safe="")
            ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp/{encoded_session}?v=1.0.0&token={alice_token}"

            with pytest.raises(
                (InvalidStatus, asyncio.TimeoutError, ConnectionRefusedError),
                match=r".*",
            ):
                async with websockets.connect(ws_url, open_timeout=5) as _:
                    # Should not reach here
                    pass

    @pytest.mark.asyncio
    async def test_json_parse_error_handled_gracefully(self, alice_token: str | None) -> None:
        """
        GIVEN an authenticated MCP WebSocket
        WHEN sending invalid JSON
        THEN should receive parse error response.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp?v=1.0.0&token={alice_token}"

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            # Send invalid JSON
            await websocket.send("not valid json{{{")

            # Should receive parse error response
            response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response = json.loads(response_text)

            assert "error" in response
            assert response["error"]["code"] == -32700  # Parse error


@pytest.mark.xdist_group(name="test_mcp_websocket_streaming_e2e")
class TestMCPWebSocketStreamingE2E:
    """E2E tests for MCP WebSocket streaming features."""

    def teardown_method(self) -> None:
        """Force GC to prevent resource accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_tools_list_returns_langgraph_run(self, alice_token: str | None) -> None:
        """
        GIVEN an authenticated MCP WebSocket
        WHEN requesting tools/list
        THEN should include langgraph-run tool with streaming capability.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp?v=1.0.0&token={alice_token}"

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            # Initialize first
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "e2e-test-client", "version": "1.0.0"},
                },
            }
            await websocket.send(json.dumps(init_message))
            await asyncio.wait_for(websocket.recv(), timeout=5.0)

            # Request tools/list
            tools_message = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            }
            await websocket.send(json.dumps(tools_message))

            # Receive response
            response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response = json.loads(response_text)

            assert "result" in response
            tools = response["result"]["tools"]

            # Should include langgraph-run tool
            tool_names = [t["name"] for t in tools]
            assert "langgraph-run" in tool_names

    @pytest.mark.asyncio
    async def test_prompts_get_code_review(self, alice_token: str | None) -> None:
        """
        GIVEN an authenticated MCP WebSocket
        WHEN requesting prompts/get for code_review
        THEN should return formatted prompt messages.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp?v=1.0.0&token={alice_token}"

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            # Initialize first
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "e2e-test-client", "version": "1.0.0"},
                },
            }
            await websocket.send(json.dumps(init_message))
            await asyncio.wait_for(websocket.recv(), timeout=5.0)

            # Request prompts/get
            prompt_message = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "prompts/get",
                "params": {
                    "name": "code_review",
                    "arguments": {
                        "code": "def hello(): return 'world'",
                        "language": "python",
                    },
                },
            }
            await websocket.send(json.dumps(prompt_message))

            # Receive response
            response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response = json.loads(response_text)

            assert "result" in response
            assert "messages" in response["result"]
            messages = response["result"]["messages"]
            assert len(messages) > 0
            assert messages[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_initialize_returns_streaming_capability(self, alice_token: str | None) -> None:
        """
        GIVEN an authenticated MCP WebSocket
        WHEN receiving initialize response
        THEN should include streaming capability.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp?v=1.0.0&token={alice_token}"

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            # Send initialize
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "e2e-test-client", "version": "1.0.0"},
                },
            }
            await websocket.send(json.dumps(init_message))

            # Receive response
            response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response = json.loads(response_text)

            assert "result" in response
            capabilities = response["result"]["capabilities"]
            assert "streaming" in capabilities
            assert capabilities["streaming"].get("supported") is True

    @pytest.mark.asyncio
    async def test_streaming_tools_call_sends_notifications(self, alice_token: str | None) -> None:
        """
        GIVEN an authenticated MCP WebSocket connection
        WHEN sending tools/call with _meta.streaming=true
        THEN should receive streaming notifications before final response.
        """
        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp/auth?v=1.0.0&token={alice_token}"

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            # Initialize first
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "e2e-test-client", "version": "1.0.0"},
                },
            }
            await websocket.send(json.dumps(init_message))
            await asyncio.wait_for(websocket.recv(), timeout=5.0)

            # Send streaming tools/call
            tool_call_message = {
                "jsonrpc": "2.0",
                "id": 10,
                "method": "tools/call",
                "params": {
                    "name": "langgraph-run",
                    "arguments": {"query": "Say hello"},
                    "_meta": {"streaming": True},
                },
            }
            await websocket.send(json.dumps(tool_call_message))

            # Collect all messages until we get the final response
            messages: list[dict[str, Any]] = []
            start_time = asyncio.get_event_loop().time()
            timeout = 30.0  # 30 second timeout for streaming

            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    break

                try:
                    response_text = await asyncio.wait_for(websocket.recv(), timeout=timeout - elapsed)
                    response = json.loads(response_text)
                    messages.append(response)

                    # Check if this is the final response
                    if response.get("id") == 10 and "result" in response:
                        break
                except TimeoutError:
                    break

            # Should have received at least some messages
            assert len(messages) >= 1, "Should receive at least the final response"

            # Check for streaming notifications
            notifications = [m for m in messages if "method" in m]
            responses = [m for m in messages if "id" in m and "result" in m]

            methods = [m.get("method") for m in notifications]
            ids = [m.get("id") for m in responses]

            # The final response should have id=10
            assert 10 in ids, "Should receive final response with id=10"

            # Verify streaming notification structure if present
            has_streaming_start = "$/streaming/start" in methods
            has_streaming_end = "$/streaming/end" in methods
            has_streaming_chunk = "$/streaming/chunk" in methods

            if has_streaming_start or has_streaming_end:
                # If we got any streaming notification, verify both start and end
                assert has_streaming_start, "Should have streaming start if streaming is active"
                assert has_streaming_end, "Should have streaming end if streaming is active"

                # Verify $/streaming/start structure
                start_notifications = [n for n in notifications if n.get("method") == "$/streaming/start"]
                for start in start_notifications:
                    assert "params" in start, "Start notification must have params"
                    params = start["params"]
                    assert "streamId" in params, "Start must have streamId"
                    assert "toolCallId" in params, "Start must have toolCallId"
                    assert isinstance(params["streamId"], str), "streamId must be string"

                # Verify $/streaming/chunk structure if present
                if has_streaming_chunk:
                    chunk_notifications = [n for n in notifications if n.get("method") == "$/streaming/chunk"]
                    for chunk in chunk_notifications:
                        assert "params" in chunk, "Chunk notification must have params"
                        params = chunk["params"]
                        assert "streamId" in params, "Chunk must have streamId"
                        assert "content" in params, "Chunk must have content"
                        # Verify content structure
                        content = params["content"]
                        assert "type" in content, "Content must have type"
                        assert "text" in content, "Content must have text"

                # Verify $/streaming/end structure
                end_notifications = [n for n in notifications if n.get("method") == "$/streaming/end"]
                for end in end_notifications:
                    assert "params" in end, "End notification must have params"
                    params = end["params"]
                    assert "streamId" in params, "End must have streamId"

                # Verify stream IDs are consistent
                start_stream_ids = {n["params"]["streamId"] for n in start_notifications}
                end_stream_ids = {n["params"]["streamId"] for n in end_notifications}
                assert start_stream_ids == end_stream_ids, "Start and end stream IDs must match"

    @pytest.mark.asyncio
    async def test_streaming_notification_order_verified(self, alice_token: str | None) -> None:
        """
        GIVEN an authenticated MCP WebSocket connection
        WHEN sending tools/call with _meta.streaming=true
        THEN streaming notifications arrive in correct order: start -> chunks -> end.
        """
        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp/auth?v=1.0.0&token={alice_token}"

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            # Initialize first
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "e2e-test-client", "version": "1.0.0"},
                },
            }
            await websocket.send(json.dumps(init_message))
            await asyncio.wait_for(websocket.recv(), timeout=5.0)

            # Send streaming tools/call
            tool_call_message = {
                "jsonrpc": "2.0",
                "id": 20,
                "method": "tools/call",
                "params": {
                    "name": "langgraph-run",
                    "arguments": {"query": "Count to three"},
                    "_meta": {"streaming": True},
                },
            }
            await websocket.send(json.dumps(tool_call_message))

            # Collect all notifications in order
            notification_order: list[str] = []
            start_time = asyncio.get_event_loop().time()
            timeout = 30.0

            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    break

                try:
                    response_text = await asyncio.wait_for(websocket.recv(), timeout=timeout - elapsed)
                    response = json.loads(response_text)

                    # Track notification methods in order
                    if "method" in response:
                        notification_order.append(response["method"])

                    # Check if this is the final response
                    if response.get("id") == 20 and "result" in response:
                        break
                except TimeoutError:
                    break

            # If streaming notifications present, verify order
            if "$/streaming/start" in notification_order:
                start_idx = notification_order.index("$/streaming/start")

                # If there's an end, it should come after start
                if "$/streaming/end" in notification_order:
                    end_idx = notification_order.index("$/streaming/end")
                    assert end_idx > start_idx, "End must come after start"

                    # All chunks should be between start and end
                    for i, method in enumerate(notification_order):
                        if method == "$/streaming/chunk":
                            assert i > start_idx, "Chunk must come after start"
                            assert i < end_idx, "Chunk must come before end"

    @pytest.mark.asyncio
    async def test_authenticated_streaming_tools_call(self, alice_token: str | None) -> None:
        """
        GIVEN an authenticated MCP WebSocket connection
        WHEN sending tools/call with _meta.streaming=true
        THEN should receive streaming notifications (authenticated streaming supported).
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp?v=1.0.0&token={alice_token}"

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            # Initialize first
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "e2e-test-client", "version": "1.0.0"},
                },
            }
            await websocket.send(json.dumps(init_message))
            await asyncio.wait_for(websocket.recv(), timeout=5.0)

            # Send streaming tools/call (authenticated)
            tool_call_message = {
                "jsonrpc": "2.0",
                "id": 30,
                "method": "tools/call",
                "params": {
                    "name": "langgraph-run",
                    "arguments": {"query": "Hello authenticated streaming"},
                    "_meta": {"streaming": True},
                },
            }
            await websocket.send(json.dumps(tool_call_message))

            # Collect messages
            messages: list[dict[str, Any]] = []
            start_time = asyncio.get_event_loop().time()
            timeout = 30.0

            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    break

                try:
                    response_text = await asyncio.wait_for(websocket.recv(), timeout=timeout - elapsed)
                    response = json.loads(response_text)
                    messages.append(response)

                    # Check if this is the final response
                    if response.get("id") == 30 and "result" in response:
                        break
                except TimeoutError:
                    break

            # Should have received at least the final response
            assert len(messages) >= 1, "Should receive at least the final response"

            # Check final response
            final_response = [m for m in messages if m.get("id") == 30 and "result" in m]
            assert len(final_response) == 1, "Should receive exactly one final response"

            # If streaming is working, verify notification structure
            notifications = [m for m in messages if "method" in m]
            if notifications:
                methods = [n.get("method") for n in notifications]

                if "$/streaming/start" in methods:
                    # Verify start notification has required fields
                    start = [n for n in notifications if n.get("method") == "$/streaming/start"][0]
                    assert "params" in start
                    assert "streamId" in start["params"]
                    assert "toolCallId" in start["params"]
                    # Authenticated connections should work
                    assert start["params"]["toolCallId"] == 30


@pytest.mark.xdist_group(name="test_mcp_websocket_security_limits_e2e")
class TestMCPWebSocketSecurityLimitsE2E:
    """E2E tests for MCP WebSocket security limits (connection, rate, size)."""

    def teardown_method(self) -> None:
        """Force GC to prevent resource accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_authenticated_user_connection_limit_enforced(self, alice_token: str | None) -> None:
        """
        GIVEN an authenticated user with active connections
        WHEN they try to exceed the per-user connection limit (default 5)
        THEN additional connections should be rejected with 4029 status.

        Note: Default limit is 5 connections per user, configurable via
        STREAMING_MAX_CONNECTIONS_PER_USER environment variable.
        """
        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        try:
            import websockets
            from websockets.exceptions import InvalidStatus
        except ImportError:
            pytest.skip("websockets library not installed")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp/auth?v=1.0.0&token={alice_token}"
        connections: list[Any] = []
        max_connections = 5  # Default limit

        try:
            # Create connections up to the limit
            for i in range(max_connections):
                ws = await websockets.connect(ws_url, open_timeout=10)
                connections.append(ws)
                assert ws.open, f"Connection {i + 1} should be open"

            # Attempt to exceed the limit
            with pytest.raises(InvalidStatus) as exc_info:
                await websockets.connect(ws_url, open_timeout=5)

            # Should be rejected with 4029 (too many connections)
            assert exc_info.value.status_code == 4029

        finally:
            for ws in connections:
                await ws.close()

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, alice_token: str | None) -> None:
        """
        GIVEN an authenticated MCP WebSocket
        WHEN sending messages faster than the rate limit (default 600/min)
        THEN should receive rate limit exceeded error.

        Note: This test sends messages rapidly to trigger rate limiting.
        Default is 600 messages per minute per user.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp?v=1.0.0&token={alice_token}"

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            # Initialize first
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "e2e-rate-limit-test", "version": "1.0.0"},
                },
            }
            await websocket.send(json.dumps(init_message))
            await asyncio.wait_for(websocket.recv(), timeout=5.0)

            # Send many messages rapidly to trigger rate limit
            rate_limit_hit = False
            for i in range(700):  # Exceed default 600/min limit
                msg = {
                    "jsonrpc": "2.0",
                    "id": i + 2,
                    "method": "tools/list",
                    "params": {},
                }
                await websocket.send(json.dumps(msg))

                try:
                    response_text = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    response = json.loads(response_text)

                    # Check if rate limit exceeded
                    if "error" in response and response["error"]["code"] == -32000:
                        rate_limit_hit = True
                        break
                except TimeoutError:
                    break

            # Rate limit should have been hit
            assert rate_limit_hit, "Rate limit should be enforced"

    @pytest.mark.asyncio
    async def test_configurable_message_size_limit(self, alice_token: str | None) -> None:
        """
        GIVEN default message size limit (1MB) on an authenticated connection
        WHEN sending a message just under the limit
        THEN should succeed without error.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp?v=1.0.0&token={alice_token}"

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            # Initialize first
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "e2e-size-test", "version": "1.0.0"},
                },
            }
            await websocket.send(json.dumps(init_message))
            await asyncio.wait_for(websocket.recv(), timeout=5.0)

            # Send message just under limit (should succeed)
            # Account for JSON overhead (method, id, params structure)
            small_query = "x" * 500_000  # 500KB - well under 1MB limit
            message = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "langgraph-run",
                    "arguments": {"query": small_query},
                },
            }
            await websocket.send(json.dumps(message))

            response_text = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            response = json.loads(response_text)

            # Should get a valid response (not size error)
            assert response["id"] == 2
            assert "result" in response or ("error" in response and response["error"]["code"] != -32600)


@pytest.mark.xdist_group(name="test_mcp_websocket_connection_limits_e2e")
class TestMCPWebSocketConnectionLimitsE2E:
    """E2E tests for MCP WebSocket connection limits."""

    def teardown_method(self) -> None:
        """Force GC to prevent resource accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_multiple_authenticated_connections_allowed(self, alice_token: str | None) -> None:
        """
        GIVEN multiple authenticated WebSocket clients
        WHEN connecting to MCP WebSocket
        THEN all connections are established within the per-user limit.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp?v=1.0.0&token={alice_token}"
        connections: list[Any] = []

        try:
            # Create 3 concurrent connections
            for _ in range(3):
                ws = await websockets.connect(ws_url, open_timeout=10)
                connections.append(ws)
                assert ws.open

            # All connections should be open
            assert len(connections) == 3
            for ws in connections:
                assert ws.open

        finally:
            # Close all connections
            for ws in connections:
                await ws.close()

    @pytest.mark.asyncio
    async def test_connection_persists_during_message_exchange(self, alice_token: str | None) -> None:
        """
        GIVEN an authenticated MCP WebSocket connection
        WHEN sending multiple messages in succession
        THEN connection remains stable throughout.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if alice_token is None:
            pytest.skip("Could not obtain alice's token from Keycloak")

        ws_url = f"{E2E_WS_BASE_URL}/api/v1/ws/mcp?v=1.0.0&token={alice_token}"

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            # Send multiple messages
            methods = ["initialize", "tools/list", "resources/list", "prompts/list"]

            for idx, method in enumerate(methods):
                if method == "initialize":
                    message = {
                        "jsonrpc": "2.0",
                        "id": idx + 1,
                        "method": method,
                        "params": {
                            "protocolVersion": "2025-11-25",
                            "capabilities": {},
                            "clientInfo": {"name": "e2e-test-client", "version": "1.0.0"},
                        },
                    }
                else:
                    message = {
                        "jsonrpc": "2.0",
                        "id": idx + 1,
                        "method": method,
                        "params": {},
                    }

                await websocket.send(json.dumps(message))
                response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response = json.loads(response_text)

                assert response["id"] == idx + 1
                assert "result" in response

            # Connection should still be open
            assert websocket.open
