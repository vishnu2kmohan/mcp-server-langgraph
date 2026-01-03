"""
PostgresWorkflowManager Version Methods Unit Tests (TDD Red Phase)

Tests for workflow version history methods:
- get_workflow_versions()
- restore_workflow_version()

Tests written FIRST before implementation (RED phase).

References:
- Plan: Chat-to-Workflow Feature (validated by 4 independent reviews)
- ADR-0089: Prompt Architecture Centralization
- Phase 3: Data Model & Persistence (MANDATORY versioning)
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


pytestmark = [
    pytest.mark.unit,
    pytest.mark.storage,
]


# =============================================================================
# Test Fixtures
# =============================================================================


def make_version_model(
    version_id: str = "v-123",
    workflow_id: str = "wf-456",
    version_number: int = 1,
    commit_message: str | None = "Initial version",
    created_by: str = "test-user",
) -> MagicMock:
    """Create a mock WorkflowVersionModel for testing."""
    model = MagicMock()
    model.id = version_id
    model.workflow_id = workflow_id
    model.version_number = version_number
    model.graph_json = {
        "nodes": [
            {"id": "start", "type": "start", "data": {"label": "Start"}},
            {"id": "end", "type": "end", "data": {"label": "End"}},
        ],
        "edges": [{"source": "start", "target": "end"}],
    }
    model.source_text = None
    model.commit_message = commit_message
    model.created_by = created_by
    model.created_at = datetime.now(UTC)
    model.prompt_version = "v1"
    model.prompt_hash = "abc123"
    model.prompt_model = "claude-opus-4-5"
    return model


def make_workflow_model(
    workflow_id: str = "wf-456",
    name: str = "Test Workflow",
    version: int = 1,
) -> MagicMock:
    """Create a mock WorkflowModel for testing."""
    model = MagicMock()
    model.id = workflow_id
    model.name = name
    model.description = "Test description"
    model.nodes = [{"id": "start", "type": "start"}]
    model.edges = []
    model.user_id = "user-123"
    model.status = "draft"
    model.version = version
    model.head_version_id = None
    model.created_at = datetime.now(UTC)
    model.updated_at = datetime.now(UTC)
    return model


# =============================================================================
# Test: get_workflow_versions() Method
# =============================================================================


@pytest.mark.xdist_group(name="test_postgres_manager_versions")
class TestGetWorkflowVersions:
    """Tests for PostgresWorkflowManager.get_workflow_versions()."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_method_exists(self) -> None:
        """get_workflow_versions method should exist on PostgresWorkflowManager."""
        from mcp_server_langgraph.storage.workflow.postgres_manager import (
            PostgresWorkflowManager,
        )

        assert hasattr(PostgresWorkflowManager, "get_workflow_versions")
        # Method should be async
        import inspect

        assert inspect.iscoroutinefunction(PostgresWorkflowManager.get_workflow_versions)

    @pytest.mark.asyncio
    async def test_returns_list_of_versions(self) -> None:
        """Should return list of WorkflowVersionModel objects."""
        from mcp_server_langgraph.storage.workflow.postgres_manager import (
            PostgresWorkflowManager,
        )

        # Mock engine and session
        mock_engine = MagicMock()
        manager = PostgresWorkflowManager(mock_engine)

        # Create mock versions
        mock_versions = [
            make_version_model("v-3", "wf-456", 3, "Added validation"),
            make_version_model("v-2", "wf-456", 2, "Added processing"),
            make_version_model("v-1", "wf-456", 1, "Initial version"),
        ]

        # Mock the session and query
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_versions
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch.object(manager, "_session_maker", return_value=mock_session):
            result = await manager.get_workflow_versions("wf-456")

        assert isinstance(result, list)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_versions_ordered_by_version_number_desc(self) -> None:
        """Versions should be ordered by version_number descending."""
        from mcp_server_langgraph.storage.workflow.postgres_manager import (
            PostgresWorkflowManager,
        )

        mock_engine = MagicMock()
        manager = PostgresWorkflowManager(mock_engine)

        # Versions returned in descending order
        mock_versions = [
            make_version_model("v-3", "wf-456", 3),
            make_version_model("v-2", "wf-456", 2),
            make_version_model("v-1", "wf-456", 1),
        ]

        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_versions
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch.object(manager, "_session_maker", return_value=mock_session):
            result = await manager.get_workflow_versions("wf-456")

        version_numbers = [v.version_number for v in result]
        assert version_numbers == [3, 2, 1]

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_workflow_with_no_versions(self) -> None:
        """Should return empty list for workflow with no versions."""
        from mcp_server_langgraph.storage.workflow.postgres_manager import (
            PostgresWorkflowManager,
        )

        mock_engine = MagicMock()
        manager = PostgresWorkflowManager(mock_engine)

        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch.object(manager, "_session_maker", return_value=mock_session):
            result = await manager.get_workflow_versions("wf-new")

        assert result == []

    @pytest.mark.asyncio
    async def test_includes_telemetry_fields(self) -> None:
        """Versions should include prompt telemetry fields."""
        from mcp_server_langgraph.storage.workflow.postgres_manager import (
            PostgresWorkflowManager,
        )

        mock_engine = MagicMock()
        manager = PostgresWorkflowManager(mock_engine)

        mock_version = make_version_model()
        mock_version.prompt_version = "v2"
        mock_version.prompt_model = "claude-sonnet-4"
        mock_version.prompt_hash = "def456"

        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_version]
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch.object(manager, "_session_maker", return_value=mock_session):
            result = await manager.get_workflow_versions("wf-456")

        assert len(result) == 1
        assert result[0].prompt_version == "v2"
        assert result[0].prompt_model == "claude-sonnet-4"


# =============================================================================
# Test: restore_workflow_version() Method
# =============================================================================


@pytest.mark.xdist_group(name="test_postgres_manager_versions")
class TestRestoreWorkflowVersion:
    """Tests for PostgresWorkflowManager.restore_workflow_version()."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_method_exists(self) -> None:
        """restore_workflow_version method should exist on PostgresWorkflowManager."""
        from mcp_server_langgraph.storage.workflow.postgres_manager import (
            PostgresWorkflowManager,
        )

        assert hasattr(PostgresWorkflowManager, "restore_workflow_version")
        import inspect

        assert inspect.iscoroutinefunction(PostgresWorkflowManager.restore_workflow_version)

    @pytest.mark.asyncio
    async def test_restore_creates_new_version(self) -> None:
        """Restore should create a new version with incremented version_number."""
        from mcp_server_langgraph.storage.workflow.postgres_manager import (
            PostgresWorkflowManager,
        )

        mock_engine = MagicMock()
        manager = PostgresWorkflowManager(mock_engine)

        # Mock existing workflow and version
        mock_workflow = make_workflow_model("wf-456", version=3)
        mock_version_to_restore = make_version_model("v-1", "wf-456", 1)

        mock_session = AsyncMock(spec=AsyncSession)

        # Mock workflow query
        mock_workflow_result = MagicMock()
        mock_workflow_result.scalar_one_or_none.return_value = mock_workflow

        # Mock version query
        mock_version_result = MagicMock()
        mock_version_result.scalar_one_or_none.return_value = mock_version_to_restore

        # Mock max version query
        mock_max_result = MagicMock()
        mock_max_result.scalar.return_value = 3

        mock_session.execute.side_effect = [
            mock_workflow_result,  # Get workflow
            mock_version_result,  # Get version to restore
            mock_max_result,  # Get max version number
        ]
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch.object(manager, "_session_maker", return_value=mock_session):
            await manager.restore_workflow_version(
                workflow_id="wf-456",
                version_id="v-1",
                user_id="user-123",
            )

        # Should have added a new version
        mock_session.add.assert_called()

    @pytest.mark.asyncio
    async def test_restore_updates_workflow_nodes_and_edges(self) -> None:
        """Restore should update workflow with nodes/edges from restored version."""
        from mcp_server_langgraph.storage.workflow.postgres_manager import (
            PostgresWorkflowManager,
        )

        mock_engine = MagicMock()
        manager = PostgresWorkflowManager(mock_engine)

        mock_workflow = make_workflow_model("wf-456", version=3)
        mock_version_to_restore = make_version_model("v-1", "wf-456", 1)
        mock_version_to_restore.graph_json = {
            "nodes": [{"id": "restored-node"}],
            "edges": [{"source": "a", "target": "b"}],
        }

        mock_session = AsyncMock(spec=AsyncSession)
        mock_workflow_result = MagicMock()
        mock_workflow_result.scalar_one_or_none.return_value = mock_workflow
        mock_version_result = MagicMock()
        mock_version_result.scalar_one_or_none.return_value = mock_version_to_restore
        mock_max_result = MagicMock()
        mock_max_result.scalar.return_value = 3

        mock_session.execute.side_effect = [
            mock_workflow_result,
            mock_version_result,
            mock_max_result,
        ]
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch.object(manager, "_session_maker", return_value=mock_session):
            await manager.restore_workflow_version(
                workflow_id="wf-456",
                version_id="v-1",
                user_id="user-123",
            )

        # Workflow should be updated with restored nodes/edges
        assert mock_workflow.nodes == [{"id": "restored-node"}]
        assert mock_workflow.edges == [{"source": "a", "target": "b"}]

    @pytest.mark.asyncio
    async def test_restore_raises_error_for_nonexistent_workflow(self) -> None:
        """Should raise ValueError if workflow not found."""
        from mcp_server_langgraph.storage.workflow.postgres_manager import (
            PostgresWorkflowManager,
        )

        mock_engine = MagicMock()
        manager = PostgresWorkflowManager(mock_engine)

        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # Workflow not found
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch.object(manager, "_session_maker", return_value=mock_session):
            with pytest.raises(ValueError, match="Workflow not found"):
                await manager.restore_workflow_version(
                    workflow_id="wf-nonexistent",
                    version_id="v-1",
                    user_id="user-123",
                )

    @pytest.mark.asyncio
    async def test_restore_raises_error_for_nonexistent_version(self) -> None:
        """Should raise ValueError if version not found."""
        from mcp_server_langgraph.storage.workflow.postgres_manager import (
            PostgresWorkflowManager,
        )

        mock_engine = MagicMock()
        manager = PostgresWorkflowManager(mock_engine)

        mock_workflow = make_workflow_model()

        mock_session = AsyncMock(spec=AsyncSession)
        mock_workflow_result = MagicMock()
        mock_workflow_result.scalar_one_or_none.return_value = mock_workflow
        mock_version_result = MagicMock()
        mock_version_result.scalar_one_or_none.return_value = None  # Version not found

        mock_session.execute.side_effect = [
            mock_workflow_result,
            mock_version_result,
        ]
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch.object(manager, "_session_maker", return_value=mock_session):
            with pytest.raises(ValueError, match="Version not found"):
                await manager.restore_workflow_version(
                    workflow_id="wf-456",
                    version_id="v-nonexistent",
                    user_id="user-123",
                )

    @pytest.mark.asyncio
    async def test_restore_includes_commit_message(self) -> None:
        """New version should have commit message indicating restoration."""
        from mcp_server_langgraph.storage.workflow.postgres_manager import (
            PostgresWorkflowManager,
        )

        mock_engine = MagicMock()
        manager = PostgresWorkflowManager(mock_engine)

        mock_workflow = make_workflow_model("wf-456", version=3)
        mock_version_to_restore = make_version_model("v-1", "wf-456", 1)

        mock_session = AsyncMock(spec=AsyncSession)
        mock_workflow_result = MagicMock()
        mock_workflow_result.scalar_one_or_none.return_value = mock_workflow
        mock_version_result = MagicMock()
        mock_version_result.scalar_one_or_none.return_value = mock_version_to_restore
        mock_max_result = MagicMock()
        mock_max_result.scalar.return_value = 3

        mock_session.execute.side_effect = [
            mock_workflow_result,
            mock_version_result,
            mock_max_result,
        ]
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch.object(manager, "_session_maker", return_value=mock_session):
            await manager.restore_workflow_version(
                workflow_id="wf-456",
                version_id="v-1",
                user_id="user-123",
            )

        # Check the version that was added has restoration commit message
        added_version = mock_session.add.call_args[0][0]
        assert "Restored from version 1" in added_version.commit_message

    @pytest.mark.asyncio
    async def test_restore_returns_updated_workflow(self) -> None:
        """Should return the updated workflow with new version."""
        from mcp_server_langgraph.storage.workflow.postgres_manager import (
            PostgresWorkflowManager,
        )

        mock_engine = MagicMock()
        manager = PostgresWorkflowManager(mock_engine)

        mock_workflow = make_workflow_model("wf-456", version=3)
        mock_version_to_restore = make_version_model("v-1", "wf-456", 1)

        mock_session = AsyncMock(spec=AsyncSession)
        mock_workflow_result = MagicMock()
        mock_workflow_result.scalar_one_or_none.return_value = mock_workflow
        mock_version_result = MagicMock()
        mock_version_result.scalar_one_or_none.return_value = mock_version_to_restore
        mock_max_result = MagicMock()
        mock_max_result.scalar.return_value = 3

        mock_session.execute.side_effect = [
            mock_workflow_result,
            mock_version_result,
            mock_max_result,
        ]
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch.object(manager, "_session_maker", return_value=mock_session):
            result = await manager.restore_workflow_version(
                workflow_id="wf-456",
                version_id="v-1",
                user_id="user-123",
            )

        assert result is not None
        assert result.id == "wf-456"
