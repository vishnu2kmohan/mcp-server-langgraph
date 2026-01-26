"""
Workflows Versions Endpoint Unit Tests (TDD Red Phase)

Tests for workflow version history endpoints:
- GET /api/v1/workflows/{id}/versions
- POST /api/v1/workflows/{id}/versions/{version_id}/restore

Tests written FIRST before implementation (RED phase).

References:
- Plan: Chat-to-Workflow Feature (validated by 4 independent reviews)
- ADR-0089: Prompt Architecture Centralization
- Phase 3: Data Model & Persistence (MANDATORY versioning)
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


# =============================================================================
# Test Fixtures
# =============================================================================


def make_workflow_version(
    version_id: str = "v-123",
    workflow_id: str = "wf-456",
    version_number: int = 1,
    commit_message: str | None = "Initial version",
) -> dict[str, Any]:
    """Create a sample workflow version for testing."""
    return {
        "id": version_id,
        "workflow_id": workflow_id,
        "version_number": version_number,
        "graph_json": {
            "nodes": [
                {"id": "start", "type": "start", "data": {"label": "Start"}},
                {"id": "end", "type": "end", "data": {"label": "End"}},
            ],
            "edges": [{"source": "start", "target": "end"}],
        },
        "source_text": None,
        "commit_message": commit_message,
        "created_by": "test-user",
        "created_at": datetime.now(UTC).isoformat(),
        "prompt_version": "v1",
        "prompt_model": "claude-opus-4-5",
    }


def make_workflow_versions_list(workflow_id: str = "wf-456") -> list[dict[str, Any]]:
    """Create a list of workflow versions for testing."""
    return [
        make_workflow_version(
            version_id="v-3",
            workflow_id=workflow_id,
            version_number=3,
            commit_message="Added validation node",
        ),
        make_workflow_version(
            version_id="v-2",
            workflow_id=workflow_id,
            version_number=2,
            commit_message="Added processing node",
        ),
        make_workflow_version(
            version_id="v-1",
            workflow_id=workflow_id,
            version_number=1,
            commit_message="Initial version",
        ),
    ]


# =============================================================================
# Test: Response Models Exist
# =============================================================================


@pytest.mark.xdist_group(name="test_workflows_versions")
class TestWorkflowVersionModelsExist:
    """Tests that workflow version response models exist."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_workflow_version_response_model_exists(self) -> None:
        """WorkflowVersionResponse model should exist in workflows module."""
        from mcp_server_langgraph.api.v1.workflows import WorkflowVersionResponse

        assert WorkflowVersionResponse is not None

    def test_workflow_version_response_has_required_fields(self) -> None:
        """WorkflowVersionResponse should have all required fields."""
        from mcp_server_langgraph.api.v1.workflows import WorkflowVersionResponse

        # Check model fields using Pydantic v2 API
        fields = WorkflowVersionResponse.model_fields
        assert "id" in fields
        assert "workflow_id" in fields
        assert "version_number" in fields
        assert "graph_json" in fields
        assert "created_by" in fields
        assert "created_at" in fields

    def test_workflow_version_response_has_optional_fields(self) -> None:
        """WorkflowVersionResponse should have optional telemetry fields."""
        from mcp_server_langgraph.api.v1.workflows import WorkflowVersionResponse

        fields = WorkflowVersionResponse.model_fields
        assert "source_text" in fields
        assert "commit_message" in fields
        assert "prompt_version" in fields
        assert "prompt_model" in fields


# =============================================================================
# Test: GET /workflows/{id}/versions Endpoint
# =============================================================================


@pytest.mark.xdist_group(name="test_workflows_versions")
class TestGetWorkflowVersionsEndpoint:
    """Tests for GET /api/v1/workflows/{id}/versions endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_versions_returns_list(self) -> None:
        """Should return list of versions for a workflow."""
        from mcp_server_langgraph.api.v1.workflows import get_workflow_versions

        # Mock dependencies
        mock_service = AsyncMock(return_value=None)
        mock_service.get_workflow_versions.return_value = make_workflow_versions_list()

        mock_user = MagicMock()
        mock_user.id = "user-123"

        with patch("mcp_server_langgraph.api.v1.workflows.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_workflow_from_chat=True)

            result = await get_workflow_versions(
                workflow_id="wf-456",
                service=mock_service,
                current_user=mock_user,
            )

        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0].version_number == 3  # Newest first

    @pytest.mark.asyncio
    async def test_get_versions_ordered_by_version_desc(self) -> None:
        """Versions should be ordered by version_number descending."""
        from mcp_server_langgraph.api.v1.workflows import get_workflow_versions

        mock_service = AsyncMock(return_value=None)
        mock_service.get_workflow_versions.return_value = make_workflow_versions_list()

        mock_user = MagicMock()
        mock_user.id = "user-123"

        with patch("mcp_server_langgraph.api.v1.workflows.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_workflow_from_chat=True)

            result = await get_workflow_versions(
                workflow_id="wf-456",
                service=mock_service,
                current_user=mock_user,
            )

        # Verify descending order
        version_numbers = [v.version_number for v in result]
        assert version_numbers == [3, 2, 1]

    @pytest.mark.asyncio
    async def test_get_versions_empty_list_for_new_workflow(self) -> None:
        """Should return empty list for workflow with no versions."""
        from mcp_server_langgraph.api.v1.workflows import get_workflow_versions

        mock_service = AsyncMock(return_value=None)
        mock_service.get_workflow_versions.return_value = []

        mock_user = MagicMock()
        mock_user.id = "user-123"

        with patch("mcp_server_langgraph.api.v1.workflows.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_workflow_from_chat=True)

            result = await get_workflow_versions(
                workflow_id="wf-new",
                service=mock_service,
                current_user=mock_user,
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_get_versions_requires_feature_flag(self) -> None:
        """Should raise 404 if feature flag is disabled."""
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.workflows import get_workflow_versions

        # Service not called when feature flag disabled
        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_user = MagicMock()
        mock_user.id = "user-123"

        with patch("mcp_server_langgraph.api.v1.workflows.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_workflow_from_chat=False)

            with pytest.raises(HTTPException) as exc_info:
                await get_workflow_versions(
                    workflow_id="wf-456",
                    service=mock_service,
                    current_user=mock_user,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_versions_includes_telemetry_fields(self) -> None:
        """Versions should include prompt telemetry fields."""
        from mcp_server_langgraph.api.v1.workflows import get_workflow_versions

        mock_service = AsyncMock(return_value=None)
        versions = make_workflow_versions_list()
        mock_service.get_workflow_versions.return_value = versions

        mock_user = MagicMock()
        mock_user.id = "user-123"

        with patch("mcp_server_langgraph.api.v1.workflows.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_workflow_from_chat=True)

            result = await get_workflow_versions(
                workflow_id="wf-456",
                service=mock_service,
                current_user=mock_user,
            )

        assert result[0].prompt_version == "v1"
        assert result[0].prompt_model == "claude-opus-4-5"


# =============================================================================
# Test: POST /workflows/{id}/versions/{version_id}/restore Endpoint
# =============================================================================


@pytest.mark.xdist_group(name="test_workflows_versions")
class TestRestoreWorkflowVersionEndpoint:
    """Tests for POST /api/v1/workflows/{id}/versions/{version_id}/restore."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_restore_version_returns_updated_workflow(self) -> None:
        """Should return the workflow with restored state."""
        from mcp_server_langgraph.api.v1.workflows import restore_workflow_version

        mock_service = AsyncMock(return_value=None)
        mock_service.restore_workflow_version.return_value = {
            "id": "wf-456",
            "name": "test-workflow",
            "version": 4,  # New version after restore
            "nodes": [{"id": "start"}, {"id": "end"}],
            "edges": [{"source": "start", "target": "end"}],
        }

        mock_user = MagicMock()
        mock_user.id = "user-123"

        with patch("mcp_server_langgraph.api.v1.workflows.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_workflow_from_chat=True)

            result = await restore_workflow_version(
                workflow_id="wf-456",
                version_id="v-2",
                service=mock_service,
                current_user=mock_user,
            )

        assert result.id == "wf-456"
        mock_service.restore_workflow_version.assert_called_once()

    @pytest.mark.asyncio
    async def test_restore_creates_new_version(self) -> None:
        """Restore should create a new version, not overwrite existing."""
        from mcp_server_langgraph.api.v1.workflows import restore_workflow_version

        mock_service = AsyncMock(return_value=None)
        # Restored workflow has incremented version
        mock_service.restore_workflow_version.return_value = {
            "id": "wf-456",
            "name": "test-workflow",
            "version": 4,  # Was 3, now 4 after restore
            "nodes": [],
            "edges": [],
        }

        mock_user = MagicMock()
        mock_user.id = "user-123"

        with patch("mcp_server_langgraph.api.v1.workflows.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_workflow_from_chat=True)

            await restore_workflow_version(
                workflow_id="wf-456",
                version_id="v-1",
                service=mock_service,
                current_user=mock_user,
            )

        # Verify service was called with correct params
        mock_service.restore_workflow_version.assert_called_once_with(
            workflow_id="wf-456",
            version_id="v-1",
            user_id="user-123",
        )

    @pytest.mark.asyncio
    async def test_restore_version_not_found(self) -> None:
        """Should raise 404 if version doesn't exist."""
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.workflows import restore_workflow_version

        mock_service = AsyncMock(return_value=None)
        mock_service.restore_workflow_version.side_effect = ValueError("Version not found")

        mock_user = MagicMock()
        mock_user.id = "user-123"

        with patch("mcp_server_langgraph.api.v1.workflows.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_workflow_from_chat=True)

            with pytest.raises(HTTPException) as exc_info:
                await restore_workflow_version(
                    workflow_id="wf-456",
                    version_id="v-nonexistent",
                    service=mock_service,
                    current_user=mock_user,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_restore_requires_feature_flag(self) -> None:
        """Should raise 404 if feature flag is disabled."""
        from fastapi import HTTPException

        from mcp_server_langgraph.api.v1.workflows import restore_workflow_version

        # Service not called when feature flag disabled
        mock_service = AsyncMock(return_value=None)  # noqa: async-mock-config
        mock_user = MagicMock()
        mock_user.id = "user-123"

        with patch("mcp_server_langgraph.api.v1.workflows.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_workflow_from_chat=False)

            with pytest.raises(HTTPException) as exc_info:
                await restore_workflow_version(
                    workflow_id="wf-456",
                    version_id="v-1",
                    service=mock_service,
                    current_user=mock_user,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_restore_adds_commit_message(self) -> None:
        """Restore should include commit message about restoration."""
        from mcp_server_langgraph.api.v1.workflows import restore_workflow_version

        mock_service = AsyncMock(return_value=None)
        mock_service.restore_workflow_version.return_value = {
            "id": "wf-456",
            "name": "test-workflow",
            "version": 4,
            "nodes": [],
            "edges": [],
        }

        mock_user = MagicMock()
        mock_user.id = "user-123"

        with patch("mcp_server_langgraph.api.v1.workflows.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_workflow_from_chat=True)

            await restore_workflow_version(
                workflow_id="wf-456",
                version_id="v-2",
                service=mock_service,
                current_user=mock_user,
            )

        # Service should receive user_id for commit message
        call_kwargs = mock_service.restore_workflow_version.call_args.kwargs
        assert call_kwargs["user_id"] == "user-123"


# =============================================================================
# Test: Service Integration
# =============================================================================


@pytest.mark.xdist_group(name="test_workflows_versions")
class TestWorkflowVersionsServiceIntegration:
    """Tests for workflow service integration with version endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_service_get_versions_called_with_workflow_id(self) -> None:
        """Service should be called with correct workflow_id."""
        from mcp_server_langgraph.api.v1.workflows import get_workflow_versions

        mock_service = AsyncMock(return_value=None)
        mock_service.get_workflow_versions.return_value = []

        mock_user = MagicMock()
        mock_user.id = "user-123"

        with patch("mcp_server_langgraph.api.v1.workflows.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_workflow_from_chat=True)

            await get_workflow_versions(
                workflow_id="wf-specific-id",
                service=mock_service,
                current_user=mock_user,
            )

        mock_service.get_workflow_versions.assert_called_once_with(workflow_id="wf-specific-id")
