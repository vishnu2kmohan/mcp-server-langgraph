"""Add pgvector extension and vector columns

Revision ID: v2w3x4y5z6a7
Revises: u1v2w3x4y5z6
Create Date: 2026-01-03

Enables pgvector extension for vector similarity search and adds
description_embedding column to plan_templates for semantic search.

Requirements:
- PostgreSQL 11+
- pgvector extension installed (CREATE EXTENSION vector)

Features:
- Vector similarity search for plan templates
- Cosine similarity indexing with IVFFlat
- 768-dimension vectors (matches text-embedding-005)
"""

from typing import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "v2w3x4y5z6a7"
down_revision: str | None = "u1v2w3x4y5z6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable pgvector and add vector columns for semantic search."""
    # Enable pgvector extension
    # This requires superuser or the extension to be pre-installed
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add description_embedding column to plan_templates table
    # Using 768 dimensions (text-embedding-005 default)
    # The table may not exist yet if this runs before plan_templates creation
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'plan_templates'
            ) THEN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'plan_templates'
                    AND column_name = 'description_embedding'
                ) THEN
                    ALTER TABLE plan_templates
                    ADD COLUMN description_embedding vector(768);
                END IF;
            END IF;
        END
        $$;
        """
    )

    # Add description_embedding column to execution_plans table
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'execution_plans'
            ) THEN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'execution_plans'
                    AND column_name = 'description_embedding'
                ) THEN
                    ALTER TABLE execution_plans
                    ADD COLUMN description_embedding vector(768);
                END IF;
            END IF;
        END
        $$;
        """
    )

    # Create IVFFlat index for cosine similarity on plan_templates
    # IVFFlat is faster for large datasets but requires training data
    # Using 100 lists for optimal performance up to 1M vectors
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'plan_templates'
                AND column_name = 'description_embedding'
            ) THEN
                CREATE INDEX IF NOT EXISTS ix_plan_templates_embedding
                ON plan_templates
                USING ivfflat (description_embedding vector_cosine_ops)
                WITH (lists = 100);
            END IF;
        END
        $$;
        """
    )

    # Create IVFFlat index for cosine similarity on execution_plans
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'execution_plans'
                AND column_name = 'description_embedding'
            ) THEN
                CREATE INDEX IF NOT EXISTS ix_execution_plans_embedding
                ON execution_plans
                USING ivfflat (description_embedding vector_cosine_ops)
                WITH (lists = 100);
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    """Remove vector columns and extension."""
    # Drop indices first
    op.execute("DROP INDEX IF EXISTS ix_plan_templates_embedding")
    op.execute("DROP INDEX IF EXISTS ix_execution_plans_embedding")

    # Remove columns
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'plan_templates'
                AND column_name = 'description_embedding'
            ) THEN
                ALTER TABLE plan_templates DROP COLUMN description_embedding;
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'execution_plans'
                AND column_name = 'description_embedding'
            ) THEN
                ALTER TABLE execution_plans DROP COLUMN description_embedding;
            END IF;
        END
        $$;
        """
    )

    # Note: We don't drop the vector extension as it may be used by other tables
    # op.execute("DROP EXTENSION IF EXISTS vector")
