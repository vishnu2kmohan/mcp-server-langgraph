"""Add workflow sharing support

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2025-12-17

This migration adds workflow sharing capabilities:
1. Adds is_public and share_link columns to workflows table
2. Creates workflow_shares table for user-to-workflow permissions
3. Adds appropriate indices for efficient querying

Sharing model:
- Workflows can be shared with specific users (view/edit/execute)
- Workflows can be made public via share_link
"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "j0k1l2m3n4o5"
down_revision: str | Sequence[str] | None = "i9j0k1l2m3n4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add workflow sharing columns and workflow_shares table."""

    # ==========================================================================
    # 1. WORKFLOWS TABLE: Add sharing columns
    # ==========================================================================

    # Add is_public column (default false)
    op.execute(
        """
        ALTER TABLE workflows
        ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT FALSE;
        """
    )

    # Add share_link column for public access
    op.execute(
        """
        ALTER TABLE workflows
        ADD COLUMN IF NOT EXISTS share_link VARCHAR(64);
        """
    )

    # Add unique index on share_link (only for non-null values)
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_workflows_share_link
        ON workflows (share_link)
        WHERE share_link IS NOT NULL;
        """
    )

    # Add index on is_public for filtering public workflows
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_workflows_is_public
        ON workflows (is_public)
        WHERE is_public = TRUE;
        """
    )

    # Add comments for documentation
    op.execute(
        """
        COMMENT ON COLUMN workflows.is_public IS
        'Whether workflow is publicly accessible via share_link';
        """
    )

    op.execute(
        """
        COMMENT ON COLUMN workflows.share_link IS
        'URL-safe token for public access (generated when is_public=true)';
        """
    )

    # ==========================================================================
    # 2. WORKFLOW_SHARES TABLE: Create for user permissions
    # ==========================================================================

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS workflow_shares (
            id VARCHAR(36) PRIMARY KEY,
            workflow_id VARCHAR(36) NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
            user_id VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            permission VARCHAR(20) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_by VARCHAR(255) NOT NULL,
            CONSTRAINT workflow_shares_permission_valid
                CHECK (permission IN ('view', 'edit', 'execute')),
            CONSTRAINT workflow_shares_workflow_user_unique
                UNIQUE (workflow_id, user_id)
        );
        """
    )

    # Add comments
    op.execute(
        """
        COMMENT ON TABLE workflow_shares IS
        'Stores user-specific permissions for shared workflows';
        """
    )

    op.execute(
        """
        COMMENT ON COLUMN workflow_shares.permission IS
        'Permission level: view (read-only), edit (modify), execute (run)';
        """
    )

    # ==========================================================================
    # 3. WORKFLOW_SHARES TABLE: Add indices
    # ==========================================================================

    # Index for querying shares by workflow
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_workflow_shares_workflow_id
        ON workflow_shares (workflow_id);
        """
    )

    # Index for querying shares by user (for "shared with me" queries)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_workflow_shares_user_id
        ON workflow_shares (user_id);
        """
    )

    # Index for querying by email (for adding shares by email)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_workflow_shares_email
        ON workflow_shares (email);
        """
    )

    # Composite index for permission filtering
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_workflow_shares_user_permission
        ON workflow_shares (user_id, permission);
        """
    )


def downgrade() -> None:
    """Remove workflow sharing columns and workflow_shares table."""

    # ==========================================================================
    # 1. Drop workflow_shares table and indices
    # ==========================================================================

    op.execute("DROP INDEX IF EXISTS ix_workflow_shares_user_permission;")
    op.execute("DROP INDEX IF EXISTS ix_workflow_shares_email;")
    op.execute("DROP INDEX IF EXISTS ix_workflow_shares_user_id;")
    op.execute("DROP INDEX IF EXISTS ix_workflow_shares_workflow_id;")
    op.execute("DROP TABLE IF EXISTS workflow_shares;")

    # ==========================================================================
    # 2. Remove sharing columns from workflows table
    # ==========================================================================

    op.execute("DROP INDEX IF EXISTS ix_workflows_is_public;")
    op.execute("DROP INDEX IF EXISTS ix_workflows_share_link;")
    op.execute(
        """
        ALTER TABLE workflows
        DROP COLUMN IF EXISTS share_link,
        DROP COLUMN IF EXISTS is_public;
        """
    )
