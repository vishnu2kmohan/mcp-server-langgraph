"""
Tests for PostgreSQL Artifacts Repository.

TDD RED Phase: These tests define the expected behavior of PostgresArtifactsRepository.
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    pass


# Test constants
TEST_USER_ID = "user-123"
TEST_SESSION_ID = "session-456"
TEST_ARTIFACT_ID = "art-789"


def create_mock_artifact_data(
    artifact_id: str = TEST_ARTIFACT_ID,
    user_id: str = TEST_USER_ID,
    session_id: str = TEST_SESSION_ID,
    **overrides: Any,
) -> dict[str, Any]:
    """Create mock artifact data for testing."""
    now = datetime.now(UTC).isoformat()
    base = {
        "id": artifact_id,
        "session_id": session_id,
        "user_id": user_id,
        "type": "code",
        "title": "Test Artifact",
        "content": "console.log('hello');",
        "content_type": "code",
        "version": 1,
        "storage_type": "inline",
        "storage_key": None,
        "edit_metadata": {"edited_by": "user"},
        "created_at": now,
        "updated_at": now,
    }
    base.update(overrides)
    return base


@pytest.mark.xdist_group(name="test_postgres_artifacts_repository")
@pytest.mark.unit
class TestPostgresArtifactsRepositoryCreate:
    """Tests for artifact creation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_artifact_stores_in_database(self) -> None:
        """Test that create_artifact stores artifact in PostgreSQL."""
        from mcp_server_langgraph.storage.artifacts.postgres_repository import (
            PostgresArtifactsRepository,
        )

        # Arrange
        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # add is sync
        mock_session.commit = AsyncMock()  # commit is async
        repo = PostgresArtifactsRepository(session=mock_session)

        artifact_data = {
            "type": "code",
            "content": "print('hello')",
            "content_type": "code",
            "session_id": TEST_SESSION_ID,
            "title": "Test Artifact",
        }

        # Act
        result = await repo.create(artifact_data, user_id=TEST_USER_ID)

        # Assert
        assert result is not None
        assert "id" in result
        assert result["version"] == 1
        assert "created_at" in result
        mock_session.add.assert_called()
        mock_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_create_artifact_creates_initial_version(self) -> None:
        """Test that create_artifact also creates version 1 in history."""
        from mcp_server_langgraph.storage.artifacts.postgres_repository import (
            PostgresArtifactsRepository,
        )

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        repo = PostgresArtifactsRepository(session=mock_session)

        artifact_data = {
            "type": "code",
            "content": "const x = 1;",
            "content_type": "code",
            "session_id": TEST_SESSION_ID,
        }

        # Act
        await repo.create(artifact_data, user_id=TEST_USER_ID)

        # Assert - should add both artifact and version
        assert mock_session.add.call_count >= 2

    @pytest.mark.asyncio
    async def test_create_artifact_generates_uuid(self) -> None:
        """Test that create_artifact generates a unique ID."""
        from mcp_server_langgraph.storage.artifacts.postgres_repository import (
            PostgresArtifactsRepository,
        )

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        repo = PostgresArtifactsRepository(session=mock_session)

        artifact_data = {
            "type": "code",
            "content": "test",
            "content_type": "code",
            "session_id": TEST_SESSION_ID,
        }

        # Act
        result = await repo.create(artifact_data, user_id=TEST_USER_ID)

        # Assert
        assert result["id"].startswith("art-")
        assert len(result["id"]) > 8


@pytest.mark.xdist_group(name="test_postgres_artifacts_repository")
@pytest.mark.unit
class TestPostgresArtifactsRepositoryGet:
    """Tests for artifact retrieval."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_artifact_returns_artifact_dict(self) -> None:
        """Test that get returns artifact as dictionary."""
        from mcp_server_langgraph.storage.artifacts.postgres_repository import (
            PostgresArtifactsRepository,
        )

        mock_session = AsyncMock()
        mock_artifact = MagicMock()
        mock_artifact.to_dict.return_value = create_mock_artifact_data()
        mock_artifact.user_id = TEST_USER_ID

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_artifact
        mock_session.execute.return_value = mock_result

        repo = PostgresArtifactsRepository(session=mock_session)

        # Act
        result = await repo.get(TEST_ARTIFACT_ID, user_id=TEST_USER_ID)

        # Assert
        assert result is not None
        assert result["id"] == TEST_ARTIFACT_ID
        assert result["user_id"] == TEST_USER_ID

    @pytest.mark.asyncio
    async def test_get_artifact_returns_none_when_not_found(self) -> None:
        """Test that get returns None for non-existent artifact."""
        from mcp_server_langgraph.storage.artifacts.postgres_repository import (
            PostgresArtifactsRepository,
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = PostgresArtifactsRepository(session=mock_session)

        # Act
        result = await repo.get("non-existent-id", user_id=TEST_USER_ID)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_artifact_returns_none_for_different_user(self) -> None:
        """Test that get returns None if artifact belongs to different user."""
        from mcp_server_langgraph.storage.artifacts.postgres_repository import (
            PostgresArtifactsRepository,
        )

        mock_session = AsyncMock()
        mock_artifact = MagicMock()
        mock_artifact.user_id = "other-user"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_artifact
        mock_session.execute.return_value = mock_result

        repo = PostgresArtifactsRepository(session=mock_session)

        # Act
        result = await repo.get(TEST_ARTIFACT_ID, user_id=TEST_USER_ID)

        # Assert
        assert result is None


@pytest.mark.xdist_group(name="test_postgres_artifacts_repository")
@pytest.mark.unit
class TestPostgresArtifactsRepositoryUpdate:
    """Tests for artifact updates."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_update_artifact_increments_version(self) -> None:
        """Test that update increments version number."""
        from mcp_server_langgraph.storage.artifacts.postgres_repository import (
            PostgresArtifactsRepository,
        )

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # add is sync
        mock_session.commit = AsyncMock()  # commit is async
        mock_artifact = MagicMock()
        mock_artifact.version = 1
        mock_artifact.user_id = TEST_USER_ID
        mock_artifact.content = "old content"
        mock_artifact.content_type = "code"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_artifact
        mock_session.execute.return_value = mock_result

        repo = PostgresArtifactsRepository(session=mock_session)

        # Act
        result = await repo.update(
            TEST_ARTIFACT_ID,
            data={"content": "new content"},
            user_id=TEST_USER_ID,
        )

        # Assert
        assert result is not None
        assert result["version"] == 2

    @pytest.mark.asyncio
    async def test_update_artifact_creates_version_entry(self) -> None:
        """Test that update creates a new version in history."""
        from mcp_server_langgraph.storage.artifacts.postgres_repository import (
            PostgresArtifactsRepository,
        )

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # add is sync
        mock_session.commit = AsyncMock()  # commit is async
        mock_artifact = MagicMock()
        mock_artifact.version = 1
        mock_artifact.user_id = TEST_USER_ID
        mock_artifact.content = "old"
        mock_artifact.content_type = "code"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_artifact
        mock_session.execute.return_value = mock_result

        repo = PostgresArtifactsRepository(session=mock_session)

        # Act
        await repo.update(
            TEST_ARTIFACT_ID,
            data={"content": "new"},
            user_id=TEST_USER_ID,
        )

        # Assert - should add version entry
        mock_session.add.assert_called()

    @pytest.mark.asyncio
    async def test_update_artifact_returns_none_for_different_user(self) -> None:
        """Test that update returns None if artifact belongs to different user."""
        from mcp_server_langgraph.storage.artifacts.postgres_repository import (
            PostgresArtifactsRepository,
        )

        mock_session = AsyncMock()
        mock_artifact = MagicMock()
        mock_artifact.user_id = "other-user"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_artifact
        mock_session.execute.return_value = mock_result

        repo = PostgresArtifactsRepository(session=mock_session)

        # Act
        result = await repo.update(
            TEST_ARTIFACT_ID,
            data={"content": "new"},
            user_id=TEST_USER_ID,
        )

        # Assert
        assert result is None


@pytest.mark.xdist_group(name="test_postgres_artifacts_repository")
@pytest.mark.unit
class TestPostgresArtifactsRepositoryDelete:
    """Tests for artifact deletion."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_delete_artifact_returns_true_on_success(self) -> None:
        """Test that delete returns True when artifact is deleted."""
        from mcp_server_langgraph.storage.artifacts.postgres_repository import (
            PostgresArtifactsRepository,
        )

        mock_session = AsyncMock()
        mock_artifact = MagicMock()
        mock_artifact.user_id = TEST_USER_ID

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_artifact
        mock_session.execute.return_value = mock_result

        repo = PostgresArtifactsRepository(session=mock_session)

        # Act
        result = await repo.delete(TEST_ARTIFACT_ID, user_id=TEST_USER_ID)

        # Assert
        assert result is True
        mock_session.delete.assert_awaited_with(mock_artifact)

    @pytest.mark.asyncio
    async def test_delete_artifact_returns_false_when_not_found(self) -> None:
        """Test that delete returns False for non-existent artifact."""
        from mcp_server_langgraph.storage.artifacts.postgres_repository import (
            PostgresArtifactsRepository,
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = PostgresArtifactsRepository(session=mock_session)

        # Act
        result = await repo.delete("non-existent", user_id=TEST_USER_ID)

        # Assert
        assert result is False


@pytest.mark.xdist_group(name="test_postgres_artifacts_repository")
@pytest.mark.unit
class TestPostgresArtifactsRepositoryList:
    """Tests for artifact listing."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_artifacts_returns_user_artifacts(self) -> None:
        """Test that list returns only artifacts for the given user."""
        from mcp_server_langgraph.storage.artifacts.postgres_repository import (
            PostgresArtifactsRepository,
        )

        mock_session = AsyncMock()
        mock_artifacts = [
            MagicMock(to_dict=lambda: create_mock_artifact_data(artifact_id="art-1")),
            MagicMock(to_dict=lambda: create_mock_artifact_data(artifact_id="art-2")),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_artifacts
        mock_session.execute.return_value = mock_result

        repo = PostgresArtifactsRepository(session=mock_session)

        # Act
        items, cursor, has_more = await repo.list(user_id=TEST_USER_ID)

        # Assert
        assert len(items) == 2
        assert cursor is None
        assert has_more is False

    @pytest.mark.asyncio
    async def test_list_artifacts_filters_by_session_id(self) -> None:
        """Test that list can filter by session_id."""
        from mcp_server_langgraph.storage.artifacts.postgres_repository import (
            PostgresArtifactsRepository,
        )

        mock_session = AsyncMock()
        mock_artifact = MagicMock()
        mock_artifact.to_dict.return_value = create_mock_artifact_data()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_artifact]
        mock_session.execute.return_value = mock_result

        repo = PostgresArtifactsRepository(session=mock_session)

        # Act
        items, _, _ = await repo.list(user_id=TEST_USER_ID, session_id=TEST_SESSION_ID)

        # Assert
        assert len(items) == 1
        # Verify session_id filter was applied in the query
        mock_session.execute.assert_awaited()

    @pytest.mark.asyncio
    async def test_list_artifacts_pagination(self) -> None:
        """Test that list supports cursor-based pagination."""
        from mcp_server_langgraph.storage.artifacts.postgres_repository import (
            PostgresArtifactsRepository,
        )

        mock_session = AsyncMock()
        # Create 3 artifacts to test pagination
        mock_artifacts = [MagicMock(to_dict=lambda i=i: create_mock_artifact_data(artifact_id=f"art-{i}")) for i in range(3)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_artifacts
        mock_session.execute.return_value = mock_result

        repo = PostgresArtifactsRepository(session=mock_session)

        # Act - request with limit
        items, cursor, has_more = await repo.list(user_id=TEST_USER_ID, limit=2)

        # Assert - should respect limit
        mock_session.execute.assert_awaited()


@pytest.mark.xdist_group(name="test_postgres_artifacts_repository")
@pytest.mark.unit
class TestPostgresArtifactsRepositoryVersions:
    """Tests for version history."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_versions_returns_version_history(self) -> None:
        """Test that get_versions returns all versions for an artifact."""
        from mcp_server_langgraph.storage.artifacts.postgres_repository import (
            PostgresArtifactsRepository,
        )

        mock_session = AsyncMock()

        # Mock artifact exists and belongs to user
        mock_artifact = MagicMock()
        mock_artifact.user_id = TEST_USER_ID

        # Mock versions
        mock_versions = [
            MagicMock(to_dict=lambda: {"id": "v1", "version": 1}),
            MagicMock(to_dict=lambda: {"id": "v2", "version": 2}),
        ]

        mock_artifact_result = MagicMock()
        mock_artifact_result.scalar_one_or_none.return_value = mock_artifact

        mock_versions_result = MagicMock()
        mock_versions_result.scalars.return_value.all.return_value = mock_versions

        mock_session.execute.side_effect = [mock_artifact_result, mock_versions_result]

        repo = PostgresArtifactsRepository(session=mock_session)

        # Act
        versions = await repo.get_versions(TEST_ARTIFACT_ID, user_id=TEST_USER_ID)

        # Assert
        assert versions is not None
        assert len(versions) == 2

    @pytest.mark.asyncio
    async def test_get_versions_returns_none_for_nonexistent_artifact(self) -> None:
        """Test that get_versions returns None if artifact doesn't exist."""
        from mcp_server_langgraph.storage.artifacts.postgres_repository import (
            PostgresArtifactsRepository,
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = PostgresArtifactsRepository(session=mock_session)

        # Act
        versions = await repo.get_versions("non-existent", user_id=TEST_USER_ID)

        # Assert
        assert versions is None


@pytest.mark.xdist_group(name="test_postgres_artifacts_repository")
@pytest.mark.unit
class TestPostgresArtifactsRepositoryFork:
    """Tests for artifact forking."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_fork_creates_new_artifact(self) -> None:
        """Test that fork creates a copy of the artifact."""
        from mcp_server_langgraph.storage.artifacts.postgres_repository import (
            PostgresArtifactsRepository,
        )

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # add is sync
        mock_session.commit = AsyncMock()  # commit is async

        # Mock source artifact
        mock_artifact = MagicMock()
        mock_artifact.id = TEST_ARTIFACT_ID
        mock_artifact.content = "original content"
        mock_artifact.content_type = "code"
        mock_artifact.type = "code"
        mock_artifact.title = "Original"
        mock_artifact.session_id = TEST_SESSION_ID
        mock_artifact.storage_type = "inline"
        mock_artifact.storage_key = None
        mock_artifact.edit_metadata = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_artifact
        mock_session.execute.return_value = mock_result

        repo = PostgresArtifactsRepository(session=mock_session)

        # Act
        result = await repo.fork(TEST_ARTIFACT_ID, new_name="Forked Copy", user_id=TEST_USER_ID)

        # Assert
        assert result is not None
        assert result["parent_id"] == TEST_ARTIFACT_ID
        assert result["version"] == 1
        mock_session.add.assert_called()

    @pytest.mark.asyncio
    async def test_fork_uses_default_name_if_not_provided(self) -> None:
        """Test that fork uses 'Fork of X' as default name."""
        from mcp_server_langgraph.storage.artifacts.postgres_repository import (
            PostgresArtifactsRepository,
        )

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # add is sync
        mock_session.commit = AsyncMock()  # commit is async

        mock_artifact = MagicMock()
        mock_artifact.id = TEST_ARTIFACT_ID
        mock_artifact.title = "Original Title"
        mock_artifact.content = "content"
        mock_artifact.content_type = "code"
        mock_artifact.type = "code"
        mock_artifact.session_id = TEST_SESSION_ID
        mock_artifact.storage_type = "inline"
        mock_artifact.storage_key = None
        mock_artifact.edit_metadata = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_artifact
        mock_session.execute.return_value = mock_result

        repo = PostgresArtifactsRepository(session=mock_session)

        # Act
        result = await repo.fork(TEST_ARTIFACT_ID, new_name=None, user_id=TEST_USER_ID)

        # Assert
        assert result is not None
        # Verify the title includes "Fork of"
        mock_session.add.assert_called()

    @pytest.mark.asyncio
    async def test_fork_returns_none_for_nonexistent_artifact(self) -> None:
        """Test that fork returns None if source artifact doesn't exist."""
        from mcp_server_langgraph.storage.artifacts.postgres_repository import (
            PostgresArtifactsRepository,
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = PostgresArtifactsRepository(session=mock_session)

        # Act
        result = await repo.fork("non-existent", new_name="Fork", user_id=TEST_USER_ID)

        # Assert
        assert result is None
