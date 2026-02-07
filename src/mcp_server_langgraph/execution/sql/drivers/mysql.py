"""MySQL driver implementation using aiomysql.

Provides async MySQL access with connection-level query cancellation
via ``KILL QUERY <thread_id>``.

The MySQL pool is expected to be managed externally, so ``close()``
releases the connection back to the pool.

aiomysql is an optional dependency; importing this module without it
installed raises a clear error at construction time.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

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
    import aiomysql

    _HAS_MYSQL = True
except ImportError:
    _HAS_MYSQL = False

if TYPE_CHECKING:
    import aiomysql


class MySQLDriver(DatabaseDriver):
    """Async MySQL driver backed by aiomysql.

    Parameters:
        pool: An ``aiomysql.Pool`` instance from which connections are acquired.
    """

    def __init__(self, pool: aiomysql.Pool) -> None:  # type: ignore[name-defined]
        if not _HAS_MYSQL:
            raise ImportError("aiomysql is required for MySQLDriver. Install it with: pip install aiomysql")
        self._pool = pool
        self._conn: aiomysql.Connection | None = None  # type: ignore[name-defined]
        self._current_thread_id: int | None = None

    @property
    def cancellation_type(self) -> CancellationType:
        return CancellationType.CONNECTION_LEVEL

    @property
    def driver_name(self) -> str:
        return "aiomysql"

    async def connect(self) -> None:
        """Acquire a connection from the pool."""
        try:
            self._conn = await self._pool.acquire()
            self._current_thread_id = self._conn.thread_id()
            logger.debug("MySQL connection acquired (thread_id=%s)", self._current_thread_id)
        except Exception as exc:
            self._conn = None
            raise SQLConnectionError(f"Failed to acquire MySQL connection: {exc}") from exc

    async def execute(
        self,
        sql: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute *sql* and return results as a list of dicts."""
        if self._conn is None:
            raise SQLConnectionError("Not connected. Call connect() first.")

        try:
            async with self._conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(sql, params)
                if cursor.description is None:
                    return []
                rows = await cursor.fetchall()
                return list(rows)
        except Exception as exc:
            if isinstance(exc, SQLConnectionError):
                raise
            raise SQLExecutionError(f"MySQL query execution failed: {exc}") from exc

    async def cancel(self) -> bool:
        """Cancel the in-flight query via ``KILL QUERY <thread_id>``."""
        thread_id = self._current_thread_id
        if thread_id is None:
            logger.debug("No active MySQL thread_id to cancel.")
            return False

        try:
            cancel_conn = await self._pool.acquire()
            try:
                async with cancel_conn.cursor() as cursor:
                    # KILL QUERY does not support parameterized queries in MySQL.
                    # Validate thread_id is an integer to prevent SQL injection.
                    if not isinstance(thread_id, int):
                        logger.warning("Invalid thread_id type: %s", type(thread_id))
                        return False
                    await cursor.execute(f"KILL QUERY {int(thread_id)}")
                logger.info("Killed MySQL query on thread_id %d", thread_id)
                return True
            finally:
                self._pool.release(cancel_conn)
        except Exception:
            logger.warning(
                "Failed to cancel MySQL query on thread_id %d",
                thread_id,
                exc_info=True,
            )
            return False

    async def close(self) -> None:
        """Release the connection back to the pool."""
        if self._conn is not None:
            try:
                self._pool.release(self._conn)
                logger.debug("MySQL connection released to pool.")
            finally:
                self._conn = None
                self._current_thread_id = None

    @property
    def is_healthy(self) -> bool:
        return self._conn is not None
