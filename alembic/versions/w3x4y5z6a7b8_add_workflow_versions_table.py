"""Add workflow_versions table for version history

Revision ID: w3x4y5z6a7b8
Revises: v2w3x4y5z6a7
Create Date: 2026-01-03

This migration adds:
1. workflow_versions table for append-only revision history
2. head_version_id and source_text columns to workflows table
3. Proper indices for efficient version queries

The workflow_versions table enables:
- Durable workflows with draft/publish lifecycle
- Version diffing and rollback
- Prompt-level telemetry linkage for optimization
- Audit trail of all workflow changes

References:
- Plan: Chat-to-Workflow Feature (validated by 4 independent reviews)
- ADR-0089: Prompt Architecture Centralization
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "w3x4y5z6a7b8"
down_revision: str | None = "v2w3x4y5z6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add workflow_versions table and extend workflows table."""

    # ==========================================================================
    # 1. CREATE workflow_versions TABLE
    # ==========================================================================

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS workflow_versions (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            workflow_id VARCHAR(36) NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
            version_number INT NOT NULL,
            graph_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            source_text TEXT,
            commit_message TEXT,
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            -- Telemetry linkage for prompt optimization
            prompt_version VARCHAR(50),
            prompt_hash VARCHAR(64),
            prompt_model VARCHAR(100),

            -- Unique constraint: one version number per workflow
            CONSTRAINT workflow_versions_unique UNIQUE (workflow_id, version_number),

            -- Ensure version numbers are positive
            CONSTRAINT workflow_versions_version_positive CHECK (version_number > 0)
        )
        """
    )

    # ==========================================================================
    # 2. ADD INDICES for workflow_versions
    # ==========================================================================

    # Index for listing versions by workflow
    op.execute("CREATE INDEX IF NOT EXISTS ix_workflow_versions_workflow_id ON workflow_versions(workflow_id)")

    # Index for ordering by creation time (descending for recent-first)
    op.execute("CREATE INDEX IF NOT EXISTS ix_workflow_versions_created_at ON workflow_versions(workflow_id, created_at DESC)")

    # Index for finding versions by prompt version (for telemetry queries)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_workflow_versions_prompt_version "
        "ON workflow_versions(prompt_version) WHERE prompt_version IS NOT NULL"
    )

    # Composite index for efficient latest version lookup
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_workflow_versions_workflow_version "
        "ON workflow_versions(workflow_id, version_number DESC)"
    )

    # ==========================================================================
    # 3. ADD COLUMNS to workflows TABLE
    # ==========================================================================

    # Add head_version_id column to workflows (points to current version)
    op.add_column(
        "workflows",
        sa.Column(
            "head_version_id",
            sa.String(36),
            nullable=True,
        ),
    )

    # Add source_text column to workflows (for Monaco editor sync)
    op.add_column(
        "workflows",
        sa.Column(
            "source_text",
            sa.Text(),
            nullable=True,
        ),
    )

    # ==========================================================================
    # 4. ADD FOREIGN KEY for head_version_id
    # ==========================================================================

    # Note: We add this as a separate constraint to handle the circular reference
    # (workflows.head_version_id -> workflow_versions.id, but workflow_versions.workflow_id -> workflows.id)
    op.execute(
        """
        ALTER TABLE workflows
        ADD CONSTRAINT fk_workflows_head_version
        FOREIGN KEY (head_version_id)
        REFERENCES workflow_versions(id)
        ON DELETE SET NULL
        """
    )

    # ==========================================================================
    # 5. ADD COMMENTS
    # ==========================================================================

    op.execute(
        "COMMENT ON TABLE workflow_versions IS 'Append-only version history for workflows, enabling diff/rollback/audit'"
    )

    op.execute(
        "COMMENT ON COLUMN workflow_versions.prompt_version IS "
        "'Prompt version used to generate this workflow version (for telemetry)'"
    )

    op.execute(
        "COMMENT ON COLUMN workflow_versions.prompt_hash IS 'SHA-256 hash of prompt content (for tracking prompt changes)'"
    )

    op.execute(
        "COMMENT ON COLUMN workflow_versions.prompt_model IS 'LLM model used to generate this version (e.g., claude-opus-4-5)'"
    )

    op.execute("COMMENT ON COLUMN workflows.head_version_id IS 'Points to the current/active version of this workflow'")

    op.execute("COMMENT ON COLUMN workflows.source_text IS 'Source code representation of workflow (for Monaco editor sync)'")


def downgrade() -> None:
    """Remove workflow_versions table and extensions to workflows table."""

    # ==========================================================================
    # 1. REMOVE COLUMNS from workflows TABLE
    # ==========================================================================

    # Drop foreign key constraint first
    op.execute("ALTER TABLE workflows DROP CONSTRAINT IF EXISTS fk_workflows_head_version")

    # Drop columns
    op.drop_column("workflows", "source_text")
    op.drop_column("workflows", "head_version_id")

    # ==========================================================================
    # 2. DROP INDICES for workflow_versions
    # ==========================================================================

    op.execute("DROP INDEX IF EXISTS ix_workflow_versions_workflow_version")
    op.execute("DROP INDEX IF EXISTS ix_workflow_versions_prompt_version")
    op.execute("DROP INDEX IF EXISTS ix_workflow_versions_created_at")
    op.execute("DROP INDEX IF EXISTS ix_workflow_versions_workflow_id")

    # ==========================================================================
    # 3. DROP workflow_versions TABLE
    # ==========================================================================

    op.execute("DROP TABLE IF EXISTS workflow_versions CASCADE")
