"""
Session Goal Repository Implementation.

Provides storage and retrieval of session goals for goal tracking.

Supports:
- Creating goals
- Completing goals with achievement status
- Querying goals by session
- Getting current (incomplete) goal

Reference: docs-internal/frontend/PENDING-BACKEND-APIS.md
"""

from abc import ABC, abstractmethod
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_server_langgraph.models.session_goal import SessionGoal


AchievementStatus = bool | Literal["partial"]


class SessionGoalRepository(ABC):
    """Abstract base class for session goal repository."""

    @abstractmethod
    async def create_goal(
        self,
        session_id: str,
        user_id: str,
        goal: str,
        set_at: int,
    ) -> dict[str, Any]:
        """Create a new goal for a session."""
        pass

    @abstractmethod
    async def complete_goal(
        self,
        session_id: str,
        user_id: str,
        goal: str,
        achieved: AchievementStatus,
        completed_at: int,
        feedback: str | None = None,
    ) -> dict[str, Any]:
        """Complete a goal with achievement status."""
        pass

    @abstractmethod
    async def get_goals_by_session(
        self,
        session_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get all goals for a session."""
        pass

    @abstractmethod
    async def get_current_goal(
        self,
        session_id: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        """Get the current (incomplete) goal for a session."""
        pass

    @abstractmethod
    async def delete_goal(
        self,
        goal_id: str,
        user_id: str,
    ) -> bool:
        """Delete a goal by ID."""
        pass

    @abstractmethod
    async def count_goals_by_session(
        self,
        session_id: str,
        user_id: str,
    ) -> int:
        """Count total goals for a session (for pagination)."""
        pass


class PostgresSessionGoalRepository(SessionGoalRepository):
    """PostgreSQL implementation of SessionGoalRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with async database session."""
        self._session = session

    def _model_to_dict(self, model: SessionGoal) -> dict[str, Any]:
        """Convert SQLAlchemy model to dictionary."""
        return {
            "id": str(model.id),
            "session_id": model.session_id,
            "user_id": model.user_id,
            "goal": model.goal,
            "achieved": self._parse_achieved(model.achieved),
            "feedback": model.feedback,
            "set_at": model.set_at,
            "completed_at": model.completed_at,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }

    def _parse_achieved(self, achieved: str | None) -> AchievementStatus | None:
        """Parse achieved string to proper type."""
        if achieved is None:
            return None
        if achieved == "true":
            return True
        if achieved == "false":
            return False
        return "partial"

    def _format_achieved(self, achieved: AchievementStatus) -> str:
        """Format achieved value for database storage."""
        if achieved is True:
            return "true"
        if achieved is False:
            return "false"
        return "partial"

    async def create_goal(
        self,
        session_id: str,
        user_id: str,
        goal: str,
        set_at: int,
    ) -> dict[str, Any]:
        """Create a new goal for a session."""
        new_goal = SessionGoal(
            id=str(uuid4()),
            session_id=session_id,
            user_id=user_id,
            goal=goal,
            set_at=set_at,
        )

        self._session.add(new_goal)
        await self._session.flush()

        return self._model_to_dict(new_goal)

    async def complete_goal(
        self,
        session_id: str,
        user_id: str,
        goal: str,
        achieved: AchievementStatus,
        completed_at: int,
        feedback: str | None = None,
    ) -> dict[str, Any]:
        """Complete a goal with achievement status."""
        # Find the most recent matching goal
        stmt = (
            select(SessionGoal)
            .where(
                and_(
                    SessionGoal.session_id == session_id,
                    SessionGoal.user_id == user_id,
                    SessionGoal.goal == goal,
                )
            )
            .order_by(desc(SessionGoal.set_at))
        )

        existing_goal = await self._session.scalar(stmt)

        if existing_goal is None:
            # Create a new completed goal if not found
            new_goal = SessionGoal(
                id=str(uuid4()),
                session_id=session_id,
                user_id=user_id,
                goal=goal,
                achieved=self._format_achieved(achieved),
                feedback=feedback,
                set_at=completed_at - 1000,  # Set slightly before completion
                completed_at=completed_at,
            )
            self._session.add(new_goal)
            await self._session.flush()
            return self._model_to_dict(new_goal)

        # Update existing goal
        existing_goal.achieved = self._format_achieved(achieved)
        existing_goal.feedback = feedback
        existing_goal.completed_at = completed_at
        await self._session.flush()

        return self._model_to_dict(existing_goal)

    async def get_goals_by_session(
        self,
        session_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get all goals for a session."""
        stmt = (
            select(SessionGoal)
            .where(
                and_(
                    SessionGoal.session_id == session_id,
                    SessionGoal.user_id == user_id,
                )
            )
            .order_by(desc(SessionGoal.set_at))
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.scalars(stmt)
        goals = result.all()

        return [self._model_to_dict(g) for g in goals]

    async def get_current_goal(
        self,
        session_id: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        """Get the current (incomplete) goal for a session."""
        stmt = (
            select(SessionGoal)
            .where(
                and_(
                    SessionGoal.session_id == session_id,
                    SessionGoal.user_id == user_id,
                    SessionGoal.completed_at.is_(None),
                )
            )
            .order_by(desc(SessionGoal.set_at))
        )

        goal = await self._session.scalar(stmt)

        if goal is None:
            return None

        return self._model_to_dict(goal)

    async def delete_goal(
        self,
        goal_id: str,
        user_id: str,
    ) -> bool:
        """Delete a goal by ID."""
        stmt = select(SessionGoal).where(
            and_(
                SessionGoal.id == goal_id,
                SessionGoal.user_id == user_id,
            )
        )

        goal = await self._session.scalar(stmt)

        if goal is None:
            return False

        await self._session.delete(goal)
        await self._session.flush()

        return True

    async def count_goals_by_session(
        self,
        session_id: str,
        user_id: str,
    ) -> int:
        """Count total goals for a session (for pagination)."""
        stmt = select(func.count(SessionGoal.id)).where(
            and_(
                SessionGoal.session_id == session_id,
                SessionGoal.user_id == user_id,
            )
        )

        count = await self._session.scalar(stmt)
        return count or 0
