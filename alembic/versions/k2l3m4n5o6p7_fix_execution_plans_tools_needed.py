"""Convert execution_plans.tools_needed from varchar[] to JSONB

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-03-21

The ORM model (v35.0) defines tools_needed as JSONB, but the original
migration d0e1f2g3h4i5 created it as ARRAY(String). Migration
c0d1e2f3g4h5 was supposed to handle the conversion but did not
update the column type. This causes INSERT failures because SQLAlchemy
generates $12::JSONB for a varchar[] column.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "k2l3m4n5o6p7"
down_revision: str | None = "j1k2l3m4n5o6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Convert tools_needed from varchar[] to JSONB."""
    conn = op.get_bind()

    col_info = conn.execute(
        sa.text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'execution_plans' "
            "AND column_name = 'tools_needed'"
        )
    ).fetchone()

    if col_info and col_info[0] == "ARRAY":
        # Add temp JSONB column
        op.execute(sa.text("ALTER TABLE execution_plans ADD COLUMN _tmp_tools_needed JSONB"))

        # Convert existing array data to JSONB
        op.execute(
            sa.text(
                "UPDATE execution_plans SET _tmp_tools_needed = "
                "CASE WHEN tools_needed IS NULL THEN NULL "
                "ELSE to_jsonb(tools_needed) END"
            )
        )

        # Drop old column and rename
        op.execute(sa.text("ALTER TABLE execution_plans DROP COLUMN tools_needed"))
        op.execute(sa.text("ALTER TABLE execution_plans RENAME COLUMN _tmp_tools_needed TO tools_needed"))


def downgrade() -> None:
    """Revert tools_needed to varchar[] (best-effort)."""
    conn = op.get_bind()

    col_info = conn.execute(
        sa.text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'execution_plans' "
            "AND column_name = 'tools_needed'"
        )
    ).fetchone()

    if col_info and col_info[0] == "jsonb":
        op.execute(sa.text("ALTER TABLE execution_plans ADD COLUMN _tmp_tools_needed VARCHAR[]"))
        op.execute(
            sa.text(
                "UPDATE execution_plans SET _tmp_tools_needed = "
                "CASE WHEN tools_needed IS NULL THEN NULL "
                "ELSE ARRAY(SELECT jsonb_array_elements_text(tools_needed)) END"
            )
        )
        op.execute(sa.text("ALTER TABLE execution_plans DROP COLUMN tools_needed"))
        op.execute(sa.text("ALTER TABLE execution_plans RENAME COLUMN _tmp_tools_needed TO tools_needed"))
