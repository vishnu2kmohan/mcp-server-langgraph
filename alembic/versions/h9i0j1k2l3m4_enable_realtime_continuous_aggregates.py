"""Enable real-time aggregation on continuous aggregates

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2026-03-20

Changes materialized_only from true to false on daily_cost_summary and
hourly_cost_summary continuous aggregates. With real-time aggregation enabled,
queries merge pre-computed data with recent un-materialized data from the raw
hypertable, ensuring aggregation results are always current.

Without this, get_cost_summary() and get_cost_by_model() return stale data
until the refresh policy runs (every 1-2 hours).
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h9i0j1k2l3m4"
down_revision: str | None = "g8h9i0j1k2l3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable real-time aggregation on cost continuous aggregates."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM timescaledb_information.continuous_aggregates
                WHERE view_name = 'daily_cost_summary'
            ) THEN
                ALTER MATERIALIZED VIEW daily_cost_summary
                    SET (timescaledb.materialized_only = false);
                RAISE NOTICE 'Enabled real-time aggregation on daily_cost_summary';
            END IF;

            IF EXISTS (
                SELECT 1 FROM timescaledb_information.continuous_aggregates
                WHERE view_name = 'hourly_cost_summary'
            ) THEN
                ALTER MATERIALIZED VIEW hourly_cost_summary
                    SET (timescaledb.materialized_only = false);
                RAISE NOTICE 'Enabled real-time aggregation on hourly_cost_summary';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """Revert to materialized-only aggregation."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM timescaledb_information.continuous_aggregates
                WHERE view_name = 'daily_cost_summary'
            ) THEN
                ALTER MATERIALIZED VIEW daily_cost_summary
                    SET (timescaledb.materialized_only = true);
                RAISE NOTICE 'Reverted daily_cost_summary to materialized-only';
            END IF;

            IF EXISTS (
                SELECT 1 FROM timescaledb_information.continuous_aggregates
                WHERE view_name = 'hourly_cost_summary'
            ) THEN
                ALTER MATERIALIZED VIEW hourly_cost_summary
                    SET (timescaledb.materialized_only = true);
                RAISE NOTICE 'Reverted hourly_cost_summary to materialized-only';
            END IF;
        END $$;
        """
    )
