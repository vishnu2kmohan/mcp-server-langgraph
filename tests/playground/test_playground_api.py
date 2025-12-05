"""
Playground API Tests (TDD Red Phase)

Tests for the Interactive Playground FastAPI server endpoints.
Following TDD: These tests are written BEFORE the implementation.

Test Coverage:
- Health check endpoint
- Session CRUD operations
- Chat message handling
- Authentication integration
"""

import gc
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

# Mark all tests in this module for xdist memory safety
pytestmark = [
    pytest.mark.unit,
    pytest.mark.playground,
    pytest.mark.xdist_group(name="playground_api"),
]


class TestPlaygroundHealth:
    """Tests for playground health check endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_health_check_returns_200(self, mock_redis, app_with_mock_manager) -> None:
        """Health check endpoint should return 200 OK."""
        # Mock Redis ping for health check
        mock_redis.ping = AsyncMock()

        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.get("/api/playground/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Status may be healthy or degraded depending on mock behavior
        assert data["status"] in ["healthy", "degraded"]
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health_check_includes_dependencies(self, app_with_mock_manager) -> None:
        """Health check should report status of dependencies (Redis, MCP server)."""
        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.get("/api/playground/health")

        data = response.json()
        assert "dependencies" in data
        assert "redis" in data["dependencies"]
        assert "mcp_server" in data["dependencies"]


class TestPlaygroundSessionCRUD:
    """Tests for session management endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_session_returns_201(self, app_with_mock_manager) -> None:
        """POST /api/playground/sessions should create a new session."""
        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.post(
                "/api/playground/sessions",
                json={"name": "Test Session"},
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Session"
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_session_requires_auth(self, app_with_mock_manager) -> None:
        """Session creation should require authentication."""
        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.post(
                "/api/playground/sessions",
                json={"name": "Test Session"},
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_list_sessions_returns_user_sessions(self, app_with_mock_manager) -> None:
        """GET /api/playground/sessions should return sessions for authenticated user."""
        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.get(
                "/api/playground/sessions",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    @pytest.mark.asyncio
    async def test_get_session_by_id(self, app_with_mock_manager) -> None:
        """GET /api/playground/sessions/{id} should return session details."""
        session_id = "test-session-123"

        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.get(
                f"/api/playground/sessions/{session_id}",
                headers={"Authorization": "Bearer test-token"},
            )

        # Expect 200 since mock returns a session
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_delete_session(self, app_with_mock_manager) -> None:
        """DELETE /api/playground/sessions/{id} should delete a session."""
        session_id = "test-session-123"

        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.delete(
                f"/api/playground/sessions/{session_id}",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestPlaygroundChat:
    """Tests for chat/message endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_send_chat_message(self, app_with_mock_manager) -> None:
        """POST /api/playground/chat should send a message and return response."""
        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.post(
                "/api/playground/chat",
                json={
                    "session_id": "test-session-123",
                    "message": "Hello, agent!",
                },
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "response" in data or "message_id" in data

    @pytest.mark.asyncio
    async def test_chat_requires_session_id(self, app_with_mock_manager) -> None:
        """Chat endpoint should require a valid session_id."""
        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.post(
                "/api/playground/chat",
                json={"message": "Hello!"},  # Missing session_id
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_chat_validates_message_length(self, app_with_mock_manager) -> None:
        """Chat should reject messages that are too long."""
        # 100KB message should be rejected
        long_message = "x" * 100_000

        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.post(
                "/api/playground/chat",
                json={
                    "session_id": "test-session-123",
                    "message": long_message,
                },
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestPlaygroundAPIInfo:
    """Tests for API info/root endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_root_endpoint_returns_api_info(self, app_with_mock_manager) -> None:
        """Root endpoint should return API information."""
        async with AsyncClient(transport=ASGITransport(app=app_with_mock_manager), base_url="http://test") as client:
            response = await client.get("/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "name" in data
        assert "playground" in data["name"].lower()
        assert "version" in data
        assert "docs_url" in data
