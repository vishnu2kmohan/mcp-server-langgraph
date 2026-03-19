-- Agentic Memory Tables for compliance_test database
--
-- Creates notes, phase_checkpoints, and compliance_reports tables
-- for the agentic memory subsystem (12-Factor migration from file-based storage).
--
-- Applied to: compliance_test database (via init-test-databases.sh)
-- Alembic equivalent: f7g8h9i0j1k2_add_notes_checkpoints_evidence.py
--
-- Tables:
--   notes              - Structured notes with FTS (tsvector + GIN)
--   phase_checkpoints  - Phase completion checkpoints (distinct from LangGraph conversation checkpoints)
--   compliance_reports - SOC 2 compliance report storage with JSONB evidence items

-- ==========================================================================
-- 1. NOTES TABLE
-- ==========================================================================

CREATE TABLE IF NOT EXISTS notes (
    id VARCHAR(36) PRIMARY KEY,
    content TEXT NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'general',
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    session_id VARCHAR(36),
    user_id VARCHAR(255),
    title VARCHAR(500),
    slug VARCHAR(500),
    search_vector TSVECTOR
);

CREATE INDEX IF NOT EXISTS ix_notes_user_created ON notes(user_id, created_at);
CREATE INDEX IF NOT EXISTS ix_notes_session_id ON notes(session_id);
CREATE INDEX IF NOT EXISTS ix_notes_category ON notes(category);
CREATE INDEX IF NOT EXISTS ix_notes_tags ON notes USING gin(tags);
CREATE INDEX IF NOT EXISTS ix_notes_search_vector ON notes USING gin(search_vector);

-- Populate search_vector for any existing rows
UPDATE notes SET search_vector =
    setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(content, '')), 'B')
WHERE search_vector IS NULL;

-- Trigger function for notes search_vector auto-update
CREATE OR REPLACE FUNCTION notes_search_vector_update()
RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.content, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'notes_search_vector_trigger'
    ) THEN
        CREATE TRIGGER notes_search_vector_trigger
        BEFORE INSERT OR UPDATE OF title, content ON notes
        FOR EACH ROW
        EXECUTE FUNCTION notes_search_vector_update();
    END IF;
END
$$;

COMMENT ON TABLE notes IS 'Structured notes for agentic memory (12-factor migration from NOTES.md/NOTES.json)';

-- ==========================================================================
-- 2. PHASE_CHECKPOINTS TABLE
-- ==========================================================================

CREATE TABLE IF NOT EXISTS phase_checkpoints (
    id VARCHAR(36) PRIMARY KEY,
    phase VARCHAR(100) NOT NULL,
    summary TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    artifacts JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    session_id VARCHAR(36),
    user_id VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS ix_phase_checkpoints_user_created ON phase_checkpoints(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_phase_checkpoints_phase ON phase_checkpoints(phase);
CREATE INDEX IF NOT EXISTS ix_phase_checkpoints_created_desc ON phase_checkpoints(created_at DESC);

COMMENT ON TABLE phase_checkpoints IS 'Phase completion checkpoints (distinct from LangGraph conversation checkpoints)';

-- ==========================================================================
-- 3. COMPLIANCE_REPORTS TABLE
-- ==========================================================================

CREATE TABLE IF NOT EXISTS compliance_reports (
    report_id VARCHAR(100) PRIMARY KEY,
    report_type VARCHAR(20) NOT NULL,
    generated_at VARCHAR(50) NOT NULL,
    period_start VARCHAR(50) NOT NULL,
    period_end VARCHAR(50) NOT NULL,
    evidence_items JSONB NOT NULL DEFAULT '[]'::jsonb,
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    compliance_score FLOAT NOT NULL,
    passed_controls INTEGER NOT NULL,
    failed_controls INTEGER NOT NULL,
    partial_controls INTEGER NOT NULL,
    total_controls INTEGER NOT NULL,
    user_id VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS ix_compliance_reports_type_generated ON compliance_reports(report_type, generated_at DESC);
CREATE INDEX IF NOT EXISTS ix_compliance_reports_generated_desc ON compliance_reports(generated_at DESC);

COMMENT ON TABLE compliance_reports IS 'SOC 2 compliance reports (12-factor migration from evidence/*.json)';

-- ==========================================================================
-- Done
-- ==========================================================================

DO $$
BEGIN
    RAISE NOTICE 'Agentic memory tables created: notes, phase_checkpoints, compliance_reports';
END
$$;
