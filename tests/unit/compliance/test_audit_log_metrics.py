"""
TDD tests for audit log store metrics.

Verifies that audit log operations record metrics via record_audit_log().
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.compliance
@pytest.mark.metrics
@pytest.mark.xdist_group(name="audit_log_metrics")
class TestAuditLogStoreMetrics:
    """Test audit log store metrics are recorded during operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_postgres_audit_log_records_metrics_on_log(self) -> None:
        """Verify PostgresAuditLogStore.log() records audit log metrics."""
        from mcp_server_langgraph.compliance.gdpr.postgres_storage import PostgresAuditLogStore
        from mcp_server_langgraph.compliance.gdpr.storage import AuditLogEntry

        # Create test audit log entry
        entry = AuditLogEntry(
            log_id="test-log-id-123",
            user_id="user:test",
            action="login",
            resource_type="session",
            resource_id="session-123",
            timestamp="2025-01-01T00:00:00Z",
            ip_address="192.168.1.1",
            user_agent="test-agent",
            metadata={"browser": "chrome"},
        )

        # Create a proper mock connection pool with context manager support
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock(return_value=None)

        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        # Create store and inject mock pool
        store = PostgresAuditLogStore(pool=mock_pool)

        with patch("mcp_server_langgraph.compliance.gdpr.postgres_storage.record_audit_log") as mock_record:
            log_id = await store.log(entry)

            # Verify log was created
            assert log_id == "test-log-id-123"

            # Verify metrics were recorded
            mock_record.assert_called_once_with(event_type="login")

    @pytest.mark.asyncio
    async def test_inmemory_audit_log_records_metrics_on_log(self) -> None:
        """Verify InMemoryAuditLogStore.log() records audit log metrics."""
        from mcp_server_langgraph.compliance.gdpr.storage import AuditLogEntry, InMemoryAuditLogStore

        store = InMemoryAuditLogStore()

        # Create test audit log entry
        entry = AuditLogEntry(
            log_id="test-log-id-456",
            user_id="user:test",
            action="logout",
            resource_type="session",
            resource_id="session-456",
            timestamp="2025-01-01T00:00:00Z",
            ip_address="192.168.1.1",
            user_agent="test-agent",
            metadata={},
        )

        with patch("mcp_server_langgraph.compliance.gdpr.storage.record_audit_log") as mock_record:
            log_id = await store.log(entry)

            # Verify log was created
            assert log_id == "test-log-id-456"

            # Verify metrics were recorded
            mock_record.assert_called_once_with(event_type="logout")

    @pytest.mark.asyncio
    async def test_audit_log_records_anonymization_metrics(self) -> None:
        """Verify anonymize_user_logs() records GDPR anonymization metrics."""
        from mcp_server_langgraph.compliance.gdpr.storage import AuditLogEntry, InMemoryAuditLogStore

        store = InMemoryAuditLogStore()

        # Create some audit logs first (without recording metrics)
        with patch("mcp_server_langgraph.compliance.gdpr.storage.record_audit_log"):
            for i in range(3):
                entry = AuditLogEntry(
                    log_id=f"test-log-{i}",
                    user_id="user:to-anonymize",
                    action="access",
                    resource_type="data",
                    resource_id=f"resource-{i}",
                    timestamp="2025-01-01T00:00:00Z",
                    ip_address=None,
                    user_agent=None,
                    metadata={},
                )
                await store.log(entry)

        with patch("mcp_server_langgraph.compliance.gdpr.storage.record_gdpr_anonymization") as mock_record:
            count = await store.anonymize_user_logs("user:to-anonymize")

            # Verify logs were anonymized
            assert count == 3

            # Verify metrics were recorded
            mock_record.assert_called_once_with(count=3, operation="audit_logs")
