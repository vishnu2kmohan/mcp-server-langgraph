"""Add organizational cost continuous aggregate

Creates a TimescaleDB continuous aggregate that pre-computes daily rollups
grouped by organizational hierarchy (organization_id, project_id, team_id).

This enables fast queries for:
- GET /cost/summary/by-organization
- GET /cost/summary/by-project
- GET /cost/summary/by-team

Revision ID: p6q7r8s9t0u1
Revises: o5p6q7r8s9t0
Create Date: 2025-12-28

Reference: Plan - Phase 3: TimescaleDB Continuous Aggregate with Organizational Dimensions
"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "p6q7r8s9t0u1"
down_revision: str | None = "o5p6q7r8s9t0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Create continuous aggregate for organizational cost rollups.

    This aggregate pre-computes daily totals grouped by:
    - organization_id
    - project_id
    - team_id
    - user_id (for drill-down)
    - model (for model-level analysis)
    - provider

    The refresh policy updates hourly with a 2-hour lag for data consistency.
    """

    # ==========================================================================
    # 1. CREATE ORGANIZATIONAL COST CONTINUOUS AGGREGATE
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
                -- Create organizational continuous aggregate if it doesn't exist
                IF NOT EXISTS (
                    SELECT 1 FROM timescaledb_information.continuous_aggregates
                    WHERE view_name = 'daily_cost_summary_org'
                ) THEN
                    CREATE MATERIALIZED VIEW daily_cost_summary_org
                    WITH (timescaledb.continuous) AS
                    SELECT
                        time_bucket('1 day', timestamp) AS bucket,
                        organization_id,
                        project_id,
                        team_id,
                        user_id,
                        model,
                        provider,
                        SUM(estimated_cost_usd) AS total_cost,
                        SUM(prompt_tokens) AS total_prompt_tokens,
                        SUM(completion_tokens) AS total_completion_tokens,
                        SUM(total_tokens) AS total_tokens,
                        COUNT(*) AS request_count
                    FROM token_usage_records
                    GROUP BY
                        bucket,
                        organization_id,
                        project_id,
                        team_id,
                        user_id,
                        model,
                        provider
                    WITH NO DATA;

                    RAISE NOTICE 'Created daily_cost_summary_org continuous aggregate';
                END IF;

                -- Add refresh policy: refresh every hour, with 2-hour lag
                PERFORM add_continuous_aggregate_policy(
                    'daily_cost_summary_org',
                    start_offset => INTERVAL '7 days',
                    end_offset => INTERVAL '2 hours',
                    schedule_interval => INTERVAL '1 hour',
                    if_not_exists => true
                );

                RAISE NOTICE 'Continuous aggregate refresh policy configured';
            ELSE
                RAISE NOTICE 'TimescaleDB not available - skipping org aggregate creation';
            END IF;
        END $$;
    """)

    # ==========================================================================
    # 2. CREATE INDICES ON CONTINUOUS AGGREGATE
    # ==========================================================================

    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM timescaledb_information.continuous_aggregates
                WHERE view_name = 'daily_cost_summary_org'
            ) THEN
                -- Index for organization cost queries
                CREATE INDEX IF NOT EXISTS ix_daily_cost_org_bucket
                ON daily_cost_summary_org (organization_id, bucket DESC);

                -- Index for project cost queries
                CREATE INDEX IF NOT EXISTS ix_daily_cost_project_bucket
                ON daily_cost_summary_org (project_id, bucket DESC);

                -- Index for team cost queries
                CREATE INDEX IF NOT EXISTS ix_daily_cost_team_bucket
                ON daily_cost_summary_org (team_id, bucket DESC);

                -- Index for org+project drill-down
                CREATE INDEX IF NOT EXISTS ix_daily_cost_org_project_bucket
                ON daily_cost_summary_org (organization_id, project_id, bucket DESC);

                -- Index for project+team drill-down
                CREATE INDEX IF NOT EXISTS ix_daily_cost_project_team_bucket
                ON daily_cost_summary_org (project_id, team_id, bucket DESC);

                RAISE NOTICE 'Created indices on daily_cost_summary_org';
            END IF;
        END $$;
    """)

    # ==========================================================================
    # 3. ADD RETENTION POLICY FOR AGGREGATE
    # ==========================================================================

    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM timescaledb_information.continuous_aggregates
                WHERE view_name = 'daily_cost_summary_org'
            ) THEN
                -- Keep organizational daily aggregates for 2 years
                -- (longer than raw data for historical reporting)
                PERFORM add_retention_policy(
                    'daily_cost_summary_org',
                    drop_after => INTERVAL '730 days',
                    if_not_exists => true
                );

                RAISE NOTICE 'Retention policy configured: 730 days';
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Remove organizational cost continuous aggregate."""

    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
            ) THEN
                -- Remove policies first
                PERFORM remove_retention_policy('daily_cost_summary_org', if_exists => true);
                PERFORM remove_continuous_aggregate_policy('daily_cost_summary_org', if_not_exists => true);

                -- Drop the aggregate
                DROP MATERIALIZED VIEW IF EXISTS daily_cost_summary_org CASCADE;

                RAISE NOTICE 'Dropped daily_cost_summary_org continuous aggregate';
            END IF;
        END $$;
    """)
