"""Add organizational cost columns

Add organization_id, project_id, team_id columns to token_usage_records table
with composite indices for organizational cost queries.

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2025-12-28

Reference: Plan - Phase 3: Database Migration for Organizational Cost Attribution
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "o5p6q7r8s9t0"
down_revision: str | None = "n4o5p6q7r8s9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add organizational hierarchy columns and indices.

    Columns:
    - organization_id: Multi-tenant org cost attribution
    - project_id: Project-level cost breakdown
    - team_id: Team/group cost attribution

    Indices (optimized for common query patterns):
    - ix_org_timestamp: Org admin viewing recent costs
    - ix_project_timestamp: Project-level cost drill-down
    - ix_team_user_timestamp: Team manager viewing member costs
    - ix_org_project_team: Multi-dimensional cost analysis
    """
    # Add organizational hierarchy columns
    op.add_column(
        "token_usage_records",
        sa.Column("organization_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "token_usage_records",
        sa.Column("project_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "token_usage_records",
        sa.Column("team_id", sa.String(255), nullable=True),
    )

    # Single-column indices for basic filtering
    op.create_index(
        "ix_token_usage_records_organization_id",
        "token_usage_records",
        ["organization_id"],
    )
    op.create_index(
        "ix_token_usage_records_project_id",
        "token_usage_records",
        ["project_id"],
    )
    op.create_index(
        "ix_token_usage_records_team_id",
        "token_usage_records",
        ["team_id"],
    )

    # Composite indices for common query patterns
    # Pattern: Org admin viewing recent costs (ORDER BY timestamp DESC)
    op.create_index(
        "ix_org_timestamp",
        "token_usage_records",
        ["organization_id", "timestamp"],
    )

    # Pattern: Project-level cost drill-down
    op.create_index(
        "ix_project_timestamp",
        "token_usage_records",
        ["project_id", "timestamp"],
    )

    # Pattern: Team manager viewing member costs
    op.create_index(
        "ix_team_user_timestamp",
        "token_usage_records",
        ["team_id", "user_id", "timestamp"],
    )

    # Pattern: Multi-dimensional cost analysis
    op.create_index(
        "ix_org_project_team",
        "token_usage_records",
        ["organization_id", "project_id", "team_id"],
    )


def downgrade() -> None:
    """Remove organizational hierarchy columns and indices."""
    # Drop composite indices first
    op.drop_index("ix_org_project_team", table_name="token_usage_records")
    op.drop_index("ix_team_user_timestamp", table_name="token_usage_records")
    op.drop_index("ix_project_timestamp", table_name="token_usage_records")
    op.drop_index("ix_org_timestamp", table_name="token_usage_records")

    # Drop single-column indices
    op.drop_index("ix_token_usage_records_team_id", table_name="token_usage_records")
    op.drop_index("ix_token_usage_records_project_id", table_name="token_usage_records")
    op.drop_index("ix_token_usage_records_organization_id", table_name="token_usage_records")

    # Drop columns
    op.drop_column("token_usage_records", "team_id")
    op.drop_column("token_usage_records", "project_id")
    op.drop_column("token_usage_records", "organization_id")
