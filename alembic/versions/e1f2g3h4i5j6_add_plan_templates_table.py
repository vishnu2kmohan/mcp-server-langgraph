"""Add plan_templates table with pgvector support.

Revision ID: e1f2g3h4i5j6
Revises: d0e1f2g3h4i5
Create Date: 2026-01-28

This migration creates the plan_templates table for storing reusable
execution plan templates with optional semantic search via pgvector.

Features:
- Reusable plan configurations
- Usage metrics (use_count, success_rate)
- Tags for organization and filtering
- Optional vector embeddings for semantic search
- Full-text search on name and description

Related Models:
- PlanTemplate (core/models/plan_template.py)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = "e1f2g3h4i5j6"
down_revision = "d0e1f2g3h4i5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create plan_templates table with pgvector support."""

    # Enable pgvector extension (requires superuser or azure_pg_admin on Azure)
    # This is idempotent - won't fail if already enabled
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Reuse orchestrator and thinking_budget enums from execution_plans
    # (already created in previous migration)

    # Create plan_templates table
    op.create_table(
        "plan_templates",
        # Primary key
        sa.Column("template_id", sa.String(36), primary_key=True),
        # Template metadata
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        # Configuration (reuse enums from execution_plans)
        sa.Column(
            "orchestrator",
            postgresql.ENUM(
                "standard",
                "swarm",
                "studio",
                "ux",
                "alert",
                name="execution_plan_orchestrator",
                create_type=False,  # Already exists
            ),
            nullable=False,
            server_default="standard",
        ),
        sa.Column(
            "thinking_budget",
            postgresql.ENUM(
                "none",
                "light",
                "medium",
                "deep",
                name="execution_plan_thinking_budget",
                create_type=False,  # Already exists
            ),
            nullable=False,
            server_default="none",
        ),
        sa.Column("critique_rounds", sa.Integer, nullable=False, server_default="0"),
        sa.Column("auto_approve", sa.Boolean, nullable=False, server_default="false"),
        # Ownership
        sa.Column("created_by", sa.String(255), nullable=False, index=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # Vector embedding for semantic search (1536 dimensions for text-embedding-3-small)
        # Use HALFVEC for storage efficiency (half precision floats)
        sa.Column(
            "description_embedding",
            postgresql.ARRAY(sa.Float),  # Store as float array, cast to vector for search
            nullable=True,
        ),
        # Usage metrics
        sa.Column("use_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("success_rate", sa.Float, nullable=False, server_default="0.0"),
        # Tags for organization
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String),
            nullable=False,
            server_default="{}",
        ),
    )

    # Create index on name for quick lookups
    op.create_index(
        "ix_plan_templates_name",
        "plan_templates",
        ["name"],
    )

    # Create GIN index on tags for array containment queries
    op.create_index(
        "ix_plan_templates_tags",
        "plan_templates",
        ["tags"],
        postgresql_using="gin",
    )

    # Create index on orchestrator for filtered queries
    op.create_index(
        "ix_plan_templates_orchestrator",
        "plan_templates",
        ["orchestrator"],
    )

    # Create index for popularity sorting (use_count DESC)
    op.create_index(
        "ix_plan_templates_use_count",
        "plan_templates",
        [sa.text("use_count DESC")],
    )

    # Create full-text search index on name and description
    op.execute(
        """
        CREATE INDEX ix_plan_templates_fts ON plan_templates
        USING gin(to_tsvector('english', name || ' ' || description))
        """
    )

    # Create vector index for semantic search (when embeddings are populated)
    # Using HNSW for fast approximate nearest neighbor search
    # Note: This requires the embedding column to have vector type
    # We'll create a generated column or view for vector operations
    op.execute(
        """
        -- Create a function to safely cast float array to vector
        CREATE OR REPLACE FUNCTION array_to_vector(arr float[])
        RETURNS vector
        LANGUAGE sql
        IMMUTABLE
        AS $$
            SELECT arr::vector
        $$
        """
    )


def downgrade() -> None:
    """Drop plan_templates table."""
    # Drop the helper function
    op.execute("DROP FUNCTION IF EXISTS array_to_vector(float[])")

    # Drop the table
    op.drop_table("plan_templates")

    # Note: We don't drop the vector extension as other tables might use it
    # Note: We don't drop the shared enums as execution_plans still uses them
