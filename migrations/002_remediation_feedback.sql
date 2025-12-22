-- =============================================================================
-- Remediation Feedback Schema
-- =============================================================================
-- Purpose: Store feedback on AI remediation recommendations for learning
-- Features:
--   - Structured rejection reasons for constraint learning
--   - Execution outcome tracking for few-shot learning
--   - Pattern analysis indexes
--
-- Reference: ADR-0026 - Comprehensive Client Resilience Patterns
-- =============================================================================

-- Create rejection_reason enum type
CREATE TYPE rejection_reason AS ENUM (
    'too_risky',
    'incorrect_diagnosis',
    'wrong_command',
    'incomplete_steps',
    'not_relevant',
    'prefer_manual',
    'other'
);

-- =============================================================================
-- Remediation Feedback Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS remediation_feedback (
    -- Primary key
    feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign keys (references remediation_requests if it exists)
    remediation_id UUID NOT NULL,
    recommendation_id UUID NOT NULL,

    -- Alert context for pattern matching
    alert_type VARCHAR(255) NOT NULL,
    alert_labels JSONB NOT NULL DEFAULT '{}',
    severity VARCHAR(50) NOT NULL,

    -- Feedback data
    action VARCHAR(50) NOT NULL CHECK (action IN ('approved', 'rejected')),
    reason rejection_reason,
    reason_detail TEXT,
    admin_user_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Post-execution feedback (for approved remediations)
    execution_success BOOLEAN,
    execution_time_seconds FLOAT,
    admin_notes TEXT,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- Indexes for Query Performance
-- =============================================================================

-- Index for finding approved examples by alert type (few-shot learning)
CREATE INDEX idx_feedback_alert_type_action
    ON remediation_feedback(alert_type, action)
    WHERE action = 'approved';

-- Index for rejection pattern analysis
CREATE INDEX idx_feedback_reason
    ON remediation_feedback(reason)
    WHERE reason IS NOT NULL;

-- Index for recent feedback queries
CREATE INDEX idx_feedback_timestamp
    ON remediation_feedback(timestamp DESC);

-- Index for finding feedback by remediation ID
CREATE INDEX idx_feedback_remediation_id
    ON remediation_feedback(remediation_id);

-- Index for user-specific feedback queries
CREATE INDEX idx_feedback_admin_user
    ON remediation_feedback(admin_user_id);

-- =============================================================================
-- Trigger: Update timestamp on modification
-- =============================================================================

CREATE OR REPLACE FUNCTION update_feedback_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_feedback_updated_at
    BEFORE UPDATE ON remediation_feedback
    FOR EACH ROW
    EXECUTE FUNCTION update_feedback_updated_at();

-- =============================================================================
-- Comments for Documentation
-- =============================================================================

COMMENT ON TABLE remediation_feedback IS
    'Stores feedback on AI remediation recommendations for model tuning';

COMMENT ON COLUMN remediation_feedback.alert_type IS
    'Alert name for pattern matching (e.g., HighCPU, HighMemory)';

COMMENT ON COLUMN remediation_feedback.alert_labels IS
    'Alert labels as JSONB for context matching';

COMMENT ON COLUMN remediation_feedback.reason IS
    'Structured rejection reason for constraint learning';

COMMENT ON COLUMN remediation_feedback.reason_detail IS
    'Free-form detail for "other" reason or additional context';

COMMENT ON COLUMN remediation_feedback.execution_success IS
    'Whether the executed remediation successfully resolved the alert';

COMMENT ON COLUMN remediation_feedback.execution_time_seconds IS
    'Time taken to execute the remediation steps';
