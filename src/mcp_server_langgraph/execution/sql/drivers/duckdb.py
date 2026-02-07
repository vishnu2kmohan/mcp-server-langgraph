"""DuckDB driver implementation.

Provides async DuckDB access for in-process analytics. DuckDB is a sync
library, so queries are run in a thread executor. Like SQLite, DuckDB
does not support query cancellation.

duckdb is an optional dependency; importing this module without it
installed raises a clear error at construction time.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping, Sequence
from typing import Any

from mcp_server_langgraph.execution.sql.drivers.base import (
    CancellationType,
    DatabaseDriver,
)
from mcp_server_langgraph.execution.sql.exceptions import (
    SQLConnectionError,
    SQLExecutionError,
)

logger = logging.getLogger(__name__)

try:
    import duckdb

    _HAS_DUCKDB = True
except ImportError:
    _HAS_DUCKDB = False


class DuckDBDriver(DatabaseDriver):
    """In-process DuckDB driver.

    Parameters:
        db_path: Path to the DuckDB database file, or ``":memory:"`` for
            an in-memory database (default).
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        if not _HAS_DUCKDB:
            raise ImportError("duckdb is required for DuckDBDriver. Install it with: pip install duckdb")
        self._db_path = db_path
        self._conn: duckdb.DuckDBPyConnection | None = None

    @property
    def cancellation_type(self) -> CancellationType:
        return CancellationType.NONE

    @property
    def driver_name(self) -> str:
        return "duckdb"

    async def connect(self) -> None:
        """Open a DuckDB connection."""
        try:
            loop = asyncio.get_running_loop()
            self._conn = await loop.run_in_executor(None, lambda: duckdb.connect(self._db_path))
            logger.debug("DuckDB connection opened: %s", self._db_path)
        except Exception as exc:
            self._conn = None
            raise SQLConnectionError(f"Failed to connect to DuckDB: {exc}") from exc

    async def execute(
        self,
        sql: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute *sql* and return results as a list of dicts."""
        if self._conn is None:
            raise SQLConnectionError("Not connected. Call connect() first.")

        loop = asyncio.get_running_loop()

        def _run() -> list[dict[str, Any]]:
            assert self._conn is not None
            if params is not None:
                if isinstance(params, Sequence):
                    result = self._conn.execute(sql, list(params))
                else:
                    result = self._conn.execute(sql, list(params.values()))
            else:
                result = self._conn.execute(sql)

            if result.description is None:
                return []

            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()
            return [dict(zip(columns, row, strict=False)) for row in rows]

        try:
            return await loop.run_in_executor(None, _run)
        except Exception as exc:
            if isinstance(exc, SQLConnectionError):
                raise
            raise SQLExecutionError(f"DuckDB query execution failed: {exc}") from exc

    async def cancel(self) -> bool:
        """DuckDB does not support query cancellation."""
        logger.warning("DuckDB does not support query cancellation; cancel() is a no-op.")
        return False

    async def close(self) -> None:
        """Close the DuckDB connection."""
        if self._conn is not None:
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._conn.close)
                logger.debug("DuckDB connection closed: %s", self._db_path)
            finally:
                self._conn = None

    @property
    def is_healthy(self) -> bool:
        return self._conn is not None
