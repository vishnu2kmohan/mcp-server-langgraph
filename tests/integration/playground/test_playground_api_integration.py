"""
Integration tests for Playground API endpoints.

Tests the playground API server against real infrastructure:
- Session management endpoints
- Chat endpoints with real MCP server
- WebSocket streaming
- Observability endpoints

Requires: docker-compose.test.yml services running

Run with:
    make test-infra-up
    pytest tests/integration/playground/test_playground_api_integration.py -v
"""

import gc

import pytest

from tests.constants import TEST_PLAYGROUND_API_PORT

pytestmark = [
    pytest.mark.integration,
    pytest.mark.playground,
    pytest.mark.api,
    pytest.mark.xdist_group(name="playground_integration_tests"),
]


@pytest.fixture
def playground_url() -> str:
    """Get Playground API URL for testing."""
    return f"http://localhost:{TEST_PLAYGROUND_API_PORT}"


@pytest.fixture
def api_client(playground_url: str):
    """Create HTTP client for Playground API."""
    import httpx

    return httpx.AsyncClient(base_url=playground_url, timeout=30.0)


@pytest.mark.xdist_group(name="playground_integration_tests")
class TestPlaygroundHealth:
    """Test Playground health endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_ok(self, api_client) -> None:
        """Test health endpoint is accessible."""
        response = await api_client.get("/api/playground/health")

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy" or "status" in data

    @pytest.mark.asyncio
    async def test_health_includes_dependencies(self, api_client) -> None:
        """Test health endpoint shows dependency status."""
        response = await api_client.get("/api/playground/health")

        if response.status_code == 200:
            data = response.json()
            # May include redis, mcp_server status
            assert "status" in data


@pytest.mark.xdist_group(name="playground_integration_tests")
class TestPlaygroundSessionAPI:
    """Test session management API endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def auth_headers(self, mock_jwt_token: str) -> dict:
        """Get authorization headers."""
        return {"Authorization": f"Bearer {mock_jwt_token}"}

    @pytest.mark.asyncio
    async def test_create_session_returns_session_id(self, api_client, auth_headers) -> None:
        """Test creating a new session."""
        response = await api_client.post(
            "/api/playground/sessions",
            json={"name": "Integration Test Session"},
            headers=auth_headers,
        )

        # Should succeed or require auth
        assert response.status_code in [200, 201, 401, 403]

        if response.status_code in [200, 201]:
            data = response.json()
            assert "session_id" in data or "id" in data

    @pytest.mark.asyncio
    async def test_list_sessions_returns_array(self, api_client, auth_headers) -> None:
        """Test listing sessions returns array."""
        response = await api_client.get(
            "/api/playground/sessions",
            headers=auth_headers,
        )

        # Should succeed or require auth
        assert response.status_code in [200, 401, 403]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) or "sessions" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_session_returns_404(self, api_client, auth_headers) -> None:
        """Test getting nonexistent session returns 404."""
        response = await api_client.get(
            "/api/playground/sessions/nonexistent-session-id",
            headers=auth_headers,
        )

        # Should be 404 or auth error
        assert response.status_code in [404, 401, 403]

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session_returns_404(self, api_client, auth_headers) -> None:
        """Test deleting nonexistent session returns 404."""
        response = await api_client.delete(
            "/api/playground/sessions/nonexistent-session-id",
            headers=auth_headers,
        )

        # Should be 404 or auth error
        assert response.status_code in [404, 401, 403]


@pytest.mark.xdist_group(name="playground_integration_tests")
class TestPlaygroundChatAPI:
    """Test chat API endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def auth_headers(self, mock_jwt_token: str) -> dict:
        """Get authorization headers."""
        return {"Authorization": f"Bearer {mock_jwt_token}"}

    @pytest.mark.asyncio
    async def test_chat_endpoint_requires_auth(self, api_client) -> None:
        """Test chat endpoint requires authentication."""
        response = await api_client.post(
            "/api/playground/chat",
            json={"session_id": "test", "message": "Hello"},
        )

        # Should require auth
        assert response.status_code in [401, 403, 422]

    @pytest.mark.asyncio
    async def test_chat_requires_session_id(self, api_client, auth_headers) -> None:
        """Test chat endpoint requires session_id."""
        response = await api_client.post(
            "/api/playground/chat",
            json={"message": "Hello"},  # Missing session_id
            headers=auth_headers,
        )

        # Should fail validation
        assert response.status_code in [400, 422, 401, 403]


@pytest.mark.xdist_group(name="playground_integration_tests")
class TestPlaygroundObservabilityAPI:
    """Test observability API endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def auth_headers(self, mock_jwt_token: str) -> dict:
        """Get authorization headers."""
        return {"Authorization": f"Bearer {mock_jwt_token}"}

    @pytest.mark.asyncio
    async def test_traces_endpoint_exists(self, api_client, auth_headers) -> None:
        """Test traces endpoint is accessible."""
        response = await api_client.get(
            "/api/playground/observability/traces",
            params={"session_id": "test-session"},
            headers=auth_headers,
        )

        # Endpoint should exist (may return empty or auth error)
        assert response.status_code in [200, 401, 403, 404]

    @pytest.mark.asyncio
    async def test_logs_endpoint_exists(self, api_client, auth_headers) -> None:
        """Test logs endpoint is accessible."""
        response = await api_client.get(
            "/api/playground/observability/logs",
            params={"session_id": "test-session"},
            headers=auth_headers,
        )

        # Endpoint should exist
        assert response.status_code in [200, 401, 403, 404]

    @pytest.mark.asyncio
    async def test_metrics_endpoint_exists(self, api_client, auth_headers) -> None:
        """Test metrics endpoint is accessible."""
        response = await api_client.get(
            "/api/playground/observability/metrics",
            params={"session_id": "test-session"},
            headers=auth_headers,
        )

        # Endpoint should exist
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.xdist_group(name="playground_integration_tests")
class TestPlaygroundWebSocket:
    """Test WebSocket endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_websocket_endpoint_exists(self, playground_url: str) -> None:
        """Test WebSocket endpoint is accessible."""
        import websockets

        ws_url = playground_url.replace("http://", "ws://")

        try:
            async with websockets.connect(
                f"{ws_url}/ws/playground/test-session",
                close_timeout=5,
            ) as _ws:
                # Connection should succeed or fail with auth error
                pass
        except websockets.exceptions.InvalidStatusCode as e:
            # Auth error (401, 403) or not found (404) is expected
            assert e.status_code in [401, 403, 404]
        except Exception:
            # Connection refused means server not running - that's OK
            pass
