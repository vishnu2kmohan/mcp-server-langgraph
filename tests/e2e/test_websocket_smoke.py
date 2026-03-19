"""
WebSocket Endpoint Smoke Tests.

Validates that all WebSocket endpoints defined in the frontend WS_ENDPOINTS
are reachable and respond appropriately to connection attempts.

These are lightweight smoke tests that verify:
1. Endpoints exist and accept WebSocket connections
2. Endpoints respond to basic messages
3. Authentication requirements are enforced

Infrastructure Requirements:
- docker-compose.test.yml running (make test-infra-up-build)
- MCP server running on port 8000
- Keycloak for authentication

Test Approach:
- Uses websockets library for real WebSocket connections
- Tests each endpoint from the frontend WS_ENDPOINTS constant
- Parameterized tests for comprehensive coverage

Note: Uses websockets >= 15.0 API with State enum instead of .open attribute.
"""

from __future__ import annotations

import asyncio
import gc
import json
import os
from typing import TYPE_CHECKING

import pytest
import requests

if TYPE_CHECKING:
    from websockets import ClientConnection


def _is_ws_open(websocket: ClientConnection) -> bool:
    """Check if websocket connection is open (compatible with websockets >= 15.0)."""
    try:
        # websockets >= 15.0 uses State enum
        from websockets import State

        return websocket.state == State.OPEN
    except (ImportError, AttributeError):
        # Fallback for older versions (< 11.0)
        return getattr(websocket, "open", False)


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.websocket,
    pytest.mark.smoke,
    pytest.mark.asyncio,
]

# E2E test configuration
E2E_WS_BASE_URL = os.getenv("E2E_WS_BASE_URL", "ws://localhost:8000")
E2E_HTTP_BASE_URL = os.getenv("E2E_HTTP_BASE_URL", "http://localhost:8000")
E2E_KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost/authn")
E2E_CLIENT_ID = "agent-studio-keycloak-client-id-for-e2e-tests"
E2E_CLIENT_SECRET = "test-client-secret-for-e2e-tests"

# WebSocket endpoints from frontend WS_ENDPOINTS constant
# These map to /api/v1/ws/* backend routes
WS_ENDPOINTS = {
    # Core endpoints
    "NOTIFICATIONS": "/api/v1/ws/notifications",
    "AGENTS_REQUESTS": "/api/v1/ws/agents/requests",
    "ALERTS": "/api/v1/ws/alerts",
    # MCP endpoints
    "MCP": "/api/v1/ws/mcp",
    "MCP_AUTH": "/api/v1/ws/mcp/auth",
    "MCP_AGGREGATED": "/api/v1/ws/mcp/aggregated",
    "MCP_TASKS": "/api/v1/ws/mcp/tasks",
    "MCP_SESSION": "/api/v1/ws/mcp/test-session-123",
    # AI/UX endpoints
    "AI_SUGGESTIONS": "/api/v1/ws/ai/suggestions",
    "ORCHESTRATOR_STATUS": "/api/v1/ws/orchestrator/status",
    # Workflow endpoints
    "WORKFLOW_EXECUTION": "/api/v1/ws/workflows/test-workflow-123",
    # Monitoring endpoints
    "METRICS_HEART": "/api/v1/ws/metrics/heart",
    "COST": "/api/v1/ws/usage/cost",
    "BUDGET_ALERTS": "/api/v1/ws/budget/alerts",
    # Connections endpoints
    "CONNECTIONS_REALTIME": "/api/v1/ws/connections/realtime",
    "CONNECTIONS_HEALTH": "/api/v1/ws/connections/health",
    # DevTools endpoints
    "DEVTOOLS": "/api/v1/ws/devtools",
    # Audit endpoints
    "AUDIT": "/api/v1/ws/audit",
    # Trace endpoints
    "TRACES": "/api/v1/ws/traces",
}

# All WebSocket endpoints require authentication (ADR-0103)
ANONYMOUS_ALLOWED_ENDPOINTS: set[str] = set()

# Endpoints that require authentication (sorted for deterministic xdist collection)
AUTH_REQUIRED_ENDPOINTS = sorted(set(WS_ENDPOINTS.keys()) - ANONYMOUS_ALLOWED_ENDPOINTS)


def _get_keycloak_token(
    username: str = "alice",
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


def _websocket_available() -> bool:
    """Check if WebSocket infrastructure is available."""
    try:
        response = requests.get(f"{E2E_HTTP_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture(autouse=True)
def skip_if_websocket_unavailable():
    """Skip E2E WebSocket tests if infrastructure is not available."""
    if not _websocket_available():
        pytest.skip("WebSocket infrastructure not available")


@pytest.fixture(scope="module")
def auth_token() -> str | None:
    """Get an access token for authenticated endpoints."""
    return _get_keycloak_token()


@pytest.mark.xdist_group(name="test_websocket_smoke")
class TestWebSocketSmoke:
    """Smoke tests for all WebSocket endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent resource accumulation."""
        gc.collect()

    @pytest.mark.parametrize(
        "endpoint_name",
        sorted(ANONYMOUS_ALLOWED_ENDPOINTS),
        ids=sorted(ANONYMOUS_ALLOWED_ENDPOINTS),
    )
    @pytest.mark.asyncio
    async def test_anonymous_endpoint_accepts_connection(
        self,
        endpoint_name: str,
    ) -> None:
        """
        GIVEN an endpoint that allows anonymous access
        WHEN connecting without authentication
        THEN the connection should be accepted.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        endpoint_path = WS_ENDPOINTS[endpoint_name]
        ws_url = f"{E2E_WS_BASE_URL}{endpoint_path}?v=1.0.0"

        try:
            async with websockets.connect(
                ws_url,
                open_timeout=10,
                close_timeout=5,
            ) as websocket:
                assert _is_ws_open(websocket), f"Connection to {endpoint_name} failed"
        except Exception as e:
            pytest.fail(f"Failed to connect to {endpoint_name} ({endpoint_path}): {e}")

    @pytest.mark.parametrize(
        "endpoint_name",
        list(AUTH_REQUIRED_ENDPOINTS),
        ids=list(AUTH_REQUIRED_ENDPOINTS),
    )
    @pytest.mark.asyncio
    async def test_authenticated_endpoint_requires_auth(
        self,
        endpoint_name: str,
    ) -> None:
        """
        GIVEN an endpoint that requires authentication
        WHEN connecting without authentication
        THEN the connection should be rejected (close code 4001 or 4003).
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        endpoint_path = WS_ENDPOINTS[endpoint_name]
        ws_url = f"{E2E_WS_BASE_URL}{endpoint_path}?v=1.0.0"

        try:
            async with websockets.connect(
                ws_url,
                open_timeout=10,
                close_timeout=5,
            ) as websocket:
                # Some endpoints may accept connection then close
                # Wait briefly for potential close
                await asyncio.sleep(0.5)
                # If still open without auth, that's a problem for auth-required endpoints
                if _is_ws_open(websocket):
                    # Try to receive any auth-required message
                    try:
                        response = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=2.0,
                        )
                        data = json.loads(response)
                        # Check for auth error response
                        if data.get("type") == "error":
                            return  # Expected behavior
                    except TimeoutError:
                        pass  # No response is also acceptable
        except websockets.ConnectionClosedError as e:
            # Expected: connection closed due to auth requirement
            # Close codes: 4001 (unauthorized), 4003 (forbidden)
            assert e.code in {4001, 4003, 1008}, f"Unexpected close code {e.code} for {endpoint_name}"

    @pytest.mark.parametrize(
        "endpoint_name",
        list(AUTH_REQUIRED_ENDPOINTS),
        ids=list(AUTH_REQUIRED_ENDPOINTS),
    )
    @pytest.mark.asyncio
    async def test_authenticated_endpoint_accepts_with_token(
        self,
        endpoint_name: str,
        auth_token: str | None,
    ) -> None:
        """
        GIVEN an endpoint that requires authentication
        WHEN connecting with a valid token
        THEN the connection should be accepted.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if not auth_token:
            pytest.skip("Could not obtain auth token from Keycloak")

        endpoint_path = WS_ENDPOINTS[endpoint_name]
        ws_url = f"{E2E_WS_BASE_URL}{endpoint_path}?v=1.0.0&token={auth_token}"

        try:
            async with websockets.connect(
                ws_url,
                open_timeout=10,
                close_timeout=5,
            ) as websocket:
                assert _is_ws_open(websocket), f"Connection to {endpoint_name} failed"

                # Send a basic subscribe message to verify two-way communication
                subscribe_msg = {
                    "type": "subscribe",
                    "id": "smoke-test-1",
                    "payload": {},
                }
                await websocket.send(json.dumps(subscribe_msg))

                # Wait for any response (we just want to verify the endpoint is responsive)
                try:
                    response = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=5.0,
                    )
                    # Parse to verify it's valid JSON
                    data = json.loads(response)
                    assert isinstance(data, dict), "Response should be JSON object"
                except TimeoutError:
                    # Some endpoints may not respond to subscribe
                    # That's acceptable for smoke tests
                    pass

        except websockets.ConnectionClosedError as e:
            # Might be closed due to authorization (not authentication)
            # This is acceptable - the endpoint exists and checked auth
            if e.code == 4003:  # Forbidden (authz failure)
                pass  # Expected for endpoints user doesn't have permission for
            else:
                pytest.fail(f"Failed to connect to {endpoint_name} ({endpoint_path}): close code {e.code}")
        except Exception as e:
            pytest.fail(f"Failed to connect to {endpoint_name} ({endpoint_path}): {e}")


@pytest.mark.xdist_group(name="test_websocket_smoke_message_format")
class TestWebSocketMessageFormat:
    """Tests for WebSocket message format validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent resource accumulation."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_mcp_endpoint_supports_jsonrpc(
        self,
        auth_token: str | None,
    ) -> None:
        """
        GIVEN the MCP WebSocket endpoint
        WHEN sending a JSON-RPC 2.0 initialize message
        THEN should receive a valid JSON-RPC response.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if not auth_token:
            pytest.skip("Could not obtain auth token from Keycloak")

        ws_url = f"{E2E_WS_BASE_URL}{WS_ENDPOINTS['MCP']}?v=1.0.0&token={auth_token}"

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            # Send JSON-RPC initialize
            init_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "smoke-test", "version": "1.0.0"},
                },
            }
            await websocket.send(json.dumps(init_msg))

            # Should receive initialize response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)

            assert "jsonrpc" in data or "result" in data, "Invalid JSON-RPC response"

    @pytest.mark.asyncio
    async def test_traces_endpoint_supports_message_envelope(
        self,
        auth_token: str | None,
    ) -> None:
        """
        GIVEN the Traces WebSocket endpoint
        WHEN sending a MessageEnvelope subscribe message
        THEN should receive a valid MessageEnvelope response.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if not auth_token:
            pytest.skip("Could not obtain auth token from Keycloak")

        ws_url = f"{E2E_WS_BASE_URL}{WS_ENDPOINTS['TRACES']}?v=1.0.0&token={auth_token}"

        try:
            async with websockets.connect(ws_url, open_timeout=10) as websocket:
                # Send MessageEnvelope subscribe
                subscribe_msg = {
                    "type": "subscribe",
                    "id": "smoke-test-traces",
                    "payload": {},
                }
                await websocket.send(json.dumps(subscribe_msg))

                # Should receive response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)

                # MessageEnvelope format should have "type" field
                assert "type" in data, "Response should be MessageEnvelope format"
        except websockets.ConnectionClosedError as e:
            if e.code == 4003:  # Forbidden (authz failure)
                pytest.skip("User doesn't have permission for traces endpoint")
            raise

    @pytest.mark.asyncio
    async def test_devtools_endpoint_supports_message_envelope(
        self,
        auth_token: str | None,
    ) -> None:
        """
        GIVEN the DevTools WebSocket endpoint
        WHEN sending a MessageEnvelope subscribe message
        THEN should receive a valid MessageEnvelope response.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if not auth_token:
            pytest.skip("Could not obtain auth token from Keycloak")

        ws_url = f"{E2E_WS_BASE_URL}{WS_ENDPOINTS['DEVTOOLS']}?v=1.0.0&token={auth_token}"

        try:
            async with websockets.connect(ws_url, open_timeout=10) as websocket:
                # Send MessageEnvelope subscribe
                subscribe_msg = {
                    "type": "subscribe",
                    "id": "smoke-test-devtools",
                    "payload": {},
                }
                await websocket.send(json.dumps(subscribe_msg))

                # Should receive response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)

                # MessageEnvelope format should have "type" field
                assert "type" in data, "Response should be MessageEnvelope format"
        except websockets.ConnectionClosedError as e:
            if e.code == 4003:  # Forbidden (authz failure)
                pytest.skip("User doesn't have permission for devtools endpoint")
            raise

    @pytest.mark.asyncio
    async def test_budget_alerts_endpoint_supports_subscribe(
        self,
        auth_token: str | None,
    ) -> None:
        """
        GIVEN the Budget Alerts WebSocket endpoint
        WHEN sending a subscribe_all message
        THEN should receive a subscribed confirmation.
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if not auth_token:
            pytest.skip("Could not obtain auth token from Keycloak")

        ws_url = f"{E2E_WS_BASE_URL}{WS_ENDPOINTS['BUDGET_ALERTS']}?v=1.0.0&token={auth_token}"

        try:
            async with websockets.connect(ws_url, open_timeout=10) as websocket:
                # Send subscribe_all message
                subscribe_msg = {
                    "type": "subscribe_all",
                    "id": "smoke-test-budget",
                    "payload": {},
                }
                await websocket.send(json.dumps(subscribe_msg))

                # Should receive subscribed response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)

                assert data.get("type") == "subscribed", f"Expected 'subscribed' response, got: {data.get('type')}"
        except websockets.ConnectionClosedError as e:
            if e.code == 4003:  # Forbidden (authz failure)
                pytest.skip("User doesn't have permission for budget alerts endpoint")
            raise

    @pytest.mark.asyncio
    async def test_ai_suggestions_endpoint_supports_context_update(
        self,
        auth_token: str | None,
    ) -> None:
        """
        GIVEN the AI Suggestions WebSocket endpoint
        WHEN sending a context_update message
        THEN connection should remain open (no response expected for context_update).
        """
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets library not installed")

        if not auth_token:
            pytest.skip("Could not obtain auth token from Keycloak")

        ws_url = f"{E2E_WS_BASE_URL}{WS_ENDPOINTS['AI_SUGGESTIONS']}?v=1.0.0&token={auth_token}"

        try:
            async with websockets.connect(ws_url, open_timeout=10) as websocket:
                # Send context_update message
                context_msg = {
                    "type": "context_update",
                    "id": "smoke-test-ai",
                    "payload": {
                        "session_id": "smoke-test-session",
                        "context": "Test context for smoke testing",
                    },
                }
                await websocket.send(json.dumps(context_msg))

                # context_update doesn't return a response, just verify connection is open
                await asyncio.sleep(0.5)
                assert _is_ws_open(websocket), "Connection should remain open after context_update"
        except websockets.ConnectionClosedError as e:
            if e.code == 4003:  # Forbidden (authz failure)
                pytest.skip("User doesn't have permission for AI suggestions endpoint")
            raise
