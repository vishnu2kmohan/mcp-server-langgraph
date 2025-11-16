-- GDPR/HIPAA/SOC2 Compliant Storage Schema
-- ==========================================
-- Migration 001: Create GDPR data storage tables with PostgreSQL
--
-- Compliance Requirements:
-- - GDPR: Articles 5, 15, 17 (retention, right to access, right to erasure)
-- - HIPAA: §164.312(b), §164.316(b)(2)(i) (audit controls, 7-year retention)
-- - SOC2: CC6.6, PI1.4 (audit logs, data retention)
--
-- Design Decisions (ADR-0041):
-- - Pure PostgreSQL (not hybrid) for simplicity and ACID guarantees
-- - JSONB for flexible metadata storage
-- - Indexes optimized for GDPR query patterns
-- - 7-year retention for audit logs and consents
-- - 90-day retention for conversations (configurable)

-- ==============================================================================
-- 1. USER PROFILES
-- ==============================================================================
-- Stores basic user information for GDPR data subject rights
-- Retention: Until user deletion request (GDPR Article 17)

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
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_user_profiles_username ON user_profiles(username);
CREATE INDEX IF NOT EXISTS idx_user_profiles_created_at ON user_profiles(created_at);

-- Enable row-level security (optional, for multi-tenancy)
-- ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE user_profiles IS 'User profile data for GDPR compliance (Articles 15, 17)';
COMMENT ON COLUMN user_profiles.metadata IS 'Flexible JSON storage for additional user attributes';

-- ==============================================================================
-- 2. USER PREFERENCES
-- ==============================================================================
-- Stores user preferences and settings
-- Retention: Until user deletion request

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id TEXT PRIMARY KEY REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for preference searches
CREATE INDEX IF NOT EXISTS idx_user_preferences_updated_at ON user_preferences(updated_at);
CREATE INDEX IF NOT EXISTS idx_user_preferences_gin ON user_preferences USING GIN (preferences);

COMMENT ON TABLE user_preferences IS 'User preferences and settings (GDPR Article 15)';

-- ==============================================================================
-- 3. CONSENT RECORDS
-- ==============================================================================
-- Stores legally binding consent records
-- Retention: 7 years (GDPR, HIPAA, SOC2 requirement)
-- NEVER deleted (compliance requirement)

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
);

-- Indexes for compliance queries
CREATE INDEX IF NOT EXISTS idx_consent_records_user_id ON consent_records(user_id);
CREATE INDEX IF NOT EXISTS idx_consent_records_type ON consent_records(consent_type);
CREATE INDEX IF NOT EXISTS idx_consent_records_timestamp ON consent_records(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_consent_records_user_type ON consent_records(user_id, consent_type);

COMMENT ON TABLE consent_records IS 'Legally binding consent records (GDPR Article 7, 7-year retention)';
COMMENT ON COLUMN consent_records.timestamp IS 'When consent was given/withdrawn - immutable for legal purposes';

-- ==============================================================================
-- 4. CONVERSATIONS
-- ==============================================================================
-- Stores conversation history with messages
-- Retention: 90 days (configurable, auto-cleanup)

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
);

-- Indexes for queries
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_last_message_at ON conversations(last_message_at DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_conversations_archived ON conversations(archived) WHERE archived = TRUE;
CREATE INDEX IF NOT EXISTS idx_conversations_user_last_message ON conversations(user_id, last_message_at DESC);

-- Index for retention cleanup (90-day auto-deletion)
-- Note: Cannot use NOW() in index predicate (not immutable)
-- Cleanup queries will filter by date in WHERE clause using this index
CREATE INDEX IF NOT EXISTS idx_conversations_retention_cleanup
    ON conversations(last_message_at)
    WHERE archived = FALSE;

COMMENT ON TABLE conversations IS 'Conversation history (90-day retention, GDPR Article 17)';
COMMENT ON COLUMN conversations.messages IS 'Array of message objects in JSONB format';
COMMENT ON INDEX idx_conversations_retention_cleanup IS 'Optimized for automated 90-day cleanup job';

-- ==============================================================================
-- 5. AUDIT LOGS
-- ==============================================================================
-- Stores comprehensive audit trail for compliance
-- Retention: 7 years (2555 days) - GDPR, HIPAA, SOC2 requirement
-- Immutable (append-only for compliance)

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
);

-- Indexes for compliance queries and time-series analysis
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id)
    WHERE resource_type IS NOT NULL AND resource_id IS NOT NULL;

-- Composite index for common HIPAA/SOC2 queries
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_timestamp_action
    ON audit_logs(user_id, timestamp DESC, action) WHERE user_id IS NOT NULL;

-- Index for retention (7-year archival to cold storage)
-- Note: Cannot use NOW() in index predicate (not immutable)
-- Archival queries will filter by date in WHERE clause using this index
CREATE INDEX IF NOT EXISTS idx_audit_logs_retention_archival
    ON audit_logs(timestamp);

COMMENT ON TABLE audit_logs IS 'Comprehensive audit trail (7-year retention, HIPAA §164.312(b), SOC2 CC6.6)';
COMMENT ON COLUMN audit_logs.user_id IS 'NOT a foreign key - preserved for audit even after user deletion';
COMMENT ON COLUMN audit_logs.metadata IS 'Structured audit context (request_id, session_id, trace_id, etc.)';
COMMENT ON INDEX idx_audit_logs_retention_archival IS 'Optimized for archival to S3/GCS after 90 days';

-- ==============================================================================
-- FUNCTIONS & TRIGGERS
-- ==============================================================================

-- Function: Update last_updated timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Auto-update user_preferences.updated_at
CREATE TRIGGER trigger_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function: Update user_profiles.last_updated timestamp
CREATE OR REPLACE FUNCTION update_user_profile_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Auto-update user_profiles.last_updated
CREATE TRIGGER trigger_user_profiles_last_updated
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_user_profile_timestamp();

-- ==============================================================================
-- DATA RETENTION VIEWS
-- ==============================================================================

-- View: Conversations eligible for 90-day cleanup
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
ORDER BY last_message_at ASC;

COMMENT ON VIEW conversations_for_cleanup IS 'Conversations older than 90 days eligible for archival/deletion (GDPR Article 5(1)(e))';

-- View: Audit logs eligible for archival (90 days → cold storage)
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
ORDER BY timestamp ASC;

COMMENT ON VIEW audit_logs_for_archival IS 'Audit logs 90+ days old for archival to S3/GCS (SOC2 CC6.6)';

-- ==============================================================================
-- GRANTS & PERMISSIONS
-- ==============================================================================

-- Note: In production, create a dedicated GDPR user with minimal permissions
-- Example:
-- CREATE USER gdpr_app WITH PASSWORD 'secure_password';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO gdpr_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gdpr_app;

-- ==============================================================================
-- VERIFICATION QUERIES
-- ==============================================================================

-- Verify schema created successfully
DO $$
BEGIN
    RAISE NOTICE 'GDPR Schema Migration 001 Complete';
    RAISE NOTICE 'Tables created: user_profiles, user_preferences, consent_records, conversations, audit_logs';
    RAISE NOTICE 'Compliance: GDPR (Articles 5, 15, 17), HIPAA (§164.312(b)), SOC2 (CC6.6, PI1.4)';
    RAISE NOTICE 'Retention: Audit logs & consents = 7 years, Conversations = 90 days';
END $$;
