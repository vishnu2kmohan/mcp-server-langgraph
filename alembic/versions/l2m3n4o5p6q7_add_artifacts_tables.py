"""Add artifacts and artifact_versions tables

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
Create Date: 2025-12-21

Creates:
- artifacts: Canvas artifacts storage with versioning
- artifact_versions: Version history shadow table

Implements:
- Phase 2: Hybrid Canvas Artifacts API
- Multi-layer storage: PostgreSQL (primary) -> Redis (cache) -> S3/GCS/Azure (hybrid)

Reference: ADR - Hybrid Canvas Architecture
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "l2m3n4o5p6q7"
down_revision: str | Sequence[str] | None = "k1l2m3n4o5p6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Create artifacts and artifact_versions tables.

    Schema design:
    - artifacts: Stores current artifact state with version tracking
    - artifact_versions: Shadow table for complete version history

    Features:
    - JSONB for flexible edit metadata
    - Full-text search via TSVECTOR
    - Hybrid storage support (inline/s3/gcs/azure)
    - User-scoped queries for security
    """
    # ==========================================================================
    # ARTIFACTS TABLE
    # ==========================================================================
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS artifacts (
            -- Primary key (UUID as string for compatibility)
            id VARCHAR(36) PRIMARY KEY,

            -- Session and user associations
            session_id VARCHAR(36) NOT NULL,
            user_id VARCHAR(255) NOT NULL,

            -- Content fields
            type VARCHAR(50) NOT NULL DEFAULT 'code',
            title VARCHAR(255) NOT NULL DEFAULT 'Untitled Artifact',
            content TEXT NOT NULL,
            content_type VARCHAR(20) NOT NULL DEFAULT 'code',

            -- Versioning
            version INTEGER NOT NULL DEFAULT 1,

            -- Hybrid storage support
            -- 'inline' = content stored in PostgreSQL
            -- 's3', 'gcs', 'azure' = content stored in cloud, storage_key has path
            storage_type VARCHAR(20) NOT NULL DEFAULT 'inline',
            storage_key VARCHAR(512),

            -- Flexible metadata (JSONB)
            edit_metadata JSONB,

            -- Timestamps
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            -- Full-text search vector (maintained by trigger)
            search_vector TSVECTOR
        )
        """
    )

    # INDEXES FOR ARTIFACTS
    op.execute("CREATE INDEX IF NOT EXISTS ix_artifacts_session_id ON artifacts(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_artifacts_user_id ON artifacts(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_artifacts_session_updated ON artifacts(session_id, updated_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_artifacts_user_updated ON artifacts(user_id, updated_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_artifacts_user_session ON artifacts(user_id, session_id)")
    # GIN index for full-text search
    op.execute("CREATE INDEX IF NOT EXISTS ix_artifacts_search_vector ON artifacts USING gin(search_vector)")

    # UPDATED_AT TRIGGER FOR ARTIFACTS
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_artifact_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute("DROP TRIGGER IF EXISTS trigger_artifact_updated_at ON artifacts")
    op.execute(
        """
        CREATE TRIGGER trigger_artifact_updated_at
            BEFORE UPDATE ON artifacts
            FOR EACH ROW
            EXECUTE FUNCTION update_artifact_updated_at()
        """
    )

    # FULL-TEXT SEARCH TRIGGER FOR ARTIFACTS
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_artifact_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector = to_tsvector('english',
                COALESCE(NEW.title, '') || ' ' ||
                COALESCE(NEW.content, '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute("DROP TRIGGER IF EXISTS trigger_artifact_search_vector ON artifacts")
    op.execute(
        """
        CREATE TRIGGER trigger_artifact_search_vector
            BEFORE INSERT OR UPDATE ON artifacts
            FOR EACH ROW
            EXECUTE FUNCTION update_artifact_search_vector()
        """
    )

    # COMMENTS FOR ARTIFACTS
    op.execute("COMMENT ON TABLE artifacts IS 'Canvas artifacts storage for Hybrid Canvas feature with versioning support'")
    op.execute("COMMENT ON COLUMN artifacts.type IS 'Artifact type: code, markdown, json, jsx, mermaid, html'")
    op.execute("COMMENT ON COLUMN artifacts.content_type IS 'Content MIME type hint: code, markdown, json, etc.'")
    op.execute("COMMENT ON COLUMN artifacts.storage_type IS 'Storage backend: inline (PostgreSQL), s3, gcs, or azure'")
    op.execute("COMMENT ON COLUMN artifacts.storage_key IS 'Cloud storage key when storage_type is not inline'")
    op.execute("COMMENT ON COLUMN artifacts.edit_metadata IS 'JSONB metadata: {edit_type, ai_confidence, language, etc.}'")

    # ==========================================================================
    # ARTIFACT_VERSIONS TABLE (Shadow table for version history)
    # ==========================================================================
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS artifact_versions (
            -- Primary key (UUID as string)
            id VARCHAR(36) PRIMARY KEY,

            -- Foreign key to parent artifact
            artifact_id VARCHAR(36) NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,

            -- Version info
            version INTEGER NOT NULL,
            parent_version INTEGER,

            -- Content snapshot
            content TEXT NOT NULL,
            content_type VARCHAR(20) NOT NULL DEFAULT 'code',

            -- Hybrid storage support (same as artifacts)
            storage_type VARCHAR(20) NOT NULL DEFAULT 'inline',
            storage_key VARCHAR(512),

            -- Who created this version
            created_by VARCHAR(255) NOT NULL,

            -- When this version was created
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            -- Version metadata (JSONB)
            -- Stores: edit_type, ai_confidence, diff_stats, etc.
            version_metadata JSONB,

            -- Unique constraint: one version number per artifact
            CONSTRAINT uq_artifact_version UNIQUE (artifact_id, version)
        )
        """
    )

    # INDEXES FOR ARTIFACT_VERSIONS
    op.execute("CREATE INDEX IF NOT EXISTS ix_artifact_versions_artifact_id ON artifact_versions(artifact_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_artifact_versions_artifact_version ON artifact_versions(artifact_id, version)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_artifact_versions_created_at ON artifact_versions(created_at DESC)")

    # COMMENTS FOR ARTIFACT_VERSIONS
    op.execute("COMMENT ON TABLE artifact_versions IS 'Version history shadow table for artifacts, enables history/rollback'")
    op.execute(
        "COMMENT ON COLUMN artifact_versions.parent_version IS 'Version this was derived from (for future DAG support)'"
    )
    op.execute("COMMENT ON COLUMN artifact_versions.created_by IS 'User ID who created this version'")
    op.execute(
        "COMMENT ON COLUMN artifact_versions.version_metadata IS "
        "'JSONB metadata: {edit_type: user|ai-suggestion|ai-generation, ai_confidence, diff_stats}'"
    )

    # ==========================================================================
    # UTILITY FUNCTIONS
    # ==========================================================================

    # Function to get latest N versions of an artifact
    op.execute(
        """
        CREATE OR REPLACE FUNCTION get_artifact_versions(
            p_artifact_id VARCHAR(36),
            p_limit INTEGER DEFAULT 10
        )
        RETURNS TABLE (
            version INTEGER,
            content TEXT,
            content_type VARCHAR(20),
            created_by VARCHAR(255),
            created_at TIMESTAMPTZ,
            version_metadata JSONB
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT
                av.version,
                av.content,
                av.content_type,
                av.created_by,
                av.created_at,
                av.version_metadata
            FROM artifact_versions av
            WHERE av.artifact_id = p_artifact_id
            ORDER BY av.version DESC
            LIMIT p_limit;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute(
        "COMMENT ON FUNCTION get_artifact_versions IS 'Retrieve latest N versions of an artifact for version history display'"
    )


def downgrade() -> None:
    """
    Drop artifacts and artifact_versions tables.

    WARNING: This will delete all artifact data permanently.
    """
    # Drop functions first
    op.execute("DROP FUNCTION IF EXISTS get_artifact_versions(VARCHAR, INTEGER)")
    op.execute("DROP FUNCTION IF EXISTS update_artifact_search_vector() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS update_artifact_updated_at() CASCADE")

    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trigger_artifact_search_vector ON artifacts")
    op.execute("DROP TRIGGER IF EXISTS trigger_artifact_updated_at ON artifacts")

    # Drop tables (artifact_versions first due to FK)
    op.execute("DROP TABLE IF EXISTS artifact_versions CASCADE")
    op.execute("DROP TABLE IF EXISTS artifacts CASCADE")
