"""Add workflow_executions table

Revision ID: t0u1v2w3x4y5
Revises: s9t0u1v2w3x4
Create Date: 2025-12-31

Creates the workflow_executions table for storing workflow execution history.
This table was previously only created via SQLAlchemy create_all() and was
missing from Alembic migrations.

Table: workflow_executions
- Stores execution history for Agent Studio workflows
- Supports status filtering and pagination
- Composite indices for efficient queries
"""

from typing import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "t0u1v2w3x4y5"
down_revision: str | None = "s9t0u1v2w3x4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create workflow_executions table."""
    # Create workflow_executions table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS workflow_executions (
            id VARCHAR(36) PRIMARY KEY,
            workflow_id VARCHAR(36) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            completed_at TIMESTAMPTZ,
            input_data JSONB,
            output_data JSONB,
            error TEXT
        )
        """
    )

    # Indices for efficient queries
    op.execute("CREATE INDEX IF NOT EXISTS ix_workflow_executions_workflow_id ON workflow_executions(workflow_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_workflow_executions_status ON workflow_executions(status)")

    # Composite indices for optimized queries
    op.execute("CREATE INDEX IF NOT EXISTS ix_workflow_executions_workflow_status ON workflow_executions(workflow_id, status)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_workflow_executions_workflow_started ON workflow_executions(workflow_id, started_at)"
    )

    # Comment on table
    op.execute("COMMENT ON TABLE workflow_executions IS 'Workflow execution history for Agent Studio'")


def downgrade() -> None:
    """Drop workflow_executions table."""
    # Drop indices
    op.execute("DROP INDEX IF EXISTS ix_workflow_executions_workflow_started")
    op.execute("DROP INDEX IF EXISTS ix_workflow_executions_workflow_status")
    op.execute("DROP INDEX IF EXISTS ix_workflow_executions_status")
    op.execute("DROP INDEX IF EXISTS ix_workflow_executions_workflow_id")

    # Drop table
    op.execute("DROP TABLE IF EXISTS workflow_executions CASCADE")
