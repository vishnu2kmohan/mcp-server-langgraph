"""Add user_id, created_by, and embedding status columns to execution_plans.

Revision ID: b8c9d0e1f2a3
Revises: z6a7b8c9d0e1
Create Date: 2026-01-31

Phase 2: Fix Embeddings Schema
- Add user_id column for GDPR filtering (export/delete by user)
- Add created_by column for ownership tracking (matching PlanTemplate pattern)
- Add embedding status columns for self-healing embedding service (Phase 7.25)

Also adds embedding status columns to plan_templates table.

GDPR Compliance:
- user_id enables Article 15 (Right of Access) - export user's plans
- user_id enables Article 17 (Right to Erasure) - delete user's plans
- Indexed for efficient GDPR queries
"""

from typing import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "z6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add user columns and embedding status tracking to execution_plans."""

    # Add user_id column to execution_plans
    # Required for GDPR filtering (export/delete by user)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'execution_plans'
                AND column_name = 'user_id'
            ) THEN
                ALTER TABLE execution_plans
                ADD COLUMN user_id VARCHAR(255);

                -- Create index for GDPR queries
                CREATE INDEX ix_execution_plans_user_id
                ON execution_plans (user_id);
            END IF;
        END
        $$;
        """
    )

    # Add created_by column to execution_plans
    # Matches PlanTemplate pattern for ownership tracking
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'execution_plans'
                AND column_name = 'created_by'
            ) THEN
                ALTER TABLE execution_plans
                ADD COLUMN created_by VARCHAR(255);

                -- Create index for ownership queries
                CREATE INDEX ix_execution_plans_created_by
                ON execution_plans (created_by);
            END IF;
        END
        $$;
        """
    )

    # Add embedding status columns to execution_plans
    # Required for Phase 7.25 self-healing embedding service
    op.execute(
        """
        DO $$
        BEGIN
            -- embedding_status: pending|processing|completed|failed
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'execution_plans'
                AND column_name = 'embedding_status'
            ) THEN
                ALTER TABLE execution_plans
                ADD COLUMN embedding_status VARCHAR(20) DEFAULT 'pending';
            END IF;

            -- embedding_error: Error reason if failed
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'execution_plans'
                AND column_name = 'embedding_error'
            ) THEN
                ALTER TABLE execution_plans
                ADD COLUMN embedding_error VARCHAR(255);
            END IF;

            -- embedding_failed_at: Timestamp of last failure
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'execution_plans'
                AND column_name = 'embedding_failed_at'
            ) THEN
                ALTER TABLE execution_plans
                ADD COLUMN embedding_failed_at TIMESTAMPTZ;
            END IF;
        END
        $$;
        """
    )

    # Add embedding status columns to plan_templates
    # Required for Phase 7.25 self-healing embedding service
    op.execute(
        """
        DO $$
        BEGIN
            -- embedding_status: pending|processing|completed|failed
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'plan_templates'
                AND column_name = 'embedding_status'
            ) THEN
                ALTER TABLE plan_templates
                ADD COLUMN embedding_status VARCHAR(20) DEFAULT 'pending';

                -- Backfill: templates with embeddings are 'completed', without are 'pending'
                UPDATE plan_templates
                SET embedding_status = CASE
                    WHEN description_embedding IS NOT NULL THEN 'completed'
                    ELSE 'pending'
                END;
            END IF;

            -- embedding_error: Error reason if failed
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'plan_templates'
                AND column_name = 'embedding_error'
            ) THEN
                ALTER TABLE plan_templates
                ADD COLUMN embedding_error VARCHAR(255);
            END IF;

            -- embedding_failed_at: Timestamp of last failure
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'plan_templates'
                AND column_name = 'embedding_failed_at'
            ) THEN
                ALTER TABLE plan_templates
                ADD COLUMN embedding_failed_at TIMESTAMPTZ;
            END IF;
        END
        $$;
        """
    )

    # Backfill embedding_status for execution_plans
    # Note: execution_plans table doesn't have description_embedding column,
    # so all existing records start as 'pending'
    op.execute(
        """
        UPDATE execution_plans
        SET embedding_status = 'pending'
        WHERE embedding_status IS NULL;
        """
    )


def downgrade() -> None:
    """Remove user columns and embedding status tracking."""

    # Remove columns from execution_plans
    op.execute("DROP INDEX IF EXISTS ix_execution_plans_user_id")
    op.execute("DROP INDEX IF EXISTS ix_execution_plans_created_by")
    op.execute(
        """
        DO $$
        BEGIN
            ALTER TABLE execution_plans
            DROP COLUMN IF EXISTS user_id,
            DROP COLUMN IF EXISTS created_by,
            DROP COLUMN IF EXISTS embedding_status,
            DROP COLUMN IF EXISTS embedding_error,
            DROP COLUMN IF EXISTS embedding_failed_at;
        END
        $$;
        """
    )

    # Remove columns from plan_templates
    op.execute(
        """
        DO $$
        BEGIN
            ALTER TABLE plan_templates
            DROP COLUMN IF EXISTS embedding_status,
            DROP COLUMN IF EXISTS embedding_error,
            DROP COLUMN IF EXISTS embedding_failed_at;
        END
        $$;
        """
    )
