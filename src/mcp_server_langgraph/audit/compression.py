"""
Audit Log TimescaleDB Compression Scheduler.

Compresses audit partitions older than a configurable threshold using
TimescaleDB's native compression. This reduces storage by 10-20x while
keeping data queryable.

Features:
- Automatic detection of TimescaleDB availability
- Identifies partitions older than threshold (default: 90 days)
- Applies compression to eligible partitions
- Skips already-compressed partitions
- Graceful fallback on non-TimescaleDB deployments

Regulatory Context:
This supports long-term retention requirements for:
- FedRAMP AU-11: 7-year retention (reduced storage costs)
- HIPAA: 6-year retention
- GDPR: 7-year retention
- SOC 2: Audit data lifecycle management
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass
class CompressionResult:
    """Result of a compression run."""

    partitions_compressed: int = 0
    partitions_skipped: int = 0
    bytes_before: int = 0
    bytes_after: int = 0
    compression_ratio: float = 0.0
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)
    skipped_reason: str | None = None


class DatabaseConnection(Protocol):
    """Protocol for database connection."""

    async def fetchval(self, query: str, *args: Any) -> Any:
        """Fetch a single value."""
        ...

    async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        """Fetch multiple rows."""
        ...

    async def execute(self, query: str, *args: Any) -> None:
        """Execute a query."""
        ...


class AuditCompressionScheduler:
    """
    Scheduler for compressing old audit partitions using TimescaleDB.

    Compresses audit_logs_partitioned partitions older than compress_after_days
    to reduce storage costs while maintaining query capability.
    """

    def __init__(
        self,
        compress_after_days: int = 90,
        schedule_hours: int = 24,
    ) -> None:
        """
        Initialize the compression scheduler.

        Args:
            compress_after_days: Compress partitions older than this (default: 90).
            schedule_hours: Hours between compression runs (default: 24).
        """
        self.compress_after_days = compress_after_days
        self.schedule_hours = schedule_hours
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def is_timescaledb_available(self, conn: DatabaseConnection) -> bool:
        """
        Check if TimescaleDB extension is available.

        Args:
            conn: Database connection.

        Returns:
            True if TimescaleDB is installed, False otherwise.
        """
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
            )
        """)
        return bool(result)

    async def is_partition_compressed(self, conn: DatabaseConnection, partition_name: str) -> bool:
        """
        Check if a partition is already compressed.

        Args:
            conn: Database connection.
            partition_name: Name of the partition to check.

        Returns:
            True if already compressed, False otherwise.
        """
        # For native PostgreSQL partitions with TimescaleDB compression,
        # we check if the chunk has compression status
        result = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT 1 FROM timescaledb_information.chunks c
                WHERE c.chunk_name = $1
                AND c.is_compressed = true
            )
            """,
            partition_name,
        )
        return bool(result)

    async def get_compressible_partitions(self, conn: DatabaseConnection) -> list[str]:
        """
        Get list of partitions eligible for compression.

        Args:
            conn: Database connection.

        Returns:
            List of partition names that are old enough to compress.
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=self.compress_after_days)

        rows = await conn.fetch(
            """
            SELECT c.relname as partition_name
            FROM pg_inherits i
            JOIN pg_class c ON i.inhrelid = c.oid
            JOIN pg_class p ON i.inhparent = p.oid
            WHERE p.relname = 'audit_logs_partitioned'
            AND c.relname ~ '^audit_logs_\\d{4}_\\d{2}$'
            AND (
                -- Parse partition name to get date
                to_date(
                    substring(c.relname from 'audit_logs_(\\d{4})_(\\d{2})'),
                    'YYYY_MM'
                ) < $1::date
            )
            ORDER BY c.relname
            """,
            cutoff_date.date(),
        )

        return [row["partition_name"] for row in rows]

    async def compress_partition(self, conn: DatabaseConnection, partition_name: str) -> bool:
        """
        Compress a single partition using TimescaleDB.

        Args:
            conn: Database connection.
            partition_name: Name of the partition to compress.

        Returns:
            True if compression succeeded, False otherwise.
        """
        try:
            # For native PostgreSQL partitions, we use TimescaleDB's
            # compress_chunk if the partition is a TimescaleDB chunk
            # Security: partition_name is from internal queries (list_uncompressed_partitions),
            # not user input. TimescaleDB compress_chunk requires dynamic table names.
            await conn.execute(  # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
                f"""
                SELECT compress_chunk('{partition_name}'::regclass)
                """
            )
            logger.info(f"Compressed partition: {partition_name}")
            return True
        except Exception as e:
            logger.warning(f"Failed to compress {partition_name}: {e}")
            return False

    async def run_compression(self, conn: DatabaseConnection) -> CompressionResult:
        """
        Run compression on all eligible partitions.

        Args:
            conn: Database connection.

        Returns:
            CompressionResult with statistics.
        """
        start_time = time.time()
        result = CompressionResult()

        # Check if TimescaleDB is available
        if not await self.is_timescaledb_available(conn):
            result.skipped_reason = "TimescaleDB not available"
            logger.info("TimescaleDB not available, skipping compression")
            return result

        # Get eligible partitions
        partitions = await self.get_compressible_partitions(conn)

        if not partitions:
            logger.info("No partitions eligible for compression")
            return result

        # Compress each partition
        for partition_name in partitions:
            # Check if already compressed
            if await self.is_partition_compressed(conn, partition_name):
                result.partitions_skipped += 1
                continue

            # Compress the partition
            if await self.compress_partition(conn, partition_name):
                result.partitions_compressed += 1
            else:
                result.errors.append(f"Failed to compress {partition_name}")

        result.duration_seconds = time.time() - start_time
        logger.info(
            f"Compression completed: {result.partitions_compressed} compressed, "
            f"{result.partitions_skipped} skipped, {len(result.errors)} errors"
        )

        return result

    async def _run_scheduled(self, get_connection: Any) -> None:
        """Run compression on schedule."""
        while self._running:
            try:
                conn = await get_connection()
                try:
                    await self.run_compression(conn)
                finally:
                    await conn.close()
            except Exception as e:
                logger.exception(f"Scheduled compression failed: {e}")

            # Wait for next run
            await asyncio.sleep(self.schedule_hours * 3600)

    def schedule(self, get_connection: Any) -> asyncio.Task[None]:
        """
        Start scheduled compression.

        Args:
            get_connection: Async function to get database connection.

        Returns:
            Background task running the scheduler.
        """
        self._running = True
        self._task = asyncio.create_task(self._run_scheduled(get_connection))
        return self._task

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
