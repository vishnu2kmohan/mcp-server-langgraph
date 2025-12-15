"""
Tests for audit log partitioning configuration and utilities.

TDD RED phase: These tests define expected behavior for partitioning support.

The partitioning system should:
- Support monthly partitions for audit_logs
- Provide partition management utilities
- Generate partition DDL statements
- Calculate partition names from timestamps
"""

import gc
from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_partitioning")
class TestPartitionNameGeneration:
    """Tests for partition name generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_partition_name_from_timestamp(self) -> None:
        """GIVEN timestamp WHEN generating name THEN format correct."""
        from mcp_server_langgraph.audit.partitions import get_partition_name

        timestamp = datetime(2025, 12, 15, 10, 30, 0, tzinfo=UTC)
        name = get_partition_name(timestamp)

        assert name == "audit_logs_2025_12"

    def test_partition_name_different_months(self) -> None:
        """GIVEN different months WHEN generating names THEN unique."""
        from mcp_server_langgraph.audit.partitions import get_partition_name

        jan = datetime(2025, 1, 1, tzinfo=UTC)
        feb = datetime(2025, 2, 1, tzinfo=UTC)

        assert get_partition_name(jan) == "audit_logs_2025_01"
        assert get_partition_name(feb) == "audit_logs_2025_02"

    def test_partition_name_year_boundary(self) -> None:
        """GIVEN year boundary WHEN generating names THEN handles correctly."""
        from mcp_server_langgraph.audit.partitions import get_partition_name

        dec_2024 = datetime(2024, 12, 31, tzinfo=UTC)
        jan_2025 = datetime(2025, 1, 1, tzinfo=UTC)

        assert get_partition_name(dec_2024) == "audit_logs_2024_12"
        assert get_partition_name(jan_2025) == "audit_logs_2025_01"


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_partitioning")
class TestPartitionDDLGeneration:
    """Tests for partition DDL generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_partition_ddl(self) -> None:
        """GIVEN year/month WHEN generating DDL THEN valid SQL returned."""
        from mcp_server_langgraph.audit.partitions import create_partition_ddl

        ddl = create_partition_ddl(2025, 12)

        assert "CREATE TABLE IF NOT EXISTS audit_logs_2025_12" in ddl
        assert "PARTITION OF audit_logs" in ddl
        assert "FOR VALUES FROM" in ddl

    def test_create_partition_ddl_date_range(self) -> None:
        """GIVEN month WHEN generating DDL THEN date range correct."""
        from mcp_server_langgraph.audit.partitions import create_partition_ddl

        ddl = create_partition_ddl(2025, 1)

        # January should span 2025-01-01 to 2025-02-01
        assert "'2025-01-01'" in ddl
        assert "'2025-02-01'" in ddl

    def test_create_partition_ddl_december(self) -> None:
        """GIVEN December WHEN generating DDL THEN spans to next year."""
        from mcp_server_langgraph.audit.partitions import create_partition_ddl

        ddl = create_partition_ddl(2025, 12)

        # December should span 2025-12-01 to 2026-01-01
        assert "'2025-12-01'" in ddl
        assert "'2026-01-01'" in ddl


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_partitioning")
class TestPartitionRetention:
    """Tests for partition-based retention management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_expired_partitions(self) -> None:
        """GIVEN retention policy WHEN querying THEN expired partitions returned."""
        from mcp_server_langgraph.audit.partitions import get_expired_partition_names

        # With 7 years retention (84 months), partitions older than that are expired
        now = datetime(2025, 12, 15, tzinfo=UTC)
        expired = get_expired_partition_names(
            reference_date=now,
            retention_months=84,  # 7 years
        )

        # 84 months before Dec 2025 is Dec 2018
        # So anything older than Dec 2018 should be expired
        assert "audit_logs_2018_11" in expired
        assert "audit_logs_2018_12" not in expired

    def test_drop_partition_ddl(self) -> None:
        """GIVEN partition name WHEN generating drop DDL THEN valid SQL."""
        from mcp_server_langgraph.audit.partitions import drop_partition_ddl

        ddl = drop_partition_ddl("audit_logs_2018_06")

        assert "DROP TABLE IF EXISTS audit_logs_2018_06" in ddl

    def test_calculate_retention_partition_names(self) -> None:
        """GIVEN retention months WHEN calculating THEN correct partitions."""
        from mcp_server_langgraph.audit.partitions import (
            calculate_retention_boundary_partition,
        )

        # 7 years = 84 months, calculate boundary
        now = datetime(2025, 12, 15, tzinfo=UTC)
        boundary = calculate_retention_boundary_partition(
            reference_date=now,
            retention_months=84,
        )

        # 84 months before Dec 2025 = Dec 2018
        assert boundary == "audit_logs_2018_12"


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_partitioning")
class TestPartitionMigrationHelpers:
    """Tests for migration helper functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_generate_initial_partitions(self) -> None:
        """GIVEN start date WHEN generating THEN partitions for 2 years created."""
        from mcp_server_langgraph.audit.partitions import generate_initial_partition_ddls

        # Generate 2 years of monthly partitions
        ddls = generate_initial_partition_ddls(
            start_year=2025,
            start_month=1,
            count_months=24,
        )

        assert len(ddls) == 24
        assert "audit_logs_2025_01" in ddls[0]
        assert "audit_logs_2026_12" in ddls[-1]

    def test_partition_table_conversion_ddl(self) -> None:
        """GIVEN existing table WHEN converting THEN valid DDL generated."""
        from mcp_server_langgraph.audit.partitions import (
            get_partition_table_setup_ddl,
        )

        ddl = get_partition_table_setup_ddl()

        # Should create partitioned table structure
        assert "PARTITION BY RANGE" in ddl
        assert "timestamp" in ddl.lower()
