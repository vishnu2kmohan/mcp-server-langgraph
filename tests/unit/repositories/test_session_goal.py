"""
Session Goal Repository Unit Tests

TDD tests for SessionGoalRepository - written FIRST before implementation.

Reference: docs-internal/frontend/PENDING-BACKEND-APIS.md
"""

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest


pytestmark = [
    pytest.mark.unit,
    pytest.mark.repository,
]


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock async database session."""
    session = AsyncMock(return_value=None)
    session.add = MagicMock()
    session.flush = AsyncMock(return_value=None)
    session.commit = AsyncMock(return_value=None)
    session.rollback = AsyncMock(return_value=None)
    session.execute = AsyncMock(return_value=None)
    session.scalar = AsyncMock(return_value=None)
    session.scalars = AsyncMock(return_value=None)
    return session


@pytest.fixture
def sample_goal_data() -> dict[str, Any]:
    """Sample goal data for testing."""
    return {
        "session_id": str(uuid4()),
        "user_id": "test-user-123",
        "goal": "Complete the integration test",
        "set_at": 1705123456789,
    }


@pytest.fixture
def sample_completed_goal_data(sample_goal_data: dict[str, Any]) -> dict[str, Any]:
    """Sample completed goal data."""
    return {
        **sample_goal_data,
        "achieved": True,
        "feedback": "All tests passed!",
        "completed_at": 1705127056789,
    }


class TestSessionGoalRepository:
    """Tests for SessionGoalRepository."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_repository_initialization_creates_connection(self, mock_session: AsyncMock) -> None:
        """
        GIVEN a database session
        WHEN creating a SessionGoalRepository
        THEN it should initialize correctly
        """
        from mcp_server_langgraph.repositories.session_goal import (
            PostgresSessionGoalRepository,
        )

        repo = PostgresSessionGoalRepository(mock_session)
        assert repo._session is mock_session

    @pytest.mark.asyncio
    async def test_create_goal(
        self,
        mock_session: AsyncMock,
        sample_goal_data: dict[str, Any],
    ) -> None:
        """
        GIVEN valid goal data
        WHEN create_goal is called
        THEN it should persist the goal and return it
        """
        from mcp_server_langgraph.repositories.session_goal import (
            PostgresSessionGoalRepository,
        )

        repo = PostgresSessionGoalRepository(mock_session)

        result = await repo.create_goal(
            session_id=sample_goal_data["session_id"],
            user_id=sample_goal_data["user_id"],
            goal=sample_goal_data["goal"],
            set_at=sample_goal_data["set_at"],
        )

        assert result["session_id"] == sample_goal_data["session_id"]
        assert result["goal"] == sample_goal_data["goal"]
        assert result["set_at"] == sample_goal_data["set_at"]
        assert "id" in result
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_complete_goal(
        self,
        mock_session: AsyncMock,
        sample_completed_goal_data: dict[str, Any],
    ) -> None:
        """
        GIVEN an existing goal
        WHEN complete_goal is called
        THEN it should update the goal with completion data
        """
        from mcp_server_langgraph.repositories.session_goal import (
            PostgresSessionGoalRepository,
        )

        # Mock finding the goal
        mock_goal = MagicMock()
        mock_goal.id = uuid4()
        mock_goal.session_id = sample_completed_goal_data["session_id"]
        mock_goal.goal = sample_completed_goal_data["goal"]
        mock_goal.set_at = sample_completed_goal_data["set_at"]
        mock_session.scalar.return_value = mock_goal

        repo = PostgresSessionGoalRepository(mock_session)

        result = await repo.complete_goal(
            session_id=sample_completed_goal_data["session_id"],
            user_id=sample_completed_goal_data["user_id"],
            goal=sample_completed_goal_data["goal"],
            achieved=sample_completed_goal_data["achieved"],
            feedback=sample_completed_goal_data["feedback"],
            completed_at=sample_completed_goal_data["completed_at"],
        )

        assert result["achieved"] == sample_completed_goal_data["achieved"]
        assert result["feedback"] == sample_completed_goal_data["feedback"]
        assert result["completed_at"] == sample_completed_goal_data["completed_at"]

    @pytest.mark.asyncio
    async def test_complete_goal_partial(
        self,
        mock_session: AsyncMock,
        sample_goal_data: dict[str, Any],
    ) -> None:
        """
        GIVEN an existing goal
        WHEN complete_goal is called with achieved='partial'
        THEN it should update with partial achievement
        """
        from mcp_server_langgraph.repositories.session_goal import (
            PostgresSessionGoalRepository,
        )

        mock_goal = MagicMock()
        mock_goal.id = uuid4()
        mock_goal.session_id = sample_goal_data["session_id"]
        mock_goal.goal = sample_goal_data["goal"]
        mock_goal.set_at = sample_goal_data["set_at"]
        mock_session.scalar.return_value = mock_goal

        repo = PostgresSessionGoalRepository(mock_session)

        result = await repo.complete_goal(
            session_id=sample_goal_data["session_id"],
            user_id=sample_goal_data["user_id"],
            goal=sample_goal_data["goal"],
            achieved="partial",
            feedback="Completed 80%",
            completed_at=1705127056789,
        )

        assert result["achieved"] == "partial"

    @pytest.mark.asyncio
    async def test_get_goals_by_session(
        self,
        mock_session: AsyncMock,
        sample_completed_goal_data: dict[str, Any],
    ) -> None:
        """
        GIVEN a session with goals
        WHEN get_goals_by_session is called
        THEN it should return all goals for that session
        """
        from mcp_server_langgraph.repositories.session_goal import (
            PostgresSessionGoalRepository,
        )

        # Mock goals
        mock_goal1 = MagicMock()
        mock_goal1.id = uuid4()
        mock_goal1.session_id = sample_completed_goal_data["session_id"]
        mock_goal1.goal = "First goal"
        mock_goal1.achieved = "true"
        mock_goal1.feedback = "Done"
        mock_goal1.set_at = 1705123456789
        mock_goal1.completed_at = 1705127056789

        mock_goal2 = MagicMock()
        mock_goal2.id = uuid4()
        mock_goal2.session_id = sample_completed_goal_data["session_id"]
        mock_goal2.goal = "Second goal"
        mock_goal2.achieved = "partial"
        mock_goal2.feedback = "Mostly done"
        mock_goal2.set_at = 1705130656789
        mock_goal2.completed_at = 1705134256789

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_goal1, mock_goal2]
        mock_session.scalars.return_value = mock_result

        repo = PostgresSessionGoalRepository(mock_session)

        results = await repo.get_goals_by_session(
            session_id=sample_completed_goal_data["session_id"],
            user_id=sample_completed_goal_data["user_id"],
        )

        assert len(results) == 2
        assert results[0]["goal"] == "First goal"
        assert results[1]["goal"] == "Second goal"

    @pytest.mark.asyncio
    async def test_get_goals_empty_session(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """
        GIVEN a session with no goals
        WHEN get_goals_by_session is called
        THEN it should return an empty list
        """
        from mcp_server_langgraph.repositories.session_goal import (
            PostgresSessionGoalRepository,
        )

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.scalars.return_value = mock_result

        repo = PostgresSessionGoalRepository(mock_session)

        results = await repo.get_goals_by_session(
            session_id=str(uuid4()),
            user_id="test-user",
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_get_current_goal(
        self,
        mock_session: AsyncMock,
        sample_goal_data: dict[str, Any],
    ) -> None:
        """
        GIVEN a session with an incomplete goal
        WHEN get_current_goal is called
        THEN it should return the incomplete goal
        """
        from mcp_server_langgraph.repositories.session_goal import (
            PostgresSessionGoalRepository,
        )

        mock_goal = MagicMock()
        mock_goal.id = uuid4()
        mock_goal.session_id = sample_goal_data["session_id"]
        mock_goal.goal = sample_goal_data["goal"]
        mock_goal.achieved = None
        mock_goal.feedback = None
        mock_goal.set_at = sample_goal_data["set_at"]
        mock_goal.completed_at = None
        mock_session.scalar.return_value = mock_goal

        repo = PostgresSessionGoalRepository(mock_session)

        result = await repo.get_current_goal(
            session_id=sample_goal_data["session_id"],
            user_id=sample_goal_data["user_id"],
        )

        assert result is not None
        assert result["goal"] == sample_goal_data["goal"]
        assert result["completed_at"] is None

    @pytest.mark.asyncio
    async def test_get_current_goal_none(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """
        GIVEN a session with no current goal
        WHEN get_current_goal is called
        THEN it should return None
        """
        from mcp_server_langgraph.repositories.session_goal import (
            PostgresSessionGoalRepository,
        )

        mock_session.scalar.return_value = None

        repo = PostgresSessionGoalRepository(mock_session)

        result = await repo.get_current_goal(
            session_id=str(uuid4()),
            user_id="test-user",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_goal(
        self,
        mock_session: AsyncMock,
        sample_goal_data: dict[str, Any],
    ) -> None:
        """
        GIVEN an existing goal
        WHEN delete_goal is called
        THEN it should delete the goal
        """
        from mcp_server_langgraph.repositories.session_goal import (
            PostgresSessionGoalRepository,
        )

        goal_id = uuid4()
        mock_goal = MagicMock()
        mock_goal.id = goal_id
        mock_session.scalar.return_value = mock_goal
        mock_session.delete = AsyncMock(return_value=None)

        repo = PostgresSessionGoalRepository(mock_session)

        result = await repo.delete_goal(
            goal_id=str(goal_id),
            user_id=sample_goal_data["user_id"],
        )

        assert result is True
        mock_session.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_goal_not_found(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """
        GIVEN a non-existent goal
        WHEN delete_goal is called
        THEN it should return False
        """
        from mcp_server_langgraph.repositories.session_goal import (
            PostgresSessionGoalRepository,
        )

        mock_session.scalar.return_value = None

        repo = PostgresSessionGoalRepository(mock_session)

        result = await repo.delete_goal(
            goal_id=str(uuid4()),
            user_id="test-user",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_count_goals_by_session(
        self,
        mock_session: AsyncMock,
        sample_goal_data: dict[str, Any],
    ) -> None:
        """
        GIVEN a session with goals
        WHEN count_goals_by_session is called
        THEN it should return the count of goals
        """
        from mcp_server_langgraph.repositories.session_goal import (
            PostgresSessionGoalRepository,
        )

        mock_session.scalar.return_value = 5

        repo = PostgresSessionGoalRepository(mock_session)

        count = await repo.count_goals_by_session(
            session_id=sample_goal_data["session_id"],
            user_id=sample_goal_data["user_id"],
        )

        assert count == 5

    @pytest.mark.asyncio
    async def test_count_goals_empty_session(
        self,
        mock_session: AsyncMock,
    ) -> None:
        """
        GIVEN a session with no goals
        WHEN count_goals_by_session is called
        THEN it should return 0
        """
        from mcp_server_langgraph.repositories.session_goal import (
            PostgresSessionGoalRepository,
        )

        mock_session.scalar.return_value = 0

        repo = PostgresSessionGoalRepository(mock_session)

        count = await repo.count_goals_by_session(
            session_id=str(uuid4()),
            user_id="test-user",
        )

        assert count == 0


class TestSessionGoalModel:
    """Tests for SessionGoal SQLAlchemy model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_creation_sets_fields(self) -> None:
        """
        GIVEN valid session goal data
        WHEN creating a SessionGoal model
        THEN it should create successfully
        """
        from mcp_server_langgraph.models.session_goal import SessionGoal

        goal = SessionGoal(
            session_id="session-123",
            user_id="user-456",
            goal="Complete the task",
            set_at=1705123456789,
        )

        assert goal.session_id == "session-123"
        assert goal.user_id == "user-456"
        assert goal.goal == "Complete the task"
        assert goal.set_at == 1705123456789

    def test_model_with_completion(self) -> None:
        """
        GIVEN completed goal data
        WHEN creating a SessionGoal model
        THEN it should include completion fields
        """
        from mcp_server_langgraph.models.session_goal import SessionGoal

        goal = SessionGoal(
            session_id="session-123",
            user_id="user-456",
            goal="Complete the task",
            achieved="true",
            feedback="All done!",
            set_at=1705123456789,
            completed_at=1705127056789,
        )

        assert goal.achieved == "true"
        assert goal.feedback == "All done!"
        assert goal.completed_at == 1705127056789
