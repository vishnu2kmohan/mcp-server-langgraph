"""ClickHouse driver implementation using asynch.

Provides async ClickHouse access via the asynch (async ClickHouse)
library. Uses HTTP protocol on port 8123. Cancellation is performed
via ``KILL QUERY WHERE query_id = ...``.

asynch is an optional dependency; importing this module without it
installed raises a clear error at construction time.
"""

from __future__ import annotations

import logging
import uuid
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
    import asynch  # type: ignore[import-not-found,import-untyped]  # noqa: F401

    _HAS_CLICKHOUSE = True
except ImportError:
    _HAS_CLICKHOUSE = False

if TYPE_CHECKING:
    pass


class ClickHouseDriver(DatabaseDriver):
    """ClickHouse driver using asynch.

    Parameters:
        client: An asynch connection/client instance.
    """

    def __init__(self, client: Any = None) -> None:
        if not _HAS_CLICKHOUSE:
            raise ImportError("asynch is required for ClickHouseDriver. Install it with: pip install asynch")
        self._client = client
        self._healthy = False
        self._current_query_id: str | None = None

    @property
    def cancellation_type(self) -> CancellationType:
        return CancellationType.JOB_BASED

    @property
    def driver_name(self) -> str:
        return "asynch"

    async def connect(self) -> None:
        """Validate the client connection."""
        if self._client is None:
            raise SQLConnectionError("No ClickHouse client provided. Supply a client via the constructor.")
        self._healthy = True
        logger.info("ClickHouse driver connected")

    async def execute(
        self,
        sql: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute *sql* and return results as a list of dicts."""
        if self._client is None or not self._healthy:
            raise SQLConnectionError("ClickHouse driver is not connected")

        query_id = str(uuid.uuid4())
        self._current_query_id = query_id

        try:
            cursor = self._client.cursor()
            if params is not None:
                await cursor.execute(sql, params, query_id=query_id)
            else:
                await cursor.execute(sql, query_id=query_id)

            if cursor.description is None:
                return []

            columns = [desc[0] for desc in cursor.description]
            rows = await cursor.fetchall()
            return [dict(zip(columns, row, strict=False)) for row in rows]
        except Exception as exc:
            if isinstance(exc, (SQLConnectionError, SQLExecutionError)):
                raise
            raise SQLExecutionError(f"ClickHouse query execution failed: {exc}") from exc
        finally:
            self._current_query_id = None

    async def cancel(self) -> bool:
        """Cancel the in-flight query via KILL QUERY."""
        query_id = self._current_query_id
        if query_id is None:
            logger.debug("No in-flight ClickHouse query to cancel")
            return False

        if self._client is None:
            logger.warning("Cannot cancel: no ClickHouse client")
            return False

        try:
            # Validate UUID format before interpolation (KILL QUERY does not
            # support parameterized queries in ClickHouse). query_id is always
            # generated internally via uuid.uuid4(), but we validate defensively.
            uuid.UUID(query_id)  # Raises ValueError if not a valid UUID
            cursor = self._client.cursor()
            await cursor.execute(f"KILL QUERY WHERE query_id = '{query_id}'")
            logger.info("Cancelled ClickHouse query %s", query_id)
            return True
        except Exception:
            logger.warning("Failed to cancel ClickHouse query %s", query_id, exc_info=True)
            return False

    async def close(self) -> None:
        """No-op: client is shared and not owned by this driver."""

    @property
    def is_healthy(self) -> bool:
        return self._healthy
