"""Add scope column to MCP connections for access control

Revision ID: b8c9d0e1f2g3
Revises: a7b8c9d0e1f2
Create Date: 2025-01-13

Adds scope field to control connection access:
- user: Personal - only owner can use
- project: Shared - project members can use
- session: Ephemeral - session-only, not persisted

Reference: Phase 6 - Connections Page Redesign Plan
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2g3"
down_revision: str | Sequence[str] | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Add scope column to mcp_connections for access control.

    Scope determines who can use the connection:
    - user: Only the owner can use (default, backward compatible)
    - project: All project members can use
    - session: Ephemeral, only within the same session
    """
    # Add scope column with default 'user' for existing rows
    op.execute(
        """
        ALTER TABLE mcp_connections
        ADD COLUMN IF NOT EXISTS scope VARCHAR(50) NOT NULL DEFAULT 'user';
        """
    )

    # Add constraint for valid scope values
    op.execute(
        """
        ALTER TABLE mcp_connections
        ADD CONSTRAINT mcp_connections_scope_valid
        CHECK (scope IN ('user', 'project', 'session'));
        """
    )

    # Add index on scope for filtering
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_mcp_connections_scope
        ON mcp_connections (scope);
        """
    )

    # Add composite index for project-scoped connections
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_mcp_connections_project_scope
        ON mcp_connections (project_id, scope)
        WHERE project_id IS NOT NULL;
        """
    )

    # Add comment for documentation
    op.execute(
        """
        COMMENT ON COLUMN mcp_connections.scope IS
        'Access scope: user (owner only), project (project members), session (ephemeral)';
        """
    )


def downgrade() -> None:
    """Remove scope column from mcp_connections."""
    # Drop constraint first
    op.execute(
        """
        ALTER TABLE mcp_connections
        DROP CONSTRAINT IF EXISTS mcp_connections_scope_valid;
        """
    )

    # Drop indexes
    op.execute(
        """
        DROP INDEX IF EXISTS ix_mcp_connections_scope;
        """
    )

    op.execute(
        """
        DROP INDEX IF EXISTS ix_mcp_connections_project_scope;
        """
    )

    # Drop column
    op.execute(
        """
        ALTER TABLE mcp_connections
        DROP COLUMN IF EXISTS scope;
        """
    )
