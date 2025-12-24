"""
User preferences repository for PostgreSQL access.

Provides async CRUD operations for user preferences with proper
transaction management and error handling.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_server_langgraph.observability.telemetry import logger
from mcp_server_langgraph.storage.user.models import UserPreferences
from mcp_server_langgraph.storage.user.postgres_models import UserPreferencesModel

if TYPE_CHECKING:
    pass


class UserPreferencesRepository:
    """
    Repository for user preferences database operations.

    Provides async CRUD operations with proper transaction handling.
    Uses SQLAlchemy 2.0 async patterns.

    Usage:
        async with async_session() as session:
            repo = UserPreferencesRepository(session)
            prefs = await repo.get_preferences("user:alice")
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the repository with a database session.

        Args:
            session: SQLAlchemy async session for database operations.
        """
        self._session = session

    async def get_preferences(self, user_id: str) -> UserPreferences | None:
        """
        Get preferences for a user.

        Args:
            user_id: User ID in OpenFGA format (user:username).

        Returns:
            UserPreferences if found, None otherwise.
        """
        stmt = select(UserPreferencesModel).where(UserPreferencesModel.user_id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return UserPreferences(
            user_id=model.user_id,
            sub_persona=model.sub_persona,
            feature_flags=model.feature_flags or {},
            preferences=model.preferences or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def upsert_preferences(self, prefs: UserPreferences) -> UserPreferences:
        """
        Create or update user preferences.

        Uses upsert semantics - creates if not exists, updates if exists.

        Args:
            prefs: UserPreferences to save.

        Returns:
            The saved UserPreferences with updated timestamps.
        """
        stmt = select(UserPreferencesModel).where(UserPreferencesModel.user_id == prefs.user_id)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        now = datetime.now(UTC)

        if existing is None:
            # Create new record
            model = UserPreferencesModel(
                user_id=prefs.user_id,
                sub_persona=prefs.sub_persona,
                feature_flags=prefs.feature_flags,
                preferences=prefs.preferences,
                created_at=now,
                updated_at=now,
            )
            self._session.add(model)
            logger.info(
                "Created user preferences",
                extra={"user_id": prefs.user_id, "sub_persona": prefs.sub_persona},
            )
        else:
            # Update existing record
            existing.sub_persona = prefs.sub_persona
            existing.feature_flags = prefs.feature_flags
            existing.preferences = prefs.preferences
            existing.updated_at = now
            model = existing
            logger.info(
                "Updated user preferences",
                extra={"user_id": prefs.user_id, "sub_persona": prefs.sub_persona},
            )

        await self._session.commit()

        return UserPreferences(
            user_id=model.user_id,
            sub_persona=model.sub_persona,
            feature_flags=model.feature_flags or {},
            preferences=model.preferences or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def delete_preferences(self, user_id: str) -> bool:
        """
        Delete preferences for a user.

        Args:
            user_id: User ID in OpenFGA format.

        Returns:
            True if deleted, False if not found.
        """
        stmt = select(UserPreferencesModel).where(UserPreferencesModel.user_id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return False

        await self._session.delete(model)
        await self._session.commit()

        logger.info("Deleted user preferences", extra={"user_id": user_id})
        return True

    async def get_all_preferences(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[UserPreferences]:
        """
        Get all user preferences with pagination.

        Useful for admin operations and analytics.

        Args:
            limit: Maximum number of records to return.
            offset: Number of records to skip.

        Returns:
            List of UserPreferences.
        """
        stmt = select(UserPreferencesModel).order_by(UserPreferencesModel.updated_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [
            UserPreferences(
                user_id=m.user_id,
                sub_persona=m.sub_persona,
                feature_flags=m.feature_flags or {},
                preferences=m.preferences or {},
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in models
        ]
