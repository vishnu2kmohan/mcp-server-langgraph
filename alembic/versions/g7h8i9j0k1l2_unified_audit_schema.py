"""Unified audit schema for regulatory compliance

Revision ID: g7h8i9j0k1l2
Revises: f6g7h8i9j0k1
Create Date: 2024-12-14

Implements unified audit logging for GDPR, HIPAA, SOC 2, FedRAMP, and EU AI Act:
- Event classification (category, outcome)
- OpenTelemetry correlation (trace_id, span_id)
- Multi-tenancy support (organization_id)
- Actor typing (actor_type)
- AI operation logging (ai_operation JSONB)
- Cryptographic integrity (sequence_number, previous_hash, event_hash)
- Compliance metadata (regulation_tags, retention_days)

Regulatory Requirements:
- GDPR: Articles 15, 17 (data access, right to erasure)
- HIPAA: 45 CFR 164.312(b) (audit controls)
- SOC 2: CC6.x, CC7.x (access controls, system operations)
- FedRAMP: NIST 800-53 AU-2, AU-3, AU-9, AU-11
- EU AI Act: Articles 12, 19, 72 (AI system logging)
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "g7h8i9j0k1l2"
down_revision = "f6g7h8i9j0k1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add unified audit schema columns and indices.

    Extends existing audit_logs table with columns for:
    - Event classification
    - OpenTelemetry correlation
    - Multi-tenancy
    - AI operation details (EU AI Act)
    - Cryptographic integrity (FedRAMP AU-9)
    - Compliance metadata
    """
    # Add columns for unified audit facility
    op.execute("""
        DO $$
        BEGIN
            -- Event classification columns
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'category'
            ) THEN
                ALTER TABLE audit_logs ADD COLUMN category VARCHAR(50);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'outcome'
            ) THEN
                ALTER TABLE audit_logs ADD COLUMN outcome VARCHAR(20);
            END IF;

            -- Actor typing column
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'actor_type'
            ) THEN
                ALTER TABLE audit_logs ADD COLUMN actor_type VARCHAR(20);
            END IF;

            -- Multi-tenancy support
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'organization_id'
            ) THEN
                ALTER TABLE audit_logs ADD COLUMN organization_id VARCHAR(255);
            END IF;

            -- OpenTelemetry correlation columns
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'trace_id'
            ) THEN
                ALTER TABLE audit_logs ADD COLUMN trace_id VARCHAR(64);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'span_id'
            ) THEN
                ALTER TABLE audit_logs ADD COLUMN span_id VARCHAR(32);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'session_id'
            ) THEN
                ALTER TABLE audit_logs ADD COLUMN session_id VARCHAR(255);
            END IF;

            -- AI operation details (EU AI Act Articles 12, 19, 72)
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'ai_operation'
            ) THEN
                ALTER TABLE audit_logs ADD COLUMN ai_operation JSONB;
            END IF;

            -- Cryptographic integrity columns (FedRAMP AU-9)
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'sequence_number'
            ) THEN
                ALTER TABLE audit_logs ADD COLUMN sequence_number BIGINT;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'previous_hash'
            ) THEN
                ALTER TABLE audit_logs ADD COLUMN previous_hash VARCHAR(64);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'event_hash'
            ) THEN
                ALTER TABLE audit_logs ADD COLUMN event_hash VARCHAR(64);
            END IF;

            -- Compliance metadata columns
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'regulation_tags'
            ) THEN
                ALTER TABLE audit_logs ADD COLUMN regulation_tags VARCHAR(20)[];
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'retention_days'
            ) THEN
                ALTER TABLE audit_logs ADD COLUMN retention_days INTEGER DEFAULT 2555;
            END IF;
        END $$;
    """)

    # Create indices for unified audit facility
    # Category-based queries (GDPR, HIPAA)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_unified_category
        ON audit_logs(category) WHERE category IS NOT NULL
    """)

    # Outcome-based queries (security monitoring)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_unified_outcome
        ON audit_logs(outcome) WHERE outcome IS NOT NULL
    """)

    # Multi-tenancy queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_unified_org
        ON audit_logs(organization_id) WHERE organization_id IS NOT NULL
    """)

    # OpenTelemetry correlation queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_unified_trace
        ON audit_logs(trace_id) WHERE trace_id IS NOT NULL
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_unified_session
        ON audit_logs(session_id) WHERE session_id IS NOT NULL
    """)

    # Hash chain integrity queries (FedRAMP AU-9)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_unified_sequence
        ON audit_logs(sequence_number) WHERE sequence_number IS NOT NULL
    """)

    # Regulation-specific queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_unified_regulation
        ON audit_logs USING GIN(regulation_tags) WHERE regulation_tags IS NOT NULL
    """)

    # Composite indices for compliance reports
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_unified_category_time
        ON audit_logs(category, timestamp DESC) WHERE category IS NOT NULL
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_unified_org_time
        ON audit_logs(organization_id, timestamp DESC) WHERE organization_id IS NOT NULL
    """)

    # AI operation queries (EU AI Act)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_unified_ai_model
        ON audit_logs((ai_operation->>'model_id')) WHERE ai_operation IS NOT NULL
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_unified_ai_provider
        ON audit_logs((ai_operation->>'provider')) WHERE ai_operation IS NOT NULL
    """)

    # Comments for documentation
    op.execute("""
        COMMENT ON COLUMN audit_logs.category IS 'Event category: authentication, authorization, data_access, data_modification, ai_operation, system, security, compliance'
    """)
    op.execute("""
        COMMENT ON COLUMN audit_logs.outcome IS 'Event outcome: success, failure, denied, error'
    """)
    op.execute("""
        COMMENT ON COLUMN audit_logs.trace_id IS 'OpenTelemetry trace ID for distributed tracing correlation'
    """)
    op.execute("""
        COMMENT ON COLUMN audit_logs.ai_operation IS 'AI operation details for EU AI Act Articles 12, 19, 72 compliance'
    """)
    op.execute("""
        COMMENT ON COLUMN audit_logs.sequence_number IS 'Sequential event number for hash chain integrity (FedRAMP AU-9)'
    """)
    op.execute("""
        COMMENT ON COLUMN audit_logs.event_hash IS 'HMAC-SHA256 hash for tamper-evidence (FedRAMP AU-9)'
    """)
    op.execute("""
        COMMENT ON COLUMN audit_logs.regulation_tags IS 'Applicable regulations: GDPR, HIPAA, SOC2, FedRAMP, EU_AI_ACT'
    """)
    op.execute("""
        COMMENT ON COLUMN audit_logs.retention_days IS 'Retention period in days (default: 2555 = 7 years)'
    """)


def downgrade() -> None:
    """Remove unified audit schema columns and indices.

    Note: Preserves base audit_logs table and columns from earlier migrations.
    Only removes columns and indices added by this migration.
    """
    # Drop indices added by this migration
    op.execute("DROP INDEX IF EXISTS idx_audit_unified_ai_provider")
    op.execute("DROP INDEX IF EXISTS idx_audit_unified_ai_model")
    op.execute("DROP INDEX IF EXISTS idx_audit_unified_org_time")
    op.execute("DROP INDEX IF EXISTS idx_audit_unified_category_time")
    op.execute("DROP INDEX IF EXISTS idx_audit_unified_regulation")
    op.execute("DROP INDEX IF EXISTS idx_audit_unified_sequence")
    op.execute("DROP INDEX IF EXISTS idx_audit_unified_session")
    op.execute("DROP INDEX IF EXISTS idx_audit_unified_trace")
    op.execute("DROP INDEX IF EXISTS idx_audit_unified_org")
    op.execute("DROP INDEX IF EXISTS idx_audit_unified_outcome")
    op.execute("DROP INDEX IF EXISTS idx_audit_unified_category")

    # Remove columns added by this migration
    op.execute("""
        DO $$
        BEGIN
            -- Remove retention_days
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'retention_days'
            ) THEN
                ALTER TABLE audit_logs DROP COLUMN retention_days;
            END IF;

            -- Remove regulation_tags
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'regulation_tags'
            ) THEN
                ALTER TABLE audit_logs DROP COLUMN regulation_tags;
            END IF;

            -- Remove event_hash
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'event_hash'
            ) THEN
                ALTER TABLE audit_logs DROP COLUMN event_hash;
            END IF;

            -- Remove previous_hash
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'previous_hash'
            ) THEN
                ALTER TABLE audit_logs DROP COLUMN previous_hash;
            END IF;

            -- Remove sequence_number
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'sequence_number'
            ) THEN
                ALTER TABLE audit_logs DROP COLUMN sequence_number;
            END IF;

            -- Remove ai_operation
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'ai_operation'
            ) THEN
                ALTER TABLE audit_logs DROP COLUMN ai_operation;
            END IF;

            -- Remove session_id
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'session_id'
            ) THEN
                ALTER TABLE audit_logs DROP COLUMN session_id;
            END IF;

            -- Remove span_id
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'span_id'
            ) THEN
                ALTER TABLE audit_logs DROP COLUMN span_id;
            END IF;

            -- Remove trace_id
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'trace_id'
            ) THEN
                ALTER TABLE audit_logs DROP COLUMN trace_id;
            END IF;

            -- Remove organization_id
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'organization_id'
            ) THEN
                ALTER TABLE audit_logs DROP COLUMN organization_id;
            END IF;

            -- Remove actor_type
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'actor_type'
            ) THEN
                ALTER TABLE audit_logs DROP COLUMN actor_type;
            END IF;

            -- Remove outcome
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'outcome'
            ) THEN
                ALTER TABLE audit_logs DROP COLUMN outcome;
            END IF;

            -- Remove category
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'category'
            ) THEN
                ALTER TABLE audit_logs DROP COLUMN category;
            END IF;
        END $$;
    """)
