"""Snowflake database driver with job-based cancellation.

Uses the snowflake-connector-python library to execute parameterized
queries against Snowflake Data Cloud. Cancellation is achieved by
calling ``SYSTEM$CANCEL_QUERY`` with the tracked ``sfqid`` of the
in-flight query.

The underlying connection is expected to be managed by an external
connection pool, so ``close()`` is intentionally a no-op.

snowflake-connector-python is an optional dependency; importing this
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
    SQLTimeoutError,
)

logger = logging.getLogger(__name__)

try:
    import snowflake.connector  # type: ignore[import-not-found,import-untyped]  # noqa: F401

    _HAS_SNOWFLAKE = True
except ImportError:
    _HAS_SNOWFLAKE = False

if TYPE_CHECKING:
    from snowflake.connector import SnowflakeConnection
    from snowflake.connector.cursor import SnowflakeCursor  # type: ignore[import-not-found,import-untyped]


class SnowflakeDriver(DatabaseDriver):
    """Snowflake driver using snowflake-connector-python.

    Parameters:
        connection: A ``SnowflakeConnection`` instance, typically
            acquired from a connection pool.
        timeout_seconds: Per-query timeout in seconds.
    """

    def __init__(
        self,
        connection: SnowflakeConnection | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not _HAS_SNOWFLAKE:
            raise ImportError(
                "snowflake-connector-python is required for SnowflakeDriver. "
                "Install it with: pip install snowflake-connector-python"
            )
        self._connection: SnowflakeConnection | None = connection
        self._timeout_seconds = timeout_seconds
        self._current_query_id: str | None = None
        self._healthy = False

    # -- DatabaseDriver interface ------------------------------------------

    @property
    def cancellation_type(self) -> CancellationType:
        return CancellationType.JOB_BASED

    @property
    def driver_name(self) -> str:
        """snowflake driver for ParameterContract lookup."""
        return "snowflake"

    async def connect(self) -> None:
        """Mark the driver as healthy.

        The connection is expected to be injected via the constructor
        (from a pool).  This method validates that a connection was
        provided and is still open.
        """
        if self._connection is None:
            raise SQLConnectionError(
                "No Snowflake connection provided. Supply a connection from the pool via the constructor."
            )
        try:
            loop = asyncio.get_running_loop()
            is_closed = await loop.run_in_executor(
                None,
                lambda: self._connection.is_closed(),  # type: ignore[union-attr]
            )
            if is_closed:
                raise SQLConnectionError("Snowflake connection is closed")
            self._healthy = True
            logger.info("Snowflake driver connected")
        except SQLConnectionError:
            self._healthy = False
            raise
        except Exception as exc:
            self._healthy = False
            raise SQLConnectionError("Failed to validate Snowflake connection") from exc

    async def execute(
        self,
        sql: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute *sql* against Snowflake and return rows as dicts."""
        if self._connection is None or not self._healthy:
            raise SQLConnectionError("Snowflake driver is not connected")

        loop = asyncio.get_running_loop()

        try:
            cursor: SnowflakeCursor = await loop.run_in_executor(
                None,
                lambda: self._connection.cursor(),  # type: ignore[union-attr]
            )

            try:
                await loop.run_in_executor(
                    None,
                    lambda: cursor.execute(
                        sql,
                        params=params,
                        timeout=int(self._timeout_seconds),
                    ),
                )

                # Track the query ID for cancellation
                self._current_query_id = cursor.sfqid

                rows = await loop.run_in_executor(None, cursor.fetchall)
                columns = [desc[0] for desc in (cursor.description or [])]

                return [dict(zip(columns, row, strict=False)) for row in rows]

            finally:
                await loop.run_in_executor(None, cursor.close)

        except Exception as exc:
            exc_name = type(exc).__name__
            if "Timeout" in exc_name or "timeout" in str(exc).lower():
                raise SQLTimeoutError(f"Snowflake query timed out after {self._timeout_seconds}s") from exc
            # Re-raise our own exceptions as-is
            if isinstance(exc, (SQLConnectionError, SQLTimeoutError)):
                raise
            raise SQLExecutionError(f"Snowflake query execution failed: {exc}") from exc
        finally:
            self._current_query_id = None

    async def cancel(self) -> bool:
        """Cancel the in-flight Snowflake query using SYSTEM$CANCEL_QUERY."""
        query_id = self._current_query_id
        if query_id is None:
            logger.debug("No in-flight Snowflake query to cancel")
            return False

        if self._connection is None:
            logger.warning("Cannot cancel: no Snowflake connection")
            return False

        try:
            loop = asyncio.get_running_loop()
            cursor: SnowflakeCursor = await loop.run_in_executor(
                None,
                lambda: self._connection.cursor(),  # type: ignore[union-attr]
            )
            try:
                await loop.run_in_executor(
                    None,
                    lambda: cursor.execute("SELECT SYSTEM$CANCEL_QUERY(%s)", (query_id,)),
                )
                logger.info("Cancelled Snowflake query %s", query_id)
                return True
            finally:
                await loop.run_in_executor(None, cursor.close)
        except Exception:
            logger.warning("Failed to cancel Snowflake query %s", query_id, exc_info=True)
            return False

    async def close(self) -> None:
        """No-op: connection is managed by the external pool."""

    @property
    def is_healthy(self) -> bool:
        return self._healthy
