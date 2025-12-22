"""Add push subscriptions and remediation feedback tables

Revision ID: k1l2m3n4o5p6
Revises: j0k1l2m3n4o5
Create Date: 2025-12-20

Creates:
- push_subscriptions: Web Push API subscription storage
- remediation_feedback: AI learning feedback from approvals/rejections

Implements:
- Phase 7: Push Notifications (Web Push API with VAPID)
- Phase 8: AI Model Tuning (Few-shot + Constraint learning)

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "k1l2m3n4o5p6"
down_revision: str | Sequence[str] | None = "j0k1l2m3n4o5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Create push subscriptions and remediation feedback tables.

    Security notes:
    - Push subscription keys are stored encrypted at rest (PostgreSQL TDE)
    - Feedback data is used for AI model improvement only
    """
    # ==========================================================================
    # PUSH SUBSCRIPTIONS TABLE
    # ==========================================================================
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            -- Primary key
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            -- User association
            user_id VARCHAR(255) NOT NULL,

            -- Web Push API subscription data
            endpoint TEXT NOT NULL,              -- Push service endpoint URL
            p256dh_key TEXT NOT NULL,            -- User's public key (base64 encoded)
            auth_key TEXT NOT NULL,              -- Auth secret (base64 encoded)

            -- Metadata
            user_agent TEXT,                     -- Browser/device info
            device_name TEXT,                    -- Optional user-provided device name

            -- Subscription lifecycle
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMPTZ,              -- Optional expiration time
            last_used_at TIMESTAMPTZ,            -- Track when last notification was sent

            -- Constraints
            CONSTRAINT unique_subscription_endpoint UNIQUE (endpoint)
        )
        """
    )

    # INDEXES FOR PUSH_SUBSCRIPTIONS
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_push_subscriptions_user_id "
        "ON push_subscriptions(user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_push_subscriptions_expires "
        "ON push_subscriptions(expires_at) WHERE expires_at IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_push_subscriptions_endpoint "
        "ON push_subscriptions(endpoint)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_push_subscriptions_last_used "
        "ON push_subscriptions(last_used_at) WHERE last_used_at IS NOT NULL"
    )

    # UPDATED_AT TRIGGER FOR PUSH_SUBSCRIPTIONS
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_push_subscription_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute("DROP TRIGGER IF EXISTS trigger_push_subscription_updated_at ON push_subscriptions")
    op.execute(
        """
        CREATE TRIGGER trigger_push_subscription_updated_at
            BEFORE UPDATE ON push_subscriptions
            FOR EACH ROW
            EXECUTE FUNCTION update_push_subscription_updated_at()
        """
    )

    # COMMENTS FOR PUSH_SUBSCRIPTIONS
    op.execute(
        "COMMENT ON TABLE push_subscriptions IS "
        "'Stores Web Push API subscriptions for browser push notifications'"
    )
    op.execute(
        "COMMENT ON COLUMN push_subscriptions.endpoint IS "
        "'Push service endpoint URL from PushSubscription.endpoint'"
    )
    op.execute(
        "COMMENT ON COLUMN push_subscriptions.p256dh_key IS "
        "'User public key from PushSubscription.getKey(\"p256dh\"), base64 encoded'"
    )
    op.execute(
        "COMMENT ON COLUMN push_subscriptions.auth_key IS "
        "'Auth secret from PushSubscription.getKey(\"auth\"), base64 encoded'"
    )
    op.execute(
        "COMMENT ON COLUMN push_subscriptions.expires_at IS "
        "'Optional expiration time from PushSubscription.expirationTime'"
    )
    op.execute(
        "COMMENT ON COLUMN push_subscriptions.last_used_at IS "
        "'Timestamp of last successful notification sent to this subscription'"
    )

    # ==========================================================================
    # REMEDIATION FEEDBACK TABLE
    # ==========================================================================
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS remediation_feedback (
            -- Primary key
            feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            -- Reference to remediation
            remediation_id VARCHAR(36) NOT NULL,
            recommendation_id VARCHAR(36) NOT NULL,

            -- Alert context for pattern matching
            alert_type VARCHAR(255) NOT NULL,
            alert_labels JSONB NOT NULL DEFAULT '{}',
            severity VARCHAR(50) NOT NULL,

            -- Feedback data
            action VARCHAR(50) NOT NULL,
            reason VARCHAR(100),
            reason_detail TEXT,
            admin_user_id VARCHAR(255) NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            -- Post-execution feedback
            execution_success BOOLEAN,
            execution_time_seconds FLOAT,
            admin_notes TEXT,

            -- Constraints
            CONSTRAINT remediation_feedback_action_valid
                CHECK (action IN ('approved', 'rejected')),
            CONSTRAINT remediation_feedback_reason_valid
                CHECK (reason IS NULL OR reason IN (
                    'too_risky', 'incorrect_diagnosis', 'wrong_command',
                    'incomplete_steps', 'not_relevant', 'prefer_manual', 'other'
                ))
        )
        """
    )

    # INDEXES FOR REMEDIATION_FEEDBACK
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_feedback_remediation_id "
        "ON remediation_feedback(remediation_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_feedback_alert_type "
        "ON remediation_feedback(alert_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_feedback_action "
        "ON remediation_feedback(action)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_feedback_reason "
        "ON remediation_feedback(reason) WHERE reason IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_feedback_timestamp "
        "ON remediation_feedback(timestamp DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_feedback_approved_by_type "
        "ON remediation_feedback(alert_type, timestamp DESC) "
        "WHERE action = 'approved'"
    )

    # COMMENTS FOR REMEDIATION_FEEDBACK
    op.execute(
        "COMMENT ON TABLE remediation_feedback IS "
        "'Stores remediation approval/rejection feedback for AI model tuning'"
    )
    op.execute(
        "COMMENT ON COLUMN remediation_feedback.alert_type IS "
        "'Alert name used for few-shot learning pattern matching'"
    )
    op.execute(
        "COMMENT ON COLUMN remediation_feedback.alert_labels IS "
        "'Alert labels (service, namespace, etc.) for context matching'"
    )
    op.execute(
        "COMMENT ON COLUMN remediation_feedback.reason IS "
        "'Structured rejection reason for constraint learning'"
    )
    op.execute(
        "COMMENT ON COLUMN remediation_feedback.execution_success IS "
        "'True if approved remediation executed successfully'"
    )

    # ==========================================================================
    # CLEANUP FUNCTIONS
    # ==========================================================================

    # Cleanup function for expired push subscriptions
    op.execute(
        """
        CREATE OR REPLACE FUNCTION cleanup_expired_push_subscriptions()
        RETURNS INTEGER AS $$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            DELETE FROM push_subscriptions
            WHERE expires_at IS NOT NULL AND expires_at < NOW();

            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RETURN deleted_count;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute(
        "COMMENT ON FUNCTION cleanup_expired_push_subscriptions IS "
        "'Removes expired push subscriptions - call periodically or via pg_cron'"
    )


def downgrade() -> None:
    """
    Drop push subscriptions and remediation feedback tables.

    WARNING: This will delete all subscription and feedback data permanently.
    """
    # Drop functions first
    op.execute("DROP FUNCTION IF EXISTS cleanup_expired_push_subscriptions()")
    op.execute("DROP FUNCTION IF EXISTS update_push_subscription_updated_at() CASCADE")

    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS trigger_push_subscription_updated_at ON push_subscriptions")

    # Drop tables
    op.execute("DROP TABLE IF EXISTS remediation_feedback CASCADE")
    op.execute("DROP TABLE IF EXISTS push_subscriptions CASCADE")
