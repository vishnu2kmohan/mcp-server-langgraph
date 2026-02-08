"""merge_langgraph_traces_and_db_connections

Revision ID: 65ec89011b7b
Revises: d1e2f3g4h5i6, d1f2g3h4i5j6
Create Date: 2026-02-08 08:50:17.593309

"""

from typing import Sequence


# revision identifiers, used by Alembic.
revision: str = "65ec89011b7b"
down_revision: str | Sequence[str] | None = ("d1e2f3g4h5i6", "d1f2g3h4i5j6")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
