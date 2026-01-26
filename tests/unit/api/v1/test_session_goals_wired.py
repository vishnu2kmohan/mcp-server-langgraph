"""
Tests for Wired Session Goal Endpoints.

TDD: Tests verify that endpoints properly use the repository for persistence.
These tests mock the repository to test endpoint behavior in isolation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from mcp_server_langgraph.api.v1.sessions import sessions_router
from mcp_server_langgraph.repositories.session_goal import SessionGoalRepository

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_current_user() -> dict:
    """Mock authenticated user."""
    return {
        "sub": "test-user-123",
        "preferred_username": "testuser",
        "email": "test@example.com",
    }


@pytest.fixture
def mock_session_service() -> MagicMock:
    """Mock session service for ownership checks."""
    service = MagicMock()
    service.get_session = AsyncMock(
        return_value={
            "id": "session-123",
            "name": "Test Session",
            "user_id": "test-user-123",
            "messages": [],
        }
    )
    return service


@pytest.fixture
def mock_goal_repository() -> MagicMock:
    """Mock goal repository."""
    repo = MagicMock(spec=SessionGoalRepository)
    return repo


@pytest.fixture
def mock_audit_repository() -> MagicMock:
    """Mock audit log repository."""
    repo = MagicMock()
    repo.log_event = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def app(
    mock_current_user: dict,
    mock_session_service: MagicMock,
    mock_goal_repository: MagicMock,
    mock_audit_repository: MagicMock,
) -> FastAPI:
    """Create FastAPI app with mocked dependencies."""
    from mcp_server_langgraph.auth.middleware import get_current_user
    from mcp_server_langgraph.api.v1 import sessions as sessions_module
    from mcp_server_langgraph.core.dependencies import (
        get_audit_log_repository,
        get_session_goal_repository,
    )

    app = FastAPI()
    app.include_router(sessions_router, prefix="/api/v1")

    # Override FastAPI dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    app.dependency_overrides[get_session_goal_repository] = lambda: mock_goal_repository
    app.dependency_overrides[get_audit_log_repository] = lambda: mock_audit_repository

    # Set the session service singleton (not a FastAPI dependency)
    sessions_module.set_session_service(mock_session_service)

    yield app

    # Clean up after test
    sessions_module._session_service = None


@pytest.mark.unit
class TestSetGoalEndpointWithRepository:
    """Tests for POST /sessions/{session_id}/goal with repository wiring."""

    @pytest.mark.asyncio
    async def test_set_goal_calls_repository_create(
        self,
        app: FastAPI,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify set_goal endpoint calls repository.create_goal."""
        # Setup mock return value
        mock_goal_repository.create_goal = AsyncMock(
            return_value={
                "id": "goal-uuid-123",
                "session_id": "session-123",
                "user_id": "test-user-123",
                "goal": "Complete the analysis",
                "set_at": 1705123456789,
                "achieved": None,
                "feedback": None,
                "completed_at": None,
            }
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/sessions/session-123/goal",
                json={
                    "goal": "Complete the analysis",
                    "set_at": 1705123456789,
                },
            )

        assert response.status_code == 201

        # Verify repository was called with correct arguments
        mock_goal_repository.create_goal.assert_called_once_with(
            session_id="session-123",
            user_id="test-user-123",
            goal="Complete the analysis",
            set_at=1705123456789,
        )

    @pytest.mark.asyncio
    async def test_set_goal_returns_repository_data(
        self,
        app: FastAPI,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify endpoint returns data from repository."""
        mock_goal_repository.create_goal = AsyncMock(
            return_value={
                "id": "goal-uuid-123",
                "session_id": "session-123",
                "user_id": "test-user-123",
                "goal": "Finish project",
                "set_at": 1705123456789,
                "achieved": None,
                "feedback": None,
                "completed_at": None,
            }
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/sessions/session-123/goal",
                json={
                    "goal": "Finish project",
                    "set_at": 1705123456789,
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["session_id"] == "session-123"
        assert data["goal"] == "Finish project"
        assert data["set_at"] == 1705123456789


@pytest.mark.unit
class TestCompleteGoalEndpointWithRepository:
    """Tests for POST /sessions/{session_id}/goal/complete with repository wiring."""

    @pytest.mark.asyncio
    async def test_complete_goal_calls_repository(
        self,
        app: FastAPI,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify complete_goal endpoint calls repository.complete_goal."""
        mock_goal_repository.complete_goal = AsyncMock(
            return_value={
                "id": "goal-uuid-123",
                "session_id": "session-123",
                "user_id": "test-user-123",
                "goal": "Complete the analysis",
                "achieved": True,
                "feedback": "Done successfully",
                "set_at": 1705123456789,
                "completed_at": 1705127056789,
            }
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/sessions/session-123/goal/complete",
                json={
                    "goal": "Complete the analysis",
                    "achieved": True,
                    "feedback": "Done successfully",
                    "completed_at": 1705127056789,
                },
            )

        assert response.status_code == 200

        # Verify repository was called
        mock_goal_repository.complete_goal.assert_called_once()
        call_args = mock_goal_repository.complete_goal.call_args
        assert call_args.kwargs["session_id"] == "session-123"
        assert call_args.kwargs["user_id"] == "test-user-123"
        assert call_args.kwargs["goal"] == "Complete the analysis"
        assert call_args.kwargs["achieved"] is True
        assert call_args.kwargs["feedback"] == "Done successfully"

    @pytest.mark.asyncio
    async def test_complete_goal_with_partial_achievement(
        self,
        app: FastAPI,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify partial achievement is passed to repository."""
        mock_goal_repository.complete_goal = AsyncMock(
            return_value={
                "id": "goal-uuid-123",
                "session_id": "session-123",
                "user_id": "test-user-123",
                "goal": "Complete 80%",
                "achieved": "partial",
                "feedback": "Almost done",
                "set_at": 1705123456789,
                "completed_at": 1705127056789,
            }
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/sessions/session-123/goal/complete",
                json={
                    "goal": "Complete 80%",
                    "achieved": "partial",
                    "feedback": "Almost done",
                    "completed_at": 1705127056789,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["achieved"] == "partial"

    @pytest.mark.asyncio
    async def test_complete_goal_returns_set_at_from_repository(
        self,
        app: FastAPI,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify set_at comes from repository (not stub calculation)."""
        actual_set_at = 1705100000000  # Different from stub calculation

        mock_goal_repository.complete_goal = AsyncMock(
            return_value={
                "id": "goal-uuid-123",
                "session_id": "session-123",
                "user_id": "test-user-123",
                "goal": "Test goal",
                "achieved": True,
                "feedback": None,
                "set_at": actual_set_at,  # This should be returned
                "completed_at": 1705127056789,
            }
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/sessions/session-123/goal/complete",
                json={
                    "goal": "Test goal",
                    "achieved": True,
                    "completed_at": 1705127056789,
                },
            )

        assert response.status_code == 200
        data = response.json()
        # Should use repository's set_at, not stub calculation
        assert data["set_at"] == actual_set_at


@pytest.mark.unit
class TestGetGoalHistoryEndpointWithRepository:
    """Tests for GET /sessions/{session_id}/goals with repository wiring."""

    @pytest.mark.asyncio
    async def test_get_history_calls_repository(
        self,
        app: FastAPI,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify get_goal_history endpoint calls repository."""
        mock_goal_repository.get_goals_by_session = AsyncMock(
            return_value=[
                {
                    "id": "goal-1",
                    "session_id": "session-123",
                    "user_id": "test-user-123",
                    "goal": "First goal",
                    "achieved": True,
                    "feedback": "Done",
                    "set_at": 1705100000000,
                    "completed_at": 1705103600000,
                },
                {
                    "id": "goal-2",
                    "session_id": "session-123",
                    "user_id": "test-user-123",
                    "goal": "Second goal",
                    "achieved": "partial",
                    "feedback": None,
                    "set_at": 1705110000000,
                    "completed_at": 1705113600000,
                },
            ]
        )
        mock_goal_repository.count_goals_by_session = AsyncMock(return_value=2)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/sessions/session-123/goals?limit=10&offset=0")

        assert response.status_code == 200

        # Verify repository was called with correct pagination
        mock_goal_repository.get_goals_by_session.assert_called_once_with(
            session_id="session-123",
            user_id="test-user-123",
            limit=10,
            offset=0,
        )
        mock_goal_repository.count_goals_by_session.assert_called_once_with(
            session_id="session-123",
            user_id="test-user-123",
        )

    @pytest.mark.asyncio
    async def test_get_history_returns_goals_from_repository(
        self,
        app: FastAPI,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify endpoint returns goals from repository."""
        mock_goal_repository.get_goals_by_session = AsyncMock(
            return_value=[
                {
                    "id": "goal-1",
                    "session_id": "session-123",
                    "user_id": "test-user-123",
                    "goal": "Test goal",
                    "achieved": True,
                    "feedback": "Great work",
                    "set_at": 1705100000000,
                    "completed_at": 1705103600000,
                },
            ]
        )
        mock_goal_repository.count_goals_by_session = AsyncMock(return_value=1)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/sessions/session-123/goals")

        assert response.status_code == 200
        data = response.json()

        assert data["session_id"] == "session-123"
        assert len(data["goals"]) == 1
        assert data["goals"][0]["id"] == "goal-1"
        assert data["goals"][0]["goal"] == "Test goal"
        assert data["goals"][0]["achieved"] is True
        assert data["goals"][0]["feedback"] == "Great work"

    @pytest.mark.asyncio
    async def test_get_history_returns_total_count(
        self,
        app: FastAPI,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify endpoint returns total count of goals (not just page size)."""
        # Return 2 goals (paginated) but total is 10
        goals = [
            {
                "id": f"goal-{i}",
                "session_id": "session-123",
                "user_id": "test-user-123",
                "goal": f"Goal {i}",
                "achieved": True,
                "feedback": None,
                "set_at": 1705100000000 + i * 1000,
                "completed_at": 1705103600000 + i * 1000,
            }
            for i in range(2)
        ]
        mock_goal_repository.get_goals_by_session = AsyncMock(return_value=goals)
        mock_goal_repository.count_goals_by_session = AsyncMock(return_value=10)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/sessions/session-123/goals?limit=2")

        assert response.status_code == 200
        data = response.json()

        # Total should be 10 (from count), not 2 (from page)
        assert data["total"] == 10
        assert len(data["goals"]) == 2

    @pytest.mark.asyncio
    async def test_get_history_empty_session(
        self,
        app: FastAPI,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify endpoint handles empty goal history."""
        mock_goal_repository.get_goals_by_session = AsyncMock(return_value=[])
        mock_goal_repository.count_goals_by_session = AsyncMock(return_value=0)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/sessions/session-123/goals")

        assert response.status_code == 200
        data = response.json()

        assert data["goals"] == []
        assert data["total"] == 0


@pytest.mark.unit
class TestSessionOwnershipValidation:
    """Tests for session ownership validation before repository calls."""

    @pytest.mark.asyncio
    async def test_set_goal_404_for_nonexistent_session(
        self,
        app: FastAPI,
        mock_session_service: MagicMock,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify 404 is returned if session doesn't exist."""
        mock_session_service.get_session = AsyncMock(return_value=None)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/sessions/nonexistent/goal",
                json={
                    "goal": "Test goal",
                    "set_at": 1705123456789,
                },
            )

        assert response.status_code == 404

        # Repository should NOT be called
        mock_goal_repository.create_goal.assert_not_called()

    @pytest.mark.asyncio
    async def test_complete_goal_404_for_nonexistent_session(
        self,
        app: FastAPI,
        mock_session_service: MagicMock,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify 404 is returned if session doesn't exist for complete."""
        mock_session_service.get_session = AsyncMock(return_value=None)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/sessions/nonexistent/goal/complete",
                json={
                    "goal": "Test goal",
                    "achieved": True,
                    "completed_at": 1705127056789,
                },
            )

        assert response.status_code == 404

        # Repository should NOT be called
        mock_goal_repository.complete_goal.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_history_404_for_nonexistent_session(
        self,
        app: FastAPI,
        mock_session_service: MagicMock,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify 404 is returned if session doesn't exist for history."""
        mock_session_service.get_session = AsyncMock(return_value=None)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/sessions/nonexistent/goals")

        assert response.status_code == 404

        # Repository should NOT be called
        mock_goal_repository.get_goals_by_session.assert_not_called()


@pytest.mark.unit
class TestGetCurrentGoalEndpoint:
    """Tests for GET /sessions/{session_id}/goal/current endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_goal_returns_200(
        self,
        app: FastAPI,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify get_current_goal returns 200 with current goal."""
        mock_goal_repository.get_current_goal = AsyncMock(
            return_value={
                "id": "goal-123",
                "session_id": "session-123",
                "user_id": "test-user-123",
                "goal": "Current active goal",
                "achieved": None,
                "feedback": None,
                "set_at": 1705123456789,
                "completed_at": None,
            }
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/sessions/session-123/goal/current")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "session-123"
        assert data["goal"]["id"] == "goal-123"
        assert data["goal"]["goal"] == "Current active goal"
        assert data["goal"]["achieved"] is None
        assert data["goal"]["completed_at"] is None

    @pytest.mark.asyncio
    async def test_get_current_goal_calls_repository(
        self,
        app: FastAPI,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify get_current_goal calls repository with correct params."""
        mock_goal_repository.get_current_goal = AsyncMock(return_value=None)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.get("/api/v1/sessions/session-123/goal/current")

        mock_goal_repository.get_current_goal.assert_called_once_with(
            session_id="session-123",
            user_id="test-user-123",
        )

    @pytest.mark.asyncio
    async def test_get_current_goal_returns_null_when_no_current(
        self,
        app: FastAPI,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify get_current_goal returns null goal when none active."""
        mock_goal_repository.get_current_goal = AsyncMock(return_value=None)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/sessions/session-123/goal/current")

        assert response.status_code == 200
        data = response.json()
        assert data["goal"] is None

    @pytest.mark.asyncio
    async def test_get_current_goal_404_for_nonexistent_session(
        self,
        app: FastAPI,
        mock_session_service: MagicMock,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify 404 is returned if session doesn't exist."""
        mock_session_service.get_session = AsyncMock(return_value=None)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/sessions/nonexistent/goal/current")

        assert response.status_code == 404
        mock_goal_repository.get_current_goal.assert_not_called()


@pytest.mark.unit
class TestDeleteGoalEndpoint:
    """Tests for DELETE /sessions/{session_id}/goals/{goal_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_goal_returns_204(
        self,
        app: FastAPI,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify delete_goal returns 204 No Content on success."""
        mock_goal_repository.delete_goal = AsyncMock(return_value=True)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete("/api/v1/sessions/session-123/goals/goal-456")

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_goal_calls_repository(
        self,
        app: FastAPI,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify delete_goal calls repository with correct params."""
        mock_goal_repository.delete_goal = AsyncMock(return_value=True)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.delete("/api/v1/sessions/session-123/goals/goal-456")

        mock_goal_repository.delete_goal.assert_called_once_with(
            goal_id="goal-456",
            user_id="test-user-123",
        )

    @pytest.mark.asyncio
    async def test_delete_goal_returns_404_when_not_found(
        self,
        app: FastAPI,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify delete_goal returns 404 when goal not found."""
        mock_goal_repository.delete_goal = AsyncMock(return_value=False)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete("/api/v1/sessions/session-123/goals/nonexistent")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_goal_404_for_nonexistent_session(
        self,
        app: FastAPI,
        mock_session_service: MagicMock,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify 404 is returned if session doesn't exist."""
        mock_session_service.get_session = AsyncMock(return_value=None)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete("/api/v1/sessions/nonexistent/goals/goal-456")

        assert response.status_code == 404
        mock_goal_repository.delete_goal.assert_not_called()
