"""
Audit log partitioning utilities.

Provides utilities for PostgreSQL table partitioning:
- Monthly partition name generation
- Partition DDL creation
- Retention management via partition drops

Partitioning enables O(1) retention cleanup via DROP PARTITION
instead of O(n) DELETE operations, critical for compliance at scale.
"""

from datetime import UTC, datetime
from dateutil.relativedelta import relativedelta


def get_partition_name(timestamp: datetime) -> str:
    """
    Generate partition name for a given timestamp.

    Partitions are named using format: audit_logs_YYYY_MM

    Args:
        timestamp: The timestamp to generate partition name for.

    Returns:
        Partition table name (e.g., "audit_logs_2025_12").
    """
    return f"audit_logs_{timestamp.year:04d}_{timestamp.month:02d}"


def create_partition_ddl(year: int, month: int) -> str:
    """
    Generate DDL for creating a monthly partition.

    Creates a partition covering the entire month from the 1st
    to the 1st of the following month.

    Args:
        year: The year for the partition.
        month: The month for the partition (1-12).

    Returns:
        CREATE TABLE DDL for the partition.
    """
    # Calculate partition boundaries
    start_date = datetime(year, month, 1, tzinfo=UTC)
    end_date = start_date + relativedelta(months=1)

    partition_name = f"audit_logs_{year:04d}_{month:02d}"
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    return f"""CREATE TABLE IF NOT EXISTS {partition_name}
    PARTITION OF audit_logs
    FOR VALUES FROM ('{start_str}') TO ('{end_str}')"""


def drop_partition_ddl(partition_name: str) -> str:
    """
    Generate DDL for dropping a partition.

    Uses DROP TABLE IF EXISTS for safe deletion.

    Args:
        partition_name: The partition table name to drop.

    Returns:
        DROP TABLE DDL for the partition.
    """
    return f"DROP TABLE IF EXISTS {partition_name}"


def get_expired_partition_names(
    reference_date: datetime,
    retention_months: int,
) -> list[str]:
    """
    Get list of partition names that have exceeded retention.

    Returns partition names for months that are older than
    the retention period from the reference date.

    Args:
        reference_date: Date to calculate retention from.
        retention_months: Number of months to retain data.

    Returns:
        List of expired partition names.
    """
    cutoff_date = reference_date - relativedelta(months=retention_months)

    expired = []
    # Generate partitions from a reasonable past (10 years before cutoff)
    # to one month before cutoff
    check_date = cutoff_date - relativedelta(years=10)

    while check_date < cutoff_date:
        expired.append(get_partition_name(check_date))
        check_date = check_date + relativedelta(months=1)

    return expired


def calculate_retention_boundary_partition(
    reference_date: datetime,
    retention_months: int,
) -> str:
    """
    Calculate the oldest partition that should be retained.

    This is the boundary - partitions before this should be dropped.

    Args:
        reference_date: Date to calculate retention from.
        retention_months: Number of months to retain data.

    Returns:
        Partition name at the retention boundary.
    """
    boundary_date = reference_date - relativedelta(months=retention_months)
    return get_partition_name(boundary_date)


def generate_initial_partition_ddls(
    start_year: int,
    start_month: int,
    count_months: int,
) -> list[str]:
    """
    Generate DDL statements for initial partition creation.

    Creates a sequence of monthly partitions starting from
    the given year/month for the specified number of months.

    Args:
        start_year: Starting year.
        start_month: Starting month (1-12).
        count_months: Number of monthly partitions to create.

    Returns:
        List of CREATE TABLE DDL statements.
    """
    ddls = []
    current = datetime(start_year, start_month, 1, tzinfo=UTC)

    for _ in range(count_months):
        ddls.append(create_partition_ddl(current.year, current.month))
        current = current + relativedelta(months=1)

    return ddls


def get_partition_table_setup_ddl() -> str:
    """
    Generate DDL for setting up partitioned audit_logs table.

    This DDL converts the audit_logs table to use
    RANGE partitioning by timestamp.

    Note: In production, this requires careful migration as
    existing data must be migrated to partitions.

    Returns:
        DDL for partitioned table setup.
    """
    return """-- Create partitioned audit_logs table
-- Note: Existing data must be migrated first

CREATE TABLE IF NOT EXISTS audit_logs_partitioned (
    id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    event_type VARCHAR(50),
    actor_id VARCHAR(255),
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    action TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    metadata JSONB,
    -- Unified audit facility columns
    category VARCHAR(50),
    outcome VARCHAR(20),
    actor_type VARCHAR(20),
    organization_id VARCHAR(255),
    trace_id VARCHAR(64),
    span_id VARCHAR(32),
    session_id VARCHAR(255),
    ai_operation JSONB,
    sequence_number BIGINT,
    previous_hash VARCHAR(64),
    event_hash VARCHAR(64),
    regulation_tags VARCHAR(20)[],
    retention_days INTEGER DEFAULT 2555,
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create indices on partitioned table
CREATE INDEX IF NOT EXISTS idx_audit_partitioned_category
    ON audit_logs_partitioned(category) WHERE category IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_partitioned_timestamp
    ON audit_logs_partitioned(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_partitioned_actor
    ON audit_logs_partitioned(actor_id) WHERE actor_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_partitioned_regulation
    ON audit_logs_partitioned USING GIN(regulation_tags)
    WHERE regulation_tags IS NOT NULL;
"""
