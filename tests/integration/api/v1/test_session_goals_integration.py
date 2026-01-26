"""
Session Goals Integration Tests

Integration tests for session goal persistence with real database.
Tests the full flow from API to database and back.

Reference: docs-internal/frontend/PENDING-BACKEND-APIS.md
"""

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

pytestmark = [
    pytest.mark.integration,
    pytest.mark.api,
]


@pytest.fixture
def mock_user() -> dict[str, Any]:
    """Mock authenticated user for testing."""
    return {
        "sub": "test-user-123",
        "preferred_username": "testuser",
        "email": "testuser@example.com",
        "roles": ["user"],
    }


@pytest.fixture
def mock_session(mock_user: dict[str, Any]) -> dict[str, Any]:
    """Sample session data for testing."""
    return {
        "id": str(uuid4()),
        "name": "Integration Test Session",
        "user_id": mock_user["sub"],
        "workflow_id": str(uuid4()),
        "messages": [],
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "status": "active",
    }


@pytest.fixture
async def integration_app(mock_user: dict[str, Any]) -> FastAPI:
    """Create a test app with sessions router and mock auth."""
    from mcp_server_langgraph.api.v1.sessions import sessions_router
    from mcp_server_langgraph.auth.middleware import get_current_user

    app = FastAPI()
    app.include_router(sessions_router, prefix="/api/v1")

    async def override_get_current_user() -> dict[str, Any]:
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    yield app

    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(integration_app: FastAPI) -> AsyncClient:
    """Create an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=integration_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.xdist_group(name="test_session_goals_integration")
class TestSessionGoalIntegration:
    """Integration tests for session goal API endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_full_goal_lifecycle(
        self,
        async_client: AsyncClient,
        mock_session: dict[str, Any],
    ) -> None:
        """
        GIVEN a valid session
        WHEN a goal is set and then completed
        THEN the full lifecycle should work correctly
        """
        session_id = mock_session["id"]
        set_at = 1705123456789
        completed_at = 1705127056789

        with patch(
            "mcp_server_langgraph.api.v1.sessions.get_session_service"
        ) as mock_get_service:
            mock_service = AsyncMock(return_value=None)
            mock_service.get_session.return_value = MagicMock(**mock_session)
            mock_get_service.return_value = mock_service

            # Step 1: Set the goal
            set_response = await async_client.post(
                f"/api/v1/sessions/{session_id}/goal",
                json={
                    "goal": "Complete the integration test",
                    "set_at": set_at,
                },
            )

            assert set_response.status_code == 201
            set_data = set_response.json()
            assert set_data["session_id"] == session_id
            assert set_data["goal"] == "Complete the integration test"
            assert set_data["set_at"] == set_at

            # Step 2: Complete the goal
            complete_response = await async_client.post(
                f"/api/v1/sessions/{session_id}/goal/complete",
                json={
                    "goal": "Complete the integration test",
                    "achieved": True,
                    "feedback": "All tests passed!",
                    "completed_at": completed_at,
                },
            )

            assert complete_response.status_code == 200
            complete_data = complete_response.json()
            assert complete_data["session_id"] == session_id
            assert complete_data["achieved"] is True
            assert complete_data["feedback"] == "All tests passed!"
            assert complete_data["completed_at"] == completed_at

    @pytest.mark.asyncio
    async def test_goal_with_partial_achievement(
        self,
        async_client: AsyncClient,
        mock_session: dict[str, Any],
    ) -> None:
        """
        GIVEN a valid session with a goal
        WHEN the goal is completed with partial achievement
        THEN the response should reflect partial status
        """
        session_id = mock_session["id"]

        with patch(
            "mcp_server_langgraph.api.v1.sessions.get_session_service"
        ) as mock_get_service:
            mock_service = AsyncMock(return_value=None)
            mock_service.get_session.return_value = MagicMock(**mock_session)
            mock_get_service.return_value = mock_service

            # Set goal
            await async_client.post(
                f"/api/v1/sessions/{session_id}/goal",
                json={"goal": "Implement all features", "set_at": 1705123456789},
            )

            # Complete with partial
            response = await async_client.post(
                f"/api/v1/sessions/{session_id}/goal/complete",
                json={
                    "goal": "Implement all features",
                    "achieved": "partial",
                    "feedback": "Completed 80% of planned work",
                    "completed_at": 1705127056789,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["achieved"] == "partial"
            assert data["feedback"] == "Completed 80% of planned work"

    @pytest.mark.asyncio
    async def test_goal_not_achieved(
        self,
        async_client: AsyncClient,
        mock_session: dict[str, Any],
    ) -> None:
        """
        GIVEN a valid session with a goal
        WHEN the goal is marked as not achieved
        THEN the response should reflect false status
        """
        session_id = mock_session["id"]

        with patch(
            "mcp_server_langgraph.api.v1.sessions.get_session_service"
        ) as mock_get_service:
            mock_service = AsyncMock(return_value=None)
            mock_service.get_session.return_value = MagicMock(**mock_session)
            mock_get_service.return_value = mock_service

            # Set goal
            await async_client.post(
                f"/api/v1/sessions/{session_id}/goal",
                json={"goal": "Fix the impossible bug", "set_at": 1705123456789},
            )

            # Complete with not achieved
            response = await async_client.post(
                f"/api/v1/sessions/{session_id}/goal/complete",
                json={
                    "goal": "Fix the impossible bug",
                    "achieved": False,
                    "feedback": "Blocked by external factors",
                    "completed_at": 1705127056789,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["achieved"] is False
            assert data["feedback"] == "Blocked by external factors"

    @pytest.mark.asyncio
    async def test_set_goal_nonexistent_session(
        self,
        async_client: AsyncClient,
    ) -> None:
        """
        GIVEN a non-existent session ID
        WHEN attempting to set a goal
        THEN the response should be 404 Not Found
        """
        with patch(
            "mcp_server_langgraph.api.v1.sessions.get_session_service"
        ) as mock_get_service:
            mock_service = AsyncMock(return_value=None)
            mock_service.get_session.return_value = None
            mock_get_service.return_value = mock_service

            response = await async_client.post(
                "/api/v1/sessions/nonexistent-session-id/goal",
                json={"goal": "Test goal", "set_at": 1705123456789},
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_complete_goal_nonexistent_session(
        self,
        async_client: AsyncClient,
    ) -> None:
        """
        GIVEN a non-existent session ID
        WHEN attempting to complete a goal
        THEN the response should be 404 Not Found
        """
        with patch(
            "mcp_server_langgraph.api.v1.sessions.get_session_service"
        ) as mock_get_service:
            mock_service = AsyncMock(return_value=None)
            mock_service.get_session.return_value = None
            mock_get_service.return_value = mock_service

            response = await async_client.post(
                "/api/v1/sessions/nonexistent-session-id/goal/complete",
                json={
                    "goal": "Test goal",
                    "achieved": True,
                    "completed_at": 1705127056789,
                },
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_set_goal_validation_empty_goal(
        self,
        async_client: AsyncClient,
    ) -> None:
        """
        GIVEN a request with an empty goal
        WHEN attempting to set the goal
        THEN the response should be 422 Unprocessable Entity
        """
        response = await async_client.post(
            "/api/v1/sessions/some-session-id/goal",
            json={"goal": "", "set_at": 1705123456789},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_set_goal_validation_missing_timestamp(
        self,
        async_client: AsyncClient,
    ) -> None:
        """
        GIVEN a request missing the set_at timestamp
        WHEN attempting to set the goal
        THEN the response should be 422 Unprocessable Entity
        """
        response = await async_client.post(
            "/api/v1/sessions/some-session-id/goal",
            json={"goal": "Valid goal text"},  # Missing set_at
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_multiple_goals_same_session(
        self,
        async_client: AsyncClient,
        mock_session: dict[str, Any],
    ) -> None:
        """
        GIVEN a valid session
        WHEN multiple goals are set and completed
        THEN all operations should succeed independently
        """
        session_id = mock_session["id"]

        with patch(
            "mcp_server_langgraph.api.v1.sessions.get_session_service"
        ) as mock_get_service:
            mock_service = AsyncMock(return_value=None)
            mock_service.get_session.return_value = MagicMock(**mock_session)
            mock_get_service.return_value = mock_service

            # Set and complete first goal
            response1 = await async_client.post(
                f"/api/v1/sessions/{session_id}/goal",
                json={"goal": "First goal", "set_at": 1705123456789},
            )
            assert response1.status_code == 201

            complete1 = await async_client.post(
                f"/api/v1/sessions/{session_id}/goal/complete",
                json={
                    "goal": "First goal",
                    "achieved": True,
                    "completed_at": 1705127056789,
                },
            )
            assert complete1.status_code == 200

            # Set and complete second goal
            response2 = await async_client.post(
                f"/api/v1/sessions/{session_id}/goal",
                json={"goal": "Second goal", "set_at": 1705130656789},
            )
            assert response2.status_code == 201

            complete2 = await async_client.post(
                f"/api/v1/sessions/{session_id}/goal/complete",
                json={
                    "goal": "Second goal",
                    "achieved": "partial",
                    "feedback": "Partially done",
                    "completed_at": 1705134256789,
                },
            )
            assert complete2.status_code == 200
            assert complete2.json()["achieved"] == "partial"
