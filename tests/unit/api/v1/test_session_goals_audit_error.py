"""
Tests for Session Goal Endpoints - Audit Logging and Error Handling.

TDD: Tests verify audit logging and error handling behavior.
"""

import gc
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from mcp_server_langgraph.api.v1.sessions import sessions_router
from mcp_server_langgraph.repositories.session_goal import SessionGoalRepository


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


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
    """Mock goal repository with successful responses."""
    repo = MagicMock(spec=SessionGoalRepository)

    repo.create_goal = AsyncMock(
        return_value={
            "id": "goal-uuid-123",
            "session_id": "session-123",
            "user_id": "test-user-123",
            "goal": "Test goal",
            "set_at": 1705123456789,
            "achieved": None,
            "feedback": None,
            "completed_at": None,
        }
    )

    repo.complete_goal = AsyncMock(
        return_value={
            "id": "goal-uuid-123",
            "session_id": "session-123",
            "user_id": "test-user-123",
            "goal": "Test goal",
            "achieved": True,
            "feedback": "Done",
            "set_at": 1705123456789,
            "completed_at": 1705127056789,
        }
    )

    repo.get_goals_by_session = AsyncMock(return_value=[])
    repo.count_goals_by_session = AsyncMock(return_value=0)

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
        get_session_goal_repository,
        get_audit_log_repository,
    )

    app = FastAPI()
    app.include_router(sessions_router, prefix="/api/v1")

    # Override dependencies
    async def _override_current_user():
        return mock_current_user

    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[get_session_goal_repository] = lambda: mock_goal_repository
    app.dependency_overrides[get_audit_log_repository] = lambda: mock_audit_repository

    # Set mock session service
    sessions_module.set_session_service(mock_session_service)

    yield app

    sessions_module._session_service = None


# =============================================================================
# Audit Logging Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_session_goals_audit")
class TestSetGoalAuditLogging:
    """Tests for audit logging on set_session_goal endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_set_goal_logs_audit_event(
        self,
        app: FastAPI,
        mock_audit_repository: MagicMock,
    ) -> None:
        """Verify set_goal logs an audit event."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/sessions/session-123/goal",
                json={
                    "goal": "Complete the analysis",
                    "set_at": 1705123456789,
                },
            )

        assert response.status_code == 201

        # Verify audit log was called
        mock_audit_repository.log_event.assert_called_once()

        # Verify audit event details
        call_kwargs = mock_audit_repository.log_event.call_args.kwargs
        assert call_kwargs["event_type"] == "session_goal.created"
        assert call_kwargs["resource_type"] == "session_goal"
        assert call_kwargs["action"] == "create"
        assert call_kwargs["actor_id"] == "test-user-123"


@pytest.mark.xdist_group(name="test_session_goals_audit")
class TestCompleteGoalAuditLogging:
    """Tests for audit logging on complete_session_goal endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_complete_goal_logs_audit_event(
        self,
        app: FastAPI,
        mock_audit_repository: MagicMock,
    ) -> None:
        """Verify complete_goal logs an audit event."""
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

        # Verify audit log was called
        mock_audit_repository.log_event.assert_called_once()

        # Verify audit event details
        call_kwargs = mock_audit_repository.log_event.call_args.kwargs
        assert call_kwargs["event_type"] == "session_goal.completed"
        assert call_kwargs["resource_type"] == "session_goal"
        assert call_kwargs["action"] == "complete"
        assert "achieved" in call_kwargs["details"]


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.xdist_group(name="test_session_goals_errors")
class TestSetGoalErrorHandling:
    """Tests for error handling on set_session_goal endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_set_goal_handles_repository_error(
        self,
        app: FastAPI,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify set_goal returns 500 on repository error."""
        mock_goal_repository.create_goal = AsyncMock(side_effect=Exception("Database connection failed"))

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/sessions/session-123/goal",
                json={
                    "goal": "Test goal",
                    "set_at": 1705123456789,
                },
            )

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data


@pytest.mark.xdist_group(name="test_session_goals_errors")
class TestCompleteGoalErrorHandling:
    """Tests for error handling on complete_session_goal endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_complete_goal_handles_repository_error(
        self,
        app: FastAPI,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify complete_goal returns 500 on repository error."""
        mock_goal_repository.complete_goal = AsyncMock(side_effect=Exception("Database connection failed"))

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/sessions/session-123/goal/complete",
                json={
                    "goal": "Test goal",
                    "achieved": True,
                    "completed_at": 1705127056789,
                },
            )

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data


@pytest.mark.xdist_group(name="test_session_goals_errors")
class TestGetHistoryErrorHandling:
    """Tests for error handling on get_session_goal_history endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_history_handles_repository_error(
        self,
        app: FastAPI,
        mock_goal_repository: MagicMock,
    ) -> None:
        """Verify get_history returns 500 on repository error."""
        mock_goal_repository.get_goals_by_session = AsyncMock(side_effect=Exception("Database connection failed"))

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/sessions/session-123/goals")

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
