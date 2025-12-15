"""Add audit_logs table

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2024-12-14

Implements audit logging for MCP connection operations:
- Event logging with metadata
- Filtering by resource, actor, event type
- Retention policy management
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "f6g7h8i9j0k1"
down_revision = "e5f6g7h8i9j0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add MCP connection audit logging columns and indices.

    Note: audit_logs table is created in initial GDPR migration (8348487e5796).
    This migration adds columns needed for MCP connection auditing.
    """

    # Add missing columns for MCP connection auditing (if they don't exist)
    # The GDPR table uses user_id, we need actor_id for connection operations
    op.execute("""
        DO $$
        BEGIN
            -- Add event_type column if not exists
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'event_type'
            ) THEN
                ALTER TABLE audit_logs ADD COLUMN event_type VARCHAR(100);
            END IF;

            -- Add actor_id column if not exists (for non-user actors like services)
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'actor_id'
            ) THEN
                ALTER TABLE audit_logs ADD COLUMN actor_id VARCHAR(255);
            END IF;

            -- Add details column if not exists (alias for metadata in new APIs)
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'details'
            ) THEN
                ALTER TABLE audit_logs ADD COLUMN details JSONB;
            END IF;

            -- Add ip_address column if not exists
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'ip_address'
            ) THEN
                ALTER TABLE audit_logs ADD COLUMN ip_address VARCHAR(45);
            END IF;

            -- Add user_agent column if not exists
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'user_agent'
            ) THEN
                ALTER TABLE audit_logs ADD COLUMN user_agent TEXT;
            END IF;
        END $$;
    """)

    # Create indices for MCP connection audit patterns (if not exist)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_actor
        ON audit_logs(actor_id) WHERE actor_id IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type
        ON audit_logs(event_type) WHERE event_type IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_time
        ON audit_logs(resource_type, resource_id, timestamp)
    """)


def downgrade() -> None:
    """Remove MCP connection audit logging columns and indices.

    Note: Does NOT drop the audit_logs table (created in GDPR migration).
    Only removes columns and indices added by this migration.
    """

    # Drop indices added by this migration
    op.execute("DROP INDEX IF EXISTS idx_audit_logs_resource_time")
    op.execute("DROP INDEX IF EXISTS idx_audit_logs_event_type")
    op.execute("DROP INDEX IF EXISTS idx_audit_logs_actor")

    # Remove columns added by this migration
    op.execute("""
        DO $$
        BEGIN
            -- Drop user_agent column if exists
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'user_agent'
            ) THEN
                ALTER TABLE audit_logs DROP COLUMN user_agent;
            END IF;

            -- Drop ip_address column if exists
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'ip_address'
            ) THEN
                ALTER TABLE audit_logs DROP COLUMN ip_address;
            END IF;

            -- Drop details column if exists
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'details'
            ) THEN
                ALTER TABLE audit_logs DROP COLUMN details;
            END IF;

            -- Drop actor_id column if exists
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'actor_id'
            ) THEN
                ALTER TABLE audit_logs DROP COLUMN actor_id;
            END IF;

            -- Drop event_type column if exists
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'event_type'
            ) THEN
                ALTER TABLE audit_logs DROP COLUMN event_type;
            END IF;
        END $$;
    """)
