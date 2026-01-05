"""Add studio_configs table for STUDIO.md configuration storage.

Revision ID: x4y5z6a7b8c9
Revises: w3x4y5z6a7b8
Create Date: 2026-01-04

This migration adds the studio_configs table for storing parsed STUDIO.md
configurations at different scopes (enterprise, organization, project, etc.)
as part of ADR-0092 Hierarchical Capability Architecture.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision = "x4y5z6a7b8c9"
down_revision = "w3x4y5z6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create studio_configs table for hierarchical configuration storage."""
    op.create_table(
        "studio_configs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "scope",
            sa.String(50),
            nullable=False,
            comment="Capability scope level: enterprise, organization, project, team, user, session, task",
        ),
        sa.Column(
            "scope_id",
            sa.String(255),
            nullable=True,
            comment="Identifier for the scope (org_id, project_id, user_id, etc.)",
        ),
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Configuration name from STUDIO.md",
        ),
        sa.Column(
            "version",
            sa.String(50),
            nullable=True,
            comment="Configuration version",
        ),
        sa.Column(
            "config",
            postgresql.JSONB(),
            nullable=False,
            comment="Parsed STUDIO.md configuration as JSON",
        ),
        sa.Column(
            "config_hash",
            sa.String(64),
            nullable=False,
            comment="SHA-256 hash of the config for change detection",
        ),
        sa.Column(
            "file_path",
            sa.Text(),
            nullable=True,
            comment="Original file path of the STUDIO.md (for file-backed configs)",
        ),
        sa.Column(
            "enabled_tools",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment="List of enabled tool names",
        ),
        sa.Column(
            "disabled_tools",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment="List of disabled tool names",
        ),
        sa.Column(
            "enabled_skills",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment="List of enabled skill names",
        ),
        sa.Column(
            "disabled_skills",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment="List of disabled skill names",
        ),
        sa.Column(
            "rules",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment="List of rules defined in STUDIO.md",
        ),
        sa.Column(
            "memory_config",
            postgresql.JSONB(),
            nullable=True,
            comment="Memory configuration (tier settings, retention, etc.)",
        ),
        sa.Column(
            "cost_config",
            postgresql.JSONB(),
            nullable=True,
            comment="Cost control configuration (budgets, limits, etc.)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.String(255),
            nullable=True,
            comment="User who created this config",
        ),
        sa.Column(
            "updated_by",
            sa.String(255),
            nullable=True,
            comment="User who last updated this config",
        ),
    )

    # Create unique constraint for scope + scope_id combination
    op.create_unique_constraint(
        "uq_studio_configs_scope",
        "studio_configs",
        ["scope", "scope_id"],
    )

    # Create index for efficient scope lookups
    op.create_index(
        "ix_studio_configs_scope_lookup",
        "studio_configs",
        ["scope", "scope_id"],
    )

    # Create index for hash-based change detection
    op.create_index(
        "ix_studio_configs_hash",
        "studio_configs",
        ["config_hash"],
    )

    # Create GIN indexes for JSONB search on tools and skills
    op.execute("CREATE INDEX ix_studio_configs_enabled_tools_gin ON studio_configs USING GIN (enabled_tools)")
    op.execute("CREATE INDEX ix_studio_configs_enabled_skills_gin ON studio_configs USING GIN (enabled_skills)")


def downgrade() -> None:
    """Drop studio_configs table."""
    # Drop GIN indexes
    op.execute("DROP INDEX IF EXISTS ix_studio_configs_enabled_skills_gin")
    op.execute("DROP INDEX IF EXISTS ix_studio_configs_enabled_tools_gin")

    # Drop regular indexes
    op.drop_index("ix_studio_configs_hash", table_name="studio_configs")
    op.drop_index("ix_studio_configs_scope_lookup", table_name="studio_configs")

    # Drop unique constraint
    op.drop_constraint("uq_studio_configs_scope", "studio_configs", type_="unique")

    # Drop table
    op.drop_table("studio_configs")
