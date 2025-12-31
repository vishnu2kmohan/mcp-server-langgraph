"""Add workflow title column

Revision ID: s9t0u1v2w3x4
Revises: r8s9t0u1v2w3
Create Date: 2025-12-31

Adds the 'title' column to the workflows table:
- title: Human-friendly display name (VARCHAR 255, nullable)
- Defaults to NULL; falls back to 'name' when not set in application logic

This column was missing from the schema despite being defined in the
SQLAlchemy model (WorkflowModel.title), causing:
    column workflows.title does not exist
"""

from typing import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "s9t0u1v2w3x4"
down_revision: str | None = "r8s9t0u1v2w3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add title column to workflows table."""
    # Add title column (nullable, defaults to NULL)
    # When title is NULL, application falls back to using 'name'
    op.execute(
        """
        ALTER TABLE workflows
        ADD COLUMN IF NOT EXISTS title VARCHAR(255);
        """
    )

    # Add comment explaining the column's purpose
    op.execute(
        """
        COMMENT ON COLUMN workflows.title IS
        'Human-friendly display name for the workflow. Falls back to name if NULL.';
        """
    )


def downgrade() -> None:
    """Remove title column from workflows table."""
    op.execute(
        """
        ALTER TABLE workflows
        DROP COLUMN IF EXISTS title;
        """
    )
