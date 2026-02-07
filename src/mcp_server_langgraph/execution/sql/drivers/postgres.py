"""PostgreSQL driver implementation using asyncpg.

Provides async PostgreSQL access with connection-level query
cancellation via ``pg_cancel_backend()``.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from mcp_server_langgraph.execution.sql.drivers.base import (
    CancellationType,
    DatabaseDriver,
)
from mcp_server_langgraph.execution.sql.exceptions import SQLConnectionError

try:
    import asyncpg
except ImportError:
    asyncpg = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class PostgresDriver(DatabaseDriver):
    """Async PostgreSQL driver backed by asyncpg.

    Acquires connections from a pre-existing ``asyncpg.Pool`` and
    supports connection-level cancellation via ``pg_cancel_backend()``.

    Parameters
    ----------
    pool:
        An ``asyncpg.Pool`` instance from which connections are acquired.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:  # type: ignore[name-defined]
        if asyncpg is None:
            raise SQLConnectionError("asyncpg is not installed. Install it with: pip install asyncpg")
        self._pool = pool
        self._conn: asyncpg.Connection | None = None  # type: ignore[name-defined]
        self._current_pid: int | None = None

    # -- DatabaseDriver protocol ------------------------------------------------

    @property
    def cancellation_type(self) -> CancellationType:
        """PostgreSQL supports connection-level cancellation."""
        return CancellationType.CONNECTION_LEVEL

    @property
    def driver_name(self) -> str:
        """asyncpg driver for ParameterContract lookup."""
        return "asyncpg"

    async def connect(self) -> None:
        """Acquire a connection from the pool."""
        try:
            self._conn = await self._pool.acquire()
            logger.debug(
                "PostgreSQL connection acquired from pool (pid=%s)",
                self._conn.get_server_pid(),
            )
        except Exception as exc:
            self._conn = None
            raise SQLConnectionError(f"Failed to acquire PostgreSQL connection: {exc}") from exc

    async def execute(
        self,
        sql: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute *sql* and return results as a list of dicts.

        Tracks the server PID so that ``cancel()`` can issue
        ``pg_cancel_backend()`` against the correct backend.

        Parameters are passed as positional arguments to asyncpg using
        ``$1, $2, ...`` placeholder style. After ParameterContract
        translation, *params* is a list of positional values.
        """
        if self._conn is None:
            raise SQLConnectionError("Not connected. Call connect() first.")

        # Track PID for cancellation
        self._current_pid = self._conn.get_server_pid()

        try:
            if isinstance(params, Sequence):
                args = tuple(params)
            elif isinstance(params, Mapping):
                args = tuple(params.values())
            else:
                args = ()
            records = await self._conn.fetch(sql, *args)
            return [dict(record) for record in records]
        finally:
            self._current_pid = None

    async def cancel(self) -> bool:
        """Cancel the in-flight query via ``pg_cancel_backend()``.

        Uses a separate connection from the pool to send the cancel
        signal, so this is safe to call concurrently with ``execute()``.

        Returns ``True`` if the cancellation signal was sent
        successfully, ``False`` otherwise.
        """
        pid = self._current_pid
        if pid is None:
            logger.debug("No active query PID to cancel.")
            return False

        try:
            result = await self._pool.fetchval("SELECT pg_cancel_backend($1)", pid)
            cancelled = bool(result)
            logger.info("pg_cancel_backend(%d) returned %s", pid, cancelled)
            return cancelled
        except Exception:
            logger.exception("Failed to cancel query on backend PID %d", pid)
            return False

    async def close(self) -> None:
        """Release the connection back to the pool."""
        if self._conn is not None:
            try:
                await self._pool.release(self._conn)
                logger.debug("PostgreSQL connection released to pool.")
            finally:
                self._conn = None
                self._current_pid = None

    @property
    def is_healthy(self) -> bool:
        """Return ``True`` if the connection is open and usable."""
        if self._conn is None:
            return False
        return not self._conn.is_closed()
