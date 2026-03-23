"""Add missing last_used_at and updated_at columns to plan_templates

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2026-03-21

The initial plan_templates migration (e1f2g3h4i5j6) omitted the
last_used_at and updated_at columns that PlanTemplateModel defines.
This causes 10 integration test failures in
test_postgres_plan_template_repository.py.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i0j1k2l3m4n5"
down_revision: str | None = "h9i0j1k2l3m4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add last_used_at and updated_at columns to plan_templates."""
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'plan_templates' AND column_name = 'last_used_at'
            ) THEN
                ALTER TABLE plan_templates
                    ADD COLUMN last_used_at TIMESTAMPTZ;
                RAISE NOTICE 'Added last_used_at column to plan_templates';
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'plan_templates' AND column_name = 'updated_at'
            ) THEN
                ALTER TABLE plan_templates
                    ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
                RAISE NOTICE 'Added updated_at column to plan_templates';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """Remove last_used_at and updated_at columns from plan_templates."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'plan_templates' AND column_name = 'updated_at'
            ) THEN
                ALTER TABLE plan_templates DROP COLUMN updated_at;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'plan_templates' AND column_name = 'last_used_at'
            ) THEN
                ALTER TABLE plan_templates DROP COLUMN last_used_at;
            END IF;
        END $$;
        """
    )
