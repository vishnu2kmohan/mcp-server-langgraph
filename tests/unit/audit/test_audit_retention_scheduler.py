"""
Tests for audit log partition retention scheduler.

TDD RED phase: These tests define expected behavior for retention management.

The retention scheduler should:
- Run periodically to clean up expired partitions
- Calculate expired partitions based on retention policy
- Drop partitions using O(1) DROP TABLE operations
- Support different retention periods for regulations (FedRAMP 7yr, HIPAA 6yr)
- Log cleanup actions for audit trail
"""

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_retention_scheduler")
class TestPartitionRetentionScheduler:
    """Tests for partition retention scheduler."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_scheduler_with_retention_config_stores_settings(self) -> None:
        """
        GIVEN retention configuration
        WHEN scheduler is created
        THEN it initializes with correct settings.
        """
        from mcp_server_langgraph.audit.retention_scheduler import (
            PartitionRetentionScheduler,
        )

        scheduler = PartitionRetentionScheduler(
            retention_months=84,  # 7 years for FedRAMP
            schedule_hours=24,
        )

        assert scheduler.retention_months == 84
        assert scheduler.schedule_hours == 24

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self) -> None:
        """
        GIVEN a retention scheduler
        WHEN started and stopped
        THEN it manages its lifecycle correctly.
        """
        from mcp_server_langgraph.audit.retention_scheduler import (
            PartitionRetentionScheduler,
        )

        scheduler = PartitionRetentionScheduler(
            retention_months=84,
            schedule_hours=24,
        )

        await scheduler.start()
        assert scheduler.is_running is True

        await scheduler.stop()
        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_scheduler_identifies_expired_partitions(self) -> None:
        """
        GIVEN partitions older than retention period
        WHEN scheduler runs cleanup
        THEN it identifies correct partitions to drop.
        """
        from mcp_server_langgraph.audit.retention_scheduler import (
            PartitionRetentionScheduler,
        )

        # Create scheduler with 7 year retention
        scheduler = PartitionRetentionScheduler(
            retention_months=84,
            schedule_hours=24,
        )

        # Mock the database executor
        mock_executor = AsyncMock(return_value=None)  # async-mock-configured
        mock_executor.get_existing_partitions = AsyncMock(
            return_value=[
                "audit_logs_2017_01",  # Expired (>7 years old)
                "audit_logs_2017_06",  # Expired
                "audit_logs_2018_01",  # Might be expired depending on current date
                "audit_logs_2024_01",  # Not expired
                "audit_logs_2025_01",  # Not expired
            ]
        )
        mock_executor.drop_partition = AsyncMock(return_value=None)  # async-mock-configured

        # Run cleanup with reference date
        reference_date = datetime(2025, 12, 15, tzinfo=UTC)
        result = await scheduler.run_cleanup(
            executor=mock_executor,
            reference_date=reference_date,
        )

        # Partitions older than Dec 2018 (84 months before Dec 2025) should be dropped
        assert result.partitions_dropped >= 2
        assert "audit_logs_2017_01" in result.dropped_names
        assert "audit_logs_2017_06" in result.dropped_names

    @pytest.mark.asyncio
    async def test_scheduler_records_cleanup_metrics(self) -> None:
        """
        GIVEN a cleanup run
        WHEN partitions are dropped
        THEN metrics are recorded.
        """
        from mcp_server_langgraph.audit.retention_scheduler import (
            PartitionRetentionScheduler,
        )

        scheduler = PartitionRetentionScheduler(
            retention_months=84,
            schedule_hours=24,
        )

        mock_executor = AsyncMock(return_value=None)  # async-mock-configured
        mock_executor.get_existing_partitions = AsyncMock(return_value=[])
        mock_executor.drop_partition = AsyncMock(return_value=None)  # async-mock-configured

        mock_metrics = MagicMock()
        scheduler.set_metrics(mock_metrics)

        reference_date = datetime(2025, 12, 15, tzinfo=UTC)
        await scheduler.run_cleanup(
            executor=mock_executor,
            reference_date=reference_date,
        )

        # Metrics should be recorded
        mock_metrics.record_retention_cleanup.assert_called()


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_retention_scheduler")
class TestPartitionRetentionExecutor:
    """Tests for partition retention executor (database operations)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_get_existing_partitions(self) -> None:
        """
        GIVEN a PostgreSQL database with partitions
        WHEN querying existing partitions
        THEN returns list of partition names.
        """
        from mcp_server_langgraph.audit.retention_scheduler import (
            PartitionRetentionExecutor,
        )

        # Mock async session
        mock_session = AsyncMock(return_value=None)  # async-mock-configured
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            "audit_logs_2024_01",
            "audit_logs_2024_02",
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        executor = PartitionRetentionExecutor(session=mock_session)
        partitions = await executor.get_existing_partitions()

        assert "audit_logs_2024_01" in partitions
        assert "audit_logs_2024_02" in partitions

    @pytest.mark.asyncio
    async def test_drop_partition(self) -> None:
        """
        GIVEN a partition name
        WHEN dropping partition
        THEN executes DROP TABLE DDL.
        """
        from mcp_server_langgraph.audit.retention_scheduler import (
            PartitionRetentionExecutor,
        )

        mock_session = AsyncMock(return_value=None)  # async-mock-configured
        executor = PartitionRetentionExecutor(session=mock_session)

        await executor.drop_partition("audit_logs_2017_01")

        # Verify execute was called (for DROP TABLE)
        mock_session.execute.assert_called()
        # Verify commit was called after drop
        mock_session.commit.assert_called()


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_retention_scheduler")
class TestRetentionCleanupResult:
    """Tests for cleanup result data class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_cleanup_result_properties(self) -> None:
        """
        GIVEN cleanup result data
        WHEN accessing properties
        THEN values are correct.
        """
        from mcp_server_langgraph.audit.retention_scheduler import (
            RetentionCleanupResult,
        )

        result = RetentionCleanupResult(
            partitions_checked=10,
            partitions_dropped=2,
            dropped_names=["audit_logs_2017_01", "audit_logs_2017_06"],
            errors=[],
            duration_ms=150.5,
        )

        assert result.partitions_checked == 10
        assert result.partitions_dropped == 2
        assert len(result.dropped_names) == 2
        assert result.duration_ms == 150.5
        assert result.success is True

    def test_cleanup_result_with_errors(self) -> None:
        """
        GIVEN cleanup with errors
        WHEN checking success
        THEN returns False.
        """
        from mcp_server_langgraph.audit.retention_scheduler import (
            RetentionCleanupResult,
        )

        result = RetentionCleanupResult(
            partitions_checked=10,
            partitions_dropped=1,
            dropped_names=["audit_logs_2017_01"],
            errors=["Failed to drop audit_logs_2017_06: permission denied"],
            duration_ms=200.0,
        )

        assert result.success is False
        assert len(result.errors) == 1


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_retention_scheduler")
class TestRetentionSchedulerFactory:
    """Tests for retention scheduler factory function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_retention_scheduler(self) -> None:
        """
        GIVEN retention configuration
        WHEN creating scheduler via factory
        THEN scheduler is configured correctly.
        """
        from mcp_server_langgraph.audit.retention_scheduler import (
            create_retention_scheduler,
        )

        scheduler = create_retention_scheduler(
            retention_months=72,  # 6 years for HIPAA
            schedule_hours=12,
        )

        assert scheduler.retention_months == 72
        assert scheduler.schedule_hours == 12

    def test_create_retention_scheduler_defaults(self) -> None:
        """
        GIVEN no configuration
        WHEN creating scheduler via factory
        THEN uses FedRAMP defaults (7 years, daily).
        """
        from mcp_server_langgraph.audit.retention_scheduler import (
            create_retention_scheduler,
        )

        scheduler = create_retention_scheduler()

        assert scheduler.retention_months == 84  # 7 years default
        assert scheduler.schedule_hours == 24  # Daily default
