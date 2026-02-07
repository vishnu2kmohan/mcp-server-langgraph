"""SQLite driver implementation using aiosqlite.

Provides async SQLite access for in-process, sandboxed SQL execution.
SQLite does not support query cancellation; cancel() is a no-op that
logs a warning and returns False.
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
    import aiosqlite
except ImportError:
    aiosqlite = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class SQLiteDriver(DatabaseDriver):
    """Async SQLite driver backed by aiosqlite.

    Uses an in-process SQLite database. Since SQLite runs in the same
    process, there is no external mechanism to cancel a running query;
    cancellation_type is ``CancellationType.NONE``.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file, or ``":memory:"`` for an
        in-memory database (default).
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None  # type: ignore[name-defined]

    # -- DatabaseDriver protocol ------------------------------------------------

    @property
    def cancellation_type(self) -> CancellationType:
        """SQLite has no cancellation support."""
        return CancellationType.NONE

    @property
    def driver_name(self) -> str:
        """aiosqlite driver for ParameterContract lookup."""
        return "aiosqlite"

    async def connect(self) -> None:
        """Open an aiosqlite connection to *db_path*."""
        if aiosqlite is None:
            raise SQLConnectionError("aiosqlite is not installed. Install it with: pip install aiosqlite")
        try:
            self._conn = await aiosqlite.connect(self._db_path)
            # Enable dict-like row access via sqlite3.Row
            self._conn.row_factory = aiosqlite.Row  # type: ignore[assignment]
            logger.debug("SQLite connection opened: %s", self._db_path)
        except Exception as exc:
            self._conn = None
            raise SQLConnectionError(f"Failed to connect to SQLite database: {exc}") from exc

    async def execute(
        self,
        sql: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute *sql* and return results as a list of dicts.

        Accepts both named (dict) and positional (list) parameters.
        """
        if self._conn is None:
            raise SQLConnectionError("Not connected. Call connect() first.")

        cursor = await self._conn.execute(sql, params if params is not None else {})

        if cursor.description is None:
            # Non-SELECT statement (INSERT, UPDATE, DELETE, DDL)
            await self._conn.commit()
            return []

        columns = [desc[0] for desc in cursor.description]
        rows = await cursor.fetchall()
        return [dict(zip(columns, row, strict=False)) for row in rows]

    async def cancel(self) -> bool:
        """SQLite does not support query cancellation.

        Returns ``False`` and logs a warning.
        """
        logger.warning("SQLite does not support query cancellation; cancel() is a no-op.")
        return False

    async def close(self) -> None:
        """Close the aiosqlite connection."""
        if self._conn is not None:
            try:
                await self._conn.close()
                logger.debug("SQLite connection closed: %s", self._db_path)
            finally:
                self._conn = None

    @property
    def is_healthy(self) -> bool:
        """Return ``True`` if the connection is open."""
        return self._conn is not None
