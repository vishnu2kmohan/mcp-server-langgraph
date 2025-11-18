"""Initial GDPR schema - user profiles, preferences, consents, conversations, audit logs

Revision ID: 8348487e5796
Revises:
Create Date: 2025-11-16 09:51:40.432968

"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "8348487e5796"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Create GDPR/HIPAA/SOC2 compliant storage schema.

    Creates:
    - user_profiles: User profile data (GDPR Articles 15, 17)
    - user_preferences: User settings
    - consent_records: Legally binding consent records (7-year retention)
    - conversations: Conversation history (90-day retention)
    - audit_logs: Comprehensive audit trail (7-year retention)

    Includes indexes, triggers, and data retention views.
    """
    # 1. USER PROFILES TABLE
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT,
            full_name TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            metadata JSONB DEFAULT '{}'::jsonb,

            -- Constraints
            CONSTRAINT user_profiles_username_not_empty CHECK (LENGTH(username) > 0),
            CONSTRAINT user_profiles_created_before_updated CHECK (created_at <= last_updated)
        )
    """
    )

    # Indexes for user_profiles
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(email) WHERE email IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_profiles_username ON user_profiles(username)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_profiles_created_at ON user_profiles(created_at)")

    # Comments for user_profiles
    op.execute("COMMENT ON TABLE user_profiles IS 'User profile data for GDPR compliance (Articles 15, 17)'")
    op.execute("COMMENT ON COLUMN user_profiles.metadata IS 'Flexible JSON storage for additional user attributes'")

    # 2. USER PREFERENCES TABLE
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY REFERENCES user_profiles(user_id) ON DELETE CASCADE,
            preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """
    )

    # Indexes for user_preferences
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_preferences_updated_at ON user_preferences(updated_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_preferences_gin ON user_preferences USING GIN (preferences)")

    # Comments for user_preferences
    op.execute("COMMENT ON TABLE user_preferences IS 'User preferences and settings (GDPR Article 15)'")

    # 3. CONSENT RECORDS TABLE
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS consent_records (
            consent_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,
            consent_type TEXT NOT NULL,
            granted BOOLEAN NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ip_address TEXT,
            user_agent TEXT,
            metadata JSONB DEFAULT '{}'::jsonb,

            -- Constraints
            CONSTRAINT consent_records_type_not_empty CHECK (LENGTH(consent_type) > 0)
        )
    """
    )

    # Indexes for consent_records
    op.execute("CREATE INDEX IF NOT EXISTS idx_consent_records_user_id ON consent_records(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_consent_records_type ON consent_records(consent_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_consent_records_timestamp ON consent_records(timestamp DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_consent_records_user_type ON consent_records(user_id, consent_type)")

    # Comments for consent_records
    op.execute("COMMENT ON TABLE consent_records IS 'Legally binding consent records (GDPR Article 7, 7-year retention)'")
    op.execute(
        "COMMENT ON COLUMN consent_records.timestamp IS 'When consent was given/withdrawn - immutable for legal purposes'"
    )

    # 4. CONVERSATIONS TABLE
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,
            title TEXT,
            messages JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_message_at TIMESTAMPTZ,
            archived BOOLEAN DEFAULT FALSE,
            metadata JSONB DEFAULT '{}'::jsonb,

            -- Constraints
            CONSTRAINT conversations_messages_is_array CHECK (jsonb_typeof(messages) = 'array'),
            CONSTRAINT conversations_last_message_after_created CHECK (
                last_message_at IS NULL OR last_message_at >= created_at
            )
        )
    """
    )

    # Indexes for conversations
    op.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_conversations_last_message_at ON conversations(last_message_at DESC NULLS LAST)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_conversations_archived ON conversations(archived) WHERE archived = TRUE")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_conversations_user_last_message ON conversations(user_id, last_message_at DESC)"
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_conversations_retention_cleanup
            ON conversations(last_message_at)
            WHERE archived = FALSE
    """
    )

    # Comments for conversations
    op.execute("COMMENT ON TABLE conversations IS 'Conversation history (90-day retention, GDPR Article 17)'")
    op.execute("COMMENT ON COLUMN conversations.messages IS 'Array of message objects in JSONB format'")
    op.execute("COMMENT ON INDEX idx_conversations_retention_cleanup IS 'Optimized for automated 90-day cleanup job'")

    # 5. AUDIT LOGS TABLE
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            log_id TEXT PRIMARY KEY,
            user_id TEXT,  -- Nullable for system events, NOT a foreign key (users can be deleted)
            action TEXT NOT NULL,
            resource_type TEXT,
            resource_id TEXT,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ip_address TEXT,
            user_agent TEXT,
            metadata JSONB DEFAULT '{}'::jsonb,

            -- Constraints
            CONSTRAINT audit_logs_action_not_empty CHECK (LENGTH(action) > 0),
            CONSTRAINT audit_logs_timestamp_not_future CHECK (timestamp <= NOW() + INTERVAL '5 minutes')
        )
    """
    )

    # Indexes for audit_logs
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id) WHERE user_id IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id)
            WHERE resource_type IS NOT NULL AND resource_id IS NOT NULL
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_audit_logs_user_timestamp_action
            ON audit_logs(user_id, timestamp DESC, action) WHERE user_id IS NOT NULL
    """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_retention_archival ON audit_logs(timestamp)")

    # Comments for audit_logs
    op.execute("COMMENT ON TABLE audit_logs IS 'Comprehensive audit trail (7-year retention, HIPAA §164.312(b), SOC2 CC6.6)'")
    op.execute("COMMENT ON COLUMN audit_logs.user_id IS 'NOT a foreign key - preserved for audit even after user deletion'")
    op.execute("COMMENT ON COLUMN audit_logs.metadata IS 'Structured audit context (request_id, session_id, trace_id, etc.)'")
    op.execute("COMMENT ON INDEX idx_audit_logs_retention_archival IS 'Optimized for archival to S3/GCS after 90 days'")

    # 6. FUNCTIONS & TRIGGERS

    # Function: Update updated_at timestamp
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """
    )

    # Trigger: Auto-update user_preferences.updated_at
    op.execute(
        """
        CREATE TRIGGER trigger_user_preferences_updated_at
            BEFORE UPDATE ON user_preferences
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()
    """
    )

    # Function: Update user_profiles.last_updated timestamp
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_user_profile_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.last_updated = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """
    )

    # Trigger: Auto-update user_profiles.last_updated
    op.execute(
        """
        CREATE TRIGGER trigger_user_profiles_last_updated
            BEFORE UPDATE ON user_profiles
            FOR EACH ROW
            EXECUTE FUNCTION update_user_profile_timestamp()
    """
    )

    # 7. DATA RETENTION VIEWS

    # View: Conversations eligible for 90-day cleanup
    op.execute(
        """
        CREATE OR REPLACE VIEW conversations_for_cleanup AS
        SELECT
            conversation_id,
            user_id,
            title,
            last_message_at,
            AGE(NOW(), last_message_at) as age
        FROM conversations
        WHERE archived = FALSE
          AND last_message_at < (NOW() - INTERVAL '90 days')
        ORDER BY last_message_at ASC
    """
    )

    op.execute(
        "COMMENT ON VIEW conversations_for_cleanup IS 'Conversations older than 90 days eligible for archival/deletion (GDPR Article 5(1)(e))'"
    )

    # View: Audit logs eligible for archival
    op.execute(
        """
        CREATE OR REPLACE VIEW audit_logs_for_archival AS
        SELECT
            log_id,
            user_id,
            action,
            timestamp,
            AGE(NOW(), timestamp) as age
        FROM audit_logs
        WHERE timestamp < (NOW() - INTERVAL '90 days')
          AND timestamp >= (NOW() - INTERVAL '2555 days')  -- Keep for 7 years
        ORDER BY timestamp ASC
    """
    )

    op.execute("COMMENT ON VIEW audit_logs_for_archival IS 'Audit logs 90+ days old for archival to S3/GCS (SOC2 CC6.6)'")


def downgrade() -> None:
    """
    Drop GDPR schema (reverse migration).

    WARNING: This will DELETE all data in the GDPR schema!
    Use with caution in production environments.
    """
    # Drop views first
    op.execute("DROP VIEW IF EXISTS audit_logs_for_archival")
    op.execute("DROP VIEW IF EXISTS conversations_for_cleanup")

    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trigger_user_profiles_last_updated ON user_profiles")
    op.execute("DROP TRIGGER IF EXISTS trigger_user_preferences_updated_at ON user_preferences")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS update_user_profile_timestamp()")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Drop tables in reverse order (respecting foreign key constraints)
    op.execute("DROP TABLE IF EXISTS audit_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS conversations CASCADE")
    op.execute("DROP TABLE IF EXISTS consent_records CASCADE")
    op.execute("DROP TABLE IF EXISTS user_preferences CASCADE")
    op.execute("DROP TABLE IF EXISTS user_profiles CASCADE")
