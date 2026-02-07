"""Redshift driver implementation using redshift_connector.

Provides async Redshift access via a sync connector run in a thread
executor. Cancellation is performed via ``pg_cancel_backend()``
(Redshift is PostgreSQL-compatible).

redshift_connector is an optional dependency; importing this module
without it installed raises a clear error at construction time.
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
    import redshift_connector

    _HAS_REDSHIFT = True
except ImportError:
    _HAS_REDSHIFT = False

if TYPE_CHECKING:
    import redshift_connector


class RedshiftDriver(DatabaseDriver):
    """Redshift driver using redshift_connector.

    Parameters:
        connection: A ``redshift_connector.Connection`` instance,
            typically acquired from a connection pool.
    """

    def __init__(
        self,
        connection: redshift_connector.Connection | None = None,  # type: ignore[name-defined]
    ) -> None:
        if not _HAS_REDSHIFT:
            raise ImportError(
                "redshift_connector is required for RedshiftDriver. Install it with: pip install redshift-connector"
            )
        self._connection = connection
        self._healthy = False
        self._current_pid: int | None = None

    @property
    def cancellation_type(self) -> CancellationType:
        return CancellationType.CONNECTION_LEVEL

    @property
    def driver_name(self) -> str:
        return "redshift_connector"

    async def connect(self) -> None:
        """Validate the injected connection."""
        if self._connection is None:
            raise SQLConnectionError("No Redshift connection provided. Supply a connection from the pool via the constructor.")
        try:
            loop = asyncio.get_running_loop()
            cursor = await loop.run_in_executor(None, self._connection.cursor)
            await loop.run_in_executor(None, lambda: cursor.execute("SELECT 1"))
            cursor.close()
            self._healthy = True
            logger.info("Redshift driver connected")
        except Exception as exc:
            self._healthy = False
            raise SQLConnectionError(f"Failed to validate Redshift connection: {exc}") from exc

    async def execute(
        self,
        sql: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute *sql* and return results as a list of dicts."""
        if self._connection is None or not self._healthy:
            raise SQLConnectionError("Redshift driver is not connected")

        loop = asyncio.get_running_loop()

        def _run() -> list[dict[str, Any]]:
            assert self._connection is not None
            # Capture backend PID for cancellation support
            self._current_pid = getattr(self._connection, "backend_pid", None)
            cursor = self._connection.cursor()
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
                cursor.close()
                self._current_pid = None

        try:
            return await loop.run_in_executor(None, _run)
        except Exception as exc:
            if isinstance(exc, (SQLConnectionError, SQLExecutionError)):
                raise
            raise SQLExecutionError(f"Redshift query execution failed: {exc}") from exc

    async def cancel(self) -> bool:
        """Cancel the in-flight query via pg_cancel_backend()."""
        if self._connection is None:
            logger.debug("No Redshift connection for cancellation.")
            return False

        pid = self._current_pid
        if pid is None:
            logger.debug("No active Redshift query PID to cancel.")
            return False

        try:
            loop = asyncio.get_running_loop()

            def _cancel() -> bool:
                assert self._connection is not None
                cursor = self._connection.cursor()
                try:
                    cursor.execute("SELECT pg_cancel_backend(%(pid)s)", {"pid": pid})
                    result = cursor.fetchone()
                    return bool(result and result[0])
                finally:
                    cursor.close()

            cancelled = await loop.run_in_executor(None, _cancel)
            logger.info("pg_cancel_backend(%d) returned %s", pid, cancelled)
            return cancelled
        except Exception:
            logger.warning("Failed to cancel Redshift query on PID %d", pid, exc_info=True)
            return False

    async def close(self) -> None:
        """No-op: connection is managed by the external pool."""

    @property
    def is_healthy(self) -> bool:
        return self._healthy
