"""Add allocation_tags column

Add allocation_tags JSONB column to token_usage_records table
for custom cost allocation tagging (e.g., environment, campaign, feature).

Revision ID: q7r8s9t0u1v2
Revises: p6q7r8s9t0u1
Create Date: 2025-12-28

Reference: Plan - Phase 2: Cost Allocation Tags for flexible cost attribution
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "q7r8s9t0u1v2"
down_revision: str | None = "p6q7r8s9t0u1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add allocation_tags column for custom cost attribution.

    The allocation_tags column stores key-value pairs for flexible
    cost categorization beyond the organizational hierarchy.

    Example tags:
    - environment: production, staging, development
    - campaign: launch-2025, holiday-promo
    - feature: chat, summarization, code-generation
    - cost_center: engineering, marketing, support
    """
    # Add allocation_tags column as JSONB (PostgreSQL native JSON)
    op.add_column(
        "token_usage_records",
        sa.Column(
            "allocation_tags",
            JSONB,
            nullable=True,
            comment="Custom key-value tags for cost allocation",
        ),
    )

    # Create GIN index for efficient JSONB key/value queries
    # This enables fast queries like: WHERE allocation_tags->>'environment' = 'production'
    op.create_index(
        "ix_token_usage_records_allocation_tags",
        "token_usage_records",
        ["allocation_tags"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Remove allocation_tags column and index."""
    op.drop_index(
        "ix_token_usage_records_allocation_tags",
        table_name="token_usage_records",
    )
    op.drop_column("token_usage_records", "allocation_tags")
