"""Add budget_records table

Create the budget_records table for storing budget configurations
per entity (organization, project, team, user). Enables cost control
and alerting with configurable thresholds.

Revision ID: r8s9t0u1v2w3
Revises: q7r8s9t0u1v2
Create Date: 2025-12-28

Reference: Plan - Phase 5: Budget Storage for persistent budget configurations
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "r8s9t0u1v2w3"
down_revision: str | None = "q7r8s9t0u1v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create budget_records table for budget management.

    Entity Types:
        - organization: Company-wide budget limits
        - project: Per-project budget limits
        - team: Team-level budget limits
        - user: Individual user budget limits

    The entity_type + entity_id combination is unique (one budget per entity).
    """
    op.create_table(
        "budget_records",
        # Primary key
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        # Entity identification (unique constraint on type + id)
        sa.Column(
            "entity_type",
            sa.String(50),
            nullable=False,
            comment="Entity type: organization, project, team, user",
        ),
        sa.Column(
            "entity_id",
            sa.String(255),
            nullable=False,
            comment="Entity identifier (e.g., 'organization:acme', 'user:alice')",
        ),
        # Budget configuration
        sa.Column(
            "monthly_limit_usd",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Monthly budget limit in USD",
        ),
        sa.Column(
            "warning_threshold",
            sa.Numeric(precision=3, scale=2),
            nullable=False,
            server_default="0.80",
            comment="Warning threshold as percentage (0.80 = 80%)",
        ),
        sa.Column(
            "critical_threshold",
            sa.Numeric(precision=3, scale=2),
            nullable=False,
            server_default="1.00",
            comment="Critical threshold as percentage (1.0 = 100%)",
        ),
        # Metadata
        sa.Column(
            "name",
            sa.String(255),
            nullable=True,
            comment="Human-readable budget name",
        ),
        sa.Column(
            "description",
            sa.String(1000),
            nullable=True,
            comment="Budget description",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Whether budget monitoring is enabled",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="When the budget was created (UTC)",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="When the budget was last updated (UTC)",
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
    )

    # Create unique index for entity_type + entity_id (one budget per entity)
    op.create_index(
        "ix_budget_entity_type_id",
        "budget_records",
        ["entity_type", "entity_id"],
        unique=True,
    )

    # Create index for filtering by entity type
    op.create_index(
        "ix_budget_entity_type",
        "budget_records",
        ["entity_type"],
    )

    # Create index for filtering enabled budgets
    op.create_index(
        "ix_budget_enabled",
        "budget_records",
        ["enabled"],
    )

    # Create trigger function to update updated_at on row update
    op.execute("""
        CREATE OR REPLACE FUNCTION update_budget_records_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Create trigger to call the function
    op.execute("""
        CREATE TRIGGER trigger_budget_records_updated_at
        BEFORE UPDATE ON budget_records
        FOR EACH ROW
        EXECUTE FUNCTION update_budget_records_updated_at();
    """)


def downgrade() -> None:
    """Remove budget_records table and related objects."""
    # Drop trigger first
    op.execute("DROP TRIGGER IF EXISTS trigger_budget_records_updated_at ON budget_records")

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS update_budget_records_updated_at()")

    # Drop indexes
    op.drop_index("ix_budget_enabled", table_name="budget_records")
    op.drop_index("ix_budget_entity_type", table_name="budget_records")
    op.drop_index("ix_budget_entity_type_id", table_name="budget_records")

    # Drop table
    op.drop_table("budget_records")
