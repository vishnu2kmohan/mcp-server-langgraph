"""Add user_preferences table for persona storage

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
Create Date: 2025-12-24

Migrates persona preferences from in-memory storage to PostgreSQL:
1. Creates user_preferences table with JSONB columns for flexibility
2. Adds index on updated_at for cleanup queries
3. Uses server_default for zero-downtime deployment

This replaces the in-memory _persona_preferences_store in user.py.
"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "n4o5p6q7r8s9"
down_revision: str | Sequence[str] | None = "m3n4o5p6q7r8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create user_preferences table."""

    # ==========================================================================
    # 1. CREATE TABLE: user_preferences
    # ==========================================================================

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_preferences (
            -- Primary key: user_id is unique per user
            user_id VARCHAR(255) PRIMARY KEY,

            -- Sub-persona selection (alice-builder, bob, etc.)
            sub_persona VARCHAR(50),

            -- Feature flags as JSONB for flexible boolean storage
            feature_flags JSONB NOT NULL DEFAULT '{}',

            -- Additional UI/UX preferences (theme, layout, etc.)
            preferences JSONB NOT NULL DEFAULT '{}',

            -- Timestamps
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    # ==========================================================================
    # 2. COMMENTS: Document columns
    # ==========================================================================

    op.execute(
        """
        COMMENT ON TABLE user_preferences IS
        'User preferences for persona and feature configuration';
        """
    )

    op.execute(
        """
        COMMENT ON COLUMN user_preferences.user_id IS
        'User ID in OpenFGA format (user:username)';
        """
    )

    op.execute(
        """
        COMMENT ON COLUMN user_preferences.sub_persona IS
        'Selected sub-persona variant (alice-builder, bob, etc.)';
        """
    )

    op.execute(
        """
        COMMENT ON COLUMN user_preferences.feature_flags IS
        'User-specific feature flag overrides';
        """
    )

    op.execute(
        """
        COMMENT ON COLUMN user_preferences.preferences IS
        'Additional UI/UX preferences (theme, layout, etc.)';
        """
    )

    # ==========================================================================
    # 3. INDICES: Add index for cleanup queries
    # ==========================================================================

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_user_preferences_updated_at
        ON user_preferences(updated_at);
        """
    )

    # ==========================================================================
    # 4. TRIGGER: Auto-update updated_at on modification
    # ==========================================================================

    # Create trigger function if not exists
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_user_preferences_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Create trigger
    op.execute(
        """
        DROP TRIGGER IF EXISTS trigger_user_preferences_updated_at ON user_preferences;
        CREATE TRIGGER trigger_user_preferences_updated_at
            BEFORE UPDATE ON user_preferences
            FOR EACH ROW
            EXECUTE FUNCTION update_user_preferences_updated_at();
        """
    )


def downgrade() -> None:
    """Remove user_preferences table."""

    # Drop trigger first
    op.execute("DROP TRIGGER IF EXISTS trigger_user_preferences_updated_at ON user_preferences;")
    op.execute("DROP FUNCTION IF EXISTS update_user_preferences_updated_at();")

    # Drop index
    op.execute("DROP INDEX IF EXISTS ix_user_preferences_updated_at;")

    # Drop table
    op.execute("DROP TABLE IF EXISTS user_preferences;")
