-- =============================================================================
-- Push Subscriptions Schema
-- =============================================================================
-- Purpose: Store Web Push API subscription data for push notifications
-- Features:
--   - Store VAPID-based push subscription endpoints
--   - Track subscription keys (p256dh and auth)
--   - Handle subscription expiry and cleanup
--   - Support multi-device subscriptions per user
--
-- Reference: ADR-0026 - Comprehensive Client Resilience Patterns
-- =============================================================================

-- =============================================================================
-- Push Subscriptions Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS push_subscriptions (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- User association (references users table if it exists)
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
);

-- =============================================================================
-- Indexes for Query Performance
-- =============================================================================

-- Index for finding all subscriptions for a user
CREATE INDEX idx_push_subscriptions_user_id
    ON push_subscriptions(user_id);

-- Index for finding expired subscriptions for cleanup
CREATE INDEX idx_push_subscriptions_expires
    ON push_subscriptions(expires_at)
    WHERE expires_at IS NOT NULL;

-- Index for endpoint lookups (for unsubscribe operations)
CREATE INDEX idx_push_subscriptions_endpoint
    ON push_subscriptions(endpoint);

-- Index for finding inactive subscriptions
CREATE INDEX idx_push_subscriptions_last_used
    ON push_subscriptions(last_used_at)
    WHERE last_used_at IS NOT NULL;

-- =============================================================================
-- Trigger: Update timestamp on modification
-- =============================================================================

CREATE OR REPLACE FUNCTION update_push_subscription_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_push_subscription_updated_at
    BEFORE UPDATE ON push_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_push_subscription_updated_at();

-- =============================================================================
-- Admin Push Subscriptions View
-- =============================================================================
-- View to quickly find all admin user subscriptions for critical alerts

-- Note: This view depends on the users table structure
-- If users table doesn't have an 'is_admin' column, adjust accordingly
CREATE OR REPLACE VIEW admin_push_subscriptions AS
SELECT ps.*
FROM push_subscriptions ps
-- Join with users table to filter admins when available
-- WHERE EXISTS (SELECT 1 FROM users u WHERE u.id = ps.user_id AND u.is_admin = true)
;

-- =============================================================================
-- Comments for Documentation
-- =============================================================================

COMMENT ON TABLE push_subscriptions IS
    'Stores Web Push API subscriptions for browser push notifications';

COMMENT ON COLUMN push_subscriptions.endpoint IS
    'Push service endpoint URL from PushSubscription.endpoint';

COMMENT ON COLUMN push_subscriptions.p256dh_key IS
    'User public key from PushSubscription.getKey("p256dh"), base64 encoded';

COMMENT ON COLUMN push_subscriptions.auth_key IS
    'Auth secret from PushSubscription.getKey("auth"), base64 encoded';

COMMENT ON COLUMN push_subscriptions.expires_at IS
    'Optional expiration time from PushSubscription.expirationTime';

COMMENT ON COLUMN push_subscriptions.last_used_at IS
    'Timestamp of last successful notification sent to this subscription';

COMMENT ON COLUMN push_subscriptions.device_name IS
    'User-provided device name for subscription management UI';
