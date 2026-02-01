"""Add v35.0 execution plan fields.

Revision ID: c0d1e2f3g4h5
Revises: b8c9d0e1f2a3
Create Date: 2026-02-01

Phase 2e: Add v35.0 RLM fields to execution_plans table.
- skills_needed: JSONB array of required skills
- selected_tool_ids: JSONB array of selected tool IDs
- llm_provider: LLM provider string (anthropic, google, openai)
- kb_focus: Knowledge base focus (all, kb_only, web_only, none)
- tool_preference: Tool preference setting
- tool_selection_mode: Tool selection mode (auto, manual, hybrid)

These fields enable:
- Audit trail for capability tracking
- Router output persistence
- Tool preference configuration
"""

from typing import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c0d1e2f3g4h5"
down_revision: str | None = "fea0842074ad"  # After merge_execution_plan_branches
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add v35.0 fields to execution_plans."""

    # Add skills_needed column (JSONB array)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'execution_plans'
                AND column_name = 'skills_needed'
            ) THEN
                ALTER TABLE execution_plans
                ADD COLUMN skills_needed JSONB;
            END IF;
        END
        $$;
        """
    )

    # Add selected_tool_ids column (JSONB array)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'execution_plans'
                AND column_name = 'selected_tool_ids'
            ) THEN
                ALTER TABLE execution_plans
                ADD COLUMN selected_tool_ids JSONB;
            END IF;
        END
        $$;
        """
    )

    # Add llm_provider column
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'execution_plans'
                AND column_name = 'llm_provider'
            ) THEN
                ALTER TABLE execution_plans
                ADD COLUMN llm_provider VARCHAR(50);
            END IF;
        END
        $$;
        """
    )

    # Add kb_focus column (all, kb_only, web_only, none)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'execution_plans'
                AND column_name = 'kb_focus'
            ) THEN
                ALTER TABLE execution_plans
                ADD COLUMN kb_focus VARCHAR(20);
            END IF;
        END
        $$;
        """
    )

    # Add tool_preference column (v35.0 Phase 2e)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'execution_plans'
                AND column_name = 'tool_preference'
            ) THEN
                ALTER TABLE execution_plans
                ADD COLUMN tool_preference VARCHAR(100);
            END IF;
        END
        $$;
        """
    )

    # Add tool_selection_mode column (auto, manual, hybrid)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'execution_plans'
                AND column_name = 'tool_selection_mode'
            ) THEN
                ALTER TABLE execution_plans
                ADD COLUMN tool_selection_mode VARCHAR(20);
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    """Remove v35.0 fields from execution_plans."""
    op.execute(
        """
        DO $$
        BEGIN
            ALTER TABLE execution_plans
            DROP COLUMN IF EXISTS skills_needed,
            DROP COLUMN IF EXISTS selected_tool_ids,
            DROP COLUMN IF EXISTS llm_provider,
            DROP COLUMN IF EXISTS kb_focus,
            DROP COLUMN IF EXISTS tool_preference,
            DROP COLUMN IF EXISTS tool_selection_mode;
        END
        $$;
        """
    )
