"""Add notes, phase_checkpoints, and compliance_reports tables

Revision ID: f7g8h9i0j1k2
Revises: 65ec89011b7b
Create Date: 2026-03-18 00:00:00.000000

Migrates agentic memory from file-based storage to PostgreSQL:
- notes: Structured notes with FTS (tsvector + GIN)
- phase_checkpoints: Phase completion checkpoints (distinct from LangGraph conversation checkpoints)
- compliance_reports: SOC 2 compliance report storage with JSONB evidence items
"""

from typing import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f7g8h9i0j1k2"
down_revision: str | None = "65ec89011b7b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create notes, phase_checkpoints, and compliance_reports tables with FTS."""

    # ==========================================================================
    # 1. NOTES TABLE
    # ==========================================================================

    op.execute(
        """
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
        )
        """
    )

    # Indices for notes
    op.execute("CREATE INDEX IF NOT EXISTS ix_notes_user_created ON notes(user_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notes_session_id ON notes(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notes_category ON notes(category)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notes_tags ON notes USING gin(tags)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notes_search_vector ON notes USING gin(search_vector)")

    # Populate search_vector for any existing rows
    op.execute(
        """
        UPDATE notes SET search_vector =
            setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(content, '')), 'B')
        WHERE search_vector IS NULL
        """
    )

    # Create trigger function for notes search_vector auto-update
    op.execute(
        """
        CREATE OR REPLACE FUNCTION notes_search_vector_update()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.content, '')), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute(
        """
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
        $$
        """
    )

    op.execute(
        "COMMENT ON TABLE notes IS 'Structured notes for agentic memory (12-factor migration from NOTES.md/NOTES.json)'"
    )

    # ==========================================================================
    # 2. PHASE_CHECKPOINTS TABLE
    # ==========================================================================

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS phase_checkpoints (
            id VARCHAR(36) PRIMARY KEY,
            phase VARCHAR(100) NOT NULL,
            summary TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            artifacts JSONB NOT NULL DEFAULT '[]'::jsonb,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            session_id VARCHAR(36),
            user_id VARCHAR(255)
        )
        """
    )

    # Indices for phase_checkpoints
    op.execute("CREATE INDEX IF NOT EXISTS ix_phase_checkpoints_user_created ON phase_checkpoints(user_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_phase_checkpoints_phase ON phase_checkpoints(phase)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_phase_checkpoints_created_desc ON phase_checkpoints(created_at DESC)")

    op.execute(
        "COMMENT ON TABLE phase_checkpoints IS 'Phase completion checkpoints (distinct from LangGraph conversation checkpoints)'"
    )

    # ==========================================================================
    # 3. COMPLIANCE_REPORTS TABLE
    # ==========================================================================

    op.execute(
        """
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
        )
        """
    )

    # Indices for compliance_reports
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_compliance_reports_type_generated ON compliance_reports(report_type, generated_at DESC)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_compliance_reports_generated_desc ON compliance_reports(generated_at DESC)")

    op.execute("COMMENT ON TABLE compliance_reports IS 'SOC 2 compliance reports (12-factor migration from evidence/*.json)'")


def downgrade() -> None:
    """Drop notes, phase_checkpoints, and compliance_reports tables."""

    # Drop trigger first
    op.execute("DROP TRIGGER IF EXISTS notes_search_vector_trigger ON notes")
    op.execute("DROP FUNCTION IF EXISTS notes_search_vector_update()")

    op.execute("DROP TABLE IF EXISTS compliance_reports")
    op.execute("DROP TABLE IF EXISTS phase_checkpoints")
    op.execute("DROP TABLE IF EXISTS notes")
