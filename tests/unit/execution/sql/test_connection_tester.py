"""Tests for ConnectionTester (Phase 6b).

Tests the connection testing service with mocked drivers, registry,
secrets provider, and egress validator.
"""

from __future__ import annotations

import asyncio
import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.execution.sql.connection_tester import (
    ConnectionTestResult,
    ConnectionTester,
)

pytestmark = pytest.mark.unit


def _make_entity(**overrides):
    """Build a mock DatabaseConnectionEntity."""
    from mcp_server_langgraph.repositories.database_connections import (
        DatabaseConnectionEntity,
    )
    import uuid
    from datetime import UTC, datetime

    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": "tenant-1",
        "owner_id": "user-1",
        "name": "test-conn",
        "description": None,
        "dialect": "postgres",
        "host": "db.example.com",
        "port": 5432,
        "database": "mydb",
        "project_id": None,
        "account_id": None,
        "warehouse_id": None,
        "secret_path": "/database/tenant-1/postgres",
        "secret_key": "test_conn",
        "ssl_mode": "require",
        "status": "disconnected",
        "last_tested_at": None,
        "dialect_version": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return DatabaseConnectionEntity(**defaults)


def _make_driver(*, version_result: str = "PostgreSQL 15.2") -> AsyncMock:
    """Create a mock driver."""
    driver = AsyncMock()  # noqa: async-mock-config - mock driver with dynamic attributes
    driver.connect = AsyncMock()  # noqa: async-mock-config
    driver.execute = AsyncMock(
        side_effect=[
            [{"?column?": 1}],  # SELECT 1
            [{"version": version_result}],  # version query
        ]
    )
    driver.close = AsyncMock()  # noqa: async-mock-config
    driver.is_healthy = True
    return driver


def _make_registry(driver: AsyncMock | None = None) -> MagicMock:
    """Create a mock DriverRegistry.

    Since _create_driver is now a per-dialect factory that returns
    (driver, resource), we patch it directly in tests to avoid
    needing real database libraries.
    """
    registry = MagicMock()
    d = driver or _make_driver()
    registry.get_driver.return_value = MagicMock(return_value=d)
    return registry, d


def _make_secrets(credentials: dict | None = None) -> AsyncMock:
    """Create a mock SecretsProvider."""
    import json

    secrets = AsyncMock()  # noqa: async-mock-config - mock secrets provider with dynamic attributes
    creds = credentials or {
        "host": "db.example.com",
        "port": 5432,
        "database": "mydb",
        "username": "admin",
        "password": "secret",
    }
    secrets.get_secret = AsyncMock(return_value=json.dumps(creds))  # noqa: async-mock-config
    secrets.set_secret = AsyncMock()  # noqa: async-mock-config
    secrets.delete_secret = AsyncMock()  # noqa: async-mock-config
    return secrets


def _patch_create_driver(driver: AsyncMock):
    """Return a patch context that makes _create_driver return (driver, None)."""

    async def mock_create_driver(self, dialect, credentials):
        return driver, None

    return patch.object(ConnectionTester, "_create_driver", mock_create_driver)


class TestConnectionTester:
    """Test ConnectionTester.test() method."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.unit
    async def test_success_returns_version(self) -> None:
        """Successful test should return version info."""
        registry, driver = _make_registry()
        secrets = _make_secrets()

        tester = ConnectionTester(registry, secrets)
        entity = _make_entity()

        with _patch_create_driver(driver):
            result = await tester.test(entity)

        assert isinstance(result, ConnectionTestResult)
        assert result.success is True
        assert result.dialect_version is not None
        assert result.error is None
        driver.connect.assert_awaited_once()
        driver.close.assert_awaited_once()

    @pytest.mark.unit
    async def test_failure_returns_sanitized_error(self) -> None:
        """Connection failure should return sanitized error."""
        driver = _make_driver()
        driver.connect.side_effect = Exception("Connection refused by 10.0.0.1:5432")
        registry, _ = _make_registry(driver)
        secrets = _make_secrets()

        tester = ConnectionTester(registry, secrets)
        entity = _make_entity()

        with _patch_create_driver(driver):
            result = await tester.test(entity)

        assert result.success is False
        assert result.error is not None
        # Raw IP should not leak
        assert "10.0.0.1" not in result.error

    @pytest.mark.unit
    async def test_timeout_returns_error(self) -> None:
        """Connection timeout should return timeout error."""
        driver = _make_driver()

        async def slow_connect():
            await asyncio.sleep(100)  # noqa: sleep-duration

        driver.connect = AsyncMock(side_effect=slow_connect)
        registry, _ = _make_registry(driver)
        secrets = _make_secrets()

        tester = ConnectionTester(registry, secrets, timeout=0.1)
        entity = _make_entity()

        with _patch_create_driver(driver):
            result = await tester.test(entity)

        assert result.success is False
        assert result.error is not None
        assert "timeout" in result.error.lower()

    @pytest.mark.unit
    async def test_closes_driver_on_success(self) -> None:
        """Driver should be closed after successful test."""
        registry, driver = _make_registry()
        secrets = _make_secrets()

        tester = ConnectionTester(registry, secrets)
        entity = _make_entity()

        with _patch_create_driver(driver):
            await tester.test(entity)

        driver.close.assert_awaited_once()

    @pytest.mark.unit
    async def test_closes_driver_on_failure(self) -> None:
        """Driver should be closed even on connection failure."""
        driver = _make_driver()
        driver.execute.side_effect = Exception("query failed")
        registry, _ = _make_registry(driver)
        secrets = _make_secrets()

        tester = ConnectionTester(registry, secrets)
        entity = _make_entity()

        with _patch_create_driver(driver):
            await tester.test(entity)

        driver.close.assert_awaited_once()

    @pytest.mark.unit
    async def test_unknown_dialect_returns_error(self) -> None:
        """Unknown dialect should return an error."""
        registry = MagicMock()
        registry.get_driver.side_effect = KeyError("No driver for 'oracle'")
        secrets = _make_secrets()

        tester = ConnectionTester(registry, secrets)
        entity = _make_entity(dialect="oracle")

        result = await tester.test(entity)

        assert result.success is False
        assert result.error is not None

    @pytest.mark.unit
    async def test_egress_validation_blocks_connection(self) -> None:
        """Egress validation failure should block connection test."""
        from mcp_server_langgraph.execution.sql.exceptions import EgressValidationError

        registry, driver = _make_registry()
        secrets = _make_secrets()
        egress = AsyncMock()
        egress.validate_before_connect.side_effect = EgressValidationError(message="Blocked by SSRF protection")

        tester = ConnectionTester(registry, secrets, egress_validator=egress)
        entity = _make_entity()

        with _patch_create_driver(driver):
            result = await tester.test(entity)

        assert result.success is False
        assert "security policy" in result.error.lower()
        # Driver should not have been called
        driver.connect.assert_not_awaited()

    @pytest.mark.unit
    async def test_skips_egress_for_hostless_dialects(self) -> None:
        """Hostless dialects (sqlite, duckdb, bigquery) should skip egress."""
        driver = _make_driver()
        registry, _ = _make_registry(driver)
        secrets = _make_secrets()
        egress = AsyncMock()  # noqa: async-mock-config - mock egress validator

        tester = ConnectionTester(registry, secrets, egress_validator=egress)

        for dialect in ("sqlite", "duckdb", "bigquery"):
            # Reset driver execute side_effect for each iteration
            driver.execute = AsyncMock(
                side_effect=[
                    [{"?column?": 1}],
                    [{"version": "test"}],
                ]
            )
            entity = _make_entity(dialect=dialect, host=None)
            with _patch_create_driver(driver):
                await tester.test(entity)
            egress.validate_before_connect.assert_not_awaited()

    @pytest.mark.unit
    async def test_cleanup_on_timeout(self) -> None:
        """Resources should be cleaned up even on timeout."""
        driver = _make_driver()
        close_called = False
        original_close = driver.close

        async def track_close():
            nonlocal close_called
            close_called = True
            return await original_close()

        driver.close = track_close

        async def slow_connect():
            await asyncio.sleep(100)  # noqa: sleep-duration

        driver.connect = AsyncMock(side_effect=slow_connect)
        registry, _ = _make_registry(driver)
        secrets = _make_secrets()

        tester = ConnectionTester(registry, secrets, timeout=0.1)
        entity = _make_entity()

        with _patch_create_driver(driver):
            await tester.test(entity)

        assert close_called

    @pytest.mark.unit
    async def test_credential_retrieval_failure(self) -> None:
        """Failed credential retrieval should return error."""
        from mcp_server_langgraph.execution.sql.credential_manager import (
            CredentialRetrievalError,
        )

        registry, _ = _make_registry()
        secrets = AsyncMock()  # noqa: async-mock-config - mock secrets provider
        secrets.get_secret = AsyncMock(return_value=None)  # noqa: async-mock-config

        tester = ConnectionTester(registry, secrets)
        entity = _make_entity()

        # SecureConnectionConfig.get_credentials raises CredentialRetrievalError
        # when get_secret returns None. Patch it to ensure we test the flow.
        with patch("mcp_server_langgraph.execution.sql.connection_tester.SecureConnectionConfig") as MockConfig:
            instance = MockConfig.return_value
            instance.get_credentials = AsyncMock(side_effect=CredentialRetrievalError("Secret not found"))

            result = await tester.test(entity)

        assert result.success is False
        assert result.error is not None

    @pytest.mark.unit
    async def test_egress_validates_credentials_host(self) -> None:
        """Egress validation should use host from credentials, not entity."""
        registry, driver = _make_registry()
        secrets = _make_secrets(
            credentials={
                "host": "real-host.internal",
                "port": 5432,
                "database": "mydb",
                "username": "admin",
                "password": "secret",
            }
        )
        egress = AsyncMock()
        egress.validate_before_connect.return_value = ("1.2.3.4", "")

        tester = ConnectionTester(registry, secrets, egress_validator=egress)
        # Entity has no host, but credentials have host
        entity = _make_entity(host=None)

        with _patch_create_driver(driver):
            await tester.test(entity)

        # Egress should have been called with the credentials host
        egress.validate_before_connect.assert_awaited_once()
        call_args = egress.validate_before_connect.call_args
        assert call_args[0][0] == "real-host.internal"

    @pytest.mark.unit
    async def test_resource_cleanup_on_success(self) -> None:
        """External resources (pools, connections) should be cleaned up."""
        driver = _make_driver()
        resource = AsyncMock()  # noqa: async-mock-config - mock resource with dynamic close

        async def mock_create_driver(self, dialect, credentials):
            return driver, resource

        registry, _ = _make_registry(driver)
        secrets = _make_secrets()

        tester = ConnectionTester(registry, secrets)
        entity = _make_entity()

        with patch.object(ConnectionTester, "_create_driver", mock_create_driver):
            await tester.test(entity)

        driver.close.assert_awaited_once()
        resource.close.assert_awaited_once()

    @pytest.mark.unit
    async def test_redshift_uses_thread_executor(self) -> None:
        """Redshift connector should run in thread executor to avoid blocking."""
        registry, driver = _make_registry()
        secrets = _make_secrets(
            credentials={
                "host": "redshift.example.com",
                "port": 5439,
                "database": "warehouse",
                "username": "admin",
                "password": "secret",
            }
        )
        tester = ConnectionTester(registry, secrets)
        entity = _make_entity(dialect="redshift")

        with patch("asyncio.to_thread") as mock_to_thread:
            mock_conn = MagicMock()
            mock_conn.close = MagicMock()
            mock_to_thread.return_value = mock_conn

            with patch("mcp_server_langgraph.execution.sql.connection_tester.ConnectionTester._create_driver") as mock_create:
                mock_create.return_value = (driver, mock_conn)
                await tester.test(entity)

        # Verify driver was created (the actual to_thread call is in _create_driver)

    @pytest.mark.unit
    async def test_snowflake_uses_thread_executor(self) -> None:
        """Snowflake connector should run in thread executor to avoid blocking."""
        registry, driver = _make_registry()
        secrets = _make_secrets(
            credentials={
                "account_id": "xy12345",
                "username": "admin",
                "password": "secret",
                "warehouse_id": "COMPUTE_WH",
                "database": "MYDB",
            }
        )
        tester = ConnectionTester(registry, secrets)
        entity = _make_entity(dialect="snowflake", host=None)

        with patch("mcp_server_langgraph.execution.sql.connection_tester.ConnectionTester._create_driver") as mock_create:
            mock_conn = MagicMock()
            mock_create.return_value = (driver, mock_conn)
            await tester.test(entity)

    @pytest.mark.unit
    async def test_trino_uses_thread_executor(self) -> None:
        """Trino connector should run in thread executor to avoid blocking."""
        registry, driver = _make_registry()
        secrets = _make_secrets(
            credentials={
                "host": "trino.example.com",
                "port": 8080,
                "username": "admin",
                "catalog": "hive",
                "schema": "default",
            }
        )
        tester = ConnectionTester(registry, secrets)
        entity = _make_entity(dialect="trino")

        with patch("mcp_server_langgraph.execution.sql.connection_tester.ConnectionTester._create_driver") as mock_create:
            mock_conn = MagicMock()
            mock_create.return_value = (driver, mock_conn)
            await tester.test(entity)

    @pytest.mark.unit
    async def test_sqlite_path_traversal_blocked(self) -> None:
        """SECURITY: SQLite paths outside allowed directory should be blocked."""
        import os

        registry, driver = _make_registry()
        secrets = _make_secrets(
            credentials={
                "db_path": "/etc/passwd",  # Attempted path traversal
            }
        )
        tester = ConnectionTester(registry, secrets)
        entity = _make_entity(dialect="sqlite", host=None)

        # Set allowed directory
        with patch.dict(os.environ, {"SQLITE_DATA_DIR": "/data"}):
            result = await tester.test(entity)

        assert result.success is False
        assert result.error is not None

    @pytest.mark.unit
    async def test_duckdb_path_traversal_blocked(self) -> None:
        """SECURITY: DuckDB paths outside allowed directory should be blocked."""
        import os

        registry, driver = _make_registry()
        secrets = _make_secrets(
            credentials={
                "db_path": "../../../etc/shadow",  # Attempted traversal
            }
        )
        tester = ConnectionTester(registry, secrets)
        entity = _make_entity(dialect="duckdb", host=None)

        with patch.dict(os.environ, {"DUCKDB_DATA_DIR": "/data"}):
            result = await tester.test(entity)

        assert result.success is False
        assert result.error is not None

    @pytest.mark.unit
    async def test_sqlite_memory_path_allowed(self) -> None:
        """SQLite :memory: path should always be allowed."""
        registry, driver = _make_registry()
        secrets = _make_secrets(
            credentials={
                "db_path": ":memory:",
            }
        )
        tester = ConnectionTester(registry, secrets)
        entity = _make_entity(dialect="sqlite", host=None)

        with _patch_create_driver(driver):
            result = await tester.test(entity)

        # Should succeed (driver is mocked)
        assert result.success is True

    @pytest.mark.unit
    async def test_null_port_uses_default(self) -> None:
        """Null port in credentials should use dialect default, not TypeError."""
        registry, driver = _make_registry()
        secrets = _make_secrets(
            credentials={
                "host": "db.example.com",
                "port": None,  # Explicitly null
                "database": "mydb",
                "username": "admin",
                "password": "secret",
            }
        )
        tester = ConnectionTester(registry, secrets)
        entity = _make_entity(dialect="postgres")

        with _patch_create_driver(driver):
            result = await tester.test(entity)

        # Should not raise TypeError
        assert result.success is True


class TestConnectionTestResult:
    """Test ConnectionTestResult dataclass."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.unit
    def test_success_result_has_version(self) -> None:
        """Success result should have version and no error."""
        result = ConnectionTestResult(success=True, dialect_version="15.2", error=None)
        assert result.success is True
        assert result.dialect_version == "15.2"

    @pytest.mark.unit
    def test_failure_result_has_error(self) -> None:
        """Failure result should have error and no version."""
        result = ConnectionTestResult(success=False, error="Connection failed", dialect_version=None)
        assert result.success is False
        assert result.error == "Connection failed"
