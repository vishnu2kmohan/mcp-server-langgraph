"""Add Full-Text Search and Performance Indices

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-01-15 00:00:00.000000

This migration adds:
1. Full-text search (FTS) support using PostgreSQL tsvector columns with GIN indices
2. Composite indices for efficient pagination with sorting
3. Triggers to automatically maintain search vectors

FTS enables efficient searching across name and description fields without
using ILIKE which requires sequential scans on large tables.
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add FTS columns, indices, and triggers for optimized queries."""

    # ==========================================================================
    # 0. SESSION TABLES: Create if not exist (required before adding FTS)
    # ==========================================================================

    # Create sessions table for studio session storage
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            user_id VARCHAR(255),
            config_model VARCHAR(100) NOT NULL DEFAULT 'gpt-4o-mini',
            config_temperature FLOAT NOT NULL DEFAULT 0.7,
            config_max_tokens INTEGER NOT NULL DEFAULT 1000,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    # Indexes for sessions
    op.execute("CREATE INDEX IF NOT EXISTS ix_sessions_name ON sessions(name)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sessions_user_id ON sessions(user_id) WHERE user_id IS NOT NULL")

    # Create messages table for message storage
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id VARCHAR(36) PRIMARY KEY,
            session_id VARCHAR(36) NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            order_index INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    # Indexes for messages
    op.execute("CREATE INDEX IF NOT EXISTS ix_messages_session_id ON messages(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_messages_session_order ON messages(session_id, order_index)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_messages_session_timestamp ON messages(session_id, timestamp)")

    # Comment on tables
    op.execute("COMMENT ON TABLE sessions IS 'Agent Studio sessions for durable chat persistence'")
    op.execute("COMMENT ON TABLE messages IS 'Messages within Agent Studio sessions'")

    # ==========================================================================
    # 1. PROJECTS TABLE: Full-Text Search
    # ==========================================================================

    # Add tsvector column for FTS
    op.add_column(
        "projects",
        sa.Column(
            "search_vector",
            sa.dialects.postgresql.TSVECTOR(),
            nullable=True,
        ),
    )

    # Create GIN index for fast FTS queries
    op.create_index(
        "ix_projects_search_vector",
        "projects",
        ["search_vector"],
        postgresql_using="gin",
    )

    # Create index for name sorting (case-insensitive)
    op.execute("""
        CREATE INDEX ix_projects_name_lower ON projects (LOWER(name));
    """)

    # Create composite index for pagination with name sorting
    op.create_index(
        "ix_projects_name_id",
        "projects",
        ["name", "id"],
    )

    # Create composite index for pagination with updated_at sorting
    op.create_index(
        "ix_projects_updated_at_id",
        "projects",
        ["updated_at", "id"],
        postgresql_ops={"updated_at": "DESC"},
    )

    # Populate search_vector for existing records
    op.execute("""
        UPDATE projects SET search_vector =
            setweight(to_tsvector('english', COALESCE(name, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(description, '')), 'B');
    """)

    # Create trigger function to maintain search_vector
    op.execute("""
        CREATE OR REPLACE FUNCTION projects_search_vector_update()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger
    op.execute("""
        CREATE TRIGGER projects_search_vector_trigger
        BEFORE INSERT OR UPDATE OF name, description ON projects
        FOR EACH ROW
        EXECUTE FUNCTION projects_search_vector_update();
    """)

    # ==========================================================================
    # 2. SESSIONS TABLE: Full-Text Search
    # ==========================================================================

    # Add tsvector column for FTS
    op.add_column(
        "sessions",
        sa.Column(
            "search_vector",
            sa.dialects.postgresql.TSVECTOR(),
            nullable=True,
        ),
    )

    # Create GIN index for fast FTS queries
    op.create_index(
        "ix_sessions_search_vector",
        "sessions",
        ["search_vector"],
        postgresql_using="gin",
    )

    # Create composite index for user_id + updated_at pagination
    op.create_index(
        "ix_sessions_user_updated",
        "sessions",
        ["user_id", "updated_at"],
        postgresql_ops={"updated_at": "DESC"},
    )

    # Create composite index for user_id + created_at pagination
    op.create_index(
        "ix_sessions_user_created",
        "sessions",
        ["user_id", "created_at"],
        postgresql_ops={"created_at": "DESC"},
    )

    # Create index for name sorting
    op.execute("""
        CREATE INDEX ix_sessions_name_lower ON sessions (LOWER(name));
    """)

    # Populate search_vector for existing records
    op.execute("""
        UPDATE sessions SET search_vector =
            to_tsvector('english', COALESCE(name, ''));
    """)

    # Create trigger function to maintain search_vector
    op.execute("""
        CREATE OR REPLACE FUNCTION sessions_search_vector_update()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english', COALESCE(NEW.name, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger
    op.execute("""
        CREATE TRIGGER sessions_search_vector_trigger
        BEFORE INSERT OR UPDATE OF name ON sessions
        FOR EACH ROW
        EXECUTE FUNCTION sessions_search_vector_update();
    """)

    # ==========================================================================
    # 3. PROJECT CHILD TABLES: Optimized Indices
    # ==========================================================================

    # Project workflows: index for added_at sorting
    op.create_index(
        "ix_project_workflows_added",
        "project_workflows",
        ["project_id", "added_at"],
        postgresql_ops={"added_at": "DESC"},
    )

    # Project sessions: index for added_at sorting
    op.create_index(
        "ix_project_sessions_added",
        "project_sessions",
        ["project_id", "added_at"],
        postgresql_ops={"added_at": "DESC"},
    )

    # Project connections: index for created_at sorting
    op.create_index(
        "ix_project_connections_created",
        "project_connections",
        ["project_id", "created_at"],
        postgresql_ops={"created_at": "DESC"},
    )


def downgrade() -> None:
    """Remove FTS columns, indices, and triggers."""

    # ==========================================================================
    # 1. PROJECTS TABLE: Remove FTS
    # ==========================================================================

    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS projects_search_vector_trigger ON projects;")

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS projects_search_vector_update();")

    # Drop indices
    op.drop_index("ix_projects_search_vector", table_name="projects")
    op.execute("DROP INDEX IF EXISTS ix_projects_name_lower;")
    op.drop_index("ix_projects_name_id", table_name="projects")
    op.drop_index("ix_projects_updated_at_id", table_name="projects")

    # Drop column
    op.drop_column("projects", "search_vector")

    # ==========================================================================
    # 2. SESSIONS TABLE: Remove FTS
    # ==========================================================================

    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS sessions_search_vector_trigger ON sessions;")

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS sessions_search_vector_update();")

    # Drop indices
    op.drop_index("ix_sessions_search_vector", table_name="sessions")
    op.drop_index("ix_sessions_user_updated", table_name="sessions")
    op.drop_index("ix_sessions_user_created", table_name="sessions")
    op.execute("DROP INDEX IF EXISTS ix_sessions_name_lower;")

    # Drop column
    op.drop_column("sessions", "search_vector")

    # ==========================================================================
    # 3. PROJECT CHILD TABLES: Remove Indices
    # ==========================================================================

    op.drop_index("ix_project_workflows_added", table_name="project_workflows")
    op.drop_index("ix_project_sessions_added", table_name="project_sessions")
    op.drop_index("ix_project_connections_created", table_name="project_connections")

    # ==========================================================================
    # 4. SESSION TABLES: Drop tables created in upgrade
    # ==========================================================================

    # Drop message indices
    op.execute("DROP INDEX IF EXISTS ix_messages_session_timestamp")
    op.execute("DROP INDEX IF EXISTS ix_messages_session_order")
    op.execute("DROP INDEX IF EXISTS ix_messages_session_id")

    # Drop session indices
    op.execute("DROP INDEX IF EXISTS ix_sessions_user_id")
    op.execute("DROP INDEX IF EXISTS ix_sessions_name")

    # Drop tables (messages first due to session_id reference)
    op.execute("DROP TABLE IF EXISTS messages CASCADE")
    op.execute("DROP TABLE IF EXISTS sessions CASCADE")
