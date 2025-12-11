"""
TDD tests for GDPR compliance metrics.

Verifies that GDPR operations record metrics:
- Data export (DSAR - Article 15/20)
- Data deletion (Article 17 - Right to Erasure)
- Retention cleanup (Article 5 - Storage Limitation)
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.compliance
@pytest.mark.gdpr
@pytest.mark.metrics
@pytest.mark.xdist_group(name="gdpr_metrics")
class TestGDPRDataExportMetrics:
    """Test GDPR data export metrics are recorded during DSAR operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_export_user_data_records_metrics_on_success(self) -> None:
        """Verify export_user_data() records success metrics."""
        from mcp_server_langgraph.compliance.gdpr.data_export import DataExportService

        # Create service without storage (will use minimal data)
        service = DataExportService(session_store=None, gdpr_storage=None)

        with patch("mcp_server_langgraph.compliance.gdpr.data_export.record_gdpr_data_export") as mock_record:
            export = await service.export_user_data(
                user_id="user:test",
                username="testuser",
                email="test@example.com",
            )

            # Verify export was created
            assert export.user_id == "user:test"
            assert export.username == "testuser"
            assert export.email == "test@example.com"

            # Verify metrics were recorded
            mock_record.assert_called_once_with(format="json", status="success")

    @pytest.mark.asyncio
    async def test_export_user_data_portable_json_records_metrics(self) -> None:
        """Verify export_user_data_portable() with JSON format records metrics."""
        from mcp_server_langgraph.compliance.gdpr.data_export import DataExportService

        service = DataExportService(session_store=None, gdpr_storage=None)

        with patch("mcp_server_langgraph.compliance.gdpr.data_export.record_gdpr_data_export") as mock_record:
            data, content_type = await service.export_user_data_portable(
                user_id="user:test",
                username="testuser",
                email="test@example.com",
                format="json",
            )

            # Verify export data
            assert content_type == "application/json"
            assert len(data) > 0

            # Verify metrics were recorded for portable export
            mock_record.assert_called_once_with(format="json", status="success")

    @pytest.mark.asyncio
    async def test_export_user_data_portable_csv_records_metrics(self) -> None:
        """Verify export_user_data_portable() with CSV format records metrics."""
        from mcp_server_langgraph.compliance.gdpr.data_export import DataExportService

        service = DataExportService(session_store=None, gdpr_storage=None)

        with patch("mcp_server_langgraph.compliance.gdpr.data_export.record_gdpr_data_export") as mock_record:
            data, content_type = await service.export_user_data_portable(
                user_id="user:test",
                username="testuser",
                email="test@example.com",
                format="csv",
            )

            # Verify export data
            assert content_type == "text/csv"
            assert len(data) > 0

            # Verify metrics were recorded for CSV export
            mock_record.assert_called_once_with(format="csv", status="success")


@pytest.mark.unit
@pytest.mark.compliance
@pytest.mark.gdpr
@pytest.mark.metrics
@pytest.mark.xdist_group(name="gdpr_metrics")
class TestGDPRDataDeletionMetrics:
    """Test GDPR data deletion metrics are recorded during Article 17 operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_delete_user_account_records_success_metrics(self) -> None:
        """Verify delete_user_account() records success metrics."""
        from mcp_server_langgraph.compliance.gdpr.data_deletion import DataDeletionService

        # Create service without storage (will return minimal results)
        service = DataDeletionService(
            session_store=None,
            gdpr_storage=None,
            openfga_client=None,
        )

        with patch("mcp_server_langgraph.compliance.gdpr.data_deletion.record_gdpr_data_deletion") as mock_record:
            result = await service.delete_user_account(
                user_id="user:test",
                username="testuser",
                reason="user_request",
            )

            # Verify deletion result
            assert result.user_id == "user:test"
            assert result.success is True

            # Verify metrics were recorded for full deletion
            mock_record.assert_called_once_with(operation="full", status="success")

    @pytest.mark.asyncio
    async def test_delete_user_account_records_failure_metrics(self) -> None:
        """Verify delete_user_account() records failure metrics on errors."""
        from mcp_server_langgraph.compliance.gdpr.data_deletion import DataDeletionService

        # Create mock session store that raises an error
        mock_session_store = MagicMock()
        mock_session_store.delete_user_sessions = AsyncMock(side_effect=Exception("Session deletion failed"))

        service = DataDeletionService(
            session_store=mock_session_store,
            gdpr_storage=None,
            openfga_client=None,
        )

        with patch("mcp_server_langgraph.compliance.gdpr.data_deletion.record_gdpr_data_deletion") as mock_record:
            result = await service.delete_user_account(
                user_id="user:test",
                username="testuser",
                reason="user_request",
            )

            # Verify deletion had errors
            assert result.user_id == "user:test"
            assert len(result.errors) > 0

            # Verify metrics were recorded with failure status
            mock_record.assert_called_once_with(operation="full", status="failure")


@pytest.mark.unit
@pytest.mark.compliance
@pytest.mark.gdpr
@pytest.mark.metrics
@pytest.mark.xdist_group(name="gdpr_metrics")
class TestGDPRRetentionCleanupMetrics:
    """Test GDPR retention cleanup metrics are recorded during Article 5 operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_cleanup_sessions_records_success_metrics(self) -> None:
        """Verify cleanup_sessions() records success metrics."""
        from mcp_server_langgraph.compliance.retention import DataRetentionService

        # Create mock session store
        mock_session_store = MagicMock()
        mock_session_store.get_inactive_sessions = AsyncMock(return_value=[])
        mock_session_store.delete_inactive_sessions = AsyncMock(return_value=5)

        service = DataRetentionService(
            config_path="nonexistent.yaml",  # Will use defaults
            session_store=mock_session_store,
            conversation_store=None,
            audit_log_store=None,
            dry_run=False,
        )

        with patch("mcp_server_langgraph.compliance.retention.record_gdpr_retention_cleanup") as mock_record:
            result = await service.cleanup_sessions()

            # Verify cleanup result
            assert result.policy_name == "user_sessions"
            assert result.deleted_count == 5

            # Verify metrics were recorded
            mock_record.assert_called_once_with(data_type="sessions", status="success", count=5)

    @pytest.mark.asyncio
    async def test_cleanup_sessions_records_failure_metrics(self) -> None:
        """Verify cleanup_sessions() records failure metrics on errors."""
        from mcp_server_langgraph.compliance.retention import DataRetentionService

        # Create mock session store that raises an error
        mock_session_store = MagicMock()
        mock_session_store.delete_inactive_sessions = AsyncMock(side_effect=Exception("Session cleanup failed"))

        service = DataRetentionService(
            config_path="nonexistent.yaml",
            session_store=mock_session_store,
            conversation_store=None,
            audit_log_store=None,
            dry_run=False,
        )

        with patch("mcp_server_langgraph.compliance.retention.record_gdpr_retention_cleanup") as mock_record:
            result = await service.cleanup_sessions()

            # Verify cleanup had errors
            assert len(result.errors) > 0

            # Verify metrics were recorded with failure status
            mock_record.assert_called_once_with(data_type="sessions", status="failure", count=0)

    @pytest.mark.asyncio
    async def test_cleanup_conversations_records_success_metrics(self) -> None:
        """Verify cleanup_conversations() records success metrics."""
        from mcp_server_langgraph.compliance.retention import DataRetentionService

        # Create mock conversation store
        mock_conversation_store = MagicMock()

        service = DataRetentionService(
            config_path="nonexistent.yaml",
            session_store=None,
            conversation_store=mock_conversation_store,
            audit_log_store=None,
            dry_run=False,
        )

        with patch("mcp_server_langgraph.compliance.retention.record_gdpr_retention_cleanup") as mock_record:
            result = await service.cleanup_conversations()

            # Verify cleanup result
            assert result.policy_name == "conversations"

            # Verify metrics were recorded (placeholder implementation returns 0)
            mock_record.assert_called_once_with(data_type="conversations", status="success", count=0)

    @pytest.mark.asyncio
    async def test_cleanup_audit_logs_records_success_metrics(self) -> None:
        """Verify cleanup_audit_logs() records success metrics."""
        from mcp_server_langgraph.compliance.retention import DataRetentionService

        # Create mock audit log store
        mock_audit_log_store = MagicMock()

        service = DataRetentionService(
            config_path="nonexistent.yaml",
            session_store=None,
            conversation_store=None,
            audit_log_store=mock_audit_log_store,
            dry_run=False,
        )

        with patch("mcp_server_langgraph.compliance.retention.record_gdpr_retention_cleanup") as mock_record:
            result = await service.cleanup_audit_logs()

            # Verify cleanup result
            assert result.policy_name == "audit_logs"

            # Verify metrics were recorded (placeholder implementation returns 0)
            mock_record.assert_called_once_with(data_type="audit_logs", status="success", count=0)
