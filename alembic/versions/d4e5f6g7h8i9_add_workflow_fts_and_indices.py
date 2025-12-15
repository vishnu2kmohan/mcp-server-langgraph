"""Add Workflow Full-Text Search and Indices

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2025-01-15 00:00:01.000000

This migration adds:
1. Creates workflows table for Agent Studio workflow definitions
2. Full-text search (FTS) support for workflows table
3. Status column for workflow filtering (active, archived, draft)
4. Composite indices for efficient cursor-based pagination

FTS enables efficient searching across workflow name and description fields
without using ILIKE which requires sequential scans on large tables.

Cursor-based pagination uses composite indices (sort_column + id) to provide
stable ordering even when multiple records have the same sort value.
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6g7h8i9"
down_revision: str | None = "c3d4e5f6g7h8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add FTS columns, indices, and triggers for workflows and messages."""

    # ==========================================================================
    # 0. WORKFLOWS TABLE: Create if not exist (required before adding columns)
    # ==========================================================================

    # Create workflows table for Agent Studio workflow storage
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS workflows (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            nodes JSONB NOT NULL DEFAULT '[]'::jsonb,
            edges JSONB NOT NULL DEFAULT '[]'::jsonb,
            user_id VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    # Indexes for workflows
    op.execute("CREATE INDEX IF NOT EXISTS ix_workflows_name ON workflows(name)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_workflows_user_id ON workflows(user_id) WHERE user_id IS NOT NULL")

    # Comment on table
    op.execute("COMMENT ON TABLE workflows IS 'Agent Studio workflow definitions with nodes and edges'")

    # ==========================================================================
    # 1. WORKFLOWS TABLE: Add status column
    # ==========================================================================

    # Add status column for filtering workflows
    op.add_column(
        "workflows",
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="active",
        ),
    )

    # Create index on status for filtering
    op.create_index(
        "ix_workflows_status",
        "workflows",
        ["status"],
    )

    # ==========================================================================
    # 2. WORKFLOWS TABLE: Full-Text Search
    # ==========================================================================

    # Add tsvector column for FTS
    op.add_column(
        "workflows",
        sa.Column(
            "search_vector",
            sa.dialects.postgresql.TSVECTOR(),
            nullable=True,
        ),
    )

    # Create GIN index for fast FTS queries
    op.create_index(
        "ix_workflows_search_vector",
        "workflows",
        ["search_vector"],
        postgresql_using="gin",
    )

    # ==========================================================================
    # 3. WORKFLOWS TABLE: Composite Indices for Cursor Pagination
    # ==========================================================================

    # Composite index for pagination by updated_at (default sort)
    # ORDER BY updated_at DESC, id DESC
    op.create_index(
        "ix_workflows_updated_at_id",
        "workflows",
        ["updated_at", "id"],
    )

    # Composite index for pagination by name
    # ORDER BY name ASC, id ASC
    op.create_index(
        "ix_workflows_name_id",
        "workflows",
        ["name", "id"],
    )

    # Composite index for filtered queries by user + updated_at
    # WHERE user_id = ? ORDER BY updated_at DESC
    op.create_index(
        "ix_workflows_user_updated",
        "workflows",
        ["user_id", "updated_at"],
    )

    # Composite index for filtered queries by user + created_at
    # WHERE user_id = ? ORDER BY created_at DESC
    op.create_index(
        "ix_workflows_user_created",
        "workflows",
        ["user_id", "created_at"],
    )

    # Composite index for status + updated_at filtering
    # WHERE status = ? ORDER BY updated_at DESC
    op.create_index(
        "ix_workflows_status_updated",
        "workflows",
        ["status", "updated_at"],
    )

    # Case-insensitive name index for search
    op.execute("""
        CREATE INDEX ix_workflows_name_lower ON workflows (LOWER(name));
    """)

    # ==========================================================================
    # 4. WORKFLOWS TABLE: Populate and Maintain FTS
    # ==========================================================================

    # Populate search_vector for existing records
    # Weighted: name (A) > description (B)
    op.execute("""
        UPDATE workflows SET search_vector =
            setweight(to_tsvector('english', COALESCE(name, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(description, '')), 'B');
    """)

    # Create trigger function to maintain search_vector
    op.execute("""
        CREATE OR REPLACE FUNCTION workflows_search_vector_update()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger to auto-update search_vector on INSERT/UPDATE
    op.execute("""
        CREATE TRIGGER workflows_search_vector_trigger
        BEFORE INSERT OR UPDATE OF name, description ON workflows
        FOR EACH ROW
        EXECUTE FUNCTION workflows_search_vector_update();
    """)

    # NOTE: Message indices (ix_messages_session_order, ix_messages_session_timestamp)
    # are created in migration b2c3d4e5f6g7 when the messages table is created.


def downgrade() -> None:
    """Remove FTS columns, indices, and triggers for workflows."""

    # ==========================================================================
    # 1. WORKFLOWS TABLE: Remove FTS
    # ==========================================================================

    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS workflows_search_vector_trigger ON workflows;")

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS workflows_search_vector_update();")

    # Drop indices
    op.drop_index("ix_workflows_search_vector", table_name="workflows")
    op.execute("DROP INDEX IF EXISTS ix_workflows_name_lower;")

    # Drop search_vector column
    op.drop_column("workflows", "search_vector")

    # ==========================================================================
    # 2. WORKFLOWS TABLE: Remove Composite Indices
    # ==========================================================================

    op.drop_index("ix_workflows_updated_at_id", table_name="workflows")
    op.drop_index("ix_workflows_name_id", table_name="workflows")
    op.drop_index("ix_workflows_user_updated", table_name="workflows")
    op.drop_index("ix_workflows_user_created", table_name="workflows")
    op.drop_index("ix_workflows_status_updated", table_name="workflows")

    # ==========================================================================
    # 3. WORKFLOWS TABLE: Remove Status Column
    # ==========================================================================

    op.drop_index("ix_workflows_status", table_name="workflows")
    op.drop_column("workflows", "status")

    # ==========================================================================
    # 4. WORKFLOWS TABLE: Drop table created in upgrade
    # ==========================================================================

    # Drop indices first
    op.execute("DROP INDEX IF EXISTS ix_workflows_user_id")
    op.execute("DROP INDEX IF EXISTS ix_workflows_name")

    # Drop the table
    op.execute("DROP TABLE IF EXISTS workflows CASCADE")
