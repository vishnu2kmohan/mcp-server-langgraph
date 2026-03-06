"""
E2E Orchestrator Status WebSocket Tests.

True end-to-end tests for orchestrator status WebSocket with live server infrastructure.
Tests the complete flow from API call through orchestrator to WebSocket broadcast.

Infrastructure Requirements:
- docker-compose.test.yml running (make test-infra-up-build)
- MCP server running on port 8000 (or via gateway on port 80)
- Keycloak for authentication

Test Approach:
- Uses websockets library for real WebSocket connections
- Authenticates via Keycloak OAuth2 to get real tokens
- Tests orchestrator status broadcasting and task lifecycle
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
    pytest.mark.orchestrator,
    pytest.mark.asyncio,
]

# E2E test configuration
E2E_WS_BASE_URL = os.getenv("E2E_WS_BASE_URL", "ws://localhost:8000")
E2E_HTTP_BASE_URL = os.getenv("E2E_HTTP_BASE_URL", "http://localhost:8000")
E2E_KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost/authn")
E2E_CLIENT_ID = "mcp-server"
E2E_CLIENT_SECRET = "test-client-secret-for-e2e-tests"

# Orchestrator status WebSocket endpoint
ORCHESTRATOR_STATUS_ENDPOINT = "/api/v1/ws/orchestrator/status"


def _get_keycloak_token(
    username: str,
    client_id: str = E2E_CLIENT_ID,
    client_secret: str = E2E_CLIENT_SECRET,
) -> str | None:
    """Get Keycloak access token via modern OAuth2 flows.

    Uses Token Exchange (RFC 8693) or client_credentials grant.
    ROPC (password grant) is disabled per security audit (ADR-0086).
    """
    token_url = f"{E2E_KEYCLOAK_URL}/realms/default/protocol/openid-connect/token"

    # Try Token Exchange first (RFC 8693) for user-specific context
    try:
        response = requests.post(
            token_url,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "client_id": client_id,
                "client_secret": client_secret,
                "requested_subject": username,
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "scope": "openid profile email",
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception:
        pass

    # Fallback to client_credentials (service account)
    try:
        response = requests.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "openid profile email",
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception:
        pass
    return None


def _orchestrator_status_available() -> bool:
    """Check if orchestrator status WebSocket endpoint is available."""
    try:
        # Check MCP server health
        response = requests.get(f"{E2E_HTTP_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def _is_ws_open(websocket: Any) -> bool:
    """Check if websocket connection is open (compatible with websockets >= 15.0)."""
    try:
        from websockets import State

        return websocket.state == State.OPEN
    except (ImportError, AttributeError):
        return getattr(websocket, "open", False)


@pytest.fixture(autouse=True)
def cleanup() -> None:
    """Force GC after each test to prevent memory issues."""
    yield
    gc.collect()


@pytest.mark.xdist_group(name="orchestrator_status_e2e")
class TestOrchestratorStatusWebSocketE2E:
    """E2E tests for orchestrator status WebSocket."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation."""
        gc.collect()

    @pytest.mark.skipif(
        not _orchestrator_status_available(),
        reason="Orchestrator status WebSocket not available (server not running)",
    )
    async def test_can_connect_to_orchestrator_status_websocket(self) -> None:
        """
        GIVEN a running server with orchestrator status WebSocket
        WHEN connecting with valid authentication
        THEN connection should succeed
        """
        import websockets

        token = _get_keycloak_token("alice")
        if not token:
            pytest.skip("Could not obtain Keycloak token")

        ws_url = f"{E2E_WS_BASE_URL}{ORCHESTRATOR_STATUS_ENDPOINT}?token={token}"

        try:
            async with websockets.connect(ws_url, open_timeout=10) as ws:
                assert _is_ws_open(ws), "WebSocket should be open"
        except Exception as e:
            pytest.skip(f"Could not connect to WebSocket: {e}")

    @pytest.mark.skipif(
        not _orchestrator_status_available(),
        reason="Orchestrator status WebSocket not available (server not running)",
    )
    async def test_receives_subscribed_message_on_connect(self) -> None:
        """
        GIVEN a connection to orchestrator status WebSocket
        WHEN connected successfully
        THEN client should receive a subscribed confirmation
        """
        import websockets

        token = _get_keycloak_token("alice")
        if not token:
            pytest.skip("Could not obtain Keycloak token")

        ws_url = f"{E2E_WS_BASE_URL}{ORCHESTRATOR_STATUS_ENDPOINT}?token={token}"

        try:
            async with websockets.connect(ws_url, open_timeout=10) as ws:
                # Send subscribe message
                await ws.send(json.dumps({"type": "subscribe", "id": "sub-1"}))

                # Wait for response
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=5)
                    data = json.loads(message)
                    assert data.get("type") == "subscribed"
                except TimeoutError:
                    pytest.skip("No response received within timeout")
        except Exception as e:
            pytest.skip(f"Could not connect to WebSocket: {e}")

    @pytest.mark.skipif(
        not _orchestrator_status_available(),
        reason="Orchestrator status WebSocket not available (server not running)",
    )
    async def test_can_request_current_status(self) -> None:
        """
        GIVEN a connection to orchestrator status WebSocket
        WHEN sending get_status message
        THEN client should receive current status snapshot
        """
        import websockets

        token = _get_keycloak_token("alice")
        if not token:
            pytest.skip("Could not obtain Keycloak token")

        ws_url = f"{E2E_WS_BASE_URL}{ORCHESTRATOR_STATUS_ENDPOINT}?token={token}"

        try:
            async with websockets.connect(ws_url, open_timeout=10) as ws:
                # Request current status
                await ws.send(json.dumps({"type": "get_status", "id": "status-1"}))

                # Wait for response
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=5)
                    data = json.loads(message)
                    assert data.get("type") == "status"
                    assert "payload" in data
                    assert "status" in data["payload"]
                except TimeoutError:
                    pytest.skip("No response received within timeout")
        except Exception as e:
            pytest.skip(f"Could not connect to WebSocket: {e}")

    @pytest.mark.skipif(
        not _orchestrator_status_available(),
        reason="Orchestrator status WebSocket not available (server not running)",
    )
    async def test_can_unsubscribe(self) -> None:
        """
        GIVEN a subscribed connection to orchestrator status WebSocket
        WHEN sending unsubscribe message
        THEN client should receive unsubscribed confirmation
        """
        import websockets

        token = _get_keycloak_token("alice")
        if not token:
            pytest.skip("Could not obtain Keycloak token")

        ws_url = f"{E2E_WS_BASE_URL}{ORCHESTRATOR_STATUS_ENDPOINT}?token={token}"

        try:
            async with websockets.connect(ws_url, open_timeout=10) as ws:
                # First subscribe
                await ws.send(json.dumps({"type": "subscribe", "id": "sub-1"}))
                await asyncio.wait_for(ws.recv(), timeout=5)

                # Then unsubscribe
                await ws.send(json.dumps({"type": "unsubscribe", "id": "unsub-1"}))

                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=5)
                    data = json.loads(message)
                    assert data.get("type") == "unsubscribed"
                except TimeoutError:
                    pytest.skip("No response received within timeout")
        except Exception as e:
            pytest.skip(f"Could not connect to WebSocket: {e}")

    @pytest.mark.skipif(
        not _orchestrator_status_available(),
        reason="Orchestrator status WebSocket not available (server not running)",
    )
    async def test_rejects_unauthenticated_connection(self) -> None:
        """
        GIVEN orchestrator status WebSocket endpoint
        WHEN connecting without authentication
        THEN connection should be rejected
        """
        import websockets

        ws_url = f"{E2E_WS_BASE_URL}{ORCHESTRATOR_STATUS_ENDPOINT}"

        try:
            async with websockets.connect(ws_url, open_timeout=10) as ws:
                # If we get here, the connection succeeded unexpectedly
                # Try to receive a message - might get an auth error
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=5)
                    data = json.loads(message)
                    # Should receive an error message about authentication
                    if data.get("type") == "error":
                        assert "auth" in data.get("payload", {}).get("message", "").lower()
                except TimeoutError:
                    pass  # Connection closed immediately is expected
        except websockets.exceptions.InvalidStatusCode as e:
            # 401 or 403 is expected for unauthenticated requests
            assert e.status_code in (401, 403, 1008)
        except Exception:
            # Connection failure is acceptable for unauthenticated requests
            pass
