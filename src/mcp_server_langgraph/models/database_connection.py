"""Database connection metadata model.

Stores connection metadata for database connections. Actual credentials
are stored in the Secrets Manager and referenced by secret_path/secret_key.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from enum import StrEnum

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from mcp_server_langgraph.models.base import Base


class DatabaseDialect(StrEnum):
    """Supported database dialects."""

    POSTGRES = "postgres"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    BIGQUERY = "bigquery"
    SNOWFLAKE = "snowflake"
    DUCKDB = "duckdb"
    REDSHIFT = "redshift"
    CLICKHOUSE = "clickhouse"
    TRINO = "trino"


class DatabaseConnection(Base):
    """Database connection metadata.

    Credentials are NEVER stored here - only a reference to the
    Secrets Manager path (secret_path + secret_key).
    """

    __tablename__ = "database_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Connection metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    dialect: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    database: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Cloud-specific
    project_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    warehouse_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Secrets Manager reference (NEVER store actual credentials)
    secret_path: Mapped[str] = mapped_column(String(512), nullable=False)
    secret_key: Mapped[str] = mapped_column(String(255), nullable=False)

    # SSL/TLS
    ssl_mode: Mapped[str] = mapped_column(String(32), default="require")

    # Status
    status: Mapped[str] = mapped_column(String(32), default="disconnected", index=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dialect_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_db_conn_tenant_name", "tenant_id", "name", unique=True),
        Index("ix_db_conn_owner", "owner_id"),
    )

    def __repr__(self) -> str:
        return f"<DatabaseConnection(id={self.id}, name={self.name!r}, dialect={self.dialect!r}, tenant={self.tenant_id!r})>"
