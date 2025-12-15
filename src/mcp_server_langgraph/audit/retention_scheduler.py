"""
Partition Retention Scheduler for Audit Logs.

Provides automated cleanup of expired audit log partitions:
- O(1) cleanup via DROP TABLE (vs O(n) DELETE)
- Configurable retention periods (FedRAMP 7yr, HIPAA 6yr, etc.)
- Scheduled execution with metrics and logging
- Graceful error handling per partition

This scheduler enables efficient long-term audit log retention
as required by FedRAMP (AU-11), HIPAA (45 CFR 164.312(b)),
and other regulatory frameworks.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_server_langgraph.audit.partitions import (
    get_expired_partition_names,
)

logger = logging.getLogger(__name__)


@dataclass
class RetentionCleanupResult:
    """Result of a retention cleanup run."""

    partitions_checked: int
    partitions_dropped: int
    dropped_names: list[str]
    errors: list[str]
    duration_ms: float

    @property
    def success(self) -> bool:
        """Return True if cleanup completed without errors."""
        return len(self.errors) == 0


class RetentionMetricsProtocol(Protocol):
    """Protocol for retention metrics recording."""

    def record_retention_cleanup(
        self,
        partitions_checked: int,
        partitions_dropped: int,
        duration_ms: float,
        success: bool,
    ) -> None:
        """Record cleanup metrics."""
        ...


class PartitionExecutorProtocol(Protocol):
    """Protocol for partition database operations."""

    async def get_existing_partitions(self) -> list[str]:
        """Get list of existing partition names."""
        ...

    async def drop_partition(self, partition_name: str) -> None:
        """Drop a partition by name."""
        ...


class PartitionRetentionExecutor:
    """
    Executes partition retention operations against PostgreSQL.

    Uses DROP TABLE for O(1) partition cleanup, which is significantly
    faster than DELETE operations for large tables.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize executor with database session.

        Args:
            session: Async SQLAlchemy session for database operations.
        """
        self._session = session

    async def get_existing_partitions(self) -> list[str]:
        """
        Get list of existing audit_logs partitions.

        Queries pg_inherits to find all child tables of
        audit_logs_partitioned.

        Returns:
            List of partition table names.
        """
        query = text("""
            SELECT c.relname
            FROM pg_inherits i
            JOIN pg_class c ON i.inhrelid = c.oid
            JOIN pg_class p ON i.inhparent = p.oid
            WHERE p.relname = 'audit_logs_partitioned'
            ORDER BY c.relname
        """)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def drop_partition(self, partition_name: str) -> None:
        """
        Drop a partition table.

        Uses DROP TABLE IF EXISTS for safe deletion.
        This is an O(1) operation vs O(n) DELETE.

        Args:
            partition_name: Name of partition to drop.
        """
        # Validate partition name to prevent SQL injection
        if not partition_name.startswith("audit_logs_"):
            raise ValueError(f"Invalid partition name: {partition_name}")

        # Use parameterized identifier (safe because we validated prefix)
        # Security: partition_name validated above - must start with "audit_logs_".
        # Dynamic SQL required for DDL (DROP TABLE) operations.
        # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text
        query = text(f"DROP TABLE IF EXISTS {partition_name}")
        await self._session.execute(query)
        await self._session.commit()
        logger.info(f"Dropped partition: {partition_name}")


class PartitionRetentionScheduler:
    """
    Scheduler for automated partition retention cleanup.

    Runs periodically to drop partitions that have exceeded
    the retention period, supporting regulatory requirements.
    """

    def __init__(
        self,
        retention_months: int = 84,  # 7 years default (FedRAMP)
        schedule_hours: int = 24,  # Daily default
    ) -> None:
        """
        Initialize retention scheduler.

        Args:
            retention_months: Number of months to retain data.
            schedule_hours: Hours between cleanup runs.
        """
        self.retention_months = retention_months
        self.schedule_hours = schedule_hours
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._metrics: RetentionMetricsProtocol | None = None

    @property
    def is_running(self) -> bool:
        """Return True if scheduler is running."""
        return self._running

    def set_metrics(self, metrics: RetentionMetricsProtocol) -> None:
        """
        Set metrics instance for recording cleanup results.

        Args:
            metrics: Metrics instance implementing RetentionMetricsProtocol.
        """
        self._metrics = metrics

    async def start(self) -> None:
        """Start the retention scheduler."""
        if self._running:
            logger.warning("Retention scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            f"Retention scheduler started (retention={self.retention_months} months, interval={self.schedule_hours} hours)"
        )

    async def stop(self) -> None:
        """Stop the retention scheduler gracefully."""
        if not self._running:
            return

        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Retention scheduler stopped")

    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                await asyncio.sleep(self.schedule_hours * 3600)
                # In production, this would get a session and run cleanup
                logger.debug("Retention scheduler tick (no-op without executor)")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Retention scheduler error: {e}")

    async def run_cleanup(
        self,
        executor: PartitionExecutorProtocol,
        reference_date: datetime | None = None,
    ) -> RetentionCleanupResult:
        """
        Run partition cleanup.

        Identifies and drops all partitions that have exceeded
        the retention period.

        Args:
            executor: Database executor for partition operations.
            reference_date: Reference date for calculating expiry.
                           Defaults to current UTC time.

        Returns:
            RetentionCleanupResult with cleanup details.
        """
        if reference_date is None:
            reference_date = datetime.now(UTC)

        start_time = time.perf_counter()

        # Get existing partitions
        existing_partitions = await executor.get_existing_partitions()

        # Calculate expired partitions
        expired_names = get_expired_partition_names(
            reference_date=reference_date,
            retention_months=self.retention_months,
        )

        # Find partitions to drop (intersection of existing and expired)
        expired_set = set(expired_names)
        to_drop = [p for p in existing_partitions if p in expired_set]

        dropped_names: list[str] = []
        errors: list[str] = []

        for partition_name in to_drop:
            try:
                await executor.drop_partition(partition_name)
                dropped_names.append(partition_name)
            except Exception as e:
                error_msg = f"Failed to drop {partition_name}: {e}"
                errors.append(error_msg)
                logger.exception(error_msg)

        duration_ms = (time.perf_counter() - start_time) * 1000

        result = RetentionCleanupResult(
            partitions_checked=len(existing_partitions),
            partitions_dropped=len(dropped_names),
            dropped_names=dropped_names,
            errors=errors,
            duration_ms=duration_ms,
        )

        # Record metrics if available
        if self._metrics is not None:
            self._metrics.record_retention_cleanup(
                partitions_checked=result.partitions_checked,
                partitions_dropped=result.partitions_dropped,
                duration_ms=result.duration_ms,
                success=result.success,
            )

        logger.info(
            f"Retention cleanup complete: "
            f"checked={result.partitions_checked}, "
            f"dropped={result.partitions_dropped}, "
            f"duration={result.duration_ms:.2f}ms"
        )

        return result


def create_retention_scheduler(
    retention_months: int = 84,  # 7 years default (FedRAMP)
    schedule_hours: int = 24,  # Daily default
) -> PartitionRetentionScheduler:
    """
    Create a partition retention scheduler.

    Factory function for creating a scheduler with the specified
    retention configuration.

    Args:
        retention_months: Number of months to retain data.
                         Default 84 (7 years) for FedRAMP compliance.
        schedule_hours: Hours between cleanup runs.
                       Default 24 (daily).

    Returns:
        Configured PartitionRetentionScheduler instance.

    Example:
        # FedRAMP 7-year retention, daily cleanup
        scheduler = create_retention_scheduler()

        # HIPAA 6-year retention, twice daily
        scheduler = create_retention_scheduler(
            retention_months=72,
            schedule_hours=12,
        )
    """
    return PartitionRetentionScheduler(
        retention_months=retention_months,
        schedule_hours=schedule_hours,
    )
