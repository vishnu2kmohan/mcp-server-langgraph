"""
Tests for Audit Log TimescaleDB Compression Scheduler.

TDD RED phase: These tests define expected behavior for the AuditCompressionScheduler
that compresses audit partitions older than 90 days using TimescaleDB.

The scheduler should:
- Identify partitions older than 90 days
- Apply TimescaleDB compression to those partitions
- Skip partitions that are already compressed
- Log compression statistics
- Handle non-TimescaleDB environments gracefully
"""

import gc
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit


def _create_mock_connection() -> AsyncMock:
    """Create a mock database connection."""
    mock = AsyncMock(return_value=None)  # async-mock-configured
    mock.fetchval = AsyncMock(return_value=True)
    mock.fetch = AsyncMock(return_value=[])
    mock.execute = AsyncMock(return_value=None)  # async-mock-configured
    return mock


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_compression")
class TestAuditCompressionScheduler:
    """Tests for AuditCompressionScheduler."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_check_timescaledb_available(self) -> None:
        """
        GIVEN a PostgreSQL connection
        WHEN checking TimescaleDB availability
        THEN returns True if extension exists.
        """
        from mcp_server_langgraph.audit.compression import AuditCompressionScheduler

        mock_conn = _create_mock_connection()
        mock_conn.fetchval.return_value = True

        scheduler = AuditCompressionScheduler()

        result = await scheduler.is_timescaledb_available(mock_conn)

        assert result is True
        mock_conn.fetchval.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_timescaledb_not_available(self) -> None:
        """
        GIVEN a PostgreSQL connection without TimescaleDB
        WHEN checking TimescaleDB availability
        THEN returns False.
        """
        from mcp_server_langgraph.audit.compression import AuditCompressionScheduler

        mock_conn = _create_mock_connection()
        mock_conn.fetchval.return_value = False

        scheduler = AuditCompressionScheduler()

        result = await scheduler.is_timescaledb_available(mock_conn)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_partitions_older_than_threshold(self) -> None:
        """
        GIVEN audit partitions exist
        WHEN querying for partitions older than 90 days
        THEN returns list of eligible partition names.
        """
        from mcp_server_langgraph.audit.compression import AuditCompressionScheduler

        mock_conn = _create_mock_connection()
        mock_conn.fetch.return_value = [
            {"partition_name": "audit_logs_2024_01"},
            {"partition_name": "audit_logs_2024_02"},
            {"partition_name": "audit_logs_2024_03"},
        ]

        scheduler = AuditCompressionScheduler(compress_after_days=90)

        partitions = await scheduler.get_compressible_partitions(mock_conn)

        assert len(partitions) == 3
        assert "audit_logs_2024_01" in partitions

    @pytest.mark.asyncio
    async def test_compress_partition(self) -> None:
        """
        GIVEN an uncompressed partition
        WHEN compressing
        THEN executes TimescaleDB compression.
        """
        from mcp_server_langgraph.audit.compression import AuditCompressionScheduler

        mock_conn = _create_mock_connection()

        scheduler = AuditCompressionScheduler()

        result = await scheduler.compress_partition(mock_conn, "audit_logs_2024_01")

        assert result is True
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_compress_partition_already_compressed(self) -> None:
        """
        GIVEN an already compressed partition
        WHEN compressing
        THEN skips and returns False.
        """
        from mcp_server_langgraph.audit.compression import AuditCompressionScheduler

        mock_conn = _create_mock_connection()
        # Simulate partition already compressed
        mock_conn.fetchval.return_value = True

        scheduler = AuditCompressionScheduler()

        result = await scheduler.is_partition_compressed(mock_conn, "audit_logs_2024_01")

        assert result is True

    @pytest.mark.asyncio
    async def test_run_compression_skips_if_no_timescaledb(self) -> None:
        """
        GIVEN TimescaleDB is not available
        WHEN running compression
        THEN skips gracefully without error.
        """
        from mcp_server_langgraph.audit.compression import (
            AuditCompressionScheduler,
            CompressionResult,
        )

        mock_conn = _create_mock_connection()
        mock_conn.fetchval.return_value = False  # TimescaleDB not available

        scheduler = AuditCompressionScheduler()

        result = await scheduler.run_compression(mock_conn)

        assert isinstance(result, CompressionResult)
        assert result.partitions_compressed == 0
        assert result.skipped_reason == "TimescaleDB not available"

    @pytest.mark.asyncio
    async def test_run_compression_compresses_eligible_partitions(self) -> None:
        """
        GIVEN TimescaleDB is available and partitions exist
        WHEN running compression
        THEN compresses eligible partitions.
        """
        from mcp_server_langgraph.audit.compression import (
            AuditCompressionScheduler,
            CompressionResult,
        )

        mock_conn = _create_mock_connection()

        # Mock TimescaleDB available
        mock_conn.fetchval.side_effect = [
            True,  # TimescaleDB available
            False,  # Partition 1 not compressed
            False,  # Partition 2 not compressed
        ]

        # Mock partitions list
        mock_conn.fetch.return_value = [
            {"partition_name": "audit_logs_2024_01"},
            {"partition_name": "audit_logs_2024_02"},
        ]

        scheduler = AuditCompressionScheduler(compress_after_days=90)

        result = await scheduler.run_compression(mock_conn)

        assert isinstance(result, CompressionResult)
        assert result.partitions_compressed == 2
        assert result.skipped_reason is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_compression")
class TestCompressionResult:
    """Tests for CompressionResult dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_compression_result_creation(self) -> None:
        """
        GIVEN compression stats
        WHEN creating CompressionResult
        THEN contains all expected fields.
        """
        from mcp_server_langgraph.audit.compression import CompressionResult

        result = CompressionResult(
            partitions_compressed=5,
            partitions_skipped=2,
            bytes_before=1000000,
            bytes_after=100000,
            compression_ratio=10.0,
            duration_seconds=5.5,
            errors=[],
        )

        assert result.partitions_compressed == 5
        assert result.partitions_skipped == 2
        assert result.compression_ratio == 10.0

    def test_compression_result_with_skip_reason(self) -> None:
        """
        GIVEN compression was skipped
        WHEN creating CompressionResult
        THEN includes skip reason.
        """
        from mcp_server_langgraph.audit.compression import CompressionResult

        result = CompressionResult(
            partitions_compressed=0,
            partitions_skipped=0,
            skipped_reason="TimescaleDB not available",
        )

        assert result.skipped_reason == "TimescaleDB not available"


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_compression")
class TestCompressionConfig:
    """Tests for compression configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_default_compress_after_days(self) -> None:
        """
        GIVEN no configuration
        WHEN creating scheduler
        THEN uses 90 day default.
        """
        from mcp_server_langgraph.audit.compression import AuditCompressionScheduler

        scheduler = AuditCompressionScheduler()

        assert scheduler.compress_after_days == 90

    def test_custom_compress_after_days(self) -> None:
        """
        GIVEN custom configuration
        WHEN creating scheduler
        THEN uses custom value.
        """
        from mcp_server_langgraph.audit.compression import AuditCompressionScheduler

        scheduler = AuditCompressionScheduler(compress_after_days=30)

        assert scheduler.compress_after_days == 30

    def test_scheduler_has_schedule_method(self) -> None:
        """
        GIVEN scheduler instance
        WHEN checking interface
        THEN has schedule method for background execution.
        """
        from mcp_server_langgraph.audit.compression import AuditCompressionScheduler

        scheduler = AuditCompressionScheduler()

        assert hasattr(scheduler, "schedule")
        assert callable(scheduler.schedule)
