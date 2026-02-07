"""Add database_connections table.

Revision ID: d1f2g3h4i5j6
Revises: c0d1e2f3g4h5
Create Date: 2026-02-06

Adds the database_connections table for storing database connection
metadata. Actual credentials are stored in the Secrets Manager and
referenced by secret_path/secret_key columns.

Supported dialects: postgres, mysql, sqlite, bigquery, snowflake,
duckdb, redshift, clickhouse, trino.
"""

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1f2g3h4i5j6"
down_revision: str | None = "c0d1e2f3g4h5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create database_connections table with indexes."""
    op.create_table(
        "database_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("owner_id", sa.String(64), nullable=False),
        # Connection metadata
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1024), nullable=True),
        sa.Column("dialect", sa.String(32), nullable=False),
        sa.Column("host", sa.String(255), nullable=True),
        sa.Column("port", sa.Integer, nullable=True),
        sa.Column("database", sa.String(255), nullable=True),
        # Cloud-specific
        sa.Column("project_id", sa.String(255), nullable=True),
        sa.Column("account_id", sa.String(255), nullable=True),
        sa.Column("warehouse_id", sa.String(255), nullable=True),
        # Secrets Manager reference
        sa.Column("secret_path", sa.String(512), nullable=False),
        sa.Column("secret_key", sa.String(255), nullable=False),
        # SSL/TLS
        sa.Column("ssl_mode", sa.String(32), nullable=False, server_default="require"),
        # Status
        sa.Column("status", sa.String(32), nullable=False, server_default="disconnected"),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dialect_version", sa.String(32), nullable=True),
        # Audit fields
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Indexes
    op.create_index(
        "ix_db_conn_tenant_id",
        "database_connections",
        ["tenant_id"],
    )
    op.create_index(
        "ix_db_conn_owner",
        "database_connections",
        ["owner_id"],
    )
    op.create_index(
        "ix_db_conn_tenant_name",
        "database_connections",
        ["tenant_id", "name"],
        unique=True,
    )
    # Filter indexes for list query performance
    op.create_index(
        "ix_db_conn_dialect",
        "database_connections",
        ["dialect"],
    )
    op.create_index(
        "ix_db_conn_status",
        "database_connections",
        ["status"],
    )


def downgrade() -> None:
    """Drop database_connections table and indexes."""
    op.drop_index("ix_db_conn_status", table_name="database_connections")
    op.drop_index("ix_db_conn_dialect", table_name="database_connections")
    op.drop_index("ix_db_conn_tenant_name", table_name="database_connections")
    op.drop_index("ix_db_conn_owner", table_name="database_connections")
    op.drop_index("ix_db_conn_tenant_id", table_name="database_connections")
    op.drop_table("database_connections")
