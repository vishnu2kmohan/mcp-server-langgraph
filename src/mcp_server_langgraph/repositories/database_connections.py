"""Database Connection Repository.

Provides ABC and PostgreSQL implementation for database connection
CRUD operations with tenant-scoped access control and secrets cleanup.

Follows the pattern from repositories/connections.py.
"""

from __future__ import annotations

import uuid as uuid_mod
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_server_langgraph.execution.sql.credential_manager import SecretsProvider
from mcp_server_langgraph.models.database_connection import DatabaseConnection


# ============================================================================
# Data transfer types
# ============================================================================


@dataclass
class DatabaseConnectionCreateData:
    """Data for creating a database connection (sans credentials)."""

    name: str
    dialect: str
    host: str | None = None
    port: int | None = None
    database: str | None = None
    description: str | None = None
    project_id: str | None = None
    account_id: str | None = None
    warehouse_id: str | None = None
    ssl_mode: str = "require"
    secret_path: str = ""
    secret_key: str = ""


@dataclass
class DatabaseConnectionEntity:
    """Entity returned by the repository — maps all model columns."""

    id: UUID
    tenant_id: str
    owner_id: str
    name: str
    description: str | None
    dialect: str
    host: str | None
    port: int | None
    database: str | None
    project_id: str | None
    account_id: str | None
    warehouse_id: str | None
    secret_path: str
    secret_key: str
    ssl_mode: str
    status: str
    last_tested_at: datetime | None
    dialect_version: str | None
    created_at: datetime
    updated_at: datetime


@dataclass
class DatabaseConnectionUpdateData:
    """Data for partial update of a database connection."""

    name: str | None = None
    description: str | None = None
    host: str | None = None
    port: int | None = None
    database: str | None = None
    ssl_mode: str | None = None
    secret_path: str | None = None
    secret_key: str | None = None
    # Cloud-specific fields
    project_id: str | None = None  # BigQuery
    account_id: str | None = None  # Snowflake
    warehouse_id: str | None = None  # Snowflake, Databricks


# ============================================================================
# Abstract base class
# ============================================================================


class DatabaseConnectionRepository(ABC):
    """Abstract base class for database connection repository."""

    @abstractmethod
    async def create(
        self,
        data: DatabaseConnectionCreateData,
        owner_id: str,
        tenant_id: str,
    ) -> DatabaseConnectionEntity:
        """Create a new database connection."""

    @abstractmethod
    async def get(
        self,
        connection_id: UUID,
        tenant_id: str,
        owner_id: str,
    ) -> DatabaseConnectionEntity | None:
        """Get connection by ID with tenant/owner scoping."""

    @abstractmethod
    async def list(
        self,
        tenant_id: str,
        owner_id: str,
        dialect: str | None = None,
        status: str | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[DatabaseConnectionEntity], int]:
        """List connections with filtering and pagination.

        Returns:
            Tuple of (items, total_count).
        """

    @abstractmethod
    async def update(
        self,
        connection_id: UUID,
        tenant_id: str,
        owner_id: str,
        data: DatabaseConnectionUpdateData,
    ) -> DatabaseConnectionEntity | None:
        """Update connection fields. Returns None if not found."""

    @abstractmethod
    async def delete(
        self,
        connection_id: UUID,
        tenant_id: str,
        owner_id: str,
    ) -> bool:
        """Delete connection and associated secrets. Returns False if not found."""

    @abstractmethod
    async def update_test_result(
        self,
        connection_id: UUID,
        tenant_id: str,
        status: str,
        dialect_version: str | None = None,
    ) -> None:
        """Update connection test result (status, dialect_version, last_tested_at)."""


# ============================================================================
# PostgreSQL implementation
# ============================================================================


class PostgresDatabaseConnectionRepository(DatabaseConnectionRepository):
    """PostgreSQL implementation of DatabaseConnectionRepository."""

    def __init__(
        self,
        session: AsyncSession,
        secrets_provider: SecretsProvider,
    ) -> None:
        self._session = session
        self._secrets = secrets_provider

    def _model_to_entity(self, model: DatabaseConnection) -> DatabaseConnectionEntity:
        """Convert SQLAlchemy model to entity dataclass."""
        return DatabaseConnectionEntity(
            id=model.id,
            tenant_id=model.tenant_id,
            owner_id=model.owner_id,
            name=model.name,
            description=model.description,
            dialect=model.dialect,
            host=model.host,
            port=model.port,
            database=model.database,
            project_id=model.project_id,
            account_id=model.account_id,
            warehouse_id=model.warehouse_id,
            secret_path=model.secret_path,
            secret_key=model.secret_key,
            ssl_mode=model.ssl_mode,
            status=model.status,
            last_tested_at=model.last_tested_at,
            dialect_version=model.dialect_version,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def create(
        self,
        data: DatabaseConnectionCreateData,
        owner_id: str,
        tenant_id: str,
    ) -> DatabaseConnectionEntity:
        """Create a new database connection."""
        now = datetime.now(UTC)
        model = DatabaseConnection(
            id=uuid_mod.uuid4(),
            tenant_id=tenant_id,
            owner_id=owner_id,
            name=data.name,
            description=data.description,
            dialect=data.dialect,
            host=data.host,
            port=data.port,
            database=data.database,
            project_id=data.project_id,
            account_id=data.account_id,
            warehouse_id=data.warehouse_id,
            secret_path=data.secret_path,
            secret_key=data.secret_key,
            ssl_mode=data.ssl_mode,
            status="disconnected",
            created_at=now,
            updated_at=now,
        )

        self._session.add(model)
        await self._session.flush()

        return self._model_to_entity(model)

    async def get(
        self,
        connection_id: UUID,
        tenant_id: str,
        owner_id: str,
    ) -> DatabaseConnectionEntity | None:
        """Get connection by ID with tenant/owner scoping."""
        stmt = select(DatabaseConnection).where(
            and_(
                DatabaseConnection.id == connection_id,
                DatabaseConnection.tenant_id == tenant_id,
                DatabaseConnection.owner_id == owner_id,
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._model_to_entity(model)

    async def list(
        self,
        tenant_id: str,
        owner_id: str,
        dialect: str | None = None,
        status: str | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[DatabaseConnectionEntity], int]:
        """List connections with filtering and pagination."""
        # Build base filter
        filters = [
            DatabaseConnection.tenant_id == tenant_id,
            DatabaseConnection.owner_id == owner_id,
        ]

        if dialect:
            filters.append(DatabaseConnection.dialect == dialect)
        if status:
            filters.append(DatabaseConnection.status == status)
        if search:
            # Escape LIKE wildcards in user input to prevent unintended matching
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            filters.append(DatabaseConnection.name.ilike(f"%{escaped}%"))

        where_clause = and_(*filters)

        # Count query
        count_stmt = select(func.count()).select_from(DatabaseConnection).where(where_clause)
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()

        # Items query
        items_stmt = (
            select(DatabaseConnection)
            .where(where_clause)
            .order_by(DatabaseConnection.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items_result = await self._session.execute(items_stmt)
        models = items_result.scalars().all()

        return [self._model_to_entity(m) for m in models], total

    async def update(
        self,
        connection_id: UUID,
        tenant_id: str,
        owner_id: str,
        data: DatabaseConnectionUpdateData,
    ) -> DatabaseConnectionEntity | None:
        """Update connection fields."""
        stmt = select(DatabaseConnection).where(
            and_(
                DatabaseConnection.id == connection_id,
                DatabaseConnection.tenant_id == tenant_id,
                DatabaseConnection.owner_id == owner_id,
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        # Apply partial updates
        if data.name is not None:
            model.name = data.name
        if data.description is not None:
            model.description = data.description
        if data.host is not None:
            model.host = data.host
        if data.port is not None:
            model.port = data.port
        if data.database is not None:
            model.database = data.database
        if data.ssl_mode is not None:
            model.ssl_mode = data.ssl_mode
        if data.secret_path is not None:
            model.secret_path = data.secret_path
        if data.secret_key is not None:
            model.secret_key = data.secret_key
        # Cloud-specific fields
        if data.project_id is not None:
            model.project_id = data.project_id
        if data.account_id is not None:
            model.account_id = data.account_id
        if data.warehouse_id is not None:
            model.warehouse_id = data.warehouse_id

        model.updated_at = datetime.now(UTC)
        await self._session.flush()

        return self._model_to_entity(model)

    async def delete(
        self,
        connection_id: UUID,
        tenant_id: str,
        owner_id: str,
    ) -> bool:
        """Delete connection and associated secrets."""
        stmt = select(DatabaseConnection).where(
            and_(
                DatabaseConnection.id == connection_id,
                DatabaseConnection.tenant_id == tenant_id,
                DatabaseConnection.owner_id == owner_id,
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return False

        # Clean up secrets
        if model.secret_path and model.secret_key:
            secret_id = f"{model.secret_path}/{model.secret_key}"
            await self._secrets.delete_secret(secret_id)

        await self._session.delete(model)
        await self._session.flush()

        return True

    async def update_test_result(
        self,
        connection_id: UUID,
        tenant_id: str,
        status: str,
        dialect_version: str | None = None,
    ) -> None:
        """Update connection test result."""
        stmt = select(DatabaseConnection).where(
            and_(
                DatabaseConnection.id == connection_id,
                DatabaseConnection.tenant_id == tenant_id,
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return

        model.status = status
        model.dialect_version = dialect_version
        model.last_tested_at = datetime.now(UTC)
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
