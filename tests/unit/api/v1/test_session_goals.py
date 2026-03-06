"""
Session Goals Router Unit Tests

Tests for session goal tracking endpoints per TDD methodology:
- POST /api/v1/sessions/{session_id}/goal
- POST /api/v1/sessions/{session_id}/goal/complete

Tests written FIRST before full implementation (RED phase).

Reference: docs-internal/frontend/PENDING-BACKEND-APIS.md
"""

import gc
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


pytestmark = [
    pytest.mark.unit,
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
def mock_audit_repository() -> MagicMock:
    """Mock audit log repository for testing."""
    repo = MagicMock()
    repo.log_event = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_goal_repository() -> MagicMock:
    """Mock goal repository for testing."""
    from mcp_server_langgraph.repositories.session_goal import SessionGoalRepository

    repo = MagicMock(spec=SessionGoalRepository)

    # Dynamic mock that echoes back input values
    async def mock_create_goal(session_id: str, user_id: str, goal: str, set_at: int) -> dict:
        return {
            "id": "goal-test-123",
            "session_id": session_id,
            "user_id": user_id,
            "goal": goal,
            "set_at": set_at,
            "achieved": None,
            "feedback": None,
            "completed_at": None,
        }

    async def mock_complete_goal(
        session_id: str,
        user_id: str,
        goal: str,
        achieved: Any,
        completed_at: int,
        feedback: str | None = None,
    ) -> dict:
        return {
            "id": "goal-test-123",
            "session_id": session_id,
            "user_id": user_id,
            "goal": goal,
            "achieved": achieved,
            "feedback": feedback,
            "set_at": completed_at - 3600000,  # Simulate 1 hour before completion
            "completed_at": completed_at,
        }

    repo.create_goal = AsyncMock(side_effect=mock_create_goal)
    repo.complete_goal = AsyncMock(side_effect=mock_complete_goal)
    repo.get_goals_by_session = AsyncMock(return_value=[])
    repo.count_goals_by_session = AsyncMock(return_value=0)

    return repo


@pytest.fixture
def test_app(
    mock_user: dict[str, Any],
    mock_goal_repository: MagicMock,
    mock_audit_repository: MagicMock,
) -> Generator[FastAPI, None, None]:
    """Create a test app with the sessions router and mock authentication."""
    from mcp_server_langgraph.api.v1.sessions import sessions_router
    from mcp_server_langgraph.auth.middleware import get_current_user
    from mcp_server_langgraph.core.dependencies import (
        get_audit_log_repository,
        get_session_goal_repository,
    )

    app = FastAPI()
    app.include_router(sessions_router, prefix="/api/v1")

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_session_goal_repository] = lambda: mock_goal_repository
    app.dependency_overrides[get_audit_log_repository] = lambda: mock_audit_repository

    yield app

    app.dependency_overrides.clear()


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)


@pytest.fixture
def sample_session(mock_user: dict[str, Any]) -> dict[str, Any]:
    """Sample session data for testing."""
    return {
        "id": str(uuid4()),
        "name": "Test Chat Session",
        "user_id": mock_user["sub"],
        "workflow_id": str(uuid4()),
        "messages": [],
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "status": "active",
    }


class TestSetSessionGoalEndpoint:
    """Tests for POST /api/v1/sessions/{session_id}/goal endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_set_goal_returns_201(self, client: TestClient, sample_session: dict[str, Any]) -> None:
        """
        GIVEN a request to set a session goal
        WHEN POST request is made with valid goal data
        THEN response should be 201 Created
        """
        session_id = sample_session["id"]
        timestamp = 1705123456789

        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)
            mock_service.get_session.return_value = MagicMock(**sample_session)
            mock_get_service.return_value = mock_service

            response = client.post(
                f"/api/v1/sessions/{session_id}/goal",
                json={"goal": "Complete the data analysis", "set_at": timestamp},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["session_id"] == session_id
            assert data["goal"] == "Complete the data analysis"
            assert data["set_at"] == timestamp

    def test_set_goal_returns_404_for_nonexistent_session(self, client: TestClient) -> None:
        """
        GIVEN a request to set a goal for non-existent session
        WHEN POST request is made
        THEN response should be 404 Not Found
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)
            mock_service.get_session.return_value = None
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/sessions/nonexistent-session/goal",
                json={"goal": "Test goal", "set_at": 1705123456789},
            )

            assert response.status_code == 404

    def test_set_goal_validates_goal_length(self, client: TestClient) -> None:
        """
        GIVEN a request to set a goal with empty goal text
        WHEN POST request is made
        THEN response should be 422 Unprocessable Entity
        """
        response = client.post(
            "/api/v1/sessions/session-123/goal",
            json={"goal": "", "set_at": 1705123456789},
        )

        assert response.status_code == 422

    def test_set_goal_requires_set_at_timestamp(self, client: TestClient) -> None:
        """
        GIVEN a request to set a goal without set_at timestamp
        WHEN POST request is made
        THEN response should be 422 Unprocessable Entity
        """
        response = client.post(
            "/api/v1/sessions/session-123/goal",
            json={"goal": "Valid goal text"},  # Missing set_at
        )

        assert response.status_code == 422

    def test_set_goal_response_structure(self, client: TestClient, sample_session: dict[str, Any]) -> None:
        """
        GIVEN a request to set a session goal
        WHEN POST request is made successfully
        THEN response should have correct structure
        """
        session_id = sample_session["id"]

        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)
            mock_service.get_session.return_value = MagicMock(**sample_session)
            mock_get_service.return_value = mock_service

            response = client.post(
                f"/api/v1/sessions/{session_id}/goal",
                json={"goal": "Test goal", "set_at": 1705123456789},
            )

            assert response.status_code == 201
            data = response.json()
            assert "session_id" in data
            assert "goal" in data
            assert "set_at" in data


class TestCompleteSessionGoalEndpoint:
    """Tests for POST /api/v1/sessions/{session_id}/goal/complete endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_complete_goal_returns_200(self, client: TestClient, sample_session: dict[str, Any]) -> None:
        """
        GIVEN a request to complete a session goal
        WHEN POST request is made with valid completion data
        THEN response should be 200 OK
        """
        session_id = sample_session["id"]
        completed_at = 1705127056789

        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)
            mock_service.get_session.return_value = MagicMock(**sample_session)
            mock_get_service.return_value = mock_service

            response = client.post(
                f"/api/v1/sessions/{session_id}/goal/complete",
                json={
                    "goal": "Complete the data analysis",
                    "achieved": True,
                    "completed_at": completed_at,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == session_id
            assert data["achieved"] is True
            assert data["completed_at"] == completed_at

    def test_complete_goal_with_partial_achievement(self, client: TestClient, sample_session: dict[str, Any]) -> None:
        """
        GIVEN a request to complete a goal with partial achievement
        WHEN POST request is made with achieved="partial"
        THEN response should include partial status
        """
        session_id = sample_session["id"]

        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)
            mock_service.get_session.return_value = MagicMock(**sample_session)
            mock_get_service.return_value = mock_service

            response = client.post(
                f"/api/v1/sessions/{session_id}/goal/complete",
                json={
                    "goal": "Complete all features",
                    "achieved": "partial",
                    "feedback": "Completed 80% of planned features",
                    "completed_at": 1705127056789,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["achieved"] == "partial"
            assert data["feedback"] == "Completed 80% of planned features"

    def test_complete_goal_with_false_achievement(self, client: TestClient, sample_session: dict[str, Any]) -> None:
        """
        GIVEN a request to complete a goal that was not achieved
        WHEN POST request is made with achieved=false
        THEN response should include false status
        """
        session_id = sample_session["id"]

        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)
            mock_service.get_session.return_value = MagicMock(**sample_session)
            mock_get_service.return_value = mock_service

            response = client.post(
                f"/api/v1/sessions/{session_id}/goal/complete",
                json={
                    "goal": "Impossible task",
                    "achieved": False,
                    "feedback": "Blocked by dependencies",
                    "completed_at": 1705127056789,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["achieved"] is False
            assert data["feedback"] == "Blocked by dependencies"

    def test_complete_goal_returns_404_for_nonexistent_session(self, client: TestClient) -> None:
        """
        GIVEN a request to complete a goal for non-existent session
        WHEN POST request is made
        THEN response should be 404 Not Found
        """
        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)
            mock_service.get_session.return_value = None
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/sessions/nonexistent-session/goal/complete",
                json={
                    "goal": "Test goal",
                    "achieved": True,
                    "completed_at": 1705127056789,
                },
            )

            assert response.status_code == 404

    def test_complete_goal_response_structure(self, client: TestClient, sample_session: dict[str, Any]) -> None:
        """
        GIVEN a request to complete a session goal
        WHEN POST request is made successfully
        THEN response should have correct structure
        """
        session_id = sample_session["id"]

        with patch("mcp_server_langgraph.api.v1.sessions.get_session_service") as mock_get_service:
            mock_service = AsyncMock(return_value=None)
            mock_service.get_session.return_value = MagicMock(**sample_session)
            mock_get_service.return_value = mock_service

            response = client.post(
                f"/api/v1/sessions/{session_id}/goal/complete",
                json={
                    "goal": "Test goal",
                    "achieved": True,
                    "completed_at": 1705127056789,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "session_id" in data
            assert "goal" in data
            assert "achieved" in data
            assert "set_at" in data
            assert "completed_at" in data


class TestSessionGoalModels:
    """Tests for session goal Pydantic models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_set_goal_request_model(self) -> None:
        """
        GIVEN a SetGoalRequest model
        WHEN creating with valid data
        THEN should validate successfully
        """
        from mcp_server_langgraph.api.v1.sessions import SetGoalRequest

        request = SetGoalRequest(goal="Complete the analysis", set_at=1705123456789)
        assert request.goal == "Complete the analysis"
        assert request.set_at == 1705123456789

    def test_set_goal_request_validates_min_length(self) -> None:
        """
        GIVEN a SetGoalRequest model
        WHEN creating with empty goal
        THEN should raise validation error
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.api.v1.sessions import SetGoalRequest

        with pytest.raises(ValidationError):
            SetGoalRequest(goal="", set_at=1705123456789)

    def test_set_goal_response_model(self) -> None:
        """
        GIVEN a SetGoalResponse model
        WHEN creating with valid data
        THEN should validate successfully
        """
        from mcp_server_langgraph.api.v1.sessions import SetGoalResponse

        response = SetGoalResponse(
            session_id="session-123",
            goal="Test goal",
            set_at=1705123456789,
        )
        assert response.session_id == "session-123"
        assert response.goal == "Test goal"
        assert response.set_at == 1705123456789

    def test_complete_goal_request_model(self) -> None:
        """
        GIVEN a CompleteGoalRequest model
        WHEN creating with valid data
        THEN should validate successfully
        """
        from mcp_server_langgraph.api.v1.sessions import CompleteGoalRequest

        request = CompleteGoalRequest(
            goal="Test goal",
            achieved=True,
            feedback="All done!",
            completed_at=1705127056789,
        )
        assert request.goal == "Test goal"
        assert request.achieved is True
        assert request.feedback == "All done!"
        assert request.completed_at == 1705127056789

    def test_complete_goal_request_partial_achievement(self) -> None:
        """
        GIVEN a CompleteGoalRequest model
        WHEN creating with achieved="partial"
        THEN should validate successfully
        """
        from mcp_server_langgraph.api.v1.sessions import CompleteGoalRequest

        request = CompleteGoalRequest(
            goal="Test goal",
            achieved="partial",
            completed_at=1705127056789,
        )
        assert request.achieved == "partial"

    def test_complete_goal_response_model(self) -> None:
        """
        GIVEN a CompleteGoalResponse model
        WHEN creating with valid data
        THEN should validate successfully
        """
        from mcp_server_langgraph.api.v1.sessions import CompleteGoalResponse

        response = CompleteGoalResponse(
            session_id="session-123",
            goal="Test goal",
            achieved=True,
            feedback="Completed!",
            set_at=1705123456789,
            completed_at=1705127056789,
        )
        assert response.session_id == "session-123"
        assert response.achieved is True
        assert response.feedback == "Completed!"
        assert response.set_at == 1705123456789
        assert response.completed_at == 1705127056789
