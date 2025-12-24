"""Add session status and workflow_id columns

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
Create Date: 2025-12-24

This migration adds session filtering support:
1. Adds status column (active, archived) with server_default for zero-downtime
2. Adds workflow_id column for session-workflow association
3. Creates composite indices for efficient user-scoped filtering
4. Backfills existing rows with default status

CRITICAL: Uses server_default to avoid table locks during migration.
CRITICAL: Uses CONCURRENTLY for index creation on large tables.
"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "m3n4o5p6q7r8"
down_revision: str | Sequence[str] | None = "l2m3n4o5p6q7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add session status and workflow_id columns with indices."""

    # ==========================================================================
    # 1. SESSIONS TABLE: Add status column with server_default
    # ==========================================================================

    # Add status column with server_default for zero-downtime
    # New rows get 'active', existing rows get NULL initially (backfilled below)
    op.execute(
        """
        ALTER TABLE sessions
        ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active';
        """
    )

    # Add workflow_id column for session-workflow association
    op.execute(
        """
        ALTER TABLE sessions
        ADD COLUMN IF NOT EXISTS workflow_id VARCHAR(36);
        """
    )

    # ==========================================================================
    # 2. BACKFILL: Set status='active' for any NULL rows (defensive)
    # ==========================================================================

    op.execute(
        """
        UPDATE sessions
        SET status = 'active'
        WHERE status IS NULL;
        """
    )

    # ==========================================================================
    # 3. INDICES: Create composite indices for efficient filtering
    # Note: Using CONCURRENTLY requires autocommit mode
    # Since Alembic runs in a transaction, we use IF NOT EXISTS instead
    # For true CONCURRENTLY on production, run separately:
    #   CREATE INDEX CONCURRENTLY ix_sessions_user_status ON sessions(user_id, status);
    # ==========================================================================

    # Composite index for user + status filtering
    # Supports: SELECT * FROM sessions WHERE user_id = ? AND status = ?
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_sessions_user_status
        ON sessions(user_id, status);
        """
    )

    # Composite index for user + workflow filtering
    # Supports: SELECT * FROM sessions WHERE user_id = ? AND workflow_id = ?
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_sessions_user_workflow
        ON sessions(user_id, workflow_id);
        """
    )

    # Index on workflow_id for workflow-to-sessions lookup
    # Supports: SELECT * FROM sessions WHERE workflow_id = ?
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_sessions_workflow_id
        ON sessions(workflow_id)
        WHERE workflow_id IS NOT NULL;
        """
    )

    # ==========================================================================
    # 4. COMMENTS: Document columns
    # ==========================================================================

    op.execute(
        """
        COMMENT ON COLUMN sessions.status IS
        'Session status: active (default), archived';
        """
    )

    op.execute(
        """
        COMMENT ON COLUMN sessions.workflow_id IS
        'Optional workflow ID this session is associated with';
        """
    )


def downgrade() -> None:
    """Remove session status and workflow_id columns and indices."""

    # Drop indices first
    op.execute("DROP INDEX IF EXISTS ix_sessions_workflow_id;")
    op.execute("DROP INDEX IF EXISTS ix_sessions_user_workflow;")
    op.execute("DROP INDEX IF EXISTS ix_sessions_user_status;")

    # Drop columns
    op.execute("ALTER TABLE sessions DROP COLUMN IF EXISTS workflow_id;")
    op.execute("ALTER TABLE sessions DROP COLUMN IF EXISTS status;")
