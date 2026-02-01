"""
Unit tests for GDPR integration with decision traces.

TDD RED Phase: Tests for decision trace export/delete in GDPR compliance.

Tests:
- UserDataExport includes decision_traces field
- DataExportService exports decision traces
- DataDeletionService deletes decision traces
"""

import gc
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_decision_trace_gdpr")
class TestUserDataExportDecisionTraces:
    """Tests for decision_traces field in UserDataExport."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_user_data_export_has_decision_traces_field(self) -> None:
        """UserDataExport should have decision_traces field."""
        from mcp_server_langgraph.compliance.gdpr.data_export import UserDataExport

        export = UserDataExport(
            export_id="test",
            export_timestamp="2026-01-08T00:00:00Z",
            user_id="user:test",
            username="test",
            email="test@example.com",
        )

        assert hasattr(export, "decision_traces")
        assert isinstance(export.decision_traces, list)

    def test_user_data_export_decision_traces_default_empty(self) -> None:
        """UserDataExport decision_traces should default to empty list."""
        from mcp_server_langgraph.compliance.gdpr.data_export import UserDataExport

        export = UserDataExport(
            export_id="test",
            export_timestamp="2026-01-08T00:00:00Z",
            user_id="user:test",
            username="test",
            email="test@example.com",
        )

        assert export.decision_traces == []


@pytest.mark.xdist_group(name="test_decision_trace_gdpr")
class TestDataExportServiceDecisionTraces:
    """Tests for decision trace export in DataExportService."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_data_export_service_has_decision_trace_method(self) -> None:
        """DataExportService should have _get_user_decision_traces method."""
        from mcp_server_langgraph.compliance.gdpr.data_export import DataExportService

        service = DataExportService()
        assert hasattr(service, "_get_user_decision_traces")
        assert callable(service._get_user_decision_traces)

    @pytest.mark.asyncio
    async def test_data_export_service_exports_decision_traces(self) -> None:
        """DataExportService should export decision traces when available."""
        from mcp_server_langgraph.compliance.gdpr.data_export import DataExportService

        # Mock the decision trace repository
        mock_repo = AsyncMock(return_value=None)
        mock_repo.get_by_user = AsyncMock(
            return_value=[
                {
                    "trace_id": "trace-123",
                    "decision_type": "routing",
                    "query_text": "test query",
                    "timestamp": "2026-01-08T00:00:00Z",
                }
            ]
        )

        service = DataExportService()

        with patch.object(service, "_get_decision_trace_repository", return_value=mock_repo):
            traces = await service._get_user_decision_traces("user:alice")

        assert len(traces) == 1
        assert traces[0]["trace_id"] == "trace-123"


@pytest.mark.xdist_group(name="test_decision_trace_gdpr")
class TestDataDeletionServiceDecisionTraces:
    """Tests for decision trace deletion in DataDeletionService."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_data_deletion_service_has_delete_decision_traces_method(self) -> None:
        """DataDeletionService should have _delete_decision_traces method."""
        from mcp_server_langgraph.compliance.gdpr.data_deletion import (
            DataDeletionService,
        )

        service = DataDeletionService()
        assert hasattr(service, "_delete_decision_traces")
        assert callable(service._delete_decision_traces)

    @pytest.mark.asyncio
    async def test_data_deletion_service_deletes_decision_traces(self) -> None:
        """DataDeletionService should delete decision traces."""
        from mcp_server_langgraph.compliance.gdpr.data_deletion import (
            DataDeletionService,
        )

        # Mock the decision trace repository
        mock_repo = AsyncMock(return_value=None)
        mock_repo.delete_by_user = AsyncMock(return_value=5)

        service = DataDeletionService()

        with patch.object(service, "_get_decision_trace_repository", return_value=mock_repo):
            count = await service._delete_decision_traces("user:alice")

        assert count == 5
        mock_repo.delete_by_user.assert_called_once_with("user:alice")


@pytest.mark.xdist_group(name="test_decision_trace_gdpr")
class TestDecisionTraceRepositoryGetter:
    """Tests for decision trace repository getter methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_export_service_has_repository_getter(self) -> None:
        """DataExportService should have _get_decision_trace_repository method."""
        from mcp_server_langgraph.compliance.gdpr.data_export import DataExportService

        service = DataExportService()
        assert hasattr(service, "_get_decision_trace_repository")

    def test_deletion_service_has_repository_getter(self) -> None:
        """DataDeletionService should have _get_decision_trace_repository method."""
        from mcp_server_langgraph.compliance.gdpr.data_deletion import (
            DataDeletionService,
        )

        service = DataDeletionService()
        assert hasattr(service, "_get_decision_trace_repository")
