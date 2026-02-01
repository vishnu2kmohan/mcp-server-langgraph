"""merge_execution_plan_branches

Revision ID: fea0842074ad
Revises: b8c9d0e1f2a3, e1f2g3h4i5j6
Create Date: 2026-01-31 18:47:47.518164

"""

from typing import Sequence


# revision identifiers, used by Alembic.
revision: str = "fea0842074ad"
down_revision: str | Sequence[str] | None = ("b8c9d0e1f2a3", "e1f2g3h4i5j6")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
