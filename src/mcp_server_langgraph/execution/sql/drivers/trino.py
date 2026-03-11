"""Trino driver implementation.

Provides async Trino access via a sync connector run in a thread
executor. Cancellation is performed via cursor.cancel().

trino (trino[sqlalchemy]) is an optional dependency; importing this
module without it installed raises a clear error at construction time.
"""

from __future__ import annotations

import asyncio
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
    import trino  # type: ignore[import-not-found]  # noqa: F401

    _HAS_TRINO = True
except ImportError:
    _HAS_TRINO = False

if TYPE_CHECKING:
    from trino.dbapi import Connection as TrinoConnection  # type: ignore[import-not-found]


class TrinoDriver(DatabaseDriver):
    """Trino driver using trino-python-client.

    Parameters:
        connection: A ``trino.dbapi.Connection`` instance.
    """

    def __init__(
        self,
        connection: TrinoConnection | None = None,
    ) -> None:
        if not _HAS_TRINO:
            raise ImportError("trino is required for TrinoDriver. Install it with: pip install trino")
        self._connection = connection
        self._healthy = False
        self._current_cursor: Any | None = None

    @property
    def cancellation_type(self) -> CancellationType:
        return CancellationType.JOB_BASED

    @property
    def driver_name(self) -> str:
        return "trino"

    async def connect(self) -> None:
        """Validate the injected connection."""
        if self._connection is None:
            raise SQLConnectionError("No Trino connection provided. Supply a connection via the constructor.")
        self._healthy = True
        logger.info("Trino driver connected")

    async def execute(
        self,
        sql: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute *sql* and return results as a list of dicts."""
        if self._connection is None or not self._healthy:
            raise SQLConnectionError("Trino driver is not connected")

        loop = asyncio.get_running_loop()

        def _run() -> list[dict[str, Any]]:
            assert self._connection is not None
            cursor = self._connection.cursor()
            self._current_cursor = cursor
            try:
                if params is not None:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)

                if cursor.description is None:
                    return []

                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row, strict=False)) for row in rows]
            finally:
                self._current_cursor = None

        try:
            return await loop.run_in_executor(None, _run)
        except Exception as exc:
            if isinstance(exc, (SQLConnectionError, SQLExecutionError)):
                raise
            raise SQLExecutionError(f"Trino query execution failed: {exc}") from exc

    async def cancel(self) -> bool:
        """Cancel the in-flight query via cursor.cancel()."""
        cursor = self._current_cursor
        if cursor is None:
            logger.debug("No in-flight Trino query to cancel")
            return False

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, cursor.cancel)
            logger.info("Cancelled Trino query")
            return True
        except Exception:
            logger.warning("Failed to cancel Trino query", exc_info=True)
            return False

    async def close(self) -> None:
        """No-op: connection is managed externally."""

    @property
    def is_healthy(self) -> bool:
        return self._healthy
