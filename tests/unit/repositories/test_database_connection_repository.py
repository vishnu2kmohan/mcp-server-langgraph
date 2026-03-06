"""Tests for DatabaseConnectionRepository (Phase 6a).

Tests the repository ABC contract via the PostgresImpl with mocked
AsyncSession and SecretsProvider.
"""

from __future__ import annotations

import gc
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from mcp_server_langgraph.repositories.database_connections import (
    DatabaseConnectionCreateData,
    DatabaseConnectionEntity,
    DatabaseConnectionRepository,
    DatabaseConnectionUpdateData,
    PostgresDatabaseConnectionRepository,
)

pytestmark = pytest.mark.unit


def _make_mock_model(
    *,
    id: uuid.UUID | None = None,
    tenant_id: str = "tenant-1",
    owner_id: str = "user-1",
    name: str = "test-conn",
    dialect: str = "postgres",
    host: str | None = "db.example.com",
    port: int | None = 5432,
    database: str | None = "mydb",
    description: str | None = None,
    project_id: str | None = None,
    account_id: str | None = None,
    warehouse_id: str | None = None,
    secret_path: str = "/database/tenant-1/postgres",
    secret_key: str = "test_conn",
    ssl_mode: str = "require",
    status: str = "disconnected",
    last_tested_at: datetime | None = None,
    dialect_version: str | None = None,
) -> MagicMock:
    """Build a mock that mimics a DatabaseConnection SQLAlchemy model."""
    model = MagicMock()
    model.id = id or uuid.uuid4()
    model.tenant_id = tenant_id
    model.owner_id = owner_id
    model.name = name
    model.dialect = dialect
    model.host = host
    model.port = port
    model.database = database
    model.description = description
    model.project_id = project_id
    model.account_id = account_id
    model.warehouse_id = warehouse_id
    model.secret_path = secret_path
    model.secret_key = secret_key
    model.ssl_mode = ssl_mode
    model.status = status
    model.last_tested_at = last_tested_at
    model.dialect_version = dialect_version
    now = datetime.now(UTC)
    model.created_at = now
    model.updated_at = now
    return model


def _make_session() -> AsyncMock:
    """Create a mock AsyncSession."""
    session = AsyncMock()  # noqa: async-mock-config - mock SQLAlchemy session with dynamic attributes
    session.add = MagicMock()
    session.flush = AsyncMock()  # noqa: async-mock-config
    session.delete = AsyncMock()  # noqa: async-mock-config
    session.execute = AsyncMock()  # noqa: async-mock-config
    return session


def _make_secrets() -> AsyncMock:
    """Create a mock SecretsProvider."""
    secrets = AsyncMock()  # noqa: async-mock-config - mock secrets provider with dynamic attributes
    secrets.get_secret = AsyncMock(return_value=None)  # noqa: async-mock-config
    secrets.set_secret = AsyncMock()  # noqa: async-mock-config
    secrets.delete_secret = AsyncMock()  # noqa: async-mock-config
    return secrets


def _make_create_data(**overrides) -> DatabaseConnectionCreateData:
    """Build a DatabaseConnectionCreateData with sensible defaults."""
    defaults = {
        "name": "test-conn",
        "dialect": "postgres",
        "host": "db.example.com",
        "port": 5432,
        "database": "mydb",
        "description": None,
        "project_id": None,
        "account_id": None,
        "warehouse_id": None,
        "ssl_mode": "require",
        "secret_path": "/database/tenant-1/postgres",
        "secret_key": "test_conn",
    }
    defaults.update(overrides)
    return DatabaseConnectionCreateData(**defaults)


class TestPostgresDatabaseConnectionRepository:
    """Test PostgresDatabaseConnectionRepository CRUD operations."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.unit
    async def test_create_returns_entity(self) -> None:
        """create() should add model to session and return entity."""
        session = _make_session()
        secrets = _make_secrets()
        repo = PostgresDatabaseConnectionRepository(session, secrets)

        data = _make_create_data()

        with patch("mcp_server_langgraph.repositories.database_connections.DatabaseConnection") as MockModel:
            mock_instance = _make_mock_model()
            MockModel.return_value = mock_instance

            entity = await repo.create(data, owner_id="user-1", tenant_id="tenant-1")

        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        assert isinstance(entity, DatabaseConnectionEntity)
        assert entity.name == "test-conn"
        assert entity.dialect == "postgres"
        assert entity.tenant_id == "tenant-1"
        assert entity.owner_id == "user-1"

    @pytest.mark.unit
    async def test_create_integrity_error_propagates(self) -> None:
        """create() should propagate IntegrityError for duplicate names."""
        session = _make_session()
        session.flush.side_effect = IntegrityError("duplicate", {}, None)
        secrets = _make_secrets()
        repo = PostgresDatabaseConnectionRepository(session, secrets)
        data = _make_create_data()

        with patch("mcp_server_langgraph.repositories.database_connections.DatabaseConnection"):
            with pytest.raises(IntegrityError):
                await repo.create(data, owner_id="user-1", tenant_id="tenant-1")

    @pytest.mark.unit
    async def test_get_returns_entity(self) -> None:
        """get() should return entity when found."""
        session = _make_session()
        secrets = _make_secrets()
        repo = PostgresDatabaseConnectionRepository(session, secrets)

        conn_id = uuid.uuid4()
        mock_model = _make_mock_model(id=conn_id)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_model
        session.execute.return_value = result_mock

        entity = await repo.get(conn_id, tenant_id="tenant-1", owner_id="user-1")

        assert entity is not None
        assert entity.id == conn_id
        assert entity.name == "test-conn"

    @pytest.mark.unit
    async def test_get_returns_none_when_not_found(self) -> None:
        """get() should return None when connection doesn't exist."""
        session = _make_session()
        secrets = _make_secrets()
        repo = PostgresDatabaseConnectionRepository(session, secrets)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock

        entity = await repo.get(uuid.uuid4(), tenant_id="tenant-1", owner_id="user-1")
        assert entity is None

    @pytest.mark.unit
    async def test_get_cross_owner_returns_none(self) -> None:
        """get() with wrong owner_id should return None (access denied)."""
        session = _make_session()
        secrets = _make_secrets()
        repo = PostgresDatabaseConnectionRepository(session, secrets)

        # The query includes owner_id filter, so wrong owner -> no match
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock

        entity = await repo.get(uuid.uuid4(), tenant_id="tenant-1", owner_id="other-user")
        assert entity is None

    @pytest.mark.unit
    async def test_list_returns_items_and_total(self) -> None:
        """list() should return items and total count."""
        session = _make_session()
        secrets = _make_secrets()
        repo = PostgresDatabaseConnectionRepository(session, secrets)

        models = [_make_mock_model(name=f"conn-{i}") for i in range(3)]

        # First call returns items, second returns count
        count_result = MagicMock()
        count_result.scalar_one.return_value = 3

        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = models

        session.execute.side_effect = [count_result, items_result]

        items, total = await repo.list(tenant_id="tenant-1", owner_id="user-1", limit=20, offset=0)

        assert total == 3
        assert len(items) == 3
        assert all(isinstance(i, DatabaseConnectionEntity) for i in items)

    @pytest.mark.unit
    async def test_list_with_dialect_filter(self) -> None:
        """list() with dialect filter should filter results."""
        session = _make_session()
        secrets = _make_secrets()
        repo = PostgresDatabaseConnectionRepository(session, secrets)

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [_make_mock_model(dialect="mysql")]
        session.execute.side_effect = [count_result, items_result]

        items, total = await repo.list(
            tenant_id="tenant-1",
            owner_id="user-1",
            dialect="mysql",
            limit=20,
            offset=0,
        )

        assert total == 1
        assert items[0].dialect == "mysql"

    @pytest.mark.unit
    async def test_list_with_search_filter(self) -> None:
        """list() with search parameter should filter by name."""
        session = _make_session()
        secrets = _make_secrets()
        repo = PostgresDatabaseConnectionRepository(session, secrets)

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [_make_mock_model(name="prod-db")]
        session.execute.side_effect = [count_result, items_result]

        items, total = await repo.list(
            tenant_id="tenant-1",
            owner_id="user-1",
            search="prod",
            limit=20,
            offset=0,
        )

        assert total == 1

    @pytest.mark.unit
    async def test_list_empty(self) -> None:
        """list() should return empty list when no connections exist."""
        session = _make_session()
        secrets = _make_secrets()
        repo = PostgresDatabaseConnectionRepository(session, secrets)

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = []
        session.execute.side_effect = [count_result, items_result]

        items, total = await repo.list(tenant_id="tenant-1", owner_id="user-1", limit=20, offset=0)

        assert total == 0
        assert items == []

    @pytest.mark.unit
    async def test_update_returns_updated_entity(self) -> None:
        """update() should update fields and return entity."""
        session = _make_session()
        secrets = _make_secrets()
        repo = PostgresDatabaseConnectionRepository(session, secrets)

        conn_id = uuid.uuid4()
        mock_model = _make_mock_model(id=conn_id, name="old-name")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_model
        session.execute.return_value = result_mock

        update_data = DatabaseConnectionUpdateData(name="new-name")
        entity = await repo.update(conn_id, tenant_id="tenant-1", owner_id="user-1", data=update_data)

        assert entity is not None
        session.flush.assert_awaited_once()

    @pytest.mark.unit
    async def test_update_returns_none_when_not_found(self) -> None:
        """update() should return None when connection doesn't exist."""
        session = _make_session()
        secrets = _make_secrets()
        repo = PostgresDatabaseConnectionRepository(session, secrets)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock

        update_data = DatabaseConnectionUpdateData(name="new-name")
        entity = await repo.update(uuid.uuid4(), tenant_id="tenant-1", owner_id="user-1", data=update_data)

        assert entity is None

    @pytest.mark.unit
    async def test_delete_returns_true(self) -> None:
        """delete() should delete model and return True."""
        session = _make_session()
        secrets = _make_secrets()
        repo = PostgresDatabaseConnectionRepository(session, secrets)

        conn_id = uuid.uuid4()
        mock_model = _make_mock_model(id=conn_id)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_model
        session.execute.return_value = result_mock

        result = await repo.delete(conn_id, tenant_id="tenant-1", owner_id="user-1")

        assert result is True
        session.delete.assert_awaited_once_with(mock_model)
        session.flush.assert_awaited_once()

    @pytest.mark.unit
    async def test_delete_returns_false_when_not_found(self) -> None:
        """delete() should return False when connection doesn't exist."""
        session = _make_session()
        secrets = _make_secrets()
        repo = PostgresDatabaseConnectionRepository(session, secrets)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock

        result = await repo.delete(uuid.uuid4(), tenant_id="tenant-1", owner_id="user-1")

        assert result is False

    @pytest.mark.unit
    async def test_delete_cleans_up_secrets(self) -> None:
        """delete() should delete the associated secret."""
        session = _make_session()
        secrets = _make_secrets()
        repo = PostgresDatabaseConnectionRepository(session, secrets)

        conn_id = uuid.uuid4()
        mock_model = _make_mock_model(
            id=conn_id,
            secret_path="/database/tenant-1/postgres",
            secret_key="test_conn",
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_model
        session.execute.return_value = result_mock

        await repo.delete(conn_id, tenant_id="tenant-1", owner_id="user-1")

        secrets.delete_secret.assert_awaited_once_with("/database/tenant-1/postgres/test_conn")

    @pytest.mark.unit
    async def test_update_test_result(self) -> None:
        """update_test_result() should set status, dialect_version, last_tested_at."""
        session = _make_session()
        secrets = _make_secrets()
        repo = PostgresDatabaseConnectionRepository(session, secrets)

        conn_id = uuid.uuid4()
        mock_model = _make_mock_model(id=conn_id)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_model
        session.execute.return_value = result_mock

        await repo.update_test_result(
            conn_id,
            tenant_id="tenant-1",
            status="connected",
            dialect_version="15.2",
        )

        assert mock_model.status == "connected"
        assert mock_model.dialect_version == "15.2"
        assert mock_model.last_tested_at is not None
        session.flush.assert_awaited_once()


class TestDatabaseConnectionRepositoryABC:
    """Test that the ABC defines the expected interface."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.unit
    def test_abc_cannot_be_instantiated(self) -> None:
        """DatabaseConnectionRepository ABC should not be instantiable."""
        with pytest.raises(TypeError):
            DatabaseConnectionRepository()  # type: ignore[abstract]

    @pytest.mark.unit
    def test_entity_dataclass_fields(self) -> None:
        """DatabaseConnectionEntity should have all expected fields."""
        import dataclasses

        fields = {f.name for f in dataclasses.fields(DatabaseConnectionEntity)}
        expected = {
            "id",
            "tenant_id",
            "owner_id",
            "name",
            "description",
            "dialect",
            "host",
            "port",
            "database",
            "project_id",
            "account_id",
            "warehouse_id",
            "secret_path",
            "secret_key",
            "ssl_mode",
            "status",
            "last_tested_at",
            "dialect_version",
            "created_at",
            "updated_at",
        }
        assert fields == expected
