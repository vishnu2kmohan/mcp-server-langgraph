"""
Tests for UserPreferencesRepository.

TDD: These tests define the expected behavior for the PostgreSQL-backed
user preferences storage, replacing the in-memory dictionary.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.storage.user.models import UserPreferences
from mcp_server_langgraph.storage.user.repository import UserPreferencesRepository

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="user_preferences")
class TestUserPreferencesRepository:
    """Tests for UserPreferencesRepository database operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_preferences_returns_none_for_nonexistent_user(self) -> None:
        """Getting preferences for a user that doesn't exist should return None."""
        # GIVEN: A repository with a mock session
        mock_session = AsyncMock(return_value=None)
        # Create explicit mock result - MagicMock() with explicit return_value prevents auto-attr pollution
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # EXPLICIT: Prevents MagicMock attr leak
        mock_session.execute.return_value = mock_result
        repo = UserPreferencesRepository(session=mock_session)

        # WHEN: Getting preferences for a nonexistent user
        result = await repo.get_preferences("user:nonexistent")

        # THEN: None is returned
        assert result is None

    @pytest.mark.asyncio
    async def test_get_preferences_returns_existing_preferences(self) -> None:
        """Getting preferences for an existing user should return their preferences."""
        # GIVEN: A repository with existing user preferences
        mock_prefs = UserPreferences(
            user_id="user:alice",
            sub_persona="alice-builder",
            feature_flags={"focus_mode": True},
        )
        mock_session = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_prefs
        mock_session.execute.return_value = mock_result
        repo = UserPreferencesRepository(session=mock_session)

        # WHEN: Getting preferences for an existing user
        result = await repo.get_preferences("user:alice")

        # THEN: The preferences are returned
        assert result is not None
        assert result.user_id == "user:alice"
        assert result.sub_persona == "alice-builder"
        assert result.feature_flags == {"focus_mode": True}

    @pytest.mark.asyncio
    async def test_upsert_preferences_creates_new_record(self) -> None:
        """Upserting preferences for a new user should create the record."""
        # GIVEN: A repository with no existing preferences
        mock_session = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        repo = UserPreferencesRepository(session=mock_session)

        # WHEN: Upserting new preferences
        prefs = UserPreferences(
            user_id="user:bob",
            sub_persona="bob",
            feature_flags={},
        )
        await repo.upsert_preferences(prefs)

        # THEN: The session add and commit are called
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_preferences_updates_existing_record(self) -> None:
        """Upserting preferences for an existing user should update the record."""
        # GIVEN: A repository with existing preferences
        existing_prefs = UserPreferences(
            user_id="user:alice",
            sub_persona="alice-builder",
            feature_flags={"old_flag": True},
        )
        mock_session = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_prefs
        mock_session.execute.return_value = mock_result
        repo = UserPreferencesRepository(session=mock_session)

        # WHEN: Upserting updated preferences
        new_prefs = UserPreferences(
            user_id="user:alice",
            sub_persona="alice-analyst",
            feature_flags={"new_flag": True},
        )
        await repo.upsert_preferences(new_prefs)

        # THEN: The existing record is updated
        assert existing_prefs.sub_persona == "alice-analyst"
        assert existing_prefs.feature_flags == {"new_flag": True}
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_preferences_removes_record(self) -> None:
        """Deleting preferences should remove the record from the database."""
        # GIVEN: A repository with existing preferences
        existing_prefs = UserPreferences(
            user_id="user:alice",
            sub_persona="alice-builder",
            feature_flags={},
        )
        mock_session = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_prefs
        mock_session.execute.return_value = mock_result
        repo = UserPreferencesRepository(session=mock_session)

        # WHEN: Deleting preferences
        result = await repo.delete_preferences("user:alice")

        # THEN: The record is deleted
        assert result is True
        mock_session.delete.assert_called_once_with(existing_prefs)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_preferences_returns_false_for_nonexistent(self) -> None:
        """Deleting nonexistent preferences should return False."""
        # GIVEN: A repository with no preferences for the user
        mock_session = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        repo = UserPreferencesRepository(session=mock_session)

        # WHEN: Deleting nonexistent preferences
        result = await repo.delete_preferences("user:nonexistent")

        # THEN: False is returned
        assert result is False
        mock_session.delete.assert_not_called()


@pytest.mark.unit
@pytest.mark.xdist_group(name="user_preferences")
class TestUserPreferencesModel:
    """Tests for UserPreferences Pydantic model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_model_with_minimal_fields(self) -> None:
        """Model should work with just user_id."""
        prefs = UserPreferences(user_id="user:test")

        assert prefs.user_id == "user:test"
        assert prefs.sub_persona is None
        assert prefs.feature_flags == {}

    def test_model_with_all_fields(self) -> None:
        """Model should accept all fields."""
        prefs = UserPreferences(
            user_id="user:alice",
            sub_persona="alice-builder",
            feature_flags={"focus_mode": True, "canvas_shortcuts": False},
        )

        assert prefs.user_id == "user:alice"
        assert prefs.sub_persona == "alice-builder"
        assert prefs.feature_flags == {"focus_mode": True, "canvas_shortcuts": False}

    def test_model_validates_user_id_required(self) -> None:
        """Model should require user_id."""
        with pytest.raises(ValueError):
            UserPreferences()  # type: ignore[call-arg]

    def test_model_feature_flags_defaults_to_empty_dict(self) -> None:
        """Feature flags should default to empty dict."""
        prefs = UserPreferences(user_id="user:test")
        assert prefs.feature_flags == {}

    def test_model_to_dict(self) -> None:
        """Model should convert to dict correctly."""
        prefs = UserPreferences(
            user_id="user:alice",
            sub_persona="alice-builder",
            feature_flags={"focus_mode": True},
        )

        result = prefs.model_dump()
        assert result["user_id"] == "user:alice"
        assert result["sub_persona"] == "alice-builder"
        assert result["feature_flags"] == {"focus_mode": True}
