"""Driver registry for dialect-aware driver lookup.

Maps SQL dialect names to their corresponding ``DatabaseDriver``
subclass, enabling the execution engine to resolve the correct driver
at runtime based on a connection's declared dialect.

Default mappings for ``postgres`` and ``sqlite`` are always registered.
Optional mappings for ``bigquery`` and ``snowflake`` are registered if
their dependencies are available (google-cloud-bigquery and
snowflake-connector-python respectively).
"""

from __future__ import annotations

import logging

from mcp_server_langgraph.execution.sql.drivers.base import DatabaseDriver
from mcp_server_langgraph.execution.sql.drivers.postgres import PostgresDriver
from mcp_server_langgraph.execution.sql.drivers.sqlite import SQLiteDriver

logger = logging.getLogger(__name__)


class DriverRegistry:
    """Maps dialect names to ``DatabaseDriver`` subclasses.

    Usage::

        registry = DriverRegistry()
        driver_cls = registry.get_driver("postgres")
        driver = driver_cls(pool=my_pool)

    The registry pre-registers drivers for ``postgres`` and ``sqlite``.
    BigQuery and Snowflake are registered if their respective libraries
    are importable.
    """

    def __init__(self) -> None:
        self._drivers: dict[str, type[DatabaseDriver]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register built-in drivers."""
        self.register("postgres", PostgresDriver)
        self.register("sqlite", SQLiteDriver)

        # Optional: BigQuery
        try:
            from mcp_server_langgraph.execution.sql.drivers.bigquery import (
                BigQueryDriver,
            )

            self.register("bigquery", BigQueryDriver)
        except ImportError:
            logger.debug("BigQuery driver not available (google-cloud-bigquery not installed)")

        # Optional: Snowflake
        try:
            from mcp_server_langgraph.execution.sql.drivers.snowflake import (
                SnowflakeDriver,
            )

            self.register("snowflake", SnowflakeDriver)
        except ImportError:
            logger.debug("Snowflake driver not available (snowflake-connector-python not installed)")

        # Optional: MySQL
        try:
            from mcp_server_langgraph.execution.sql.drivers.mysql import MySQLDriver

            self.register("mysql", MySQLDriver)
        except ImportError:
            logger.debug("MySQL driver not available (aiomysql not installed)")

        # Optional: DuckDB
        try:
            from mcp_server_langgraph.execution.sql.drivers.duckdb import DuckDBDriver

            self.register("duckdb", DuckDBDriver)
        except ImportError:
            logger.debug("DuckDB driver not available (duckdb not installed)")

        # Optional: Redshift
        try:
            from mcp_server_langgraph.execution.sql.drivers.redshift import (
                RedshiftDriver,
            )

            self.register("redshift", RedshiftDriver)
        except ImportError:
            logger.debug("Redshift driver not available (redshift-connector not installed)")

        # Optional: ClickHouse
        try:
            from mcp_server_langgraph.execution.sql.drivers.clickhouse import (
                ClickHouseDriver,
            )

            self.register("clickhouse", ClickHouseDriver)
        except ImportError:
            logger.debug("ClickHouse driver not available (asynch not installed)")

        # Optional: Trino
        try:
            from mcp_server_langgraph.execution.sql.drivers.trino import TrinoDriver

            self.register("trino", TrinoDriver)
        except ImportError:
            logger.debug("Trino driver not available (trino not installed)")

    def register(self, dialect: str, driver_cls: type[DatabaseDriver]) -> None:
        """Register a driver class for a dialect.

        Parameters
        ----------
        dialect:
            The dialect name (e.g. ``"postgres"``, ``"sqlite"``).
        driver_cls:
            A concrete subclass of ``DatabaseDriver``.
        """
        if not isinstance(dialect, str) or not dialect:
            raise ValueError("dialect must be a non-empty string")
        if not (isinstance(driver_cls, type) and issubclass(driver_cls, DatabaseDriver)):
            raise TypeError(f"driver_cls must be a subclass of DatabaseDriver, got {driver_cls!r}")
        self._drivers[dialect] = driver_cls
        logger.debug("Registered driver %s for dialect '%s'", driver_cls.__name__, dialect)

    def get_driver(self, dialect: str) -> type[DatabaseDriver]:
        """Look up the driver class for *dialect*.

        Parameters
        ----------
        dialect:
            The dialect name to look up.

        Returns
        -------
        type[DatabaseDriver]
            The driver class registered for the given dialect.

        Raises
        ------
        KeyError
            If no driver is registered for *dialect*.
        """
        try:
            return self._drivers[dialect]
        except KeyError:
            available = ", ".join(sorted(self._drivers)) or "(none)"
            raise KeyError(f"No driver registered for dialect '{dialect}'. Available dialects: {available}") from None

    def list_dialects(self) -> list[str]:
        """Return a sorted list of all registered dialect names."""
        return sorted(self._drivers.keys())
