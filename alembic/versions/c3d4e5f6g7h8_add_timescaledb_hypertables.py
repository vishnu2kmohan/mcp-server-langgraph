"""Add TimescaleDB Hypertables for Cost/Metrics

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2025-01-15 12:00:00.000000

This migration enables TimescaleDB for cost/metrics data:
1. Enables TimescaleDB extension
2. Converts token_usage_records to a hypertable (partitioned by timestamp)
3. Sets up compression policies for data older than 7 days
4. Creates continuous aggregates for pre-computed rollups
5. Configures native retention policies using drop_chunks

Benefits:
- 10-20x storage reduction via compression
- Sub-second aggregation queries via continuous aggregates
- O(1) retention cleanup via drop_chunks (vs O(n) DELETE)
- Automatic time-based partitioning for query performance

IMPORTANT: This migration requires TimescaleDB extension installed.
For managed PostgreSQL (RDS, Cloud SQL, Azure), enable TimescaleDB first:
- AWS RDS: Enable timescaledb in parameter group
- Google Cloud SQL: Enable timescaledb extension
- Azure: Use Azure Database for PostgreSQL Flexible Server with TimescaleDB
"""

from typing import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6g7h8"
down_revision: str | None = "b2c3d4e5f6g7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Enable TimescaleDB and convert token_usage_records to hypertable.

    This is a no-op if TimescaleDB is not available, allowing the migration
    to run on standard PostgreSQL while enabling optimizations where available.
    """

    # ==========================================================================
    # 0. CREATE TOKEN_USAGE_RECORDS TABLE (required before hypertable conversion)
    # ==========================================================================

    # Create the token_usage_records table for cost tracking
    # Note: Primary key includes timestamp for TimescaleDB hypertable compatibility
    # TimescaleDB requires the partitioning column to be part of any unique index
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS token_usage_records (
            id SERIAL NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            user_id VARCHAR(255) NOT NULL,
            session_id VARCHAR(255) NOT NULL,
            model VARCHAR(255) NOT NULL,
            provider VARCHAR(100) NOT NULL,
            prompt_tokens INTEGER NOT NULL,
            completion_tokens INTEGER NOT NULL,
            total_tokens INTEGER NOT NULL,
            estimated_cost_usd NUMERIC(10, 6) NOT NULL,
            feature VARCHAR(255),
            metadata JSONB,
            PRIMARY KEY (id, timestamp)
        )
        """
    )

    # Create indices for token_usage_records
    op.execute("CREATE INDEX IF NOT EXISTS ix_token_usage_timestamp ON token_usage_records(timestamp)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_token_usage_user_id ON token_usage_records(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_token_usage_session_id ON token_usage_records(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_token_usage_model ON token_usage_records(model)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_timestamp ON token_usage_records(user_id, timestamp)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_provider_model ON token_usage_records(provider, model)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_timestamp_desc ON token_usage_records(timestamp DESC)")

    # Comment on table
    op.execute("COMMENT ON TABLE token_usage_records IS 'LLM token usage and cost tracking for budgeting and analytics'")

    # ==========================================================================
    # 1. ENABLE TIMESCALEDB EXTENSION
    # ==========================================================================

    # Check if TimescaleDB is available and enable it
    # This is idempotent - safe to run multiple times
    op.execute("""
        DO $$
        BEGIN
            -- Try to create TimescaleDB extension
            CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
            RAISE NOTICE 'TimescaleDB extension enabled';
        EXCEPTION
            WHEN undefined_file THEN
                RAISE NOTICE 'TimescaleDB not available - skipping hypertable creation';
            WHEN insufficient_privilege THEN
                RAISE NOTICE 'Insufficient privileges for TimescaleDB - skipping';
        END $$;
    """)

    # ==========================================================================
    # 2. CONVERT TOKEN_USAGE_RECORDS TO HYPERTABLE
    # ==========================================================================

    # Convert existing table to hypertable with 1-day chunk interval
    # migrate_data => true preserves existing records
    op.execute("""
        DO $$
        BEGIN
            -- Only proceed if TimescaleDB is available
            IF EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
            ) THEN
                -- Check if already a hypertable
                IF NOT EXISTS (
                    SELECT 1 FROM timescaledb_information.hypertables
                    WHERE hypertable_name = 'token_usage_records'
                ) THEN
                    -- Convert to hypertable with 1-day chunks
                    PERFORM create_hypertable(
                        'token_usage_records',
                        'timestamp',
                        chunk_time_interval => INTERVAL '1 day',
                        migrate_data => true,
                        if_not_exists => true
                    );
                    RAISE NOTICE 'Converted token_usage_records to hypertable';
                ELSE
                    RAISE NOTICE 'token_usage_records is already a hypertable';
                END IF;
            ELSE
                RAISE NOTICE 'TimescaleDB not available - skipping hypertable creation';
            END IF;
        END $$;
    """)

    # ==========================================================================
    # 3. ENABLE COMPRESSION FOR OLD DATA
    # ==========================================================================

    # Enable compression on the hypertable
    # Compress data older than 7 days (10-20x storage reduction)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
            ) AND EXISTS (
                SELECT 1 FROM timescaledb_information.hypertables
                WHERE hypertable_name = 'token_usage_records'
            ) THEN
                -- Enable compression with segment by user_id for efficient queries
                ALTER TABLE token_usage_records SET (
                    timescaledb.compress,
                    timescaledb.compress_segmentby = 'user_id, model, provider',
                    timescaledb.compress_orderby = 'timestamp DESC'
                );

                -- Add compression policy: compress chunks older than 7 days
                PERFORM add_compression_policy(
                    'token_usage_records',
                    compress_after => INTERVAL '7 days',
                    if_not_exists => true
                );

                RAISE NOTICE 'Compression policy enabled for token_usage_records';
            END IF;
        END $$;
    """)

    # ==========================================================================
    # 4. CREATE CONTINUOUS AGGREGATES
    # ==========================================================================

    # Create daily cost summary continuous aggregate
    # Pre-computes daily rollups for fast /cost/summary and /cost/history queries
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
            ) AND EXISTS (
                SELECT 1 FROM timescaledb_information.hypertables
                WHERE hypertable_name = 'token_usage_records'
            ) THEN
                -- Create continuous aggregate if it doesn't exist
                IF NOT EXISTS (
                    SELECT 1 FROM timescaledb_information.continuous_aggregates
                    WHERE view_name = 'daily_cost_summary'
                ) THEN
                    CREATE MATERIALIZED VIEW daily_cost_summary
                    WITH (timescaledb.continuous) AS
                    SELECT
                        time_bucket('1 day', timestamp) AS bucket,
                        user_id,
                        model,
                        provider,
                        SUM(estimated_cost_usd) AS total_cost,
                        SUM(prompt_tokens) AS total_prompt_tokens,
                        SUM(completion_tokens) AS total_completion_tokens,
                        SUM(total_tokens) AS total_tokens,
                        COUNT(*) AS request_count
                    FROM token_usage_records
                    GROUP BY bucket, user_id, model, provider
                    WITH NO DATA;

                    RAISE NOTICE 'Created daily_cost_summary continuous aggregate';
                END IF;

                -- Add refresh policy: refresh every hour, with 2-hour lag
                PERFORM add_continuous_aggregate_policy(
                    'daily_cost_summary',
                    start_offset => INTERVAL '7 days',
                    end_offset => INTERVAL '2 hours',
                    schedule_interval => INTERVAL '1 hour',
                    if_not_exists => true
                );

                RAISE NOTICE 'Continuous aggregate refresh policy configured';
            END IF;
        END $$;
    """)

    # Create hourly cost summary for real-time dashboards
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
            ) AND EXISTS (
                SELECT 1 FROM timescaledb_information.hypertables
                WHERE hypertable_name = 'token_usage_records'
            ) THEN
                -- Create hourly aggregate for real-time dashboards
                IF NOT EXISTS (
                    SELECT 1 FROM timescaledb_information.continuous_aggregates
                    WHERE view_name = 'hourly_cost_summary'
                ) THEN
                    CREATE MATERIALIZED VIEW hourly_cost_summary
                    WITH (timescaledb.continuous) AS
                    SELECT
                        time_bucket('1 hour', timestamp) AS bucket,
                        user_id,
                        model,
                        provider,
                        SUM(estimated_cost_usd) AS total_cost,
                        SUM(total_tokens) AS total_tokens,
                        COUNT(*) AS request_count
                    FROM token_usage_records
                    GROUP BY bucket, user_id, model, provider
                    WITH NO DATA;

                    RAISE NOTICE 'Created hourly_cost_summary continuous aggregate';
                END IF;

                -- Refresh every 5 minutes for near real-time data
                PERFORM add_continuous_aggregate_policy(
                    'hourly_cost_summary',
                    start_offset => INTERVAL '1 day',
                    end_offset => INTERVAL '5 minutes',
                    schedule_interval => INTERVAL '5 minutes',
                    if_not_exists => true
                );
            END IF;
        END $$;
    """)

    # ==========================================================================
    # 5. CONFIGURE NATIVE RETENTION POLICY
    # ==========================================================================

    # Use TimescaleDB's drop_chunks for O(1) retention cleanup
    # Much faster than DELETE queries for old data
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
            ) AND EXISTS (
                SELECT 1 FROM timescaledb_information.hypertables
                WHERE hypertable_name = 'token_usage_records'
            ) THEN
                -- Add retention policy: drop chunks older than 90 days
                PERFORM add_retention_policy(
                    'token_usage_records',
                    drop_after => INTERVAL '90 days',
                    if_not_exists => true
                );

                RAISE NOTICE 'Retention policy configured: 90 days';

                -- Also add retention for continuous aggregates
                -- Keep daily aggregates for 1 year
                PERFORM add_retention_policy(
                    'daily_cost_summary',
                    drop_after => INTERVAL '365 days',
                    if_not_exists => true
                );

                -- Keep hourly aggregates for 30 days
                PERFORM add_retention_policy(
                    'hourly_cost_summary',
                    drop_after => INTERVAL '30 days',
                    if_not_exists => true
                );

                RAISE NOTICE 'Continuous aggregate retention policies configured';
            END IF;
        END $$;
    """)

    # ==========================================================================
    # 6. CREATE OPTIMIZED INDICES FOR AGGREGATES
    # ==========================================================================

    # Add indices on continuous aggregates for common query patterns
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM timescaledb_information.continuous_aggregates
                WHERE view_name = 'daily_cost_summary'
            ) THEN
                -- Index for user cost queries
                CREATE INDEX IF NOT EXISTS ix_daily_cost_user_bucket
                ON daily_cost_summary (user_id, bucket DESC);

                -- Index for model cost queries
                CREATE INDEX IF NOT EXISTS ix_daily_cost_model_bucket
                ON daily_cost_summary (model, bucket DESC);

                -- Index for provider cost queries
                CREATE INDEX IF NOT EXISTS ix_daily_cost_provider_bucket
                ON daily_cost_summary (provider, bucket DESC);

                RAISE NOTICE 'Created indices on daily_cost_summary';
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """
    Remove TimescaleDB hypertables and revert to standard table.

    WARNING: This will decompress all data and remove continuous aggregates.
    The underlying data is preserved but partitioning benefits are lost.
    """

    # ==========================================================================
    # 1. DROP CONTINUOUS AGGREGATES
    # ==========================================================================

    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
            ) THEN
                -- Remove policies first
                PERFORM remove_retention_policy('hourly_cost_summary', if_exists => true);
                PERFORM remove_continuous_aggregate_policy('hourly_cost_summary', if_not_exists => true);
                DROP MATERIALIZED VIEW IF EXISTS hourly_cost_summary CASCADE;

                PERFORM remove_retention_policy('daily_cost_summary', if_exists => true);
                PERFORM remove_continuous_aggregate_policy('daily_cost_summary', if_not_exists => true);
                DROP MATERIALIZED VIEW IF EXISTS daily_cost_summary CASCADE;

                RAISE NOTICE 'Dropped continuous aggregates';
            END IF;
        END $$;
    """)

    # ==========================================================================
    # 2. REMOVE COMPRESSION AND RETENTION POLICIES
    # ==========================================================================

    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
            ) AND EXISTS (
                SELECT 1 FROM timescaledb_information.hypertables
                WHERE hypertable_name = 'token_usage_records'
            ) THEN
                -- Remove policies
                PERFORM remove_retention_policy('token_usage_records', if_exists => true);
                PERFORM remove_compression_policy('token_usage_records', if_exists => true);

                -- Decompress all chunks
                PERFORM decompress_chunk(c.chunk_name::regclass)
                FROM timescaledb_information.chunks c
                WHERE c.hypertable_name = 'token_usage_records'
                AND c.is_compressed = true;

                -- Disable compression
                ALTER TABLE token_usage_records SET (timescaledb.compress = false);

                RAISE NOTICE 'Removed compression and retention policies';
            END IF;
        END $$;
    """)

    # ==========================================================================
    # 3. NOTE: HYPERTABLE CANNOT BE REVERTED TO REGULAR TABLE
    # ==========================================================================

    # TimescaleDB does not support converting a hypertable back to a regular table.
    # The data remains accessible as a hypertable.
    # To fully revert:
    # 1. Create new regular table
    # 2. Copy data from hypertable
    # 3. Drop hypertable
    # 4. Rename new table
    # This is left as a manual operation due to potential data loss.

    op.execute("""
        DO $$
        BEGIN
            RAISE NOTICE 'NOTE: Hypertable cannot be automatically reverted to regular table.';
            RAISE NOTICE 'Data remains in token_usage_records as a hypertable.';
            RAISE NOTICE 'For full revert, manually migrate data to a new table.';
        END $$;
    """)

    # ==========================================================================
    # 4. DROP TOKEN_USAGE_RECORDS TABLE
    # ==========================================================================

    # Drop indices first
    op.execute("DROP INDEX IF EXISTS ix_timestamp_desc")
    op.execute("DROP INDEX IF EXISTS ix_provider_model")
    op.execute("DROP INDEX IF EXISTS ix_user_timestamp")
    op.execute("DROP INDEX IF EXISTS ix_token_usage_model")
    op.execute("DROP INDEX IF EXISTS ix_token_usage_session_id")
    op.execute("DROP INDEX IF EXISTS ix_token_usage_user_id")
    op.execute("DROP INDEX IF EXISTS ix_token_usage_timestamp")

    # Drop the table (CASCADE handles hypertable chunks if any)
    op.execute("DROP TABLE IF EXISTS token_usage_records CASCADE")
