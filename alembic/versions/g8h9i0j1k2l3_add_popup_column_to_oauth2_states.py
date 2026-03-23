"""Add popup column to mcp_oauth2_states table

Revision ID: g8h9i0j1k2l3
Revises: f7g8h9i0j1k2
Create Date: 2026-03-20 00:00:00.000000

Fixes schema drift: ORM model OAuth2StateModel defines popup column
(Boolean, NOT NULL, DEFAULT FALSE) but the original migration
e5f6g7h8i9j0_add_mcp_connections.py did not include it.
"""

from typing import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "g8h9i0j1k2l3"
down_revision: str | None = "f7g8h9i0j1k2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add popup column to mcp_oauth2_states."""
    op.execute(
        """
        ALTER TABLE mcp_oauth2_states
        ADD COLUMN IF NOT EXISTS popup BOOLEAN NOT NULL DEFAULT FALSE
        """
    )
    op.execute(
        "COMMENT ON COLUMN mcp_oauth2_states.popup IS "
        "'If true, OAuth2 callback returns HTML for popup close instead of redirect'"
    )


def downgrade() -> None:
    """Remove popup column from mcp_oauth2_states."""
    op.execute(
        """
        ALTER TABLE mcp_oauth2_states
        DROP COLUMN IF EXISTS popup
        """
    )
