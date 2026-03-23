"""Fix execution_plan and plan_template schema drift

Revision ID: j1k2l3m4n5o6
Revises: i0j1k2l3m4n5
Create Date: 2026-03-21

Resolves multiple ORM-vs-migration mismatches:
1. execution_plans: missing description_embedding vector(768) column
2. plan_templates: description_embedding is float[] instead of vector(768)
3. Both tables: ENUM columns where ORM expects VARCHAR(20)

Uses add-column/copy/drop/rename pattern for ENUM->VARCHAR conversion
because ALTER COLUMN TYPE fails with asyncpg when indexes reference the column.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "j1k2l3m4n5o6"
down_revision: str | None = "i0j1k2l3m4n5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (table, column, default_value_or_None, nullable)
_ENUM_CONVERSIONS = [
    ("execution_plans", "status", "awaiting_approval", False),
    ("execution_plans", "complexity", None, False),
    ("execution_plans", "risk_level", None, False),
    ("execution_plans", "task_type", None, False),
    ("execution_plans", "suggested_orchestrator", "standard", False),
    ("execution_plans", "thinking_budget", "none", False),
    ("plan_templates", "orchestrator", "standard", False),
    ("plan_templates", "thinking_budget", "none", False),
]


def upgrade() -> None:
    """Fix schema drift in execution_plans and plan_templates."""
    conn = op.get_bind()

    # 1. Add missing description_embedding to execution_plans
    has_col = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'execution_plans' "
            "AND column_name = 'description_embedding'"
        )
    ).fetchone()
    if not has_col:
        op.execute(sa.text("ALTER TABLE execution_plans ADD COLUMN description_embedding vector(768)"))

    # 2. Convert plan_templates.description_embedding from float[] to vector(768)
    col_info = conn.execute(
        sa.text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'plan_templates' "
            "AND column_name = 'description_embedding'"
        )
    ).fetchone()
    if col_info and col_info[0] == "ARRAY":
        op.execute(sa.text("ALTER TABLE plan_templates DROP COLUMN description_embedding"))
        op.execute(sa.text("ALTER TABLE plan_templates ADD COLUMN description_embedding vector(768)"))

    # 3. Convert ENUM columns to VARCHAR(20) in both tables
    #    Pattern: add temp column -> copy data -> drop old -> rename temp
    #    This avoids ALTER COLUMN TYPE which conflicts with asyncpg index handling
    for table, column, default_val, not_null in _ENUM_CONVERSIONS:
        col_type = conn.execute(
            sa.text("SELECT data_type FROM information_schema.columns WHERE table_name = :table AND column_name = :column"),
            {"table": table, "column": column},
        ).fetchone()
        if col_type and col_type[0] == "USER-DEFINED":
            _convert_enum_column(table, column, default_val, not_null)


def _convert_enum_column(table: str, column: str, default_val: str | None, not_null: bool) -> None:
    """Convert a single ENUM column to VARCHAR(20) using add/copy/drop/rename."""
    tmp = f"_tmp_{column}"

    # Add temporary VARCHAR column
    op.execute(sa.text(f"ALTER TABLE {table} ADD COLUMN {tmp} VARCHAR(20)"))

    # Copy data (cast enum -> text -> varchar)
    op.execute(sa.text(f"UPDATE {table} SET {tmp} = {column}::text"))

    # Apply NOT NULL if needed
    if not_null:
        op.execute(sa.text(f"ALTER TABLE {table} ALTER COLUMN {tmp} SET NOT NULL"))

    # Set default if needed
    if default_val is not None:
        # SAFETY: default_val comes from hardcoded _ENUM_CONVERSIONS — must be a simple SQL literal
        # Use raise (not assert) because assert is stripped by python -O
        if not default_val.replace("_", "").isalnum():
            raise ValueError(f"Unsafe default value: {default_val!r}")
        op.execute(sa.text(f"ALTER TABLE {table} ALTER COLUMN {tmp} SET DEFAULT '{default_val}'"))

    # Drop the old ENUM column (this also drops any indexes on it)
    op.execute(sa.text(f"ALTER TABLE {table} DROP COLUMN {column}"))

    # Rename temp to original name
    op.execute(sa.text(f"ALTER TABLE {table} RENAME COLUMN {tmp} TO {column}"))


def downgrade() -> None:
    """Revert schema changes (best-effort for dev environments).

    NOTE: ENUM column conversions (step 3) are NOT reversed because recreating
    PostgreSQL ENUM types requires the exact type definitions from the original
    migration. VARCHAR(20) is a superset of ENUM values, so this is safe.
    """
    conn = op.get_bind()

    # Remove description_embedding from execution_plans
    has_col = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'execution_plans' "
            "AND column_name = 'description_embedding'"
        )
    ).fetchone()
    if has_col:
        op.execute(sa.text("ALTER TABLE execution_plans DROP COLUMN description_embedding"))

    # Revert plan_templates.description_embedding to float[]
    has_col = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'plan_templates' "
            "AND column_name = 'description_embedding'"
        )
    ).fetchone()
    if has_col:
        op.execute(sa.text("ALTER TABLE plan_templates DROP COLUMN description_embedding"))
        op.execute(sa.text("ALTER TABLE plan_templates ADD COLUMN description_embedding FLOAT[]"))
