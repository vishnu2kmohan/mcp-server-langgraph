"""
Unit tests for database driver implementations, registry, and base types.

Tests CancellationType enum, DatabaseDriver ABC, QueryLimits dataclass,
DriverRegistry, and all concrete driver implementations (SQLite, Postgres,
BigQuery, Snowflake, MySQL, DuckDB, Redshift, ClickHouse, Trino) with
appropriate mocking for external dependencies.
"""

import gc
from collections.abc import Mapping, Sequence
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.execution.sql.drivers.base import (
    CancellationType,
    DatabaseDriver,
    QueryLimits,
)
from mcp_server_langgraph.execution.sql.drivers.registry import DriverRegistry
from mcp_server_langgraph.execution.sql.drivers.sqlite import SQLiteDriver
from mcp_server_langgraph.execution.sql.drivers.postgres import PostgresDriver

# Optional drivers - import if available
try:
    from mcp_server_langgraph.execution.sql.drivers.bigquery import BigQueryDriver

    _HAS_BIGQUERY_DRIVER = True
except ImportError:
    _HAS_BIGQUERY_DRIVER = False

try:
    from mcp_server_langgraph.execution.sql.drivers.snowflake import SnowflakeDriver

    _HAS_SNOWFLAKE_DRIVER = True
except ImportError:
    _HAS_SNOWFLAKE_DRIVER = False

try:
    from mcp_server_langgraph.execution.sql.drivers.mysql import MySQLDriver

    _HAS_MYSQL_DRIVER = True
except ImportError:
    _HAS_MYSQL_DRIVER = False

try:
    from mcp_server_langgraph.execution.sql.drivers.duckdb import DuckDBDriver

    _HAS_DUCKDB_DRIVER = True
except ImportError:
    _HAS_DUCKDB_DRIVER = False

try:
    from mcp_server_langgraph.execution.sql.drivers.redshift import RedshiftDriver

    _HAS_REDSHIFT_DRIVER = True
except ImportError:
    _HAS_REDSHIFT_DRIVER = False

try:
    from mcp_server_langgraph.execution.sql.drivers.clickhouse import ClickHouseDriver

    _HAS_CLICKHOUSE_DRIVER = True
except ImportError:
    _HAS_CLICKHOUSE_DRIVER = False

try:
    from mcp_server_langgraph.execution.sql.drivers.trino import TrinoDriver

    _HAS_TRINO_DRIVER = True
except ImportError:
    _HAS_TRINO_DRIVER = False

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# CancellationType enum
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testcancellationtype")
class TestCancellationType:
    """Verify CancellationType enum values and members."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_connection_level_value(self):
        assert CancellationType.CONNECTION_LEVEL.value == "connection"

    def test_job_based_value(self):
        assert CancellationType.JOB_BASED.value == "job"

    def test_param_value_with_none_returns_null_string(self):
        assert CancellationType.NONE.value == "none"

    def test_all_three_members(self):
        members = list(CancellationType)
        assert len(members) == 3
        assert CancellationType.CONNECTION_LEVEL in members
        assert CancellationType.JOB_BASED in members
        assert CancellationType.NONE in members

    def test_param_style_enum_has_expected_names(self):
        assert CancellationType.CONNECTION_LEVEL.name == "CONNECTION_LEVEL"
        assert CancellationType.JOB_BASED.name == "JOB_BASED"
        assert CancellationType.NONE.name == "NONE"


# ---------------------------------------------------------------------------
# DatabaseDriver ABC
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testdatabasedriverabc")
class TestDatabaseDriverABC:
    """Verify DatabaseDriver cannot be instantiated directly and a concrete
    subclass that implements all abstract methods works."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError, match="abstract"):
            DatabaseDriver()  # type: ignore[abstract]

    def test_concrete_subclass_works(self):
        """A subclass implementing all abstract methods can be instantiated."""

        class ConcreteDriver(DatabaseDriver):
            @property
            def cancellation_type(self) -> CancellationType:
                return CancellationType.NONE

            @property
            def driver_name(self) -> str:
                return "test"

            async def connect(self) -> None:
                pass

            async def execute(self, sql, params=None):
                return []

            async def cancel(self) -> bool:
                return False

            async def close(self) -> None:
                pass

            @property
            def is_healthy(self) -> bool:
                return True

        driver = ConcreteDriver()
        assert driver.cancellation_type == CancellationType.NONE
        assert driver.is_healthy is True
        assert driver.driver_name == "test"

    def test_missing_abstract_method_raises(self):
        """A subclass missing an abstract method cannot be instantiated."""

        class IncompleteDriver(DatabaseDriver):
            @property
            def cancellation_type(self) -> CancellationType:
                return CancellationType.NONE

            async def connect(self) -> None:
                pass

            # Missing: execute, cancel, close, is_healthy

        with pytest.raises(TypeError):
            IncompleteDriver()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# QueryLimits dataclass
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testquerylimits")
class TestQueryLimits:
    """Verify QueryLimits defaults and from_sandbox factory."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_query_result_has_default_empty_values(self):
        limits = QueryLimits()
        assert limits.timeout_seconds == 30
        assert limits.max_rows == 10000
        assert limits.max_bytes == 50 * 1024 * 1024

    def test_from_sandbox_pyodide(self):
        limits = QueryLimits.from_sandbox("pyodide")
        assert limits.timeout_seconds == 10
        assert limits.max_rows == 1000
        assert limits.max_bytes == 10 * 1024 * 1024

    def test_from_sandbox_docker(self):
        limits = QueryLimits.from_sandbox("docker")
        assert limits.timeout_seconds == 30
        assert limits.max_rows == 10000
        assert limits.max_bytes == 50 * 1024 * 1024

    def test_from_sandbox_kubernetes(self):
        limits = QueryLimits.from_sandbox("kubernetes")
        assert limits.timeout_seconds == 60
        assert limits.max_rows == 50000
        assert limits.max_bytes == 100 * 1024 * 1024

    def test_from_sandbox_unknown_uses_kubernetes_defaults(self):
        """Unknown sandbox type falls through to the else branch (kubernetes defaults)."""
        limits = QueryLimits.from_sandbox("unknown_sandbox")
        assert limits.timeout_seconds == 60
        assert limits.max_rows == 50000
        assert limits.max_bytes == 100 * 1024 * 1024


@pytest.mark.unit
@pytest.mark.xdist_group(name="testquerylimitsdataclass")
class TestQueryLimitsDataclass:
    """Verify QueryLimits dataclass field values and behavior."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_field_values_custom(self):
        limits = QueryLimits(timeout_seconds=5, max_rows=100, max_bytes=1024)
        assert limits.timeout_seconds == 5
        assert limits.max_rows == 100
        assert limits.max_bytes == 1024

    def test_query_result_columns_are_mutable(self):
        """QueryLimits is a regular (non-frozen) dataclass, so fields are mutable."""
        limits = QueryLimits()
        limits.timeout_seconds = 99
        assert limits.timeout_seconds == 99

    def test_query_result_equality_with_same_data(self):
        a = QueryLimits(timeout_seconds=30, max_rows=10000, max_bytes=50 * 1024 * 1024)
        b = QueryLimits()
        assert a == b

    def test_query_result_inequality_with_different_data(self):
        a = QueryLimits(timeout_seconds=10)
        b = QueryLimits(timeout_seconds=30)
        assert a != b


# ---------------------------------------------------------------------------
# DriverRegistry
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testdriverregistry")
class TestDriverRegistry:
    """Verify DriverRegistry register/get_driver/list_dialects behavior."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_register_and_get_driver(self):
        registry = DriverRegistry()
        # postgres and sqlite should be pre-registered
        assert registry.get_driver("postgres") is PostgresDriver
        assert registry.get_driver("sqlite") is SQLiteDriver

    def test_unknown_dialect_raises_key_error(self):
        registry = DriverRegistry()
        with pytest.raises(KeyError, match="No driver registered for dialect 'oracle'"):
            registry.get_driver("oracle")

    def test_list_dialects_contains_defaults(self):
        registry = DriverRegistry()
        dialects = registry.list_dialects()
        assert "postgres" in dialects
        assert "sqlite" in dialects
        # Result is sorted
        assert dialects == sorted(dialects)

    def test_register_custom_driver(self):
        """Registering a custom driver makes it retrievable."""

        class CustomDriver(DatabaseDriver):
            @property
            def cancellation_type(self) -> CancellationType:
                return CancellationType.NONE

            async def connect(self) -> None:
                pass

            async def execute(self, sql, params=None):
                return []

            async def cancel(self) -> bool:
                return False

            async def close(self) -> None:
                pass

            @property
            def is_healthy(self) -> bool:
                return True

        registry = DriverRegistry()
        registry.register("custom", CustomDriver)
        assert registry.get_driver("custom") is CustomDriver
        assert "custom" in registry.list_dialects()

    def test_register_overrides_existing(self):
        """Re-registering a dialect replaces the previous driver."""
        registry = DriverRegistry()
        original = registry.get_driver("sqlite")

        class AltSQLiteDriver(DatabaseDriver):
            @property
            def cancellation_type(self) -> CancellationType:
                return CancellationType.NONE

            async def connect(self) -> None:
                pass

            async def execute(self, sql, params=None):
                return []

            async def cancel(self) -> bool:
                return False

            async def close(self) -> None:
                pass

            @property
            def is_healthy(self) -> bool:
                return True

        registry.register("sqlite", AltSQLiteDriver)
        assert registry.get_driver("sqlite") is AltSQLiteDriver
        assert registry.get_driver("sqlite") is not original

    def test_register_invalid_dialect_raises(self):
        registry = DriverRegistry()
        with pytest.raises(ValueError, match="non-empty string"):
            registry.register("", SQLiteDriver)

    def test_register_non_driver_class_raises(self):
        registry = DriverRegistry()
        with pytest.raises(TypeError, match="subclass of DatabaseDriver"):
            registry.register("bad", str)  # type: ignore[arg-type]

    def test_list_dialects_returns_sorted(self):
        registry = DriverRegistry()
        dialects = registry.list_dialects()
        assert dialects == sorted(dialects)


# ---------------------------------------------------------------------------
# SQLiteDriver
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testsqlitedriver")
class TestSQLiteDriver:
    """Verify SQLiteDriver behavior with in-memory database."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_cancellation_type_is_none(self):
        driver = SQLiteDriver()
        assert driver.cancellation_type == CancellationType.NONE

    async def test_cancel_returns_false(self):
        driver = SQLiteDriver()
        result = await driver.cancel()
        assert result is False

    async def test_connect_execute_close_lifecycle(self):
        """Full lifecycle: connect, create table, insert, select, close."""
        driver = SQLiteDriver(":memory:")
        await driver.connect()
        assert driver.is_healthy

        # Create a table
        await driver.execute("CREATE TABLE test (id INTEGER, name TEXT)")

        # Insert data
        await driver.execute(
            "INSERT INTO test (id, name) VALUES (:id, :name)",
            {"id": 1, "name": "alice"},
        )

        # Select data
        results = await driver.execute("SELECT id, name FROM test")
        assert len(results) == 1
        assert results[0]["id"] == 1
        assert results[0]["name"] == "alice"

        await driver.close()
        assert not driver.is_healthy

    async def test_is_healthy_before_connect(self):
        driver = SQLiteDriver()
        assert driver.is_healthy is False

    async def test_is_healthy_after_connect(self):
        driver = SQLiteDriver(":memory:")
        await driver.connect()
        assert driver.is_healthy is True
        await driver.close()

    async def test_execute_returns_list_of_dicts(self):
        driver = SQLiteDriver(":memory:")
        await driver.connect()

        await driver.execute("CREATE TABLE items (id INTEGER, label TEXT, value REAL)")
        await driver.execute("INSERT INTO items VALUES (1, 'a', 1.5)")
        await driver.execute("INSERT INTO items VALUES (2, 'b', 2.5)")

        results = await driver.execute("SELECT * FROM items ORDER BY id")
        assert isinstance(results, list)
        assert len(results) == 2
        assert isinstance(results[0], dict)
        assert set(results[0].keys()) == {"id", "label", "value"}
        assert results[0]["id"] == 1
        assert results[1]["id"] == 2

        await driver.close()

    async def test_execute_without_connect_raises(self):
        driver = SQLiteDriver(":memory:")
        with pytest.raises(Exception, match="Not connected"):
            await driver.execute("SELECT 1")

    async def test_close_is_idempotent(self):
        driver = SQLiteDriver(":memory:")
        await driver.connect()
        await driver.close()
        # Closing again should not raise
        await driver.close()
        assert not driver.is_healthy


# ---------------------------------------------------------------------------
# PostgresDriver
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testpostgresdriver")
class TestPostgresDriver:
    """Verify PostgresDriver behavior with mocked asyncpg pool."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_cancellation_type_is_connection_level(self):
        mock_pool = MagicMock()
        driver = PostgresDriver(pool=mock_pool)
        assert driver.cancellation_type == CancellationType.CONNECTION_LEVEL

    async def test_cancel_with_no_active_query(self):
        mock_pool = MagicMock()
        driver = PostgresDriver(pool=mock_pool)
        # No active PID since no query is running
        result = await driver.cancel()
        assert result is False

    async def test_cancel_with_mock_pool(self):
        mock_pool = AsyncMock()  # noqa: async-mock-config
        mock_pool.fetchval = AsyncMock(return_value=True)

        driver = PostgresDriver(pool=mock_pool)
        # Simulate an active query PID
        driver._current_pid = 12345

        result = await driver.cancel()
        assert result is True
        mock_pool.fetchval.assert_awaited_once_with("SELECT pg_cancel_backend($1)", 12345)

    async def test_execute_with_mock_connection(self):
        mock_record = {"id": 1, "name": "alice"}
        mock_conn = AsyncMock()  # noqa: async-mock-config
        mock_conn.fetch = AsyncMock(return_value=[mock_record])
        mock_conn.get_server_pid = MagicMock(return_value=42)

        mock_pool = AsyncMock()  # noqa: async-mock-config
        mock_pool.acquire = AsyncMock(return_value=mock_conn)

        driver = PostgresDriver(pool=mock_pool)
        await driver.connect()

        results = await driver.execute("SELECT id, name FROM users")
        assert results == [{"id": 1, "name": "alice"}]
        mock_conn.fetch.assert_awaited_once_with("SELECT id, name FROM users")

    async def test_execute_with_params(self):
        mock_record = {"id": 1}
        mock_conn = AsyncMock()  # noqa: async-mock-config
        mock_conn.fetch = AsyncMock(return_value=[mock_record])
        mock_conn.get_server_pid = MagicMock(return_value=42)

        mock_pool = AsyncMock()  # noqa: async-mock-config
        mock_pool.acquire = AsyncMock(return_value=mock_conn)

        driver = PostgresDriver(pool=mock_pool)
        await driver.connect()

        await driver.execute("SELECT * FROM users WHERE id = $1", {"id": 1})
        mock_conn.fetch.assert_awaited_once_with("SELECT * FROM users WHERE id = $1", 1)

    async def test_is_healthy_before_connect(self):
        mock_pool = MagicMock()
        driver = PostgresDriver(pool=mock_pool)
        assert driver.is_healthy is False

    async def test_is_healthy_after_connect(self):
        mock_conn = AsyncMock()  # noqa: async-mock-config
        mock_conn.is_closed = MagicMock(return_value=False)
        mock_conn.get_server_pid = MagicMock(return_value=42)

        mock_pool = AsyncMock()  # noqa: async-mock-config
        mock_pool.acquire = AsyncMock(return_value=mock_conn)

        driver = PostgresDriver(pool=mock_pool)
        await driver.connect()
        assert driver.is_healthy is True

    async def test_close_releases_to_pool(self):
        mock_conn = AsyncMock()  # noqa: async-mock-config
        mock_conn.get_server_pid = MagicMock(return_value=42)
        mock_pool = AsyncMock()  # noqa: async-mock-config
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()  # noqa: async-mock-config

        driver = PostgresDriver(pool=mock_pool)
        await driver.connect()
        await driver.close()

        mock_pool.release.assert_awaited_once_with(mock_conn)
        assert driver.is_healthy is False


# ---------------------------------------------------------------------------
# BigQueryDriver
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testbigquerydriver")
class TestBigQueryDriver:
    """Verify BigQueryDriver behavior with mocked BigQuery client."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture
    def mock_bigquery_module(self):
        """Patch the _HAS_BIGQUERY flag and provide mock bigquery module."""
        with patch("mcp_server_langgraph.execution.sql.drivers.bigquery._HAS_BIGQUERY", True):
            yield

    @pytest.mark.skipif(not _HAS_BIGQUERY_DRIVER, reason="BigQuery driver not available")
    def test_cancellation_type_is_job_based(self, mock_bigquery_module):
        mock_client = MagicMock()
        driver = BigQueryDriver(project="test-project", client=mock_client)
        assert driver.cancellation_type == CancellationType.JOB_BASED

    @pytest.mark.skipif(not _HAS_BIGQUERY_DRIVER, reason="BigQuery driver not available")
    async def test_cancel_with_no_active_job(self, mock_bigquery_module):
        mock_client = MagicMock()
        driver = BigQueryDriver(project="test-project", client=mock_client)
        result = await driver.cancel()
        assert result is False

    @pytest.mark.skipif(not _HAS_BIGQUERY_DRIVER, reason="BigQuery driver not available")
    async def test_cancel_with_mock_job(self, mock_bigquery_module):
        mock_client = MagicMock()
        mock_job = MagicMock()
        mock_job.job_id = "job-123"
        mock_job.cancel = MagicMock()

        driver = BigQueryDriver(project="test-project", client=mock_client)
        driver._current_job = mock_job

        result = await driver.cancel()
        assert result is True
        mock_job.cancel.assert_called_once()

    @pytest.mark.skipif(not _HAS_BIGQUERY_DRIVER, reason="BigQuery driver not available")
    async def test_close_is_noop(self, mock_bigquery_module):
        mock_client = MagicMock()
        driver = BigQueryDriver(project="test-project", client=mock_client)
        await driver.connect()
        # close() should not raise
        await driver.close()

    @pytest.mark.skipif(not _HAS_BIGQUERY_DRIVER, reason="BigQuery driver not available")
    async def test_is_healthy_after_connect(self, mock_bigquery_module):
        mock_client = MagicMock()
        driver = BigQueryDriver(project="test-project", client=mock_client)
        await driver.connect()
        assert driver.is_healthy is True

    @pytest.mark.skipif(not _HAS_BIGQUERY_DRIVER, reason="BigQuery driver not available")
    def test_is_healthy_before_connect(self, mock_bigquery_module):
        mock_client = MagicMock()
        driver = BigQueryDriver(project="test-project", client=mock_client)
        assert driver.is_healthy is False


# ---------------------------------------------------------------------------
# SnowflakeDriver
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testsnowflakedriver")
class TestSnowflakeDriver:
    """Verify SnowflakeDriver behavior with mocked Snowflake connection."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture
    def mock_snowflake_module(self):
        """Patch the _HAS_SNOWFLAKE flag."""
        with patch(
            "mcp_server_langgraph.execution.sql.drivers.snowflake._HAS_SNOWFLAKE",
            True,
        ):
            yield

    @pytest.mark.skipif(not _HAS_SNOWFLAKE_DRIVER, reason="Snowflake driver not available")
    def test_cancellation_type_is_job_based(self, mock_snowflake_module):
        mock_conn = MagicMock()
        driver = SnowflakeDriver(connection=mock_conn)
        assert driver.cancellation_type == CancellationType.JOB_BASED

    @pytest.mark.skipif(not _HAS_SNOWFLAKE_DRIVER, reason="Snowflake driver not available")
    async def test_cancel_with_no_active_query(self, mock_snowflake_module):
        mock_conn = MagicMock()
        driver = SnowflakeDriver(connection=mock_conn)
        result = await driver.cancel()
        assert result is False

    @pytest.mark.skipif(not _HAS_SNOWFLAKE_DRIVER, reason="Snowflake driver not available")
    async def test_cancel_with_mock_cursor(self, mock_snowflake_module):
        mock_cancel_cursor = MagicMock()
        mock_cancel_cursor.execute = MagicMock()
        mock_cancel_cursor.close = MagicMock()

        mock_conn = MagicMock()
        mock_conn.cursor = MagicMock(return_value=mock_cancel_cursor)

        driver = SnowflakeDriver(connection=mock_conn)
        driver._healthy = True
        driver._current_query_id = "query-abc-123"

        result = await driver.cancel()
        assert result is True
        mock_cancel_cursor.execute.assert_called_once_with("SELECT SYSTEM$CANCEL_QUERY(%s)", ("query-abc-123",))

    @pytest.mark.skipif(not _HAS_SNOWFLAKE_DRIVER, reason="Snowflake driver not available")
    async def test_close_is_noop(self, mock_snowflake_module):
        mock_conn = MagicMock()
        driver = SnowflakeDriver(connection=mock_conn)
        # close() should not raise
        await driver.close()

    @pytest.mark.skipif(not _HAS_SNOWFLAKE_DRIVER, reason="Snowflake driver not available")
    def test_is_healthy_before_connect(self, mock_snowflake_module):
        mock_conn = MagicMock()
        driver = SnowflakeDriver(connection=mock_conn)
        assert driver.is_healthy is False

    @pytest.mark.skipif(not _HAS_SNOWFLAKE_DRIVER, reason="Snowflake driver not available")
    async def test_connect_validates_connection(self, mock_snowflake_module):
        mock_conn = MagicMock()
        mock_conn.is_closed = MagicMock(return_value=False)

        driver = SnowflakeDriver(connection=mock_conn)
        await driver.connect()
        assert driver.is_healthy is True


# ---------------------------------------------------------------------------
# driver_name property tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testdrivername")
class TestDriverNameProperty:
    """Verify each driver exposes a driver_name property for ParameterContract lookup."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_sqlite_driver_name(self):
        driver = SQLiteDriver()
        assert driver.driver_name == "aiosqlite"

    def test_postgres_driver_name(self):
        mock_pool = MagicMock()
        driver = PostgresDriver(pool=mock_pool)
        assert driver.driver_name == "asyncpg"

    @pytest.mark.skipif(not _HAS_BIGQUERY_DRIVER, reason="BigQuery driver not available")
    def test_bigquery_driver_name(self):
        mock_client = MagicMock()
        driver = BigQueryDriver(project="test", client=mock_client)
        assert driver.driver_name == "bigquery"

    @pytest.mark.skipif(not _HAS_SNOWFLAKE_DRIVER, reason="Snowflake driver not available")
    def test_snowflake_driver_name(self):
        with patch("mcp_server_langgraph.execution.sql.drivers.snowflake._HAS_SNOWFLAKE", True):
            mock_conn = MagicMock()
            driver = SnowflakeDriver(connection=mock_conn)
            assert driver.driver_name == "snowflake"

    @pytest.mark.skipif(not _HAS_MYSQL_DRIVER, reason="MySQL driver not available")
    def test_mysql_driver_name(self):
        with patch("mcp_server_langgraph.execution.sql.drivers.mysql._HAS_MYSQL", True):
            mock_pool = MagicMock()
            driver = MySQLDriver(pool=mock_pool)
            assert driver.driver_name == "aiomysql"

    @pytest.mark.skipif(not _HAS_DUCKDB_DRIVER, reason="DuckDB driver not available")
    def test_duckdb_driver_name(self):
        with patch("mcp_server_langgraph.execution.sql.drivers.duckdb._HAS_DUCKDB", True):
            driver = DuckDBDriver()
            assert driver.driver_name == "duckdb"

    @pytest.mark.skipif(not _HAS_REDSHIFT_DRIVER, reason="Redshift driver not available")
    def test_redshift_driver_name(self):
        with patch("mcp_server_langgraph.execution.sql.drivers.redshift._HAS_REDSHIFT", True):
            mock_conn = MagicMock()
            driver = RedshiftDriver(connection=mock_conn)
            assert driver.driver_name == "redshift_connector"

    @pytest.mark.skipif(not _HAS_CLICKHOUSE_DRIVER, reason="ClickHouse driver not available")
    def test_clickhouse_driver_name(self):
        with patch("mcp_server_langgraph.execution.sql.drivers.clickhouse._HAS_CLICKHOUSE", True):
            mock_client = MagicMock()
            driver = ClickHouseDriver(client=mock_client)
            assert driver.driver_name == "asynch"

    @pytest.mark.skipif(not _HAS_TRINO_DRIVER, reason="Trino driver not available")
    def test_trino_driver_name(self):
        with patch("mcp_server_langgraph.execution.sql.drivers.trino._HAS_TRINO", True):
            mock_conn = MagicMock()
            driver = TrinoDriver(connection=mock_conn)
            assert driver.driver_name == "trino"

    def test_driver_name_is_abstract(self):
        """driver_name should be an abstract property on DatabaseDriver."""

        class IncompleteDriver(DatabaseDriver):
            @property
            def cancellation_type(self) -> CancellationType:
                return CancellationType.NONE

            async def connect(self) -> None:
                pass

            async def execute(self, sql, params=None):
                return []

            async def cancel(self) -> bool:
                return False

            async def close(self) -> None:
                pass

            @property
            def is_healthy(self) -> bool:
                return True

            # Missing: driver_name

        with pytest.raises(TypeError, match="abstract"):
            IncompleteDriver()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# ABC execute() signature compliance
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testabcsignaturecompliance")
class TestABCSignatureCompliance:
    """Verify that the execute() method accepts both Sequence and Mapping params."""

    def teardown_method(self) -> None:
        gc.collect()

    async def test_sqlite_accepts_dict_params(self):
        driver = SQLiteDriver(":memory:")
        await driver.connect()
        await driver.execute("CREATE TABLE t (id INTEGER, name TEXT)")
        result = await driver.execute("INSERT INTO t VALUES (:id, :name)", {"id": 1, "name": "test"})
        assert isinstance(result, list)
        await driver.close()

    async def test_sqlite_accepts_sequence_params(self):
        """SQLite driver should accept positional params from ParameterContract."""
        driver = SQLiteDriver(":memory:")
        await driver.connect()
        await driver.execute("CREATE TABLE t (id INTEGER, name TEXT)")
        # SQLite with ? placeholders and list params
        result = await driver.execute("INSERT INTO t VALUES (?, ?)", [1, "test"])
        assert isinstance(result, list)
        await driver.close()

    def test_concrete_driver_with_driver_name_works(self):
        """A concrete subclass implementing all abstract methods including driver_name."""

        class TestDriver(DatabaseDriver):
            @property
            def cancellation_type(self) -> CancellationType:
                return CancellationType.NONE

            @property
            def driver_name(self) -> str:
                return "test_driver"

            async def connect(self) -> None:
                pass

            async def execute(self, sql: str, params: Sequence | Mapping | None = None) -> list[dict]:
                return []

            async def cancel(self) -> bool:
                return False

            async def close(self) -> None:
                pass

            @property
            def is_healthy(self) -> bool:
                return True

        driver = TestDriver()
        assert driver.driver_name == "test_driver"


# ---------------------------------------------------------------------------
# MySQLDriver
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testmysqldriver")
class TestMySQLDriver:
    """Verify MySQLDriver behavior with mocked aiomysql pool."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture(autouse=True)
    def _mock_mysql(self):
        """Mock MySQL driver availability for all tests in this class."""
        with patch("mcp_server_langgraph.execution.sql.drivers.mysql._HAS_MYSQL", True):
            yield

    @pytest.mark.skipif(not _HAS_MYSQL_DRIVER, reason="MySQL driver not available")
    def test_cancellation_type_is_connection_level(self):
        mock_pool = MagicMock()
        driver = MySQLDriver(pool=mock_pool)
        assert driver.cancellation_type == CancellationType.CONNECTION_LEVEL

    @pytest.mark.skipif(not _HAS_MYSQL_DRIVER, reason="MySQL driver not available")
    async def test_cancel_with_no_active_query(self):
        mock_pool = MagicMock()
        driver = MySQLDriver(pool=mock_pool)
        result = await driver.cancel()
        assert result is False

    @pytest.mark.skipif(not _HAS_MYSQL_DRIVER, reason="MySQL driver not available")
    async def test_cancel_with_mock_connection(self):
        mock_cancel_conn = AsyncMock()  # noqa: async-mock-config
        mock_cancel_cursor = AsyncMock()  # noqa: async-mock-config
        mock_cancel_conn.cursor = MagicMock(return_value=mock_cancel_cursor)
        mock_cancel_cursor.__aenter__ = AsyncMock(return_value=mock_cancel_cursor)
        mock_cancel_cursor.__aexit__ = AsyncMock(return_value=False)

        mock_pool = AsyncMock()  # noqa: async-mock-config
        mock_pool.acquire = AsyncMock(return_value=mock_cancel_conn)
        mock_pool.release = MagicMock()

        driver = MySQLDriver(pool=mock_pool)
        driver._current_thread_id = 12345

        result = await driver.cancel()
        assert result is True

    @pytest.mark.skipif(not _HAS_MYSQL_DRIVER, reason="MySQL driver not available")
    async def test_close_releases_to_pool(self):
        mock_conn = AsyncMock()  # noqa: async-mock-config
        mock_pool = AsyncMock()  # noqa: async-mock-config
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = MagicMock()

        driver = MySQLDriver(pool=mock_pool)
        driver._conn = mock_conn
        await driver.close()
        mock_pool.release.assert_called_once_with(mock_conn)

    @pytest.mark.skipif(not _HAS_MYSQL_DRIVER, reason="MySQL driver not available")
    def test_is_healthy_before_connect(self):
        mock_pool = MagicMock()
        driver = MySQLDriver(pool=mock_pool)
        assert driver.is_healthy is False


# ---------------------------------------------------------------------------
# DuckDBDriver
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testduckdbdriver")
class TestDuckDBDriver:
    """Verify DuckDBDriver behavior with mocked/real duckdb connection."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture(autouse=True)
    def _mock_duckdb(self):
        """Mock DuckDB driver availability for all tests in this class."""
        with patch("mcp_server_langgraph.execution.sql.drivers.duckdb._HAS_DUCKDB", True):
            yield

    @pytest.mark.skipif(not _HAS_DUCKDB_DRIVER, reason="DuckDB driver not available")
    def test_cancellation_type_is_none(self):
        driver = DuckDBDriver()
        assert driver.cancellation_type == CancellationType.NONE

    @pytest.mark.skipif(not _HAS_DUCKDB_DRIVER, reason="DuckDB driver not available")
    async def test_cancel_returns_false(self):
        driver = DuckDBDriver()
        result = await driver.cancel()
        assert result is False

    @pytest.mark.skipif(not _HAS_DUCKDB_DRIVER, reason="DuckDB driver not available")
    def test_is_healthy_before_connect(self):
        driver = DuckDBDriver()
        assert driver.is_healthy is False


# ---------------------------------------------------------------------------
# RedshiftDriver
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testredshiftdriver")
class TestRedshiftDriver:
    """Verify RedshiftDriver behavior with mocked redshift_connector."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture(autouse=True)
    def _mock_redshift(self):
        """Mock Redshift driver availability for all tests in this class."""
        with patch("mcp_server_langgraph.execution.sql.drivers.redshift._HAS_REDSHIFT", True):
            yield

    @pytest.mark.skipif(not _HAS_REDSHIFT_DRIVER, reason="Redshift driver not available")
    def test_cancellation_type_is_connection_level(self):
        mock_conn = MagicMock()
        driver = RedshiftDriver(connection=mock_conn)
        assert driver.cancellation_type == CancellationType.CONNECTION_LEVEL

    @pytest.mark.skipif(not _HAS_REDSHIFT_DRIVER, reason="Redshift driver not available")
    async def test_cancel_with_no_active_query(self):
        mock_conn = MagicMock()
        driver = RedshiftDriver(connection=mock_conn)
        result = await driver.cancel()
        assert result is False

    @pytest.mark.skipif(not _HAS_REDSHIFT_DRIVER, reason="Redshift driver not available")
    async def test_close_is_noop(self):
        mock_conn = MagicMock()
        driver = RedshiftDriver(connection=mock_conn)
        await driver.close()

    @pytest.mark.skipif(not _HAS_REDSHIFT_DRIVER, reason="Redshift driver not available")
    def test_is_healthy_before_connect(self):
        mock_conn = MagicMock()
        driver = RedshiftDriver(connection=mock_conn)
        assert driver.is_healthy is False


# ---------------------------------------------------------------------------
# ClickHouseDriver
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testclickhousedriver")
class TestClickHouseDriver:
    """Verify ClickHouseDriver behavior with mocked asynch client."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture(autouse=True)
    def _mock_clickhouse(self):
        """Mock ClickHouse driver availability for all tests in this class."""
        with patch(
            "mcp_server_langgraph.execution.sql.drivers.clickhouse._HAS_CLICKHOUSE",
            True,
        ):
            yield

    @pytest.mark.skipif(not _HAS_CLICKHOUSE_DRIVER, reason="ClickHouse driver not available")
    def test_cancellation_type_is_job_based(self):
        mock_client = MagicMock()
        driver = ClickHouseDriver(client=mock_client)
        assert driver.cancellation_type == CancellationType.JOB_BASED

    @pytest.mark.skipif(not _HAS_CLICKHOUSE_DRIVER, reason="ClickHouse driver not available")
    async def test_cancel_with_no_active_query(self):
        mock_client = MagicMock()
        driver = ClickHouseDriver(client=mock_client)
        result = await driver.cancel()
        assert result is False

    @pytest.mark.skipif(not _HAS_CLICKHOUSE_DRIVER, reason="ClickHouse driver not available")
    async def test_close_is_noop(self):
        mock_client = MagicMock()
        driver = ClickHouseDriver(client=mock_client)
        await driver.close()

    @pytest.mark.skipif(not _HAS_CLICKHOUSE_DRIVER, reason="ClickHouse driver not available")
    def test_is_healthy_before_connect(self):
        mock_client = MagicMock()
        driver = ClickHouseDriver(client=mock_client)
        assert driver.is_healthy is False


# ---------------------------------------------------------------------------
# TrinoDriver
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.xdist_group(name="testTrinodriver")
class TestTrinoDriver:
    """Verify TrinoDriver behavior with mocked trino connection."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture(autouse=True)
    def _mock_trino(self):
        """Mock Trino driver availability for all tests in this class."""
        with patch("mcp_server_langgraph.execution.sql.drivers.trino._HAS_TRINO", True):
            yield

    @pytest.mark.skipif(not _HAS_TRINO_DRIVER, reason="Trino driver not available")
    def test_cancellation_type_is_job_based(self):
        mock_conn = MagicMock()
        driver = TrinoDriver(connection=mock_conn)
        assert driver.cancellation_type == CancellationType.JOB_BASED

    @pytest.mark.skipif(not _HAS_TRINO_DRIVER, reason="Trino driver not available")
    async def test_cancel_with_no_active_query(self):
        mock_conn = MagicMock()
        driver = TrinoDriver(connection=mock_conn)
        result = await driver.cancel()
        assert result is False

    @pytest.mark.skipif(not _HAS_TRINO_DRIVER, reason="Trino driver not available")
    async def test_close_is_noop(self):
        mock_conn = MagicMock()
        driver = TrinoDriver(connection=mock_conn)
        await driver.close()

    @pytest.mark.skipif(not _HAS_TRINO_DRIVER, reason="Trino driver not available")
    def test_is_healthy_before_connect(self):
        mock_conn = MagicMock()
        driver = TrinoDriver(connection=mock_conn)
        assert driver.is_healthy is False
