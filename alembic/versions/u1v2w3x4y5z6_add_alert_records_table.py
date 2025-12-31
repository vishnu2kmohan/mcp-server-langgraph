"""Add alert_records table

Revision ID: u1v2w3x4y5z6
Revises: t0u1v2w3x4y5
Create Date: 2025-12-31

Creates the alert_records table for storing Alertmanager alerts.
This table was previously only created via SQLAlchemy create_all() and was
missing from Alembic migrations.

Table: alert_records
- Stores infrastructure alerts from Alertmanager
- Supports AI recommendation lookup
- Provides alert history and audit trail
- 30-day retention by default
"""

from typing import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "u1v2w3x4y5z6"
down_revision: str | None = "t0u1v2w3x4y5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create alert_records table."""
    # Create alert_records table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS alert_records (
            id SERIAL PRIMARY KEY,
            alert_id VARCHAR(255) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            severity VARCHAR(50) NOT NULL,
            state VARCHAR(50) NOT NULL,
            message TEXT NOT NULL DEFAULT '',
            labels JSONB NOT NULL DEFAULT '{}'::jsonb,
            annotations JSONB NOT NULL DEFAULT '{}'::jsonb,
            started_at TIMESTAMPTZ,
            ended_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            generator_url TEXT
        )
        """
    )

    # Indices for efficient queries
    op.execute("CREATE INDEX IF NOT EXISTS ix_alert_records_alert_id ON alert_records(alert_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_alert_records_severity ON alert_records(severity)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_alert_records_state ON alert_records(state)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_alert_records_started_at ON alert_records(started_at)")

    # Composite indices for common query patterns
    op.execute("CREATE INDEX IF NOT EXISTS ix_alerts_severity_state ON alert_records(severity, state)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_alerts_started_at_state ON alert_records(started_at, state)")

    # Comment on table
    op.execute("COMMENT ON TABLE alert_records IS 'Infrastructure alerts from Alertmanager for AI recommendations'")


def downgrade() -> None:
    """Drop alert_records table."""
    # Drop indices
    op.execute("DROP INDEX IF EXISTS ix_alerts_started_at_state")
    op.execute("DROP INDEX IF EXISTS ix_alerts_severity_state")
    op.execute("DROP INDEX IF EXISTS ix_alert_records_started_at")
    op.execute("DROP INDEX IF EXISTS ix_alert_records_state")
    op.execute("DROP INDEX IF EXISTS ix_alert_records_severity")
    op.execute("DROP INDEX IF EXISTS ix_alert_records_alert_id")

    # Drop table
    op.execute("DROP TABLE IF EXISTS alert_records CASCADE")
