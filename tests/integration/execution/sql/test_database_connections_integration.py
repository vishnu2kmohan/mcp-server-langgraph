"""Integration tests for database connections CRUD + connection tester.

These tests verify end-to-end flows:
- SQLite connection tester (no external deps needed)
- InMemorySecretsProvider for credential storage
- ConnectionTester with real SQLite driver

Requires no external services (no postgres-test, no docker).
"""

from __future__ import annotations

import gc
import uuid
from datetime import UTC, datetime

import pytest

from mcp_server_langgraph.core.secrets import InMemorySecretsProvider
from mcp_server_langgraph.execution.sql.connection_tester import (
    ConnectionTester,
    ConnectionTestResult,
)
from mcp_server_langgraph.execution.sql.drivers.registry import DriverRegistry
from mcp_server_langgraph.repositories.database_connections import (
    DatabaseConnectionEntity,
)

pytestmark = [pytest.mark.integration, pytest.mark.sql]


def _make_sqlite_entity(**overrides) -> DatabaseConnectionEntity:
    """Create a SQLite connection entity for testing."""
    now = datetime.now(UTC)
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": "test-tenant",
        "owner_id": "test-user",
        "name": "test-sqlite",
        "description": "Integration test SQLite",
        "dialect": "sqlite",
        "host": None,
        "port": None,
        "database": ":memory:",
        "project_id": None,
        "account_id": None,
        "warehouse_id": None,
        "secret_path": "/database/test-tenant/sqlite",
        "secret_key": "test-sqlite",
        "ssl_mode": "disable",
        "status": "disconnected",
        "last_tested_at": None,
        "dialect_version": None,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return DatabaseConnectionEntity(**defaults)


@pytest.mark.xdist_group(name="test_db_conn_integration")
class TestSQLiteConnectionTester:
    """Test ConnectionTester with real SQLite driver (no external deps)."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.integration
    async def test_sqlite_connection_test_success(self) -> None:
        """SQLite connection test should succeed with version info."""
        import json

        secrets = InMemorySecretsProvider()

        # Store SQLite credentials
        creds = json.dumps({"db_path": ":memory:"})
        await secrets.set_secret("/database/test-tenant/sqlite/test-sqlite", creds)

        registry = DriverRegistry()
        tester = ConnectionTester(registry, secrets)

        entity = _make_sqlite_entity()
        result = await tester.test(entity)

        assert isinstance(result, ConnectionTestResult)
        # SQLite should always connect successfully -- no external deps needed
        assert result.success is True, f"SQLite connection test failed: {result.error}"
        assert result.dialect_version is not None
        assert result.error is None

    @pytest.mark.integration
    async def test_secrets_provider_round_trip(self) -> None:
        """InMemorySecretsProvider should store and retrieve secrets."""
        secrets = InMemorySecretsProvider()

        await secrets.set_secret("test-key", "test-value")
        value = await secrets.get_secret("test-key")
        assert value == "test-value"

        await secrets.delete_secret("test-key")
        value = await secrets.get_secret("test-key")
        assert value is None

    @pytest.mark.integration
    async def test_unknown_dialect_returns_error(self) -> None:
        """Connection test with unknown dialect should fail gracefully."""
        import json

        secrets = InMemorySecretsProvider()
        creds = json.dumps({"host": "localhost"})
        await secrets.set_secret("/database/test-tenant/oracle/test-oracle", creds)

        registry = DriverRegistry()
        tester = ConnectionTester(registry, secrets)

        entity = _make_sqlite_entity(dialect="oracle", name="test-oracle", secret_key="test-oracle")
        result = await tester.test(entity)

        assert result.success is False
        assert result.error is not None
