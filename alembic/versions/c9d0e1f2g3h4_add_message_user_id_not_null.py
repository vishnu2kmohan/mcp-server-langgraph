"""Add messages.user_id column and enforce NOT NULL on both tables.

Revision ID: c9d0e1f2g3h4
Revises: b8c9d0e1f2g3
Create Date: 2026-01-22

This migration implements Phase 0 of the Message Embedding & Session Lifecycle Plan:

1. Add user_id column to messages table (for ownership tracking)
2. Backfill messages.user_id from sessions.user_id where available
3. Backfill orphaned messages (session.user_id is NULL) with sentinel "system"
4. Backfill sessions.user_id with "system" where NULL
5. Enforce NOT NULL on both messages.user_id and sessions.user_id

Security: Enables user-scoped access control for messages and sessions.
Reference: Plan v8 - Task 0.2, Findings 21, 29
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "c9d0e1f2g3h4"
down_revision = "b8c9d0e1f2g3"
branch_labels = None
depends_on = None

# Sentinel value for orphaned data (sessions/messages without known owner)
SYSTEM_SENTINEL = "system"


def upgrade() -> None:
    """Add user_id to messages and enforce NOT NULL on both tables."""

    # ==========================================================================
    # 1. Add user_id column to messages table (nullable initially)
    # ==========================================================================
    op.add_column(
        "messages",
        sa.Column("user_id", sa.String(255), nullable=True),
    )

    # Create index for user_id queries
    op.create_index(
        "ix_messages_user_id",
        "messages",
        ["user_id"],
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )

    # ==========================================================================
    # 2. Backfill messages.user_id from sessions.user_id where session has owner
    # ==========================================================================
    op.execute(
        """
        UPDATE messages m
        SET user_id = s.user_id
        FROM sessions s
        WHERE m.session_id = s.id
          AND s.user_id IS NOT NULL
          AND m.user_id IS NULL
        """
    )

    # ==========================================================================
    # 3. Backfill orphaned messages (session.user_id is NULL) with sentinel
    # ==========================================================================
    op.execute(
        f"""
        UPDATE messages
        SET user_id = '{SYSTEM_SENTINEL}'
        WHERE user_id IS NULL
        """
    )

    # ==========================================================================
    # 4. Backfill sessions.user_id with sentinel where NULL
    # ==========================================================================
    op.execute(
        f"""
        UPDATE sessions
        SET user_id = '{SYSTEM_SENTINEL}'
        WHERE user_id IS NULL
        """
    )

    # ==========================================================================
    # 5. Enforce NOT NULL on messages.user_id
    # ==========================================================================
    op.alter_column(
        "messages",
        "user_id",
        existing_type=sa.String(255),
        nullable=False,
    )

    # ==========================================================================
    # 6. Enforce NOT NULL on sessions.user_id
    # ==========================================================================
    op.alter_column(
        "sessions",
        "user_id",
        existing_type=sa.String(255),
        nullable=False,
    )

    # ==========================================================================
    # 7. Update index on sessions.user_id (remove WHERE clause since non-null)
    # ==========================================================================
    op.execute("DROP INDEX IF EXISTS ix_sessions_user_id")
    op.create_index(
        "ix_sessions_user_id",
        "sessions",
        ["user_id"],
    )

    # Update index on messages.user_id (remove WHERE clause since non-null)
    op.execute("DROP INDEX IF EXISTS ix_messages_user_id")
    op.create_index(
        "ix_messages_user_id",
        "messages",
        ["user_id"],
    )

    # ==========================================================================
    # 8. Add comments documenting the security model
    # ==========================================================================
    op.execute(
        f"COMMENT ON COLUMN sessions.user_id IS "
        f"'Owner user ID (required). Sentinel value \"{SYSTEM_SENTINEL}\" for legacy data.'"
    )
    op.execute(
        f"COMMENT ON COLUMN messages.user_id IS "
        f"'Owner user ID (required). Enables user-scoped message access.'"
    )


def downgrade() -> None:
    """Revert user_id NOT NULL constraints and remove messages.user_id column."""

    # Remove NOT NULL constraint on sessions.user_id
    op.alter_column(
        "sessions",
        "user_id",
        existing_type=sa.String(255),
        nullable=True,
    )

    # Restore conditional index on sessions.user_id
    op.execute("DROP INDEX IF EXISTS ix_sessions_user_id")
    op.create_index(
        "ix_sessions_user_id",
        "sessions",
        ["user_id"],
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )

    # Drop index on messages.user_id
    op.execute("DROP INDEX IF EXISTS ix_messages_user_id")

    # Drop user_id column from messages
    op.drop_column("messages", "user_id")
