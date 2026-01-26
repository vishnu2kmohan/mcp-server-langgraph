"""
Tests for CompositeArtifactsServiceAdapter.

TDD RED Phase: These tests define the expected behavior of the adapter
that bridges CompositeArtifactsService to the ArtifactsServiceProtocol
used by the API router.

The adapter handles:
- Cursor-based pagination (protocol) vs offset-based (composite)
- Parameter unpacking for create/update operations
- Response format conversion
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit

# Test constants
TEST_USER_ID = "user-adapter-123"
TEST_SESSION_ID = "session-adapter-456"
TEST_ARTIFACT_ID = "art-adapter-789"


def create_test_artifact(
    artifact_id: str = TEST_ARTIFACT_ID,
    version: int = 1,
    **overrides: Any,
) -> dict[str, Any]:
    """Create test artifact dictionary."""
    base = {
        "id": artifact_id,
        "session_id": TEST_SESSION_ID,
        "user_id": TEST_USER_ID,
        "type": "code",
        "title": "Test Artifact",
        "content": "def hello(): pass",
        "content_type": "code",
        "version": version,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "storage_type": "inline",
        "storage_key": None,
    }
    base.update(overrides)
    return base


@pytest.mark.xdist_group(name="test_service_adapter")
@pytest.mark.unit
class TestServiceAdapterListArtifacts:
    """Tests for list_artifacts method with cursor-based pagination."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_list_artifacts_converts_cursor_to_offset(self) -> None:
        """Test that cursor-based pagination is converted to offset."""
        from mcp_server_langgraph.storage.artifacts.service_adapter import (
            CompositeArtifactsServiceAdapter,
        )

        mock_composite = AsyncMock(return_value=None)
        mock_composite.list.return_value = [create_test_artifact()]

        adapter = CompositeArtifactsServiceAdapter(mock_composite)

        # Act - cursor "20" means offset 20
        items, next_cursor, has_more = await adapter.list_artifacts(
            user_id=TEST_USER_ID,
            session_id=TEST_SESSION_ID,
            limit=10,
            cursor="20",
        )

        # Assert
        mock_composite.list.assert_awaited_once_with(
            user_id=TEST_USER_ID,
            session_id=TEST_SESSION_ID,
            limit=11,  # Request 1 extra to check has_more
            offset=20,
        )

    @pytest.mark.asyncio
    async def test_list_artifacts_returns_cursor_when_more_items(self) -> None:
        """Test that cursor is returned when more items exist."""
        from mcp_server_langgraph.storage.artifacts.service_adapter import (
            CompositeArtifactsServiceAdapter,
        )

        mock_composite = AsyncMock(return_value=None)
        # Return 11 items (1 more than limit) to indicate has_more
        mock_composite.list.return_value = [create_test_artifact(artifact_id=f"art-{i}") for i in range(11)]

        adapter = CompositeArtifactsServiceAdapter(mock_composite)

        # Act
        items, next_cursor, has_more = await adapter.list_artifacts(
            user_id=TEST_USER_ID,
            limit=10,
        )

        # Assert
        assert len(items) == 10  # Return only requested limit
        assert has_more is True
        assert next_cursor == "10"  # Next offset

    @pytest.mark.asyncio
    async def test_list_artifacts_returns_no_cursor_at_end(self) -> None:
        """Test that no cursor is returned when at end of list."""
        from mcp_server_langgraph.storage.artifacts.service_adapter import (
            CompositeArtifactsServiceAdapter,
        )

        mock_composite = AsyncMock(return_value=None)
        # Return fewer items than limit
        mock_composite.list.return_value = [create_test_artifact(artifact_id=f"art-{i}") for i in range(5)]

        adapter = CompositeArtifactsServiceAdapter(mock_composite)

        # Act
        items, next_cursor, has_more = await adapter.list_artifacts(
            user_id=TEST_USER_ID,
            limit=10,
        )

        # Assert
        assert len(items) == 5
        assert has_more is False
        assert next_cursor is None


@pytest.mark.xdist_group(name="test_service_adapter")
@pytest.mark.unit
class TestServiceAdapterGetArtifact:
    """Tests for get_artifact method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_artifact_delegates_to_composite(self) -> None:
        """Test that get_artifact delegates to composite service."""
        from mcp_server_langgraph.storage.artifacts.service_adapter import (
            CompositeArtifactsServiceAdapter,
        )

        mock_composite = AsyncMock(return_value=None)
        artifact = create_test_artifact()
        mock_composite.get.return_value = artifact

        adapter = CompositeArtifactsServiceAdapter(mock_composite)

        # Act
        result = await adapter.get_artifact(TEST_ARTIFACT_ID, TEST_USER_ID)

        # Assert
        assert result == artifact
        mock_composite.get.assert_awaited_once_with(
            artifact_id=TEST_ARTIFACT_ID,
            user_id=TEST_USER_ID,
        )


@pytest.mark.xdist_group(name="test_service_adapter")
@pytest.mark.unit
class TestServiceAdapterCreateArtifact:
    """Tests for create_artifact method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_artifact_unpacks_data_dict(self) -> None:
        """Test that create_artifact unpacks the data dictionary."""
        from mcp_server_langgraph.storage.artifacts.service_adapter import (
            CompositeArtifactsServiceAdapter,
        )

        mock_composite = AsyncMock(return_value=None)
        created_artifact = create_test_artifact()
        mock_composite.create.return_value = created_artifact

        adapter = CompositeArtifactsServiceAdapter(mock_composite)

        # Act - data dict as passed by router
        data = {
            "session_id": TEST_SESSION_ID,
            "type": "code",
            "title": "New Artifact",
            "content": "print('hello')",
            "content_type": "code",
            "edit_metadata": {"edited_by": "user"},
        }
        await adapter.create_artifact(data, TEST_USER_ID)

        # Assert
        mock_composite.create.assert_awaited_once()
        call_kwargs = mock_composite.create.call_args.kwargs
        assert call_kwargs["session_id"] == TEST_SESSION_ID
        assert call_kwargs["user_id"] == TEST_USER_ID
        assert call_kwargs["artifact_type"] == "code"
        assert call_kwargs["title"] == "New Artifact"
        assert call_kwargs["content"] == "print('hello')"

    @pytest.mark.asyncio
    async def test_create_artifact_returns_minimal_response(self) -> None:
        """Test that create returns id, version, created_at."""
        from mcp_server_langgraph.storage.artifacts.service_adapter import (
            CompositeArtifactsServiceAdapter,
        )

        mock_composite = AsyncMock(return_value=None)
        mock_composite.create.return_value = {
            "id": "art-new-123",
            "version": 1,
            "created_at": "2025-01-01T00:00:00Z",
            "title": "New Artifact",
            "content": "...",
        }

        adapter = CompositeArtifactsServiceAdapter(mock_composite)

        # Act
        result = await adapter.create_artifact(
            {"session_id": TEST_SESSION_ID, "type": "code", "content": "x", "content_type": "code"},
            TEST_USER_ID,
        )

        # Assert - returns minimal response
        assert "id" in result
        assert "version" in result
        assert "created_at" in result


@pytest.mark.xdist_group(name="test_service_adapter")
@pytest.mark.unit
class TestServiceAdapterUpdateArtifact:
    """Tests for update_artifact method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_update_artifact_unpacks_data_dict(self) -> None:
        """Test that update_artifact unpacks the data dictionary."""
        from mcp_server_langgraph.storage.artifacts.service_adapter import (
            CompositeArtifactsServiceAdapter,
        )

        mock_composite = AsyncMock(return_value=None)
        updated_artifact = create_test_artifact(version=2)
        mock_composite.update.return_value = updated_artifact

        adapter = CompositeArtifactsServiceAdapter(mock_composite)

        # Act
        data = {
            "content": "updated content",
            "title": "Updated Title",
            "edit_metadata": {"edited_by": "ai-suggestion"},
        }
        await adapter.update_artifact(TEST_ARTIFACT_ID, data, TEST_USER_ID)

        # Assert
        mock_composite.update.assert_awaited_once_with(
            artifact_id=TEST_ARTIFACT_ID,
            user_id=TEST_USER_ID,
            content="updated content",
            title="Updated Title",
            edit_metadata={"edited_by": "ai-suggestion"},
        )

    @pytest.mark.asyncio
    async def test_update_artifact_returns_minimal_response(self) -> None:
        """Test that update returns id, version, updated_at."""
        from mcp_server_langgraph.storage.artifacts.service_adapter import (
            CompositeArtifactsServiceAdapter,
        )

        mock_composite = AsyncMock(return_value=None)
        mock_composite.update.return_value = {
            "id": TEST_ARTIFACT_ID,
            "version": 2,
            "updated_at": "2025-01-02T00:00:00Z",
            "content": "...",
        }

        adapter = CompositeArtifactsServiceAdapter(mock_composite)

        # Act
        result = await adapter.update_artifact(
            TEST_ARTIFACT_ID,
            {"content": "new"},
            TEST_USER_ID,
        )

        # Assert
        assert "id" in result
        assert "version" in result
        assert "updated_at" in result


@pytest.mark.xdist_group(name="test_service_adapter")
@pytest.mark.unit
class TestServiceAdapterDeleteArtifact:
    """Tests for delete_artifact method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_delete_artifact_delegates_to_composite(self) -> None:
        """Test that delete_artifact delegates to composite service."""
        from mcp_server_langgraph.storage.artifacts.service_adapter import (
            CompositeArtifactsServiceAdapter,
        )

        mock_composite = AsyncMock(return_value=None)
        mock_composite.delete.return_value = True

        adapter = CompositeArtifactsServiceAdapter(mock_composite)

        # Act
        result = await adapter.delete_artifact(TEST_ARTIFACT_ID, TEST_USER_ID)

        # Assert
        assert result is True
        mock_composite.delete.assert_awaited_once_with(
            artifact_id=TEST_ARTIFACT_ID,
            user_id=TEST_USER_ID,
        )


@pytest.mark.xdist_group(name="test_service_adapter")
@pytest.mark.unit
class TestServiceAdapterVersions:
    """Tests for get_artifact_versions method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_versions_delegates_to_composite(self) -> None:
        """Test that get_artifact_versions delegates to composite service."""
        from mcp_server_langgraph.storage.artifacts.service_adapter import (
            CompositeArtifactsServiceAdapter,
        )

        mock_composite = AsyncMock(return_value=None)
        versions = [
            {"id": "v1", "version": 1, "content": "..."},
            {"id": "v2", "version": 2, "content": "..."},
        ]
        mock_composite.get_versions.return_value = versions

        adapter = CompositeArtifactsServiceAdapter(mock_composite)

        # Act
        result = await adapter.get_artifact_versions(TEST_ARTIFACT_ID, TEST_USER_ID)

        # Assert
        assert result == versions
        mock_composite.get_versions.assert_awaited_once()


@pytest.mark.xdist_group(name="test_service_adapter")
@pytest.mark.unit
class TestServiceAdapterFork:
    """Tests for fork_artifact method."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_fork_artifact_delegates_to_composite(self) -> None:
        """Test that fork_artifact delegates to composite service."""
        from mcp_server_langgraph.storage.artifacts.service_adapter import (
            CompositeArtifactsServiceAdapter,
        )

        mock_composite = AsyncMock(return_value=None)
        forked = {"id": "art-forked", "version": 1}
        mock_composite.fork.return_value = forked

        adapter = CompositeArtifactsServiceAdapter(mock_composite)

        # Act
        await adapter.fork_artifact(
            TEST_ARTIFACT_ID,
            "Forked Artifact",
            TEST_USER_ID,
        )

        # Assert
        mock_composite.fork.assert_awaited_once_with(
            artifact_id=TEST_ARTIFACT_ID,
            user_id=TEST_USER_ID,
            new_name="Forked Artifact",
        )

    @pytest.mark.asyncio
    async def test_fork_returns_parent_id(self) -> None:
        """Test that fork response includes parent_id."""
        from mcp_server_langgraph.storage.artifacts.service_adapter import (
            CompositeArtifactsServiceAdapter,
        )

        mock_composite = AsyncMock(return_value=None)
        mock_composite.fork.return_value = {
            "id": "art-forked",
            "version": 1,
            "title": "Forked",
        }

        adapter = CompositeArtifactsServiceAdapter(mock_composite)

        # Act
        result = await adapter.fork_artifact(
            TEST_ARTIFACT_ID,
            None,
            TEST_USER_ID,
        )

        # Assert - adapter should add parent_id
        assert result is not None
        assert "id" in result
        assert "parent_id" in result
        assert result["parent_id"] == TEST_ARTIFACT_ID


@pytest.mark.xdist_group(name="test_service_adapter")
@pytest.mark.unit
class TestServiceAdapterSemanticSearch:
    """Tests for semantic search methods (exposed via adapter)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_semantic_search_delegates_to_composite(self) -> None:
        """Test that semantic_search delegates to composite service."""
        from mcp_server_langgraph.storage.artifacts.service_adapter import (
            CompositeArtifactsServiceAdapter,
        )

        mock_composite = AsyncMock(return_value=None)
        mock_composite.semantic_search.return_value = [
            {"artifact_id": "art-1", "score": 0.95},
        ]

        adapter = CompositeArtifactsServiceAdapter(mock_composite)

        # Act
        results = await adapter.semantic_search(
            query="function to add numbers",
            user_id=TEST_USER_ID,
            limit=10,
        )

        # Assert
        assert len(results) == 1
        mock_composite.semantic_search.assert_awaited_once_with(
            query="function to add numbers",
            user_id=TEST_USER_ID,
            limit=10,
        )

    @pytest.mark.asyncio
    async def test_find_similar_delegates_to_composite(self) -> None:
        """Test that find_similar delegates to composite service."""
        from mcp_server_langgraph.storage.artifacts.service_adapter import (
            CompositeArtifactsServiceAdapter,
        )

        mock_composite = AsyncMock(return_value=None)
        mock_composite.find_similar.return_value = [
            {"artifact_id": "art-similar", "score": 0.9},
        ]

        adapter = CompositeArtifactsServiceAdapter(mock_composite)

        # Act
        results = await adapter.find_similar(
            artifact_id=TEST_ARTIFACT_ID,
            user_id=TEST_USER_ID,
            limit=5,
        )

        # Assert
        assert len(results) == 1
        mock_composite.find_similar.assert_awaited_once()
