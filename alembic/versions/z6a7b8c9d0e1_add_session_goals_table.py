"""Add session_goals table for goal tracking per session.

Revision ID: z6a7b8c9d0e1
Revises: y5z6a7b8c9d0
Create Date: 2026-01-13

This migration adds the session_goals table for tracking user goals within sessions:
- Allows users to set, track, and complete goals
- Supports boolean, partial achievement states
- Includes optional feedback for goal completion
- Indexed for efficient session-based queries

Reference: docs-internal/frontend/PENDING-BACKEND-APIS.md
Frontend Integration: useSetSessionGoalMutation, useCompleteSessionGoalMutation
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "z6a7b8c9d0e1"
down_revision = "y5z6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create session_goals table for goal tracking."""
    op.create_table(
        "session_goals",
        # Primary key
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Unique goal identifier (UUID)",
        ),
        # Session reference
        sa.Column(
            "session_id",
            sa.String(255),
            nullable=False,
            comment="Session identifier (references sessions.id)",
        ),
        # User reference
        sa.Column(
            "user_id",
            sa.String(255),
            nullable=False,
            comment="User who set the goal",
        ),
        # Goal content
        sa.Column(
            "goal",
            sa.Text(),
            nullable=False,
            comment="The goal text set by the user",
        ),
        # Achievement status: 'true', 'false', 'partial'
        sa.Column(
            "achieved",
            sa.String(10),
            nullable=True,
            comment="Achievement status: true, false, or partial",
        ),
        # Optional feedback when completing
        sa.Column(
            "feedback",
            sa.Text(),
            nullable=True,
            comment="User feedback on goal completion",
        ),
        # Timestamps (stored as Unix milliseconds for frontend compatibility)
        sa.Column(
            "set_at",
            sa.BigInteger(),
            nullable=False,
            comment="When the goal was set (Unix timestamp ms)",
        ),
        sa.Column(
            "completed_at",
            sa.BigInteger(),
            nullable=True,
            comment="When the goal was completed (Unix timestamp ms)",
        ),
        # Database timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
            comment="Database record creation time",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
            comment="Database record last update time",
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "achieved IN ('true', 'false', 'partial')",
            name="ck_session_goals_achieved_values",
        ),
    )

    # Create indexes for efficient queries
    # Index for looking up goals by session
    op.create_index(
        "ix_session_goals_session_id",
        "session_goals",
        ["session_id"],
    )
    # Index for looking up goals by user
    op.create_index(
        "ix_session_goals_user_id",
        "session_goals",
        ["user_id"],
    )
    # Index for chronological goal listing per session
    op.create_index(
        "ix_session_goals_session_set_at",
        "session_goals",
        ["session_id", "set_at"],
    )
    # Index for filtering by achievement status
    op.create_index(
        "ix_session_goals_achieved",
        "session_goals",
        ["achieved"],
    )

    # Create trigger for updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_session_goals_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_session_goals_updated_at
        BEFORE UPDATE ON session_goals
        FOR EACH ROW
        EXECUTE FUNCTION update_session_goals_updated_at();
    """)


def downgrade() -> None:
    """Drop session_goals table."""
    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS trg_session_goals_updated_at ON session_goals")
    op.execute("DROP FUNCTION IF EXISTS update_session_goals_updated_at()")

    # Drop indexes
    op.drop_index("ix_session_goals_achieved", table_name="session_goals")
    op.drop_index("ix_session_goals_session_set_at", table_name="session_goals")
    op.drop_index("ix_session_goals_user_id", table_name="session_goals")
    op.drop_index("ix_session_goals_session_id", table_name="session_goals")

    # Drop table
    op.drop_table("session_goals")
