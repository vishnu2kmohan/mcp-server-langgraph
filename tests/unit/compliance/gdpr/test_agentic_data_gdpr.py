"""
Unit tests for GDPR integration with agentic data (notes, checkpoints, evidence).

TDD RED Phase: Tests for notes/checkpoints/evidence export/delete in GDPR compliance.

Tests:
- UserDataExport includes notes and checkpoints fields
- DataExportService exports notes and checkpoints
- DataDeletionService deletes notes, checkpoints, and evidence reports
"""

import gc
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_agentic_data_gdpr")
class TestUserDataExportAgenticFields:
    """Tests for notes/checkpoints fields in UserDataExport."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_user_data_export_has_notes_field(self) -> None:
        """UserDataExport should have notes field."""
        from mcp_server_langgraph.compliance.gdpr.data_export import UserDataExport

        export = UserDataExport(
            export_id="test",
            export_timestamp="2026-01-08T00:00:00Z",
            user_id="user:test",
            username="test",
            email="test@example.com",
        )

        assert hasattr(export, "notes")
        assert isinstance(export.notes, list)

    def test_user_data_export_has_checkpoints_field(self) -> None:
        """UserDataExport should have checkpoints field."""
        from mcp_server_langgraph.compliance.gdpr.data_export import UserDataExport

        export = UserDataExport(
            export_id="test",
            export_timestamp="2026-01-08T00:00:00Z",
            user_id="user:test",
            username="test",
            email="test@example.com",
        )

        assert hasattr(export, "checkpoints")
        assert isinstance(export.checkpoints, list)

    def test_user_data_export_notes_default_empty(self) -> None:
        """UserDataExport notes should default to empty list."""
        from mcp_server_langgraph.compliance.gdpr.data_export import UserDataExport

        export = UserDataExport(
            export_id="test",
            export_timestamp="2026-01-08T00:00:00Z",
            user_id="user:test",
            username="test",
            email="test@example.com",
        )

        assert export.notes == []

    def test_user_data_export_checkpoints_default_empty(self) -> None:
        """UserDataExport checkpoints should default to empty list."""
        from mcp_server_langgraph.compliance.gdpr.data_export import UserDataExport

        export = UserDataExport(
            export_id="test",
            export_timestamp="2026-01-08T00:00:00Z",
            user_id="user:test",
            username="test",
            email="test@example.com",
        )

        assert export.checkpoints == []


@pytest.mark.xdist_group(name="test_agentic_data_gdpr")
class TestDataExportServiceAgenticData:
    """Tests for notes/checkpoints export in DataExportService."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_data_export_service_has_notes_method(self) -> None:
        """DataExportService should have _get_user_notes method."""
        from mcp_server_langgraph.compliance.gdpr.data_export import DataExportService

        service = DataExportService()
        assert hasattr(service, "_get_user_notes")
        assert callable(service._get_user_notes)

    def test_data_export_service_has_checkpoints_method(self) -> None:
        """DataExportService should have _get_user_checkpoints method."""
        from mcp_server_langgraph.compliance.gdpr.data_export import DataExportService

        service = DataExportService()
        assert hasattr(service, "_get_user_checkpoints")
        assert callable(service._get_user_checkpoints)

    def test_data_export_service_has_notes_repository_getter(self) -> None:
        """DataExportService should have _get_notes_repository method."""
        from mcp_server_langgraph.compliance.gdpr.data_export import DataExportService

        service = DataExportService()
        assert hasattr(service, "_get_notes_repository")

    def test_data_export_service_has_checkpoint_repository_getter(self) -> None:
        """DataExportService should have _get_checkpoint_repository method."""
        from mcp_server_langgraph.compliance.gdpr.data_export import DataExportService

        service = DataExportService()
        assert hasattr(service, "_get_checkpoint_repository")

    @pytest.mark.asyncio
    async def test_data_export_service_exports_notes(self) -> None:
        """DataExportService should export notes when available."""
        from mcp_server_langgraph.compliance.gdpr.data_export import DataExportService

        mock_repo = AsyncMock()  # noqa: async-mock-config
        mock_repo.list_by_user = AsyncMock(
            return_value=[
                AsyncMock(
                    model_dump=lambda: {
                        "id": "note-1",
                        "content": "Test note",
                        "category": "research",
                        "user_id": "user:alice",
                    }
                )
            ]
        )

        service = DataExportService()

        with patch.object(service, "_get_notes_repository", return_value=mock_repo):
            notes = await service._get_user_notes("user:alice")

        assert len(notes) == 1
        assert notes[0]["id"] == "note-1"

    @pytest.mark.asyncio
    async def test_data_export_service_exports_checkpoints(self) -> None:
        """DataExportService should export checkpoints when available."""
        from mcp_server_langgraph.compliance.gdpr.data_export import DataExportService

        mock_repo = AsyncMock()  # noqa: async-mock-config
        mock_repo.list_by_user = AsyncMock(
            return_value=[
                AsyncMock(
                    model_dump=lambda: {
                        "id": "cp-1",
                        "phase": "research",
                        "summary": "Completed research",
                        "user_id": "user:alice",
                    }
                )
            ]
        )

        service = DataExportService()

        with patch.object(service, "_get_checkpoint_repository", return_value=mock_repo):
            checkpoints = await service._get_user_checkpoints("user:alice")

        assert len(checkpoints) == 1
        assert checkpoints[0]["id"] == "cp-1"

    @pytest.mark.asyncio
    async def test_data_export_service_returns_empty_when_no_notes_repo(self) -> None:
        """DataExportService should return empty list when notes repo unavailable."""
        from mcp_server_langgraph.compliance.gdpr.data_export import DataExportService

        service = DataExportService()

        with patch.object(service, "_get_notes_repository", return_value=None):
            notes = await service._get_user_notes("user:alice")

        assert notes == []

    @pytest.mark.asyncio
    async def test_data_export_service_returns_empty_when_no_checkpoint_repo(self) -> None:
        """DataExportService should return empty list when checkpoint repo unavailable."""
        from mcp_server_langgraph.compliance.gdpr.data_export import DataExportService

        service = DataExportService()

        with patch.object(service, "_get_checkpoint_repository", return_value=None):
            checkpoints = await service._get_user_checkpoints("user:alice")

        assert checkpoints == []

    @pytest.mark.asyncio
    async def test_gather_user_data_includes_notes_and_checkpoints(self) -> None:
        """_gather_user_data should include notes and checkpoints in export."""
        from mcp_server_langgraph.compliance.gdpr.data_export import DataExportService

        service = DataExportService()

        mock_notes_repo = AsyncMock()  # noqa: async-mock-config
        mock_notes_repo.list_by_user = AsyncMock(
            return_value=[AsyncMock(model_dump=lambda: {"id": "note-1", "content": "Test"})]
        )

        mock_cp_repo = AsyncMock()  # noqa: async-mock-config
        mock_cp_repo.list_by_user = AsyncMock(return_value=[AsyncMock(model_dump=lambda: {"id": "cp-1", "phase": "research"})])

        with (
            patch.object(service, "_get_notes_repository", return_value=mock_notes_repo),
            patch.object(service, "_get_checkpoint_repository", return_value=mock_cp_repo),
        ):
            export = await service._gather_user_data("user:alice", "alice", "alice@example.com")

        assert len(export.notes) == 1
        assert len(export.checkpoints) == 1


@pytest.mark.xdist_group(name="test_agentic_data_gdpr")
class TestDataDeletionServiceAgenticData:
    """Tests for notes/checkpoints/evidence deletion in DataDeletionService."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_data_deletion_service_has_delete_notes_method(self) -> None:
        """DataDeletionService should have _delete_notes method."""
        from mcp_server_langgraph.compliance.gdpr.data_deletion import DataDeletionService

        service = DataDeletionService()
        assert hasattr(service, "_delete_notes")
        assert callable(service._delete_notes)

    def test_data_deletion_service_has_delete_checkpoints_method(self) -> None:
        """DataDeletionService should have _delete_checkpoints method."""
        from mcp_server_langgraph.compliance.gdpr.data_deletion import DataDeletionService

        service = DataDeletionService()
        assert hasattr(service, "_delete_checkpoints")
        assert callable(service._delete_checkpoints)

    def test_data_deletion_service_has_delete_evidence_reports_method(self) -> None:
        """DataDeletionService should have _delete_evidence_reports method."""
        from mcp_server_langgraph.compliance.gdpr.data_deletion import DataDeletionService

        service = DataDeletionService()
        assert hasattr(service, "_delete_evidence_reports")
        assert callable(service._delete_evidence_reports)

    def test_data_deletion_service_has_notes_repository_getter(self) -> None:
        """DataDeletionService should have _get_notes_repository method."""
        from mcp_server_langgraph.compliance.gdpr.data_deletion import DataDeletionService

        service = DataDeletionService()
        assert hasattr(service, "_get_notes_repository")

    def test_data_deletion_service_has_checkpoint_repository_getter(self) -> None:
        """DataDeletionService should have _get_checkpoint_repository method."""
        from mcp_server_langgraph.compliance.gdpr.data_deletion import DataDeletionService

        service = DataDeletionService()
        assert hasattr(service, "_get_checkpoint_repository")

    def test_data_deletion_service_has_evidence_repository_getter(self) -> None:
        """DataDeletionService should have _get_evidence_repository method."""
        from mcp_server_langgraph.compliance.gdpr.data_deletion import DataDeletionService

        service = DataDeletionService()
        assert hasattr(service, "_get_evidence_repository")

    @pytest.mark.asyncio
    async def test_data_deletion_service_deletes_notes(self) -> None:
        """DataDeletionService should delete notes via repository."""
        from mcp_server_langgraph.compliance.gdpr.data_deletion import DataDeletionService

        mock_repo = AsyncMock()  # noqa: async-mock-config
        mock_repo.delete_by_user = AsyncMock(return_value=3)

        service = DataDeletionService()

        with patch.object(service, "_get_notes_repository", return_value=mock_repo):
            count = await service._delete_notes("user:alice")

        assert count == 3
        mock_repo.delete_by_user.assert_called_once_with("user:alice")

    @pytest.mark.asyncio
    async def test_data_deletion_service_deletes_checkpoints(self) -> None:
        """DataDeletionService should delete checkpoints via repository."""
        from mcp_server_langgraph.compliance.gdpr.data_deletion import DataDeletionService

        mock_repo = AsyncMock()  # noqa: async-mock-config
        mock_repo.delete_by_user = AsyncMock(return_value=5)

        service = DataDeletionService()

        with patch.object(service, "_get_checkpoint_repository", return_value=mock_repo):
            count = await service._delete_checkpoints("user:alice")

        assert count == 5
        mock_repo.delete_by_user.assert_called_once_with("user:alice")

    @pytest.mark.asyncio
    async def test_data_deletion_service_deletes_evidence_reports(self) -> None:
        """DataDeletionService should delete evidence reports via repository."""
        from mcp_server_langgraph.compliance.gdpr.data_deletion import DataDeletionService

        mock_repo = AsyncMock()  # noqa: async-mock-config
        mock_repo.delete_reports_by_user = AsyncMock(return_value=2)

        service = DataDeletionService()

        with patch.object(service, "_get_evidence_repository", return_value=mock_repo):
            count = await service._delete_evidence_reports("user:alice")

        assert count == 2
        mock_repo.delete_reports_by_user.assert_called_once_with("user:alice")

    @pytest.mark.asyncio
    async def test_data_deletion_returns_zero_when_no_notes_repo(self) -> None:
        """DataDeletionService should return 0 when notes repo unavailable."""
        from mcp_server_langgraph.compliance.gdpr.data_deletion import DataDeletionService

        service = DataDeletionService()

        with patch.object(service, "_get_notes_repository", return_value=None):
            count = await service._delete_notes("user:alice")

        assert count == 0

    @pytest.mark.asyncio
    async def test_data_deletion_returns_zero_when_no_checkpoint_repo(self) -> None:
        """DataDeletionService should return 0 when checkpoint repo unavailable."""
        from mcp_server_langgraph.compliance.gdpr.data_deletion import DataDeletionService

        service = DataDeletionService()

        with patch.object(service, "_get_checkpoint_repository", return_value=None):
            count = await service._delete_checkpoints("user:alice")

        assert count == 0

    @pytest.mark.asyncio
    async def test_data_deletion_returns_zero_when_no_evidence_repo(self) -> None:
        """DataDeletionService should return 0 when evidence repo unavailable."""
        from mcp_server_langgraph.compliance.gdpr.data_deletion import DataDeletionService

        service = DataDeletionService()

        with patch.object(service, "_get_evidence_repository", return_value=None):
            count = await service._delete_evidence_reports("user:alice")

        assert count == 0
